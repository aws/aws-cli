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

from awscli.testutils import unittest
from awscli.customizations import sessiontokenservice


import sys


class TestAssumeRolePlugin(unittest.TestCase):
    def test_assume_role_provider_injected(self):
        session = mock.Mock()

        credential_provider = mock.Mock()
        session.get_component.return_value = credential_provider
        providers = [mock.Mock(), mock.Mock()]

        credential_provider.get_provider.side_effect = providers

        sessiontokenservice.inject_session_token_provider_cache(
            session, event_name='building-command-table.foo')

        session.get_component.assert_called_with('credential_provider')

        credential_provider.get_provider.assert_any_call('assume-role')
        credential_provider.get_provider.assert_any_call('shared-credentials-file')

        for provider in providers:
            self.assertIsInstance(provider.cache, sessiontokenservice.JSONFileCache)

    def test_assume_role_provider_registration(self):
        event_handlers = HierarchicalEmitter()
        sessiontokenservice.register_session_token_provider(event_handlers)
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

        sessiontokenservice.inject_session_token_provider_cache(
            session, event_name='building-command-table.foo')

        credential_provider = session.get_component.return_value
        self.assertFalse(credential_provider.get_provider.called)
