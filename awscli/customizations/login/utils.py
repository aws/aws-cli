# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import base64
import binascii
import datetime
import hashlib
import json
import logging
import secrets
import string
import textwrap
import uuid
from enum import Enum

from awscrt.crypto import EC, ECExportFormat, ECType
from botocore.compat import parse_qsl
from botocore.useragent import register_feature_id
from dateutil.tz.tz import tzutc

from awscli.botocore.exceptions import (
    LoginAuthorizationCodeError,
    LoginInsufficientPermissions,
)
from awscli.botocore.utils import (
    ArnParser,
    build_add_dpop_header_handler,
    get_base_sign_in_uri,
    percent_encode_sequence,
)
from awscli.compat import compat_input

LOG = logging.getLogger(__name__)


class LoginType(Enum):
    SAME_DEVICE = 1
    CROSS_DEVICE = 2


CLIENT_ID = {
    LoginType.SAME_DEVICE: 'arn:aws:signin:::devtools/same-device',
    LoginType.CROSS_DEVICE: 'arn:aws:signin:::devtools/cross-device',
}


class BaseLoginTokenFetcher:
    """Base class that can acquire an access token from AWS Sign-In"""

    def __init__(
        self,
        client,
        on_pending_authorization,
        private_key=None,
        base_uri_builder=None,
    ):
        self._client = client
        self._on_pending_authorization = on_pending_authorization
        self._expected_state = uuid.uuid4()

        self._code_verifier = ''.join(
            secrets.choice(string.ascii_letters + string.digits + '-._~')
            for _ in range(64)
        )
        self._code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(self._code_verifier.encode()).digest()
        ).decode()

        if private_key is None:
            private_key = EC.new_generate(ECType.P_256)
        self._private_key = private_key

        if base_uri_builder is None:
            base_uri_builder = get_base_sign_in_uri
        self._base_endpoint = base_uri_builder(self._client)

    def fetch_token(self):
        """Retrieves an access token via AWS Sign-In"""
        raise NotImplementedError('fetch_token')

    @staticmethod
    def _get_browser_handler_args(authorization_uri):
        """Generates the arguments for the method that opens the browser"""
        return {
            'verificationUri': authorization_uri,
            'verificationUriComplete': authorization_uri,
            'userCode': None,
        }

    def _exchange_auth_code_for_access_token(
        self, client_id, auth_code, redirect_uri=None
    ):
        """Exchanges the temporary auth code for an access token"""
        body = {
            'clientId': client_id,
            'grantType': 'authorization_code',
            'code': auth_code,
            'codeVerifier': self._code_verifier,
        }

        # Won't have a redirect URI for the cross-device workflow
        if redirect_uri:
            body['redirectUri'] = redirect_uri

        self._client.meta.events.register(
            'before-call.signin.CreateOAuth2Token',
            build_add_dpop_header_handler(self._private_key),
        )

        try:
            response = self._client.create_o_auth2_token(
                tokenInput=body,
            )
        except self._client.exceptions.AccessDeniedException as e:
            error_type = e.response.get('error', '')
            if error_type == 'AUTHCODE_EXPIRED':
                raise LoginAuthorizationCodeError(
                    error_msg="Unable to complete the login process due to an expired authorization "
                    "code. Please reauthenticate using 'aws login'."
                )
            elif error_type == 'INSUFFICIENT_PERMISSIONS':
                raise LoginInsufficientPermissions()

            raise

        if response is None or 'tokenOutput' not in response:
            raise LoginAuthorizationCodeError(
                error_msg='Failed to retrieve an access token.'
            )

        output = response.get('tokenOutput')

        expires_timestamp = datetime.datetime.now(
            tzutc()
        ) + datetime.timedelta(seconds=output['expiresIn'])
        login_session = self._extract_login_session_from_id_token(
            output['idToken']
        )
        account_id = self._extract_account_id_from_login_session(login_session)

        token = {
            'accessToken': {
                'accessKeyId': output['accessToken']['accessKeyId'],
                'secretAccessKey': output['accessToken']['secretAccessKey'],
                'sessionToken': output['accessToken']['sessionToken'],
                'accountId': account_id,
                'expiresAt': expires_timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
            },
            'tokenType': output['tokenType'],
            'clientId': client_id,
            'refreshToken': output['refreshToken'],
            'idToken': output['idToken'],
            'dpopKey': self._serialize_to_pem(self._private_key),
        }
        return token, login_session

    def _get_authorization_uri(
        self, client_id, expected_state, code_challenge, redirect_uri=None
    ):
        query_params = {
            'response_type': 'code',
            'client_id': client_id,
            'state': expected_state,
            'code_challenge_method': 'SHA-256',
            'scope': 'openid',
            # Don't want to encode code_challenge again, so we append below
        }

        if redirect_uri:
            query_params['redirect_uri'] = redirect_uri

        return (
            f'{self._base_endpoint}/v1/authorize?'
            f'{percent_encode_sequence(query_params)}'
            f'&code_challenge={code_challenge[:-1]}'
        )

    @staticmethod
    def _extract_login_session_from_id_token(id_token):
        # Extract the subject arn from the JWT payload
        parts = id_token.split('.')
        if len(parts) != 3:
            raise ValueError('Invalid JWT token - cannot extract payload')
        payload_bytes = base64_url_decode(parts[1])
        payload_json = json.loads(payload_bytes)

        if 'sub' not in payload_json:
            raise ValueError('Invalid JWT token - missing sub')

        return payload_json['sub']

    @staticmethod
    def _extract_account_id_from_login_session(login_session):
        login_session_arn = ArnParser().parse_arn(login_session)

        return login_session_arn['account']

    @staticmethod
    def _serialize_to_pem(private_key):
        contents = base64.b64encode(
            private_key.export_key(ECExportFormat.SEC1)
        ).decode('utf-8')
        # RFC 1421 calls for 64 character lines max
        wrapped_contents = textwrap.fill(contents, width=64)
        return f'-----BEGIN EC PRIVATE KEY-----\n{wrapped_contents}\n-----END EC PRIVATE KEY-----\n'


class SameDeviceLoginTokenFetcher(BaseLoginTokenFetcher):
    """
    Logs in using OAuth's auth code and PKCE flow,
    intended for when the user is on a device with a web browser and the
    ability to initialize the callback server
    """

    def __init__(
        self,
        client,
        auth_code_fetcher,
        on_pending_authorization,
        private_key=None,
        base_uri_builder=None,
    ):
        super().__init__(
            client,
            on_pending_authorization,
            private_key=private_key,
            base_uri_builder=base_uri_builder,
        )
        self._auth_code_fetcher = auth_code_fetcher

    def fetch_token(self):
        register_feature_id('LOGIN_SAME_DEVICE')
        authorization_uri = self._get_authorization_uri(
            client_id=CLIENT_ID[LoginType.SAME_DEVICE],
            redirect_uri=self._auth_code_fetcher.redirect_uri_with_port(),
            expected_state=self._expected_state,
            code_challenge=self._code_challenge,
        )

        # Open/display the link, then block until the redirect uri is hit
        self._on_pending_authorization(
            **self._get_browser_handler_args(authorization_uri)
        )
        auth_code, state = self._auth_code_fetcher.get_auth_code_and_state()

        if auth_code is None:
            raise LoginAuthorizationCodeError(
                error_msg='Failed to retrieve an authorization code.'
            )

        # The state we get back from the redirect is just a string, so
        # cast our original UUID before comparing
        if state != str(self._expected_state):
            raise LoginAuthorizationCodeError(
                error_msg=f'State parameter {state} does not match expected value {self._expected_state}.'
            )

        return self._exchange_auth_code_for_access_token(
            client_id=CLIENT_ID[LoginType.SAME_DEVICE],
            auth_code=auth_code,
            redirect_uri=self._auth_code_fetcher.redirect_uri_with_port(),
        )


class CrossDeviceLoginTokenFetcher(BaseLoginTokenFetcher):
    """
    Logs in by prompting the user to enter the auth code,
    intended for when the user is unable to open a web browser
    on the same device where the CLI is running.
    """

    def fetch_token(self):
        register_feature_id('LOGIN_CROSS_DEVICE')
        redirect_uri = f'{self._base_endpoint}/v1/sessions/confirmation'

        authorization_uri = self._get_authorization_uri(
            client_id=CLIENT_ID[LoginType.CROSS_DEVICE],
            expected_state=self._expected_state,
            code_challenge=self._code_challenge,
            redirect_uri=redirect_uri,
        )

        self._on_pending_authorization(
            **self._get_browser_handler_args(authorization_uri)
        )

        verification_code = self._prompt(
            '\nEnter the authorization code displayed in your browser'
        )

        auth_code, state = self.parse_verification_code(verification_code)

        if auth_code is None:
            raise LoginAuthorizationCodeError(
                error_msg='Failed to retrieve an authorization code.'
            )

        if state != str(self._expected_state):
            raise LoginAuthorizationCodeError(
                error_msg=f'State parameter {state} does not match expected value {self._expected_state}.'
            )

        return self._exchange_auth_code_for_access_token(
            client_id=CLIENT_ID[LoginType.CROSS_DEVICE],
            auth_code=auth_code,
            redirect_uri=redirect_uri,
        )

    @staticmethod
    def parse_verification_code(verification_code):
        """
        Parse the verification code that the user pastes from the browser,
        which is expected to be base64-encoded 'state={state}&auth_code={code}'
        """
        try:
            query_string = base64.b64decode(verification_code).decode('utf-8')
        except (UnicodeDecodeError, binascii.Error):
            raise ValueError('Failed to decode the verification code.')

        params_dict = dict(parse_qsl(query_string))

        if 'state' not in params_dict or 'code' not in params_dict:
            raise ValueError(
                'Failed to retrieve an auth_code or state from the verification code'
            )

        return params_dict['code'], params_dict['state']

    @staticmethod
    def _prompt(
        prompt_text,
    ):
        response = compat_input(f'{prompt_text}: ')
        if not response:
            response = None
        return response


def base64_url_decode(data):
    data += '=' * (-len(data) % 4)  # restore '=' padding
    return base64.urlsafe_b64decode(data)
