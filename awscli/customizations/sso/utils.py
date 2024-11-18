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
import datetime
import json
import logging
import os
import socket
import time
import webbrowser
from functools import partial
from http.server import HTTPServer, BaseHTTPRequestHandler

from botocore.compat import urlparse, parse_qs
from botocore.credentials import JSONFileCache
from botocore.exceptions import (
    AuthCodeFetcherError,
    PendingAuthorizationExpiredError,
)
from botocore.utils import SSOTokenFetcher, SSOTokenFetcherAuth
from botocore.utils import original_ld_library_path

from awscli import __version__ as awscli_version
from awscli.customizations.assumerole import CACHE_DIR as AWS_CREDS_CACHE_DIR
from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ConfigurationError
from awscli.customizations.utils import uni_print

LOG = logging.getLogger(__name__)

SSO_TOKEN_DIR = os.path.expanduser(
    os.path.join('~', '.aws', 'sso', 'cache')
)

LOGIN_ARGS = [
    {
        'name': 'no-browser',
        'action': 'store_true',
        'default': False,
        'help_text': (
            'Disables automatically opening the verification URL in the '
            'default browser.'
        )
    },
    {
        'name': 'use-device-code',
        'action': 'store_true',
        'default': False,
        'help_text': (
            'Uses the Device Code authorization grant and login flow '
            'instead of the Authorization Code flow.'
        )
    }
]


def _serialize_utc_timestamp(obj):
    if isinstance(obj, datetime.datetime):
        return obj.strftime('%Y-%m-%dT%H:%M:%SZ')
    return obj


def _sso_json_dumps(obj):
    return json.dumps(obj, default=_serialize_utc_timestamp)


def do_sso_login(session, sso_region, start_url, token_cache=None,
                 on_pending_authorization=None, force_refresh=False,
                 registration_scopes=None, session_name=None,
                 use_device_code=False):
    if token_cache is None:
        token_cache = JSONFileCache(SSO_TOKEN_DIR, dumps_func=_sso_json_dumps)
    if on_pending_authorization is None:
        on_pending_authorization = OpenBrowserHandler(
            open_browser=open_browser_with_original_ld_path
        )

    # For the auth flow, we need a non-legacy sso-session and check that the
    # user hasn't opted into falling back to the device code flow
    if session_name and not use_device_code:
        token_fetcher = SSOTokenFetcherAuth(
            sso_region=sso_region,
            client_creator=session.create_client,
            auth_code_fetcher=AuthCodeFetcher(),
            cache=token_cache,
            on_pending_authorization=on_pending_authorization,
        )
    else:
        token_fetcher = SSOTokenFetcher(
            sso_region=sso_region,
            client_creator=session.create_client,
            cache=token_cache,
            on_pending_authorization=on_pending_authorization,
        )

    return token_fetcher.fetch_token(
        start_url=start_url,
        session_name=session_name,
        force_refresh=force_refresh,
        registration_scopes=registration_scopes,
    )


def parse_sso_registration_scopes(raw_scopes):
    parsed_scopes = []
    for scope in raw_scopes.split(','):
        if scope := scope.strip():
            parsed_scopes.append(scope)
    return parsed_scopes


def open_browser_with_original_ld_path(url):
    with original_ld_library_path():
        webbrowser.open_new_tab(url)


class BaseAuthorizationhandler:
    def __call__(
        self, userCode, verificationUri, verificationUriComplete, **kwargs
    ):
        # Pending authorization handlers should always take **kwargs in case
        # the API begins to return new values.
        raise NotImplementedError("authorization_handler")


class PrintOnlyHandler(BaseAuthorizationhandler):
    def __init__(self, outfile=None):
        self._outfile = outfile

    def __call__(
        self, userCode, verificationUri, verificationUriComplete, **kwargs
    ):
        opening_msg = (
            f'Browser will not be automatically opened.\n'
            f'Please visit the following URL:\n'
            f'\n{verificationUri}\n'

        )

        user_code_msg = (
            f'\nThen enter the code:\n'
            f'\n{userCode}\n'
            f'\nAlternatively, you may visit the following URL which will '
            f'autofill the code upon loading:'
            f'\n{verificationUriComplete}\n'
        )

        uni_print(opening_msg, self._outfile)
        if userCode:
            uni_print(user_code_msg, self._outfile)


class OpenBrowserHandler(BaseAuthorizationhandler):
    def __init__(self, outfile=None, open_browser=None):
        self._outfile = outfile
        if open_browser is None:
            open_browser = webbrowser.open_new_tab
        self._open_browser = open_browser

    def __call__(
        self, userCode, verificationUri, verificationUriComplete, **kwargs
    ):
        opening_msg = (
            f'Attempting to automatically open the SSO authorization page in '
            f'your default browser.\nIf the browser does not open or you wish '
            f'to use a different device to authorize this request, open the '
            f'following URL:\n'
            f'\n{verificationUri}\n'
        )

        user_code_msg = (
            f'\nThen enter the code:\n'
            f'\n{userCode}\n'
        )
        uni_print(opening_msg, self._outfile)
        if userCode:
            uni_print(user_code_msg, self._outfile)

        if self._open_browser:
            try:
                return self._open_browser(verificationUriComplete)
            except Exception:
                LOG.debug('Failed to open browser:', exc_info=True)


class AuthCodeFetcher:
    """Manages the local web server that will be used
    to retrieve the authorization code from the OAuth callback
    """
    # How many seconds handle_request should wait for an incoming request
    _REQUEST_TIMEOUT = 10
    # How long we wait overall for the callback
    _OVERALL_TIMEOUT = 60 * 10

    def __init__(self):
        self._auth_code = None
        self._state = None
        self._is_done = False

        # We do this so that the request handler can have a reference to this
        # AuthCodeFetcher so that it can pass back the state and auth code
        try:
            handler = partial(OAuthCallbackHandler, self)
            self.http_server = HTTPServer(('', 0), handler)
            self.http_server.timeout = self._REQUEST_TIMEOUT
        except socket.error as e:
            raise AuthCodeFetcherError(error_msg=e)

    def redirect_uri_without_port(self):
        return 'http://127.0.0.1/oauth/callback'

    def redirect_uri_with_port(self):
        return f'http://127.0.0.1:{self.http_server.server_port}/oauth/callback'

    def get_auth_code_and_state(self):
        """Blocks until the expected redirect request with either the
        authorization code/state or and error is handled
        """
        start = time.time()
        while not self._is_done and time.time() < start + self._OVERALL_TIMEOUT:
            self.http_server.handle_request()
        self.http_server.server_close()

        if not self._is_done:
            raise PendingAuthorizationExpiredError

        return self._auth_code, self._state

    def set_auth_code_and_state(self, auth_code, state):
        self._auth_code = auth_code
        self._state = state
        self._is_done = True


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler to handle OAuth callback requests, extracting
    the auth code and state parameters, and displaying a page directing
    the user to return to the CLI.
    """
    def __init__(self, auth_code_fetcher, *args, **kwargs):
        self._auth_code_fetcher = auth_code_fetcher
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        # Suppress built-in logging, otherwise it prints
        # each request to console
        pass

    def version_string(self):
        # Override the Host header in case helpful for debugging
        return f'AWS CLI/{awscli_version}'

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        with open(
            os.path.join(os.path.dirname(__file__), 'index.html'),
            'rb',
        ) as file:
            self.wfile.write(file.read())

        query_params = parse_qs(urlparse(self.path).query)

        if 'error' in query_params:
            self._auth_code_fetcher.set_auth_code_and_state(
                None,
                None,
            )
        elif 'code' in query_params and 'state' in query_params:
            self._auth_code_fetcher.set_auth_code_and_state(
                query_params['code'][0],
                query_params['state'][0],
            )


class InvalidSSOConfigError(ConfigurationError):
    pass


class BaseSSOCommand(BasicCommand):
    _REQUIRED_SSO_CONFIG_VARS = [
        'sso_start_url',
        'sso_region',
    ]

    def _get_sso_config(self, sso_session=None):
        scoped_config = self._session.get_scoped_config()
        if sso_session is None:
            sso_session = scoped_config.get('sso_session')
        if sso_session:
            return self._get_sso_session_config(sso_session)
        else:
            return self._get_legacy_sso_config(scoped_config)

    def _get_sso_session_config(self, session_name):
        full_config = self._session.full_config
        if session_name not in full_config.get('sso_sessions', {}):
            raise InvalidSSOConfigError(
                f'The specified sso-session does not exist: "{session_name}"'
            )
        session_config = full_config['sso_sessions'][session_name]
        sso_config, missing = self._get_required_config_vars(session_config)
        sso_config['session_name'] = session_name

        scopes_var = 'sso_registration_scopes'
        if scopes_var in session_config:
            raw_scopes = session_config[scopes_var]
            parsed_scopes = parse_sso_registration_scopes(raw_scopes)
            sso_config['registration_scopes'] = parsed_scopes

        if missing:
            error_msg = (
                'Missing the following required SSO configuration values: %s. '
            ) % ', '.join(missing)
            raise InvalidSSOConfigError(error_msg)

        return sso_config

    def _get_legacy_sso_config(self, scoped_config):
        sso_config, missing = self._get_required_config_vars(scoped_config)
        if missing:
            raise InvalidSSOConfigError(
                'Missing the following required SSO configuration values: %s. '
                'To make sure this profile is properly configured to use SSO, '
                'please run: aws configure sso' % ', '.join(missing)
            )
        return sso_config

    def _get_required_config_vars(self, config):
        sso_config = {}
        missing_vars = []
        for config_var in self._REQUIRED_SSO_CONFIG_VARS:
            if config_var not in config:
                missing_vars.append(config_var)
            else:
                sso_config[config_var] = config[config_var]
        return sso_config, missing_vars
