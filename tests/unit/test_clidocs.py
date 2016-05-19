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
import json

import mock
from botocore.model import ShapeResolver, StructureShape, StringShape
from botocore.model import DenormalizedStructureBuilder
from botocore.docs.bcdoc.restdoc import ReSTDocument

from awscli.testutils import unittest, FileCreator
from awscli.clidocs import OperationDocumentEventHandler, \
    CLIDocumentEventHandler, TopicListerDocumentEventHandler, \
    TopicDocumentEventHandler
from awscli.help import ServiceHelpCommand, TopicListerCommand, \
    TopicHelpCommand


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
            'arg-name', self.help_command, 'process-cli-arg.foo.bar')
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


class TestTranslationMap(unittest.TestCase):
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

    def test_boolean_arg_groups(self):
        builder = DenormalizedStructureBuilder()
        input_model = builder.with_members({
            'Flag': {'type': 'boolean'}
        }).build_model()
        argument_model = input_model.members['Flag']
        argument_model.name = 'Flag'
        self.arg_table['flag'] = mock.Mock(
            cli_type_name='boolean', argument_model=argument_model)
        self.arg_table['no-flag'] = mock.Mock(
            cli_type_name='boolean', argument_model=argument_model)
        # The --no-flag should not be used in the translation.
        self.assertEqual(
            self.operation_handler.build_translation_map(),
            {'Flag': 'flag'}
        )


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

    def test_documents_enum_values(self):
        shape = {
            'type': 'string',
            'enum': ['FOO', 'BAZ']
        }
        shape = StringShape('EnumArg', shape)
        arg_table = {'arg-name': mock.Mock(argument_model=shape)}
        help_command = mock.Mock()
        help_command.doc = ReSTDocument()
        help_command.event_class = 'custom'
        help_command.arg_table = arg_table
        operation_model = mock.Mock()
        operation_model.service_model.operation_names = []
        help_command.obj = operation_model
        operation_handler = OperationDocumentEventHandler(help_command)
        operation_handler.doc_option('arg-name', help_command)
        rendered = help_command.doc.getvalue().decode('utf-8')
        self.assertIn('Possible values', rendered)
        self.assertIn('FOO', rendered)
        self.assertIn('BAZ', rendered)


class TestTopicDocumentEventHandlerBase(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.file_creator = FileCreator()

        self.tags_dict = {}

        # Make a temporary json index to base information on
        self.json_index = self.file_creator.create_file('index.json', '')
        with open(self.json_index, 'w') as f:
            json.dump(self.tags_dict, f, indent=4, sort_keys=True)

        self.index_patch = mock.patch('awscli.topictags.TopicTagDB.index_file',
                                      self.json_index)
        self.dir_patch = mock.patch('awscli.topictags.TopicTagDB.topic_dir',
                                    self.file_creator.rootdir)
        self.index_patch.start()
        self.dir_patch.start()

    def tearDown(self):
        self.dir_patch.stop()
        self.index_patch.stop()
        self.file_creator.remove_all()


class TestTopicListerDocumentEventHandler(TestTopicDocumentEventHandlerBase):
    def setUp(self):
        super(TestTopicListerDocumentEventHandler, self).setUp()
        self.descriptions = [
            'This describes the first topic',
            'This describes the second topic',
            'This describes the third topic'
        ]
        self.tags_dict = {
            'topic-name-1': {
                'title': ['The first topic title'],
                'description': [self.descriptions[0]],
                'category': ['General']
            },
            'topic-name-2': {
                'title': ['The second topic title'],
                'description': [self.descriptions[1]],
                'category': ['S3']
            },
            'topic-name-3': {
                'title': ['The third topic title'],
                'description': [self.descriptions[2]],
                'category': ['General']
            }

        }

        with open(self.json_index, 'w') as f:
            json.dump(self.tags_dict, f, indent=4, sort_keys=True)

        self.cmd = TopicListerCommand(self.session)
        self.doc_handler = TopicListerDocumentEventHandler(self.cmd)

    def test_breadcrumbs(self):
        self.doc_handler.doc_breadcrumbs(self.cmd)
        self.assertEqual(self.cmd.doc.getvalue().decode('utf-8'), '')
        self.cmd.doc.target = 'html'
        self.doc_handler.doc_breadcrumbs(self.cmd)
        self.assertEqual(
            '[ :ref:`aws <cli:aws>` ]',
            self.cmd.doc.getvalue().decode('utf-8')
        )

    def test_title(self):
        self.doc_handler.doc_title(self.cmd)
        title_contents = self.cmd.doc.getvalue().decode('utf-8')
        self.assertIn('.. _cli:aws help %s:' % self.cmd.name, title_contents)
        self.assertIn('AWS CLI Topic Guide', title_contents)

    def test_description(self):
        self.doc_handler.doc_description(self.cmd)
        self.assertIn(
            'This is the AWS CLI Topic Guide',
            self.cmd.doc.getvalue().decode('utf-8')
        )

    def test_subitems_start(self):
        ref_output = [
            '-------\nGeneral\n-------',
            ('* topic-name-1: %s\n'
             '* topic-name-3: %s\n' %
             (self.descriptions[0], self.descriptions[2])),
            '--\nS3\n--',
            '* topic-name-2: %s\n' % self.descriptions[1]
        ]

        self.doc_handler.doc_subitems_start(self.cmd)
        contents = self.cmd.doc.getvalue().decode('utf-8')

        for line in ref_output:
            self.assertIn(line, contents)
        # Make sure the toctree is not in the man page
        self.assertNotIn('.. toctree::', contents)

    def test_subitems_start_html(self):
        self.cmd.doc.target = 'html'
        ref_output = [
            '-------\nGeneral\n-------',
            ('* :ref:`topic-name-1 <cli:aws help topic-name-1>`: %s\n'
             '* :ref:`topic-name-3 <cli:aws help topic-name-3>`: %s\n' %
             (self.descriptions[0], self.descriptions[2])),
            '--\nS3\n--',
            ('* :ref:`topic-name-2 <cli:aws help topic-name-2>`: %s\n' %
             self.descriptions[1])
        ]

        self.doc_handler.doc_subitems_start(self.cmd)
        contents = self.cmd.doc.getvalue().decode('utf-8')

        for line in ref_output:
            self.assertIn(line, contents)
        # Make sure the hidden toctree is in the html
        self.assertIn('.. toctree::', contents)
        self.assertIn(':hidden:', contents)


class TestTopicDocumentEventHandler(TestTopicDocumentEventHandlerBase):
    def setUp(self):
        super(TestTopicDocumentEventHandler, self).setUp()
        self.name = 'topic-name-1'
        self.title = 'The first topic title'
        self.description = 'This is about the first topic'
        self.category = 'General'
        self.related_command = 'foo'
        self.related_topic = 'topic-name-2'
        self.topic_body = 'Hello World!'

        self.tags_dict = {
            self.name: {
                'title': [self.title],
                'description': [self.description],
                'category': [self.category],
                'related topic': [self.related_topic],
                'related command': [self.related_command]
            }
        }
        with open(self.json_index, 'w') as f:
            json.dump(self.tags_dict, f, indent=4, sort_keys=True)

        self.cmd = TopicHelpCommand(self.session, self.name)
        self.doc_handler = TopicDocumentEventHandler(self.cmd)

    def test_breadcrumbs(self):
        self.doc_handler.doc_breadcrumbs(self.cmd)
        self.assertEqual(self.cmd.doc.getvalue().decode('utf-8'), '')
        self.cmd.doc.target = 'html'
        self.doc_handler.doc_breadcrumbs(self.cmd)
        self.assertEqual(
            '[ :ref:`aws <cli:aws>` . :ref:`topics <cli:aws help topics>` ]',
            self.cmd.doc.getvalue().decode('utf-8')
        )

    def test_title(self):
        self.doc_handler.doc_title(self.cmd)
        title_contents = self.cmd.doc.getvalue().decode('utf-8')
        self.assertIn('.. _cli:aws help %s:' % self.name, title_contents)
        self.assertIn(self.title, title_contents)

    def test_description(self):
        lines = [
            ':title: ' + self.title,
            ':description: ' + self.description,
            ':category:' + self.category,
            ':related command: ' + self.related_command,
            ':related topic: ' + self.related_topic,
            self.topic_body
        ]
        body = '\n'.join(lines)
        self.file_creator.create_file(self.name + '.rst', body)
        self.doc_handler.doc_description(self.cmd)
        contents = self.cmd.doc.getvalue().decode('utf-8')
        self.assertIn(self.topic_body, contents)
        self.assertNotIn(':title ' + self.title, contents)

    def test_description_no_tags(self):
        lines = [
            self.topic_body
        ]
        body = '\n'.join(lines)
        self.file_creator.create_file(self.name + '.rst', body)
        self.doc_handler.doc_description(self.cmd)
        contents = self.cmd.doc.getvalue().decode('utf-8')
        self.assertIn(self.topic_body, contents)

    def test_description_tags_in_body(self):
        lines = [
            ':title: ' + self.title,
            ':description: ' + self.description,
            ':related command: ' + self.related_command
        ]
        body_lines = [
            ':related_topic: ' + self.related_topic,
            self.topic_body,
            ':foo: bar'
        ]
        body = '\n'.join(lines + body_lines)
        ref_body = '\n'.join(body_lines)
        self.file_creator.create_file(self.name + '.rst', body)
        self.doc_handler.doc_description(self.cmd)
        contents = self.cmd.doc.getvalue().decode('utf-8')
        self.assertIn(ref_body, contents)
