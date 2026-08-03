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
from botocore.docs.method import (
    document_custom_method,
    document_custom_signature,
    document_model_driven_method,
    document_model_driven_signature,
    get_instance_public_methods,
)
from botocore.docs.utils import DocumentedShape
from botocore.hooks import HierarchicalEmitter
from tests import unittest
from tests.unit.docs import BaseDocsTest


class TestGetInstanceMethods(unittest.TestCase):
    class MySampleClass:
        def _internal_method(self):
            pass

        def public_method(self):
            pass

    def test_get_instance_methods(self):
        instance = self.MySampleClass()
        instance_methods = get_instance_public_methods(instance)
        self.assertEqual(len(instance_methods), 1)
        self.assertIn('public_method', instance_methods)
        self.assertEqual(
            instance.public_method, instance_methods['public_method']
        )


class TestDocumentModelDrivenSignature(BaseDocsTest):
    def setUp(self):
        super().setUp()
        self.add_shape_to_params('Foo', 'String')
        self.add_shape_to_params('Bar', 'String', is_required=True)
        self.add_shape_to_params('Baz', 'String')

    def test_document_signature(self):
        document_model_driven_signature(
            self.doc_structure, 'my_method', self.operation_model
        )
        self.assert_contains_line('.. py:method:: my_method(**kwargs)')

    def test_document_signature_exclude_all_kwargs(self):
        exclude_params = ['Foo', 'Bar', 'Baz']
        document_model_driven_signature(
            self.doc_structure,
            'my_method',
            self.operation_model,
            exclude=exclude_params,
        )
        self.assert_contains_line('.. py:method:: my_method()')

    def test_document_signature_exclude_and_include(self):
        exclude_params = ['Foo', 'Bar', 'Baz']
        include_params = [
            DocumentedShape(
                name='Biz', type_name='integer', documentation='biz docs'
            )
        ]
        document_model_driven_signature(
            self.doc_structure,
            'my_method',
            self.operation_model,
            include=include_params,
            exclude=exclude_params,
        )
        self.assert_contains_line('.. py:method:: my_method(**kwargs)')


class TestDocumentCustomSignature(BaseDocsTest):
    def sample_method(self, foo, bar='bar', baz=None):
        pass

    def test_document_signature(self):
        document_custom_signature(
            self.doc_structure, 'my_method', self.sample_method
        )
        self.assert_contains_line(
            '.. py:method:: my_method(foo, bar=\'bar\', baz=None)'
        )


class TestDocumentCustomMethod(BaseDocsTest):
    def custom_method(self, foo):
        """This is a custom method

        :type foo: string
        :param foo: The foo parameter
        """
        pass

    def test_document_custom_signature(self):
        document_custom_method(
            self.doc_structure, 'my_method', self.custom_method
        )
        self.assert_contains_lines_in_order(
            [
                '.. py:method:: my_method(foo)',
                '  This is a custom method',
                '  :type foo: string',
                '  :param foo: The foo parameter',
            ]
        )


class TestDocumentModelDrivenMethod(BaseDocsTest):
    def setUp(self):
        super().setUp()
        self.event_emitter = HierarchicalEmitter()
        self.add_shape_to_params('Bar', 'String')

    def test_default(self):
        document_model_driven_method(
            self.doc_structure,
            'foo',
            self.operation_model,
            event_emitter=self.event_emitter,
            method_description='This describes the foo method.',
            example_prefix='response = client.foo',
        )
        cross_ref_link = (
            'See also: `AWS API Documentation '
            '<https://docs.aws.amazon.com/goto/WebAPI'
            '/myservice-2014-01-01/SampleOperation>'
        )
        self.assert_contains_lines_in_order(
            [
                '.. py:method:: foo(**kwargs)',
                '  This describes the foo method.',
                cross_ref_link,
                '  **Request Syntax**',
                '  ::',
                '    response = client.foo(',
                '        Bar=\'string\'',
                '    )',
                '  :type Bar: string',
                '  :param Bar:',
                '  :rtype: dict',
                '  :returns:',
                '    **Response Syntax**',
                '    ::',
                '      {',
                '          \'Bar\': \'string\'',
                '      }',
                '    **Response Structure**',
                '    - *(dict) --*',
                '      - **Bar** *(string) --*',
            ]
        )

    def test_no_input_output_shape(self):
        del self.json_model['operations']['SampleOperation']['input']
        del self.json_model['operations']['SampleOperation']['output']
        document_model_driven_method(
            self.doc_structure,
            'foo',
            self.operation_model,
            event_emitter=self.event_emitter,
            method_description='This describes the foo method.',
            example_prefix='response = client.foo',
        )
        self.assert_contains_lines_in_order(
            [
                '.. py:method:: foo()',
                '  This describes the foo method.',
                '  **Request Syntax**',
                '  ::',
                '    response = client.foo()',
                '  :returns: None',
            ]
        )

    def test_include_input(self):
        include_params = [
            DocumentedShape(
                name='Biz', type_name='string', documentation='biz docs'
            )
        ]
        document_model_driven_method(
            self.doc_structure,
            'foo',
            self.operation_model,
            event_emitter=self.event_emitter,
            method_description='This describes the foo method.',
            example_prefix='response = client.foo',
            include_input=include_params,
        )
        self.assert_contains_lines_in_order(
            [
                '.. py:method:: foo(**kwargs)',
                '  This describes the foo method.',
                '  **Request Syntax**',
                '  ::',
                '    response = client.foo(',
                '        Bar=\'string\',',
                '        Biz=\'string\'',
                '    )',
                '  :type Bar: string',
                '  :param Bar:',
                '  :type Biz: string',
                '  :param Biz: biz docs',
                '  :rtype: dict',
                '  :returns:',
                '    **Response Syntax**',
                '    ::',
                '      {',
                '          \'Bar\': \'string\'',
                '      }',
                '    **Response Structure**',
                '    - *(dict) --*',
                '      - **Bar** *(string) --*',
            ]
        )

    def test_include_output(self):
        include_params = [
            DocumentedShape(
                name='Biz', type_name='string', documentation='biz docs'
            )
        ]
        document_model_driven_method(
            self.doc_structure,
            'foo',
            self.operation_model,
            event_emitter=self.event_emitter,
            method_description='This describes the foo method.',
            example_prefix='response = client.foo',
            include_output=include_params,
        )
        self.assert_contains_lines_in_order(
            [
                '.. py:method:: foo(**kwargs)',
                '  This describes the foo method.',
                '  **Request Syntax**',
                '  ::',
                '    response = client.foo(',
                '        Bar=\'string\'',
                '    )',
                '  :type Bar: string',
                '  :param Bar:',
                '  :rtype: dict',
                '  :returns:',
                '    **Response Syntax**',
                '    ::',
                '      {',
                '          \'Bar\': \'string\'',
                '          \'Biz\': \'string\'',
                '      }',
                '    **Response Structure**',
                '    - *(dict) --*',
                '      - **Bar** *(string) --*',
                '      - **Biz** *(string) --*',
            ]
        )

    def test_exclude_input(self):
        self.add_shape_to_params('Biz', 'String')
        document_model_driven_method(
            self.doc_structure,
            'foo',
            self.operation_model,
            event_emitter=self.event_emitter,
            method_description='This describes the foo method.',
            example_prefix='response = client.foo',
            exclude_input=['Bar'],
        )
        self.assert_contains_lines_in_order(
            [
                '.. py:method:: foo(**kwargs)',
                '  This describes the foo method.',
                '  **Request Syntax**',
                '  ::',
                '    response = client.foo(',
                '        Biz=\'string\'',
                '    )',
                '  :type Biz: string',
                '  :param Biz:',
                '  :rtype: dict',
                '  :returns:',
                '    **Response Syntax**',
                '    ::',
                '      {',
                '          \'Bar\': \'string\'',
                '          \'Biz\': \'string\'',
                '      }',
                '    **Response Structure**',
                '    - *(dict) --*',
                '      - **Bar** *(string) --*',
                '      - **Biz** *(string) --*',
            ]
        )
        self.assert_not_contains_lines(
            [':param Bar: string', 'Bar=\'string\'']
        )

    def test_exclude_output(self):
        self.add_shape_to_params('Biz', 'String')
        document_model_driven_method(
            self.doc_structure,
            'foo',
            self.operation_model,
            event_emitter=self.event_emitter,
            method_description='This describes the foo method.',
            example_prefix='response = client.foo',
            exclude_output=['Bar'],
        )
        self.assert_contains_lines_in_order(
            [
                '.. py:method:: foo(**kwargs)',
                '  This describes the foo method.',
                '  **Request Syntax**',
                '  ::',
                '    response = client.foo(',
                '        Bar=\'string\'',
                '        Biz=\'string\'',
                '    )',
                '  :type Biz: string',
                '  :param Biz:',
                '  :rtype: dict',
                '  :returns:',
                '    **Response Syntax**',
                '    ::',
                '      {',
                '          \'Biz\': \'string\'',
                '      }',
                '    **Response Structure**',
                '    - *(dict) --*',
                '      - **Biz** *(string) --*',
            ]
        )
        self.assert_not_contains_lines(
            [
                '\'Bar\': \'string\'',
                '- **Bar** *(string) --*',
            ]
        )

    def test_streaming_body_in_output(self):
        self.add_shape_to_params('Body', 'Blob')
        self.json_model['shapes']['Blob'] = {'type': 'blob'}
        self.json_model['shapes']['SampleOperationInputOutput']['payload'] = (
            'Body'
        )
        document_model_driven_method(
            self.doc_structure,
            'foo',
            self.operation_model,
            event_emitter=self.event_emitter,
            method_description='This describes the foo method.',
            example_prefix='response = client.foo',
        )
        self.assert_contains_line('**Body** (:class:`.StreamingBody`)')

    def test_event_stream_body_in_output(self):
        self.add_shape_to_params('Payload', 'EventStream')
        self.json_model['shapes']['SampleOperationInputOutput']['payload'] = (
            'Payload'
        )
        self.json_model['shapes']['EventStream'] = {
            'type': 'structure',
            'eventstream': True,
            'members': {'Event': {'shape': 'Event'}},
        }
        self.json_model['shapes']['Event'] = {
            'type': 'structure',
            'event': True,
            'members': {
                'Fields': {
                    'shape': 'EventFields',
                    'eventpayload': True,
                }
            },
        }
        self.json_model['shapes']['EventFields'] = {
            'type': 'structure',
            'members': {'Field': {'shape': 'EventField'}},
        }
        self.json_model['shapes']['EventField'] = {'type': 'blob'}
        document_model_driven_method(
            self.doc_structure,
            'foo',
            self.operation_model,
            event_emitter=self.event_emitter,
            method_description='This describes the foo method.',
            example_prefix='response = client.foo',
        )
        self.assert_contains_lines_in_order(
            [
                "this operation contains an :class:`.EventStream`",
                "'Payload': EventStream({",
                "'Event': {",
                "'Fields': {",
                "'Field': b'bytes'",
                "**Payload** (:class:`.EventStream`)",
                "**Event** *(dict)",
                "**Fields** *(dict)",
                "**Field** *(bytes)",
            ]
        )

    def test_streaming_body_in_input(self):
        del self.json_model['operations']['SampleOperation']['output']
        self.add_shape_to_params('Body', 'Blob')
        self.json_model['shapes']['Blob'] = {'type': 'blob'}
        self.json_model['shapes']['SampleOperationInputOutput']['payload'] = (
            'Body'
        )
        document_model_driven_method(
            self.doc_structure,
            'foo',
            self.operation_model,
            event_emitter=self.event_emitter,
            method_description='This describes the foo method.',
            example_prefix='response = client.foo',
        )
        # The line in the example
        self.assert_contains_line('Body=b\'bytes\'|file')
        # The line in the parameter description
        self.assert_contains_line(
            ':type Body: bytes or seekable file-like object'
        )

    def test_deprecated(self):
        self.json_model['operations']['SampleOperation']['deprecated'] = True
        document_model_driven_method(
            self.doc_structure,
            'foo',
            self.operation_model,
            event_emitter=self.event_emitter,
            method_description='This describes the foo method.',
            example_prefix='response = client.foo',
        )
        # The line in the example
        self.assert_contains_lines_in_order(
            [
                '  .. danger::',
                '        This operation is deprecated and may not function as '
                'expected. This operation should not be used going forward and is '
                'only kept for the purpose of backwards compatiblity.',
            ]
        )
