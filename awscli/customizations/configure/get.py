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
import logging
import re
import sys

from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ParamValidationError
from awscli.customizations.utils import validate_mutually_exclusive

from . import PREDEFINED_SECTION_NAMES, SUBSECTION_TYPE_ALLOWLIST, SubsectionNotFoundError

LOG = logging.getLogger(__name__)


class ConfigureGetCommand(BasicCommand):
    NAME = 'get'
    DESCRIPTION = BasicCommand.FROM_FILE(
        'configure', 'get', '_description.rst'
    )
    SYNOPSIS = 'aws configure get varname [--profile profile-name]'
    EXAMPLES = BasicCommand.FROM_FILE('configure', 'get', '_examples.rst')
    ARG_TABLE = [
        {
            'name': 'varname',
            'help_text': 'The name of the config value to retrieve.',
            'action': 'store',
            'cli_type_name': 'string',
            'positional_arg': True,
        },
        {
            'name': 'sso-session',
            'help_text': 'The name of the sub-section to configure.',
            'action': 'store',
            'cli_type_name': 'string',
        },
        {
            'name': 'services',
            'help_text': 'The name of the sub-section to configure.',
            'action': 'store',
            'cli_type_name': 'string',
        },
    ]

    def __init__(self, session, stream=None, error_stream=None):
        super(ConfigureGetCommand, self).__init__(session)
        if stream is None:
            stream = sys.stdout
        if error_stream is None:
            error_stream = sys.stderr
        self._stream = stream
        self._error_stream = error_stream

    def _subsection_parameter_to_argument_name(self, parameter_name):
        return parameter_name.replace("-", "_")

    def _get_subsection_config_name_from_args(self, args):
        # Validate mutual exclusivity of sub-section type parameters
        groups = [
            [self._subsection_parameter_to_argument_name(key)]
            for key in SUBSECTION_TYPE_ALLOWLIST.keys()
        ]
        validate_mutually_exclusive(args, *groups)

        subsection_name = None
        subsection_config_name = None

        for (
            section_type,
            section_properties,
        ) in SUBSECTION_TYPE_ALLOWLIST.items():
            cli_parameter_name = self._subsection_parameter_to_argument_name(
                section_type
            )

            if hasattr(args, cli_parameter_name):
                subsection_name = getattr(args, cli_parameter_name)
                if subsection_name is not None:
                    subsection_config_name = section_properties[
                        'full_config_name'
                    ]
                    break

        return (subsection_config_name, subsection_name)

    def _run_main(self, args, parsed_globals):
        varname = args.varname
        section_type, section_name = self._get_subsection_config_name_from_args(args)

        if section_type:
            value = self._get_subsection_property(
                section_type.replace("-", "_"),
                section_name,
                varname
            )
        elif '.' not in varname:
            # get_scoped_config() returns the config variables in the config
            # file (not the logical_var names), which is what we want.
            config = self._session.get_scoped_config()
            value = config.get(varname)
        else:
            value = self._get_dotted_config_value(varname)

        LOG.debug('Config value retrieved: %s' % value)

        if isinstance(value, str):
            self._stream.write(value)
            self._stream.write('\n')
            return 0
        elif isinstance(value, dict):
            # TODO: add support for this. We would need to print it off in
            # the same format as the config file.
            self._error_stream.write(
                'varname (%s) must reference a value, not a section or '
                'sub-section.' % varname
            )
            return 1
        else:
            return 1

    def _get_dotted_config_value(self, varname):
        parts = varname.split('.')
        num_dots = varname.count('.')

        # Logic to deal with predefined sections like [plugin] etc.
        if num_dots == 1 and parts[0] in PREDEFINED_SECTION_NAMES:
            full_config = self._session.full_config
            section, config_name = varname.split('.')
            value = full_config.get(section, {}).get(config_name)
            if value is None:
                # Try to retrieve it from the profile config.
                value = (
                    full_config['profiles'].get(section, {}).get(config_name)
                )
            return value

        if parts[0] == 'profile':
            profile_name = parts[1]
            config_name = parts[2]
            remaining = parts[3:]
        # Check if varname starts with 'default' profile (e.g.
        # default.emr-dev.emr.instance_profile) If not, go further to check
        # if varname starts with a known profile name
        elif parts[0] == 'default' or (
            parts[0] in self._session.full_config['profiles']
        ):
            profile_name = parts[0]
            config_name = parts[1]
            remaining = parts[2:]
        else:
            profile_name = self._session.get_config_variable('profile')
            if profile_name is None:
                profile_name = 'default'
            config_name = parts[0]
            remaining = parts[1:]

        value = (
            self._session.full_config['profiles']
            .get(profile_name, {})
            .get(config_name)
        )
        if len(remaining) == 1:
            try:
                value = value.get(remaining[-1])
            except AttributeError:
                value = None
        return value

    def _get_subsection_property(self, section_type, section_name, varname):
        full_config = self._session.full_config

        if section_type not in full_config:
            raise SubsectionNotFoundError(f"The config sub-section ({section_name}) could not be found ")

        section_type_config = full_config[section_type]
        section_config = section_type_config.get(section_name, None)

        if section_config is None:
            raise SubsectionNotFoundError(f"The config sub-section ({section_name}) could not be found ")

        # Handle nested properties
        if '.' in varname:
            parts = varname.split('.')
            if len(parts) == 2:
                value = section_config.get(parts[0])
                if isinstance(value, dict):
                    return value.get(parts[1])
                else:
                    return None
        else:
            return section_config.get(varname)
