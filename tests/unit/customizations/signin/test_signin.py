# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from argparse import Namespace
from awscli.customizations.signin import exceptions
from awscli.customizations.signin.signin import SigninCommand
from awscli.testutils import unittest, capture_output, mock
from tests.unit.customizations.configure import FakeSession


class TestSigninCommand(unittest.TestCase):

    def setUp(self):
        self.global_args = Namespace()
        self.global_args.profile = 'default'

    def test_signin_defaults(self):
        credentials = mock.Mock()
        credentials.access_key = 'ASIAAAAAAAAAAAAAAAAAA'
        credentials.secret_key = 'SECRET_ACCESS_TEST_VALUE'
        credentials.token = 'SESSION_TOKEN_TEST_VALUE'
        session = FakeSession({}, profile='default', credentials=credentials)
        cmd = SigninCommand(session=session)
        with capture_output() as captured:
            cmd(args='', parsed_globals=self.global_args)
        self.assertIn(
            ('https://signin.aws.amazon.com/federation?Action=login&Destinatio'
             'n=https%3A%2F%2Fconsole.aws.amazon.com%2F&SigninToken='),
            captured.stdout.getvalue()
        )

    @mock.patch('awscli.customizations.signin.signin.URLLib3Session.send')
    def test_signin_with_bad_request(self, mock_send):
        response = mock.Mock()
        response.status_code = 400
        response.content = 'Bad Request'
        mock_send.return_value = response
        credentials = mock.Mock()
        credentials.access_key = 'ASIAAAAAAAAAAAAAAAAAA'
        credentials.secret_key = 'SECRET_ACCESS_TEST_VALUE'
        credentials.token = 'SESSION_TOKEN_TEST_VALUE'
        session = FakeSession({}, profile='default', credentials=credentials)
        cmd = SigninCommand(session=session)
        msg = "Signin doesn't raise federation response error with bad data"
        with self.assertRaises(exceptions.FederationResponseError, msg=msg):
            cmd(
                args='',
                parsed_globals=self.global_args
            )

    @mock.patch('awscli.customizations.signin.signin.URLLib3Session.send')
    def test_signin_with_non_json_response(self, mock_send):
        response = mock.Mock()
        response.status_code = 200
        response.content = 'Some Non-JSON Content'
        mock_send.return_value = response
        credentials = mock.Mock()
        credentials.access_key = 'ASIAAAAAAAAAAAAAAAAAA'
        credentials.secret_key = 'SECRET_ACCESS_TEST_VALUE'
        credentials.token = 'SESSION_TOKEN_TEST_VALUE'
        session = FakeSession({}, profile='default', credentials=credentials)
        cmd = SigninCommand(session=session)
        msg = "Signin doesn't raise federation response error with bad data"
        with self.assertRaises(exceptions.FederationResponseError, msg=msg):
            cmd(
                args='',
                parsed_globals=self.global_args
            )

    @mock.patch('awscli.customizations.signin.signin.URLLib3Session.send')
    def test_signin_with_malformed_json_response(self, mock_send):
        response = mock.Mock()
        response.status_code = 200
        response.content = '{"test_key": "test_value"}'
        mock_send.return_value = response
        credentials = mock.Mock()
        credentials.access_key = 'ASIAAAAAAAAAAAAAAAAAA'
        credentials.secret_key = 'SECRET_ACCESS_TEST_VALUE'
        credentials.token = 'SESSION_TOKEN_TEST_VALUE'
        session = FakeSession({}, profile='default', credentials=credentials)
        cmd = SigninCommand(session=session)
        msg = "Signin doesn't raise federation response error with bad data"
        with self.assertRaises(exceptions.FederationResponseError, msg=msg):
            cmd(
                args='',
                parsed_globals=self.global_args
            )

    def test_signin_with_user_credentials(self):
        credentials = mock.Mock()
        credentials.access_key = 'AKIAAAAAAAAAAAAAAAAAA'
        credentials.secret_key = 'SECRET_ACCESS_TEST_VALUE'
        credentials.token = None
        session = FakeSession({}, profile='default', credentials=credentials)
        cmd = SigninCommand(session=session)
        msg = "Signin doesn't raise error when using non-temporary credentials"
        with self.assertRaises(exceptions.NonTemporaryCredentialsError,
                               msg=msg):
            cmd(
                args='',
                parsed_globals=self.global_args
            )

    def test_build_getsignintoken_url_default(self):
        url = SigninCommand._build_getsignintoken_url(
            credentials={
                'sessionId': 'TEST_VALUE',
                'sessionKey': 'TEST_VALUE',
                'sessionToken': 'TEST_VALUE'
            },
            partition='aws.amazon.com'
        )
        self.assertEqual(
            url,
            ('https://signin.aws.amazon.com/federation?Action=getSigninToken&S'
             'ession=%7B%22sessionId%22%3A+%22TEST_VALUE%22%2C+%22sessionKey%2'
             '2%3A+%22TEST_VALUE%22%2C+%22sessionToken%22%3A+%22TEST_VALUE%22%'
             '7D'),
            'Improperly formatted default Signin Token URL'
        )

    def test_build_getsignintoken_url_with_duration_min(self):
        url = SigninCommand._build_getsignintoken_url(
            credentials={
                'sessionId': 'TEST_VALUE',
                'sessionKey': 'TEST_VALUE',
                'sessionToken': 'TEST_VALUE'
            },
            partition='aws.amazon.com',
            session_duration=900
        )
        self.assertEqual(
            url,
            ('https://signin.aws.amazon.com/federation?Action=getSigninToken&S'
             'essionDuration=900&Session=%7B%22sessionId%22%3A+%22TEST_VALUE%2'
             '2%2C+%22sessionKey%22%3A+%22TEST_VALUE%22%2C+%22sessionToken%22%'
             '3A+%22TEST_VALUE%22%7D'),
            'Improperly formatted Signin Token URL with minimum duration'
        )

    def test_build_getsignintoken_url_with_duration_max(self):
        url = SigninCommand._build_getsignintoken_url(
            credentials={
                'sessionId': 'TEST_VALUE',
                'sessionKey': 'TEST_VALUE',
                'sessionToken': 'TEST_VALUE'
            },
            partition='aws.amazon.com',
            session_duration=43200
        )
        self.assertEqual(
            url,
            ('https://signin.aws.amazon.com/federation?Action=getSigninToken&S'
             'essionDuration=43200&Session=%7B%22sessionId%22%3A+%22TEST_VALUE'
             '%22%2C+%22sessionKey%22%3A+%22TEST_VALUE%22%2C+%22sessionToken%2'
             '2%3A+%22TEST_VALUE%22%7D'),
            'Improperly formatted Signin Token URL with maximum duration'
        )

    def test_build_getsignintoken_url_with_duration_too_long(self):
        msg = 'URL improperly generated with out-of-range session duration'
        with self.assertRaises(exceptions.SessionDurationOutOfRangeError,
                               msg=msg):
            SigninCommand._build_getsignintoken_url(
                credentials={
                    'sessionId': 'TEST_VALUE',
                    'sessionKey': 'TEST_VALUE',
                    'sessionToken': 'TEST_VALUE'
                },
                partition='aws.amazon.com',
                session_duration=43201
            )

    def test_build_getsignintoken_url_with_duration_too_short(self):
        msg = 'URL improperly generated with out-of-range session duration'
        with self.assertRaises(exceptions.SessionDurationOutOfRangeError,
                               msg=msg):
            SigninCommand._build_getsignintoken_url(
                credentials={
                    'sessionId': 'TEST_VALUE',
                    'sessionKey': 'TEST_VALUE',
                    'sessionToken': 'TEST_VALUE'
                },
                partition='aws.amazon.com',
                session_duration=899
            )

    def test_build_login_url_default(self):
        url = SigninCommand._build_login_url(
            partition='aws.amazon.com',
            signin_token='TOKEN_HERE'
        )
        self.assertEqual(
            url,
            ('https://signin.aws.amazon.com/federation?Action=login&Destinatio'
             'n=https%3A%2F%2Fconsole.aws.amazon.com%2F&SigninToken=TOKEN_HERE'
             ),
            'Improperly formatted default Login URL'
        )

    def test_build_login_url_with_optional_urls(self):
        url = SigninCommand._build_login_url(
            partition='aws.amazon.com',
            signin_token='TOKEN_HERE',
            destination_url='https://desturl.amazon.com/',
            issuer_url='http://login.mycompany.com/'
        )
        self.assertEqual(
            url,
            ('https://signin.aws.amazon.com/federation?Action=login&Issuer=htt'
             'p%3A%2F%2Flogin.mycompany.com%2F&Destination=https%3A%2F%2Fdestu'
             'rl.amazon.com%2F&SigninToken=TOKEN_HERE'),
            'Improperly formatted Login URL with destination and issuer URLs'
        )
