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
import os
import logging
import json
import webbrowser

from botocore.utils import SSOTokenFetcher
from botocore.utils import original_ld_library_path
from botocore.credentials import JSONFileCache

from awscli.customizations.commands import BasicCommand
from awscli.customizations.utils import uni_print
from awscli.customizations.assumerole import CACHE_DIR as AWS_CREDS_CACHE_DIR
from awscli.customizations.exceptions import ConfigurationError

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
            'Disables automatically opening the verfication URL in the '
            'default browser.'
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
                 registration_scopes=None, session_name=None):
    if token_cache is None:
        token_cache = JSONFileCache(SSO_TOKEN_DIR, dumps_func=_sso_json_dumps)
    if on_pending_authorization is None:
        on_pending_authorization = OpenBrowserHandler(
            open_browser=open_browser_with_original_ld_path
        )
    token_fetcher = SSOTokenFetcher(
        sso_region=sso_region,
        client_creator=session.create_client,
        cache=token_cache,
        on_pending_authorization=on_pending_authorization
    )
    return token_fetcher.fetch_token(
        start_url=start_url,
        session_name=session_name,
        force_refresh=force_refresh,
        registration_scopes=registration_scopes,
    )


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
            f'\nThen enter the code:\n'
            f'\n{userCode}\n'
            f'\nAlternatively, you may visit the following URL which will '
            f'autofill the code upon loading:'
            f'\n{verificationUriComplete}\n'
        )
        uni_print(opening_msg, self._outfile)


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
            f'\nThen enter the code:\n'
            f'\n{userCode}\n'
        )
        uni_print(opening_msg, self._outfile)
        if self._open_browser:
            try:
                return self._open_browser(verificationUriComplete)
            except Exception:
                LOG.debug('Failed to open browser:', exc_info=True)


class InvalidSSOConfigError(ConfigurationError):
    pass


class BaseSSOCommand(BasicCommand):
    _REQUIRED_SSO_CONFIG_VARS = [
        'sso_start_url',
        'sso_region',
    ]

    def _get_sso_config(self):
        scoped_config = self._session.get_scoped_config()
        sso_session_config = self._get_sso_session_config(scoped_config)
        if sso_session_config:
            return sso_session_config
        return self._get_legacy_sso_config(scoped_config)

    def _get_sso_session_config(self, scoped_config):
        if 'sso_session' not in scoped_config:
            return None

        for config_var in self._REQUIRED_SSO_CONFIG_VARS:
            if config_var in scoped_config:
                raise InvalidSSOConfigError(
                    'Inline SSO configuration and sso_session cannot be '
                    'configured on the same profile.'
                )

        session_name = scoped_config['sso_session']
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
            parsed_scopes = self._parse_registration_scopes(raw_scopes)
            sso_config['registration_scopes'] = parsed_scopes

        if missing:
            error_msg = (
                'Missing the following required SSO configuration values: %s. '
            ) % ', '.join(missing)
            raise InvalidSSOConfigError(error_msg)

        return sso_config

    def _parse_registration_scopes(self, raw_scopes):
        parsed_scopes = []
        for scope in raw_scopes.split(','):
            scope = scope.strip()
            if scope:
                parsed_scopes.append(scope)
        return parsed_scopes

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
