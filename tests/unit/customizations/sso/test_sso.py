# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import botocore.credentials
import botocore.session
from botocore.exceptions import ProfileNotFound, UnknownCredentialError

from awscli.testutils import mock
from awscli.testutils import unittest
from awscli.customizations.sso import inject_json_file_cache


class TestInjectJSONFileCache(unittest.TestCase):
    def setUp(self):
        self.mock_sso_provider = mock.Mock(
            spec=botocore.credentials.SSOProvider)
        self.mock_resolver = mock.Mock(botocore.credentials.CredentialResolver)
        self.mock_resolver.get_provider.return_value = self.mock_sso_provider
        self.session = mock.Mock(spec=botocore.session.Session)
        self.session.get_component.return_value = self.mock_resolver

    def test_inject_json_file_cache(self):
        inject_json_file_cache(
            self.session, event_name='session-initialized'
        )
        self.session.get_component.assert_called_with('credential_provider')
        self.assertIsInstance(
            self.mock_sso_provider.cache,
            botocore.credentials.JSONFileCache,
        )

    def test_profile_not_found_is_not_propagated(self):
        self.session.get_component.side_effect = ProfileNotFound(
            profile='unknown')
        try:
            inject_json_file_cache(
                self.session, event_name='session-initialized'
            )
        except ProfileNotFound:
            self.fail('ProfileNotFound should not have been raised.')

    def test_provider_not_found_error_is_not_propagated(self):
        self.mock_resolver.get_provider.side_effect = UnknownCredentialError(
            name='sso'
        )
        try:
            inject_json_file_cache(
                self.session, event_name='session-initialized'
            )
        except UnknownCredentialError:
            self.fail('UnknownCredentialError should not have been raised.')
