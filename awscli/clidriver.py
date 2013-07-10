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
from botocore.compat import copy_kwargs

from awscli import EnvironmentVariables, __version__
from awscli.formatter import get_formatter
from awscli.paramfile import get_paramfile
from awscli.plugin import load_plugins
from awscli.argparser import MainArgParser
from awscli.argparser import ServiceArgParser
from awscli.argparser import OperationArgParser
from awscli.help import ProviderHelpCommand
from awscli.help import ServiceHelpCommand
from awscli.help import OperationHelpCommand
from awscli.argprocess import unpack_cli_arg


LOG = logging.getLogger('awscli.clidriver')


class UnknownArgumentError(Exception):
    pass


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
        return commands

    def _build_argument_table(self):
        LOG.debug('_build_argument_table')
        argument_table = {}
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
                    # "{provider}/_regions", so first resolve
                    # the provider.
                    provider = self.session.get_variable('provider')
                    # The grab the var from the session
                    choices_path = choices.format(provider=provider)
                    choices = list(self.session.get_data(choices_path))
                option_params['choices'] = choices
            argument_object = BuiltInArgument(option, option_params)
            argument_object.add_to_arg_table(argument_table)
        # Then the final step is to send out an event so handlers
        # can add extra arguments or modify existing arguments.
        LOG.debug('_build_argument_table_again')
        self.session.emit('building-top-level-params',
                          argument_table=argument_table)
        return argument_table

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
        self._handle_top_level_args(parsed_args)
        try:
            return command_table[parsed_args.command](remaining, parsed_args)
        except UnknownArgumentError as e:
            sys.stderr.write(str(e) + '\n')
            return 255
        except Exception as e:
            LOG.debug("Exception caught in main()", exc_info=True)
            LOG.debug("Exiting with rc 255")
            sys.stderr.write("%s\n" % e)
            return 255

    def _handle_top_level_args(self, args):
        self.session.emit('top-level-args-parsed', parsed_args=args)
        if args.debug:
            # TODO:
            # Unfortunately, by setting debug mode here, we miss out
            # on all of the debug events prior to this such as the
            # loading of plugins, etc.
            self.session.set_debug_logger(logger_name='botocore')
            self.session.set_debug_logger(logger_name='awscli')


class CLICommand(object):
    """Interface for a CLI command.

    This class represents a top level CLI command
    (``aws ec2``, ``aws s3``, ``aws config``).

    """

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


class BuiltInCommand(CLICommand):
    """
    A top-level command that is not associated with a service.

    For example, if you want to implement ``aws mycommand``
    we would create a BuiltInCommand object for that.
    """

    def __init__(self, name, session):
        self.name = name
        self.session = session


class ServiceCommand(CLICommand):
    """A service command for the CLI.

    For example, ``aws ec2 ...`` we'd create a ServiceCommand
    object that represents the ec2 service.

    """

    def __init__(self, name, session):
        self.name = name
        self.session = session
        self._command_table = None
        self._service_object = None

    def _get_command_table(self):
        if self._command_table is None:
            self._command_table = self._create_command_table()
        return self._command_table

    def _get_service_object(self):
        if self._service_object is None:
            self._service_object = self.session.get_service(self.name)
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
        command_table = {}
        service_object = self._get_service_object()
        for operation_object in service_object.operations:
            LOG.debug(operation_object)
            LOG.debug('operation.name=%s' % operation_object.name)
            cli_name = xform_name(operation_object.name, '-')
            command_table[cli_name] = ServiceOperation(
                name=cli_name,
                operation_object=operation_object,
                operation_caller=CLIOperationCaller(self.session),
                service_object=service_object)
        return command_table

    def create_help_command(self):
        command_table = self._get_command_table()
        service_object = self._get_service_object()
        return ServiceHelpCommand(session=self.session,
                                  obj=service_object,
                                  command_table=command_table,
                                  arg_table=None)

    def _create_parser(self):
        # Also add a 'help' command.
        command_table = self._get_command_table()
        command_table['help'] = self.create_help_command()
        self.session.emit('building-operation-table.%s' % self.name,
                          command_table=command_table)
        return ServiceArgParser(
            operations_table=command_table, service_name=self.name)


class BaseCLIArgument(object):
    """Interface for CLI argument.

    This class represents the interface used for representing CLI
    arguments.

    """

    def __init__(self, name, argument_object):
        self._name = name
        self.argument_object = argument_object

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

    def add_to_parser(self, parser, cli_name=None):
        """Add this object to the parser instance.

        This method is called by the associated ``ArgumentParser``
        instance.  This method should make the relevant calls
        to ``add_argument`` to add itself to the argparser.

        :type parser: ``argparse.ArgumentParser``.
        :param parser: The argument parser associated with the operation.

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

    @property
    def cli_name(self):
        return '--' + self._name

    @property
    def cli_type_name(self):
        pass

    @property
    def required(self):
        pass

    @property
    def documentation(self):
        pass

    @property
    def py_name(self):
        return self._name.replace('-', '_')

    @property
    def name(self):
        return self._name


class BuiltInArgument(BaseCLIArgument):
    """
    Represents a CLI argument that maps to the top-level command.
    These are global arguments that are not associated with any
    particular service.
    """

    def add_to_arg_table(self, argument_table):
        # This is used by the ServiceOperation so we can add ourselves
        # to the argument table.  For the normal case, we use our name
        # as the key, and ourself as the value.  For a more complicated
        # example, see BooleanArgument.add_to_arg_table
        argument_table[self._name] = self

    def add_to_parser(self, parser, cli_name=None):
        """

        See the ``BaseCLIArgument.add_to_parser`` docs for more information.

        """
        if not cli_name:
            cli_name = self.cli_name
        parser.add_argument(cli_name, **self.argument_object)

    def required(self):
        required = False
        if 'required' in self.argument_object:
            required = self.argument_object['required']
        return required

    @property
    def documentation(self):
        documentation = ''
        if 'help' in self.argument_object:
            documentation = self.argument_object['help']
        return documentation

    @property
    def cli_type_name(self):
        cli_type_name = 'string'
        if 'action' in self.argument_object:
            if self.argument_object['action'] in ['store_true',
                                                  'store_false']:
                cli_type_name = 'boolean'
        return cli_type_name

    @property
    def cli_type(self):
        cli_type = str
        if 'action' in self.argument_object:
            if self.argument_object['action'] in ['store_true',
                                                  'store_false']:
                cli_type = bool
        return cli_type

    @property
    def choices(self):
        choices = []
        if 'choices' in self.argument_object:
            choices = self.argument_object['choices']
        return choices


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
        super(CLIArgument, self).__init__(name, argument_object)
        self.operation_object = operation_object

    @property
    def name(self):
        # TODO: move cli specific attrs out of the parameter
        # object, or at least into a distinct config property
        # or something.
        # The [2:] is to strip off the leading '--' part (--foo -> foo).
        return self._name

    @property
    def py_name(self):
        return self._name.replace('-', '_')

    @property
    def required(self):
        return self.argument_object.required

    @required.setter
    def required(self, value):
        self.argument_object.required = value

    @property
    def documentation(self):
        return self.argument_object.documentation

    @property
    def cli_type_name(self):
        return self.argument_object.type

    @property
    def cli_type(self):
        return self.TYPE_MAP.get(self.argument_object.type, str)

    def add_to_arg_table(self, argument_table):
        # This is used by the ServiceOperation so we can add ourselves
        # to the argument table.  For the normal case, we use our name
        # as the key, and ourself as the value.  For a more complicated
        # example, see BooleanArgument.add_to_arg_table
        argument_table[self.name] = self

    def add_to_parser(self, parser, cli_name=None):
        """

        See the ``BaseCLIArgument.add_to_parser`` docs for more information.

        """
        # We need to add ourselve to the argparser instance.  For the normal
        # case we just need to make a single add_argument call.
        if not cli_name:
            cli_name = self.cli_name
        LOG.debug('add_to_parser: %s' % cli_name)
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
            LOG.debug('add_to_params: %s' % self.py_name)
            parameters[self.argument_object.py_name] = self._unpack_argument(value)

    def _unpack_argument(self, value):
        if not hasattr(self.argument_object, 'no_paramfile'):
            value = self._handle_param_file(value)
        service_name = self.operation_object.service.endpoint_prefix
        operation_name = xform_name(self.operation_object.name, '-')
        responses = self._emit('process-cli-arg.%s.%s' % (
            service_name, operation_name), param=self.argument_object,
            value=value,
            operation=self.operation_object)
        override = first_non_none_response(responses)
        if override is not None:
            # A plugin supplied an alternate conversion,
            # use it instead.
            return override
        else:
            # Fall back to the default arg processing.
            return unpack_cli_arg(self.argument_object, value)

    def _handle_param_file(self, value):
        session = self.operation_object.service.session
        if isinstance(value, list) and len(value) == 1:
            temp = value[0]
        else:
            temp = value
        temp = get_paramfile(session, temp)
        if temp:
            value = temp
        return value

    def _emit(self, name, **kwargs):
        session = self.operation_object.service.session
        return session.emit(name, **kwargs)


class ListArgument(CLIArgument):

    def add_to_parser(self, parser, cli_name=None):
        if not cli_name:
            cli_name = self.cli_name
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

    def add_to_parser(self, parser, cli_name=None):
        # If we're a required parameter we need to add two options
        # to the argparse.ArgumentParser instance, one for --foo, one for
        # --no-foo.  We handle this by knowing that we're going to be
        # called twice (we added two values to the argument table in
        # add_to_arg_table).  The first time through we create a
        # mutex group, the second time through we add to this mutex group.
        if not cli_name:
            cli_name = self.cli_name
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
                dest=cli_name[2:], action=action)
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

    def __init__(self, name, operation_object, operation_caller,
                 service_object):
        LOG.debug('creating ServiceOperation: %s' % name)
        self._arg_table = None
        self._name = name
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
            op_help(parsed_args, parsed_globals)
        elif parsed_args.help:
            remaining.append(parsed_args.help)
        if remaining:
            raise UnknownArgumentError(
                "Unknown options: %s" % ', '.join(remaining))
        call_parameters = self._build_call_parameters(parsed_args,
                                                      self.arg_table)
        return self._operation_caller.invoke(
            self._operation_object, call_parameters, parsed_globals)

    def create_help_command(self):
        return OperationHelpCommand(
            self._service_object.session, self._service_object,
            self._operation_object, arg_table=self.arg_table)

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
        for name, value in vars(args).items():
            if name in arg_table:
                arg_object = arg_table[name]
                arg_object.add_to_params(service_params, value)
        return service_params

    def _create_argument_table(self):
        argument_table = {}
        # Arguments are treated a differently than service and
        # operations.  Instead of doing a get_parameter() we just
        # load all the parameter objects up front for the operation.
        # We could potentially do the same thing as service/operations
        # but botocore already builds all the parameter objects
        # when calling an operation so we'd have to optimize that first
        # before using get_parameter() in the cli would be advantageous
        for argument in self._operation_object.params:
            #cli_arg_name = xform_name(argument.name, '-')
            cli_arg_name = argument.cli_name[2:]
            arg_class = self.ARG_TYPES.get(argument.type,
                                           self.DEFAULT_ARG_CLASS)
            arg_object = arg_class(cli_arg_name, argument,
                                   self._operation_object)
            arg_object.add_to_arg_table(argument_table)
        LOG.debug(argument_table)
        service_name = self._service_object.endpoint_prefix
        operation_name = self._operation_object.name
        self._emit('building-argument-table.%s.%s' % (service_name,
                                                      operation_name),
                   operation=self._operation_object,
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
