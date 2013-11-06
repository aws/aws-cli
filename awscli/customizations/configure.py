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
import os
import re
import logging

import six
from botocore.exceptions import ProfileNotFound

from awscli.customizations.commands import BasicCommand


try:
    raw_input = raw_input
except NameError:
    raw_input = input


logger = logging.getLogger(__name__)


def register_configure_cmd(cli):
    cli.register('building-command-table.main',
                 ConfigureCommand.add_command)

def add_configure_cmd(command_table, session, **kwargs):
    command_table['configure'] = ConfigureCommand(session)


class SectionNotFoundError(Exception):
    pass


class InteractivePrompter(object):
    def get_value(self, current_value, config_name, prompt_text=''):
        if config_name in ('aws_access_key_id', 'aws_secret_access_key'):
            current_value = self._mask_value(current_value)
        response = raw_input("%s [%s]: " % (prompt_text, current_value))
        if not response:
            # If the user hits enter, we return a value of None
            # instead of an empty string.  That way we can determine
            # whether or not a value has changed.
            response = None
        return response

    def _mask_value(self, current_value):
        if current_value is None:
            return 'None'
        else:
            return ('*' * 16) +  current_value[-4:]


class ConfigFileWriter(object):
    SECTION_REGEX = re.compile(r'\[(?P<header>[^]]+)\]')
    OPTION_REGEX = re.compile(
        r'(?P<option>[^:=\s][^:=]*)'
        r'\s*(?P<vi>[:=])\s*'
        r'(?P<value>.*)$'
    )

    def update_config(self, new_values, config_filename):
        section_name = new_values.pop('__section__', 'default')
        if not os.path.isfile(config_filename):
            self._create_file(config_filename)
            self._write_new_section(section_name, new_values, config_filename)
            return
        with open(config_filename, 'r') as f:
            contents = f.readlines()
        # We can only update a single section at a time so we first need
        # to find the section in question
        try:
            self._update_section_contents(contents, section_name, new_values)
            with open(config_filename, 'w') as f:
                f.write(''.join(contents))
        except SectionNotFoundError:
            self._write_new_section(section_name, new_values, config_filename)

    def _create_file(self, config_filename):
        # Create the file as well as the parent dir if needed.
        dirname, basename = os.path.split(config_filename)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        with os.fdopen(os.open(config_filename,
                               os.O_WRONLY|os.O_CREAT, 0o600), 'w') as f:
            pass

    def _write_new_section(self, section_name, new_values, config_filename):
        with open(config_filename, 'a') as f:
            f.write('[%s]\n' % section_name)
            for key, value in new_values.items():
                f.write('%s = %s\n' % (key, value))

    def _update_section_contents(self, contents, section_name, new_values):
        new_values = new_values.copy()
        # contents is a list of file line contents.
        start_index = 0
        for i in range(len(contents)):
            line = contents[i]
            match = self.SECTION_REGEX.search(line)
            if match is not None and self._matches_section(match,
                                                           section_name):
                break
        else:
            raise SectionNotFoundError(section_name)
        # If we get here, then we've found the section.  We now need
        # to figure out if we're updating a value or adding a new value.
        i += 1
        last_matching_line = i
        for j in range(i, len(contents)):
            line = contents[j]
            match = self.OPTION_REGEX.search(line)
            if match is not None:
                last_matching_line = j
                key_name = match.group(1).strip()
                if key_name in new_values:
                    new_line = '%s = %s\n' % (key_name, new_values[key_name])
                    contents[j] = new_line
                    del new_values[key_name]
            elif self.SECTION_REGEX.search(line) is not None:
                # We've hit a new section which means the config key is
                # not in the section.  We need to add it here.
                self._insert_new_values(line_number=last_matching_line,
                                        contents=contents,
                                        new_values=new_values)
                return

        if new_values:
            if not contents[-1].endswith('\n'):
                contents.append('\n')
            self._insert_new_values(line_number=last_matching_line + 1,
                                    contents=contents,
                                    new_values=new_values)

    def _insert_new_values(self, line_number, contents, new_values):
        new_contents = []
        for key, value in new_values.items():
            new_contents.append('%s = %s\n' % (key, value))
        contents.insert(line_number + 1, ''.join(new_contents))

    def _matches_section(self, match, section_name):
        parts = section_name.split(' ')
        unquoted_match = match.group(0) == '[%s]' % section_name
        if len(parts) > 1:
            quoted_match = match.group(0) == '[%s "%s"]' % (
                parts[0], ' '.join(parts[1:]))
            return unquoted_match or quoted_match
        return unquoted_match


class ConfigureCommand(BasicCommand):
    NAME = 'configure'
    DESCRIPTION = (
        'Configure AWS CLI configuration data.  If this command '
        'is run with no arguments, you will be prompted for configuration '
        'values such as your AWS Access Key Id and you AWS Secret Access '
        'Key.  You can configure a specific profile using the ``--profile`` '
        'argument.  If your config file does not exist (the default location '
        'is ``~/.aws/config``), it will be automatically created for you. '
        'To keep an existing value, hit enter when prompted for the value.\n\n'
        'When you are prompted for information, the current value will be '
        'displayed in ``[brackets]``.  If the config item has no value, it '
        'be displayed as ``[None]``.\n\n'
        'Note that the ``configure`` command only work with values from the '
        'config file.  It does not use any configuration values from '
        'environment variables or the IAM role.\n'
    )
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

    # If you want to add new values to prompt, update this list here.
    VALUES_TO_PROMPT = [
        # (logical_name, config_name, prompt_text)
        ('aws_access_key_id', "AWS Access Key ID"),
        ('aws_secret_access_key', "AWS Secret Access Key"),
        ('region', "Default region name"),
        ('output', "Default output format"),
    ]

    def __init__(self, session, prompter=None, config_writer=None):
        self._session = session
        if prompter is None:
            prompter = InteractivePrompter()
        self._prompter = prompter
        if config_writer is None:
            config_writer = ConfigFileWriter()
        self._config_writer = config_writer

    def _run_main(self, parsed_args, parsed_globals):
        # Called when invoked with no args "aws configure"
        new_values = {}
        if parsed_globals.profile is not None:
            profile = parsed_globals.profile
            self._session.profile = parsed_globals.profile
        # This is the config from the config file scoped to a specific
        # profile.
        try:
            config = self._session.get_config()
        except ProfileNotFound:
            config = {}
        for config_name, prompt_text in self.VALUES_TO_PROMPT:
            current_value = config.get(config_name)
            new_value = self._prompter.get_value(current_value, config_name,
                                                 prompt_text)
            if new_value is not None and new_value != current_value:
                new_values[config_name] = new_value
        config_filename = os.path.expanduser(
            self._session.get_variable('config_file'))
        if new_values:
            if parsed_globals.profile is not None:
                new_values['__section__'] = (
                    'profile %s' % parsed_globals.profile)
            self._config_writer.update_config(new_values, config_filename)
