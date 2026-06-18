# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore.compat import json
from botocore.config import Config
from tests import BaseSessionTest, ClientHTTPStubber


class TestDynamoDBEndpointDiscovery(BaseSessionTest):
    def setUp(self):
        super().setUp()
        self.region = 'us-west-2'
        self.config = Config(endpoint_discovery_enabled=True)
        self.create_client()

    def create_client(self):
        self.client = self.session.create_client(
            'dynamodb', self.region, config=self.config
        )
        self.http_stubber = ClientHTTPStubber(self.client)

    def test_dynamodb_endpoint_discovery_enabled(self):
        discovered_endpoint = 'https://discovered.domain'
        response = {
            'Endpoints': [
                {
                    'Address': discovered_endpoint,
                    'CachePeriodInMinutes': 1,
                }
            ]
        }
        response_body = json.dumps(response).encode()
        with self.http_stubber as stubber:
            stubber.add_response(status=200, body=response_body)
            stubber.add_response(status=200, body=b'{}')
            self.client.describe_table(TableName='sometable')
            self.assertEqual(len(self.http_stubber.requests), 2)
            discover_request = self.http_stubber.requests[1]
            self.assertEqual(discover_request.url, discovered_endpoint)

    def test_dynamodb_endpoint_discovery_disabled(self):
        self.config = Config(endpoint_discovery_enabled=False)
        self.create_client()
        with self.http_stubber as stubber:
            stubber.add_response(status=200, body=b'{}')
            self.client.describe_table(TableName='sometable')
            self.assertEqual(len(self.http_stubber.requests), 1)

    def test_dynamodb_endpoint_discovery_no_config_default(self):
        self.config = None
        self.create_client()
        with self.http_stubber as stubber:
            stubber.add_response(status=200, body=b'{}')
            self.client.describe_table(TableName='sometable')
            self.assertEqual(len(self.http_stubber.requests), 1)
