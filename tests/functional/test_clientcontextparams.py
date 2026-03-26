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

    def test_boolean_flag_sets_client_context_params(self):
        self.run_cmd('s3api list-buckets --disable-s3-express-session-auth')
        config = self.driver.session.get_default_client_config()
        self.assertEqual(
            config.client_context_params,
            {'DisableS3ExpressSessionAuth': True},
        )

    def test_negative_flag_sets_false(self):
        self.run_cmd('s3api list-buckets --no-disable-s3-express-session-auth')
        config = self.driver.session.get_default_client_config()
        self.assertEqual(
            config.client_context_params,
            {'DisableS3ExpressSessionAuth': False},
        )

    def test_no_flag_does_not_set_client_context_params(self):
        self.run_cmd('s3api list-buckets')
        config = self.driver.session.get_default_client_config()
        if config is not None:
            self.assertIsNone(config.client_context_params)
