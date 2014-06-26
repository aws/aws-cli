# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Test utilities for the AWS CLI.

This module includes various classes/functions that help in writing
CLI unit/integration tests.  This module should not be imported by
any module **except** for test code.  This is included in the CLI
package so that code that is not part of the CLI can still take
advantage of all the testing utilities we provide.

"""
import os
import sys
import copy
import shutil
import time
import json
import random
import logging
import tempfile
import platform
import contextlib
from subprocess import Popen, PIPE

try:
    import mock
except ImportError as e:
    # In the off chance something imports this module
    # that's not suppose to, we should not stop the CLI
    # by raising an ImportError.  Now if anything actually
    # *uses* this module that isn't suppose to, that's s
    # different story.
    mock = None
import six
from botocore.hooks import HierarchicalEmitter
from botocore.session import Session
import botocore.loaders
from botocore.vendored import requests

import awscli.clidriver
from awscli.plugin import load_plugins
from awscli.clidriver import CLIDriver
from awscli import EnvironmentVariables


# The unittest module got a significant overhaul
# in 2.7, so if we're in 2.6 we can use the backported
# version unittest2.
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest


_LOADER = botocore.loaders.Loader()
INTEG_LOG = logging.getLogger('awscli.tests.integration')
AWS_CMD = None


def create_clidriver():
    driver = awscli.clidriver.create_clidriver()
    session = driver.session
    data_path = session.get_config_variable('data_path')
    _LOADER.data_path = data_path or ''
    session.register_component('data_loader', _LOADER)
    return driver


def get_aws_cmd():
    global AWS_CMD
    import awscli
    if AWS_CMD is None:
        # Try <repo>/bin/aws
        repo_root = os.path.dirname(os.path.abspath(awscli.__file__))
        aws_cmd = os.path.join(repo_root, 'bin', 'aws')
        if not os.path.isfile(aws_cmd):
            aws_cmd = _search_path_for_cmd('aws')
            if aws_cmd is None:
                raise ValueError('Could not find "aws" executable.  Either '
                                 'make sure it is on your PATH, or you can '
                                 'explicitly set this value using '
                                 '"set_aws_cmd()"')
        AWS_CMD = aws_cmd
    return AWS_CMD


def _search_path_for_cmd(cmd_name):
    for path in os.environ.get('PATH', '').split(os.pathsep):
        full_cmd_path = os.path.join(path, cmd_name)
        if os.path.isfile(full_cmd_path):
            return full_cmd_path
    return None


def set_aws_cmd(aws_cmd):
    global AWS_CMD
    AWS_CMD = aws_cmd


@contextlib.contextmanager
def temporary_file(mode):
    """This is a cross platform temporary file creation.

    tempfile.NamedTemporary file on windows creates a secure temp file
    that can't be read by other processes and can't be opened a second time.

    For tests, we generally *want* them to be read multiple times.
    The test fixture writes the temp file contents, the test reads the
    temp file.

    """
    temporary_directory = tempfile.mkdtemp()
    basename = 'tmpfile-%s-%s' % (int(time.time()), random.randint(1, 1000))
    full_filename = os.path.join(temporary_directory, basename)
    open(full_filename, 'w').close()
    try:
        with open(full_filename, mode) as f:
            yield f
    finally:
        shutil.rmtree(temporary_directory)


class BaseCLIDriverTest(unittest.TestCase):
    """Base unittest that use clidriver.

    This will load all the default plugins as well so it
    will simulate the behavior the user will see.
    """
    def setUp(self):
        self.environ = {
            'AWS_DATA_PATH': os.environ['AWS_DATA_PATH'],
            'AWS_DEFAULT_REGION': 'us-east-1',
            'AWS_ACCESS_KEY_ID': 'access_key',
            'AWS_SECRET_ACCESS_KEY': 'secret_key',
            'AWS_CONFIG_FILE': '',
        }
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()
        emitter = HierarchicalEmitter()
        session = Session(EnvironmentVariables, emitter, loader=_LOADER)
        load_plugins({}, event_hooks=emitter)
        driver = CLIDriver(session=session)
        self.session = session
        self.driver = driver

    def tearDown(self):
        self.environ_patch.stop()


class BaseAWSHelpOutputTest(BaseCLIDriverTest):
    def setUp(self):
        super(BaseAWSHelpOutputTest, self).setUp()
        self.renderer_patch = mock.patch('awscli.help.get_renderer')
        self.renderer_mock = self.renderer_patch.start()
        self.renderer = CapturedRenderer()
        self.renderer_mock.return_value = self.renderer

    def tearDown(self):
        super(BaseAWSHelpOutputTest, self).tearDown()
        self.renderer_patch.stop()

    def assert_contains(self, contains):
        if contains not in self.renderer.rendered_contents:
            self.fail("The expected contents:\n%s\nwere not in the "
                      "actual rendered contents:\n%s" % (
                          contains, self.renderer.rendered_contents))

    def assert_not_contains(self, contents):
        if contents in self.renderer.rendered_contents:
            self.fail("The contents:\n%s\nwere not suppose to be in the "
                      "actual rendered contents:\n%s" % (
                          contents, self.renderer.rendered_contents))

    def assert_text_order(self, *args, **kwargs):
        # First we need to find where the SYNOPSIS section starts.
        starting_from = kwargs.pop('starting_from')
        args = list(args)
        contents = self.renderer.rendered_contents
        self.assertIn(starting_from, contents)
        start_index = contents.find(starting_from)
        arg_indices = [contents.find(arg, start_index) for arg in args]
        previous = arg_indices[0]
        for i, index in enumerate(arg_indices[1:], 1):
            if index == -1:
                self.fail('The string %r was not found in the contents: %s'
                          % (args[index], contents))
            if index < previous:
                self.fail('The string %r came before %r, but was suppose to come '
                          'after it.\n%s' % (args[i], args[i - 1], contents))
            previous = index


class CapturedRenderer(object):
    def __init__(self):
        self.rendered_contents = ''

    def render(self, contents):
        self.rendered_contents = contents.decode('utf-8')


class BaseAWSCommandParamsTest(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.last_params = {}
        # awscli/__init__.py injects AWS_DATA_PATH at import time
        # so that we can find cli.json.  This might be fixed in the
        # future, but for now we just grab that value out of the real
        # os.environ so the patched os.environ has this data and
        # the CLI works.
        self.environ = {
            'AWS_DATA_PATH': os.environ['AWS_DATA_PATH'],
            'AWS_DEFAULT_REGION': 'us-east-1',
            'AWS_ACCESS_KEY_ID': 'access_key',
            'AWS_SECRET_ACCESS_KEY': 'secret_key',
        }
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()
        self.http_response = requests.models.Response()
        self.http_response.status_code = 200
        self.parsed_response = {}
        self.make_request_patch = mock.patch('botocore.endpoint.Endpoint.make_request')
        self.make_request_is_patched = False
        self.operations_called = []
        self.parsed_responses = None
        self.driver = create_clidriver()

    def tearDown(self):
        # This clears all the previous registrations.
        self.environ_patch.stop()
        if self.make_request_is_patched:
            self.make_request_patch.stop()

    def before_call(self, params, **kwargs):
        self._store_params(params)

    def _store_params(self, params):
        self.last_params = params

    def patch_make_request(self):
        make_request_patch = self.make_request_patch.start()
        if self.parsed_responses is not None:
            make_request_patch.side_effect = lambda *args, **kwargs: \
                (self.http_response, self.parsed_responses.pop(0))
        else:
            make_request_patch.return_value = (self.http_response, self.parsed_response)
        self.make_request_is_patched = True

    def assert_params_for_cmd(self, cmd, params=None, expected_rc=0,
                              stderr_contains=None, ignore_params=None):
        stdout, stderr, rc = self.run_cmd(cmd, expected_rc)
        if stderr_contains is not None:
            self.assertIn(stderr_contains, stderr)
        if params is not None:
            last_params = copy.copy(self.last_params)
            if ignore_params is not None:
                for key in ignore_params:
                    try:
                        del last_params[key]
                    except KeyError:
                        pass
            self.assertDictEqual(params, last_params)
        return stdout, stderr, rc

    def before_parameter_build(self, params, operation, **kwargs):
        self.last_kwargs = params
        self.operations_called.append((operation, params))

    def run_cmd(self, cmd, expected_rc=0):
        logging.debug("Calling cmd: %s", cmd)
        self.patch_make_request()
        self.driver.session.register('before-call', self.before_call)
        self.driver.session.register('before-parameter-build',
                                self.before_parameter_build)
        if not isinstance(cmd, list):
            cmdlist = cmd.split()
        else:
            cmdlist = cmd

        captured_stderr = six.StringIO()
        captured_stdout = six.StringIO()
        with mock.patch('sys.stderr', captured_stderr):
            with mock.patch('sys.stdout', captured_stdout):
                try:
                    rc = self.driver.main(cmdlist)
                except SystemExit as e:
                    # We need to catch SystemExit so that we
                    # can get a proper rc and still present the
                    # stdout/stderr to the test runner so we can
                    # figure out what went wrong.
                    rc = e.code
        stderr = captured_stderr.getvalue()
        stdout = captured_stdout.getvalue()
        self.assertEqual(
            rc, expected_rc,
            "Unexpected rc (expected: %s, actual: %s) for command: %s" % (
                expected_rc, rc, cmd))
        return stdout, stderr, rc


class FileCreator(object):
    def __init__(self):
        self.rootdir = tempfile.mkdtemp()

    def remove_all(self):
        shutil.rmtree(self.rootdir)

    def create_file(self, filename, contents, mtime=None):
        """Creates a file in a tmpdir

        ``filename`` should be a relative path, e.g. "foo/bar/baz.txt"
        It will be translated into a full path in a tmp dir.

        If the ``mtime`` argument is provided, then the file's
        mtime will be set to the provided value (must be an epoch time).
        Otherwise the mtime is left untouched.

        Returns the full path to the file.

        """
        full_path = os.path.join(self.rootdir, filename)
        if not os.path.isdir(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))
        with open(full_path, 'w') as f:
            f.write(contents)
        if mtime is not None:
            os.utime(full_path, (mtime, mtime))
        return full_path

    def append_file(self, filename, contents):
        """Append contents to a file

        ``filename`` should be a relative path, e.g. "foo/bar/baz.txt"
        It will be translated into a full path in a tmp dir.

        Returns the full path to the file.
        """
        full_path = os.path.join(self.rootdir, filename)
        if not os.path.isdir(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))
        with open(full_path, 'a') as f:
            f.write(contents)
        return full_path

    def full_path(self, filename):
        """Translate relative path to full path in temp dir.

        f.full_path('foo/bar.txt') -> /tmp/asdfasd/foo/bar.txt
        """
        return os.path.join(self.rootdir, filename)


class ProcessTerminatedError(Exception):
    pass


class Result(object):
    def __init__(self, rc, stdout, stderr, memory_usage=None):
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr
        INTEG_LOG.debug("rc: %s", rc)
        INTEG_LOG.debug("stdout: %s", stdout)
        INTEG_LOG.debug("stderr: %s", stderr)
        if memory_usage is None:
            memory_usage = []
        self.memory_usage = memory_usage

    @property
    def json(self):
        return json.loads(self.stdout)


def _escape_quotes(command):
    # For windows we have different rules for escaping.
    # First, double quotes must be escaped.
    command = command.replace('"', '\\"')
    # Second, single quotes do nothing, to quote a value we need
    # to use double quotes.
    command = command.replace("'", '"')
    return command


def aws(command, collect_memory=False, env_vars=None,
        wait_for_finish=True):
    """Run an aws command.

    This help function abstracts the differences of running the "aws"
    command on different platforms.

    If collect_memory is ``True`` the the Result object will have a list
    of memory usage taken at 2 second intervals.  The memory usage
    will be in bytes.

    If env_vars is None, this will set the environment variables
    to be used by the aws process.

    If wait_for_finish is False, then the Process object is returned
    to the caller.  It is then the caller's responsibility to ensure
    proper cleanup.  This can be useful if you want to test timeout's
    or how the CLI responds to various signals.

    """
    if platform.system() == 'Windows':
        command = _escape_quotes(command)
    if 'AWS_TEST_COMMAND' in os.environ:
        aws_command = os.environ['AWS_TEST_COMMAND']
    else:
        aws_command = 'python %s' % get_aws_cmd()
    full_command = '%s %s' % (aws_command, command)
    stdout_encoding = _get_stdout_encoding()
    if isinstance(full_command, six.text_type) and not six.PY3:
        full_command = full_command.encode(stdout_encoding)
    INTEG_LOG.debug("Running command: %s", full_command)
    env = os.environ.copy()
    env['AWS_DEFAULT_REGION'] = "us-east-1"
    if env_vars is not None:
        env = env_vars
    process = Popen(full_command, stdout=PIPE, stderr=PIPE, shell=True,
                    env=env)
    if not wait_for_finish:
        return process
    memory = None
    if not collect_memory:
        stdout, stderr = process.communicate()
    else:
        stdout, stderr, memory = _wait_and_collect_mem(process)
    return Result(process.returncode,
                  stdout.decode(stdout_encoding),
                  stderr.decode(stdout_encoding),
                  memory)


def _get_stdout_encoding():
    encoding = getattr(sys.__stdout__, 'encoding', None)
    if encoding is None:
        encoding = 'utf-8'
    return encoding


def _wait_and_collect_mem(process):
    # We only know how to collect memory on mac/linux.
    if platform.system() == 'Darwin':
        get_memory = _get_memory_with_ps
    elif platform.system() == 'Linux':
        get_memory = _get_memory_with_ps
    else:
        raise ValueError(
            "Can't collect memory for process on platform %s." %
            platform.system())
    memory = []
    while process.poll() is None:
        try:
            current = get_memory(process.pid)
        except ProcessTerminatedError:
            # It's possible the process terminated between .poll()
            # and get_memory().
            break
        memory.append(current)
    stdout, stderr = process.communicate()
    return stdout, stderr, memory


def _get_memory_with_ps(pid):
    # It's probably possible to do with proc_pidinfo and ctypes on a Mac,
    # but we'll do it the easy way with parsing ps output.
    command_list = 'ps u -p'.split()
    command_list.append(str(pid))
    p = Popen(command_list, stdout=PIPE)
    stdout = p.communicate()[0]
    if not p.returncode == 0:
        raise ProcessTerminatedError(str(pid))
    else:
        # Get the RSS from output that looks like this:
        # USER       PID  %CPU %MEM      VSZ    RSS   TT  STAT STARTED      TIME COMMAND
        # user     47102   0.0  0.1  2437000   4496 s002  S+    7:04PM   0:00.12 python2.6
        return int(stdout.splitlines()[1].split()[5]) * 1024
