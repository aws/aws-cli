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
from awscli.testutils import unittest, FileCreator

from awscli.clidocs import OperationDocumentEventHandler, \
    CLIDocumentEventHandler, TopicListerDocumentEventHandler, \
    TopicDocumentEventHandler

from awscli.help import ServiceHelpCommand, TopicListerCommand, \
    TopicHelpCommand
from awscli.topictags import TopicTagDB
from botocore.model import ShapeResolver, StructureShape

import mock


class TestRecursiveShapes(unittest.TestCase):
    def setUp(self):
        self.arg_table = {}
        self.help_command = mock.Mock()
        self.help_command.event_class = 'custom'
        self.help_command.arg_table = self.arg_table
        self.operation_model = mock.Mock()
        self.operation_model.service_model.operation_names = []
        self.help_command.obj = self.operation_model
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

        operation_model = mock.Mock()
        operation_model.output_shape = shape
        self.help_command.obj = operation_model
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


class TestTopicListerDocumentEventHandler(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.file_creator = FileCreator()
        self.descriptions = [
            'This describes the first topic',
            'This describes the second topic'
        ]
        self.tags_dict = {
            'topic-name-1': {
                'title': ['The first topic title'],
                'description': [self.descriptions[0]],
                'category': ['General Topics', 'Troubleshooting']
            },
            'topic-name-2': {
                'title': ['The second topic title'],
                'description': [self.descriptions[1]],
                'category': ['General Topics']
            }
        }
        self.topic_tag_db = TopicTagDB(self.tags_dict)
        self.cmd = TopicListerCommand(self.session, self.topic_tag_db)
        self.doc_handler = TopicListerDocumentEventHandler(self.cmd)

    def tearDown(self):
        self.file_creator.remove_all()

    def test_breadcrumbs(self):
        self.doc_handler.doc_breadcrumbs(self.cmd)
        self.assertEqual(self.cmd.doc.getvalue().decode('utf-8'), '')
        self.cmd.doc.target = 'html'
        self.doc_handler.doc_breadcrumbs(self.cmd)
        self.assertEqual(
            '[ :doc:`aws <../reference/index>` ]',
            self.cmd.doc.getvalue().decode('utf-8')
        )

    def test_title(self):
        self.doc_handler.doc_title(self.cmd)
        self.assertIn(self.cmd.title, self.cmd.doc.getvalue().decode('utf-8'))

    def test_description(self):
        self.doc_handler.doc_description(self.cmd)
        self.assertIn(
            self.cmd.description,
            self.cmd.doc.getvalue().decode('utf-8')
        )

    def _assert_categories_and_topics(self, contents):
        for category in self.cmd.categories:
            self.assertIn(category, contents)
        for entry in self.cmd.entries:
            self.assertIn('* '+self.cmd.entries[entry], contents)

    def test_subitems_start(self):
        self.doc_handler.doc_subitems_start(self.cmd)
        contents = self.cmd.doc.getvalue().decode('utf-8')
        self._assert_categories_and_topics(contents)

        # Make sure the toctree is not in the man page
        self.assertNotIn('.. toctree::', contents)

    def test_subitems_start_html(self):
        self.cmd.doc.target = 'html'
        self.doc_handler.doc_subitems_start(self.cmd)
        contents = self.cmd.doc.getvalue().decode('utf-8')
        self._assert_categories_and_topics(contents)

        # Make sure the hidd toctree is in the html
        self.assertIn('.. toctree::', contents)
        self.assertIn(':hidden:', contents)


class TestTopicDocumentEventHandler(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.file_creator = FileCreator()

        self.name = 'topic-name-1'
        self.title = 'The first topic title'
        self.topic_body = 'Hello World!'

        self.tags_dict = {
            self.name: {
                'title': [self.title],
            }
        }
        self.topic_tag_db = TopicTagDB(self.tags_dict)
        self.cmd = TopicHelpCommand(self.session, self.name, self.topic_tag_db)
        self.dir_patch = mock.patch('awscli.topictags.TopicTagDB.topic_dir',
                                    self.file_creator.rootdir)
        self.doc_handler = TopicDocumentEventHandler(self.cmd)
        self.dir_patch.start()

    def tearDown(self):
        self.dir_patch.stop()
        self.file_creator.remove_all()

    def test_breadcrumbs(self):
        self.doc_handler.doc_breadcrumbs(self.cmd)
        self.assertEqual(self.cmd.doc.getvalue().decode('utf-8'), '')
        self.cmd.doc.target = 'html'
        self.doc_handler.doc_breadcrumbs(self.cmd)
        self.assertEqual(
            '[ :doc:`aws <../reference/index>` . :doc:`topics <index>` ]',
            self.cmd.doc.getvalue().decode('utf-8')
        )

    def test_title(self):
        self.doc_handler.doc_title(self.cmd)
        self.assertIn(self.cmd.title, self.cmd.doc.getvalue().decode('utf-8'))

    def test_description(self):
        lines = [
            ':title: ' + self.title,
            self.topic_body
        ]
        body = '\n'.join(lines)
        self.file_creator.create_file(self.name+'.rst', body)
        self.doc_handler.doc_description(self.cmd)
        contents = self.cmd.doc.getvalue().decode('utf-8')
        self.assertIn(self.topic_body, contents)
        self.assertNotIn(':title '+self.title, contents)
