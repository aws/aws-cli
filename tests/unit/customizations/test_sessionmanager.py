# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import botocore.session
import errno
import json
import pytest
import subprocess
import sys

from awscli.customizations import sessionmanager
from awscli.testutils import mock, unittest


class TestSessionManager(unittest.TestCase):

    def setUp(self):
        self.session = mock.Mock(botocore.session.Session)
        self.client = mock.Mock()
        self.region = 'us-west-2'
        self.profile = 'testProfile'
        self.endpoint_url = 'testUrl'
        self.client.meta.region_name = self.region
        self.client.meta.endpoint_url = self.endpoint_url
        self.session.create_client.return_value = self.client
        self.session.profile = self.profile
        self.caller = sessionmanager.StartSessionCaller(self.session)

        self.parsed_globals = mock.Mock()
        self.parsed_globals.profile = 'user_profile'

    def test_start_session_when_non_custom_start_session_fails(self):
        self.client.start_session.side_effect = Exception('some exception')
        params = {}
        with self.assertRaisesRegex(Exception, 'some exception'):
            self.caller.invoke('ssm', 'StartSession', params, mock.Mock())

    @mock.patch("awscli.customizations.sessionmanager.check_output")
    @mock.patch('awscli.customizations.sessionmanager.check_call')
    def test_start_session_success_scenario(
            self, mock_check_call, mock_check_output
    ):
        mock_check_output.return_value = "1.2.0.0\n"
        mock_check_call.return_value = 0

        start_session_params = {
            "Target": "i-123456789"
        }

        start_session_response = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url"
        }

        self.client.start_session.return_value = start_session_response

        rc = self.caller.invoke('ssm', 'StartSession',
                                start_session_params, self.parsed_globals)
        self.assertEqual(rc, 0)
        self.client.start_session.assert_called_with(**start_session_params)

        mock_check_output_list = mock_check_output.call_args[0]
        self.assertEqual(
            mock_check_output_list[0], ["session-manager-plugin", "--version"]
        )

        mock_check_call_list = mock_check_call.call_args[0][0]
        mock_check_call_list[1] = json.loads(mock_check_call_list[1])
        self.assertEqual(
            mock_check_call_list,
            ['session-manager-plugin',
             start_session_response,
             self.region,
             'StartSession',
             self.parsed_globals.profile,
             json.dumps(start_session_params),
             self.endpoint_url]
        )

    @mock.patch("awscli.customizations.sessionmanager.check_output")
    @mock.patch('awscli.customizations.sessionmanager.check_call')
    def test_start_session_when_check_call_fails(
        self, mock_check_call, mock_check_output
    ):
        mock_check_output.return_value = "1.2.0.0\n"
        mock_check_call.side_effect = OSError(errno.ENOENT, 'some error')

        start_session_params = {
            "Target": "i-123456789"
        }

        start_session_response = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url"
        }

        terminate_session_params = {
            "SessionId": "session-id"
        }

        self.client.start_session.return_value = start_session_response

        with self.assertRaises(ValueError):
            self.caller.invoke('ssm', 'StartSession',
                               start_session_params, self.parsed_globals)

            self.client.start_session.assert_called_with(
                **start_session_params)
            self.client.terminate_session.assert_called_with(
                **terminate_session_params)

            mock_check_call_list = mock_check_call.call_args[0][0]
            mock_check_call_list[1] = json.loads(mock_check_call_list[1])
            self.assertEqual(
                mock_check_call_list,
                ['session-manager-plugin',
                 start_session_response,
                 self.region,
                 'StartSession',
                 self.parsed_globals.profile,
                 json.dumps(start_session_params),
                 self.endpoint_url]
            )

    @mock.patch('awscli.customizations.sessionmanager.check_call')
    @mock.patch("awscli.customizations.sessionmanager.check_output")
    def test_start_session_when_no_profile_is_passed(
        self, mock_check_output, mock_check_call
    ):
        mock_check_output.return_value = "1.2.500.0\n"
        self.session.profile = "session_profile"
        self.parsed_globals.profile = None
        mock_check_call.return_value = 0

        start_session_params = {
            "Target": "i-123456789"
        }

        start_session_response = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url"
        }
        ssm_env_name = "AWS_SSM_START_SESSION_RESPONSE"

        self.client.start_session.return_value = start_session_response

        rc = self.caller.invoke('ssm', 'StartSession',
                                start_session_params, self.parsed_globals)
        self.assertEqual(rc, 0)
        self.client.start_session.assert_called_with(**start_session_params)
        mock_check_call_list = mock_check_call.call_args[0][0]
        self.assertEqual(
            mock_check_call_list,
            [
                "session-manager-plugin",
                ssm_env_name,
                self.region,
                "StartSession",
                "",
                json.dumps(start_session_params),
                self.endpoint_url,
            ],
        )

    @mock.patch("awscli.customizations.sessionmanager.check_call")
    @mock.patch("awscli.customizations.sessionmanager.check_output")
    def test_start_session_with_env_variable_success_scenario(
        self, mock_check_output, mock_check_call
    ):
        mock_check_output.return_value = "1.2.500.0\n"
        mock_check_call.return_value = 0

        start_session_params = {
            "Target": "i-123456789"
        }

        start_session_response = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url",
        }
        ssm_env_name = "AWS_SSM_START_SESSION_RESPONSE"

        self.client.start_session.return_value = start_session_response
        rc = self.caller.invoke(
            "ssm", "StartSession", start_session_params, self.parsed_globals
        )
        self.assertEqual(rc, 0)
        self.client.start_session.assert_called_with(**start_session_params)

        mock_check_output_list = mock_check_output.call_args[0]
        self.assertEqual(
            mock_check_output_list[0], ["session-manager-plugin", "--version"]
        )

        mock_check_call_list = mock_check_call.call_args[0][0]
        self.assertEqual(
            mock_check_call_list,
            [
                "session-manager-plugin",
                ssm_env_name,
                self.region,
                "StartSession",
                self.parsed_globals.profile,
                json.dumps(start_session_params),
                self.endpoint_url,
            ],
        )
        env_variable = mock_check_call.call_args[1]
        self.assertEqual(
            env_variable["env"][ssm_env_name],
            json.dumps(start_session_response)
        )

    @mock.patch("awscli.customizations.sessionmanager.check_call")
    @mock.patch("awscli.customizations.sessionmanager.check_output")
    def test_start_session_when_check_output_fails(
        self, mock_check_output, mock_check_call
    ):
        mock_check_output.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="session-manager-plugin", output="some error"
        )

        start_session_params = {
            "Target": "i-123456789"
        }
        start_session_response = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url",
        }

        self.client.start_session.return_value = start_session_response
        with self.assertRaises(subprocess.CalledProcessError):
            self.caller.invoke(
                "ssm",
                "StartSession",
                start_session_params,
                self.parsed_globals
            )

        self.client.start_session.assert_called_with(**start_session_params)
        self.client.terminate_session.assert_not_called()
        mock_check_output.assert_called_with(
            ["session-manager-plugin", "--version"], text=True
        )
        mock_check_call.assert_not_called()

    @mock.patch("awscli.customizations.sessionmanager.check_call")
    @mock.patch("awscli.customizations.sessionmanager.check_output")
    def test_start_session_when_response_not_json(
        self, mock_check_output, mock_check_call
    ):
        mock_check_output.return_value = "1.2.500.0\n"
        start_session_params = {
            "Target": "i-123456789"
        }
        start_session_response = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url",
            "para2": {"Not a json format"},
        }
        expected_env_value = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url",
        }

        ssm_env_name = "AWS_SSM_START_SESSION_RESPONSE"

        self.client.start_session.return_value = start_session_response
        rc = self.caller.invoke(
            "ssm", "StartSession", start_session_params, self.parsed_globals
        )
        self.assertEqual(rc, 0)
        self.client.start_session.assert_called_with(**start_session_params)

        mock_check_output_list = mock_check_output.call_args[0]
        self.assertEqual(
            mock_check_output_list[0], ["session-manager-plugin", "--version"]
        )

        mock_check_call_list = mock_check_call.call_args[0][0]
        self.assertEqual(
            mock_check_call_list,
            [
                "session-manager-plugin",
                ssm_env_name,
                self.region,
                "StartSession",
                self.parsed_globals.profile,
                json.dumps(start_session_params),
                self.endpoint_url,
            ],
        )
        env_variable = mock_check_call.call_args[1]
        self.assertEqual(
            env_variable["env"][ssm_env_name], json.dumps(expected_env_value)
        )

    @mock.patch("awscli.customizations.sessionmanager.check_call")
    @mock.patch("awscli.customizations.sessionmanager.check_output")
    def test_start_session_when_invalid_plugin_version(
        self, mock_check_output, mock_check_call
    ):
        mock_check_output.return_value = "InvalidVersion"

        start_session_params = {
            "Target": "i-123456789"
        }
        start_session_response = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url",
        }

        self.client.start_session.return_value = start_session_response
        self.caller.invoke(
            "ssm", "StartSession", start_session_params, self.parsed_globals
        )
        self.client.start_session.assert_called_with(**start_session_params)
        self.client.terminate_session.assert_not_called()
        mock_check_output.assert_called_with(
            ["session-manager-plugin", "--version"], text=True
        )

        mock_check_call_list = mock_check_call.call_args[0][0]
        self.assertEqual(
            mock_check_call_list,
            [
                "session-manager-plugin",
                json.dumps(start_session_response),
                self.region,
                "StartSession",
                self.parsed_globals.profile,
                json.dumps(start_session_params),
                self.endpoint_url,
            ],
        )


class TestVersionRequirement:
    version_requirement = \
        sessionmanager.VersionRequirement(min_version="1.2.497.0")

    @pytest.mark.parametrize(
        "version, expected_result",
        [
            ("2.0.0.0", True),
            ("2.1", True),
            ("2", True),
            ("1.3.1.1", True),
            ("\r\n1. 3.1.1", True),
            ("1.3.1.0", True),
            ("1.3", True),
            ("1.2.498.1", True),
            ("1.2.498", True),
            ("1.2.497.1", True),
            ("1.2.497.0", False),
            ("1.2.497", False),
            ("1.2.1.1", False),
            ("1.2.1", False),
            ("1.2", False),
            ("1.1.1.0", False),
            ("1.1.1", False),
            ("1.0.497.0", False),
            ("1.0. 497.0\r\n", False),
            ("1", False),
            ("0.3.497.0", False),
        ],
    )
    def test_meets_requirement(self, version, expected_result):
        assert expected_result == \
            self.version_requirement.meets_requirement(version)

    @pytest.mark.parametrize(
        "version, expected_result",
        [
            ("\r\n1.3.1.1", "1.3.1.1"),
            ("\r1.3 .1.1", "1.3.1.1"),
            ("1 .3.1.1", "1.3.1.1"),
            (" 1.3.1.1", "1.3.1.1"),
            ("1.3.1.1 ", "1.3.1.1"),
            (" 1.3.1.1 ", "1.3.1.1"),
            ("\n1.3.1.1 ", "1.3.1.1"),
            ("1.3.1.1\n", "1.3.1.1"),
            ("1.3\r\n.1.1", "1.3.1.1"),
            (" 1\r. 3", "1.3"),
            (" 1. 3. ", "1.3."),
            ("1.1.1\r\n", "1.1.1"),
            ("1\r", "1"),
        ],
    )
    def test_sanitize_plugin_version(self, version, expected_result):
        assert expected_result == \
            self.version_requirement._sanitize_plugin_version(version)

    @pytest.mark.parametrize(
        "version, expected_result",
        [
            ("999.99999.99.9", True),
            ("2", True),
            ("1.1.1.1", True),
            ("1.1.1", True),
            ("1.1", True),
            ("1.1.1.1.1", False),
            ("1.1.1.1.0", False),
            ("1.1.1.a", False),
            ("1.a.1.1", False),
            ("1-1.1.1", False),
            ("1.1.", False),
            ("invalid_version", False),
        ],
    )
    def test_is_valid_version(self, version, expected_result):
        assert expected_result == \
            self.version_requirement._is_valid_version(version)


class TestRecommendedMinimumVersionRequirement:
    version_requirement = sessionmanager.VersionRequirement(
        min_version="1.2.764.0"
    )

    @pytest.mark.parametrize(
        "version, expected_result",
        [
            # The first version with the capability must satisfy the check.
            ("1.2.764.0", True),
            ("1.2.764", True),
            ("1.2.764.1", True),
            ("1.2.765.0", True),
            ("1.3", True),
            ("2.0.0.0", True),
            ("\r\n1.2. 764.0", True),
            # Anything below the threshold does not.
            ("1.2.763.9", False),
            ("1.2.763", False),
            ("1.2.497.0", False),
            ("1.2", False),
            ("1", False),
            ("0.9.999.9", False),
            # Unparseable versions never satisfy the check.
            ("invalid_version", False),
            ("", False),
        ],
    )
    def test_meets_or_exceeds(self, version, expected_result):
        assert expected_result == \
            self.version_requirement.meets_or_exceeds(version)

    @pytest.mark.parametrize(
        "version, expected_result",
        [
            ("1.2.764.0", True),
            ("\r\n1.2.764.0\n", True),
            ("1.2.764", True),
            ("invalid_version", False),
            ("", False),
            ("1.1.1.1.1", False),
        ],
    )
    def test_is_valid_plugin_version(self, version, expected_result):
        assert expected_result == \
            self.version_requirement.is_valid_plugin_version(version)


class TestOutdatedPluginVersionWarning(unittest.TestCase):

    def setUp(self):
        self.session = mock.Mock(botocore.session.Session)
        self.client = mock.Mock()
        self.region = 'us-west-2'
        self.endpoint_url = 'testUrl'
        self.client.meta.region_name = self.region
        self.client.meta.endpoint_url = self.endpoint_url
        self.session.create_client.return_value = self.client
        self.caller = sessionmanager.StartSessionCaller(self.session)

        self.parsed_globals = mock.Mock()
        self.parsed_globals.profile = 'user_profile'

        self.start_session_params = {"Target": "i-123456789"}
        self.client.start_session.return_value = {
            "SessionId": "session-id",
            "TokenValue": "token-value",
            "StreamUrl": "stream-url",
        }

    def _invoke_with_plugin_version(self, plugin_version):
        with mock.patch(
            'awscli.customizations.sessionmanager.check_output'
        ) as mock_check_output, mock.patch(
            'awscli.customizations.sessionmanager.check_call'
        ) as mock_check_call, mock.patch(
            'awscli.customizations.sessionmanager.uni_print'
        ) as mock_uni_print:
            mock_check_output.return_value = plugin_version
            mock_check_call.return_value = 0
            rc = self.caller.invoke(
                'ssm', 'StartSession', self.start_session_params,
                self.parsed_globals
            )
        return rc, mock_uni_print

    def _warning_messages(self, mock_uni_print):
        return [
            call_args[0][0] for call_args in mock_uni_print.call_args_list
            if call_args[0]
            and call_args[0][0] ==
            sessionmanager.OUTDATED_PLUGIN_VERSION_MESSAGE
        ]

    def test_warns_when_plugin_version_is_below_threshold(self):
        rc, mock_uni_print = self._invoke_with_plugin_version("1.2.763.0\n")
        # The warning is advisory only and must not fail the request.
        self.assertEqual(rc, 0)
        self.assertEqual(len(self._warning_messages(mock_uni_print)), 1)
        mock_uni_print.assert_called_with(
            sessionmanager.OUTDATED_PLUGIN_VERSION_MESSAGE, sys.stderr
        )

    def test_warns_when_plugin_version_predates_env_var_support(self):
        rc, mock_uni_print = self._invoke_with_plugin_version("1.2.0.0\n")
        self.assertEqual(rc, 0)
        self.assertEqual(len(self._warning_messages(mock_uni_print)), 1)

    def test_no_warning_at_exact_threshold_version(self):
        rc, mock_uni_print = self._invoke_with_plugin_version("1.2.764.0\n")
        self.assertEqual(rc, 0)
        self.assertEqual(self._warning_messages(mock_uni_print), [])

    def test_no_warning_when_plugin_version_is_newer(self):
        rc, mock_uni_print = self._invoke_with_plugin_version("1.2.765.0\n")
        self.assertEqual(rc, 0)
        self.assertEqual(self._warning_messages(mock_uni_print), [])

    def test_no_warning_when_plugin_version_is_unparseable(self):
        rc, mock_uni_print = self._invoke_with_plugin_version(
            "not_a_version\n"
        )
        self.assertEqual(rc, 0)
        self.assertEqual(self._warning_messages(mock_uni_print), [])

    def test_outdated_plugin_still_receives_start_session_response(self):
        # An outdated plugin must keep the existing fallback behavior of
        # receiving the response directly rather than via an env var.
        with mock.patch(
            'awscli.customizations.sessionmanager.check_output'
        ) as mock_check_output, mock.patch(
            'awscli.customizations.sessionmanager.check_call'
        ) as mock_check_call, mock.patch(
            'awscli.customizations.sessionmanager.uni_print'
        ):
            mock_check_output.return_value = "1.2.0.0\n"
            mock_check_call.return_value = 0
            rc = self.caller.invoke(
                'ssm', 'StartSession', self.start_session_params,
                self.parsed_globals
            )

        self.assertEqual(rc, 0)
        check_call_args = mock_check_call.call_args[0][0]
        self.assertEqual(
            json.loads(check_call_args[1]),
            {
                "SessionId": "session-id",
                "TokenValue": "token-value",
                "StreamUrl": "stream-url",
            },
        )
