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

import mock
from mock import patch, call
import base64
import botocore
import json
from datetime import datetime

from awscli.testutils import unittest, capture_output
from awscli.customizations.eks.get_token import (
    GetTokenCommand,
    TokenGenerator
)


REGION = 'us-west-2'
SIGN_REGION = 'us-east-1'
CLUSTER_NAME = 'MyCluster'
TOKEN_PREFIX = "k8s-aws-v1."

CREDENTIALS   = 'ABCDEFGHIJKLMNOPQRST'
SECRET_KEY    = 'TSRQPONMLKJUHGFEDCBA'
SESSION_TOKEN = 'TOKENTOKENTOKENTOKEN'

class TestTokenGenerator(unittest.TestCase):
    def assert_url_correct(self, url, is_session):
        url_no_signature = url[0:-64]

        if is_session:
            self.assertIn("X-Amz-Security-Token=" + SESSION_TOKEN + "&", url_no_signature)
        else:
            self.assertNotIn("X-Amz-Security-Token=" + SESSION_TOKEN + "&", url_no_signature)

        self.assertIn("X-Amz-Credential=" + CREDENTIALS + "%2F", url_no_signature)
        self.assertIn("%3Bx-k8s-aws-id&", url_no_signature)

    def setUp(self):
        session = botocore.session.get_session()
        session.set_credentials(CREDENTIALS, SECRET_KEY)
        self._session = session

        self.mock_sts_client = mock.Mock()
        self.mock_sts_client.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": CREDENTIALS,
                "SecretAccessKey": SECRET_KEY,
                "SessionToken": SESSION_TOKEN,
            },
        }

        self.maxDiff = None

    def test_url(self):
        generator = TokenGenerator(self._session)
        url = generator._get_presigned_url(CLUSTER_NAME, None, REGION)
        self.assert_url_correct(url, False)

    def test_url_no_region(self):
        self._session.set_config_variable('region', 'us-east-1')
        generator = TokenGenerator(self._session)
        url = generator._get_presigned_url(CLUSTER_NAME, None, None)
        self.assert_url_correct(url, False)

    @patch.object(botocore.session.Session, 'create_client')
    def test_url_with_role(self, mock_create_client):
        mock_create_client.return_value = self.mock_sts_client
        generator = TokenGenerator(self._session)
        url = generator._get_presigned_url(CLUSTER_NAME, "arn:aws:iam::012345678910:role/RoleArn", REGION)
        self.assert_url_correct(url, True)

    def test_token_no_role(self):
        generator = TokenGenerator(self._session)
        token = generator.get_token(CLUSTER_NAME, None, REGION)
        prefix = token[:len(TOKEN_PREFIX)]
        self.assertEqual(prefix, TOKEN_PREFIX)
        token_no_prefix = token[len(TOKEN_PREFIX):]

        decrypted_token = base64.urlsafe_b64decode(
            token_no_prefix.encode()
        ).decode()
        self.assert_url_correct(decrypted_token, False)

    @patch.object(TokenGenerator, '_get_presigned_url', return_value='aHR0cHM6Ly9zdHMuYW1hem9uYXdzLmNvbS8=')
    def test_token_no_padding(self, mock_presigned_url):
        generator = TokenGenerator(self._session)
        tok = generator.get_token(CLUSTER_NAME, None, REGION)
        self.assertTrue('=' not in tok)

    @patch.object(botocore.session.Session, 'create_client')
    def test_token_sess(self, mock_create_client):
        mock_create_client.return_value = self.mock_sts_client

        generator = TokenGenerator(self._session)
        token = generator.get_token(CLUSTER_NAME, "arn:aws:iam::012345678910:role/RoleArn", REGION)
        prefix = token[:len(TOKEN_PREFIX)]
        self.assertEqual(prefix, TOKEN_PREFIX)
        token_no_prefix = token[len(TOKEN_PREFIX):]

        decrypted_token = base64.urlsafe_b64decode(
            token_no_prefix.encode()
        ).decode()
        self.assert_url_correct(decrypted_token, True)

class TestGetTokenCommand(unittest.TestCase):

    def setUp(self):
        session = botocore.session.get_session()
        session.set_credentials(CREDENTIALS, SECRET_KEY)
        self._session = session
        self.maxDiff = None

    def test_get_expiration_time(self):
        cmd = GetTokenCommand(self._session)
        timestamp = cmd.get_expiration_time()
        try:
            datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            raise ValueError("Incorrect data format, should be %Y-%m-%dT%H:%M:%SZ")

    @patch.object(GetTokenCommand, 'get_expiration_time', return_value='2019-06-21T22:07:54Z')
    def test_run_main(self, mock_expiration_time):
        mock_token_generator = mock.Mock()
        fake_token = 'k8s-aws-v1.aHR0cHM6Ly9zdHMuYW1hem9uYXdzLmNvbS8='
        mock_token_generator.get_token.return_value = fake_token

        mock_args = mock.Mock()
        mock_args.cluster_name = "my-cluster"
        mock_args.role_arn = None

        mock_globals = mock.Mock()
        mock_globals.region = 'us-west-2'

        expected_stdout = json.dumps({
            "kind": "ExecCredential",
            "apiVersion": "client.authentication.k8s.io/v1alpha1", "spec": {},
            "status": {
                "expirationTimestamp": "2019-06-21T22:07:54Z",
                "token": fake_token,
            },
        }) +'\n'
        cmd = GetTokenCommand(self._session)
        with capture_output() as captured:
            cmd._run_main(mock_args, mock_globals, mock_token_generator)
            self.assertEqual(expected_stdout, captured.stdout.getvalue())
