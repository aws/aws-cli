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


def construct_entry_point_handlers_chain():
    handlers = [
        ParamValidationErrorsHandler(),
        PrompterInterruptExceptionHandler(),
        InterruptExceptionHandler(),
        GeneralExceptionHandler(),
    ]
    return ChainedExceptionHandler(exception_handlers=handlers)


def construct_cli_error_handlers_chain(session=None):
    handlers = [
        ParamValidationErrorsHandler(),
        UnknownArgumentErrorHandler(),
        ConfigurationErrorHandler(),
        NoRegionErrorHandler(),
        NoCredentialsErrorHandler(),
        PagerErrorHandler(),
        InterruptExceptionHandler(),
        ClientErrorHandler(session),
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

    def __init__(self, session=None):
        self._session = session

    def _do_handle_exception(self, exception, stdout, stderr):
        if self._session:
            self._try_display_structured_error(exception, stderr)

        return super()._do_handle_exception(exception, stdout, stderr)

    def _try_display_structured_error(self, exception, stderr):
        try:
            error_response = self._extract_error_response(exception)

            if error_response and 'Error' in error_response:
                error_info = error_response['Error']

                if self._should_display_structured_error(error_info):
                    output = self._session.get_config_variable('output')

                    parsed_globals = argparse.Namespace()
                    parsed_globals.output = output
                    parsed_globals.query = None

                    formatter = get_formatter(output, parsed_globals)
                    formatter('error', error_info, stderr)
        except Exception as e:
            LOG.debug(
                'Failed to display structured error: %s', e, exc_info=True
            )

    def _should_display_structured_error(self, error_info):
        if not self._has_additional_error_members(error_info):
            return False

        config_store = self._session.get_component('config_store')
        error_format = config_store.get_config_variable('cli_error_format')

        if error_format:
            error_format = error_format.upper()

        valid_formats = ['STANDARD', 'LEGACY']
        if error_format and error_format not in valid_formats:
            raise ValueError(
                f"Invalid cli_error_format: {error_format}. "
                f"Valid values are: {', '.join(valid_formats)}"
            )

        if error_format == 'LEGACY':
            return False

        return True

    def _has_additional_error_members(self, error_response):
        if not error_response:
            return False

        standard_keys = {'Code', 'Message'}
        error_keys = set(error_response.keys())
        return len(error_keys - standard_keys) > 0

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
