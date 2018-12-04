# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestAPIVersions(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestAPIVersions, self).setUp()
        self.files = FileCreator()
        # We just pick ec2 because it is a service that actually has
        # multiple api versions.
        self.service_name = 'ec2'
        self.api_version = '2014-10-01'
        config_contents = (
            '[default]\n'
            'api_versions =\n'
            '    %s = %s\n' % (self.service_name, self.api_version)
        )
        self.environ['AWS_CONFIG_FILE'] = self.files.create_file(
            'myconfig', config_contents)
        self.driver = create_clidriver()

    def tearDown(self):
        super(TestAPIVersions, self).tearDown()
        self.files.remove_all()

    def test_command_send_correct_api_version(self):
        cmdline = 'ec2 describe-instances'
        self.run_cmd(cmdline)
        # Make sure that the correct api version is used for the client
        # by checking the version that was sent in the request.
        self.assertEqual(self.last_params['Version'], self.api_version)

    def test_command_interface_reflects_api_version(self):
        # Take an arbitrary command such as describe-nat-gateways that is not
        # in the 2014-10-01 EC2 API version and make sure its CLI command
        # interface is not available as well.
        cmdline = 'ec2 describe-nat-gateways'
        _, stderr, _ = self.run_cmd(cmdline, expected_rc=2)
        self.assertIn("Invalid choice: 'describe-nat-gateways'", stderr)
