# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from botocore.docs.example import (
    RequestExampleDocumenter,
    ResponseExampleDocumenter,
)
from botocore.docs.utils import DocumentedShape
from botocore.hooks import HierarchicalEmitter
from tests import mock
from tests.unit.docs import BaseDocsTest


class BaseExampleDocumenterTest(BaseDocsTest):
    def setUp(self):
        super().setUp()
        self.event_emitter = HierarchicalEmitter()
        self.request_example = RequestExampleDocumenter(
            service_name='myservice',
            operation_name='SampleOperation',
            event_emitter=self.event_emitter,
        )
        self.response_example = ResponseExampleDocumenter(
            service_name='myservice',
            operation_name='SampleOperation',
            event_emitter=self.event_emitter,
        )


class TestDocumentDefaultValue(BaseExampleDocumenterTest):
    def setUp(self):
        super().setUp()
        self.add_shape_to_params('Foo', 'String', 'This describes foo.')

    def test_request_example(self):
        self.request_example.document_example(
            self.doc_structure,
            self.operation_model.input_shape,
            prefix='response = myclient.call',
        )
        self.assert_contains_lines_in_order(
            [
                '::',
                '  response = myclient.call(',
                '      Foo=\'string\'',
                '  )',
            ]
        )

    def test_response_example(self):
        self.response_example.document_example(
            self.doc_structure,
            self.operation_model.input_shape,
        )
        self.assert_contains_lines_in_order(
            ['::', '  {', '      \'Foo\': \'string\'', '  }']
        )


class TestDocumentNoMembers(BaseExampleDocumenterTest):
    def setUp(self):
        super().setUp()

    def test_request_example(self):
        self.request_example.document_example(
            self.doc_structure,
            self.operation_model.input_shape,
            prefix='response = myclient.call',
        )
        self.assert_contains_lines_in_order(
            ['::', '  response = myclient.call()']
        )

    def test_response_example(self):
        self.response_example.document_example(
            self.doc_structure,
            self.operation_model.input_shape,
        )
        self.assert_contains_lines_in_order(['::', '  {}'])


class TestTraverseAndDocumentShape(BaseExampleDocumenterTest):
    def setUp(self):
        super().setUp()
        self.add_shape_to_params('Foo', 'String', 'This describes foo.')
        self.event_emitter = mock.Mock()
        self.request_example = RequestExampleDocumenter(
            service_name='myservice',
            operation_name='SampleOperation',
            event_emitter=self.event_emitter,
        )
        self.response_example = ResponseExampleDocumenter(
            service_name='myservice',
            operation_name='SampleOperation',
            event_emitter=self.event_emitter,
        )

    def test_events_emitted_response_example(self):
        self.response_example.traverse_and_document_shape(
            section=self.doc_structure,
            shape=self.operation_model.input_shape,
            history=[],
        )
        structure_section = self.doc_structure.get_section('structure-value')
        print(self.event_emitter.emit.call_args_list[0][1]['section'].name)
        self.assertEqual(
            self.event_emitter.emit.call_args_list,
            [
                mock.call(
                    'docs.response-example.myservice.SampleOperation.Foo',
                    section=structure_section.get_section('Foo').get_section(
                        'member-value'
                    ),
                ),
                mock.call(
                    (
                        'docs.response-example.myservice.SampleOperation'
                        '.complete-section'
                    ),
                    section=self.doc_structure,
                ),
            ],
        )

    def test_events_emitted_request_example(self):
        self.request_example.traverse_and_document_shape(
            section=self.doc_structure,
            shape=self.operation_model.input_shape,
            history=[],
        )
        structure_section = self.doc_structure.get_section('structure-value')
        self.assertEqual(
            self.event_emitter.emit.call_args_list,
            [
                mock.call(
                    'docs.request-example.myservice.SampleOperation.Foo',
                    section=structure_section.get_section('Foo').get_section(
                        'member-value'
                    ),
                ),
                mock.call(
                    (
                        'docs.request-example.myservice.SampleOperation'
                        '.complete-section'
                    ),
                    section=self.doc_structure,
                ),
            ],
        )


class TestDocumentEnumValue(BaseExampleDocumenterTest):
    def setUp(self):
        super().setUp()
        self.add_shape(
            {'EnumString': {'type': 'string', 'enum': ['foo', 'bar']}}
        )
        self.add_shape_to_params('Foo', 'EnumString', 'This describes foo.')

    def test_request_example(self):
        self.request_example.document_example(
            self.doc_structure,
            self.operation_model.input_shape,
            prefix='response = myclient.call',
        )
        self.assert_contains_lines_in_order(
            [
                '::',
                '  response = myclient.call(',
                '      Foo=\'foo\'|\'bar\'',
                '  )',
            ]
        )

    def test_response_example(self):
        self.response_example.document_example(
            self.doc_structure,
            self.operation_model.input_shape,
        )
        self.assert_contains_lines_in_order(
            ['::', '  {', '      \'Foo\': \'foo\'|\'bar\'', '  }']
        )


class TestDocumentMultipleDefaultValues(BaseExampleDocumenterTest):
    def setUp(self):
        super().setUp()
        self.add_shape_to_params('Foo', 'String', 'This describes foo.')
        self.add_shape_to_params(
            'Bar', 'String', 'This describes bar.', is_required=True
        )

    def test_request_example(self):
        self.request_example.document_example(
            self.doc_structure,
            self.operation_model.input_shape,
            prefix='response = myclient.call',
        )
        self.assert_contains_lines_in_order(
            [
                '::',
                '  response = myclient.call(',
                '      Foo=\'string\',',
                '      Bar=\'string\'',
                '  )',
            ]
        )

    def test_response_example(self):
        self.response_example.document_example(
            self.doc_structure,
            self.operation_model.input_shape,
        )
        self.assert_contains_lines_in_order(
            [
                '::',
                '  {',
                '      \'Foo\': \'string\',',
                '      \'Bar\': \'string\'',
                '  }',
            ]
        )


class TestDocumentInclude(BaseExampleDocumenterTest):
    def setUp(self):
        super().setUp()
        self.add_shape_to_params('Foo', 'String', 'This describes foo.')
        self.include_params = [
            DocumentedShape(
                name='Baz',
                type_name='integer',
                documentation='This describes baz.',
            )
        ]

    def test_request_example(self):
        self.request_example.document_example(
            self.doc_structure,
            self.operation_model.input_shape,
            prefix='response = myclient.call',
            include=self.include_params,
        )
        self.assert_contains_lines_in_order(
            [
                '::',
                '  response = myclient.call(',
                '      Foo=\'string\',',
                '      Baz=123',
                '  )',
            ]
        )

    def test_response_example(self):
        self.response_example.document_example(
            self.doc_structure,
            self.operation_model.input_shape,
            include=self.include_params,
        )
        self.assert_contains_lines_in_order(
            [
                '::',
                '  {',
                '      \'Foo\': \'string\',',
                '      \'Baz\': 123',
                '  }',
            ]
        )


class TestDocumentExclude(BaseExampleDocumenterTest):
    def setUp(self):
        super().setUp()
        self.add_shape_to_params('Foo', 'String', 'This describes foo.')
        self.add_shape_to_params(
            'Bar', 'String', 'This describes bar.', is_required=True
        )
        self.exclude_params = ['Foo']

    def test_request_example(self):
        self.request_example.document_example(
            self.doc_structure,
            self.operation_model.input_shape,
            prefix='response = myclient.call',
            exclude=self.exclude_params,
        )
        self.assert_contains_lines_in_order(
            [
                '::',
                '  response = myclient.call(',
                '      Bar=\'string\'',
                '  )',
            ]
        )
        self.assert_not_contains_line('      Foo=\'string\'')

    def test_response_example(self):
        self.response_example.document_example(
            self.doc_structure,
            self.operation_model.input_shape,
            exclude=self.exclude_params,
        )
        self.assert_contains_lines_in_order(
            ['::', '  {', '      \'Bar\': \'string\'', '  }']
        )
        self.assert_not_contains_line('\'Foo\': \'string\',')


class TestDocumentList(BaseExampleDocumenterTest):
    def setUp(self):
        super().setUp()
        self.add_shape(
            {
                'List': {
                    'type': 'list',
                    'member': {
                        'shape': 'String',
                        'documentation': 'A string element',
                    },
                }
            }
        )
        self.add_shape_to_params('Foo', 'List', 'This describes the list.')

    def test_request_example(self):
        self.request_example.document_example(
            self.doc_structure,
            self.operation_model.input_shape,
            prefix='response = myclient.call',
        )
        self.assert_contains_lines_in_order(
            [
                '::',
                '  response = myclient.call(',
                '      Foo=[',
                '          \'string\',',
                '      ]',
                '  )',
            ]
        )

    def test_response_example(self):
        self.response_example.document_example(
            self.doc_structure, self.operation_model.input_shape
        )
        self.assert_contains_lines_in_order(
            [
                '::',
                '  {',
                '      \'Foo\': [',
                '          \'string\',',
                '      ]',
                '  }',
            ]
        )


class TestDocumentMap(BaseExampleDocumenterTest):
    def setUp(self):
        super().setUp()
        self.add_shape(
            {
                'Map': {
                    'type': 'map',
                    'key': {'shape': 'String'},
                    'value': {'shape': 'String'},
                }
            }
        )
        self.add_shape_to_params('Foo', 'Map', 'This describes the map.')

    def test_request_example(self):
        self.request_example.document_example(
            self.doc_structure,
            self.operation_model.input_shape,
            prefix='response = myclient.call',
        )
        self.assert_contains_lines_in_order(
            [
                '::',
                '  response = myclient.call(',
                '      Foo={',
                '          \'string\': \'string\'',
                '      }',
                '  )',
            ]
        )

    def test_response_example(self):
        self.response_example.document_example(
            self.doc_structure, self.operation_model.input_shape
        )
        self.assert_contains_lines_in_order(
            [
                '::',
                '  {',
                '      \'Foo\': {',
                '          \'string\': \'string\'',
                '      }',
                '  }',
            ]
        )


class TestDocumentStructure(BaseExampleDocumenterTest):
    def setUp(self):
        super().setUp()
        self.add_shape(
            {
                'Structure': {
                    'type': 'structure',
                    'members': {
                        'Member': {
                            'shape': 'String',
                            'documentation': 'This is its member.',
                        }
                    },
                }
            }
        )
        self.add_shape_to_params(
            'Foo', 'Structure', 'This describes the structure.'
        )

    def test_request_example(self):
        self.request_example.document_example(
            self.doc_structure,
            self.operation_model.input_shape,
            prefix='response = myclient.call',
        )
        self.assert_contains_lines_in_order(
            [
                '::',
                '  response = myclient.call(',
                '      Foo={',
                '          \'Member\': \'string\'',
                '      }',
                '  )',
            ]
        )

    def test_response_example(self):
        self.response_example.document_example(
            self.doc_structure, self.operation_model.input_shape
        )
        self.assert_contains_lines_in_order(
            [
                '::',
                '  {',
                '      \'Foo\': {',
                '          \'Member\': \'string\'',
                '      }',
                '  }',
            ]
        )


class TestDocumentRecursiveShape(BaseExampleDocumenterTest):
    def setUp(self):
        super().setUp()
        self.add_shape(
            {
                'Structure': {
                    'type': 'structure',
                    'members': {
                        'Foo': {
                            'shape': 'Structure',
                            'documentation': 'This is a recursive structure.',
                        }
                    },
                }
            }
        )
        self.add_shape_to_params(
            'Foo', 'Structure', 'This describes the structure.'
        )

    def test_request_example(self):
        self.request_example.document_example(
            self.doc_structure,
            self.operation_model.input_shape,
            prefix='response = myclient.call',
        )
        self.assert_contains_lines_in_order(
            [
                '::',
                '  response = myclient.call(',
                '      Foo={',
                '          \'Foo\': {\'... recursive ...\'}',
                '      }',
                '  )',
            ]
        )

    def test_response_example(self):
        self.response_example.document_example(
            self.doc_structure, self.operation_model.input_shape
        )
        self.assert_contains_lines_in_order(
            [
                '::',
                '  {',
                '      \'Foo\': {',
                '          \'Foo\': {\'... recursive ...\'}',
                '      }',
                '  }',
            ]
        )
