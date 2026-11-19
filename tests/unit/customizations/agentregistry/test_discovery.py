# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Discovery and token documents are checked for shape before they are used.

They come from the network, so a document of the wrong shape must fail with
a clear error rather than an AttributeError or TypeError.
"""

import http.client
import logging
import socket
import ssl
import urllib.error
from unittest.mock import patch

import pytest

from awscli.customizations.agentregistry import providers, utils
from awscli.customizations.agentregistry.providers import (
    CognitoProvider,
    GenericOidcProvider,
)
from awscli.customizations.agentregistry.utils import AgentRegistryJWTError
from tests.unit.customizations.agentregistry.utils import make_jwt

ENDPOINT = 'https://registry.example'
REGISTRY_ID = 'abcDEF123456'
ISSUER = 'https://idp.example.com'
COGNITO_ISSUER = 'https://cognito-idp.us-west-2.amazonaws.com/us-west-2_AbC123'


def _discover(document):
    with patch.object(utils, 'http_get_json', return_value=document):
        return utils.discover_registry(ENDPOINT, REGISTRY_ID).issuer


def _oidc(document):
    with patch.object(utils, 'http_get_json', return_value=document):
        return utils.fetch_oidc_metadata(ISSUER)


# --- Protected Resource Metadata --------------------------------------------


def test_issuer_is_read_from_resource_metadata():
    assert _discover({'authorization_servers': [ISSUER]}) == ISSUER


def test_resource_metadata_path_names_the_registry():
    document = {'authorization_servers': [ISSUER]}
    with patch.object(utils, 'http_get_json', return_value=document) as get:
        utils.discover_registry(ENDPOINT, REGISTRY_ID)
    assert get.call_args.args[0] == (
        f'{ENDPOINT}/.well-known/oauth-protected-resource/registry/'
        f'{REGISTRY_ID}/mcp'
    )


def test_registry_id_cannot_leave_its_path_segment():
    # Callers pass a validated id; the path is quoted all the same.
    document = {'authorization_servers': [ISSUER]}
    with patch.object(utils, 'http_get_json', return_value=document) as get:
        utils.discover_registry(ENDPOINT, '../x/?y#z')
    assert get.call_args.args[0] == (
        f'{ENDPOINT}/.well-known/oauth-protected-resource/registry/'
        f'..%2Fx%2F%3Fy%23z/mcp'
    )


@pytest.mark.parametrize('document', [[], ['x'], 'x', 1, None, True])
def test_resource_metadata_that_is_not_an_object_is_refused(document):
    with pytest.raises(AgentRegistryJWTError, match='not a JSON object'):
        _discover(document)


@pytest.mark.parametrize('servers', [ISSUER, {'url': ISSUER}, 1, True])
def test_authorization_servers_that_is_not_a_list_is_refused(servers):
    with pytest.raises(AgentRegistryJWTError, match='JSON array'):
        _discover({'authorization_servers': servers})


@pytest.mark.parametrize('server', [1, None, {'url': ISSUER}, [ISSUER]])
def test_authorization_server_that_is_not_a_string_is_refused(server):
    with pytest.raises(AgentRegistryJWTError, match='not a URL string'):
        _discover({'authorization_servers': [server, ISSUER]})


@pytest.mark.parametrize(
    'document', [{}, {'authorization_servers': []}, {'other': 1}]
)
def test_no_authorization_server_is_explained(document):
    with pytest.raises(AgentRegistryJWTError, match='no authorization'):
        _discover(document)


# --- OIDC discovery ---------------------------------------------------------


def test_oidc_metadata_is_returned():
    document = {
        'issuer': ISSUER,
        'authorization_endpoint': f'{ISSUER}/authorize',
        'token_endpoint': f'{ISSUER}/token',
        'scopes_supported': ['openid'],
    }
    assert _oidc(document) == document


def _http_error(code, msg):
    url = f'{ISSUER}/.well-known/openid-configuration'
    return urllib.error.HTTPError(url, code, msg, {}, None)


def _certificate_error():
    return urllib.error.URLError(
        ssl.SSLCertVerificationError(
            1,
            '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: '
            'unable to get local issuer certificate',
        )
    )


def test_missing_oidc_metadata_is_empty():
    error = _http_error(404, 'Not Found')
    with patch.object(utils, 'http_get_json', side_effect=error):
        assert utils.fetch_oidc_metadata(ISSUER) == {}


@pytest.mark.parametrize('code', [400, 403, 500, 503])
def test_oidc_metadata_http_error_is_reported(code):
    error = _http_error(code, 'Bad \x1b[31mthing')
    with patch.object(utils, 'http_get_json', side_effect=error):
        with pytest.raises(AgentRegistryJWTError) as e:
            utils.fetch_oidc_metadata(ISSUER)
    message = str(e.value)
    assert ISSUER in message
    assert f'HTTP Error {code}' in message
    assert '\x1b' not in message


def test_unreachable_oidc_metadata_is_reported():
    error = urllib.error.URLError('connection refused')
    with patch.object(utils, 'http_get_json', side_effect=error):
        with pytest.raises(AgentRegistryJWTError) as e:
            utils.fetch_oidc_metadata(ISSUER)
    message = str(e.value)
    assert ISSUER in message
    assert 'connection refused' in message
    assert '--ca-bundle' not in message


def test_untrusted_oidc_certificate_points_at_ca_bundle():
    with patch.object(
        utils, 'http_get_json', side_effect=_certificate_error()
    ):
        with pytest.raises(AgentRegistryJWTError) as e:
            utils.fetch_oidc_metadata(ISSUER)
    message = str(e.value)
    assert ISSUER in message
    assert 'CERTIFICATE_VERIFY_FAILED' in message
    assert '--ca-bundle' in message


def test_oidc_metadata_that_is_not_json_is_reported():
    with patch.object(
        utils, 'http_get_json', side_effect=ValueError('Expecting value')
    ):
        with pytest.raises(AgentRegistryJWTError, match='Expecting value'):
            utils.fetch_oidc_metadata(ISSUER)


def test_untrusted_cognito_certificate_is_not_mistaken_for_a_missing_domain():
    with (
        patch.object(utils, 'http_get_json', side_effect=_certificate_error()),
        patch.object(providers, 'run_browser_login') as login,
    ):
        with pytest.raises(AgentRegistryJWTError) as e:
            CognitoProvider(COGNITO_ISSUER).authenticate(
                session=None,
                endpoint=ENDPOINT,
                registry_id=REGISTRY_ID,
                client_id='client',
            )
    assert '--ca-bundle' in str(e.value)
    assert 'configure-jwt-signin' not in str(e.value)
    login.assert_not_called()


def test_generic_provider_without_discovery_document_explains_it():
    with (
        patch.object(
            utils, 'http_get_json', side_effect=_http_error(404, 'Not Found')
        ),
        patch.object(providers, 'run_browser_login') as login,
    ):
        with pytest.raises(AgentRegistryJWTError, match='does not advertise'):
            GenericOidcProvider(ISSUER).authenticate(
                endpoint=ENDPOINT, registry_id=REGISTRY_ID, client_id='client'
            )
    login.assert_not_called()


def test_generic_provider_reports_an_untrusted_certificate():
    with (
        patch.object(utils, 'http_get_json', side_effect=_certificate_error()),
        patch.object(providers, 'run_browser_login') as login,
    ):
        with pytest.raises(AgentRegistryJWTError, match='--ca-bundle'):
            GenericOidcProvider(ISSUER).authenticate(
                endpoint=ENDPOINT, registry_id=REGISTRY_ID, client_id='client'
            )
    login.assert_not_called()


@pytest.mark.parametrize('document', [[], ['x'], 'x', 1, None, True])
def test_oidc_metadata_that_is_not_an_object_is_refused(document):
    with pytest.raises(AgentRegistryJWTError, match='not a JSON object'):
        _oidc(document)


@pytest.mark.parametrize('key', ['authorization_endpoint', 'token_endpoint'])
@pytest.mark.parametrize('value', [1, True, [f'{ISSUER}/x'], {'url': 'x'}])
def test_oidc_endpoint_that_is_not_a_string_is_refused(key, value):
    document = {
        'authorization_endpoint': f'{ISSUER}/authorize',
        'token_endpoint': f'{ISSUER}/token',
    }
    document[key] = value
    with pytest.raises(AgentRegistryJWTError, match=f'{key} that is not'):
        _oidc(document)


def test_missing_oidc_endpoints_are_left_to_the_provider():
    assert _oidc({'issuer': ISSUER}) == {'issuer': ISSUER}


def test_malformed_oidc_metadata_stops_sign_in():
    document = {
        'issuer': ISSUER,
        'authorization_endpoint': [f'{ISSUER}/authorize'],
        'token_endpoint': f'{ISSUER}/token',
    }
    with (
        patch.object(utils, 'http_get_json', return_value=document),
        patch.object(providers, 'run_browser_login') as login,
    ):
        with pytest.raises(AgentRegistryJWTError, match='not a URL string'):
            GenericOidcProvider(ISSUER).authenticate(
                endpoint=ENDPOINT, registry_id=REGISTRY_ID, client_id='client'
            )
    login.assert_not_called()


# --- Issuer binding (OpenID Connect Discovery, section 4.3) ------------------


def _endpoints(issuer=ISSUER, host=ISSUER):
    return {
        'issuer': issuer,
        'authorization_endpoint': f'{host}/authorize',
        'token_endpoint': f'{host}/token',
    }


@pytest.mark.parametrize(
    'trusted,published',
    [
        (ISSUER, ISSUER),
        (f'{ISSUER}/', f'{ISSUER}/'),
        (ISSUER, f'{ISSUER}/'),
        (f'{ISSUER}/', ISSUER),
        (f'{ISSUER}/tenant', f'{ISSUER}/tenant/'),
    ],
)
def test_discovery_document_for_the_trusted_issuer_is_accepted(
    trusted, published
):
    document = _endpoints(issuer=published)
    with patch.object(utils, 'http_get_json', return_value=document):
        assert utils.fetch_oidc_metadata(trusted) == document


@pytest.mark.parametrize(
    'published',
    [
        'https://evil.example',
        'https://idp.example.com.evil.example',
        'http://idp.example.com',
        'https://IDP.example.com',
        f'{ISSUER}//',
        f'{ISSUER}/other',
        f'{ISSUER} ',
        '',
        None,
        1,
        [ISSUER],
    ],
)
def test_discovery_document_for_another_issuer_is_refused(published):
    document = _endpoints(issuer=published, host='https://evil.example')
    if published is None:
        del document['issuer']
    with patch.object(utils, 'http_get_json', return_value=document):
        with pytest.raises(AgentRegistryJWTError) as e:
            utils.fetch_oidc_metadata(ISSUER)
    message = str(e.value)
    assert 'Refusing to sign in' in message
    assert ISSUER in message


def test_issuer_in_the_refusal_is_printed_safely():
    document = _endpoints(issuer='https://evil.example/\x1b[2J')
    with patch.object(utils, 'http_get_json', return_value=document):
        with pytest.raises(AgentRegistryJWTError) as e:
            utils.fetch_oidc_metadata(ISSUER)
    assert '\x1b' not in str(e.value)


@pytest.mark.parametrize(
    'provider,issuer',
    [
        (GenericOidcProvider, ISSUER),
        (CognitoProvider, COGNITO_ISSUER),
    ],
)
def test_mismatched_issuer_stops_sign_in_before_the_browser_opens(
    provider, issuer
):
    document = _endpoints(
        issuer='https://evil.example', host='https://evil.example'
    )
    with (
        patch.object(utils, 'http_get_json', return_value=document),
        patch.object(providers, 'run_browser_login') as login,
        patch.object(providers, 'save_token') as save,
        patch(
            'awscli.customizations.agentregistry.browserflow.'
            'open_browser_with_original_ld_path'
        ) as browser,
        patch(
            'awscli.customizations.agentregistry.browserflow.urlopen'
        ) as exchange,
    ):
        with pytest.raises(AgentRegistryJWTError, match='another issuer'):
            provider(issuer).authenticate(
                session=None,
                endpoint=ENDPOINT,
                registry_id=REGISTRY_ID,
                client_id='client',
            )
    login.assert_not_called()
    save.assert_not_called()
    browser.assert_not_called()
    exchange.assert_not_called()


@pytest.mark.parametrize(
    'provider,issuer',
    [
        (GenericOidcProvider, ISSUER),
        (CognitoProvider, COGNITO_ISSUER),
    ],
)
def test_matching_issuer_signs_in_with_its_endpoints(provider, issuer):
    document = _endpoints(issuer=issuer, host='https://login.example.com')
    with (
        patch.object(utils, 'http_get_json', return_value=document),
        patch.object(
            providers, 'run_browser_login', return_value={'access_token': 't'}
        ) as login,
        patch.object(providers, 'save_token'),
    ):
        provider(issuer).authenticate(
            session=None,
            endpoint=ENDPOINT,
            registry_id=REGISTRY_ID,
            client_id='client',
        )
    kwargs = login.call_args.kwargs
    assert (
        kwargs['authorize_endpoint'] == 'https://login.example.com/authorize'
    )
    assert kwargs['token_endpoint'] == 'https://login.example.com/token'


@pytest.mark.parametrize(
    'supported', ['openid profile email', 1, {'openid': True}, None]
)
def test_malformed_scopes_supported_requests_only_openid(supported):
    assert utils.requested_scopes({'scopes_supported': supported}) == [
        'openid'
    ]


# --- Token responses --------------------------------------------------------


@pytest.mark.parametrize('payload', [[], 'x', 1, None])
def test_token_response_that_is_not_an_object_is_refused(payload):
    with pytest.raises(AgentRegistryJWTError, match='not a JSON object'):
        utils.select_bearer_token(payload)


@pytest.mark.parametrize('token', [1, ['a.b.c'], {'a': 'b'}, True])
def test_token_that_is_not_a_string_is_not_used(token):
    with pytest.raises(AgentRegistryJWTError, match='no access token'):
        utils.select_bearer_token({'access_token': token, 'id_token': token})


def test_id_token_is_used_when_the_access_token_is_not_a_string():
    identity = make_jwt()
    payload = {'access_token': 1, 'id_token': identity}
    assert utils.select_bearer_token(payload) == (identity, 'id_token')


# --- Read errors ------------------------------------------------------------

_READ_ERRORS = [
    TimeoutError('The read operation timed out'),
    socket.timeout('timed out'),
    ConnectionResetError(54, 'Connection reset by peer'),
    http.client.IncompleteRead(b'{"a', 10),
    http.client.RemoteDisconnected(''),
]
_READ_ERROR_IDS = [
    'timeout',
    'socket-timeout',
    'reset',
    'incomplete',
    'disconnected',
]


@pytest.mark.parametrize('error', _READ_ERRORS, ids=_READ_ERROR_IDS)
def test_resource_metadata_read_errors_are_reported_cleanly(error):
    with patch.object(utils, 'http_get_json', side_effect=error):
        with pytest.raises(AgentRegistryJWTError) as e:
            utils.discover_registry(ENDPOINT, REGISTRY_ID)
    message = str(e.value)
    assert message.startswith(
        f'Could not read protected resource metadata from {ENDPOINT}/'
    )
    # Never an empty reason.
    assert not message.endswith(': ')


@pytest.mark.parametrize('error', _READ_ERRORS, ids=_READ_ERROR_IDS)
def test_oidc_discovery_read_errors_are_reported_cleanly(error):
    with patch.object(utils, 'http_get_json', side_effect=error):
        with pytest.raises(AgentRegistryJWTError) as e:
            utils.fetch_oidc_metadata(ISSUER)
    message = str(e.value)
    assert ISSUER in message
    assert not message.endswith(': ')


# --- Scopes advertised in the metadata (RFC 9728) ---------------------------


def _registry(document):
    with patch.object(utils, 'http_get_json', return_value=document):
        return utils.discover_registry(ENDPOINT, REGISTRY_ID)


def test_advertised_scopes_are_read_with_the_issuer():
    registry = _registry(
        {
            'authorization_servers': [ISSUER],
            'scopes_supported': ['registry:read', 'openid', 'registry:read'],
        }
    )
    assert registry.issuer == ISSUER
    # Once each, in order.
    assert registry.scopes == ['registry:read', 'openid']


def test_no_advertised_scopes():
    registry = _registry({'authorization_servers': [ISSUER]})
    assert registry == (ISSUER, [])


@pytest.mark.parametrize(
    'scopes',
    [
        'registry:read',
        {'registry:read': True},
        7,
        True,
        ['registry:read', 7],
        ['registry:read', None],
        ['registry read'],
        ['registry"read'],
        ['registry\\read'],
        ['r\x1b[2J'],
        ['caf\u00e9'],
        [''],
        [f'scope{n}' for n in range(utils.MAX_ADVERTISED_SCOPES + 1)],
        ['registry:read', 'x' * (utils.MAX_SCOPE_LENGTH + 1)],
    ],
    ids=[
        'string',
        'object',
        'number',
        'bool',
        'non-string',
        'null',
        'space',
        'quote',
        'backslash',
        'control',
        'non-ascii',
        'empty',
        'too-many',
        'too-long',
    ],
)
def test_unusable_advertised_scopes_are_ignored(scopes, caplog):
    caplog.set_level(logging.DEBUG, logger=utils.__name__)
    registry = _registry(
        {'authorization_servers': [ISSUER], 'scopes_supported': scopes}
    )
    # Sign-in still works, with the defaults.
    assert registry == (ISSUER, [])
    assert 'Ignoring scopes_supported' in caplog.text


def test_as_many_advertised_scopes_as_allowed_are_kept():
    scopes = [f'scope{n}' for n in range(utils.MAX_ADVERTISED_SCOPES)]
    registry = _registry(
        {'authorization_servers': [ISSUER], 'scopes_supported': scopes}
    )
    assert registry.scopes == scopes


def test_a_scope_of_the_longest_allowed_length_is_kept():
    longest = 'x' * utils.MAX_SCOPE_LENGTH
    registry = _registry(
        {'authorization_servers': [ISSUER], 'scopes_supported': [longest]}
    )
    assert registry.scopes == [longest]
