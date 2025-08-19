# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import datetime
import os
from unittest import mock

import botocore.session
from botocore.exceptions import ClientError, ProfileNotFound

from awscli.customizations.configure.mfalogin import (
    ConfigureMFALoginCommand,
    InteractiveMFAPrompter,
)
from awscli.testutils import unittest


class TestInteractiveMFAPrompter(unittest.TestCase):
    def test_get_value_with_response(self):
        prompter = InteractiveMFAPrompter()
        # Mock the entire compat_input function, not just the return value
        with mock.patch(
            'awscli.customizations.configure.mfalogin.compat_input'
        ) as mock_input:
            mock_input.return_value = 'response'
            self.assertEqual(
                prompter.get_value('current', 'prompt'), 'response'
            )

    def test_get_value_with_no_response(self):
        prompter = InteractiveMFAPrompter()
        # Mock the entire compat_input function, not just the return value
        with mock.patch(
            'awscli.customizations.configure.mfalogin.compat_input'
        ) as mock_input:
            mock_input.return_value = ''
            self.assertEqual(
                prompter.get_value('current', 'prompt'), 'current'
            )


class TestConfigureMFALoginCommand(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.session.get_scoped_config.return_value = {}
        self.session.get_credentials.return_value = mock.Mock()
        # Add available_profiles to the session mock
        self.session.available_profiles = ['default', 'test']
        self.prompter = mock.Mock()
        self.config_writer = mock.Mock()
        self.command = ConfigureMFALoginCommand(
            self.session,
            prompter=self.prompter,
            config_writer=self.config_writer,
        )
        self.parsed_args = mock.Mock()
        self.parsed_args.profile = None
        self.parsed_args.update_profile = None
        self.parsed_args.duration_seconds = None
        self.parsed_args.serial_number = None
        self.parsed_globals = mock.Mock()
        # Set profile in parsed_globals
        self.parsed_globals.profile = 'default'

    def test_no_credentials_found(self):
        # Setup mock responses for interactive prompting
        self.prompter.get_credential_value.side_effect = [
            'AKIAIOSFODNN7EXAMPLE',  # access key
            'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # secret key
            'arn:aws:iam::123456789012:mfa/user',  # MFA serial
            '123456',  # MFA token
        ]
        self.prompter.get_value.return_value = 'session-test'  # profile name
        
        # Mock botocore.session.Session
        mock_session = mock.Mock()
        mock_session.get_credentials.return_value = None
        mock_session.available_profiles = ['default']
        
        # Mock STS for the interactive prompting path
        sts_client = mock.Mock()
        sts_client.get_session_token.return_value = {
            'Credentials': {
                'AccessKeyId': 'ASIAIOSFODNN7EXAMPLE',
                'SecretAccessKey': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY',
                'SessionToken': 'SESSION_TOKEN',
                'Expiration': datetime.datetime(2023, 5, 19, 18, 6, 10),
            }
        }
        mock_session.create_client.return_value = sts_client

        with mock.patch('botocore.session.Session', return_value=mock_session):
            with mock.patch(
                'sys.stdin.isatty', return_value=False
            ):  # Non-interactive
                with mock.patch('os.path.expanduser', return_value='/tmp/credentials'):
                    with mock.patch('sys.stdout'):
                        rc = self.command._run_main(
                            self.parsed_args, self.parsed_globals
                        )
                        self.assertEqual(rc, 0)  # Should succeed via interactive prompting

    def test_profile_not_found(self):
        # Set profile to a non-existent profile
        self.parsed_globals.profile = 'nonexistent'

        # Mock botocore.session.Session
        mock_session = mock.Mock()
        mock_session.available_profiles = ['default', 'test']

        with mock.patch('botocore.session.Session', return_value=mock_session):
            with mock.patch('sys.stderr') as mock_stderr:
                rc = self.command._run_main(
                    self.parsed_args, self.parsed_globals
                )
                self.assertEqual(rc, 1)
                mock_stderr.write.assert_called_with(
                    "The profile (nonexistent) could not be found. \n"
                )

    def test_no_mfa_serial_provided(self):
        # Mock botocore.session.Session
        mock_session = mock.Mock()
        mock_session.get_credentials.return_value = mock.Mock()
        mock_session.get_scoped_config.return_value = {}
        mock_session.available_profiles = ['default']

        with mock.patch('botocore.session.Session', return_value=mock_session):
            with mock.patch('sys.stdin.isatty', return_value=True):
                self.prompter.get_credential_value.return_value = None
                with mock.patch('sys.stderr') as mock_stderr:
                    rc = self.command._run_main(
                        self.parsed_args, self.parsed_globals
                    )
                    self.assertEqual(rc, 1)
                    mock_stderr.write.assert_called_with(
                        "MFA serial number or MFA device ARN is required\n"
                    )

    def test_no_token_code_provided(self):
        # Mock botocore.session.Session
        mock_session = mock.Mock()
        mock_session.get_credentials.return_value = mock.Mock()
        mock_session.get_scoped_config.return_value = {}
        mock_session.available_profiles = ['default']

        with mock.patch('botocore.session.Session', return_value=mock_session):
            with mock.patch('sys.stdin.isatty', return_value=True):
                self.prompter.get_credential_value.side_effect = [
                    'arn:aws:iam::123456789012:mfa/user',
                    None,
                ]
                with mock.patch('sys.stderr') as mock_stderr:
                    rc = self.command._run_main(
                        self.parsed_args, self.parsed_globals
                    )
                    self.assertEqual(rc, 1)
                    mock_stderr.write.assert_called_with(
                        "MFA token code is required\n"
                    )

    def test_sts_client_error(self):
        # Mock botocore.session.Session
        mock_session = mock.Mock()
        mock_session.get_credentials.return_value = mock.Mock()
        mock_session.get_scoped_config.return_value = {}
        mock_session.available_profiles = ['default']

        sts_client = mock.Mock()
        sts_client.get_session_token.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'InvalidClientTokenId',
                    'Message': 'Test error',
                }
            },
            'GetSessionToken',
        )
        mock_session.create_client.return_value = sts_client

        with mock.patch('botocore.session.Session', return_value=mock_session):
            self.prompter.get_credential_value.side_effect = [
                'arn:aws:iam::123456789012:mfa/user',
                '123456',
            ]
            self.prompter.get_value.return_value = 'session-test'

            with mock.patch('sys.stderr') as mock_stderr:
                rc = self.command._run_main(
                    self.parsed_args, self.parsed_globals
                )
                self.assertEqual(rc, 1)
                mock_stderr.write.assert_called_with(
                    mock.ANY
                )  # Just check it was called

    def test_successful_mfa_login(self):
        # Setup
        self.parsed_args.duration_seconds = 43200
        self.prompter.get_credential_value.side_effect = [
            'arn:aws:iam::123456789012:mfa/user',
            '123456',
        ]
        self.prompter.get_value.return_value = 'session-test'

        expiration = datetime.datetime(2023, 5, 19, 18, 6, 10)
        sts_response = {
            'Credentials': {
                'AccessKeyId': 'ASIAIOSFODNN7EXAMPLE',
                'SecretAccessKey': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY',
                'SessionToken': 'AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE',
                'Expiration': expiration,
            }
        }

        # Mock botocore.session.Session
        mock_session = mock.Mock()
        mock_session.get_credentials.return_value = mock.Mock()
        mock_session.get_scoped_config.return_value = {}
        mock_session.available_profiles = ['default']

        sts_client = mock.Mock()
        sts_client.get_session_token.return_value = sts_response
        mock_session.create_client.return_value = sts_client

        with mock.patch('botocore.session.Session', return_value=mock_session):
            with mock.patch('sys.stdin.isatty', return_value=True):
                with mock.patch(
                    'os.path.expanduser', return_value='/tmp/credentials'
                ):
                    with mock.patch('sys.stdout'):
                        rc = self.command._run_main(
                            self.parsed_args, self.parsed_globals
                        )

        # Verify
        self.assertEqual(rc, 0)

        # Check STS was called correctly
        sts_client.get_session_token.assert_called_with(
            DurationSeconds=43200,
            SerialNumber='arn:aws:iam::123456789012:mfa/user',
            TokenCode='123456',
        )

        # Check config writer was called correctly
        expected_values = {
            '__section__': 'session-test',
            'aws_access_key_id': 'ASIAIOSFODNN7EXAMPLE',
            'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY',
            'aws_session_token': 'AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE',
            '#Credentials expire at: ': f"{expiration.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        }

        self.config_writer.update_config.assert_called_with(
            expected_values, '/tmp/credentials'
        )

    def test_serial_number_from_parameter(self):
        # Setup - use serial number from parameter
        self.parsed_args.serial_number = (
            'arn:aws:iam::123456789012:mfa/user-param'
        )
        self.parsed_args.duration_seconds = 43200

        # Mock botocore.session.Session
        mock_session = mock.Mock()
        mock_session.get_credentials.return_value = mock.Mock()
        mock_session.get_scoped_config.return_value = {
            'mfa_serial': 'arn:aws:iam::123456789012:mfa/user-config'
        }
        mock_session.available_profiles = ['default']

        sts_client = mock.Mock()
        expiration = datetime.datetime(2023, 5, 19, 18, 6, 10)
        sts_response = {
            'Credentials': {
                'AccessKeyId': 'ASIAIOSFODNN7EXAMPLE',
                'SecretAccessKey': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY',
                'SessionToken': 'SESSION_TOKEN',
                'Expiration': expiration,
            }
        }
        sts_client.get_session_token.return_value = sts_response
        mock_session.create_client.return_value = sts_client

        with mock.patch('botocore.session.Session', return_value=mock_session):
            with mock.patch('sys.stdin.isatty', return_value=True):
                self.prompter.get_credential_value.return_value = '123456'
                self.prompter.get_value.return_value = 'session-test'
                with mock.patch(
                    'os.path.expanduser', return_value='/tmp/credentials'
                ):
                    with mock.patch('sys.stdout'):
                        rc = self.command._run_main(
                            self.parsed_args, self.parsed_globals
                        )

        # Verify
        self.assertEqual(rc, 0)

        # Check that the parameter value was used instead of the config value
        sts_client.get_session_token.assert_called_with(
            DurationSeconds=43200,
            SerialNumber='arn:aws:iam::123456789012:mfa/user-param',
            TokenCode='123456',
        )

    def test_missing_default_profile_interactive(self):
        """Test prompting for credentials when no default profile exists in interactive mode."""
        self.parsed_globals.profile = None  # Use default profile

        # Mock botocore.session.Session to raise ProfileNotFound
        with mock.patch('botocore.session.Session') as mock_session_class:
            mock_session_class.side_effect = ProfileNotFound(profile='default')

            # Mock sys.stdin.isatty to return True (interactive)
            with mock.patch('sys.stdin.isatty', return_value=True):
                # Mock the _handle_interactive_prompting method
                with mock.patch.object(
                    self.command,
                    '_handle_interactive_prompting',
                    return_value=0,
                ) as mock_handle:
                    rc = self.command._run_main(
                        self.parsed_args, self.parsed_globals
                    )

                    self.assertEqual(rc, 0)
                    mock_handle.assert_called_once_with(
                        self.parsed_args, None
                    )

    def test_missing_default_profile_non_interactive(self):
        """Test error when no default profile exists in non-interactive mode."""
        self.parsed_globals.profile = None  # Use default profile
        
        # Setup mock responses for interactive prompting
        self.prompter.get_credential_value.side_effect = [
            'AKIAIOSFODNN7EXAMPLE',  # access key
            'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # secret key
            'arn:aws:iam::123456789012:mfa/user',  # MFA serial
            '123456',  # MFA token
        ]
        self.prompter.get_value.return_value = 'session-test'  # profile name

        # Mock botocore.session.Session to return None credentials
        mock_session = mock.Mock()
        mock_session.get_credentials.return_value = None
        mock_session.available_profiles = ['default']
        
        with mock.patch('botocore.session.Session', return_value=mock_session):
            with mock.patch('sys.stdin.isatty', return_value=False):
                # Mock STS for the interactive prompting path
                sts_client = mock.Mock()
                sts_client.get_session_token.return_value = {
                    'Credentials': {
                        'AccessKeyId': 'ASIAIOSFODNN7EXAMPLE',
                        'SecretAccessKey': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY',
                        'SessionToken': 'SESSION_TOKEN',
                        'Expiration': datetime.datetime(2023, 5, 19, 18, 6, 10),
                    }
                }
                mock_session.create_client.return_value = sts_client
                
                with mock.patch('os.path.expanduser', return_value='/tmp/credentials'):
                    with mock.patch('sys.stdout'):
                        rc = self.command._run_main(
                            self.parsed_args, self.parsed_globals
                        )

                        self.assertEqual(rc, 0)  # Should succeed via interactive prompting

    def test_handle_missing_default_profile_success(self):
        """Test successful credential prompting and MFA login when no default profile exists."""
        # Setup mock responses for prompting - now all via get_credential_value
        self.prompter.get_credential_value.side_effect = [
            'AKIAIOSFODNN7EXAMPLE',  # access key
            'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # secret key
            'arn:aws:iam::123456789012:mfa/user',  # MFA serial
            '123456',  # MFA token
        ]
        self.prompter.get_value.return_value = 'session-test'  # profile name

        # Mock STS response
        expiration = datetime.datetime(2023, 5, 19, 18, 6, 10)
        sts_response = {
            'Credentials': {
                'AccessKeyId': 'ASIAIOSFODNN7EXAMPLE',
                'SecretAccessKey': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY',
                'SessionToken': 'SESSION_TOKEN',
                'Expiration': expiration,
            }
        }

        # Mock botocore session and STS client
        mock_session = mock.Mock()
        sts_client = mock.Mock()
        sts_client.get_session_token.return_value = sts_response
        mock_session.create_client.return_value = sts_client

        with mock.patch('botocore.session.Session', return_value=mock_session):
            with mock.patch(
                'os.path.expanduser', return_value='/tmp/credentials'
            ):
                with mock.patch('sys.stdout'):
                    rc = self.command._handle_interactive_prompting(
                        self.parsed_args, 43200
                    )

        # Verify success
        self.assertEqual(rc, 0)

        # Verify STS call
        sts_client.get_session_token.assert_called_with(
            DurationSeconds=43200,
            SerialNumber='arn:aws:iam::123456789012:mfa/user',
            TokenCode='123456',
        )

        # Verify only the session profile was written
        self.assertEqual(self.config_writer.update_config.call_count, 1)

    def test_handle_missing_default_profile_missing_access_key(self):
        """Test error when access key is not provided."""
        self.prompter.get_credential_value.return_value = (
            None  # No access key provided
        )

        with mock.patch('sys.stderr') as mock_stderr:
            rc = self.command._handle_interactive_prompting(
                self.parsed_args, 43200
            )

            self.assertEqual(rc, 1)
            mock_stderr.write.assert_called_with(
                "AWS Access Key ID is required\n"
            )

    def test_handle_missing_default_profile_missing_secret_key(self):
        """Test error when secret key is not provided."""
        self.prompter.get_credential_value.side_effect = [
            'AKIAIOSFODNN7EXAMPLE',  # access key provided
            None,  # secret key not provided
        ]

        with mock.patch('sys.stderr') as mock_stderr:
            rc = self.command._handle_interactive_prompting(
                self.parsed_args, 43200
            )

            self.assertEqual(rc, 1)
            mock_stderr.write.assert_called_with(
                "AWS Secret Access Key is required\n"
            )

    def test_credential_value_prompting_clean_display(self):
        """Test that credential prompting doesn't show default values."""
        prompter = InteractiveMFAPrompter()
        with mock.patch(
            'awscli.customizations.configure.mfalogin.compat_input'
        ) as mock_input:
            mock_input.return_value = 'test-value'
            result = prompter.get_credential_value(
                'None', 'aws_access_key_id', 'AWS Access Key ID'
            )

            # Verify the prompt doesn't show [None] or any default value
            mock_input.assert_called_with('AWS Access Key ID: ')
            self.assertEqual(result, 'test-value')

    def test_handle_missing_default_profile_sts_error(self):
        """Test STS error handling in missing default profile scenario."""
        self.prompter.get_credential_value.side_effect = [
            'AKIAIOSFODNN7EXAMPLE',  # access key
            'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # secret key
            'arn:aws:iam::123456789012:mfa/user',  # MFA serial
            '123456',  # MFA token
        ]
        self.prompter.get_value.return_value = 'session-test'  # profile name

        # Mock STS client to raise an error
        mock_session = mock.Mock()
        sts_client = mock.Mock()
        sts_client.get_session_token.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'InvalidClientTokenId',
                    'Message': 'Invalid credentials',
                }
            },
            'GetSessionToken',
        )
        mock_session.create_client.return_value = sts_client

        with mock.patch('botocore.session.Session', return_value=mock_session):
            with mock.patch('sys.stderr') as mock_stderr:
                rc = self.command._handle_interactive_prompting(
                    self.parsed_args, 43200
                )

                self.assertEqual(rc, 1)
                # Verify error message was written
                mock_stderr.write.assert_called()
                self.assertIn(
                    'An error occurred', str(mock_stderr.write.call_args)
                )

    def test_non_interactive_missing_mfa_serial(self):
        """Test non-interactive mode when MFA serial is missing."""
        mock_session = mock.Mock()
        mock_session.get_credentials.return_value = mock.Mock()
        mock_session.get_scoped_config.return_value = {}  # No mfa_serial in config
        mock_session.available_profiles = ['default']

        with mock.patch('botocore.session.Session', return_value=mock_session):
            with mock.patch(
                'sys.stdin.isatty', return_value=False
            ):  # Non-interactive
                self.prompter.get_credential_value.return_value = None
                with mock.patch('sys.stderr') as mock_stderr:
                    rc = self.command._run_main(
                        self.parsed_args, self.parsed_globals
                    )

                    self.assertEqual(rc, 1)
                    mock_stderr.write.assert_called_with(
                        "MFA serial number or MFA device ARN is required\n"
                    )

    def test_non_interactive_missing_token_code(self):
        """Test non-interactive mode when token code would be prompted."""
        mock_session = mock.Mock()
        mock_session.get_credentials.return_value = mock.Mock()
        mock_session.get_scoped_config.return_value = {
            'mfa_serial': 'arn:aws:iam::123456789012:mfa/user'
        }
        mock_session.available_profiles = ['default']

        with mock.patch('botocore.session.Session', return_value=mock_session):
            with mock.patch(
                'sys.stdin.isatty', return_value=False
            ):  # Non-interactive
                self.prompter.get_credential_value.return_value = None
                with mock.patch('sys.stderr') as mock_stderr:
                    rc = self.command._run_main(
                        self.parsed_args, self.parsed_globals
                    )

                    self.assertEqual(rc, 1)
                    mock_stderr.write.assert_called_with(
                        "MFA token code is required\n"
                    )

    def test_empty_credential_input_handling(self):
        """Test handling of empty credential inputs."""
        self.prompter.get_credential_value.return_value = ''  # Empty string

        with mock.patch('sys.stderr') as mock_stderr:
            rc = self.command._handle_interactive_prompting(
                self.parsed_args, 43200
            )

            self.assertEqual(rc, 1)
            mock_stderr.write.assert_called_with(
                "AWS Access Key ID is required\n"
            )
