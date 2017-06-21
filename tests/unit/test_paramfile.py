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
import platform

import locale
import mock
from awscli.compat import six
from awscli.testutils import unittest, FileCreator
from awscli.testutils import skip_if_windows

from awscli.paramfile import get_paramfile, get_file, ResourceLoadingError


class TestParamFile(unittest.TestCase):
    def setUp(self):
        self.files = FileCreator()

    def tearDown(self):
        self.files.remove_all()

    def test_text_file(self):
        contents = 'This is a test'
        filename = self.files.create_file('foo', contents)
        prefixed_filename = 'file://' + filename
        data = get_paramfile(prefixed_filename)
        self.assertEqual(data, contents)
        self.assertIsInstance(data, six.string_types)

    def test_binary_file(self):
        contents = 'This is a test'
        filename = self.files.create_file('foo', contents)
        prefixed_filename = 'fileb://' + filename
        data = get_paramfile(prefixed_filename)
        self.assertEqual(data, b'This is a test')
        self.assertIsInstance(data, six.binary_type)

    @skip_if_windows('Binary content error only occurs '
                     'on non-Windows platforms.')
    def test_cannot_load_text_file(self):
        contents = b'\xbfX\xac\xbe'
        filename = self.files.create_file('foo', contents, mode='wb')
        prefixed_filename = 'file://' + filename
        with self.assertRaises(ResourceLoadingError):
            get_paramfile(prefixed_filename)

    def test_file_does_not_exist_raises_error(self):
        with self.assertRaises(ResourceLoadingError):
            get_paramfile('file://file/does/not/existsasdf.txt')

    def test_no_match_uris_returns_none(self):
        self.assertIsNone(get_paramfile('foobar://somewhere.bar'))

    def test_non_string_type_returns_none(self):
        self.assertIsNone(get_paramfile(100))

    def test_get_file_utf8_text(self):
        contents = b'\xe9\x96\xa2\xe6\x88\xb8\xe3\x81\xa6\xe3\x81\x99\xe3\x81\xa8'
        filename = self.files.create_file('foo', contents, mode='wb')
        data = get_file('', filename, 'r')
        self.assertEqual(data, u'\u95a2\u6238\u3066\u3059\u3068')
        self.assertIsInstance(data, six.string_types)

    @unittest.skipIf(locale.getpreferredencoding() != 'cp932',
            'encoding fallback test with cp932 system')
    def test_get_file_fallback_platformdefault_in_cp932(self):
        contents = b'\x8a\xd6\x8c\xcb\x82\xc4\x82\xb7\x82\xc6'
        filename = self.files.create_file('foo', contents, mode='wb')
        data = get_file('', filename, 'r')
        self.assertEqual(data, u'\u95a2\u6238\u3066\u3059\u3068')
        self.assertIsInstance(data, six.string_types)


class TestHTTPBasedResourceLoading(unittest.TestCase):
    def setUp(self):
        self.requests_patch = mock.patch('awscli.paramfile.requests')
        self.requests_mock = self.requests_patch.start()
        self.response = mock.Mock(status_code=200)
        self.requests_mock.get.return_value = self.response

    def tearDown(self):
        self.requests_patch.stop()

    def test_resource_from_http(self):
        self.response.text = 'http contents'
        loaded = get_paramfile('http://foo.bar.baz')
        self.assertEqual(loaded, 'http contents')
        self.requests_mock.get.assert_called_with('http://foo.bar.baz')

    def test_resource_from_https(self):
        self.response.text = 'http contents'
        loaded = get_paramfile('https://foo.bar.baz')
        self.assertEqual(loaded, 'http contents')
        self.requests_mock.get.assert_called_with('https://foo.bar.baz')

    def test_non_200_raises_error(self):
        self.response.status_code = 500
        with self.assertRaisesRegexp(ResourceLoadingError, 'foo\.bar\.baz'):
            get_paramfile('https://foo.bar.baz')

    def test_connection_error_raises_error(self):
        self.requests_mock.get.side_effect = Exception("Connection error.")
        with self.assertRaisesRegexp(ResourceLoadingError, 'foo\.bar\.baz'):
            get_paramfile('https://foo.bar.baz')
