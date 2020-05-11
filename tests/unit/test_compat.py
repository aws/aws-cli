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
import locale
import os
import signal

from nose.tools import assert_equal
from botocore.compat import six

from awscli.compat import ensure_text_type
from awscli.compat import compat_shell_quote
from awscli.compat import get_popen_kwargs_for_pager_cmd
from awscli.compat import getpreferredencoding
from awscli.compat import ignore_user_entered_signals
from awscli.testutils import mock, unittest, skip_if_windows


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


class TestGetPopenPagerCmd(unittest.TestCase):
    @mock.patch('awscli.compat.is_windows', True)
    @mock.patch('awscli.compat.default_pager', 'more')
    def test_windows(self):
        kwargs = get_popen_kwargs_for_pager_cmd()
        self.assertEqual({'args': 'more', 'shell': True}, kwargs)

    @mock.patch('awscli.compat.is_windows', True)
    @mock.patch('awscli.compat.default_pager', 'more')
    def test_windows_with_specific_pager(self):
        kwargs = get_popen_kwargs_for_pager_cmd('less -R')
        self.assertEqual({'args': 'less -R', 'shell': True}, kwargs)

    @mock.patch('awscli.compat.is_windows', False)
    @mock.patch('awscli.compat.default_pager', 'less -R')
    def test_non_windows(self):
        kwargs = get_popen_kwargs_for_pager_cmd()
        self.assertEqual({'args': ['less', '-R']}, kwargs)

    @mock.patch('awscli.compat.is_windows', False)
    @mock.patch('awscli.compat.default_pager', 'less -R')
    def test_non_windows_specific_pager(self):
        kwargs = get_popen_kwargs_for_pager_cmd('more')
        self.assertEqual({'args': ['more']}, kwargs)


class TestIgnoreUserSignals(unittest.TestCase):
    @skip_if_windows("These signals are not supported for windows")
    def test_ignore_signal_sigint(self):
        with ignore_user_entered_signals():
            try:
                os.kill(os.getpid(), signal.SIGINT)
            except KeyboardInterrupt:
                self.fail('The ignore_user_entered_signals context '
                          'manager should have ignored')

    @skip_if_windows("These signals are not supported for windows")
    def test_ignore_signal_sigquit(self):
        with ignore_user_entered_signals():
            self.assertEqual(signal.getsignal(signal.SIGQUIT), signal.SIG_IGN)
            os.kill(os.getpid(), signal.SIGQUIT)

    @skip_if_windows("These signals are not supported for windows")
    def test_ignore_signal_sigtstp(self):
        with ignore_user_entered_signals():
            self.assertEqual(signal.getsignal(signal.SIGTSTP), signal.SIG_IGN)
            os.kill(os.getpid(), signal.SIGTSTP)


class TestGetPreferredEncoding(unittest.TestCase):

    @mock.patch.dict(os.environ, {'AWS_CLI_FILE_ENCODING': 'cp1252'})
    def test_getpreferredencoding_with_env_var(self):
        encoding = getpreferredencoding()
        self.assertEqual(encoding, 'cp1252')

    def test_getpreferredencoding_wo_env_var(self):
        encoding = getpreferredencoding()
        self.assertEqual(encoding, locale.getpreferredencoding())
