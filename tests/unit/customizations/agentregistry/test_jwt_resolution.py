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
"""Sign-in wiring: the shared setup of the commands that sign in, and the
generated data plane commands, which do not."""

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import shutil
from unittest.mock import ANY, Mock, patch

import botocore
import botocore.config
import botocore.loaders
import botocore.session
import pytest
from botocore.awsrequest import AWSResponse
from botocore.endpoint import Endpoint
from botocore.exceptions import ClientError
from botocore.hooks import HierarchicalEmitter
from botocore.httpsession import URLLib3Session, get_cert_path
from botocore.tokens import SSOTokenProvider

from awscli.customizations import agentregistry
from awscli.customizations.agentregistry import (
    cache,
    constants,
    dataplane,
    providers,
    utils,
)
from awscli.customizations.agentregistry.utils import (
    AgentRegistryJWTError,
    bare_registry_id,
    resolve_data_plane_endpoint,
)
from tests.unit.customizations.agentregistry.utils import make_jwt

LIST = 'list-discoverable-registry-records'
SEARCH = 'search-discoverable-registry-records'
BATCH_GET = 'batch-get-discoverable-registry-record'

REGISTRY_ID = 'abcDEF123456'
OTHER_REGISTRY_ID = 'xyzXYZ9876543210'
REGISTRY_ARN = (
    f'arn:aws:agent-registry:us-west-2:123456789012:registry/{REGISTRY_ID}'
)
MODEL_PATH = (
    pathlib.Path(botocore.loaders.Loader.BUILTIN_DATA_PATH)
    / 'agent-registry'
    / '2025-12-01'
    / 'service-2.json'
)
# Botocore's, which this customization no longer sets.
PREFERENCE_ENV_VAR = 'AWS_AUTH_SCHEME_PREFERENCE'


@pytest.fixture
def auth_env(monkeypatch):
    # Set before deleting so monkeypatch restores the original absence even
    # though the code under test writes these variables itself.
    for name in (constants.TOKEN_ENV_VAR, PREFERENCE_ENV_VAR):
        monkeypatch.setenv(name, 'placeholder')
        monkeypatch.delenv(name)


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
            'AWS_CA_BUNDLE',
            'AWS_REGION',
            'AWS_DEFAULT_REGION',
        ):
            monkeypatch.delenv(name)
    return path


def _session():
    session = botocore.session.Session()
    # Only the models shipped with the CLI, never a local ~/.aws/models
    # overlay, which can change the service id and so the env var names.
    session.register_component(
        'data_loader',
        botocore.loaders.Loader(
            extra_search_paths=[botocore.loaders.Loader.BUILTIN_DATA_PATH],
            include_default_search_paths=False,
        ),
    )
    return session


def _globals(**overrides):
    values = {
        'region': 'us-west-2',
        'endpoint_url': None,
        'ca_bundle': None,
        'verify_ssl': None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


# --- Registry id ------------------------------------------------------------


@pytest.mark.parametrize(
    'arn',
    [
        REGISTRY_ARN,
        f'arn:aws-cn:agent-registry:cn-north-1:123456789012:registry/'
        f'{REGISTRY_ID}',
        f'arn:aws-us-gov:agent-registry:us-gov-west-1:123456789012:registry/'
        f'{REGISTRY_ID}',
    ],
)
def test_arn_in_any_partition_shares_the_id(arn):
    assert bare_registry_id(arn) == bare_registry_id(REGISTRY_ID)


@pytest.mark.parametrize(
    'identifier',
    [
        'reg1',  # too short
        'a' * 17,  # too long
        'abcDEF12345/',
        'abcDEF123456/../x',
        '../abcDEF123456',
        'abcDEF%2f3456',
        'abcDEF123456\n',
        'abcDEF 123456',
        'abcDEF12345\x1b',
        '',
        None,
        123456789012,
        ['abcDEF123456'],
        # ARNs for another service, resource type or account shape.
        f'arn:aws:s3:us-west-2:123456789012:registry/{REGISTRY_ID}',
        f'arn:aws:agent-registry:us-west-2:123456789012:record/{REGISTRY_ID}',
        f'arn:aws:agent-registry:us-west-2:1234:registry/{REGISTRY_ID}',
        f'arn:aws:agent-registry:us-west-2:123456789012:registry/'
        f'{REGISTRY_ID}/record/r',
        f'{REGISTRY_ARN}\n',
    ],
)
def test_malformed_registry_identifier_is_refused(identifier):
    with pytest.raises(AgentRegistryJWTError, match='registry identifier'):
        bare_registry_id(identifier)


def test_refused_identifier_is_not_echoed_raw():
    with pytest.raises(AgentRegistryJWTError) as e:
        bare_registry_id('abc\x1b[2Jdef')
    assert '\x1b' not in str(e.value)


def test_id_rule_matches_the_bundled_model():
    shapes = json.loads(MODEL_PATH.read_text())['shapes']
    pattern = shapes['RegistryIdentifier']['pattern']
    # The customization captures the id; the model's pattern does not.
    expected = pattern.replace('(arn:aws(-[^:]+)?', '(?:arn:aws(?:-[^:]+)?')
    expected = expected.replace('[a-zA-Z0-9]{12,16}', '([a-zA-Z0-9]{12,16})')
    assert utils._REGISTRY_IDENTIFIER.pattern == expected


# --- Endpoint ---------------------------------------------------------------


def test_default_endpoint_follows_the_endpoint_rules(config_file):
    # The legacy resolver would say agent-registry.us-west-2.amazonaws.com;
    # requests are sent by the endpoint rules.
    endpoint = resolve_data_plane_endpoint(_session(), _globals(), 'us-west-2')
    assert endpoint == 'https://agent-registry.us-west-2.api.aws'


def test_endpoint_from_service_environment_variable(config_file, monkeypatch):
    monkeypatch.setenv(
        'AWS_ENDPOINT_URL_AGENT_REGISTRY', 'https://env.example/'
    )
    endpoint = resolve_data_plane_endpoint(_session(), _globals(), 'us-west-2')
    assert endpoint == 'https://env.example'


def test_endpoint_from_profile_in_config_file(config_file):
    config_file.write_text(
        '[profile dev]\n'
        'services = dev-services\n'
        '[services dev-services]\n'
        'agent_registry =\n'
        '  endpoint_url = https://config.example\n'
    )
    session = _session()
    # What the CLI does with --profile dev.
    session.set_config_variable('profile', 'dev')
    endpoint = resolve_data_plane_endpoint(session, _globals(), 'us-west-2')
    assert endpoint == 'https://config.example'
    # The default profile is not affected.
    endpoint = resolve_data_plane_endpoint(_session(), _globals(), 'us-west-2')
    assert endpoint == 'https://agent-registry.us-west-2.api.aws'


def test_endpoint_url_argument_wins(config_file, monkeypatch):
    monkeypatch.setenv(
        'AWS_ENDPOINT_URL_AGENT_REGISTRY', 'https://env.example'
    )
    globals_ = _globals(endpoint_url='https://flag.example/')
    endpoint = resolve_data_plane_endpoint(_session(), globals_, 'us-west-2')
    assert endpoint == 'https://flag.example'


# Botocore builds no client without a region, even for an endpoint override.
@pytest.mark.parametrize('endpoint_url', [None, 'https://flag.example'])
def test_missing_region_is_explained(config_file, endpoint_url):
    globals_ = _globals(region=None, endpoint_url=endpoint_url)
    with pytest.raises(AgentRegistryJWTError, match='--region'):
        resolve_data_plane_endpoint(_session(), globals_, None)


@pytest.mark.parametrize('source', ['argument', 'environment', 'config'])
def test_plain_http_endpoint_is_refused(config_file, monkeypatch, source):
    url = 'http://localhost:8080'
    globals_ = _globals()
    if source == 'argument':
        globals_ = _globals(endpoint_url=url)
    elif source == 'environment':
        monkeypatch.setenv('AWS_ENDPOINT_URL_AGENT_REGISTRY', url)
    else:
        config_file.write_text(f'[default]\nendpoint_url = {url}\n')
    with pytest.raises(AgentRegistryJWTError, match='registry endpoint'):
        resolve_data_plane_endpoint(_session(), globals_, 'us-west-2')


@pytest.mark.parametrize('source', ['argument', 'environment', 'config'])
def test_plain_http_endpoint_resolves_when_https_is_not_required(
    config_file, monkeypatch, source
):
    # For a SigV4 call, which botocore may send to a local endpoint.
    url = 'http://localhost:8080/'
    globals_ = _globals()
    if source == 'argument':
        globals_ = _globals(endpoint_url=url)
    elif source == 'environment':
        monkeypatch.setenv('AWS_ENDPOINT_URL_AGENT_REGISTRY', url)
    else:
        config_file.write_text(f'[default]\nendpoint_url = {url}\n')
    endpoint = resolve_data_plane_endpoint(
        _session(), globals_, 'us-west-2', https_only=False
    )
    assert endpoint == 'http://localhost:8080'


_CONFIGURED_ENDPOINT_SETTINGS = (
    'AWS_ENDPOINT_URL_AGENT_REGISTRY, AWS_ENDPOINT_URL or endpoint_url in the '
    'config file'
)


@pytest.mark.parametrize(
    'suffix', ['?x=1', '/?x=1', '/base?x=1', '#x', '/base/#x', '?x=1#y']
)
@pytest.mark.parametrize(
    'source', ['argument', 'environment', 'global environment', 'config']
)
@pytest.mark.parametrize('https_only', [True, False])
def test_endpoint_with_a_query_or_fragment_is_refused(
    config_file, monkeypatch, suffix, source, https_only
):
    url = f'https://registry.example{suffix}'
    globals_ = _globals()
    if source == 'argument':
        globals_ = _globals(endpoint_url=url)
    elif source == 'environment':
        monkeypatch.setenv('AWS_ENDPOINT_URL_AGENT_REGISTRY', url)
    elif source == 'global environment':
        monkeypatch.setenv('AWS_ENDPOINT_URL', url)
    else:
        config_file.write_text(f'[default]\nendpoint_url = {url}\n')
    with pytest.raises(AgentRegistryJWTError) as e:
        resolve_data_plane_endpoint(
            _session(), globals_, 'us-west-2', https_only=https_only
        )
    setting = (
        '--endpoint-url'
        if source == 'argument'
        else _CONFIGURED_ENDPOINT_SETTINGS
    )
    assert str(e.value) == (
        'Refusing registry endpoint https://registry.example: it has a query '
        'string or fragment, and a registry endpoint can only have a scheme, '
        'host and path. Remove the query string or fragment from '
        f'{setting}.'
    )


@pytest.mark.parametrize(
    'url', ['https://registry.example/?', 'https://r.example/#']
)
def test_an_empty_query_or_fragment_is_no_query(config_file, url):
    globals_ = _globals(endpoint_url=url)
    endpoint = resolve_data_plane_endpoint(_session(), globals_, 'us-west-2')
    assert '?' not in endpoint and '#' not in endpoint


@pytest.mark.parametrize('authorizer', ['JWT', None])
def test_a_query_is_refused_before_any_sign_in_or_call(
    config_file, auth_env, authorizer
):
    session = _session()
    globals_ = _globals(endpoint_url='https://registry.example/?x=1')
    with (
        patch.object(cache, 'load_token') as load,
        patch.object(providers, 'sign_in') as sign_in,
        patch.object(
            URLLib3Session, 'send', side_effect=AssertionError('sent')
        ) as send,
        pytest.raises(AgentRegistryJWTError, match='query string'),
    ):
        _connect(_args(authorizer=authorizer), globals_, session)
    load.assert_not_called()
    sign_in.assert_not_called()
    send.assert_not_called()


def test_endpoint_resolution_needs_no_credentials(config_file):
    session = _session()
    with patch.object(session, 'get_credentials') as credentials:
        resolve_data_plane_endpoint(session, _globals(), 'us-west-2')
    credentials.assert_not_called()


@pytest.fixture
def no_network():
    """Fails a test whose request reaches the network."""
    with patch.object(
        URLLib3Session, 'send', side_effect=AssertionError('request sent')
    ) as send:
        yield send


# What the previous implementation, which ran botocore's endpoint rules
# directly, resolved each of these to.
@pytest.mark.parametrize(
    'endpoint_url,environment,expected',
    [
        (None, None, 'https://agent-registry.us-west-2.api.aws'),
        ('https://flag.example', None, 'https://flag.example'),
        ('https://flag.example/', None, 'https://flag.example'),
        ('https://Flag.Example:443/', None, 'https://Flag.Example:443'),
        ('https://flag.example/prefix', None, 'https://flag.example/prefix'),
        ('https://flag.example/prefix/', None, 'https://flag.example/prefix'),
        ('https://flag.example/a/b//', None, 'https://flag.example/a/b'),
        (None, 'https://env.example', 'https://env.example'),
        (None, 'https://env.example/', 'https://env.example'),
        (None, 'https://env.example/base/', 'https://env.example/base'),
    ],
)
def test_endpoint_is_read_from_a_request_that_is_never_sent(
    config_file, monkeypatch, no_network, endpoint_url, environment, expected
):
    if environment:
        monkeypatch.setenv('AWS_ENDPOINT_URL_AGENT_REGISTRY', environment)
    session = _session()
    with patch.object(session, 'get_credentials') as credentials:
        endpoint = resolve_data_plane_endpoint(
            session, _globals(endpoint_url=endpoint_url), 'us-west-2'
        )
    assert endpoint == expected
    no_network.assert_not_called()
    credentials.assert_not_called()


def test_endpoint_resolution_leaves_later_clients_alone(config_file):
    session = _session()
    resolve_data_plane_endpoint(session, _globals(), 'us-west-2')
    client = session.create_client(
        'agent-registry',
        region_name='us-west-2',
        config=botocore.config.Config(signature_version=botocore.UNSIGNED),
    )
    with patch.object(
        URLLib3Session,
        'send',
        side_effect=lambda request: AWSResponse(request.url, 200, {}, _Body()),
    ) as send:
        client.list_discoverable_registry_records(registryId=REGISTRY_ID)
    [request] = [call.args[0] for call in send.call_args_list]
    assert request.url == (
        'https://agent-registry.us-west-2.api.aws/registries/'
        f'{REGISTRY_ID}/discoverable-records-list'
    )


# --- The shared setup: create_data_plane_client and use_bearer_token -------


ENDPOINT = 'https://registry.example'


def _args(**overrides):
    values = {
        'registry_id': REGISTRY_ID,
        'authorizer': 'JWT',
        'client_id': 'client',
        'no_browser': False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


@pytest.fixture
def flow():
    """Patch every step that would touch the network or a browser."""
    provider = Mock(display_name='test provider')
    provider.authenticate.return_value = 'signed-in-token'
    with (
        patch.object(
            dataplane, 'resolve_data_plane_endpoint', return_value=ENDPOINT
        ) as endpoint,
        patch.object(cache, 'load_token', return_value=None) as load,
        patch.object(
            providers,
            'discover_registry',
            return_value=utils.RegistryAuthorization(
                'https://idp.example.com', []
            ),
        ) as discover,
        patch.object(providers, 'identify_provider', return_value=provider),
    ):
        yield Mock(
            endpoint=endpoint,
            load=load,
            discover=discover,
            provider=provider,
        )


def _cli_session(ca_bundle=None, region='us-west-2'):
    session = Mock()
    session.get_config_variable.side_effect = {
        'region': region,
        'ca_bundle': ca_bundle,
    }.get
    return session


def _connect(args=None, globals_=None, session=None):
    return dataplane.create_data_plane_client(
        session or _cli_session(),
        args or _args(),
        globals_ or _globals(),
    )


@pytest.mark.parametrize('authorizer', [None, 'SIGV4'])
def test_without_jwt_there_is_no_sign_in(auth_env, flow, authorizer):
    session = _cli_session()
    globals_ = _globals()
    data_plane = _connect(_args(authorizer=authorizer), globals_, session)
    flow.load.assert_not_called()
    assert constants.TOKEN_ENV_VAR not in os.environ
    assert PREFERENCE_ENV_VAR not in os.environ
    # Created as botocore would, with no auth configuration added.
    assert session.create_client.call_args.kwargs['config'] is None
    # A SigV4 call may go to a local plain-HTTP endpoint.
    flow.endpoint.assert_called_once_with(
        session, globals_, 'us-west-2', https_only=False
    )
    assert data_plane.client is session.create_client.return_value
    assert data_plane.endpoint == ENDPOINT


def test_sign_in_exports_the_token_before_the_client_is_created(
    auth_env, flow
):
    session = _cli_session()
    globals_ = _globals(endpoint_url='https://flag.example', verify_ssl=None)
    exported = []

    def create_client(*args, **kwargs):
        exported.append(
            (
                os.environ.get(constants.TOKEN_ENV_VAR),
                os.environ.get(PREFERENCE_ENV_VAR),
            )
        )
        return Mock()

    session.create_client.side_effect = create_client
    data_plane = _connect(_args(), globals_, session)
    flow.endpoint.assert_called_once_with(
        session, globals_, 'us-west-2', https_only=True
    )
    assert flow.load.call_args.kwargs['session'] is session
    assert flow.provider.authenticate.call_args.kwargs['session'] is session
    # Exported first, so the client picks up the token. The bearer scheme
    # is selected in the client's config, not in the environment.
    assert exported == [('signed-in-token', None)]
    session.create_client.assert_called_once_with(
        'agent-registry',
        region_name='us-west-2',
        endpoint_url='https://flag.example',
        verify=None,
        config=ANY,
    )
    config = session.create_client.call_args.kwargs['config']
    assert config.auth_scheme_preference == 'httpBearerAuth'
    assert data_plane.endpoint == ENDPOINT
    assert data_plane.region == 'us-west-2'


def test_cache_and_sign_in_are_keyed_by_the_resolved_endpoint(auth_env, flow):
    _connect(_args(client_id='my-client'))
    assert flow.load.call_args.args == (ENDPOINT, REGISTRY_ID)
    # A different --client-id than the cached one is a miss.
    assert flow.load.call_args.kwargs['client_id'] == 'my-client'
    kwargs = flow.provider.authenticate.call_args.kwargs
    assert kwargs['endpoint'] == ENDPOINT
    assert kwargs['client_id'] == 'my-client'
    assert 'idp_domain' not in kwargs


@pytest.mark.parametrize('no_browser', [False, True])
def test_no_browser_reaches_the_sign_in(auth_env, flow, no_browser):
    _connect(_args(no_browser=no_browser))
    kwargs = flow.provider.authenticate.call_args.kwargs
    assert kwargs['open_browser'] is not no_browser


def test_region_is_required_before_anything_else(auth_env, flow):
    session = _cli_session(region=None)
    with pytest.raises(AgentRegistryJWTError) as e:
        _connect(_args(), _globals(region=None), session)
    assert str(e.value) == (
        'A region is required. Pass --region or configure a default region.'
    )
    flow.endpoint.assert_not_called()
    flow.load.assert_not_called()
    session.create_client.assert_not_called()


def test_the_setup_redacts_logs_and_history(auth_env, flow):
    with patch.object(dataplane, 'redact_logs_and_history') as redact:
        _connect(_args(authorizer=None))
    redact.assert_called_once_with()


# --- A token that is already set ------------------------------------------


def test_preset_token_is_sent_as_is(auth_env, flow, monkeypatch):
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
    monkeypatch.setenv(PREFERENCE_ENV_VAR, 'sigv4')
    session = _cli_session()
    data_plane = _connect(session=session)
    assert os.environ[constants.TOKEN_ENV_VAR] == 'minted-out-of-band'
    # Left as it is: the client's config selects the bearer scheme.
    assert os.environ[PREFERENCE_ENV_VAR] == 'sigv4'
    config = session.create_client.call_args.kwargs['config']
    assert config.auth_scheme_preference == 'httpBearerAuth'
    # Still resolved, https only: the call goes there with the token.
    assert flow.endpoint.call_args.kwargs == {'https_only': True}
    assert data_plane.endpoint == ENDPOINT
    flow.load.assert_not_called()
    flow.discover.assert_not_called()
    flow.provider.authenticate.assert_not_called()


def test_preset_token_is_redacted(auth_env, flow, monkeypatch):
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
    with patch.object(providers, 'redact_logs_and_history') as redact:
        _connect()
    redact.assert_called_once_with('minted-out-of-band')


def test_preset_token_still_refuses_no_verify_ssl(auth_env, flow, monkeypatch):
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
    session = _cli_session()
    with pytest.raises(AgentRegistryJWTError, match='--ca-bundle'):
        _connect(_args(), _globals(verify_ssl=False), session)
    session.create_client.assert_not_called()


def test_empty_preset_token_signs_in(auth_env, flow, monkeypatch):
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, '')
    _connect()
    flow.load.assert_called_once()
    assert os.environ[constants.TOKEN_ENV_VAR] == 'signed-in-token'


def test_preset_token_is_never_sent_over_plain_http(monkeypatch):
    # The before-send guard checks the outgoing request, however the token
    # got there.
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
    request = Mock(url='http://registry.example/x')
    request.headers = {'Authorization': b'Bearer minted-out-of-band'}
    with pytest.raises(AgentRegistryJWTError, match='only https'):
        agentregistry.reject_bearer_over_plain_http(request)


@pytest.mark.parametrize('cached', [True, False])
def test_cached_and_new_sign_ins_select_bearer_in_the_client_config(
    auth_env, flow, monkeypatch, cached
):
    monkeypatch.setenv(PREFERENCE_ENV_VAR, 'sigv4')
    if cached:
        flow.load.return_value = make_jwt()
    session = _cli_session()
    _connect(session=session)
    assert flow.provider.authenticate.called is not cached
    assert os.environ[PREFERENCE_ENV_VAR] == 'sigv4'
    config = session.create_client.call_args.kwargs['config']
    assert config.auth_scheme_preference == 'httpBearerAuth'


def test_arn_and_id_share_one_sign_in(auth_env, flow):
    session = _cli_session()
    _connect(_args(registry_id=REGISTRY_ARN), session=session)
    by_arn = (flow.load.call_args, flow.discover.call_args)
    flow.load.reset_mock()
    flow.discover.reset_mock()
    # The first call exported its token, which would now count as pre-set.
    del os.environ[constants.TOKEN_ENV_VAR]
    _connect(_args(registry_id=REGISTRY_ID), session=session)
    by_id = (flow.load.call_args, flow.discover.call_args)
    assert by_arn == by_id
    # The cache key, the metadata path and the token's registry are the id.
    assert flow.load.call_args.args[1] == REGISTRY_ID
    assert flow.discover.call_args.args[1] == REGISTRY_ID
    authenticate = flow.provider.authenticate.call_args.kwargs
    assert authenticate['registry_id'] == REGISTRY_ID


def test_malformed_registry_id_is_refused_before_sign_in(auth_env, flow):
    session = _cli_session()
    with pytest.raises(AgentRegistryJWTError, match='registry identifier'):
        _connect(_args(registry_id='../../evil'), session=session)
    flow.load.assert_not_called()
    flow.discover.assert_not_called()
    session.create_client.assert_not_called()


def test_no_verify_ssl_is_refused_before_sign_in(auth_env, flow):
    with pytest.raises(AgentRegistryJWTError) as e:
        _connect(_args(), _globals(verify_ssl=False))
    assert str(e.value) == (
        "TLS verification can't be disabled with --authorizer JWT: unlike a "
        'SigV4 signature, the bearer token can be replayed by anything that '
        'intercepts the connection. If you use a TLS-inspecting proxy, trust '
        'its certificate authority with --ca-bundle instead.'
    )
    flow.endpoint.assert_not_called()
    flow.load.assert_not_called()
    flow.discover.assert_not_called()
    assert constants.TOKEN_ENV_VAR not in os.environ


@pytest.mark.parametrize('verify_ssl', [None, True, '/corp.pem'])
def test_verified_tls_is_allowed(auth_env, flow, verify_ssl):
    _connect(_args(), _globals(verify_ssl=verify_ssl))
    assert os.environ[constants.TOKEN_ENV_VAR] == 'signed-in-token'


@pytest.mark.parametrize('authorizer', [None, 'SIGV4'])
def test_no_verify_ssl_without_jwt_is_left_alone(auth_env, flow, authorizer):
    session = _cli_session()
    _connect(_args(authorizer=authorizer), _globals(verify_ssl=False), session)
    flow.load.assert_not_called()
    assert session.create_client.call_args.kwargs['verify'] is False


BEARER_TLS_MESSAGE = (
    "TLS verification can't be disabled for a request signed with a bearer "
    'token, from AWS_BEARER_TOKEN_AGENT_REGISTRY or an IAM Identity Center '
    'sign-in: unlike a SigV4 signature, the bearer token can be replayed by '
    'anything that intercepts the connection. Drop --no-verify-ssl, or, if '
    'you use a TLS-inspecting proxy, trust its certificate authority with '
    '--ca-bundle instead. To sign with SigV4, do not select httpBearerAuth '
    'in AWS_AUTH_SCHEME_PREFERENCE or auth_scheme_preference.'
)


def _armed(client):
    """Whether the bearer check, and only it, is on ``client``'s events."""
    registered = [
        (call.args, call.kwargs)
        for call in client.meta.events.register.call_args_list
    ]
    return registered == [
        (
            ('before-sign.agent-registry', utils.refuse_bearer_signature),
            {'unique_id': ANY},
        )
    ]


@pytest.mark.parametrize('authorizer', [None, 'SIGV4'])
@pytest.mark.parametrize('token', [None, 'minted-out-of-band'])
def test_without_jwt_no_verify_ssl_arms_the_bearer_check(
    auth_env, flow, monkeypatch, authorizer, token
):
    # botocore sends a token itself when it selects the bearer scheme, with a
    # token from the environment or an IAM Identity Center sign-in, so the
    # client refuses to sign with one over unverified TLS. Only botocore's
    # choice of signer tells, so nothing is refused yet.
    if token:
        monkeypatch.setenv(constants.TOKEN_ENV_VAR, token)
    session = _cli_session()
    _connect(_args(authorizer=authorizer), _globals(verify_ssl=False), session)
    assert session.create_client.call_args.kwargs['verify'] is False
    assert _armed(session.create_client.return_value)
    flow.load.assert_not_called()


@pytest.mark.parametrize('authorizer', [None, 'SIGV4'])
@pytest.mark.parametrize('verify_ssl', [None, True, '/corp.pem'])
def test_preset_token_without_jwt_allows_verified_tls(
    auth_env, flow, monkeypatch, authorizer, verify_ssl
):
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
    session = _cli_session()
    _connect(
        _args(authorizer=authorizer), _globals(verify_ssl=verify_ssl), session
    )
    assert session.create_client.call_args.kwargs['verify'] == verify_ssl
    # Still a SigV4 client as botocore would create it.
    assert session.create_client.call_args.kwargs['config'] is None
    client = session.create_client.return_value
    client.meta.events.register.assert_not_called()
    flow.load.assert_not_called()


def test_the_bearer_check_refuses_only_a_bearer_signature():
    with pytest.raises(AgentRegistryJWTError) as e:
        utils.refuse_bearer_signature(signature_version='bearer')
    assert str(e.value) == BEARER_TLS_MESSAGE
    for signature_version in ('v4', 's3v4', botocore.UNSIGNED, None):
        utils.refuse_bearer_signature(signature_version=signature_version)


@pytest.mark.parametrize('verify_ssl', [None, True, '/corp.pem'])
def test_the_bearer_check_is_armed_only_without_verification(verify_ssl):
    events = Mock()
    utils.arm_unverified_tls_check(events, _globals(verify_ssl=verify_ssl))
    events.register.assert_not_called()


def test_the_bearer_check_is_registered_once_however_often_it_is_armed():
    emitter = HierarchicalEmitter()
    with patch.object(utils, 'refuse_bearer_signature') as check:
        for _ in range(3):
            utils.arm_unverified_tls_check(emitter, _globals(verify_ssl=False))
    emitter.emit('before-sign.agent-registry.Op', signature_version='v4')
    check.assert_called_once_with(signature_version='v4', event_name=ANY)
    # Only this service's requests.
    emitter.emit('before-sign.agent-registry-control.Op')
    emitter.emit('before-sign.s3.Op')
    check.assert_called_once()


def test_empty_preset_token_without_jwt_honors_no_verify_ssl(
    auth_env, flow, monkeypatch
):
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, '')
    session = _cli_session()
    _connect(_args(authorizer=None), _globals(verify_ssl=False), session)
    assert session.create_client.call_args.kwargs['verify'] is False


def test_jwt_with_a_preset_token_keeps_the_jwt_message(
    auth_env, flow, monkeypatch
):
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
    with pytest.raises(AgentRegistryJWTError) as e:
        _connect(_args(), _globals(verify_ssl=False))
    assert str(e.value).startswith(
        "TLS verification can't be disabled with --authorizer JWT: "
    )


@pytest.mark.parametrize(
    'flag,configured,expected',
    [
        ('/flag.pem', '/config.pem', '/flag.pem'),
        (None, '/config.pem', '/config.pem'),
        (None, None, None),
    ],
)
def test_ca_bundle_reaches_every_https_call(
    auth_env, flow, flag, configured, expected
):
    data_plane = _connect(
        _args(),
        _globals(ca_bundle=flag),
        _cli_session(ca_bundle=configured),
    )
    assert flow.load.call_args.kwargs['ca_bundle'] == expected
    assert flow.discover.call_args.kwargs['ca_bundle'] == expected
    kwargs = flow.provider.authenticate.call_args.kwargs
    assert kwargs['ca_bundle'] == expected
    assert 'idp_audience' not in kwargs
    assert data_plane.ca_bundle == expected


def test_cached_token_skips_sign_in(auth_env, flow):
    token = make_jwt()
    flow.load.return_value = token
    _connect()
    flow.discover.assert_not_called()
    assert os.environ[constants.TOKEN_ENV_VAR] == token


# --- Scopes the registry advertises ----------------------------------------


@pytest.mark.parametrize(
    'advertised', [[], ['registry:read'], ['registry:read', 'registry:write']]
)
def test_advertised_scopes_are_requested_at_sign_in(
    auth_env, flow, advertised
):
    flow.discover.return_value = utils.RegistryAuthorization(
        'https://idp.example.com', advertised
    )
    _connect()
    kwargs = flow.provider.authenticate.call_args.kwargs
    assert kwargs['extra_scopes'] == advertised
    assert 'scopes' not in flow.load.call_args.kwargs


@pytest.mark.parametrize(
    'document,requested',
    [
        # Present: the defaults and the advertised scopes.
        (
            {'scopes_supported': ['registry:read', 'openid']},
            ['openid', 'registry:read'],
        ),
        # Absent, or unusable: the defaults only, exactly as before.
        ({}, ['openid']),
        ({'scopes_supported': 'registry:read'}, ['openid']),
        ({'scopes_supported': ['registry:read', 7]}, ['openid']),
        ({'scopes_supported': ['bad scope']}, ['openid']),
        ({'scopes_supported': [f's{n}' for n in range(51)]}, ['openid']),
    ],
    ids=['present', 'absent', 'string', 'non-string', 'invalid', 'too-many'],
)
def test_advertised_scopes_from_metadata_to_the_sign_in_and_the_cache(
    auth_env, document, requested
):
    # Real discovery, provider and cache; only the HTTP and browser are not.
    metadata = dict(
        document, authorization_servers=['https://idp.example.com']
    )
    oidc = {
        'issuer': 'https://idp.example.com',
        'authorization_endpoint': 'https://idp.example.com/authorize',
        'token_endpoint': 'https://idp.example.com/token',
    }
    token = make_jwt()
    with (
        patch.object(
            dataplane, 'resolve_data_plane_endpoint', return_value=ENDPOINT
        ),
        patch.object(
            utils,
            'http_get_json',
            side_effect=lambda url, **kwargs: (
                metadata if 'oauth-protected-resource' in url else oidc
            ),
        ),
        patch.object(
            providers,
            'run_browser_login',
            return_value={'access_token': token},
        ) as login,
    ):
        _connect()
    assert login.call_args.kwargs['scopes'] == requested
    assert login.call_args.kwargs['open_browser'] is True
    entry = cache.read_entry(ENDPOINT, REGISTRY_ID)
    assert entry['scopes'] == requested
    assert os.environ[constants.TOKEN_ENV_VAR] == token


# --- Pre-set token note -----------------------------------------------------

PRESET_NOTE = (
    'Using the token in AWS_BEARER_TOKEN_AGENT_REGISTRY; the cached '
    'sign-in, --client-id and --no-browser are not used.'
)


def test_preset_token_says_what_it_replaces(
    auth_env, flow, monkeypatch, capsys
):
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
    _connect()
    assert capsys.readouterr().err.strip() == PRESET_NOTE
    flow.load.assert_not_called()


def test_signed_in_token_prints_no_preset_note(auth_env, flow, capsys):
    flow.load.return_value = make_jwt()
    _connect()
    assert 'AWS_BEARER_TOKEN_AGENT_REGISTRY' not in capsys.readouterr().err


def test_preset_note_names_the_commands_sign_in_arguments(capsys):
    utils.note_preset_token(('--client-id',))
    utils.note_preset_token()
    utils.note_preset_token(('--a', '--b'))
    lines = capsys.readouterr().err.splitlines()
    assert lines == [
        'Using the token in AWS_BEARER_TOKEN_AGENT_REGISTRY; the cached '
        'sign-in and --client-id are not used.',
        'Using the token in AWS_BEARER_TOKEN_AGENT_REGISTRY; the cached '
        'sign-in is not used.',
        'Using the token in AWS_BEARER_TOKEN_AGENT_REGISTRY; the cached '
        'sign-in, --a and --b are not used.',
    ]


# --- 401 hint ---------------------------------------------------------------

SIGN_OUT_HINT = (
    "If the registry's sign-in settings changed, run: aws agent-registry "
    f'sign-out --registry-id {REGISTRY_ID}'
)


def _after_call(emitter, status, operation='ListDiscoverableRegistryRecords'):
    return emitter.emit(
        f'after-call.agent-registry.{operation}',
        http_response=Mock(status_code=status),
        parsed={},
        model=Mock(),
        context={},
    )


def test_the_hint_is_registered_for_the_data_plane_operations():
    cli = Mock()
    agentregistry.initialize(cli)
    events = {call.args[0] for call in cli.register.call_args_list}
    for operation in constants.DATA_PLANE_API_OPERATIONS:
        assert f'after-call.agent-registry.{operation}' in events


@pytest.mark.parametrize('operation', constants.DATA_PLANE_API_OPERATIONS)
def test_401_after_a_cached_sign_in_prints_the_sign_out_hint_once(
    auth_env, flow, capsys, operation
):
    emitter = HierarchicalEmitter()
    agentregistry.initialize(emitter)
    _connect(_args(registry_id=REGISTRY_ARN))
    capsys.readouterr()
    responses = _after_call(emitter, 401, operation)
    _after_call(emitter, 401, operation)
    # The error itself is left alone.
    assert [response for _, response in responses] == [None]
    assert capsys.readouterr().err.strip() == SIGN_OUT_HINT


@pytest.mark.parametrize('status', [200, 400, 403, 500])
def test_other_statuses_print_no_hint(auth_env, flow, capsys, status):
    emitter = HierarchicalEmitter()
    agentregistry.initialize(emitter)
    _connect()
    capsys.readouterr()
    _after_call(emitter, status)
    assert capsys.readouterr().err == ''


@pytest.mark.parametrize('authorizer', [None, 'SIGV4', 'preset'])
def test_no_hint_without_a_cached_sign_in(
    auth_env, flow, capsys, monkeypatch, authorizer
):
    emitter = HierarchicalEmitter()
    agentregistry.initialize(emitter)
    if authorizer == 'preset':
        # sign-out would not help: nothing is cached.
        monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
        authorizer = 'JWT'
    _connect(_args(authorizer=authorizer))
    capsys.readouterr()
    _after_call(emitter, 401)
    assert capsys.readouterr().err == ''


# --- Client id from the previous sign-in ------------------------------------

_REAL_LOAD_TOKEN = cache.load_token


def _previous_sign_in(issuer='https://idp.example.com', **kwargs):
    kwargs.setdefault('client_id', 'cached-client')
    kwargs.setdefault('token', make_jwt())
    kwargs.setdefault('expires_in', 3600)
    cache.save_token(
        ENDPOINT,
        REGISTRY_ID,
        refresh_token='rt',
        issuer=issuer,
        pool_region='us-west-2',
        **kwargs,
    )


def test_newly_advertised_scope_at_refresh_signs_in_with_the_same_client(
    auth_env, flow, capsys
):
    # Expired, and the registry now advertises a scope it lacks.
    _previous_sign_in(token=make_jwt(exp=1), expires_in=1, scopes=['openid'])
    advertised = utils.RegistryAuthorization(
        'https://idp.example.com', ['registry:read']
    )
    flow.discover.return_value = advertised
    # The real lookup, with the same metadata at the pre-refresh check.
    flow.load.side_effect = _REAL_LOAD_TOKEN
    with (
        patch.object(cache, 'discover_registry', return_value=advertised),
        patch.object(cache, '_refresh') as refresh,
    ):
        _connect(_args(client_id=None))
    refresh.assert_not_called()
    kwargs = flow.provider.authenticate.call_args.kwargs
    assert kwargs['client_id'] == 'cached-client'
    assert kwargs['extra_scopes'] == ['registry:read']
    err = capsys.readouterr().err
    assert (
        "The registry now asks for scopes the cached sign-in doesn't have; "
        'signing in again.'
    ) in err
    assert 'Using client id cached-client from the previous sign-in.' in err


def _refresh_failing_with(flow, error):
    """Run the setup with an expired sign-in whose refresh raises."""
    _previous_sign_in(token=make_jwt(exp=1), expires_in=1)
    flow.load.side_effect = _REAL_LOAD_TOKEN
    with patch.object(cache, '_refresh', side_effect=error):
        _connect(_args(client_id=None))


def test_refresh_that_fails_for_now_does_not_start_a_sign_in(auth_env, flow):
    error = ClientError(
        {'Error': {'Code': 'TooManyRequestsException', 'Message': 'Slow'}},
        'GetTokensFromRefreshToken',
    )
    with pytest.raises(AgentRegistryJWTError, match='Try again'):
        _refresh_failing_with(flow, error)
    flow.provider.authenticate.assert_not_called()
    assert constants.TOKEN_ENV_VAR not in os.environ


def test_refresh_token_the_provider_rejects_starts_a_sign_in(auth_env, flow):
    error = ClientError(
        {'Error': {'Code': 'NotAuthorizedException', 'Message': 'Revoked'}},
        'GetTokensFromRefreshToken',
    )
    _refresh_failing_with(flow, error)
    kwargs = flow.provider.authenticate.call_args.kwargs
    assert kwargs['client_id'] == 'cached-client'
    assert os.environ[constants.TOKEN_ENV_VAR] == 'signed-in-token'


@pytest.mark.parametrize(
    'issuer', ['https://idp.example.com', 'https://idp.example.com/']
)
def test_the_client_id_is_reused_for_the_same_issuer(auth_env, flow, issuer):
    _previous_sign_in(issuer=issuer)
    _connect(_args(client_id=None))
    assert flow.provider.authenticate.call_args.kwargs['client_id'] == (
        'cached-client'
    )


def test_the_client_id_is_not_reused_when_the_issuer_changed(
    auth_env, flow, capsys
):
    # The registry now trusts https://idp.example.com (see the flow fixture).
    _previous_sign_in(issuer='https://old-idp.example.com')
    _connect(_args(client_id=None))
    # Left to the provider, which prompts or explains, as without a cache.
    assert flow.provider.authenticate.call_args.kwargs['client_id'] is None
    assert 'from the previous sign-in' not in capsys.readouterr().err


@pytest.mark.parametrize('kwargs', [{'client_id': None}, {'client_id': ''}])
def test_an_entry_without_a_client_id_offers_none(auth_env, flow, kwargs):
    _previous_sign_in(**kwargs)
    _connect(_args(client_id=None))
    assert flow.provider.authenticate.call_args.kwargs['client_id'] is None


def test_an_explicit_client_id_wins(auth_env, flow, capsys):
    _previous_sign_in()
    _connect(_args(client_id='explicit-client'))
    assert flow.provider.authenticate.call_args.kwargs['client_id'] == (
        'explicit-client'
    )
    assert 'from the previous sign-in' not in capsys.readouterr().err


# --- Generated data plane commands ------------------------------------------


def test_generated_commands_get_only_redaction_and_the_guards():
    cli = Mock()
    agentregistry.initialize(cli)
    registered = [
        (call.args[0], call.args[1]) for call in cli.register.call_args_list
    ]
    assert not [
        event for event, _ in registered if 'building-argument-table' in event
    ]
    assert not [
        event for event, _ in registered if 'operation-args-parsed' in event
    ]
    calling = [
        (event, handler)
        for event, handler in registered
        if event.startswith('calling-command')
    ]
    [(arm_event, arm), *per_operation] = calling
    # The TLS check is armed for every operation of the service, on the
    # emitter the command's client copies.
    assert arm_event == 'calling-command.agent-registry'
    assert arm.func is agentregistry.arm_unverified_tls_check_on_command
    assert arm.args == (cli,)
    assert per_operation == [
        (
            f'calling-command.agent-registry.{operation}',
            agentregistry.redact_data_plane_call,
        )
        for operation in (LIST, SEARCH, BATCH_GET)
    ]
    assert (
        'before-send.agent-registry',
        agentregistry.reject_bearer_over_plain_http,
    ) in registered


@pytest.mark.parametrize('verify_ssl', [None, False])
def test_redaction_hook_never_overrides_the_command(monkeypatch, verify_ssl):
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
    emitter = HierarchicalEmitter()
    agentregistry.initialize(emitter)
    with (
        patch.object(agentregistry, 'redact_logs_and_history') as redact,
        patch.object(providers, 'sign_in') as sign_in,
        patch.object(cache, 'load_token') as load,
    ):
        for operation in (LIST, SEARCH, BATCH_GET):
            handler, response = emitter.emit_until_response(
                f'calling-command.agent-registry.{operation}',
                call_parameters={'registryId': REGISTRY_ID},
                parsed_args=argparse.Namespace(),
                parsed_globals=_globals(verify_ssl=verify_ssl),
            )
            # A non-None response would replace the API call.
            assert response is None
    assert redact.call_count == 3
    redact.assert_called_with('minted-out-of-band')
    sign_in.assert_not_called()
    load.assert_not_called()


@pytest.mark.parametrize('verify_ssl', [None, True, '/corp.pem', False])
def test_generated_commands_arm_the_bearer_check_only_without_verification(
    monkeypatch, verify_ssl
):
    monkeypatch.delenv(constants.TOKEN_ENV_VAR, raising=False)
    emitter = HierarchicalEmitter()
    agentregistry.initialize(emitter)
    with patch.object(agentregistry, 'redact_logs_and_history'):
        emitter.emit(
            f'calling-command.agent-registry.{LIST}',
            call_parameters={'registryId': REGISTRY_ID},
            parsed_args=argparse.Namespace(),
            parsed_globals=_globals(verify_ssl=verify_ssl),
        )
    before_sign = f'before-sign.agent-registry.{LIST}'
    # SigV4 is never refused.
    emitter.emit(before_sign, signature_version='v4')
    if verify_ssl is False:
        with pytest.raises(AgentRegistryJWTError, match='bearer token'):
            emitter.emit(before_sign, signature_version='bearer')
    else:
        emitter.emit(before_sign, signature_version='bearer')


@pytest.mark.parametrize('verify_ssl', [None, False])
def test_an_operation_a_model_overlay_adds_is_armed_too(
    monkeypatch, verify_ssl
):
    monkeypatch.delenv(constants.TOKEN_ENV_VAR, raising=False)
    operation = 'some-new-operation'
    assert operation not in constants.DATA_PLANE_OPERATIONS
    emitter = HierarchicalEmitter()
    agentregistry.initialize(emitter)
    _, response = emitter.emit_until_response(
        f'calling-command.agent-registry.{operation}',
        call_parameters={},
        parsed_args=argparse.Namespace(),
        parsed_globals=_globals(verify_ssl=verify_ssl),
    )
    # Never overrides the command.
    assert response is None
    before_sign = 'before-sign.agent-registry.SomeNewOperation'
    emitter.emit(before_sign, signature_version='v4')
    if verify_ssl is False:
        with pytest.raises(AgentRegistryJWTError, match='bearer token'):
            emitter.emit(before_sign, signature_version='bearer')
    else:
        emitter.emit(before_sign, signature_version='bearer')


def test_redaction_hook_without_a_preset_token(monkeypatch):
    monkeypatch.delenv(constants.TOKEN_ENV_VAR, raising=False)
    with patch.object(agentregistry, 'redact_logs_and_history') as redact:
        agentregistry.redact_data_plane_call()
    # Presigned URLs and anything that looks like a token are still removed.
    redact.assert_called_once_with(None)


def test_initialize_runs_once_however_often_its_events_fire():
    from awscli.handlers_registry import PLUGIN_REGISTRY
    from awscli.lazy_emitter import LazyInitEmitter

    entry = ('awscli.customizations.agentregistry', 'initialize')
    # The registry's real entries for this customization. The other plugins
    # matching these events need real command and argument objects.
    registry = {
        event: [entry]
        for event, entries in PLUGIN_REGISTRY.items()
        if entry in [tuple(item) for item in entries]
    }
    assert set(registry) == {
        'building-command-table.agent-registry',
        'building-argument-table.agent-registry',
        'calling-command.agent-registry',
    }
    emitter = LazyInitEmitter(plugin_registry=registry)
    with (
        patch.object(
            agentregistry, 'initialize', wraps=agentregistry.initialize
        ) as initialize,
        patch.object(agentregistry, 'redact_logs_and_history') as redact,
    ):
        for round_ in range(3):
            command_table = {}
            emitter.emit(
                'building-command-table.agent-registry',
                command_table=command_table,
                session=Mock(),
            )
            assert set(command_table) == {
                'list-skills',
                'install-skill',
                'uninstall-skill',
                'sign-out',
            }
            for operation in (LIST, SEARCH, BATCH_GET):
                argument_table = {}
                emitter.emit(
                    f'building-argument-table.agent-registry.{operation}',
                    argument_table=argument_table,
                    session=Mock(),
                    command=Mock(),
                    operation_model=Mock(),
                )
                # No --authorizer or --client-id.
                assert argument_table == {}
                calls = redact.call_count
                emitter.emit(
                    f'calling-command.agent-registry.{operation}',
                    call_parameters={'registryId': REGISTRY_ID},
                    parsed_args=argparse.Namespace(),
                    parsed_globals=_globals(),
                )
                # One redaction per call, not one per registration.
                assert redact.call_count == calls + 1
    initialize.assert_called_once_with(emitter)
    assert redact.call_count == 9


def _driver(monkeypatch, *data_paths):
    """A real CLI driver that loads only the models shipped with the CLI,
    and any in ``data_paths`` first."""
    from awscli.clidriver import create_clidriver

    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-west-2')
    driver = create_clidriver()
    session = driver.session
    data_path = session.get_config_variable('data_path').split(os.pathsep)
    session.register_component(
        'data_loader',
        botocore.loaders.Loader(
            extra_search_paths=[
                *data_paths,
                *data_path,
                botocore.loaders.Loader.BUILTIN_DATA_PATH,
            ],
            include_default_search_paths=False,
        ),
    )
    return driver


@pytest.mark.parametrize('name', ['list-available-skills', 'remove-skill'])
def test_old_skill_command_names_are_unknown(
    config_file, auth_env, monkeypatch, capsys, name
):
    # Renamed to list-skills and uninstall-skill before release, with no
    # aliases. agent-toolkit's commands of these names are its own.
    rc = _driver(monkeypatch).main(['agent-registry', name])
    assert rc == 252
    assert f"Found invalid choice '{name}'" in capsys.readouterr().err


@pytest.mark.parametrize(
    'name,required',
    [('list-skills', '--registry-id'), ('uninstall-skill', '--name')],
)
def test_skill_commands_are_in_the_command_table(
    config_file, auth_env, monkeypatch, capsys, name, required
):
    # The command's own parser rejects the missing argument, so the name
    # was found.
    rc = _driver(monkeypatch).main(['agent-registry', name])
    assert rc == 252
    err = capsys.readouterr().err
    assert 'invalid choice' not in err
    assert f'the following arguments are required: {required}' in err


def test_install_skill_takes_record_name_and_not_name(
    config_file, auth_env, monkeypatch, capsys
):
    # uninstall-skill --name is the installed skill's name, so install-skill
    # names a record by --record-name, and has no --name.
    from awscli.customizations.agentregistry.install_skill import (
        InstallSkillCommand,
    )

    argv = ['agent-registry', 'install-skill', '--registry-id', REGISTRY_ID]
    with patch.object(InstallSkillCommand, '_run_main', return_value=0) as run:
        rc = _driver(monkeypatch).main([*argv, '--record-name', 'pdf-extract'])
        assert rc == 0
        assert run.call_args.args[0].record_name == 'pdf-extract'
        rc = _driver(monkeypatch).main([*argv, '--name', 'pdf-extract'])
    assert rc == 252
    assert 'Unknown options: --name' in capsys.readouterr().err
    run.assert_called_once()


def test_uninstall_skill_still_takes_name(config_file, auth_env, monkeypatch):
    from awscli.customizations.agentregistry.uninstall_skill import (
        UninstallSkillCommand,
    )

    with patch.object(
        UninstallSkillCommand, '_run_main', return_value=0
    ) as run:
        rc = _driver(monkeypatch).main(
            ['agent-registry', 'uninstall-skill', '--name', 'pdf-extract']
        )
    assert rc == 0
    assert run.call_args.args[0].name == 'pdf-extract'


GENERATED_COMMAND_LINES = [
    [LIST, '--registry-id', REGISTRY_ID],
    [SEARCH, '--search-query', 'q', '--registry-ids', REGISTRY_ID],
    [BATCH_GET, '--entries', f'registryId={REGISTRY_ID},recordIds=rec'],
]


@pytest.mark.parametrize('argv', GENERATED_COMMAND_LINES)
@pytest.mark.parametrize(
    'argument', [['--authorizer', 'JWT'], ['--client-id', 'c']]
)
def test_generated_commands_have_no_sign_in_arguments(
    config_file, auth_env, monkeypatch, capsys, argv, argument
):
    from awscli.clidriver import CLIOperationCaller

    driver = _driver(monkeypatch)
    with patch.object(CLIOperationCaller, 'invoke', return_value=0) as invoke:
        rc = driver.main(['agent-registry', *argv, *argument])
    assert rc == 252
    assert f'Unknown options: {", ".join(argument)}' in capsys.readouterr().err
    invoke.assert_not_called()


@pytest.mark.parametrize('argv', GENERATED_COMMAND_LINES)
def test_generated_commands_never_sign_in(
    config_file, auth_env, monkeypatch, argv
):
    from awscli.clidriver import CLIOperationCaller

    driver = _driver(monkeypatch)
    with (
        patch.object(cache, 'load_token') as load,
        patch.object(providers, 'sign_in') as sign_in,
        patch.object(CLIOperationCaller, 'invoke', return_value=0) as invoke,
    ):
        rc = driver.main(['agent-registry', *argv])
    assert rc == 0
    invoke.assert_called_once()
    load.assert_not_called()
    sign_in.assert_not_called()
    assert constants.TOKEN_ENV_VAR not in os.environ
    assert PREFERENCE_ENV_VAR not in os.environ


@pytest.mark.parametrize('value', ['input', 'yaml-input', 'output'])
def test_generate_cli_skeleton_on_a_generated_command(
    config_file, auth_env, monkeypatch, capsys, value
):
    from awscli.customizations.generatecliskeleton import (
        StubbedCLIOperationCaller,
    )

    argv = ['agent-registry', LIST]
    if value == 'output':
        # Output skeletons still validate the command's arguments.
        argv += ['--registry-id', REGISTRY_ID]
    driver = _driver(monkeypatch)
    with (
        patch.object(cache, 'load_token') as load,
        patch.object(
            StubbedCLIOperationCaller, 'invoke', return_value=0
        ) as stubbed,
    ):
        rc = driver.main([*argv, '--generate-cli-skeleton', value])
    assert rc == 0
    load.assert_not_called()
    if value == 'output':
        stubbed.assert_called_once()
    else:
        assert 'registryId' in capsys.readouterr().out


class _Body:
    def stream(self):
        yield b'{"registryRecords": []}'


def _model_with_auth(tmp_path, auth):
    """A data path with a copy of the bundled model that declares ``auth``.

    For the service, with no operation declaring its own, so the result does
    not depend on which auth schemes the bundled model declares.
    """
    source = MODEL_PATH.parent
    target = tmp_path / 'models' / 'agent-registry' / source.name
    shutil.copytree(source, target)
    model = json.loads(MODEL_PATH.read_text())
    model['metadata']['auth'] = auth
    for operation in model['operations'].values():
        operation.pop('auth', None)
    (target / 'service-2.json').write_text(json.dumps(model))
    return str(tmp_path / 'models')


@pytest.fixture
def bearer_capable_model(tmp_path):
    """The bundled model, declaring the bearer scheme after SigV4.

    As the model overlays for CUSTOM_JWT registries do.
    """
    return _model_with_auth(
        tmp_path, ['aws.auth#sigv4', 'smithy.api#httpBearerAuth']
    )


@pytest.fixture
def sigv4_only_model(tmp_path):
    """The bundled model, declaring SigV4 only."""
    return _model_with_auth(tmp_path, ['aws.auth#sigv4'])


def _sent_authorization(monkeypatch, data_paths, argv=None):
    """Run a generated command; return the Authorization header it sent."""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'AKIDEXAMPLE')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'secret')
    driver = _driver(monkeypatch, *data_paths)
    sent = []

    def send(request):
        sent.append(request.headers.get('Authorization'))
        return AWSResponse(request.url, 200, {}, _Body())

    argv = argv or [LIST, '--registry-id', REGISTRY_ID]
    # Where the request would go on the wire, after every before-send hook.
    with patch.object(Endpoint, '_send', side_effect=send):
        rc = driver.main(['agent-registry', *argv])
    return rc, sent


@pytest.mark.parametrize('token', [None, 'minted-out-of-band'])
def test_generated_commands_sign_with_sigv4_by_default(
    config_file, auth_env, monkeypatch, bearer_capable_model, token
):
    # A token alone selects nothing: botocore prefers bearer auth on its own
    # only for an allowlist of services, and this customization adds none.
    if token:
        monkeypatch.setenv(constants.TOKEN_ENV_VAR, token)
    rc, sent = _sent_authorization(monkeypatch, [bearer_capable_model])
    assert rc == 0
    [authorization] = sent
    assert authorization.startswith(b'AWS4-HMAC-SHA256 ')


def test_generated_commands_send_a_token_the_caller_selects(
    config_file, auth_env, monkeypatch, bearer_capable_model
):
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
    monkeypatch.setenv(PREFERENCE_ENV_VAR, 'httpBearerAuth')
    rc, sent = _sent_authorization(monkeypatch, [bearer_capable_model])
    assert rc == 0
    assert sent == [b'Bearer minted-out-of-band']


def test_model_without_the_bearer_trait_signs_with_sigv4_whatever_is_set(
    config_file, auth_env, monkeypatch, sigv4_only_model
):
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
    monkeypatch.setenv(PREFERENCE_ENV_VAR, 'httpBearerAuth')
    rc, sent = _sent_authorization(monkeypatch, [sigv4_only_model])
    assert rc == 0
    [authorization] = sent
    assert authorization.startswith(b'AWS4-HMAC-SHA256 ')


def test_generated_commands_never_send_a_token_over_plain_http(
    config_file, auth_env, monkeypatch, capsys, bearer_capable_model
):
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
    monkeypatch.setenv(PREFERENCE_ENV_VAR, 'httpBearerAuth')
    rc, sent = _sent_authorization(
        monkeypatch,
        [bearer_capable_model],
        [
            LIST,
            '--registry-id',
            REGISTRY_ID,
            '--endpoint-url',
            'http://x.test',
        ],
    )
    assert rc != 0
    assert sent == []
    # botocore refuses a bearer token for an http endpoint itself; our
    # before-send guard is the backstop if it ever stops doing so.
    err = capsys.readouterr().err
    assert (
        'only https URLs are allowed' in err
        or 'Bearer authorization requires an HTTPS endpoint' in err
    )


def _run_generated(monkeypatch, data_paths, argv):
    """Run ``aws agent-registry <argv>``; return rc, Authorization headers
    sent, and whether the operation was invoked (a client was created)."""
    from awscli.clidriver import CLIOperationCaller

    original_invoke = CLIOperationCaller.invoke
    with patch.object(
        CLIOperationCaller,
        'invoke',
        autospec=True,
        side_effect=original_invoke,
    ) as invoke:
        rc, sent = _sent_authorization(monkeypatch, data_paths, argv)
    return rc, sent, invoke.called


SSO_TOKEN = 'idc-access-token-never-shown'


@pytest.fixture
def sso_session_profile(config_file, monkeypatch, tmp_path):
    """The default profile signs in with IAM Identity Center (sso_session).

    With a cached, unexpired access token where botocore's SSO token
    provider reads it, and no AWS_BEARER_TOKEN_AGENT_REGISTRY. Returns a
    function that appends lines to the profile.
    """
    cache_dir = tmp_path / 'sso-cache'
    cache_dir.mkdir()
    expires = datetime.datetime.now(datetime.timezone.utc) + (
        datetime.timedelta(hours=1)
    )
    token = {
        'startUrl': 'https://corp.awsapps.com/start',
        'region': 'us-east-1',
        'accessToken': SSO_TOKEN,
        'expiresAt': expires.strftime('%Y-%m-%dT%H:%M:%SZ'),
    }
    key = hashlib.sha1(b'corp').hexdigest()
    (cache_dir / f'{key}.json').write_text(json.dumps(token))
    monkeypatch.setattr(
        SSOTokenProvider, '_SSO_TOKEN_CACHE_DIR', str(cache_dir)
    )

    def write(*profile_lines):
        config_file.write_text(
            '\n'.join(
                [
                    '[default]',
                    'sso_session = corp',
                    *profile_lines,
                    '[sso-session corp]',
                    'sso_start_url = https://corp.awsapps.com/start',
                    'sso_region = us-east-1',
                    '',
                ]
            )
        )

    write()
    return write


def _prefer_bearer(monkeypatch, sso_session_profile, source):
    """Select the bearer scheme from the environment or the config file."""
    if source == 'env':
        monkeypatch.setenv(PREFERENCE_ENV_VAR, 'httpBearerAuth')
    else:
        sso_session_profile('auth_scheme_preference = httpBearerAuth')


@pytest.mark.parametrize('argv', GENERATED_COMMAND_LINES)
def test_generated_commands_refuse_no_verify_ssl_with_a_preset_token(
    config_file,
    auth_env,
    monkeypatch,
    capsys,
    bearer_capable_model,
    argv,
):
    # Talos e8c4b13a: the token, the bearer scheme selected, and no TLS
    # verification.
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
    monkeypatch.setenv(PREFERENCE_ENV_VAR, 'httpBearerAuth')
    rc, sent, invoked = _run_generated(
        monkeypatch, [bearer_capable_model], [*argv, '--no-verify-ssl']
    )
    assert rc == 255
    # Refused on before-sign, once botocore has chosen the bearer signer:
    # the client exists, the request is never sent.
    assert invoked
    assert sent == []
    out, err = capsys.readouterr()
    assert BEARER_TLS_MESSAGE in err
    assert 'minted-out-of-band' not in out + err


@pytest.mark.parametrize('source', ['env', 'config'])
@pytest.mark.parametrize('argv', GENERATED_COMMAND_LINES)
def test_generated_commands_refuse_no_verify_ssl_with_an_sso_token(
    auth_env,
    monkeypatch,
    capsys,
    bearer_capable_model,
    sso_session_profile,
    argv,
    source,
):
    _prefer_bearer(monkeypatch, sso_session_profile, source)
    rc, sent, invoked = _run_generated(
        monkeypatch, [bearer_capable_model], [*argv, '--no-verify-ssl']
    )
    assert rc == 255
    assert invoked
    assert sent == []
    out, err = capsys.readouterr()
    assert BEARER_TLS_MESSAGE in err
    assert SSO_TOKEN not in out + err


@pytest.mark.parametrize('source', ['env', 'config'])
@pytest.mark.parametrize('verification', ['default', 'ca-bundle'])
@pytest.mark.parametrize('argv', GENERATED_COMMAND_LINES)
def test_generated_commands_send_an_sso_token_over_verified_tls(
    auth_env,
    monkeypatch,
    tmp_path,
    bearer_capable_model,
    sso_session_profile,
    argv,
    verification,
    source,
):
    # What the refusal above prevents: botocore does send the IAM Identity
    # Center token when the bearer scheme is selected.
    _prefer_bearer(monkeypatch, sso_session_profile, source)
    if verification == 'ca-bundle':
        bundle = tmp_path / 'corporate.pem'
        shutil.copyfile(get_cert_path(True), bundle)
        argv = [*argv, '--ca-bundle', str(bundle)]
    rc, sent, invoked = _run_generated(
        monkeypatch, [bearer_capable_model], argv
    )
    assert rc == 0
    assert sent == [f'Bearer {SSO_TOKEN}'.encode()]


@pytest.mark.parametrize('preference', [None, 'sigv4,httpBearerAuth'])
@pytest.mark.parametrize('argv', GENERATED_COMMAND_LINES)
def test_generated_commands_sign_with_sigv4_over_unverified_tls_with_a_token(
    config_file,
    auth_env,
    monkeypatch,
    capsys,
    bearer_capable_model,
    argv,
    preference,
):
    # The token alone does not select the bearer scheme, so nothing it could
    # leak is sent, and the call is not refused.
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
    if preference:
        monkeypatch.setenv(PREFERENCE_ENV_VAR, preference)
    rc, sent, invoked = _run_generated(
        monkeypatch, [bearer_capable_model], [*argv, '--no-verify-ssl']
    )
    assert rc == 0
    assert invoked
    [authorization] = sent
    assert authorization.startswith(b'AWS4-HMAC-SHA256 ')
    assert "TLS verification can't be disabled" not in capsys.readouterr().err


@pytest.mark.parametrize('token', [None, ''])
@pytest.mark.parametrize('argv', GENERATED_COMMAND_LINES)
def test_generated_commands_without_a_token_honor_no_verify_ssl(
    config_file, auth_env, monkeypatch, bearer_capable_model, argv, token
):
    if token is not None:
        monkeypatch.setenv(constants.TOKEN_ENV_VAR, token)
    rc, sent, invoked = _run_generated(
        monkeypatch, [bearer_capable_model], [*argv, '--no-verify-ssl']
    )
    assert rc == 0
    assert invoked
    [authorization] = sent
    assert authorization.startswith(b'AWS4-HMAC-SHA256 ')


@pytest.mark.parametrize('verification', ['default', 'ca-bundle'])
@pytest.mark.parametrize('argv', GENERATED_COMMAND_LINES)
def test_generated_commands_send_a_preset_token_over_verified_tls(
    config_file,
    auth_env,
    monkeypatch,
    tmp_path,
    bearer_capable_model,
    argv,
    verification,
):
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
    monkeypatch.setenv(PREFERENCE_ENV_VAR, 'httpBearerAuth')
    if verification == 'ca-bundle':
        bundle = tmp_path / 'corporate.pem'
        shutil.copyfile(get_cert_path(True), bundle)
        argv = [*argv, '--ca-bundle', str(bundle)]
    rc, sent, invoked = _run_generated(
        monkeypatch, [bearer_capable_model], argv
    )
    assert rc == 0
    assert invoked
    assert sent == [b'Bearer minted-out-of-band']


def _skill_command_line(command, tmp_path):
    argv = [command, '--registry-id', REGISTRY_ID]
    if command == 'install-skill':
        target = tmp_path / 'skills'
        argv += ['--record-id', 'rec', '--target-directory', str(target)]
    return argv


@pytest.mark.parametrize('command', ['list-skills', 'install-skill'])
def test_skill_commands_without_jwt_refuse_no_verify_ssl_with_a_preset_token(
    config_file,
    auth_env,
    monkeypatch,
    capsys,
    tmp_path,
    bearer_capable_model,
    command,
):
    # Talos e8c4b13a, for the commands that create their own client.
    argv = _skill_command_line(command, tmp_path)
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
    monkeypatch.setenv(PREFERENCE_ENV_VAR, 'httpBearerAuth')
    with patch.object(utils, '_opener') as opener:
        rc, sent = _sent_authorization(
            monkeypatch, [bearer_capable_model], [*argv, '--no-verify-ssl']
        )
    assert rc == 255
    # Refused on before-sign: no request, and no other HTTP call.
    assert sent == []
    opener.assert_not_called()
    out, err = capsys.readouterr()
    assert BEARER_TLS_MESSAGE in err
    assert 'minted-out-of-band' not in out + err
    assert not (tmp_path / 'skills').exists()


@pytest.mark.parametrize('source', ['env', 'config'])
@pytest.mark.parametrize('command', ['list-skills', 'install-skill'])
def test_skill_commands_without_jwt_refuse_no_verify_ssl_with_an_sso_token(
    auth_env,
    monkeypatch,
    capsys,
    tmp_path,
    bearer_capable_model,
    sso_session_profile,
    command,
    source,
):
    argv = _skill_command_line(command, tmp_path)
    _prefer_bearer(monkeypatch, sso_session_profile, source)
    with patch.object(utils, '_opener') as opener:
        rc, sent = _sent_authorization(
            monkeypatch, [bearer_capable_model], [*argv, '--no-verify-ssl']
        )
    assert rc == 255
    assert sent == []
    opener.assert_not_called()
    out, err = capsys.readouterr()
    assert BEARER_TLS_MESSAGE in err
    assert SSO_TOKEN not in out + err
    assert not (tmp_path / 'skills').exists()


@pytest.mark.parametrize('command', ['list-skills', 'install-skill'])
def test_skill_commands_send_an_sso_token_over_verified_tls(
    auth_env,
    monkeypatch,
    tmp_path,
    bearer_capable_model,
    sso_session_profile,
    command,
):
    argv = _skill_command_line(command, tmp_path)
    monkeypatch.setenv(PREFERENCE_ENV_VAR, 'httpBearerAuth')
    with patch.object(utils, '_opener'):
        rc, sent = _sent_authorization(
            monkeypatch, [bearer_capable_model], argv
        )
    assert sent == [f'Bearer {SSO_TOKEN}'.encode()]
    if command == 'list-skills':
        assert rc == 0


@pytest.mark.parametrize('preference', [None, 'sigv4,httpBearerAuth'])
@pytest.mark.parametrize('command', ['list-skills', 'install-skill'])
def test_skill_commands_sign_with_sigv4_over_unverified_tls_with_a_token(
    config_file,
    auth_env,
    monkeypatch,
    capsys,
    tmp_path,
    bearer_capable_model,
    command,
    preference,
):
    argv = _skill_command_line(command, tmp_path)
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, 'minted-out-of-band')
    if preference:
        monkeypatch.setenv(PREFERENCE_ENV_VAR, preference)
    with patch.object(utils, '_opener'):
        rc, sent = _sent_authorization(
            monkeypatch, [bearer_capable_model], [*argv, '--no-verify-ssl']
        )
    [authorization] = sent
    assert authorization.startswith(b'AWS4-HMAC-SHA256 ')
    assert "TLS verification can't be disabled" not in capsys.readouterr().err
    if command == 'list-skills':
        assert rc == 0


@pytest.mark.parametrize('command', ['list-skills', 'install-skill'])
def test_skill_commands_with_jwt_refuse_no_verify_ssl_before_sign_in(
    config_file,
    auth_env,
    monkeypatch,
    capsys,
    tmp_path,
    bearer_capable_model,
    command,
):
    argv = _skill_command_line(command, tmp_path)
    with (
        patch.object(cache, 'load_token') as load,
        patch.object(providers, 'sign_in') as sign_in,
        patch.object(utils, '_opener') as opener,
    ):
        rc, sent = _sent_authorization(
            monkeypatch,
            [bearer_capable_model],
            [*argv, '--authorizer', 'JWT', '--no-verify-ssl'],
        )
    assert rc == 255
    assert sent == []
    load.assert_not_called()
    sign_in.assert_not_called()
    opener.assert_not_called()
    assert (
        "TLS verification can't be disabled with --authorizer JWT: "
    ) in capsys.readouterr().err


# --- The commands that sign in: bearer through the client's own config -----


def _bearer_capable_session(data_path):
    session = botocore.session.Session()
    session.register_component(
        'data_loader',
        botocore.loaders.Loader(
            extra_search_paths=[
                data_path,
                botocore.loaders.Loader.BUILTIN_DATA_PATH,
            ],
            include_default_search_paths=False,
        ),
    )
    return session


def _authorization_sent_by(client):
    """Make a data plane call; return the Authorization header it sent."""
    sent = []

    def send(request):
        sent.append(request.headers.get('Authorization'))
        return AWSResponse(request.url, 200, {}, _Body())

    with patch.object(URLLib3Session, 'send', side_effect=send):
        client.list_discoverable_registry_records(registryId=REGISTRY_ID)
    return sent


@pytest.mark.parametrize('source', ['preset', 'cached', 'new'])
def test_jwt_sends_the_bearer_token_with_only_the_client_config(
    config_file, auth_env, monkeypatch, bearer_capable_model, source
):
    # SigV4 credentials are there too, and nothing in the environment or the
    # config file asks for the bearer scheme.
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'AKIDEXAMPLE')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'secret')
    token = make_jwt()
    if source == 'preset':
        monkeypatch.setenv(constants.TOKEN_ENV_VAR, token)
    cached = token if source == 'cached' else None
    with (
        patch.object(cache, 'load_token', return_value=cached),
        patch.object(providers, 'sign_in', return_value=token) as sign_in,
    ):
        data_plane = dataplane.create_data_plane_client(
            _bearer_capable_session(bearer_capable_model), _args(), _globals()
        )
    assert sign_in.called is (source == 'new')
    assert PREFERENCE_ENV_VAR not in os.environ
    assert _authorization_sent_by(data_plane.client) == [
        f'Bearer {token}'.encode()
    ]


@pytest.mark.parametrize('source', ['profile', 'environment'])
def test_jwt_client_config_wins_over_a_sigv4_preference(
    config_file, auth_env, monkeypatch, bearer_capable_model, source
):
    if source == 'profile':
        config_file.write_text('[default]\nauth_scheme_preference = sigv4\n')
    else:
        monkeypatch.setenv(PREFERENCE_ENV_VAR, 'sigv4')
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'AKIDEXAMPLE')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'secret')
    token = make_jwt()
    session = _bearer_capable_session(bearer_capable_model)
    with patch.object(cache, 'load_token', return_value=token):
        data_plane = dataplane.create_data_plane_client(
            session, _args(), _globals()
        )
    assert _authorization_sent_by(data_plane.client) == [
        f'Bearer {token}'.encode()
    ]
    # Any other client still follows the preference, token or not.
    other = session.create_client('agent-registry', region_name='us-west-2')
    [authorization] = _authorization_sent_by(other)
    assert authorization.startswith(b'AWS4-HMAC-SHA256 ')
