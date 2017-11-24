# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from nose.tools import assert_equal
from botocore.compat import six

from awscli.compat import ensure_text_type
from awscli.compat import compat_shell_quote
from awscli.compat import is_windows
from awscli.compat import get_popen_pager_cmd_with_kwargs
from awscli.testutils import mock, unittest


class TestEnsureText(unittest.TestCase):
    def test_string(self):
        value = 'foo'
        response = ensure_text_type(value)
        self.assertIsInstance(response, six.text_type)
        self.assertEqual(response, 'foo')

    def test_binary(self):
        value = b'bar'
        response = ensure_text_type(value)
        self.assertIsInstance(response, six.text_type)
        self.assertEqual(response, 'bar')

    def test_unicode(self):
        value = u'baz'
        response = ensure_text_type(value)
        self.assertIsInstance(response, six.text_type)
        self.assertEqual(response, 'baz')

    def test_non_ascii(self):
        value = b'\xe2\x9c\x93'
        response = ensure_text_type(value)
        self.assertIsInstance(response, six.text_type)
        self.assertEqual(response, u'\u2713')

    def test_non_string_or_bytes_raises_error(self):
        value = 500
        with self.assertRaises(ValueError):
            ensure_text_type(value)


def test_compat_shell_quote_windows():
    windows_cases = {
        '': '""',
        '"': '\\"',
        '\\': '\\',
        '\\a': '\\a',
        '\\\\': '\\\\',
        '\\"': '\\\\\\"',
        '\\\\"': '\\\\\\\\\\"',
        'foo bar': '"foo bar"',
        'foo\tbar': '"foo\tbar"',
    }
    for input_string, expected_output in windows_cases.items():
        yield ShellQuoteTestCase().run, input_string, expected_output, "win32"


def test_comat_shell_quote_unix():
    unix_cases = {
        "": "''",
        "*": "'*'",
        "foo": "foo",
        "foo bar": "'foo bar'",
        "foo\tbar": "'foo\tbar'",
        "foo\nbar": "'foo\nbar'",
        "foo'bar": "'foo'\"'\"'bar'",
    }
    for input_string, expected_output in unix_cases.items():
        yield ShellQuoteTestCase().run, input_string, expected_output, "linux2"
        yield ShellQuoteTestCase().run, input_string, expected_output, "darwin"


class ShellQuoteTestCase(object):
    def run(self, s, expected, platform=None):
        assert_equal(compat_shell_quote(s, platform), expected)


class TestIsWindows(unittest.TestCase):
    @mock.patch('os.name', 'nt')
    def test_is_windows(self):
        self.assertTrue(is_windows())

    @mock.patch('os.name', 'posix')
    def test_is_non_windows(self):
        self.assertFalse(is_windows())


class TestGetPopenPagerCmd(unittest.TestCase):
    @mock.patch('os.name', 'nt')
    def test_windows(self):
        popen_cmd, kwargs = get_popen_pager_cmd_with_kwargs()
        self.assertEqual('more', popen_cmd)
        self.assertEqual({'shell': True}, kwargs)

    @mock.patch('os.name', 'nt')
    def test_windows_with_specific_pager(self):
        popen_cmd, kwargs = get_popen_pager_cmd_with_kwargs('less -R')
        self.assertEqual('less -R', popen_cmd)
        self.assertEqual({'shell': True}, kwargs)

    @mock.patch('os.name', 'posix')
    def test_non_windows(self):
        popen_cmd, kwargs = get_popen_pager_cmd_with_kwargs()
        self.assertEqual(['less', '-R'], popen_cmd)
        self.assertEqual({}, kwargs)

    @mock.patch('os.name', 'posix')
    def test_non_windows_specific_pager(self):
        popen_cmd, kwargs = get_popen_pager_cmd_with_kwargs('more')
        self.assertEqual(['more'], popen_cmd)
        self.assertEqual({}, kwargs)
