# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class NoCredentialsError(BotoCoreError):
    """
    No credentials could be found
    """
    fmt = 'Unable to locate credentials'


class NoRegionError(BotoCoreError):
    """
    No region was specified

    :ivar env_var: The name of the environment variable to use to
        specify the default region.
    """
    fmt = 'You must specify a region or set the {env_var} environment variable.'


class UnknownSignatureVersionError(BotoCoreError):
    """
    Requested Signature Version is not known.

    :ivar signature_version: The name of the requested signature version.
    """
    fmt = 'Unknown Signature Version: {signature_version}.'


class ServiceNotInRegionError(BotoCoreError):
    """
    The service is not available in requested region.

    :ivar service_name: The name of the service.
    :ivar region_name: The name of the region.
    """
    fmt = 'Service {service_name} not available in region {region_name}'


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


class MissingParametersError(BotoCoreError):
    """
    One or more required parameters were not supplied.

    :ivar missing: str
    :ivar missing: The names of the missing parameters
    """
    fmt = 'The following required parameters are missing: {missing}'


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


class PaginationError(BotoCoreError):
    fmt = 'Error during pagination: {message}'
