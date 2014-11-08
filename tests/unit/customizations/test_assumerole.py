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
import shutil
import tempfile
import os
from datetime import datetime, timedelta

import mock
from botocore.hooks import HierarchicalEmitter
from botocore.exceptions import PartialCredentialsError
from dateutil.tz import tzlocal

from awscli.testutils import unittest
from awscli.customizations import assumerole


class TestAssumeRolePlugin(unittest.TestCase):
    def test_assume_role_provider_injected(self):
        session = mock.Mock()
        assumerole.inject_assume_role_provider(
            session, event_name='building-command-table.foo')

        session.get_component.assert_called_with('credential_provider')
        credential_provider = session.get_component.return_value
        call_args = credential_provider.insert_before.call_args[0]
        self.assertEqual(call_args[0], 'config-file')
        self.assertIsInstance(call_args[1], assumerole.AssumeRoleProvider)

    def test_assume_role_provider_not_injected_for_main_command_table(self):
        session = mock.Mock()
        # When the main/top-level command table is created, it's emitted with
        # an event name of building-command-table.main.  We want to verify
        # that the assumerole provider is not hooked up when that happens.
        assumerole.inject_assume_role_provider(
            session, event_name='building-command-table.main')
        self.assertFalse(session.get_component.called)

    def test_assume_role_provider_registration(self):
        event_handlers = HierarchicalEmitter()
        assumerole.register_assume_role_provider(event_handlers)
        session = mock.Mock()
        event_handlers.emit('building-command-table.foo', session=session)
        # Just verifying that anything on the session was called ensures
        # that our handler was called, as it's the only thing that should
        # be registered.
        session.get_component.assert_called_with('credential_provider')

    def test_provider_not_registered_on_error(self):
        session = mock.Mock()
        session.get_component.side_effect = Exception(
            "Couldn't get credential_provider.")
        assumerole.inject_assume_role_provider(
            session, event_name='building-command-table.foo')
        self.assertFalse(
            session.get_component.return_value.insert_before.called)


class TestAssumeRoleCredentialProvider(unittest.TestCase):

    maxDiff = None

    def setUp(self):
        self.fake_config = {
            'profiles': {
                'development': {
                    'role_arn': 'myrole',
                    'source_profile': 'longterm',
                },
                'longterm': {
                    'aws_access_key_id': 'akid',
                    'aws_secret_access_key': 'skid',
                }
            }
        }

    def create_config_loader(self, with_config=None):
        if with_config is None:
            with_config = self.fake_config
        load_config = mock.Mock()
        load_config.return_value = with_config
        return load_config

    def create_client_creator(self, with_response):
        # Create a mock sts client that returns a specific response
        # for assume_role.
        client = mock.Mock()
        client.assume_role.return_value = with_response
        return mock.Mock(return_value=client)

    def test_assume_role_with_no_cache(self):
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': datetime.now(tzlocal()).isoformat()
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        provider = assumerole.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator, cache={}, profile_name='development')

        credentials = provider.load()

        self.assertEqual(credentials.access_key, 'foo')
        self.assertEqual(credentials.secret_key, 'bar')
        self.assertEqual(credentials.token, 'baz')

    def test_assume_role_retrieves_from_cache(self):
        date_in_future = datetime.utcnow() + timedelta(seconds=1000)
        utc_timestamp = date_in_future.isoformat() + 'Z'
        self.fake_config['profiles']['development']['role_arn'] = 'myrole'
        cache = {
            'development--myrole': {
                'Credentials': {
                    'AccessKeyId': 'foo-cached',
                    'SecretAccessKey': 'bar-cached',
                    'SessionToken': 'baz-cached',
                    'Expiration': utc_timestamp,
                }
            }
        }
        provider = assumerole.AssumeRoleProvider(
            self.create_config_loader(), mock.Mock(),
            cache=cache, profile_name='development')

        credentials = provider.load()

        self.assertEqual(credentials.access_key, 'foo-cached')
        self.assertEqual(credentials.secret_key, 'bar-cached')
        self.assertEqual(credentials.token, 'baz-cached')

    def test_assume_role_in_cache_but_expired(self):
        expired_creds = datetime.utcnow()
        utc_timestamp = expired_creds.isoformat() + 'Z'
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': utc_timestamp,
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        cache = {
            'development--myrole': {
                'Credentials': {
                    'AccessKeyId': 'foo-cached',
                    'SecretAccessKey': 'bar-cached',
                    'SessionToken': 'baz-cached',
                    'Expiration': utc_timestamp,
                }
            }
        }
        provider = assumerole.AssumeRoleProvider(
            self.create_config_loader(), client_creator,
            cache=cache, profile_name='development')

        credentials = provider.load()

        self.assertEqual(credentials.access_key, 'foo')
        self.assertEqual(credentials.secret_key, 'bar')
        self.assertEqual(credentials.token, 'baz')

    def test_external_id_provided(self):
        self.fake_config['profiles']['development']['external_id'] = 'myid'
        response = {
            'Credentials': {
                'AccessKeyId': 'foo',
                'SecretAccessKey': 'bar',
                'SessionToken': 'baz',
                'Expiration': datetime.now(tzlocal()).isoformat(),
            },
        }
        client_creator = self.create_client_creator(with_response=response)
        provider = assumerole.AssumeRoleProvider(
            self.create_config_loader(),
            client_creator, cache={}, profile_name='development')

        provider.load()

        client = client_creator.return_value
        client.assume_role.assert_called_with(
            RoleArn='myrole', ExternalId='myid', RoleSessionName=mock.ANY)

    def test_no_config_is_noop(self):
        self.fake_config['profiles']['development'] = {
            'aws_access_key_id': 'foo',
            'aws_secret_access_key': 'bar',
        }
        provider = assumerole.AssumeRoleProvider(
            self.create_config_loader(),
            mock.Mock(), cache={}, profile_name='development')

        # Because a role_arn was not specified, the AssumeRoleProvider
        # is a noop and will not return credentials (which means we
        # move on to the next provider).
        credentials = provider.load()
        self.assertIsNone(credentials)

    def test_source_profile_not_provided(self):
        del self.fake_config['profiles']['development']['source_profile']
        provider = assumerole.AssumeRoleProvider(
            self.create_config_loader(),
            mock.Mock(), cache={}, profile_name='development')

        # source_profile is required, we shoudl get an error.
        with self.assertRaises(PartialCredentialsError):
            provider.load()

    def test_source_profile_does_not_exist(self):
        dev_profile = self.fake_config['profiles']['development']
        dev_profile['source_profile'] = 'does-not-exist'
        provider = assumerole.AssumeRoleProvider(
            self.create_config_loader(),
            mock.Mock(), cache={}, profile_name='development')

        # source_profile is required, we shoudl get an error.
        with self.assertRaises(assumerole.InvalidConfigError):
            provider.load()


class TestJSONCache(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.cache = assumerole.JSONFileCache(self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_supports_contains_check(self):
        # By default the cache is empty because we're
        # using a new temp dir everytime.
        self.assertTrue('mykey' not in self.cache)

    def test_add_key_and_contains_check(self):
        self.cache['mykey'] = {'foo': 'bar'}
        self.assertTrue('mykey' in self.cache)

    def test_added_key_can_be_retrieved(self):
        self.cache['mykey'] = {'foo': 'bar'}
        self.assertEqual(self.cache['mykey'], {'foo': 'bar'})

    def test_only_accepts_json_serializable_data(self):
        with self.assertRaises(ValueError):
            # set()'s cannot be serialized to a JSOn string.
            self.cache['mykey'] = set()

    def test_can_override_existing_values(self):
        self.cache['mykey'] = {'foo': 'bar'}
        self.cache['mykey'] = {'baz': 'newvalue'}
        self.assertEqual(self.cache['mykey'], {'baz': 'newvalue'})

    def test_can_add_multiple_keys(self):
        self.cache['mykey'] = {'foo': 'bar'}
        self.cache['mykey2'] = {'baz': 'qux'}
        self.assertEqual(self.cache['mykey'], {'foo': 'bar'})
        self.assertEqual(self.cache['mykey2'], {'baz': 'qux'})

    def test_working_dir_does_not_exist(self):
        working_dir = os.path.join(self.tempdir, 'foo')
        cache = assumerole.JSONFileCache(working_dir)
        cache['foo'] = {'bar': 'baz'}
        self.assertEqual(cache['foo'], {'bar': 'baz'})

    def test_key_error_raised_when_cache_key_does_not_exist(self):
        with self.assertRaises(KeyError):
            self.cache['foo']
