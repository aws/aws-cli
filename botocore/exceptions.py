# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# Copyright 2012 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
from .base import get_data


class BotoCoreException(Exception):
    """
    The base exception class for BotoCore exceptions.

    The main job of this class is to lookup the format string
    for the exception in the message database.  This format
    string will use the standard Python formatting using named
    variables in the format string.  It is then expected that
    the required variable data will be passed as keyword parameters
    to the class constructor.
    """

    @classmethod
    def get_message_format(cls):
        return get_data('messages/%s' % cls.__name__)

    def __init__(self, message, **params):
        Exception.__init__(self, message)
        self.params = params

    def __str__(self):
        return self.get_message_format().format(**self.params)


class ValidationException(BotoCoreException):

    pass


class RangeException(BotoCoreException):

    pass
