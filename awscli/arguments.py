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
"""Abstractions for CLI arguments.

This module contains abstractions for representing CLI arguments.
This includes how the CLI argument parser is created, how arguments
are serialized, and how arguments are bound (if at all) to operation
arguments.

"""
import logging

from botocore.hooks import first_non_none_response
from botocore import xform_name

from awscli.paramfile import get_paramfile, ResourceLoadingError
from awscli.argprocess import unpack_cli_arg


LOG = logging.getLogger('awscli.arguments')


class BadArgumentError(Exception):
    pass


class UnknownArgumentError(Exception):
    pass


class BaseCLIArgument(object):
    """Interface for CLI argument.

    This class represents the interface used for representing CLI
    arguments.

    """

    def __init__(self, name):
        self._name = name

    def add_to_arg_table(self, argument_table):
        """Add this object to the argument_table.

        The ``argument_table`` represents the argument for the operation.
        This is called by the ``ServiceOperation`` object to create the
        arguments associated with the operation.

        :type argument_table: dict
        :param argument_table: The argument table.  The key is the argument
            name, and the value is an object implementing this interface.
        """
        argument_table[self.name] = self

    def add_to_parser(self, parser):
        """Add this object to the parser instance.

        This method is called by the associated ``ArgumentParser``
        instance.  This method should make the relevant calls
        to ``add_argument`` to add itself to the argparser.

        :type parser: ``argparse.ArgumentParser``.
        :param parser: The argument parser associated with the operation.

        """
        pass

    def add_to_params(self, parameters, value):
        """Add this object to the parameters dict.

        This method is responsible for taking the value specified
        on the command line, and deciding how that corresponds to
        parameters used by the service/operation.

        :type parameters: dict
        :param parameters: The parameters dictionary that will be
            given to ``botocore``.  This should match up to the
            parameters associated with the particular operation.

        :param value: The value associated with the CLI option.

        """
        pass

    @property
    def name(self):
        return self._name

    @property
    def cli_name(self):
        return '--' + self._name

    @property
    def cli_type_name(self):
        raise NotImplementedError("cli_type_name")

    @property
    def required(self):
        raise NotImplementedError("required")

    @property
    def documentation(self):
        raise NotImplementedError("documentation")

    @property
    def cli_type(self):
        raise NotImplementedError("cli_type")

    @property
    def py_name(self):
        return self._name.replace('-', '_')

    @property
    def choices(self):
        """List valid choices for argument value.

        If this value is not None then this should return a list of valid
        values for the argument.

        """
        return None

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def group_name(self):
        """Get the group name associated with the argument.

        An argument can be part of a group.  This property will
        return the name of that group.

        This base class has no default behavior for groups, code
        that consumes argument objects can use them for whatever
        purposes they like (documentation, mututally exclusive group
        validation, etc.).

        """
        return None


class CustomArgument(BaseCLIArgument):
    """
    Represents a CLI argument that is configured from a dictionary.

    For example, the "top level" arguments used for the CLI
    (--region, --output) can use a DictBasedArgument argument,
    as these are described in the cli.json file as dictionaries.

    """

    def __init__(self, name, help_text='', dest=None, default=None,
                 action=None, required=None, choices=None, nargs=None,
                 cli_type_name=None, group_name=None):
        self._name = name
        self._help = help_text
        self._dest = dest
        self._default = default
        self._action = action
        self._required = required
        self._nargs = nargs
        self._cli_type_name = cli_type_name
        self._group_name = group_name
        if choices is None:
            choices = []
        self._choices = choices
        # TODO: We should eliminate this altogether.
        # You should not have to depend on an argument_object
        # as part of the interface.  Currently the argprocess
        # and docs code relies on this object.
        self.argument_object = None

    def add_to_parser(self, parser):
        """

        See the ``BaseCLIArgument.add_to_parser`` docs for more information.

        """
        cli_name = self.cli_name
        kwargs = {}
        if self._dest is not None:
            kwargs['dest'] = self._dest
        if self._action is not None:
            kwargs['action'] = self._action
        if self._default is not None:
            kwargs['default'] = self._default
        if self._choices:
            kwargs['choices'] = self._choices
        if self._required is not None:
            kwargs['required'] = self._required
        if self._nargs is not None:
            kwargs['nargs'] = self._nargs
        parser.add_argument(cli_name, **kwargs)

    def required(self):
        if self._required is None:
            return False
        return self._required

    @property
    def documentation(self):
        return self._help

    @property
    def cli_type_name(self):
        if self._cli_type_name is not None:
            return self._cli_type_name
        elif self._action in ['store_true', 'store_false']:
            return 'boolean'
        else:
            # Default to 'string' type if we don't have any
            # other info.
            return 'string'

    @property
    def cli_type(self):
        cli_type = str
        if self._action in ['store_true', 'store_false']:
            cli_type = bool
        return cli_type

    @property
    def choices(self):
        return self._choices

    @property
    def group_name(self):
        return self._group_name


class CLIArgument(BaseCLIArgument):
    """Represents a CLI argument that maps to a service parameter.

    """

    TYPE_MAP = {
        'structure': str,
        'map': str,
        'timestamp': str,
        'list': str,
        'string': str,
        'float': float,
        'integer': str,
        'long': int,
        'boolean': bool,
        'double': float,
        'blob': str
    }

    def __init__(self, name, argument_object, operation_object):
        """

        :type name: str
        :param name: The name of the argument in "cli" form
            (e.g.  ``min-instances``).

        :type argument_object: ``botocore.parameter.Parameter``
        :param argument_object: The parameter object to associate with
            this object.

        :type operation_object: ``botocore.operation.Operation``
        :param operation_object: The operation object associated with
            this object.

        """
        self._name = name
        self.argument_object = argument_object
        self.operation_object = operation_object

    @property
    def py_name(self):
        return self._name.replace('-', '_')

    @property
    def required(self):
        return self.argument_object.required

    @required.setter
    def required(self, value):
        self.argument_object.required = value

    @property
    def documentation(self):
        return self.argument_object.documentation

    @property
    def cli_type_name(self):
        return self.argument_object.type

    @property
    def cli_type(self):
        return self.TYPE_MAP.get(self.argument_object.type, str)

    def add_to_parser(self, parser):
        """

        See the ``BaseCLIArgument.add_to_parser`` docs for more information.

        """
        cli_name = self.cli_name
        parser.add_argument(
            cli_name,
            help=self.documentation,
            type=self.cli_type,
            required=self.required)

    def add_to_params(self, parameters, value):
        if value is None:
            return
        else:
            # This is a two step process.  First is the process of converting
            # the command line value into a python value.  Normally this is
            # handled by argparse directly, but there are cases where extra
            # processing is needed.  For example, "--foo name=value" the value
            # can be converted from "name=value" to {"name": "value"}.  This is
            # referred to as the "unpacking" process.  Once we've unpacked the
            # argument value, we have to decide how this is converted into
            # something that can be consumed by botocore.  Many times this is
            # just associating the key and value in the params dict as down
            # below.  Sometimes this can be more complicated, and subclasses
            # can customize as they need.
            unpacked = self._unpack_argument(value)
            LOG.debug('Unpacked value of "%s" for parameter "%s": %s', value,
                      self.argument_object.py_name, unpacked)
            parameters[self.argument_object.py_name] = unpacked

    def _unpack_argument(self, value):
        if not hasattr(self.argument_object, 'no_paramfile'):
            value = self._handle_param_file(value)
        service_name = self.operation_object.service.endpoint_prefix
        operation_name = xform_name(self.operation_object.name, '-')
        responses = self._emit('process-cli-arg.%s.%s' % (
            service_name, operation_name), param=self.argument_object,
            value=value,
            operation=self.operation_object)
        override = first_non_none_response(responses)
        if override is not None:
            # A plugin supplied an alternate conversion,
            # use it instead.
            return override
        else:
            # Fall back to the default arg processing.
            return unpack_cli_arg(self.argument_object, value)

    def _handle_param_file(self, value):
        session = self.operation_object.service.session
        # If the arg is suppose to be a list type, just
        # get the first element in the list, as it may
        # refer to a file:// (or http/https) type.
        potential_param_value = value
        if isinstance(value, list) and len(value) == 1:
            potential_param_value = value[0]
        try:
            actual_value = get_paramfile(session, potential_param_value)
        except ResourceLoadingError as e:
            raise BadArgumentError(
                "Bad value for argument '%s': %s" % (self.cli_name, e))
        if actual_value is not None:
            value = actual_value
        return value

    def _emit(self, name, **kwargs):
        session = self.operation_object.service.session
        return session.emit(name, **kwargs)


class ListArgument(CLIArgument):

    def add_to_parser(self, parser):
        cli_name = self.cli_name
        parser.add_argument(cli_name,
                            nargs='*',
                            type=self.cli_type,
                            required=self.required)


class BooleanArgument(CLIArgument):
    """Represent a boolean CLI argument.

    A boolean parameter is specified without a value::

        aws foo bar --enabled

    For cases wher the boolean parameter is required we need to add
    two parameters::

        aws foo bar --enabled
        aws foo bar --no-enabled

    We use the capabilities of the CLIArgument to help achieve this.

    """

    def __init__(self, name, argument_object, operation_object,
                 action='store_true', dest=None, group_name=None):
        super(BooleanArgument, self).__init__(name, argument_object,
                                              operation_object)
        self._mutex_group = None
        self._action = action
        if dest is None:
            self._destination = self.py_name
        else:
            self._destination = dest
        if group_name is None:
            self._group_name = self.name
        else:
            self._group_name = group_name

    def add_to_params(self, parameters, value):
        # If a value was explicitly specified (so value is True/False
        # but *not* None) then we add it to the params dict.
        # If the value was not explicitly set (value is None)
        # we don't add it to the params dict.
        if value is not None:
            parameters[self.py_name] = value

    def add_to_arg_table(self, argument_table):
        # Boolean parameters are a bit tricky.  For a single boolean parameter
        # we actually want two CLI params, a --foo, and a --no-foo.  To do this
        # we need to add two entries to the argument table.  So we can add
        # ourself as the positive option (--no), and then create a clone of
        # ourselves for the negative service.  We then insert both into the
        # arg table.
        argument_table[self.name] = self
        negative_name = 'no-%s' % self.name
        negative_version = self.__class__(negative_name, self.argument_object,
                                          self.operation_object,
                                          action='store_false',
                                          dest=self._destination,
                                          group_name=self.group_name)
        argument_table[negative_name] = negative_version

    def add_to_parser(self, parser):
        parser.add_argument(self.cli_name,
                            help=self.documentation,
                            action=self._action,
                            default=None,
                            dest=self._destination)

    @property
    def group_name(self):
        return self._group_name
