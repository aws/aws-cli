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
from awscli.customizations.commands import BasicCommand
from awscli.customizations.signin import exceptions

import urllib.parse
import urllib.request
import urllib.error
from botocore.awsrequest import AWSRequest
from botocore.httpsession import URLLib3Session
import json
import sys


class SigninCommand(BasicCommand):
    NAME = 'signin'
    DESCRIPTION = BasicCommand.FROM_FILE()
    SYNOPSIS = ''
    ARG_TABLE = [
        {
            'name': 'session-duration',
            'cli_type_name': 'integer',
            'help_text': (
                "<p>Specifies the duration of the console session. This is"
                " separate from the duration of the temporary credentials that"
                " you specify using the DurationSeconds parameter of an"
                " sts:AssumeRole call. You can specify a --session-duration"
                " maximum value of 43200 (12 hours). If the --session-duration"
                " parameter is missing, then the session defaults to the"
                " duration of the credentials of the profile used for this "
                " command (which defaults to one hour).</p><p>See the"
                " documentation for the `sts:AssumeRole` API for details about"
                " how to specify a duration using the DurationSeconds"
                " parameter. The ability to create a console session that is"
                " longer than one hour is intrinsic to the getSigninToken"
                " operation of the federation endpoint.</p>"
            ),
            'required': False
        },
        {
            'name': 'destination-url',
            'help_text': (
                "<p>URL for the desired AWS console page. The browser will"
                " automatically redirect to this URL after login.</p><p>To"
                " provide this value you will need to set the config option"
                " `cli_follow_urlparam` to false.</p>"
            ),
            'required': False
        },
        {
            'name': 'issuer-url',
            'help_text': (
                "<p>URL for your internal sign-in page. The browser will"
                " automatically redirect to this URL after the user's session"
                " expires.</p><p>To provide this value you will need to set the"
                " config option `cli_follow_urlparam` to false.</p>"
            ),
            'required': False
        },
        {
            'name': 'partition',
            'help_text': (
                "<p>The AWS partition for the signin URLs.</p><ul>"
                "<li>**AWS** = aws.amazon.com</li>"
                "<li>**AWS_US_GOV** = amazonaws-us-gov.com</li>"
                "<li>**AWS_CN** = amazonaws.cn</li></ul>"
            ),
            'required': False,
            'default': 'AWS',
            'choices': ['AWS', 'AWS_CN', 'AWS_US_GOV'],
        },
    ]
    EXAMPLES = BasicCommand.FROM_FILE()

    def __init__(self, session, prompter=None, config_writer=None):
        super(SigninCommand, self).__init__(session)

    def _run_main(self, parsed_args, parsed_globals):
        # Called when invoked with no args "aws signin"
        # Reference Architecture: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_enable-console-custom-url.html

        credentials = self._session.get_credentials()
        if credentials.token is None:
            # Temporary credentials are REQUIRED
            raise exceptions.NonTemporaryCredentialsError()

        json_credentials = {
            'sessionId': credentials.access_key,
            'sessionKey': credentials.secret_key,
            'sessionToken': credentials.token
        }

        partitions = {
            'AWS': 'aws.amazon.com',
            'AWS_US_GOV': 'amazonaws-us-gov.com',
            'AWS_CN': 'amazonaws.cn'
        }
        token_url = self._build_getsignintoken_url(
            credentials=json_credentials,
            partition=partitions[parsed_args.partition],
            session_duration=parsed_args.session_duration
        )

        # Federation endpoint always returns a JSON object with a
        # 'SigninToken' key as long as the request is properly formatted
        # with an in-range SessionDuration parameter. Conveniently this
        # allows us to test with invalid credentials or partitions we don't
        # have credentials for.
        req = URLLib3Session()
        response = req.send(AWSRequest('GET', token_url).prepare())
        if response.status_code >= 400:
            raise exceptions.FederationResponseError(
                msg=f"HTTP Code {response.status_code}"
            )

        federation_response = response.content
        try:
            signin_token_json = json.loads(federation_response)
        except ValueError:
            raise exceptions.FederationResponseError(
                msg='Malformed reponse. Not a JSON string.'
            )

        if 'SigninToken' not in signin_token_json:
            raise exceptions.FederationResponseError(
                msg=('Malformed reponse. JSON string does not contain key '
                     'Signintoken')
            )

        signin_url = self._build_login_url(
            partition=partitions[parsed_args.partition],
            signin_token=signin_token_json['SigninToken'],
            destination_url=parsed_args.destination_url,
            issuer_url=parsed_args.issuer_url
        )

        sys.stdout.write(signin_url + "\n")
        return 0

    @staticmethod
    def _build_getsignintoken_url(credentials, partition,
                                  session_duration=None):
        string_credentials = json.dumps(credentials)
        url = f"https://signin.{partition}/federation?Action=getSigninToken"
        if session_duration:
            if not 900 <= session_duration <= 43200:
                raise exceptions.SessionDurationOutOfRangeError()
            url += f"&SessionDuration={session_duration}"
        url += f"&Session={urllib.parse.quote_plus(string_credentials)}"
        return url

    @staticmethod
    def _build_login_url(partition, signin_token, destination_url=None,
                         issuer_url=None):
        url = f"https://signin.{partition}/federation?Action=login"
        if issuer_url:
            url += f"&Issuer={urllib.parse.quote_plus(issuer_url)}"
        dest_url = destination_url or f"https://console.{partition}/"
        url += f"&Destination={urllib.parse.quote_plus(dest_url)}"
        url += f"&SigninToken={signin_token}"
        return url
