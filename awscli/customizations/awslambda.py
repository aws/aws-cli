# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import zipfile
import copy
from contextlib import closing

from botocore.vendored import six

from awscli.arguments import CustomArgument, CLIArgument
from awscli.customizations import utils

ERROR_MSG = (
    "--zip-file must be a zip file with the fileb:// prefix.\n"
    "Example usage:  --zip-file fileb://path/to/file.zip")

ZIP_DOCSTRING = ('<p>The path to the zip file of the code you are uploading. '
                 'Example: fileb://code.zip</p>')


def register_lambda_create_function(cli):
    cli.register('building-argument-table.lambda.create-function',
                 _extract_code_and_zip_file_arguments)
    cli.register('building-argument-table.lambda.update-function-code',
                 _modify_zipfile_docstring)
    cli.register('process-cli-arg.lambda.update-function-code',
                 validate_is_zip_file)


def validate_is_zip_file(cli_argument, value, **kwargs):
    if cli_argument.name == 'zip-file':
        _should_contain_zip_content(value)


def _extract_code_and_zip_file_arguments(session, argument_table, **kwargs):
    argument_table['zip-file'] = ZipFileArgument(
        'zip-file', help_text=ZIP_DOCSTRING, cli_type_name='blob')
    code_argument = argument_table['code']
    code_model = copy.deepcopy(code_argument.argument_model)
    del code_model.members['ZipFile']
    argument_table['code'] = CodeArgument(
        name='code',
        argument_model=code_model,
        operation_model=code_argument._operation_model,
        is_required=False,
        event_emitter=session.get_component('event_emitter'),
        serialized_name='Code'
    )


def _modify_zipfile_docstring(session, argument_table, **kwargs):
    if 'zip-file' in argument_table:
        argument_table['zip-file'].documentation = ZIP_DOCSTRING


def _should_contain_zip_content(value):
    if not isinstance(value, bytes):
        # If it's not bytes it's basically impossible for
        # this to be valid zip content, but we'll at least
        # still try to load the contents as a zip file
        # to be absolutely sure.
        value = value.encode('utf-8')
    fileobj = six.BytesIO(value)
    try:
        with closing(zipfile.ZipFile(fileobj)) as f:
            f.infolist()
    except zipfile.BadZipfile:
        raise ValueError(ERROR_MSG)


class ZipFileArgument(CustomArgument):
    def add_to_params(self, parameters, value):
        if value is None:
            return
        _should_contain_zip_content(value)
        zip_file_param = {'ZipFile': value}
        if parameters.get('Code'):
            parameters['Code'].update(zip_file_param)
        else:
            parameters['Code'] = zip_file_param


class CodeArgument(CLIArgument):
    def add_to_params(self, parameters, value):
        if value is None:
            return
        unpacked = self._unpack_argument(value)
        if 'ZipFile' in unpacked:
            raise ValueError("ZipFile cannot be provided "
                             "as part of the --code argument.  "
                             "Please use the '--zip-file' "
                             "option instead to specify a zip file.")
        if parameters.get('Code'):
            parameters['Code'].update(unpacked)
        else:
            parameters['Code'] = unpacked
