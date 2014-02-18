# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import webbrowser

from botocore.compat import json, urlencode
import botocore.vendored.requests

from awscli.customizations.commands import BasicCommand
from awscli.customizations.commands import BasicDocHandler
from awscli.customizations.utils import InteractivePrompter


LOG = logging.getLogger(__name__)

issuer_url = 'https://mysignin.internal.mycompany.com/'
console_url = 'https://console.aws.amazon.com/'
signin_url = 'https://signin.aws.amazon.com/federation'


def register_session_cmd(cli):
    cli.register('building-command-table.main',
                 SessionCommand.add_command)


class NoTemporaryCredentialsError(Exception):
    pass

    
class SessionDocHandler(BasicDocHandler):

    def doc_subitems_start(self, help_command, **kwargs):
        self.doc.style.h2('Available Commands')

    def doc_subitem(self, command_name, help_command, **kwargs):
        doc = help_command.doc
        doc.style.tocitem(command_name)

    def doc_subitems_end(self, help_command, **kwargs):
        pass


class StartCommand(BasicCommand):
    
    NAME = 'start'
    DESCRIPTION = 'Start a new session.'
    SYNOPSIS = ('aws session start [mfa-serial-number SN]'
                '[--assume-role role-arn]')
    EXAMPLES = (
        'To start a new session::\n'
        '\n'
        '    $aws session start\n'
        '\n'
        'To start a new MFA session::\n'
        '\n'
        '    $ aws session start --mfa-serial-number\n'
        '    MFA Token [None]: token\n'
        '\n'
        'You can store your MFA serial number in your config file '
        'using the name mfa_serial_number.\n\n'
        'To start a session and assume an IAM Role::\n'
        '\n'
        '    $ aws session start --assume-role role_arn\n'
    )
    ARG_TABLE = [
        {'name': 'mfa-serial-number',
         'help_text': 'The serial number of your MFA device, if needed.',
         'action': 'store', 'cli_type_name': 'String'},
        {'name': 'role-arn', 'help_text': 'Assume an IAM Role',
         'action': 'store', 'required': False, 'cli_type_name': 'string'}]

    def __init__(self, session, prompter=None):
        super(StartCommand, self).__init__(session)
        if prompter is None:
            prompter = InteractivePrompter()
        self._prompter = prompter

    def _run_main(self, parsed_args, parsed_globals):
        if parsed_args.role_arn is not None:
            self._session.create_temporary_credentials(
                'sts', 'AssumeRole', role_arn=parsed_args.role_arn,
                role_session_name='awscli')
        else:
            serial_number = parsed_args.mfa_serial_number
            token = None
            if serial_number is None:
                serial_number = self._session.get_variable('mfa_serial_number')
            if serial_number:
                token = self._prompter.get_value('', 'mfa_token', 'MFA Token')
            self._session.create_temporary_credentials(
                'sts', 'GetSessionToken', serial_number=serial_number,
                token_code=token)


class EndCommand(BasicCommand):

    NAME = 'end'
    DESCRIPTION = 'End the current session.'
    SYNOPSIS = 'aws session end'
    EXAMPLES = (
        '\n'
        'To clear temporary credentials and use regular credentials::\n'
        '\n'
        '    $ aws session end\n'
    )

    def _run_main(self, parsed_args, parsed_globals):
        self._session.delete_temporary_credentials()


class ConsoleCommand(BasicCommand):

    NAME = 'console'
    DESCRIPTION = 'Launch the web console using temporary credentials.'
    SYNOPSIS = 'aws session console'
    EXAMPLES = (
        '\n'
        'To open the AWS web console in a new tab of your default '
        'browser:\n'
        '    $ aws session console\n'
    )

    def _run_main(self, parsed_args, parsed_globals):
        creds = self._session.get_credentials()
        if not creds.token:
            msg = ('The console can only be launched with '
                   'temporary credentials.')
            raise NoTemporaryCredentialsError(msg)
        session_data = {'sessionId': creds.access_key,
                        'sessionKey': creds.secret_key,
                        'sessionToken': creds.token}
        session = json.dumps(session_data)
        params = {'Action': 'getSigninToken',
                  'Session': session}
        r = botocore.vendored.requests.get(signin_url, params=params)
        params = json.loads(r.text)
        params['Action'] = 'login'
        params['Issuer'] = 'foo'
        params['Destination'] = console_url
        url = signin_url + '?' + urlencode(params)
        webbrowser.open(url)


class SessionCommand(BasicCommand):
    NAME = 'session'
    DESCRIPTION = 'The description'
    SYNOPSIS = 'aws session start|end|help'
    EXAMPLES = 'put examples here'
    SUBCOMMANDS = [
        {'name': 'start', 'command_class': StartCommand},
        {'name': 'end', 'command_class': EndCommand},
        {'name': 'console', 'command_class': ConsoleCommand}
    ]
