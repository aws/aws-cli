# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from awscli.argprocess import ParamError, ParamSyntaxError
from awscli.customizations.arguments import OverrideRequiredArgsArgument
from awscli.paramfile import LOCAL_PREFIX_MAP, get_paramfile


def register_cli_input_args(cli):
    cli.register('building-argument-table', add_cli_input_json)
    cli.register('building-argument-table', add_cli_input_yaml)


def add_cli_input_json(session, argument_table, **kwargs):
    _add_cli_input_argument(session, argument_table, CliInputJSONArgument)


def add_cli_input_yaml(session, argument_table, **kwargs):
    _add_cli_input_argument(session, argument_table, CliInputYAMLArgument)


def _add_cli_input_argument(session, argument_table, argument_cls):
    # This argument cannot support operations with streaming output which
    # is designated by the argument name `outfile`.
    if 'outfile' not in argument_table:
        cli_input_argument = argument_cls(session)
        cli_input_argument.add_to_arg_table(argument_table)


class CliInputArgument(OverrideRequiredArgsArgument):
    """This argument inputs a formatted string as the entire command input.

    Ideally, the value to this argument will be a filled out file in a
    format such as JSON that was generated by ``--generate-cli-skeleton``.
    The parameters in the file will be overwritten by any arguments specified
    on the command line.
    """

    def _register_argument_action(self):
        self._session.register(
            'calling-command.*', self.add_to_call_parameters
        )
        super(CliInputArgument, self)._register_argument_action()

    def add_to_call_parameters(self, call_parameters, parsed_args, **kwargs):
        arg_value = self._get_arg_value(parsed_args)
        if arg_value is None:
            return

        loaded_params = self._load_parameters(arg_value)
        if not isinstance(loaded_params, dict):
            raise ParamError(
                self.cli_name,
                "Invalid type: expecting map, "
                f"received {type(loaded_params)}",
            )
        self._update_call_parameters(call_parameters, loaded_params)

    def _get_arg_value(self, parsed_args):
        arg_value = getattr(parsed_args, self.py_name, None)
        if arg_value is None:
            return

        cli_input_args = [
            k
            for k, v in vars(parsed_args).items()
            if v is not None and k.startswith('cli_input')
        ]
        if len(cli_input_args) != 1:
            raise ParamSyntaxError(
                'Only one --cli-input- parameter may be specified.'
            )

        # If the value starts with file:// or fileb://, return the contents
        # from the file.
        paramfile_data = get_paramfile(arg_value, LOCAL_PREFIX_MAP)
        if paramfile_data is not None:
            return paramfile_data

        return arg_value

    def _load_parameters(self, arg_value):
        raise NotImplementedError('_load_parameters')

    def _update_call_parameters(self, call_parameters, loaded_parameters):
        for input_key in loaded_parameters.keys():
            # Only add the values to ``call_parameters`` if not already
            # present.
            if input_key not in call_parameters:
                call_parameters[input_key] = loaded_parameters[input_key]


class CliInputJSONArgument(CliInputArgument):
    """This argument inputs a JSON string as the entire input for a command.

    Ideally, the value to this argument should be a filled out JSON file
    generated by ``--generate-cli-skeleton``. The items in the JSON string
    will not clobber other arguments entered into the command line.
    """

    ARG_DATA = {
        'name': 'cli-input-json',
        'group_name': 'cli_input',
        'help_text': (
            'Reads arguments from the JSON string provided. The JSON string '
            'follows the format provided by ``--generate-cli-skeleton``. If '
            'other arguments are provided on the command line, those values '
            'will override the JSON-provided values. It is not possible to '
            'pass arbitrary binary values using a JSON-provided value as the '
            'string will be taken literally. This may not be specified along '
            'with ``--cli-input-yaml``.'
        ),
    }

    def _load_parameters(self, arg_value):
        try:
            return json.loads(arg_value)
        except ValueError:
            raise ParamError(self.name, "Invalid JSON received.")


class CliInputYAMLArgument(CliInputArgument):
    ARG_DATA = {
        'name': 'cli-input-yaml',
        'group_name': 'cli_input',
        'help_text': (
            'Reads arguments from the YAML string provided. The YAML string '
            'follows the format provided by '
            '``--generate-cli-skeleton yaml-input``. '
            'If other arguments are provided on the command line, those '
            'values will override the YAML-provided values. This may not be '
            'specified along with ``--cli-input-json``.'
        ),
    }

    def _load_parameters(self, arg_value):
        yaml = YAML(typ='safe', pure=True)

        try:
            return yaml.load(arg_value)
        except YAMLError:
            raise ParamError(self.name, "Invalid YAML received.")
