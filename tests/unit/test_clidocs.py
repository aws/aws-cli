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
from awscli.testutils import unittest

from awscli.clidocs import OperationDocumentEventHandler
from botocore.model import ShapeResolver, StructureShape

import mock


class TestRecursiveShapes(unittest.TestCase):
    def setUp(self):
        self.arg_table = {}
        self.help_command = mock.Mock()
        self.help_command.event_class = 'custom'
        self.help_command.arg_table = self.arg_table
        self.help_command.obj.service.operations = []
        self.operation_handler = OperationDocumentEventHandler(
            self.help_command)

    def assert_rendered_docs_contain(self, expected):
        writes = [args[0][0] for args in
                  self.help_command.doc.write.call_args_list]
        writes = '\n'.join(writes)
        self.assertIn(expected, writes)

    def test_handle_recursive_input(self):
        shape_map = {
            'RecursiveStruct': {
                'type': 'structure',
                'members': {
                    'A': {'shape': 'NonRecursive'},
                    'B':  {'shape': 'RecursiveStruct'},
                }
            },
            'NonRecursive': {'type': 'string'}
        }
        shape = StructureShape('RecursiveStruct', shape_map['RecursiveStruct'],
                               ShapeResolver(shape_map))

        self.arg_table['arg-name'] = mock.Mock(argument_model=shape)
        self.operation_handler.doc_option_example(
            'arg-name', self.help_command)
        self.assert_rendered_docs_contain('{ ... recursive ... }')

    def test_handle_recursive_output(self):
        shape_map = {
            'RecursiveStruct': {
                'type': 'structure',
                'members': {
                    'A': {'shape': 'NonRecursive'},
                    'B':  {'shape': 'RecursiveStruct'},
                }
            },
            'NonRecursive': {'type': 'string'}
        }
        shape = StructureShape('RecursiveStruct', shape_map['RecursiveStruct'],
                               ShapeResolver(shape_map))

        operation = mock.Mock()
        operation.model.output_shape = shape
        self.help_command.obj = operation
        self.operation_handler.doc_output(self.help_command, 'event-name')
        self.assert_rendered_docs_contain('( ... recursive ... )')
