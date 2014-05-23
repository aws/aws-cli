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
import logging
import six

from botocore.compat import OrderedDict, json

from awscli import utils
from awscli import SCALAR_TYPES, COMPLEX_TYPES
from awscli.paramfile import get_paramfile, ResourceLoadingError


LOG = logging.getLogger('awscli.argprocess')


class ParamError(Exception):
    def __init__(self, param, message):
        full_message = ("Error parsing parameter '%s': %s" %
                        (param.cli_name, message))
        super(ParamError, self).__init__(full_message)
        self.param = param
        self.message = message


class ParamSyntaxError(Exception):
    pass


class ParamUnknownKeyError(Exception):
    def __init__(self, param, key, valid_keys):
        valid_keys = ', '.join(valid_keys)
        full_message = (
            "Unknown key '%s' for parameter %s, valid choices "
            "are: %s" % (key, param.cli_name, valid_keys))
        super(ParamUnknownKeyError, self).__init__(full_message)


def unpack_argument(session, service_name, operation_name, param, value):
    """
    Unpack an argument's value from the commandline. This is part one of a two
    step process in handling commandline arguments. Emits the load-cli-arg
    event with service, operation, and parameter names. Example::

        load-cli-arg.ec2.describe-instances.foo

    """
    param_name = getattr(param, 'name', 'anonymous')

    value_override = session.emit_first_non_none_response(
        'load-cli-arg.%s.%s.%s' % (service_name,
                                   operation_name,
                                   param_name),
        param=param, value=value, service_name=service_name,
        operation_name=operation_name)

    if value_override is not None:
        value = value_override

    return value


def uri_param(param, value, **kwargs):
    """Handler that supports param values from URIs.
    """
    # Some params have a 'no_paramfile' attribute in their JSON
    # models which means that we should not allow any uri based params
    # for this argument.
    if getattr(param, 'no_paramfile', False):
        return
    else:
        return _check_for_uri_param(param, value)


def _check_for_uri_param(param, value):
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    try:
        return get_paramfile(value)
    except ResourceLoadingError as e:
        raise ParamError(param, six.text_type(e))


def detect_shape_structure(param):
    if param.type in SCALAR_TYPES:
        return 'scalar'
    elif param.type == 'structure':
        sub_types = [detect_shape_structure(p)
                     for p in param.members]
        # We're distinguishing between structure(scalar)
        # and structure(scalars), because for the case of
        # a single scalar in a structure we can simplify
        # more than a structure(scalars).
        if len(sub_types) == 1 and all(p == 'scalar' for p in sub_types):
            return 'structure(scalar)'
        elif len(sub_types) > 1 and all(p == 'scalar' for p in sub_types):
            return 'structure(scalars)'
        else:
            return 'structure(%s)' % ', '.join(sorted(set(sub_types)))
    elif param.type == 'list':
        return 'list-%s' % detect_shape_structure(param.members)
    elif param.type == 'map':
        if param.members.type in SCALAR_TYPES:
            return 'map-scalar'
        else:
            return 'map-%s' % detect_shape_structure(param.members)


class ParamShorthand(object):

    # To add support for a new shape:
    #
    #  * Add it to SHORTHAND_SHAPES below, key is the shape structure
    #    value is the name of the method to call.
    #  * Implement parse method.
    #  * Implement _doc_<parse_method_name>.  This is used to generate
    #    the docs for this shorthand syntax.

    SHORTHAND_SHAPES = {
        'structure(scalars)': '_key_value_parse',
        'structure(scalar)': '_special_key_value_parse',
        'map-scalar': '_key_value_parse',
        'list-structure(scalar)': '_list_scalar_parse',
        'list-structure(scalars)': '_list_key_value_parse',
        'list-structure(list-scalar, scalar)': '_list_scalar_list_parse',
    }

    def __init__(self):
        pass

    def __call__(self, param, value, **kwargs):
        """Attempt to parse shorthand syntax for values.

        This is intended to be hooked up as an event handler (hence the
        **kwargs).  Given ``param`` object and its string ``value``,
        figure out if we can parse it.  If we can parse it, we return
        the parsed value (typically some sort of python dict).

        :type param: :class:`botocore.parameters.Parameter`
        :param param: The parameter object (includes various metadata
            about the parameter).

        :type value: str
        :param value: The value for the parameter type on the command
            line, e.g ``--foo this_value``, value would be ``"this_value"``.

        :returns: If we can parse the value we return the parsed value.
            If it looks like JSON, we return None (which tells the event
            emitter to use the default ``unpack_cli_arg`` provided that
            no other event handlers can parsed the value).  If we
            run into an error parsing the value, a ``ParamError`` will
            be raised.

        """
        parse_method = self.get_parse_method_for_param(param, value)
        if parse_method is None:
            return
        else:
            try:
                LOG.debug("Using %s for param %s", parse_method, param)
                parsed = getattr(self, parse_method)(param, value)
            except ParamSyntaxError as e:
                doc_fn = self._get_example_fn(param)
                # Try to give them a helpful error message.
                if doc_fn is None:
                    raise e
                else:
                    raise ParamError(param, "should be: %s" % doc_fn(param))
            return parsed

    def get_parse_method_for_param(self, param, value=None):
        # We first need to make sure this is a parameter that qualifies
        # for simplification.  The first short-circuit case is if it looks
        # like json we immediately return.
        if isinstance(value, list):
            check_val = value[0]
        else:
            check_val = value
        if isinstance(check_val, six.string_types) and check_val.strip().startswith(
                ('[', '{')):
            LOG.debug("Param %s looks like JSON, not considered for "
                      "param shorthand.", param.py_name)
            return
        structure = detect_shape_structure(param)
        # If this looks like shorthand then we log the detected structure
        # to help with debugging why the shorthand may not work, for
        # example list-structure(list-structure(scalars))
        LOG.debug('Detected structure: {0}'.format(structure))
        parse_method = self.SHORTHAND_SHAPES.get(structure)
        return parse_method

    def _get_example_fn(self, param):
        doc_fn = None
        shape_structure = detect_shape_structure(param)
        method = self.SHORTHAND_SHAPES.get(shape_structure)
        if method:
            doc_fn = getattr(self, '_docs' + method, None)
        return doc_fn

    def add_example_fn(self, arg_name, help_command, **kwargs):
        """
        Adds a callable to the ``example_fn`` attribute of the parameter
        if the parameter type is supported by shorthand syntax.  This
        callable should return a string containing just the example and
        not any of the ReST formatting that might be required in the docs.
        """
        argument = help_command.arg_table[arg_name]
        if hasattr(argument, 'argument_object') and argument.argument_object:
            param = argument.argument_object
            LOG.debug('Adding example fn for: %s' % param.name)
            doc_fn = self._get_example_fn(param)
            param.example_fn = doc_fn

    def _list_scalar_list_parse(self, param, value):
        # Think something like ec2.DescribeInstances.Filters.
        # We're looking for key=val1,val2,val3,key2=val1,val2.
        args = {}
        for arg in param.members.members:
            # Arg name -> arg object lookup
            args[arg.name] = arg
        parsed = []
        for v in value:
            parts = self._split_on_commas(v)
            current_parsed = {}
            current_key = None
            for part in parts:
                current = part.split('=', 1)
                if len(current) == 2:
                    # This is a key/value pair.
                    current_key = current[0].strip()
                    if current_key not in args:
                        raise ParamUnknownKeyError(param, current_key,
                                                   args.keys())
                    current_value = unpack_scalar_cli_arg(args[current_key],
                                                          current[1].strip())
                    if args[current_key].type == 'list':
                        current_parsed[current_key] = current_value.split(',')
                    else:
                        current_parsed[current_key] = current_value
                elif current_key is not None:
                    # This is a value which we associate with the current_key,
                    # so key1=val1,val2
                    #               ^
                    #               |
                    #             val2 is associated with key1.
                    current_value = unpack_scalar_cli_arg(args[current_key],
                                                          current[0])
                    current_parsed[current_key].append(current_value)
                else:
                    raise ParamSyntaxError(part)
            parsed.append(current_parsed)
        return parsed

    def _list_scalar_parse(self, param, value):
        single_param = param.members.members[0]
        parsed = []
        # We know that value is a list in this case.
        for v in value:
            parsed.append({single_param.name: v})
        return parsed

    def _list_key_value_parse(self, param, value):
        # param is a list param.
        # param.member is the struct param.
        struct_param = param.members
        parsed = []
        for v in value:
            single_struct_param = self._key_value_parse(struct_param, v)
            parsed.append(single_struct_param)
        return parsed

    def _special_key_value_parse(self, param, value):
        # This is a special key value parse that can do the normal
        # key=value parsing, *but* supports a few additional conveniences
        # when working with a structure with a single element.
        # Precondition: param is a shape of structure(scalar)
        if len(param.members) == 1 and param.members[0].name == 'Value' and \
                '=' not in value:
            # We have an even shorter shorthand syntax for structure
            # of scalars of a single element with a member name of
            # 'Value'.
            return {'Value': value}
        else:
            return self._key_value_parse(param, value)

    def _key_value_parse(self, param, value):
        # The expected structure is:
        #  key=value,key2=value
        # that is, csv key value pairs, where the key and values
        # are separated by '='.  All of this should be whitespace
        # insensitive.
        parsed = OrderedDict()
        parts = self._split_on_commas(value)
        valid_names = self._create_name_to_params(param)
        for part in parts:
            try:
                key, value = part.split('=', 1)
            except ValueError:
                raise ParamSyntaxError(part)
            key = key.strip()
            value = value.strip()
            if valid_names and key not in valid_names:
                raise ParamUnknownKeyError(param, key, valid_names)
            if valid_names:
                sub_param = valid_names[key]
                if sub_param is not None:
                    value = unpack_scalar_cli_arg(sub_param, value)
            parsed[key] = value
        return parsed

    def _create_name_to_params(self, param):
        if param.type == 'structure':
            return dict([(p.name, p) for p in param.members])
        elif param.type == 'map' and hasattr(param.keys, 'enum'):
            return dict([(v, None) for v in param.keys.enum])

    def _docs_list_scalar_list_parse(self, param):
        s = 'Key value pairs, where values are separated by commas.\n'
        s += '%s ' % param.cli_name
        inner_params = param.members.members
        scalar_params = [p for p in inner_params if p.type in SCALAR_TYPES]
        list_params = [p for p in inner_params if p.type == 'list']
        for param in scalar_params:
            s += '%s=%s1,' % (param.name, param.type)
        for param in list_params[:-1]:
            param_type = param.members.type
            s += '%s=%s1,%s2,' % (param.name, param_type, param_type)
        last_param = list_params[-1]
        param_type = last_param.members.type
        s += '%s=%s1,%s2' % (last_param.name, param_type, param_type)
        return s

    def _docs_list_scalar_parse(self, param):
        name = param.members.members[0].name
        return '%s %s1 %s2 %s3' % (param.cli_name, name, name, name)

    def _docs_list_key_value_parse(self, param):
        s = "Key value pairs, with multiple values separated by a space.\n"
        s += '%s ' % param.cli_name
        s += ','.join(['%s=%s' % (sub_param.name, sub_param.type)
                       for sub_param in param.members.members])
        return s

    def _docs_special_key_value_parse(self, param):
        if len(param.members) == 1 and param.members[0].name == 'Value':
            # Returning None will indicate that we don't have
            # any examples to generate, and the entire examples section
            # should be skipped for this arg.
            return None
        else:
            return self._docs_key_value_parse(param)

    def _docs_key_value_parse(self, param):
        s = '%s ' % param.cli_name
        if param.type == 'structure':
            s += ','.join(['%s=value' % sub_param.name
                            for sub_param in param.members])
        elif param.type == 'map':
            s += 'key_name=string,key_name2=string'
            if param.keys.type == 'string' and hasattr(param.keys, 'enum'):
                s += '\nWhere valid key names are:\n'
                for value in param.keys.enum:
                    s += '  %s\n' % value
        return s

    def _split_on_commas(self, value):
        try:
            return utils.split_on_commas(value)
        except ValueError as e:
            raise ParamSyntaxError(six.text_type(e))


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
    if parameter.type in SCALAR_TYPES:
        return unpack_scalar_cli_arg(parameter, value)
    elif parameter.type in COMPLEX_TYPES:
        return unpack_complex_cli_arg(parameter, value)
    else:
        return six.text_type(value)


def unpack_complex_cli_arg(parameter, value):
    if parameter.type == 'structure' or parameter.type == 'map':
        if value.lstrip()[0] == '{':
            try:
                return json.loads(value, object_pairs_hook=OrderedDict)
            except ValueError as e:
                raise ParamError(
                    parameter, "Invalid JSON: %s\nJSON received: %s"
                    % (e, value))
        raise ParamError(parameter, "Invalid JSON:\n%s" % value)
    elif parameter.type == 'list':
        if isinstance(value, six.string_types):
            if value.lstrip()[0] == '[':
                return json.loads(value, object_pairs_hook=OrderedDict)
        elif isinstance(value, list) and len(value) == 1:
            single_value = value[0].strip()
            if single_value and single_value[0] == '[':
                return json.loads(value[0], object_pairs_hook=OrderedDict)
        try:
            return [unpack_cli_arg(parameter.members, v) for v in value]
        except ParamError as e:
            # The list params don't have a name/cli_name attached to them
            # so they will have bad error messages.  We're going to
            # attach the parent parameter to this error message to provide
            # a more helpful error message.
            raise ParamError(parameter, e.message)


def unpack_scalar_cli_arg(parameter, value):
    if parameter.type == 'integer' or parameter.type == 'long':
        return int(value)
    elif parameter.type == 'float' or parameter.type == 'double':
        # TODO: losing precision on double types
        return float(value)
    elif parameter.type == 'blob' and parameter.payload and parameter.streaming:
        file_path = os.path.expandvars(value)
        file_path = os.path.expanduser(file_path)
        if not os.path.isfile(file_path):
            msg = 'Blob values must be a path to a file.'
            raise ParamError(parameter, msg)
        return open(file_path, 'rb')
    elif parameter.type == 'boolean':
        if isinstance(value, six.string_types) and value.lower() == 'false':
            return False
        return bool(value)
    else:
        return value
