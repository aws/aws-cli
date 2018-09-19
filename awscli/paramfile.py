# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import logging
import os
import copy

from awscli.compat import six

from awscli.compat import compat_open
from awscli.argprocess import ParamError


logger = logging.getLogger(__name__)


class ResourceLoadingError(Exception):
    pass


def register_uri_param_handler(session, **kwargs):
    prefix_map = copy.deepcopy(LOCAL_PREFIX_MAP)
    handler = URIArgumentHandler(prefix_map)
    session.register('load-cli-arg', handler)


class URIArgumentHandler(object):
    def __init__(self, prefixes):
        self._prefixes = prefixes

    def __call__(self, event_name, param, value, **kwargs):
        """Handler that supports param values from local files."""
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
        try:
            return get_paramfile(value, self._prefixes)
        except ResourceLoadingError as e:
            raise ParamError(param.cli_name, six.text_type(e))


def get_paramfile(path, cases):
    """Load parameter based on a resource URI.

    It is possible to pass parameters to operations by referring
    to files or URI's.  If such a reference is detected, this
    function attempts to retrieve the data from the file or URI
    and returns it.  If there are any errors or if the ``path``
    does not appear to refer to a file or URI, a ``None`` is
    returned.

    :type path: str
    :param path: The resource URI, e.g. file://foo.txt.  This value
        may also be a non resource URI, in which case ``None`` is returned.

    :type cases: dict
    :param cases: A dictionary of URI prefixes to function mappings
        that a parameter is checked against.

    :return: The loaded value associated with the resource URI.
        If the provided ``path`` is not a resource URI, then a
        value of ``None`` is returned.

    """
    data = None
    if isinstance(path, six.string_types):
        for prefix, function_spec in cases.items():
            if path.startswith(prefix):
                function, kwargs = function_spec
                data = function(prefix, path, **kwargs)
    return data


def get_file(prefix, path, mode):
    file_path = os.path.expandvars(os.path.expanduser(path[len(prefix):]))
    try:
        with compat_open(file_path, mode) as f:
            return f.read()
    except UnicodeDecodeError:
        raise ResourceLoadingError(
            'Unable to load paramfile (%s), text contents could '
            'not be decoded.  If this is a binary file, please use the '
            'fileb:// prefix instead of the file:// prefix.' % file_path)
    except (OSError, IOError) as e:
        raise ResourceLoadingError('Unable to load paramfile %s: %s' % (
            path, e))


LOCAL_PREFIX_MAP = {
    'file://': (get_file, {'mode': 'r'}),
    'fileb://': (get_file, {'mode': 'rb'}),
}
