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
from awscli.testutils import BaseAWSCommandParamsTest


class TestRb(BaseAWSCommandParamsTest):

    prefix = 's3 rb '

    def test_rb(self):
        command = self.prefix + 's3://bucket'
        self.run_cmd(command)
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(self.operations_called[0][0].name, 'DeleteBucket')

    def test_rb_force_empty_bucket(self):
        command = self.prefix + 's3://bucket --force'
        self.run_cmd(command)
        self.assertEqual(len(self.operations_called), 2)
        self.assertEqual(self.operations_called[0][0].name, 'ListObjects')
        self.assertEqual(self.operations_called[1][0].name, 'DeleteBucket')

    def test_rb_force_non_empty_bucket(self):
        command = self.prefix + 's3://bucket --force'
        self.parsed_responses = [{
            'Contents': [
                {
                    'Key': 'foo',
                    'Size': 100,
                    'LastModified': '2016-03-01T23:50:13.000Z'
                }
            ]
        }, {}, {}]
        self.run_cmd(command)
        self.assertEqual(len(self.operations_called), 3)
        self.assertEqual(self.operations_called[0][0].name, 'ListObjects')
        self.assertEqual(self.operations_called[1][0].name, 'DeleteObject')
        self.assertEqual(self.operations_called[2][0].name, 'DeleteBucket')

    def test_rb_failed_rc(self):
        command = self.prefix + 's3://bucket'
        self.http_response.status_code = 500
        _, stderr, _ = self.run_cmd(command, expected_rc=1)
        self.assertIn('remove_bucket failed:', stderr)

    def test_rb_force_with_failed_rm(self):
        command = self.prefix + 's3://bucket --force'
        self.http_response.status_code = 500
        _, stderr, _ = self.run_cmd(command, expected_rc=255)
        self.assertIn('remove_bucket failed:', stderr)
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(self.operations_called[0][0].name, 'ListObjects')

    def test_nonzero_exit_if_uri_scheme_not_provided(self):
        command = self.prefix + 'bucket'
        self.run_cmd(command, expected_rc=255)

    def test_nonzero_exit_if_key_provided(self):
        command = self.prefix + 's3://bucket/key --force'
        self.run_cmd(command, expected_rc=255)

        command = self.prefix + 's3://bucket/key'
        self.run_cmd(command, expected_rc=255)
