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

    def _run_main(self, args, parsed_globals):
        varname = args.varname
        value = args.value
        section = 'default'
        # Before handing things off to the config writer,
        # we need to find out three things:
        # 1. What section we're writing to (section).
        # 2. The name of the config key (varname)
        # 3. The actual value (value).
        if '.' not in varname:
            # unqualified name, scope it to the current
            # profile (or leave it as the 'default' section if
            # no profile is set).
            if self._session.profile is not None:
                section = profile_to_section(self._session.profile)
        else:
            # First figure out if it's been scoped to a profile.
            parts = varname.split('.')
            if parts[0] in ('default', 'profile'):
                # Then we know we're scoped to a profile.
                if parts[0] == 'default':
                    section = 'default'
                    remaining = parts[1:]
                else:
                    # [profile, profile_name, ...]
                    section = profile_to_section(parts[1])
                    remaining = parts[2:]
                varname = remaining[0]
                if len(remaining) == 2:
                    value = {remaining[1]: value}
            elif parts[0] not in PREDEFINED_SECTION_NAMES:
                if self._session.profile is not None:
                    section = profile_to_section(self._session.profile)
                else:
                    profile_name = self._session.get_config_variable('profile')
                    if profile_name is not None:
                        section = profile_name
                varname = parts[0]
                if len(parts) == 2:
                    value = {parts[1]: value}
            elif len(parts) == 2:
                # Otherwise it's something like "set preview.service true"
                # of something in the [plugin] section.
                section, varname = parts
        config_filename = os.path.expanduser(
            self._session.get_config_variable('config_file'))
        updated_config = {'__section__': section, varname: value}
        if varname in self._WRITE_TO_CREDS_FILE:
            config_filename = os.path.expanduser(
                self._session.get_config_variable('credentials_file'))
            section_name = updated_config['__section__']
            if section_name.startswith('profile '):
                updated_config['__section__'] = section_name[8:]
        self._config_writer.update_config(updated_config, config_filename)
