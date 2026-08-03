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
from botocore import client
from botocore.hooks import HierarchicalEmitter
from botocore.model import ServiceModel
from botocore.paginate import PaginatorModel
from botocore.waiter import WaiterModel
from tests import create_session, mock, temporary_file, unittest


# This is an old version of the session tests to ensure backwards compatibility
# there is a new unit/test_session.py set of tests for the new config interface
# which should be prefered. When backwards compatibility can be dropped then
# this test should be removed.
class BaseSessionTest(unittest.TestCase):
    def setUp(self):
        self.env_vars = {
            'profile': (None, 'FOO_PROFILE', None, None),
            'region': ('foo_region', 'FOO_REGION', None, None),
            'data_path': ('data_path', 'FOO_DATA_PATH', None, None),
            'config_file': (None, 'FOO_CONFIG_FILE', None, None),
            'credentials_file': (None, None, '/tmp/nowhere', None),
            'ca_bundle': ('foo_ca_bundle', 'FOO_AWS_CA_BUNDLE', None, None),
            'api_versions': ('foo_api_versions', None, {}, None),
        }
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
        self.session = create_session(session_vars=self.env_vars)

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
        env_vars = {
            'profile': (
                None,
                ['BAR_DEFAULT_PROFILE', 'BAR_PROFILE'],
                None,
                None,
            ),
        }
        session = create_session(session_vars=env_vars)
        self.environ['BAR_DEFAULT_PROFILE'] = 'first'
        self.environ['BAR_PROFILE'] = 'second'
        self.assertEqual(session.get_config_variable('profile'), 'first')

    def test_profile_when_set_explicitly(self):
        session = create_session(session_vars=self.env_vars, profile='asdf')
        self.assertEqual(session.profile, 'asdf')

    def test_profile_when_pulled_from_env(self):
        self.environ['FOO_PROFILE'] = 'bar'
        # Even though we didn't explicitly pass in a profile, the
        # profile property will still look this up for us.
        self.assertEqual(self.session.profile, 'bar')

    def test_multiple_env_vars_uses_second_var(self):
        env_vars = {
            'profile': (
                None,
                ['BAR_DEFAULT_PROFILE', 'BAR_PROFILE'],
                None,
                None,
            ),
        }
        session = create_session(session_vars=env_vars)
        self.environ.pop('BAR_DEFAULT_PROFILE', None)
        self.environ['BAR_PROFILE'] = 'second'
        self.assertEqual(session.get_config_variable('profile'), 'second')

    def test_profile(self):
        self.assertEqual(self.session.get_config_variable('profile'), 'foo')
        self.assertEqual(
            self.session.get_config_variable('region'), 'us-west-11'
        )
        self.session.get_config_variable('profile') == 'default'
        saved_region = self.environ['FOO_REGION']
        del self.environ['FOO_REGION']
        saved_profile = self.environ['FOO_PROFILE']
        del self.environ['FOO_PROFILE']
        session = create_session(session_vars=self.env_vars)
        self.assertEqual(session.get_config_variable('profile'), None)
        self.assertEqual(session.get_config_variable('region'), 'us-west-1')
        self.environ['FOO_REGION'] = saved_region
        self.environ['FOO_PROFILE'] = saved_profile

    def test_profile_does_not_exist_raises_exception(self):
        # Given we have no profile:
        self.environ['FOO_PROFILE'] = 'profile_that_does_not_exist'
        session = create_session(session_vars=self.env_vars)
        with self.assertRaises(botocore.exceptions.ProfileNotFound):
            session.get_scoped_config()

    def test_variable_does_not_exist(self):
        session = create_session(session_vars=self.env_vars)
        self.assertIsNone(session.get_config_variable('foo/bar'))

    def test_get_aws_services_in_alphabetical_order(self):
        session = create_session(session_vars=self.env_vars)
        services = session.get_available_services()
        self.assertEqual(sorted(services), services)

    def test_profile_does_not_exist_with_default_profile(self):
        session = create_session(session_vars=self.env_vars)
        config = session.get_scoped_config()
        # We should have loaded this properly, and we'll check
        # that foo_access_key which is defined in the config
        # file should be present in the loaded config dict.
        self.assertIn('aws_access_key_id', config)

    def test_type_conversions_occur_when_specified(self):
        # Specify that we can retrieve the var from the
        # FOO_TIMEOUT env var, with a conversion function
        # of int().
        self.env_vars['metadata_service_timeout'] = (
            None,
            'FOO_TIMEOUT',
            None,
            int,
        )
        # Environment variables are always strings.
        self.environ['FOO_TIMEOUT'] = '10'
        session = create_session(session_vars=self.env_vars)
        # But we should type convert this to a string.
        self.assertEqual(
            session.get_config_variable('metadata_service_timeout'), 10
        )

    def test_default_profile_specified_raises_exception(self):
        # If you explicity set the default profile and you don't
        # have that in your config file, an exception is raised.
        config_path = os.path.join(
            os.path.dirname(__file__), 'cfg', 'boto_config_empty'
        )
        self.environ['FOO_CONFIG_FILE'] = config_path
        self.environ['FOO_PROFILE'] = 'default'
        session = create_session(session_vars=self.env_vars)
        # In this case, even though we specified default, because
        # the boto_config_empty config file does not have a default
        # profile, we should be raising an exception.
        with self.assertRaises(botocore.exceptions.ProfileNotFound):
            session.get_scoped_config()

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
        session = create_session(
            session_vars=self.env_vars, event_hooks=events
        )
        calls = []

        def handler(**kwargs):
            return calls.append(kwargs)

        events.register('foo', handler)

        session.emit('foo')
        self.assertEqual(len(calls), 1)

    def test_emit_first_non_none(self):
        session = create_session(session_vars=self.env_vars)
        session.register('foo', lambda **kwargs: None)
        session.register('foo', lambda **kwargs: 'first')
        session.register('foo', lambda **kwargs: 'second')
        response = session.emit_first_non_none_response('foo')
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
        session = botocore.session.Session(
            self.env_vars, None, include_builtin_handlers=True
        )
        session.emit('foo')
        self.assertTrue(self.foo_called)


class TestSessionConfigurationVars(BaseSessionTest):
    def test_per_session_config_vars(self):
        self.session.session_var_map['foobar'] = (
            None,
            'FOOBAR',
            'default',
            None,
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

        # Can disable this check via the ``methods`` arg.
        del self.environ['FOOBAR']
        self.assertEqual(
            self.session.get_config_variable(
                'foobar', methods=('env', 'config')
            ),
            'default',
        )

    def test_default_value_can_be_overriden(self):
        self.session.session_var_map['foobar'] = (
            None,
            'FOOBAR',
            'default',
            None,
        )
        self.assertEqual(self.session.get_config_variable('foobar'), 'default')

    def test_can_get_session_vars_info_from_default_session(self):
        # This test is to ensure that you can still reach the session_vars_map
        # information from the session and that it has the expected value.
        self.session = create_session()
        self.assertEqual(
            self.session.session_var_map['region'],
            ('region', 'AWS_DEFAULT_REGION', None, None),
        )
        self.assertEqual(
            self.session.session_var_map['profile'],
            (None, ['AWS_DEFAULT_PROFILE', 'AWS_PROFILE'], None, None),
        )
        self.assertEqual(
            self.session.session_var_map['data_path'],
            ('data_path', 'AWS_DATA_PATH', None, None),
        )
        self.assertEqual(
            self.session.session_var_map['config_file'],
            (None, 'AWS_CONFIG_FILE', '~/.aws/config', None),
        )
        self.assertEqual(
            self.session.session_var_map['ca_bundle'],
            ('ca_bundle', 'AWS_CA_BUNDLE', None, None),
        )
        self.assertEqual(
            self.session.session_var_map['api_versions'],
            ('api_versions', None, {}, None),
        )
        self.assertEqual(
            self.session.session_var_map['credentials_file'],
            (None, 'AWS_SHARED_CREDENTIALS_FILE', '~/.aws/credentials', None),
        )
        self.assertEqual(
            self.session.session_var_map['metadata_service_timeout'],
            (
                'metadata_service_timeout',
                'AWS_METADATA_SERVICE_TIMEOUT',
                1,
                int,
            ),
        )
        self.assertEqual(
            self.session.session_var_map['metadata_service_num_attempts'],
            (
                'metadata_service_num_attempts',
                'AWS_METADATA_SERVICE_NUM_ATTEMPTS',
                1,
                int,
            ),
        )
        self.assertEqual(
            self.session.session_var_map['parameter_validation'],
            ('parameter_validation', None, True, None),
        )


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


class TestConfigLoaderObject(BaseSessionTest):
    def test_config_loader_delegation(self):
        session = create_session(
            session_vars=self.env_vars, profile='credfile-profile'
        )
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
            self.session = create_session(session_vars=self.env_vars)
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
            self.session = create_session(session_vars=self.env_vars)
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
            self.session = create_session(session_vars=self.env_vars)
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
            self.session = create_session(session_vars=self.env_vars)
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
            self.session = create_session(session_vars=self.env_vars)
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
