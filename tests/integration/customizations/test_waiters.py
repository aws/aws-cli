# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import random

from nose.plugins.attrib import attr
import botocore.session

from awscli.testutils import unittest, aws


class TestDynamoDBWait(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client('dynamodb', 'us-west-2')

    @attr('slow')
    def test_wait_table_exists(self):
        # Create a table.
        table_name = 'awscliddb-%s' % random.randint(1, 10000)
        self.client.create_table(
            TableName=table_name,
            ProvisionedThroughput={"ReadCapacityUnits": 5,
                                   "WriteCapacityUnits": 5},
            KeySchema=[{"AttributeName": "foo", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "foo",
                                   "AttributeType": "S"}])
        self.addCleanup(self.client.delete_table, TableName=table_name)

        # Wait for the table to be active.
        p = aws(
            'dynamodb wait table-exists --table-name %s --region us-west-2' %
            table_name)
        self.assertEqual(p.rc, 0)

        # Make sure the table is active.
        parsed = self.client.describe_table(TableName=table_name)
        self.assertEqual(parsed['Table']['TableStatus'], 'ACTIVE')
