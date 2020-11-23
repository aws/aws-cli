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

import copy
import json
import mock

from awscli.testutils import BaseAWSCommandParamsTest, unittest
from awscli.customizations.emrcontainers.base36 import Base36
from awscli.customizations.emrcontainers.constants \
    import TRUST_POLICY_STATEMENT_FORMAT, \
    TRUST_POLICY_STATEMENT_ALREADY_EXISTS, \
    TRUST_POLICY_UPDATE_SUCCESSFUL


def json_matches(first, second):
    return json.dumps(first, sort_keys=True) == json.dumps(second,
                                                           sort_keys=True)


class TestUpdateAssumeRolePolicy(BaseAWSCommandParamsTest):
    cluster_name = 'test-cluster'
    namespace = 'test'
    role_name = 'myrole'
    account_id = '123456789012'
    oidc_provider = 'oidc-provider/id/test'

    base36_encoded_role_name = Base36().encode(role_name)
    expected_statement = TRUST_POLICY_STATEMENT_FORMAT % {
        "AWS_ACCOUNT_ID": account_id,
        "OIDC_PROVIDER": oidc_provider,
        "NAMESPACE": namespace,
        "BASE36_ENCODED_ROLE_NAME": base36_encoded_role_name
    }

    command = 'emr-containers update-role-trust-policy --cluster-name=%s ' \
              '--namespace=%s --role-name=%s' % (cluster_name, namespace,
                                                 role_name)

    def setUp(self):
        super(TestUpdateAssumeRolePolicy, self).setUp()

        self.policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::123456789012:root"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }

        self.expected_policy_document = copy.deepcopy(self.policy_document)
        self.expected_policy_document.get("Statement").append(
            json.loads(self.expected_statement))

    # Assert the call to update trust policy of the role
    def assert_trust_policy_updated(self, cmd_output):
        self.assertTrue(TRUST_POLICY_UPDATE_SUCCESSFUL % self.role_name
                        in cmd_output)

        # Check if UpdateAssumeRolePolicy was invoked
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(self.operations_called[0][0].name,
                         'UpdateAssumeRolePolicy')
        self.assertEqual(self.operations_called[0][1]['RoleName'],
                         self.role_name)

        self.assertTrue(json_matches(json.loads(
            self.operations_called[0][1]['PolicyDocument']),
            self.expected_policy_document))

    # Use case: Expected trust policy does not exist
    # Expected results: Operation is performed by client
    # to update the trust policy in expected format
    @mock.patch('awscli.customizations.emrcontainers.'
                'iam.IAM.get_assume_role_policy')
    @mock.patch('awscli.customizations.emrcontainers.'
                'eks.EKS.get_oidc_issuer_id')
    @mock.patch('awscli.customizations.emrcontainers.'
                'eks.EKS.get_account_id')
    def test_trust_policy_does_not_exist(self, get_account_id_patch,
                                         get_oidc_issuer_id_patch,
                                         get_assume_role_policy_patch):
        get_assume_role_policy_patch.return_value = self.policy_document
        get_oidc_issuer_id_patch.return_value = self.oidc_provider
        get_account_id_patch.return_value = self.account_id

        output = self.run_cmd(self.command, expected_rc=0)
        self.assert_trust_policy_updated(output[0])

    # Use case: Expected trust policy exists but the condition section
    # has an additional condition
    # Expected results: Operation is performed by client to update
    # the trust policy in expected format
    @mock.patch('awscli.customizations.emrcontainers.'
                'iam.IAM.get_assume_role_policy')
    @mock.patch('awscli.customizations.emrcontainers.'
                'eks.EKS.get_oidc_issuer_id')
    @mock.patch('awscli.customizations.emrcontainers.'
                'eks.EKS.get_account_id')
    def test_trust_policy_exists_with_more_keys(self, get_account_id_patch,
                                                get_oidc_issuer_id_patch,
                                                get_assume_role_policy_patch):
        statement_with_additional_condition_key = json.loads(
            self.expected_statement)
        statement_with_additional_condition_key.get("Condition").get(
            "StringLike")["test:key"] = "value"
        self.policy_document.get("Statement").append(
            statement_with_additional_condition_key)

        self.expected_policy_document = copy.deepcopy(self.policy_document)
        self.expected_policy_document.get("Statement").append(json.loads(
            self.expected_statement))

        get_assume_role_policy_patch.return_value = self.policy_document
        get_oidc_issuer_id_patch.return_value = self.oidc_provider
        get_account_id_patch.return_value = self.account_id

        output = self.run_cmd(self.command, expected_rc=0)
        self.assert_trust_policy_updated(output[0])

    # Use case: Initial trust policy document does not have Statements section
    # Expected results: Operation is performed by client to update
    # the trust policy in expected format
    @mock.patch('awscli.customizations.emrcontainers.'
                'iam.IAM.get_assume_role_policy')
    @mock.patch('awscli.customizations.emrcontainers.'
                'eks.EKS.get_oidc_issuer_id')
    @mock.patch('awscli.customizations.emrcontainers.'
                'eks.EKS.get_account_id')
    def test_policy_document_has_missing_key(self,
                                             get_account_id_patch,
                                             get_oidc_issuer_id_patch,
                                             get_assume_role_policy_patch):
        del self.policy_document["Statement"]

        self.expected_policy_document = copy.deepcopy(self.policy_document)
        self.expected_policy_document["Statement"] = [json.loads(
            self.expected_statement)]

        get_assume_role_policy_patch.return_value = self.policy_document
        get_oidc_issuer_id_patch.return_value = self.oidc_provider
        get_account_id_patch.return_value = self.account_id

        output = self.run_cmd(self.command, expected_rc=0)
        self.assert_trust_policy_updated(output[0])

    # Use case: Initial trust policy document has empty Statements section
    # Expected results: Operation is performed by client to update
    # the trust policy in expected format
    @mock.patch('awscli.customizations.emrcontainers.'
                'iam.IAM.get_assume_role_policy')
    @mock.patch('awscli.customizations.emrcontainers.'
                'eks.EKS.get_oidc_issuer_id')
    @mock.patch('awscli.customizations.emrcontainers.'
                'eks.EKS.get_account_id')
    def test_policy_document_has_empty_statements(self,
                                                  get_account_id_patch,
                                                  get_oidc_issuer_id_patch,
                                                  get_assume_role_policy_patch):
        del self.policy_document.get("Statement")[:]

        self.expected_policy_document = copy.deepcopy(self.policy_document)
        self.expected_policy_document.get("Statement").append(json.loads(
            self.expected_statement))

        get_assume_role_policy_patch.return_value = self.policy_document
        get_oidc_issuer_id_patch.return_value = self.oidc_provider
        get_account_id_patch.return_value = self.account_id

        output = self.run_cmd(self.command, expected_rc=0)
        self.assert_trust_policy_updated(output[0])

    # Use case: Expected trust policy does not exist and user performs a dry run
    # Expected results: No operation is performed by client
    # The command should print the expected policy document to stdout
    @mock.patch('awscli.customizations.emrcontainers.'
                'iam.IAM.get_assume_role_policy')
    @mock.patch('awscli.customizations.emrcontainers.'
                'eks.EKS.get_oidc_issuer_id')
    @mock.patch('awscli.customizations.emrcontainers.'
                'eks.EKS.get_account_id')
    def test_trust_policy_does_not_exist_dry_run(self, get_account_id_patch,
                                                 get_oidc_issuer_id_patch,
                                                 get_assume_role_policy_patch):
        get_assume_role_policy_patch.return_value = self.policy_document
        get_oidc_issuer_id_patch.return_value = self.oidc_provider
        get_account_id_patch.return_value = self.account_id

        output = self.run_cmd(self.command + " --dry-run", expected_rc=0)
        self.assertEqual(len(self.operations_called), 0)
        self.assertTrue(json_matches(json.loads(output[0]),
                                     self.expected_policy_document))

    # Use case: Expected trust policy already exists
    # Expected results: No operation is performed by client
    # The command should print that the trust policy statement already exists
    @mock.patch('awscli.customizations.emrcontainers.'
                'iam.IAM.get_assume_role_policy')
    @mock.patch('awscli.customizations.emrcontainers.'
                'eks.EKS.get_oidc_issuer_id')
    @mock.patch('awscli.customizations.emrcontainers.'
                'eks.EKS.get_account_id')
    def test_trust_policy_exists(self, get_account_id_patch,
                                 get_oidc_issuer_id_patch,
                                 get_assume_role_policy_patch):
        self.policy_document = self.expected_policy_document

        get_assume_role_policy_patch.return_value = self.policy_document
        get_oidc_issuer_id_patch.return_value = self.oidc_provider
        get_account_id_patch.return_value = self.account_id

        output = self.run_cmd(self.command, expected_rc=0)
        self.assertEqual(len(self.operations_called), 0)
        self.assertTrue(TRUST_POLICY_STATEMENT_ALREADY_EXISTS % self.role_name
                        in output[0])


if __name__ == "__main__":
    unittest.main()
