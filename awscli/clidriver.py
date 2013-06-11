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
from botocore.hooks import first_non_none_response
from botocore.hooks import HierarchicalEmitter
from botocore import xform_name

from awscli import EnvironmentVariables, __version__
from .formatter import get_formatter
from .paramfile import get_paramfile
from .plugin import load_plugins
from .argparser import MainArgParser, ServiceArgParser, OperationArgParser
from .argprocess import unpack_cli_arg
from .help import get_provider_help, get_service_help, get_operation_help


log = logging.getLogger('awscli.clidriver')


class UnknownArgumentError(Exception):
    pass


def main():
    driver = create_clidriver()
    return driver.main()


def create_clidriver():
    emitter = HierarchicalEmitter()
    session = botocore.session.Session(EnvironmentVariables, emitter)
    session.user_agent_name = 'aws-cli'
    session.user_agent_version = __version__
    load_plugins(session.full_config.get('plugins', {}),
                 event_hooks=emitter)
    driver = CLIDriver(session=session)
    return driver


class CLIDriver(object):

    def __init__(self, session=None):
        if session is None:
            self.session = botocore.session.get_session(EnvironmentVariables)
            self.session.user_agent_name = 'aws-cli'
            self.session.user_agent_version = __version__
        else:
            self.session = session

    def _build_command_table(self):
        """
        Create the main parser to handle the global arguments.

        :rtype: ``argparser.ArgumentParser``
        :return: The parser object

        """
        command_table = self._build_builtin_commands(self.session)
        self.session.emit('building-command-table',
                          command_table=command_table,
                          session=self.session)
        return command_table

    def _build_builtin_commands(self, session):
        # TODO: ordered dict.
        commands = {}
        services = session.get_available_services()
        for service_name in services:
            commands[service_name] = ServiceCommand(service_name, self.session)
        # Also add a 'help' command.
        commands['help'] = ProviderHelpCommand(self.session)
        return commands

    def _create_parser_from_command_table(self, command_table):
        provider = self.session.get_variable('provider')
        parser = MainArgParser(
            command_table, self.session.user_agent(),
            self.session.get_data(provider + '/_regions'))
        return parser

    def main(self, args=None):
        """

        :param args: List of arguments, with the 'aws' removed.  For example,
            the command "aws s3 list-objects --bucket foo" will have an
            args list of ``['s3', 'list-objects', '--bucket', 'foo']``.

        """
        if args is None:
            args = sys.argv[1:]
        command_table = self._build_command_table()
        parser = self._create_parser_from_command_table(command_table)
        args, remaining = parser.parse_known_args(args)
        self._handle_top_level_args(args)
        try:
            return command_table[args.command].call(remaining, args)
        except UnknownArgumentError as e:
            sys.stderr.write(str(e) + '\n')
            return 255
        except Exception as e:
            log.debug("Exception caugh in main()", exc_info=True)
            log.debug("Exiting with rc 255")
            sys.stderr.write("%s\n" % e)
            return 255

    def _handle_top_level_args(self, args):
        if args.debug:
            self.session.set_debug_logger(logger_name='botocore')
            self.session.set_debug_logger(logger_name='awscli')


class CLICommand(object):
    """Interface for a CLI command.

    This class represents a top level CLI command
    (``aws ec2``, ``aws s3``, ``aws config``).

    """

    def call(self, args, parsed_globals):
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


class ProviderHelpCommand(CLICommand):
    """Implements top level help command.

    This is what is called when ``aws help`` is run.

    """
    def __init__(self, session):
        self._session = session

    def call(self, args, parsed_globals):
        if not args:
            get_provider_help(self._session)


class ServiceCommand(CLICommand):
    """A service command for the CLI.

    For example, ``aws ec2 ...`` we'd create a ServiceCommand
    object that represents the ec2 service.

    """
    def __init__(self, name, session):
        self._name = name
        self._session = session

    def call(self, args, parsed_globals):
        # Once we know we're trying to call a service for this operation
        # we can go ahead and create the parser for it.  We
        # can also grab the Service object from botocore.
        service_object = self._session.get_service(self._name)
        op_table = self._create_operations_table(service_object)
        service_parser = self._create_service_parser(op_table)
        args, remaining = service_parser.parse_known_args(args)
        return op_table[args.operation].call(remaining, parsed_globals)

    def _create_service_parser(self, operation_table):
        parser = ServiceArgParser(operation_table, self._name)
        return parser

    def _create_operations_table(self, service_object):
        operation_table = {}
        service_data = self._session.get_service_data(self._name)
        operations_data = service_data['operations']
        for operation_name in operations_data:
            cli_name = xform_name(operation_name, '-')
            operation_table[cli_name] = ServiceOperation(
                cli_name, operations_data[operation_name],
                CLIOperationCaller(self._session),
                service_object)
        # Also add a 'help' command.
        operation_table['help'] = ServiceHelpCommand(self._session,
                                                     service_object)
        self._session.emit('building-operation-table.%s' % self._name,
                           operation_table=operation_table)
        return operation_table


class ServiceHelpCommand(CLICommand):
    """Implements service level help.

    This is the object invoked whenever a service command
    help is implemented, e.g. ``aws ec2 help``.

    """
    def __init__(self, session, service):
        """

        :type session: ``botocore.session.Session``
        :param session: A botocore session.

        :type service: ``botocore.service.Service``
        :param service: A botocore service object representing the
            particular service.

        """
        self._session = session
        self._service = service

    def call(self, args, parsed_globals):
        if not args:
            get_service_help(self._session, self._service)


class OperationHelpCommand(CLICommand):
    """Implements operation level help.

    This is the object invoked whenever help for a service is requested,
    e.g. ``aws ec2 describe-instances help``.

    """
    def __init__(self, session, service, operation):
        self._session = session
        self._service = service
        self._operation = operation

    def call(self, args, parsed_globals):
        get_operation_help(self._session, self._service, self._operation)


class BaseCLIArgument(object):
    """Interface for CLI argument.

    This class represents the interface used for representing CLI
    arguments.

    """

    def add_to_arg_table(self, argument_table):
        """Add this object to the argument_table.

        The ``argument_table`` represents the argument for the operation.
        This is called by the ``ServiceOperation`` object to create the
        arguments associated with the operation.

        :type argument_table: dict
        :param argument_table: The argument table.  The key is the argument
            name, and the value is an object implementing this interface.
        """
        pass

    def add_to_parser(self, parser, cli_name):
        """Add this object to the parser instance.

        This method is called by the associated ``ArgumentParser``
        instance.  This method should make the relevant calls
        to ``add_argument`` to add itself to the argparser.

        :type parser: ``argparse.ArgumentParser``.
        :param parser: The argument parser associated with the operation.

        :type cli_name: str
        :param cli_name: The key from the argument table.

        """
        pass

    def add_to_params(self, parameters, value):
        """Add this object to the parameters dict.

        This method is responsible for taking the value specified
        on the command line, and deciding how that corresponds to
        parameters used by the service/operation.

        :type parameters: dict
        :param parameters: The parameters dictionary that will be
            given to ``botocore``.  This should match up to the
            parameters associated with the particular operation.

        :param value: The value associated with the CLI option.

        """
        pass


class CLIArgument(BaseCLIArgument):
    """Represents a CLI argument that maps to a service parameter.

    """
    TYPE_MAP = {
        'structure': str,
        'map': str,
        'timestamp': str,
        'list': str,
        'string': str,
        'float': float,
        'integer': str,
        'long': int,
        'boolean': bool,
        'double': float,
        'blob': str
    }

    def __init__(self, name, argument_object, operation_object):
        """

        :type name: str
        :param name: The name of the argument in "cli" form
            (e.g.  ``min-instances``).

        :type argument_object: ``botocore.parameter.Parameter``
        :param argument_object: The parameter object to associate with
            this object.

        :type operation_object: ``botocore.operation.Operation``
        :param operation_object: The operation object associated with
            this object.

        """
        self._name = name
        self._argument_object = argument_object
        self._operation_object = operation_object

    @property
    def py_name(self):
        return self._name.replace('-', '_')

    @property
    def name(self):
        # TODO: move cli specific attrs out of the parameter
        # object, or at least into a distinct config property
        # or something.
        # The [2:] is to strip off the leading '--' part (--foo -> foo).
        return self._argument_object.cli_name[2:]

    @property
    def required(self):
        return self._argument_object.required

    @required.setter
    def required(self, value):
        self._argument_object.required = value

    @property
    def documentation(self):
        return self._argument_object.documentation

    @property
    def cli_type(self):
        return self.TYPE_MAP.get(self._argument_object.type, str)

    def add_to_arg_table(self, argument_table):
        # This is used by the ServiceOperation so we can add ourselves
        # to the argument table.  For the normal case, we use our name
        # as the key, and ourself as the value.  For a more complicated
        # example, see BooleanArgument.add_to_arg_table
        argument_table[self.name] = self

    def add_to_parser(self, parser, cli_name):
        """

        See the ``BaseCLIArgument.add_to_parser`` docs for more information.

        """
        # We need to add ourselve to the argparser instance.  For the normal
        # case we just need to make a single add_argument call.
        cli_name = '--%s' % cli_name
        parser.add_argument(
            cli_name,
            help=self.documentation,
            type=self.cli_type,
            required=self.required,
            dest=self.name)

    def add_to_params(self, parameters, value):
        if value is None:
            return
        else:
            # This is a two step process.  First is the process of converting
            # the command line value into a python value.  Normally this is
            # handled by argparse directly, but there are cases where extra
            # processing is needed.  For example, "--foo name=value" the value
            # can be converted from "name=value" to {"name": "value"}.  This is
            # referred to as the "unpacking" process.  Once we've unpacked the
            # argument value, we have to decide how this is converted into
            # something that can be consumed by botocore.  Many times this is
            # just associating the key and value in the params dict as down
            # below.  Sometimes this can be more complicated, and subclasses
            # can customize as they need.
            parameters[self.py_name] = self._unpack_argument(value)

    def _unpack_argument(self, value):
        if not hasattr(self._argument_object, 'no_paramfile'):
            value = self._handle_param_file(value)
        service_name = self._operation_object.service.endpoint_prefix
        operation_name = xform_name(self._operation_object.name, '-')
        responses = self._emit('process-cli-arg.%s.%s' % (
            service_name, operation_name), param=self._argument_object,
            value=value,
            operation=self._operation_object)
        override = first_non_none_response(responses)
        if override is not None:
            # A plugin supplied an alternate conversion,
            # use it instead.
            return override
        else:
            # Fall back to the default arg processing.
            return unpack_cli_arg(self._argument_object, value)

    def _handle_param_file(self, value):
        session = self._operation_object.service.session
        if isinstance(value, list) and len(value) == 1:
            temp = value[0]
        else:
            temp = value
        temp = get_paramfile(session, temp)
        if temp:
            value = temp
        return value

    def _emit(self, name, **kwargs):
        session = self._operation_object.service.session
        return session.emit(name, **kwargs)


class ListArgument(CLIArgument):
    def add_to_parser(self, parser, cli_name):
        cli_name = '--%s' % cli_name
        parser.add_argument(cli_name,
                            nargs='*',
                            type=self.cli_type,
                            required=self.required,
                            dest=self.name)


class BooleanArgument(CLIArgument):
    """Represent a boolean CLI argument.

    A boolean parameter is specified without a value::

        aws foo bar --enabled

    For cases wher the boolean parameter is required we need to add
    two parameters::

        aws foo bar --enabled
        aws foo bar --no-enabled

    We use the capabilities of the CLIArgument to help achieve this.

    """
    def __init__(self, name, argument_object, operation_object):
        super(BooleanArgument, self).__init__(name, argument_object,
                                              operation_object)
        self._mutex_group = None

    def add_to_params(self, parameters, value):
        unpacked = self._unpack_argument(value)
        if not unpacked and not self.required:
            # Any False non-required value is just omitted
            # from the parameter dict.  This could cause problems
            # if there are non required parameters that default to
            # True.
            return
        else:
            parameters[self.py_name] = unpacked

    def add_to_arg_table(self, argument_table):
        # If this parameter is required, we need to add two command line
        # arguments, --foo, and --no-foo.  We do this by adding two
        # entries to the argument table and assigning both values to us.
        argument_table[self.name] = self
        if self.required:
            negative_name = 'no-%s' % self.name
            argument_table[negative_name] = self

    def add_to_parser(self, parser, cli_name):
        # If we're a required parameter we need to add two options
        # to the argparse.ArgumentParser instance, one for --foo, one for
        # --no-foo.  We handle this by knowing that we're going to be
        # called twice (we added two values to the argument table in
        # add_to_arg_table).  The first time through we create a
        # mutex group, the second time through we add to this mutex group.
        cli_name = '--%s' % cli_name
        if self._is_negative_version(cli_name):
            action = 'store_false'
        else:
            action = 'store_true'
        if self.required:
            if self._mutex_group is None:
                # This is our first time being called, so we need to
                # create the mutex group.
                self._mutex_group = parser.add_mutually_exclusive_group(
                    required=True)
            self._mutex_group.add_argument(
                cli_name, help=self.documentation,
                dest=self.name, action=action)
        else:
            # If we're not a required parameter, we assume we default to False.
            # In this case we only add a single boolean parameter, '--foo'.
            # We don't need a '--no-foo' because a user can just not specify
            # '--foo' and we won't send the parameter to the service.
            parser.add_argument(cli_name,
                                help=self.documentation,
                                action=action,
                                dest=self.name)

    def _is_negative_version(self, cli_name):
        return cli_name.startswith('--no-')


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

    def __init__(self, name, operation_model, operation_caller,
                 service_object):
        self._name = name
        self._operation_model = operation_model
        self._operation_caller = operation_caller
        self._service_object = service_object

    def call(self, args, parsed_globals):
        # Once we know we're trying to call a particular operation
        # of a service we can go ahead and load the parameters.
        # We can also create the operation object from botocore.
        operation_object = self._service_object.get_operation(self._name)
        arg_table = self._create_argument_table(operation_object)
        operation_parser = self._create_operation_parser(arg_table)
        self._add_help(operation_parser)
        args, remaining = operation_parser.parse_known_args(args)
        if args.help == 'help':
            op_help = OperationHelpCommand(
                self._service_object.session, self._service_object,
                operation_object)
            op_help.call(args, parsed_globals)
        if remaining:
            raise UnknownArgumentError(
                "Unknown options: %s" % ','.join(remaining))
        call_parameters = self._build_call_parameters(args, arg_table)
        return self._operation_caller.invoke(
            operation_object, call_parameters, parsed_globals)

    def _add_help(self, parser):
        # The 'help' output is processed a little differently from
        # the provider/operation help because the arg_table has
        # CLIArguments for values.
        parser.add_argument('help', nargs='?')

    def _build_call_parameters(self, args, arg_table):
        # We need to convert the args specified on the command
        # line as valid **kwargs we can hand to boto.
        service_params = {}
        # args is an argparse.Namespace object so we're using vars()
        # so we can iterate over the parsed key/values.
        for name, value in vars(args).items():
            if name in arg_table:
                arg_object = arg_table[name]
                arg_object.add_to_params(service_params, value)
        return service_params

    def _create_argument_table(self, operation_object):
        argument_table = {}
        # Arguments are treated a differently than service and
        # operations.  Instead of doing a get_parameter() we just
        # load all the parameter objects up front for the operation.
        # We could potentially do the same thing as service/operations
        # but botocore already builds all the parameter objects
        # when calling an operation so we'd have to optimize that first
        # before using get_parameter() in the cli would be advantageous
        for argument in operation_object.params:
            cli_arg_name = xform_name(argument.name, '-')
            arg_class = self.ARG_TYPES.get(argument.type,
                                           self.DEFAULT_ARG_CLASS)
            arg_object = arg_class(cli_arg_name, argument, operation_object)
            arg_object.add_to_arg_table(argument_table)
        service_name = self._service_object.endpoint_prefix
        operation_name = operation_object.name
        self._emit('building-argument-table.%s.%s' % (service_name,
                                                      operation_name),
                   operation=operation_object,
                   argument_table=argument_table)
        return argument_table

    def _emit(self, name, **kwargs):
        session = self._service_object.session
        return session.emit(name, **kwargs)

    def _create_operation_parser(self, arg_table):
        parser = OperationArgParser(arg_table, self._name)
        return parser


class CLIOperationCaller(object):
    """Call an AWS operation and format the response."""
    def __init__(self, session):
        self._session = session

    def invoke(self, operation_object, parameters, parsed_globals):
        endpoint = operation_object.service.get_endpoint(parsed_globals.region)
        endpoint.verify = not parsed_globals.no_verify_ssl
        if operation_object.can_paginate and parsed_globals.paginate:
            pages = operation_object.paginate(endpoint, **parameters)
            self._display_response(operation_object, pages,
                                   parsed_globals)
            return 0
        else:
            http_response, response_data = operation_object.call(endpoint,
                                                                 **parameters)
            self._display_response(operation_object, response_data,
                                   parsed_globals)
            return self._handle_http_response(http_response, response_data)

    def _display_response(self, operation, response, args):
        output = args.output
        if output is None:
            output = self._session.get_variable('output')
        formatter = get_formatter(output, args)
        formatter(operation, response)

    def _handle_http_response(self, http_response, response_data):
        if http_response.status_code >= 500:
            msg = self._session.get_data('messages/ServerError')
            code, message = self._get_error_code_and_message(response_data)
            sys.stderr.write(msg.format(error_code=code,
                                        error_message=message))
            sys.stderr.write('\n')
            return http_response.status_code - 399
        if http_response.status_code >= 400:
            msg = self._session.get_data('messages/ClientError')
            code, message = self._get_error_code_and_message(response_data)
            sys.stderr.write(msg.format(error_code=code,
                                        error_message=message))
            sys.stderr.write('\n')
            return http_response.status_code - 399
        return 0

    def _get_error_code_and_message(self, response):
        code = 'Unknown'
        message = 'Unknown'
        if 'Errors' in response:
            if isinstance(response['Errors'], list):
                error = response['Errors'][-1]
                if 'Code' in error:
                    code = error['Code']
                elif 'Type' in error:
                    code = error['Type']
                if 'Message' in error:
                    message = error['Message']
        return (code, message)
