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
from awscli.customizations.exceptions import ParamValidationError


class DDBError(Exception):
    pass


class EmptyExpressionError(DDBError, ParamValidationError):
    def __init__(self):
        super(EmptyExpressionError, self).__init__(
            "Expressions must not be empty"
        )


class LexerError(DDBError, ParamValidationError):
    def __init__(self, expression, position, message):
        underline = ' ' * position + '^'
        error_message = '%s\n%s\n%s' % (message, expression, underline)
        super(LexerError, self).__init__(error_message)


class ParserError(DDBError, ParamValidationError):
    pass


class UnexpectedTokenError(ParserError):
    def __init__(self, token, expected_type, expression):
        message = (
            "Unexpected token `{value}` of type `{token_type}`. "
            "Expected type: {expected_type}\n"
            "{expression}\n{underline}"
        )
        if token is None:
            token = {
                'type': 'None', 'value': None,
                'start': len(expression), 'end': len(expression),
            }
        token_length = token['end'] - token['start']
        message = message.format(
            value=token['value'],
            token_type=token['type'],
            expected_type=expected_type,
            expression=expression,
            underline=' ' * token['start'] + '^' * (max(token_length, 1)),
        )
        self.token = token
        self.expression = expression
        self.expected_type = expected_type
        super(UnexpectedTokenError, self).__init__(message)


class InvalidLiteralValueError(ParserError):
    def __init__(self, token, message, expression):
        error_message = (
            'Invalid token value: {message}\n'
            '{expression}\n{underline}\n'
        )
        token_length = token['end'] - token['start']
        underline = ' ' * token['start'] + '^' * (max(token_length, 1))
        error_message = error_message.format(
            message=message,
            expression=expression,
            underline=underline,
        )
        self.token = token
        self.expression = expression
        super(InvalidLiteralValueError, self).__init__(error_message)


class UnknownExpressionError(ParserError):
    def __init__(self, start_token, expression):
        message = (
            'Unknown expression type starting at token `{token_value}`\n'
            '{expression}\n{underline}'
        )
        token_length = start_token['end'] - start_token['start']
        underline = ' ' * start_token['start'] + '^' * (max(token_length, 1))
        message = message.format(
            token_value=start_token['value'],
            expression=expression,
            underline=underline,
        )
        self.start_token = start_token
        self.expression = expression
        super(UnknownExpressionError, self).__init__(message)
