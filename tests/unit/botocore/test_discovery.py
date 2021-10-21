import time
from mock import Mock, call
from tests import unittest

from botocore.awsrequest import AWSRequest
from botocore.client import ClientMeta
from botocore.hooks import HierarchicalEmitter
from botocore.model import ServiceModel
from botocore.exceptions import ConnectionError
from botocore.handlers import inject_api_version_header_if_needed
from botocore.discovery import (
    EndpointDiscoveryManager, EndpointDiscoveryHandler,
    EndpointDiscoveryRequired, EndpointDiscoveryRefreshFailed,
    block_endpoint_discovery_required_operations,
)


class BaseEndpointDiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.service_description = {
            'version': '2.0',
            'metadata': {
                'apiVersion': '2018-08-31',
                'endpointPrefix': 'fooendpoint',
                'jsonVersion': '1.1',
                'protocol': 'json',
                'serviceAbbreviation': 'FooService',
                'serviceId': 'FooService',
                'serviceFullName': 'AwsFooService',
                'signatureVersion': 'v4',
                'signingName': 'awsfooservice',
                'targetPrefix': 'awsfooservice'
            },
            'operations': {
                'DescribeEndpoints': {
                    'name': 'DescribeEndpoints',
                    'http': {
                        'method': 'POST',
                        'requestUri': '/'
                    },
                    'input': {'shape': 'DescribeEndpointsRequest'},
                    'output': {'shape': 'DescribeEndpointsResponse'},
                    'endpointoperation': True
                },
                'TestDiscoveryRequired': {
                    'name': 'TestDiscoveryRequired',
                    'http': {
                        'method': 'POST',
                        'requestUri': '/'
                    },
                    'input': {'shape': 'TestDiscoveryIdsRequest'},
                    'output': {'shape': 'EmptyStruct'},
                    'endpointdiscovery': {'required': True}
                },
                'TestDiscoveryOptional': {
                    'name': 'TestDiscoveryOptional',
                    'http': {
                        'method': 'POST',
                        'requestUri': '/'
                    },
                    'input': {'shape': 'TestDiscoveryIdsRequest'},
                    'output': {'shape': 'EmptyStruct'},
                    'endpointdiscovery': {}
                },
                'TestDiscovery': {
                    'name': 'TestDiscovery',
                    'http': {
                        'method': 'POST',
                        'requestUri': '/'
                    },
                    'input': {'shape': 'EmptyStruct'},
                    'output': {'shape': 'EmptyStruct'},
                    'endpointdiscovery': {}
                },
            },
            'shapes': {
                'Boolean': {'type': 'boolean'},
                'DescribeEndpointsRequest': {
                    'type': 'structure',
                    'members': {
                        'Operation': {'shape': 'String'},
                        'Identifiers': {'shape': 'Identifiers'}
                    }
                },
                'DescribeEndpointsResponse': {
                    'type': 'structure',
                    'required': ['Endpoints'],
                    'members': {
                        'Endpoints': {'shape': 'Endpoints'}
                    }
                },
                'Endpoint': {
                    'type': 'structure',
                    'required': [
                        'Address',
                        'CachePeriodInMinutes'
                    ],
                    'members': {
                        'Address': {'shape': 'String'},
                        'CachePeriodInMinutes': {'shape': 'Long'}
                    }
                },
                'Endpoints': {
                    'type': 'list',
                    'member': {'shape': 'Endpoint'}
                },
                'Identifiers': {
                    'type': 'map',
                    'key': {'shape': 'String'},
                    'value': {'shape': 'String'}
                },
                'Long': {'type': 'long'},
                'String': {'type': 'string'},
                'TestDiscoveryIdsRequest': {
                    'type': 'structure',
                    'required': ['Foo', 'Nested'],
                    'members': {
                        'Foo': {
                            'shape': 'String',
                            'endpointdiscoveryid': True,
                        },
                        'Baz': {'shape': 'String'},
                        'Nested': {'shape': 'Nested'}
                    }
                },
                'EmptyStruct': {
                    'type': 'structure',
                    'members': {}
                },
                'Nested': {
                    'type': 'structure',
                    'required': 'Bar',
                    'members': {
                        'Bar': {
                            'shape': 'String',
                            'endpointdiscoveryid': True,
                        }
                    }
                }
            }
        }


class TestEndpointDiscoveryManager(BaseEndpointDiscoveryTest):
    def setUp(self):
        super(TestEndpointDiscoveryManager, self).setUp()
        self.construct_manager()

    def construct_manager(self, cache=None, time=None, side_effect=None):
        self.service_model = ServiceModel(self.service_description)
        self.meta = Mock(spec=ClientMeta)
        self.meta.service_model = self.service_model
        self.client = Mock()
        if side_effect is None:
            side_effect = [{
                'Endpoints': [{
                    'Address': 'new.com',
                    'CachePeriodInMinutes': 2,
                }]
            }]
        self.client.describe_endpoints.side_effect = side_effect
        self.client.meta = self.meta
        self.manager = EndpointDiscoveryManager(
            self.client, cache=cache, current_time=time
        )

    def test_injects_api_version_if_endpoint_operation(self):
        model = self.service_model.operation_model('DescribeEndpoints')
        params = {'headers': {}}
        inject_api_version_header_if_needed(model, params)
        self.assertEqual(params['headers'].get('x-amz-api-version'),
                         '2018-08-31')

    def test_no_inject_api_version_if_not_endpoint_operation(self):
        model = self.service_model.operation_model('TestDiscoveryRequired')
        params = {'headers': {}}
        inject_api_version_header_if_needed(model, params)
        self.assertNotIn('x-amz-api-version', params['headers'])

    def test_gather_identifiers(self):
        params = {
            'Foo': 'value1',
            'Nested': {'Bar': 'value2'}
        }
        operation = self.service_model.operation_model('TestDiscoveryRequired')
        ids = self.manager.gather_identifiers(operation, params)
        self.assertEqual(ids, {'Foo': 'value1', 'Bar': 'value2'})

    def test_gather_identifiers_none(self):
        operation = self.service_model.operation_model('TestDiscovery')
        ids = self.manager.gather_identifiers(operation, {})
        self.assertEqual(ids, {})

    def test_describe_endpoint(self):
        kwargs = {
            'Operation': 'FooBar',
            'Identifiers': {'Foo': 'value1', 'Bar': 'value2'},
        }
        self.manager.describe_endpoint(**kwargs)
        self.client.describe_endpoints.assert_called_with(**kwargs)

    def test_describe_endpoint_no_input(self):
        describe = self.service_description['operations']['DescribeEndpoints']
        del describe['input']
        self.construct_manager()
        self.manager.describe_endpoint(Operation='FooBar', Identifiers={})
        self.client.describe_endpoints.assert_called_with()

    def test_describe_endpoint_empty_input(self):
        describe = self.service_description['operations']['DescribeEndpoints']
        describe['input'] = {'shape': 'EmptyStruct'}
        self.construct_manager()
        self.manager.describe_endpoint(Operation='FooBar', Identifiers={})
        self.client.describe_endpoints.assert_called_with()

    def test_describe_endpoint_ids_and_operation(self):
        cache = {}
        self.construct_manager(cache=cache)
        ids = {'Foo': 'value1', 'Bar': 'value2'}
        kwargs = {
            'Operation': 'TestDiscoveryRequired',
            'Identifiers': ids,
        }
        self.manager.describe_endpoint(**kwargs)
        self.client.describe_endpoints.assert_called_with(**kwargs)
        key = ((('Bar', 'value2'), ('Foo', 'value1')), 'TestDiscoveryRequired')
        self.assertIn(key, cache)
        self.assertEqual(cache[key][0]['Address'], 'new.com')
        self.manager.describe_endpoint(**kwargs)
        call_count = self.client.describe_endpoints.call_count
        self.assertEqual(call_count, 1)

    def test_describe_endpoint_no_ids_or_operation(self):
        cache = {}
        describe = self.service_description['operations']['DescribeEndpoints']
        describe['input'] = {'shape': 'EmptyStruct'}
        self.construct_manager(cache=cache)
        self.manager.describe_endpoint(
            Operation='TestDiscoveryRequired', Identifiers={}
        )
        self.client.describe_endpoints.assert_called_with()
        key = ()
        self.assertIn(key, cache)
        self.assertEqual(cache[key][0]['Address'], 'new.com')
        self.manager.describe_endpoint(
            Operation='TestDiscoveryRequired', Identifiers={}
        )
        call_count = self.client.describe_endpoints.call_count
        self.assertEqual(call_count, 1)

    def test_describe_endpoint_expired_entry(self):
        current_time = time.time()
        key = ()
        cache = {
            key: [{'Address': 'old.com', 'Expiration': current_time - 10}]
        }
        self.construct_manager(cache=cache)
        kwargs = {
            'Identifiers': {},
            'Operation': 'TestDiscoveryRequired',
        }
        self.manager.describe_endpoint(**kwargs)
        self.client.describe_endpoints.assert_called_with()
        self.assertIn(key, cache)
        self.assertEqual(cache[key][0]['Address'], 'new.com')
        self.manager.describe_endpoint(**kwargs)
        call_count = self.client.describe_endpoints.call_count
        self.assertEqual(call_count, 1)

    def test_describe_endpoint_cache_expiration(self):
        def _time():
            return float(0)
        cache = {}
        self.construct_manager(cache=cache, time=_time)
        self.manager.describe_endpoint(
            Operation='TestDiscoveryRequired', Identifiers={}
        )
        key = ()
        self.assertIn(key, cache)
        self.assertEqual(cache[key][0]['Expiration'], float(120))

    def test_delete_endpoints_present(self):
        key = ()
        cache = {
            key: [{'Address': 'old.com', 'Expiration': 0}]
        }
        self.construct_manager(cache=cache)
        kwargs = {
            'Identifiers': {},
            'Operation': 'TestDiscoveryRequired',
        }
        self.manager.delete_endpoints(**kwargs)
        self.assertEqual(cache, {})

    def test_delete_endpoints_absent(self):
        cache = {}
        self.construct_manager(cache=cache)
        kwargs = {
            'Identifiers': {},
            'Operation': 'TestDiscoveryRequired',
        }
        self.manager.delete_endpoints(**kwargs)
        self.assertEqual(cache, {})

    def test_describe_endpoint_optional_fails_no_cache(self):
        side_effect = [ConnectionError(error=None)]
        self.construct_manager(side_effect=side_effect)
        kwargs = {'Operation': 'TestDiscoveryOptional'}
        endpoint = self.manager.describe_endpoint(**kwargs)
        self.assertIsNone(endpoint)
        # This second call should be blocked as we just failed
        endpoint = self.manager.describe_endpoint(**kwargs)
        self.assertIsNone(endpoint)
        self.client.describe_endpoints.call_args_list == [call()]

    def test_describe_endpoint_optional_fails_stale_cache(self):
        key = ()
        cache = {
            key: [{'Address': 'old.com', 'Expiration': 0}]
        }
        side_effect = [ConnectionError(error=None)] * 2
        self.construct_manager(cache=cache, side_effect=side_effect)
        kwargs = {'Operation': 'TestDiscoveryOptional'}
        endpoint = self.manager.describe_endpoint(**kwargs)
        self.assertEqual(endpoint, 'old.com')
        # This second call shouldn't go through as we just failed
        endpoint = self.manager.describe_endpoint(**kwargs)
        self.assertEqual(endpoint, 'old.com')
        self.client.describe_endpoints.call_args_list == [call()]

    def test_describe_endpoint_required_fails_no_cache(self):
        side_effect = [ConnectionError(error=None)] * 2
        self.construct_manager(side_effect=side_effect)
        kwargs = {'Operation': 'TestDiscoveryRequired'}
        with self.assertRaises(EndpointDiscoveryRefreshFailed):
            self.manager.describe_endpoint(**kwargs)
        # This second call should go through, as we have no cache
        with self.assertRaises(EndpointDiscoveryRefreshFailed):
            self.manager.describe_endpoint(**kwargs)
        describe_count = self.client.describe_endpoints.call_count
        self.assertEqual(describe_count, 2)

    def test_describe_endpoint_required_fails_stale_cache(self):
        key = ()
        cache = {
            key: [{'Address': 'old.com', 'Expiration': 0}]
        }
        side_effect = [ConnectionError(error=None)] * 2
        self.construct_manager(cache=cache, side_effect=side_effect)
        kwargs = {'Operation': 'TestDiscoveryRequired'}
        endpoint = self.manager.describe_endpoint(**kwargs)
        self.assertEqual(endpoint, 'old.com')
        # We have a stale endpoint, so this shouldn't fail or force a refresh
        endpoint = self.manager.describe_endpoint(**kwargs)
        self.assertEqual(endpoint, 'old.com')
        self.client.describe_endpoints.call_args_list == [call()]

    def test_describe_endpoint_required_force_refresh_success(self):
        side_effect = [
            ConnectionError(error=None),
            {'Endpoints': [{
                'Address': 'new.com',
                'CachePeriodInMinutes': 2,
            }]},
        ]
        self.construct_manager(side_effect=side_effect)
        kwargs = {'Operation': 'TestDiscoveryRequired'}
        # First call will fail
        with self.assertRaises(EndpointDiscoveryRefreshFailed):
            self.manager.describe_endpoint(**kwargs)
        self.client.describe_endpoints.call_args_list == [call()]
        # Force a refresh if the cache is empty but discovery is required
        endpoint = self.manager.describe_endpoint(**kwargs)
        self.assertEqual(endpoint, 'new.com')

    def test_describe_endpoint_retries_after_failing(self):
        fake_time = Mock()
        fake_time.side_effect = [0, 100, 200]
        side_effect = [
            ConnectionError(error=None),
            {'Endpoints': [{
                'Address': 'new.com',
                'CachePeriodInMinutes': 2,
            }]},
        ]
        self.construct_manager(side_effect=side_effect, time=fake_time)
        kwargs = {'Operation': 'TestDiscoveryOptional'}
        endpoint = self.manager.describe_endpoint(**kwargs)
        self.assertIsNone(endpoint)
        self.client.describe_endpoints.call_args_list == [call()]
        # Second time should try again as enough time has elapsed
        endpoint = self.manager.describe_endpoint(**kwargs)
        self.assertEqual(endpoint, 'new.com')


class TestEndpointDiscoveryHandler(BaseEndpointDiscoveryTest):
    def setUp(self):
        super(TestEndpointDiscoveryHandler, self).setUp()
        self.manager = Mock(spec=EndpointDiscoveryManager)
        self.handler = EndpointDiscoveryHandler(self.manager)
        self.service_model = ServiceModel(self.service_description)

    def test_register_handler(self):
        events = Mock(spec=HierarchicalEmitter)
        self.handler.register(events, 'foo-bar')
        events.register.assert_any_call(
            'before-parameter-build.foo-bar', self.handler.gather_identifiers
        )
        events.register.assert_any_call(
            'needs-retry.foo-bar', self.handler.handle_retries
        )
        events.register_first.assert_called_with(
            'request-created.foo-bar', self.handler.discover_endpoint
        )

    def test_discover_endpoint(self):
        request = AWSRequest()
        request.context = {
            'discovery': {'identifiers': {}}
        }
        self.manager.describe_endpoint.return_value = 'https://new.foo'
        self.handler.discover_endpoint(request, 'TestOperation')
        self.assertEqual(request.url, 'https://new.foo')
        self.manager.describe_endpoint.assert_called_with(
            Operation='TestOperation', Identifiers={}
        )

    def test_discover_endpoint_fails(self):
        request = AWSRequest()
        request.context = {
            'discovery': {'identifiers': {}}
        }
        request.url = 'old.com'
        self.manager.describe_endpoint.return_value = None
        self.handler.discover_endpoint(request, 'TestOperation')
        self.assertEqual(request.url, 'old.com')
        self.manager.describe_endpoint.assert_called_with(
            Operation='TestOperation', Identifiers={}
        )

    def test_discover_endpoint_no_protocol(self):
        request = AWSRequest()
        request.context = {
            'discovery': {'identifiers': {}}
        }
        self.manager.describe_endpoint.return_value = 'new.foo'
        self.handler.discover_endpoint(request, 'TestOperation')
        self.assertEqual(request.url, 'https://new.foo')
        self.manager.describe_endpoint.assert_called_with(
            Operation='TestOperation', Identifiers={}
        )

    def test_inject_no_context(self):
        request = AWSRequest(url='https://original.foo')
        self.handler.discover_endpoint(request, 'TestOperation')
        self.assertEqual(request.url, 'https://original.foo')
        self.manager.describe_endpoint.assert_not_called()

    def test_gather_identifiers(self):
        context = {}
        params = {
            'Foo': 'value1',
            'Nested': {'Bar': 'value2'}
        }
        ids = {
            'Foo': 'value1',
            'Bar': 'value2'
        }
        model = self.service_model.operation_model('TestDiscoveryRequired')
        self.manager.gather_identifiers.return_value = ids
        self.handler.gather_identifiers(params, model, context)
        self.assertEqual(context['discovery']['identifiers'], ids)

    def test_gather_identifiers_not_discoverable(self):
        context = {}
        model = self.service_model.operation_model('DescribeEndpoints')
        self.handler.gather_identifiers({}, model, context)
        self.assertEqual(context, {})

    def test_discovery_disabled_but_required(self):
        model = self.service_model.operation_model('TestDiscoveryRequired')
        with self.assertRaises(EndpointDiscoveryRequired):
            block_endpoint_discovery_required_operations(model)

    def test_discovery_disabled_but_optional(self):
        context = {}
        model = self.service_model.operation_model('TestDiscoveryOptional')
        block_endpoint_discovery_required_operations(model, context=context)
        self.assertEqual(context, {})

    def test_does_not_retry_no_response(self):
        retry = self.handler.handle_retries(None, None, None)
        self.assertIsNone(retry)

    def test_does_not_retry_other_errors(self):
        parsed_response = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        response = (None, parsed_response)
        retry = self.handler.handle_retries(None, response, None)
        self.assertIsNone(retry)

    def test_does_not_retry_if_no_context(self):
        request_dict = {'context': {}}
        parsed_response = {
            'ResponseMetadata': {'HTTPStatusCode': 421}
        }
        response = (None, parsed_response)
        retry = self.handler.handle_retries(request_dict, response, None)
        self.assertIsNone(retry)

    def _assert_retries(self, parsed_response):
        request_dict = {
            'context': {
                'discovery': {'identifiers': {}}
            }
        }
        response = (None, parsed_response)
        model = self.service_model.operation_model('TestDiscoveryOptional')
        retry = self.handler.handle_retries(request_dict, response, model)
        self.assertEqual(retry, 0)
        self.manager.delete_endpoints.assert_called_with(
            Operation='TestDiscoveryOptional', Identifiers={}
        )

    def test_retries_421_status_code(self):
        parsed_response = {
            'ResponseMetadata': {'HTTPStatusCode': 421}
        }
        self._assert_retries(parsed_response)

    def test_retries_invalid_endpoint_exception(self):
        parsed_response = {'Error': {'Code': 'InvalidEndpointException'}}
        self._assert_retries(parsed_response)
