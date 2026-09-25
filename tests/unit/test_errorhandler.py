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
import errno
import io
import signal
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
from awscli.testutils import mock

Case = namedtuple('Case', ['exception', 'rc', 'stderr', 'stdout'])

BROKEN_PIPE_RC = 128 + 13


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


@pytest.fixture
def broken_pipe_error():
    return BrokenPipeError(errno.EPIPE, 'Broken pipe')


@pytest.fixture
def no_stdout_redirect():
    # The handler replaces the process wide stdout file descriptor, which
    # would swallow the output of the test runner itself.  Tests that care
    # about the redirect exercise it directly instead.
    with mock.patch.object(
        errorhandler, '_redirect_stdout_to_devnull'
    ) as patched:
        yield patched


@pytest.mark.parametrize(
    "chain_factory",
    [
        errorhandler.construct_entry_point_handlers_chain,
        errorhandler.construct_cli_error_handlers_chain,
    ],
)
def test_broken_pipe_is_handled_quietly(
    chain_factory, broken_pipe_error, no_stdout_redirect
):
    # A closed downstream pipe is a normal way for a command to end, so it
    # should not produce any error output.  See aws/aws-cli#5899.
    stdout = io.StringIO()
    stderr = io.StringIO()

    rc = chain_factory().handle_exception(broken_pipe_error, stdout, stderr)

    assert rc == BROKEN_PIPE_RC
    assert stderr.getvalue() == ''
    assert stdout.getvalue() == ''


def test_broken_pipe_rc_matches_sigpipe():
    # 128 + SIGPIPE is what standard Unix utilities report for a closed pipe.
    assert errorhandler.BROKEN_PIPE_RC == 128 + signal.SIGPIPE


def test_broken_pipe_redirects_stdout(broken_pipe_error, no_stdout_redirect):
    errorhandler.BrokenPipeExceptionHandler().handle_exception(
        broken_pipe_error, io.StringIO(), io.StringIO()
    )
    no_stdout_redirect.assert_called_once_with()


def test_unrelated_os_error_still_reported(no_stdout_redirect):
    # BrokenPipeError is an OSError subclass, so make sure the new handler
    # does not start silencing other OSErrors.
    stdout = io.StringIO()
    stderr = io.StringIO()
    error = OSError(errno.EACCES, 'Permission denied')

    rc = errorhandler.construct_entry_point_handlers_chain().handle_exception(
        error, stdout, stderr
    )

    assert rc == 255
    assert 'Permission denied' in stderr.getvalue()
    no_stdout_redirect.assert_not_called()


def test_redirect_stdout_to_devnull_discards_writes(tmp_path):
    # Use a real file as a stand in for stdout so that the file descriptor
    # belonging to the test runner is never touched.
    path = tmp_path / 'stdout.txt'
    with open(path, 'w') as fake_stdout:
        with mock.patch('sys.stdout', fake_stdout):
            errorhandler._redirect_stdout_to_devnull()
        fake_stdout.write('discarded')

    assert path.read_text() == ''


def test_redirect_stdout_to_devnull_without_fileno():
    # capture_output() and friends replace stdout with an in memory stream
    # that has no file descriptor, which must not raise.
    with mock.patch('sys.stdout', io.StringIO()):
        errorhandler._redirect_stdout_to_devnull()
