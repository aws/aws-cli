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
import json
import logging
import os
import platform
import sys
from subprocess import Popen, PIPE

AWS_CMD = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))), 'bin', 'aws')
LOG = logging.getLogger('awscli.tests.integration')


class ProcessTerminatedError(Exception):
    pass


class Result(object):
    def __init__(self, rc, stdout, stderr, memory_usage=None):
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr
        LOG.debug("rc: %s", rc)
        LOG.debug("stdout: %s", stdout)
        LOG.debug("stderr: %s", stderr)
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
        aws_command = 'python %s' % AWS_CMD
    full_command = '%s %s' % (aws_command, command)
    LOG.debug("Running command: %s", full_command)
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
    encoding = getattr(sys.__stdout__, 'encoding')
    if encoding is None:
        encoding = 'utf-8'
    return Result(process.returncode,
                  stdout.decode(encoding),
                  stderr.decode(encoding),
                  memory)


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
