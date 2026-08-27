# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Adds an ``aws docs search <query>`` command.

The command queries the public AWS documentation search endpoint and
renders the returned suggestions either as plain text (title/link pairs)
or as the raw JSON exactly as it comes back from the service.

The HTTP side effect is isolated behind :class:`DocSearchClient` so that
the command logic and rendering can be exercised without performing a
real network call.  The rendering helpers are pure functions operating on
plain data, which keeps the testable "onion" thin and fast.
"""

import enum
import json
import os
import sys
import uuid
from dataclasses import dataclass

from awscli.botocore.awsrequest import AWSRequest
from awscli.botocore.httpsession import URLLib3Session
from awscli.compat import is_windows
from awscli.customizations.commands import BasicCommand

#: The public AWS documentation search endpoint.
DOC_SEARCH_URL = 'https://proxy.search.docs.aws.com/search'
#: The documentation domain scoped for the search.
DOCS_DOMAIN = 'docs.aws.amazon.com'
#: Locale requested from the search service when none can be detected.
DEFAULT_LOCALE = 'en_us'
#: Environment variables consulted (in order) to detect the user's locale.
LOCALE_ENV_VARS = ('LC_ALL', 'LC_MESSAGES', 'LANG')


def normalize_locale(raw_locale):
    """Normalize an OS locale string to the API's ``ll_cc`` form.

    Converts values like ``en_US.UTF-8`` or ``en-US`` to ``en_us``. Returns
    an empty string for unusable locales (empty, ``C`` or ``POSIX``), which
    signals that the caller should fall back to the default.
    """
    if not raw_locale:
        return ''
    # Drop encoding ('.UTF-8') and modifier ('@euro') suffixes.
    language = raw_locale.split('.', 1)[0].split('@', 1)[0]
    language = language.replace('-', '_')
    if not language or language.upper() in ('C', 'POSIX'):
        return ''
    return language.lower()


def _windows_locale():
    """Return the current user's locale on Windows (e.g. ``en-US``).

    Reads it from the Win32 API since Windows shells do not populate the
    ``LC_*``/``LANG`` environment variables. Returns an empty string if the
    lookup fails.
    """
    import ctypes

    # LOCALE_NAME_MAX_LENGTH is 85 wide chars.
    buffer_length = 85
    buffer = ctypes.create_unicode_buffer(buffer_length)
    written = ctypes.windll.kernel32.GetUserDefaultLocaleName(
        buffer, buffer_length
    )
    if written:
        return buffer.value
    return ''


def _os_locale():
    """Return the OS-reported locale for the current platform.

    On Unix (Linux/macOS) the standard ``LC_*``/``LANG`` environment
    variables are authoritative, so there is nothing extra to query here and
    we return an empty string. On Windows those variables are typically
    unset, so we ask the OS directly.
    """
    if is_windows:
        return _windows_locale()
    return ''


def detect_locale(environ=None, os_locale=None):
    """Detect the user's locale in a cross-platform way.

    Resolution order:

    1. The standard locale environment variables (``LC_ALL``,
       ``LC_MESSAGES``, ``LANG``) -- authoritative on Linux and set by most
       macOS terminal sessions.
    2. An OS-level query -- primarily for Windows, whose shells do not set
       those environment variables.
    3. :data:`DEFAULT_LOCALE` as a final fallback.

    ``environ`` and ``os_locale`` are injectable so this stays deterministic
    and testable across platforms without actually running on them.
    """
    environ = environ if environ is not None else os.environ
    for name in LOCALE_ENV_VARS:
        normalized = normalize_locale(environ.get(name))
        if normalized:
            return normalized
    query = os_locale if os_locale is not None else _os_locale
    normalized = normalize_locale(query())
    if normalized:
        return normalized
    return DEFAULT_LOCALE


class DocSearchError(Exception):
    """Raised when the documentation search request fails."""


class OutputFormat(enum.Enum):
    """The supported rendering formats for search results.

    Using an enum (instead of bare strings scattered around the module)
    keeps the set of valid formats closed and impossible to mistype.
    """

    TEXT = 'text'
    JSON = 'json'

    @classmethod
    def choices(cls):
        return [member.value for member in cls]


@dataclass(frozen=True)
class TextExcerpt:
    """A single ``textExcerptSuggestion`` reduced to what text output needs."""

    title: str
    link: str


def build_search_payload(query, locale=DEFAULT_LOCALE):
    """Build the JSON request body for a documentation search.

    Pure function: given a query string and locale it returns the exact
    structure expected by the documentation search endpoint.
    """
    return {
        'textQuery': {'input': query},
        'contextAttributes': [{'key': 'domain', 'value': DOCS_DOMAIN}],
        'acceptSuggestionBody': 'RawText',
        'locales': [locale],
    }


def parse_excerpts(raw_response):
    """Parse raw JSON text into a list of :class:`TextExcerpt`.

    Suggestions that do not carry a ``textExcerptSuggestion`` are skipped
    rather than surfaced as empty/``null`` rows.
    """
    data = json.loads(raw_response)
    excerpts = []
    for suggestion in data.get('suggestions', []):
        excerpt = suggestion.get('textExcerptSuggestion')
        if excerpt is None:
            continue
        excerpts.append(
            TextExcerpt(
                title=excerpt.get('title', ''),
                link=excerpt.get('link', ''),
            )
        )
    return excerpts


def render_text(excerpts):
    """Render excerpts as ``title``/``link`` pairs separated by blank lines.
    """
    return ''.join(
        f'{excerpt.title}\n{excerpt.link}\n\n' for excerpt in excerpts
    )


def render(raw_response, output_format):
    """Render a raw search response according to ``output_format``.

    ``OutputFormat.JSON`` returns the response exactly as it came back from
    the service; ``OutputFormat.TEXT`` extracts and formats the excerpts.
    """
    if output_format is OutputFormat.JSON:
        return raw_response
    return render_text(parse_excerpts(raw_response))


class DocSearchClient:
    """Performs the documentation search HTTP call.

    This is the only side-effecting piece of the feature.  It accepts an
    injectable HTTP ``session`` (any object exposing ``send``), a
    ``session_id_factory`` (a no-arg callable returning the per-request
    session id), and an optional ``user_agent`` string. Injecting these
    lets tests supply fakes and avoid real network access or
    nondeterministic ids.
    """

    def __init__(
        self,
        session=None,
        endpoint_url=DOC_SEARCH_URL,
        session_id_factory=None,
        locale=None,
        user_agent=None,
    ):
        self._session = session or URLLib3Session()
        self._endpoint_url = endpoint_url
        self._session_id_factory = session_id_factory or (
            lambda: str(uuid.uuid4())
        )
        self._locale = locale or detect_locale()
        self._user_agent = user_agent

    def search(self, query):
        """Return the raw response body text for ``query``."""
        payload = json.dumps(build_search_payload(query, self._locale))
        url = f'{self._endpoint_url}?session={self._session_id_factory()}'
        headers = {'Content-Type': 'application/json'}
        if self._user_agent:
            headers['User-Agent'] = self._user_agent
        request = AWSRequest(
            method='POST',
            url=url,
            data=payload,
            headers=headers,
        ).prepare()
        response = self._session.send(request)
        if response.status_code != 200:
            raise DocSearchError(
                'Documentation search failed with HTTP status '
                f'{response.status_code}.'
            )
        return response.text


class DocsSearchCommand(BasicCommand):
    NAME = 'search'
    DESCRIPTION = (
        'Search the AWS documentation and print matching results.\n\n'
        'By default results are printed as plain text, with each result '
        'rendered as a title followed by its documentation link. Use '
        '``--format json`` to print the raw response exactly as returned '
        'by the documentation search service.'
    )
    SYNOPSIS = 'aws docs search <query> [--format text|json]'
    EXAMPLES = (
        'Search for guidance on S3 bucket naming::\n\n'
        '    $ aws docs search "S3 bucket naming rules"\n\n'
        'Return the raw JSON payload::\n\n'
        '    $ aws docs search "S3 bucket naming rules" --format json\n'
    )
    ARG_TABLE = [
        {
            'name': 'query',
            'help_text': 'The text to search the AWS documentation for.',
            'action': 'store',
            'cli_type_name': 'string',
            'positional_arg': True,
        },
        {
            'name': 'format',
            'help_text': (
                'The output format. ``text`` prints title/link pairs; '
                '``json`` prints the raw search response.'
            ),
            'action': 'store',
            'cli_type_name': 'string',
            'choices': OutputFormat.choices(),
            'default': OutputFormat.TEXT.value,
        },
    ]

    def __init__(self, session, client=None, stream=None):
        super().__init__(session)
        self._client = (
            client
            if client is not None
            else DocSearchClient(user_agent=self._default_user_agent(session))
        )
        self._stream = stream if stream is not None else sys.stdout

    @staticmethod
    def _default_user_agent(session):
        """Return the CLI's own User-Agent, if the session can provide one."""
        user_agent = getattr(session, 'user_agent', None)
        if callable(user_agent):
            return user_agent()
        return None

    def _run_main(self, parsed_args, parsed_globals):
        output_format = OutputFormat(parsed_args.format)
        raw_response = self._client.search(parsed_args.query)
        self._stream.write(render(raw_response, output_format))
        return 0


class DocsCommand(BasicCommand):
    NAME = 'docs'
    DESCRIPTION = 'Search and interact with the AWS documentation.'
    SYNOPSIS = 'aws docs <subcommand> [parameters]'
    SUBCOMMANDS = [
        {'name': 'search', 'command_class': DocsSearchCommand},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        if parsed_args.subcommand is None:
            self._raise_usage_error()


def register_docs_commands(event_handlers):
    event_handlers.register(
        'building-command-table.main', DocsCommand.add_command
    )
