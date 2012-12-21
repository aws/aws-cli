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


class BotoCoreError(Exception):
    """
    The base exception class for BotoCore exceptions.

    :ivar msg: The descriptive message associated with the error.
    """
    fmt = 'An unspecified error occured'

    def __init__(self, **kwargs):
        msg = self.fmt.format(**kwargs)
        Exception.__init__(self, msg)
        self.kwargs = kwargs


class DataNotFoundError(BotoCoreError):
    """
    The data associated with a particular path could not be loaded.

    :ivar path: The data path that the user attempted to load.
    """
    fmt = 'Unable to load data for: {data_path}'


class NoCredentials(BotoCoreError):
    """
    No credentials could be found.
    """


class ProfileNotFound(BotoCoreError):
    """
    The specified configuration profile was not found in the
    configuration file.

    :ivar profile: The name of the profile the user attempted to load.
    """
    fmt = 'The config profile ({profile}) could not be found'


class ConfigParseError(BotoCoreError):
    """
    The configuration file could not be parsed.

    :ivar path: The path to the configuration file.
    """
    fmt = 'Unable to parse config file: {path}'


class ConfigNotFound(BotoCoreError):
    """
    The specified configuration file could not be found.

    :ivar path: The path to the configuration file.
    """
    fmt = 'The specified config file ({path}) could not be found.'


class ValidationError(BotoCoreError):
    """
    An exception occurred validating parameters.

    :ivar value: The value that was being validated.
    :ivar type_name: The name of the underlying type.
    """
    fmt = 'Unable to convert value ({value}) to type {type_name}'


class RangeError(BotoCoreError):
    """
    A parameter value was out of the valid range.

    :ivar value: The value that was being checked.
    :ivar min_value: The specified minimum value.
    :ivar max_value: The specified maximum value.
    """
    fmt = 'Value out of range: {min_value} <= {value} <= {max_value}'


class UnknownServiceStyle(BotoCoreError):
    """
    Unknown style of service invocation.

    :ivar service_style: The style requested.
    """
    fmt = 'The service style ({service_style}) is not understood.'
