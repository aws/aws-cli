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

from botocore.utils import ArgumentGenerator

from awscli.customizations.arguments import OverrideRequiredArgsArgument


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
    print it to standard output. This JSON skeleton then can be filled out
    and can be used as input to ``--input-cli-json`` in order to run the
    command with the filled out JSON skeleton.
    """
    ARG_DATA = {
        'name': 'generate-cli-skeleton',
        'help_text': 'Prints a sample input JSON to standard output. Note the '
                     'specified operation is not run if this argument is '
                     'specified. The sample input can be used as an argument '
                     'for ``--cli-input-json``.',
        'action': 'store_true',
        'group_name': 'generate_cli_skeleton'
    }

    def __init__(self, session, operation_model):
        super(GenerateCliSkeletonArgument, self).__init__(session)
        self._operation_model = operation_model

    def _register_argument_action(self):
        self._session.register(
            'calling-command.*', self.generate_json_skeleton)
        super(GenerateCliSkeletonArgument, self)._register_argument_action()

    def generate_json_skeleton(self, call_parameters, parsed_args,
                               parsed_globals, **kwargs):

        # Only perform the method if the ``--generate-cli-skeleton`` was
        # included in the command line.
        if getattr(parsed_args, 'generate_cli_skeleton', False):

            # Obtain the model of the operation
            operation_model = self._operation_model

            # Generate the skeleton based on the ``input_shape``.
            argument_generator = ArgumentGenerator()
            operation_input_shape = operation_model.input_shape
            # If the ``input_shape`` is ``None``, generate an empty
            # dictionary.
            if operation_input_shape is None:
                skeleton = {}
            else:
                skeleton = argument_generator.generate_skeleton(
                    operation_input_shape)

            # Write the generated skeleton to standard output.
            sys.stdout.write(json.dumps(skeleton, indent=4))
            sys.stdout.write('\n')
            # This is the return code
            return 0
