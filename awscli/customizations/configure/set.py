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
import re

from awscli.customizations.commands import BasicCommand
from awscli.customizations.configure.writer import ConfigFileWriter

from . import PREDEFINED_SECTION_NAMES, profile_to_section


class ConfigureSetCommand(BasicCommand):
    NAME = 'set'
    DESCRIPTION = BasicCommand.FROM_FILE('configure', 'set',
                                         '_description.rst')
    SYNOPSIS = 'aws configure set varname value [--profile profile-name]'
    EXAMPLES = BasicCommand.FROM_FILE('configure', 'set', '_examples.rst')
    ARG_TABLE = [
        {'name': 'varname',
         'help_text': 'The name of the config value to set.',
         'action': 'store',
         'cli_type_name': 'string', 'positional_arg': True},
        {'name': 'value',
         'help_text': 'The value to set.',
         'action': 'store',
         'no_paramfile': True,  # To disable the default paramfile behavior
         'cli_type_name': 'string', 'positional_arg': True},
        {'name': 'profile-pattern',
         'help_text': 'Regexp pattern for profile names to update.',
         'action': 'store',
         'required': False,
         'cli_type_name': 'string', 'positional_arg': False},
    ]
    # Any variables specified in this list will be written to
    # the ~/.aws/credentials file instead of ~/.aws/config.
    _WRITE_TO_CREDS_FILE = ['aws_access_key_id', 'aws_secret_access_key',
                            'aws_session_token']

    def __init__(self, session, config_writer=None):
        super(ConfigureSetCommand, self).__init__(session)
        if config_writer is None:
            config_writer = ConfigFileWriter()
        self._config_writer = config_writer

    def _get_sections_for_pattern(self, args):
        if args.profile_pattern:
            return [
                profile_to_section(profile)
                for profile in self._session.full_config.get('profiles', [])
                if re.match(args.profile_pattern, profile)
            ]
        return []

    def _parse_varname(self, varname):
        """
        :return:  sections: list of of one section to update
                  varname: name of the variable
                  key: list where first element will be key if input value
                       should be dict
        """
        if '.' not in varname:
            # just a varname without section and key
            return [], varname, []
        else:
            parts = varname.split('.')
            if parts[0] == 'default':
                return [parts[0]], parts[1], parts[2:]
            if parts[0] == 'profile':
                # [profile, profile_name, ...]
                return [profile_to_section(parts[1])], parts[2], parts[3:]
            if parts[0] not in PREDEFINED_SECTION_NAMES:
                return [], parts[0], parts[1:]
            if len(parts) == 2:
                # Otherwise it's something in the [plugin] section
                return [parts[0]], parts[1], []
            return [], varname, []

    def _run_main(self, args, parsed_globals):
        # Before handing things off to the config writer,
        # we need to find out three things:
        # 1. What section we're writing to (section).
        # 2. The name of the config key (varname)
        # 3. The actual value (value).
        sections, varname, key = self._parse_varname(args.varname)
        value = {key[0]: args.value} if len(key) == 1 else args.value
        sections = self._get_sections_for_pattern(args) or sections
        if not sections:
            # unqualified name, scope it to the current
            # profile (or leave it as the 'default' section if
            # no profile is set).
            if self._session.profile is not None:
                sections = [profile_to_section(self._session.profile)]
            else:
                profile_name = self._session.get_config_variable('profile')
                if profile_name is not None:
                    sections = [profile_name]
                else:
                    sections = ['default']
        config_filename = os.path.expanduser(
            self._session.get_config_variable('config_file'))
        updated_config = {varname: value}
        if varname in self._WRITE_TO_CREDS_FILE:
            config_filename = os.path.expanduser(
                self._session.get_config_variable('credentials_file'))
            sections = [name[8:] if name.startswith('profile ') else name
                        for name in sections]
        for section in sections:
            updated_config['__section__'] = section
            self._config_writer.update_config(updated_config,
                                              config_filename)
        return 0
