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
import logging

from botocore.exceptions import ClientError

from awscli.formatter import get_formatter


LOG = logging.getLogger('awscli.structured_error')


class StructuredErrorHandler:
    """Handles display of structured error information from AWS services.

    This class is responsible for determining when to display structured
    error output and formatting it appropriately based on user configuration
    and output format settings.
    """

    def __init__(self, session, output_stream_factory):
        self._session = session
        self._output_stream_factory = output_stream_factory

    def handle_error(self, error_response, parsed_globals):
        error_info = error_response.get('Error', {})

        if self.should_display(error_info, parsed_globals):
            self.display(error_info, parsed_globals)

    def should_display(self, error_info, parsed_globals):
        if not self._has_additional_error_members(error_info):
            return False

        config_store = self._session.get_component('config_store')
        error_format = config_store.get_config_variable('cli_error_format')
        if error_format == 'LEGACY':
            return False

        output = self._get_output_format(parsed_globals)
        if output == 'off':
            return False

        return True

    def display(self, error_response, parsed_globals):
        output = self._get_output_format(parsed_globals)

        try:
            formatter = get_formatter(output, parsed_globals)

            with self._output_stream_factory.get_output_stream() as stream:
                formatter('error', error_response, stream)
        except Exception as e:
            # Log the error but don't let it prevent the normal error handling
            LOG.debug(
                "Failed to display structured error output: %s",
                e,
                exc_info=True,
            )

    def _get_output_format(self, parsed_globals):
        output = parsed_globals.output
        if output is None:
            output = self._session.get_config_variable('output')
        return output

    def _has_additional_error_members(self, error_response):
        if not error_response:
            return False

        standard_keys = {'Code', 'Message'}
        error_keys = set(error_response.keys())
        return len(error_keys - standard_keys) > 0

    @staticmethod
    def extract_error_response(exception):
        if not isinstance(exception, ClientError):
            return None

        if hasattr(exception, 'response') and 'Error' in exception.response:
            return {'Error': exception.response['Error']}

        return None
