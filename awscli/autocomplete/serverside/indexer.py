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
import json

from botocore.exceptions import UnknownServiceError
from botocore import xform_name

import awscli.clidriver
from awscli.autocomplete.db import DatabaseConnection


def create_apicall_indexer(filename):
    index = APICallIndexer(DatabaseConnection(filename))
    return index


class APICallIndexer(object):
    _CREATE_APICALL_TABLE = """\
        CREATE TABLE IF NOT EXISTS apicall_table (
          apicall_data TEXT,
          param_id INTEGER UNIQUE,
          FOREIGN KEY (param_id) REFERENCES
            param_table(param_id)
        );
    """
    _INSERT_COMMAND = """\
        INSERT OR REPLACE INTO apicall_table (apicall_data, param_id)
        VALUES
          (:apicall_data,
           (SELECT param_id FROM param_table
            WHERE
              argname = :argname AND
              command = :command AND
              parent = :parent))
    """

    def __init__(self, db_connection):
        self._db_connection = db_connection

    def generate_index(self, clidriver):
        self._create_tables()
        session = clidriver.session
        loader = session.get_component('data_loader')
        for key, command in self._iter_all_commands(clidriver):
            self._construct_completion_data(loader, command)

    def _iter_all_commands(self, clidriver):
        stack = sorted(clidriver.subcommand_table.items())
        while stack:
            key, command = stack.pop()
            for subkey, subcommand in sorted(command.subcommand_table.items()):
                stack.append((subkey, subcommand))
            yield key, command

    def _create_tables(self):
        self._db_connection.execute(self._CREATE_APICALL_TABLE)

    def _construct_completion_data(self, loader, command):
        # This method uses internal attributes to decided whether or not
        # to generate server side completion data.
        # This is using internal attributes and specific command subclasses
        # to retrieve the needed completion info.  There's no public
        # way to access this information.
        if not isinstance(command, awscli.clidriver.ServiceOperation):
            return
        # First, if there's no completions-1.json file, we can immediately
        # return.
        op_model = command._operation_model
        service_name = op_model.service_model.service_name
        try:
            completions = loader.load_service_model(
                service_name, type_name='completions-1')
        except UnknownServiceError:
            return None
        # The completions-1 file is for the entire service.  We need
        # to now check if there's completion data for this specific
        # operation.
        if op_model.name not in completions['operations']:
            return
        completion_for_op = completions['operations'][op_model.name]
        for arg_name, arg_obj in sorted(command.arg_table.items()):
            if not hasattr(arg_obj, '_serialized_name'):
                continue
            api_casing = arg_obj._serialized_name
            if api_casing not in completion_for_op:
                continue
            # At this point we know there's completion info we need.
            transformed = self._transform_completion_data(
                completion_for_op[api_casing], completions['resources'],
                service_name)
            self._insert_into_db(transformed, arg_name, command)

    def _insert_into_db(self, transformed, arg_name, command):
        parent = '.'.join(['aws'] + command.lineage_names[:-1])
        self._db_connection.execute(
            self._INSERT_COMMAND,
            apicall_data=json.dumps(transformed),
            argname=arg_name,
            command=command.name,
            parent=parent,
        )

    def _transform_completion_data(self, completions_for_op, resources,
                                   service_name):
        # The completions-1.json data is strictly model based.  That is,
        # it's based entirely on the service API and has no mention of CLI
        # commands, parameters, etc.  This method attempts to map
        # the CLI specific commands parameters to the data in
        # completions-1.json.
        # The final format we need is:
        #
        # {'completions': [{
        #    'parameters': {},
        #    'service': 'client-name',
        #    'operation': 'snake_case_method',
        #    'jp_expr': 'jmespath[].expr',
        #  }]
        # }
        #
        # This transformation minimizes the amount of processing needed
        # by the completer during completion time.
        completions = []
        for completion in completions_for_op['completions']:
            resource = resources[completion['resourceName']]
            jp_expr = resource['resourceIdentifier'][
                completion['resourceIdentifier']]
            transformed = {'parameters': completion['parameters'],
                           'service': service_name,
                           'operation': xform_name(resource['operation']),
                           'jp_expr': jp_expr}
            completions.append(transformed)
        return {'completions': completions}
