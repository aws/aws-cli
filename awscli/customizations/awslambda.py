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
from awscli.arguments import CustomArgument
from awscli.customizations import utils


def register_lambda_create_function(cli):
    cli.register('building-argument-table.lambda.create-function',
                 _flatten_code_argument)


def _flatten_code_argument(argument_table, **kwargs):
    argument_table['zip-file'] = ZipFileArgument(
        'zip-file', help_text=('The path to the zip file of the code you '
                               'are uploading. Example: fileb://code.zip'),
        cli_type_name='blob', required=True)
    del argument_table['code']


class ZipFileArgument(CustomArgument):
    def add_to_params(self, parameters, value):
        zip_file_param = {'ZipFile': value}
        parameters['Code'] = zip_file_param
