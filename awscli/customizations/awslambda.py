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


ERROR_MSG = (
    "--zip-file must be a zip file with the fileb:// prefix.\n"
    "Example usage:  --zip-file fileb://path/to/file.zip")

ZIP_DOCSTRING = (
    '<p>The path to the zip file of the {param_type} you are uploading. '
    'Example: fileb://{param_type}.zip</p>'
)


def register_lambda_create_function(cli):
    cli.register('building-argument-table.lambda.create-function',
                 ZipFileArgumentHoister('Code').hoist)
    cli.register('building-argument-table.lambda.publish-layer-version',
                 ZipFileArgumentHoister('Content').hoist)
    cli.register('building-argument-table.lambda.update-function-code',
                 _modify_zipfile_docstring)
    cli.register('process-cli-arg.lambda.update-function-code',
                 validate_is_zip_file)


def validate_is_zip_file(cli_argument, value, **kwargs):
    if cli_argument.name == 'zip-file':
        _should_contain_zip_content(value)


class ZipFileArgumentHoister(object):
    """Hoists a ZipFile argument up to the top level.

    Injects a top-level ZipFileArgument into the argument table which maps
    a --zip-file parameter to the underlying ``serialized_name`` ZipFile
    shape. Repalces the old ZipFile argument with an instance of
    ReplacedZipFileArgument to prevent its usage and recommend the new
    top-level injected parameter.
    """
    def __init__(self, serialized_name):
        self._serialized_name = serialized_name
        self._name = serialized_name.lower()

    def hoist(self, session, argument_table, **kwargs):
        help_text = ZIP_DOCSTRING.format(param_type=self._name)
        argument_table['zip-file'] = ZipFileArgument(
            'zip-file', help_text=help_text, cli_type_name='blob',
            serialized_name=self._serialized_name
        )
        argument = argument_table[self._name]
        model = copy.deepcopy(argument.argument_model)
        del model.members['ZipFile']
        argument_table[self._name] = ReplacedZipFileArgument(
            name=self._name,
            argument_model=model,
            operation_model=argument._operation_model,
            is_required=False,
            event_emitter=session.get_component('event_emitter'),
            serialized_name=self._serialized_name,
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
    """A new ZipFile argument to be injected at the top level.

    This class injects a ZipFile argument under the specified serialized_name
    parameter. This can be used to take a top level parameter like --zip-file
    and inject it into a nested different parameter like Code so
    --zip-file foo.zip winds up being serilized as
    { 'Code': { 'ZipFile': <contents of foo.zip> } }.
    """
    def __init__(self, *args, **kwargs):
        self._param_to_replace = kwargs.pop('serialized_name')
        super(ZipFileArgument, self).__init__(*args, **kwargs)

    def add_to_params(self, parameters, value):
        if value is None:
            return
        _should_contain_zip_content(value)
        zip_file_param = {'ZipFile': value}
        if parameters.get(self._param_to_replace):
            parameters[self._param_to_replace].update(zip_file_param)
        else:
            parameters[self._param_to_replace] = zip_file_param


class ReplacedZipFileArgument(CLIArgument):
    """A replacement arugment for nested ZipFile argument.

    This prevents the use of a non-working nested argument that expects binary.
    Instead an instance of ZipFileArgument should be injected at the top level
    and used instead. That way fileb:// can be used to load the binary
    contents. And the argument class can inject those bytes into the correct
    serialization name.
    """
    def __init__(self, *args, **kwargs):
        super(ReplacedZipFileArgument, self).__init__(*args, **kwargs)
        self._cli_name = '--%s' % kwargs['name']
        self._param_to_replace = kwargs['serialized_name']

    def add_to_params(self, parameters, value):
        if value is None:
            return
        unpacked = self._unpack_argument(value)
        if 'ZipFile' in unpacked:
            raise ValueError(
                "ZipFile cannot be provided "
                "as part of the %s argument.  "
                "Please use the '--zip-file' "
                "option instead to specify a zip file." % self._cli_name)
        if parameters.get(self._param_to_replace):
            parameters[self._param_to_replace].update(unpacked)
        else:
            parameters[self._param_to_replace] = unpacked
