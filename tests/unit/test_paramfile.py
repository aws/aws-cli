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
from awscli.testutils import mock, unittest, FileCreator
from awscli.testutils import skip_if_windows

from awscli.paramfile import (
    get_paramfile,
    ResourceLoadingError,
    LOCAL_PREFIX_MAP,
    REMOTE_PREFIX_MAP,
    register_uri_param_handler,
)
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
        self.assertIsInstance(data, str)

    def test_binary_file(self):
        contents = 'This is a test'
        filename = self.files.create_file('foo', contents)
        prefixed_filename = 'fileb://' + filename
        data = self.get_paramfile(prefixed_filename)
        self.assertEqual(data, b'This is a test')
        self.assertIsInstance(data, bytes)

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


class TestHTTPBasedResourceLoading(unittest.TestCase):
    def setUp(self):
        self.session_patch = mock.patch('awscli.paramfile.URLLib3Session.send')
        self.session_mock = self.session_patch.start()
        self.response = mock.Mock(status_code=200)
        self.session_mock.return_value = self.response

    def tearDown(self):
        self.session_patch.stop()

    def get_paramfile(self, path):
        return get_paramfile(path, REMOTE_PREFIX_MAP.copy())

    def test_resource_from_http(self):
        self.response.text = 'http contents'
        loaded = self.get_paramfile('http://foo.bar.baz')
        self.assertEqual(loaded, 'http contents')

    def test_resource_from_https(self):
        self.response.text = 'http contents'
        loaded = self.get_paramfile('https://foo.bar.baz')
        self.assertEqual(loaded, 'http contents')

    def test_non_200_raises_error(self):
        self.response.status_code = 500
        with self.assertRaisesRegex(ResourceLoadingError, 'foo\.bar\.baz'):
            self.get_paramfile('https://foo.bar.baz')

    def test_connection_error_raises_error(self):
        self.session_mock.side_effect = Exception("Connection error.")
        with self.assertRaisesRegex(ResourceLoadingError, 'foo\.bar\.baz'):
            self.get_paramfile('https://foo.bar.baz')


class TestConfigureURIArgumentHandler(unittest.TestCase):
    @mock.patch('awscli.paramfile.URIArgumentHandler')
    def test_profile_not_found(self, mock_handler_cls):
        session = mock.Mock(spec=Session)
        session.get_scoped_config.side_effect = ProfileNotFound(profile='foo')

        register_uri_param_handler(session)
        cases = mock_handler_cls.call_args[0][0]

        self.assertIn('file://', cases)
        self.assertIn('fileb://', cases)
        self.assertIn('http://', cases)
        self.assertIn('http://', cases)

    @mock.patch('awscli.paramfile.URIArgumentHandler')
    def test_missing_config_value(self, mock_handler_cls):
        session = mock.Mock(spec=Session)
        session.get_scoped_config.return_value = {}

        register_uri_param_handler(session)
        cases = mock_handler_cls.call_args[0][0]

        self.assertIn('file://', cases)
        self.assertIn('fileb://', cases)
        self.assertIn('http://', cases)
        self.assertIn('http://', cases)

    @mock.patch('awscli.paramfile.URIArgumentHandler')
    def test_config_value_true(self, mock_handler_cls):
        session = mock.Mock(spec=Session)
        session.get_scoped_config.return_value = {
            'cli_follow_urlparam': 'true'}

        register_uri_param_handler(session)
        cases = mock_handler_cls.call_args[0][0]

        self.assertIn('file://', cases)
        self.assertIn('fileb://', cases)
        self.assertIn('http://', cases)
        self.assertIn('http://', cases)

    @mock.patch('awscli.paramfile.URIArgumentHandler')
    def test_config_value_false(self, mock_handler_cls):
        session = mock.Mock(spec=Session)
        session.get_scoped_config.return_value = {
            'cli_follow_urlparam': 'false'}

        register_uri_param_handler(session)
        cases = mock_handler_cls.call_args[0][0]

        self.assertIn('file://', cases)
        self.assertIn('fileb://', cases)
        self.assertNotIn('http://', cases)
        self.assertNotIn('http://', cases)
