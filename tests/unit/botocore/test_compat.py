# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import datetime

import pytest

from botocore.compat import (
    HAS_CRT,
    compat_shell_split,
    ensure_bytes,
    get_md5,
    get_tzinfo_options,
    total_seconds,
    unquote_str,
)
from botocore.exceptions import MD5UnavailableError
from tests import BaseEnvVar, mock, unittest


class TotalSecondsTest(BaseEnvVar):
    def test_total_seconds(self):
        delta = datetime.timedelta(days=1, seconds=45)
        remaining = total_seconds(delta)
        self.assertEqual(remaining, 86445.0)

        delta = datetime.timedelta(seconds=33, microseconds=772)
        remaining = total_seconds(delta)
        self.assertEqual(remaining, 33.000772)


class TestUnquoteStr(unittest.TestCase):
    def test_unquote_str(self):
        value = '%E2%9C%93'
        # Note: decoded to unicode and utf-8 decoded as well.
        # This would work in python2 and python3.
        self.assertEqual(unquote_str(value), '\u2713')

    def test_unquote_normal(self):
        value = 'foo'
        # Note: decoded to unicode and utf-8 decoded as well.
        # This would work in python2 and python3.
        self.assertEqual(unquote_str(value), 'foo')

    def test_unquote_with_spaces(self):
        value = 'foo+bar'
        # Note: decoded to unicode and utf-8 decoded as well.
        # This would work in python2 and python3.
        self.assertEqual(unquote_str(value), 'foo bar')


class TestEnsureBytes(unittest.TestCase):
    def test_string(self):
        value = 'foo'
        response = ensure_bytes(value)
        self.assertIsInstance(response, bytes)
        self.assertEqual(response, b'foo')

    def test_binary(self):
        value = b'bar'
        response = ensure_bytes(value)
        self.assertIsInstance(response, bytes)
        self.assertEqual(response, b'bar')

    def test_unicode(self):
        value = 'baz'
        response = ensure_bytes(value)
        self.assertIsInstance(response, bytes)
        self.assertEqual(response, b'baz')

    def test_non_ascii(self):
        value = '\u2713'
        response = ensure_bytes(value)
        self.assertIsInstance(response, bytes)
        self.assertEqual(response, b'\xe2\x9c\x93')

    def test_non_string_or_bytes_raises_error(self):
        value = 500
        with self.assertRaises(ValueError):
            ensure_bytes(value)


class TestGetMD5(unittest.TestCase):
    def test_available(self):
        md5 = mock.Mock()
        with mock.patch('botocore.compat.MD5_AVAILABLE', True):
            with mock.patch('hashlib.md5', mock.Mock(return_value=md5)):
                self.assertEqual(get_md5(), md5)

    def test_unavailable_raises_error(self):
        with mock.patch('botocore.compat.MD5_AVAILABLE', False):
            with self.assertRaises(MD5UnavailableError):
                get_md5()


@pytest.fixture
def shell_split_runner():
    # Single runner fixture for all tests
    return ShellSplitTestRunner()


def get_windows_test_cases():
    windows_cases = {
        r'': [],
        r'spam \\': [r'spam', '\\\\'],
        r'spam ': [r'spam'],
        r' spam': [r'spam'],
        'spam eggs': [r'spam', r'eggs'],
        'spam\teggs': [r'spam', r'eggs'],
        'spam\neggs': ['spam\neggs'],
        '""': [''],
        '" "': [' '],
        '"\t"': ['\t'],
        '\\\\': ['\\\\'],
        '\\\\ ': ['\\\\'],
        '\\\\\t': ['\\\\'],
        r'\"': ['"'],
        # The following four test cases are official test cases given in
        # Microsoft's documentation.
        r'"abc" d e': [r'abc', r'd', r'e'],
        r'a\\b d"e f"g h': [r'a\\b', r'de fg', r'h'],
        r'a\\\"b c d': [r'a\"b', r'c', r'd'],
        r'a\\\\"b c" d e': [r'a\\b c', r'd', r'e'],
    }
    return windows_cases.items()


@pytest.mark.parametrize(
    "input_string, expected_output", get_windows_test_cases()
)
def test_compat_shell_split_windows(
    shell_split_runner, input_string, expected_output
):
    shell_split_runner.assert_equal(input_string, expected_output, "win32")


def test_compat_shell_split_windows_raises_error(shell_split_runner):
    shell_split_runner.assert_raises(r'"', ValueError, "win32")


def get_unix_test_cases():
    unix_cases = {
        r'': [],
        r'spam \\': [r'spam', '\\'],
        r'spam ': [r'spam'],
        r' spam': [r'spam'],
        'spam eggs': [r'spam', r'eggs'],
        'spam\teggs': [r'spam', r'eggs'],
        'spam\neggs': ['spam', 'eggs'],
        '""': [''],
        '" "': [' '],
        '"\t"': ['\t'],
        '\\\\': ['\\'],
        '\\\\ ': ['\\'],
        '\\\\\t': ['\\'],
        r'\"': ['"'],
        # The following four test cases are official test cases given in
        # Microsoft's documentation, but adapted to unix shell splitting.
        r'"abc" d e': [r'abc', r'd', r'e'],
        r'a\\b d"e f"g h': [r'a\b', r'de fg', r'h'],
        r'a\\\"b c d': [r'a\"b', r'c', r'd'],
        r'a\\\\"b c" d e': [r'a\\b c', r'd', r'e'],
    }
    return unix_cases.items()


@pytest.mark.parametrize(
    "input_string, expected_output", get_unix_test_cases()
)
def test_compat_shell_split_unix_linux2(
    shell_split_runner, input_string, expected_output
):
    shell_split_runner.assert_equal(input_string, expected_output, "linux2")


@pytest.mark.parametrize(
    "input_string, expected_output", get_unix_test_cases()
)
def test_compat_shell_split_unix_darwin(
    shell_split_runner, input_string, expected_output
):
    shell_split_runner.assert_equal(input_string, expected_output, "darwin")


def test_compat_shell_split_unix_linux2_raises_error(shell_split_runner):
    shell_split_runner.assert_raises(r'"', ValueError, "linux2")


def test_compat_shell_split_unix_darwin_raises_error(shell_split_runner):
    shell_split_runner.assert_raises(r'"', ValueError, "darwin")


class ShellSplitTestRunner:
    def assert_equal(self, s, expected, platform):
        assert compat_shell_split(s, platform) == expected

    def assert_raises(self, s, exception_cls, platform):
        with pytest.raises(exception_cls):
            compat_shell_split(s, platform)


class TestTimezoneOperations(unittest.TestCase):
    def test_get_tzinfo_options(self):
        options = get_tzinfo_options()
        self.assertTrue(len(options) > 0)

        for tzinfo in options:
            self.assertIsInstance(tzinfo(), datetime.tzinfo)


class TestCRTIntegration(unittest.TestCase):
    def test_has_crt_global(self):
        try:
            import awscrt.auth  # noqa

            assert HAS_CRT
        except ImportError:
            assert not HAS_CRT
