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
import json
import sys

from botocore import xform_name
from botocore.stub import Stubber
from botocore.utils import ArgumentGenerator

from awscli.clidriver import CLIOperationCaller
from awscli.customizations.arguments import OverrideRequiredArgsArgument
from awscli.utils import json_encoder


def register_generate_cli_skeleton(cli):
    cli.register('building-argument-table', add_generate_skeleton)


def add_generate_skeleton(session, operation_model, argument_table, **kwargs):
    # This argument cannot support operations with streaming output which
    # is designated by the argument name `outfile`.
    if 'outfile' not in argument_table:
        generate_cli_skeleton_argument = GenerateCliSkeletonArgument(
            session, operation_model)
        generate_cli_skeleton_argument.add_to_arg_table(argument_table)


class GenerateCliSkeletonArgument(OverrideRequiredArgsArgument):
    """This argument writes a generated JSON skeleton to stdout

    The argument, if present in the command line, will prevent the intended
    command from taking place. Instead, it will generate a JSON skeleton and
    print it to standard output.
    """
    ARG_DATA = {
        'name': 'generate-cli-skeleton',
        'help_text': (
            'Prints a JSON skeleton to standard output without sending '
            'an API request. If provided with no value or the value '
            '``input``, prints a sample input JSON that can be used as an '
            'argument for ``--cli-input-json``. If provided with the value '
            '``output``, it validates the command inputs and returns a '
            'sample output JSON for that command.'
        ),
        'nargs': '?',
        'const': 'input',
        'choices': ['input', 'output'],
    }

    def __init__(self, session, operation_model):
        super(GenerateCliSkeletonArgument, self).__init__(session)
        self._operation_model = operation_model

    def _register_argument_action(self):
        self._session.register(
            'calling-command.*', self.generate_json_skeleton)
        super(GenerateCliSkeletonArgument, self)._register_argument_action()

    def override_required_args(self, argument_table, args, **kwargs):
        arg_name = '--' + self.name
        if arg_name in args:
            arg_location = args.index(arg_name)
            try:
                # If the value of --generate-cli-skeleton is ``output``,
                # do not force required arguments to be optional as
                # ``--generate-cli-skeleton output`` validates commands
                # as well as print out the sample output.
                if args[arg_location + 1] == 'output':
                    return
            except IndexError:
                pass
            super(GenerateCliSkeletonArgument, self).override_required_args(
                argument_table, args, **kwargs)

    def generate_json_skeleton(self, call_parameters, parsed_args,
                               parsed_globals, **kwargs):
        if getattr(parsed_args, 'generate_cli_skeleton', None):
            for_output = parsed_args.generate_cli_skeleton == 'output'
            operation_model = self._operation_model

            if for_output:
                service_name = operation_model.service_model.service_name
                operation_name = operation_model.name
                # TODO: It would be better to abstract this logic into
                # classes for both the input and output option such that
                # a similar set of inputs are taken in and output
                # similar functionality.
                return StubbedCLIOperationCaller(self._session).invoke(
                    service_name, operation_name, call_parameters,
                    parsed_globals)
            else:
                argument_generator = ArgumentGenerator()
                operation_input_shape = operation_model.input_shape
                if operation_input_shape is None:
                    skeleton = {}
                else:
                    skeleton = argument_generator.generate_skeleton(
                        operation_input_shape)

                sys.stdout.write(
                    json.dumps(skeleton, indent=4, default=json_encoder)
                )
                sys.stdout.write('\n')
                return 0


class StubbedCLIOperationCaller(CLIOperationCaller):
    """A stubbed CLIOperationCaller

    It generates a fake response and uses the response and provided parameters
    to make a stubbed client call for an operation command.
    """
    def _make_client_call(self, client, operation_name, parameters,
                          parsed_globals):
        method_name = xform_name(operation_name)
        operation_model = client.meta.service_model.operation_model(
            operation_name)
        fake_response = {}
        if operation_model.output_shape:
            argument_generator = ArgumentGenerator(use_member_names=True)
            fake_response = argument_generator.generate_skeleton(
                operation_model.output_shape)
        with Stubber(client) as stubber:
            stubber.add_response(method_name, fake_response)
            return getattr(client, method_name)(**parameters)
