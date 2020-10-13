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
import nose
from collections import namedtuple

from botocore.exceptions import (
    NoRegionError, NoCredentialsError, ClientError,
    ParamValidationError as BotocoreParamValidationError,
)
from awscli.arguments import UnknownArgumentError
from awscli.argparser import ArgParseException
from awscli.argprocess import ParamError, ParamSyntaxError
from awscli.customizations.exceptions import (
    ParamValidationError, ConfigurationError
)

from awscli import errorhandler


def _assert_rc_and_error_message(case):
    stderr = io.StringIO()
    stdout = io.StringIO()
    error_handler = errorhandler.construct_cli_error_handlers_chain()
    try:
        raise case.exception
    except BaseException as e:
        cr = error_handler.handle_exception(e, stdout, stderr)
        nose.tools.eq_(cr, case.rc, case.exception.__class__)
        nose.tools.assert_in(case.stderr, stderr.getvalue())
        nose.tools.eq_(case.stdout, stdout.getvalue())


def test_error_handling():
    Case = namedtuple('Case', [
        'exception',
        'rc',
        'stderr',
        'stdout'
    ])
    cases = [
        Case(Exception('error'), 255, 'error', ''),
        Case(KeyboardInterrupt(), 130, '', '\n'),
        Case(NoRegionError(), 253, 'region', ''),
        Case(NoCredentialsError(), 253, 'credentials', ''),
        Case(ClientError(error_response={}, operation_name=''), 254,
             'An error occurred', ''
        ),
        Case(BotocoreParamValidationError(report='param_name'), 252,
             'param_name', ''),
        Case(UnknownArgumentError('error'), 252, 'error', ''),
        Case(ArgParseException('error'), 252, 'error', ''),
        Case(ParamSyntaxError('error'), 252, 'error', ''),
        Case(ParamError(cli_name='cli', message='message'), 252,
             "'cli': message", ''),
        Case(ParamValidationError('error'), 252, 'error', ''),
        Case(ConfigurationError('error'), 253, 'error', ''),
    ]
    for case in cases:
        yield _assert_rc_and_error_message, case
