# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import BaseAWSCommandParamsTest


class TestClientContextParams(BaseAWSCommandParamsTest):
    def setUp(self):
        super().setUp()
        self.parsed_responses = [{'Buckets': [], 'Owner': {}}]

    def _get_client_context_params(self):
        config = self.driver.session.get_default_client_config()
        if config is None:
            return None
        return config.client_context_params

    def test_boolean_flag_sets_client_context_params(self):
        self.run_cmd('s3api list-buckets --disable-s3-express-session-auth')
        params = self._get_client_context_params()
        self.assertIn('disable_s3_express_session_auth', params)
        self.assertTrue(params['disable_s3_express_session_auth'])

    def test_negative_flag_sets_false(self):
        self.run_cmd('s3api list-buckets --no-disable-s3-express-session-auth')
        params = self._get_client_context_params()
        self.assertIn('disable_s3_express_session_auth', params)
        self.assertFalse(params['disable_s3_express_session_auth'])

    def test_no_flag_does_not_set_client_context_params(self):
        self.run_cmd('s3api list-buckets')
        params = self._get_client_context_params()
        if params is not None:
            self.assertNotIn('disable_s3_express_session_auth', params)

    def test_params_use_snake_case_keys(self):
        self.run_cmd('s3api list-buckets --disable-s3-express-session-auth')
        for key in self._get_client_context_params():
            self.assertEqual(key, key.lower())
