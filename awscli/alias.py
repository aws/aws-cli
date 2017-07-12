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

from awscli.compat import compat_shell_quote
from awscli.commands import CLICommand
from awscli.utils import emit_top_level_args_parsed_event


LOG = logging.getLogger(__name__)


class InvalidAliasException(Exception):
    pass


class AliasLoader(object):
    def __init__(self,
                 alias_filename=os.path.expanduser(
                     os.path.join('~', '.aws', 'cli', 'alias'))):
        """Interface for loading and interacting with alias file

        :param alias_filename: The name of the file to load aliases from.
            This file must be an INI file.
        """
        self._filename = alias_filename
        self._aliases = None

    def _build_aliases(self):
        self._aliases = self._load_aliases()
        self._cleanup_alias_values(self._aliases.get('toplevel', {}))

    def _load_aliases(self):
        if os.path.exists(self._filename):
            return raw_config_parse(
                self._filename, parse_subsections=False)
        return {'toplevel': {}}

    def _cleanup_alias_values(self, aliases):
        for alias in aliases:
            # Beginning and end line separators should not be included
            # in the internal representation of the alias value.
            aliases[alias] = aliases[alias].strip()

    def get_aliases(self):
        if self._aliases is None:
            self._build_aliases()
        return self._aliases.get('toplevel', {})


class AliasCommandInjector(object):
    def __init__(self, session, alias_loader):
        """Injects alias commands for a command table

        :type session: botocore.session.Session
        :param session: The botocore session

        :type alias_loader: awscli.alias.AliasLoader
        :param alias_loader: The alias loader to use
        """
        self._session = session
        self._alias_loader = alias_loader

    def inject_aliases(self, command_table, parser):
        for alias_name, alias_value in \
                self._alias_loader.get_aliases().items():
            if alias_value.startswith('!'):
                alias_cmd = ExternalAliasCommand(alias_name, alias_value)
            else:
                service_alias_cmd_args = [
                    alias_name, alias_value, self._session, command_table,
                    parser
                ]
                # If the alias name matches something already in the
                # command table provide the command it is about
                # to clobber as a possible reference that it will
                # need to proxy to.
                if alias_name in command_table:
                    service_alias_cmd_args.append(
                        command_table[alias_name])
                alias_cmd = ServiceAliasCommand(*service_alias_cmd_args)
            command_table[alias_name] = alias_cmd


class BaseAliasCommand(CLICommand):
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
                 parser, shadow_proxy_command=None):
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

        :type shadow_proxy_command: CLICommand
        :param shadow_proxy_command: A built-in command that
            potentially shadows the alias in name. If the alias
            references this command in its value, the alias should proxy
            to this command as oppposed to proxy to itself in the command
            table
        """
        super(ServiceAliasCommand, self).__init__(alias_name, alias_value)
        self._session = session
        self._command_table = command_table
        self._parser = parser
        self._shadow_proxy_command = shadow_proxy_command

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
        command = self._command_table[parsed_alias_args.command]
        if self._shadow_proxy_command:
            shadow_name = self._shadow_proxy_command.name
            # Use the shadow command only if the aliases value
            # uses that command indicating it needs to proxy over to
            # a built-in command.
            if shadow_name == parsed_alias_args.command:
                LOG.debug(
                    'Using shadowed command object: %s '
                    'for alias: %s', self._shadow_proxy_command,
                    self._alias_name
                )
                command = self._shadow_proxy_command
        return command(remaining, parsed_globals)

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
            # compare the parsed alias parameters to the default as
            # specified by the parser. If the parsed values from the alias
            # differs from the default value in the parser,
            # that global parameter must have been provided in the alias.
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
    def __init__(self, alias_name, alias_value, invoker=subprocess.call):
        """Command for external aliases

        Executes command external of CLI as opposed to being a proxy
        to another command.

        :type alias_name: string
        :param alias_name: The name of the alias

        :type alias_value: string
        :param alias_value: The parsed value of the alias. This can be
            retrieved from `AliasLoader.get_aliases()[alias_name]`

        :type invoker: callable
        :param invoker: Callable to run arguments of external alias. The
            signature should match that of ``subprocess.call``
        """
        self._alias_name = alias_name
        self._alias_value = alias_value
        self._invoker = invoker

    def __call__(self, args, parsed_globals):
        command_components = [
            self._alias_value[1:]
        ]
        command_components.extend(compat_shell_quote(a) for a in args)
        command = ' '.join(command_components)
        LOG.debug(
            'Using external alias %r with value: %r to run: %r',
            self._alias_name, self._alias_value, command)
        return self._invoker(command, shell=True)
