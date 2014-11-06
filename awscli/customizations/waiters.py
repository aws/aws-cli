# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore import xform_name

from awscli.clidriver import ServiceOperation
from awscli.customizations.commands import BasicCommand, BasicHelp, \
    BasicDocHandler


def register_add_waiters(cli):
    cli.register('building-command-table', add_waiters)


def add_waiters(command_table, session, command_object, **kwargs):
    # Check if the command object passed in has a ``service_object``. We
    # only want to add wait commands to top level model-driven services.
    # These require service objects.
    service_object = getattr(command_object, 'service_object', None)
    if service_object is not None:
        # Get a client out of the service object.
        client = translate_service_object_to_client(service_object)
        # Find all of the waiters for that client.
        waiters = client.waiter_names
        # If there are waiters make a wait command.
        if waiters:
            command_table['wait'] = WaitCommand(client, service_object)


def translate_service_object_to_client(service_object):
    # Create a client from a service object.
    session = service_object.session
    return session.create_client(service_object.service_name)


class WaitCommand(BasicCommand):
    NAME = 'wait'
    DESCRIPTION = 'Wait until a particular condition is satisfied.'

    def __init__(self, client, service_object):
        self._client = client
        self._service_object = service_object
        self.waiter_cmd_builder = WaiterStateCommandBuilder(
            client=self._client,
            service_object=self._service_object
        )
        super(WaitCommand, self).__init__(self._service_object.session)

    def _run_main(self, parsed_args, parsed_globals):
        if parsed_args.subcommand is None:
            raise ValueError("usage: aws [options] <command> <subcommand> "
                             "[parameters]\naws: error: too few arguments")

    def _build_subcommand_table(self):
        subcommand_table = super(WaitCommand, self)._build_subcommand_table()
        self.waiter_cmd_builder.build_all_waiter_state_cmds(subcommand_table)
        return subcommand_table

    def create_help_command(self):
        return BasicHelp(self._session, self,
                         command_table=self.subcommand_table,
                         arg_table=self.arg_table,
                         event_handler_class=WaiterCommandDocHandler)


class WaiterStateCommandBuilder(object):
    def __init__(self, client, service_object):
        self._client = client
        self._service_object = service_object

    def build_all_waiter_state_cmds(self, subcommand_table):
        """This adds waiter state commands to the subcommand table passed in.

        This is the method that adds waiter state commands like
        ``instance-running`` to ``ec2 wait``.
        """
        waiters = self._client.waiter_names
        for waiter_name in waiters:
            waiter_cli_name = waiter_name.replace('_', '-')
            subcommand_table[waiter_cli_name] = \
                self._build_waiter_state_cmd(waiter_name)

    def _build_waiter_state_cmd(self, waiter_name):
        # Get the waiter
        waiter = self._client.get_waiter(waiter_name)

        # Create the cli name for the waiter operation
        waiter_cli_name = waiter_name.replace('_', '-')

        # Obtain the name of the service operation that is used to implement
        # the specified waiter.
        operation_name = waiter.config.operation

        # Create an operation object to make a command for the waiter. The
        # operation object is used to generate the arguments for the waiter
        # state command.
        operation_object = self._service_object.get_operation(operation_name)
        waiter_state_command = WaiterStateCommand(
            name=waiter_cli_name, parent_name='wait',
            operation_object=operation_object,
            operation_caller=WaiterCaller(self._client, waiter_name),
            service_object=self._service_object
        )
        # Build the top level description for the waiter state command.
        # Most waiters do not have a description so they need to be generated
        # using the waiter configuration.
        waiter_state_doc_builder = WaiterStateDocBuilder(waiter.config)
        description = waiter_state_doc_builder.build_waiter_state_description()
        waiter_state_command.DESCRIPTION = description
        return waiter_state_command


class WaiterStateDocBuilder(object):
    SUCCESS_DESCRIPTIONS = {
        'error': u'%s is thrown ',
        'path': u'%s ',
        'pathAll': u'%s for all elements ',
        'pathAny': u'%s for any element ',
        'status': u'%s response is received '
    }

    def __init__(self, waiter_config):
        self._waiter_config = waiter_config

    def build_waiter_state_description(self):
        description = self._waiter_config.description
        # Use the description provided in the waiter config file. If no
        # description is provided, use a heuristic to generate a description
        # for the waiter.
        if not description:
            description = u'Wait until '
            # Look at all of the acceptors and find the success state
            # acceptor.
            for acceptor in self._waiter_config.acceptors:
                # Build the description off of the success acceptor.
                if acceptor.state == 'success':
                    description += self._build_success_description(acceptor)
                    break
            # Include what operation is being used.
            description += self._build_operation_description(
                self._waiter_config.operation)
        return description

    def _build_success_description(self, acceptor):
        matcher = acceptor.matcher
        # Pick the description template to use based on what the matcher is.
        success_description = self.SUCCESS_DESCRIPTIONS[matcher]
        resource_description = None
        # If success is based off of the state of a resource include the
        # description about what resource is looked at.
        if matcher in ['path', 'pathAny', 'pathAll']:
            resource_description = u'JMESPath query %s returns ' % \
                acceptor.argument
            # Prepend the resource description to the template description
            success_description = resource_description + success_description
        # Complete the description by filling in the expected success state.
        full_success_description = success_description % acceptor.expected
        return full_success_description

    def _build_operation_description(self, operation):
        operation_name = xform_name(operation).replace('_', '-')
        return u'when polling with ``%s``.' % operation_name


class WaiterCaller(object):
    def __init__(self, client, waiter_name):
        self._client = client
        self._waiter_name = waiter_name

    def invoke(self, operation_object, parameters, parsed_globals):
        # Create the endpoint based on the parsed globals
        endpoint = operation_object.service.get_endpoint(
            region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl)
        # Make a clone of the client using the newly configured endpoint
        client = self._client.clone_client(endpoint=endpoint)
        # Make the waiter and call its wait method.
        client.get_waiter(self._waiter_name).wait(**parameters)
        return 0


class WaiterStateCommand(ServiceOperation):
    DESCRIPTION = ''

    def create_help_command(self):
        help_command = super(WaiterStateCommand, self).create_help_command()
        # Change the operation object's description by changing it to the
        # description for a waiter state command.
        self._operation_object.documentation = self.DESCRIPTION
        # Change the output shape because waiters provide no output.
        self._operation_object.model.output_shape = None
        return help_command


class WaiterCommandDocHandler(BasicDocHandler):
    def doc_synopsis_start(self, help_command, **kwargs):
        pass

    def doc_synopsis_option(self, arg_name, help_command, **kwargs):
        pass

    def doc_synopsis_end(self, help_command, **kwargs):
        pass

    def doc_options_start(self, help_command, **kwargs):
        pass

    def doc_option(self, arg_name, help_command, **kwargs):
        pass
