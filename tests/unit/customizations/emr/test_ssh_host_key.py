# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.testutils import mock
from tests.unit.customizations.emr import EMRBaseAWSCommandParamsTest as \
    BaseAWSCommandParamsTest


CLUSTER_ID = "j-TESTCLUSTER123"
KEY_PAIR_FILE = "/tmp/test_key.pem"
MASTER_DNS = "ec2-1-2-3-4.us-west-2.compute.amazonaws.com"


class TestSSHHostKeyVerification(BaseAWSCommandParamsTest):
    """Verify all EMR SSH commands use StrictHostKeyChecking=accept-new
    when OpenSSH supports it."""

    def _get_ssh_command(self, mock_call):
        self.assertTrue(mock_call.called)
        return mock_call.call_args[0][0]

    def _assert_accept_new(self, command):
        joined = ' '.join(command)
        self.assertIn('StrictHostKeyChecking=accept-new', joined)
        self.assertNotIn('StrictHostKeyChecking=no', joined)

    @mock.patch('subprocess.call', return_value=0)
    @mock.patch('awscli.customizations.emr.ssh._supports_accept_new',
                return_value=True)
    @mock.patch('awscli.customizations.emr.sshutils.validate_and_find_master_dns',
                return_value=MASTER_DNS)
    @mock.patch('awscli.customizations.emr.sshutils.validate_ssh_with_key_file')
    @mock.patch('awscli.customizations.emr.emrutils.which', return_value='/usr/bin/ssh')
    def test_socks_uses_accept_new(self, mock_which, mock_validate,
                                   mock_dns, mock_probe, mock_call):
        self.run_cmd(
            f'emr socks --cluster-id {CLUSTER_ID} '
            f'--key-pair-file {KEY_PAIR_FILE}', 0)
        command = self._get_ssh_command(mock_call)
        self._assert_accept_new(command)

    @mock.patch('subprocess.call', return_value=0)
    @mock.patch('awscli.customizations.emr.ssh._supports_accept_new',
                return_value=True)
    @mock.patch('awscli.customizations.emr.sshutils.validate_and_find_master_dns',
                return_value=MASTER_DNS)
    @mock.patch('awscli.customizations.emr.sshutils.validate_ssh_with_key_file')
    @mock.patch('awscli.customizations.emr.emrutils.which', return_value='/usr/bin/ssh')
    def test_ssh_uses_accept_new(self, mock_which, mock_validate,
                                 mock_dns, mock_probe, mock_call):
        self.run_cmd(
            f'emr ssh --cluster-id {CLUSTER_ID} '
            f'--key-pair-file {KEY_PAIR_FILE}', 0)
        command = self._get_ssh_command(mock_call)
        self._assert_accept_new(command)

    @mock.patch('subprocess.call', return_value=0)
    @mock.patch('awscli.customizations.emr.ssh._supports_accept_new',
                return_value=True)
    @mock.patch('awscli.customizations.emr.sshutils.validate_and_find_master_dns',
                return_value=MASTER_DNS)
    @mock.patch('awscli.customizations.emr.sshutils.validate_scp_with_key_file')
    @mock.patch('awscli.customizations.emr.emrutils.which', return_value='/usr/bin/scp')
    def test_put_uses_accept_new(self, mock_which, mock_validate,
                                 mock_dns, mock_probe, mock_call):
        self.run_cmd(
            f'emr put --cluster-id {CLUSTER_ID} '
            f'--key-pair-file {KEY_PAIR_FILE} --src /tmp/local.txt', 0)
        command = self._get_ssh_command(mock_call)
        self._assert_accept_new(command)

    @mock.patch('subprocess.call', return_value=0)
    @mock.patch('awscli.customizations.emr.ssh._supports_accept_new',
                return_value=True)
    @mock.patch('awscli.customizations.emr.sshutils.validate_and_find_master_dns',
                return_value=MASTER_DNS)
    @mock.patch('awscli.customizations.emr.sshutils.validate_scp_with_key_file')
    @mock.patch('awscli.customizations.emr.emrutils.which', return_value='/usr/bin/scp')
    def test_get_uses_accept_new(self, mock_which, mock_validate,
                                 mock_dns, mock_probe, mock_call):
        self.run_cmd(
            f'emr get --cluster-id {CLUSTER_ID} '
            f'--key-pair-file {KEY_PAIR_FILE} --src /remote/file.txt', 0)
        command = self._get_ssh_command(mock_call)
        self._assert_accept_new(command)


class TestSSHFallbackOnOldOpenSSH(BaseAWSCommandParamsTest):
    """Verify fallback to StrictHostKeyChecking=no when accept-new
    is not supported, with a warning."""

    def _get_ssh_command(self, mock_call):
        self.assertTrue(mock_call.called)
        return mock_call.call_args[0][0]

    @mock.patch('subprocess.call', return_value=0)
    @mock.patch('awscli.customizations.emr.ssh._supports_accept_new',
                return_value=False)
    @mock.patch('awscli.customizations.emr.sshutils.validate_and_find_master_dns',
                return_value=MASTER_DNS)
    @mock.patch('awscli.customizations.emr.sshutils.validate_ssh_with_key_file')
    @mock.patch('awscli.customizations.emr.emrutils.which', return_value='/usr/bin/ssh')
    def test_falls_back_to_no_with_warning(self, mock_which, mock_validate,
                                           mock_dns, mock_probe, mock_call):
        _, stderr, _ = self.run_cmd(
            f'emr ssh --cluster-id {CLUSTER_ID} '
            f'--key-pair-file {KEY_PAIR_FILE}', 0)
        command = self._get_ssh_command(mock_call)
        joined = ' '.join(command)
        self.assertIn('StrictHostKeyChecking=no', joined)
        self.assertNotIn('StrictHostKeyChecking=accept-new', joined)
        self.assertIn('Upgrade to OpenSSH 7.6+', stderr)


class TestSSHOptionsPassthrough(BaseAWSCommandParamsTest):
    """Verify --ssh-options are passed through and can override defaults."""

    def _get_ssh_command(self, mock_call):
        self.assertTrue(mock_call.called)
        return mock_call.call_args[0][0]

    @mock.patch('subprocess.call', return_value=0)
    @mock.patch('awscli.customizations.emr.sshutils.validate_and_find_master_dns',
                return_value=MASTER_DNS)
    @mock.patch('awscli.customizations.emr.sshutils.validate_ssh_with_key_file')
    @mock.patch('awscli.customizations.emr.emrutils.which', return_value='/usr/bin/ssh')
    def test_ssh_options_override_strict_host_key(self, mock_which,
                                                  mock_validate,
                                                  mock_dns, mock_call):
        self.run_cmd(
            f'emr ssh --cluster-id {CLUSTER_ID} --key-pair-file {KEY_PAIR_FILE} '
            '--ssh-options StrictHostKeyChecking=no', 0)
        command = self._get_ssh_command(mock_call)
        joined = ' '.join(command)
        self.assertIn('StrictHostKeyChecking=no', joined)
        self.assertNotIn('StrictHostKeyChecking=accept-new', joined)

    @mock.patch('subprocess.call', return_value=0)
    @mock.patch('awscli.customizations.emr.ssh._supports_accept_new',
                return_value=True)
    @mock.patch('awscli.customizations.emr.sshutils.validate_and_find_master_dns',
                return_value=MASTER_DNS)
    @mock.patch('awscli.customizations.emr.sshutils.validate_ssh_with_key_file')
    @mock.patch('awscli.customizations.emr.emrutils.which', return_value='/usr/bin/ssh')
    def test_ssh_options_additional_options(self, mock_which, mock_validate,
                                           mock_dns, mock_probe, mock_call):
        self.run_cmd(
            f'emr ssh --cluster-id {CLUSTER_ID} --key-pair-file {KEY_PAIR_FILE} '
            '--ssh-options ConnectTimeout=30', 0)
        command = self._get_ssh_command(mock_call)
        joined = ' '.join(command)
        self.assertIn('StrictHostKeyChecking=accept-new', joined)
        self.assertIn('ConnectTimeout=30', joined)

    @mock.patch('subprocess.call', return_value=0)
    @mock.patch('awscli.customizations.emr.sshutils.validate_and_find_master_dns',
                return_value=MASTER_DNS)
    @mock.patch('awscli.customizations.emr.sshutils.validate_scp_with_key_file')
    @mock.patch('awscli.customizations.emr.emrutils.which', return_value='/usr/bin/scp')
    def test_put_options_override(self, mock_which, mock_validate,
                                  mock_dns, mock_call):
        self.run_cmd(
            f'emr put --cluster-id {CLUSTER_ID} --key-pair-file {KEY_PAIR_FILE} '
            '--src /tmp/f.txt '
            '--ssh-options StrictHostKeyChecking=no', 0)
        command = self._get_ssh_command(mock_call)
        joined = ' '.join(command)
        self.assertIn('StrictHostKeyChecking=no', joined)
        self.assertNotIn('StrictHostKeyChecking=accept-new', joined)
