# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import json
import os
import sqlite3

from botocore.history import HistoryRecorder

from awscli.clidriver import AWSCLIEntryPoint
from awscli.testutils import (
    BaseCLIWireResponseTest,
    FileCreator,
    create_clidriver,
    mock,
)

ACCESS_KEY_ID = 'ASIAEXAMPLERESPONSE'
SECRET_ACCESS_KEY = 'responseSecret/abc+def'
SESSION_TOKEN = 'responseToken/IQoJb3Jp+Z2luX2Vj=='
EXPIRATION = '2026-11-16T12:00:00Z'
ROLE_ARN = 'arn:aws:iam::123456789012:role/demo'
ASSUMED_ROLE_ARN = 'arn:aws:sts::123456789012:assumed-role/demo/session'
# The session token of the credentials that sign each request.
REQUEST_SESSION_TOKEN = 'requestToken/FwoGZXIvYXdz+EJr=='
SECRETS = (SECRET_ACCESS_KEY, SESSION_TOKEN, REQUEST_SESSION_TOKEN)


def sts_response(operation, extra=''):
    return (
        f'<{operation}Response '
        'xmlns="https://sts.amazonaws.com/doc/2011-06-15/">'
        f'<{operation}Result>'
        '<Credentials>'
        f'<AccessKeyId>{ACCESS_KEY_ID}</AccessKeyId>'
        f'<SecretAccessKey>{SECRET_ACCESS_KEY}</SecretAccessKey>'
        f'<SessionToken>{SESSION_TOKEN}</SessionToken>'
        f'<Expiration>{EXPIRATION}</Expiration>'
        '</Credentials>'
        f'{extra}'
        f'</{operation}Result>'
        '<ResponseMetadata><RequestId>req-1</RequestId></ResponseMetadata>'
        f'</{operation}Response>'
    ).encode()


ASSUMED_ROLE_USER = (
    '<AssumedRoleUser>'
    f'<Arn>{ASSUMED_ROLE_ARN}</Arn>'
    '<AssumedRoleId>AROAEXAMPLE:session</AssumedRoleId>'
    '</AssumedRoleUser>'
)
FEDERATED_USER = (
    '<FederatedUser>'
    '<Arn>arn:aws:sts::123456789012:federated-user/demo</Arn>'
    '<FederatedUserId>123456789012:demo</FederatedUserId>'
    '</FederatedUser>'
)
SSO_RESPONSE = json.dumps(
    {
        'roleCredentials': {
            'accessKeyId': ACCESS_KEY_ID,
            'secretAccessKey': SECRET_ACCESS_KEY,
            'sessionToken': SESSION_TOKEN,
            'expiration': 1794830400000,
        }
    }
).encode('utf-8')

COGNITO_RESPONSE = json.dumps(
    {
        'IdentityId': 'us-east-1:identity',
        'Credentials': {
            'AccessKeyId': ACCESS_KEY_ID,
            'SecretKey': SECRET_ACCESS_KEY,
            'SessionToken': SESSION_TOKEN,
            'Expiration': 1794830400,
        },
    }
).encode()

# (command, response body, non-secret values that stay visible)
RESPONSES = {
    'AssumeRole': (
        [
            'sts',
            'assume-role',
            '--role-arn',
            ROLE_ARN,
            '--role-session-name',
            'session',
        ],
        sts_response('AssumeRole', ASSUMED_ROLE_USER),
        [ACCESS_KEY_ID, EXPIRATION, ASSUMED_ROLE_ARN],
    ),
    'AssumeRoleWithWebIdentity': (
        [
            'sts',
            'assume-role-with-web-identity',
            '--role-arn',
            ROLE_ARN,
            '--role-session-name',
            'session',
            '--web-identity-token',
            'web-identity-token',
        ],
        sts_response('AssumeRoleWithWebIdentity', ASSUMED_ROLE_USER),
        [ACCESS_KEY_ID, EXPIRATION, ASSUMED_ROLE_ARN],
    ),
    'AssumeRoleWithSAML': (
        [
            'sts',
            'assume-role-with-saml',
            '--role-arn',
            ROLE_ARN,
            '--principal-arn',
            'arn:aws:iam::123456789012:saml-provider/demo',
            '--saml-assertion',
            'c2FtbA==',
        ],
        sts_response('AssumeRoleWithSAML', ASSUMED_ROLE_USER),
        [ACCESS_KEY_ID, EXPIRATION, ASSUMED_ROLE_ARN],
    ),
    'GetSessionToken': (
        ['sts', 'get-session-token'],
        sts_response('GetSessionToken'),
        [ACCESS_KEY_ID, EXPIRATION],
    ),
    'GetFederationToken': (
        ['sts', 'get-federation-token', '--name', 'demo'],
        sts_response('GetFederationToken', FEDERATED_USER),
        [ACCESS_KEY_ID, EXPIRATION],
    ),
    'GetRoleCredentials': (
        [
            'sso',
            'get-role-credentials',
            '--role-name',
            'demo',
            '--account-id',
            '123456789012',
            '--access-token',
            'sso-access-token',
        ],
        SSO_RESPONSE,
        [ACCESS_KEY_ID, '1794830400000'],
    ),
    'GetCredentialsForIdentity': (
        [
            'cognito-identity',
            'get-credentials-for-identity',
            '--identity-id',
            'us-east-1:identity',
        ],
        COGNITO_RESPONSE,
        [ACCESS_KEY_ID, 'us-east-1:identity'],
    ),
}


class TestCredentialRedaction(BaseCLIWireResponseTest):
    def setUp(self):
        super().setUp()
        self.files = FileCreator()
        self.addCleanup(self.files.remove_all)
        self.history_file = os.path.join(self.files.rootdir, 'history.db')
        self.environ['AWS_CONFIG_FILE'] = self.files.create_file(
            'config', '[default]\ncli_history = enabled\n'
        )
        self.environ['AWS_CLI_HISTORY_FILE'] = self.history_file
        self.environ['AWS_SESSION_TOKEN'] = REQUEST_SESSION_TOKEN
        self.recorder = HistoryRecorder()
        for module in (
            'awscli.clidriver.HISTORY_RECORDER',
            'awscli.customizations.history.HISTORY_RECORDER',
            'botocore.endpoint.history_recorder',
            'botocore.client.history_recorder',
        ):
            patcher = mock.patch(module, self.recorder)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.create_driver()

    def create_driver(self):
        # The driver reads the config file when it's created.
        self.driver = create_clidriver()
        self.entry_point = AWSCLIEntryPoint(self.driver)

    def tearDown(self):
        for handler in self.recorder._handlers:
            handler._writer.close()
        super().tearDown()

    def history_text(self):
        with sqlite3.connect(self.history_file) as connection:
            rows = connection.execute(
                'SELECT event_type, payload FROM records'
            ).fetchall()
        connection.close()
        self.assertIn('HTTP_RESPONSE', [row[0] for row in rows])
        return '\n'.join(row[1] for row in rows)

    def assert_redacted(self, text, visible):
        for secret in SECRETS:
            self.assertNotIn(secret, text)
        self.assertIn('<redacted credential>', text)
        for value in visible:
            self.assertIn(value, text)

    def run_operation(self, operation, extra_args=()):
        cmdline, body, visible = RESPONSES[operation]
        self.patch_send(content=body)
        _, stderr, _ = self.run_cmd(cmdline + list(extra_args))
        return stderr, visible

    def test_history_has_no_secrets(self):
        for operation in RESPONSES:
            with self.subTest(operation=operation):
                _, visible = self.run_operation(operation)
                self.assert_redacted(self.history_text(), visible)

    def test_debug_output_has_no_secrets(self):
        for operation in RESPONSES:
            with self.subTest(operation=operation):
                stderr, visible = self.run_operation(operation, ['--debug'])
                self.assertIn('Response body', stderr)
                self.assert_redacted(stderr, visible)

    def test_signed_request_hides_security_token_header(self):
        stderr, _ = self.run_operation('GetSessionToken', ['--debug'])
        self.assertIn('x-amz-security-token:<redacted credential>', stderr)
        self.assertNotIn(REQUEST_SESSION_TOKEN, stderr)
        self.assertNotIn(REQUEST_SESSION_TOKEN, self.history_text())

    def test_sigv2_request_hides_security_token(self):
        self.patch_send(
            content=b'<ListDomainsResponse><ListDomainsResult/>'
            b'</ListDomainsResponse>'
        )
        _, stderr, _ = self.run_cmd(['sdb', 'list-domains', '--debug'])
        self.assertIn('SecurityToken=<redacted credential>', stderr)
        self.assertNotIn(REQUEST_SESSION_TOKEN, stderr)
        self.assertNotIn(REQUEST_SESSION_TOKEN, self.history_text())

    def test_history_show_has_no_secrets(self):
        self.run_operation('AssumeRole')
        stdout, _, _ = self.run_cmd(['history', 'show'])
        self.assert_redacted(stdout, [ACCESS_KEY_ID, ASSUMED_ROLE_ARN])

    def test_role_profile_credentials_are_redacted(self):
        # The AssumeRole call the credential provider makes for a role
        # profile goes through the same history and debug logging.
        self.environ['AWS_CONFIG_FILE'] = self.files.create_file(
            'config',
            '[default]\n'
            'cli_history = enabled\n'
            '[profile role]\n'
            f'role_arn = {ROLE_ARN}\n'
            'source_profile = base\n'
            'credential_cache = memory\n'
            'cli_history = enabled\n'
            '[profile base]\n'
            'aws_access_key_id = AKIDEXAMPLEBASE\n'
            'aws_secret_access_key = baseSecret/abc\n',
        )
        self.create_driver()
        bodies = {
            'AssumeRole': sts_response('AssumeRole', ASSUMED_ROLE_USER),
            'GetCallerIdentity': (
                b'<GetCallerIdentityResponse><GetCallerIdentityResult>'
                b'<Arn>' + ASSUMED_ROLE_ARN.encode() + b'</Arn>'
                b'</GetCallerIdentityResult></GetCallerIdentityResponse>'
            ),
        }

        def send(request):
            if 'Action=AssumeRole' in str(request.body):
                action = 'AssumeRole'
            else:
                action = 'GetCallerIdentity'
            return mock.Mock(
                status_code=200, headers={}, content=bodies[action]
            )

        with mock.patch('botocore.endpoint.Endpoint._send', side_effect=send):
            _, stderr, _ = self.run_cmd(
                ['sts', 'get-caller-identity', '--profile', 'role', '--debug']
            )
        visible = [ACCESS_KEY_ID, EXPIRATION, ASSUMED_ROLE_ARN]
        self.assert_redacted(stderr, visible)
        self.assert_redacted(self.history_text(), visible)
