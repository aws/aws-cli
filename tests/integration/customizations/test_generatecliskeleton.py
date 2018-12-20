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
import os
import json
import logging

import mock
from nose.tools import assert_equal

from awscli.testutils import unittest, aws, capture_output
from awscli.clidriver import create_clidriver
from awscli.customizations.preview import PREVIEW_SERVICES


class TestIntegGenerateCliSkeleton(unittest.TestCase):
    """This tests various services to see if the generated skeleton is correct

    The operations and services selected are arbitrary. Tried to pick
    operations that do not have many input options for the sake of readablity
    and maintenance. These are essentially smoke tests. It is not trying to
    test the different types of input shapes that can be generated in the
    skeleton. It is only testing wheter the skeleton generator argument works
    for various services.
    """
    def test_generate_cli_skeleton_s3api(self):
        p = aws('s3api delete-object --generate-cli-skeleton')
        self.assertEqual(p.rc, 0)
        self.assertEqual(
            json.loads(p.stdout),
            {
                'Bucket': '',
                'BypassGovernanceRetention': True,
                'Key': '',
                'MFA': '',
                'VersionId': '',
                'RequestPayer': 'requester',
            }
        )

    def test_generate_cli_skeleton_sqs(self):
        p = aws('sqs change-message-visibility --generate-cli-skeleton')
        self.assertEqual(p.rc, 0)
        self.assertEqual(
            json.loads(p.stdout),
            {'QueueUrl': '', 'ReceiptHandle': '', 'VisibilityTimeout': 0}
        )

    def test_generate_cli_skeleton_iam(self):
        p = aws('iam create-group --generate-cli-skeleton')
        self.assertEqual(p.rc, 0)
        self.assertEqual(
            json.loads(p.stdout),
            {'Path': '', 'GroupName': ''}
        )


def test_can_generate_skeletons_for_all_service_comands():
    environ = {
        'AWS_DATA_PATH': os.environ['AWS_DATA_PATH'],
        'AWS_DEFAULT_REGION': 'us-east-1',
        'AWS_ACCESS_KEY_ID': 'access_key',
        'AWS_SECRET_ACCESS_KEY': 'secret_key',
        'AWS_CONFIG_FILE': '',
        'AWS_SHARED_CREDENTIALS_FILE': '',
    }
    with mock.patch('os.environ', environ):
        driver = create_clidriver()
        help_command = driver.create_help_command()
        for command_name, command_obj in help_command.command_table.items():
            if command_name in PREVIEW_SERVICES:
                # Skip over any preview services for now.
                continue
            sub_help = command_obj.create_help_command()
            # This avoids command objects like ``PreviewModeCommand`` that
            # do not exhibit any visible functionality (i.e. provides a command
            # for the CLI).
            if hasattr(sub_help, 'command_table'):
                for sub_name, sub_command in sub_help.command_table.items():
                    op_help = sub_command.create_help_command()
                    arg_table = op_help.arg_table
                    if 'generate-cli-skeleton' in arg_table:
                        yield _test_gen_skeleton, command_name, sub_name,


def _test_gen_skeleton(command_name, operation_name):
    command = '%s %s --generate-cli-skeleton' % (command_name,
                                                 operation_name)
    stdout, stderr, _ = _run_cmd(command)
    # Test that a valid JSON blob is emitted to stdout is valid.
    try:
        json.loads(stdout)
    except ValueError as e:
        raise AssertionError(
            "Could not generate CLI skeleton for command: %s %s\n"
            "stdout:\n%s\n"
            "stderr:\n%s\n" % (command_name, operation_name, stdout,
                               stderr))


def _run_cmd(cmd, expected_rc=0):
    logging.debug("Calling cmd: %s", cmd)
    # Drivers do not seem to be reusable since the formatters seem to not clear
    # themselves between runs. This is fine in practice since a driver is only
    # called once but for tests it means we need to create a new driver for
    # each test, which is far more heavyweight than it needs to be. Might be
    # worth seeing if we can make drivers reusable to speed these up generated
    # tests.
    driver = create_clidriver()
    if not isinstance(cmd, list):
        cmdlist = cmd.split()
    else:
        cmdlist = cmd

    with capture_output() as captured:
        try:
            rc = driver.main(cmdlist)
        except SystemExit as e:
            # We need to catch SystemExit so that we
            # can get a proper rc and still present the
            # stdout/stderr to the test runner so we can
            # figure out what went wrong.
            rc = e.code
    stderr = captured.stderr.getvalue()
    stdout = captured.stdout.getvalue()
    assert_equal(
        rc, expected_rc,
        "Unexpected rc (expected: %s, actual: %s) for command: %s\n"
        "stdout:\n%sstderr:\n%s" % (
            expected_rc, rc, cmd, stdout, stderr))
    return stdout, stderr, rc
