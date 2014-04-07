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
from tests import unittest
from awscli import arguments

from mock import Mock, patch, mock_open


class DemoArgument(arguments.CustomArgument):
    def add_to_params(self, params, value):
        params[self.py_name] = value


class TestArgumentClasses(unittest.TestCase):
    def test_can_set_required(self):
        arg = DemoArgument('test-arg')
        self.assertFalse(arg.required)
        arg.required = True
        self.assertTrue(arg.required)

    @patch('os.path.isfile', Mock(return_value=True))
    def test_with_paramfile(self):
        arg = DemoArgument('test-arg')
        params = {}

        m = mock_open(read_data='{"hello": "world"}')
        with patch('__builtin__.open', m, create=True) as open_mock:
            arg.add_to_params_preprocess(params, 'file:///tmp/foo.json')

        open_mock.assert_called_with('/tmp/foo.json')
        self.assertEqual({'hello': 'world'}, params['test_arg'])

    def test_no_paramfile(self):
        arg = DemoArgument('test-arg', no_paramfile=True)
        params = {}

        arg.add_to_params_preprocess(params, 'file:///tmp/foo.json')

        self.assertEqual('file:///tmp/foo.json', params['test_arg'])
