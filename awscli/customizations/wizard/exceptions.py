# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from traceback import format_tb


class BaseWizardException(Exception):
    pass


class InvalidDataTypeConversionException(BaseWizardException):
    MSG_FORMAT = 'Invalid value {value} for datatype {datatype}'

    def __init__(self, value, datatype):
        message = self.MSG_FORMAT.format(value=value, datatype=datatype)
        super().__init__(message)


class InvalidChoiceException(Exception):
    pass


class UnableToRunWizardError(Exception):
    pass


class UnexpectedWizardException(Exception):
    MSG_FORMAT = (
        'Encountered unexpected exception inside of wizard:\n\n'
        'Traceback:\n{original_tb}'
        '{original_exception_cls}: {original_exception}'
    )

    def __init__(self, original_exception):
        self.original_exception = original_exception
        message = self.MSG_FORMAT.format(
            original_tb=''.join(format_tb(original_exception.__traceback__)),
            original_exception_cls=self.original_exception.__class__.__name__,
            original_exception=self.original_exception
        )
        super().__init__(message)
