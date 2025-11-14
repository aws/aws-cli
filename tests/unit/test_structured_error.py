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

from awscli.structured_error import StructuredErrorHandler
from tests.unit.test_clidriver import FakeSession


class TestStructuredErrorHandler:
    def setup_method(self):
        self.session = FakeSession()
        from awscli.utils import OutputStreamFactory

        self.output_stream_factory = OutputStreamFactory(self.session)
        self.handler = StructuredErrorHandler(
            self.session, self.output_stream_factory
        )

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

        result = StructuredErrorHandler.extract_error_response(client_error)

        assert result is not None
        assert 'Error' in result
        assert result['Error']['Code'] == 'NoSuchBucket'
        assert result['Error']['BucketName'] == 'my-bucket'

    def test_extract_error_response_from_non_client_error(self):
        result = StructuredErrorHandler.extract_error_response(
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
        error_response = {
            'Code': 'NoSuchBucket',
            'Message': 'Error',
            'BucketName': 'my-bucket',
        }
        parsed_globals = mock.Mock()
        parsed_globals.output = 'json'

        assert self.handler.should_display(error_response, parsed_globals)

    def test_should_display_without_additional_members(self):
        error_response = {'Code': 'AccessDenied', 'Message': 'Access Denied'}
        parsed_globals = mock.Mock()
        parsed_globals.output = 'json'

        assert not self.handler.should_display(error_response, parsed_globals)

    def test_should_display_respects_hide_details(self):
        error_response = {
            'Code': 'NoSuchBucket',
            'Message': 'Error',
            'BucketName': 'test',
        }
        parsed_globals = mock.Mock()
        parsed_globals.output = 'json'

        self.session.config_store.set_config_provider(
            'cli_hide_error_details', mock.Mock(provide=lambda: True)
        )

        assert not self.handler.should_display(error_response, parsed_globals)

    def test_should_display_respects_legacy_format(self):
        error_response = {
            'Code': 'NoSuchBucket',
            'Message': 'Error',
            'BucketName': 'test',
        }
        parsed_globals = mock.Mock()
        parsed_globals.output = 'json'

        self.session.config_store.set_config_provider(
            'cli_error_format', mock.Mock(provide=lambda: 'LEGACY')
        )

        assert not self.handler.should_display(error_response, parsed_globals)

    def test_should_display_respects_output_off(self):
        error_response = {
            'Code': 'NoSuchBucket',
            'Message': 'Error',
            'BucketName': 'test',
        }
        parsed_globals = mock.Mock()
        parsed_globals.output = 'off'

        assert not self.handler.should_display(error_response, parsed_globals)

    def test_display_json_format(self):
        error_response = {
            'Code': 'NoSuchBucket',
            'Message': 'The specified bucket does not exist',
            'BucketName': 'my-bucket',
        }
        parsed_globals = mock.Mock()
        parsed_globals.output = 'json'
        parsed_globals.query = None

        mock_stream = io.StringIO()
        mock_context_manager = mock.MagicMock()
        mock_context_manager.__enter__.return_value = mock_stream
        mock_context_manager.__exit__.return_value = False

        mock_stream_factory = mock.Mock()
        mock_stream_factory.get_output_stream.return_value = (
            mock_context_manager
        )
        self.handler._output_stream_factory = mock_stream_factory

        self.handler.display(error_response, parsed_globals)

        output = mock_stream.getvalue()
        assert 'NoSuchBucket' in output
        assert 'my-bucket' in output

    def test_display_handles_exceptions_gracefully(self):
        error_response = {'Code': 'SomeError', 'Message': 'An error occurred'}
        parsed_globals = mock.Mock()
        parsed_globals.output = 'json'

        mock_context_manager = mock.MagicMock()
        mock_context_manager.__enter__.side_effect = Exception('Stream error')

        mock_stream_factory = mock.Mock()
        mock_stream_factory.get_output_stream.return_value = (
            mock_context_manager
        )
        self.handler._output_stream_factory = mock_stream_factory

        self.handler.display(error_response, parsed_globals)
