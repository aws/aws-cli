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
from awscli.testutils import unittest
import mock

from awscli.customizations.commands import BasicHelp, BasicCommand


class TestCommandLoader(unittest.TestCase):

    def test_basic_help_with_contents(self):
        cmd_object = mock.Mock()
        mock_module = mock.Mock()
        mock_module.__file__ = '/some/root'
        cmd_object.DESCRIPTION = BasicCommand.FROM_FILE(
            'foo', 'bar', 'baz.txt', root_module=mock_module)
        help_command = BasicHelp(mock.Mock(), cmd_object, {}, {})
        with mock.patch('awscli.customizations.commands._open') as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = \
                    'fake description'
            self.assertEqual(help_command.description, 'fake description')
