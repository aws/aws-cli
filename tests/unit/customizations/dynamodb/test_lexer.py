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

from nose.tools import assert_equal, assert_raises, assert_in

from awscli.customizations.dynamodb.exceptions import (
    LexerError, EmptyExpressionError,
)
from awscli.customizations.dynamodb.lexer import Lexer


def test_lexer():
    cases = [
        ('foo', [{'type': 'unquoted_identifier', 'value': 'foo'}]),
        ("'foo'", [{'type': 'identifier', 'value': 'foo'}]),
        ("'f\\'oo'", [{'type': 'identifier', 'value': "f'oo"}]),
        ('"spam"', [{'type': 'literal', 'value': 'spam'}]),
        ('"s\\"pam"', [{'type': 'literal', 'value': 's"pam'}]),
        ('100', [{'type': 'literal', 'value': Decimal('100')}]),
        ('-100', [{'type': 'literal', 'value': Decimal('-100')}]),
        ('1.01', [{'type': 'literal', 'value': Decimal('1.01')}]),
        ('1.01e6', [{'type': 'literal', 'value': Decimal('1.01e6')}]),
        ('1.01E6', [{'type': 'literal', 'value': Decimal('1.01e6')}]),
        ('1.01e+6', [{'type': 'literal', 'value': Decimal('1.01e6')}]),
        ('1.01e-6', [{'type': 'literal', 'value': Decimal('1.01e-6')}]),
        ("foo, 'bar', \"baz\"", [
            {'type': 'unquoted_identifier', 'value': 'foo'},
            {'type': 'comma', 'value': ','},
            {'type': 'identifier', 'value': 'bar'},
            {'type': 'comma', 'value': ','},
            {'type': 'literal', 'value': 'baz'},
        ]),
        ('b"4pyT"', [{'type': 'literal', 'value': b'\xe2\x9c\x93'}]),
        ('boo', [{'type': 'unquoted_identifier', 'value': 'boo'}]),
        ('b[0]', [
            {'type': 'unquoted_identifier', 'value': 'b'},
            {'type': 'lbracket', 'value': '['},
            {'type': 'literal', 'value': Decimal('0')},
            {'type': 'rbracket', 'value': ']'},
        ]),
        ('true', [{'type': 'literal', 'value': True}]),
        ('false', [{'type': 'literal', 'value': False}]),
        ('null', [{'type': 'literal', 'value': None}]),
    ]

    tester = LexTester()
    for case in cases:
        yield tester.assert_tokens, case[0], case[1]

    simple_tokens = {
        '.': 'dot',
        ',': 'comma',
        ':': 'colon',
        '(': 'lparen',
        ')': 'rparen',
        '{': 'lbrace',
        '}': 'rbrace',
        '[': 'lbracket',
        ']': 'rbracket',
        '=': 'eq',
        '>': 'gt',
        '>=': 'gte',
        '<': 'lt',
        '<=': 'lte',
        '<>': 'ne',
    }
    for token, token_type  in simple_tokens.items():
        expected = [{'type': token_type, 'value': token}]
        yield tester.assert_tokens, token, expected

    string_tokens = ['and', 'between', 'in', 'or', 'not']
    for token in string_tokens:
        expected = [{'type': token, 'value': token}]
        yield tester.assert_tokens, token, expected

        expected = [{'type': token, 'value': token.upper()}]
        yield tester.assert_tokens, token.upper(), expected

        expected = [{'type': token, 'value': token.capitalize()}]
        yield tester.assert_tokens, token.capitalize(), expected


def test_lexer_error():
    cases = {
        "'": "'\n^",
        '"': '"\n^',
        '-': '-\n^',
        '1e-': '1e-\n  ^',
        '1ex': '1ex\n  ^',
        '1.': '1.\n ^',
        '1.x': '1.x\n  ^',
        '&': '&\n^',
        '|': '|\n^',
        'b"': 'b"\n ^',
        'b"&"': 'b"&"\n^',
        # Invalid padding
        'b"898989;;"': 'b"898989;;"\n^',
    }

    tester = LexTester()
    yield tester.assert_empty_error, ''

    for expression, error_part in cases.items():
        yield tester.assert_lex_error, expression, error_part


class LexTester(object):
    def __init__(self):
        self.lexer = Lexer()

    def assert_tokens(self, expression, expected):
        actual = self.lexer.tokenize(expression)
        simple_tokens = [
            {'type': t['type'], 'value': t['value']} for t in actual
        ]
        assert_equal(simple_tokens.pop()['type'], 'eof')
        assert_equal(simple_tokens, expected)

    def assert_lex_error(self, expression, error_part):
        try:
            list(self.lexer.tokenize(expression))
            raise AssertionError(
                'LexerError not raised for expression: %s' % expression
            )
        except LexerError as e:
            assert_in(error_part, str(e))

    def assert_empty_error(self, expression):
        with assert_raises(EmptyExpressionError):
            list(self.lexer.tokenize(expression))
