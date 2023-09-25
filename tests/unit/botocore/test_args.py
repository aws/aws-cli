#!/usr/bin/env
# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import socket

import botocore.config
from tests import unittest
import mock

from botocore import args
from botocore import exceptions
from botocore.client import ClientEndpointBridge
from botocore.config import Config
from botocore.configprovider import ConfigValueStore
from botocore.hooks import HierarchicalEmitter
from botocore.model import ServiceModel


class TestCreateClientArgs(unittest.TestCase):
    def setUp(self):
        self.event_emitter = mock.Mock(HierarchicalEmitter)
        self.config_store = ConfigValueStore()
        self.args_create = args.ClientArgsCreator(
            self.event_emitter, None, None, None, None, self.config_store)
        self.service_name = 'ec2'
        self.region = 'us-west-2'
        self.endpoint_url = 'https://ec2/'
        self.service_model = self._get_service_model()
        self.bridge = mock.Mock(ClientEndpointBridge)
        self._set_endpoint_bridge_resolve()
        self._set_resolver_uses_builtin()
        self.default_socket_options = [
            (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        ]

    def _get_service_model(self, service_name=None):
        if service_name is None:
            service_name = self.service_name
        service_model = mock.Mock(ServiceModel)
        service_model.service_name = service_name
        service_model.endpoint_prefix = service_name
        service_model.metadata = {
            'serviceFullName': 'MyService',
            'protocol': 'query'
        }
        service_model.operation_names = []
        return service_model

    def _set_endpoint_bridge_resolve(self, **override_kwargs):
        ret_val = {
            'region_name': self.region,
            'signature_version': 'v4',
            'endpoint_url': self.endpoint_url,
            'signing_name': self.service_name,
            'signing_region': self.region,
            'metadata': {}
        }
        ret_val.update(**override_kwargs)
        self.bridge.resolve.return_value = ret_val

    def _set_resolver_uses_builtin(self, uses_builtin=True):
        self.bridge.resolver_uses_builtin_data.return_value = uses_builtin

    def call_get_client_args(self, **override_kwargs):
        call_kwargs = {
            'service_model': self.service_model,
            'region_name': self.region,
            'is_secure': True,
            'endpoint_url': self.endpoint_url,
            'verify': True,
            'credentials': None,
            'scoped_config': {},
            'client_config': None,
            'endpoint_bridge': self.bridge,
            'endpoints_ruleset_data': {
                'version': '1.0',
                'parameters': {},
                'rules': [],
            },
            'partition_data': {},
        }
        call_kwargs.update(**override_kwargs)
        return self.args_create.get_client_args(**call_kwargs)

    def assert_create_endpoint_call(self, mock_endpoint, **override_kwargs):
        call_kwargs = {
            'endpoint_url': self.endpoint_url,
            'region_name': self.region,
            'response_parser_factory': None,
            'timeout': (60, 60),
            'verify': True,
            'max_pool_connections': 10,
            'proxies': None,
            'proxies_config': None,
            'socket_options': self.default_socket_options,
            'client_cert': None,
        }
        call_kwargs.update(**override_kwargs)
        mock_endpoint.return_value.create_endpoint.assert_called_with(
            self.service_model, **call_kwargs
        )

    def test_compute_s3_configuration(self):
        self.assertIsNone(self.args_create.compute_s3_config(None))

    def test_compute_s3_config_only_config_store(self):
        self.config_store.set_config_variable(
            's3', {'use_accelerate_endpoint': True})
        self.assertEqual(
            self.args_create.compute_s3_config(None),
            {'use_accelerate_endpoint': True}
        )

    def test_client_s3_accelerate_from_client_config(self):
        self.assertEqual(
            self.args_create.compute_s3_config(
                client_config=Config(s3={'use_accelerate_endpoint': True})
            ),
            {'use_accelerate_endpoint': True}
        )

    def test_client_s3_accelerate_client_config_overrides_config_store(self):
        self.config_store.set_config_variable(
            's3', {'use_accelerate_endpoint': False})
        self.assertEqual(
            self.args_create.compute_s3_config(
                client_config=Config(s3={'use_accelerate_endpoint': True})
            ),
            # client_config beats scoped_config
            {'use_accelerate_endpoint': True}
        )

    def test_max_pool_from_client_config_forwarded_to_endpoint_creator(self):
        config = botocore.config.Config(max_pool_connections=20)
        with mock.patch('botocore.args.EndpointCreator') as m:
            self.call_get_client_args(client_config=config)
            self.assert_create_endpoint_call(m, max_pool_connections=20)

    def test_proxies_from_client_config_forwarded_to_endpoint_creator(self):
        proxies = {'http': 'http://foo.bar:1234',
                   'https': 'https://foo.bar:4321'}
        config = botocore.config.Config(proxies=proxies)
        with mock.patch('botocore.args.EndpointCreator') as m:
            self.call_get_client_args(client_config=config)
            self.assert_create_endpoint_call(m, proxies=proxies)

    def test_s3_with_endpoint_url_still_resolves_region(self):
        self.service_model.endpoint_prefix = 's3'
        self.service_model.metadata = {'protocol': 'rest-xml'}
        self.bridge.resolve.side_effect = [
            {
                'region_name': None, 'signature_version': 's3v4',
                'endpoint_url': 'http://other.com/', 'signing_name': 's3',
                'signing_region': None, 'metadata': {}
            },
            {
                'region_name': 'us-west-2', 'signature_version': 's3v4',
                'enpoint_url': 'https://s3-us-west-2.amazonaws.com',
                'signing_name': 's3', 'signing_region': 'us-west-2',
                'metadata': {}
            }
        ]
        client_args = self.call_get_client_args(
            endpoint_url='http://other.com/')
        self.assertEqual(
            client_args['client_config'].region_name, 'us-west-2')

    def test_region_does_not_resolve_if_not_s3_and_endpoint_url_provided(self):
        self.service_model.endpoint_prefix = 'ec2'
        self.service_model.metadata = {'protocol': 'query'}
        self.bridge.resolve.side_effect = [{
            'region_name': None, 'signature_version': 'v4',
            'endpoint_url': 'http://other.com/', 'signing_name': 'ec2',
            'signing_region': None, 'metadata': {}
        }]
        client_args = self.call_get_client_args(
            endpoint_url='http://other.com/')
        self.assertEqual(client_args['client_config'].region_name, None)

    def test_provide_retry_config(self):
        config = botocore.config.Config(retries={'max_attempts': 10})
        client_args = self.call_get_client_args(client_config=config)
        self.assertEqual(
            client_args['client_config'].retries['max_attempts'], 10)

    def test_tcp_keepalive_enabled(self):
        scoped_config = {'tcp_keepalive': 'true'}
        with mock.patch('botocore.args.EndpointCreator') as m:
            self.call_get_client_args(scoped_config=scoped_config)
            self.assert_create_endpoint_call(
                m, socket_options=self.default_socket_options + [
                    (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                ]
            )

    def test_tcp_keepalive_not_specified(self):
        scoped_config = {}
        with mock.patch('botocore.args.EndpointCreator') as m:
            self.call_get_client_args(scoped_config=scoped_config)
            self.assert_create_endpoint_call(
                m, socket_options=self.default_socket_options)

    def test_tcp_keepalive_explicitly_disabled(self):
        scoped_config = {'tcp_keepalive': 'false'}
        with mock.patch('botocore.args.EndpointCreator') as m:
            self.call_get_client_args(scoped_config=scoped_config)
            self.assert_create_endpoint_call(
                m, socket_options=self.default_socket_options)

    def test_tcp_keepalive_enabled_case_insensitive(self):
        scoped_config = {'tcp_keepalive': 'True'}
        with mock.patch('botocore.args.EndpointCreator') as m:
            self.call_get_client_args(scoped_config=scoped_config)
            self.assert_create_endpoint_call(
                m, socket_options=self.default_socket_options + [
                    (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                ]
            )

    def test_client_config_has_use_dualstack_endpoint_flag(self):
        self._set_endpoint_bridge_resolve(
            metadata={
                'tags': ['dualstack']
            }
        )
        client_args = self.call_get_client_args(
            service_model=self._get_service_model('ec2'),
        )
        self.assertTrue(client_args['client_config'].use_dualstack_endpoint)

    def test_client_config_has_use_fips_endpoint_flag(self):
        self._set_endpoint_bridge_resolve(
            metadata={
                'tags': ['fips']
            }
        )
        client_args = self.call_get_client_args(
            service_model=self._get_service_model('ec2'),
        )
        self.assertTrue(client_args['client_config'].use_fips_endpoint)

    def test_client_config_has_both_use_fips_and_use_dualstack__endpoint_flags(self):
        self._set_endpoint_bridge_resolve(
            metadata={
                'tags': ['fips', 'dualstack']
            }
        )
        client_args = self.call_get_client_args(
            service_model=self._get_service_model('ec2'),
        )
        self.assertTrue(client_args['client_config'].use_fips_endpoint)
        self.assertTrue(client_args['client_config'].use_dualstack_endpoint)

    def test_s3_override_use_dualstack_endpoint_flag(self):
        self._set_endpoint_bridge_resolve(
            metadata={
                'tags': ['dualstack']
            }
        )
        client_args = self.call_get_client_args(
            service_model=self._get_service_model('s3'),
        )
        self.assertTrue(client_args['client_config'].s3['use_dualstack_endpoint'])

    def test_sts_use_resolved_endpoint_for_regional_configuration(self):
        resolved_endpoint = 'https://resolved-endpoint'
        resolved_region = 'resolved-region'
        self._set_endpoint_bridge_resolve(
            endpoint_url=resolved_endpoint,
            signing_region=resolved_region
        )
        client_args = self.call_get_client_args(
            service_model=self._get_service_model('sts'),
            region_name='us-west-2', endpoint_url=None
        )
        self.assertEqual(client_args['endpoint'].host, resolved_endpoint)
        self.assertEqual(
            client_args['request_signer'].region_name, resolved_region)

    def test_can_merge_max_attempts(self):
        self.config_store.set_config_variable('max_attempts', 4)
        config = self.call_get_client_args()['client_config']
        self.assertEqual(config.retries['max_attempts'], 4)

    def test_uses_config_value_if_present_for_max_attempts(self):
        config = self.call_get_client_args(
                client_config=Config(retries={'max_attempts': 2})
        )['client_config']
        self.assertEqual(config.retries['max_attempts'], 2)

    def test_uses_client_config_over_config_store_max_attempts(self):
        self.config_store.set_config_variable('max_attempts', 4)
        config = self.call_get_client_args(
                client_config=Config(retries={'max_attempts': 2})
        )['client_config']
        self.assertEqual(config.retries['max_attempts'], 2)

    def test_max_attempts_unset_if_retries_is_none(self):
        config = self.call_get_client_args(
                client_config=Config(retries=None)
        )['client_config']
        self.assertEqual(config.retries, {'mode': 'standard'})

    def test_retry_mode_set_on_config_store(self):
        self.config_store.set_config_variable('retry_mode', 'standard')
        config = self.call_get_client_args()['client_config']
        self.assertEqual(config.retries['mode'], 'standard')

    def test_retry_mode_set_on_client_config(self):
        config = self.call_get_client_args(
                client_config=Config(retries={'mode': 'standard'})
        )['client_config']
        self.assertEqual(config.retries['mode'], 'standard')

    def test_client_config_beats_config_store(self):
        self.config_store.set_config_variable('retry_mode', 'other-mode')
        config = self.call_get_client_args(
                client_config=Config(retries={'mode': 'standard'})
        )['client_config']
        self.assertEqual(config.retries['mode'], 'standard')

    def test_creates_ruleset_resolver_if_given_data(self):
        with mock.patch('botocore.args.EndpointRulesetResolver') as m:
            self.call_get_client_args(
                service_model=self._get_service_model('s3'),
                endpoints_ruleset_data={
                    'version': '1.0',
                    'parameters': {},
                    'rules': [],
                },
            )
            self.assertEqual(len(m.call_args_list), 1)

    def test_doesnt_create_ruleset_resolver_if_not_given_data(self):
        with mock.patch('botocore.args.EndpointRulesetResolver') as m:
            self.call_get_client_args(
                service_model=self._get_service_model('s3'),
                endpoints_ruleset_data=None,
            )
            m.assert_not_called()

    def test_request_compression_client_config(self):
        input_config = Config(
            disable_request_compression=True,
            request_min_compression_size_bytes=100,
        )
        client_args = self.call_get_client_args(client_config=input_config)
        config = client_args['client_config']
        self.assertEqual(config.request_min_compression_size_bytes, 100)
        self.assertTrue(config.disable_request_compression)

    def test_request_compression_config_store(self):
        self.config_store.set_config_variable(
            'request_min_compression_size_bytes', 100
        )
        self.config_store.set_config_variable(
            'disable_request_compression', True
        )
        config = self.call_get_client_args()['client_config']
        self.assertEqual(config.request_min_compression_size_bytes, 100)
        self.assertTrue(config.disable_request_compression)

    def test_request_compression_client_config_overrides_config_store(self):
        self.config_store.set_config_variable(
            'request_min_compression_size_bytes', 100
        )
        self.config_store.set_config_variable(
            'disable_request_compression', True
        )
        input_config = Config(
            disable_request_compression=False,
            request_min_compression_size_bytes=1,
        )
        client_args = self.call_get_client_args(client_config=input_config)
        config = client_args['client_config']
        self.assertEqual(config.request_min_compression_size_bytes, 1)
        self.assertFalse(config.disable_request_compression)

    def test_coercible_value_request_min_compression_size_bytes(self):
        config = Config(request_min_compression_size_bytes='100')
        client_args = self.call_get_client_args(client_config=config)
        config = client_args['client_config']
        self.assertEqual(config.request_min_compression_size_bytes, 100)

    def test_coercible_value_disable_request_compression(self):
        config = Config(disable_request_compression='true')
        client_args = self.call_get_client_args(client_config=config)
        config = client_args['client_config']
        self.assertTrue(config.disable_request_compression)

    def test_bad_type_request_min_compression_size_bytes(self):
        with self.assertRaises(exceptions.InvalidConfigError):
            config = Config(request_min_compression_size_bytes='foo')
            self.call_get_client_args(client_config=config)
        self.config_store.set_config_variable(
            'request_min_compression_size_bytes', 'foo'
        )
        with self.assertRaises(exceptions.InvalidConfigError):
            self.call_get_client_args()

    def test_low_min_request_min_compression_size_bytes(self):
        with self.assertRaises(exceptions.InvalidConfigError):
            config = Config(request_min_compression_size_bytes=0)
            self.call_get_client_args(client_config=config)
        self.config_store.set_config_variable(
            'request_min_compression_size_bytes', 0
        )
        with self.assertRaises(exceptions.InvalidConfigError):
            self.call_get_client_args()

    def test_high_max_request_min_compression_size_bytes(self):
        with self.assertRaises(exceptions.InvalidConfigError):
            config = Config(request_min_compression_size_bytes=9999999)
            self.call_get_client_args(client_config=config)
        self.config_store.set_config_variable(
            'request_min_compression_size_bytes', 9999999
        )
        with self.assertRaises(exceptions.InvalidConfigError):
            self.call_get_client_args()

    def test_bad_value_disable_request_compression(self):
        input_config = Config(disable_request_compression='foo')
        client_args = self.call_get_client_args(client_config=input_config)
        config = client_args['client_config']
        self.assertFalse(config.disable_request_compression)


class TestEndpointResolverBuiltins(unittest.TestCase):
    def setUp(self):
        event_emitter = mock.Mock(HierarchicalEmitter)
        self.config_store = ConfigValueStore()
        self.args_create = args.ClientArgsCreator(
            event_emitter=event_emitter,
            user_agent=None,
            response_parser_factory=None,
            loader=None,
            exceptions_factory=None,
            config_store=self.config_store,
        )
        self.bridge = ClientEndpointBridge(
            endpoint_resolver=mock.Mock(),
            scoped_config=None,
            client_config=Config(),
            default_endpoint=None,
            service_signing_name=None,
            config_store=self.config_store,
        )
        # assume a legacy endpoint resolver that uses the builtin
        # endpoints.json file
        self.bridge.endpoint_resolver.uses_builtin_data = True

    def call_compute_endpoint_resolver_builtin_defaults(self, **overrides):
        defaults = {
            'region_name': 'ca-central-1',
            'service_name': 'fooservice',
            's3_config': {},
            'endpoint_bridge': self.bridge,
            'client_endpoint_url': None,
            'legacy_endpoint_url': 'https://my.legacy.endpoint.com',
        }
        kwargs = {**defaults, **overrides}
        return self.args_create.compute_endpoint_resolver_builtin_defaults(
            **kwargs
        )

    def test_builtins_defaults(self):
        bins = self.call_compute_endpoint_resolver_builtin_defaults()

        self.assertEqual(bins['AWS::Region'], 'ca-central-1')
        self.assertEqual(bins['AWS::UseFIPS'], False)
        self.assertEqual(bins['AWS::UseDualStack'], False)
        self.assertEqual(bins['AWS::STS::UseGlobalEndpoint'], False)
        self.assertEqual(bins['AWS::S3::UseGlobalEndpoint'], False)
        self.assertEqual(bins['AWS::S3::Accelerate'], False)
        self.assertEqual(bins['AWS::S3::ForcePathStyle'], False)
        self.assertEqual(bins['AWS::S3::UseArnRegion'], True)
        self.assertEqual(bins['AWS::S3Control::UseArnRegion'], False)
        self.assertEqual(
            bins['AWS::S3::DisableMultiRegionAccessPoints'], False
        )
        self.assertEqual(bins['SDK::Endpoint'], None)

    def test_aws_region(self):
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            region_name='my-region-1',
        )
        self.assertEqual(bins['AWS::Region'], 'my-region-1')

    def test_aws_use_fips_when_config_is_set_true(self):
        self.config_store.set_config_variable('use_fips_endpoint', True)
        bins = self.call_compute_endpoint_resolver_builtin_defaults()
        self.assertEqual(bins['AWS::UseFIPS'], True)

    def test_aws_use_fips_when_config_is_set_false(self):
        self.config_store.set_config_variable('use_fips_endpoint', False)
        bins = self.call_compute_endpoint_resolver_builtin_defaults()
        self.assertEqual(bins['AWS::UseFIPS'], False)

    def test_aws_use_dualstack_when_config_is_set_true(self):
        self.bridge.client_config = Config(s3={'use_dualstack_endpoint': True})
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            service_name='s3-control'
        )
        self.assertEqual(bins['AWS::UseDualStack'], True)

    def test_aws_use_dualstack_when_config_is_set_false(self):
        self.bridge.client_config = Config(
            s3={'use_dualstack_endpoint': False}
        )
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            service_name='s3-control'
        )
        self.assertEqual(bins['AWS::UseDualStack'], False)

    def test_aws_use_dualstack_when_non_dualstack_service(self):
        self.bridge.client_config = Config(s3={'use_dualstack_endpoint': True})
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            service_name='other-service'
        )
        self.assertEqual(bins['AWS::UseDualStack'], False)

    def test_aws_sts_global_endpoint_with_default_and_nonlegacy_region(self):
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            region_name='eu-south-1',
        )
        self.assertEqual(bins['AWS::STS::UseGlobalEndpoint'], False)

    def test_aws_sts_global_endpoint_with_nondefault_config(self):
        self.config_store.set_config_variable(
            'sts_regional_endpoints', 'regional'
        )
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            region_name='us-west-2',
        )
        self.assertEqual(bins['AWS::STS::UseGlobalEndpoint'], False)

    def test_s3_accelerate_with_config_set_true(self):
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            s3_config={'use_accelerate_endpoint': True},
        )
        self.assertEqual(bins['AWS::S3::Accelerate'], True)

    def test_s3_accelerate_with_config_set_false(self):
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            s3_config={'use_accelerate_endpoint': False},
        )
        self.assertEqual(bins['AWS::S3::Accelerate'], False)

    def test_force_path_style_with_config_set_to_path(self):
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            s3_config={'addressing_style': 'path'},
        )
        self.assertEqual(bins['AWS::S3::ForcePathStyle'], True)

    def test_force_path_style_with_config_set_to_auto(self):
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            s3_config={'addressing_style': 'auto'},
        )
        self.assertEqual(bins['AWS::S3::ForcePathStyle'], False)

    def test_force_path_style_with_config_set_to_virtual(self):
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            s3_config={'addressing_style': 'virtual'},
        )
        self.assertEqual(bins['AWS::S3::ForcePathStyle'], False)

    def test_use_arn_region_with_config_set_false(self):
        # These two builtins both take their value from the ``use_arn_region``
        # in the S3 configuration, but have different default values.
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            s3_config={'use_arn_region': False},
        )
        self.assertEqual(bins['AWS::S3::UseArnRegion'], False)
        self.assertEqual(bins['AWS::S3Control::UseArnRegion'], False)

    def test_use_arn_region_with_config_set_true(self):
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            s3_config={'use_arn_region': True},
        )
        self.assertEqual(bins['AWS::S3::UseArnRegion'], True)
        self.assertEqual(bins['AWS::S3Control::UseArnRegion'], True)

    def test_disable_mrap_with_config_set_true(self):
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            s3_config={'s3_disable_multiregion_access_points': True},
        )
        self.assertEqual(bins['AWS::S3::DisableMultiRegionAccessPoints'], True)

    def test_disable_mrap_with_config_set_false(self):
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            s3_config={'s3_disable_multiregion_access_points': False},
        )
        self.assertEqual(
            bins['AWS::S3::DisableMultiRegionAccessPoints'], False
        )

    def test_sdk_endpoint_both_inputs_set(self):
        # assume a legacy endpoint resolver that uses a customized
        # endpoints.json file
        self.bridge.endpoint_resolver.uses_builtin_data = False
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            client_endpoint_url='https://my.client.endpoint.com',
            legacy_endpoint_url='https://my.legacy.endpoint.com',
        )
        self.assertEqual(
            bins['SDK::Endpoint'], 'https://my.client.endpoint.com'
        )

    def test_sdk_endpoint_legacy_set_with_builtin_data(self):
        # assume a legacy endpoint resolver that uses a customized
        # endpoints.json file
        self.bridge.endpoint_resolver.uses_builtin_data = False
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            client_endpoint_url=None,
            legacy_endpoint_url='https://my.legacy.endpoint.com',
        )
        self.assertEqual(
            bins['SDK::Endpoint'], 'https://my.legacy.endpoint.com'
        )

    def test_sdk_endpoint_legacy_set_without_builtin_data(self):
        # assume a legacy endpoint resolver that uses the builtin
        # endpoints.json file
        self.bridge.endpoint_resolver.uses_builtin_data = True
        bins = self.call_compute_endpoint_resolver_builtin_defaults(
            client_endpoint_url=None,
            legacy_endpoint_url='https://my.legacy.endpoint.com',
        )
        self.assertEqual(bins['SDK::Endpoint'], None)
