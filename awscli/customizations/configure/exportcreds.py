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
from awscli.customizations.exceptions import ConfigurationError


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
    DOCUMENTATION = ""

    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        self._stream = stream

    def display_credentials(self, credentials):
        pass


class BasePerLineFormatter(BaseCredentialFormatter):

    _VAR_FORMAT = 'export {var_name}={var_value}'

    def display_credentials(self, credentials):
        output = (
            self._format_line('AWS_ACCESS_KEY_ID', credentials.access_key) +
            self._format_line('AWS_SECRET_ACCESS_KEY', credentials.secret_key))
        if credentials.token is not None:
            output += self._format_line('AWS_SESSION_TOKEN', credentials.token)
        if credentials.expiry_time is not None:
            output += self._format_line(
                'AWS_CREDENTIAL_EXPIRATION', credentials.expiry_time)
        self._stream.write(output)

    def _format_line(self, var_name, var_value):
        return self._VAR_FORMAT.format(
            var_name=var_name, var_value=var_value) + '\n'


class BashEnvVarFormatter(BasePerLineFormatter):

    FORMAT = 'env'
    DOCUMENTATION = (
        "Display credentials as exported shell variables: "
        "``export AWS_ACCESS_KEY_ID=EXAMPLE``"
    )
    _VAR_FORMAT = 'export {var_name}={var_value}'


class BashNoExportEnvFormatter(BasePerLineFormatter):

    FORMAT = 'env-no-export'
    DOCUMENTATION = (
        "Display credentials as non-exported shell variables: "
        "``AWS_ACCESS_KEY_ID=EXAMPLE``"
    )
    _VAR_FORMAT = '{var_name}={var_value}'


class PowershellFormatter(BasePerLineFormatter):

    FORMAT = 'powershell'
    DOCUMENTATION = (
        'Display credentials as PowerShell environment variables: '
        '``$Env:AWS_ACCESS_KEY_ID="EXAMPLE"``'
    )
    _VAR_FORMAT = '$Env:{var_name}="{var_value}"'


class WindowsCmdFormatter(BasePerLineFormatter):

    FORMAT = 'windows-cmd'
    DOCUMENTATION = (
        'Display credentials as Windows cmd environment variables: '
        '``set AWS_ACCESS_KEY_ID=EXAMPLE``'
    )
    _VAR_FORMAT = 'set {var_name}={var_value}'


class CredentialProcessFormatter(BaseCredentialFormatter):

    FORMAT = 'process'
    DOCUMENTATION = (
        "Display credentials as JSON output, in the schema "
        "expected by the ``credential_process`` config value."
        "This enables any library or tool that supports "
        "``credential_process`` to use the AWS CLI's credential "
        "resolution process: ``credential_process = aws configure "
        "export-credentials --profile myprofile``"
    )

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
    [CredentialProcessFormatter, BashEnvVarFormatter, BashNoExportEnvFormatter,
     PowershellFormatter, WindowsCmdFormatter]
}


def generate_docs(formats):
    lines = ['The output format to display credentials.  '
             'Defaults to `process`.  ', '<ul>']
    for name, cls in formats.items():
        line = f'<li>``{name}`` - {cls.DOCUMENTATION} </li>'
        lines.append(line)
    lines.append('</ul>')
    return '\n'.join(lines)


class ConfigureExportCredentialsCommand(BasicCommand):

    NAME = 'export-credentials'
    SYNOPSIS = 'aws configure export-credentials --profile profile-name'
    DESCRIPTION = (
        "Export credentials in various formats.  This command will retrieve "
        "AWS credentials using the AWS CLI's credential resolution process "
        "and display the credentials in the specified ``--format``. By "
        "default, the output format is ``process``, which is a JSON format "
        "that's expected by the credential process feature supported by the "
        "AWS SDKs and Tools.  This command ignores the global ``--query`` and "
        "``--output`` options."
    )
    ARG_TABLE = [
        {'name': 'format',
         'help_text': generate_docs(SUPPORTED_FORMATS),
         'action': 'store',
         'choices': list(SUPPORTED_FORMATS),
         'default': CredentialProcessFormatter.FORMAT},
    ]
    _RECURSION_VAR = '_AWS_CLI_PROFILE_CHAIN'
    # Two levels is reasonable because you might explicitly run
    # "aws configure export-credentials" with a profile that is configured
    # with a credential_process of "aws configure export-credentials".
    # So we'll give one more level of recursion for padding and then
    # error out when we hit _MAX_RECURSION.
    _MAX_RECURSION = 4

    def __init__(self, session, out_stream=None, error_stream=None, env=None):
        super(ConfigureExportCredentialsCommand, self).__init__(session)
        if out_stream is None:
            out_stream = sys.stdout
        if error_stream is None:
            error_stream = sys.stderr
        if env is None:
            env = os.environ
        self._out_stream = out_stream
        self._error_stream = error_stream
        self._env = env

    def _detect_recursion_barrier(self):
        profile = self._get_current_profile()
        seen_profiles = self._parse_profile_chain(
            self._env.get(self._RECURSION_VAR, ''))
        if len(seen_profiles) >= self._MAX_RECURSION:
            raise ConfigurationError(
                f"Maximum recursive credential process resolution reached "
                f"({self._MAX_RECURSION}).\n"
                f"Profiles seen: {' -> '.join(seen_profiles)}"
            )
        if profile in seen_profiles:
            raise ConfigurationError(
                f"Credential process resolution detected an infinite loop, "
                f"profile cycle: {' -> '.join(seen_profiles + [profile])}\n"
            )

    def _update_recursion_barrier(self):
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
        self._detect_recursion_barrier()
        self._update_recursion_barrier()
        try:
            creds = self._session.get_credentials()
        except Exception as e:
            original_msg = str(e).strip()
            raise ConfigurationError(
                f"Unable to retrieve credentials: {original_msg}\n")
        if creds is None:
            raise ConfigurationError(
                "Unable to retrieve credentials: no credentials found")
        creds_with_expiry = convert_botocore_credentials(creds)
        formatter = SUPPORTED_FORMATS[parsed_args.format](self._out_stream)
        formatter.display_credentials(creds_with_expiry)
