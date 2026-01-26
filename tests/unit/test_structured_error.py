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
import json
import signal
from unittest import mock

from ruamel.yaml import YAML
from botocore.exceptions import ClientError, NoCredentialsError, NoRegionError

from awscli.arguments import UnknownArgumentError
from awscli.constants import (
    CLIENT_ERROR_RC,
    CONFIGURATION_ERROR_RC,
    PARAM_VALIDATION_ERROR_RC,
)
from awscli.customizations.exceptions import (
    ConfigurationError,
    ParamValidationError,
)
from awscli.errorhandler import (
    ClientErrorHandler,
    EnhancedErrorFormatter,
    construct_cli_error_handlers_chain,
)
from awscli.utils import PagerInitializationException
from tests.unit.test_clidriver import FakeSession


class TestClientErrorHandler:
    def setup_method(self):
        self.session = FakeSession()
        self.handler = ClientErrorHandler(self.session)

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
        expected = (
            '\n'
            'aws: [ERROR]: An error occurred (NoSuchBucket) '
            'when calling the GetObject operation: Error\n'
            '\n'
            'Additional error details:\n'
            'BucketName: my-bucket\n'
        )
        assert stderr.getvalue() == expected

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
        expected = (
            '\n'
            'aws: [ERROR]: An error occurred (AccessDenied) '
            'when calling the GetObject operation: Access Denied\n'
        )
        assert stderr.getvalue() == expected

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
        expected = (
            '\n'
            'aws: [ERROR]: An error occurred (NoSuchBucket) '
            'when calling the GetObject operation: Error\n'
        )
        assert stderr.getvalue() == expected

    def test_error_format_case_insensitive(self):
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
        expected = (
            '\n'
            'aws: [ERROR]: An error occurred (NoSuchBucket) '
            'when calling the GetObject operation: Error\n'
            '\n'
            'Additional error details:\n'
            'BucketName: test\n'
        )
        assert stderr.getvalue() == expected


class TestEnhancedErrorFormatter:
    def setup_method(self):
        self.formatter = EnhancedErrorFormatter()

    def test_format_error_with_no_additional_fields(self):
        error_info = {
            'Code': 'AccessDenied',
            'Message': 'Access Denied',
        }

        stream = io.StringIO()
        self.formatter.format_error(error_info, stream)

        output = stream.getvalue()
        assert output == ''

    def test_format_error_with_simple_fields(self):
        error_info = {
            'Code': 'NoSuchBucket',
            'Message': 'The bucket does not exist',
            'BucketName': 'my-bucket',
            'Region': 'us-east-1',
        }

        stream = io.StringIO()
        self.formatter.format_error(error_info, stream)

        output = stream.getvalue()
        expected = (
            '\n'
            'Additional error details:\n'
            'BucketName: my-bucket\n'
            'Region: us-east-1\n'
        )
        assert output == expected

    def test_format_error_with_small_list(self):
        error_info = {
            'Code': 'ValidationError',
            'Message': 'Validation failed',
            'AllowedValues': ['value1', 'value2', 'value3'],
        }

        stream = io.StringIO()
        self.formatter.format_error(error_info, stream)

        output = stream.getvalue()
        expected = (
            '\n'
            'Additional error details:\n'
            'AllowedValues: [value1, value2, value3]\n'
        )
        assert output == expected

    def test_format_error_with_small_dict(self):
        error_info = {
            'Code': 'ValidationError',
            'Message': 'Validation failed',
            'Metadata': {'key1': 'value1', 'key2': 'value2'},
        }

        stream = io.StringIO()
        self.formatter.format_error(error_info, stream)

        output = stream.getvalue()
        expected = (
            '\n'
            'Additional error details:\n'
            'Metadata: {key1: value1, key2: value2}\n'
        )
        assert output == expected

    def test_format_error_with_complex_object(self):
        error_info = {
            'Code': 'ValidationError',
            'Message': 'Validation failed',
            'Details': [1, 2, 3, 4, 5, 6],
        }

        stream = io.StringIO()
        self.formatter.format_error(error_info, stream)

        output = stream.getvalue()
        expected = (
            '\n'
            'Additional error details:\n'
            'Details: <complex value>, '
            '--cli-error-format json recommended for full details\n'
        )
        assert output == expected

    def test_format_error_with_nested_dict(self):
        error_info = {
            'Code': 'ValidationError',
            'Message': 'Validation failed',
            'FieldErrors': {
                'email': {'pattern': 'invalid', 'required': True},
                'age': {'min': 0, 'max': 120},
            },
        }

        stream = io.StringIO()
        self.formatter.format_error(error_info, stream)

        output = stream.getvalue()
        expected = (
            '\n'
            'Additional error details:\n'
            'FieldErrors: <complex value>, '
            '--cli-error-format json recommended for full details\n'
        )
        assert output == expected

    def test_format_error_with_list_of_dicts(self):
        error_info = {
            'Code': 'TransactionCanceledException',
            'Message': 'Transaction cancelled',
            'CancellationReasons': [
                {
                    'Code': 'ConditionalCheckFailed',
                    'Message': 'Check failed',
                },
                {
                    'Code': 'ItemCollectionSizeLimitExceeded',
                    'Message': 'Too large',
                },
            ],
        }

        stream = io.StringIO()
        self.formatter.format_error(error_info, stream)

        output = stream.getvalue()
        expected = (
            '\n'
            'Additional error details:\n'
            'CancellationReasons: <complex value>, '
            '--cli-error-format json recommended for full details\n'
        )
        assert output == expected

    def test_format_error_with_mixed_types(self):
        error_info = {
            'Code': 'ComplexError',
            'Message': 'Complex error occurred',
            'StringField': 'test-value',
            'IntField': 42,
            'FloatField': 3.14,
            'BoolField': True,
            'NoneField': None,
        }

        stream = io.StringIO()
        self.formatter.format_error(error_info, stream)

        output = stream.getvalue()
        expected = (
            '\n'
            'Additional error details:\n'
            'StringField: test-value\n'
            'IntField: 42\n'
            'FloatField: 3.14\n'
            'BoolField: True\n'
            'NoneField: None\n'
        )
        assert output == expected

    def test_format_error_with_unicode_and_special_chars(self):
        error_info = {
            'Code': 'InvalidInput',
            'Message': 'Invalid input provided',
            'UserName': 'éîa',
            'Description': 'Error with "quotes" and \'apostrophes\'',
            'Path': '/path/to/file.txt',
        }

        stream = io.StringIO()
        self.formatter.format_error(error_info, stream)

        output = stream.getvalue()
        expected = (
            '\n'
            'Additional error details:\n'
            'UserName: éîa\n'
            'Description: Error with "quotes" and \'apostrophes\'\n'
            'Path: /path/to/file.txt\n'
        )
        assert output == expected

    def test_format_error_with_large_list(self):
        error_info = {
            'Code': 'LargeList',
            'Message': 'Large list error',
            'Items': list(range(10)),
        }

        stream = io.StringIO()
        self.formatter.format_error(error_info, stream)

        output = stream.getvalue()
        expected = (
            '\n'
            'Additional error details:\n'
            'Items: <complex value>, '
            '--cli-error-format json recommended for full details\n'
        )
        assert output == expected


class TestRealWorldErrorScenarios:
    def setup_method(self):
        self.session = FakeSession()
        self.handler = ClientErrorHandler(self.session)

    def test_dynamodb_transaction_cancelled_error(self):
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
        expected = (
            '\n'
            'aws: [ERROR]: An error occurred (TransactionCanceledException) '
            'when calling the TransactWriteItems operation: '
            'Transaction cancelled, please refer to '
            'CancellationReasons for specific reasons\n'
            '\n'
            'Additional error details:\n'
            'CancellationReasons: <complex value>, '
            '--cli-error-format json recommended for full details\n'
        )
        assert stderr.getvalue() == expected


class TestParsedGlobalsPassthrough:
    def test_error_handler_receives_parsed_globals_from_clidriver(self):
        session = FakeSession()

        parsed_globals = argparse.Namespace()
        parsed_globals.cli_error_format = 'json'
        parsed_globals.command = 's3'
        parsed_globals.color = 'auto'
        parsed_globals.query = None

        error_handler = construct_cli_error_handlers_chain(session)

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

        rc = error_handler.handle_exception(
            client_error, stdout, stderr, parsed_globals=parsed_globals
        )

        assert rc == CLIENT_ERROR_RC

        stderr_output = stderr.getvalue()
        parsed_json = json.loads(stderr_output)
        assert parsed_json['Code'] == 'NoSuchBucket'
        assert parsed_json['Message'] == 'The specified bucket does not exist'
        assert parsed_json['BucketName'] == 'test-bucket'

    def test_error_handler_without_parsed_globals_uses_default(self):
        session = FakeSession()

        error_handler = construct_cli_error_handlers_chain(session)

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

        rc = error_handler.handle_exception(
            client_error, stdout, stderr, parsed_globals=None
        )

        assert rc == CLIENT_ERROR_RC
        expected = (
            '\n'
            'aws: [ERROR]: An error occurred (NoSuchBucket) '
            'when calling the GetObject operation: '
            'The specified bucket does not exist\n'
            '\n'
            'Additional error details:\n'
            'BucketName: test-bucket\n'
        )
        assert stderr.getvalue() == expected


class TestNonModeledErrorStructuredFormatting:
    def setup_method(self):
        self.yaml = YAML(typ="safe", pure=True)

    def _load_yaml(self, content):
        return self.yaml.load(io.StringIO(content))

    def test_no_region_error_with_json_format(self):
        session = FakeSession()
        error_handler = construct_cli_error_handlers_chain(session)
        exception = NoRegionError()

        stdout = io.StringIO()
        stderr = io.StringIO()
        parsed_globals = argparse.Namespace()
        parsed_globals.cli_error_format = 'json'
        parsed_globals.query = None
        parsed_globals.color = 'auto'

        rc = error_handler.handle_exception(
            exception, stdout, stderr, parsed_globals=parsed_globals
        )

        assert rc == CONFIGURATION_ERROR_RC
        stderr_output = stderr.getvalue()
        parsed_json = json.loads(stderr_output)
        assert parsed_json['Code'] == 'NoRegion'
        assert 'aws configure' in parsed_json['Message']

    def test_no_credentials_error_with_yaml_format(self):
        session = FakeSession()
        error_handler = construct_cli_error_handlers_chain(session)
        exception = NoCredentialsError()

        stdout = io.StringIO()
        stderr = io.StringIO()
        parsed_globals = argparse.Namespace()
        parsed_globals.cli_error_format = 'yaml'
        parsed_globals.query = None
        parsed_globals.color = 'auto'

        rc = error_handler.handle_exception(
            exception, stdout, stderr, parsed_globals=parsed_globals
        )

        assert rc == CONFIGURATION_ERROR_RC
        stderr_output = stderr.getvalue()
        parsed_yaml = self._load_yaml(stderr_output)
        assert parsed_yaml['Code'] == 'NoCredentials'
        assert (
            'aws' in parsed_yaml['Message']
            and 'login' in parsed_yaml['Message']
        )

    def test_configuration_error_with_enhanced_format(self):
        session = FakeSession()

        error_handler = construct_cli_error_handlers_chain(session)
        exception = ConfigurationError('Invalid configuration value')

        stdout = io.StringIO()
        stderr = io.StringIO()
        parsed_globals = argparse.Namespace()
        parsed_globals.cli_error_format = 'enhanced'
        parsed_globals.query = None
        parsed_globals.color = 'auto'

        rc = error_handler.handle_exception(
            exception, stdout, stderr, parsed_globals=parsed_globals
        )

        assert rc == CONFIGURATION_ERROR_RC
        expected = (
            '\n'
            'aws: [ERROR]: An error occurred (Configuration): '
            'Invalid configuration value\n'
        )
        assert stderr.getvalue() == expected

    def test_pager_error_with_json_format(self):
        session = FakeSession()

        error_handler = construct_cli_error_handlers_chain(session)
        exception = PagerInitializationException('Pager not found')

        stdout = io.StringIO()
        stderr = io.StringIO()
        parsed_globals = argparse.Namespace()
        parsed_globals.cli_error_format = 'json'
        parsed_globals.query = None
        parsed_globals.color = 'auto'

        rc = error_handler.handle_exception(
            exception, stdout, stderr, parsed_globals=parsed_globals
        )

        assert rc == CONFIGURATION_ERROR_RC
        stderr_output = stderr.getvalue()
        parsed_json = json.loads(stderr_output)
        assert parsed_json['Code'] == 'Pager'
        assert 'Unable to redirect output to pager' in parsed_json['Message']

    def test_param_validation_error_with_yaml_format(self):
        session = FakeSession()

        error_handler = construct_cli_error_handlers_chain(session)
        exception = ParamValidationError('Invalid parameter value')

        stdout = io.StringIO()
        stderr = io.StringIO()
        parsed_globals = argparse.Namespace()
        parsed_globals.cli_error_format = 'yaml'
        parsed_globals.query = None
        parsed_globals.color = 'auto'

        rc = error_handler.handle_exception(
            exception, stdout, stderr, parsed_globals=parsed_globals
        )

        assert rc == PARAM_VALIDATION_ERROR_RC
        stderr_output = stderr.getvalue()
        parsed_yaml = self._load_yaml(stderr_output)
        assert parsed_yaml['Code'] == 'ParamValidation'
        assert 'Invalid parameter value' in parsed_yaml['Message']

    def test_error_codes_without_error_suffix(self):
        session = FakeSession()
        error_handler = construct_cli_error_handlers_chain(session)

        parsed_globals = argparse.Namespace()
        parsed_globals.cli_error_format = 'json'
        parsed_globals.query = None
        parsed_globals.color = 'auto'

        test_cases = [
            (NoRegionError(), 'NoRegion'),
            (NoCredentialsError(), 'NoCredentials'),
            (ConfigurationError('test'), 'Configuration'),
            (PagerInitializationException('test'), 'Pager'),
            (ParamValidationError('test'), 'ParamValidation'),
        ]

        for exception, expected_code in test_cases:
            stdout = io.StringIO()
            stderr = io.StringIO()

            error_handler.handle_exception(
                exception, stdout, stderr, parsed_globals=parsed_globals
            )

            stderr_output = stderr.getvalue()
            parsed_json = json.loads(stderr_output)
            assert parsed_json['Code'] == expected_code

    def test_unknown_argument_error_remains_plain_text(self):
        session = FakeSession()
        error_handler = construct_cli_error_handlers_chain(session)
        exception = UnknownArgumentError('--invalid-arg')

        stdout = io.StringIO()
        stderr = io.StringIO()
        parsed_globals = argparse.Namespace()
        parsed_globals.cli_error_format = 'json'
        parsed_globals.query = None
        parsed_globals.color = 'auto'

        rc = error_handler.handle_exception(
            exception, stdout, stderr, parsed_globals=parsed_globals
        )

        assert rc == PARAM_VALIDATION_ERROR_RC
        expected = (
            '\n'
            'usage: aws [options] <command> <subcommand> '
            '[<subcommand> ...] [parameters]\n'
            'To see help text, you can run:\n'
            '\n'
            '  aws help\n'
            '  aws <command> help\n'
            '  aws <command> <subcommand> help\n'
            '\n'
            '\n'
            'aws: [ERROR]: --invalid-arg\n'
        )
        assert stderr.getvalue() == expected

    def test_legacy_format_uses_plain_text(self):
        session = FakeSession()
        error_handler = construct_cli_error_handlers_chain(session)
        exception = NoRegionError()

        stdout = io.StringIO()
        stderr = io.StringIO()
        parsed_globals = argparse.Namespace()
        parsed_globals.cli_error_format = 'legacy'
        parsed_globals.query = None
        parsed_globals.color = 'auto'

        rc = error_handler.handle_exception(
            exception, stdout, stderr, parsed_globals=parsed_globals
        )

        assert rc == CONFIGURATION_ERROR_RC
        expected = (
            '\n'
            'aws: [ERROR]: You must specify a region. You can also '
            'configure your region by running "aws configure".\n'
        )
        assert stderr.getvalue() == expected

    def test_enhanced_format_includes_error_prefix(self):
        session = FakeSession()
        error_handler = construct_cli_error_handlers_chain(session)
        exception = NoRegionError()

        stdout = io.StringIO()
        stderr = io.StringIO()
        parsed_globals = argparse.Namespace()
        parsed_globals.cli_error_format = 'enhanced'
        parsed_globals.query = None
        parsed_globals.color = 'auto'

        rc = error_handler.handle_exception(
            exception, stdout, stderr, parsed_globals=parsed_globals
        )

        assert rc == CONFIGURATION_ERROR_RC
        expected = (
            '\n'
            'aws: [ERROR]: An error occurred (NoRegion): '
            'You must specify a region. You can also configure your region '
            'by running "aws configure".\n'
        )
        assert stderr.getvalue() == expected

    def test_interrupt_exception_remains_plain_text(self):
        session = FakeSession()
        error_handler = construct_cli_error_handlers_chain(session)
        exception = KeyboardInterrupt()

        stdout = io.StringIO()
        stderr = io.StringIO()
        parsed_globals = argparse.Namespace()
        parsed_globals.cli_error_format = 'json'
        parsed_globals.query = None
        parsed_globals.color = 'auto'

        rc = error_handler.handle_exception(
            exception, stdout, stderr, parsed_globals=parsed_globals
        )

        assert rc == 128 + signal.SIGINT
        assert stdout.getvalue() == "\n"
        assert stderr.getvalue() == ""
