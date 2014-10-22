import json
import sys

from botocore.utils import ArgumentGenerator

from awscli.customizations.arguments import OverrideRequiredArgsArgument


def register_generate_cli_skeleton(cli):
    cli.register('building-argument-table', add_generate_skeleton)


def add_generate_skeleton(operation, argument_table, **kwargs):
    generate_cli_skeleton_argument = GenerateCliSkeletonArgument(operation)
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

    def __init__(self, operation_object):
        self._operation_object = operation_object
        super(GenerateCliSkeletonArgument, self).__init__(
            self._operation_object.session)

    def _register_argument_action(self):
        self._operation_object.session.register(
            'calling-service-operation', self.generate_json_skeleton)
        super(GenerateCliSkeletonArgument, self)._register_argument_action()

    def generate_json_skeleton(self, service_operation, call_parameters,
                               parsed_args, parsed_globals, **kwargs):

        # Only perform the method if the ``--generate-cli-skeleton`` was
        # included in the command line.
        if getattr(parsed_args, 'generate_cli_skeleton', False):

            # Ensure the operation will not be called from botocore.
            service_operation.disable_call_operation()

            # Obtain the model of the operation
            operation_model = self._operation_object.model

            # Generate the skeleton based on the ``input_shape``.
            argument_generator = ArgumentGenerator()
            operation_input_shape = operation_model.input_shape
            skeleton = argument_generator.generate_skeleton(
                operation_input_shape)

            # Write the generated skeleton to standard output.
            sys.stdout.write(json.dumps(skeleton, indent=4))
            sys.stdout.write('\n')
