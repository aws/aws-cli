# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from botocore.exceptions import ClientError

from awscli.clidriver import CLIOperationCaller
from awscli.errorhandler import ClientErrorHandler
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

    def test_extract_error_response_from_non_client_error(self):
        result = ClientErrorHandler._extract_error_response(
            ValueError('Some error')
        )
        assert result is None

    def test_has_additional_error_members(self):
        assert self.handler._has_additional_error_members(
            {'Code': 'NoSuchBucket', 'Message': 'Error', 'BucketName': 'test'}
        )

        assert not self.handler._has_additional_error_members(
            {'Code': 'AccessDenied', 'Message': 'Access Denied'}
        )

        assert not self.handler._has_additional_error_members({})
        assert not self.handler._has_additional_error_members(None)

    def test_should_display_with_additional_members(self):
        error_info = {
            'Code': 'NoSuchBucket',
            'Message': 'Error',
            'BucketName': 'my-bucket',
        }

        assert self.handler._should_display_structured_error(error_info)

    def test_should_display_without_additional_members(self):
        error_info = {'Code': 'AccessDenied', 'Message': 'Access Denied'}

        assert not self.handler._should_display_structured_error(error_info)

    def test_should_display_respects_legacy_format(self):
        error_info = {
            'Code': 'NoSuchBucket',
            'Message': 'Error',
            'BucketName': 'test',
        }

        self.session.config_store.set_config_provider(
            'cli_error_format', mock.Mock(provide=lambda: 'LEGACY')
        )

        assert not self.handler._should_display_structured_error(error_info)

    def test_should_display_validates_error_format(self):
        error_info = {
            'Code': 'NoSuchBucket',
            'Message': 'Error',
            'BucketName': 'test',
        }

        self.session.config_store.set_config_provider(
            'cli_error_format', mock.Mock(provide=lambda: 'INVALID')
        )

        try:
            self.handler._should_display_structured_error(error_info)
            assert False, "Expected ValueError to be raised"
        except ValueError as e:
            assert 'Invalid cli_error_format' in str(e)
            assert 'INVALID' in str(e)
            assert 'STANDARD' in str(e)
            assert 'LEGACY' in str(e)

    def test_should_display_case_insensitive(self):
        error_info = {
            'Code': 'NoSuchBucket',
            'Message': 'Error',
            'BucketName': 'test',
        }

        self.session.config_store.set_config_provider(
            'cli_error_format', mock.Mock(provide=lambda: 'standard')
        )
        assert self.handler._should_display_structured_error(error_info)

        self.session.config_store.set_config_provider(
            'cli_error_format', mock.Mock(provide=lambda: 'legacy')
        )
        assert not self.handler._should_display_structured_error(error_info)

        self.session.config_store.set_config_provider(
            'cli_error_format', mock.Mock(provide=lambda: 'Standard')
        )
        assert self.handler._should_display_structured_error(error_info)


class TestStructuredErrorWithPagination:
    def setup_method(self):
        self.session = FakeSession()
        self.caller = CLIOperationCaller(self.session)

    def test_formatter_error_propagates_to_error_handler(self):
        """Test ClientError during formatting propagates to handler."""
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'Access Denied',
                'BucketName': 'my-bucket',
            },
            'ResponseMetadata': {'RequestId': '123'},
        }

        client_error = ClientError(error_response, 'ListObjects')

        parsed_globals = mock.Mock()
        parsed_globals.output = 'json'
        parsed_globals.query = None

        mock_formatter = mock.Mock()
        mock_formatter.side_effect = client_error

        with mock.patch(
            'awscli.clidriver.get_formatter', return_value=mock_formatter
        ):
            # The error should propagate without being caught
            try:
                self.caller._display_response(
                    'list-objects', {}, parsed_globals
                )
                assert False, "Expected ClientError to be raised"
            except ClientError as e:
                # Verify the error propagated correctly
                assert e.response['Error']['Code'] == 'AccessDenied'
                assert e.response['Error']['BucketName'] == 'my-bucket'


class TestClientErrorHandlerWithStructuredErrors:
    def setup_method(self):
        self.session = FakeSession()

    def test_client_error_handler_displays_structured_error(self):
        from awscli.errorhandler import ClientErrorHandler

        error_response = {
            'Error': {
                'Code': 'NoSuchBucket',
                'Message': 'The specified bucket does not exist',
                'BucketName': 'my-bucket',
            },
            'ResponseMetadata': {'RequestId': '123'},
        }
        client_error = ClientError(error_response, 'GetObject')

        handler = ClientErrorHandler(self.session)

        stdout = io.StringIO()
        stderr = io.StringIO()

        rc = handler.handle_exception(client_error, stdout, stderr)

        # Should return CLIENT_ERROR_RC
        from awscli.constants import CLIENT_ERROR_RC

        assert rc == CLIENT_ERROR_RC

        stderr_output = stderr.getvalue()
        assert 'NoSuchBucket' in stderr_output
        assert 'my-bucket' in stderr_output
        assert 'ClientError' in stderr_output or '"Code"' in stderr_output

        stdout_output = stdout.getvalue()
        assert stdout_output == ''

    def test_client_error_handler_without_additional_fields(self):
        from awscli.errorhandler import ClientErrorHandler

        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'Access Denied',
            },
            'ResponseMetadata': {'RequestId': '123'},
        }
        client_error = ClientError(error_response, 'GetObject')

        handler = ClientErrorHandler(self.session)

        stdout = io.StringIO()
        stderr = io.StringIO()

        rc = handler.handle_exception(client_error, stdout, stderr)

        # Should return CLIENT_ERROR_RC
        from awscli.constants import CLIENT_ERROR_RC

        assert rc == CLIENT_ERROR_RC

        stdout_output = stdout.getvalue()
        assert stdout_output == ''

        stderr_output = stderr.getvalue()
        assert (
            'ClientError' in stderr_output
            or 'AccessDenied' in stderr_output
        )
        assert '"Code"' not in stderr_output
