# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import create_clidriver
from awscli.testutils import BaseAWSCommandParamsTest, FileCreator


class TestArgsResolution(BaseAWSCommandParamsTest):

    def setUp(self):
        super(TestArgsResolution, self).setUp()
        self.files = FileCreator()
        config_contents = (
            '[profile bar]\n'
            'region = us-west-2\n'
        )
        self.environ['AWS_CONFIG_FILE'] = self.files.create_file(
            'myconfig', config_contents)
        self.driver = create_clidriver()

    def tearDown(self):
        super(TestArgsResolution, self).tearDown()
        self.files.remove_all()

    def test_profile_resolution_order(self):
        self.environ['AWS_PROFILE'] = 'foo'
        self.parsed_responses = [{"Reservations": []}]
        self.run_cmd('--profile bar ec2 describe-instances', expected_rc=0)
        self.assertEqual(self.driver.session.profile, 'bar')

    def test_can_get_version_with_non_existent_profile(self):
        self.environ['AWS_PROFILE'] = 'foo'
        # ProfileNotFound exception shouldn't be raised
        self.run_cmd('--version', expected_rc=0)
