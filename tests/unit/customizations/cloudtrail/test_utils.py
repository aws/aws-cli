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

from awscli.customizations.cloudtrail import utils
from awscli.testutils import mock, unittest


class TestCloudTrailUtils(unittest.TestCase):
    @mock.patch('awscli.customizations.cloudtrail.utils.get_account_id')
    def test_gets_sts_account_id(self, mock_get_account_id):
        mock_get_account_id.return_value = '1234'
        account_id = utils.get_account_id(mock_get_account_id)
        self.assertEqual(account_id, '1234')

    def test_gets_sts_account_id_with_empty_response(self):
        mock_sts_client = mock.Mock()
        mock_sts_client.get_caller_identity.return_value = {}
        with self.assertRaises(KeyError):
            utils.get_account_id(mock_sts_client)

    def test_gets_account_id_from_arn(self):
        arn = 'foo:bar:baz:qux:1234'
        self.assertEqual('1234', utils.get_account_id_from_arn(arn))

    def test_gets_account_id_from_arn_with_invalid_arn(self):
        arn = 'foo:bar:baz'
        with self.assertRaises(IndexError):
            utils.get_account_id_from_arn(arn)

    def test_gets_trail_by_arn(self):
        cloudtrail_client = mock.Mock()
        cloudtrail_client.describe_trails.return_value = {'trailList': [
            {'TrailARN': 'a', 'Foo': 'Baz'},
            {'TrailARN': 'b', 'Foo': 'Bar'}
        ]}
        result = utils.get_trail_by_arn(cloudtrail_client, 'b')
        self.assertEqual('Bar', result['Foo'])

    def test_throws_when_unable_to_get_trail_by_arn(self):
        cloudtrail_client = mock.Mock()
        cloudtrail_client.describe_trails.return_value = {'trailList': []}
        with self.assertRaises(ValueError):
            utils.get_trail_by_arn(cloudtrail_client, 'b')

    def test_get_trail_by_arn_with_invalid_trail(self):
        cloudtrail_client = mock.Mock()
        cloudtrail_client.describe_trails.return_value = {'trailList': [
            {'TrailARN': 'a', 'Foo': 'Baz'}
        ]}
        with self.assertRaises(ValueError):
            utils.get_trail_by_arn(cloudtrail_client, 'nonexistent')
