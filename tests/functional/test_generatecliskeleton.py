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
import json

from awscli.testutils import BaseAWSCommandParamsTest


class TestGenerateCliSkeletonOutput(BaseAWSCommandParamsTest):
    def test_generate_cli_skeleton_output(self):
        cmdline = 'ec2 describe-regions --generate-cli-skeleton output'
        stdout, _, _ = self.run_cmd(cmdline)
        # The format of the response should be a json blob with the
        # following structure:
        # {
        #     "Regions": [
        #         {
        #             "RegionName": "RegionName",
        #             "Endpoint": "Endpoint"
        #         }
        #     ]
        # }
        #
        # We assert only components of the response in case members
        # are added in the future that would break an exactly equals
        # assertion
        skeleton_output = json.loads(stdout)
        self.assertIn('Regions', skeleton_output)
        self.assertEqual(
            skeleton_output['Regions'][0]['RegionName'], 'RegionName')
        self.assertEqual(
            skeleton_output['Regions'][0]['Endpoint'], 'Endpoint')

    def test_can_pass_in_input_parameters(self):
        cmdline = 'ec2 describe-regions --generate-cli-skeleton output '
        cmdline += ' --region-names us-east-1'
        stdout, _, _ = self.assert_params_for_cmd(
            cmdline, {'RegionNames': ['us-east-1']})

        # Make sure the output has the proper mocked response as well.
        skeleton_output = json.loads(stdout)
        self.assertIn('Regions', skeleton_output)
        self.assertEqual(
            skeleton_output['Regions'][0]['RegionName'], 'RegionName')
        self.assertEqual(
            skeleton_output['Regions'][0]['Endpoint'], 'Endpoint')

    def test_when_no_output_shape(self):
        cmdline = 'ec2 attach-internet-gateway '
        cmdline += '--internet-gateway-id igw-c0a643a9 --vpc-id vpc-a01106 '
        cmdline += '--generate-cli-skeleton output'
        stdout, _, _ = self.assert_params_for_cmd(
            cmdline,
            {'InternetGatewayId': 'igw-c0a643a9', 'VpcId': 'vpc-a01106'})
        # There should be no output as the command has no output shape
        self.assertEqual('', stdout)

    def test_can_handle_timestamps(self):
        cmdline = 's3api list-buckets --generate-cli-skeleton output'
        stdout, _, _ = self.run_cmd(cmdline)
        skeleton_output = json.loads(stdout)
        # The CreationDate has the type of timestamp
        self.assertEqual(
            skeleton_output['Buckets'][0]['CreationDate'],
            '1970-01-01T00:00:00'
        )

    def test_can_handle_lists_with_strings_that_have_a_min_length(self):
        cmdline = 'dynamodb list-tables --generate-cli-skeleton output'
        stdout, _, _ = self.run_cmd(cmdline)
        skeleton_output = json.loads(stdout)
        self.assertEqual(skeleton_output['TableNames'], ['TableName'])

    def test_respects_formatting(self):
        cmdline = 'ec2 describe-regions --generate-cli-skeleton output '
        cmdline += ' --query Regions[].RegionName --output text'
        stdout, _, _ = self.run_cmd(cmdline)
        self.assertEqual(stdout, 'RegionName\n')

    def test_validates_at_command_line_level(self):
        cmdline = 'ec2 create-vpc --generate-cli-skeleton output'
        stdout, stderr, _ = self.run_cmd(cmdline, expected_rc=2)
        self.assertIn('required', stderr)
        self.assertIn('--cidr-block', stderr)
        self.assertEqual('', stdout)

    def test_validates_at_client_level(self):
        cmdline = 'ec2 describe-instances --generate-cli-skeleton output '
        # Note: The for --filters instead of Value the key should be Values
        # which should throw a validation error.
        cmdline += '--filters Name=instance-id,Value=foo'
        stdout, stderr, _ = self.run_cmd(cmdline, expected_rc=255)
        self.assertIn('Unknown parameter in Filters[0]', stderr)
        self.assertEqual('', stdout)
