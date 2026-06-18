# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
# language governing permissions and limitations under thimport mock
import contextlib
import copy
import json
import logging
import os
import socket
import threading

import pytest

import botocore.config
import botocore.exceptions
import botocore.session
from botocore import xform_name
from tests import ClientHTTPStubber, mock, temporary_file

logger = logging.getLogger(__name__)

CASES_FILE = os.path.join(os.path.dirname(__file__), 'cases.json')
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data/')


class RetryableException(botocore.exceptions.EndpointConnectionError):
    fmt = '{message}'


class NonRetryableException(Exception):
    pass


EXPECTED_EXCEPTIONS_THROWN = (
    botocore.exceptions.ClientError,
    NonRetryableException,
    RetryableException,
)


def _load_test_cases():
    with open(CASES_FILE) as f:
        loaded_tests = json.loads(f.read())
    test_cases = _get_cases_with_defaults(loaded_tests)
    _replace_expected_anys(test_cases)
    return test_cases


def _get_cases_with_defaults(loaded_tests):
    cases = []
    defaults = loaded_tests['defaults']
    for case in loaded_tests['cases']:
        base = copy.deepcopy(defaults)
        base.update(case)
        cases.append(base)
    return cases


def _replace_expected_anys(test_cases):
    for case in test_cases:
        for expected_event in case['expectedMonitoringEvents']:
            for entry, value in expected_event.items():
                if value in ['ANY_STR', 'ANY_INT']:
                    expected_event[entry] = mock.ANY


@pytest.mark.parametrize("test_case", _load_test_cases())
def test_client_monitoring(test_case):
    _run_test_case(test_case)


@contextlib.contextmanager
def _configured_session(case_configuration, listener_port):
    environ = {
        'AWS_ACCESS_KEY_ID': case_configuration['accessKey'],
        'AWS_SECRET_ACCESS_KEY': 'secret-key',
        'AWS_DEFAULT_REGION': case_configuration['region'],
        'AWS_DATA_PATH': DATA_DIR,
        'AWS_CSM_PORT': listener_port,
    }
    if 'sessionToken' in case_configuration:
        environ['AWS_SESSION_TOKEN'] = case_configuration['sessionToken']
    environ.update(case_configuration['environmentVariables'])
    with temporary_file('w') as f:
        _setup_shared_config(
            f, case_configuration['sharedConfigFile'], environ
        )
        with mock.patch('os.environ', environ):
            session = botocore.session.Session()
            if 'maxRetries' in case_configuration:
                _setup_max_retry_attempts(session, case_configuration)
            yield session


def _setup_shared_config(fileobj, shared_config_options, environ):
    fileobj.write('[default]\n')
    for key, value in shared_config_options.items():
        fileobj.write(f'{key} = {value}\n')
    fileobj.flush()
    environ['AWS_CONFIG_FILE'] = fileobj.name


def _setup_max_retry_attempts(session, case_configuration):
    config = botocore.config.Config(
        retries={'max_attempts': case_configuration['maxRetries']}
    )
    session.set_default_client_config(config)


def _run_test_case(case):
    with MonitoringListener() as listener:
        with _configured_session(
            case['configuration'], listener.port
        ) as session:
            for api_call in case['apiCalls']:
                _make_api_call(session, api_call)
    assert listener.received_events == case['expectedMonitoringEvents']


def _make_api_call(session, api_call):
    client = session.create_client(
        api_call['serviceId'].lower().replace(' ', '')
    )
    operation_name = api_call['operationName']
    client_method = getattr(client, xform_name(operation_name))
    with _stubbed_http_layer(client, api_call['attemptResponses']):
        try:
            client_method(**api_call['params'])
        except EXPECTED_EXCEPTIONS_THROWN:
            pass


@contextlib.contextmanager
def _stubbed_http_layer(client, attempt_responses):
    with ClientHTTPStubber(client) as stubber:
        _add_stubbed_responses(stubber, attempt_responses)
        yield


def _add_stubbed_responses(stubber, attempt_responses):
    for attempt_response in attempt_responses:
        if 'sdkException' in attempt_response:
            sdk_exception = attempt_response['sdkException']
            _add_sdk_exception(
                stubber, sdk_exception['message'], sdk_exception['isRetryable']
            )
        else:
            _add_stubbed_response(stubber, attempt_response)


def _add_sdk_exception(stubber, message, is_retryable):
    if is_retryable:
        stubber.responses.append(RetryableException(message=message))
    else:
        stubber.responses.append(NonRetryableException(message))


def _add_stubbed_response(stubber, attempt_response):
    headers = attempt_response['responseHeaders']
    status_code = attempt_response['httpStatus']
    if 'errorCode' in attempt_response:
        error = {
            '__type': attempt_response['errorCode'],
            'message': attempt_response['errorMessage'],
        }
        content = json.dumps(error).encode('utf-8')
    else:
        content = b'{}'
    stubber.add_response(status=status_code, headers=headers, body=content)


class MonitoringListener(threading.Thread):
    _PACKET_SIZE = 1024 * 8

    def __init__(self, port=0):
        threading.Thread.__init__(self)
        self._socket = None
        self.port = port
        self.received_events = []

    def __enter__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind(('127.0.0.1', self.port))
        # The socket may have been assigned to an unused port so we
        # reset the port member after binding.
        self.port = self._socket.getsockname()[1]
        self.start()
        return self

    def __exit__(self, *args):
        self._socket.sendto(b'', ('127.0.0.1', self.port))
        self.join()
        self._socket.close()

    def run(self):
        logger.debug('Started listener')
        while True:
            data = self._socket.recv(self._PACKET_SIZE)
            logger.debug('Received: %s', data.decode('utf-8'))
            if not data:
                return
            self.received_events.append(json.loads(data.decode('utf-8')))
