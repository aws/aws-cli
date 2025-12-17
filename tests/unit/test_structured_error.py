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
import argparse
import io
from unittest import mock

from botocore.exceptions import ClientError

from awscli.constants import CLIENT_ERROR_RC
from awscli.errorhandler import (
    ClientErrorHandler,
    EnhancedErrorFormatter,
    construct_cli_error_handlers_chain,
)
from tests.unit.test_clidriver import FakeSession


class TestClientErrorHandler:
    def setup_method(self):
        self.session = FakeSession()
        self.handler = ClientErrorHandler(self.session)

    def test_extract_error_response_from_client_error(self):
        error_response = {
            'Error': {
                'Code': 'NoSuchBucket',
                'Message': 'The specified bucket does not exist',
                'BucketName': 'my-bucket',
            },
            'ResponseMetadata': {'RequestId': '123'},
        }
        client_error = ClientError(error_response, 'GetObject')

        result = ClientErrorHandler._extract_error_response(client_error)

        assert result is not None
        assert 'Error' in result
        assert result['Error']['Code'] == 'NoSuchBucket'
        assert result['Error']['BucketName'] == 'my-bucket'

    def test_extract_error_response_with_top_level_fields(self):
        error_response = {
            'Error': {
                'Code': 'TransactionCanceledException',
                'Message': 'Transaction cancelled',
            },
            'CancellationReasons': [
                {
                    'Code': 'ConditionalCheckFailed',
                    'Message': 'The conditional request failed',
                    'Item': {'id': {'S': '123'}},
                }
            ],
            'ResponseMetadata': {'RequestId': '456'},
        }
        client_error = ClientError(error_response, 'TransactWriteItems')

        result = ClientErrorHandler._extract_error_response(client_error)

        assert result is not None
        assert 'Error' in result
        assert result['Error']['Code'] == 'TransactionCanceledException'
        assert 'CancellationReasons' in result['Error']
        assert len(result['Error']['CancellationReasons']) == 1
        assert (
            result['Error']['CancellationReasons'][0]['Code']
            == 'ConditionalCheckFailed'
        )

    def test_extract_error_response_from_non_client_error(self):
        result = ClientErrorHandler._extract_error_response(
            ValueError('Some error')
        )
        assert result is None

    def test_displays_structured_error_with_additional_members(self):
        error_response = {
            'Error': {
                'Code': 'NoSuchBucket',
                'Message': 'Error',
                'BucketName': 'my-bucket',
            },
            'ResponseMetadata': {'RequestId': '123'},
        }
        client_error = ClientError(error_response, 'GetObject')

        stdout = io.StringIO()
        stderr = io.StringIO()

        rc = self.handler.handle_exception(client_error, stdout, stderr)

        assert rc == CLIENT_ERROR_RC
        stderr_output = stderr.getvalue()
        assert 'NoSuchBucket' in stderr_output
        assert 'my-bucket' in stderr_output
        assert 'BucketName' in stderr_output

    def test_displays_standard_error_without_additional_members(self):
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'Access Denied',
            },
            'ResponseMetadata': {'RequestId': '123'},
        }
        client_error = ClientError(error_response, 'GetObject')

        stdout = io.StringIO()
        stderr = io.StringIO()

        rc = self.handler.handle_exception(client_error, stdout, stderr)

        assert rc == CLIENT_ERROR_RC
        stderr_output = stderr.getvalue()
        assert 'AccessDenied' in stderr_output
        assert 'Additional error details' not in stderr_output

    def test_respects_legacy_format_config(self):
        error_response = {
            'Error': {
                'Code': 'NoSuchBucket',
                'Message': 'Error',
                'BucketName': 'test',
            },
            'ResponseMetadata': {'RequestId': '123'},
        }
        client_error = ClientError(error_response, 'GetObject')

        self.session.session_vars['cli_error_format'] = 'legacy'

        stdout = io.StringIO()
        stderr = io.StringIO()

        rc = self.handler.handle_exception(client_error, stdout, stderr)

        assert rc == CLIENT_ERROR_RC
        stderr_output = stderr.getvalue()
        assert 'NoSuchBucket' in stderr_output
        assert 'BucketName' not in stderr_output

    def test_error_format_case_insensitive(self):
        """Test that error format config is case-insensitive."""
        error_response = {
            'Error': {
                'Code': 'NoSuchBucket',
                'Message': 'Error',
                'BucketName': 'test',
            },
            'ResponseMetadata': {'RequestId': '123'},
        }
        client_error = ClientError(error_response, 'GetObject')

        self.session.config_store.set_config_provider(
            'cli_error_format', mock.Mock(provide=lambda: 'Enhanced')
        )

        stdout = io.StringIO()
        stderr = io.StringIO()

        rc = self.handler.handle_exception(client_error, stdout, stderr)

        assert rc == CLIENT_ERROR_RC
        stderr_output = stderr.getvalue()
        assert 'NoSuchBucket' in stderr_output
        assert 'test' in stderr_output


class TestEnhancedErrorFormatter:
    def setup_method(self):
        self.formatter = EnhancedErrorFormatter()

    def test_is_simple_value(self):
        assert self.formatter._is_simple_value('string')
        assert self.formatter._is_simple_value(42)
        assert self.formatter._is_simple_value(3.14)
        assert self.formatter._is_simple_value(True)
        assert self.formatter._is_simple_value(None)
        assert not self.formatter._is_simple_value([1, 2, 3])
        assert not self.formatter._is_simple_value({'key': 'value'})

    def test_is_small_collection_list(self):
        assert self.formatter._is_small_collection(['a', 'b'])
        assert self.formatter._is_small_collection([1, 2, 3, 4])

        assert not self.formatter._is_small_collection([1, 2, 3, 4, 5])

        assert not self.formatter._is_small_collection([1, [2, 3]])
        assert not self.formatter._is_small_collection([{'key': 'value'}])

    def test_is_small_collection_dict(self):
        assert self.formatter._is_small_collection({'key': 'value'})
        assert self.formatter._is_small_collection(
            {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        )

        assert not self.formatter._is_small_collection(
            {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5}
        )

        assert not self.formatter._is_small_collection({'key': [1, 2]})
        assert not self.formatter._is_small_collection({'key': {'nested': 1}})

    def test_format_inline_list(self):
        result = self.formatter._format_inline([1, 2, 3])
        assert result == '[1, 2, 3]'

        result = self.formatter._format_inline(['a', 'b', 'c'])
        assert result == '[a, b, c]'

    def test_format_inline_dict(self):
        result = self.formatter._format_inline({'a': 1, 'b': 2})
        assert 'a: 1' in result
        assert 'b: 2' in result
        assert result.startswith('{')
        assert result.endswith('}')

    def test_get_additional_fields(self):
        error_info = {
            'Code': 'NoSuchBucket',
            'Message': 'The bucket does not exist',
            'BucketName': 'my-bucket',
            'Region': 'us-east-1',
        }

        additional = self.formatter._get_additional_fields(error_info)
        assert 'Code' not in additional
        assert 'Message' not in additional
        assert additional['BucketName'] == 'my-bucket'
        assert additional['Region'] == 'us-east-1'

    def test_format_error_with_no_additional_fields(self):
        error_info = {
            'Code': 'AccessDenied',
            'Message': 'Access Denied',
        }
        formatted_message = 'An error occurred (AccessDenied): Access Denied'

        stream = io.StringIO()
        self.formatter.format_error(error_info, formatted_message, stream)

        output = stream.getvalue()
        assert formatted_message in output
        assert 'Additional error details' not in output

    def test_format_error_with_simple_fields(self):
        error_info = {
            'Code': 'NoSuchBucket',
            'Message': 'The bucket does not exist',
            'BucketName': 'my-bucket',
            'Region': 'us-east-1',
        }
        formatted_message = (
            'An error occurred (NoSuchBucket): The bucket does not exist'
        )

        stream = io.StringIO()
        self.formatter.format_error(error_info, formatted_message, stream)

        output = stream.getvalue()
        assert formatted_message in output
        assert 'Additional error details' in output
        assert 'BucketName: my-bucket' in output
        assert 'Region: us-east-1' in output

    def test_format_error_with_small_list(self):
        error_info = {
            'Code': 'ValidationError',
            'Message': 'Validation failed',
            'AllowedValues': ['value1', 'value2', 'value3'],
        }
        formatted_message = (
            'An error occurred (ValidationError): Validation failed'
        )

        stream = io.StringIO()
        self.formatter.format_error(error_info, formatted_message, stream)

        output = stream.getvalue()
        assert formatted_message in output
        assert 'Additional error details' not in output
        assert 'AllowedValues: [value1, value2, value3]' in output

    def test_format_error_with_small_dict(self):
        error_info = {
            'Code': 'ValidationError',
            'Message': 'Validation failed',
            'Metadata': {'key1': 'value1', 'key2': 'value2'},
        }
        formatted_message = (
            'An error occurred (ValidationError): Validation failed'
        )

        stream = io.StringIO()
        self.formatter.format_error(error_info, formatted_message, stream)

        output = stream.getvalue()
        assert formatted_message in output
        assert 'Additional error details' not in output
        assert 'Metadata:' in output
        assert 'key1: value1' in output
        assert 'key2: value2' in output

    def test_format_error_with_complex_object(self):
        error_info = {
            'Code': 'ValidationError',
            'Message': 'Validation failed',
            'Details': [1, 2, 3, 4, 5, 6],
        }
        formatted_message = (
            'An error occurred (ValidationError): Validation failed'
        )

        stream = io.StringIO()
        self.formatter.format_error(error_info, formatted_message, stream)

        output = stream.getvalue()
        assert formatted_message in output
        assert 'Additional error details' not in output
        assert 'Details: <complex value>' in output
        assert '--cli-error-format with json, yaml, or text' in output

    def test_format_error_with_nested_dict(self):
        """Test formatting with nested dictionary structures."""
        error_info = {
            'Code': 'ValidationError',
            'Message': 'Validation failed',
            'FieldErrors': {
                'email': {'pattern': 'invalid', 'required': True},
                'age': {'min': 0, 'max': 120},
            },
        }
        formatted_message = (
            'An error occurred (ValidationError): Validation failed'
        )

        stream = io.StringIO()
        self.formatter.format_error(error_info, formatted_message, stream)

        output = stream.getvalue()
        assert formatted_message in output
        assert 'FieldErrors: <complex value>' in output

    def test_format_error_with_list_of_dicts(self):
        """Test formatting with list containing dictionaries."""
        error_info = {
            'Code': 'TransactionCanceledException',
            'Message': 'Transaction cancelled',
            'CancellationReasons': [
                {'Code': 'ConditionalCheckFailed', 'Message': 'Check failed'},
                {'Code': 'ItemCollectionSizeLimitExceeded', 'Message': 'Too large'},
            ],
        }
        formatted_message = (
            'An error occurred (TransactionCanceledException): '
            'Transaction cancelled'
        )

        stream = io.StringIO()
        self.formatter.format_error(error_info, formatted_message, stream)

        output = stream.getvalue()
        assert formatted_message in output
        assert 'CancellationReasons: <complex value>' in output

    def test_format_error_with_mixed_types(self):
        """Test formatting with various data types."""
        error_info = {
            'Code': 'ComplexError',
            'Message': 'Complex error occurred',
            'StringField': 'test-value',
            'IntField': 42,
            'FloatField': 3.14,
            'BoolField': True,
            'NoneField': None,
        }
        formatted_message = (
            'An error occurred (ComplexError): Complex error occurred'
        )

        stream = io.StringIO()
        self.formatter.format_error(error_info, formatted_message, stream)

        output = stream.getvalue()
        assert formatted_message in output
        assert 'Additional error details' in output
        assert 'StringField: test-value' in output
        assert 'IntField: 42' in output
        assert 'FloatField: 3.14' in output
        assert 'BoolField: True' in output
        assert 'NoneField: None' in output

    def test_format_error_with_unicode_and_special_chars(self):
        """Test formatting with unicode and special characters."""
        error_info = {
            'Code': 'InvalidInput',
            'Message': 'Invalid input provided',
            'UserName': 'José García',
            'Description': 'Error with "quotes" and \'apostrophes\'',
            'Path': '/path/to/file.txt',
        }
        formatted_message = (
            'An error occurred (InvalidInput): Invalid input provided'
        )

        stream = io.StringIO()
        self.formatter.format_error(error_info, formatted_message, stream)

        output = stream.getvalue()
        assert formatted_message in output
        assert 'José García' in output
        assert 'quotes' in output
        assert 'apostrophes' in output

    def test_format_error_with_large_list(self):
        """Test that large lists are marked as complex."""
        error_info = {
            'Code': 'LargeList',
            'Message': 'Large list error',
            'Items': list(range(10)),
        }
        formatted_message = (
            'An error occurred (LargeList): Large list error'
        )

        stream = io.StringIO()
        self.formatter.format_error(error_info, formatted_message, stream)

        output = stream.getvalue()
        assert formatted_message in output
        assert 'Items: <complex value>' in output


class TestRealWorldErrorScenarios:
    """Test real-world AWS error response structures."""

    def setup_method(self):
        self.session = FakeSession()
        self.handler = ClientErrorHandler(self.session)

    def test_dynamodb_transaction_cancelled_error(self):
        """Test DynamoDB TransactionCanceledException with CancellationReasons."""
        error_response = {
            'Error': {
                'Code': 'TransactionCanceledException',
                'Message': (
                    'Transaction cancelled, please refer to '
                    'CancellationReasons for specific reasons'
                ),
            },
            'CancellationReasons': [
                {
                    'Code': 'ConditionalCheckFailed',
                    'Message': 'The conditional request failed',
                    'Item': {
                        'id': {'S': 'item-123'},
                        'status': {'S': 'active'},
                    },
                },
                {
                    'Code': 'None',
                    'Message': None,
                },
            ],
            'ResponseMetadata': {
                'RequestId': 'abc-123',
                'HTTPStatusCode': 400,
            },
        }
        client_error = ClientError(error_response, 'TransactWriteItems')

        stdout = io.StringIO()
        stderr = io.StringIO()

        rc = self.handler.handle_exception(client_error, stdout, stderr)

        assert rc == CLIENT_ERROR_RC
        stderr_output = stderr.getvalue()
        assert 'TransactionCanceledException' in stderr_output
        assert 'CancellationReasons' in stderr_output

    def test_throttling_error_with_retry_info(self):
        """Test throttling error with retry information."""
        error_response = {
            'Error': {
                'Code': 'ThrottlingException',
                'Message': 'Rate exceeded',
            },
            'RetryAfterSeconds': 30,
            'RequestsPerSecond': 100,
            'CurrentRate': 150,
            'ResponseMetadata': {'RequestId': 'throttle-123'},
        }
        client_error = ClientError(error_response, 'DescribeInstances')

        stdout = io.StringIO()
        stderr = io.StringIO()

        rc = self.handler.handle_exception(client_error, stdout, stderr)

        assert rc == CLIENT_ERROR_RC
        stderr_output = stderr.getvalue()
        assert 'ThrottlingException' in stderr_output
        assert '30' in stderr_output
        assert '100' in stderr_output


class TestParsedGlobalsPassthrough:
    def test_error_handler_receives_parsed_globals_from_clidriver(self):
        session = FakeSession()

        parsed_globals = argparse.Namespace()
        parsed_globals.cli_error_format = 'json'
        parsed_globals.command = 's3'
        parsed_globals.color = 'auto'

        error_handler = construct_cli_error_handlers_chain(
            session, parsed_globals
        )

        error_response = {
            'Error': {
                'Code': 'NoSuchBucket',
                'Message': 'The specified bucket does not exist',
                'BucketName': 'test-bucket',
            },
            'ResponseMetadata': {'RequestId': '123'},
        }
        client_error = ClientError(error_response, 'GetObject')

        stdout = io.StringIO()
        stderr = io.StringIO()

        rc = error_handler.handle_exception(client_error, stdout, stderr)

        assert rc == CLIENT_ERROR_RC

        stderr_output = stderr.getvalue()
        assert '"Code"' in stderr_output or '"code"' in stderr_output.lower()
        assert 'NoSuchBucket' in stderr_output
        assert 'test-bucket' in stderr_output

    def test_error_handler_without_parsed_globals_uses_default(self):
        session = FakeSession()

        error_handler = construct_cli_error_handlers_chain(session, None)

        error_response = {
            'Error': {
                'Code': 'NoSuchBucket',
                'Message': 'The specified bucket does not exist',
                'BucketName': 'test-bucket',
            },
            'ResponseMetadata': {'RequestId': '123'},
        }
        client_error = ClientError(error_response, 'GetObject')

        stdout = io.StringIO()
        stderr = io.StringIO()

        rc = error_handler.handle_exception(client_error, stdout, stderr)

        assert rc == CLIENT_ERROR_RC

        stderr_output = stderr.getvalue()
        assert 'NoSuchBucket' in stderr_output
        assert 'test-bucket' in stderr_output
        assert 'BucketName' in stderr_output
