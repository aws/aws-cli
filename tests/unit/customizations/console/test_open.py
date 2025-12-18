# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import unittest
import webbrowser
from io import StringIO

from awscli.testutils import mock

from awscli.customizations.console.open import OpenConsoleCommand


class TestOpenConsoleCommand(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.command = OpenConsoleCommand(self.session)
        self.parsed_args = mock.Mock()
        self.parsed_globals = mock.Mock()

    @mock.patch('awscli.customizations.console.open.webbrowser.open_new_tab')
    def test_opens_console_url_successfully(self, mock_open_browser):
        """Test that the command opens the AWS console URL in browser."""
        mock_open_browser.return_value = True

        result = self.command._run_main(self.parsed_args, self.parsed_globals)

        mock_open_browser.assert_called_once_with(
            'https://console.aws.amazon.com/')
        self.assertEqual(result, 0)

    @mock.patch('awscli.customizations.console.open.webbrowser.open_new_tab')
    @mock.patch('sys.stderr', new_callable=StringIO)
    def test_handles_browser_error(self, mock_stderr, mock_open_browser):
        """Test that the command handles browser opening errors gracefully."""
        mock_open_browser.side_effect = webbrowser.Error(
            'Browser not available')

        result = self.command._run_main(self.parsed_args, self.parsed_globals)

        mock_open_browser.assert_called_once_with(
            'https://console.aws.amazon.com/')
        self.assertEqual(result, 1)
        error_output = mock_stderr.getvalue()
        self.assertIn('Failed to open browser', error_output)
        self.assertIn('https://console.aws.amazon.com/', error_output)

    def test_command_name(self):
        """Test that the command has the correct name."""
        self.assertEqual(self.command.NAME, 'console')

    def test_command_description(self):
        """Test that the command has a description."""
        self.assertIn('AWS Management Console', self.command.DESCRIPTION)
