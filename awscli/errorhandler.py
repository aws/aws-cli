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
import logging
import signal

from botocore.exceptions import (
    NoRegionError, NoCredentialsError, ClientError,
    ParamValidationError as BotocoreParamValidationError,
)

from awscli.argprocess import ParamError, ParamSyntaxError
from awscli.arguments import UnknownArgumentError
from awscli.argparser import ArgParseException, USAGE
from awscli.constants import (
    PARAM_VALIDATION_ERROR_RC, CONFIGURATION_ERROR_RC, CLIENT_ERROR_RC,
    GENERAL_ERROR_RC
)
from awscli.autoprompt.factory import PrompterKeyboardInterrupt
from awscli.customizations.exceptions import (
    ParamValidationError, ConfigurationError
)


LOG = logging.getLogger(__name__)


def construct_entry_point_handlers_chain():
    handlers = [
        ParamValidationErrorsHandler(),
        PrompterInterruptExceptionHandler(),
        InterruptExceptionHandler(),
        GeneralExceptionHandler()
    ]
    return ChainedExceptionHandler(exception_handlers=handlers)


def construct_cli_error_handlers_chain():
    handlers = [
        ParamValidationErrorsHandler(),
        UnknownArgumentErrorHandler(),
        ConfigurationErrorHandler(),
        NoRegionErrorHandler(),
        NoCredentialsErrorHandler(),
        InterruptExceptionHandler(),
        ClientErrorHandler(),
        GeneralExceptionHandler()
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
        ParamError, ParamSyntaxError, ArgParseException,
        ParamValidationError, BotocoreParamValidationError
    )
    RC = PARAM_VALIDATION_ERROR_RC


class SilenceParamValidationMsgErrorHandler(ParamValidationErrorsHandler):
    def _do_handle_exception(self, exception, stdout, stderr):
        return self.RC


class ClientErrorHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = ClientError
    RC = CLIENT_ERROR_RC


class ConfigurationErrorHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = ConfigurationError
    RC = CONFIGURATION_ERROR_RC


class NoRegionErrorHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = NoRegionError
    RC = CONFIGURATION_ERROR_RC
    MESSAGE = '%s You can also configure your region by running "aws configure".'


class NoCredentialsErrorHandler(FilteredExceptionHandler):
    EXCEPTIONS_TO_HANDLE = NoCredentialsError
    RC = CONFIGURATION_ERROR_RC
    MESSAGE = '%s. You can configure credentials by running "aws configure".'


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
