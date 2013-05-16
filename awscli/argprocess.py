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
import csv
import logging

import six


SCALAR_TYPES = set([
    'string', 'float', 'integer', 'long', 'boolean', 'double',
    'blob', 'timestamp'
])
COMPLEX_TYPES = set(['structure', 'map', 'list'])
LOG = logging.getLogger('awscli.argprocess')


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


class ParamShorthand(object):

    SHORTHAND_SHAPES = {
        'structure(scalar)': '_key_value_parse',
        'map-scalar': '_key_value_parse',
        'list-structure(scalar)': '_list_scalar_parse',
        'list-structure(list-scalar, scalar)': '_list_scalar_list_parse',
    }

    def __init__(self):
        pass

    def add_docs(self, operation_doc, **kwargs):
        pass

    def __call__(self, param, value, **kwargs):
        # We first need to make sure this is a parameter that qualifies
        # for simplification.  The first short-circuit case is if it looks
        # like json we immediately return.
        if isinstance(value, list):
            check_val = value[0]
        else:
            check_val = value
        if isinstance(check_val, str) and check_val.startswith(('[', '{')):
            LOG.debug("Param %s looks like JSON, not considered for "
                      "param shorthand.", param.py_name)
            return
        structure = detect_shape_structure(param)
        parse_method = self.SHORTHAND_SHAPES.get(structure)
        if parse_method is None:
            return
        else:
            parsed = getattr(self, parse_method)(param, value)
            return parsed

    def _list_scalar_list_parse(self, param, value):
        # Think something like ec2.DescribeInstances.Filters.
        arg_types = {}
        for arg in param.members.members:
            arg_types[arg.py_name] = arg.type
        parsed = []
        for v in value:
            parts = v.split(',')
            current_parsed = {}
            for part in parts:
                current = part.split(':', 1)
                if len(current) == 2:
                    # This is a key/value pair.
                    current_key = current[0].strip()
                    current_value = current[1].strip()
                    if arg_types[current_key] == 'list':
                        current_parsed[current_key] = [current_value]
                    else:
                        current_parsed[current_key] = current_value
                else:
                    assert len(current) == 1
                    assert arg_types[current_key] == 'list'
                    current_parsed[current_key].append(current[0])
            parsed.append(current_parsed)
        return parsed

    def _list_scalar_parse(self, param, value):
        assert len(param.members.members) == 1
        assert isinstance(value, list)
        single_param = param.members.members[0]
        parsed = []
        # We know that value is a list in this case.
        for v in value:
            parsed.append({single_param.py_name: v})
        return parsed

    def _key_value_parse(self, param, value):
        # The expected structure is:
        #  key=value,key2=value
        # that is, csv key value pairs, where the key and values
        # are separated by ':'.  All of this should be whitespace
        # insensitive.
        parsed = {}
        parts = value.split(',')
        for part in parts:
            key, value = part.split(':')
            parsed[key.strip()] = value.strip()
        return parsed


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
