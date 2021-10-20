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
from botocore.compat import OrderedDict
from tests.unit.docs import BaseDocsTest
from botocore.docs.sharedexample import SharedExampleDocumenter, \
    document_shared_examples


class TestDocumentSharedExamples(BaseDocsTest):
    def setUp(self):
        super(TestDocumentSharedExamples, self).setUp()
        self.add_shape({
            "foo": {
                "type": "string"
            }
        })
        self.add_shape({
            "nested": {"type": "string"}
        })
        self.add_shape({
            "other": {
                "type": "structure",
                "members": {"nested": {"shape": "nested"}}
            }
        })
        self.add_shape({
            "aloha": {
                "type": "list",
                "member": {"shape": "other"}
            }
        })
        self.add_shape_to_params('foo', 'foo')
        self.add_shape_to_params('aloha', 'aloha')
        self._examples = [{
                "id": "sample-id",
                "title": "sample-title",
                "description": "Sample Description.",
                "input": OrderedDict([
                    ("aloha", [
                        "other",
                        {
                            "nested": "fun!"
                        }
                    ]),
                    ("foo", "bar"),
                ]),
                "output": OrderedDict([
                    ("foo", "baz"),
                ]),
                "comments": {
                    "input": {
                        "aloha": "mahalo"
                    },
                    "output": {
                        "foo": "Sample Comment"
                    }
                }
            }
        ]

    def test_default(self):
        document_shared_examples(
            self.doc_structure, self.operation_model,
            'response = client.foo', self._examples)
        self.assert_contains_lines_in_order([
            "**Examples**",
            "Sample Description.",
            "::",
            "  response = client.foo(",
            "      # mahalo",
            "      aloha=[",
            "          'other',",
            "          {",
            "              'nested': 'fun!',",
            "          },",
            "      ],",
            "      foo='bar',",
            "  )",
            "  print(response)",
            "Expected Output:",
            "::",
            "  {",
            "      # Sample Comment",
            "      'foo': 'baz',",
            "      'ResponseMetadata': {",
            "          '...': '...',",
            "      },",
            "  }",
        ])


class TestSharedExampleDocumenter(BaseDocsTest):
    def setUp(self):
        super(TestSharedExampleDocumenter, self).setUp()
        self.documenter = SharedExampleDocumenter()

    def test_is_input(self):
        self.add_shape_to_params('foo', 'String')
        self.documenter.document_shared_example(
            example={
                'input': {
                    'foo': 'bar'
                }
            },
            prefix='foo.bar',
            section=self.doc_structure,
            operation_model=self.operation_model
        )
        self.assert_contains_lines_in_order([
            "foo.bar(",
            "    foo='bar'",
            ")"
        ])

    def test_dict_example(self):
        self.add_shape({
            'bar': {
                "type": "structure",
                "members": {
                    "bar": {"shape": "String"}
                }
            }
        })
        self.add_shape_to_params('foo', 'bar')
        self.documenter.document_shared_example(
            example={
                'input': {
                    'foo': {'bar': 'baz'}
                }
            },
            prefix='foo.bar',
            section=self.doc_structure,
            operation_model=self.operation_model
        )
        self.assert_contains_lines_in_order([
            "foo.bar(",
            "    foo={",
            "        'bar': 'baz',",
            "    },",
            ")"
        ])

    def test_list_example(self):
        self.add_shape({
            "foo": {
                "type": "list",
                "member": {"shape": "String"}
            }
        })
        self.add_shape_to_params('foo', 'foo')
        self.documenter.document_shared_example(
            example={
                'input': {
                    'foo': ['bar']
                }
            },
            prefix='foo.bar',
            section=self.doc_structure,
            operation_model=self.operation_model
        )
        self.assert_contains_lines_in_order([
            "foo.bar(",
            "    foo=[",
            "        'bar',",
            "    ],",
            ")"
        ])

    def test_can_handle_no_input_key(self):
        self.add_shape_to_params('foo', 'String')
        self.documenter.document_shared_example(
            example={},
            prefix='foo.bar',
            section=self.doc_structure,
            operation_model=self.operation_model
        )
        self.assert_contains_lines_in_order([
            "foo.bar(",
            ")"
        ])

    def test_unicode_string_example(self):
        self.add_shape_to_params('foo', 'String')
        self.documenter.document_shared_example(
            example={
                'input': {
                    'foo': u'bar'
                }
            },
            prefix='foo.bar',
            section=self.doc_structure,
            operation_model=self.operation_model
        )
        self.assert_contains_lines_in_order([
            "foo.bar(",
            "    foo='bar'",
            ")"
        ])

    def test_timestamp_example(self):
        self.add_shape({
            'foo': {'type': 'timestamp'}
        })
        self.add_shape_to_params('foo', 'foo')
        self.documenter.document_shared_example(
            example={
                'input': {
                    'foo': 'Fri, 20 Nov 2015 21:13:12 GMT'
                }
            },
            prefix='foo.bar',
            section=self.doc_structure,
            operation_model=self.operation_model
        )
        self.assert_contains_lines_in_order([
            "foo.bar(",
            "    foo=datetime(2015, 11, 20, 21, 13, 12, 4, 324, 0)",
            ")"
        ])

    def test_map_example(self):
        self.add_shape({
            "baz": {"type": "string"}
        })
        self.add_shape({
            'bar': {
                "type": "map",
                "key": {"shape": "baz"},
                "value": {"shape": "baz"}
            }
        })
        self.add_shape_to_params('foo', 'bar')
        self.documenter.document_shared_example(
            example={
                'input': {
                    'foo': {'bar': 'baz'}
                }
            },
            prefix='foo.bar',
            section=self.doc_structure,
            operation_model=self.operation_model
        )
        self.assert_contains_lines_in_order([
            "foo.bar(",
            "    foo={",
            "        'bar': 'baz',",
            "    },",
            ")"
        ])

    def test_add_comment(self):
        self.add_shape_to_params('foo', 'String')
        self.documenter.document_shared_example(
            example={
                'input': {
                    'foo': 'bar'
                },
                'comments': {
                    'input': {
                        'foo': 'baz'
                    }
                }
            },
            prefix='foo.bar',
            section=self.doc_structure,
            operation_model=self.operation_model
        )
        self.assert_contains_lines_in_order([
            "foo.bar(",
            "    # baz",
            "    foo='bar',",
            ")"
        ])

    def test_unicode_exammple(self):
        self.add_shape_to_params('foo', 'String')
        self.documenter.document_shared_example(
            example={
                'input': {
                    'foo': u'\u2713'
                }
            },
            prefix='foo.bar',
            section=self.doc_structure,
            operation_model=self.operation_model
        )
        self.assert_contains_lines_in_order([
            u"foo.bar(",
            u"    foo='\u2713'",
            u")"
        ])

    def test_escape_character_example(self):
        self.add_shape_to_params('foo', 'String')
        self.documenter.document_shared_example(
            example={
                'output': {
                    'foo': 'good\n\rintentions!\n\r'
                }
            },
            prefix='foo.bar',
            section=self.doc_structure,
            operation_model=self.operation_model
        )
        self.assert_contains_lines_in_order([
            "Expected Output:",
            "  {",
            "      'foo': 'good\\n\\rintentions!\\n\\r',",
            "  }",
        ])
