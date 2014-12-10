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
from awscli.compat import six

from botocore import xform_name
from botocore.compat import OrderedDict, json

from awscli import utils
from awscli import SCALAR_TYPES, COMPLEX_TYPES
from awscli.paramfile import get_paramfile, ResourceLoadingError
from awscli.paramfile import PARAMFILE_DISABLED


LOG = logging.getLogger('awscli.argprocess')


class ParamError(Exception):
    def __init__(self, cli_name, message):
        """

        :type cli_name: string
        :param cli_name: The complete cli argument name,
            e.g. "--foo-bar".  It should include the leading
            hyphens if that's how a user would specify the name.

        :type message: string
        :param message: The error message to display to the user.

        """
        full_message = ("Error parsing parameter '%s': %s" %
                        (cli_name, message))
        super(ParamError, self).__init__(full_message)
        self.cli_name = cli_name
        self.message = message


class ParamSyntaxError(Exception):
    pass


class ParamUnknownKeyError(Exception):
    def __init__(self, key, valid_keys):
        valid_keys = ', '.join(valid_keys)
        full_message = (
            "Unknown key '%s', valid choices "
            "are: %s" % (key, valid_keys))
        super(ParamUnknownKeyError, self).__init__(full_message)


def unpack_argument(session, service_name, operation_name, cli_argument, value):
    """
    Unpack an argument's value from the commandline. This is part one of a two
    step process in handling commandline arguments. Emits the load-cli-arg
    event with service, operation, and parameter names. Example::

        load-cli-arg.ec2.describe-instances.foo

    """
    param_name = getattr(cli_argument, 'name', 'anonymous')

    value_override = session.emit_first_non_none_response(
        'load-cli-arg.%s.%s.%s' % (service_name,
                                   operation_name,
                                   param_name),
        param=cli_argument, value=value, service_name=service_name,
        operation_name=operation_name)

    if value_override is not None:
        value = value_override

    return value


def uri_param(event_name, param, value, **kwargs):
    """Handler that supports param values from URIs.
    """
    cli_argument = param
    qualified_param_name = '.'.join(event_name.split('.')[1:])
    if qualified_param_name in PARAMFILE_DISABLED or \
            getattr(cli_argument, 'no_paramfile', None):
        return
    else:
        return _check_for_uri_param(cli_argument, value)


def _check_for_uri_param(param, value):
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    try:
        return get_paramfile(value)
    except ResourceLoadingError as e:
        raise ParamError(param.cli_name, six.text_type(e))


def detect_shape_structure(param):
    stack = []
    return _detect_shape_structure(param, stack)


def _detect_shape_structure(param, stack):
    if param.name in stack:
        return 'recursive'
    else:
        stack.append(param.name)
    try:
        if param.type_name in SCALAR_TYPES:
            return 'scalar'
        elif param.type_name == 'structure':
            sub_types = [_detect_shape_structure(p, stack)
                        for p in param.members.values()]
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
        elif param.type_name == 'list':
            return 'list-%s' % _detect_shape_structure(param.member, stack)
        elif param.type_name == 'map':
            if param.value.type_name in SCALAR_TYPES:
                return 'map-scalar'
            else:
                return 'map-%s' % _detect_shape_structure(param.value, stack)
    finally:
        stack.pop()


def unpack_cli_arg(cli_argument, value):
    """
    Parses and unpacks the encoded string command line parameter
    and returns native Python data structures that can be passed
    to the Operation.

    :type cli_argument: :class:`awscli.arguments.BaseCLIArgument`
    :param cli_argument: The CLI argument object.

    :param value: The value of the parameter.  This can be a number of
        different python types (str, list, etc).  This is the value as
        it's specified on the command line.

    :return: The "unpacked" argument than can be sent to the `Operation`
        object in python.
    """
    return _unpack_cli_arg(cli_argument.argument_model, value,
                           cli_argument.cli_name)


def _unpack_cli_arg(argument_model, value, cli_name):
    if argument_model.type_name in SCALAR_TYPES:
        return unpack_scalar_cli_arg(
            argument_model, value, cli_name)
    elif argument_model.type_name in COMPLEX_TYPES:
        return _unpack_complex_cli_arg(
            argument_model, value, cli_name)
    else:
        return six.text_type(value)


def _unpack_complex_cli_arg(argument_model, value, cli_name):
    type_name = argument_model.type_name
    if type_name == 'structure' or type_name == 'map':
        if value.lstrip()[0] == '{':
            try:
                return json.loads(value, object_pairs_hook=OrderedDict)
            except ValueError as e:
                raise ParamError(
                    cli_name, "Invalid JSON: %s\nJSON received: %s"
                    % (e, value))
        raise ParamError(cli_name, "Invalid JSON:\n%s" % value)
    elif type_name == 'list':
        if isinstance(value, six.string_types):
            if value.lstrip()[0] == '[':
                return json.loads(value, object_pairs_hook=OrderedDict)
        elif isinstance(value, list) and len(value) == 1:
            single_value = value[0].strip()
            if single_value and single_value[0] == '[':
                return json.loads(value[0], object_pairs_hook=OrderedDict)
        try:
            # There's a couple of cases remaining here.
            # 1. It's possible that this is just a list of strings, i.e
            # --security-group-ids sg-1 sg-2 sg-3 => ['sg-1', 'sg-2', 'sg-3']
            # 2. It's possible this is a list of json objects:
            # --filters '{"Name": ..}' '{"Name": ...}'
            member_shape_model = argument_model.member
            return [_unpack_cli_arg(member_shape_model, v, cli_name)
                    for v in value]
        except (ValueError, TypeError) as e:
            # The list params don't have a name/cli_name attached to them
            # so they will have bad error messages.  We're going to
            # attach the parent parameter to this error message to provide
            # a more helpful error message.
            raise ParamError(cli_name, value[0])


def unpack_scalar_cli_arg(argument_model, value, cli_name=''):
    # Note the cli_name is used strictly for error reporting.  It's
    # not required to use unpack_scalar_cli_arg
    if argument_model.type_name == 'integer' or argument_model.type_name == 'long':
        return int(value)
    elif argument_model.type_name == 'float' or argument_model.type_name == 'double':
        # TODO: losing precision on double types
        return float(value)
    elif argument_model.type_name == 'blob' and \
            argument_model.serialization.get('streaming'):
        file_path = os.path.expandvars(value)
        file_path = os.path.expanduser(file_path)
        if not os.path.isfile(file_path):
            msg = 'Blob values must be a path to a file.'
            raise ParamError(cli_name, msg)
        return open(file_path, 'rb')
    elif argument_model.type_name == 'boolean':
        if isinstance(value, six.string_types) and value.lower() == 'false':
            return False
        return bool(value)
    else:
        return value


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
        'structure(list-scalar, scalar)': '_struct_scalar_list_parse',
        'map-scalar': '_key_value_parse',
        'list-structure(scalar)': '_list_scalar_parse',
        'list-structure(scalars)': '_list_key_value_parse',
        'list-structure(list-scalar, scalar)': '_list_scalar_list_parse',
    }

    def __init__(self):
        pass

    def __call__(self, cli_argument, value, **kwargs):
        """Attempt to parse shorthand syntax for values.

        This is intended to be hooked up as an event handler (hence the
        **kwargs).  Given ``param`` object and its string ``value``,
        figure out if we can parse it.  If we can parse it, we return
        the parsed value (typically some sort of python dict).

        :type cli_argument: :class:`awscli.arguments.BaseCLIArgument`
        :param cli_argument: The CLI argument object.

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
        parse_method = self.get_parse_method_for_param(cli_argument, value)
        if parse_method is None:
            return
        else:
            try:
                LOG.debug("Using %s for param %s", parse_method,
                          cli_argument.cli_name)
                parsed = getattr(self, parse_method)(
                    cli_argument.argument_model, value)
            except ParamSyntaxError as e:
                docgen = ParamShorthandDocGen()
                example_usage = docgen.generate_shorthand_example(cli_argument)
                raise ParamError(cli_argument.cli_name, "should be: %s" % example_usage)
            except (ParamError, ParamUnknownKeyError) as e:
                # The shorthand parse methods don't have the cli_name,
                # so any ParamError won't have this value.  To accomodate
                # this, ParamErrors are caught and reraised with the cli_name
                # injected.
                raise ParamError(cli_argument.cli_name, str(e))
            return parsed

    def get_parse_method_for_param(self, cli_argument, value=None):
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
                      "param shorthand.", cli_argument.py_name)
            return
        structure = detect_shape_structure(cli_argument.argument_model)
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
        model = argument.argument_model
        LOG.debug('Adding example fn for: %s' % arg_name)
        doc_fn = self._get_example_fn(model)
        # XXX: fix this, don't set attributes on argument objects.
        argument.example_fn = doc_fn

    def _list_scalar_list_parse(self, param, value):
        # Think something like ec2.DescribeInstances.Filters.
        # We're looking for key=val1,val2,val3,key2=val1,val2.
        parsed = []

        for v in value:
            struct = self._struct_scalar_list_parse(param.member, v)
            parsed.append(struct)

        return parsed

    def _struct_scalar_list_parse(self, param, value):
        # Create a mapping of argument name -> argument object
        args = {}
        for member_name, arg in param.members.items():
            # Arg name -> arg object lookup
            args[member_name] = arg

        parts = self._split_on_commas(value)
        current_parsed = {}
        current_key = None
        for part in parts:
            current = part.split('=', 1)
            if len(current) == 2:
                # This is a key/value pair.
                current_key = current[0].strip()
                if current_key not in args:
                    raise ParamUnknownKeyError(current_key,
                                               args.keys())
                current_value = unpack_scalar_cli_arg(args[current_key],
                                                      current[1].strip())
                if args[current_key].type_name == 'list':
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

        return current_parsed

    def _list_scalar_parse(self, param, value):
        single_param_name = list(param.member.members.keys())[0]
        parsed = []
        # We know that value is a list in this case.
        for v in value:
            parsed.append({single_param_name: v})
        return parsed

    def _list_key_value_parse(self, param, value):
        # param is a list param.
        # param.member is the struct param.
        struct_param = param.member
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
        if self._is_special_case_key_value(param, value):
            # We have an even shorter shorthand syntax for structure
            # of scalars of a single element with a member name of
            # 'Value'.
            return {'Value': value}
        else:
            return self._key_value_parse(param, value)

    def _is_special_case_key_value(self, param, value):
        members = param.members
        if len(param.members) == 1:
            if list(members.keys())[0] == 'Value' and \
                    '=' not in value:
                return True
        return False

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
                raise ParamUnknownKeyError(key, valid_names)
            if valid_names:
                sub_param = valid_names[key]
                if sub_param is not None:
                    # TODO: you are here.  unpack_scalar_cli_arg takes
                    # the cli_name, but we don't have it.  What are our
                    # options?
                    value = unpack_scalar_cli_arg(sub_param, value)
            parsed[key] = value
        return parsed

    def _create_name_to_params(self, param):
        if param.type_name == 'structure':
            return dict([(member_name, p) for member_name, p
                         in param.members.items()])
        elif param.type_name == 'map' and hasattr(param.key, 'enum'):
            return dict([(v, None) for v in param.key.enum])

    def _split_on_commas(self, value):
        try:
            return utils.split_on_commas(value)
        except ValueError as e:
            raise ParamSyntaxError(six.text_type(e))


class ParamShorthandDocGen(object):
    """Documentation generator for param shorthand syntax."""

    SHORTHAND_SHAPES = ParamShorthand.SHORTHAND_SHAPES

    def supports_shorthand(self, cli_argument):
        """Checks if a CLI argument supports shorthand syntax."""
        if cli_argument.argument_model is not None:
            structure = detect_shape_structure(cli_argument.argument_model)
            return structure in self.SHORTHAND_SHAPES
        return False

    def generate_shorthand_example(self, cli_argument):
        """Generate documentation for a CLI argument.

        :type cli_argument: awscli.arguments.BaseCLIArgument
        :param cli_argument: The CLI argument which to generate
            documentation for.
        """
        structure = detect_shape_structure(cli_argument.argument_model)
        parse_method_name = self.SHORTHAND_SHAPES.get(structure)
        doc_method_name = '_docs%s' % parse_method_name
        method = getattr(self, doc_method_name)
        doc_string = method(cli_argument)
        return doc_string

    def _docs_list_scalar_parse(self, cli_argument):
        cli_name = cli_argument.cli_name
        structure_members = cli_argument.argument_model.member.members
        # We know based on the SHORTHAND_SHAPES that this is a
        # structure with a single member, so we can safely say:
        member_name = list(structure_members.keys())[0]
        return '%s %s1 %s2 %s3' % (cli_name, member_name,
                                   member_name, member_name)

    def _docs_key_value_parse(self, cli_argument):
        cli_name = cli_argument.cli_name
        model = cli_argument.argument_model
        s = '%s ' % cli_name
        if model.type_name == 'structure':
            members_dict = model.members
            member_names = list(members_dict.keys())
            s += ','.join(['%s=value' % name for name in member_names])
        elif model.type_name == 'map':
            s += 'key_name=string,key_name2=string'
            if self._has_enum_values(model.key):
                enum_values = self._get_enum_values(model.key)
                s += '\nWhere valid key names are:\n'
                for value in enum_values:
                    s += '  %s\n' % value
        return s

    def _docs_list_key_value_parse(self, cli_argument):
        s = "Key value pairs, with multiple values separated by a space.\n"
        s += '%s ' % cli_argument.cli_name
        members = cli_argument.argument_model.member.members
        pair = ','.join(['%s=%s' % (member_name, shape.type_name)
                         for member_name, shape in members.items()])
        pair += ' %s' % pair
        s += pair
        return s

    def _docs_list_scalar_list_parse(self, cli_argument):
        s = ('Key value pairs, where values are separated by commas, '
             'and multiple pairs are separated by spaces.\n')
        s += '%s ' % cli_argument.cli_name
        pair = self._generate_struct_list_scalar_docs(
            cli_argument.argument_model.member.members)
        pair += ' %s' % pair
        s += pair
        return s

    def _docs_struct_scalar_list_parse(self, cli_argument):
        s = ('Key value pairs, where values are separated by commas.\n')
        s += '%s ' % cli_argument.cli_name
        s += self._generate_struct_list_scalar_docs(
            cli_argument.argument_model.members)
        return s

    def _generate_struct_list_scalar_docs(self, members_dict):
        scalar_params = list(self._get_scalar_params(members_dict))
        list_params = list(self._get_list_params(members_dict))
        pair = ''
        for member_name, param in scalar_params:
            pair += '%s=%s1,' % (member_name, param.type_name)
        for member_name, param in list_params[:-1]:
            param_type = param.member.type_name
            pair += '%s=%s1,%s2,' % (member_name, param_type, param_type)
        member_name, last_param = list_params[-1]
        param_type = last_param.member.type_name
        pair += '%s=%s1,%s2' % (member_name, param_type, param_type)
        return pair

    def _get_scalar_params(self, members_dict):
        for key, value in members_dict.items():
            if value.type_name in SCALAR_TYPES:
                yield (key, value)

    def _get_list_params(self, members_dict):
        for key, value in members_dict.items():
            if value.type_name == 'list':
                yield (key, value)

    def _has_enum_values(self, model):
        return 'enum' in model.metadata

    def _get_enum_values(self, model):
        return model.metadata['enum']

    def _docs_special_key_value_parse(self, cli_argument):
        members = cli_argument.argument_model.members
        if len(members) == 1 and 'Value' in members:
            # Returning None will indicate that we don't have
            # any examples to generate, and the entire examples section
            # should be skipped for this arg.
            return None
        else:
            return self._docs_key_value_parse(cli_argument)
