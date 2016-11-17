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
import os
import shlex
import subprocess

from botocore.configloader import raw_config_parse

from awscli.utils import emit_top_level_args_parsed_event


LOG = logging.getLogger(__name__)


class InvalidAliasException(Exception):
    pass


class AliasLoader(object):
    ALIAS_FILENAME = os.path.expanduser(
        os.path.join('~', '.aws', 'cli', 'alias'))

    def __init__(self, alias_filename=None):
        """Interface for loading and interacting with alias file

        :param alias_filename: The name of the file to load aliases from.
            This file must be an INI file. If no filename is provided,
            the value of ALIAS_FILENAME will be used.
        """
        self._filename = alias_filename
        if alias_filename is None:
            self._filename = self.ALIAS_FILENAME
        self._aliases = self._load_aliases()
        self._cleanup_alias_values()

    def _load_aliases(self):
        if os.path.exists(self._filename):
            return raw_config_parse(
                self._filename, parse_subsections=False)
        return {'toplevel': {}}

    def _cleanup_alias_values(self):
        aliases = self.get_aliases()
        for alias in aliases:
            # Beginning and end line separators should not be included
            # in the internal representation of the alias value.
            aliases[alias] = aliases[alias].strip(os.linesep)

    def get_aliases(self):
        return self._aliases.get('toplevel', {})


class BaseAliasCommand(object):
    _UNDOCUMENTED = True

    def __init__(self, alias_name, alias_value):
        """Base class for alias command

        :type alias_name: string
        :param alias_name: The name of the alias

        :type alias_value: string
        :param alias_value: The parsed value of the alias. This can be
            retrieved from `AliasLoader.get_aliases()[alias_name]`
        """
        self._alias_name = alias_name
        self._alias_value = alias_value

    def __call__(self, args, parsed_args):
        raise NotImplementedError('__call__')

    @property
    def name(self):
        return self._alias_name

    @name.setter
    def name(self, value):
        self._alias_name = value


class ServiceAliasCommand(BaseAliasCommand):
    UNSUPPORTED_GLOBAL_PARAMETERS = [
        'debug',
        'profile'
    ]

    def __init__(self, alias_name, alias_value, session, command_table,
                 parser):
        """Command for a `toplevel` subcommand alias

        :type alias_name: string
        :param alias_name: The name of the alias

        :type alias_value: string
        :param alias_value: The parsed value of the alias. This can be
            retrieved from `AliasLoader.get_aliases()[alias_name]`

        :type session: botocore.session.Session
        :param session: The botocore session

        :type command_table: dict
        :param command_table: The command table containing all of the
            possible service command objects that a particular alias could
            redirect to.

        :type parser: awscli.argparser.MainArgParser
        :param parser: The parser to parse commands provided at the top level
            of a CLI command which includes service commands and global
            parameters. This is used to parse the service commmand and any
            global parameters from the alias's value.
        """
        super(ServiceAliasCommand, self).__init__(alias_name, alias_value)
        self._session = session
        self._command_table = command_table
        self._parser = parser

    def __call__(self, args, parsed_globals):
        alias_args = self._get_alias_args()
        parsed_alias_args, remaining = self._parser.parse_known_args(
            alias_args)
        self._update_parsed_globals(parsed_alias_args, parsed_globals)
        # Take any of the remaining arguments that were not parsed out and
        # prepend them to the remaining args provided to the alias.
        remaining.extend(args)
        LOG.debug(
            'Alias %r passing on arguments: %r to %r command',
            self._alias_name, remaining, parsed_alias_args.command)
        # Pass the update remaing args and global args to the service command
        # the alias proxied to.
        return self._command_table[parsed_alias_args.command](
            remaining, parsed_globals)

    def _get_alias_args(self):
        try:
            alias_args = shlex.split(self._alias_value)
        except ValueError as e:
            raise InvalidAliasException(
                'Value of alias "%s" could not be parsed. '
                'Received error: %s when parsing:\n%s' % (
                    self._alias_name, e, self._alias_value)
            )

        alias_args = [arg.strip(os.linesep) for arg in alias_args]
        LOG.debug(
            'Expanded subcommand alias %r with value: %r to: %r',
            self._alias_name, self._alias_value, alias_args
        )
        return alias_args

    def _update_parsed_globals(self, parsed_alias_args, parsed_globals):
        global_params_to_update = self._get_global_parameters_to_update(
            parsed_alias_args)
        # Emit the top level args parsed event to ensure all possible
        # customizations that typically get applied are applied to the
        # global parameters provided in the alias before updating
        # the original provided global parameter values
        # and passing those onto subsequent commands.
        emit_top_level_args_parsed_event(self._session, parsed_alias_args)
        for param_name in global_params_to_update:
            updated_param_value = getattr(parsed_alias_args, param_name)
            setattr(parsed_globals, param_name, updated_param_value)

    def _get_global_parameters_to_update(self, parsed_alias_args):
        # Retrieve a list of global parameters that the newly parsed args
        # from the alias will have to clobber from the originally provided
        # parsed globals.
        global_params_to_update = []
        for parsed_param, value in vars(parsed_alias_args).items():
            # To determine which parameters in the alias were global values
            # compare the parsed parameter to its default as specified by
            # the parser. If the parsed value differs from the default value
            # that global parameter must have been provided.
            if self._parser.get_default(parsed_param) != value:
                if parsed_param in self.UNSUPPORTED_GLOBAL_PARAMETERS:
                    raise InvalidAliasException(
                        'Global parameter "--%s" detected in alias "%s" '
                        'which is not support in subcommand aliases.' % (
                            parsed_param, self._alias_name))
                else:
                    global_params_to_update.append(parsed_param)
        return global_params_to_update


class ExternalAliasCommand(BaseAliasCommand):
    """Command for `toplevel` external alias"""
    def __call__(self, args, parsed_globals):
        command_components = [
            self._alias_value.lstrip('!')
        ]
        command_components.extend(args)
        command = ' '.join(command_components)
        LOG.debug(
            'Using external alias %r with value: %r to run: %r',
            self._alias_name, self._alias_value, command)
        return subprocess.call(command, shell=True)
