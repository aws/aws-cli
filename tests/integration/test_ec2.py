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
from awscli.testutils import unittest, aws


class BaseEC2Test(unittest.TestCase):
    def assert_dry_run_success(self, command):
        result = aws(command)
        expected_response = ('Request would have succeeded, '
                             'but DryRun flag is set.')
        self.assertIn(expected_response, result.stderr)


class TestDescribeInstances(BaseEC2Test):
    def setUp(self):
        self.prefix = 'ec2 describe-instances --region us-west-2 --dry-run'

    def test_describe_instances_with_id(self):
        command = self.prefix + ' --instance-ids id-example'
        self.assert_dry_run_success(command)

    def test_describe_instances_with_filter(self):
        command = self.prefix + ' --filters Name=private-dns-name,Values='
        command += 'sample-dns-name'
        self.assert_dry_run_success(command)
