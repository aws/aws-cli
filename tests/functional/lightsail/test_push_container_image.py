# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import mock
import errno
import json
import awscli

from awscli.testutils import BaseAWSCommandParamsTest
from awscli.testutils import BaseAWSHelpOutputTest


class TestPushContainerImageTest(BaseAWSCommandParamsTest):

    def get_push_container_command(self, extra_params):
        cmd = (
            'lightsail '
            'push-container-image '
            '--service-name=dyservicev3 '
            '--label david16  '
            '--image hello:latest '
        )
        if extra_params is not None:
            cmd += extra_params
        return cmd

    def assert_expected_input_options(self, mock_subprocess_run):
        self.assertEqual(['lightsailctl', '--plugin', '--input-stdin'],
                         mock_subprocess_run.call_args[0][0])

    def assert_expected_input_version(self, actual_input_version):
        self.assertEqual('1', actual_input_version)

    def assert_expected_operation(self, actual_operation):
        self.assertEqual('PushContainerImage', actual_operation)

    def assert_expected_payload(self, actual_payload):
        self.assertEqual(
            {
                'service': 'dyservicev3',
                'image': 'hello:latest',
                'label': 'david16',
            },
            actual_payload
        )

    def assert_expected_configuration(self,
                                      configuration_payload,
                                      **expected_options):
        for option, value in expected_options.items():
            self.assertEqual(configuration_payload[option], value)

    @mock.patch('awscli.customizations.lightsail.'
                'push_container_image.subprocess.run')
    def test_start_lightsailctl_failed(
            self, mock_subprocess_run):
        cmdline = 'lightsail ' \
                  '--region us-west-2 ' \
                  '--endpoint-url https://override.custom.endpoint.com ' \
                  'push-container-image ' \
                  '--service-name=dyservicev3 ' \
                  '--label david16  '
        mock_subprocess_run.side_effect = OSError(errno.ENOENT, 'some error')
        response = self.run_cmd(cmdline, expected_rc=252)
        self.assertEqual(response[2], 252)

    @mock.patch('awscli.customizations.lightsail.'
                'push_container_image.subprocess.run')
    def test_start_lightsailctl_success(
            self, mock_subprocess_run):

        cmdline = self.get_push_container_command(None)

        mock_subprocess_run.return_value = 0
        response = self.run_cmd(cmdline)

        self.assert_expected_input_options(mock_subprocess_run)

        actual_input = json.loads(
            mock_subprocess_run.call_args[1]['input'])
        self.assert_expected_input_version(actual_input['inputVersion'])
        self.assert_expected_operation(actual_input['operation'])
        self.assert_expected_payload(actual_input['payload'])
        self.assert_expected_configuration(actual_input['configuration'],
                                           debug=False,
                                           paginate=True,
                                           region='us-east-1',
                                           doNotSignRequest=False,
                                           readTimeout=60,
                                           connectTimeout=60,
                                           cliVersion=awscli.__version__)
        self.assertEqual(response[2], 0)

    @mock.patch('awscli.customizations.lightsail.'
                'push_container_image.subprocess.run')
    def test_start_lightsailctl_with_region_success(
            self, mock_subprocess_run):

        cmdline = self.get_push_container_command('--region us-west-2')

        mock_subprocess_run.return_value = 0
        response = self.run_cmd(cmdline)

        self.assert_expected_input_options(mock_subprocess_run)

        actual_input = json.loads(
            mock_subprocess_run.call_args[1]['input'])
        self.assert_expected_input_version(actual_input['inputVersion'])
        self.assert_expected_operation(actual_input['operation'])
        self.assert_expected_payload(actual_input['payload'])
        self.assert_expected_configuration(actual_input['configuration'],
                                           region='us-west-2')
        self.assertEqual(response[2], 0)

    @mock.patch('awscli.customizations.lightsail.'
                'push_container_image.subprocess.run')
    def test_start_lightsailctl_with_url_success(
            self, mock_subprocess_run):

        extra_param = (
            '--endpoint-url https://test.amazon.com '
        )
        cmdline = self.get_push_container_command(extra_param)

        mock_subprocess_run.return_value = 0
        response = self.run_cmd(cmdline)

        self.assert_expected_input_options(mock_subprocess_run)

        actual_input = json.loads(
            mock_subprocess_run.call_args[1]['input'])
        self.assert_expected_input_version(actual_input['inputVersion'])
        self.assert_expected_operation(actual_input['operation'])
        self.assert_expected_payload(actual_input['payload'])
        self.assert_expected_configuration(actual_input['configuration'],
                                           endpoint='https://test.amazon.com')
        self.assertEqual(response[2], 0)

    @mock.patch('awscli.customizations.lightsail.'
                'push_container_image.subprocess.run')
    def test_start_lightsailctl_with_no_verify_ssl_ssuccess(
            self, mock_subprocess_run):

        extra_param = (
            '--no-verify-ssl '
        )
        cmdline = self.get_push_container_command(extra_param)

        mock_subprocess_run.return_value = 0
        response = self.run_cmd(cmdline)

        self.assert_expected_input_options(mock_subprocess_run)

        actual_input = json.loads(
            mock_subprocess_run.call_args[1]['input'])
        self.assert_expected_input_version(actual_input['inputVersion'])
        self.assert_expected_operation(actual_input['operation'])
        self.assert_expected_payload(actual_input['payload'])
        self.assert_expected_configuration(actual_input['configuration'],
                                           doNotVerifySSL=True)
        self.assertEqual(response[2], 0)

    @mock.patch('awscli.customizations.lightsail.'
                'push_container_image.subprocess.run')
    def test_start_lightsailctl_with_no_sign_request_ssuccess(
            self, mock_subprocess_run):

        extra_param = (
            '--no-sign-request '
        )
        cmdline = self.get_push_container_command(extra_param)

        mock_subprocess_run.return_value = 0
        response = self.run_cmd(cmdline)

        self.assert_expected_input_options(mock_subprocess_run)

        actual_input = json.loads(
            mock_subprocess_run.call_args[1]['input'])
        self.assert_expected_input_version(actual_input['inputVersion'])
        self.assert_expected_operation(actual_input['operation'])
        self.assert_expected_payload(actual_input['payload'])
        self.assert_expected_configuration(actual_input['configuration'],
                                           doNotSignRequest=True)
        self.assertEqual(response[2], 0)

    @mock.patch('awscli.customizations.lightsail.'
                'push_container_image.subprocess.run')
    def test_start_lightsailctl_with_no_paginate_ssuccess(
            self, mock_subprocess_run):

        extra_param = (
            '--no-paginate '
        )
        cmdline = self.get_push_container_command(extra_param)

        mock_subprocess_run.return_value = 0
        response = self.run_cmd(cmdline)

        self.assert_expected_input_options(mock_subprocess_run)

        actual_input = json.loads(
            mock_subprocess_run.call_args[1]['input'])
        self.assert_expected_input_version(actual_input['inputVersion'])
        self.assert_expected_operation(actual_input['operation'])
        self.assert_expected_payload(actual_input['payload'])
        self.assert_expected_configuration(actual_input['configuration'],
                                           paginate=False)
        self.assertEqual(response[2], 0)

    @mock.patch('awscli.customizations.lightsail.'
                'push_container_image.subprocess.run')
    def test_start_lightsailctl_with_output_json_ssuccess(
            self, mock_subprocess_run):

        extra_param = (
            '--output json'
        )
        cmdline = self.get_push_container_command(extra_param)

        mock_subprocess_run.return_value = 0
        response = self.run_cmd(cmdline)

        self.assert_expected_input_options(mock_subprocess_run)

        actual_input = json.loads(
            mock_subprocess_run.call_args[1]['input'])
        self.assert_expected_input_version(actual_input['inputVersion'])
        self.assert_expected_operation(actual_input['operation'])
        self.assert_expected_payload(actual_input['payload'])
        self.assert_expected_configuration(actual_input['configuration'],
                                           output='json')
        self.assertEqual(response[2], 0)

    @mock.patch('awscli.customizations.lightsail.'
                'push_container_image.subprocess.run')
    def test_start_lightsailctl_with_read_timeout_ssuccess(
            self, mock_subprocess_run):

        extra_param = (
            '--cli-read-timeout 70 '
        )
        cmdline = self.get_push_container_command(extra_param)

        mock_subprocess_run.return_value = 0
        response = self.run_cmd(cmdline)

        self.assert_expected_input_options(mock_subprocess_run)

        actual_input = json.loads(
            mock_subprocess_run.call_args[1]['input'])
        self.assert_expected_input_version(actual_input['inputVersion'])
        self.assert_expected_operation(actual_input['operation'])
        self.assert_expected_payload(actual_input['payload'])
        self.assert_expected_configuration(actual_input['configuration'],
                                           readTimeout=70)
        self.assertEqual(response[2], 0)

    @mock.patch('awscli.customizations.lightsail.'
                'push_container_image.subprocess.run')
    def test_start_lightsailctl_with_con_timeout_ssuccess(
            self, mock_subprocess_run):

        extra_param = (
            '--cli-connect-timeout 80 '
        )
        cmdline = self.get_push_container_command(extra_param)

        mock_subprocess_run.return_value = 0
        response = self.run_cmd(cmdline)

        self.assert_expected_input_options(mock_subprocess_run)

        actual_input = json.loads(
            mock_subprocess_run.call_args[1]['input'])
        self.assert_expected_input_version(actual_input['inputVersion'])
        self.assert_expected_operation(actual_input['operation'])
        self.assert_expected_payload(actual_input['payload'])
        self.assert_expected_configuration(actual_input['configuration'],
                                           connectTimeout=80)
        self.assertEqual(response[2], 0)

    @mock.patch('awscli.customizations.lightsail.'
                'push_container_image.subprocess.run')
    def test_start_lightsailctl_with_cabundle_ssuccess(
            self, mock_subprocess_run):

        extra_param = (
            '--ca-bundle testPEM'
        )
        cmdline = self.get_push_container_command(extra_param)

        mock_subprocess_run.return_value = 0
        response = self.run_cmd(cmdline)

        self.assert_expected_input_options(mock_subprocess_run)

        actual_input = json.loads(
            mock_subprocess_run.call_args[1]['input'])
        self.assert_expected_input_version(actual_input['inputVersion'])
        self.assert_expected_operation(actual_input['operation'])
        self.assert_expected_payload(actual_input['payload'])
        self.assert_expected_configuration(actual_input['configuration'],
                                           caBundle='testPEM')
        self.assertEqual(response[2], 0)


class TestHelpOutput(BaseAWSHelpOutputTest):

    def test_lightsailctl_output(self):
        self.driver.main(['lightsail', 'push-container-image', 'help'])
        self.assert_contains('push-container-image')
