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
from awscli.customizations.exceptions import ParamValidationError
from awscli.customizations.utils import validate_mutually_exclusive

from . import (
    PREDEFINED_SECTION_NAMES,
    SUBSECTION_TYPE_ALLOWLIST,
    get_section_header,
    profile_to_section,
)


class ConfigureSetCommand(BasicCommand):
    NAME = 'set'
    DESCRIPTION = BasicCommand.FROM_FILE(
        'configure', 'set', '_description.rst'
    )
    SYNOPSIS = 'aws configure set varname value [--profile profile-name]'
    EXAMPLES = BasicCommand.FROM_FILE('configure', 'set', '_examples.rst')
    ARG_TABLE = [
        {
            'name': 'varname',
            'help_text': 'The name of the config value to set.',
            'action': 'store',
            'cli_type_name': 'string',
            'positional_arg': True,
        },
        {
            'name': 'value',
            'help_text': 'The value to set.',
            'action': 'store',
            'no_paramfile': True,  # To disable the default paramfile behavior
            'cli_type_name': 'string',
            'positional_arg': True,
        },
        {
            'name': 'sso-session',
            'help_text': 'The name of the SSO session sub-section to configure.',
            'action': 'store',
            'cli_type_name': 'string',
            'group_name': 'subsection',
        },
        {
            'name': 'services',
            'help_text': 'The name of the services sub-section to configure.',
            'action': 'store',
            'cli_type_name': 'string',
            'group_name': 'subsection',
        },
    ]
    # Any variables specified in this list will be written to
    # the ~/.aws/credentials file instead of ~/.aws/config.
    _WRITE_TO_CREDS_FILE = [
        'aws_access_key_id',
        'aws_secret_access_key',
        'aws_session_token',
    ]

    def __init__(self, session, config_writer=None):
        super(ConfigureSetCommand, self).__init__(session)
        if config_writer is None:
            config_writer = ConfigFileWriter()
        self._config_writer = config_writer

    def _get_config_file(self, path):
        config_path = self._session.get_config_variable(path)
        return os.path.expanduser(config_path)

    def _subsection_parameter_to_argument_name(self, parameter_name):
        return parameter_name.replace("-", "_")

    def _get_subsection_from_args(self, args):
        # Validate mutual exclusivity of sub-section type parameters
        groups = [[self._subsection_parameter_to_argument_name(key)] for key in SUBSECTION_TYPE_ALLOWLIST.keys()]
        validate_mutually_exclusive(args, *groups)

        subsection_name = None
        subsection_type = None

        for section_type in SUBSECTION_TYPE_ALLOWLIST.keys():
            cli_parameter_name = self._subsection_parameter_to_argument_name(section_type)
            if hasattr(args, cli_parameter_name):
                subsection_name = getattr(args, cli_parameter_name)
                if subsection_name is not None:
                    if not re.match(r"[\w\d_\-/.%@:\+]+", subsection_name):
                        raise ParamValidationError(
                            f"aws: [ERROR]: Invalid value for --{section_type}."
                        )
                    subsection_type = section_type
                    break

        return (subsection_type, subsection_name)


    def _set_subsection_property(self, section_type, section_name, varname, value):
        if '.' in varname:
            parts = varname.split('.')
            # Check if there are more than two parts to the property name to set (e.g., aaa.bbb.ccc)
            # This would result in a deeply nested property, which is not supported. 
            if len(parts) > 2:
                raise ParamValidationError(
                    "Found more than two parts in the property to set. "
                    "Deep nesting of properties is not supported."
                )
            varname = parts[0]
            value = {parts[1]: value}
        
        # Build update dict
        updated_config = {
            '__section__': get_section_header(section_type, section_name), 
            varname: value
        }

        # Write to config file
        config_filename = self._get_config_file('config_file')
        self._config_writer.update_config(updated_config, config_filename)
        
        return 0
    
    def _run_main(self, args, parsed_globals):
        varname = args.varname
        value = args.value
        profile = 'default'

        section_type, section_name = self._get_subsection_from_args(args)
        if section_type is not None:
            return self._set_subsection_property(section_type, section_name, varname, value)

        # Not in a sub-section, continue with previous profile logic.
        # Before handing things off to the config writer,
        # we need to find out three things:
        # 1. What section we're writing to (profile).
        # 2. The name of the config key (varname)
        # 3. The actual value (value).
        if '.' not in varname:
            # unqualified name, scope it to the current
            # profile (or leave it as the 'default' section if
            # no profile is set).
            if self._session.profile is not None:
                profile = self._session.profile
        else:
            # First figure out if it's been scoped to a profile.
            parts = varname.split('.')
            if parts[0] in ('default', 'profile'):
                # Then we know we're scoped to a profile.
                if parts[0] == 'default':
                    profile = 'default'
                    remaining = parts[1:]
                else:
                    # [profile, profile_name, ...]
                    profile = parts[1]
                    remaining = parts[2:]
                varname = remaining[0]
                if len(remaining) == 2:
                    value = {remaining[1]: value}
            elif parts[0] not in PREDEFINED_SECTION_NAMES:
                if self._session.profile is not None:
                    profile = self._session.profile
                else:
                    profile_name = self._session.get_config_variable('profile')
                    if profile_name is not None:
                        profile = profile_name
                varname = parts[0]
                if len(parts) == 2:
                    value = {parts[1]: value}
            elif len(parts) == 2:
                # Otherwise it's something in the [plugin] section
                profile, varname = parts
        config_filename = self._get_config_file('config_file')
        if varname in self._WRITE_TO_CREDS_FILE:
            # When writing to the creds file, the section is just the profile
            section = profile
            config_filename = self._get_config_file('credentials_file')
        elif profile in PREDEFINED_SECTION_NAMES or profile == 'default':
            section = profile
        else:
            section = profile_to_section(profile)
        updated_config = {'__section__': section, varname: value}
        self._config_writer.update_config(updated_config, config_filename)
        return 0
