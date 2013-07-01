#!/usr/bin/env
# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
from tests import unittest

import mock

from botocore import retryhandler

HTTP_500_RESPONSE = mock.Mock()
HTTP_500_RESPONSE.status_code = 500

HTTP_400_RESPONSE = mock.Mock()
HTTP_400_RESPONSE.status_code = 400

HTTP_200_RESPONSE = mock.Mock()
HTTP_200_RESPONSE.status_code = 200


class TestRetryCheckers(unittest.TestCase):
    def assert_should_be_retried(self, response, attempt_number=1):
        self.assertTrue(self.checker(
            response=response, attempt_number=attempt_number))

    def assert_should_not_be_retried(self, response, attempt_number=1):
        self.assertFalse(self.checker(
            response=response, attempt_number=attempt_number))

    def test_status_code_checker(self):
        self.checker = retryhandler.HTTPStatusCodeChecker(500)
        self.assert_should_be_retried(response=(HTTP_500_RESPONSE, {}))

    def test_max_attempts(self):
        self.checker = retryhandler.MaxAttemptsDecorator(
            retryhandler.HTTPStatusCodeChecker(500), max_attempts=3)

        # Retry up to three times.
        self.assert_should_be_retried(
            (HTTP_500_RESPONSE, {}), attempt_number=1)
        self.assert_should_be_retried(
            (HTTP_500_RESPONSE, {}), attempt_number=2)
        # On the third failed response, we've reached the
        # max attempts so we should return False.
        self.assert_should_not_be_retried(
            (HTTP_500_RESPONSE, {}), attempt_number=3)

    def test_max_attempts_successful(self):
        self.checker = retryhandler.MaxAttemptsDecorator(
            retryhandler.HTTPStatusCodeChecker(500), max_attempts=3)

        self.assert_should_be_retried(
            (HTTP_500_RESPONSE, {}), attempt_number=1)
        # The second retry is successful.
        self.assert_should_not_be_retried(
            (HTTP_200_RESPONSE, {}), attempt_number=2)

        # But now we can reuse this object.
        self.assert_should_be_retried(
            (HTTP_500_RESPONSE, {}), attempt_number=1)
        self.assert_should_be_retried(
            (HTTP_500_RESPONSE, {}), attempt_number=2)
        self.assert_should_not_be_retried(
            (HTTP_500_RESPONSE, {}), attempt_number=3)

    def test_error_code_checker(self):
        self.checker = retryhandler.ServiceErrorCodeChecker(
            status_code=400, error_code='Throttled')
        response = (HTTP_400_RESPONSE,
                    {'Errors': [{'Code': 'Throttled'}]})
        self.assert_should_be_retried(response)

    def test_error_code_checker_does_not_match(self):
        self.checker = retryhandler.ServiceErrorCodeChecker(
            status_code=400, error_code='Throttled')
        response = (HTTP_400_RESPONSE,
                    {'Errors': [{'Code': 'NotThrottled'}]})
        self.assert_should_not_be_retried(response)

    def test_multi_checker(self):
        checker = retryhandler.ServiceErrorCodeChecker(
            status_code=400, error_code='Throttled')
        checker2 = retryhandler.HTTPStatusCodeChecker(500)
        self.checker = retryhandler.MultiChecker([checker, checker2])
        self.assert_should_be_retried((HTTP_500_RESPONSE, {}))
        self.assert_should_be_retried(
            response=(HTTP_400_RESPONSE, {'Errors': [{'Code': 'Throttled'}]}))
        self.assert_should_not_be_retried(
            response=(HTTP_200_RESPONSE, {}))


class TestCreateRetryConfiguration(unittest.TestCase):
    def setUp(self):
        self.retry_config = {
            '__default__': {
                'max_attempts': 5,
                'delay': {
                    'type': 'exponential',
                    'base': 1,
                    'growth_factor': 2,
                },
                'policies': {
                    'throttling': {
                        'applies_when': {
                            'response': {
                                'service_error_code': 'Throttling',
                                'http_status_code': 400,
                            }
                        }
                    }
                }
            },
            'OperationFoo': {
                'policies': {
                    'crc32check': {
                        'applies_when': {
                            'response': {
                                'crc32body': 'x-amz-crc32',
                            }
                        }
                    }
                }
            }
        }

    def test_create_retry_single_checker_service_level(self):
        checker = retryhandler.create_checker_from_retry_config(
            self.retry_config, operation_name=None)
        self.assertIsInstance(checker, retryhandler.MaxAttemptsDecorator)
        # We're reaching into internal fields here, but only to check
        # that the object is created properly.
        self.assertEqual(checker._max_attempts, 5)
        self.assertIsInstance(checker._checker,
                              retryhandler.ServiceErrorCodeChecker)
        self.assertEqual(checker._checker._error_code, 'Throttling')
        self.assertEqual(checker._checker._status_code, 400)

    def test_create_retry_for_operation(self):
        checker = retryhandler.create_checker_from_retry_config(
            self.retry_config, operation_name='OperationFoo')
        self.assertIsInstance(checker, retryhandler.MaxAttemptsDecorator)
        self.assertEqual(checker._max_attempts, 5)
        self.assertIsInstance(checker._checker,
                              retryhandler.MultiChecker)

    def test_create_retry_handler_with_no_operation(self):
        handler = retryhandler.create_retry_handler(
            self.retry_config, operation_name=None)
        self.assertIsInstance(handler, retryhandler.RetryHandler)
        # No good way to test for the delay function as the action
        # other than to just invoke it.
        self.assertEqual(handler._action(attempts=2), 2)
        self.assertEqual(handler._action(attempts=3), 4)


class TestRetryHandler(unittest.TestCase):
    def test_action_tied_to_policy(self):
        # When a retry rule matches we should return the
        # amount of time to sleep, otherwise we should return None.
        delay_function = retryhandler.create_exponential_delay_function( 1, 2)
        checker = retryhandler.HTTPStatusCodeChecker(500)
        handler = retryhandler.RetryHandler(checker, delay_function)
        response = (HTTP_500_RESPONSE, {})

        self.assertEqual(
            handler(response=response, attempts=1), 1)
        self.assertEqual(
            handler(response=response, attempts=2), 2)
        self.assertEqual(
            handler(response=response, attempts=3), 4)
        self.assertEqual(
            handler(response=response, attempts=4), 8)

    def test_none_response_when_no_matches(self):
        delay_function = retryhandler.create_exponential_delay_function( 1, 2)
        checker = retryhandler.HTTPStatusCodeChecker(500)
        handler = retryhandler.RetryHandler(checker, delay_function)
        response = (HTTP_200_RESPONSE, {})

        self.assertIsNone(handler(response=response, attempts=1))


class TestCRC32Checker(unittest.TestCase):
    def setUp(self):
        self.checker = retryhandler.CRC32Checker('x-amz-crc32')

    def test_crc32_matches(self):
        http_response = mock.Mock()
        http_response.status_code = 200
        # This is the crc32 of b'foo', so this should
        # pass the crc32 check.
        http_response.headers = {'x-amz-crc32': 2356372769}
        http_response.content = b'foo'
        self.assertIsNone(self.checker(
            response=(http_response, {}), attempt_number=1))

    def test_crc32_missing(self):
        # It's not an error is the crc32 header is missing.
        http_response = mock.Mock()
        http_response.status_code = 200
        http_response.headers = {}
        self.assertIsNone(self.checker(
            response=(http_response, {}), attempt_number=1))

    def test_crc32_check_fails(self):
        http_response = mock.Mock()
        http_response.status_code = 200
        # This is not the crc32 of b'foo', so this should
        # fail the crc32 check.
        http_response.headers = {'x-amz-crc32': 2356372768}
        http_response.content = b'foo'
        self.assertFalse(self.checker(
            response=(http_response, {}), attempt_number=1))


if __name__ == "__main__":
    unittest.main()
