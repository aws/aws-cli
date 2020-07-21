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
import mock

from botocore.hooks import HierarchicalEmitter
from botocore.exceptions import ProfileNotFound
from botocore.session import Session
from botocore.credentials import (
    AssumeRoleProvider,
    CredentialResolver,
    AssumeRoleWithWebIdentityProvider
)

from awscli.testutils import unittest
from awscli.customizations import assumerole


class TestAssumeRolePlugin(unittest.TestCase):
    def test_assume_role_provider_injected(self):
        mock_assume_role = mock.Mock(spec=AssumeRoleProvider)
        mock_web_identity = mock.Mock(spec=AssumeRoleWithWebIdentityProvider)
        providers = {
            'assume-role': mock_assume_role,
            'assume-role-with-web-identity': mock_web_identity,
        }
        mock_resolver = mock.Mock(spec=CredentialResolver)
        mock_resolver.get_provider = providers.get
        session = mock.Mock(spec=Session)
        session.get_component.return_value = mock_resolver

        assumerole.inject_assume_role_provider_cache(
            session, event_name='building-command-table.foo')
        session.get_component.assert_called_with('credential_provider')
        self.assertIsInstance(mock_assume_role.cache, assumerole.JSONFileCache)
        self.assertIsInstance(
            mock_web_identity.cache,
            assumerole.JSONFileCache,
        )

    def test_assume_role_provider_registration(self):
        event_handlers = HierarchicalEmitter()
        assumerole.register_assume_role_provider(event_handlers)
        session = mock.Mock(spec=Session)
        event_handlers.emit('session-initialized', session=session)
        # Just verifying that anything on the session was called ensures
        # that our handler was called, as it's the only thing that should
        # be registered.
        session.get_component.assert_called_with('credential_provider')

    def test_no_registration_if_profile_does_not_exist(self):
        session = mock.Mock(spec=Session)
        session.get_component.side_effect = ProfileNotFound(
            profile='unknown')

        assumerole.inject_assume_role_provider_cache(
            session, event_name='building-command-table.foo')

        credential_provider = session.get_component.return_value
        self.assertFalse(credential_provider.get_provider.called)
