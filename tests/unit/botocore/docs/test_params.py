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
from botocore.docs.params import (
    RequestParamsDocumenter,
    ResponseParamsDocumenter,
)
from botocore.docs.utils import DocumentedShape
from botocore.hooks import HierarchicalEmitter
from tests import mock
from tests.unit.docs import BaseDocsTest


class BaseParamsDocumenterTest(BaseDocsTest):
    def setUp(self):
        super().setUp()
        self.event_emitter = HierarchicalEmitter()
        self.request_params = RequestParamsDocumenter(
            service_name='myservice',
            operation_name='SampleOperation',
            event_emitter=self.event_emitter,
        )
        self.response_params = ResponseParamsDocumenter(
            service_name='myservice',
            operation_name='SampleOperation',
            event_emitter=self.event_emitter,
        )


class TestDocumentDefaultValue(BaseParamsDocumenterTest):
    def setUp(self):
        super().setUp()
        self.add_shape_to_params('Foo', 'String', 'This describes foo.')

    def test_request_params(self):
        self.request_params.document_params(
            self.doc_structure, self.operation_model.input_shape
        )
        self.assert_contains_lines_in_order(
            [':type Foo: string', ':param Foo: This describes foo.']
        )

    def test_response_params(self):
        self.response_params.document_params(
            self.doc_structure, self.operation_model.input_shape
        )
        self.assert_contains_lines_in_order(
            ['- *(dict) --*', '  - **Foo** *(string) --* This describes foo.']
        )


class TestTraverseAndDocumentShape(BaseParamsDocumenterTest):
    def setUp(self):
        super().setUp()
        self.add_shape_to_params('Foo', 'String', 'This describes foo.')
        self.event_emitter = mock.Mock()
        self.request_params = RequestParamsDocumenter(
            service_name='myservice',
            operation_name='SampleOperation',
            event_emitter=self.event_emitter,
        )
        self.response_params = ResponseParamsDocumenter(
            service_name='myservice',
            operation_name='SampleOperation',
            event_emitter=self.event_emitter,
        )

    def test_events_emitted_response_params(self):
        self.response_params.traverse_and_document_shape(
            section=self.doc_structure,
            shape=self.operation_model.input_shape,
            history=[],
        )
        self.assertEqual(
            self.event_emitter.emit.call_args_list,
            [
                mock.call(
                    'docs.response-params.myservice.SampleOperation.Foo',
                    section=self.doc_structure.get_section('Foo'),
                ),
                mock.call(
                    (
                        'docs.response-params.myservice.SampleOperation'
                        '.complete-section'
                    ),
                    section=self.doc_structure,
                ),
            ],
        )

    def test_events_emitted_request_params(self):
        self.request_params.traverse_and_document_shape(
            section=self.doc_structure,
            shape=self.operation_model.input_shape,
            history=[],
        )
        self.assertEqual(
            self.event_emitter.emit.call_args_list,
            [
                mock.call(
                    'docs.request-params.myservice.SampleOperation.Foo',
                    section=self.doc_structure.get_section('Foo'),
                ),
                mock.call(
                    (
                        'docs.request-params.myservice.SampleOperation'
                        '.complete-section'
                    ),
                    section=self.doc_structure,
                ),
            ],
        )


class TestDocumentMultipleDefaultValues(BaseParamsDocumenterTest):
    def setUp(self):
        super().setUp()
        self.add_shape_to_params('Foo', 'String', 'This describes foo.')
        self.add_shape_to_params(
            'Bar', 'String', 'This describes bar.', is_required=True
        )

    def test_request_params(self):
        self.request_params.document_params(
            self.doc_structure, self.operation_model.input_shape
        )
        self.assert_contains_lines_in_order(
            [
                ':type Foo: string',
                ':param Foo: This describes foo.',
                ':type Bar: string',
                ':param Bar: **[REQUIRED]** This describes bar.',
            ]
        )

    def test_response_params(self):
        self.response_params.document_params(
            self.doc_structure, self.operation_model.input_shape
        )
        self.assert_contains_lines_in_order(
            [
                '- *(dict) --*',
                '  - **Foo** *(string) --* This describes foo.',
                '  - **Bar** *(string) --* This describes bar.',
            ]
        )


class TestDocumentInclude(BaseParamsDocumenterTest):
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

    def test_request_params(self):
        self.request_params.document_params(
            self.doc_structure,
            self.operation_model.input_shape,
            include=self.include_params,
        )
        self.assert_contains_lines_in_order(
            [
                ':type Foo: string',
                ':param Foo: This describes foo.',
                ':type Baz: int',
                ':param Baz: This describes baz.',
            ]
        )

    def test_response_params(self):
        self.response_params.document_params(
            self.doc_structure,
            self.operation_model.input_shape,
            include=self.include_params,
        )
        self.assert_contains_lines_in_order(
            [
                '- *(dict) --*',
                '  - **Foo** *(string) --* This describes foo.',
                '  - **Baz** *(integer) --* This describes baz.',
            ]
        )


class TestDocumentExclude(BaseParamsDocumenterTest):
    def setUp(self):
        super().setUp()
        self.add_shape_to_params('Foo', 'String', 'This describes foo.')
        self.add_shape_to_params(
            'Bar', 'String', 'This describes bar.', is_required=True
        )
        self.exclude_params = ['Foo']

    def test_request_params(self):
        self.request_params.document_params(
            self.doc_structure,
            self.operation_model.input_shape,
            exclude=self.exclude_params,
        )
        self.assert_contains_lines_in_order(
            [
                ':type Bar: string',
                ':param Bar: **[REQUIRED]** This describes bar.',
            ]
        )
        self.assert_not_contains_lines(
            [':type Foo: string', ':param Foo: This describes foo.']
        )

    def test_response_params(self):
        self.response_params.document_params(
            self.doc_structure,
            self.operation_model.input_shape,
            exclude=self.exclude_params,
        )
        self.assert_contains_lines_in_order(
            ['- *(dict) --*', '  - **Bar** *(string) --* This describes bar.']
        )
        self.assert_not_contains_line(
            '  - **Foo** *(string) --* This describes foo.'
        )


class TestDocumentList(BaseParamsDocumenterTest):
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
        self.add_shape_to_params(
            'Foo',
            'List',
            'This describes the list. Each element of this list is a string.',
        )

    def test_request_params(self):
        self.request_params.document_params(
            self.doc_structure, self.operation_model.input_shape
        )
        self.assert_contains_lines_in_order(
            [
                ':type Foo: list',
                ':param Foo: This describes the list.',
                '  - *(string) --* A string element',
            ]
        )

    def test_response_params(self):
        self.response_params.document_params(
            self.doc_structure, self.operation_model.input_shape
        )
        self.assert_contains_lines_in_order(
            [
                '- *(dict) --*',
                (
                    '  - **Foo** *(list) --* This describes the list. '
                    'Each element of this list is a string.'
                ),
                '    - *(string) --* A string element',
            ]
        )


class TestDocumentMap(BaseParamsDocumenterTest):
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

    def test_request_params(self):
        self.request_params.document_params(
            self.doc_structure, self.operation_model.input_shape
        )
        self.assert_contains_lines_in_order(
            [
                ':type Foo: dict',
                ':param Foo: This describes the map.',
                '  - *(string) --*',
                '    - *(string) --*',
            ]
        )

    def test_response_params(self):
        self.response_params.document_params(
            self.doc_structure, self.operation_model.input_shape
        )
        self.assert_contains_lines_in_order(
            [
                '- *(dict) --*',
                '  - **Foo** *(dict) --* This describes the map.',
                '    - *(string) --*',
                '      - *(string) --*',
            ]
        )


class TestDocumentStructure(BaseParamsDocumenterTest):
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

    def test_request_params(self):
        self.request_params.document_params(
            self.doc_structure, self.operation_model.input_shape
        )
        self.assert_contains_lines_in_order(
            [
                ':type Foo: dict',
                ':param Foo: This describes the structure.',
                '  - **Member** *(string) --* This is its member.',
            ]
        )

    def test_response_params(self):
        self.response_params.document_params(
            self.doc_structure, self.operation_model.input_shape
        )
        self.assert_contains_lines_in_order(
            [
                '- *(dict) --*',
                '  - **Foo** *(dict) --* This describes the structure.',
                '    - **Member** *(string) --* This is its member.',
            ]
        )


class TestDocumentRecursiveShape(BaseParamsDocumenterTest):
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

    def test_request_params(self):
        self.request_params.document_params(
            self.doc_structure, self.operation_model.input_shape
        )
        self.assert_contains_lines_in_order(
            [
                ':type Foo: dict',
                ':param Foo: This describes the structure.',
                '  - **Foo** *(dict) --* This is a recursive structure.',
            ]
        )

    def test_response_params(self):
        self.response_params.document_params(
            self.doc_structure, self.operation_model.input_shape
        )
        self.assert_contains_lines_in_order(
            [
                '- *(dict) --*',
                '  - **Foo** *(dict) --* This is a recursive structure.',
            ]
        )
