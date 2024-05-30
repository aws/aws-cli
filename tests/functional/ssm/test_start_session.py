# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import errno
import json

from awscli.testutils import BaseAWSCommandParamsTest
from awscli.testutils import BaseAWSHelpOutputTest
from awscli.testutils import create_clidriver, mock, temporary_file
from botocore.exceptions import ProfileNotFound


class TestSessionManager(BaseAWSCommandParamsTest):
    @mock.patch('awscli.customizations.sessionmanager.check_call')
    @mock.patch("awscli.customizations.sessionmanager.check_output")
    def test_start_session_success(self, mock_check_output, mock_check_call):
        cmdline = 'ssm start-session --target instance-id'
        mock_check_call.return_value = 0
        mock_check_output.return_value = "1.2.0.0\n"
        expected_response = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url",
        }
        self.parsed_responses = [expected_response]
        start_session_params = {"Target": "instance-id"}

        self.run_cmd(cmdline, expected_rc=0)

        mock_check_call.assert_called_once_with(
            [
                "session-manager-plugin",
                json.dumps(expected_response),
                mock.ANY,
                "StartSession",
                "",
                json.dumps(start_session_params),
                mock.ANY,
            ],
            env=self.environ,
        )

    @mock.patch("awscli.customizations.sessionmanager.check_call")
    @mock.patch("awscli.customizations.sessionmanager.check_output")
    def test_start_session_with_new_version_plugin_success(
        self, mock_check_output, mock_check_call
    ):
        cmdline = "ssm start-session --target instance-id"
        mock_check_call.return_value = 0
        mock_check_output.return_value = "1.2.500.0\n"
        expected_response = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url",
        }
        self.parsed_responses = [expected_response]

        ssm_env_name = "AWS_SSM_START_SESSION_RESPONSE"
        start_session_params = {"Target": "instance-id"}
        expected_env = self.environ.copy()
        expected_env.update({ssm_env_name: json.dumps(expected_response)})

        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(self.operations_called[0][0].name,
                         'StartSession')
        self.assertEqual(self.operations_called[0][1],
                         {'Target': 'instance-id'})

        mock_check_call.assert_called_once_with(
            [
                "session-manager-plugin",
                ssm_env_name,
                mock.ANY,
                "StartSession",
                "",
                json.dumps(start_session_params),
                mock.ANY,
            ],
            env=expected_env,
        )

    @mock.patch("awscli.customizations.sessionmanager.check_call")
    @mock.patch("awscli.customizations.sessionmanager.check_output")
    def test_profile_parameter_passed_to_sessionmanager_plugin(
        self, mock_check_output, mock_check_call
    ):
        cmdline = (
            "ssm start-session --target instance-id "
            "--profile user_profile"
        )
        mock_check_call.return_value = 0
        mock_check_output.return_value = "1.2.500.0\n"
        expected_response = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url",
        }
        self.parsed_responses = [expected_response]
        ssm_env_name = "AWS_SSM_START_SESSION_RESPONSE"
        start_session_params = {
            "Target": "instance-id",
        }

        # We test this by creating 4 credentials
        # env vars, default profile (default),
        # env aws profile (local_profile)
        # and StartSession command profile (user_profile)
        # We want to make sure only profile name in command
        # be set to session manager plugin as parameter
        self.environ['AWS_ACCESS_KEY_ID'] = 'env_var_akid'
        self.environ['AWS_SECRET_ACCESS_KEY'] = 'env_var_sak'

        with temporary_file('w') as f:
            f.write(
                '[default]\n'
                'aws_access_key_id = shared_default_akid\n'
                'aws_secret_access_key = shared_default_sak\n'
                '[local_profile]\n'
                'aws_access_key_id = shared_local_akid\n'
                'aws_secret_access_key = shared_local_sak\n'
                '[user_profile]\n'
                'aws_access_key_id = shared_user_akid\n'
                'aws_secret_access_key = shared_user_sak\n'
            )
            f.flush()

            self.environ['AWS_SHARED_CREDENTIALS_FILE'] = f.name
            self.environ["AWS_PROFILE"] = "local_profile"

            expected_env = self.environ.copy()
            expected_env.update({ssm_env_name: json.dumps(expected_response)})

            self.driver = create_clidriver()
            self.run_cmd(cmdline, expected_rc=0)

        self.assertEqual(self.operations_called[0][0].name,
                         'StartSession')
        self.assertEqual(self.operations_called[0][1],
                         {'Target': 'instance-id'})
        mock_check_call.assert_called_once_with(
            [
                "session-manager-plugin",
                ssm_env_name,
                mock.ANY,
                "StartSession",
                "user_profile",
                json.dumps(start_session_params),
                mock.ANY,
            ],
            env=expected_env,
        )

    @mock.patch("awscli.customizations.sessionmanager.check_call")
    @mock.patch("awscli.customizations.sessionmanager.check_output")
    def test_profile_environment_not_passed_to_sessionmanager_plugin(
        self, mock_check_output, mock_check_call
    ):
        cmdline = "ssm start-session --target instance-id"
        mock_check_call.return_value = 0
        mock_check_output.return_value = "1.2.500.0\n"
        expected_response = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url",
        }
        self.parsed_responses = [expected_response]
        ssm_env_name = "AWS_SSM_START_SESSION_RESPONSE"
        start_session_params = {
            "Target": "instance-id",
        }

        with temporary_file('w') as f:
            f.write(
                '[default]\n'
                'aws_access_key_id = shared_default_akid\n'
                'aws_secret_access_key = shared_default_sak\n'
                '[local_profile]\n'
                'aws_access_key_id = shared_local_akid\n'
                'aws_secret_access_key = shared_local_sak\n'
            )
            f.flush()

            self.environ.pop("AWS_ACCESS_KEY_ID", None)
            self.environ.pop("AWS_SECRET_ACCESS_KEY", None)
            self.environ['AWS_SHARED_CREDENTIALS_FILE'] = f.name
            self.environ["AWS_PROFILE"] = "local_profile"

            expected_env = self.environ.copy()
            expected_env.update({ssm_env_name: json.dumps(expected_response)})

            self.driver = create_clidriver()
            self.run_cmd(cmdline, expected_rc=0)

        self.assertEqual(self.operations_called[0][0].name,
                         'StartSession')
        self.assertEqual(self.operations_called[0][1],
                         {'Target': 'instance-id'})
        mock_check_call.assert_called_once_with(
            [
                "session-manager-plugin",
                ssm_env_name,
                mock.ANY,
                "StartSession",
                "",
                json.dumps(start_session_params),
                mock.ANY,
            ],
            env=expected_env,
        )

    @mock.patch("awscli.customizations.sessionmanager.check_call")
    @mock.patch("awscli.customizations.sessionmanager.check_output")
    def test_default_profile_used_and_not_passed_to_sessionmanager_plugin(
        self, mock_check_output, mock_check_call
    ):
        cmdline = "ssm start-session --target instance-id"
        mock_check_call.return_value = 0
        mock_check_output.return_value = "1.2.500.0\n"
        expected_response = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url",
        }
        self.parsed_responses = [expected_response]
        ssm_env_name = "AWS_SSM_START_SESSION_RESPONSE"
        start_session_params = {
            "Target": "instance-id",
        }

        with temporary_file('w') as f:
            f.write(
                '[default]\n'
                'aws_access_key_id = shared_default_akid\n'
                'aws_secret_access_key = shared_default_sak\n'
            )
            f.flush()

            self.environ.pop("AWS_ACCESS_KEY_ID", None)
            self.environ.pop("AWS_SECRET_ACCESS_KEY", None)
            self.environ.pop("AWS_SHARED_CREDENTIALS_FILE", None)
            self.environ.pop("AWS_PROFILE", None)

            expected_env = self.environ.copy()
            expected_env.update({ssm_env_name: json.dumps(expected_response)})

            self.driver = create_clidriver()
            self.run_cmd(cmdline, expected_rc=0)

        self.assertEqual(self.operations_called[0][0].name,
                         'StartSession')
        self.assertEqual(self.operations_called[0][1],
                         {'Target': 'instance-id'})
        mock_check_call.assert_called_once_with(
            [
                "session-manager-plugin",
                ssm_env_name,
                mock.ANY,
                "StartSession",
                "",
                json.dumps(start_session_params),
                mock.ANY,
            ],
            env=expected_env,
        )

    def test_start_session_with_user_profile_not_exist(self):
        cmdline = (
            "ssm start-session --target instance-id "
            "--profile user_profile"
        )
        with temporary_file('w') as f:
            f.write(
                '[default]\n'
                'aws_access_key_id = shared_default_akid\n'
                'aws_secret_access_key = shared_default_sak\n'
            )
            f.flush()

            self.environ.pop("AWS_ACCESS_KEY_ID", None)
            self.environ.pop("AWS_SECRET_ACCESS_KEY", None)
            self.environ.pop("AWS_PROFILE", None)
            self.environ['AWS_SHARED_CREDENTIALS_FILE'] = f.name

            try:
                self.driver = create_clidriver()
                self.run_cmd(cmdline, expected_rc=255)
            except ProfileNotFound as e:
                self.assertIn(
                    'The config profile (user_profile) could not be found',
                    str(e)
                )

    @mock.patch('awscli.customizations.sessionmanager.check_call')
    @mock.patch("awscli.customizations.sessionmanager.check_output")
    def test_start_session_fails(self, mock_check_output, mock_check_call):
        cmdline = "ssm start-session --target instance-id"
        mock_check_output.return_value = "1.2.500.0\n"
        mock_check_call.side_effect = OSError(errno.ENOENT, "some error")
        self.parsed_responses = [
            {
                "SessionId": "session-id",
                "TokenValue": "token-value",
                "StreamUrl": "stream-url",
            }
        ]
        self.run_cmd(cmdline, expected_rc=255)
        self.assertEqual(
            self.operations_called[0][0].name, "StartSession"
        )
        self.assertEqual(
            self.operations_called[0][1], {"Target": "instance-id"}
        )
        self.assertEqual(
            self.operations_called[1][0].name, "TerminateSession"
        )
        self.assertEqual(
            self.operations_called[1][1], {"SessionId": "session-id"}
        )

    @mock.patch("awscli.customizations.sessionmanager.check_call")
    @mock.patch("awscli.customizations.sessionmanager.check_output")
    def test_start_session_when_get_plugin_version_fails(
        self, mock_check_output, mock_check_call
    ):
        cmdline = 'ssm start-session --target instance-id'
        mock_check_output.side_effect = OSError(errno.ENOENT, 'some error')
        self.parsed_responses = [
            {
                "SessionId": "session-id",
                "TokenValue": "token-value",
                "StreamUrl": "stream-url",
            }
        ]
        self.run_cmd(cmdline, expected_rc=255)
        self.assertEqual(self.operations_called[0][0].name,
                         'StartSession')
        self.assertEqual(self.operations_called[0][1],
                         {'Target': 'instance-id'})
        self.assertEqual(self.operations_called[1][0].name,
                         'TerminateSession')
        self.assertEqual(self.operations_called[1][1],
                         {'SessionId': 'session-id'})


class TestHelpOutput(BaseAWSHelpOutputTest):
    def test_start_session_output(self):
        self.driver.main(['ssm', 'start-session', 'help'])
        self.assert_contains('Output\n======\n\nNone')
