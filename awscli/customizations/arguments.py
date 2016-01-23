# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os

from awscli.arguments import CustomArgument
import jmespath

def resolve_given_outfile_path(path):
    """Asserts that a path is writable and returns the expanded path"""
    if path is None:
        return
    outfile = os.path.expanduser(os.path.expandvars(path))
    if not os.access(os.path.dirname(os.path.abspath(outfile)), os.W_OK):
        raise ValueError('Unable to write to file: %s' % outfile)
    return outfile


def is_parsed_result_successful(parsed_result):
    """Returns True if a parsed result is successful"""
    return parsed_result['ResponseMetadata']['HTTPStatusCode'] < 300


class OverrideRequiredArgsArgument(CustomArgument):
    """An argument that if specified makes all other arguments not required

    By not required, it refers to not having an error thrown when the
    parser does not find an argument that is required on the command line.
    To obtain this argument's property of ignoring required arguments,
    subclass from this class and fill out the ``ARG_DATA`` parameter as
    described below. Note this class is really only useful for subclassing.
    """

    # ``ARG_DATA`` follows the same format as a member of ``ARG_TABLE`` in
    # ``BasicCommand`` class as specified in
    # ``awscli/customizations/commands.py``.
    #
    # For example, an ``ARG_DATA`` variable would be filled out as:
    #
    # ARG_DATA =
    # {'name': 'my-argument',
    #  'help_text': 'This is argument ensures the argument is specified'
    #               'no other arguments are required'}
    ARG_DATA = {'name': 'no-required-args'}

    def __init__(self, session):
        self._session = session
        self._register_argument_action()
        super(OverrideRequiredArgsArgument, self).__init__(**self.ARG_DATA)

    def _register_argument_action(self):
        self._session.register('before-building-argument-table-parser',
                               self.override_required_args)

    def override_required_args(self, argument_table, args, **kwargs):
        name_in_cmdline = '--' + self.name
        # Set all ``Argument`` objects in ``argument_table`` to not required
        # if this argument's name is present in the command line.
        if name_in_cmdline in args:
            for arg_name in argument_table.keys():
                argument_table[arg_name].required = False


class StatefulArgument(CustomArgument):
    """An argument that maintains a stateful value"""

    def __init__(self, *args, **kwargs):
        super(StatefulArgument, self).__init__(*args, **kwargs)
        self._value = None

    def add_to_params(self, parameters, value):
        super(StatefulArgument, self).add_to_params(parameters, value)
        self._value = value

    @property
    def value(self):
        return self._value


class QueryOutFileArgument(StatefulArgument):
    """An argument that write a JMESPath query result to a file"""

    def __init__(self, session, name, query, after_call_event, perm,
                 *args, **kwargs):
        self._session = session
        self._query = query
        self._after_call_event = after_call_event
        self._perm = perm
        # Generate default help_text if text was not provided.
        if 'help_text' not in kwargs:
            kwargs['help_text'] = ('Saves the command output contents of %s '
                                   'to the given filename' % self.query)
        super(QueryOutFileArgument, self).__init__(name, *args, **kwargs)

    @property
    def query(self):
        return self._query

    @property
    def perm(self):
        return self._perm

    def add_to_params(self, parameters, value):
        value = resolve_given_outfile_path(value)
        super(QueryOutFileArgument, self).add_to_params(parameters, value)
        if self.value is not None:
            # Only register the event to save the argument if it is set
            self._session.register(self._after_call_event, self.save_query)

    def save_query(self, parsed, **kwargs):
        """Saves the result of a JMESPath expression to a file.

        This method only saves the query data if the response code of
        the parsed result is < 300.
        """
        if is_parsed_result_successful(parsed):
            contents = jmespath.search(self.query, parsed)
            with open(self.value, 'w') as fp:
                # Don't write 'None' to a file -- write ''.
                if contents is None:
                    fp.write('')
                else:
                    fp.write(contents)
                os.chmod(self.value, self.perm)
