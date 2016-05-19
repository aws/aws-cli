# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.customizations.emr import sshutils
from awscli.customizations.emr import exceptions
from awscli.testutils import unittest


class TestSSHUtils(unittest.TestCase):

    @mock.patch('awscli.customizations.emr.sshutils.emrutils')
    def test_validate_and_find_master_dns_waits(self, emrutils):
        emrutils.get_cluster_state.return_value = 'STARTING'
        session = mock.Mock()
        client = mock.Mock()
        emrutils.get_client.return_value = client

        sshutils.validate_and_find_master_dns(session, None, 'cluster-id')

        # We should have:
        # 1. Waiter for the cluster to be running.
        client.get_waiter.assert_called_with('cluster_running')
        client.get_waiter.return_value.wait.assert_called_with(
            ClusterId='cluster-id')

        # 2. Found the master public DNS
        self.assertTrue(emrutils.find_master_dns.called)

    @mock.patch('awscli.customizations.emr.sshutils.emrutils')
    def test_cluster_in_terminated_states(self, emrutils):
        emrutils.get_cluster_state.return_value = 'TERMINATED'
        with self.assertRaises(exceptions.ClusterTerminatedError):
            sshutils.validate_and_find_master_dns(
                mock.Mock(), None, 'cluster-id')

    @mock.patch('awscli.customizations.emr.sshutils.emrutils')
    def test_ssh_scp_key_file_format(self, emrutils):
        def which_side_effect(program):
            if program == 'ssh' or program == 'scp':
                return '/some/path'
        emrutils.which.side_effect = which_side_effect

        key_file1 = 'key.abc'
        sshutils.validate_ssh_with_key_file(key_file1)
        sshutils.validate_scp_with_key_file(key_file1)

        key_file2 = 'key'
        sshutils.validate_ssh_with_key_file(key_file2)
        sshutils.validate_scp_with_key_file(key_file2)
