# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import sys

from awscli.compat import get_stderr_text_writer
from awscli.utils import write_exception
from awscli.constants import (
    PARAM_VALIDATION_ERROR_RC, CONFIGURATION_ERROR_RC, CLIENT_ERROR_RC,
    GENERAL_ERROR_RC
)

from botocore.exceptions import (
    ClientError, NoRegionError, NoCredentialsError,
    ParamValidationError as BototcoreParamValidationError
)


class ParamValidationError(Exception):
    """CLI parameter validation failed. Indicates RC 252.

    This exception indicates that the command was either invalid or failed to
    pass a client side validation on the command syntax or parameters provided.
    """
    RC = PARAM_VALIDATION_ERROR_RC
    DEBUG_MESSAGE = "Client side parameter validation failed"


class ConfigurationError(Exception):
    """CLI configuration is an invalid state. Indicates RC 253.

    This exception indicates that the command run may be syntactically correct
    but the CLI's environment or configuration is incorrect, incomplete, etc.
    """
    DEBUG_MESSAGE = "Invalid CLI or client configuration"
    RC = CONFIGURATION_ERROR_RC


class ExceptionHandler:
    # Context manager to suppress exception from clidriver and return
    # appropriate rc, log error and debug messages
    EXCEPTIONS_MAP = {
        ClientError: {
            'rc': CLIENT_ERROR_RC,
            'debug_message': 'Service returned an exception'
        },
        BototcoreParamValidationError: {
            'rc': PARAM_VALIDATION_ERROR_RC,
            'debug_message': 'Client side parameter validation failed'
        },
        NoCredentialsError: {
            'rc': CONFIGURATION_ERROR_RC,
            'debug_message': '{fmt}. You can configure credentials by running '
                             '"aws configure".',
            'error_message': '{fmt}. You can configure credentials by running '
                             '"aws configure".'

        },
        NoRegionError: {
            'rc': CONFIGURATION_ERROR_RC,
            'debug_message': '{fmt} You can also configure your '
                             'region by running "aws configure".',
            'error_message': '{fmt} You can also configure your '
                             'region by running "aws configure".',
        }

    }

    def __init__(self, *exceptions, logger=None):
        self._exceptions = exceptions
        self._logger = logger
        self.rc = None
        if self._logger is None:
            self._logger = logging.getLogger('awscli.clidriver')

    def __enter__(self):
        return self

    def _handle_exception(self, exctype, excinst):
        if hasattr(exctype, 'RC'):
            if hasattr(exctype, 'DEBUG_MESSAGE'):
                self._logger.debug(excinst.DEBUG_MESSAGE, exc_info=True)
            write_exception(excinst, outfile=get_stderr_text_writer())
            rc = exctype.RC
        elif issubclass(exctype, tuple(self.EXCEPTIONS_MAP)):
            for e in self.EXCEPTIONS_MAP:
                if issubclass(exctype, e):
                    excep = self.EXCEPTIONS_MAP[e]
            if 'debug_message' in excep:
                self._logger.debug(excep['debug_message'].format(**vars(exctype)),
                                   exc_info=True)
            error_message = str(excinst)
            if 'error_message' in excep:
                error_message = excep['error_message'].format(**vars(exctype))
            write_exception(error_message, outfile=get_stderr_text_writer())
            rc = excep['rc']
        elif issubclass(exctype, KeyboardInterrupt):
            # Shell standard for signals that terminate
            # the process is to return 128 + signum, in this case
            # SIGINT=2, so we'll have an RC of 130.
            sys.stdout.write("\n")
            rc = 128 + signal.SIGINT
        else:
            # RC 255 is the catch-all. 255 specifically should not be relied
            # on as exceptions can move from this catch-all classification
            # to a more specific RC such as one of the above.
            self._logger.debug("Exception caught in main()", exc_info=True)
            self._logger.debug("Exiting with rc %s" % GENERAL_ERROR_RC)
            write_exception(excinst, outfile=get_stderr_text_writer())
            rc = GENERAL_ERROR_RC
        return rc

    def __exit__(self, exctype, excinst, exctb):
        if exctype is not None:
            self.rc = self._handle_exception(exctype, excinst)
        return exctype is not None and issubclass(exctype, self._exceptions)
