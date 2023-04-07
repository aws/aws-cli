# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import base64
from datetime import datetime
import json
import os

from awscli.testutils import mock
from awscli.testutils import BaseAWSCommandParamsTest
from awscli.compat import urlparse


class TestGetTokenCommand(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestGetTokenCommand, self).setUp()
        self.cluster_name = 'MyCluster'
        self.role_arn = 'arn:aws:iam::012345678910:role/RoleArn'
        self.access_key = 'ABCDEFGHIJKLMNOPQRST'
        self.secret_key = 'TSRQPONMLKJUHGFEDCBA'
        self.session_token = 'TOKENTOKENTOKENTOKEN'
        self.environ['AWS_ACCESS_KEY_ID'] = self.access_key
        self.environ['AWS_SECRET_ACCESS_KEY'] = self.secret_key
        self.expected_token_prefix = 'k8s-aws-v1.'

    def run_get_token(self, cmd):
        response, _, _ = self.run_cmd(cmd)
        return json.loads(response)

    def assert_url_correct(
        self,
        response,
        expected_endpoint='sts.amazonaws.com',
        expected_signing_region='us-east-1',
        has_session_token=False,
    ):
        url = self._get_url(response)
        url_components = urlparse.urlparse(url)
        self.assertEqual(url_components.netloc, expected_endpoint)
        parsed_qs = urlparse.parse_qs(url_components.query)
        self.assertIn(
            expected_signing_region, parsed_qs['X-Amz-Credential'][0]
        )
        if has_session_token:
            self.assertEqual(
                [self.session_token], parsed_qs['X-Amz-Security-Token']
            )
        else:
            self.assertNotIn('X-Amz-Security-Token', parsed_qs)

        self.assertIn(self.access_key, parsed_qs['X-Amz-Credential'][0])
        self.assertIn('x-k8s-aws-id', parsed_qs['X-Amz-SignedHeaders'][0])

    def _get_url(self, response):
        token = response['status']['token']
        b64_token = token[len(self.expected_token_prefix) :].encode()
        missing_padding = len(b64_token) % 4
        if missing_padding:
            b64_token += b'=' * (4 - missing_padding)
        return base64.urlsafe_b64decode(b64_token).decode()

    def set_kubernetes_exec_info(self, api_version):
        # Set KUBERNETES_EXEC_INFO env var with default payload and provided
        # api version
        self.environ['KUBERNETES_EXEC_INFO'] = (
            '{"kind":"ExecCredential",'
            f'"apiVersion":"client.authentication.k8s.io/{api_version}",'
            '"spec":{"interactive":true}}'
        )

    @mock.patch('awscli.customizations.eks.get_token.datetime')
    def test_get_token(self, mock_datetime):
        mock_datetime.utcnow.return_value = datetime(2019, 10, 23, 23, 0, 0, 0)
        cmd = 'eks get-token --cluster-name %s' % self.cluster_name
        response = self.run_get_token(cmd)
        self.assertEqual(
            response,
            {
                "kind": "ExecCredential",
                "apiVersion": "client.authentication.k8s.io/v1beta1",
                "spec": {},
                "status": {
                    "expirationTimestamp": "2019-10-23T23:14:00Z",
                    "token": mock.ANY,  # This is asserted in later cases
                },
            },
        )

    @mock.patch('awscli.customizations.eks.get_token.datetime')
    def test_query_nested_object(self, mock_datetime):
        mock_datetime.utcnow.return_value = datetime(2019, 10, 23, 23, 0, 0, 0)
        cmd = 'eks get-token --cluster-name %s' % self.cluster_name
        cmd += ' --query status'
        response = self.run_get_token(cmd)
        self.assertEqual(
            response,
            {
                "expirationTimestamp": "2019-10-23T23:14:00Z",
                "token": mock.ANY,  # This is asserted in later cases
            },
        )

    def test_query_value(self):
        cmd = 'eks get-token --cluster-name %s' % self.cluster_name
        cmd += ' --query apiVersion'
        response = self.run_get_token(cmd)
        self.assertEqual(
            response, "client.authentication.k8s.io/v1beta1",
        )

    @mock.patch('awscli.customizations.eks.get_token.datetime')
    def test_output_text(self, mock_datetime):
        mock_datetime.utcnow.return_value = datetime(2019, 10, 23, 23, 0, 0, 0)
        cmd = 'eks get-token --cluster-name %s' % self.cluster_name
        cmd += ' --output text'
        stdout, _, _ = self.run_cmd(cmd)
        self.assertIn("ExecCredential", stdout)
        self.assertIn("client.authentication.k8s.io/v1beta1", stdout)
        self.assertIn("2019-10-23T23:14:00Z", stdout)

    @mock.patch('awscli.customizations.eks.get_token.datetime')
    def test_output_table(self, mock_datetime):
        mock_datetime.utcnow.return_value = datetime(2019, 10, 23, 23, 0, 0, 0)
        cmd = 'eks get-token --cluster-name %s' % self.cluster_name
        cmd += ' --output table'
        stdout, _, _ = self.run_cmd(cmd)
        self.assertIn("ExecCredential", stdout)
        self.assertIn("client.authentication.k8s.io/v1beta1", stdout)
        self.assertIn("2019-10-23T23:14:00Z", stdout)

    def test_url(self):
        cmd = 'eks get-token --cluster-name %s' % self.cluster_name
        response = self.run_get_token(cmd)
        self.assert_url_correct(response)

    def test_url_with_region(self):
        cmd = 'eks get-token --cluster-name %s' % self.cluster_name
        cmd += ' --region us-west-2'
        response = self.run_get_token(cmd)
        # Even though us-west-2 was specified, we should still only be
        # signing for the global endpoint.
        self.assert_url_correct(
            response,
            expected_endpoint='sts.amazonaws.com',
            expected_signing_region='us-east-1',
        )

    def test_url_with_arn(self):
        cmd = 'eks get-token --cluster-name %s' % self.cluster_name
        cmd += ' --role-arn %s' % self.role_arn
        self.parsed_responses = [
            {
                "Credentials": {
                    "AccessKeyId": self.access_key,
                    "SecretAccessKey": self.secret_key,
                    "SessionToken": self.session_token,
                },
            }
        ]
        response = self.run_get_token(cmd)
        assume_role_call = self.operations_called[0]
        self.assertEqual(assume_role_call[0].name, 'AssumeRole')
        self.assertEqual(
            assume_role_call[1],
            {'RoleArn': self.role_arn, 'RoleSessionName': 'EKSGetTokenAuth'},
        )
        self.assert_url_correct(response, has_session_token=True)

    def test_token_has_no_padding(self):
        cmd = 'eks get-token --cluster-name %s' % self.cluster_name
        num_rounds = 100
        # It is difficult to patch everything out to get an exact
        # reproduceable token. So to make sure there is no padding, we
        # run the command N times and make sure there is no padding in the
        # generated token.
        for _ in range(num_rounds):
            response = self.run_get_token(cmd)
            self.assertNotIn('=', response['status']['token'])

    def test_url_different_partition(self):
        cmd = 'eks get-token --cluster-name %s' % self.cluster_name
        cmd += ' --region cn-north-1'
        response = self.run_get_token(cmd)
        self.assert_url_correct(
            response,
            expected_endpoint='sts.cn-north-1.amazonaws.com.cn',
            expected_signing_region='cn-north-1',
        )

    def test_api_version_discovery_deprecated(self):
        self.set_kubernetes_exec_info('v1alpha1')
        cmd = 'eks get-token --cluster-name %s' % self.cluster_name
        stdout, stderr, _ = self.run_cmd(cmd)
        response = json.loads(stdout)

        self.assertEqual(
            response["apiVersion"],
            "client.authentication.k8s.io/v1alpha1",
        )

        self.assertEqual(
            stderr,
            (
                "Kubeconfig user entry is using deprecated API "
                "version client.authentication.k8s.io/v1alpha1. Run 'aws eks update-kubeconfig' to update.\n"
            ),
        )

    def test_api_version_discovery_malformed(self):
        self.environ['KUBERNETES_EXEC_INFO'] = (
            '{{"kind":"ExecCredential",'
            '"apiVersion":"client.authentication.k8s.io/v1alpha1",'
            '"spec":{"interactive":true}}'
        )
        cmd = 'eks get-token --cluster-name %s' % self.cluster_name
        stdout, stderr, _ = self.run_cmd(cmd)
        response = json.loads(stdout)

        self.assertEqual(
            response["apiVersion"],
            "client.authentication.k8s.io/v1beta1",
        )

        self.assertEqual(
            stderr,
            (
                "Error parsing KUBERNETES_EXEC_INFO, defaulting to client.authentication.k8s.io/v1beta1. "
                "This is likely a bug in your Kubernetes client. Please update your Kubernetes client.\n"
            ),
        )

    def test_api_version_discovery_empty(self):
        cmd = 'eks get-token --cluster-name %s' % self.cluster_name
        stdout, stderr, _ = self.run_cmd(cmd)
        response = json.loads(stdout)

        self.assertEqual(
            response["apiVersion"],
            "client.authentication.k8s.io/v1beta1",
        )

        self.assertEqual(stderr, "",)

    def test_api_version_discovery_v1(self):
        self.set_kubernetes_exec_info('v1')
        cmd = 'eks get-token --cluster-name %s' % self.cluster_name
        stdout, stderr, _ = self.run_cmd(cmd)
        response = json.loads(stdout)

        self.assertEqual(
            response["apiVersion"],
            "client.authentication.k8s.io/v1",
        )

        self.assertEqual(stderr, "")

    def test_api_version_discovery_v1beta1(self):
        self.set_kubernetes_exec_info('v1beta1')
        cmd = 'eks get-token --cluster-name %s' % self.cluster_name
        stdout, stderr, _ = self.run_cmd(cmd)
        response = json.loads(stdout)

        self.assertEqual(
            response["apiVersion"],
            "client.authentication.k8s.io/v1beta1",
        )

        self.assertEqual(stderr, "")

    def test_api_version_discovery_unknown(self):
        self.set_kubernetes_exec_info('v2')
        cmd = 'eks get-token --cluster-name %s' % self.cluster_name
        stdout, stderr, _ = self.run_cmd(cmd)
        response = json.loads(stdout)

        self.assertEqual(
            response["apiVersion"],
            "client.authentication.k8s.io/v1beta1",
        )

        self.assertEqual(
            stderr,
            (
                "Unrecognized API version in KUBERNETES_EXEC_INFO, defaulting to client.authentication.k8s.io/v1beta1. "
                "This is likely due to an outdated AWS CLI. Please update your AWS CLI.\n"
            ),
        )
