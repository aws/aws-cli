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
import os
import logging

from botocore.exceptions import ProfileNotFound

from awscli.compat import compat_input
from awscli.customizations.commands import BasicCommand
from awscli.customizations.configure.addmodel import AddModelCommand
from awscli.customizations.configure.set import ConfigureSetCommand
from awscli.customizations.configure.get import ConfigureGetCommand
from awscli.customizations.configure.list import ConfigureListCommand
from awscli.customizations.configure.writer import ConfigFileWriter

from . import mask_value, profile_to_section


logger = logging.getLogger(__name__)


def register_configure_cmd(cli):
    cli.register('building-command-table.main',
                 ConfigureCommand.add_command)


class InteractivePrompter(object):

    def get_value(self, current_value, config_name, prompt_text=''):
        if config_name in ('aws_access_key_id', 'aws_secret_access_key'):
            current_value = mask_value(current_value)
        response = compat_input("%s [%s]: " % (prompt_text, current_value))
        if not response:
            # If the user hits enter, we return a value of None
            # instead of an empty string.  That way we can determine
            # whether or not a value has changed.
            response = None
        return response


class ConfigureCommand(BasicCommand):
    NAME = 'configure'
    DESCRIPTION = BasicCommand.FROM_FILE()
    SYNOPSIS = ('aws configure [--profile profile-name]')
    EXAMPLES = (
        'To create a new configuration::\n'
        '\n'
        '    $ aws configure\n'
        '    AWS Access Key ID [None]: accesskey\n'
        '    AWS Secret Access Key [None]: secretkey\n'
        '    Default region name [None]: us-west-2\n'
        '    Default output format [None]:\n'
        '\n'
        'To update just the region name::\n'
        '\n'
        '    $ aws configure\n'
        '    AWS Access Key ID [****]:\n'
        '    AWS Secret Access Key [****]:\n'
        '    Default region name [us-west-1]: us-west-2\n'
        '    Default output format [None]:\n'
    )
    SUBCOMMANDS = [
        {'name': 'list', 'command_class': ConfigureListCommand},
        {'name': 'get', 'command_class': ConfigureGetCommand},
        {'name': 'set', 'command_class': ConfigureSetCommand},
        {'name': 'add-model', 'command_class': AddModelCommand}
    ]

    # If you want to add new values to prompt, update this list here.
    VALUES_TO_PROMPT = [
        # (logical_name, config_name, prompt_text)
        ('aws_access_key_id', "AWS Access Key ID"),
        ('aws_secret_access_key', "AWS Secret Access Key"),
        ('region', "Default region name"),
        ('output', "Default output format"),
    ]

    def __init__(self, session, prompter=None, config_writer=None):
        super(ConfigureCommand, self).__init__(session)
        if prompter is None:
            prompter = InteractivePrompter()
        self._prompter = prompter
        if config_writer is None:
            config_writer = ConfigFileWriter()
        self._config_writer = config_writer

    def _run_main(self, parsed_args, parsed_globals):
        # Called when invoked with no args "aws configure"
        new_values = {}
        # This is the config from the config file scoped to a specific
        # profile.
        try:
            config = self._session.get_scoped_config()
        except ProfileNotFound:
            config = {}
        for config_name, prompt_text in self.VALUES_TO_PROMPT:
            current_value = config.get(config_name)
            new_value = self._prompter.get_value(current_value, config_name,
                                                 prompt_text)
            if new_value is not None and new_value != current_value:
                new_values[config_name] = new_value
        config_filename = os.path.expanduser(
            self._session.get_config_variable('config_file'))
        if new_values:
            profile = self._session.profile
            self._write_out_creds_file_values(new_values, profile)
            if profile is not None:
                section = profile_to_section(profile)
                new_values['__section__'] = section
            self._config_writer.update_config(new_values, config_filename)

    def _write_out_creds_file_values(self, new_values, profile_name):
        # The access_key/secret_key are now *always* written to the shared
        # credentials file (~/.aws/credentials), see aws/aws-cli#847.
        # post-conditions: ~/.aws/credentials will have the updated credential
        # file values and new_values will have the cred vars removed.
        credential_file_values = {}
        if 'aws_access_key_id' in new_values:
            credential_file_values['aws_access_key_id'] = new_values.pop(
                'aws_access_key_id')
        if 'aws_secret_access_key' in new_values:
            credential_file_values['aws_secret_access_key'] = new_values.pop(
                'aws_secret_access_key')
        if credential_file_values:
            if profile_name is not None:
                credential_file_values['__section__'] = profile_name
            shared_credentials_filename = os.path.expanduser(
                self._session.get_config_variable('credentials_file'))
            self._config_writer.update_config(
                credential_file_values,
                shared_credentials_filename)
