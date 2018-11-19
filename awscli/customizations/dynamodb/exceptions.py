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


class DDBError(Exception):
    pass


class EmptyExpressionError(DDBError):
    def __init__(self):
        super(EmptyExpressionError, self).__init__(
            "Expressions must not be empty"
        )


class LexerError(DDBError):
    def __init__(self, expression, position, message):
        underline = ' ' * position + '^'
        error_message = '%s\n%s\n%s' % (message, expression, underline)
        super(LexerError, self).__init__(error_message)
