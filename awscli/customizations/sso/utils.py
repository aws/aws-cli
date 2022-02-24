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

from awscli.customizations.utils import uni_print
from awscli.customizations.assumerole import CACHE_DIR as AWS_CREDS_CACHE_DIR

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
                 on_pending_authorization=None, force_refresh=False):
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
        force_refresh=force_refresh
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
