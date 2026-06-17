# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from botocore.auth import (
    BaseSigner,
    resolve_auth_scheme_preference,
    resolve_auth_type,
)
from botocore.exceptions import (
    UnknownSignatureVersionError,
    UnsupportedSignatureVersionError,
)
from tests import mock, unittest


class TestAuthTraitResolution(unittest.TestCase):
    def test_auth_resolves_first_available(self):
        auth = ['aws.auth#foo', 'aws.auth#bar']
        # Don't declare a signer for "foo"
        auth_types = {'bar': mock.Mock(spec=BaseSigner)}
        auth_type_conversions = {'aws.auth#foo': 'foo', 'aws.auth#bar': 'bar'}

        with mock.patch('botocore.auth.AUTH_TYPE_MAPS', auth_types):
            with mock.patch(
                'botocore.auth.AUTH_TYPE_TO_SIGNATURE_VERSION',
                auth_type_conversions,
            ):
                assert resolve_auth_type(auth) == 'bar'

    def test_invalid_auth_type_error(self):
        with self.assertRaises(UnknownSignatureVersionError):
            resolve_auth_type(['aws.auth#invalidAuth'])

    def test_no_known_auth_type(self):
        with self.assertRaises(UnsupportedSignatureVersionError):
            resolve_auth_type([])


@pytest.mark.parametrize(
    "preference_list, auth_options, expected",
    [
        (['sigv4', 'httpBearerAuth'], ['smithy.api#httpBearerAuth'], 'bearer'),
        (['noAuth', 'sigv4'], ['aws.auth#sigv4'], 'v4'),
        (['foo', 'httpBearerAuth'], ['smithy.api#httpBearerAuth'], 'bearer'),
        (['noAuth', 'sigv4'], ['smithy.api#noAuth'], 'none'),
        (['foo'], ['aws.auth#sigv4', 'smithy.api#httpBearerAuth'], 'v4'),
    ],
)
def test_resolve_auth_scheme_preference(
    preference_list, auth_options, expected
):
    assert (
        resolve_auth_scheme_preference(preference_list, auth_options)
        == expected
    )


@pytest.mark.parametrize(
    "preference_list, auth_options",
    [(['foo'], ['aws.auth#invalidAuth']), (['foo'], [])],
)
def test_resolve_auth_scheme_preference_unsupported(
    preference_list, auth_options
):
    with pytest.raises(UnsupportedSignatureVersionError):
        resolve_auth_scheme_preference(preference_list, auth_options)
