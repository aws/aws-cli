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
from awscli.testutils import unittest
from awscli.testutils import BaseAWSHelpOutputTest

import mock

from awscli.customizations import utils


class FakeParsedArgs(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class TestCommandTableRenames(BaseAWSHelpOutputTest):

    def test_rename_command_table(self):
        handler = lambda command_table, **kwargs: utils.rename_command(
            command_table, 'ec2', 'fooec2')
        # Verify that we can rename a top level command.
        self.session.register('building-command-table.main', handler)
        self.driver.main(['fooec2', 'help'])
        self.assert_contains('fooec2')

        # We can also see subcommands help as well.
        self.driver.main(['fooec2', 'run-instances', 'help'])
        self.assert_contains('run-instances')


class TestValidateMututuallyExclusiveGroups(unittest.TestCase):
    def test_two_single_groups(self):
        # The most basic example of mutually exclusive args.
        # If foo is specified, but bar is not, then we're fine.
        parsed = FakeParsedArgs(foo='one', bar=None)
        utils.validate_mutually_exclusive(parsed, ['foo'], ['bar'])
        # If bar is specified and foo is not, then we're fine.
        parsed = FakeParsedArgs(foo=None, bar='one')
        utils.validate_mutually_exclusive(parsed, ['foo'], ['bar'])
        # But if we specify both foo and bar then we get an error.
        parsed = FakeParsedArgs(foo='one', bar='two')
        with self.assertRaises(ValueError):
            utils.validate_mutually_exclusive(parsed, ['foo'], ['bar'])


    def test_multiple_groups(self):
        groups = (['one', 'two', 'three'], ['foo', 'bar', 'baz'],
                  ['qux', 'bad', 'morebad'])
        # This is fine.
        parsed = FakeParsedArgs(foo='foo', bar='bar', baz='baz')
        utils.validate_mutually_exclusive(parsed, *groups)
        # But this is bad.
        parsed = FakeParsedArgs(foo='one', bar=None, qux='three')
        with self.assertRaises(ValueError):
            utils.validate_mutually_exclusive(parsed, *groups)
