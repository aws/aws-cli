# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import sys

from botocore.credentials import Credentials

from awscli.arguments import create_argument_model_from_schema
from awscli.compat import compat_input
from awscli.customizations.commands import BasicCommand
from awscli.customizations.configure.writer import ConfigFileWriter


CONFIG_KEY_MFA_SERIAL_NUMBER = 'aws_mfa_serial_number'
CONFIG_KEY_ACCESS_KEY_ID = 'aws_access_key_id'
CONFIG_KEY_SECRET_ACCESS_KEY = 'aws_secret_access_key'
CONFIG_KEY_SESSION_TOKEN = 'aws_session_token'
CONFIG_KEY_ACCESS_KEY_ID_SAVED = '%s_saved' % CONFIG_KEY_ACCESS_KEY_ID
CONFIG_KEY_SECRET_ACCESS_KEY_SAVED = '%s_saved' % CONFIG_KEY_SECRET_ACCESS_KEY


def get_saved_credentials(session):
    """
    Return saved credentials (ie. non-temporary ones) if they are present, else
    default to credentials already set in the given session.

    :type session: botocore.session.Session
    :rtype: botocore.credentials.Credentials
    """
    config = session.get_scoped_config()
    access_key = config.get(CONFIG_KEY_ACCESS_KEY_ID_SAVED)
    secret_key = config.get(CONFIG_KEY_SECRET_ACCESS_KEY_SAVED)

    if access_key is None or secret_key is None:
        return session.get_credentials()

    return Credentials(
        access_key=access_key, secret_key=secret_key, token=None)


class ConfigureMfaCommand(BasicCommand):
    NAME = 'mfa'
    DESCRIPTION = BasicCommand.FROM_FILE('configure', 'mfa',
                                         '_description.rst')
    SYNOPSIS = 'aws configure mfa ' \
               '[--duration-seconds seconds] ' \
               '[--serial-number mfa_serial_number] ' \
               '[--token mfa_token] ' \
               '[--profile profile-name]'
    EXAMPLES = BasicCommand.FROM_FILE('configure', 'mfa', '_examples.rst')
    ARG_TABLE = [
        {'name': 'duration-seconds',
         'help_text': 'Duration in seconds for session validity.',
         'default': 43200,
         'argument_model': create_argument_model_from_schema({
             'type': 'integer'}),
         'action': 'store',
         'required': False,
         'cli_type_name': 'string', 'positional_arg': False},
        {'name': 'serial-number',
         'help_text': 'The serial number of the MFA device to use when '
                      'requesting temporary credentials.',
         'action': 'store',
         'required': False,
         'cli_type_name': 'string', 'positional_arg': False},
        {'name': 'token',
         'help_text': 'The MFA token to use when requesting temporary '
                      'credentials.',
         'action': 'store',
         'required': False,
         'cli_type_name': 'string', 'positional_arg': False},
    ]

    def __init__(self, session, config_writer=None):
        super(ConfigureMfaCommand, self).__init__(session)
        if config_writer is None:
            config_writer = ConfigFileWriter()
        self._config_writer = config_writer

    def refresh_temporary_credentials(
            self, duration=43200, mfa_serial_number=None, mfa_token=None):
        saved_credentials = get_saved_credentials(session=self._session)
        self._session.set_credentials(
            access_key=saved_credentials.access_key,
            secret_key=saved_credentials.secret_key,
            token=None)

        if mfa_serial_number is None:
            mfa_serial_number = self.get_mfa_serial_number()

        if mfa_token is None:
            mfa_token = compat_input("MFA token: ")

        if not mfa_token:
            raise ValueError('MFA token required.')
        elif len(mfa_token) < 6:
            raise ValueError('MFA token is required to be at least 6 long.')

        client = self._session.create_client('sts')
        response = client.get_session_token(
            DurationSeconds=duration,
            SerialNumber=mfa_serial_number,
            TokenCode=mfa_token).get('Credentials')

        access_key_id = response.get('AccessKeyId')
        secret_access_key = response.get('SecretAccessKey')
        session_token = response.get('SessionToken')

        from awscli.customizations.configure.set import ConfigureSetCommand
        set_command = ConfigureSetCommand(self._session, self._config_writer)

        # set saved values only if they never existed
        if saved_credentials.access_key is not None \
                and saved_credentials.secret_key is not None:
            set_command(
                args=[CONFIG_KEY_ACCESS_KEY_ID_SAVED, saved_credentials.access_key],
                parsed_globals=None)
            set_command(
                args=[CONFIG_KEY_SECRET_ACCESS_KEY_SAVED, saved_credentials.secret_key],
                parsed_globals=None)

        set_command(
            args=[CONFIG_KEY_ACCESS_KEY_ID, access_key_id],
            parsed_globals=None)
        set_command(
            args=[CONFIG_KEY_SECRET_ACCESS_KEY, secret_access_key],
            parsed_globals=None)
        set_command(
            args=[CONFIG_KEY_SESSION_TOKEN, session_token],
            parsed_globals=None)

    def get_mfa_serial_number(self):
        from awscli.customizations.configure.set import ConfigureSetCommand
        config = self._session.get_scoped_config()
        mfa_serial_number = config.get(CONFIG_KEY_MFA_SERIAL_NUMBER)
        if mfa_serial_number is None:
            mfa_serial_number = self.select_mfa_device()
            set_command = ConfigureSetCommand(
                self._session, self._config_writer)
            set_command(
                args=[CONFIG_KEY_MFA_SERIAL_NUMBER, mfa_serial_number],
                parsed_globals=None)
        return mfa_serial_number

    def select_mfa_device(self):
        client = self._session.create_client('iam')
        mfa_devices = [
            device['SerialNumber']
            for device in client.list_mfa_devices()['MFADevices']
        ]

        mfa_device_count = len(mfa_devices)
        if mfa_device_count == 0:
            raise Exception('No MFA device configured. '
                            'Refer to http://docs.aws.amazon.com/IAM/latest/'
                            'UserGuide/id_credentials_mfa_enable_virtual.html '
                            'for information on how to add one.')
        elif mfa_device_count == 1:
            # if there is only one device configured, use it
            return mfa_devices.pop()

        for i in range(len(mfa_devices)):
            sys.stdout.write('[%d] %s\n' % (i, mfa_devices[i]))

        response = compat_input("Select MFA Device [0]: ")
        if not response:
            response = 0

        try:
            return mfa_devices.pop(int(response))
        except (ValueError, IndexError):
            raise Exception(
                'Invalid Choice. Please select a number from the list.')

    def _run_main(self, parsed_args, parsed_globals):
        self.refresh_temporary_credentials(
            duration=parsed_args.duration_seconds,
            mfa_serial_number=parsed_args.serial_number,
            mfa_token=parsed_args.token
        )
