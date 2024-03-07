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

from tests.unit.customizations.emr import EMRBaseAWSCommandParamsTest as \
    BaseAWSCommandParamsTest


class TestModifyClusterAttributes(BaseAWSCommandParamsTest):
    prefix = 'emr modify-cluster-attributes'

    def test_visible_to_all(self):
        args = ' --cluster-id j-ABC123456 --visible-to-all-users'
        cmdline = self.prefix + args
        result = {'JobFlowIds': ['j-ABC123456'], 'VisibleToAllUsers': True}
        self.assert_params_for_cmd(cmdline, result)

    def test_no_visible_to_all(self):
        args = ' --cluster-id j-ABC123456 --no-visible-to-all-users'
        cmdline = self.prefix + args
        result = {'JobFlowIds': ['j-ABC123456'], 'VisibleToAllUsers': False}
        self.assert_params_for_cmd(cmdline, result)

    def test_termination_protected(self):
        args = ' --cluster-id j-ABC123456 --termination-protected'
        cmdline = self.prefix + args
        result = {'JobFlowIds': ['j-ABC123456'], 'TerminationProtected': True}
        self.assert_params_for_cmd(cmdline, result)

    def test_no_termination_protected(self):
        args = ' --cluster-id j-ABC123456 --no-termination-protected'
        cmdline = self.prefix + args
        result = {'JobFlowIds': ['j-ABC123456'], 'TerminationProtected': False}
        self.assert_params_for_cmd(cmdline, result)

    def test_no_auto_terminate(self):
        args = ' --cluster-id j-ABC123456 --no-auto-terminate'
        cmdline = self.prefix + args
        result = {'JobFlowIds': ['j-ABC123456'], 'KeepJobFlowAliveWhenNoSteps': True}
        self.assert_params_for_cmd(cmdline, result)

    def test_auto_terminate(self):
        args = ' --cluster-id j-ABC123456 --auto-terminate'
        cmdline = self.prefix + args
        result = {'JobFlowIds': ['j-ABC123456'], 'KeepJobFlowAliveWhenNoSteps': False}

    def test_unhealthy_node_replacement(self):
        args = ' --cluster-id j-ABC123456 --unhealthy-node-replacement'
        cmdline = self.prefix + args
        result = {'JobFlowIds': ['j-ABC123456'], 'UnhealthyNodeReplacement': True}
        self.assert_params_for_cmd(cmdline, result)

    def test_no_unhealthy_node_replacement(self):
        args = ' --cluster-id j-ABC123456 --no-unhealthy-node-replacement'
        cmdline = self.prefix + args
        result = {'JobFlowIds': ['j-ABC123456'], 'UnhealthyNodeReplacement': False}
        self.assert_params_for_cmd(cmdline, result)

    def test_visible_to_all_and_no_visible_to_all(self):
        args = ' --cluster-id j-ABC123456 --no-visible-to-all-users'\
               ' --visible-to-all-users'
        cmdline = self.prefix + args
        expected_error_msg = (
            '\naws: error: You cannot specify both --visible-to-all-users '
            'and --no-visible-to-all-users options together.\n')
        result = self.run_cmd(cmdline, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_temination_protected_and_no_termination_protected(self):
        args = ' --cluster-id j-ABC123456 --no-termination-protected'\
               ' --termination-protected'
        cmdline = self.prefix + args
        expected_error_msg = (
            '\naws: error: You cannot specify both --termination-protected '
            'and --no-termination-protected options together.\n')
        result = self.run_cmd(cmdline, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_auto_terminate_and_no_auto_terminate(self):
        args = ' --cluster-id j-ABC123456 --auto-terminate'\
               ' --no-auto-terminate'
        cmdline = self.prefix + args
        expected_error_msg = (
            '\naws: error: You cannot specify both --auto-terminate '
            'and --no-auto-terminate options together.\n')
        result = self.run_cmd(cmdline, 255)
        self.assertEqual(expected_error_msg, result[1])

    def test_can_set_multiple_attributes(self):
        args = ' --cluster-id j-ABC123456 --termination-protected'\
               ' --visible-to-all-users --unhealthy-node-replacement'
        cmdline = self.prefix + args
        result_set_termination_protection = {
            'JobFlowIds': ['j-ABC123456'], 'TerminationProtected': True}
        result_set_visible_to_all_users = {
            'JobFlowIds': ['j-ABC123456'], 'VisibleToAllUsers': True}
        result_set_unhealty_node_replacement = {
            'JobFlowIds': ['j-ABC123456'], 'UnhealthyNodeReplacement': True}
        self.run_cmd(cmdline)
        self.assertDictEqual(
            self.operations_called[0][1], result_set_visible_to_all_users)
        self.assertDictEqual(
            self.operations_called[1][1], result_set_termination_protection)
        self.assertDictEqual(
            self.operations_called[2][1], result_set_unhealty_node_replacement)

    def test_can_set_multiple_attributes_with_no(self):
        args = ' --cluster-id j-ABC123456 --termination-protected'\
               ' --no-visible-to-all-users --unhealthy-node-replacement'
        cmdline = self.prefix + args
        result_set_termination_protection = {
            'JobFlowIds': ['j-ABC123456'], 'TerminationProtected': True}
        result_set_visible_to_all_users = {
            'JobFlowIds': ['j-ABC123456'], 'VisibleToAllUsers': False}
        result_set_unhealty_node_replacement = {
            'JobFlowIds': ['j-ABC123456'], 'UnhealthyNodeReplacement': True}
        self.run_cmd(cmdline)
        self.assertDictEqual(
            self.operations_called[0][1], result_set_visible_to_all_users)
        self.assertDictEqual(
            self.operations_called[1][1], result_set_termination_protection)
        self.assertDictEqual(
            self.operations_called[2][1], result_set_unhealty_node_replacement)

    def test_at_least_one_option(self):
        args = ' --cluster-id j-ABC123456'
        cmdline = self.prefix + args
        expected_error_msg = (
            '\naws: error: Must specify one of the following boolean options: '
            '--visible-to-all-users|--no-visible-to-all-users, '
            '--termination-protected|--no-termination-protected, '
            '--auto-terminate|--no-auto-terminate, '
            '--unhealthy-node-replacement|--no-unhealthy-node-replacement.\n')
        result = self.run_cmd(cmdline, 255)
        self.assertEqual(expected_error_msg, result[1])

if __name__ == "__main__":
    unittest.main()
