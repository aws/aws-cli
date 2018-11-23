# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from decimal import Decimal

from awscli.customizations.dynamodb.exceptions import (
    UnexpectedTokenError, UnknownExpressionError, InvalidLiteralValueError,
    EmptyExpressionError,
)
from awscli.customizations.dynamodb.parser import Parser
from awscli.testutils import unittest


class FakeLexer(object):
    def __init__(self, tokens):
        self._tokens = tokens

    def tokenize(self, expression):
        return self._tokens


class TestParser(unittest.TestCase):
    maxDiff = None

    def assert_parse(self, tokens, expected):
        self.assertEqual(expected, self._parse(tokens))

    def _parse(self, tokens, expression=None):
        if expression is None:
            self._insert_token_positions(tokens)
            expression = ''
            for token in tokens:
                expression += str(token['value']) + ' '
            expression = expression.strip()
        lexer = FakeLexer(tokens)
        parser = Parser(lexer)
        return parser.parse(expression)

    def _insert_token_positions(self, tokens):
        position = 0
        for token in tokens:
            if 'start' not in token:
                token['start'] = position
            if 'end' not in token:
                token['end'] = token['start'] + len(str(token['value']))
            position = token['end'] + 1

    def test_parse_sequence(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'comma', 'value': ','},
            {'type': 'identifier', 'value': 'bar'},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'sequence',
            'children': [
                {'type': 'identifier', 'value': 'foo', 'children': []},
                {'type': 'identifier', 'value': 'bar', 'children': []},
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_single_identifier(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eof', 'value': ''},
        ]
        expected = {'type': 'identifier', 'value': 'foo', 'children': []}
        self.assert_parse(tokens, expected)

    def test_parse_and_expression(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'and', 'value': 'and'},
            {'type': 'identifier', 'value': 'baz'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bam'},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'and_expression',
            'children': [
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {'type': 'identifier', 'value': 'foo', 'children': []},
                        {'type': 'literal', 'value': 'bar', 'children': []},
                    ],
                },
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {'type': 'identifier', 'value': 'baz', 'children': []},
                        {'type': 'literal', 'value': 'bam', 'children': []},
                    ],
                },
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_multiple_and_expressions(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'and', 'value': 'and'},
            {'type': 'identifier', 'value': 'baz'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bam'},
            {'type': 'and', 'value': 'and'},
            {'type': 'identifier', 'value': 'spam'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'eggs'},
            {'type': 'eof', 'value': ''},
        ]
        left_and_expression = {
            'type': 'and_expression',
            'children': [
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {'type': 'identifier', 'value': 'foo', 'children': []},
                        {'type': 'literal', 'value': 'bar', 'children': []},
                    ],
                },
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {'type': 'identifier', 'value': 'baz', 'children': []},
                        {'type': 'literal', 'value': 'bam', 'children': []},
                    ],
                },
            ]
        }
        expected = {
            'type': 'and_expression',
            'children': [
                left_and_expression,
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {
                            'type': 'identifier',
                            'value': 'spam', 'children': []
                        },
                        {'type': 'literal', 'value': 'eggs', 'children': []},
                    ],
                },
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_and_missing_second_expression(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'and', 'value': 'and'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnknownExpressionError):
            self._parse(tokens)

    def test_parse_or_expression(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'or', 'value': 'or'},
            {'type': 'identifier', 'value': 'baz'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bam'},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'or_expression',
            'children': [
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {'type': 'identifier', 'value': 'foo', 'children': []},
                        {'type': 'literal', 'value': 'bar', 'children': []},
                    ],
                },
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {'type': 'identifier', 'value': 'baz', 'children': []},
                        {'type': 'literal', 'value': 'bam', 'children': []},
                    ],
                },
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_multiple_or_expressions(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'or', 'value': 'or'},
            {'type': 'identifier', 'value': 'baz'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bam'},
            {'type': 'or', 'value': 'or'},
            {'type': 'identifier', 'value': 'spam'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'eggs'},
            {'type': 'eof', 'value': ''},
        ]
        left_or_expression = {
            'type': 'or_expression',
            'children': [
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {'type': 'identifier', 'value': 'foo', 'children': []},
                        {'type': 'literal', 'value': 'bar', 'children': []},
                    ],
                },
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {'type': 'identifier', 'value': 'baz', 'children': []},
                        {'type': 'literal', 'value': 'bam', 'children': []},
                    ],
                },
            ]
        }
        expected = {
            'type': 'or_expression',
            'children': [
                left_or_expression,
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {
                            'type': 'identifier',
                            'value': 'spam', 'children': []
                        },
                        {'type': 'literal', 'value': 'eggs', 'children': []},
                    ],
                },
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_or_missing_second_expression(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'or', 'value': 'or'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnknownExpressionError):
            self._parse(tokens)

    def test_parse_mixed_and_or_expressions(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'and', 'value': 'and'},
            {'type': 'identifier', 'value': 'baz'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bam'},
            {'type': 'or', 'value': 'or'},
            {'type': 'identifier', 'value': 'spam'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'eggs'},
            {'type': 'eof', 'value': ''},
        ]
        left_and_expression = {
            'type': 'and_expression',
            'children': [
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {'type': 'identifier', 'value': 'foo', 'children': []},
                        {'type': 'literal', 'value': 'bar', 'children': []},
                    ],
                },
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {'type': 'identifier', 'value': 'baz', 'children': []},
                        {'type': 'literal', 'value': 'bam', 'children': []},
                    ],
                },
            ]
        }
        expected = {
            'type': 'or_expression',
            'children': [
                left_and_expression,
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {
                            'type': 'identifier',
                            'value': 'spam', 'children': []
                        },
                        {'type': 'literal', 'value': 'eggs', 'children': []},
                    ],
                },
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_subexpression(self):
        tokens = [
            {'type': 'lparen', 'value': '('},
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'rparen', 'value': ')'},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'subexpression',
            'children': [
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {'type': 'identifier', 'value': 'foo', 'children': []},
                        {'type': 'literal', 'value': 'bar', 'children': []},
                    ],
                },
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_subexpression_with_and(self):
        tokens = [
            {'type': 'lparen', 'value': '('},
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'and', 'value': 'and'},
            {'type': 'identifier', 'value': 'baz'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bam'},
            {'type': 'rparen', 'value': ')'},
            {'type': 'eof', 'value': ''},
        ]
        and_expression = {
            'type': 'and_expression',
            'children': [
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {'type': 'identifier', 'value': 'foo', 'children': []},
                        {'type': 'literal', 'value': 'bar', 'children': []},
                    ],
                },
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {'type': 'identifier', 'value': 'baz', 'children': []},
                        {'type': 'literal', 'value': 'bam', 'children': []},
                    ],
                },
            ]
        }
        expected = {
            'type': 'subexpression',
            'children': [and_expression]
        }
        self.assert_parse(tokens, expected)

    def test_parse_subexpression_unmatched_paren(self):
        tokens = [
            {'type': 'lparen', 'value': '('},
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_parse_not_expression(self):
        tokens = [
            {'type': 'not', 'value': 'not'},
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'not_expression',
            'children': [
                {
                    'type': 'comparator', 'value': 'eq',
                    'children': [
                        {'type': 'identifier', 'value': 'foo', 'children': []},
                        {'type': 'literal', 'value': 'bar', 'children': []},
                    ],
                },
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_not_missing_expression(self):
        tokens = [
            {'type': 'not', 'value': 'not'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnknownExpressionError):
            self._parse(tokens)

    def test_parse_function(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'lparen', 'value': '('},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'comma', 'value': ','},
            {'type': 'literal', 'value': 'baz'},
            {'type': 'rparen', 'value': ')'},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'function', 'value': 'foo',
            'children': [
                {'type': 'literal', 'value': 'bar', 'children': []},
                {'type': 'literal', 'value': 'baz', 'children': []},
            ]
        }
        self.assert_parse(tokens, expected)

    def test_function_missing_closing_paren(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'lparen', 'value': '('},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_function_args_missing_comma(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'lparen', 'value': '('},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'literal', 'value': 'baz'},
            {'type': 'rparen', 'value': ')'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_parse_in_expression(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'in', 'value': 'in'},
            {'type': 'lparen', 'value': '('},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'comma', 'value': ','},
            {'type': 'literal', 'value': 'baz'},
            {'type': 'rparen', 'value': ')'},
            {'type': 'eof', 'value': ''},
        ]
        sequence = {
            'type': 'sequence',
            'children': [
                {'type': 'literal', 'value': 'bar', 'children': []},
                {'type': 'literal', 'value': 'baz', 'children': []},
            ]
        }
        expected = {
            'type': 'in_expression',
            'children': [
                {'type': 'identifier', 'value': 'foo', 'children': []},
                sequence,
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_in_missing_operand(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'in', 'value': 'in'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_in_missing_parens(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'in', 'value': 'in'},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'comma', 'value': ','},
            {'type': 'literal', 'value': 'baz'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_parse_between_expression(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'between', 'value': 'between'},
            {'type': 'literal', 'value': 1},
            {'type': 'and', 'value': 'and'},
            {'type': 'literal', 'value': 3},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'between_expression',
            'children': [
                {'type': 'identifier', 'value': 'foo', 'children': []},
                {'type': 'literal', 'value': 1, 'children': []},
                {'type': 'literal', 'value': 3, 'children': []},
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_between_missing_and(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'between', 'value': 'between'},
            {'type': 'literal', 'value': 1},
            {'type': 'literal', 'value': 3},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_parse_between_missing_right_operand(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'between', 'value': 'between'},
            {'type': 'literal', 'value': 1},
            {'type': 'and', 'value': 'and'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_parse_between_missing_center_operand(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'between', 'value': 'between'},
            {'type': 'and', 'value': 'and'},
            {'type': 'literal', 'value': 3},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_parse_comparison_expression(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'lte', 'value': '<='},
            {'type': 'literal', 'value': 8},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'comparator', 'value': 'lte',
            'children': [
                {'type': 'identifier', 'value': 'foo', 'children': []},
                {'type': 'literal', 'value': 8, 'children': []},
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_unmatched_comparator(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'gte', 'value': '>='},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_parse_list_literal(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'lbracket', 'value': '['},
            {'type': 'literal', 'value': 8},
            {'type': 'comma', 'value': ','},
            {'type': 'literal', 'value': 9},
            {'type': 'rbracket', 'value': ']'},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'comparator', 'value': 'eq',
            'children': [
                {'type': 'identifier', 'value': 'foo', 'children': []},
                {'type': 'literal', 'children': [], 'value': [8, 9]},
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_empty_list(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'lbracket', 'value': '['},
            {'type': 'rbracket', 'value': ']'},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'comparator', 'value': 'eq',
            'children': [
                {'type': 'identifier', 'value': 'foo', 'children': []},
                {'type': 'literal', 'children': [], 'value': []},
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_list_literal_can_only_contain_literals(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'lbracket', 'value': '['},
            {'type': 'identifier', 'value': 'bar'},
            {'type': 'comma', 'value': ','},
            {'type': 'literal', 'value': 9},
            {'type': 'rbracket', 'value': ']'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_list_with_unmatched_bracket(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'lbracket', 'value': '['},
            {'type': 'literal', 'value': 9},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_parse_set_literal(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'lbrace', 'value': '{'},
            {'type': 'literal', 'value': Decimal('8')},
            {'type': 'comma', 'value': ','},
            {'type': 'literal', 'value': Decimal('9')},
            {'type': 'rbrace', 'value': '}'},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'comparator', 'value': 'eq',
            'children': [
                {'type': 'identifier', 'value': 'foo', 'children': []},
                {'type': 'literal', 'children': [], 'value': {8, 9}},
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_set_literal_can_only_contain_literals(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'lbrace', 'value': '{'},
            {'type': 'identifier', 'value': 'bar'},
            {'type': 'rbrace', 'value': '}'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_parse_sets_dont_take_floats(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'lbrace', 'value': '{'},
            {'type': 'literal', 'value': 1.1},
            {'type': 'rbrace', 'value': '}'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(InvalidLiteralValueError):
            self._parse(tokens)

    def test_sets_cant_contain_collections(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'lbrace', 'value': '{'},
            {'type': 'lbracket', 'value': '['},
            {'type': 'literal', 'value': 9},
            {'type': 'rbracket', 'value': ']'},
            {'type': 'rbrace', 'value': '}'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_set_values_must_all_be_same_type(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'lbrace', 'value': '{'},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'comma', 'value': ','},
            {'type': 'literal', 'value': Decimal('9')},
            {'type': 'rbrace', 'value': '}'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(InvalidLiteralValueError):
            self._parse(tokens)

    def test_set_with_unmatched_brace(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'lbrace', 'value': '{'},
            {'type': 'literal', 'value': Decimal('8')},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_parse_map_literal(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'lbrace', 'value': '{'},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'colon', 'value': ':'},
            {'type': 'literal', 'value': 4},
            {'type': 'comma', 'value': ','},
            {'type': 'literal', 'value': 'baz'},
            {'type': 'colon', 'value': ':'},
            {'type': 'literal', 'value': 3},
            {'type': 'rbrace', 'value': '}'},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'comparator', 'value': 'eq',
            'children': [
                {'type': 'identifier', 'value': 'foo', 'children': []},
                {'type': 'literal', 'children': [], 'value': {
                    "bar": 4, "baz": 3
                }},
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_empty_map(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'lbrace', 'value': '{'},
            {'type': 'rbrace', 'value': '}'},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'comparator', 'value': 'eq',
            'children': [
                {'type': 'identifier', 'value': 'foo', 'children': []},
                {'type': 'literal', 'children': [], 'value': {}},
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_map_with_unmatched_brace(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'lbrace', 'value': '{'},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'colon', 'value': ':'},
            {'type': 'literal', 'value': 4},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_map_missing_colon(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'lbrace', 'value': '{'},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'literal', 'value': 4},
            {'type': 'rbrace', 'value': '}'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_map_key_must_be_string(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'eq', 'value': '='},
            {'type': 'lbrace', 'value': '{'},
            {'type': 'literal', 'value': 9},
            {'type': 'colon', 'value': ':'},
            {'type': 'literal', 'value': 4},
            {'type': 'rbrace', 'value': '}'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(InvalidLiteralValueError):
            self._parse(tokens)

    def test_parse_empty_expression(self):
        tokens = [{'type': 'eof', 'value': ''}]
        with self.assertRaises(EmptyExpressionError):
            self._parse(tokens)

    def test_eof_expected_but_not_matched(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'comma', 'value': ','},
            {'type': 'identifier', 'value': 'bar'},
            {'type': 'identifier', 'value': 'baz'},
            {'type': 'eof', 'value': ''},
        ]
        expected = 'Expected type: eof'
        with self.assertRaisesRegexp(UnexpectedTokenError, expected):
            self._parse(tokens)

    def test_missing_eof(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'comma', 'value': ','},
            {'type': 'identifier', 'value': 'bar'},
        ]
        with self.assertRaises(UnexpectedTokenError):
            self._parse(tokens)

    def test_dotted_identifier(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'dot', 'value': '.'},
            {'type': 'identifier', 'value': 'bar'},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'path_identifier',
            'children': [
                {'type': 'identifier', 'value': 'foo', 'children': []},
                {'type': 'identifier', 'value': 'bar', 'children': []},
            ]
        }
        self.assert_parse(tokens, expected)

    def test_index_identifier(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'lbracket', 'value': '['},
            {'type': 'literal', 'value': Decimal(0)},
            {'type': 'rbracket', 'value': ']'},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'index_identifier', 'value': Decimal(0),
            'children': [
                {'type': 'identifier', 'value': 'foo', 'children': []},
            ]
        }
        self.assert_parse(tokens, expected)

    def test_index_identifier_must_be_whole_number(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'lbracket', 'value': '['},
            {'type': 'literal', 'value': Decimal(1.1)},
            {'type': 'rbracket', 'value': ']'},
            {'type': 'eof', 'value': ''},
        ]
        with self.assertRaises(InvalidLiteralValueError):
            self._parse(tokens)

    def test_dotted_index_identifier(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'lbracket', 'value': '['},
            {'type': 'literal', 'value': Decimal(0)},
            {'type': 'rbracket', 'value': ']'},
            {'type': 'dot', 'value': '.'},
            {'type': 'identifier', 'value': 'bar'},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'path_identifier',
            'children': [
                {'type': 'index_identifier', 'value': Decimal(0), 'children': [
                    {'type': 'identifier', 'value': 'foo', 'children': []},
                ]},
                {'type': 'identifier', 'value': 'bar', 'children': []},
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_between_complex_identifier(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'dot', 'value': '.'},
            {'type': 'identifier', 'value': 'bar'},
            {'type': 'between', 'value': 'between'},
            {'type': 'literal', 'value': 1},
            {'type': 'and', 'value': 'and'},
            {'type': 'literal', 'value': 3},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'between_expression',
            'children': [
                {'type': 'path_identifier', 'children': [
                    {'type': 'identifier', 'value': 'foo', 'children': []},
                    {'type': 'identifier', 'value': 'bar', 'children': []},
                ]},
                {'type': 'literal', 'value': 1, 'children': []},
                {'type': 'literal', 'value': 3, 'children': []},
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_in_complex_identifier(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'lbracket', 'value': '['},
            {'type': 'literal', 'value': Decimal(0)},
            {'type': 'rbracket', 'value': ']'},
            {'type': 'in', 'value': 'in'},
            {'type': 'lparen', 'value': '('},
            {'type': 'literal', 'value': 'bar'},
            {'type': 'comma', 'value': ','},
            {'type': 'literal', 'value': 'baz'},
            {'type': 'rparen', 'value': ')'},
            {'type': 'eof', 'value': ''},
        ]
        sequence = {
            'type': 'sequence',
            'children': [
                {'type': 'literal', 'value': 'bar', 'children': []},
                {'type': 'literal', 'value': 'baz', 'children': []},
            ]
        }
        expected = {
            'type': 'in_expression',
            'children': [
                {'type': 'index_identifier', 'value': Decimal(0), 'children': [
                    {'type': 'identifier', 'value': 'foo', 'children': []},
                ]},
                sequence,
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_compare_complex_identifier(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'dot', 'value': '.'},
            {'type': 'identifier', 'value': 'bar'},
            {'type': 'gte', 'value': '>='},
            {'type': 'literal', 'value': 8},
            {'type': 'eof', 'value': ''},
        ]
        expected = {
            'type': 'comparator', 'value': 'gte',
            'children': [
                {'type': 'path_identifier', 'children': [
                    {'type': 'identifier', 'value': 'foo', 'children': []},
                    {'type': 'identifier', 'value': 'bar', 'children': []},
                ]},
                {'type': 'literal', 'value': 8, 'children': []},
            ]
        }
        self.assert_parse(tokens, expected)

    def test_parse_complex_identifier_sequence(self):
        tokens = [
            {'type': 'identifier', 'value': 'foo'},
            {'type': 'dot', 'value': '.'},
            {'type': 'identifier', 'value': 'bar'},
            {'type': 'comma', 'value': ','},
            {'type': 'identifier', 'value': 'baz'},
            {'type': 'eof', 'value': ''},
        ]
        first = {
            'type': 'path_identifier',
            'children': [
                {'type': 'identifier', 'value': 'foo', 'children': []},
                {'type': 'identifier', 'value': 'bar', 'children': []},
            ]
        }
        expected = {
            'type': 'sequence', 'children': [
                first,
                {'type': 'identifier', 'value': 'baz', 'children': []},
            ]
        }
        self.assert_parse(tokens, expected)
