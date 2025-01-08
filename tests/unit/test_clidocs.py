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

from botocore.model import ShapeResolver, StructureShape, StringShape, \
    ListShape, MapShape, Shape, DenormalizedStructureBuilder

from awscli.testutils import mock, unittest, FileCreator
from awscli.clidocs import OperationDocumentEventHandler, \
    CLIDocumentEventHandler, TopicListerDocumentEventHandler, \
    TopicDocumentEventHandler, GlobalOptionsDocumenter
from awscli.bcdoc.restdoc import ReSTDocument
from awscli.help import ServiceHelpCommand, TopicListerCommand, \
    TopicHelpCommand, HelpCommand
from awscli.arguments import CustomArgument


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

    def assert_proper_indentation(self):
        indent = self.help_command.doc.style.indent.call_count
        dedent = self.help_command.doc.style.dedent.call_count
        message = 'Imbalanced indentation: indent (%s) != dedent (%s)'
        self.assertEqual(indent, dedent, message % (indent, dedent))

    def test_handle_recursive_input(self):
        shape_map = {
            'RecursiveStruct': {
                'type': 'structure',
                'members': {
                    'A': {'shape': 'NonRecursive'},
                    'B': {'shape': 'RecursiveStruct'},
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
                    'B': {'shape': 'RecursiveStruct'},
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

    def test_handle_empty_nested_struct(self):
        shape_map = {
            'InputStruct': {
                'type': 'structure',
                'members': {
                    'A': {'shape': 'Empty'},
                }
            },
            'Empty': {'type': 'structure', 'members': {}}
        }
        shape = StructureShape('InputStruct', shape_map['InputStruct'],
                               ShapeResolver(shape_map))

        self.arg_table['arg-name'] = mock.Mock(argument_model=shape)
        self.operation_handler.doc_option_example(
            'arg-name', self.help_command, 'process-cli-arg.foo.bar')
        self.assert_proper_indentation()

    def test_handle_no_output_shape(self):
        operation_model = mock.Mock()
        operation_model.output_shape = None
        self.help_command.obj = operation_model
        self.operation_handler.doc_output(self.help_command, 'event-name')
        self.assert_rendered_docs_contain('None')

    def test_handle_memberless_output_shape(self):
        shape_map = {
            'NoMembers': {
                'type': 'structure',
                'members': {}
            }
        }
        shape = StructureShape('NoMembers', shape_map['NoMembers'],
                               ShapeResolver(shape_map))

        operation_model = mock.Mock()
        operation_model.output_shape = shape
        self.help_command.obj = operation_model
        self.operation_handler.doc_output(self.help_command, 'event-name')
        self.assert_rendered_docs_contain('None')


class TestCLIDocumentEventHandler(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.obj = None
        self.command_table = {}
        self.arg_table = {}
        self.name = 'my-command'
        self.event_class = 'aws'

    def create_help_command(self):
        help_command = mock.Mock()
        help_command.doc = ReSTDocument()
        help_command.event_class = 'custom'
        help_command.arg_table = {}
        operation_model = mock.Mock()
        operation_model.documentation = 'description'
        operation_model.service_model.operation_names = []
        help_command.obj = operation_model
        return help_command

    def create_tagged_union_shape(self):
        shape_model = {
            'type': 'structure',
            'union': True,
            'members': {}
        }
        tagged_union = StructureShape('tagged_union', shape_model)
        return tagged_union

    def get_help_docs_for_argument(self, shape):
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
        return help_command.doc.getvalue().decode('utf-8')

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

    def test_documents_json_header_shape(self):
        shape = {
            'type': 'string',
            'jsonvalue': True,
            'location': 'header',
            'locationName': 'X-Amz-Header-Name'
        }
        shape = StringShape('JSONValueArg', shape)
        rendered = self.get_help_docs_for_argument(shape)
        self.assertIn('(JSON)', rendered)

    def test_documents_enum_values(self):
        shape = {
            'type': 'string',
            'enum': ['FOO', 'BAZ']
        }
        shape = StringShape('EnumArg', shape)
        rendered = self.get_help_docs_for_argument(shape)
        self.assertIn('Possible values', rendered)
        self.assertIn('FOO', rendered)
        self.assertIn('BAZ', rendered)

    def test_documents_recursive_input(self):
        shape_map = {
            'RecursiveStruct': {
                'type': 'structure',
                'members': {
                    'A': {'shape': 'NonRecursive'},
                    'B': {'shape': 'RecursiveStruct'},
                }
            },
            'NonRecursive': {'type': 'string'}
        }
        shape = StructureShape('RecursiveStruct',
                               shape_map['RecursiveStruct'],
                               ShapeResolver(shape_map))
        rendered = self.get_help_docs_for_argument(shape)
        self.assertIn('( ... recursive ... )', rendered)

    def test_documents_nested_structure(self):
        shape_map = {
            'UpperStructure': {
                'type': 'structure',
                'members': {
                    'A': {'shape': 'NestedStruct'},
                    'B': {'shape': 'NestedStruct'},
                }
            },
            'NestedStruct': {
                'type': 'structure',
                'members': {
                    'Nested_A': {'shape': 'Line'},
                    'Nested_B': {'shape': 'Line'},
                }
            },
            'Line': {'type': 'string'}
        }
        shape = StructureShape('UpperStructure',
                               shape_map['UpperStructure'],
                               ShapeResolver(shape_map))
        rendered = self.get_help_docs_for_argument(shape)
        self.assertEqual(rendered.count('A -> (structure)'), 1)
        self.assertEqual(rendered.count('B -> (structure)'), 1)
        self.assertEqual(rendered.count('Nested_A -> (string)'), 2)
        self.assertEqual(rendered.count('Nested_B -> (string)'), 2)

    def test_documents_nested_list(self):
        shape_map = {
            'UpperList': {
                'type': 'list',
                'member': {'shape': 'NestedStruct'},
            },
            'NestedStruct': {
                'type': 'structure',
                'members': {
                    'Nested_A': {'shape': 'Line'},
                    'Nested_B': {'shape': 'Line'},
                }
            },
            'Line': {'type': 'string'}
        }
        shape = ListShape('UpperList', shape_map['UpperList'],
                          ShapeResolver(shape_map))
        rendered = self.get_help_docs_for_argument(shape)
        self.assertEqual(rendered.count('(structure)'), 1)
        self.assertEqual(rendered.count('Nested_A -> (string)'), 1)
        self.assertEqual(rendered.count('Nested_B -> (string)'), 1)

    def test_documents_nested_map(self):
        shape_map = {
            'UpperMap': {
                'type': 'map',
                'key': {'shape': 'NestedStruct'},
                'value': {'shape': 'NestedStruct'},
            },
            'NestedStruct': {
                'type': 'structure',
                'members': {
                    'Nested_A': {'shape': 'Line'},
                    'Nested_B': {'shape': 'Line'},
                }
            },
            'Line': {'type': 'string'}
        }
        shape = MapShape('UpperMap', shape_map['UpperMap'],
                         ShapeResolver(shape_map))
        rendered = self.get_help_docs_for_argument(shape)
        self.assertEqual(rendered.count('key -> (structure)'), 1)
        self.assertEqual(rendered.count('value -> (structure)'), 1)
        self.assertEqual(rendered.count('Nested_A -> (string)'), 2)
        self.assertEqual(rendered.count('Nested_B -> (string)'), 2)

    def test_description_only_for_crosslink_manpage(self):
        help_command = self.create_help_command()
        operation_handler = OperationDocumentEventHandler(help_command)
        operation_handler.doc_description(help_command=help_command)
        rendered = help_command.doc.getvalue().decode('utf-8')
        # The links are generated in the "man" mode.
        self.assertIn('See also: AWS API Documentation', rendered)

    def test_includes_webapi_crosslink_in_html(self):
        help_command = self.create_help_command()
        # Configure this for 'html' generation:
        help_command.obj.service_model.metadata = {'uid': 'service-1-2-3'}
        help_command.obj.name = 'myoperation'
        help_command.doc.target = 'html'

        operation_handler = OperationDocumentEventHandler(help_command)
        operation_handler.doc_description(help_command=help_command)
        rendered = help_command.doc.getvalue().decode('utf-8')
        # Should expect an externa link because we're generating html.
        self.assertIn(
            'See also: `AWS API Documentation '
            '<https://docs.aws.amazon.com/goto/'
            'WebAPI/service-1-2-3/myoperation>`_', rendered)

    def test_includes_streaming_blob_options(self):
        help_command = self.create_help_command()
        blob_shape = Shape('blob_shape', {'type': 'blob'})
        blob_shape.serialization = {'streaming': True}
        blob_arg = CustomArgument('blob_arg', argument_model=blob_shape)
        help_command.arg_table = {'blob_arg': blob_arg}
        operation_handler = OperationDocumentEventHandler(help_command)
        operation_handler.doc_option(arg_name='blob_arg',
                                     help_command=help_command)
        rendered = help_command.doc.getvalue().decode('utf-8')
        self.assertIn('streaming blob', rendered)

    def test_streaming_blob_comes_after_docstring(self):
        help_command = self.create_help_command()
        blob_shape = Shape('blob_shape', {'type': 'blob'})
        blob_shape.serialization = {'streaming': True}
        blob_arg = CustomArgument(name='blob_arg',
                                  argument_model=blob_shape,
                                  help_text='FooBar')
        help_command.arg_table = {'blob_arg': blob_arg}
        operation_handler = OperationDocumentEventHandler(help_command)
        operation_handler.doc_option(arg_name='blob_arg',
                                     help_command=help_command)
        rendered = help_command.doc.getvalue().decode('utf-8')
        self.assertRegex(rendered, r'FooBar[\s\S]*streaming blob')

    def test_includes_tagged_union_options(self):
        help_command = self.create_help_command()
        tagged_union = self.create_tagged_union_shape()
        arg = CustomArgument(name='tagged_union',
                             argument_model=tagged_union)
        help_command.arg_table = {'tagged_union': arg}
        operation_handler = OperationDocumentEventHandler(help_command)
        operation_handler.doc_option(arg_name='tagged_union',
                                     help_command=help_command)
        rendered = help_command.doc.getvalue().decode('utf-8')
        self.assertIn('(tagged union structure)', rendered)

    def test_tagged_union_comes_after_docstring_options(self):
        help_command = self.create_help_command()
        tagged_union = self.create_tagged_union_shape()
        arg = CustomArgument(name='tagged_union',
                             argument_model=tagged_union,
                             help_text='FooBar')
        help_command.arg_table = {'tagged_union': arg}
        operation_handler = OperationDocumentEventHandler(help_command)
        operation_handler.doc_option(arg_name='tagged_union',
                                     help_command=help_command)
        rendered = help_command.doc.getvalue().decode('utf-8')
        self.assertRegex(rendered, r'FooBar[\s\S]*Tagged Union')

    def test_tagged_union_comes_after_docstring_output(self):
        help_command = self.create_help_command()
        tagged_union = self.create_tagged_union_shape()
        tagged_union.documentation = "FooBar"
        shape = DenormalizedStructureBuilder().with_members({
            'foo': {
                'type': 'structure',
                'union': True,
                'documentation': 'FooBar',
                'members': {}
            }
        }).build_model()
        help_command.obj.output_shape = shape
        operation_handler = OperationDocumentEventHandler(help_command)
        operation_handler.doc_output(help_command=help_command,
                                     event_name='foobar')
        rendered = help_command.doc.getvalue().decode('utf-8')
        self.assertRegex(rendered, r'FooBar[\s\S]*Tagged Union')


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

    def test_excludes_global_options(self):
        self.doc_handler.doc_global_option(self.cmd)
        global_options = self.cmd.doc.getvalue().decode('utf-8')
        self.assertNotIn('Global Options', global_options)


class TestGlobalOptionsDocumenter(unittest.TestCase):
    def create_help_command(self):
        types = ['blob', 'integer', 'boolean', 'string']
        arg_table = {}
        for t in types:
            name = f'{t}_type'
            help_text = f'This arg type is {t}'
            choices = ['A', 'B', 'C'] if t == 'string' else []
            arg_table[name] = CustomArgument(name=name,
                                             cli_type_name=t,
                                             help_text=help_text,
                                             choices=choices)
        help_command = mock.Mock(spec=HelpCommand)
        help_command.arg_table = arg_table
        help_command.doc = ReSTDocument()
        return help_command

    def create_documenter(self):
        return GlobalOptionsDocumenter(self.create_help_command())

    def test_doc_global_options(self):
        documenter = self.create_documenter()
        options = documenter.doc_global_options()
        self.assertIn('``--string_type`` (string)', options)
        self.assertIn('``--integer_type`` (integer)', options)
        self.assertIn('``--boolean_type`` (boolean)', options)
        self.assertIn('``--blob_type`` (blob)', options)
        self.assertIn('*   A', options)
        self.assertIn('*   B', options)
        self.assertIn('*   C', options)

    def test_doc_global_synopsis(self):
        documenter = self.create_documenter()
        synopsis = documenter.doc_global_synopsis()
        self.assertIn('[--string_type <value>]', synopsis)
        self.assertIn('[--integer_type <value>]', synopsis)
        self.assertIn('[--boolean_type]', synopsis)
        self.assertIn('[--blob_type <value>]', synopsis)
