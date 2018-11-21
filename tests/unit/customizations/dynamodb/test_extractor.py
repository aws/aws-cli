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
from decimal import Decimal

from awscli.customizations.dynamodb.extractor import AttributeExtractor
from awscli.testutils import unittest


class FakeParser(object):
    def __init__(self, parsed_result):
        self.parsed_result = parsed_result

    def parse(self, expression):
        return self.parsed_result


class TestExtractor(unittest.TestCase):
    def test_extract_identifier(self):
        parsed_result = {'type': 'identifier', 'value': 'spam'}
        parser = FakeParser(parsed_result)
        extractor = AttributeExtractor(parser)
        result = extractor.extract('spam')
        expected = {
            'expression': '#n0',
            'identifiers': {'#n0': 'spam'},
            'values': {},
            'substitution_count': 1,
        }
        self.assertEqual(result, expected)

    def test_extract_string(self):
        parsed_result = {'type': 'literal', 'value': 'spam'}
        parser = FakeParser(parsed_result)
        extractor = AttributeExtractor(parser)
        result = extractor.extract('"spam"')
        expected = {
            'expression': ':n0',
            'identifiers': {},
            'values': {':n0': 'spam'},
            'substitution_count': 1,
        }
        self.assertEqual(result, expected)

    def test_extract_bytes(self):
        parsed_result = {'type': 'literal', 'value': b'spam'}
        parser = FakeParser(parsed_result)
        extractor = AttributeExtractor(parser)
        result = extractor.extract('b"spam"')
        expected = {
            'expression': ':n0',
            'identifiers': {},
            'values': {':n0': b'spam'},
            'substitution_count': 1,
        }
        self.assertEqual(result, expected)

    def test_extract_number(self):
        parsed_result = {'type': 'literal', 'value': 7}
        parser = FakeParser(parsed_result)
        extractor = AttributeExtractor(parser)
        result = extractor.extract("7")
        expected = {
            'expression': ':n0',
            'identifiers': {},
            'values': {':n0': 7},
            'substitution_count': 1,
        }
        self.assertEqual(result, expected)

    def test_set_index_offset(self):
        parsed_result = {'type': 'identifier', 'value': 'spam'}
        parser = FakeParser(parsed_result)
        extractor = AttributeExtractor(parser)
        result = extractor.extract('spam', 5)
        expected = {
            'expression': '#n5',
            'identifiers': {'#n5': 'spam'},
            'values': {},
            'substitution_count': 1,
        }
        self.assertEqual(result, expected)

    def test_represent_comparator(self):
        parsed_result = {
            'type': 'comparator', 'value': 'eq',
            'children': [
                {'type': 'identifier', 'value': 'spam'},
                {'type': 'literal', 'value': 7}
            ]
        }
        parser = FakeParser(parsed_result)
        extractor = AttributeExtractor(parser)
        result = extractor.extract('spam = 7')
        expected = {
            'expression': '#n0 = :n1',
            'identifiers': {'#n0': 'spam'},
            'values': {':n1': 7},
            'substitution_count': 2,
        }
        self.assertEqual(result, expected)

    def test_represent_or(self):
        parsed_result = {
            'type': 'or_expression',
            'children': [
                {'type': 'comparator', 'value': 'eq', 'children': [
                    {'type': 'identifier', 'value': 'spam'},
                    {'type': 'literal', 'value': 7}
                ]},
                {'type': 'comparator', 'value': 'eq', 'children': [
                    {'type': 'identifier', 'value': 'eggs'},
                    {'type': 'literal', 'value': 6}
                ]}
            ]
        }
        parser = FakeParser(parsed_result)
        extractor = AttributeExtractor(parser)
        result = extractor.extract('spam = 7 or eggs = 6')
        expected = {
            'expression': '#n0 = :n1 OR #n2 = :n3',
            'identifiers': {'#n0': 'spam', '#n2': 'eggs'},
            'values': {':n1': 7, ':n3': 6},
            'substitution_count': 4,
        }
        self.assertEqual(result, expected)

    def test_represent_and(self):
        parsed_result = {
            'type': 'and_expression',
            'children': [
                {'type': 'comparator', 'value': 'eq', 'children': [
                    {'type': 'identifier', 'value': 'spam'},
                    {'type': 'literal', 'value': 7}
                ]},
                {'type': 'comparator', 'value': 'eq', 'children': [
                    {'type': 'identifier', 'value': 'eggs'},
                    {'type': 'literal', 'value': 6}
                ]}
            ]
        }
        parser = FakeParser(parsed_result)
        extractor = AttributeExtractor(parser)
        result = extractor.extract('spam = 7 and eggs = 6')
        expected = {
            'expression': '#n0 = :n1 AND #n2 = :n3',
            'identifiers': {'#n0': 'spam', '#n2': 'eggs'},
            'values': {':n1': 7, ':n3': 6},
            'substitution_count': 4,
        }
        self.assertEqual(result, expected)

    def test_represent_in(self):
        parsed_result = {
            'type': 'in_expression',
            'children': [
                {'type': 'identifier', 'value': 'spam'},
                {'type': 'sequence', 'children': [
                    {'type': 'literal', 'value': 1},
                    {'type': 'literal', 'value': 2},
                ]}
            ]
        }
        parser = FakeParser(parsed_result)
        extractor = AttributeExtractor(parser)
        result = extractor.extract('spam IN (2, 3)')
        expected = {
            'expression': '#n0 IN (:n1, :n2)',
            'identifiers': {'#n0': 'spam'},
            'values': {':n1': 1, ':n2': 2},
            'substitution_count': 3,
        }
        self.assertEqual(result, expected)

    def test_represent_not(self):
        parsed_result = {
            'type': 'not_expression',
            'children': [
                {'type': 'comparator', 'value': 'ne', 'children': [
                    {'type': 'identifier', 'value': 'spam'},
                    {'type': 'literal', 'value': 7}
                ]},
            ]
        }
        parser = FakeParser(parsed_result)
        extractor = AttributeExtractor(parser)
        result = extractor.extract('NOT spam <> 7')
        expected = {
            'expression': 'NOT #n0 <> :n1',
            'identifiers': {'#n0': 'spam'},
            'values': {':n1': 7},
            'substitution_count': 2,
        }
        self.assertEqual(result, expected)

    def test_represent_subexpression(self):
        parsed_result = {
            'type': 'subexpression',
            'children': [
                {'type': 'comparator', 'value': 'lte', 'children': [
                    {'type': 'identifier', 'value': 'spam'},
                    {'type': 'literal', 'value': 7}
                ]},
            ]
        }
        parser = FakeParser(parsed_result)
        extractor = AttributeExtractor(parser)
        result = extractor.extract('( spam <= 7 )')
        expected = {
            'expression': '( #n0 <= :n1 )',
            'identifiers': {'#n0': 'spam'},
            'values': {':n1': 7},
            'substitution_count': 2,
        }
        self.assertEqual(result, expected)

    def test_represent_between(self):
        parsed_result = {
            'type': 'between_expression',
            'children': [
                {'type': 'identifier', 'value': 'spam'},
                {'type': 'literal', 'value': 1},
                {'type': 'literal', 'value': 2},
            ]
        }
        parser = FakeParser(parsed_result)
        extractor = AttributeExtractor(parser)
        result = extractor.extract('spam between 1 and 2')
        expected = {
            'expression': '#n0 BETWEEN :n1 AND :n2',
            'identifiers': {'#n0': 'spam'},
            'values': {':n1': 1, ':n2': 2},
            'substitution_count': 3,
        }
        self.assertEqual(result, expected)

    def test_represent_function(self):
        parsed_result = {
            'type': 'function', 'value': 'myfunction',
            'children': [
                {'type': 'identifier', 'value': 'spam'},
                {'type': 'literal', 'value': 1},
            ]
        }
        parser = FakeParser(parsed_result)
        extractor = AttributeExtractor(parser)
        result = extractor.extract('myfunction(1, 2)')
        expected = {
            'expression': 'myfunction(#n0, :n1)',
            'identifiers': {'#n0': 'spam'},
            'values': {':n1': 1},
            'substitution_count': 2,
        }
        self.assertEqual(result, expected)

    def test_represent_path_identifier(self):
        parsed_result = {
            'type': 'path_identifier',
            'children': [
                {'type': 'identifier', 'value': 'foo', 'children': []},
                {'type': 'identifier', 'value': 'bar', 'children': []},
            ]
        }
        parser = FakeParser(parsed_result)
        extractor = AttributeExtractor(parser)
        result = extractor.extract('foo.bar')
        expected = {
            'expression': '#n0.#n1',
            'identifiers': {'#n0': 'foo', '#n1': 'bar'},
            'values': {},
            'substitution_count': 2,
        }
        self.assertEqual(result, expected)

    def test_represent_index_identifier(self):
        parsed_result = {
            'type': 'index_identifier', 'value': Decimal(0),
            'children': [
                {'type': 'identifier', 'value': 'foo', 'children': []},
            ]
        }
        parser = FakeParser(parsed_result)
        extractor = AttributeExtractor(parser)
        result = extractor.extract('foo[0]')
        expected = {
            'expression': '#n0[0]',
            'identifiers': {'#n0': 'foo'},
            'values': {},
            'substitution_count': 1,
        }
        self.assertEqual(result, expected)

    def test_represent_dotted_index_identifier(self):
        parsed_result = {
            'type': 'path_identifier',
            'children': [
                {'type': 'index_identifier', 'value': Decimal(0), 'children': [
                    {'type': 'identifier', 'value': 'foo', 'children': []},
                ]},
                {'type': 'identifier', 'value': 'bar', 'children': []},
            ]
        }
        parser = FakeParser(parsed_result)
        extractor = AttributeExtractor(parser)
        result = extractor.extract('foo[0].bar')
        expected = {
            'expression': '#n0[0].#n1',
            'identifiers': {'#n0': 'foo', '#n1': 'bar'},
            'values': {},
            'substitution_count': 2,
        }
        self.assertEqual(result, expected)

