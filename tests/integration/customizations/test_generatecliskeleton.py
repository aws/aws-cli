# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import contextlib
import os
import json
import logging

import mock
import pytest
import ruamel.yaml as yaml

from awscli.clidriver import create_clidriver

# NOTE: This should be a standalone pytest fixture.  However, fixtures cannot
# be used outside of other fixtures or test cases, and it is needed by
# get_all_cli_skeleton_commands to generate the parameterization cases.
# So the environ patching logic is extracted out to this general helper
# context manager that can be used in both case generator and an actual
# fixture for the tests.
@contextlib.contextmanager
def patch_environ():
    environ = {
        'AWS_DATA_PATH': os.environ['AWS_DATA_PATH'],
        'AWS_DEFAULT_REGION': 'us-east-1',
        'AWS_ACCESS_KEY_ID': 'access_key',
        'AWS_SECRET_ACCESS_KEY': 'secret_key',
        'AWS_CONFIG_FILE': '',
        'AWS_SHARED_CREDENTIALS_FILE': '',
    }
    with mock.patch('os.environ', environ):
        yield


@pytest.fixture
def clean_environ():
    with patch_environ():
        yield


def get_all_cli_skeleton_commands():
    skeleton_commands = []
    with patch_environ():
        driver = create_clidriver()
        help_command = driver.create_help_command()
        for command_name, command_obj in help_command.command_table.items():
            sub_help = command_obj.create_help_command()
            # This avoids command objects like ``PreviewModeCommand`` that
            # do not exhibit any visible functionality (i.e. provides a command
            # for the CLI).
            if hasattr(sub_help, 'command_table'):
                for sub_name, sub_command in sub_help.command_table.items():
                    op_help = sub_command.create_help_command()
                    arg_table = op_help.arg_table
                    if 'generate-cli-skeleton' in arg_table:
                        skeleton_commands.append(f'{command_name} {sub_name}')
    return skeleton_commands


SKELETON_COMMANDS = get_all_cli_skeleton_commands()


@pytest.mark.parametrize('cmd', SKELETON_COMMANDS)
def test_gen_input_skeleton(cmd, capsys, clean_environ):
    stdout, stderr, _ = _run_cmd(cmd + ' --generate-cli-skeleton', capsys)
    # Test that a valid JSON blob is emitted to stdout is valid.
    try:
        json.loads(stdout)
    except ValueError:
        raise AssertionError(
            f"Could not generate CLI skeleton for command: {cmd}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}\n"
        )


@pytest.mark.parametrize('cmd', SKELETON_COMMANDS)
def test_gen_yaml_input_skeleton(cmd, capsys, clean_environ):
    stdout, stderr, _ = _run_cmd(
        cmd + ' --generate-cli-skeleton yaml-input', capsys
    )
    try:
        yaml.safe_load(stdout)
    except ValueError:
        raise AssertionError(
            f"Could not generate CLI YAML skeleton for command: {cmd}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}\n"
        )


def _run_cmd(cmd, capsys, expected_rc=0):
    logging.debug("Calling cmd: %s", cmd)
    # Drivers do not seem to be reusable since the formatters seem to not clear
    # themselves between runs. This is fine in practice since a driver is only
    # called once but for tests it means we need to create a new driver for
    # each test, which is far more heavyweight than it needs to be. Might be
    # worth seeing if we can make drivers reusable to speed these up generated
    # tests.
    driver = create_clidriver()
    try:
        rc = driver.main(cmd.split())
    except SystemExit as e:
        # We need to catch SystemExit so that we
        # can get a proper rc and still present the
        # stdout/stderr to the test runner so we can
        # figure out what went wrong.
        rc = e.code
    stdout, stderr = capsys.readouterr()
    assert rc == expected_rc, (
        f"Unexpected rc (expected: {expected_rc}, actual: {rc}) "
        f"for command: {cmd}\nstdout:\n{stdout}stderr:\n{stderr}"
    )
    return stdout, stderr, rc
