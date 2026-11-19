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
"""Provider detection, browser-only sign-in, and argument wiring."""

import json
import os
from unittest.mock import Mock, patch

import botocore
import botocore.config
import botocore.loaders
import botocore.session
import pytest
from botocore.awsrequest import AWSResponse
from botocore.httpsession import URLLib3Session

from awscli.customizations import agentregistry
from awscli.customizations.agentregistry import (
    constants,
    dataplane,
    providers,
    utils,
)
from awscli.customizations.agentregistry.providers import (
    CognitoProvider,
    GenericOidcProvider,
    identify_provider,
)
from awscli.customizations.agentregistry.utils import AgentRegistryJWTError
from tests.unit.customizations.agentregistry.utils import make_jwe, make_jwt

COGNITO_ISSUER = 'https://cognito-idp.us-west-2.amazonaws.com/us-west-2_AbC123'
ENDPOINT = 'https://agent-registry.us-west-2.api.aws'


@pytest.fixture
def terminal():
    with patch.object(providers, 'stdin_is_terminal', return_value=True):
        yield


def test_cognito_issuer_is_recognised_with_region_and_pool():
    provider = identify_provider(COGNITO_ISSUER)
    assert isinstance(provider, CognitoProvider)
    assert provider.pool_id == 'us-west-2_AbC123'
    assert provider.pool_region == 'us-west-2'


def test_cognito_china_partition_is_recognised():
    issuer = 'https://cognito-idp.cn-north-1.amazonaws.com.cn/cn-north-1_X1'
    provider = identify_provider(issuer)
    assert isinstance(provider, CognitoProvider)
    assert provider.pool_region == 'cn-north-1'


@pytest.mark.parametrize(
    'issuer',
    [
        # Lookalikes that the old substring match accepted as Cognito.
        'https://evil.example/cognito-idp.us-east-1.amazonaws.com/us-east-1_X',
        'https://cognito-idp.us-east-1.amazonaws.com.evil.example/us-east-1_X',
        'https://xcognito-idp.us-east-1.amazonaws.com/us-east-1_X',
    ],
)
def test_cognito_lookalikes_are_not_treated_as_cognito(issuer):
    assert not isinstance(identify_provider(issuer), CognitoProvider)


def test_plain_http_issuer_is_unsupported():
    with pytest.raises(AgentRegistryJWTError):
        identify_provider('http://idp.example.com/')


COGNITO_DOMAIN = 'https://p.auth.us-west-2.amazoncognito.com'
COGNITO_METADATA = {
    'issuer': COGNITO_ISSUER,
    'authorization_endpoint': f'{COGNITO_DOMAIN}/oauth2/authorize',
    'token_endpoint': f'{COGNITO_DOMAIN}/oauth2/token',
    'revocation_endpoint': f'{COGNITO_DOMAIN}/oauth2/revoke',
}


def test_cognito_sign_in_uses_endpoints_from_discovery():
    payload = {'access_token': 'tok', 'expires_in': 3600}
    with (
        patch.object(
            providers, 'fetch_oidc_metadata', return_value=COGNITO_METADATA
        ) as fetch,
        patch.object(
            providers, 'run_browser_login', return_value=payload
        ) as login,
        patch.object(providers, 'save_token') as save,
    ):
        token = CognitoProvider(COGNITO_ISSUER).authenticate(
            session=Mock(),
            endpoint=ENDPOINT,
            registry_id='reg1',
            client_id='client',
            ca_bundle='/corp.pem',
        )
    assert token == 'tok'
    assert fetch.call_args.args[0] == COGNITO_ISSUER
    assert fetch.call_args.kwargs['ca_bundle'] == '/corp.pem'
    kwargs = login.call_args.kwargs
    assert (
        kwargs['authorize_endpoint']
        == COGNITO_METADATA['authorization_endpoint']
    )
    assert kwargs['token_endpoint'] == COGNITO_METADATA['token_endpoint']
    assert kwargs['scopes'] == ['openid']
    assert kwargs['ca_bundle'] == '/corp.pem'
    assert save.call_args.args == (ENDPOINT, 'reg1')
    saved = save.call_args.kwargs
    assert saved['pool_region'] == 'us-west-2'
    assert saved['client_id'] == 'client'
    assert saved['issuer'] == COGNITO_ISSUER
    assert saved['revocation_endpoint'] == f'{COGNITO_DOMAIN}/oauth2/revoke'


def _refresh_session(result):
    session = Mock()
    client = session.create_client.return_value
    client.get_tokens_from_refresh_token.return_value = {
        'AuthenticationResult': result
    }
    return session, client


COGNITO_CACHED = {
    'issuer': COGNITO_ISSUER,
    'poolRegion': 'us-west-2',
    'clientId': 'client',
    'refreshToken': 'rt',
}
# Where a refresh for COGNITO_CACHED goes: the issuer's scheme and host.
COGNITO_REFRESH_URL = 'https://cognito-idp.us-west-2.amazonaws.com/'


def test_cognito_refresh_uses_get_tokens_from_refresh_token():
    access = make_jwt()
    session, client = _refresh_session(
        {'AccessToken': access, 'ExpiresIn': 3600, 'IdToken': make_jwt()}
    )
    assert CognitoProvider.refresh(session, COGNITO_CACHED, '/corp.pem') == (
        access,
        3600,
        None,
    )
    client.get_tokens_from_refresh_token.assert_called_once_with(
        ClientId='client', RefreshToken='rt'
    )
    client.initiate_auth.assert_not_called()
    kwargs = session.create_client.call_args.kwargs
    assert kwargs['verify'] == '/corp.pem'
    assert kwargs['region_name'] == 'us-west-2'
    # The issuer's host, whatever endpoint is configured.
    assert kwargs['endpoint_url'] == (
        'https://cognito-idp.us-west-2.amazonaws.com'
    )
    # No AWS credentials: the request is not signed.
    assert kwargs['config'].signature_version is botocore.UNSIGNED
    # The https check, on this client only.
    client.meta.events.register.assert_called_once_with(
        'before-send.cognito-identity-provider.GetTokensFromRefreshToken',
        providers._refuse_plain_http_refresh,
    )


def test_cognito_refresh_returns_the_rotated_refresh_token():
    access = make_jwt()
    session, _ = _refresh_session(
        {'AccessToken': access, 'RefreshToken': 'rotated-rt'}
    )
    assert CognitoProvider.refresh(session, COGNITO_CACHED) == (
        access,
        None,
        'rotated-rt',
    )


def test_cognito_refresh_applies_the_sign_in_token_selection():
    identity = make_jwt(aud='client')
    session, _ = _refresh_session(
        {'AccessToken': make_jwe(), 'IdToken': identity}
    )
    assert CognitoProvider.refresh(session, COGNITO_CACHED)[0] == identity


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    """An isolated environment with an empty config file and no region."""
    path = tmp_path / 'config'
    path.write_text('')
    monkeypatch.setenv('AWS_CONFIG_FILE', str(path))
    monkeypatch.setenv('AWS_SHARED_CREDENTIALS_FILE', str(tmp_path / 'creds'))
    for name in list(os.environ):
        if name.startswith('AWS_ENDPOINT_URL') or name in (
            'AWS_PROFILE',
            'AWS_DEFAULT_PROFILE',
            'AWS_IGNORE_CONFIGURED_ENDPOINT_URLS',
            'AWS_REGION',
            'AWS_DEFAULT_REGION',
        ):
            monkeypatch.delenv(name)
    return path


def _session():
    session = botocore.session.Session()
    # Only the models shipped with the CLI, never a local ~/.aws/models
    # overlay.
    session.register_component(
        'data_loader',
        botocore.loaders.Loader(
            extra_search_paths=[botocore.loaders.Loader.BUILTIN_DATA_PATH],
            include_default_search_paths=False,
        ),
    )
    return session


class _Body:
    def __init__(self, document):
        self._content = json.dumps(document).encode()

    def stream(self):
        yield self._content


def _cognito_replies(document):
    """Stand in for the network; record each request that reaches it."""
    return patch.object(
        URLLib3Session,
        'send',
        side_effect=lambda request: AWSResponse(
            request.url, 200, {}, _Body(document)
        ),
    )


def test_refresh_guard_is_named_by_cognitos_hyphenized_service_id():
    service_id = _session().get_service_model('cognito-idp').service_id
    assert service_id.hyphenize() == 'cognito-identity-provider'
    assert providers._REFRESH_BEFORE_SEND == (
        f'before-send.{service_id.hyphenize()}.GetTokensFromRefreshToken'
    )


def _configure_endpoint(config_file, monkeypatch, source, url):
    """Configure ``url`` as the Cognito endpoint, the way ``source`` says."""
    if source == 'service':
        monkeypatch.setenv('AWS_ENDPOINT_URL_COGNITO_IDENTITY_PROVIDER', url)
    elif source == 'global':
        monkeypatch.setenv('AWS_ENDPOINT_URL', url)
    elif source == 'profile':
        config_file.write_text(f'[default]\nendpoint_url = {url}\n')
    elif source == 'services-section':
        config_file.write_text(
            f'[default]\nservices = overrides\n\n'
            f'[services overrides]\ncognito_identity_provider =\n'
            f'  endpoint_url = {url}\n'
        )


ENDPOINT_SOURCES = ['service', 'global', 'profile', 'services-section']


def _refreshed_request(session=None, cached=COGNITO_CACHED):
    """Refresh ``cached``; return the request that reached the network."""
    access = make_jwt()
    with _cognito_replies(
        {'AuthenticationResult': {'AccessToken': access}}
    ) as send:
        token, _, _ = CognitoProvider.refresh(session or _session(), cached)
    assert token == access
    [request] = [call.args[0] for call in send.call_args_list]
    return request


def test_cognito_refresh_goes_to_the_issuer_host(config_file):
    request = _refreshed_request()
    assert request.url == COGNITO_REFRESH_URL
    assert request.headers['X-Amz-Target'] == (
        b'AWSCognitoIdentityProviderService.GetTokensFromRefreshToken'
    )
    assert json.loads(request.body) == {
        'ClientId': 'client',
        'RefreshToken': 'rt',
    }


@pytest.mark.parametrize(
    'url', ['https://attacker.example', 'http://localhost:9229']
)
@pytest.mark.parametrize('source', ENDPOINT_SOURCES)
def test_cognito_refresh_ignores_configured_endpoints(
    config_file, monkeypatch, source, url
):
    # The refresh token is a reusable credential: it only goes to the pool
    # that issued it, whatever endpoint the environment or config names.
    _configure_endpoint(config_file, monkeypatch, source, url)
    request = _refreshed_request()
    assert request.url == COGNITO_REFRESH_URL
    assert json.loads(request.body)['RefreshToken'] == 'rt'


@pytest.mark.parametrize('source', [None, *ENDPOINT_SOURCES])
def test_cognito_refresh_in_china_goes_to_the_cn_host(
    config_file, monkeypatch, source
):
    _configure_endpoint(
        config_file, monkeypatch, source, 'https://attacker.example'
    )
    cached = {
        **COGNITO_CACHED,
        'issuer': 'https://cognito-idp.cn-north-1.amazonaws.com.cn/'
        'cn-north-1_X1',
        'poolRegion': 'cn-north-1',
    }
    request = _refreshed_request(cached=cached)
    assert request.url == 'https://cognito-idp.cn-north-1.amazonaws.com.cn/'


@pytest.mark.parametrize(
    'issuer',
    [
        # A sign-in saved by this CLI always has one.
        None,
        '',
        123,
        'https://attacker.example/us-west-2_AbC123',
        'https://idp.example.com',
        'http://cognito-idp.us-west-2.amazonaws.com/us-west-2_AbC123',
        'https://cognito-idp.us-west-2.amazonaws.com.evil.example/'
        'us-west-2_AbC123',
        'https://cognito-idp.us-west-2.amazonaws.com:8443/us-west-2_AbC123',
        'https://user@cognito-idp.us-west-2.amazonaws.com/us-west-2_AbC123',
        f'{COGNITO_ISSUER}\n',
        f'{COGNITO_ISSUER}/extra',
        # Another region's pool than the entry's poolRegion.
        'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_AbC123',
    ],
)
def test_cognito_refresh_without_a_usable_issuer_sends_nothing(issuer):
    cached = dict(COGNITO_CACHED)
    if issuer is None:
        del cached['issuer']
    else:
        cached['issuer'] = issuer
    assert CognitoProvider.refresh_endpoint(cached) is None
    session = Mock()
    with _cognito_replies({}) as send:
        # A cache miss, so the caller signs in again.
        assert CognitoProvider.refresh(session, cached) == (None, None, None)
    session.create_client.assert_not_called()
    send.assert_not_called()


@pytest.mark.parametrize(
    'issuer,expected',
    [
        (COGNITO_ISSUER, 'https://cognito-idp.us-west-2.amazonaws.com'),
        (
            f'{COGNITO_ISSUER}/',
            'https://cognito-idp.us-west-2.amazonaws.com',
        ),
    ],
)
def test_cognito_refresh_endpoint_is_the_issuer_origin(issuer, expected):
    cached = {**COGNITO_CACHED, 'issuer': issuer}
    assert CognitoProvider.refresh_endpoint(cached) == expected


def test_cognito_refresh_guard_refuses_plain_http():
    # Defense in depth: the pinned endpoint is always https.
    request = Mock(url='http://cognito-idp.us-west-2.amazonaws.com/')
    with pytest.raises(AgentRegistryJWTError, match='Cognito endpoint'):
        providers._refuse_plain_http_refresh(request)
    providers._refuse_plain_http_refresh(Mock(url=COGNITO_REFRESH_URL))


def test_cognito_refresh_pin_and_guard_are_only_on_its_own_client(
    config_file, monkeypatch
):
    monkeypatch.setenv(
        'AWS_ENDPOINT_URL_COGNITO_IDENTITY_PROVIDER', 'http://localhost:9229'
    )
    session = _session()
    assert _refreshed_request(session).url == COGNITO_REFRESH_URL
    # Another client of the same session, as aws cognito-idp would use,
    # still follows the configured endpoint, plain http included.
    client = session.create_client(
        'cognito-idp',
        region_name='us-west-2',
        config=botocore.config.Config(signature_version=botocore.UNSIGNED),
    )
    with _cognito_replies({}) as send:
        client.get_tokens_from_refresh_token(ClientId='c', RefreshToken='r')
    [request] = [call.args[0] for call in send.call_args_list]
    assert request.url == 'http://localhost:9229/'


@pytest.mark.parametrize(
    'metadata',
    [
        {'issuer': COGNITO_ISSUER},
        {
            'issuer': COGNITO_ISSUER,
            'token_endpoint': f'{COGNITO_DOMAIN}/oauth2/token',
        },
    ],
)
def test_cognito_pool_without_domain_tells_the_owner_to_add_one(metadata):
    with (
        patch.object(providers, 'fetch_oidc_metadata', return_value=metadata),
        patch.object(providers, 'run_browser_login') as login,
    ):
        with pytest.raises(AgentRegistryJWTError) as e:
            CognitoProvider(COGNITO_ISSUER).authenticate(
                session=Mock(),
                endpoint=ENDPOINT,
                registry_id='reg1',
                client_id='client',
            )
    message = str(e.value)
    assert 'registry owner must add a domain to the user pool' in message
    assert 'Branding, then Domain' in message
    assert 'configure-jwt-signin' not in message
    login.assert_not_called()


def test_cognito_requires_a_client_id(terminal):
    with patch.object(providers, 'prompt', return_value=''):
        with pytest.raises(AgentRegistryJWTError, match='client id'):
            CognitoProvider(COGNITO_ISSUER).authenticate(
                session=Mock(), endpoint=ENDPOINT, registry_id='reg1'
            )


def test_cognito_prompts_for_the_client_id_at_a_terminal(terminal):
    with (
        patch.object(providers, 'prompt', return_value='typed') as asked,
        patch.object(
            providers, 'fetch_oidc_metadata', return_value=COGNITO_METADATA
        ),
        patch.object(
            providers, 'run_browser_login', return_value={'access_token': 't'}
        ) as login,
        patch.object(providers, 'save_token'),
    ):
        CognitoProvider(COGNITO_ISSUER).authenticate(
            session=Mock(), endpoint=ENDPOINT, registry_id='reg1'
        )
    asked.assert_called_once()
    assert login.call_args.kwargs['client_id'] == 'typed'


def test_missing_stdin_counts_as_not_a_terminal(monkeypatch):
    monkeypatch.setattr(utils.sys, 'stdin', None)
    assert not utils.stdin_is_terminal()


GENERIC_METADATA = {
    'issuer': 'https://idp.example.com',
    'authorization_endpoint': 'https://idp.example.com/authorize',
    'token_endpoint': 'https://idp.example.com/oauth/token',
}


@pytest.mark.parametrize(
    'authenticate',
    [
        lambda: CognitoProvider(COGNITO_ISSUER).authenticate(
            session=Mock(), endpoint=ENDPOINT, registry_id='reg1'
        ),
        lambda: GenericOidcProvider('https://idp.example.com').authenticate(
            endpoint=ENDPOINT, registry_id='reg1'
        ),
    ],
)
def test_missing_client_id_without_a_terminal_says_to_pass_it(authenticate):
    # input() would fail with a bare "EOF when reading a line".
    with (
        patch.object(providers, 'stdin_is_terminal', return_value=False),
        patch.object(providers, 'prompt') as asked,
        patch.object(
            providers, 'fetch_oidc_metadata', return_value=GENERIC_METADATA
        ),
        patch.object(providers, 'run_browser_login') as login,
    ):
        with pytest.raises(AgentRegistryJWTError, match='Pass --client-id'):
            authenticate()
    asked.assert_not_called()
    login.assert_not_called()


def test_generic_provider_without_endpoints_fails_rather_than_asking_for_password():
    with (
        patch.object(
            providers,
            'fetch_oidc_metadata',
            return_value={'issuer': 'https://idp.example.com'},
        ),
        patch.object(providers, 'run_browser_login') as login,
    ):
        with pytest.raises(AgentRegistryJWTError, match='sign-in'):
            GenericOidcProvider('https://idp.example.com').authenticate(
                endpoint=ENDPOINT, registry_id='reg1', client_id='client'
            )
    login.assert_not_called()


@pytest.mark.parametrize('client_id', [None, ''])
def test_generic_provider_requires_a_client_id(terminal, client_id):
    with (
        patch.object(
            providers, 'fetch_oidc_metadata', return_value=GENERIC_METADATA
        ),
        patch.object(providers, 'prompt', return_value='') as asked,
        patch.object(providers, 'run_browser_login') as login,
        patch.object(providers, 'save_token') as save,
    ):
        with pytest.raises(AgentRegistryJWTError, match='client id'):
            GenericOidcProvider('https://idp.example.com').authenticate(
                endpoint=ENDPOINT, registry_id='reg1', client_id=client_id
            )
    asked.assert_called_once()
    login.assert_not_called()
    save.assert_not_called()


@pytest.mark.parametrize(
    'revocation,expected',
    [
        (
            'https://idp.example.com/oauth/revoke',
            'https://idp.example.com/oauth/revoke',
        ),
        (None, None),
        ('', None),
        (['https://idp.example.com/oauth/revoke'], None),
    ],
)
def test_generic_sign_in_saves_what_refresh_and_sign_out_need(
    revocation, expected
):
    metadata = dict(GENERIC_METADATA, revocation_endpoint=revocation)
    with (
        patch.object(providers, 'fetch_oidc_metadata', return_value=metadata),
        patch.object(
            providers, 'run_browser_login', return_value={'access_token': 't'}
        ),
        patch.object(providers, 'save_token') as save,
    ):
        GenericOidcProvider('https://idp.example.com/').authenticate(
            endpoint=ENDPOINT, registry_id='reg1', client_id='client'
        )
    assert save.call_args.args == (ENDPOINT, 'reg1')
    saved = save.call_args.kwargs
    assert saved['revocation_endpoint'] == expected
    assert saved['token_endpoint'] == metadata['token_endpoint']
    assert saved['client_id'] == 'client'
    # As the registry's metadata publishes it.
    assert saved['issuer'] == 'https://idp.example.com/'


def test_generic_sign_in_requests_only_needed_scopes_and_no_audience():
    metadata = {
        'issuer': 'https://idp.example.com',
        'authorization_endpoint': 'https://idp.example.com/authorize',
        'token_endpoint': 'https://idp.example.com/oauth/token',
        'scopes_supported': ['openid', 'email', 'offline_access', 'admin'],
    }
    payload = {'access_token': 'tok', 'expires_in': 60}
    with (
        patch.object(
            providers, 'fetch_oidc_metadata', return_value=metadata
        ) as fetch,
        patch.object(
            providers, 'run_browser_login', return_value=payload
        ) as login,
        patch.object(providers, 'save_token') as save,
    ):
        GenericOidcProvider('https://idp.example.com').authenticate(
            endpoint=ENDPOINT,
            registry_id='reg1',
            client_id='client',
            ca_bundle='/corp.pem',
        )
    kwargs = login.call_args.kwargs
    assert 'audience' not in kwargs
    # Only the scopes this flow needs, never everything advertised.
    assert kwargs['scopes'] == ['openid', 'email', 'offline_access']
    assert kwargs['ca_bundle'] == '/corp.pem'
    assert fetch.call_args.kwargs['ca_bundle'] == '/corp.pem'
    assert (
        save.call_args.kwargs['token_endpoint'] == metadata['token_endpoint']
    )


def test_sign_in_arguments():
    # No password flow, audience or sign-in domain arguments.
    names = [argument['name'] for argument in dataplane.SIGN_IN_ARGUMENTS]
    assert names == ['authorizer', 'client-id', 'no-browser']


def test_before_send_guard_is_registered():
    cli = Mock()
    agentregistry.initialize(cli)
    events = [call.args[0] for call in cli.register.call_args_list]
    assert 'before-send.agent-registry' in events


def test_only_in_scope_commands_are_added():
    table = {}
    agentregistry.inject_commands(table, session=Mock())
    assert set(table) == {
        'list-skills',
        'install-skill',
        'uninstall-skill',
        'sign-out',
    }


def test_authorizer_help_describes_browser_sign_in():
    # Sign-in is browser-only; the CLI never asks for a password.
    docs = constants.AUTHORIZER_DOCS
    assert 'prompts for credentials' not in docs
    assert 'browser' in docs
    assert 'cached' in docs
    assert 'AWS_BEARER_TOKEN_AGENT_REGISTRY' in docs
    assert 'sign-out' in docs


def test_help_lists_the_owner_setup():
    docs = constants.CLIENT_ID_DOCS
    assert 'public client with no client secret' in docs
    assert 'http://127.0.0.1:8484/oauth/callback' in docs
    assert 'authorization-code flow' in docs
    assert '<code>openid</code> scope' in docs
    assert 'Cognito user pool also needs a domain' in docs
    assert 'localhost' not in docs


# --- Scopes -----------------------------------------------------------------


def test_cognito_requests_openid_and_the_extra_scopes():
    with (
        patch.object(
            providers, 'fetch_oidc_metadata', return_value=COGNITO_METADATA
        ),
        patch.object(
            providers, 'run_browser_login', return_value={'access_token': 't'}
        ) as login,
        patch.object(providers, 'save_token') as save,
    ):
        CognitoProvider(COGNITO_ISSUER).authenticate(
            session=Mock(),
            endpoint=ENDPOINT,
            registry_id='reg1',
            client_id='client',
            extra_scopes=['registry/read', 'openid'],
        )
    assert login.call_args.kwargs['scopes'] == ['openid', 'registry/read']
    assert save.call_args.kwargs['scopes'] == ['openid', 'registry/read']


@pytest.mark.parametrize(
    'payload,stored',
    [
        # Granted as requested.
        ({'access_token': 't'}, ['openid', 'email', 'registry:read']),
        (
            {'access_token': 't', 'scope': 'openid registry:read'},
            ['openid', 'email', 'registry:read'],
        ),
        # Reported differently, as Entra does: both are kept.
        (
            {'access_token': 't', 'scope': 'api://registry/.default'},
            ['openid', 'email', 'registry:read', 'api://registry/.default'],
        ),
        # One left out: still kept, so a refresh still finds every
        # advertised scope in the cached sign-in.
        (
            {'access_token': 't', 'scope': 'openid'},
            ['openid', 'email', 'registry:read'],
        ),
        (
            {'access_token': 't', 'scope': ''},
            ['openid', 'email', 'registry:read'],
        ),
        (
            {'access_token': 't', 'scope': 7},
            ['openid', 'email', 'registry:read'],
        ),
    ],
)
def test_generic_requests_defaults_and_extras_and_stores_the_granted(
    payload, stored
):
    metadata = dict(GENERIC_METADATA, scopes_supported=['openid', 'email'])
    with (
        patch.object(providers, 'fetch_oidc_metadata', return_value=metadata),
        patch.object(
            providers, 'run_browser_login', return_value=payload
        ) as login,
        patch.object(providers, 'save_token') as save,
    ):
        GenericOidcProvider('https://idp.example.com').authenticate(
            endpoint=ENDPOINT,
            registry_id='reg1',
            client_id='client',
            extra_scopes=['registry:read', 'email'],
        )
    assert login.call_args.kwargs['scopes'] == [
        'openid',
        'email',
        'registry:read',
    ]
    assert save.call_args.kwargs['scopes'] == stored


def test_authorizer_help_says_advertised_scopes_are_requested():
    assert (
        'The CLI requests any scopes the registry advertises in its Protected '
        'Resource Metadata'
    ) in constants.AUTHORIZER_DOCS


def test_no_browser_help_says_the_redirect_still_comes_here():
    docs = constants.NO_BROWSER_DOCS
    assert 'Print the sign-in link instead of opening a browser' in docs
    assert '<code>ssh -L 8484:127.0.0.1:8484</code>' in docs


# --- --no-browser -----------------------------------------------------------


@pytest.mark.parametrize('open_browser', [True, False])
def test_sign_in_passes_open_browser_to_the_provider(open_browser):
    provider = Mock(display_name='test provider')
    with (
        patch.object(
            providers,
            'discover_registry',
            return_value=utils.RegistryAuthorization(
                'https://idp.example.com', []
            ),
        ),
        patch.object(providers, 'identify_provider', return_value=provider),
    ):
        providers.sign_in(
            Mock(),
            ENDPOINT,
            'reg1',
            client_id='client',
            open_browser=open_browser,
        )
    kwargs = provider.authenticate.call_args.kwargs
    assert kwargs['open_browser'] is open_browser


def test_sign_in_opens_the_browser_by_default():
    provider = Mock(display_name='test provider')
    with (
        patch.object(
            providers,
            'discover_registry',
            return_value=utils.RegistryAuthorization(
                'https://idp.example.com', []
            ),
        ),
        patch.object(providers, 'identify_provider', return_value=provider),
    ):
        providers.sign_in(Mock(), ENDPOINT, 'reg1', client_id='client')
    assert provider.authenticate.call_args.kwargs['open_browser'] is True


@pytest.mark.parametrize('open_browser', [True, False])
@pytest.mark.parametrize(
    'provider_cls,issuer,metadata',
    [
        (CognitoProvider, COGNITO_ISSUER, COGNITO_METADATA),
        (GenericOidcProvider, 'https://idp.example.com', GENERIC_METADATA),
    ],
    ids=['cognito', 'generic'],
)
def test_providers_pass_open_browser_to_the_browser_login(
    provider_cls, issuer, metadata, open_browser
):
    with (
        patch.object(providers, 'fetch_oidc_metadata', return_value=metadata),
        patch.object(
            providers, 'run_browser_login', return_value={'access_token': 't'}
        ) as login,
        patch.object(providers, 'save_token'),
    ):
        provider_cls(issuer).authenticate(
            session=Mock(),
            endpoint=ENDPOINT,
            registry_id='reg1',
            client_id='client',
            open_browser=open_browser,
        )
    assert login.call_args.kwargs['open_browser'] is open_browser
