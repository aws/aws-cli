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

import logging
import os

from botocore.compat import OrderedDict, json
from botocore.utils import is_json_value_header

from awscli import COMPLEX_TYPES, SCALAR_TYPES, shorthand
from awscli.utils import (
    find_service_and_method_in_event_name,
    is_document_type,
    is_document_type_container,
)

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
        full_message = "Error parsing parameter '%s': %s" % (cli_name, message)
        super().__init__(full_message)
        self.cli_name = cli_name
        self.message = message


class ParamSyntaxError(Exception):
    pass


class ParamUnknownKeyError(Exception):
    def __init__(self, key, valid_keys):
        valid_keys = ', '.join(valid_keys)
        full_message = (
            f"Unknown key '{key}', valid choices are: {valid_key}"
        )
        super().__init__(full_message)


class TooComplexError(Exception):
    pass


def unpack_argument(
    session, service_name, operation_name, cli_argument, value
):
    """
    Unpack an argument's value from the commandline. This is part one of a two
    step process in handling commandline arguments. Emits the load-cli-arg
    event with service, operation, and parameter names. Example::

        load-cli-arg.ec2.describe-instances.foo

    """
    param_name = getattr(cli_argument, 'name', 'anonymous')

    value_override = session.emit_first_non_none_response(
        f'load-cli-arg.{service_name}.{operation_name}.{param_name}',
        param=cli_argument,
        value=value,
        service_name=service_name,
        operation_name=operation_name,
    )

    if value_override is not None:
        value = value_override

    return value


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
            sub_types = [
                _detect_shape_structure(p, stack)
                for p in param.members.values()
            ]
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
    return _unpack_cli_arg(
        cli_argument.argument_model, value, cli_argument.cli_name
    )


def _special_type(model):
    # check if model is jsonvalue header and that value is serializable
    if (
        model.serialization.get('jsonvalue')
        and model.serialization.get('location') == 'header'
        and model.type_name == 'string'
    ):
        return True
    return False


def _unpack_cli_arg(argument_model, value, cli_name):
    if is_json_value_header(argument_model) or is_document_type(
        argument_model
    ):
        return _unpack_json_cli_arg(argument_model, value, cli_name)
    elif argument_model.type_name in SCALAR_TYPES:
        return unpack_scalar_cli_arg(argument_model, value, cli_name)
    elif argument_model.type_name in COMPLEX_TYPES:
        return _unpack_complex_cli_arg(argument_model, value, cli_name)
    else:
        return str(value)


def _unpack_json_cli_arg(argument_model, value, cli_name):
    try:
        return json.loads(value, object_pairs_hook=OrderedDict)
    except ValueError as e:
        raise ParamError(
            cli_name, f"Invalid JSON: {e}\nJSON received: {value}"
        )


def _unpack_complex_cli_arg(argument_model, value, cli_name):
    type_name = argument_model.type_name
    if type_name == 'structure' or type_name == 'map':
        if value.lstrip()[0] == '{':
            return _unpack_json_cli_arg(argument_model, value, cli_name)
        raise ParamError(cli_name, f"Invalid JSON:\n{value}")
    elif type_name == 'list':
        if isinstance(value, str):
            if value.lstrip()[0] == '[':
                return _unpack_json_cli_arg(argument_model, value, cli_name)
        elif isinstance(value, list) and len(value) == 1:
            single_value = value[0].strip()
            if single_value and single_value[0] == '[':
                return _unpack_json_cli_arg(argument_model, value[0], cli_name)
        try:
            # There's a couple of cases remaining here.
            # 1. It's possible that this is just a list of strings, i.e
            # --security-group-ids sg-1 sg-2 sg-3 => ['sg-1', 'sg-2', 'sg-3']
            # 2. It's possible this is a list of json objects:
            # --filters '{"Name": ..}' '{"Name": ...}'
            member_shape_model = argument_model.member
            return [
                _unpack_cli_arg(member_shape_model, v, cli_name) for v in value
            ]
        except (ValueError, TypeError):
            # The list params don't have a name/cli_name attached to them
            # so they will have bad error messages.  We're going to
            # attach the parent parameter to this error message to provide
            # a more helpful error message.
            raise ParamError(cli_name, value[0])


def unpack_scalar_cli_arg(argument_model, value, cli_name=''):
    # Note the cli_name is used strictly for error reporting.  It's
    # not required to use unpack_scalar_cli_arg
    if (
        argument_model.type_name == 'integer'
        or argument_model.type_name == 'long'
    ):
        return int(value)
    elif (
        argument_model.type_name == 'float'
        or argument_model.type_name == 'double'
    ):
        # TODO: losing precision on double types
        return float(value)
    elif (
        argument_model.type_name == 'blob'
        and argument_model.serialization.get('streaming')
    ):
        file_path = os.path.expandvars(value)
        file_path = os.path.expanduser(file_path)
        if not os.path.isfile(file_path):
            msg = 'Blob values must be a path to a file.'
            raise ParamError(cli_name, msg)
        return open(file_path, 'rb')
    elif argument_model.type_name == 'boolean':
        if isinstance(value, str) and value.lower() == 'false':
            return False
        return bool(value)
    else:
        return value


def _supports_shorthand_syntax(model):
    # Shorthand syntax is only supported if:
    #
    # 1. The argument is not a document type nor is a wrapper around a document
    # type (e.g. is a list of document types or a map of document types). These
    # should all be expressed as JSON input.
    #
    # 2. The argument is sufficiently complex, that is, it's base type is
    # a complex type *and* if it's a list, then it can't be a list of
    # scalar types.
    if is_document_type_container(model):
        return False
    return _is_complex_shape(model)


def _is_complex_shape(model):
    if model.type_name not in ['structure', 'list', 'map']:
        return False
    elif model.type_name == 'list':
        if model.member.type_name not in ['structure', 'list', 'map']:
            return False
    return True


class ParamShorthand:
    def _uses_old_list_case(self, service_id, operation_name, argument_name):
        """
        Determines whether a given operation for a service needs to use the
        deprecated shorthand parsing case for lists of structures that only have
        a single member.
        """
        cases = {
            'firehose': {'put-record-batch': ['records']},
            'workspaces': {
                'reboot-workspaces': ['reboot-workspace-requests'],
                'rebuild-workspaces': ['rebuild-workspace-requests'],
                'terminate-workspaces': ['terminate-workspace-requests'],
            },
            'elastic-load-balancing': {
                'remove-tags': ['tags'],
                'describe-instance-health': ['instances'],
                'deregister-instances-from-load-balancer': ['instances'],
                'register-instances-with-load-balancer': ['instances'],
            },
        }
        cases = cases.get(service_id, {}).get(operation_name, [])
        return argument_name in cases


class ParamShorthandParser(ParamShorthand):
    def __init__(self):
        self._parser = shorthand.ShorthandParser()
        self._visitor = shorthand.BackCompatVisitor()

    def __call__(self, cli_argument, value, event_name, **kwargs):
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

        if not self._should_parse_as_shorthand(cli_argument, value):
            return
        else:
            service_id, operation_name = find_service_and_method_in_event_name(
                event_name
            )
            return self._parse_as_shorthand(
                cli_argument, value, service_id, operation_name
            )

    def _parse_as_shorthand(
        self, cli_argument, value, service_id, operation_name
    ):
        try:
            LOG.debug("Parsing param %s as shorthand", cli_argument.cli_name)
            handled_value = self._handle_special_cases(
                cli_argument, value, service_id, operation_name
            )
            if handled_value is not None:
                return handled_value
            if isinstance(value, list):
                # Because of how we're using argparse, list shapes
                # are configured with nargs='+' which means the ``value``
                # is given to us "conveniently" as a list.  When
                # this happens we need to parse each list element
                # individually.
                parsed = [self._parser.parse(v) for v in value]
                self._visitor.visit(parsed, cli_argument.argument_model)
            else:
                # Otherwise value is just a string.
                parsed = self._parser.parse(value)
                self._visitor.visit(parsed, cli_argument.argument_model)
        except shorthand.ShorthandParseError as e:
            raise ParamError(cli_argument.cli_name, str(e))
        except (ParamError, ParamUnknownKeyError) as e:
            # The shorthand parse methods don't have the cli_name,
            # so any ParamError won't have this value.  To accommodate
            # this, ParamErrors are caught and reraised with the cli_name
            # injected.
            raise ParamError(cli_argument.cli_name, str(e))
        return parsed

    def _handle_special_cases(
        self, cli_argument, value, service_id, operation_name
    ):
        # We need to handle a few special cases that the previous
        # parser handled in order to stay backwards compatible.
        model = cli_argument.argument_model
        if (
            model.type_name == 'list'
            and model.member.type_name == 'structure'
            and len(model.member.members) == 1
            and self._uses_old_list_case(
                service_id, operation_name, cli_argument.name
            )
        ):
            # First special case is handling a list of structures
            # of a single element such as:
            #
            # --instance-ids id-1 id-2 id-3
            #
            # gets parsed as:
            #
            # [{"InstanceId": "id-1"}, {"InstanceId": "id-2"},
            #  {"InstanceId": "id-3"}]
            key_name = list(model.member.members.keys())[0]
            new_values = [{key_name: v} for v in value]
            return new_values
        elif (
            model.type_name == 'structure'
            and len(model.members) == 1
            and 'Value' in model.members
            and model.members['Value'].type_name == 'string'
            and '=' not in value
        ):
            # Second special case is where a structure of a single
            # value whose member name is "Value" can be specified
            # as:
            # --instance-terminate-behavior shutdown
            #
            # gets parsed as:
            # {"Value": "shutdown"}
            return {'Value': value}

    def _should_parse_as_shorthand(self, cli_argument, value):
        # We first need to make sure this is a parameter that qualifies
        # for simplification.  The first short-circuit case is if it looks
        # like json we immediately return.
        if value and isinstance(value, list):
            check_val = value[0]
        else:
            check_val = value
        if isinstance(check_val, str) and check_val.strip().startswith(
            ('[', '{')
        ):
            LOG.debug(
                "Param %s looks like JSON, not considered for "
                "param shorthand.",
                cli_argument.py_name,
            )
            return False
        model = cli_argument.argument_model
        return _supports_shorthand_syntax(model)


class ParamShorthandDocGen(ParamShorthand):
    """Documentation generator for param shorthand syntax."""

    _DONT_DOC = object()
    _MAX_STACK = 3

    def supports_shorthand(self, argument_model):
        """Checks if a CLI argument supports shorthand syntax."""
        if argument_model is not None:
            return _supports_shorthand_syntax(argument_model)
        return False

    def generate_shorthand_example(
        self, cli_argument, service_id, operation_name
    ):
        """Generate documentation for a CLI argument.

        :type cli_argument: awscli.arguments.BaseCLIArgument
        :param cli_argument: The CLI argument which to generate
            documentation for.

        :return: Returns either a string or ``None``.  If a string
            is returned, it is the generated shorthand example.
            If a value of ``None`` is returned then this indicates
            that no shorthand syntax is available for the provided
            ``argument_model``.

        """
        docstring = self._handle_special_cases(
            cli_argument, service_id, operation_name
        )
        if docstring is self._DONT_DOC:
            return None
        elif docstring:
            return docstring

        # Otherwise we fall back to the normal docgen for shorthand
        # syntax.
        stack = []
        try:
            if cli_argument.argument_model.type_name == 'list':
                argument_model = cli_argument.argument_model.member
                return self._shorthand_docs(argument_model, stack) + ' ...'
            else:
                return self._shorthand_docs(cli_argument.argument_model, stack)
        except TooComplexError:
            return ''

    def _handle_special_cases(self, cli_argument, service_id, operation_name):
        model = cli_argument.argument_model
        if (
            model.type_name == 'list'
            and model.member.type_name == 'structure'
            and len(model.member.members) == 1
            and self._uses_old_list_case(
                service_id, operation_name, cli_argument.name
            )
        ):
            member_name = list(model.member.members)[0]
            # Handle special case where the min/max is exactly one.
            metadata = model.metadata
            cli_name = cli_argument.cli_name
            if metadata.get('min') == 1 and metadata.get('max') == 1:
                return f'{cli_name} {member_name}1'
            return f'{cli_name} {member_name}1 {member_name}2 {member_name}3'
        elif (
            model.type_name == 'structure'
            and len(model.members) == 1
            and 'Value' in model.members
            and model.members['Value'].type_name == 'string'
        ):
            return self._DONT_DOC
        return ''

    def _shorthand_docs(self, argument_model, stack):
        if len(stack) > self._MAX_STACK:
            raise TooComplexError()
        if argument_model.type_name == 'structure':
            return self._structure_docs(argument_model, stack)
        elif argument_model.type_name == 'list':
            return self._list_docs(argument_model, stack)
        elif argument_model.type_name == 'map':
            return self._map_docs(argument_model, stack)
        else:
            return argument_model.type_name

    def _list_docs(self, argument_model, stack):
        list_member = argument_model.member
        stack.append(list_member.name)
        try:
            element_docs = self._shorthand_docs(argument_model.member, stack)
        finally:
            stack.pop()
        if list_member.type_name in COMPLEX_TYPES or len(stack) > 1:
            return '[%s,%s]' % (element_docs, element_docs)
        else:
            return '%s,%s' % (element_docs, element_docs)

    def _map_docs(self, argument_model, stack):
        k = argument_model.key
        value_docs = self._shorthand_docs(argument_model.value, stack)
        start = 'KeyName1=%s,KeyName2=%s' % (value_docs, value_docs)
        if k.enum and not stack:
            start += '\n\nWhere valid key names are:\n'
            for enum in k.enum:
                start += '  %s\n' % enum
        elif stack:
            start = '{%s}' % start
        return start

    def _structure_docs(self, argument_model, stack):
        parts = []
        for name, member_shape in argument_model.members.items():
            if is_document_type_container(member_shape):
                continue
            parts.append(self._member_docs(name, member_shape, stack))
        inner_part = ','.join(parts)
        if not stack:
            return inner_part
        return '{%s}' % inner_part

    def _member_docs(self, name, shape, stack):
        if stack.count(shape.name) > 0:
            return '( ... recursive ... )'
        stack.append(shape.name)
        try:
            value_doc = self._shorthand_docs(shape, stack)
        finally:
            stack.pop()
        return '%s=%s' % (name, value_doc)
