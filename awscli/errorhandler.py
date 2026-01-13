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
import argparse
import logging
import signal

from botocore.exceptions import (
    ClientError,
    NoCredentialsError,
    NoRegionError,
)
from botocore.exceptions import (
    ParamValidationError as BotocoreParamValidationError,
)

from awscli.argparser import USAGE, ArgParseException
from awscli.argprocess import ParamError, ParamSyntaxError
from awscli.arguments import UnknownArgumentError
from awscli.autoprompt.factory import PrompterKeyboardInterrupt
from awscli.constants import (
    CLIENT_ERROR_RC,
    CONFIGURATION_ERROR_RC,
    GENERAL_ERROR_RC,
    PARAM_VALIDATION_ERROR_RC,
)
from awscli.customizations.exceptions import (
    ConfigurationError,
    ParamValidationError,
)
from awscli.errorformat import write_error
from awscli.formatter import get_formatter
from awscli.utils import PagerInitializationException

LOG = logging.getLogger(__name__)

VALID_ERROR_FORMATS = ['legacy', 'json', 'yaml', 'text', 'table', 'enhanced']
# Maximum number of items to display inline for collections
MAX_INLINE_ITEMS = 5


class EnhancedErrorFormatter:
    def format_error(self, error_info, stream):
        additional_fields = self._get_additional_fields(error_info)

        if not additional_fields:
            return

        stream.write('\nAdditional error details:\n')
        for key, value in additional_fields.items():
            if self._is_simple_value(value):
                stream.write(f'{key}: {value}\n')
            elif self._is_small_collection(value):
                stream.write(f'{key}: {self._format_inline(value)}\n')
            else:
                stream.write(
                    f'{key}: <complex value> '
                    f'(Use --cli-error-format with json or yaml '
                    f'to see full details)\n'
                )

    def _is_simple_value(self, value):
        return isinstance(value, (str, int, float, bool, type(None)))

    def _is_small_collection(self, value):
        if isinstance(value, list):
            return len(value) < MAX_INLINE_ITEMS and all(
                self._is_simple_value(item) for item in value
            )
        elif isinstance(value, dict):
            return len(value) < MAX_INLINE_ITEMS and all(
                self._is_simple_value(v) for v in value.values()
            )
        return False

    def _format_inline(self, value):
        if isinstance(value, list):
            return f"[{', '.join(str(item) for item in value)}]"
        elif isinstance(value, dict):
            items = ', '.join(f'{k}: {v}' for k, v in value.items())
            return f'{{{items}}}'
        return str(value)

    def _get_additional_fields(self, error_info):
        standard_keys = {'Code', 'Message'}
        return {k: v for k, v in error_info.items() if k not in standard_keys}


def construct_entry_point_handlers_chain():
    handlers = [
        ParamValidationErrorsHandler(),
        PrompterInterruptExceptionHandler(),
        InterruptExceptionHandler(),
        GeneralExceptionHandler(),
    ]
    return ChainedExceptionHandler(exception_handlers=handlers)


def construct_cli_error_handlers_chain(session=None):
    # UnknownArgumentErrorHandler and InterruptExceptionHandler are
    # intentionally excluded from structured formatting
    handlers = [
        ParamValidationErrorsHandler(session),
        UnknownArgumentErrorHandler(),
        ConfigurationErrorHandler(session),
        NoRegionErrorHandler(session),
        NoCredentialsErrorHandler(session),
        PagerErrorHandler(session),
        InterruptExceptionHandler(),
        ClientErrorHandler(session),
        GeneralExceptionHandler(session),
    ]
    return ChainedExceptionHandler(exception_handlers=handlers)


class BaseExceptionHandler:
    def handle_exception(self, exception, stdout, stderr):
        raise NotImplementedError('handle_exception')


class FilteredExceptionHandler(BaseExceptionHandler):
    EXCEPTIONS_TO_HANDLE = ()
    RC = None

    def __init__(self, session=None):
        self._session = session

    def handle_exception(self, exception, stdout, stderr, **kwargs):
        if isinstance(exception, self.EXCEPTIONS_TO_HANDLE):
            return_val = self._do_handle_exception(
                exception, stdout, stderr, **kwargs
            )
            if return_val is not None:
                return return_val

    def _do_handle_exception(self, exception, stdout, stderr, **kwargs):
        parsed_globals = kwargs.get('parsed_globals')
        error_info = self._extract_error_info(exception)

        if error_info:
            formatted_message = self._get_formatted_message(
                error_info, exception
            )
            displayed_structured = self._display_structured_error(
                error_info, formatted_message, stderr, parsed_globals
            )
            if displayed_structured:
                return self.RC

        message = (error_info or {}).get('Message', str(exception))
        write_error(stderr, message)
        return self.RC

    def _extract_error_info(self, exception):
        """Extract error information for structured formatting.

        Returns None by default. Subclasses should override to provide
        error information as a dict with 'Code' and 'Message' keys.
        """
        return None

    def _get_formatted_message(self, error_info, exception):
        code = error_info.get('Code', 'Unknown')
        message = error_info.get('Message', str(exception))
        return f"An error occurred ({code}): {message}"

    def _resolve_error_format(self, parsed_globals):
        if parsed_globals:
            error_format = getattr(parsed_globals, 'cli_error_format', None)
            if error_format:
                return error_format.lower()

        if self._session:
            try:
                error_format = self._session.get_config_variable(
                    'cli_error_format'
                )
                if error_format:
                    return error_format.lower()
            except (KeyError, AttributeError) as e:
                LOG.debug('Failed to get cli_error_format from config: %s', e)

        return 'enhanced'

    def _display_structured_error(
        self, error_info, formatted_message, stderr, parsed_globals=None
    ):
        try:
            error_format = self._resolve_error_format(parsed_globals)

            if error_format == 'legacy':
                return False

            if error_format not in VALID_ERROR_FORMATS:
                LOG.warning(
                    f"Invalid cli_error_format: '{error_format}'. "
                    f"Using 'enhanced' format."
                )
                error_format = 'enhanced'

            if error_format == 'enhanced':
                write_error(stderr, formatted_message)
                EnhancedErrorFormatter().format_error(error_info, stderr)
                return True

            formatter_args = parsed_globals or argparse.Namespace(
                query=None, color='auto'
            )
            formatter = get_formatter(error_format, formatter_args)
            formatter('error', error_info, stderr)
            return True

        except Exception as e:
            LOG.debug(
                'Failed to display structured error: %s', e, exc_info=True
            )
            return False


class ParamValidationErrorsHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = (
        ParamError,
        ParamSyntaxError,
        ArgParseException,
        ParamValidationError,
        BotocoreParamValidationError,
    )
    RC = PARAM_VALIDATION_ERROR_RC

    def _extract_error_info(self, exception):
        return {'Code': 'ParamValidation', 'Message': str(exception)}


class SilenceParamValidationMsgErrorHandler(ParamValidationErrorsHandler):
    def _do_handle_exception(self, exception, stdout, stderr, **kwargs):
        return self.RC


class ClientErrorHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = ClientError
    RC = CLIENT_ERROR_RC

    def _do_handle_exception(self, exception, stdout, stderr, **kwargs):
        parsed_globals = kwargs.get('parsed_globals')
        error_info = self._extract_error_info(exception)

        if error_info:
            formatted_message = self._get_formatted_message(
                error_info, exception
            )
            displayed_structured = self._display_structured_error(
                error_info, formatted_message, stderr, parsed_globals
            )
            if displayed_structured:
                return self.RC

        write_error(stderr, str(exception))
        return self.RC

    def _get_formatted_message(self, error_info, exception):
        return str(exception)

    def _extract_error_info(self, exception):
        error_response = self._extract_error_response(exception)
        if error_response and 'Error' in error_response:
            return error_response['Error']
        return None

    @staticmethod
    def _extract_error_response(exception):
        if not isinstance(exception, ClientError):
            return None

        if hasattr(exception, 'response') and 'Error' in exception.response:
            error_dict = dict(exception.response['Error'])

            # AWS services return modeled error fields
            # at the top level of the error response,
            # not nested under an Error key. Botocore preserves this structure.
            # Include these fields to provide complete error information.
            # Exclude response metadata and avoid duplicates.
            excluded_keys = {'Error', 'ResponseMetadata', 'Code', 'Message'}
            for key, value in exception.response.items():
                if key not in excluded_keys and key not in error_dict:
                    error_dict[key] = value

            return {'Error': error_dict}

        return None


class ConfigurationErrorHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = ConfigurationError
    RC = CONFIGURATION_ERROR_RC

    def _extract_error_info(self, exception):
        return {'Code': 'Configuration', 'Message': str(exception)}


class NoRegionErrorHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = NoRegionError
    RC = CONFIGURATION_ERROR_RC

    def _extract_error_info(self, exception):
        message = (
            f'{exception} You can also configure your region by running '
            f'"aws configure".'
        )
        return {'Code': 'NoRegion', 'Message': message}


class NoCredentialsErrorHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = NoCredentialsError
    RC = CONFIGURATION_ERROR_RC

    def _extract_error_info(self, exception):
        message = (
            f'{exception}. You can configure credentials '
            f'by running "aws login".'
        )
        return {'Code': 'NoCredentials', 'Message': message}


class PagerErrorHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = PagerInitializationException
    RC = CONFIGURATION_ERROR_RC

    def _extract_error_info(self, exception):
        message = (
            f'Unable to redirect output to pager. Received the '
            f'following error when opening pager:\n{exception}\n\n'
            f'Learn more about configuring the output pager by running '
            f'"aws help config-vars".'
        )
        return {'Code': 'Pager', 'Message': message}


class UnknownArgumentErrorHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = UnknownArgumentError
    RC = PARAM_VALIDATION_ERROR_RC

    def _do_handle_exception(self, exception, stdout, stderr, **kwargs):
        stderr.write("\n")
        stderr.write(f'usage: {USAGE}\n')
        write_error(stderr, str(exception))
        return self.RC


class InterruptExceptionHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = KeyboardInterrupt
    RC = 128 + signal.SIGINT

    def _do_handle_exception(self, exception, stdout, stderr, **kwargs):
        stdout.write("\n")
        return self.RC


class PrompterInterruptExceptionHandler(InterruptExceptionHandler):
    EXCEPTIONS_TO_HANDLE = PrompterKeyboardInterrupt

    def _do_handle_exception(self, exception, stdout, stderr, **kwargs):
        stderr.write(f'{exception}')
        stderr.write("\n")
        return self.RC


class GeneralExceptionHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = Exception
    RC = GENERAL_ERROR_RC

    def _do_handle_exception(self, exception, stdout, stderr, **kwargs):
        # Generic exceptions don't have meaningful structure,
        # so always use plain text formatting
        write_error(stderr, str(exception))
        return self.RC


class ChainedExceptionHandler(BaseExceptionHandler):
    def __init__(self, exception_handlers):
        self._exception_handlers = exception_handlers

    def inject_handler(self, position, handler):
        self._exception_handlers.insert(position, handler)

    def handle_exception(self, exception, stdout, stderr, **kwargs):
        for handler in self._exception_handlers:
            return_value = handler.handle_exception(
                exception, stdout, stderr, **kwargs
            )
            if return_value is not None:
                return return_value
