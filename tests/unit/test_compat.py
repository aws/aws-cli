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
import os
import signal

import pytest

from awscli.compat import ensure_text_type
from awscli.compat import compat_shell_quote
from awscli.compat import compat_open
from awscli.compat import get_popen_kwargs_for_pager_cmd
from awscli.compat import ignore_user_entered_signals
from awscli.testutils import mock, unittest, skip_if_windows, FileCreator


class TestEnsureText(unittest.TestCase):
    def test_string(self):
        value = 'foo'
        response = ensure_text_type(value)
        self.assertIsInstance(response, str)
        self.assertEqual(response, 'foo')

    def test_binary(self):
        value = b'bar'
        response = ensure_text_type(value)
        self.assertIsInstance(response, str)
        self.assertEqual(response, 'bar')

    def test_unicode(self):
        value = u'baz'
        response = ensure_text_type(value)
        self.assertIsInstance(response, str)
        self.assertEqual(response, 'baz')

    def test_non_ascii(self):
        value = b'\xe2\x9c\x93'
        response = ensure_text_type(value)
        self.assertIsInstance(response, str)
        self.assertEqual(response, u'\u2713')

    def test_non_string_or_bytes_raises_error(self):
        value = 500
        with self.assertRaises(ValueError):
            ensure_text_type(value)


@pytest.mark.parametrize(
    "input_string, expected_output",
    (
        ('', '""'),
        ('"', '\\"'),
        ('\\', '\\'),
        ('\\a', '\\a'),
        ('\\\\', '\\\\'),
        ('\\"', '\\\\\\"'),
        ('\\\\"', '\\\\\\\\\\"'),
        ('foo bar', '"foo bar"'),
        ('foo\tbar', '"foo\tbar"'),
    )
)
def test_compat_shell_quote_windows(input_string, expected_output):
    assert compat_shell_quote(input_string, "win32") == expected_output


@pytest.mark.parametrize(
    "input_string, expected_output",
    (
        ('', "''"),
        ('*', "'*'"),
        ('foo', 'foo'),
        ('foo bar', "'foo bar'"),
        ('foo\tbar', "'foo\tbar'"),
        ('foo\nbar', "'foo\nbar'"),
        ("foo'bar", '\'foo\'"\'"\'bar\'')
    )
)
def test_comat_shell_quote_linux(input_string, expected_output):
    assert compat_shell_quote(input_string, "linux2") == expected_output


@pytest.mark.parametrize(
    "input_string, expected_output",
    (
        ('', "''"),
        ('*', "'*'"),
        ('foo', 'foo'),
        ('foo bar', "'foo bar'"),
        ('foo\tbar', "'foo\tbar'"),
        ('foo\nbar', "'foo\nbar'"),
        ("foo'bar", '\'foo\'"\'"\'bar\'')
    )
)
def test_comat_shell_quote_darwin(input_string, expected_output):
    assert compat_shell_quote(input_string, "darwin") == expected_output


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


class TestCompatOpenWithAccessPermissions(unittest.TestCase):
    def setUp(self):
        self.files = FileCreator()

    def tearDown(self):
        self.files.remove_all()

    @skip_if_windows('Permissions tests only supported on mac/linux')
    def test_can_create_file_with_acess_permissions(self):
        file_path = os.path.join(self.files.rootdir, "foo_600.txt")
        with compat_open(file_path, access_permissions=0o600, mode='w') as f:
            f.write('bar')
        self.assertEqual(os.stat(file_path).st_mode & 0o777, 0o600)

    def test_not_override_existing_file_access_permissions(self):
        file_path = os.path.join(self.files.rootdir, "foo.txt")
        with open(file_path, mode='w') as f:
            f.write('bar')
        expected_st_mode = os.stat(file_path).st_mode

        with compat_open(file_path, access_permissions=0o600, mode='w') as f:
            f.write('bar')
        self.assertEqual(os.stat(file_path).st_mode, expected_st_mode)
