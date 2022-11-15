# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os
import io
import sys
import csv
import json
from datetime import datetime
from collections import namedtuple

from awscli.customizations.commands import BasicCommand


# Takes botocore's ReadOnlyCredentials and exposes an expiry_time.
Credentials = namedtuple(
    'Credentials', ['access_key', 'secret_key', 'token', 'expiry_time'])


def convert_botocore_credentials(credentials):
    # Converts botocore credentials to our `Credentials` type.
    frozen = credentials.get_frozen_credentials()
    expiry_time_str = None
    # Botocore does not expose an attribute for the expiry_time of temporary
    # credentials, so for the time being we need to access an internal
    # attribute to retrieve this info.  We're following up to see if botocore
    # can make this a public attribute.
    expiry_time = getattr(credentials, '_expiry_time', None)
    if expiry_time is not None and isinstance(expiry_time, datetime):
        expiry_time_str = expiry_time.isoformat()
    return Credentials(
        access_key=frozen.access_key,
        secret_key=frozen.secret_key,
        token=frozen.token,
        expiry_time=expiry_time_str,
    )


class BaseCredentialFormatter(object):

    FORMAT = None

    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        self._stream = stream

    def display_credentials(self, credentials):
        pass


class BashEnvVarFormatter(BaseCredentialFormatter):

    FORMAT = 'env'

    def display_credentials(self, credentials):
        output = (
            f'export AWS_ACCESS_KEY_ID={credentials.access_key}\n'
            f'export AWS_SECRET_ACCESS_KEY={credentials.secret_key}\n'
        )
        if credentials.token is not None:
            output += f'export AWS_SESSION_TOKEN={credentials.token}\n'
        if credentials.expiry_time is not None:
            output += (
                f'export AWS_CREDENTIAL_EXPIRATION={credentials.expiry_time}\n'
            )
        self._stream.write(output)


class PowershellFormatter(BaseCredentialFormatter):

    FORMAT = 'powershell'

    def display_credentials(self, credentials):
        output = (
            f'$Env:AWS_ACCESS_KEY_ID="{credentials.access_key}"\n'
            f'$Env:AWS_SECRET_ACCESS_KEY="{credentials.secret_key}"\n'
        )
        if credentials.token is not None:
            output += f'$Env:AWS_SESSION_TOKEN="{credentials.token}"\n'
        if credentials.expiry_time is not None:
            output += (
                f'$Env:AWS_CREDENTIAL_EXPIRATION={credentials.expiry_time}\n'
            )
        self._stream.write(output)


class WindowsCmdFormatter(BaseCredentialFormatter):

    FORMAT = 'windows-cmd'

    def display_credentials(self, credentials):
        output = (
            f'set AWS_ACCESS_KEY_ID={credentials.access_key}\n'
            f'set AWS_SECRET_ACCESS_KEY={credentials.secret_key}\n'
        )
        if credentials.token is not None:
            output += f'set AWS_SESSION_TOKEN={credentials.token}\n'
        if credentials.expiry_time is not None:
            output += (
                f'set AWS_CREDENTIAL_EXPIRATION={credentials.expiry_time}\n'
            )
        self._stream.write(output)


class CredentialProcessFormatter(BaseCredentialFormatter):

    FORMAT = 'process'

    def display_credentials(self, credentials):
        output = {
            'Version': 1,
            'AccessKeyId': credentials.access_key,
            'SecretAccessKey': credentials.secret_key,
        }
        if credentials.token is not None:
            output['SessionToken'] = credentials.token
        if credentials.expiry_time is not None:
            output['Expiration'] = credentials.expiry_time
        self._stream.write(
            json.dumps(output, indent=2, separators=(',', ': '))
        )
        self._stream.write('\n')


SUPPORTED_FORMATS = {
    format_cls.FORMAT: format_cls for format_cls in
    [BashEnvVarFormatter, CredentialProcessFormatter, PowershellFormatter,
     WindowsCmdFormatter]
}


class ConfigureExportCredsCommand(BasicCommand):
    NAME = 'export-creds'
    SYNOPSIS = 'aws configure export-creds --profile profile-name'
    ARG_TABLE = [
        {'name': 'format',
         'help_text': (
             'The output format to display credentials.'
             'Defaults to "process".'),
         'action': 'store',
         'choices': list(SUPPORTED_FORMATS),
         'default': CredentialProcessFormatter.FORMAT},
    ]
    _RECURSION_VAR = '_AWS_CLI_PROFILE_CHAIN'
    # Two levels is reasonable because you might explicitly run
    # "aws configure export-creds" with a profile that is configured
    # with a credential_process of "aws configure export-creds".
    # So we'll give one more level of recursion for padding and then
    # error out when we hit _MAX_RECURSION.
    _MAX_RECURSION = 4

    def __init__(self, session, out_stream=None, error_stream=None, env=None):
        super(ConfigureExportCredsCommand, self).__init__(session)
        if out_stream is None:
            out_stream = sys.stdout
        if error_stream is None:
            error_stream = sys.stderr
        if env is None:
            env = os.environ
        self._out_stream = out_stream
        self._error_stream = error_stream
        self._env = env

    def _recursion_barrier_detected(self):
        profile = self._get_current_profile()
        seen_profiles = self._parse_profile_chain(
            self._env.get(self._RECURSION_VAR, ''))
        if len(seen_profiles) >= self._MAX_RECURSION:
            return True
        return profile in seen_profiles

    def _set_recursion_barrier(self):
        profile = self._get_current_profile()
        seen_profiles = self._parse_profile_chain(
            self._env.get(self._RECURSION_VAR, ''))
        seen_profiles.append(profile)
        serialized = self._serialize_to_csv_str(seen_profiles)
        self._env[self._RECURSION_VAR] = serialized

    def _serialize_to_csv_str(self, profiles):
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(profiles)
        serialized = out.getvalue().strip()
        return serialized

    def _get_current_profile(self):
        profile = self._session.get_config_variable('profile')
        if profile is None:
            profile = 'default'
        return profile

    def _parse_profile_chain(self, value):
        result = list(csv.reader([value]))[0]
        return result

    def _run_main(self, parsed_args, parsed_globals):
        if self._recursion_barrier_detected():
            self._error_stream.write(
                "\n\nRecursive credential resolution process detected.\n"
                "Try setting an explicit '--profile' value in the "
                "'credential_process' configuration and ensure there "
                "are no cycles:\n\n"
                "credential_process = aws configure export-creds "
                "--profile other-profile\n"
            )
            return 2
        self._set_recursion_barrier()
        try:
            creds = self._session.get_credentials()
        except Exception as e:
            self._error_stream.write(
                "Unable to retrieve credentials: %s\n" % e)
            return 1
        if creds is None:
            self._error_stream.write(
                "Unable to retrieve credentials: no credentials found\n")
            return 1
        creds_with_expiry = convert_botocore_credentials(creds)
        formatter = SUPPORTED_FORMATS[parsed_args.format](self._out_stream)
        formatter.display_credentials(creds_with_expiry)
