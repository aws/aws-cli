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

from awscli.compat import six
import awscli.customizations.dynamodb.ast as ast
from .exceptions import (
    EmptyExpressionError, UnexpectedTokenError, UnknownExpressionError,
    InvalidLiteralValueError,
)

from .lexer import Lexer
from .types import Binary


class Parser(object):
    COMPARATORS = ['eq', 'ne', 'lt', 'lte', 'gt', 'gte']

    def __init__(self, lexer=None):
        self._lexer = lexer
        if lexer is None:
            self._lexer = Lexer()
        self._position = 0
        self._tokens = []
        self._current = None
        self._expression = None

    def parse(self, expression):
        self._position = 0
        self._expression = expression
        self._tokens = list(self._lexer.tokenize(expression))
        self._current = self._tokens[0]

        parsed = self._parse_expression()

        if not self._match('eof'):
            raise UnexpectedTokenError(
                token=self._current,
                expression=self._expression,
                expected_type='eof',
            )
        return parsed

    def _parse_expression(self):
        if self._match('eof') or self._current is None:
            raise EmptyExpressionError()

        expression = self._parse_simple_expression()

        identifier_types = [
            'identifier', 'path_identifier', 'index_identifier'
        ]
        if expression['type'] in identifier_types and self._match('comma'):
            self._advance()
            return self._parse_sequence(expression)
        else:
            return self._parse_and_or(expression)

    def _parse_and_or(self, left_expression):
        expression = left_expression

        while self._match(['and', 'or']):
            conjunction_type = self._current['type']
            self._advance()
            right = self._parse_simple_expression()
            if conjunction_type == 'and':
                expression = ast.and_expression(expression, right)
            else:
                expression = ast.or_expression(expression, right)

        return expression

    def _parse_simple_expression(self):
        if self._match('lparen'):
            return self._parse_subexpression()
        if self._match('not'):
            return self._parse_not_expression()
        return self._parse_condition_expression()

    def _parse_subexpression(self):
        self._advance_if_match('lparen')
        expression = self._parse_expression()
        self._advance_if_match('rparen')
        return ast.subexpression(expression)

    def _parse_not_expression(self):
        self._advance_if_match('not')
        expression = self._parse_simple_expression()
        return ast.not_expression(expression)

    def _parse_condition_expression(self):
        # function names cannot be literals or complex identifiers, so there
        # is no need to parse the name ahead of time
        if self._match_next('lparen'):
            return self._parse_function()

        operand_types = [
            'literal', 'identifier', 'unquoted_identifier',
            'lbracket', 'lbrace',
        ]
        if not self._match(operand_types):
            raise UnknownExpressionError(
                start_token=self._current,
                expression=self._expression,
            )

        left = self._parse_operand()

        if self._match('in'):
            return self._parse_in_expression(left)
        elif self._match('between'):
            return self._parse_between_expression(left)
        elif self._match(self.COMPARATORS):
            return self._parse_comparison_expression(left)

        return left

    def _parse_function(self):
        function_name = self._current.get('value')
        self._advance_if_match(['identifier', 'unquoted_identifier'])
        self._advance_if_match('lparen')
        arguments = self._parse_sequence()["children"]
        self._advance_if_match('rparen')
        return ast.function_expression(function_name, arguments)

    def _parse_in_expression(self, left):
        self._advance_if_match('in')
        self._advance_if_match('lparen')
        right = self._parse_sequence()
        self._advance_if_match('rparen')
        return ast.in_expression(left, right)

    def _parse_between_expression(self, left):
        self._advance_if_match('between')
        middle = self._parse_operand()
        self._advance_if_match('and')
        right = self._parse_operand()
        return ast.between_expression(left, middle, right)

    def _parse_comparison_expression(self, left):
        comparator = self._current['type']
        self._advance_if_match(self.COMPARATORS)
        right = self._parse_operand()
        return ast.comparison_expression(comparator, left, right)

    def _parse_sequence(self, first_element=None):
        elements = []
        if first_element:
            elements = [first_element]

        while True:
            elements.append(self._parse_operand())
            if not self._match('comma'):
                break
            self._advance()
        return ast.sequence(elements)

    def _parse_operand(self):
        if self._match(['literal', 'lbracket', 'lbrace']):
            return self._parse_literal()
        elif self._match(['identifier', 'unquoted_identifier']):
            return self._parse_path_identifier()
        else:
            raise UnexpectedTokenError(
                token=self._current,
                expression=self._expression,
                expected_type=[
                    'literal', 'lbracket', 'lbrace', 'identifier',
                    'unquoted_identiifer',
                ],
            )

    def _parse_path_identifier(self):
        identifier = self._parse_identifier()

        while self._match('dot'):
            self._advance()
            right = self._parse_identifier()
            identifier = ast.path_identifier(identifier, right)

        return identifier

    def _parse_identifier(self):
        identifier = ast.identifier(self._current['value'])
        self._advance()

        if self._match('lbracket'):
            self._advance()

            index = self._parse_literal()
            val = index['value']
            if not isinstance(val, Decimal) or val.to_integral_value() != val:
                raise InvalidLiteralValueError(
                    token=self._current,
                    expression=self._expression,
                    message='List indices must be whole numbers.',
                )
            self._advance_if_match('rbracket')
            identifier = ast.index_identifier(
                name=identifier, index=index['value']
            )

        return identifier

    def _parse_literal(self):
        if self._match('literal'):
            value = self._current['value']
            self._advance()
        elif self._match('lbracket'):
            self._advance()
            if self._match('rbracket'):
                value = []
            else:
                value = self._parse_literal_sequence()
            self._advance_if_match('rbracket')
        elif self._match('lbrace'):
            self._advance()
            if self._match_next('colon') or self._match('rbrace'):
                value = self._parse_literal_map()
            else:
                value = self._parse_literal_set()
            self._advance_if_match('rbrace')
        else:
            raise UnexpectedTokenError(
                token=self._current,
                expression=self._expression,
                expected_type=['literal', 'lbracket', 'lbrace'],
            )
        return ast.literal(value)

    def _parse_literal_set(self):
        valid_types = (six.string_types, Binary, Decimal)
        first_type = type(self._current['value'])

        elements = set()
        while True:
            element = self._current
            if not self._match('literal'):
                raise UnexpectedTokenError(
                    token=self._current,
                    expression=self._expression,
                    expected_type='literal',
                )
            if not isinstance(element['value'], valid_types):
                message = (
                    'Sets may only contain numbers, strings, or bytes, '
                    'but literal of type `%s` was found'
                )
                raise InvalidLiteralValueError(
                    token=self._current,
                    expression=self._expression,
                    message=message % type(element['type']),
                )
            if not isinstance(element['value'], first_type):
                message = (
                    'Set values must all be of the same type. First type was '
                    '`%s`, but found value of type `%s`'
                )
                raise InvalidLiteralValueError(
                    token=self._current,
                    expression=self._expression,
                    message=message % (first_type, type(element['type'])),
                )

            elements.add(self._current['value'])
            self._advance()
            if not self._match('comma'):
                break
            self._advance()
        return elements

    def _parse_literal_map(self):
        if self._match('rbrace'):
            return {}

        elements = {}
        while True:
            key = self._current['value']
            if not isinstance(key, six.string_types):
                raise InvalidLiteralValueError(
                    token=self._current,
                    expression=self._expression,
                    message=(
                        'Keys must be of type `str`, found `%s`' % type(key)
                    )
                )
            self._advance_if_match('literal')
            self._advance_if_match('colon')
            value = self._parse_literal()['value']
            elements[key] = value
            if not self._match('comma'):
                break
            self._advance()
        return elements

    def _parse_literal_sequence(self):
        elements = []
        while True:
            elements.append(self._parse_literal()['value'])
            if not self._match('comma'):
                break
            self._advance()
        return elements

    def _advance(self):
        if self._position == len(self._tokens) - 1:
            self._current = None
        else:
            self._position += 1
            self._current = self._tokens[self._position]

    def _peek(self):
        if self._position == len(self._tokens) - 1:
            return None
        return self._tokens[self._position + 1]

    def _match(self, expected_type):
        return self._do_match(self._current, expected_type)

    def _match_next(self, expected_type):
        return self._do_match(self._peek(), expected_type)

    def _do_match(self, token, expected_type):
        if token is None:
            return False
        if isinstance(expected_type, list):
            return any(token['type'] == t for t in expected_type)
        return token['type'] == expected_type

    def _advance_if_match(self, token_type):
        if self._match(token_type):
            self._advance()
        else:
            raise UnexpectedTokenError(
                token=self._current,
                expected_type=token_type,
                expression=self._expression,
            )
