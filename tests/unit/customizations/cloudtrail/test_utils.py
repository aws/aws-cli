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
from mock import Mock

from awscli.customizations.cloudtrail import utils
from awscli.testutils import unittest


class TestCloudTrailUtils(unittest.TestCase):
    def test_gets_account_id_from_arn(self):
        arn = 'foo:bar:baz:qux:1234'
        self.assertEqual('1234', utils.get_account_id_from_arn(arn))

    def test_gets_trail_by_arn(self):
        cloudtrail_client = Mock()
        cloudtrail_client.describe_trails.return_value = {'trailList': [
            {'TrailARN': 'a', 'Foo': 'Baz'},
            {'TrailARN': 'b', 'Foo': 'Bar'}
        ]}
        result = utils.get_trail_by_arn(cloudtrail_client, 'b')
        self.assertEqual('Bar', result['Foo'])

    def test_throws_when_unable_to_get_trail_by_arn(self):
        cloudtrail_client = Mock()
        cloudtrail_client.describe_trails.return_value = {'trailList': []}
        self.assertRaises(
            ValueError, utils.get_trail_by_arn, cloudtrail_client, 'b')
