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
import io
from collections import namedtuple

import pytest
from botocore.exceptions import (
    ClientError,
    NoCredentialsError,
    NoRegionError,
)
from botocore.exceptions import (
    ParamValidationError as BotocoreParamValidationError,
)

from awscli import errorhandler
from awscli.argparser import ArgParseException
from awscli.argprocess import ParamError, ParamSyntaxError
from awscli.arguments import UnknownArgumentError
from awscli.autoprompt.factory import PrompterKeyboardInterrupt
from awscli.customizations.exceptions import (
    ConfigurationError,
    ParamValidationError,
)

Case = namedtuple('Case', ['exception', 'rc', 'stderr', 'stdout'])


def _assert_rc_and_error_message(case, error_handler):
    stderr = io.StringIO()
    stdout = io.StringIO()
    try:
        raise case.exception
    except BaseException as e:
        cr = error_handler.handle_exception(e, stdout, stderr)
        assert cr == case.rc, case.exception.__class__
        assert case.stderr in stderr.getvalue()
        assert case.stdout == stdout.getvalue()


@pytest.mark.parametrize(
    "case",
    [
        Case(Exception('error'), 255, 'error', ''),
        Case(KeyboardInterrupt(), 130, '', '\n'),
        Case(NoRegionError(), 253, 'region', ''),
        Case(NoCredentialsError(), 253, 'credentials', ''),
        Case(
            ClientError(error_response={}, operation_name=''),
            254,
            'An error occurred',
            '',
        ),
        Case(
            BotocoreParamValidationError(report='param_name'),
            252,
            'param_name',
            '',
        ),
        Case(UnknownArgumentError('error'), 252, 'error', ''),
        Case(ArgParseException('error'), 252, 'error', ''),
        Case(ParamSyntaxError('error'), 252, 'error', ''),
        Case(
            ParamError(cli_name='cli', message='message'),
            252,
            "'cli': message",
            '',
        ),
        Case(ParamValidationError('error'), 252, 'error', ''),
        Case(ConfigurationError('error'), 253, 'error', ''),
    ],
)
def test_cli_error_handling_chain(case):
    error_handler = errorhandler.construct_cli_error_handlers_chain()
    _assert_rc_and_error_message(case, error_handler)


@pytest.mark.parametrize(
    "case",
    [
        Case(Exception('error'), 255, 'error', ''),
        Case(KeyboardInterrupt(), 130, '', '\n'),
        Case(NoRegionError(), 253, 'region', ''),
        Case(NoCredentialsError(), 253, 'credentials', ''),
        Case(
            ClientError(error_response={}, operation_name=''),
            254,
            'An error occurred',
            '',
        ),
        Case(BotocoreParamValidationError(report='param_name'), 252, '', ''),
        Case(UnknownArgumentError('error'), 252, '', ''),
        Case(ArgParseException('error'), 252, '', ''),
        Case(ParamSyntaxError('error'), 252, '', ''),
        Case(ParamError(cli_name='cli', message='message'), 252, '', ''),
        Case(ParamValidationError('error'), 252, '', ''),
        Case(ConfigurationError('error'), 253, 'error', ''),
    ],
)
def test_cli_error_handling_chain_injection(case):
    error_handler = errorhandler.construct_cli_error_handlers_chain()
    error_handler.inject_handler(
        0, errorhandler.SilenceParamValidationMsgErrorHandler()
    )
    _assert_rc_and_error_message(case, error_handler)


@pytest.mark.parametrize(
    "case",
    [
        Case(Exception('error'), 255, 'error', ''),
        Case(KeyboardInterrupt(), 130, '', '\n'),
        Case(PrompterKeyboardInterrupt('error'), 130, 'error', ''),
        Case(ParamValidationError('error'), 252, 'error', ''),
    ],
)
def test_entry_point_error_handling_chain(case):
    error_handler = errorhandler.construct_entry_point_handlers_chain()
    _assert_rc_and_error_message(case, error_handler)
