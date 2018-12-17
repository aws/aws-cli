# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os
import csv
from awscli.customizations.commands import BasicCommand
from awscli.customizations.configure.writer import ConfigFileWriter

from . import PREDEFINED_SECTION_NAMES, profile_to_section


class ConfigureImportCommand(BasicCommand):
    NAME = 'import'
    DESCRIPTION = BasicCommand.FROM_FILE('configure', 'import',
                                         '_description.rst')
    SYNOPSIS = 'aws configure import profile_name filename'
    EXAMPLES = BasicCommand.FROM_FILE('configure', 'import', '_examples.rst')
    ARG_TABLE = [
        {'name': 'profile_name',
         'help_text': 'The name of the new profile',
         'action': 'store',
         'cli_type_name': 'string', 'positional_arg': True}, 
        {'name': 'filename',
         'help_text': 'The name of the csv',
         'action': 'store',
         'cli_type_name': 'string', 'positional_arg': True}
    ]
    
    def __init__(self, session, config_writer=None):
        super(ConfigureImportCommand, self).__init__(session)
        if config_writer is None:
            config_writer = ConfigFileWriter()
        self._config_writer = config_writer

    def _run_main(self, args, parsed_globals):
        #importing the csv file into a nice hash
        with open(args.filename,"r") as f:
            i = csv.reader(f) 
            keys = next(i)
            values = next(i)
            data = dict(zip(keys, values))

        config_filename = os.path.expanduser(
            self._session.get_config_variable('credentials_file'))
        
        profile_name = args.profile_name
        
        updated_config = {
            '__section__' : profile_name,
            'aws_access_key_id' : data['Access key ID'],
            'aws_secret_access_key' : data['Secret access key']     
        }
        self._config_writer.update_config(updated_config, config_filename)
        