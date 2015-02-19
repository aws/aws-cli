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

from awscli.clidocs import OperationDocumentEventHandler, \
    CLIDocumentEventHandler
from awscli.help import ServiceHelpCommand
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


class TestCLIDocumentEventHandler(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.obj = None
        self.command_table = {}
        self.arg_table = {}
        self.name = 'my-command'
        self.event_class = 'aws'

    def test_breadcrumbs_man(self):
        # Create an arbitrary help command class. This was chosen
        # because it is fairly easy to instantiate.
        help_cmd = ServiceHelpCommand(
            self.session, self.obj, self.command_table, self.arg_table,
            self.name, self.event_class
        )

        doc_handler = CLIDocumentEventHandler(help_cmd)
        doc_handler.doc_breadcrumbs(help_cmd)
        # These should not show up in the man page
        self.assertEqual(help_cmd.doc.getvalue().decode('utf-8'), '')

    def test_breadcrumbs_html(self):
        help_cmd = ServiceHelpCommand(
            self.session, self.obj, self.command_table, self.arg_table,
            self.name, self.event_class
        )
        help_cmd.doc.target = 'html'
        doc_handler = CLIDocumentEventHandler(help_cmd)
        doc_handler.doc_breadcrumbs(help_cmd)
        self.assertEqual(
            help_cmd.doc.getvalue().decode('utf-8'),
            '[ :ref:`aws <cli:aws>` ]'
        )

    def test_breadcrumbs_service_command_html(self):
        help_cmd = ServiceHelpCommand(
            self.session, self.obj, self.command_table, self.arg_table,
            self.name, 'ec2'
        )
        help_cmd.doc.target = 'html'
        doc_handler = CLIDocumentEventHandler(help_cmd)
        doc_handler.doc_breadcrumbs(help_cmd)
        self.assertEqual(
            help_cmd.doc.getvalue().decode('utf-8'),
            '[ :ref:`aws <cli:aws>` ]'
        )

    def test_breadcrumbs_operation_command_html(self):
        help_cmd = ServiceHelpCommand(
            self.session, self.obj, self.command_table, self.arg_table,
            self.name, 'ec2.run-instances'
        )
        help_cmd.doc.target = 'html'
        doc_handler = CLIDocumentEventHandler(help_cmd)
        doc_handler.doc_breadcrumbs(help_cmd)
        self.assertEqual(
            help_cmd.doc.getvalue().decode('utf-8'),
            '[ :ref:`aws <cli:aws>` . :ref:`ec2 <cli:aws ec2>` ]'
        )

    def test_breadcrumbs_wait_command_html(self):
        help_cmd = ServiceHelpCommand(
            self.session, self.obj, self.command_table, self.arg_table,
            self.name, 's3api.wait.object-exists'
        )
        help_cmd.doc.target = 'html'
        doc_handler = CLIDocumentEventHandler(help_cmd)
        doc_handler.doc_breadcrumbs(help_cmd)
        self.assertEqual(
            help_cmd.doc.getvalue().decode('utf-8'),
            ('[ :ref:`aws <cli:aws>` . :ref:`s3api <cli:aws s3api>`'
             ' . :ref:`wait <cli:aws s3api wait>` ]')
        )
