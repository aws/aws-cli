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
from awscli.formatter import get_formatter
from awscli.utils import PagerInitializationException

LOG = logging.getLogger(__name__)

VALID_ERROR_FORMATS = ['legacy', 'json', 'yaml', 'text', 'table', 'enhanced']
# Maximum number of items to display inline for collections
MAX_INLINE_ITEMS = 5


class EnhancedErrorFormatter:
    def format_error(self, error_info, formatted_message, stream):
        stream.write(formatted_message)
        stream.write('\n')

        additional_fields = self._get_additional_fields(error_info)

        if not additional_fields:
            return

        if len(additional_fields) == 1:
            stream.write('\n')
            for key, value in additional_fields.items():
                if self._is_simple_value(value):
                    stream.write(f'{key}: {value}\n')
                elif self._is_small_collection(value):
                    stream.write(f'{key}: {self._format_inline(value)}\n')
                else:
                    stream.write(
                        f'{key}: <complex value>\n'
                        f'(Use --error-format json or --error-format yaml '
                        f'to see full details)\n'
                    )
        else:
            stream.write('\nAdditional error details:\n')
            for key, value in additional_fields.items():
                if self._is_simple_value(value):
                    stream.write(f'  {key}: {value}\n')
                elif self._is_small_collection(value):
                    stream.write(f'  {key}: {self._format_inline(value)}\n')
                else:
                    stream.write(
                        f'  {key}: <complex value>\n'
                        f'    (Use --error-format json or --error-format yaml '
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
            return '[' + ', '.join(str(item) for item in value) + ']'
        elif isinstance(value, dict):
            items = [f'{k}: {v}' for k, v in value.items()]
            return '{' + ', '.join(items) + '}'
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


def construct_cli_error_handlers_chain(session=None, parsed_globals=None):
    handlers = [
        ParamValidationErrorsHandler(),
        UnknownArgumentErrorHandler(),
        ConfigurationErrorHandler(),
        NoRegionErrorHandler(),
        NoCredentialsErrorHandler(),
        PagerErrorHandler(),
        InterruptExceptionHandler(),
        ClientErrorHandler(session, parsed_globals),
        GeneralExceptionHandler(),
    ]
    return ChainedExceptionHandler(exception_handlers=handlers)


class BaseExceptionHandler:
    def handle_exception(self, exception, stdout, stderr):
        raise NotImplementedError('handle_exception')


class FilteredExceptionHandler(BaseExceptionHandler):
    EXCEPTIONS_TO_HANDLE = ()
    MESSAGE = '%s'

    def handle_exception(self, exception, stdout, stderr):
        if isinstance(exception, self.EXCEPTIONS_TO_HANDLE):
            return_val = self._do_handle_exception(exception, stdout, stderr)
            if return_val is not None:
                return return_val

    def _do_handle_exception(self, exception, stdout, stderr):
        stderr.write("\n")
        stderr.write(self.MESSAGE % exception)
        stderr.write("\n")
        return self.RC


class ParamValidationErrorsHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = (
        ParamError,
        ParamSyntaxError,
        ArgParseException,
        ParamValidationError,
        BotocoreParamValidationError,
    )
    RC = PARAM_VALIDATION_ERROR_RC


class SilenceParamValidationMsgErrorHandler(ParamValidationErrorsHandler):
    def _do_handle_exception(self, exception, stdout, stderr):
        return self.RC


class ClientErrorHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = ClientError
    RC = CLIENT_ERROR_RC

    def __init__(self, session=None, parsed_globals=None):
        self._session = session
        self._parsed_globals = parsed_globals
        self._enhanced_formatter = None

    def _do_handle_exception(self, exception, stdout, stderr):
        displayed_structured = False
        if self._session:
            displayed_structured = self._try_display_structured_error(
                exception, stderr
            )

        if not displayed_structured:
            return super()._do_handle_exception(exception, stdout, stderr)

        return self.RC

    def _resolve_error_format(self, parsed_globals):
        if parsed_globals:
            error_format = getattr(parsed_globals, 'cli_error_format', None)
            if error_format:
                return error_format.lower()
        try:
            error_format = self._session.get_config_variable(
                'cli_error_format'
            )
            if error_format:
                return error_format.lower()
        except (KeyError, AttributeError):
            pass

        return 'enhanced'

    def _try_display_structured_error(self, exception, stderr):
        try:
            error_response = self._extract_error_response(exception)
            if not error_response or 'Error' not in error_response:
                return False

            error_info = error_response['Error']
            error_format = self._resolve_error_format(self._parsed_globals)

            if error_format not in VALID_ERROR_FORMATS:
                LOG.warning(
                    f"Invalid cli_error_format: '{error_format}'. "
                    f"Using 'enhanced' format."
                )
                error_format = 'enhanced'

            if error_format == 'legacy':
                return False

            formatted_message = str(exception)

            if error_format == 'enhanced':
                if self._enhanced_formatter is None:
                    self._enhanced_formatter = EnhancedErrorFormatter()
                self._enhanced_formatter.format_error(
                    error_info, formatted_message, stderr
                )
                return True

            temp_parsed_globals = argparse.Namespace()
            temp_parsed_globals.output = error_format
            temp_parsed_globals.query = None
            temp_parsed_globals.color = (
                getattr(self._parsed_globals, 'color', 'auto')
                if self._parsed_globals
                else 'auto'
            )

            formatter = get_formatter(error_format, temp_parsed_globals)
            formatter('error', error_info, stderr)
            return True

        except Exception as e:
            LOG.debug(
                'Failed to display structured error: %s', e, exc_info=True
            )
            return False

    @staticmethod
    def _extract_error_response(exception):
        if not isinstance(exception, ClientError):
            return None

        if hasattr(exception, 'response') and 'Error' in exception.response:
            return {'Error': exception.response['Error']}

        return None


class ConfigurationErrorHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = ConfigurationError
    RC = CONFIGURATION_ERROR_RC


class NoRegionErrorHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = NoRegionError
    RC = CONFIGURATION_ERROR_RC
    MESSAGE = (
        '%s You can also configure your region by running "aws configure".'
    )


class NoCredentialsErrorHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = NoCredentialsError
    RC = CONFIGURATION_ERROR_RC
    MESSAGE = '%s. You can configure credentials by running "aws login".'


class PagerErrorHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = PagerInitializationException
    RC = CONFIGURATION_ERROR_RC
    MESSAGE = (
        'Unable to redirect output to pager. Received the '
        'following error when opening pager:\n%s\n\n'
        'Learn more about configuring the output pager by running '
        '"aws help config-vars".'
    )


class UnknownArgumentErrorHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = UnknownArgumentError
    RC = PARAM_VALIDATION_ERROR_RC

    def _do_handle_exception(self, exception, stdout, stderr):
        stderr.write("\n")
        stderr.write(f'usage: {USAGE}\n{exception}\n')
        stderr.write("\n")
        return self.RC


class InterruptExceptionHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = KeyboardInterrupt
    RC = 128 + signal.SIGINT

    def _do_handle_exception(self, exception, stdout, stderr):
        stdout.write("\n")
        return self.RC


class PrompterInterruptExceptionHandler(InterruptExceptionHandler):
    EXCEPTIONS_TO_HANDLE = PrompterKeyboardInterrupt

    def _do_handle_exception(self, exception, stdout, stderr):
        stderr.write(f'{exception}')
        stderr.write("\n")
        return self.RC


class GeneralExceptionHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = Exception
    RC = GENERAL_ERROR_RC


class ChainedExceptionHandler(BaseExceptionHandler):
    def __init__(self, exception_handlers):
        self._exception_handlers = exception_handlers

    def inject_handler(self, position, handler):
        self._exception_handlers.insert(position, handler)

    def handle_exception(self, exception, stdout, stderr):
        for handler in self._exception_handlers:
            return_value = handler.handle_exception(exception, stdout, stderr)
            if return_value is not None:
                return return_value
