# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import json
import mock
import io
from datetime import datetime, timedelta

from dateutil.tz import tzutc
import pytest
from botocore.credentials import RefreshableCredentials
from botocore.credentials import Credentials as StaticCredentials
from botocore.credentials import ReadOnlyCredentials
from botocore.session import Session

from awscli.testutils import unittest
from awscli.customizations.configure.exportcreds import (
    Credentials,
    convert_botocore_credentials,
    ConfigureExportCredentialsCommand,
    BashEnvVarFormatter,
    BashNoExportEnvFormatter,
    PowershellFormatter,
    WindowsCmdFormatter,
    CredentialProcessFormatter,
)


class JSONValue:
    def __init__(self, json_str):
        self.json_str = json_str
        self.parsed_json = json.loads(json_str)

    def __eq__(self, other):
        if isinstance(other, str):
            other_parsed = json.loads(other)
            return self.parsed_json == other_parsed
        return self.parsed_json == other


@pytest.mark.parametrize(
    'format_cls, expected', [
        (BashEnvVarFormatter, (
            ('export AWS_ACCESS_KEY_ID=access_key\n'
             'export AWS_SECRET_ACCESS_KEY=secret_key\n'),
            ('export AWS_ACCESS_KEY_ID=access_key\n'
             'export AWS_SECRET_ACCESS_KEY=secret_key\n'
             'export AWS_SESSION_TOKEN=token\n'
             'export AWS_CREDENTIAL_EXPIRATION=2023-01-01T00:00:00Z\n'),
        )),
        (BashNoExportEnvFormatter, (
            ('AWS_ACCESS_KEY_ID=access_key\n'
             'AWS_SECRET_ACCESS_KEY=secret_key\n'),
            ('AWS_ACCESS_KEY_ID=access_key\n'
             'AWS_SECRET_ACCESS_KEY=secret_key\n'
             'AWS_SESSION_TOKEN=token\n'
             'AWS_CREDENTIAL_EXPIRATION=2023-01-01T00:00:00Z\n'),
        )),
        (PowershellFormatter, (
            ('$Env:AWS_ACCESS_KEY_ID="access_key"\n'
             '$Env:AWS_SECRET_ACCESS_KEY="secret_key"\n'),
            ('$Env:AWS_ACCESS_KEY_ID="access_key"\n'
             '$Env:AWS_SECRET_ACCESS_KEY="secret_key"\n'
             '$Env:AWS_SESSION_TOKEN="token"\n'
             '$Env:AWS_CREDENTIAL_EXPIRATION=2023-01-01T00:00:00Z\n'),
        )),
        (WindowsCmdFormatter, (
            ('set AWS_ACCESS_KEY_ID=access_key\n'
             'set AWS_SECRET_ACCESS_KEY=secret_key\n'),
            ('set AWS_ACCESS_KEY_ID=access_key\n'
             'set AWS_SECRET_ACCESS_KEY=secret_key\n'
             'set AWS_SESSION_TOKEN=token\n'
             'set AWS_CREDENTIAL_EXPIRATION=2023-01-01T00:00:00Z\n'),
        )),
        (CredentialProcessFormatter, (
            JSONValue(
                '{"Version": 1, "AccessKeyId": "access_key", '
                '"SecretAccessKey": "secret_key"}'),
            JSONValue(
                '{"Version": 1, "AccessKeyId": "access_key", '
                '"SecretAccessKey": "secret_key", "SessionToken": '
                '"token", "Expiration": "2023-01-01T00:00:00Z"}'),
        )),
    ]
)
def test_cred_formatter(format_cls, expected):
    stream = io.StringIO()
    expected_static, expected_temporary = expected
    formatter = format_cls(stream)

    # Static case, only access_key/secret_key
    creds = Credentials('access_key', 'secret_key', None, None)
    formatter.display_credentials(creds)
    assert stream.getvalue() == expected_static

    # Refreshable case, access_key/secret_key/token/expiration.
    # Reset back to an empty stream.
    stream.truncate(0)
    stream.seek(0)
    expiry = '2023-01-01T00:00:00Z'
    temp_creds = Credentials(
        'access_key', 'secret_key', 'token', expiry)
    formatter.display_credentials(temp_creds)
    assert stream.getvalue() == expected_temporary


class TestCanConvertBotocoreCredentials(unittest.TestCase):
    def test_can_convert_static_creds_with_no_expiry(self):
        self.assertEqual(
            convert_botocore_credentials(
                StaticCredentials('access_key', 'secret_key')
            ),
            Credentials('access_key', 'secret_key', token=None,
                        expiry_time=None)
        )

    def test_can_convert_creds_with_token_and_no_expiry(self):
        self.assertEqual(
            convert_botocore_credentials(
                StaticCredentials('access_key', 'secret_key', 'token')
            ),
            Credentials('access_key', 'secret_key', 'token', expiry_time=None)
        )

    def test_can_convert_refreshable_with_expiry(self):
        expiry = datetime.now(tzutc()) + timedelta(hours=12)
        self.assertEqual(
            convert_botocore_credentials(
                RefreshableCredentials(
                    'access_key',
                    'secret_key',
                    'token',
                    expiry_time=expiry,
                    refresh_using=None,
                    method='explicit',
                )
            ),
            Credentials('access_key', 'secret_key', 'token',
                        expiry_time=expiry.isoformat())
        )

    def test_no_expiry_time_if_non_datetime_value(self):
        bad_creds = mock.Mock(spec=StaticCredentials)
        bad_creds.get_frozen_credentials.return_value = ReadOnlyCredentials(
            'access_key', 'secret_key', 'token')
        bad_creds._expiry_time = 'not a datetime'
        self.assertEqual(
            convert_botocore_credentials(bad_creds),
            Credentials('access_key', 'secret_key', 'token',
                        expiry_time=None)
        )


class TestConfigureExportCredentialsCommand(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock(spec=Session)
        self.session.emit_first_non_none_response.return_value = None
        self.out_stream = io.StringIO()
        self.err_stream = io.StringIO()
        self.os_env = {}
        self.session.get_config_variable.return_value = 'default'
        self.export_creds_cmd = ConfigureExportCredentialsCommand(
            self.session, self.out_stream, self.err_stream, env=self.os_env)
        self.global_args = mock.Mock()
        self.expiry = '2023-01-01T00:00:00Z'
        self.creds = StaticCredentials('access_key', 'secret_key')

    def test_can_export_creds(self):
        self.session.get_credentials.return_value = self.creds
        rc = self.export_creds_cmd(args=[], parsed_globals=self.global_args)
        self.assertEqual(rc, 0)
        self.assertEqual(
            self.out_stream.getvalue(),
            JSONValue(
                '{"Version": 1, "AccessKeyId": "access_key", '
                '"SecretAccessKey": "secret_key"}')
        )

    def test_can_export_creds_explicit_format(self):
        self.session.get_credentials.return_value = self.creds
        rc = self.export_creds_cmd(
            args=['--format', 'env'],
            parsed_globals=self.global_args)
        self.assertEqual(rc, 0)
        self.assertEqual(
            self.out_stream.getvalue(),
            'export AWS_ACCESS_KEY_ID=access_key\n'
            'export AWS_SECRET_ACCESS_KEY=secret_key\n'
        )

    def test_show_error_when_no_cred(self):
        self.session.get_credentials.return_value = None
        rc = self.export_creds_cmd(args=[], parsed_globals=self.global_args)
        self.assertIn(
            'Unable to retrieve credentials', self.err_stream.getvalue()
        )
        self.assertEqual(rc, 1)

    def test_show_error_when_cred_resolution_errors(self):
        self.session.get_credentials.side_effect = Exception(
            "resolution failed")
        rc = self.export_creds_cmd(args=[], parsed_globals=self.global_args)
        self.assertIn(
            'resolution failed', self.err_stream.getvalue()
        )
        self.assertEqual(rc, 1)

    def test_can_detect_recursive_resolution(self):
        self.os_env['_AWS_CLI_PROFILE_CHAIN'] = 'default'
        rc = self.export_creds_cmd(args=[], parsed_globals=self.global_args)
        self.assertIn(
            'Recursive credential resolution process detected',
            self.err_stream.getvalue()
        )
        self.assertEqual(rc, 2)

    def test_nested_calls_not_recursive(self):
        self.session.get_credentials.return_value = self.creds
        # If we've seen the profiles foo and bar:
        self.os_env['_AWS_CLI_PROFILE_CHAIN'] = 'foo,bar'
        # And we're now on baz, then we shouldn't get an error
        # because there's no cycle.
        self.session.get_config_variable.return_value = 'baz'
        rc = self.export_creds_cmd(args=[], parsed_globals=self.global_args)
        self.assertEqual(rc, 0)
        self.assertEqual(
            self.out_stream.getvalue(),
            JSONValue(
                '{"Version": 1, "AccessKeyId": "access_key", '
                '"SecretAccessKey": "secret_key"}')
        )

    def test_nested_calls_with_cycle(self):
        self.session.get_credentials.return_value = self.creds
        self.os_env['_AWS_CLI_PROFILE_CHAIN'] = 'foo,bar,baz'
        self.session.get_config_variable.return_value = 'bar'
        rc = self.export_creds_cmd(args=[], parsed_globals=self.global_args)
        self.assertIn(
            'Recursive credential resolution process detected',
            self.err_stream.getvalue()
        )
        self.assertEqual(rc, 2)

    def test_handles_comma_char_in_profile_name_no_cycle(self):
        self.session.get_credentials.return_value = self.creds
        self.os_env['_AWS_CLI_PROFILE_CHAIN'] = 'foo,bar,baz'
        # Shouldn't be a cycle, the comma is part of the profile name.
        self.session.get_config_variable.return_value = 'bar,baz'
        rc = self.export_creds_cmd(args=[], parsed_globals=self.global_args)
        self.assertEqual(rc, 0)
        self.assertEqual(
            self.out_stream.getvalue(),
            JSONValue(
                '{"Version": 1, "AccessKeyId": "access_key", '
                '"SecretAccessKey": "secret_key"}')
        )

    def test_detects_comma_char_with_cycle(self):
        self.session.get_credentials.return_value = self.creds
        # To test the round tripping of CSV writing/reading, we'll invoke
        # the command twice to ensure however it records the profiles
        # that it detects a cycle with names that need to be escaped/quoted.
        self.os_env['_AWS_CLI_PROFILE_CHAIN'] = 'foo,bar'
        self.session.get_config_variable.return_value = 'bar,baz'
        # First time it succeeds.
        rc = self.export_creds_cmd(args=[], parsed_globals=self.global_args)
        self.assertEqual(rc, 0)
        # Second time, it detects the cycle.
        second_invoke = ConfigureExportCredentialsCommand(
            self.session, self.out_stream, self.err_stream, env=self.os_env)
        rc = second_invoke(args=[], parsed_globals=self.global_args)
        self.assertIn(
            'Recursive credential resolution process detected',
            self.err_stream.getvalue()
        )
        self.assertEqual(rc, 2)

    def test_max_recursion_limit(self):
        self.session.get_credentials.return_value = self.creds
        self.os_env['_AWS_CLI_PROFILE_CHAIN'] = ','.join(
            ['a', 'b', 'c', 'd', 'e', 'f', 'g'])
        rc = self.export_creds_cmd(args=[], parsed_globals=self.global_args)
        self.assertIn(
            'Recursive credential resolution process detected',
            self.err_stream.getvalue()
        )
        self.assertEqual(rc, 2)
