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
from requests import ConnectionError

from botocore import retryhandler
from botocore.exceptions import ChecksumError


HTTP_500_RESPONSE = mock.Mock()
HTTP_500_RESPONSE.status_code = 500

HTTP_400_RESPONSE = mock.Mock()
HTTP_400_RESPONSE.status_code = 400

HTTP_200_RESPONSE = mock.Mock()
HTTP_200_RESPONSE.status_code = 200


class TestRetryCheckers(unittest.TestCase):
    def assert_should_be_retried(self, response, attempt_number=1,
                                 caught_exception=None):
        self.assertTrue(self.checker(
            response=response, attempt_number=attempt_number,
            caught_exception=caught_exception))

    def assert_should_not_be_retried(self, response, attempt_number=1,
                                     caught_exception=None):
        self.assertFalse(self.checker(
            response=response, attempt_number=attempt_number,
            caught_exception=caught_exception))

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

    def test_error_code_checker_ignore_caught_exception(self):
        self.checker = retryhandler.ServiceErrorCodeChecker(
            status_code=400, error_code='Throttled')
        self.assert_should_not_be_retried(response=None,
                                          caught_exception=RuntimeError())

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

    def test_exception_checker_ignores_response(self):
        self.checker = retryhandler.ExceptionRaiser()
        self.assert_should_not_be_retried(
            response=(HTTP_200_RESPONSE, {}), caught_exception=None)

    def test_value_error_raised_when_missing_response_and_exception(self):
        self.checker = retryhandler.ExceptionRaiser()
        with self.assertRaises(ValueError):
            self.checker(1, response=None, caught_exception=None)


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
            },
            'OperationBar': {
                'policies': {
                    'socket_errors': {
                        'applies_when': {
                            'socket_errors': ["GENERAL_CONNECTION_ERROR"],
                        }
                    }
                }
            },
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

    def test_retry_with_socket_errors(self):
        checker = retryhandler.create_checker_from_retry_config(
            self.retry_config, operation_name='OperationBar')
        self.assertIsInstance(checker, retryhandler.BaseChecker)
        all_checkers = checker._checker._checkers
        self.assertIsInstance(all_checkers[0],
                              retryhandler.ServiceErrorCodeChecker)
        self.assertIsInstance(all_checkers[1],
                              retryhandler.ExceptionRaiser)

    def test_create_retry_handler_with_socket_errors(self):
        handler = retryhandler.create_retry_handler(
            self.retry_config, operation_name='OperationBar')
        with self.assertRaises(ConnectionError):
            handler(response=None, attempts=10,
                    caught_exception=ConnectionError())
        # No connection error raised because attempts < max_attempts.
        sleep_time = handler(response=None, attempts=1,
                             caught_exception=ConnectionError())
        self.assertEqual(sleep_time, 1)
        # But any other exception should be raised even if
        # attempts < max_attempts.
        with self.assertRaises(ValueError):
            sleep_time = handler(response=None, attempts=1,
                                caught_exception=ValueError())

    def test_create_retry_handler_with_no_operation(self):
        handler = retryhandler.create_retry_handler(
            self.retry_config, operation_name=None)
        self.assertIsInstance(handler, retryhandler.RetryHandler)
        # No good way to test for the delay function as the action
        # other than to just invoke it.
        self.assertEqual(handler._action(attempts=2), 2)
        self.assertEqual(handler._action(attempts=3), 4)

    def test_crc32_check_propogates_error(self):
        handler = retryhandler.create_retry_handler(
            self.retry_config, operation_name='OperationFoo')
        http_response = mock.Mock()
        http_response.status_code = 200
        # This is not the crc32 of b'foo', so this should
        # fail the crc32 check.
        http_response.headers = {'x-amz-crc32': 2356372768}
        http_response.content = b'foo'
        # The first 10 attempts we get a retry.
        self.assertEqual(handler(response=(http_response, {}), attempts=1,
                                 caught_exception=None), 1)
        with self.assertRaises(ChecksumError):
            handler(response=(http_response, {}), attempts=10,
                    caught_exception=None)


class TestRetryHandler(unittest.TestCase):
    def test_action_tied_to_policy(self):
        # When a retry rule matches we should return the
        # amount of time to sleep, otherwise we should return None.
        delay_function = retryhandler.create_exponential_delay_function( 1, 2)
        checker = retryhandler.HTTPStatusCodeChecker(500)
        handler = retryhandler.RetryHandler(checker, delay_function)
        response = (HTTP_500_RESPONSE, {})

        self.assertEqual(
            handler(response=response, attempts=1, caught_exception=None), 1)
        self.assertEqual(
            handler(response=response, attempts=2, caught_exception=None), 2)
        self.assertEqual(
            handler(response=response, attempts=3, caught_exception=None), 4)
        self.assertEqual(
            handler(response=response, attempts=4, caught_exception=None), 8)

    def test_none_response_when_no_matches(self):
        delay_function = retryhandler.create_exponential_delay_function( 1, 2)
        checker = retryhandler.HTTPStatusCodeChecker(500)
        handler = retryhandler.RetryHandler(checker, delay_function)
        response = (HTTP_200_RESPONSE, {})

        self.assertIsNone(handler(response=response, attempts=1,
                                  caught_exception=None))


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
            response=(http_response, {}), attempt_number=1,
            caught_exception=None))

    def test_crc32_missing(self):
        # It's not an error is the crc32 header is missing.
        http_response = mock.Mock()
        http_response.status_code = 200
        http_response.headers = {}
        self.assertIsNone(self.checker(
            response=(http_response, {}), attempt_number=1,
            caught_exception=None))

    def test_crc32_check_fails(self):
        http_response = mock.Mock()
        http_response.status_code = 200
        # This is not the crc32 of b'foo', so this should
        # fail the crc32 check.
        http_response.headers = {'x-amz-crc32': 2356372768}
        http_response.content = b'foo'
        with self.assertRaises(ChecksumError):
            self.checker(response=(http_response, {}), attempt_number=1,
                         caught_exception=None)


class TestDelayExponential(unittest.TestCase):
    def test_delay_with_numeric_base(self):
        self.assertEqual(retryhandler.delay_exponential(base=3,
                                                        growth_factor=2,
                                                        attempts=3), 12)

    def test_delay_with_rand_string(self):
        delay = retryhandler.delay_exponential(base='rand',
                                               growth_factor=2,
                                               attempts=3)
        # 2 ** (3 - 1) == 4, so the retry is between 0, 4.
        self.assertTrue(0 <= delay <= 4)

    def test_value_error_raised_with_non_positive_number(self):
        with self.assertRaises(ValueError):
            retryhandler.delay_exponential(
                base=-1, growth_factor=2, attempts=3)


if __name__ == "__main__":
    unittest.main()
