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
import io
from unittest import mock

import botocore.session
import pytest
from botocore.stub import Stubber

from awscli.customizations.lambdaweb import wait
from awscli.customizations.lambdaweb.exceptions import (
    ActivationFailedError,
    ActivationTimeoutError,
)

REGION = 'us-east-1'
FUNCTION_NAME = 'my-fn'
ENDPOINT_NAME = 'my-endpoint'
REVISION_ID = 'rev-001'

_TIMESTAMP = '2026-01-01T00:00:00Z'


def _endpoint_response(
    state,
    state_reason='ok',
    update_status=None,
    update_status_reason='ok',
):
    response = {
        'functionArn': f'arn:aws:lambda:{REGION}:111111111111:function:{FUNCTION_NAME}',
        'endpointArn': f'arn:aws:lambda:{REGION}:111111111111:endpoint:{ENDPOINT_NAME}',
        'endpointName': ENDPOINT_NAME,
        'endpointType': 'HomeRegion',
        'domainName': 'abc.lambda-url.us-east-1.on.aws',
        'authType': 'ApplicationManaged',
        'autoDeploymentMode': 'LatestRevision',
        'revisionWeights': [{'revisionId': REVISION_ID, 'weight': 100}],
        'regions': [REGION],
        'state': state,
        'stateReason': state_reason,
        'regionalEndpoints': {},
        'createdAt': _TIMESTAMP,
        'updatedAt': _TIMESTAMP,
    }
    if update_status is not None:
        response['updateStatus'] = update_status
        response['updateStatusReason'] = update_status_reason
    return response


@pytest.fixture
def client():
    return botocore.session.get_session().create_client(
        'lambda-web',
        region_name=REGION,
    )


@pytest.fixture
def stubber(client):
    with Stubber(client) as stubber:
        yield stubber


def test_wait_returns_on_active(client, stubber):
    expected = _endpoint_response('Active')
    stubber.add_response(
        'get_web_function_endpoint',
        expected,
        expected_params={
            'functionName': FUNCTION_NAME,
            'endpointName': ENDPOINT_NAME,
        },
    )
    with (
        mock.patch.object(wait.time, 'sleep'),
        mock.patch.object(wait.time, 'monotonic', return_value=0.0),
    ):
        result = wait.wait_for_endpoint_active(
            client,
            FUNCTION_NAME,
            ENDPOINT_NAME,
            timeout_seconds=60,
            poll_interval_seconds=1,
        )
    assert result['state'] == 'Active'
    assert result['endpointName'] == ENDPOINT_NAME
    stubber.assert_no_pending_responses()


def test_wait_raises_activation_failed_on_failed_state(client, stubber):
    stubber.add_response(
        'get_web_function_endpoint',
        _endpoint_response('Failed', state_reason='Image build failed'),
        expected_params={
            'functionName': FUNCTION_NAME,
            'endpointName': ENDPOINT_NAME,
        },
    )
    with (
        mock.patch.object(wait.time, 'sleep'),
        mock.patch.object(wait.time, 'monotonic', return_value=0.0),
    ):
        with pytest.raises(ActivationFailedError) as excinfo:
            wait.wait_for_endpoint_active(
                client,
                FUNCTION_NAME,
                ENDPOINT_NAME,
                timeout_seconds=60,
                poll_interval_seconds=1,
            )
    assert 'Image build failed' in str(excinfo.value)
    assert ENDPOINT_NAME in str(excinfo.value)
    stubber.assert_no_pending_responses()


def test_wait_for_endpoint_updated_uses_update_status(client, stubber):
    stubber.add_response(
        'get_web_function_endpoint',
        _endpoint_response('Active', update_status='InProgress'),
        expected_params={
            'functionName': FUNCTION_NAME,
            'endpointName': ENDPOINT_NAME,
        },
    )
    stubber.add_response(
        'get_web_function_endpoint',
        _endpoint_response('Active', update_status='Successful'),
        expected_params={
            'functionName': FUNCTION_NAME,
            'endpointName': ENDPOINT_NAME,
        },
    )

    with (
        mock.patch.object(wait.time, 'sleep'),
        mock.patch.object(wait.time, 'monotonic', return_value=0.0),
    ):
        result = wait.wait_for_endpoint_updated(
            client,
            FUNCTION_NAME,
            ENDPOINT_NAME,
            timeout_seconds=60,
            poll_interval_seconds=1,
        )

    assert result['updateStatus'] == 'Successful'
    stubber.assert_no_pending_responses()


def test_wait_for_endpoint_updated_raises_on_failed_update(client, stubber):
    stubber.add_response(
        'get_web_function_endpoint',
        _endpoint_response(
            'Active',
            update_status='Failed',
            update_status_reason='Regional rollout failed',
        ),
        expected_params={
            'functionName': FUNCTION_NAME,
            'endpointName': ENDPOINT_NAME,
        },
    )

    with (
        mock.patch.object(wait.time, 'sleep'),
        mock.patch.object(wait.time, 'monotonic', return_value=0.0),
        pytest.raises(ActivationFailedError) as excinfo,
    ):
        wait.wait_for_endpoint_updated(
            client,
            FUNCTION_NAME,
            ENDPOINT_NAME,
            timeout_seconds=60,
            poll_interval_seconds=1,
        )

    assert 'Regional rollout failed' in str(excinfo.value)
    stubber.assert_no_pending_responses()


def test_wait_raises_timeout_with_resume_command(client, stubber):
    # Initial monotonic call sets deadline = 0 + 5 = 5; the loop check then
    # observes 1000 >= 5 and raises before any client call is made.
    monotonic_values = iter([0.0, 1000.0])
    with (
        mock.patch.object(wait.time, 'sleep'),
        mock.patch.object(
            wait.time, 'monotonic', side_effect=lambda: next(monotonic_values)
        ),
    ):
        with pytest.raises(ActivationTimeoutError) as excinfo:
            wait.wait_for_endpoint_active(
                client,
                FUNCTION_NAME,
                ENDPOINT_NAME,
                timeout_seconds=5,
                poll_interval_seconds=1,
            )
    message = str(excinfo.value)
    assert 'aws lambda-web get-web-function-endpoint' in message
    assert f'--function-name {FUNCTION_NAME}' in message
    assert f'--endpoint-name {ENDPOINT_NAME}' in message
    assert '5 seconds' in message


def test_wait_throttling_triggers_exponential_backoff(client, stubber):
    for _ in range(4):
        stubber.add_client_error(
            'get_web_function_endpoint',
            service_error_code='ThrottlingException',
            service_message='Rate exceeded',
            http_status_code=429,
        )
    stubber.add_response(
        'get_web_function_endpoint',
        _endpoint_response('Active'),
        expected_params={
            'functionName': FUNCTION_NAME,
            'endpointName': ENDPOINT_NAME,
        },
    )
    with (
        mock.patch.object(wait.time, 'sleep') as sleep_mock,
        mock.patch.object(wait.time, 'monotonic', return_value=0.0),
    ):
        result = wait.wait_for_endpoint_active(
            client,
            FUNCTION_NAME,
            ENDPOINT_NAME,
            timeout_seconds=10_000,
            poll_interval_seconds=999,  # never used; Active short-circuits.
        )
    assert result['state'] == 'Active'
    backoffs = [call.args[0] for call in sleep_mock.call_args_list]
    # First four sleeps are throttle backoffs: 2, 4, 8, 16.
    assert backoffs[:4] == [2, 4, 8, 16]
    # Strictly increasing while below the cap.
    capped_below = [b for b in backoffs[:4] if b < 60]
    assert all(a < b for a, b in zip(capped_below, capped_below[1:])), backoffs
    stubber.assert_no_pending_responses()


@pytest.mark.parametrize(
    'error_code',
    (
        'TooManyRequestsException',
        'Throttling',
        'ThrottledException',
        'RequestThrottled',
    ),
)
def test_wait_retries_common_throttle_codes(client, stubber, error_code):
    stubber.add_client_error(
        'get_web_function_endpoint',
        service_error_code=error_code,
        service_message='Rate exceeded',
        http_status_code=429,
    )
    stubber.add_response(
        'get_web_function_endpoint',
        _endpoint_response('Active'),
        expected_params={
            'functionName': FUNCTION_NAME,
            'endpointName': ENDPOINT_NAME,
        },
    )

    with (
        mock.patch.object(wait.time, 'sleep') as sleep_mock,
        mock.patch.object(wait.time, 'monotonic', return_value=0.0),
    ):
        result = wait.wait_for_endpoint_active(
            client,
            FUNCTION_NAME,
            ENDPOINT_NAME,
            timeout_seconds=60,
            poll_interval_seconds=7,
        )

    assert result['state'] == 'Active'
    sleep_mock.assert_called_once_with(2)
    stubber.assert_no_pending_responses()


def test_wait_throttling_caps_at_60(client, stubber):
    # attempt=6 -> min(60, 64) = 60. Verify the cap holds.
    for _ in range(6):
        stubber.add_client_error(
            'get_web_function_endpoint',
            service_error_code='ThrottlingException',
            service_message='Rate exceeded',
            http_status_code=429,
        )
    stubber.add_response(
        'get_web_function_endpoint',
        _endpoint_response('Active'),
        expected_params={
            'functionName': FUNCTION_NAME,
            'endpointName': ENDPOINT_NAME,
        },
    )
    with (
        mock.patch.object(wait.time, 'sleep') as sleep_mock,
        mock.patch.object(wait.time, 'monotonic', return_value=0.0),
    ):
        wait.wait_for_endpoint_active(
            client,
            FUNCTION_NAME,
            ENDPOINT_NAME,
            timeout_seconds=10_000,
            poll_interval_seconds=999,
        )
    backoffs = [call.args[0] for call in sleep_mock.call_args_list]
    assert backoffs[:6] == [2, 4, 8, 16, 32, 60]


def test_wait_throttling_backoff_resets_after_successful_fetch(
    client, stubber
):
    stubber.add_client_error(
        'get_web_function_endpoint',
        service_error_code='ThrottlingException',
        service_message='Rate exceeded',
        http_status_code=429,
    )
    stubber.add_response(
        'get_web_function_endpoint',
        _endpoint_response('Pending'),
        expected_params={
            'functionName': FUNCTION_NAME,
            'endpointName': ENDPOINT_NAME,
        },
    )
    stubber.add_client_error(
        'get_web_function_endpoint',
        service_error_code='ThrottlingException',
        service_message='Rate exceeded',
        http_status_code=429,
    )
    stubber.add_response(
        'get_web_function_endpoint',
        _endpoint_response('Active'),
        expected_params={
            'functionName': FUNCTION_NAME,
            'endpointName': ENDPOINT_NAME,
        },
    )

    with (
        mock.patch.object(wait.time, 'sleep') as sleep_mock,
        mock.patch.object(wait.time, 'monotonic', return_value=0.0),
    ):
        wait.wait_for_endpoint_active(
            client,
            FUNCTION_NAME,
            ENDPOINT_NAME,
            timeout_seconds=10_000,
            poll_interval_seconds=7,
        )

    assert [call.args[0] for call in sleep_mock.call_args_list] == [2, 7, 2]


def test_wait_throttling_backoff_does_not_exceed_timeout(client, stubber):
    for _ in range(2):
        stubber.add_client_error(
            'get_web_function_endpoint',
            service_error_code='ThrottlingException',
            service_message='Rate exceeded',
            http_status_code=429,
        )

    now = [0.0]
    sleeps = []

    def advance(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    with (
        mock.patch.object(wait.time, 'sleep', side_effect=advance),
        mock.patch.object(wait.time, 'monotonic', side_effect=lambda: now[0]),
        pytest.raises(ActivationTimeoutError),
    ):
        wait.wait_for_endpoint_active(
            client,
            FUNCTION_NAME,
            ENDPOINT_NAME,
            timeout_seconds=3,
            poll_interval_seconds=7,
        )

    assert sleeps == [2, 1]
    stubber.assert_no_pending_responses()


def test_wait_non_throttling_client_error_propagates(client, stubber):
    stubber.add_client_error(
        'get_web_function_endpoint',
        service_error_code='ResourceNotFoundException',
        service_message='not found',
        http_status_code=404,
    )
    with (
        mock.patch.object(wait.time, 'sleep'),
        mock.patch.object(wait.time, 'monotonic', return_value=0.0),
    ):
        with pytest.raises(Exception) as excinfo:
            wait.wait_for_endpoint_active(
                client,
                FUNCTION_NAME,
                ENDPOINT_NAME,
                timeout_seconds=60,
                poll_interval_seconds=1,
            )
    assert 'ResourceNotFoundException' in str(excinfo.value)


def test_wait_keyboard_interrupt_prints_resume_to_stderr(
    client, stubber, capsys
):
    stubber.add_response(
        'get_web_function_endpoint',
        _endpoint_response('Pending'),
        expected_params={
            'functionName': FUNCTION_NAME,
            'endpointName': ENDPOINT_NAME,
        },
    )

    def _interrupt(_seconds):
        raise KeyboardInterrupt()

    with (
        mock.patch.object(wait.time, 'sleep', side_effect=_interrupt),
        mock.patch.object(wait.time, 'monotonic', return_value=0.0),
    ):
        with pytest.raises(KeyboardInterrupt):
            wait.wait_for_endpoint_active(
                client,
                FUNCTION_NAME,
                ENDPOINT_NAME,
                timeout_seconds=60,
                poll_interval_seconds=1,
            )

    captured = capsys.readouterr()
    assert captured.out == ''
    assert 'Interrupted. Resume with:' in captured.err
    assert 'aws lambda-web get-web-function-endpoint' in captured.err
    assert f'--function-name {FUNCTION_NAME}' in captured.err
    assert f'--endpoint-name {ENDPOINT_NAME}' in captured.err
    stubber.assert_no_pending_responses()


def test_wait_no_stdout_output(client, stubber, capsys):
    # A few Pending ticks then Active. capsys.out must stay empty.
    for _ in range(2):
        stubber.add_response(
            'get_web_function_endpoint',
            _endpoint_response('Pending'),
            expected_params={
                'functionName': FUNCTION_NAME,
                'endpointName': ENDPOINT_NAME,
            },
        )
    stubber.add_response(
        'get_web_function_endpoint',
        _endpoint_response('Active'),
        expected_params={
            'functionName': FUNCTION_NAME,
            'endpointName': ENDPOINT_NAME,
        },
    )
    with (
        mock.patch.object(wait.time, 'sleep'),
        mock.patch.object(wait.time, 'monotonic', return_value=0.0),
    ):
        wait.wait_for_endpoint_active(
            client,
            FUNCTION_NAME,
            ENDPOINT_NAME,
            timeout_seconds=60,
            poll_interval_seconds=1,
        )
    captured = capsys.readouterr()
    assert captured.out == ''
    stubber.assert_no_pending_responses()


def test_progress_emitter_lines_even_on_tty():
    # Accessible polling: rewritten lines are not announced by screen
    # readers, so a TTY gets the same line-per-update emitter.
    stream = io.StringIO()
    stream.isatty = lambda: True
    emitter = wait._make_progress_emitter(stream)
    assert isinstance(emitter, wait.LineLogger)


def test_progress_emitter_lines_when_not_tty():
    stream = io.StringIO()
    stream.isatty = lambda: False
    emitter = wait._make_progress_emitter(stream)
    assert isinstance(emitter, wait.LineLogger)


def test_line_logger_never_rewrites_output():
    stream = io.StringIO()
    stream.isatty = lambda: True
    logger = wait.LineLogger(stream)
    logger.start()
    logger.tick('Pending', 12, 600)
    logger.stop()
    output = stream.getvalue()
    assert 'Pending' in output
    assert '12s elapsed' in output
    assert 'timeout 600s' in output
    assert '\r' not in output
    assert '\x1b' not in output


def test_line_logger_frequency_rate_limits_lines():
    stream = io.StringIO()
    stream.isatty = lambda: False
    logger = wait.LineLogger(stream, 'endpoint', frequency_seconds=30)
    for elapsed in (0, 5, 10, 30, 35, 60):
        logger.tick('Pending', elapsed, 600)
    lines = stream.getvalue().splitlines()
    assert len(lines) == 3
    assert '0s elapsed' in lines[0]
    assert '30s elapsed' in lines[1]
    assert '60s elapsed' in lines[2]


def test_line_logger_no_frequency_writes_every_tick():
    stream = io.StringIO()
    stream.isatty = lambda: False
    logger = wait.LineLogger(stream, 'endpoint')
    for elapsed in (0, 5, 10):
        logger.tick('Pending', elapsed, 600)
    assert len(stream.getvalue().splitlines()) == 3


def test_line_logger_tick_writes_one_line_per_tick():
    stream = io.StringIO()
    stream.isatty = lambda: False
    logger = wait.LineLogger(stream, 'endpoint')
    logger.start()
    logger.tick('Pending', 30, 600)
    logger.stop()
    assert stream.getvalue() == (
        'Waiting for endpoint to become active '
        '(state Pending, 30s elapsed, timeout 600s) ...\n'
    )


def test_line_logger_uses_resource_label():
    stream = io.StringIO()
    stream.isatty = lambda: False
    logger = wait.LineLogger(stream, 'endpoint')
    logger.tick('Pending', 5, 600)
    assert 'Waiting for endpoint to become active' in stream.getvalue()


def test_line_logger_default_label_is_generic():
    stream = io.StringIO()
    stream.isatty = lambda: False
    logger = wait.LineLogger(stream)
    logger.tick('Pending', 1, 600)
    assert 'Waiting for resource to become active' in stream.getvalue()


def test_wait_passes_progress_frequency_to_emitter(client, stubber):
    stubber.add_response(
        'get_web_function_endpoint',
        _endpoint_response('Pending'),
        expected_params={
            'functionName': FUNCTION_NAME,
            'endpointName': ENDPOINT_NAME,
        },
    )
    stubber.add_response(
        'get_web_function_endpoint',
        _endpoint_response('Active'),
        expected_params={
            'functionName': FUNCTION_NAME,
            'endpointName': ENDPOINT_NAME,
        },
    )
    with (
        mock.patch.object(wait.time, 'sleep'),
        mock.patch.object(wait.time, 'monotonic', return_value=0.0),
        mock.patch.object(
            wait, '_make_progress_emitter', wraps=wait._make_progress_emitter
        ) as make_emitter,
    ):
        wait.wait_for_endpoint_active(
            client,
            FUNCTION_NAME,
            ENDPOINT_NAME,
            timeout_seconds=60,
            poll_interval_seconds=1,
            progress_frequency_seconds=45,
        )
    assert make_emitter.call_args.args[-1] == 45
    stubber.assert_no_pending_responses()


def test_progress_frequency_can_be_shorter_than_poll_interval(client, stubber):
    stubber.add_response(
        'get_web_function_endpoint',
        _endpoint_response('Pending'),
        expected_params={
            'functionName': FUNCTION_NAME,
            'endpointName': ENDPOINT_NAME,
        },
    )
    stubber.add_response(
        'get_web_function_endpoint',
        _endpoint_response('Active'),
        expected_params={
            'functionName': FUNCTION_NAME,
            'endpointName': ENDPOINT_NAME,
        },
    )
    now = [0.0]
    sleeps = []

    def advance(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    stderr = io.StringIO()
    with (
        mock.patch.object(wait.time, 'sleep', side_effect=advance),
        mock.patch.object(wait.time, 'monotonic', side_effect=lambda: now[0]),
    ):
        wait.wait_for_endpoint_active(
            client,
            FUNCTION_NAME,
            ENDPOINT_NAME,
            timeout_seconds=60,
            poll_interval_seconds=5,
            progress_frequency_seconds=1,
            stderr=stderr,
        )

    lines = stderr.getvalue().splitlines()
    assert sleeps == [1, 1, 1, 1, 1]
    assert len(lines) == 5
    assert '0s elapsed' in lines[0]
    assert '4s elapsed' in lines[-1]
    stubber.assert_no_pending_responses()


def _revision_response(state, state_reason='ok'):
    return {
        'functionArn': f'arn:aws:lambda:{REGION}:111111111111:function:{FUNCTION_NAME}',
        'revisionArn': f'arn:aws:lambda:{REGION}:111111111111:revision:{REVISION_ID}',
        'revisionId': REVISION_ID,
        'buildConfig': {
            'codeConfig': {
                's3Object': {'bucket': 'test-bucket', 'key': 'test-key'},
            },
            'runtimeConfig': {'runtime': 'nodejs24.x'},
        },
        'serviceConfig': {
            'executionRoleArn': (
                f'arn:aws:iam::111111111111:role/awscli-lambdaweb-{FUNCTION_NAME}'
            ),
        },
        'state': state,
        'stateReason': state_reason,
        'createdAt': _TIMESTAMP,
    }


def test_wait_for_revision_active_polls_get_web_function_revision(
    client, stubber
):
    expected = _revision_response('Active')
    stubber.add_response(
        'get_web_function_revision',
        expected,
        expected_params={
            'functionName': FUNCTION_NAME,
            'revisionId': REVISION_ID,
        },
    )
    with (
        mock.patch.object(wait.time, 'sleep'),
        mock.patch.object(wait.time, 'monotonic', return_value=0.0),
    ):
        result = wait.wait_for_revision_active(
            client,
            FUNCTION_NAME,
            REVISION_ID,
            timeout_seconds=60,
            poll_interval_seconds=1,
        )
    assert result['state'] == 'Active'
    assert result['revisionId'] == REVISION_ID
    stubber.assert_no_pending_responses()


def test_wait_for_revision_progress_line_says_revision(client, stubber):
    stubber.add_response(
        'get_web_function_revision',
        _revision_response('Pending'),
        expected_params={
            'functionName': FUNCTION_NAME,
            'revisionId': REVISION_ID,
        },
    )
    stubber.add_response(
        'get_web_function_revision',
        _revision_response('Active'),
        expected_params={
            'functionName': FUNCTION_NAME,
            'revisionId': REVISION_ID,
        },
    )
    stderr = io.StringIO()
    stderr.isatty = lambda: False
    with (
        mock.patch.object(wait.time, 'sleep'),
        mock.patch.object(wait.time, 'monotonic', return_value=0.0),
    ):
        wait.wait_for_revision_active(
            client,
            FUNCTION_NAME,
            REVISION_ID,
            timeout_seconds=60,
            poll_interval_seconds=1,
            stderr=stderr,
        )
    out = stderr.getvalue()
    assert 'Waiting for revision to become active' in out
    assert 'Waiting for endpoint to become active' not in out
    stubber.assert_no_pending_responses()


def test_wait_for_revision_timeout_resume_command_uses_revision_id(
    client, stubber
):
    monotonic_values = iter([0.0, 1000.0])
    with (
        mock.patch.object(wait.time, 'sleep'),
        mock.patch.object(
            wait.time, 'monotonic', side_effect=lambda: next(monotonic_values)
        ),
    ):
        with pytest.raises(ActivationTimeoutError) as excinfo:
            wait.wait_for_revision_active(
                client,
                FUNCTION_NAME,
                REVISION_ID,
                timeout_seconds=5,
                poll_interval_seconds=1,
            )
    message = str(excinfo.value)
    assert 'aws lambda-web get-web-function-revision' in message
    assert f'--revision-id {REVISION_ID}' in message
