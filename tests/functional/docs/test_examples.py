#!/usr/bin/env python
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
"""Test help output for the AWS CLI.

The purpose of these docs is to test that the generated output looks how
we expect.

It's intended to be as end to end as possible, but instead of looking
at the man output, we look one step before at the generated rst output
(it's easier to verify).

"""
import os
from awscli.testutils import BaseAWSHelpOutputTest


# Mapping of command names to subcommands that have examples in their help
# output.  This isn't mean to be an exhaustive list, but should help catch
# things like command table renames, virtual commands, etc.
COMMAND_EXAMPLES = {
    'cloudwatch': ['put-metric-data'],
    's3': ['cp', 'ls', 'mb', 'mv', 'rb', 'rm', 'sync'],
    's3api': ['get-object', 'put-object'],
    'ec2': ['run-instances', 'start-instances', 'stop-instances'],
    'swf': ['deprecate-domain', 'describe-domain'],
    'sqs': ['create-queue', 'get-queue-attributes'],
    'emr': ['add-steps', 'create-default-roles', 'describe-cluster', 'schedule-hbase-backup'],
    'opsworks': ['register'],
}


class _ExampleTests(BaseAWSHelpOutputTest):
    def noop_test(self):
        pass


def test_examples():
    for command, subcommands in COMMAND_EXAMPLES.items():
        for subcommand in subcommands:
            yield verify_has_examples, command, subcommand


def test_all_examples_have_only_ascii():
    # Verify that all the example *.rst file contain ascii only characters.
    # Otherwise this will break downstream doc generation.
    _dname = os.path.dirname
    examples_dir = os.path.join(
        _dname(_dname(_dname(_dname(os.path.abspath(__file__))))),
        'awscli', 'examples')
    for rootdir, _, filenames in os.walk(examples_dir):
        for filename in filenames:
            if not filename.endswith('.rst'):
                continue
            full_path = os.path.join(rootdir, filename)
            yield verify_has_only_ascii_chars, full_path


def verify_has_only_ascii_chars(filename):
    with open(filename, 'rb') as f:
        bytes_content = f.read()
        try:
            bytes_content.decode('ascii')
        except UnicodeDecodeError as e:
            # The test has failed so we'll try to provide a useful error
            # message.
            offset = e.start
            spread = 20
            bad_text = bytes_content[offset-spread:e.start+spread]
            underlined = ' ' * spread + '^'
            error_text = '\n'.join([bad_text, underlined])
            line_number = bytes_content[:offset].count(b'\n') + 1
            raise AssertionError(
                "Non ascii characters found in the examples file %s, line %s:"
                "\n\n%s\n" % (filename, line_number, error_text))



def verify_has_examples(command, subcommand):
    t = _ExampleTests(methodName='noop_test')
    t.setUp()
    try:
        t.driver.main([command, subcommand, 'help'])
        t.assert_contains_with_count('========\nExamples\n========', 1)
    finally:
        t.tearDown()
