#!/usr/bin/env
# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import pickle
from tests import unittest

import botocore.awsrequest
import botocore.session
from botocore import exceptions


def test_client_error_can_handle_missing_code_or_message():
    response = {'Error': {}}
    expect = 'An error occurred (Unknown) when calling the blackhole operation: Unknown'
    assert str(exceptions.ClientError(response, 'blackhole')) == expect


def test_client_error_has_operation_name_set():
    response = {'Error': {}}
    exception = exceptions.ClientError(response, 'blackhole')
    assert hasattr(exception, 'operation_name')


def test_client_error_set_correct_operation_name():
    response = {'Error': {}}
    exception = exceptions.ClientError(response, 'blackhole')
    assert exception.operation_name == 'blackhole'


def test_retry_info_added_when_present():
    response = {
        'Error': {},
        'ResponseMetadata': {
            'MaxAttemptsReached': True,
            'RetryAttempts': 3,
        }
    }
    error_msg = str(exceptions.ClientError(response, 'operation'))
    if '(reached max retries: 3)' not in error_msg:
        raise AssertionError("retry information not inject into error "
                             "message: %s" % error_msg)


def test_retry_info_not_added_if_retry_attempts_not_present():
    response = {
        'Error': {},
        'ResponseMetadata': {
            'MaxAttemptsReached': True,
        }
    }
    # Because RetryAttempts is missing, retry info is not
    # in the error message.
    error_msg = str(exceptions.ClientError(response, 'operation'))
    if 'max retries' in error_msg:
        raise AssertionError("Retry information should not be in exception "
                             "message when retry attempts not in response "
                             "metadata: %s" % error_msg)


def test_can_handle_when_response_missing_error_key():
    response = {
        'ResponseMetadata': {
            'HTTPHeaders': {},
            'HTTPStatusCode': 503,
            'MaxAttemptsReached': True,
            'RetryAttempts': 4
        }
    }
    e = exceptions.ClientError(response, 'SomeOperation')
    if 'An error occurred (Unknown)' not in str(e):
        raise AssertionError(
            "Error code should default to 'Unknown' "
            "when missing error response, instead got: %s" % str(e))


class TestPickleExceptions(unittest.TestCase):
    def test_single_kwarg_botocore_error(self):
        exception = botocore.exceptions.DataNotFoundError(
            data_path='mypath')
        unpickled_exception = pickle.loads(pickle.dumps(exception))
        self.assertIsInstance(
            unpickled_exception, botocore.exceptions.DataNotFoundError)
        self.assertEqual(str(unpickled_exception), str(exception))
        self.assertEqual(unpickled_exception.kwargs, exception.kwargs)

    def test_multiple_kwarg_botocore_error(self):
        exception = botocore.exceptions.UnknownServiceError(
            service_name='myservice', known_service_names=['s3']
        )
        unpickled_exception = pickle.loads(pickle.dumps(exception))
        self.assertIsInstance(
            unpickled_exception, botocore.exceptions.UnknownServiceError)
        self.assertEqual(str(unpickled_exception), str(exception))
        self.assertEqual(unpickled_exception.kwargs, exception.kwargs)

    def test_client_error(self):
        exception = botocore.exceptions.ClientError(
            error_response={
                'Error': {'Code': 'MyCode', 'Message': 'MyMessage'}},
            operation_name='myoperation'
        )
        unpickled_exception = pickle.loads(pickle.dumps(exception))
        self.assertIsInstance(
            unpickled_exception, botocore.exceptions.ClientError)
        self.assertEqual(str(unpickled_exception), str(exception))
        self.assertEqual(
            unpickled_exception.operation_name, exception.operation_name)
        self.assertEqual(unpickled_exception.response, exception.response)

    def test_dynamic_client_error(self):
        session = botocore.session.Session()
        client = session.create_client('s3', 'us-west-2')
        exception = client.exceptions.NoSuchKey(
            error_response={
                'Error': {'Code': 'NoSuchKey', 'Message': 'Not Found'}},
            operation_name='myoperation'
        )
        unpickled_exception = pickle.loads(pickle.dumps(exception))
        self.assertIsInstance(
            unpickled_exception, botocore.exceptions.ClientError)
        self.assertEqual(str(unpickled_exception), str(exception))
        self.assertEqual(
            unpickled_exception.operation_name, exception.operation_name)
        self.assertEqual(unpickled_exception.response, exception.response)

    def test_http_client_error(self):
        exception = botocore.exceptions.HTTPClientError(
            botocore.awsrequest.AWSRequest(),
            botocore.awsrequest.AWSResponse(
                url='https://foo.com',
                status_code=400,
                headers={},
                raw=b''
            ),
            error='error'
        )
        unpickled_exception = pickle.loads(pickle.dumps(exception))
        self.assertIsInstance(
            unpickled_exception,
            botocore.exceptions.HTTPClientError
        )
        self.assertEqual(str(unpickled_exception), str(exception))
        self.assertEqual(unpickled_exception.kwargs, exception.kwargs)
        # The request/response properties on the HTTPClientError do not have
        # __eq__ defined so we want to make sure properties are at least
        # of the expected type
        self.assertIsInstance(
            unpickled_exception.request, botocore.awsrequest.AWSRequest)
        self.assertIsInstance(
            unpickled_exception.response, botocore.awsrequest.AWSResponse)
