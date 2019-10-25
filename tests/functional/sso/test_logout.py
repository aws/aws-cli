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
import json
import os

from awscli.testutils import mock
from tests.functional.sso import BaseSSOTest


class TestLogoutCommand(BaseSSOTest):
    def setUp(self):
        super(TestLogoutCommand, self).setUp()
        self.token_cache_dir = self.files.full_path('token-cache')
        self.token_cache_dir_patch = mock.patch(
            'awscli.customizations.sso.logout.SSO_TOKEN_DIR',
            self.token_cache_dir
        )
        self.token_cache_dir_patch.start()
        self.aws_creds_cache_dir = self.files.full_path('aws-creds-cache')
        self.aws_creds_cache_dir_patch = mock.patch(
            'awscli.customizations.sso.logout.AWS_CREDS_CACHE_DIR',
            self.aws_creds_cache_dir
        )
        self.aws_creds_cache_dir_patch.start()

    def tearDown(self):
        super(TestLogoutCommand, self).tearDown()
        self.token_cache_dir_patch.stop()
        self.aws_creds_cache_dir_patch.stop()

    def add_cached_token(self, filename):
        token_path = os.path.join(self.token_cache_dir, filename)
        token_contents = {
            'region': self.sso_region,
            'startUrl': self.start_url,
            'expiresAt': '2019-10-26T05:19:09UTC',
            'accessToken': self.access_token,
        }
        self.files.create_file(token_path, json.dumps(token_contents))
        return token_path

    def add_cached_aws_credentials(self, filename, from_sso=True):
        creds_contents = {
            'Credentials': {
                'AccessKeyId': 'access-key',
                'SecretAccessKey': 'secret-key',
                "SessionToken": 'session-token',
                "Expiration": '2020-01-23T20:48:59UTC'
            },
        }
        if from_sso:
            creds_contents['ProviderType'] = 'sso'
        creds_path = os.path.join(self.aws_creds_cache_dir, filename)
        self.files.create_file(creds_path, json.dumps(creds_contents))
        return creds_path

    def assert_file_exists(self, filename):
        self.assertTrue(os.path.exists(filename))

    def assert_file_does_not_exist(self, filename):
        self.assertFalse(os.path.exists(filename))

    def test_logout(self):
        token = self.add_cached_token('token.json')
        creds = self.add_cached_aws_credentials('sso-creds.json')
        self.run_cmd('sso logout')
        self.assert_file_does_not_exist(token)
        self.assert_file_does_not_exist(creds)

    def test_logout_multiple_cached_files(self):
        token = self.add_cached_token('token.json')
        token2 = self.add_cached_token('token2.json')
        creds = self.add_cached_aws_credentials('sso-creds.json')
        creds2 = self.add_cached_aws_credentials('sso-creds2.json')
        self.run_cmd('sso logout')
        self.assert_file_does_not_exist(token)
        self.assert_file_does_not_exist(token2)
        self.assert_file_does_not_exist(creds)
        self.assert_file_does_not_exist(creds2)

    def test_logout_ignores_non_sso_tokens(self):
        registration_token = os.path.join(
            self.token_cache_dir, 'botocore-client-id.json')
        self.files.create_file(
            registration_token, json.dumps({'clientId': 'myid'}))
        self.run_cmd('sso logout')
        self.assert_file_exists(registration_token)

    def test_logout_ignores_non_sso_retrieved_aws_creds(self):
        creds = self.add_cached_aws_credentials('creds.json', from_sso=False)
        self.run_cmd('sso logout')
        self.assert_file_exists(creds)

    def test_ignores_invalid_json_files(self):
        invalid_json = os.path.join(self.token_cache_dir, 'invalid.json')
        self.files.create_file(invalid_json, '{not-json')
        self.run_cmd('sso logout')
        self.assert_file_exists(invalid_json)

    def test_does_not_fail_when_cache_does_not_exist(self):
        self.assertFalse(os.path.exists(self.token_cache_dir))
        self.assertFalse(os.path.exists(self.aws_creds_cache_dir))
        self.run_cmd('sso logout', expected_rc=0)

    def test_calls_sso_logout_with_token(self):
        token = self.add_cached_token('token.json')
        self.run_cmd('sso logout')
        self.assert_file_does_not_exist(token)
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(self.operations_called[0][0].name, 'Logout')
        expected_logout_params = {
            'accessToken': self.access_token,
        }
        self.assertEqual(self.operations_called[0][1], expected_logout_params)

    def test_calls_sso_logout_and_handles_client_error(self):
        self.http_response.status_code = 400
        token = self.add_cached_token('token.json')
        self.run_cmd('sso logout', expected_rc=0)
        self.assert_file_does_not_exist(token)
