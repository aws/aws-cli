# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""Bounded polling shared by start-query/poll command lifecycles.

Some query lifecycles (e.g. ``athena:GetQueryExecution`` and
``logs:GetQueryResults``) have no botocore waiter, so a command must poll a
started query to a terminal state by hand. Commands share the *timing* mechanism
here -- a monotonic deadline, a poll-count cap, and a geometric (1.5x, capped)
backoff -- while each keeps its own terminal-state and error handling so no
behaviour drifts between them.

``clock`` and ``sleep`` are injectable so tests advance time deterministically
without real sleeping.
"""

from __future__ import annotations

import time
from collections.abc import Callable

# Backoff ceiling applied to the sleep interval between polls.
MAX_POLL_INTERVAL = 5.0
_GROWTH = 1.5


class BoundedPoller:
    """A monotonic, bounded poll loop clock with capped geometric backoff.

    Usage::

        poller = BoundedPoller(interval=1.0, max_wait=300.0, max_polls=10_000,
                               clock=clock, sleep=sleep)
        while True:
            result = do_one_poll()
            poller.record_poll()
            if terminal(result):
                break
            if poller.exhausted():
                ... handle timeout (e.g. StopQuery) ...
                break
            poller.sleep_and_backoff()
    """

    def __init__(
        self,
        *,
        interval: float,
        max_wait: float,
        max_polls: int,
        clock: Callable[[], float],
        sleep: Callable[[float], None],
        max_interval: float = MAX_POLL_INTERVAL,
        growth: float = _GROWTH,
    ) -> None:
        self._interval = float(interval)
        self._max_wait = float(max_wait)
        self._max_polls = int(max_polls)
        self._clock = clock
        self._sleep = sleep
        self._max_interval = float(max_interval)
        self._growth = float(growth)
        # Monotonic deadline anchored at construction.
        self._deadline = clock() + self._max_wait
        self.polls = 0

    def record_poll(self) -> int:
        """Count one completed poll and return the running total."""
        self.polls += 1
        return self.polls

    def remaining(self) -> float:
        """Seconds left before the deadline (clamp to >= 0 for sleep math)."""
        return self._deadline - self._clock()

    def exhausted(self) -> bool:
        """True once the time budget or the poll-count cap is reached."""
        return self.polls >= self._max_polls or self._clock() >= self._deadline

    def sleep_and_backoff(self) -> None:
        """Sleep the current interval (clamped to remaining time), then grow it."""
        self._sleep(min(self._interval, max(0.0, self.remaining())))
        self._interval = min(self._interval * self._growth, self._max_interval)


def drive_poll(
    call_op: Callable[[str, dict], dict],
    poll_op: str,
    params: dict,
    *,
    terminal: Callable[[dict], str | None],
    is_retriable: Callable[[dict], bool],
    on_timeout: Callable[[], None] | None = None,
    interval: float = 1.0,
    max_wait: float = 300.0,
    max_polls: int = 10_000,
    max_transient: int = 5,
    clock: Callable[[], float] | None = None,
    sleep: Callable[[float], None] | None = None,
    key: str = "",
) -> dict:
    """Drive a poll-until-terminal loop with bounded retries.

    Returns a result envelope (from helpers.ok_result/err_result):
    - On terminal status: the last successful result from call_op
    - On timeout: err_result with code 'TIMEOUT' and retriable=True
    - On non-retriable error: the error result from call_op
    - On transient errors exhausted: err_result with the last transient error

    The *terminal* callback receives a successful result dict and returns
    the terminal status string if polling should stop, or None to continue.

    The *is_retriable* callback receives a failed result dict and returns
    True if the error is transient (will be counted against max_transient).

    The returned envelope carries ``polls_count`` (the number of polls made)
    so callers can surface it in their own diagnostics.
    """
    # Late import keeps the dependency one-way (helpers never imports poll) and
    # avoids any import-time cycle.
    from awscli.customizations.compositereadonly.helpers import (
        TIMEOUT,
        err_result,
    )

    sleep = time.sleep if sleep is None else sleep
    clock = time.monotonic if clock is None else clock

    poller = BoundedPoller(
        interval=interval,
        max_wait=max_wait,
        max_polls=max_polls,
        clock=clock,
        sleep=sleep,
        max_interval=MAX_POLL_INTERVAL,
    )
    transient = 0
    while True:
        res = call_op(poll_op, params)
        poller.record_poll()
        if res["ok"]:
            # Terminal callback decides whether this successful poll ends it.
            if terminal(res) is not None:
                res["polls_count"] = poller.polls
                return res
        elif is_retriable(res):
            # Count transient errors; abort with the last one once exhausted.
            if transient >= max_transient:
                res["polls_count"] = poller.polls
                return res
            transient += 1
        else:
            # Non-retriable error: hand the caller the raw failure result.
            res["polls_count"] = poller.polls
            return res
        if poller.exhausted():
            # Let the caller cancel the lifecycle (e.g. StopQuery) before we
            # report the timeout.
            if on_timeout is not None:
                on_timeout()
            timed_out = err_result(
                TIMEOUT,
                f"Polling {poll_op} did not reach a terminal state within "
                f"{max_wait:g}s after {poller.polls} polls.",
                retriable=True,
                key=key or None,
                value={"polls": poller.polls},
            )
            timed_out["polls_count"] = poller.polls
            return timed_out
        poller.sleep_and_backoff()
