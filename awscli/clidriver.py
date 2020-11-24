# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import json
import os
import platform
import sys
import logging

import distro

import botocore.session
from botocore import xform_name
from botocore.compat import copy_kwargs, OrderedDict
from botocore.history import get_global_history_recorder
from botocore.configprovider import InstanceVarProvider
from botocore.configprovider import EnvironmentProvider
from botocore.configprovider import ScopedConfigProvider
from botocore.configprovider import ConstantProvider
from botocore.configprovider import ChainProvider

from awscli import __version__
from awscli.compat import (
    default_pager, get_stderr_text_writer, get_stdout_text_writer
)
from awscli.formatter import get_formatter
from awscli.plugin import load_plugins
from awscli.commands import CLICommand
from awscli.argparser import MainArgParser
from awscli.argparser import FirstPassGlobalArgParser
from awscli.argparser import ServiceArgParser
from awscli.argparser import ArgTableArgParser
from awscli.help import ProviderHelpCommand
from awscli.help import ServiceHelpCommand
from awscli.help import OperationHelpCommand
from awscli.arguments import CustomArgument
from awscli.arguments import ListArgument
from awscli.arguments import BooleanArgument
from awscli.arguments import CLIArgument
from awscli.arguments import UnknownArgumentError
from awscli.argprocess import unpack_argument
from awscli.alias import AliasLoader
from awscli.alias import AliasCommandInjector
from awscli.logger import set_stream_logger, remove_stream_logger
from awscli.utils import emit_top_level_args_parsed_event
from awscli.utils import OutputStreamFactory
from awscli.utils import IMDSRegionProvider
from awscli.constants import PARAM_VALIDATION_ERROR_RC
from awscli.autoprompt.core import AutoPromptDriver
from awscli.errorhandler import (
    construct_cli_error_handlers_chain, construct_entry_point_handlers_chain
)


LOG = logging.getLogger('awscli.clidriver')
LOG_FORMAT = (
    '%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')
HISTORY_RECORDER = get_global_history_recorder()
METADATA_FILENAME = 'metadata.json'
# Don't remove this line.  The idna encoding
# is used by getaddrinfo when dealing with unicode hostnames,
# and in some cases, there appears to be a race condition
# where threads will get a LookupError on getaddrinfo() saying
# that the encoding doesn't exist.  Using the idna encoding before
# running any CLI code (and any threads it may create) ensures that
# the encodings.idna is imported and registered in the codecs registry,
# which will stop the LookupErrors from happening.
# See: https://bugs.python.org/issue29288
u''.encode('idna')


def main():
    return AWSCLIEntryPoint().main(sys.argv[1:])


def create_clidriver(args=None):
    debug = None
    if args is not None:
        parser = FirstPassGlobalArgParser()
        args, _ = parser.parse_known_args(args)
        debug = args.debug
    session = botocore.session.Session()
    _set_user_agent_for_session(session)
    load_plugins(session.full_config.get('plugins', {}),
                 event_hooks=session.get_component('event_emitter'))
    error_handlers_chain = construct_cli_error_handlers_chain()
    driver = CLIDriver(session=session,
                       error_handler=error_handlers_chain,
                       debug=debug)
    return driver


def _get_distribution_source():
    metadata_file = os.path.join(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'),
        METADATA_FILENAME
    )
    metadata = {}
    if os.path.isfile(metadata_file):
        with open(metadata_file) as f:
            metadata = json.load(f)
    return metadata.get('distribution_source', 'other')


def _get_distribution():
    distribution = None
    if platform.system() == 'Linux':
        distribution = _get_linux_distribution()
    return distribution


def _get_linux_distribution():
    linux_distribution = 'unknown'
    try:
        linux_distribution = distro.id()
        version = distro.major_version()
        if version:
            linux_distribution += '.%s' % version
    except Exception:
        pass
    return linux_distribution


def _set_user_agent_for_session(session):
    session.user_agent_name = 'aws-cli'
    session.user_agent_version = __version__
    # user_agent_extra on linux will look like "rpm/x86_64.Ubuntu.18"
    # on mac and windows like "sources/x86_64"
    session.user_agent_extra = '%s/%s' % (
        _get_distribution_source(),
        platform.machine()
    )
    linux_distribution = _get_distribution()
    if linux_distribution:
        session.user_agent_extra += ".%s" % linux_distribution


def no_pager_handler(session, parsed_args, **kwargs):
    if parsed_args.no_cli_pager:
        config_store = session.get_component('config_store')
        config_store.set_config_provider(
            'pager', ConstantProvider(value=None)
        )


class AWSCLIEntryPoint:
    def __init__(self, driver=None):
        self._error_handler = construct_entry_point_handlers_chain()
        self._driver = driver

    def main(self, args):
        try:
            rc = self._do_main(args)
        except BaseException as e:
            LOG.debug("Exception caught in AWSCLIEntryPoint", exc_info=True)
            return self._error_handler.handle_exception(
                e,
                stdout=get_stdout_text_writer(),
                stderr=get_stderr_text_writer()
            )

        HISTORY_RECORDER.record('CLI_RC', rc, 'CLI')
        return rc

    def _run_driver(self, driver, args, prompt_mode):
        driver.session.user_agent_extra += " prompt/%s" % prompt_mode
        return driver.main(args)

    def _do_main(self, args):
        driver = self._driver
        if driver is None:
            driver = create_clidriver(args)
        autoprompt_driver = AutoPromptDriver(driver)
        auto_prompt_mode = autoprompt_driver.resolve_mode(args)
        if auto_prompt_mode == 'on':
            args = autoprompt_driver.prompt_for_args(args)
            rc = self._run_driver(driver, args, prompt_mode='on')
        elif auto_prompt_mode == 'on-partial':
            autoprompt_driver.inject_silence_param_error_msg_handler(driver)
            rc = self._run_driver(driver, args, prompt_mode='off')
            if rc == PARAM_VALIDATION_ERROR_RC:
                args = autoprompt_driver.prompt_for_args(args)
                driver = create_clidriver(args)
                rc = self._run_driver(driver, args, prompt_mode='partial')
        else:
            rc = self._run_driver(driver, args, prompt_mode='off')
        return rc


class CLIDriver(object):

    def __init__(self, session=None, error_handler=None,
                 debug=False):
        if session is None:
            self.session = botocore.session.get_session()
            _set_user_agent_for_session(self.session)
        else:
            self.session = session
        self._error_handler = error_handler
        if self._error_handler is None:
            self._error_handler = construct_cli_error_handlers_chain()
        if debug:
            self._set_logging(debug)
        self._update_config_chain()
        self._cli_data = None
        self._command_table = None
        self._argument_table = None
        self.alias_loader = AliasLoader()

    def _update_config_chain(self):
        config_store = self.session.get_component('config_store')
        config_store.set_config_provider(
            'region',
            self._construct_cli_region_chain()
        )
        config_store.set_config_provider(
            'output',
            self._construct_cli_output_chain()
        )
        config_store.set_config_provider(
            'pager',
            self._construct_cli_pager_chain()
        )
        config_store.set_config_provider(
            'cli_binary_format',
            self._construct_cli_binary_format_chain()
        )
        config_store.set_config_provider(
            'cli_auto_prompt',
            self._construct_cli_auto_prompt_chain()
        )

    def _construct_cli_region_chain(self):
        providers = [
            InstanceVarProvider(
                instance_var='region',
                session=self.session
            ),
            EnvironmentProvider(
                name='AWS_REGION',
                env=os.environ,
            ),
            EnvironmentProvider(
                name='AWS_DEFAULT_REGION',
                env=os.environ,
            ),
            ScopedConfigProvider(
                config_var_name='region',
                session=self.session,
            ),
            IMDSRegionProvider(self.session),
        ]
        return ChainProvider(providers=providers)

    def _construct_cli_output_chain(self):
        providers = [
            InstanceVarProvider(
                instance_var='output',
                session=self.session,
            ),
            EnvironmentProvider(
                name='AWS_DEFAULT_OUTPUT',
                env=os.environ,
            ),
            ScopedConfigProvider(
                config_var_name='output',
                session=self.session,
            ),
            ConstantProvider(value='json'),
        ]
        return ChainProvider(providers=providers)

    def _construct_cli_pager_chain(self):
        providers = [
            EnvironmentProvider(
                name='AWS_PAGER',
                env=os.environ,
            ),
            ScopedConfigProvider(
                config_var_name='cli_pager',
                session=self.session,
            ),
            EnvironmentProvider(
                name='PAGER',
                env=os.environ,
            ),
            ConstantProvider(value=default_pager),
        ]
        return ChainProvider(providers=providers)

    def _construct_cli_binary_format_chain(self):
        providers = [
            ScopedConfigProvider(
                config_var_name='cli_binary_format',
                session=self.session,
            ),
            ConstantProvider(value='base64'),
        ]
        return ChainProvider(providers=providers)

    def _construct_cli_auto_prompt_chain(self):
        providers = [
            InstanceVarProvider(
                instance_var='cli_auto_prompt',
                session=self.session,
            ),
            EnvironmentProvider(
                name='AWS_CLI_AUTO_PROMPT',
                env=os.environ,
            ),
            ScopedConfigProvider(
                config_var_name='cli_auto_prompt',
                session=self.session
            ),
            ConstantProvider(value='off'),
        ]
        return ChainProvider(providers=providers)

    @property
    def subcommand_table(self):
        return self._get_command_table()

    @property
    def arg_table(self):
        return self._get_argument_table()

    @property
    def error_handler(self):
        return self._error_handler

    def _get_cli_data(self):
        # Not crazy about this but the data in here is needed in
        # several places (e.g. MainArgParser, ProviderHelp) so
        # we load it here once.
        if self._cli_data is None:
            self._cli_data = self.session.get_data('cli')
        return self._cli_data

    def _get_command_table(self):
        if self._command_table is None:
            self._command_table = self._build_command_table()
        return self._command_table

    def _get_argument_table(self):
        if self._argument_table is None:
            self._argument_table = self._build_argument_table()
        return self._argument_table

    def _build_command_table(self):
        """
        Create the main parser to handle the global arguments.

        :rtype: ``argparser.ArgumentParser``
        :return: The parser object

        """
        command_table = self._build_builtin_commands(self.session)
        self.session.emit('building-command-table.main',
                          command_table=command_table,
                          session=self.session,
                          command_object=self)
        return command_table

    def _build_builtin_commands(self, session):
        commands = OrderedDict()
        services = session.get_available_services()
        for service_name in services:
            commands[service_name] = ServiceCommand(cli_name=service_name,
                                                    session=self.session,
                                                    service_name=service_name)
        return commands

    def _add_aliases(self, command_table, parser):
        parser = self.create_parser(command_table)
        injector = AliasCommandInjector(
            self.session, self.alias_loader)
        injector.inject_aliases(command_table, parser)

    def _build_argument_table(self):
        argument_table = OrderedDict()
        cli_data = self._get_cli_data()
        cli_arguments = cli_data.get('options', None)
        for option in cli_arguments:
            option_params = copy_kwargs(cli_arguments[option])
            cli_argument = self._create_cli_argument(option, option_params)
            cli_argument.add_to_arg_table(argument_table)
        # Then the final step is to send out an event so handlers
        # can add extra arguments or modify existing arguments.
        self.session.emit('building-top-level-params',
                          session=self.session,
                          argument_table=argument_table,
                          driver=self)
        return argument_table

    def _create_cli_argument(self, option_name, option_params):
        return CustomArgument(
            option_name, help_text=option_params.get('help', ''),
            dest=option_params.get('dest'),
            default=option_params.get('default'),
            action=option_params.get('action'),
            required=option_params.get('required'),
            choices=option_params.get('choices'),
            cli_type_name=option_params.get('type'))

    def create_help_command(self):
        cli_data = self._get_cli_data()
        return ProviderHelpCommand(self.session, self._get_command_table(),
                                   self._get_argument_table(),
                                   cli_data.get('description', None),
                                   cli_data.get('synopsis', None),
                                   cli_data.get('help_usage', None))

    def create_parser(self, command_table):
        # Also add a 'help' command.
        command_table['help'] = self.create_help_command()
        cli_data = self._get_cli_data()
        parser = MainArgParser(
            command_table, self.session.user_agent(),
            cli_data.get('description', None),
            self._get_argument_table(),
            prog="aws")
        return parser

    def main(self, args=None):
        """

        :param args: List of arguments, with the 'aws' removed.  For example,
            the command "aws s3 list-objects --bucket foo" will have an
            args list of ``['s3', 'list-objects', '--bucket', 'foo']``.

        """
        if args is None:
            args = sys.argv[1:]
        command_table = self._get_command_table()
        parser = self.create_parser(command_table)
        self._add_aliases(command_table, parser)
        try:
            # Because _handle_top_level_args emits events, it's possible
            # that exceptions can be raised, which should have the same
            # general exception handling logic as calling into the
            # command table.  This is why it's in the try/except clause.
            parsed_args, remaining = parser.parse_known_args(args)
            self._handle_top_level_args(parsed_args)
            self._emit_session_event(parsed_args)
            HISTORY_RECORDER.record(
                'CLI_VERSION', self.session.user_agent(), 'CLI')
            HISTORY_RECORDER.record('CLI_ARGUMENTS', args, 'CLI')
            return command_table[parsed_args.command](remaining, parsed_args)
        except BaseException as e:
            LOG.debug("Exception caught in main()", exc_info=True)
            return self._error_handler.handle_exception(
                e,
                stdout=get_stdout_text_writer(),
                stderr=get_stderr_text_writer()
            )

    def _emit_session_event(self, parsed_args):
        # This event is guaranteed to run after the session has been
        # initialized and a profile has been set.  This was previously
        # problematic because if something in CLIDriver caused the
        # session components to be reset (such as session.profile = foo)
        # then all the prior registered components would be removed.
        self.session.emit(
            'session-initialized', session=self.session,
            parsed_args=parsed_args)

    def _show_error(self, msg):
        LOG.debug(msg, exc_info=True)
        sys.stderr.write(msg)
        sys.stderr.write('\n')

    def _handle_top_level_args(self, args):
        emit_top_level_args_parsed_event(self.session, args)
        if getattr(args, 'profile', False):
            self.session.set_config_variable('profile', args.profile)
        if getattr(args, 'region', False):
            self.session.set_config_variable('region', args.region)
        self._set_logging(getattr(args, 'debug', False))

    def _set_logging(self, debug):
        loggers_list = ['botocore', 'awscli', 's3transfer', 'urllib3']
        if debug:
            for logger_name in loggers_list:
                set_stream_logger(logger_name, logging.DEBUG,
                                  format_string=LOG_FORMAT)
            LOG.debug("CLI version: %s", self.session.user_agent())
            LOG.debug("Arguments entered to CLI: %s", sys.argv[1:])
        else:
            # In case user set --debug before entering prompt mode and removed
            # it during editing inside the prompter we need to remove all the
            # debug handlers
            for logger_name in loggers_list:
                remove_stream_logger(logger_name)
            set_stream_logger(logger_name='awscli',
                              log_level=logging.ERROR)


class ServiceCommand(CLICommand):

    """A service command for the CLI.

    For example, ``aws ec2 ...`` we'd create a ServiceCommand
    object that represents the ec2 service.

    """

    def __init__(self, cli_name, session, service_name=None):
        # The cli_name is the name the user types, the name we show
        # in doc, etc.
        # The service_name is the name we used internally with botocore.
        # For example, we have the 's3api' as the cli_name for the service
        # but this is actually bound to the 's3' service name in botocore,
        # i.e. we load s3.json from the botocore data dir.  Most of
        # the time these are the same thing but in the case of renames,
        # we want users/external things to be able to rename the cli name
        # but *not* the service name, as this has to be exactly what
        # botocore expects.
        self._name = cli_name
        self.session = session
        self._command_table = None
        if service_name is None:
            # Then default to using the cli name.
            self._service_name = cli_name
        else:
            self._service_name = service_name
        self._lineage = [self]
        self._service_model = None

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def service_model(self):
        return self._get_service_model()

    @property
    def lineage(self):
        return self._lineage

    @lineage.setter
    def lineage(self, value):
        self._lineage = value

    @property
    def subcommand_table(self):
        return self._get_command_table()

    @property
    def arg_table(self):
        # No service level arguments so we just return an empty
        # dictionary.
        return {}

    def _get_command_table(self):
        if self._command_table is None:
            self._command_table = self._create_command_table()
        return self._command_table

    def _get_service_model(self):
        if self._service_model is None:
            self._service_model = self.session.get_service_model(
                self._service_name)
        return self._service_model

    def __call__(self, args, parsed_globals):
        # Once we know we're trying to call a service for this operation
        # we can go ahead and create the parser for it.  We
        # can also grab the Service object from botocore.
        service_parser = self.create_parser()
        parsed_args, remaining = service_parser.parse_known_args(args)
        command_table = self._get_command_table()
        return command_table[parsed_args.operation](remaining, parsed_globals)

    def _create_command_table(self):
        command_table = OrderedDict()
        service_model = self._get_service_model()
        for operation_name in service_model.operation_names:
            cli_name = xform_name(operation_name, '-')
            operation_model = service_model.operation_model(operation_name)
            command_table[cli_name] = ServiceOperation(
                name=cli_name,
                parent_name=self._name,
                session=self.session,
                operation_model=operation_model,
                operation_caller=CLIOperationCaller(self.session),
            )
        self.session.emit('building-command-table.%s' % self._name,
                          command_table=command_table,
                          session=self.session,
                          command_object=self)
        self._add_lineage(command_table)
        return command_table

    def _add_lineage(self, command_table):
        for command in command_table:
            command_obj = command_table[command]
            command_obj.lineage = self.lineage + [command_obj]

    def create_help_command(self):
        command_table = self._get_command_table()
        return ServiceHelpCommand(session=self.session,
                                  obj=self._get_service_model(),
                                  command_table=command_table,
                                  arg_table=None,
                                  event_class='.'.join(self.lineage_names),
                                  name=self._name)

    def create_parser(self):
        command_table = self._get_command_table()
        # Also add a 'help' command.
        command_table['help'] = self.create_help_command()
        return ServiceArgParser(
            operations_table=command_table, service_name=self._name)


class ServiceOperation(object):

    """A single operation of a service.

    This class represents a single operation for a service, for
    example ``ec2.DescribeInstances``.

    """

    ARG_TYPES = {
        'list': ListArgument,
        'boolean': BooleanArgument,
    }
    DEFAULT_ARG_CLASS = CLIArgument

    def __init__(self, name, parent_name, operation_caller,
                 operation_model, session):
        """

        :type name: str
        :param name: The name of the operation/subcommand.

        :type parent_name: str
        :param parent_name: The name of the parent command.

        :type operation_model: ``botocore.model.OperationModel``
        :param operation_object: The operation model
            associated with this subcommand.

        :type operation_caller: ``CLIOperationCaller``
        :param operation_caller: An object that can properly call the
            operation.

        :type session: ``botocore.session.Session``
        :param session: The session object.

        """
        self._arg_table = None
        self._name = name
        # These is used so we can figure out what the proper event
        # name should be <parent name>.<name>.
        self._parent_name = parent_name
        self._operation_caller = operation_caller
        self._lineage = [self]
        self._operation_model = operation_model
        self._session = session
        if operation_model.deprecated:
            self._UNDOCUMENTED = True

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def lineage(self):
        return self._lineage

    @lineage.setter
    def lineage(self, value):
        self._lineage = value

    @property
    def lineage_names(self):
        # Represents the lineage of a command in terms of command ``name``
        return [cmd.name for cmd in self.lineage]

    @property
    def subcommand_table(self):
        # There's no subcommands for an operation so we return an
        # empty dictionary.
        return {}

    @property
    def arg_table(self):
        if self._arg_table is None:
            self._arg_table = self._create_argument_table()
        return self._arg_table

    def __call__(self, args, parsed_globals):
        # Once we know we're trying to call a particular operation
        # of a service we can go ahead and load the parameters.
        event = 'before-building-argument-table-parser.%s.%s' % \
            (self._parent_name, self._name)
        self._emit(event, argument_table=self.arg_table, args=args,
                   session=self._session)
        operation_parser = self._create_operation_parser(self.arg_table)
        self._add_help(operation_parser)
        parsed_args, remaining = operation_parser.parse_known_args(args)
        if parsed_args.help == 'help':
            op_help = self.create_help_command()
            return op_help(remaining, parsed_globals)
        elif parsed_args.help:
            remaining.append(parsed_args.help)
        if remaining:
            raise UnknownArgumentError(
                "Unknown options: %s" % ', '.join(remaining))
        event = 'operation-args-parsed.%s.%s' % (self._parent_name,
                                                 self._name)
        self._emit(event, parsed_args=parsed_args,
                   parsed_globals=parsed_globals)
        call_parameters = self._build_call_parameters(
            parsed_args, self.arg_table)
        event = 'calling-command.%s.%s' % (self._parent_name,
                                           self._name)
        override = self._emit_first_non_none_response(
            event,
            call_parameters=call_parameters,
            parsed_args=parsed_args,
            parsed_globals=parsed_globals
        )
        # There are two possible values for override. It can be some type
        # of exception that will be raised if detected or it can represent
        # the desired return code. Note that a return code of 0 represents
        # a success.
        if hasattr(self._session, 'user_agent_extra'):
            self._add_customization_to_user_agent()
        if override is not None:
            if isinstance(override, Exception):
                # If the override value provided back is an exception then
                # raise the exception
                raise override
            else:
                # This is the value usually returned by the ``invoke()``
                # method of the operation caller. It represents the return
                # code of the operation.
                return override
        else:
            # No override value was supplied.
            return self._operation_caller.invoke(
                self._operation_model.service_model.service_name,
                self._operation_model.name,
                call_parameters, parsed_globals)

    def create_help_command(self):
        return OperationHelpCommand(
            self._session,
            operation_model=self._operation_model,
            arg_table=self.arg_table,
            name=self._name, event_class='.'.join(self.lineage_names))

    def _add_help(self, parser):
        # The 'help' output is processed a little differently from
        # the operation help because the arg_table has
        # CLIArguments for values.
        parser.add_argument('help', nargs='?')

    def _build_call_parameters(self, args, arg_table):
        # We need to convert the args specified on the command
        # line as valid **kwargs we can hand to botocore.
        service_params = {}
        # args is an argparse.Namespace object so we're using vars()
        # so we can iterate over the parsed key/values.
        parsed_args = vars(args)
        for arg_object in arg_table.values():
            py_name = arg_object.py_name
            if py_name in parsed_args:
                value = parsed_args[py_name]
                value = self._unpack_arg(arg_object, value)
                arg_object.add_to_params(service_params, value)
        return service_params

    def _unpack_arg(self, cli_argument, value):
        # Unpacks a commandline argument into a Python value by firing the
        # load-cli-arg.service-name.operation-name event.
        session = self._session
        service_name = self._operation_model.service_model.endpoint_prefix
        operation_name = xform_name(self._name, '-')

        return unpack_argument(session, service_name, operation_name,
                               cli_argument, value)

    def _create_argument_table(self):
        argument_table = OrderedDict()
        input_shape = self._operation_model.input_shape
        required_arguments = []
        arg_dict = {}
        if input_shape is not None:
            required_arguments = input_shape.required_members
            arg_dict = input_shape.members
        for arg_name, arg_shape in arg_dict.items():
            cli_arg_name = xform_name(arg_name, '-')
            arg_class = self.ARG_TYPES.get(arg_shape.type_name,
                                           self.DEFAULT_ARG_CLASS)
            is_token = arg_shape.metadata.get('idempotencyToken', False)
            is_required = arg_name in required_arguments and not is_token
            event_emitter = self._session.get_component('event_emitter')
            arg_object = arg_class(
                name=cli_arg_name,
                argument_model=arg_shape,
                is_required=is_required,
                operation_model=self._operation_model,
                serialized_name=arg_name,
                event_emitter=event_emitter)
            arg_object.add_to_arg_table(argument_table)
        LOG.debug(argument_table)
        self._emit('building-argument-table.%s.%s' % (self._parent_name,
                                                      self._name),
                   operation_model=self._operation_model,
                   session=self._session,
                   command=self,
                   argument_table=argument_table)
        return argument_table

    def _emit(self, name, **kwargs):
        return self._session.emit(name, **kwargs)

    def _emit_first_non_none_response(self, name, **kwargs):
        return self._session.emit_first_non_none_response(
            name, **kwargs)

    def _create_operation_parser(self, arg_table):
        parser = ArgTableArgParser(arg_table)
        return parser

    def _add_customization_to_user_agent(self):
        if ' command/' in self._session.user_agent_extra:
            self._session.user_agent_extra += '.%s' % self.lineage_names[-1]
        else:
            self._session.user_agent_extra += ' command/%s' % '.'.join(
                self.lineage_names
            )


class CLIOperationCaller(object):

    """Call an AWS operation and format the response."""

    def __init__(self, session):
        self._session = session
        self._output_stream_factory = OutputStreamFactory(session)

    def invoke(self, service_name, operation_name, parameters, parsed_globals):
        """Invoke an operation and format the response.

        :type service_name: str
        :param service_name: The name of the service.  Note this is the
            service name, not the endpoint prefix (e.g. ``ses`` not ``email``).

        :type operation_name: str
        :param operation_name: The operation name of the service.  The casing
            of the operation name should match the exact casing used by the
            service, e.g. ``DescribeInstances``, not ``describe-instances`` or
            ``describe_instances``.

        :type parameters: dict
        :param parameters: The parameters for the operation call.  Again,
            these values have the same casing used by the service.

        :type parsed_globals: Namespace
        :param parsed_globals: The parsed globals from the command line.

        :return: None, the result is displayed through a formatter, but no
            value is returned.

        """
        client = self._session.create_client(
            service_name, region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl)
        response = self._make_client_call(
            client, operation_name, parameters, parsed_globals)
        self._display_response(operation_name, response, parsed_globals)
        return 0

    def _make_client_call(self, client, operation_name, parameters,
                          parsed_globals):
        py_operation_name = xform_name(operation_name)
        if client.can_paginate(py_operation_name) and parsed_globals.paginate:
            paginator = client.get_paginator(py_operation_name)
            response = paginator.paginate(**parameters)
        else:
            response = getattr(client, xform_name(operation_name))(
                **parameters)
        return response

    def _display_response(self, command_name, response,
                          parsed_globals):
        output = parsed_globals.output
        if output is None:
            output = self._session.get_config_variable('output')

        formatter = get_formatter(output, parsed_globals)
        with self._output_stream_factory.get_output_stream() as stream:
            formatter(command_name, response, stream)
