# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import pytest

import botocore.session
from botocore.exceptions import WaiterError
from tests import random_chars, unittest


@pytest.mark.slow
class TestWaiterForDynamoDB(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client('dynamodb', 'us-west-2')

    def test_create_table_and_wait(self):
        table_name = f'botocoretest-{random_chars(10)}'
        self.client.create_table(
            TableName=table_name,
            ProvisionedThroughput={
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5,
            },
            KeySchema=[{"AttributeName": "foo", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "foo", "AttributeType": "S"}
            ],
        )
        self.addCleanup(self.client.delete_table, TableName=table_name)
        waiter = self.client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        parsed = self.client.describe_table(TableName=table_name)
        self.assertEqual(parsed['Table']['TableStatus'], 'ACTIVE')


class TestCanGetWaitersThroughClientInterface(unittest.TestCase):
    def test_get_ses_waiter(self):
        # We're checking this because ses is not the endpoint prefix
        # for the service, it's email.  We want to make sure this does
        # not affect the lookup process.
        session = botocore.session.get_session()
        client = session.create_client('ses', 'us-east-1')
        # If we have at least one waiter in the list, we know that we have
        # actually loaded the waiters and this test has passed.
        self.assertTrue(len(client.waiter_names) > 0)


class TestMatchersWithErrors(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client(
            'ec2', region_name='us-west-2'
        )

    def test_dont_search_on_error_responses(self):
        """Test that InstanceExists can handle a nonexistent instance."""
        waiter = self.client.get_waiter('instance_exists')
        waiter.config.max_attempts = 1
        with self.assertRaises(WaiterError):
            waiter.wait(InstanceIds=['i-12345'])
