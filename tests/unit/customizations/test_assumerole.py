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
import platform
from datetime import datetime, timedelta

import mock
from botocore.hooks import HierarchicalEmitter
from botocore.exceptions import PartialCredentialsError
from botocore.exceptions import ProfileNotFound
from dateutil.tz import tzlocal

from awscli.testutils import unittest, skip_if_windows
from awscli.customizations import assumerole


class TestAssumeRolePlugin(unittest.TestCase):
    def test_assume_role_provider_injected(self):
        session = mock.Mock()
        assumerole.inject_assume_role_provider_cache(
            session, event_name='building-command-table.foo')
        session.get_component.assert_called_with('credential_provider')
        credential_provider = session.get_component.return_value
        get_provider = credential_provider.get_provider
        get_provider.assert_called_with('assume-role')
        self.assertIsInstance(get_provider.return_value.cache,
                              assumerole.JSONFileCache)

    def test_assume_role_provider_registration(self):
        event_handlers = HierarchicalEmitter()
        assumerole.register_assume_role_provider(event_handlers)
        session = mock.Mock()
        event_handlers.emit('session-initialized', session=session)
        # Just verifying that anything on the session was called ensures
        # that our handler was called, as it's the only thing that should
        # be registered.
        session.get_component.assert_called_with('credential_provider')

    def test_no_registration_if_profile_does_not_exist(self):
        session = mock.Mock()
        session.get_component.side_effect = ProfileNotFound(
            profile='unknown')

        assumerole.inject_assume_role_provider_cache(
            session, event_name='building-command-table.foo')

        credential_provider = session.get_component.return_value
        self.assertFalse(credential_provider.get_provider.called)


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

    def test_file_is_truncated_before_writing(self):
        self.cache['mykey'] = {
            'really long key in the cache': 'really long value in cache'}
        # Now overwrite it with a smaller value.
        self.cache['mykey'] = {'a': 'b'}
        self.assertEqual(self.cache['mykey'], {'a': 'b'})

    @skip_if_windows('File permissions tests not supported on Windows.')
    def test_permissions_for_file_restricted(self):
        self.cache['mykey'] = {'foo': 'bar'}
        filename = os.path.join(self.tempdir, 'mykey.json')
        self.assertEqual(os.stat(filename).st_mode & 0xFFF, 0o600)
