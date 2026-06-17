#!/usr/bin/env
# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import logging
import os
import shutil
import tempfile

import pytest

import botocore.config
import botocore.exceptions
import botocore.loaders
import botocore.session
from botocore import (
    UNSIGNED,
    client,
    register_initializer,
    unregister_initializer,
)
from botocore.configprovider import ConfigChainFactory
from botocore.hooks import HierarchicalEmitter
from botocore.model import ServiceModel
from botocore.paginate import PaginatorModel
from botocore.waiter import WaiterModel
from tests import create_session, mock, requires_crt, temporary_file, unittest


class BaseSessionTest(unittest.TestCase):
    def setUp(self):
        self.environ = {}
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()
        self.environ['FOO_PROFILE'] = 'foo'
        self.environ['FOO_REGION'] = 'us-west-11'
        data_path = os.path.join(os.path.dirname(__file__), 'data')
        self.environ['FOO_DATA_PATH'] = data_path
        config_path = os.path.join(
            os.path.dirname(__file__), 'cfg', 'foo_config'
        )
        self.environ['FOO_CONFIG_FILE'] = config_path
        self.session = create_session()
        config_chain_builder = ConfigChainFactory(
            session=self.session,
            environ=self.environ,
        )
        config_store = self.session.get_component('config_store')
        config_updates = {
            'profile': config_chain_builder.create_config_chain(
                instance_name='profile',
                env_var_names='FOO_PROFILE',
            ),
            'region': config_chain_builder.create_config_chain(
                instance_name='region',
                env_var_names='FOO_REGION',
                config_property_names='foo_region',
            ),
            'data_path': config_chain_builder.create_config_chain(
                instance_name='data_path',
                env_var_names='FOO_DATA_PATH',
                config_property_names='data_path',
            ),
            'config_file': config_chain_builder.create_config_chain(
                instance_name='config_file',
                env_var_names='FOO_CONFIG_FILE',
            ),
            'credentials_file': config_chain_builder.create_config_chain(
                instance_name='credentials_file',
                default='/tmp/nowhere',
            ),
            'ca_bundle': config_chain_builder.create_config_chain(
                instance_name='ca_bundle',
                env_var_names='FOO_AWS_CA_BUNDLE',
                config_property_names='foo_ca_bundle',
            ),
            'api_versions': config_chain_builder.create_config_chain(
                instance_name='api_versions',
                config_property_names='foo_api_versions',
                default={},
            ),
        }
        for name, provider in config_updates.items():
            config_store.set_config_provider(name, provider)

    def update_session_config_mapping(self, logical_name, **kwargs):
        config_chain_builder = ConfigChainFactory(
            session=self.session,
            environ=self.environ,
        )
        self.session.get_component('config_store').set_config_provider(
            logical_name,
            config_chain_builder.create_config_chain(**kwargs),
        )

    def tearDown(self):
        self.environ_patch.stop()


class SessionTest(BaseSessionTest):
    def close_log_file_handler(self, tempdir, filename):
        logger = logging.getLogger('botocore')
        handlers = logger.handlers
        for handler in handlers[:]:
            if hasattr(handler, 'stream') and handler.stream.name == filename:
                handler.stream.close()
                logger.removeHandler(handler)
                os.remove(filename)
                # logging has an atexit handler that will try to flush/close
                # the file.  By setting this flag to False, we'll prevent it
                # from raising an exception, which is fine because we're
                # handling the closing of the file ourself.
                logging.raiseExceptions = False
        shutil.rmtree(tempdir)

    def test_supports_multiple_env_vars_for_single_logical_name(self):
        self.update_session_config_mapping(
            'profile', env_var_names=['BAR_DEFAULT_PROFILE', 'BAR_PROFILE']
        )
        self.environ['BAR_DEFAULT_PROFILE'] = 'first'
        self.environ['BAR_PROFILE'] = 'second'
        self.assertEqual(self.session.get_config_variable('profile'), 'first')

    def test_profile_when_set_explicitly(self):
        session = create_session(profile='asdf')
        self.assertEqual(session.profile, 'asdf')

    def test_profile_when_pulled_from_env(self):
        self.environ['FOO_PROFILE'] = 'bar'
        # Even though we didn't explicitly pass in a profile, the
        # profile property will still look this up for us.
        self.assertEqual(self.session.profile, 'bar')

    def test_multiple_env_vars_uses_second_var(self):
        self.update_session_config_mapping(
            'profile', env_var_names=['BAR_DEFAULT_PROFILE', 'BAR_PROFILE']
        )
        self.environ.pop('BAR_DEFAULT_PROFILE', None)
        self.environ['BAR_PROFILE'] = 'second'
        self.assertEqual(self.session.get_config_variable('profile'), 'second')

    def test_profile_does_not_exist_raises_exception(self):
        # Given we have no profile:
        self.environ['FOO_PROFILE'] = 'profile_that_does_not_exist'
        with self.assertRaises(botocore.exceptions.ProfileNotFound):
            self.session.get_scoped_config()

    def test_variable_does_not_exist(self):
        self.assertIsNone(self.session.get_config_variable('foo/bar'))

    def test_get_aws_services_in_alphabetical_order(self):
        services = self.session.get_available_services()
        self.assertEqual(sorted(services), services)

    def test_profile_does_not_exist_with_default_profile(self):
        config = self.session.get_scoped_config()
        # We should have loaded this properly, and we'll check
        # that foo_access_key which is defined in the config
        # file should be present in the loaded config dict.
        self.assertIn('aws_access_key_id', config)

    def test_type_conversions_occur_when_specified(self):
        # Specify that we can retrieve the var from the
        # FOO_TIMEOUT env var, with a conversion function
        # of int().
        self.update_session_config_mapping(
            'metadata_service_timeout',
            env_var_names='FOO_TIMEOUT',
            conversion_func=int,
        )
        # Environment variables are always strings.
        self.environ['FOO_TIMEOUT'] = '10'
        # But we should type convert this to a string.
        self.assertEqual(
            self.session.get_config_variable('metadata_service_timeout'), 10
        )

    def test_default_profile_specified_raises_exception(self):
        # If you explicity set the default profile and you don't
        # have that in your config file, an exception is raised.
        config_path = os.path.join(
            os.path.dirname(__file__), 'cfg', 'boto_config_empty'
        )
        self.environ['FOO_CONFIG_FILE'] = config_path
        self.environ['FOO_PROFILE'] = 'default'
        # In this case, even though we specified default, because
        # the boto_config_empty config file does not have a default
        # profile, we should be raising an exception.
        with self.assertRaises(botocore.exceptions.ProfileNotFound):
            self.session.get_scoped_config()

    def test_file_logger(self):
        tempdir = tempfile.mkdtemp()
        temp_file = os.path.join(tempdir, 'file_logger')
        self.session.set_file_logger(logging.DEBUG, temp_file)
        self.addCleanup(self.close_log_file_handler, tempdir, temp_file)
        self.session.get_credentials()
        self.assertTrue(os.path.isfile(temp_file))
        with open(temp_file) as logfile:
            s = logfile.read()
        self.assertTrue('Looking for credentials' in s)

    def test_full_config_property(self):
        full_config = self.session.full_config
        self.assertTrue('foo' in full_config['profiles'])
        self.assertTrue('default' in full_config['profiles'])

    def test_full_config_merges_creds_file_data(self):
        with temporary_file('w') as f:
            self.session.set_config_variable('credentials_file', f.name)
            f.write('[newprofile]\n')
            f.write('aws_access_key_id=FROM_CREDS_FILE_1\n')
            f.write('aws_secret_access_key=FROM_CREDS_FILE_2\n')
            f.flush()

            full_config = self.session.full_config
            self.assertEqual(
                full_config['profiles']['newprofile'],
                {
                    'aws_access_key_id': 'FROM_CREDS_FILE_1',
                    'aws_secret_access_key': 'FROM_CREDS_FILE_2',
                },
            )

    def test_path_not_in_available_profiles(self):
        with temporary_file('w') as f:
            self.session.set_config_variable('credentials_file', f.name)
            f.write('[newprofile]\n')
            f.write('aws_access_key_id=FROM_CREDS_FILE_1\n')
            f.write('aws_secret_access_key=FROM_CREDS_FILE_2\n')
            f.flush()

            profiles = self.session.available_profiles
            self.assertEqual(set(profiles), {'foo', 'default', 'newprofile'})

    def test_emit_delegates_to_emitter(self):
        calls = []

        def handler(**kwargs):
            return calls.append(kwargs)

        self.session.register('foo', handler)
        self.session.emit('foo')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['event_name'], 'foo')

    def test_emitter_can_be_passed_in(self):
        events = HierarchicalEmitter()
        session = create_session(event_hooks=events)
        calls = []

        def handler(**kwargs):
            return calls.append(kwargs)

        events.register('foo', handler)

        session.emit('foo')
        self.assertEqual(len(calls), 1)

    def test_emit_first_non_none(self):
        self.session.register('foo', lambda **kwargs: None)
        self.session.register('foo', lambda **kwargs: 'first')
        self.session.register('foo', lambda **kwargs: 'second')
        response = self.session.emit_first_non_none_response('foo')
        self.assertEqual(response, 'first')

    @mock.patch('logging.getLogger')
    @mock.patch('logging.FileHandler')
    def test_logger_name_can_be_passed_in(self, file_handler, get_logger):
        self.session.set_debug_logger('botocore.hooks')
        get_logger.assert_called_with('botocore.hooks')

        self.session.set_file_logger('DEBUG', 'debuglog', 'botocore.service')
        get_logger.assert_called_with('botocore.service')
        file_handler.assert_called_with('debuglog')

    @mock.patch('logging.getLogger')
    @mock.patch('logging.StreamHandler')
    @mock.patch('logging.Formatter')
    def test_general_purpose_logger(self, formatter, file_handler, get_logger):
        self.session.set_stream_logger('foo.bar', 'ERROR', format_string='foo')
        get_logger.assert_called_with('foo.bar')
        get_logger.return_value.setLevel.assert_called_with(logging.DEBUG)
        formatter.assert_called_with('foo')

    def test_register_with_unique_id(self):
        calls = []

        def handler(**kwargs):
            return calls.append(kwargs)

        self.session.register('foo', handler, unique_id='bar')
        self.session.emit('foo')
        self.assertEqual(calls[0]['event_name'], 'foo')
        calls = []
        self.session.unregister('foo', unique_id='bar')
        self.session.emit('foo')
        self.assertEqual(calls, [])


class TestBuiltinEventHandlers(BaseSessionTest):
    def setUp(self):
        super().setUp()
        self.builtin_handlers = [
            ('foo', self.on_foo),
        ]
        self.foo_called = False
        self.handler_patch = mock.patch(
            'botocore.handlers.BUILTIN_HANDLERS', self.builtin_handlers
        )
        self.handler_patch.start()

    def on_foo(self, **kwargs):
        self.foo_called = True

    def tearDown(self):
        super().tearDown()
        self.handler_patch.stop()

    def test_registered_builtin_handlers(self):
        session = create_session(include_builtin_handlers=True)
        session.emit('foo')
        self.assertTrue(self.foo_called)


class TestSessionConfigurationVars(BaseSessionTest):
    def test_per_session_config_vars(self):
        self.update_session_config_mapping(
            'foobar',
            instance_name='foobar',
            env_var_names='FOOBAR',
            default='default',
        )
        # Default value.
        self.assertEqual(self.session.get_config_variable('foobar'), 'default')
        # Retrieve from os environment variable.
        self.environ['FOOBAR'] = 'fromenv'
        self.assertEqual(self.session.get_config_variable('foobar'), 'fromenv')

        # Explicit override.
        self.session.set_config_variable('foobar', 'session-instance')
        self.assertEqual(
            self.session.get_config_variable('foobar'), 'session-instance'
        )

        # Back to default value.
        del self.environ['FOOBAR']
        self.session.set_config_variable('foobar', None)
        self.assertEqual(self.session.get_config_variable('foobar'), 'default')

    def test_default_value_can_be_overriden(self):
        self.update_session_config_mapping(
            'foobar',
            instance_name='foobar',
            env_var_names='FOOBAR',
            default='default',
        )
        self.assertEqual(self.session.get_config_variable('foobar'), 'default')

    def test_can_get_with_methods(self):
        self.environ['AWS_DEFAULT_REGION'] = 'env-var'
        self.session.set_config_variable('region', 'instance-var')
        value = self.session.get_config_variable('region')
        self.assertEqual(value, 'instance-var')

        value = self.session.get_config_variable('region', methods=('env',))
        self.assertEqual(value, 'env-var')


class TestSessionPartitionFiles(BaseSessionTest):
    def test_lists_partitions_on_disk(self):
        mock_resolver = mock.Mock()
        mock_resolver.get_available_partitions.return_value = ['foo']
        self.session._register_internal_component(
            'endpoint_resolver', mock_resolver
        )
        self.assertEqual(['foo'], self.session.get_available_partitions())

    def test_proxies_list_endpoints_to_resolver(self):
        resolver = mock.Mock()
        resolver.get_available_endpoints.return_value = ['a', 'b']
        self.session._register_internal_component(
            'endpoint_resolver', resolver
        )
        self.session.get_available_regions('foo', 'bar', True)

    def test_provides_empty_list_for_unknown_service_regions(self):
        regions = self.session.get_available_regions('__foo__')
        self.assertEqual([], regions)

    def test_provides_correct_partition_for_region(self):
        partition = self.session.get_partition_for_region('us-west-2')
        self.assertEqual(partition, 'aws')

    def test_provides_correct_partition_for_region_regex(self):
        partition = self.session.get_partition_for_region('af-south-99')
        self.assertEqual(partition, 'aws')

    def test_provides_correct_partition_for_region_non_default(self):
        partition = self.session.get_partition_for_region('cn-north-1')
        self.assertEqual(partition, 'aws-cn')

    def test_raises_exception_for_invalid_region(self):
        with self.assertRaises(botocore.exceptions.UnknownRegionError):
            self.session.get_partition_for_region('no-good-1')


class TestSessionUserAgent(BaseSessionTest):
    def test_can_change_user_agent_name(self):
        self.session.user_agent_name = 'something-else'
        self.assertTrue(self.session.user_agent().startswith('something-else'))

    def test_can_change_user_agent_version(self):
        self.session.user_agent_version = '24.0'
        self.assertTrue(self.session.user_agent().startswith('Botocore/24.0'))

    def test_can_append_to_user_agent(self):
        self.session.user_agent_extra = 'custom-thing/other'
        self.assertTrue(
            self.session.user_agent().endswith('custom-thing/other')
        )

    def test_execution_env_not_set(self):
        self.assertFalse(self.session.user_agent().endswith('FooEnv'))

    def test_execution_env_set(self):
        self.environ['AWS_EXECUTION_ENV'] = 'FooEnv'
        self.assertTrue(self.session.user_agent().endswith(' exec-env/FooEnv'))

    def test_agent_extra_and_exec_env(self):
        self.session.user_agent_extra = 'custom-thing/other'
        self.environ['AWS_EXECUTION_ENV'] = 'FooEnv'
        user_agent = self.session.user_agent()
        self.assertTrue(user_agent.endswith('custom-thing/other'))
        self.assertIn('exec-env/FooEnv', user_agent)

    @requires_crt()
    def test_crt_user_agent_appended(self):
        user_agent = self.session.user_agent()
        self.assertIn(' awscrt/', user_agent)
        self.assertNotIn('awscrt/Unknown', user_agent)

    @requires_crt()
    def test_crt_and_extra_user_agent(self):
        user_agent = self.session.user_agent()
        self.assertIn(' awscrt/', user_agent)
        self.assertNotIn('custom-thing/other', user_agent)
        self.session.user_agent_extra = 'custom-thing/other'
        user_agent_w_extra = self.session.user_agent()
        self.assertIn(' awscrt/', user_agent)
        self.assertTrue(user_agent_w_extra.endswith('custom-thing/other'))


class TestConfigLoaderObject(BaseSessionTest):
    def test_config_loader_delegation(self):
        session = create_session(profile='credfile-profile')
        with temporary_file('w') as f:
            f.write('[credfile-profile]\naws_access_key_id=a\n')
            f.write('aws_secret_access_key=b\n')
            f.flush()
            session.set_config_variable('credentials_file', f.name)
            # Now trying to retrieve the scoped config should pull in
            # values from the shared credentials file.
            self.assertEqual(
                session.get_scoped_config(),
                {'aws_access_key_id': 'a', 'aws_secret_access_key': 'b'},
            )


class TestGetServiceModel(BaseSessionTest):
    def test_get_service_model(self):
        loader = mock.Mock()
        loader.load_service_model.return_value = {
            'metadata': {'serviceId': 'foo'}
        }
        self.session.register_component('data_loader', loader)
        model = self.session.get_service_model('made_up')
        self.assertIsInstance(model, ServiceModel)
        self.assertEqual(model.service_name, 'made_up')


class TestGetPaginatorModel(BaseSessionTest):
    def test_get_paginator_model(self):
        loader = mock.Mock()
        loader.load_service_model.return_value = {"pagination": {}}
        self.session.register_component('data_loader', loader)

        model = self.session.get_paginator_model('foo')

        # Verify we get a PaginatorModel back
        self.assertIsInstance(model, PaginatorModel)
        # Verify we called the loader correctly.
        loader.load_service_model.assert_called_with(
            'foo', 'paginators-1', None
        )


class TestGetWaiterModel(BaseSessionTest):
    def test_get_waiter_model(self):
        loader = mock.Mock()
        loader.load_service_model.return_value = {"version": 2, "waiters": {}}
        self.session.register_component('data_loader', loader)

        model = self.session.get_waiter_model('foo')

        # Verify we (1) get the expected return data,
        self.assertIsInstance(model, WaiterModel)
        self.assertEqual(model.waiter_names, [])
        # and (2) call the loader correctly.
        loader.load_service_model.assert_called_with('foo', 'waiters-2', None)


class TestCreateClient(BaseSessionTest):
    def test_can_create_client(self):
        sts_client = self.session.create_client('sts', 'us-west-2')
        self.assertIsInstance(sts_client, client.BaseClient)

    def test_credential_provider_not_called_when_creds_provided(self):
        cred_provider = mock.Mock()
        self.session.register_component('credential_provider', cred_provider)
        self.session.create_client(
            'sts',
            'us-west-2',
            aws_access_key_id='foo',
            aws_secret_access_key='bar',
            aws_session_token='baz',
        )
        self.assertFalse(
            cred_provider.load_credentials.called,
            "Credential provider was called even though "
            "explicit credentials were provided to the "
            "create_client call.",
        )

    def test_cred_provider_called_when_partial_creds_provided(self):
        with self.assertRaises(botocore.exceptions.PartialCredentialsError):
            self.session.create_client(
                'sts',
                'us-west-2',
                aws_access_key_id='foo',
                aws_secret_access_key=None,
            )
        with self.assertRaises(botocore.exceptions.PartialCredentialsError):
            self.session.create_client(
                'sts',
                'us-west-2',
                aws_access_key_id=None,
                aws_secret_access_key='foo',
            )

    def test_cred_provider_not_called_on_unsigned_client(self):
        cred_provider = mock.Mock()
        self.session.register_component('credential_provider', cred_provider)
        config = botocore.config.Config(signature_version=UNSIGNED)
        self.session.create_client('sts', 'us-west-2', config=config)
        self.assertFalse(cred_provider.load_credentials.called)

    @mock.patch('botocore.client.ClientCreator')
    def test_config_passed_to_client_creator(self, client_creator):
        # Make sure there is no default set
        self.assertEqual(self.session.get_default_client_config(), None)

        # The config passed to the client should be the one that is used
        # in creating the client.
        config = botocore.config.Config(region_name='us-west-2')
        self.session.create_client('sts', config=config)
        client_creator.return_value.create_client.assert_called_with(
            service_name=mock.ANY,
            region_name=mock.ANY,
            is_secure=mock.ANY,
            endpoint_url=mock.ANY,
            verify=mock.ANY,
            credentials=mock.ANY,
            scoped_config=mock.ANY,
            client_config=config,
            api_version=mock.ANY,
            auth_token=mock.ANY,
        )

    @mock.patch('botocore.client.ClientCreator')
    def test_create_client_with_default_client_config(self, client_creator):
        config = botocore.config.Config()
        self.session.set_default_client_config(config)
        self.session.create_client('sts')

        client_creator.return_value.create_client.assert_called_with(
            service_name=mock.ANY,
            region_name=mock.ANY,
            is_secure=mock.ANY,
            endpoint_url=mock.ANY,
            verify=mock.ANY,
            credentials=mock.ANY,
            scoped_config=mock.ANY,
            client_config=config,
            api_version=mock.ANY,
            auth_token=mock.ANY,
        )

    @mock.patch('botocore.client.ClientCreator')
    def test_create_client_with_merging_client_configs(self, client_creator):
        config = botocore.config.Config(region_name='us-west-2')
        other_config = botocore.config.Config(region_name='us-east-1')
        self.session.set_default_client_config(config)
        self.session.create_client('sts', config=other_config)

        # Grab the client config used in creating the client
        used_client_config = (
            client_creator.return_value.create_client.call_args[1][
                'client_config'
            ]
        )
        # Check that the client configs were merged
        self.assertEqual(used_client_config.region_name, 'us-east-1')
        # Make sure that the client config used is not the default client
        # config or the one passed in. It should be a new config.
        self.assertIsNot(used_client_config, config)
        self.assertIsNot(used_client_config, other_config)

    def test_create_client_with_region(self):
        ec2_client = self.session.create_client('ec2', 'us-west-2')
        self.assertEqual(ec2_client.meta.region_name, 'us-west-2')

    def test_create_client_with_region_and_client_config(self):
        config = botocore.config.Config()
        # Use a client config with no region configured.
        ec2_client = self.session.create_client(
            'ec2', region_name='us-west-2', config=config
        )
        self.assertEqual(ec2_client.meta.region_name, 'us-west-2')

        # If the region name is changed, it should not change the
        # region of the client
        config.region_name = 'us-east-1'
        self.assertEqual(ec2_client.meta.region_name, 'us-west-2')

        # Now make a new client with the updated client config.
        ec2_client = self.session.create_client('ec2', config=config)
        self.assertEqual(ec2_client.meta.region_name, 'us-east-1')

    def test_create_client_no_region_and_no_client_config(self):
        ec2_client = self.session.create_client('ec2')
        self.assertEqual(ec2_client.meta.region_name, 'us-west-11')

    @mock.patch('botocore.client.ClientCreator')
    def test_create_client_with_ca_bundle_from_config(self, client_creator):
        with temporary_file('w') as f:
            del self.environ['FOO_PROFILE']
            self.environ['FOO_CONFIG_FILE'] = f.name
            f.write('[default]\n')
            f.write('foo_ca_bundle=config-certs.pem\n')
            f.flush()

            self.session.create_client('ec2', 'us-west-2')
            call_kwargs = client_creator.return_value.create_client.call_args[
                1
            ]
            self.assertEqual(call_kwargs['verify'], 'config-certs.pem')

    @mock.patch('botocore.client.ClientCreator')
    def test_create_client_with_ca_bundle_from_env_var(self, client_creator):
        self.environ['FOO_AWS_CA_BUNDLE'] = 'env-certs.pem'
        self.session.create_client('ec2', 'us-west-2')
        call_kwargs = client_creator.return_value.create_client.call_args[1]
        self.assertEqual(call_kwargs['verify'], 'env-certs.pem')

    @mock.patch('botocore.client.ClientCreator')
    def test_create_client_with_verify_param(self, client_creator):
        self.session.create_client(
            'ec2', 'us-west-2', verify='verify-certs.pem'
        )
        call_kwargs = client_creator.return_value.create_client.call_args[1]
        self.assertEqual(call_kwargs['verify'], 'verify-certs.pem')

    @mock.patch('botocore.client.ClientCreator')
    def test_create_client_verify_param_overrides_all(self, client_creator):
        with temporary_file('w') as f:
            # Set the ca cert using the config file
            del self.environ['FOO_PROFILE']
            self.environ['FOO_CONFIG_FILE'] = f.name
            f.write('[default]\n')
            f.write('foo_ca_bundle=config-certs.pem\n')
            f.flush()

            # Set the ca cert with an environment variable
            self.environ['FOO_AWS_CA_BUNDLE'] = 'env-certs.pem'

            # Set the ca cert using the verify parameter
            self.session.create_client(
                'ec2', 'us-west-2', verify='verify-certs.pem'
            )
            call_kwargs = client_creator.return_value.create_client.call_args[
                1
            ]
            # The verify parameter should override all the other
            # configurations
            self.assertEqual(call_kwargs['verify'], 'verify-certs.pem')

    @mock.patch('botocore.client.ClientCreator')
    def test_create_client_use_no_api_version_by_default(self, client_creator):
        self.session.create_client('myservice', 'us-west-2')
        call_kwargs = client_creator.return_value.create_client.call_args[1]
        self.assertEqual(call_kwargs['api_version'], None)

    @mock.patch('botocore.client.ClientCreator')
    def test_create_client_uses_api_version_from_config(self, client_creator):
        config_api_version = '2012-01-01'
        with temporary_file('w') as f:
            del self.environ['FOO_PROFILE']
            self.environ['FOO_CONFIG_FILE'] = f.name
            f.write('[default]\n')
            f.write(
                'foo_api_versions =\n'
                f'    myservice = {config_api_version}\n'
            )  # fmt: skip
            f.flush()

            self.session.create_client('myservice', 'us-west-2')
            call_kwargs = client_creator.return_value.create_client.call_args[
                1
            ]
            self.assertEqual(call_kwargs['api_version'], config_api_version)

    @mock.patch('botocore.client.ClientCreator')
    def test_can_specify_multiple_versions_from_config(self, client_creator):
        config_api_version = '2012-01-01'
        second_config_api_version = '2013-01-01'
        with temporary_file('w') as f:
            del self.environ['FOO_PROFILE']
            self.environ['FOO_CONFIG_FILE'] = f.name
            f.write('[default]\n')
            f.write(
                f'foo_api_versions =\n'
                f'    myservice = {config_api_version}\n'
                f'    myservice2 = {second_config_api_version}\n'
            )  # fmt: skip
            f.flush()

            self.session.create_client('myservice', 'us-west-2')
            call_kwargs = client_creator.return_value.create_client.call_args[
                1
            ]
            self.assertEqual(call_kwargs['api_version'], config_api_version)

            self.session.create_client('myservice2', 'us-west-2')
            call_kwargs = client_creator.return_value.create_client.call_args[
                1
            ]
            self.assertEqual(
                call_kwargs['api_version'], second_config_api_version
            )

    @mock.patch('botocore.client.ClientCreator')
    def test_param_api_version_overrides_config_value(self, client_creator):
        config_api_version = '2012-01-01'
        override_api_version = '2014-01-01'
        with temporary_file('w') as f:
            del self.environ['FOO_PROFILE']
            self.environ['FOO_CONFIG_FILE'] = f.name
            f.write('[default]\n')
            f.write(
                'foo_api_versions =\n'
                f'    myservice = {config_api_version}\n'
            )  # fmt: skip
            f.flush()

            self.session.create_client(
                'myservice', 'us-west-2', api_version=override_api_version
            )
            call_kwargs = client_creator.return_value.create_client.call_args[
                1
            ]
            self.assertEqual(call_kwargs['api_version'], override_api_version)

    @mock.patch('botocore.client.ClientCreator')
    def test_create_client_with_credentials(self, client_creator):
        self.session.create_client(
            'sts',
            'us-west-2',
            aws_access_key_id='foo',
            aws_secret_access_key='bar',
            aws_session_token='baz',
            aws_account_id='bin',
        )
        credentials = (
            client_creator.return_value.create_client.call_args.kwargs[
                'credentials'
            ]
        )
        self.assertEqual(credentials.access_key, 'foo')
        self.assertEqual(credentials.secret_key, 'bar')
        self.assertEqual(credentials.token, 'baz')
        self.assertEqual(credentials.account_id, 'bin')

    @mock.patch('botocore.client.ClientCreator')
    def test_create_client_with_ignored_credentials(self, client_creator):
        with self.assertLogs('botocore.session', level='DEBUG') as log:
            self.session.create_client(
                'sts',
                'us-west-2',
                aws_account_id='foo',
            )
            credentials = (
                client_creator.return_value.create_client.call_args.kwargs[
                    'credentials'
                ]
            )
            self.assertIn(
                'Ignoring the following credential-related values',
                log.output[0],
            )
            self.assertIn('aws_account_id', log.output[0])
            self.assertEqual(credentials.account_id, None)


class TestSessionComponent(BaseSessionTest):
    def test_internal_component(self):
        component = object()
        self.session._register_internal_component('internal', component)
        self.assertIs(
            self.session._get_internal_component('internal'), component
        )
        with self.assertRaises(ValueError):
            self.session.get_component('internal')

    def test_internal_endpoint_resolver_is_same_as_deprecated_public(self):
        endpoint_resolver = self.session._get_internal_component(
            'endpoint_resolver'
        )
        # get_component has been deprecated to the public
        with pytest.warns(DeprecationWarning):
            self.assertIs(
                self.session.get_component('endpoint_resolver'),
                endpoint_resolver,
            )

    def test_internal_exceptions_factory_is_same_as_deprecated_public(self):
        exceptions_factory = self.session._get_internal_component(
            'exceptions_factory'
        )
        # get_component has been deprecated to the public
        with pytest.warns(DeprecationWarning):
            self.assertIs(
                self.session.get_component('exceptions_factory'),
                exceptions_factory,
            )


class TestClientMonitoring(BaseSessionTest):
    def assert_created_client_is_monitored(self, session):
        with mock.patch(
            'botocore.monitoring.Monitor', spec=True
        ) as mock_monitor:
            client = session.create_client('ec2', 'us-west-2')
        mock_monitor.return_value.register.assert_called_with(
            client.meta.events
        )

    def assert_monitoring_host_and_port(self, session, host, port):
        with mock.patch(
            'botocore.monitoring.SocketPublisher', spec=True
        ) as mock_publisher:
            session.create_client('ec2', 'us-west-2')
        self.assertEqual(mock_publisher.call_count, 1)
        _, args, kwargs = mock_publisher.mock_calls[0]
        self.assertEqual(kwargs.get('host'), host)
        self.assertEqual(kwargs.get('port'), port)

    def assert_created_client_is_not_monitored(self, session):
        with mock.patch(
            'botocore.session.monitoring.Monitor', spec=True
        ) as mock_monitor:
            session.create_client('ec2', 'us-west-2')
            mock_monitor.return_value.register.assert_not_called()

    def test_with_csm_enabled_from_config(self):
        with temporary_file('w') as f:
            del self.environ['FOO_PROFILE']
            self.environ['FOO_CONFIG_FILE'] = f.name
            f.write('[default]\n')
            f.write('csm_enabled=true\n')
            f.flush()
            self.assert_created_client_is_monitored(self.session)

    def test_with_csm_enabled_from_env(self):
        self.environ['AWS_CSM_ENABLED'] = 'true'
        self.assert_created_client_is_monitored(self.session)

    def test_with_csm_host(self):
        custom_host = '10.13.37.1'
        self.environ['AWS_CSM_ENABLED'] = 'true'
        self.environ['AWS_CSM_HOST'] = custom_host
        self.assert_monitoring_host_and_port(self.session, custom_host, 31000)

    def test_with_csm_port(self):
        custom_port = '1234'
        self.environ['AWS_CSM_ENABLED'] = 'true'
        self.environ['AWS_CSM_PORT'] = custom_port
        self.assert_monitoring_host_and_port(
            self.session,
            '127.0.0.1',
            int(custom_port),
        )

    def test_with_csm_disabled_from_config(self):
        with temporary_file('w') as f:
            del self.environ['FOO_PROFILE']
            self.environ['FOO_CONFIG_FILE'] = f.name
            f.write('[default]\n')
            f.write('csm_enabled=false\n')
            f.flush()
            self.assert_created_client_is_not_monitored(self.session)

    def test_with_csm_disabled_from_env(self):
        self.environ['AWS_CSM_ENABLED'] = 'false'
        self.assert_created_client_is_not_monitored(self.session)

    def test_csm_not_configured(self):
        self.assert_created_client_is_not_monitored(self.session)


class TestComponentLocator(unittest.TestCase):
    def setUp(self):
        self.components = botocore.session.ComponentLocator()

    def test_unknown_component_raises_exception(self):
        with self.assertRaises(ValueError):
            self.components.get_component('unknown-component')

    def test_can_register_and_retrieve_component(self):
        component = object()
        self.components.register_component('foo', component)
        self.assertIs(self.components.get_component('foo'), component)

    def test_last_registration_wins(self):
        first = object()
        second = object()
        self.components.register_component('foo', first)
        self.components.register_component('foo', second)
        self.assertIs(self.components.get_component('foo'), second)

    def test_can_lazy_register_a_component(self):
        component = object()

        def lazy():
            return component

        self.components.lazy_register_component('foo', lazy)
        self.assertIs(self.components.get_component('foo'), component)

    def test_latest_registration_wins_even_if_lazy(self):
        first = object()
        second = object()

        def lazy_second():
            return second

        self.components.register_component('foo', first)
        self.components.lazy_register_component('foo', lazy_second)
        self.assertIs(self.components.get_component('foo'), second)

    def test_latest_registration_overrides_lazy(self):
        first = object()
        second = object()

        def lazy_first():
            return first

        self.components.lazy_register_component('foo', lazy_first)
        self.components.register_component('foo', second)
        self.assertIs(self.components.get_component('foo'), second)

    def test_lazy_registration_factory_does_not_remove_from_list_on_error(
        self,
    ):
        class ArbitraryError(Exception):
            pass

        def bad_factory():
            raise ArbitraryError("Factory raises an exception.")

        self.components.lazy_register_component('foo', bad_factory)

        with self.assertRaises(ArbitraryError):
            self.components.get_component('foo')

        # Trying again should raise the same exception,
        # not an ValueError("Unknown component")
        with self.assertRaises(ArbitraryError):
            self.components.get_component('foo')


class TestDefaultClientConfig(BaseSessionTest):
    def test_new_session_has_no_default_client_config(self):
        self.assertEqual(self.session.get_default_client_config(), None)

    def test_set_and_get_client_config(self):
        client_config = botocore.config.Config()
        self.session.set_default_client_config(client_config)
        self.assertIs(self.session.get_default_client_config(), client_config)


class TestSessionRegionSetup(BaseSessionTest):
    def test_new_session_with_valid_region(self):
        s3_client = self.session.create_client('s3', 'us-west-2')
        self.assertIsInstance(s3_client, client.BaseClient)
        self.assertEqual(s3_client.meta.region_name, 'us-west-2')

    def test_new_session_with_unknown_region(self):
        s3_client = self.session.create_client('s3', 'MyCustomRegion1')
        self.assertIsInstance(s3_client, client.BaseClient)
        self.assertEqual(s3_client.meta.region_name, 'MyCustomRegion1')

    def test_new_session_with_invalid_region(self):
        with self.assertRaises(botocore.exceptions.InvalidRegionError):
            self.session.create_client('s3', 'not.a.real#region')

    def test_new_session_with_none_region(self):
        s3_client = self.session.create_client('s3', region_name=None)
        self.assertIsInstance(s3_client, client.BaseClient)
        self.assertTrue(s3_client.meta.region_name is not None)


class TestInitializationHooks(BaseSessionTest):
    def test_can_register_init_hook(self):
        call_args = []

        def init_hook(session):
            call_args.append(session)

        register_initializer(init_hook)
        self.addCleanup(unregister_initializer, init_hook)
        session = create_session()
        self.assertEqual(call_args, [session])

    def test_can_unregister_hook(self):
        call_args = []

        def init_hook(session):
            call_args.append(session)

        register_initializer(init_hook)
        unregister_initializer(init_hook)
        create_session()
        self.assertEqual(call_args, [])

    def test_unregister_hook_raises_value_error(self):
        def not_registered(session):
            return None

        with self.assertRaises(ValueError):
            self.assertRaises(unregister_initializer(not_registered))
