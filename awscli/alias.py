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


def register_alias_commands(event_handlers, alias_filename=None):
    kwargs = {}
    if alias_filename is not None:
        kwargs['alias_filename'] = alias_filename
    alias_injector = AliasSubCommandInjector(AliasLoader(**kwargs))
    event_handlers.register(
        'building-command-table',
        alias_injector.on_building_command_table
    )


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
        self._cleanup_alias_values(self._aliases)

    def _load_aliases(self):
        parsed = {}
        if os.path.exists(self._filename):
            parsed = raw_config_parse(
                self._filename, parse_subsections=False)
        self._normalize_key_names(parsed)
        return parsed

    def _normalize_key_names(self, parsed):
        for key in list(parsed):
            if key.startswith('command '):
                new_key = tuple(key.split())
                value = parsed.pop(key)
                parsed[new_key] = value

    def _cleanup_alias_values(self, all_aliases):
        for section_aliases in all_aliases.values():
            for alias in section_aliases:
                # Beginning and end line separators should not be included
                # in the internal representation of the alias value.
                section_aliases[alias] = section_aliases[alias].strip()

    def get_aliases(self, command=None):
        # To preserve existing behavior, get_alises() with no args
        # will return the top level aliases, i.e `[topleve]`.
        # However, you can now get aliases for a specific section by
        # providing a command key which is a tuple of the command
        # lineage, i.e. `('ec2', 'wait',)`.
        if command is None:
            key = 'toplevel'
        else:
            key = ('command',) + tuple(command)
        if self._aliases is None:
            self._build_aliases()
        return self._aliases.get(key, {})


class BaseAliasCommandInjector(object):
    def __init__(self, alias_loader):
        self._alias_loader = alias_loader

    def _get_alias_items(self, command=None):
        return self._alias_loader.get_aliases(command=command).items()

    def _is_external_alias(self, alias_value):
        return alias_value.startswith('!')

    def _inject_external_alias(self, alias_name, alias_value, command_table):
        command_table[alias_name] = ExternalAliasCommand(
            alias_name, alias_value)


class AliasCommandInjector(BaseAliasCommandInjector):
    def __init__(self, session, alias_loader):
        """Injects alias commands for a command table

        :type session: botocore.session.Session
        :param session: The botocore session

        :type alias_loader: awscli.alias.AliasLoader
        :param alias_loader: The alias loader to use
        """
        super(AliasCommandInjector, self).__init__(alias_loader)
        self._session = session

    def inject_aliases(self, command_table, parser):
        for alias_name, alias_value in self._get_alias_items():
            if self._is_external_alias(alias_value):
                self._inject_external_alias(alias_name, alias_value,
                                            command_table)
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


class AliasSubCommandInjector(BaseAliasCommandInjector):
    def __init__(self, alias_loader):
        super(AliasSubCommandInjector, self).__init__(alias_loader)
        self._global_cmd_driver = None
        self._global_args_parser = None

    def _retrieve_global_args_parser(self):
        if self._global_args_parser is None:
            if self._global_cmd_driver is not None:
                command_table = self._global_cmd_driver.subcommand_table
                self._global_args_parser = \
                    self._global_cmd_driver.create_parser(command_table)
        return self._global_args_parser

    def on_building_command_table(self, command_table, event_name,
                                  command_object, session, **kwargs):
        if not isinstance(command_object, CLICommand) and \
                event_name == 'building-command-table.main':
            self._global_cmd_driver = command_object
            return
        key_name = tuple(event_name.split('.', 1)[1].split('_'))
        aliases_for_cmd = self._alias_loader.get_aliases(command=key_name)
        if not aliases_for_cmd:
            return
        for alias_name, alias_value in aliases_for_cmd.items():
            if self._is_external_alias(alias_value):
                self._inject_external_alias(
                    alias_name, alias_value, command_table)
            else:
                proxied_sub_command = command_table.get(alias_name)
                command_table[alias_name] = InternalAliasSubCommand(
                    alias_name, alias_value, command_object,
                    self._retrieve_global_args_parser(),
                    session=session,
                    proxied_sub_command=proxied_sub_command)


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
        self._lineage = [self]

    def __call__(self, args, parsed_args):
        raise NotImplementedError('__call__')

    @property
    def name(self):
        return self._alias_name

    @name.setter
    def name(self, value):
        self._alias_name = value

    @property
    def lineage(self):
        return self._lineage

    @lineage.setter
    def lineage(self, value):
        self._lineage = value


class BaseInternalAliasCommand(BaseAliasCommand):
    UNSUPPORTED_GLOBAL_PARAMETERS = [
        'debug',
        'profile'
    ]

    def __init__(self, alias_name, alias_value, session):
        super(BaseInternalAliasCommand, self).__init__(alias_name, alias_value)
        self._session = session

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

    def _update_parsed_globals(self, arg_parser, parsed_alias_args,
                               parsed_globals):
        global_params_to_update = self._get_global_parameters_to_update(
            arg_parser, parsed_alias_args)
        # Emit the top level args parsed event to ensure all possible
        # customizations that typically get applied are applied to the
        # global parameters provided in the alias before updating
        # the original provided global parameter values
        # and passing those onto subsequent commands.
        emit_top_level_args_parsed_event(self._session, parsed_alias_args)
        for param_name in global_params_to_update:
            updated_param_value = getattr(parsed_alias_args, param_name)
            setattr(parsed_globals, param_name, updated_param_value)

    def _get_global_parameters_to_update(self, arg_parser, parsed_alias_args):
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
            if arg_parser.get_default(parsed_param) != value:
                if parsed_param in self.UNSUPPORTED_GLOBAL_PARAMETERS:
                    raise InvalidAliasException(
                        'Global parameter "--%s" detected in alias "%s" '
                        'which is not support in subcommand aliases.' % (
                            parsed_param, self._alias_name))
                else:
                    global_params_to_update.append(parsed_param)
        return global_params_to_update


class ServiceAliasCommand(BaseInternalAliasCommand):
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
            parameters. This is used to parse the service command and any
            global parameters from the alias's value.

        :type shadow_proxy_command: CLICommand
        :param shadow_proxy_command: A built-in command that
            potentially shadows the alias in name. If the alias
            references this command in its value, the alias should proxy
            to this command as opposed to proxy to itself in the command
            table
        """
        super(ServiceAliasCommand, self).__init__(
            alias_name, alias_value, session)
        self._command_table = command_table
        self._parser = parser
        self._shadow_proxy_command = shadow_proxy_command

    def __call__(self, args, parsed_globals):
        alias_args = self._get_alias_args()
        parsed_alias_args, remaining = self._parser.parse_known_args(
            alias_args)
        self._update_parsed_globals(self._parser, parsed_alias_args,
                                    parsed_globals)
        # Take any of the remaining arguments that were not parsed out and
        # prepend them to the remaining args provided to the alias.
        remaining.extend(args)
        LOG.debug(
            'Alias %r passing on arguments: %r to %r command',
            self._alias_name, remaining, parsed_alias_args.command)
        # Pass the update remaining args and global args to the service command
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
        super(ExternalAliasCommand, self).__init__(alias_name, alias_value)
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


class InternalAliasSubCommand(BaseInternalAliasCommand):

    def __init__(self, alias_name, alias_value, command_object,
                 global_args_parser, session,
                 proxied_sub_command=None):
        super(InternalAliasSubCommand, self).__init__(
            alias_name, alias_value, session)
        self._command_object = command_object
        self._global_args_parser = global_args_parser
        self._proxied_sub_command = proxied_sub_command

    def _process_global_args(self, arg_parser, alias_args, parsed_globals):
        globally_parseable_args = [parsed_globals.command] + alias_args
        alias_globals, remaining = arg_parser\
            .parse_known_args(globally_parseable_args)
        self._update_parsed_globals(arg_parser, alias_globals, parsed_globals)
        return remaining

    def __call__(self, args, parsed_globals):
        # args - Args explicitly provided by the user when
        #   invoking this command.
        # parsed_globals - Global args explicitly provided by the user
        #  that we've already parsed.
        # alias_args - Any args (including the command name) that are
        #  embedded as part of the alias value (i.e defined in the alias file)
        alias_args = self._get_alias_args()
        cmd_specific_args = self._process_global_args(
            self._global_args_parser, alias_args, parsed_globals)
        cmd_specific_args.extend(args)
        if self._proxied_sub_command is not None:
            # If we overwrote an existing command, we just delegate to that
            # command we proxied to.  We know that when this happens, the
            # first argument will match the command associated with this
            # command so we remove that value before delegating to the
            # proxied command.
            cmd_specific_args = cmd_specific_args[1:]
            LOG.debug("Delegating to proxy sub-command with new alias "
                      "args: %s", alias_args)
            return self._proxied_sub_command(cmd_specific_args, parsed_globals)
        else:
            return self._command_object(cmd_specific_args, parsed_globals)
