# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import subprocess
import sys

import pytest

# Commands that should never trigger a prompt_toolkit import.
BASIC_COMMANDS = [
    's3 ls',
    'configure list',
    'logs describe-log-groups',
    'ecs describe-services',
]

_CHECK_SCRIPT = """\
import os
import sys

from unittest.mock import patch
from awscli.botocore.awsrequest import AWSResponse
from awscli.clidriver import create_clidriver

env = {{
    'AWS_DATA_PATH': os.environ.get('AWS_DATA_PATH', ''),
    'AWS_DEFAULT_REGION': 'us-east-1',
    'AWS_ACCESS_KEY_ID': 'testing',
    'AWS_SECRET_ACCESS_KEY': 'testing',
    'AWS_CONFIG_FILE': '',
    'AWS_SHARED_CREDENTIALS_FILE': '',
}}
if os.environ.get('ComSpec'):
    env['ComSpec'] = os.environ['ComSpec']

http_response = AWSResponse(None, 200, {{}}, None)

with patch('os.environ', env), \\
     patch('awscli.botocore.endpoint.Endpoint.make_request',
           return_value=(http_response, {{}})):
    driver = create_clidriver()
    try:
        driver.main({args})
    except SystemExit:
        pass

mods = [m for m in sys.modules if m.startswith('prompt_toolkit')]
if mods:
    print('FAIL: prompt_toolkit modules loaded: ' + ', '.join(sorted(mods)))
    sys.exit(1)
else:
    print('OK')
"""


@pytest.mark.parametrize('cmd', BASIC_COMMANDS)
def test_prompt_toolkit_not_imported(cmd):
    # Historically prompt_toolkit has contributed to significant
    # unnecessary initialization time. This test verifies it
    # is not imported for a handful of commands for which we know
    # it is not needed.
    script = _CHECK_SCRIPT.format(args=repr(cmd.split()))
    # Since prompt_toolkit might be imported during test-running, we execute
    # the commands in a subprocess to ensure we are testing only the modules
    # loaded for the commands under test.
    # We apply a timeout to prevent the subprocess for silently stalling our
    # scripts.
    result = subprocess.run(
        [sys.executable, '-c', script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"prompt_toolkit was unexpectedly imported for 'aws {cmd}':\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
