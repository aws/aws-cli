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
"""Tokens and presigned URL credentials stay out of logs and CLI history."""

import argparse
import io
import json
import logging
import sqlite3
from unittest.mock import Mock, patch

import pytest
from botocore.awsrequest import AWSRequest
from botocore.history import BaseHistoryHandler

from awscli.customizations import agentregistry
from awscli.customizations.agentregistry import constants, providers, utils
from awscli.customizations.agentregistry.utils import (
    redact_logs_and_history,
    redact_secrets,
)
from awscli.customizations.history.db import (
    DatabaseConnection,
    DatabaseHistoryHandler,
    DatabaseRecordWriter,
    RecordBuilder,
)
from awscli.logger import remove_stream_logger, set_stream_logger
from tests.unit.customizations.agentregistry.utils import make_jwe, make_jwt

REGISTRY_ID = 'abcDEF123456'
# A fixed expiry: the token is part of test ids, which every xdist worker
# must collect identically.
ACCESS_TOKEN = make_jwt(sub='user', exp=2_000_000_000)
REFRESH_TOKEN = make_jwe()
OPAQUE_TOKEN = 'opaque-bearer-token-0123456789'
PRESIGNED = (
    'https://bucket.s3.us-west-2.amazonaws.com/skills/pkg.zip'
    '?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=ASIAEXAMPLE%2F2026'
    '&X-Amz-Date=20261019T000000Z&X-Amz-Expires=300'
    '&X-Amz-Security-Token=IQoJb3JpZ2luX2Vj%2Bsession'
    '&X-Amz-SignedHeaders=host&X-Amz-Signature=deadbeefcafe'
)
SECRETS = (
    ACCESS_TOKEN,
    REFRESH_TOKEN,
    OPAQUE_TOKEN,
    'ASIAEXAMPLE',
    'IQoJb3JpZ2luX2Vj',
    'deadbeefcafe',
)


def _assert_clean(text):
    for secret in SECRETS:
        assert secret not in text


# --- redact_secrets ---------------------------------------------------------


@pytest.mark.parametrize(
    'text,expected',
    [
        (
            "{'Authorization': b'Bearer abc.def-ghi_jk~+/=='}",
            "{'Authorization': b'Bearer <redacted>'}",
        ),
        (
            "{'Authorization': 'Bearer abc'}",
            "{'Authorization': 'Bearer <redacted>'}",
        ),
        ('authorization: bearer abc', 'authorization: bearer <redacted>'),
        (f'"AccessToken": "{ACCESS_TOKEN}"', '"AccessToken": "<redacted>"'),
        (f'"RefreshToken":"{REFRESH_TOKEN}"', '"RefreshToken":"<redacted>"'),
        (
            'X-Amz-Signature=abc&X-Amz-Credential=AKIA%2Fx&'
            'x-amz-security-token=tok"',
            'X-Amz-Signature=<redacted>&X-Amz-Credential=<redacted>&'
            'x-amz-security-token=<redacted>"',
        ),
        (
            'X-Amz-Signature=abc\\u0026X-Amz-Date=1',
            'X-Amz-Signature=<redacted>\\u0026X-Amz-Date=1',
        ),
        (
            'X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Expires=300',
            'X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Expires=300',
        ),
        (
            'Sending http request to registry',
            'Sending http request to registry',
        ),
    ],
)
def test_redact_secrets(text, expected):
    assert redact_secrets(text) == expected


def test_literal_secrets_are_redacted_whatever_their_shape():
    assert redact_secrets(f'token={OPAQUE_TOKEN};', {OPAQUE_TOKEN}) == (
        'token=<redacted>;'
    )


def test_short_values_are_never_treated_as_secrets():
    redact_logs_and_history('short', loggers=(), recorder=Mock())
    assert 'short' not in utils._LOG_REDACTION.secrets


# --- Logs -----------------------------------------------------------------


@pytest.fixture
def debug_log():
    """The handler --debug installs, writing to a buffer."""
    stream = io.StringIO()
    set_stream_logger('botocore', logging.DEBUG, stream=stream)
    try:
        yield stream
    finally:
        remove_stream_logger('botocore')


def _sent_request():
    return AWSRequest(
        method='POST',
        url='https://agent-registry.us-west-2.api.aws/registries/x',
        headers={'Authorization': f'Bearer {OPAQUE_TOKEN}'},
        data=b'{}',
    ).prepare()


def test_debug_log_of_the_request_and_response_is_redacted(debug_log):
    redact_logs_and_history(OPAQUE_TOKEN, recorder=Mock())
    # What botocore.endpoint and botocore.parsers log.
    endpoint_log = logging.getLogger('botocore.endpoint')
    endpoint_log.debug('Sending http request: %s', _sent_request())
    body = json.dumps({'artifact': {'downloadUrl': PRESIGNED}}).encode()
    logging.getLogger('botocore.parsers').debug('Response body:\n%s', body)
    endpoint_log.debug(
        'Making request with params: %s',
        {'body': json.dumps({'RefreshToken': REFRESH_TOKEN}).encode()},
    )
    endpoint_log.debug('Exported %s', OPAQUE_TOKEN)
    output = debug_log.getvalue()
    _assert_clean(output)
    assert "'Authorization': 'Bearer <redacted>'" in output
    assert 'X-Amz-Signature=<redacted>' in output
    assert 'X-Amz-Date=20261019T000000Z' in output
    assert 'Exported <redacted>' in output


def test_exception_tracebacks_are_redacted(debug_log):
    redact_logs_and_history(OPAQUE_TOKEN, recorder=Mock())
    try:
        raise RuntimeError(f'bad header Bearer {ACCESS_TOKEN}')
    except RuntimeError:
        logging.getLogger('botocore.endpoint').debug('failed', exc_info=True)
    output = debug_log.getvalue()
    assert 'RuntimeError: bad header Bearer <redacted>' in output
    _assert_clean(output)


def test_record_that_cannot_be_formatted_is_left_to_the_handler():
    record = logging.LogRecord(
        'botocore', logging.DEBUG, __file__, 1, '%s and %s', ('one',), None
    )
    # The handler then reports the bad record as it would without the filter.
    assert utils._RedactSecrets().filter(record) is True
    assert record.msg == '%s and %s'


def test_the_filter_is_attached_once(debug_log):
    redact_logs_and_history(recorder=Mock())
    redact_logs_and_history(recorder=Mock())
    [handler] = logging.getLogger('botocore').handlers
    assert handler.filters.count(utils._LOG_REDACTION) == 1


@pytest.fixture
def no_known_secrets():
    """No literal secrets added by an earlier test."""
    with patch.object(utils._LOG_REDACTION, 'secrets', set()):
        yield


@pytest.fixture
def auth_env(monkeypatch):
    # Set before deleting so monkeypatch restores the original absence even
    # though the code under test writes these variables itself.
    for name in (constants.TOKEN_ENV_VAR, 'AWS_AUTH_SCHEME_PREFERENCE'):
        monkeypatch.setenv(name, 'placeholder')
        monkeypatch.delenv(name)


def test_signed_in_token_is_redacted_from_the_debug_log(
    debug_log, auth_env, no_known_secrets
):
    provider = Mock(display_name='test')
    provider.authenticate.return_value = OPAQUE_TOKEN
    with (
        patch.object(providers.cache, 'load_token', return_value=None),
        patch.object(
            providers,
            'discover_registry',
            return_value=utils.RegistryAuthorization(
                'https://idp.example.com', []
            ),
        ),
        patch.object(providers, 'identify_provider', return_value=provider),
    ):
        providers.use_bearer_token(
            Mock(), 'https://registry.example', REGISTRY_ID, client_id='c'
        )
    logging.getLogger('botocore.endpoint').debug(
        'Sending http request: %s', _sent_request()
    )
    logging.getLogger('botocore.endpoint').debug('Token %s', OPAQUE_TOKEN)
    output = debug_log.getvalue()
    _assert_clean(output)
    assert 'Token <redacted>' in output


def test_generated_command_redacts_a_preset_token_from_the_debug_log(
    debug_log, monkeypatch, no_known_secrets
):
    # A token that does not look like a JWT, outside any Authorization
    # header, is only recognised as the literal value.
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, OPAQUE_TOKEN)
    agentregistry.redact_data_plane_call(
        call_parameters={'registryId': REGISTRY_ID},
        parsed_args=argparse.Namespace(),
        parsed_globals=argparse.Namespace(),
    )
    logging.getLogger('botocore.endpoint').debug('Token %s', OPAQUE_TOKEN)
    output = debug_log.getvalue()
    _assert_clean(output)
    assert 'Token <redacted>' in output


# --- History --------------------------------------------------------------


class _Collect(BaseHistoryHandler):
    def __init__(self):
        self.events = []

    def emit(self, event_type, payload, source):
        self.events.append((event_type, payload, source))


@pytest.fixture
def recorder(history_recorder):
    history_recorder.enable()
    return history_recorder


def _record_a_bearer_call(recorder):
    request = _sent_request()
    recorder.record(
        'API_CALL',
        {
            'service': 'cognito-idp',
            'operation': 'GetTokensFromRefreshToken',
            'params': {'ClientId': 'client', 'RefreshToken': REFRESH_TOKEN},
        },
    )
    recorder.record(
        'HTTP_REQUEST',
        {
            'method': request.method,
            'headers': request.headers,
            'streaming': False,
            'url': request.url,
            'body': request.body,
        },
    )
    recorder.record(
        'HTTP_RESPONSE',
        {
            'status_code': 200,
            'headers': {},
            'body': json.dumps(
                {'registryRecords': [{'artifact': {'downloadUrl': PRESIGNED}}]}
            ).encode(),
            'streaming': False,
            'context': {'operation_name': 'BatchGet'},
        },
    )
    recorder.record(
        'PARSED_RESPONSE',
        {'registryRecords': [{'artifact': {'downloadUrl': PRESIGNED}}]},
    )
    return request


def test_history_handlers_only_ever_see_redacted_payloads(recorder):
    handler = _Collect()
    recorder.add_handler(handler)
    redact_logs_and_history(OPAQUE_TOKEN)
    late = _Collect()
    recorder.add_handler(late)
    request = _record_a_bearer_call(recorder)

    for collected in (handler, late):
        events = {event: payload for event, payload, _ in collected.events}
        assert set(events) == {
            'API_CALL',
            'HTTP_REQUEST',
            'HTTP_RESPONSE',
            'PARSED_RESPONSE',
        }
        _assert_clean(repr(events))
        headers = events['HTTP_REQUEST']['headers']
        assert headers['Authorization'] == 'Bearer <redacted>'
        assert events['API_CALL']['params']['ClientId'] == 'client'
        url = events['PARSED_RESPONSE']['registryRecords'][0]['artifact'][
            'downloadUrl'
        ]
        assert url.startswith('https://bucket.s3.us-west-2.amazonaws.com/')
        assert 'X-Amz-Signature=<redacted>' in url
    # The request being sent keeps its token.
    assert request.headers['Authorization'] == f'Bearer {OPAQUE_TOKEN}'


def test_recorder_is_wrapped_once(recorder):
    handler = _Collect()
    recorder.add_handler(handler)
    redact_logs_and_history()
    redact_logs_and_history()
    recorder.record('CLI_RC', 0, 'CLI')
    assert handler.events == [('CLI_RC', 0, 'CLI')]


def test_payloads_without_secrets_are_unchanged(recorder):
    handler = _Collect()
    recorder.add_handler(handler)
    redact_logs_and_history()
    payload = {
        'status_code': 200,
        'headers': {'x-amzn-requestid': 'abc'},
        'body': b'\xff\xfe binary',
        'list': [1, ('a', None)],
    }
    recorder.record('HTTP_RESPONSE', payload)
    assert handler.events[0][1] == payload
    assert isinstance(handler.events[0][1]['list'][1], tuple)


def test_history_database_never_stores_the_token(recorder, tmp_path):
    db = tmp_path / 'history.db'
    connection = DatabaseConnection(str(db))
    recorder.add_handler(
        DatabaseHistoryHandler(
            DatabaseRecordWriter(connection), RecordBuilder()
        )
    )
    redact_logs_and_history(OPAQUE_TOKEN)
    _record_a_bearer_call(recorder)
    connection.close()
    rows = sqlite3.connect(str(db)).execute('SELECT payload FROM records')
    stored = '\n'.join(row[0] for row in rows)
    assert 'Bearer <redacted>' in stored
    _assert_clean(stored)
    _assert_clean(db.read_bytes().decode('utf-8', 'replace'))


def test_generated_command_redacts_a_preset_token_from_history(
    recorder, monkeypatch, no_known_secrets
):
    monkeypatch.setenv(constants.TOKEN_ENV_VAR, OPAQUE_TOKEN)
    handler = _Collect()
    recorder.add_handler(handler)
    agentregistry.redact_data_plane_call()
    _record_a_bearer_call(recorder)
    recorder.record('CLI_ARGUMENTS', f'token {OPAQUE_TOKEN}', 'CLI')
    _assert_clean(repr(handler.events))


def test_sigv4_generated_command_still_redacts_presigned_urls(
    recorder, monkeypatch
):
    monkeypatch.delenv(constants.TOKEN_ENV_VAR, raising=False)
    handler = _Collect()
    recorder.add_handler(handler)
    agentregistry.redact_data_plane_call()
    recorder.record(
        'PARSED_RESPONSE',
        {'registryRecords': [{'artifact': {'downloadUrl': PRESIGNED}}]},
    )
    _assert_clean(repr(handler.events))


def test_failed_redaction_records_a_placeholder_never_the_payload(recorder):
    handler = _Collect()
    recorder.add_handler(handler)
    redact_logs_and_history(OPAQUE_TOKEN)
    with patch.object(utils, '_redacted', side_effect=RecursionError('deep')):
        # Must not raise into botocore's request path.
        recorder.record(
            'HTTP_REQUEST',
            {'headers': {'Authorization': f'Bearer {OPAQUE_TOKEN}'}},
        )
    assert handler.events == [
        ('HTTP_REQUEST', '<redaction failed>', 'BOTOCORE')
    ]


@pytest.mark.parametrize('enabled,handlers', [(False, 1), (True, 0)])
def test_every_payload_is_redacted_whatever_the_recorder_keeps(
    history_recorder, enabled, handlers
):
    if enabled:
        history_recorder.enable()
    collected = [_Collect() for _ in range(handlers)]
    for handler in collected:
        history_recorder.add_handler(handler)
    redact_logs_and_history()
    payload = {'body': b'x'}
    with patch.object(utils, '_redacted', wraps=utils._redacted) as redact:
        history_recorder.record('HTTP_REQUEST', payload)
    assert redact.call_args_list[0].args[0] is payload
    # The recorder still decides what it keeps: here, nothing.
    assert [handler.events for handler in collected] == [[]] * handlers


# --- Token fields, whatever the token looks like ---------------------------


@pytest.mark.parametrize(
    'text,expected',
    [
        (
            'b\'{"ClientId":"c","RefreshToken":"opaque-1"}\'',
            'b\'{"ClientId":"c","RefreshToken":"<redacted>"}\'',
        ),
        (
            # An escaped quote inside the value.
            '{"access_token": "a\\"b", "token_type": "Bearer"}',
            '{"access_token": "<redacted>", "token_type": "Bearer"}',
        ),
        (
            "{'ClientId': 'c', 'RefreshToken': 'opaque-2'}",
            "{'ClientId': 'c', 'RefreshToken': '<redacted>'}",
        ),
        (
            'grant_type=refresh_token&refresh_token=opaque-3&client_id=c',
            'grant_type=refresh_token&refresh_token=<redacted>&client_id=c',
        ),
        ('id_token=abc', 'id_token=<redacted>'),
        (
            '"IdToken":"x","AccessToken":"y"',
            '"IdToken":"<redacted>","AccessToken":"<redacted>"',
        ),
        # Other fields are kept.
        (
            '"TokenType":"Bearer","ExpiresIn":3600',
            '"TokenType":"Bearer","ExpiresIn":3600',
        ),
        ('my_refresh_token=keep', 'my_refresh_token=keep'),
    ],
)
def test_token_fields_are_redacted_by_name(text, expected):
    assert redact_secrets(text) == expected


def test_token_fields_in_history_payloads_are_redacted_by_name(recorder):
    handler = _Collect()
    recorder.add_handler(handler)
    redact_logs_and_history()
    recorder.record(
        'PARSED_RESPONSE',
        {
            'AuthenticationResult': {
                'RefreshToken': 'opaque-rotated',
                'AccessToken': 'opaque-access',
                'TokenType': 'Bearer',
            },
            'list': [{'id_token': b'opaque-id'}],
        },
    )
    payload = handler.events[0][1]
    assert payload['AuthenticationResult'] == {
        'RefreshToken': '<redacted>',
        'AccessToken': '<redacted>',
        'TokenType': 'Bearer',
    }
    assert payload['list'] == [{'id_token': '<redacted>'}]


class _Raw:
    def __init__(self, body):
        self._body = body

    def stream(self, **kwargs):
        yield self._body


def test_rotated_opaque_refresh_token_never_reaches_logs_or_history(
    tmp_path, monkeypatch, debug_log, recorder
):
    import botocore.client
    import botocore.endpoint
    import botocore.loaders
    import botocore.session
    from botocore.awsrequest import AWSResponse

    from awscli.customizations.agentregistry import cache

    config = tmp_path / 'config'
    config.write_text('')
    monkeypatch.setenv('AWS_CONFIG_FILE', str(config))
    monkeypatch.setenv('AWS_SHARED_CREDENTIALS_FILE', str(tmp_path / 'creds'))
    for name in ('AWS_PROFILE', 'AWS_DEFAULT_PROFILE'):
        monkeypatch.delenv(name, raising=False)
    for name in [
        n for n in __import__('os').environ if n.startswith('AWS_ENDPOINT_URL')
    ]:
        monkeypatch.delenv(name)
    monkeypatch.setattr(cache, 'CACHE_DIR', str(tmp_path / 'cache'))
    session = botocore.session.Session()
    session.register_component(
        'data_loader',
        botocore.loaders.Loader(
            extra_search_paths=[botocore.loaders.Loader.BUILTIN_DATA_PATH],
            include_default_search_paths=False,
        ),
    )
    # Neither looks like a JWT, so only the field name gives them away.
    old = 'opaque-refresh-token-old-0123456789'
    rotated = 'opaque-refresh-token-rotated-9876543210'
    access = make_jwt(sub='user')
    body = json.dumps(
        {
            'AuthenticationResult': {
                'AccessToken': access,
                'ExpiresIn': 3600,
                'TokenType': 'Bearer',
                'RefreshToken': rotated,
            }
        }
    ).encode()

    def cognito(request, **kwargs):
        return AWSResponse(request.url, 200, {}, _Raw(body))

    session.register(
        'before-send.cognito-identity-provider.GetTokensFromRefreshToken',
        cognito,
    )
    endpoint = 'https://agent-registry.us-west-2.api.aws'
    cache.save_token(
        endpoint,
        REGISTRY_ID,
        token=make_jwt(exp=1),
        expires_in=1,
        refresh_token=old,
        client_id='client',
        issuer='https://cognito-idp.us-west-2.amazonaws.com/us-west-2_AbC123',
        pool_region='us-west-2',
    )
    handler = _Collect()
    recorder.add_handler(handler)
    with (
        patch.object(botocore.endpoint, 'history_recorder', recorder),
        patch.object(botocore.client, 'history_recorder', recorder),
    ):
        assert cache.load_token(endpoint, REGISTRY_ID, session=session) == (
            access
        )
    # The rotation was kept.
    assert cache.read_entry(endpoint, REGISTRY_ID)['refreshToken'] == rotated
    output = debug_log.getvalue()
    recorded = repr(handler.events)
    # The call was really logged and recorded.
    assert 'GetTokensFromRefreshToken' in output
    assert 'Response body' in output
    assert {event for event, _, _ in handler.events} >= {
        'API_CALL',
        'HTTP_REQUEST',
        'HTTP_RESPONSE',
        'PARSED_RESPONSE',
    }
    for secret in (old, rotated, access):
        assert secret not in output
        assert secret not in recorded
