# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import _awscrt


def from_code(code):
    """Given an AWS Common Runtime error code, return an exception.

    Returns a common Python exception type, if it's appropriate.
    For example, `code=1` aka `AWS_ERROR_OOM` will result in `MemoryError`.
    Otherwise, an :class:`AwsCrtError` is returned.

    Args:
        code (int): error code.

    Returns:
        BaseException:
    """
    builtin = _awscrt.get_corresponding_builtin_exception(code)
    if builtin:
        return builtin()

    name = _awscrt.get_error_name(code)
    msg = _awscrt.get_error_message(code)
    return AwsCrtError(code=code, name=name, message=msg)


class AwsCrtError(Exception):
    """
    Base exception class for AWS Common Runtime exceptions.

    Args:
        code (int): Int value of error.
        name (str): Name of error.
        message (str): Message about error.

    Attributes:
        code (int): Int value of error.
        name (str): Name of error.
        message (str): Message about error.
    """

    def __init__(self, code, name, message):
        self.code = code
        self.name = name
        self.message = message

    def __repr__(self):
        return "{0}(name={1}, message={2}, code={3})".format(
            self.__class__.__name__, repr(self.name), repr(self.message), self.code)

    def __str__(self):
        return "{}: {}".format(self.name, self.message)
