# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import io
import json
from argparse import Namespace
from unittest import mock

import pytest

from awscli.argparser import ArgParseException
from awscli.customizations.docs import (
    DEFAULT_LOCALE,
    DOC_SEARCH_URL,
    DOCS_DOMAIN,
    DocSearchClient,
    DocSearchError,
    DocsSearchCommand,
    OutputFormat,
    TextExcerpt,
    _os_locale,
    _windows_locale,
    build_search_payload,
    detect_locale,
    normalize_locale,
    parse_excerpts,
    register_docs_commands,
    render,
    render_text,
)

SAMPLE_RESPONSE = json.dumps(
    {
        'suggestions': [
            {
                'textExcerptSuggestion': {
                    'title': 'Bucket naming rules',
                    'link': 'https://docs.aws.amazon.com/s3/naming.html',
                    'summary': 'General purpose bucket naming rules.',
                }
            },
            {
                'textExcerptSuggestion': {
                    'title': 'Working with buckets',
                    'link': 'https://docs.aws.amazon.com/s3/buckets.html',
                }
            },
        ]
    }
)


def mock_session():
    session = mock.Mock()
    session.user_agent_extra = 'aws-cli'
    # The BasicCommand arg-unpacking path emits events; returning None keeps
    # the real string values instead of substituting Mock objects.
    session.emit.return_value = None
    session.emit_first_non_none_response.return_value = None
    return session


class FakeHttpResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


class FakeHttpSession:
    """A fake HTTP session that records the request and returns a response."""

    def __init__(self, response):
        self._response = response
        self.sent_request = None

    def send(self, request):
        self.sent_request = request
        return self._response


class FakeDocSearchClient:
    def __init__(self, raw_response):
        self._raw_response = raw_response
        self.queries = []

    def search(self, query):
        self.queries.append(query)
        return self._raw_response


# ---------------------------------------------------------------------------
# Pure function tests (fast, no side effects)
# ---------------------------------------------------------------------------
class TestOutputFormat:
    def test_choices_are_the_enum_values(self):
        assert OutputFormat.choices() == ['text', 'json']

    def test_round_trips_from_value(self):
        assert OutputFormat('text') is OutputFormat.TEXT
        assert OutputFormat('json') is OutputFormat.JSON


class TestBuildSearchPayload:
    def test_payload_matches_expected_shape(self):
        payload = build_search_payload('S3 bucket naming rules')
        assert payload == {
            'textQuery': {'input': 'S3 bucket naming rules'},
            'contextAttributes': [{'key': 'domain', 'value': DOCS_DOMAIN}],
            'acceptSuggestionBody': 'RawText',
            'locales': ['en_us'],
        }

    def test_locale_is_used_in_payload(self):
        payload = build_search_payload('anything', 'de_de')
        assert payload['locales'] == ['de_de']

    def test_defaults_to_default_locale(self):
        payload = build_search_payload('anything')
        assert payload['locales'] == [DEFAULT_LOCALE]


class TestNormalizeLocale:
    @pytest.mark.parametrize(
        'raw,expected',
        [
            ('en_US.UTF-8', 'en_us'),
            ('en_US', 'en_us'),
            ('en-US', 'en_us'),
            ('fr_FR.UTF-8', 'fr_fr'),
            ('de_DE@euro', 'de_de'),
            ('ja_JP.eucJP', 'ja_jp'),
        ],
    )
    def test_normalizes_os_locales(self, raw, expected):
        assert normalize_locale(raw) == expected

    @pytest.mark.parametrize('raw', ['', None, 'C', 'POSIX', 'c', 'posix'])
    def test_unusable_locales_return_empty(self, raw):
        assert normalize_locale(raw) == ''


class TestDetectLocale:
    def test_prefers_lc_all(self):
        environ = {
            'LC_ALL': 'fr_FR.UTF-8',
            'LC_MESSAGES': 'de_DE.UTF-8',
            'LANG': 'en_US.UTF-8',
        }
        assert detect_locale(environ, os_locale=lambda: '') == 'fr_fr'

    def test_falls_back_through_precedence(self):
        assert (
            detect_locale({'LANG': 'es_ES.UTF-8'}, os_locale=lambda: '')
            == 'es_es'
        )
        assert (
            detect_locale(
                {'LC_MESSAGES': 'it_IT.UTF-8', 'LANG': 'C'},
                os_locale=lambda: '',
            )
            == 'it_it'
        )

    def test_skips_unusable_values(self):
        assert (
            detect_locale({'LC_ALL': 'C', 'LANG': 'pt_BR.UTF-8'})
            == 'pt_br'
        )

    def test_uses_os_locale_when_env_unset(self):
        # Simulates Windows, where the LC_*/LANG variables are not set and
        # the locale comes from the OS as a BCP-47 tag like 'en-US'.
        assert detect_locale({}, os_locale=lambda: 'en-US') == 'en_us'

    def test_env_takes_precedence_over_os_locale(self):
        assert (
            detect_locale({'LANG': 'ja_JP.UTF-8'}, os_locale=lambda: 'en-US')
            == 'ja_jp'
        )

    def test_defaults_when_env_and_os_locale_empty(self):
        # Simulates e.g. a macOS GUI/launchd session with no LANG set and no
        # OS value available.
        assert detect_locale({}, os_locale=lambda: '') == DEFAULT_LOCALE

    def test_defaults_when_nothing_set(self):
        assert detect_locale({}, os_locale=lambda: '') == DEFAULT_LOCALE


class TestPlatformLocale:
    def test_os_locale_returns_empty_on_non_windows(self):
        with mock.patch('awscli.customizations.docs.is_windows', False):
            assert _os_locale() == ''

    def test_os_locale_uses_windows_lookup_on_windows(self):
        with mock.patch('awscli.customizations.docs.is_windows', True):
            with mock.patch(
                'awscli.customizations.docs._windows_locale',
                return_value='en-US',
            ):
                assert _os_locale() == 'en-US'

    def test_windows_locale_reads_win32_api(self):
        # Simulate the Win32 GetUserDefaultLocaleName call filling the buffer.
        def fake_get_locale(buffer, length):
            buffer.value = 'de-DE'
            return len('de-DE')

        fake_ctypes = mock.MagicMock()
        fake_ctypes.create_unicode_buffer.side_effect = (
            lambda n: mock.Mock(value='')
        )
        fake_ctypes.windll.kernel32.GetUserDefaultLocaleName = fake_get_locale
        with mock.patch.dict('sys.modules', {'ctypes': fake_ctypes}):
            assert _windows_locale() == 'de-DE'

    def test_windows_locale_returns_empty_on_failure(self):
        fake_ctypes = mock.MagicMock()
        fake_ctypes.create_unicode_buffer.side_effect = (
            lambda n: mock.Mock(value='')
        )
        fake_ctypes.windll.kernel32.GetUserDefaultLocaleName.return_value = 0
        with mock.patch.dict('sys.modules', {'ctypes': fake_ctypes}):
            assert _windows_locale() == ''


class TestParseExcerpts:
    def test_extracts_title_and_link(self):
        excerpts = parse_excerpts(SAMPLE_RESPONSE)
        assert excerpts == [
            TextExcerpt(
                title='Bucket naming rules',
                link='https://docs.aws.amazon.com/s3/naming.html',
            ),
            TextExcerpt(
                title='Working with buckets',
                link='https://docs.aws.amazon.com/s3/buckets.html',
            ),
        ]

    def test_skips_suggestions_without_text_excerpt(self):
        raw = json.dumps(
            {
                'suggestions': [
                    {'someOtherSuggestion': {'title': 'nope'}},
                    {
                        'textExcerptSuggestion': {
                            'title': 'yes',
                            'link': 'https://docs.aws.amazon.com/x.html',
                        }
                    },
                ]
            }
        )
        excerpts = parse_excerpts(raw)
        assert excerpts == [
            TextExcerpt(
                title='yes', link='https://docs.aws.amazon.com/x.html'
            )
        ]

    def test_empty_suggestions_returns_empty_list(self):
        assert parse_excerpts(json.dumps({'suggestions': []})) == []

    def test_missing_suggestions_key_returns_empty_list(self):
        assert parse_excerpts(json.dumps({})) == []


class TestRenderText:
    def test_matches_jq_title_link_blank_line_format(self):
        excerpts = parse_excerpts(SAMPLE_RESPONSE)
        rendered = render_text(excerpts)
        assert rendered == (
            'Bucket naming rules\n'
            'https://docs.aws.amazon.com/s3/naming.html\n'
            '\n'
            'Working with buckets\n'
            'https://docs.aws.amazon.com/s3/buckets.html\n'
            '\n'
        )

    def test_empty_excerpts_render_to_empty_string(self):
        assert render_text([]) == ''


class TestRender:
    def test_json_format_returns_response_verbatim(self):
        assert render(SAMPLE_RESPONSE, OutputFormat.JSON) == SAMPLE_RESPONSE

    def test_text_format_extracts_excerpts(self):
        assert render(SAMPLE_RESPONSE, OutputFormat.TEXT) == render_text(
            parse_excerpts(SAMPLE_RESPONSE)
        )


# ---------------------------------------------------------------------------
# Client tests (side effect isolated behind a fake HTTP session)
# ---------------------------------------------------------------------------
class TestDocSearchClient:
    def test_posts_expected_request(self):
        session = FakeHttpSession(FakeHttpResponse(200, SAMPLE_RESPONSE))
        client = DocSearchClient(
            session=session,
            session_id_factory=lambda: 'fixed-session-id',
            locale='en_us',
            user_agent='aws-cli/9.9.9 Python/3.12 Linux/6.1',
        )

        result = client.search('S3 bucket naming rules')

        assert result == SAMPLE_RESPONSE
        request = session.sent_request
        assert request.method == 'POST'
        assert request.url == f'{DOC_SEARCH_URL}?session=fixed-session-id'
        assert request.headers['Content-Type'] == 'application/json'
        assert (
            request.headers['User-Agent']
            == 'aws-cli/9.9.9 Python/3.12 Linux/6.1'
        )
        assert json.loads(request.body) == build_search_payload(
            'S3 bucket naming rules', 'en_us'
        )

    def test_omits_user_agent_header_when_not_provided(self):
        session = FakeHttpSession(FakeHttpResponse(200, SAMPLE_RESPONSE))
        client = DocSearchClient(session=session)
        client.search('anything')
        assert 'User-Agent' not in session.sent_request.headers

    def test_uses_detected_locale_in_payload(self, monkeypatch):
        monkeypatch.setenv('LC_ALL', 'fr_FR.UTF-8')
        session = FakeHttpSession(FakeHttpResponse(200, SAMPLE_RESPONSE))
        client = DocSearchClient(session=session)
        client.search('anything')
        assert json.loads(session.sent_request.body)['locales'] == ['fr_fr']

    def test_explicit_locale_overrides_detection(self, monkeypatch):
        monkeypatch.setenv('LC_ALL', 'fr_FR.UTF-8')
        session = FakeHttpSession(FakeHttpResponse(200, SAMPLE_RESPONSE))
        client = DocSearchClient(session=session, locale='ja_jp')
        client.search('anything')
        assert json.loads(session.sent_request.body)['locales'] == ['ja_jp']

    def test_endpoint_uses_amazon_docs_proxy_domain(self):
        assert DOC_SEARCH_URL == 'https://proxy.search.docs.aws.com/search'

    def test_generates_a_unique_session_per_call_by_default(self):
        session = FakeHttpSession(FakeHttpResponse(200, SAMPLE_RESPONSE))
        client = DocSearchClient(session=session)

        client.search('one')
        first_url = session.sent_request.url
        client.search('two')
        second_url = session.sent_request.url

        assert first_url != second_url
        assert first_url.startswith(f'{DOC_SEARCH_URL}?session=')
        assert second_url.startswith(f'{DOC_SEARCH_URL}?session=')

    def test_uses_custom_endpoint_url(self):
        session = FakeHttpSession(FakeHttpResponse(200, SAMPLE_RESPONSE))
        client = DocSearchClient(
            session=session,
            endpoint_url='https://example.test/search',
            session_id_factory=lambda: 'abc',
        )
        client.search('anything')
        assert (
            session.sent_request.url
            == 'https://example.test/search?session=abc'
        )

    def test_non_200_raises(self):
        session = FakeHttpSession(FakeHttpResponse(503, 'unavailable'))
        client = DocSearchClient(session=session)
        with pytest.raises(DocSearchError, match='HTTP status 503'):
            client.search('S3 bucket naming rules')


# ---------------------------------------------------------------------------
# Command tests (fake client + captured output stream)
# ---------------------------------------------------------------------------
class TestDocsSearchCommand:
    def _command(self, raw_response=SAMPLE_RESPONSE):
        client = FakeDocSearchClient(raw_response)
        stream = io.StringIO()
        command = DocsSearchCommand(
            mock_session(), client=client, stream=stream
        )
        return command, client, stream

    def test_default_text_output(self):
        command, client, stream = self._command()
        rc = command(['S3 bucket naming rules'], Namespace())
        assert rc == 0
        assert client.queries == ['S3 bucket naming rules']
        assert stream.getvalue() == render(SAMPLE_RESPONSE, OutputFormat.TEXT)

    def test_json_output_is_verbatim(self):
        command, client, stream = self._command()
        rc = command(
            ['S3 bucket naming rules', '--format', 'json'], Namespace()
        )
        assert rc == 0
        assert stream.getvalue() == SAMPLE_RESPONSE

    def test_explicit_text_format(self):
        command, client, stream = self._command()
        rc = command(
            ['S3 bucket naming rules', '--format', 'text'], Namespace()
        )
        assert rc == 0
        assert stream.getvalue() == render(SAMPLE_RESPONSE, OutputFormat.TEXT)

    def test_invalid_format_is_rejected(self):
        command, _, _ = self._command()
        with pytest.raises(ArgParseException, match='invalid choice'):
            command(['query', '--format', 'yaml'], Namespace())

    def test_defaults_to_real_client_when_none_supplied(self):
        command = DocsSearchCommand(mock_session())
        assert isinstance(command._client, DocSearchClient)

    def test_default_client_uses_cli_user_agent(self):
        session = mock_session()
        session.user_agent.return_value = 'aws-cli/9.9.9 Python/3.12 Linux/6.1'
        command = DocsSearchCommand(session)
        assert (
            command._client._user_agent
            == 'aws-cli/9.9.9 Python/3.12 Linux/6.1'
        )

    def test_default_user_agent_handles_session_without_user_agent(self):
        session = object()  # no user_agent attribute
        assert DocsSearchCommand._default_user_agent(session) is None


# ---------------------------------------------------------------------------
# Registration wiring
# ---------------------------------------------------------------------------
class TestRegistration:
    def test_registers_against_building_command_table_main(self):
        handlers = mock.Mock()
        register_docs_commands(handlers)
        handlers.register.assert_called_once()
        event_name = handlers.register.call_args.args[0]
        assert event_name == 'building-command-table.main'
