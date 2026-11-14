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
"""Unit tests for the shared BoundedPoller (deterministic, injected clock)."""

from awscli.customizations.compositereadonly.poll import (
    MAX_POLL_INTERVAL,
    BoundedPoller,
)


class FakeClock:
    """A manually advanced monotonic clock."""

    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def _poller(clock, sleeps, **kwargs):
    kwargs.setdefault("interval", 1.0)
    kwargs.setdefault("max_wait", 10.0)
    kwargs.setdefault("max_polls", 100)
    return BoundedPoller(
        clock=clock, sleep=lambda s: sleeps.append(s), **kwargs
    )


def test_record_poll_counts_up():
    clock = FakeClock()
    poller = _poller(clock, [])
    assert poller.record_poll() == 1
    assert poller.record_poll() == 2
    assert poller.polls == 2


def test_exhausted_on_poll_count_cap():
    clock = FakeClock()
    poller = _poller(clock, [], max_polls=2)
    poller.record_poll()
    assert poller.exhausted() is False
    poller.record_poll()
    # The poll-count cap is reached even though no wall time elapsed.
    assert poller.exhausted() is True


def test_exhausted_on_deadline():
    clock = FakeClock()
    poller = _poller(clock, [], max_wait=5.0)
    assert poller.exhausted() is False
    clock.advance(5.0)
    # Deadline reached -> exhausted regardless of poll count.
    assert poller.exhausted() is True


def test_remaining_decreases_with_clock():
    clock = FakeClock()
    poller = _poller(clock, [], max_wait=10.0)
    assert poller.remaining() == 10.0
    clock.advance(3.0)
    assert poller.remaining() == 7.0


def test_backoff_grows_geometrically_and_caps():
    clock = FakeClock()
    sleeps = []
    poller = _poller(
        clock,
        sleeps,
        interval=1.0,
        max_wait=1000.0,
        growth=2.0,
        max_interval=MAX_POLL_INTERVAL,
    )
    for _ in range(6):
        poller.sleep_and_backoff()
    # 1, 2, 4, then capped at MAX_POLL_INTERVAL (5.0).
    assert sleeps[0] == 1.0
    assert sleeps[1] == 2.0
    assert sleeps[2] == 4.0
    assert all(s <= MAX_POLL_INTERVAL for s in sleeps)
    assert sleeps[-1] == MAX_POLL_INTERVAL


def test_sleep_is_clamped_to_remaining_time():
    clock = FakeClock()
    sleeps = []
    # interval (10s) exceeds the remaining budget (3s); sleep is clamped so the
    # poller never sleeps past its own deadline.
    poller = _poller(clock, sleeps, interval=10.0, max_wait=3.0)
    poller.sleep_and_backoff()
    assert sleeps[0] == 3.0


def test_sleep_never_negative_past_deadline():
    clock = FakeClock()
    sleeps = []
    poller = _poller(clock, sleeps, interval=10.0, max_wait=5.0)
    clock.advance(8.0)  # already past the deadline
    poller.sleep_and_backoff()
    # remaining() would be negative; the clamp floors the sleep at 0.
    assert sleeps[0] == 0.0
