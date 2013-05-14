# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Module for processing CLI args."""
import os
import json

import six


SCALAR_TYPES = set([
    'string', 'float', 'integer', 'long', 'boolean', 'double',
    'blob', 'timestamp'
])
COMPLEX_TYPES = set(['structure', 'map', 'list'])


def detect_shape_structure(param):
    if param.type in SCALAR_TYPES:
        return 'scalar'
    elif param.type == 'structure':
        sub_types = [detect_shape_structure(p)
                     for p in param.members]
        if all(p in SCALAR_TYPES for p in sub_types):
            return 'structure(scalar)'
        else:
            return 'structure(%s)' % ', '.join(sorted(set(sub_types)))
    elif param.type == 'list':
        return 'list-%s' % detect_shape_structure(param.members)
    elif param.type == 'map':
        if param.members.type in SCALAR_TYPES:
            return 'map-scalar'


class ParamSimplifier(object):
    def __init__(self):
        pass

    def __call__(self, param, value, **kwargs):
        pass



def unpack_cli_arg(parameter, value):
    """
    Parses and unpacks the encoded string command line parameter
    and returns native Python data structures that can be passed
    to the Operation.

    :type parameter: :class:`botocore.parameter.Parameter`
    :param parameter: The parameter object containing metadata about
        the parameter.

    :param value: The value of the parameter.  This can be a number of
        different python types (str, list, etc).  This is the value as
        it's specified on the command line.

    :return: The "unpacked" argument than can be sent to the `Operation`
        object in python.
    """
    if parameter.type == 'integer':
        return int(value)
    elif parameter.type == 'float' or parameter.type == 'double':
        # TODO: losing precision on double types
        return float(value)
    elif parameter.type == 'structure' or parameter.type == 'map':
        if value[0] == '{':
            d = json.loads(value)
        else:
            msg = 'Structure option value must be JSON or path to file.'
            raise ValueError(msg)
        return d
    elif parameter.type == 'list':
        if isinstance(value, six.string_types):
            if value[0] == '[':
                return json.loads(value)
        elif isinstance(value, list) and len(value) == 1:
            if value[0][0] == '[':
                return json.loads(value[0])
        return [unpack_cli_arg(parameter.members, v) for v in value]
    elif parameter.type == 'blob' and parameter.payload and parameter.streaming:
        file_path = os.path.expandvars(value)
        file_path = os.path.expanduser(file_path)
        if not os.path.isfile(file_path):
            msg = 'Blob values must be a path to a file.'
            raise ValueError(msg)
        return open(file_path, 'rb')
    else:
        return str(value)
