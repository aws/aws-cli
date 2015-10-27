# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.customizations import argrename
from awscli.customizations import arguments

from botocore import model


class TestArgumenManipulations(unittest.TestCase):
    def setUp(self):
        self.argument_table = {}

    def test_can_rename_argument(self):
        arg = arguments.CustomArgument('foo')
        self.argument_table['foo'] = arg
        handler = argrename.rename_arg('foo', 'bar')
        handler(self.argument_table)

        self.assertIn('bar', self.argument_table)
        self.assertNotIn('foo', self.argument_table)
        self.assertEqual(arg.name, 'bar')

    def test_can_alias_an_argument(self):
        arg = arguments.CustomArgument(
            'foo', dest='foo',
            argument_model=model.Shape('FooArg', {'type': 'string'}))
        self.argument_table['foo'] = arg
        handler = argrename.hidden_alias('foo', 'alias-name')

        handler(self.argument_table)

        self.assertIn('alias-name', self.argument_table)
        self.assertIn('foo', self.argument_table)
        self.assertEqual(self.argument_table['alias-name'].name, 'alias-name')
