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
from subprocess import Popen, PIPE

AWS_CMD = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))), 'bin', 'aws')

LOG = logging.getLogger('awscli.tests.integration')


class Result(object):
    def __init__(self, rc, stdout, stderr):
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr

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


def aws(command):
    if platform.system() == 'Windows':
        command = _escape_quotes(command)
    full_command = 'python %s %s' % (AWS_CMD, command)
    LOG.debug("Running command: %s", full_command)
    env = os.environ.copy()
    env['AWS_DEFAULT_REGION'] = "us-east-1"
    process = Popen(full_command, stdout=PIPE, stderr=PIPE, shell=True,
                    env=env)
    stdout, stderr = process.communicate()
    return Result(process.returncode,
                  stdout.decode('utf-8'),
                  stderr.decode('utf-8'))
