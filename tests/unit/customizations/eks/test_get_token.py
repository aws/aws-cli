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
import base64
import boto3
import datetime

from awscli.testutils import unittest, capture_output
from awscli.customizations.eks.get_token import (
    GetTokenCommand,
    TokenGenerator
)


REGION = 'us-west-2'
SIGN_REGION = 'us-east-1'
CLUSTER_NAME = 'MyCluster'
DATE_STRING = datetime.date.today().strftime('%Y%m%d')
TOKEN_PREFIX = "k8s-aws-v1."

CREDENTIALS   = 'ABCDEFGHIJKLMNOPQRST'
SECRET_KEY    = 'TSRQPONMLKJUHGFEDCBA'
SESSION_TOKEN = 'TOKENTOKENTOKENTOKEN'

class TestTokenGenerator(unittest.TestCase):
    def assert_url_correct(self, url, is_session):
        url_no_signature = url[0:-64]

        if is_session:
            self.assertIn("X-Amz-Security-Token=" + SESSION_TOKEN + "&", url_no_signature)

        self.assertIn("X-Amz-Credential=" + CREDENTIALS + "%2F", url_no_signature)
        self.assertIn("%3Bx-k8s-aws-id&", url_no_signature)

    def setUp(self):
        self._session_handler = mock.Mock()
        self._session = boto3.Session(
            region_name=REGION,
            aws_access_key_id=CREDENTIALS,
            aws_secret_access_key=SECRET_KEY
        )
        self._session_handler.get_session = mock.Mock(return_value=self._session)

        self._assuming_handler = mock.Mock()
        # While assuming a role, you have a session token
        self._assuming_session = boto3.Session(
            region_name=REGION,
            aws_access_key_id=CREDENTIALS,
            aws_secret_access_key=SECRET_KEY,
            aws_session_token=SESSION_TOKEN
        )
        self._assuming_handler.get_session = mock.Mock(return_value=self._assuming_session)

        self.maxDiff = None

    def test_url(self):
        generator = TokenGenerator(REGION, self._session_handler)
        url = generator._get_presigned_url(CLUSTER_NAME, None)
        self.assert_url_correct(url, False)

    def test_url_sess(self):
        generator = TokenGenerator(REGION, self._assuming_handler)
        url = generator._get_presigned_url(CLUSTER_NAME, "RoleArn")
        print("URL: " + url)
        self.assert_url_correct(url, True)

    def test_token(self):
        generator = TokenGenerator(REGION, self._session_handler)
        token = generator.get_token(CLUSTER_NAME, None)
        prefix = token[:len(TOKEN_PREFIX)]
        self.assertEqual(prefix, TOKEN_PREFIX)
        token_no_prefix = token[len(TOKEN_PREFIX):]

        decrypted_token = base64.urlsafe_b64decode(
            token_no_prefix.encode()
        ).decode()
        self.assert_url_correct(decrypted_token, False)

    def test_token_sess(self):
        generator = TokenGenerator(REGION, self._assuming_handler)
        token = generator.get_token(CLUSTER_NAME, "RoleArn")
        prefix = token[:len(TOKEN_PREFIX)]
        self.assertEqual(prefix, TOKEN_PREFIX)
        token_no_prefix = token[len(TOKEN_PREFIX):]

        decrypted_token = base64.urlsafe_b64decode(
            token_no_prefix.encode()
        ).decode()
        self.assert_url_correct(decrypted_token, True)
