# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import unittest

import mock
from awscli import errorhandler


class TestErrorHandler(unittest.TestCase):

    def create_http_response(self, **kwargs):
        response = mock.Mock()
        for key, value in kwargs.items():
            setattr(response, key, value)
        return response

    def test_error_handler_client_side(self):
        response = {
            'Error': {'Code': 'AccessDenied',
                      'HostId': 'foohost',
                      'Message': 'Access Denied',
                      'RequestId': 'requestid'},
            'ResponseMetadata': {}}
        handler = errorhandler.ErrorHandler()
        http_response = self.create_http_response(status_code=403)
        # We're manually using the try/except form because
        # we want to catch the exception and assert that it has specific
        # attributes on it.
        operation = mock.Mock()
        operation.name = 'OperationName'
        try:
            handler(http_response, response, operation)
        except errorhandler.ClientError as e:
            # First, the operation name should be in the error message.
            self.assertIn('OperationName', str(e))
            # We should state that this is a ClientError.
            self.assertIn('client error', str(e))
            # And these values should be available on the exception
            # so clients can access this information programmatically.
            self.assertEqual(e.error_code, 'AccessDenied')
            self.assertEqual(e.error_message, 'Access Denied')
            self.assertEqual(e.operation_name, 'OperationName')
        except Exception as e:
            self.fail("Unexpected error raised: %s" % e)
        else:
            self.fail("Expected errorhandler.ClientError to be raised "
                      "but no exception was raised.")

    def test_error_handler_server_side(self):
        response = {
            'Error': {'Code': 'InternalError',
                      'HostId': 'foohost',
                      'Message': 'An internal error has occurred',
                      'RequestId': 'requestid'},
            'ResponseMetadata': {}}
        handler = errorhandler.ErrorHandler()
        http_response = self.create_http_response(status_code=500)
        # We're manually using the try/except form because
        # we want to catch the exception and assert that it has specific
        # attributes on it.
        operation = mock.Mock()
        operation.name = 'OperationName'
        try:
            handler(http_response, response, operation)
        except errorhandler.ServerError as e:
            # First, the operation name should be in the error message.
            self.assertIn('OperationName', str(e))
            # We should state that this is a ServerError.
            self.assertIn('server error', str(e))
            # And these values should be available on the exception
            # so clients can access this information programmatically.
            self.assertEqual(e.error_code, 'InternalError')
            self.assertEqual(e.error_message, 'An internal error has occurred')
            self.assertEqual(e.operation_name, 'OperationName')
        except Exception as e:
            self.fail("Unexpected error raised: %s" % e)
        else:
            self.fail("Expected errorhandler.ServerError to be raised "
                      "but no exception was raised.")

    def test_no_exception_raised_on_200(self):
        response = {
            'CommonPrefixes': [],
            'Contents': [],
        }
        handler = errorhandler.ErrorHandler()
        http_response = self.create_http_response(status_code=200)
        # We're manually using the try/except form because
        # we want to catch the exception and assert that it has specific
        # attributes on it.
        operation = mock.Mock()
        operation.name = 'OperationName'
        try:
            self.assertIsNone(handler(http_response, response, operation))
        except errorhandler.BaseOperationError as e:
            self.fail("Unexpected error raised: %s" % e)


if __name__ == '__main__':
    unittest.main()
