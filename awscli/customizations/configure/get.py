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
import logging

from awscli.customizations.commands import BasicCommand

from . import PREDEFINED_SECTION_NAMES

LOG = logging.getLogger(__name__)


class ConfigureGetCommand(BasicCommand):
    NAME = 'get'
    DESCRIPTION = BasicCommand.FROM_FILE('configure', 'get',
                                         '_description.rst')
    SYNOPSIS = 'aws configure get varname [--profile profile-name]'
    EXAMPLES = BasicCommand.FROM_FILE('configure', 'get', '_examples.rst')
    ARG_TABLE = [
        {'name': 'varname',
         'help_text': 'The name of the config value to retrieve.',
         'action': 'store',
         'cli_type_name': 'string', 'positional_arg': True},
    ]

    def __init__(self, session, stream=None, error_stream=None):
        super(ConfigureGetCommand, self).__init__(session)
        if stream is None:
            stream = sys.stdout
        if error_stream is None:
            error_stream = sys.stderr
        self._stream = stream
        self._error_stream = error_stream

    def _run_main(self, args, parsed_globals):
        varname = args.varname

        if '.' not in varname:
            # get_scoped_config() returns the config variables in the config
            # file (not the logical_var names), which is what we want.
            config = self._session.get_scoped_config()
            value = config.get(varname)
        else:
            value = self._get_dotted_config_value(varname)

        LOG.debug(u'Config value retrieved: %s' % value)

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

        # Logic to deal with predefined sections like [preview], [plugin] and
        # etc.
        if num_dots == 1 and parts[0] in PREDEFINED_SECTION_NAMES:
            full_config = self._session.full_config
            section, config_name = varname.split('.')
            value = full_config.get(section, {}).get(config_name)
            if value is None:
                # Try to retrieve it from the profile config.
                value = full_config['profiles'].get(
                    section, {}).get(config_name)
            return value

        if parts[0] == 'profile':
            profile_name = parts[1]
            config_name = parts[2]
            remaining = parts[3:]
        # Check if varname starts with 'default' profile (e.g.
        # default.emr-dev.emr.instance_profile) If not, go further to check
        # if varname starts with a known profile name
        elif parts[0] == 'default' or (
                parts[0] in self._session.full_config['profiles']):
            profile_name = parts[0]
            config_name = parts[1]
            remaining = parts[2:]
        else:
            profile_name = self._session.get_config_variable('profile')
            if profile_name is None:
                profile_name = 'default'
            config_name = parts[0]
            remaining = parts[1:]

        value = self._session.full_config['profiles'].get(
            profile_name, {}).get(config_name)
        if len(remaining) == 1:
            try:
                value = value.get(remaining[-1])
            except AttributeError:
                value = None
        return value
