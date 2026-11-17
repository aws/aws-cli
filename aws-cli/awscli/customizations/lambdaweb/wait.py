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
import sys
import time

from botocore.exceptions import ClientError

from awscli.customizations.lambdaweb import constants
from awscli.customizations.lambdaweb.exceptions import (
    ActivationFailedError,
    ActivationTimeoutError,
)

_THROTTLE_CODES = (
    'ThrottlingException',
    'TooManyRequestsException',
    'Throttling',
    'ThrottledException',
    'RequestThrottled',
)


def _fmt_progress(elapsed, timeout):
    """Return a human-readable progress fragment like ``'12s elapsed, timeout 600s'``."""
    return f'{int(elapsed)}s elapsed, timeout {int(timeout)}s'


class _ProgressEmitter:
    """Base for progress emitters used by the polling loop."""

    def start(self):
        pass

    def tick(self, state, elapsed, timeout):
        pass

    def seconds_until_next_tick(self, elapsed):
        return None

    def stop(self):
        pass


class LineLogger(_ProgressEmitter):
    """Appends one line per update; never rewrites in place.

    Rewritten lines are not announced by screen readers, so accessible
    polling appends discrete lines. ``frequency_seconds`` rate-limits the
    lines without slowing the underlying polling.
    """

    def __init__(
        self,
        stderr,
        resource_label='resource',
        frequency_seconds=None,
        *,
        action='become active',
        status_label='state',
    ):
        self._stderr = stderr
        self._resource_label = resource_label
        self._frequency = frequency_seconds
        self._action = action
        self._status_label = status_label
        self._last_emit_elapsed = None

    def tick(self, state, elapsed, timeout):
        if (
            self._frequency is not None
            and self._last_emit_elapsed is not None
            and elapsed - self._last_emit_elapsed < self._frequency
        ):
            return
        self._last_emit_elapsed = elapsed
        self._stderr.write(
            f'Waiting for {self._resource_label} to {self._action} '
            f'({self._status_label} {state}, '
            f'{_fmt_progress(elapsed, timeout)}) ...\n'
        )
        self._stderr.flush()

    def seconds_until_next_tick(self, elapsed):
        if self._frequency is None or self._last_emit_elapsed is None:
            return None
        since_last = elapsed - self._last_emit_elapsed
        return max(0, self._frequency - since_last)


def _make_progress_emitter(
    stderr,
    resource_label='resource',
    frequency_seconds=None,
    *,
    action='become active',
    status_label='state',
):
    """Return the line-based progress emitter (line-based even on a TTY)."""
    return LineLogger(
        stderr,
        resource_label,
        frequency_seconds,
        action=action,
        status_label=status_label,
    )


def _resume_command(operation, function_name, key_flag, key_value):
    return (
        f'aws lambda-web {operation} --function-name {function_name} '
        f'{key_flag} {key_value}'
    )


def _sleep_until_next_poll(
    emitter,
    status,
    elapsed,
    timeout_seconds,
    poll_interval_seconds,
):
    """Sleep between API polls while emitting scheduled progress messages."""
    remaining = poll_interval_seconds
    current_elapsed = elapsed
    while remaining > 0:
        next_tick = emitter.seconds_until_next_tick(current_elapsed)
        if next_tick is None or next_tick <= 0 or next_tick >= remaining:
            time.sleep(remaining)
            return
        time.sleep(next_tick)
        current_elapsed += next_tick
        remaining -= next_tick
        emitter.tick(status, current_elapsed, timeout_seconds)


def _poll_until(
    *,
    fetch,
    timeout_seconds,
    poll_interval_seconds,
    stderr,
    timeout_message,
    failed_label,
    interrupt_resume,
    resource_label='resource',
    progress_frequency_seconds=None,
    status_key='state',
    success_status='Active',
    failure_status='Failed',
    failure_reason_key='stateReason',
    progress_action='become active',
    progress_status_label='state',
):
    """Drive the polling loop. ``fetch`` returns the response dict."""
    start = time.monotonic()
    deadline = start + timeout_seconds
    throttle_attempt = 1
    emitter = _make_progress_emitter(
        stderr,
        resource_label,
        progress_frequency_seconds,
        action=progress_action,
        status_label=progress_status_label,
    )
    emitter.start()
    try:
        while True:
            if time.monotonic() >= deadline:
                raise ActivationTimeoutError(timeout_message)
            try:
                response = fetch()
            except ClientError as exc:
                code = exc.response.get('Error', {}).get('Code')
                if code in _THROTTLE_CODES:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ActivationTimeoutError(timeout_message)
                    backoff = min(
                        constants.THROTTLE_BACKOFF_CAP_SECONDS,
                        2**throttle_attempt,
                        remaining,
                    )
                    time.sleep(backoff)
                    throttle_attempt += 1
                    continue
                raise
            throttle_attempt = 1
            status = response.get(status_key)
            if status == success_status:
                return response
            if status == failure_status:
                reason = response.get(failure_reason_key, 'unknown')
                raise ActivationFailedError(f"{failed_label} failed: {reason}")
            elapsed = time.monotonic() - start
            emitter.tick(status, elapsed, timeout_seconds)
            _sleep_until_next_poll(
                emitter,
                status,
                elapsed,
                timeout_seconds,
                poll_interval_seconds,
            )
    except KeyboardInterrupt:
        stderr.write(f'Interrupted. Resume with: {interrupt_resume}\n')
        stderr.flush()
        raise
    finally:
        emitter.stop()


def wait_for_endpoint_active(
    client,
    function_name,
    endpoint_name,
    *,
    timeout_seconds,
    poll_interval_seconds,
    stderr=None,
    progress_frequency_seconds=None,
):
    """Poll ``GetWebFunctionEndpoint`` until the endpoint is ``Active``."""
    if stderr is None:
        stderr = sys.stderr
    resume = _resume_command(
        'get-web-function-endpoint',
        function_name,
        '--endpoint-name',
        endpoint_name,
    )
    timeout_message = (
        f"Endpoint '{endpoint_name}' for function '{function_name}' did "
        f"not become active within {timeout_seconds} seconds. "
        f"Resume with: {resume}"
    )

    def fetch():
        return client.get_web_function_endpoint(
            functionName=function_name, endpointName=endpoint_name
        )

    return _poll_until(
        fetch=fetch,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        stderr=stderr,
        timeout_message=timeout_message,
        failed_label=f"Endpoint '{endpoint_name}'",
        interrupt_resume=resume,
        resource_label='endpoint',
        progress_frequency_seconds=progress_frequency_seconds,
    )


def wait_for_endpoint_updated(
    client,
    function_name,
    endpoint_name,
    *,
    timeout_seconds,
    poll_interval_seconds,
    stderr=None,
    progress_frequency_seconds=None,
):
    """Poll until the endpoint's most recent update is ``Successful``."""
    if stderr is None:
        stderr = sys.stderr
    resume = _resume_command(
        'get-web-function-endpoint',
        function_name,
        '--endpoint-name',
        endpoint_name,
    )
    timeout_message = (
        f"Endpoint '{endpoint_name}' for function '{function_name}' did "
        f"not finish updating within {timeout_seconds} seconds. "
        f"Resume with: {resume}"
    )

    def fetch():
        return client.get_web_function_endpoint(
            functionName=function_name, endpointName=endpoint_name
        )

    return _poll_until(
        fetch=fetch,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        stderr=stderr,
        timeout_message=timeout_message,
        failed_label=f"Endpoint '{endpoint_name}' update",
        interrupt_resume=resume,
        resource_label='endpoint update',
        progress_frequency_seconds=progress_frequency_seconds,
        status_key='updateStatus',
        success_status='Successful',
        failure_status='Failed',
        failure_reason_key='updateStatusReason',
        progress_action='complete',
        progress_status_label='status',
    )


def wait_for_revision_active(
    client,
    function_name,
    revision_id,
    *,
    timeout_seconds,
    poll_interval_seconds,
    stderr=None,
    progress_frequency_seconds=None,
):
    """Poll ``GetWebFunctionRevision`` until the revision is ``Active``."""
    if stderr is None:
        stderr = sys.stderr
    resume = _resume_command(
        'get-web-function-revision',
        function_name,
        '--revision-id',
        revision_id,
    )
    timeout_message = (
        f"Revision '{revision_id}' for function '{function_name}' did "
        f"not become active within {timeout_seconds} seconds. "
        f"Resume with: {resume}"
    )

    def fetch():
        return client.get_web_function_revision(
            functionName=function_name, revisionId=revision_id
        )

    return _poll_until(
        fetch=fetch,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        stderr=stderr,
        timeout_message=timeout_message,
        failed_label=f"Revision '{revision_id}'",
        interrupt_resume=resume,
        resource_label='revision',
        progress_frequency_seconds=progress_frequency_seconds,
    )
