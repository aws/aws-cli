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


class BaseTokenTest(unittest.TestCase):
    def setUp(self):
        self._session = botocore.session.get_session()
        self._access_key = 'ABCDEFGHIJKLMNOPQRST'
        self._secret_key = 'TSRQPONMLKJUHGFEDCBA'
        self._region = 'us-west-2'
        self._cluster_name = 'MyCluster'
        self._session.set_credentials(self._access_key, self._secret_key)
        self._sts_client = self._session.create_client('sts', self._region)


class TestTokenGenerator(BaseTokenTest):
    @patch.object(TokenGenerator, '_get_presigned_url', return_value='aHR0cHM6Ly9zdHMuYW1hem9uYXdzLmNvbS8=')
    def test_token_no_padding(self, mock_presigned_url):
        generator = TokenGenerator(self._sts_client)
        tok = generator.get_token(self._cluster_name)
        self.assertTrue('=' not in tok)


class TestGetTokenCommand(BaseTokenTest):
    def test_get_expiration_time(self):
        cmd = GetTokenCommand(self._session)
        timestamp = cmd.get_expiration_time()
        try:
            datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            raise ValueError("Incorrect data format, should be %Y-%m-%dT%H:%M:%SZ")
