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
from awscli.autocomplete.local import model


class InMemoryIndex(model.ModelIndex):
    # An in-memory version of a model index.

    def __init__(self, index):
        """

        The index param you provide is a dictionary that has top level
        keys that correspond to the method names here:


        ::

            {'command_names': {'dot.lineage': [<values>]},
             'arg_names': {'dot.lineage': {'command_name': [<values>]}},
             'get_argument_data': {
                 'dot.lineage': {
                     'command-name': {
                         'arg-name': (argname, type, command, parent,
                                      nargs, positional_arg)
                     }
                 }
            }

        """
        self.index = index

    def command_names(self, lineage):
        parent = '.'.join(lineage)
        return self.index['command_names'].get(parent, [])

    def arg_names(self, lineage, command_name, positional_arg=False):
        parent = '.'.join(lineage)
        arg_names = self.index['arg_names'].get(parent, {}).get(
            command_name, [])
        filtered_arg_names = []
        for arg_name in arg_names:
            arg_data = self.get_argument_data(lineage, command_name, arg_name)
            if arg_data.positional_arg == positional_arg:
                filtered_arg_names.append(arg_name)
        return filtered_arg_names

    def get_argument_data(self, lineage, command_name, arg_name):
        parent = '.'.join(lineage)
        arg_data = self.index['arg_data'].get(parent, {}).get(
            command_name, {}).get(arg_name)
        if arg_data is not None:
            return model.CLIArgument(*arg_data)


