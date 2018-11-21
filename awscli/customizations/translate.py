# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import copy

from awscli.arguments import CustomArgument, CLIArgument

FILE_DOCSTRING = ('<p>The path to the file of the code you are uploading. '
                  'Example: fileb://data.csv</p>')


def register_translate_import_terminology(cli):
    cli.register('building-argument-table.translate.import-terminology',
                 _hoist_file_parameter)


def _hoist_file_parameter(session, argument_table, **kwargs):
    argument_table['data-file'] = FileArgument(
        'data-file', help_text=FILE_DOCSTRING, cli_type_name='blob',
        required=True)
    file_argument = argument_table['terminology-data']
    file_model = copy.deepcopy(file_argument.argument_model)
    del file_model.members['File']
    argument_table['terminology-data'] = TerminologyDataArgument(
        name='terminology-data',
        argument_model=file_model,
        operation_model=file_argument._operation_model,
        is_required=False,
        event_emitter=session.get_component('event_emitter'),
        serialized_name='TerminologyData'
    )


class FileArgument(CustomArgument):
    def add_to_params(self, parameters, value):
        if value is None:
            return
        file_param = {'File': value}
        if parameters.get('TerminologyData'):
            parameters['TerminologyData'].update(file_param)
        else:
            parameters['TerminologyData'] = file_param


class TerminologyDataArgument(CLIArgument):
    def add_to_params(self, parameters, value):
        if value is None:
            return
        unpacked = self._unpack_argument(value)
        if 'File' in unpacked:
            raise ValueError("File cannot be provided as part of the "
                             "'--terminology-data' argument. Please use the "
                             "'--data-file' option instead to specify a "
                             "file.")
        if parameters.get('TerminologyData'):
            parameters['TerminologyData'].update(unpacked)
        else:
            parameters['TerminologyData'] = unpacked
