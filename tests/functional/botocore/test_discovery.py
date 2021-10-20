# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os

from tests import ClientHTTPStubber, temporary_file
from tests.functional import FunctionalSessionTest

import botocore
from botocore.config import Config
from botocore.compat import json
from botocore.discovery import EndpointDiscoveryRequired
from botocore.exceptions import ClientError, InvalidEndpointDiscoveryConfigurationError


class TestEndpointDiscovery(FunctionalSessionTest):
    def setUp(self):
        super(TestEndpointDiscovery, self).setUp()
        self.region = 'us-west-2'

    def create_client(
        self,
        service_name='dynamodb',
        region=None,
        config=None,
        endpoint_url=None
    ):
        if region is None:
            region = self.region
        client = self.session.create_client(
            service_name, region, config=config, endpoint_url=endpoint_url
        )
        http_stubber = ClientHTTPStubber(client)

        return client, http_stubber

    def add_describe_endpoints_response(self, stubber, discovered_endpoint):
        response = {
            'Endpoints': [{
                'Address': discovered_endpoint,
                'CachePeriodInMinutes': 1,
            }]
        }
        response_body = json.dumps(response).encode()
        stubber.add_response(status=200, body=response_body)
        stubber.add_response(status=200, body=b'{}')

    def set_endpoint_discovery_config_file(self, fileobj, config_val):
        fileobj.write(
            '[default]\n'
            'endpoint_discovery_enabled=%s\n' % config_val
        )
        fileobj.flush()
        self.environ['AWS_CONFIG_FILE'] = fileobj.name

    def assert_endpoint_discovery_used(self, stubber, discovered_endpoint):
        self.assertEqual(len(stubber.requests), 2)
        discover_request = stubber.requests[1]
        self.assertEqual(discover_request.url, discovered_endpoint)

    def assert_discovery_skipped(self, stubber, operation):
        self.assertEqual(len(stubber.requests), 1)
        self.assertEqual(
            stubber.requests[0].headers.get('X-Amz-Target'),
            operation
        )

    def assert_endpoint_used(self, actual_url, expected_url):
        self.assertEqual(actual_url, expected_url)

    def test_endpoint_discovery_enabled(self):
        discovered_endpoint = 'https://discovered.domain'
        config = Config(endpoint_discovery_enabled=True)
        client, http_stubber = self.create_client(config=config)
        with http_stubber as stubber:
            self.add_describe_endpoints_response(stubber, discovered_endpoint)
            client.describe_table(TableName='sometable')
            self.assert_endpoint_discovery_used(stubber, discovered_endpoint)

    def test_endpoint_discovery_with_invalid_endpoint(self):
        discovered_endpoint = 'https://discovered.domain'
        response = {
            'Error': {
                'Code': 'InvalidEndpointException',
                'Message': 'Test Error',
            }
        }
        response_body = json.dumps(response).encode()

        config = Config(endpoint_discovery_enabled=True)
        client, http_stubber = self.create_client(config=config)
        with http_stubber as stubber:
            stubber.add_response(status=421, body=response_body)
            with self.assertRaises(ClientError):
                client.describe_table(TableName='sometable')

    def test_endpoint_discovery_disabled(self):
        config = Config(endpoint_discovery_enabled=False)
        client, http_stubber = self.create_client(config=config)
        with http_stubber as stubber:
            stubber.add_response(status=200, body=b'{}')
            client.describe_table(TableName='sometable')
            self.assertEqual(len(stubber.requests), 1)

    def test_endpoint_discovery_no_config_default(self):
        client, http_stubber = self.create_client()
        with http_stubber as stubber:
            stubber.add_response(status=200, body=b'{}')
            client.describe_table(TableName='sometable')
            self.assertEqual(len(stubber.requests), 1)

    def test_endpoint_discovery_default_required_endpoint(self):
        discovered_endpoint = "https://discovered.domain"
        client, http_stubber = self.create_client(service_name="test-discovery-endpoint")
        with http_stubber as stubber:
            self.add_describe_endpoints_response(stubber, discovered_endpoint)
            client.test_discovery_required(Foo="bar")
            self.assert_endpoint_discovery_used(stubber, discovered_endpoint)

    def test_endpoint_discovery_required_with_discovery_enabled(self):
        discovered_endpoint = "https://discovered.domain"
        config = Config(endpoint_discovery_enabled=True)
        client, http_stubber = self.create_client(
            service_name="test-discovery-endpoint", config=config
        )
        with http_stubber as stubber:
            self.add_describe_endpoints_response(stubber, discovered_endpoint)
            client.test_discovery_required(Foo="bar")
            self.assert_endpoint_discovery_used(stubber, discovered_endpoint)

    def test_endpoint_discovery_required_with_discovery_disabled(self):
        discovered_endpoint = "https://discovered.domain"
        config = Config(endpoint_discovery_enabled=False)
        client, http_stubber = self.create_client(
            service_name="test-discovery-endpoint", config=config
        )
        self.add_describe_endpoints_response(http_stubber, discovered_endpoint)
        with self.assertRaises(EndpointDiscoveryRequired):
            client.test_discovery_required(Foo="bar")

    def test_endpoint_discovery_required_with_custom_endpoint(self):
        endpoint = "https://custom.domain/"
        client, http_stubber = self.create_client(
            service_name="test-discovery-endpoint", endpoint_url=endpoint
        )
        with http_stubber as stubber:
            stubber.add_response(status=200, body=b'{}')
            client.test_discovery_required(Foo="bar")
            self.assert_discovery_skipped(
                stubber,
                b"test-discovery-endpoint.TestDiscoveryRequired"
            )
            self.assert_endpoint_used(stubber.requests[0].url, endpoint)

    def test_endpoint_discovery_disabled_with_custom_endpoint(self):
        endpoint = "https://custom.domain/"
        config = Config(endpoint_discovery_enabled=False)
        client, http_stubber = self.create_client(
            service_name="test-discovery-endpoint",
            config=config,
            endpoint_url=endpoint
        )
        with http_stubber as stubber:
            stubber.add_response(status=200, body=b'{}')
            client.test_discovery_required(Foo="bar")
            self.assert_discovery_skipped(
                stubber,
                b"test-discovery-endpoint.TestDiscoveryRequired"
            )
            self.assert_endpoint_used(stubber.requests[0].url, endpoint)

    def test_endpoint_discovery_enabled_with_custom_endpoint(self):
        endpoint = "https://custom.domain/"
        config = Config(endpoint_discovery_enabled=True)
        client, http_stubber = self.create_client(
            service_name="test-discovery-endpoint",
            config=config,
            endpoint_url=endpoint
        )
        with http_stubber as stubber:
            stubber.add_response(status=200, body=b'{}')
            client.test_discovery_required(Foo="bar")
            self.assert_discovery_skipped(
                stubber,
                b"test-discovery-endpoint.TestDiscoveryRequired"
            )
            self.assert_endpoint_used(stubber.requests[0].url, endpoint)

    def test_endpoint_discovery_optional_with_custom_endpoint(self):
        endpoint = "https://custom.domain/"
        client, http_stubber = self.create_client(
            service_name="test-discovery-endpoint", endpoint_url=endpoint
        )
        with http_stubber as stubber:
            stubber.add_response(status=200, body=b'{}')
            client.test_discovery_optional(Foo="bar")
            self.assert_discovery_skipped(
                stubber,
                b"test-discovery-endpoint.TestDiscoveryOptional"
            )
            self.assert_endpoint_used(stubber.requests[0].url, endpoint)

    def test_endpoint_discovery_optional_disabled_with_custom_endpoint(self):
        endpoint = "https://custom.domain/"
        config = Config(endpoint_discovery_enabled=False)
        client, http_stubber = self.create_client(
            service_name="test-discovery-endpoint",
            config=config,
            endpoint_url=endpoint
        )
        with http_stubber as stubber:
            stubber.add_response(status=200, body=b'{}')
            client.test_discovery_optional(Foo="bar")
            self.assert_discovery_skipped(
                stubber,
                b"test-discovery-endpoint.TestDiscoveryOptional",
            )
            self.assert_endpoint_used(stubber.requests[0].url, endpoint)

    def test_endpoint_discovery_default_optional_endpoint(self):
        client, http_stubber = self.create_client(service_name="test-discovery-endpoint")
        with http_stubber as stubber:
            stubber.add_response(status=200, body=b'{}')
            client.test_discovery_optional(Foo="bar")
            self.assertEqual(len(stubber.requests), 1)

    def test_endpoint_discovery_enabled_optional_endpoint(self):
        discovered_endpoint = 'https://discovered.domain'
        config = Config(endpoint_discovery_enabled=True)
        client, http_stubber = self.create_client(
            service_name="test-discovery-endpoint", config=config
        )
        with http_stubber as stubber:
            self.add_describe_endpoints_response(stubber, discovered_endpoint)
            client.test_discovery_optional(Foo="bar")
            self.assert_endpoint_discovery_used(stubber, discovered_endpoint)

    def test_endpoint_discovery_manual_auto_on_required_endpoint(self):
        discovered_endpoint = 'https://discovered.domain'
        config = Config(endpoint_discovery_enabled=" aUto  \n")
        client, http_stubber = self.create_client(
            service_name="test-discovery-endpoint", config=config
        )
        with http_stubber as stubber:
            self.add_describe_endpoints_response(stubber, discovered_endpoint)
            client.test_discovery_required(Foo="bar")
            self.assert_endpoint_discovery_used(stubber, discovered_endpoint)

    def test_endpoint_discovery_enabled_with_random_string(self):
        config = Config(endpoint_discovery_enabled="bad value")
        with self.assertRaises(InvalidEndpointDiscoveryConfigurationError):
            client, http_stubber = self.create_client(
                service_name="test-discovery-endpoint", config=config
            )

    def test_endpoint_discovery_required_with_env_var_default(self):
        self.environ['AWS_ENDPOINT_DISCOVERY_ENABLED'] = 'auto'
        discovered_endpoint = 'https://discovered.domain'
        client, http_stubber = self.create_client(
            service_name="test-discovery-endpoint", config=None
        )
        with http_stubber as stubber:
            self.add_describe_endpoints_response(stubber, discovered_endpoint)
            client.test_discovery_required(Foo="bar")
            self.assert_endpoint_discovery_used(stubber, discovered_endpoint)

    def test_endpoint_discovery_optional_with_env_var_default(self):
        self.environ['AWS_ENDPOINT_DISCOVERY_ENABLED'] = 'auto'
        client, http_stubber = self.create_client(
            service_name="test-discovery-endpoint", config=None
        )
        with http_stubber as stubber:
            stubber.add_response(status=200, body=b'{}')
            client.test_discovery_optional(Foo="bar")
            self.assert_discovery_skipped(
                stubber,
                b"test-discovery-endpoint.TestDiscoveryOptional"
            )

    def test_endpoint_discovery_optional_with_env_var_enabled(self):
        self.environ['AWS_ENDPOINT_DISCOVERY_ENABLED'] = "True"
        discovered_endpoint = 'https://discovered.domain'
        client, http_stubber = self.create_client(
            service_name="test-discovery-endpoint"
        )
        with http_stubber as stubber:
            self.add_describe_endpoints_response(stubber, discovered_endpoint)
            client.test_discovery_optional(Foo="bar")
            self.assert_endpoint_discovery_used(stubber, discovered_endpoint)

    def test_endpoint_discovery_required_with_env_var_disabled(self):
        self.environ['AWS_ENDPOINT_DISCOVERY_ENABLED'] = "False"
        discovered_endpoint = 'https://discovered.domain'
        client, http_stubber = self.create_client(
            service_name="test-discovery-endpoint"
        )
        self.add_describe_endpoints_response(http_stubber, discovered_endpoint)
        with self.assertRaises(EndpointDiscoveryRequired):
            client.test_discovery_required(Foo="bar")

    def test_endpoint_discovery_with_config_file_enabled(self):
        with temporary_file('w') as f:
            self.set_endpoint_discovery_config_file(f, "True")
            discovered_endpoint = 'https://discovered.domain'
            client, http_stubber = self.create_client(
                service_name="test-discovery-endpoint"
            )
            with http_stubber as stubber:
                self.add_describe_endpoints_response(stubber, discovered_endpoint)
                client.test_discovery_required(Foo="bar")
                self.assert_endpoint_discovery_used(stubber, discovered_endpoint)

    def test_endpoint_discovery_with_config_file_enabled_lowercase(self):
        with temporary_file('w') as f:
            self.set_endpoint_discovery_config_file(f, "true")
            discovered_endpoint = 'https://discovered.domain'
            client, http_stubber = self.create_client(
                service_name="test-discovery-endpoint"
            )
            with http_stubber as stubber:
                self.add_describe_endpoints_response(stubber, discovered_endpoint)
                client.test_discovery_required(Foo="bar")
                self.assert_endpoint_discovery_used(stubber, discovered_endpoint)

    def test_endpoint_discovery_with_config_file_disabled(self):
        with temporary_file('w') as f:
            self.set_endpoint_discovery_config_file(f, "false")
            discovered_endpoint = 'https://discovered.domain'
            client, http_stubber = self.create_client(
                service_name="test-discovery-endpoint"
            )
            self.add_describe_endpoints_response(http_stubber, discovered_endpoint)
            with self.assertRaises(EndpointDiscoveryRequired):
                client.test_discovery_required(Foo="bar")

    def test_endpoint_discovery_with_config_file_auto(self):
        with temporary_file('w') as f:
            self.set_endpoint_discovery_config_file(f, "AUTO")
            discovered_endpoint = 'https://discovered.domain'
            client, http_stubber = self.create_client(
                service_name="test-discovery-endpoint"
            )
            with http_stubber as stubber:
                self.add_describe_endpoints_response(stubber, discovered_endpoint)
                client.test_discovery_required(Foo="bar")
                self.assert_endpoint_discovery_used(stubber, discovered_endpoint)
