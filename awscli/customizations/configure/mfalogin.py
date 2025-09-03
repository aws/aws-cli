# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import logging
import os
import random
import string
import sys

# Import botocore at module level to avoid repeated imports
import botocore.session
from botocore.exceptions import ClientError, ProfileNotFound

from awscli.compat import compat_input
from awscli.customizations.commands import BasicCommand
from awscli.customizations.configure import profile_to_section
from awscli.customizations.configure.writer import ConfigFileWriter

LOG = logging.getLogger(__name__)


class InteractiveMFAPrompter:
    """Handles interactive prompting for MFA login."""

    def get_value(self, current_value, prompt_text=''):
        """Prompt for a value, showing the current value as a default."""
        response = compat_input(f"{prompt_text} [{current_value}]: ")
        if not response:
            # If the user hits enter, return the current value
            return current_value
        return response

    def get_credential_value(self, current_value, config_name, prompt_text=''):
        """Prompt for credential values with masking for sensitive data."""
        response = compat_input(f"{prompt_text}: ")
        if not response:
            return None
        return response


class ConfigureMFALoginCommand(BasicCommand):
    """Configures MFA login for AWS CLI by creating temporary credentials."""

    NAME = 'mfa-login'
    DESCRIPTION = BasicCommand.FROM_FILE(
        'configure', 'mfa-login', '_description.rst'
    )
    SYNOPSIS = (
        'aws configure mfa-login [--profile profile-name] '
        '[--update-profile profile-to-update] [--duration-seconds seconds] '
        '[--serial-number mfa-serial-number]'
    )
    EXAMPLES = BasicCommand.FROM_FILE('configure', 'mfa-login', '_examples.rst')
    ARG_TABLE = [
        {
            'name': 'update-profile',
            'help_text': (
                'The profile to update with temporary credentials. '
                'If not provided, a default name will be generated.'
            ),
            'action': 'store',
            'required': False,
            'cli_type_name': 'string',
        },
        {
            'name': 'duration-seconds',
            'help_text': (
                'The duration, in seconds, that the credentials should remain valid. '
                'Minimum is 900 seconds (15 minutes), maximum is 129600 seconds (36 hours).'
            ),
            'action': 'store',
            'required': False,
            'cli_type_name': 'integer',
            'default': 43200,
        },
        {
            'name': 'serial-number',
            'help_text': (
                'The ARN or serial number of the MFA device associated with the IAM user. '
                'If not provided, will use the mfa_serial from the profile configuration.'
            ),
            'action': 'store',
            'required': False,
            'cli_type_name': 'string',
        },
    ]

    # Values to prompt for during interactive setup
    VALUES_TO_PROMPT = [
        ('aws_access_key_id', 'AWS Access Key ID'),
        ('aws_secret_access_key', 'AWS Secret Access Key'),
        ('mfa_serial', 'MFA serial number or ARN'),
        ('mfa_token', 'MFA token code'),
    ]

    def __init__(self, session, prompter=None, config_writer=None):
        super().__init__(session)
        if prompter is None:
            prompter = InteractiveMFAPrompter()
        self._prompter = prompter
        if config_writer is None:
            config_writer = ConfigFileWriter()
        self._config_writer = config_writer

    def _generate_profile_name_from_mfa(self, mfa_serial):
        """Generate a deterministic profile name from MFA serial/ARN."""
        if mfa_serial.startswith('arn:aws:iam::'):
            # Parse ARN: arn:aws:iam::123456789012:mfa/device-name
            parts = mfa_serial.split(':')
            account_id = parts[4]
            device_name = parts[5].split('/')[-1]  # Get device name after 'mfa/'
            return f"{account_id}-{device_name}"
        else:
            # Assume it's just a serial number
            return f"session-{mfa_serial}"

    def _get_target_profile(self, parsed_args, mfa_serial=None):
        """Get or generate the target profile name."""
        target_profile = parsed_args.update_profile
        if not target_profile:
            if mfa_serial:
                target_profile = self._generate_profile_name_from_mfa(mfa_serial)
            else:
                target_profile = "session-temp"
            target_profile = self._prompter.get_value(
                target_profile, 'Profile to update'
            )
        return target_profile

    def _get_mfa_token(self):
        """Prompt for MFA token code."""
        token_code = self._prompter.get_credential_value(
            'None', 'mfa_token', 'MFA token code'
        )
        if not token_code:
            sys.stderr.write("MFA token code is required\n")
            return None
        return token_code

    def _call_sts_get_session_token(self, sts_client, duration_seconds, mfa_serial, token_code):
        """Call STS to get temporary credentials."""
        try:
            response = sts_client.get_session_token(
                DurationSeconds=duration_seconds,
                SerialNumber=mfa_serial,
                TokenCode=token_code,
            )
            return response
        except ClientError as e:
            sys.stderr.write(f"An error occurred: {e}\n")
            return None



    def _resolve_mfa_serial(self, parsed_args, source_config):
        """Resolve MFA serial from args, config, or prompt."""
        mfa_serial = parsed_args.serial_number or source_config.get('mfa_serial')
        if not mfa_serial:
            mfa_serial = self._prompter.get_credential_value(
                'None', 'mfa_serial', 'MFA serial number or ARN'
            )
            if not mfa_serial:
                sys.stderr.write("MFA serial number or MFA device ARN is required\n")
                return None
        return mfa_serial

    def _write_temporary_credentials(self, temp_credentials, target_profile):
        """Write temporary credentials to the credentials file."""
        credentials_file = os.path.expanduser(self._session.get_config_variable('credentials_file'))

        credential_values = {
            '__section__': target_profile,
            'aws_access_key_id': temp_credentials['AccessKeyId'],
            'aws_secret_access_key': temp_credentials['SecretAccessKey'],
            'aws_session_token': temp_credentials['SessionToken'],
        }

        try:
            expiration_time = temp_credentials['Expiration'].strftime(
                '%Y-%m-%d %H:%M:%S UTC'
            )
        except AttributeError:
            expiration_time = str(temp_credentials['Expiration'])

        self._config_writer.update_config(credential_values, credentials_file)

        sys.stdout.write(
            f"Temporary credentials written to profile '{target_profile}'\n"
        )
        sys.stdout.write(f"Credentials will expire at {expiration_time}\n")
        sys.stdout.write(
            f"To use these credentials, specify --profile {target_profile} when running AWS CLI commands\n"
        )
        return 0

    def _run_main(self, parsed_args, parsed_globals):
        duration_seconds = parsed_args.duration_seconds

        # Use the CLI session directly
        credentials = self._session.get_credentials()
        if credentials is None:
            return self._handle_interactive_prompting(parsed_args, duration_seconds)
        
        source_config = self._session.get_scoped_config()

        # Resolve MFA serial number
        mfa_serial = self._resolve_mfa_serial(parsed_args, source_config)
        if not mfa_serial:
            return 1

        # Get MFA token code
        token_code = self._get_mfa_token()
        if not token_code:
            return 1

        # Get the target profile name
        target_profile = self._get_target_profile(parsed_args, mfa_serial)

        # Call STS to get temporary credentials
        sts_client = self._session.create_client('sts')
        response = self._call_sts_get_session_token(
            sts_client, duration_seconds, mfa_serial, token_code
        )
        if not response:
            return 1

        # Write credentials and return
        return self._write_temporary_credentials(
            response['Credentials'], target_profile
        )

    def _handle_interactive_prompting(self, parsed_args, duration_seconds):
        """Handle the case where no default profile exists, and there is no profile explicitly named as a configuration source"""
        sys.stdout.write(
            "Please provide your AWS credentials:\n"
        )

        values = {}
        for config_name, prompt_text in self.VALUES_TO_PROMPT:
            if config_name == 'mfa_serial' and parsed_args.serial_number:
                values[config_name] = parsed_args.serial_number
                continue
                
            value = self._prompter.get_credential_value(
                'None', config_name, prompt_text
            )
            if not value or value == 'None':
                sys.stderr.write(f"{prompt_text} is required\n")
                return 1
            values[config_name] = value

        # Get the target profile name
        target_profile = self._get_target_profile(parsed_args, values['mfa_serial'])

        # Create STS client with the provided credentials
        session = botocore.session.Session()
        sts_client = session.create_client(
            'sts',
            aws_access_key_id=values['aws_access_key_id'],
            aws_secret_access_key=values['aws_secret_access_key'],
        )

        # Call STS to get temporary credentials
        response = self._call_sts_get_session_token(
            sts_client, duration_seconds, values['mfa_serial'], values['mfa_token']
        )
        if not response:
            return 1

        # Write credentials and return
        return self._write_temporary_credentials(
            response['Credentials'], target_profile
        )
