#!/usr/bin/env python
# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestMBCommand(BaseAWSCommandParamsTest):

    prefix = 's3 mb '

    def test_make_bucket(self):
        command = self.prefix + 's3://bucket'
        self.run_cmd(command)
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(self.operations_called[0][0].name, 'CreateBucket')

    def test_adds_location_constraint(self):
        command = self.prefix + 's3://bucket --region us-west-2'
        self.parsed_responses = [{'Location': 'us-west-2'}]
        expected_params = {
            'Bucket': 'bucket',
            'CreateBucketConfiguration': {
                'LocationConstraint': 'us-west-2'
            }
        }
        self.assert_params_for_cmd(command, expected_params)

    def test_location_constraint_not_added_on_us_east_1(self):
        command = self.prefix + 's3://bucket --region us-east-1'
        expected_params = {
            'Bucket': 'bucket'
        }
        self.assert_params_for_cmd(command, expected_params)

    def test_nonzero_exit_if_invalid_path_provided(self):
        command = self.prefix + 'bucket'
        self.run_cmd(command, expected_rc=255)

    def test_incompatible_with_express_directory_bucket(self):
        command = self.prefix + 's3://bucket--usw2-az1--x-s3/'
        stderr = self.run_cmd(command, expected_rc=255)[1]
        self.assertIn('Cannot use mb command with a directory bucket.', stderr)