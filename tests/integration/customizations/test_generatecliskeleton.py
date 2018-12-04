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
import json

from nose.tools import assert_equal

from awscli.clidriver import create_clidriver
from awscli.testutils import unittest, aws
from awscli.customizations.preview import PREVIEW_SERVICES


def test_can_generate_skeletons_for_all_service_comands():
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
                    yield _test_gen_skeleton, command_name, sub_name


def _test_gen_skeleton(command_name, operation_name):
    p = aws('%s %s --generate-cli-skeleton' % (command_name, operation_name))
    assert_equal(p.rc, 0, 'Received non zero RC (%s) for command: %s %s'
                 % (p.rc, command_name, operation_name))
    try:
        parsed = json.loads(p.stdout)
    except ValueError as e:
        raise AssertionError(
            "Could not generate CLI skeleton for command: %s %s\n"
            "stdout:\n%s\n"
            "stderr:\n%s\n" % (command_name, operation_name))


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
            {'Bucket': '','Key': '', 'MFA': '', 'VersionId': '',
             'RequestPayer': ''}
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
