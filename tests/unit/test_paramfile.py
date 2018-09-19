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
import mock
from awscli.compat import six
from awscli.testutils import unittest, FileCreator
from awscli.testutils import skip_if_windows

from awscli.paramfile import get_paramfile, ResourceLoadingError
from awscli.paramfile import LOCAL_PREFIX_MAP
from awscli.paramfile import register_uri_param_handler
from botocore.session import Session
from botocore.exceptions import ProfileNotFound


class TestParamFile(unittest.TestCase):
    def setUp(self):
        self.files = FileCreator()

    def tearDown(self):
        self.files.remove_all()

    def get_paramfile(self, path):
        return get_paramfile(path, LOCAL_PREFIX_MAP.copy())

    def test_text_file(self):
        contents = 'This is a test'
        filename = self.files.create_file('foo', contents)
        prefixed_filename = 'file://' + filename
        data = self.get_paramfile(prefixed_filename)
        self.assertEqual(data, contents)
        self.assertIsInstance(data, six.string_types)

    def test_binary_file(self):
        contents = 'This is a test'
        filename = self.files.create_file('foo', contents)
        prefixed_filename = 'fileb://' + filename
        data = self.get_paramfile(prefixed_filename)
        self.assertEqual(data, b'This is a test')
        self.assertIsInstance(data, six.binary_type)

    @skip_if_windows('Binary content error only occurs '
                     'on non-Windows platforms.')
    def test_cannot_load_text_file(self):
        contents = b'\xbfX\xac\xbe'
        filename = self.files.create_file('foo', contents, mode='wb')
        prefixed_filename = 'file://' + filename
        with self.assertRaises(ResourceLoadingError):
            self.get_paramfile(prefixed_filename)

    def test_file_does_not_exist_raises_error(self):
        with self.assertRaises(ResourceLoadingError):
            self.get_paramfile('file://file/does/not/existsasdf.txt')

    def test_no_match_uris_returns_none(self):
        self.assertIsNone(self.get_paramfile('foobar://somewhere.bar'))

    def test_non_string_type_returns_none(self):
        self.assertIsNone(self.get_paramfile(100))


class TestConfigureURIArgumentHandler(unittest.TestCase):

    @mock.patch('awscli.paramfile.URIArgumentHandler')
    def test_default_prefix_maps(self, mock_handler_cls):
        session = mock.Mock(spec=Session)
        session.get_scoped_config.return_value = {}

        register_uri_param_handler(session)
        cases = mock_handler_cls.call_args[0][0]

        self.assertIn('file://', cases)
        self.assertIn('fileb://', cases)
