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
import sys
import logging

import botocore.session
from botocore import __version__ as botocore_version
from botocore.hooks import HierarchicalEmitter
from botocore import xform_name
from botocore.compat import copy_kwargs, OrderedDict
from botocore.exceptions import NoCredentialsError
from botocore.exceptions import NoRegionError

from awscli import EnvironmentVariables, __version__
from awscli.formatter import get_formatter
from awscli.plugin import load_plugins
from awscli.argparser import MainArgParser
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


LOG = logging.getLogger('awscli.clidriver')
LOG_FORMAT = (
    '%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')



def main():
    driver = create_clidriver()
    return driver.main()


def create_clidriver():
    emitter = HierarchicalEmitter()
    session = botocore.session.Session(EnvironmentVariables, emitter)
    _set_user_agent_for_session(session)
    load_plugins(session.full_config.get('plugins', {}),
                 event_hooks=emitter)
    driver = CLIDriver(session=session)
    return driver


def _set_user_agent_for_session(session):
    session.user_agent_name = 'aws-cli'
    session.user_agent_version = __version__


class CLIDriver(object):

    def __init__(self, session=None):
        if session is None:
            self.session = botocore.session.get_session(EnvironmentVariables)
            _set_user_agent_for_session(self.session)
        else:
            self.session = session
        self._cli_data = None
        self._command_table = None
        self._argument_table = None

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
                          session=self.session)
        return command_table

    def _build_builtin_commands(self, session):
        commands = OrderedDict()
        services = session.get_available_services()
        for service_name in services:
            commands[service_name] = ServiceCommand(cli_name=service_name,
                                                    session=self.session,
                                                    service_name=service_name)
        return commands

    def _build_argument_table(self):
        argument_table = OrderedDict()
        cli_data = self._get_cli_data()
        cli_arguments = cli_data.get('options', None)
        for option in cli_arguments:
            option_params = copy_kwargs(cli_arguments[option])
            # Special case the 'choices' param.  Allows choices
            # to reference a variable from the session.
            if 'choices' in option_params:
                choices = option_params['choices']
                if not isinstance(choices, list):
                    # Assume it's a reference like
                    # "{provider}/_foo", so first resolve
                    # the provider.
                    provider = self.session.get_config_variable('provider')
                    # The grab the var from the session
                    choices_path = choices.format(provider=provider)
                    choices = list(self.session.get_data(choices_path))
                option_params['choices'] = choices
            argument_object = self._create_argument_object(option,
                                                           option_params)
            argument_object.add_to_arg_table(argument_table)
        # Then the final step is to send out an event so handlers
        # can add extra arguments or modify existing arguments.
        self.session.emit('building-top-level-params',
                          argument_table=argument_table)
        return argument_table

    def _create_argument_object(self, option_name, option_params):
        return CustomArgument(
            option_name, help_text=option_params.get('help', ''),
            dest=option_params.get('dest'),default=option_params.get('default'),
            action=option_params.get('action'),
            required=option_params.get('required'),
            choices=option_params.get('choices'))

    def create_help_command(self):
        cli_data = self._get_cli_data()
        return ProviderHelpCommand(self.session, self._get_command_table(),
                                   self._get_argument_table(),
                                   cli_data.get('description', None),
                                   cli_data.get('synopsis', None),
                                   cli_data.get('help_usage', None))

    def _create_parser(self):
        # Also add a 'help' command.
        command_table = self._get_command_table()
        command_table['help'] = self.create_help_command()
        cli_data = self._get_cli_data()
        parser = MainArgParser(
            command_table, self.session.user_agent(),
            cli_data.get('description', None),
            cli_data.get('synopsis', None),
            self._get_argument_table())
        return parser

    def main(self, args=None):
        """

        :param args: List of arguments, with the 'aws' removed.  For example,
            the command "aws s3 list-objects --bucket foo" will have an
            args list of ``['s3', 'list-objects', '--bucket', 'foo']``.

        """
        if args is None:
            args = sys.argv[1:]
        parser = self._create_parser()
        command_table = self._get_command_table()
        parsed_args, remaining = parser.parse_known_args(args)
        try:
            # Because _handle_top_level_args emits events, it's possible
            # that exceptions can be raised, which should have the same
            # general exception handling logic as calling into the
            # command table.  This is why it's in the try/except clause.
            self._handle_top_level_args(parsed_args)
            return command_table[parsed_args.command](remaining, parsed_args)
        except UnknownArgumentError as e:
            sys.stderr.write(str(e) + '\n')
            return 255
        except NoRegionError as e:
            msg = ('%s You can also configure your region by running '
                   '"aws configure".' % e)
            self._show_error(msg)
            return 255
        except NoCredentialsError as e:
            msg = ('%s. You can configure credentials by running '
                   '"aws configure".' % e)
            self._show_error(msg)
            return 255
        except Exception as e:
            LOG.debug("Exception caught in main()", exc_info=True)
            LOG.debug("Exiting with rc 255")
            sys.stderr.write("\n")
            sys.stderr.write("%s\n" % e)
            return 255

    def _show_error(self, msg):
        LOG.debug(msg, exc_info=True)
        sys.stderr.write(msg)
        sys.stderr.write('\n')

    def _handle_top_level_args(self, args):
        self.session.emit(
            'top-level-args-parsed', parsed_args=args, session=self.session)
        if args.profile:
            self.session.profile = args.profile
        if args.debug:
            # TODO:
            # Unfortunately, by setting debug mode here, we miss out
            # on all of the debug events prior to this such as the
            # loading of plugins, etc.
            self.session.set_stream_logger('botocore', logging.DEBUG,
                                           format_string=LOG_FORMAT)
            self.session.set_stream_logger('awscli', logging.DEBUG,
                                           format_string=LOG_FORMAT)
            LOG.debug("CLI version: %s, botocore version: %s",
                      self.session.user_agent(),
                      botocore_version)
        else:
            self.session.set_stream_logger(logger_name='awscli',
                                           log_level=logging.ERROR)


class CLICommand(object):
    """Interface for a CLI command.

    This class represents a top level CLI command
    (``aws ec2``, ``aws s3``, ``aws config``).

    """

    @property
    def name(self):
        # Subclasses must implement a name.
        raise NotImplementedError("name")

    @name.setter
    def name(self, value):
        # Subclasses must implement setting/changing the cmd name.
        raise NotImplementedError("name")

    def __call__(self, args, parsed_globals):
        """Invoke CLI operation.

        :type args: str
        :param args: The remaining command line args.

        :type parsed_globals: ``argparse.Namespace``
        :param parsed_globals: The parsed arguments so far.

        :rtype: int
        :return: The return code of the operation.  This will be used
            as the RC code for the ``aws`` process.

        """
        # Subclasses are expected to implement this method.
        pass

    def create_help_command(self):
        # Subclasses are expected to implement this method if they want
        # help docs.
        return None

    @property
    def arg_table(self):
        return {}


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
        self._service_object = None
        if service_name is None:
            # Then default to using the cli name.
            self._service_name = cli_name
        else:
            self._service_name = service_name

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    def _get_command_table(self):
        if self._command_table is None:
            self._command_table = self._create_command_table()
        return self._command_table

    def _get_service_object(self):
        if self._service_object is None:
            self._service_object = self.session.get_service(self._service_name)
        return self._service_object

    def __call__(self, args, parsed_globals):
        # Once we know we're trying to call a service for this operation
        # we can go ahead and create the parser for it.  We
        # can also grab the Service object from botocore.
        service_parser = self._create_parser()
        parsed_args, remaining = service_parser.parse_known_args(args)
        command_table = self._get_command_table()
        return command_table[parsed_args.operation](remaining, parsed_globals)

    def _create_command_table(self):
        command_table = OrderedDict()
        service_object = self._get_service_object()
        for operation_object in service_object.operations:
            cli_name = xform_name(operation_object.name, '-')
            command_table[cli_name] = ServiceOperation(
                name=cli_name,
                parent_name=self._name,
                operation_object=operation_object,
                operation_caller=CLIOperationCaller(self.session),
                service_object=service_object)
        self.session.emit('building-command-table.%s' % self._name,
                          command_table=command_table,
                          session=self.session)
        return command_table

    def create_help_command(self):
        command_table = self._get_command_table()
        service_object = self._get_service_object()
        return ServiceHelpCommand(session=self.session,
                                  obj=service_object,
                                  command_table=command_table,
                                  arg_table=None,
                                  event_class='Operation',
                                  name=self._name)

    def _create_parser(self):
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

    def __init__(self, name, parent_name, operation_object, operation_caller,
                 service_object):
        """

        :type name: str
        :param name: The name of the operation/subcommand.

        :type parent_name: str
        :param parent_name: The name of the parent command.

        :type operation_object: ``botocore.operation.Operation``
        :param operation_object: The operation associated with this subcommand.

        :type operation_caller: ``CLIOperationCaller``
        :param operation_caller: An object that can properly call the
            operation.

        :type service_object: ``botocore.service.Service``
        :param service_object: The service associated wtih the object.

        """
        self._arg_table = None
        self._name = name
        # These is used so we can figure out what the proper event
        # name should be <parent name>.<name>.
        self._parent_name = parent_name
        self._operation_object = operation_object
        self._operation_caller = operation_caller
        self._service_object = service_object

    @property
    def arg_table(self):
        if self._arg_table is None:
            self._arg_table = self._create_argument_table()
        return self._arg_table

    def __call__(self, args, parsed_globals):
        # Once we know we're trying to call a particular operation
        # of a service we can go ahead and load the parameters.
        operation_parser = self._create_operation_parser(self.arg_table)
        self._add_help(operation_parser)
        parsed_args, remaining = operation_parser.parse_known_args(args)
        if parsed_args.help == 'help':
            op_help = self.create_help_command()
            return op_help(parsed_args, parsed_globals)
        elif parsed_args.help:
            remaining.append(parsed_args.help)
        if remaining:
            raise UnknownArgumentError(
                "Unknown options: %s" % ', '.join(remaining))
        event = 'operation-args-parsed.%s.%s' % (self._parent_name,
                                                 self._name)
        self._emit(event, parsed_args=parsed_args,
                   parsed_globals=parsed_globals)
        call_parameters = self._build_call_parameters(parsed_args,
                                                      self.arg_table)
        return self._operation_caller.invoke(
            self._operation_object, call_parameters, parsed_globals)

    def create_help_command(self):
        return OperationHelpCommand(
            self._service_object.session, self._service_object,
            self._operation_object, arg_table=self.arg_table,
            name=self._name, event_class=self._parent_name)

    def _add_help(self, parser):
        # The 'help' output is processed a little differently from
        # the provider/operation help because the arg_table has
        # CLIArguments for values.
        parser.add_argument('help', nargs='?')

    def _build_call_parameters(self, args, arg_table):
        # We need to convert the args specified on the command
        # line as valid **kwargs we can hand to botocore.
        service_params = {}
        # args is an argparse.Namespace object so we're using vars()
        # so we can iterate over the parsed key/values.
        parsed_args = vars(args)
        for arg_name, arg_object in arg_table.items():
            py_name = arg_object.py_name
            if py_name in parsed_args:
                value = parsed_args[py_name]
                value = self._unpack_arg(arg_object, value)
                arg_object.add_to_params(service_params, value)
        return service_params

    def _unpack_arg(self, arg_object, value):
        # Unpacks a commandline argument into a Python value by firing the
        # load-cli-arg.service-name.operation-name event.
        session = self._service_object.session
        service_name = self._service_object.endpoint_prefix
        operation_name = xform_name(self._operation_object.name, '-')

        param = arg_object
        if hasattr(param, 'argument_object') and param.argument_object:
            param = param.argument_object

        return unpack_argument(session, service_name, operation_name,
                               param, value)

    def _create_argument_table(self):
        argument_table = OrderedDict()
        # Arguments are treated a differently than service and
        # operations.  Instead of doing a get_parameter() we just
        # load all the parameter objects up front for the operation.
        # We could potentially do the same thing as service/operations
        # but botocore already builds all the parameter objects
        # when calling an operation so we'd have to optimize that first
        # before using get_parameter() in the cli would be advantageous
        for argument in self._operation_object.params:
            cli_arg_name = argument.cli_name[2:]
            arg_class = self.ARG_TYPES.get(argument.type,
                                           self.DEFAULT_ARG_CLASS)
            arg_object = arg_class(cli_arg_name, argument,
                                   self._operation_object)
            arg_object.add_to_arg_table(argument_table)
        LOG.debug(argument_table)
        self._emit('building-argument-table.%s.%s' % (self._parent_name,
                                                      self._name),
                   operation=self._operation_object,
                   argument_table=argument_table)
        return argument_table

    def _emit(self, name, **kwargs):
        session = self._service_object.session
        return session.emit(name, **kwargs)

    def _create_operation_parser(self, arg_table):
        parser = ArgTableArgParser(arg_table)
        return parser


class CLIOperationCaller(object):
    """
    Call an AWS operation and format the response.

    This class handles the non-error path.  If an HTTP error occurs
    on the call to the service operation, it will be detected and
    handled by the :class:`awscli.errorhandler.ErrorHandler` which
    is registered on the ``after-call`` event.
    """

    def __init__(self, session):
        self._session = session

    def invoke(self, operation_object, parameters, parsed_globals):
        # We could get an error from get_endpoint() about not having
        # a region configured.  Before this happens we want to check
        # for credentials so we can give a good error message.
        if not self._session.get_credentials():
            raise NoCredentialsError()
        endpoint = operation_object.service.get_endpoint(
            region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl)
        if operation_object.can_paginate and parsed_globals.paginate:
            pages = operation_object.paginate(endpoint, **parameters)
            self._display_response(operation_object, pages,
                                   parsed_globals)
        else:
            http_response, response_data = operation_object.call(endpoint,
                                                                 **parameters)
            self._display_response(operation_object, response_data,
                                   parsed_globals)
        return 0

    def _display_response(self, operation, response, args):
        output = args.output
        if output is None:
            output = self._session.get_config_variable('output')
        formatter = get_formatter(output, args)
        formatter(operation, response)
