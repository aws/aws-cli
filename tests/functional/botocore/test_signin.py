# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import pytest

from botocore import xform_name
from botocore.session import get_session
from botocore.stub import Stubber

_OAUTH2_OPERATIONS = [
    'CreateOAuth2Token',
    'CreateOAuth2TokenWithIAM',
    'IntrospectOAuth2TokenWithIAM',
    'RevokeOAuth2TokenWithIAM',
]

_METHOD_RENAMES = [
    ('create_o_auth2_token_with_iam', 'create_oauth2_token_with_iam'),
    ('introspect_o_auth2_token_with_iam', 'introspect_oauth2_token_with_iam'),
    ('revoke_o_auth2_token_with_iam', 'revoke_oauth2_token_with_iam'),
]


@pytest.mark.validates_models
@pytest.mark.parametrize("operation", _OAUTH2_OPERATIONS)
def test_oauth2_xform_name(operation):
    assert 'oauth2' in xform_name(operation, '_')
    assert 'oauth2' in xform_name(operation, '-')


class TestSigninOAuth2:
    def setup_method(self):
        session = get_session()
        self.client = session.create_client('signin', 'us-east-1')
        self.stubber = Stubber(self.client)
        self.stubber.activate()

    def test_create_oauth2_token_aliased(self):
        # create_o_auth2_token was released without a rename, so we keep a
        # hidden alias for backwards compatibility.
        assert (
            self.client.create_o_auth2_token.__func__
            is self.client.create_oauth2_token.__func__
        )

    @pytest.mark.parametrize("modeled, renamed", _METHOD_RENAMES)
    def test_with_iam_methods_are_renamed(self, modeled, renamed):
        assert hasattr(self.client, renamed)
        assert not hasattr(self.client, modeled)
