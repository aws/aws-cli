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

from awscli.testutils import unittest
from awscli import errorhandler


class TestChainedExceptionHandler(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        handlers = [
            errorhandler.ParamValidationErrorsHandler(),
            errorhandler.UnknownArgumentErrorHandler(),
            errorhandler.ClientErrorHandler(),
            errorhandler.ConfigurationErrorHandler(),
            errorhandler.NoRegionErrorHandler(),
            errorhandler.NoCredentialsErrorHandler(),
            errorhandler.InterruptExceptionHandler(),
            errorhandler.GeneralExceptionHandler()
        ]
        cls.error_handlers_chain = errorhandler.ChainedExceptionHandler(
            exception_handlers=handlers)

    def _assert_rc_and_error_message(self, case):
        stderr = io.StringIO()
        stdout = io.StringIO()
        try:
            raise case.exception
        except Exception as e:
            cr = self.error_handlers_chain.handle_exception(e, stdout, stderr)
            self.assertEqual(cr, case.rc, case.exception.__class__)
            self.assertIn(case.message, stderr.getvalue())
            self.assertEqual('', stdout.getvalue())

    def test_error_handling(self):
        Case = namedtuple('Case', [
            'exception',
            'rc',
            'message',
        ])
        cases = [
            Case(Exception(), 255, '\n\n'),
            Case(NoRegionError(), 253, 'region'),
            Case(NoCredentialsError(), 253, 'credentials'),
            Case(ClientError(error_response={}, operation_name=''), 254,
                 'An error occurred'
            ),
            Case(BotocoreParamValidationError(report='param_name'), 252,
                 'param_name'),
            Case(UnknownArgumentError(), 252, ''),
            Case(ArgParseException(), 252, '\n\n'),
            Case(ParamSyntaxError(), 252, '\n\n'),
            Case(ParamError(cli_name='cli', message='message'), 252,
                 "'cli': message"),
            Case(ParamValidationError(), 252, '\n\n'),
            Case(ConfigurationError(), 253, '\n\n'),
        ]
        for case in cases:
            self._assert_rc_and_error_message(case)
