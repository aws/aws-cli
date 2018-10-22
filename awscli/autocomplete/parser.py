# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
class ParsedResult(object):
    def __init__(self, current_command=None,
                 global_params=None, current_params=None,
                 lineage=None, last_fragment=None, unparsed_items=None):
        # Example:
        #  aws --debug ec2 describe-instances --instance-ids i-123 i-124 \
        #    --region us-west-2
        #
        # This would parse to:
        # ParsedResult(
        #  current_command='describe-instances',
        #  global_params={'debug': None, 'region': 'us-west-2'},
        #  current_params={'instance-ids': ['i-123', 'i-124']},
        #  lineage=['aws', 'ec2'],
        #  last_fragment=None
        # )
        #
        # An example of last fragment is:
        #
        # "aws ec2 describe-"
        #
        # This would parse to:
        #
        # ParsedResult(current_command='ec2', lineage=['aws'],
        #              last_fragment='describe-')
        self.current_command = current_command
        if global_params is None:
            global_params = {}
        self.global_params = global_params
        if current_params is None:
            current_params = {}
        self.current_params = current_params
        if lineage is None:
            lineage = []
        self.lineage = lineage
        # last_fragment is used to indicate that the value
        # is not a known subcommand/option.  It will only
        # ever apply to the last word in the command line.
        self.last_fragment = last_fragment
        if unparsed_items is None:
            unparsed_items = []
        self.unparsed_items = unparsed_items

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__


class ParseState(object):
    def __init__(self):
        self._current_command = None
        self._lineage = []

    @property
    def current_command(self):
        return self._current_command

    @current_command.setter
    def current_command(self, value):
        if self._current_command is not None:
            self._lineage.append(self._current_command)
        self._current_command = value

    @property
    def lineage(self):
        return self._lineage

    @property
    def full_lineage(self):
        if self.current_command is None:
            return self._lineage
        return self._lineage + [self.current_command]


class CLIParser(object):
    """Parses AWS CLI command.

    This is different from the parser used when actually invoking CLI commands
    in that it can handle incomplete commands.  It will partially parse
    everything it understands, but incomplete commands will not generate
    errors.  This class is intended for use with auto completion and is
    not a general purpose AWS CLI parser.

    """
    def __init__(self, index):
        self._index = index

    def parse(self, command_line, location=None):
        """Parses as much of the command line input as possible.

        :param command_line: The command line as a string.
        :param location: The offset (0 based) of the current location
            of the cursor.

        """
        # NOTE: This parser doesn't support using `=` as a separator
        # between option and value, e.g `--foo=bar`.  This is something
        # we should look into adding.
        parsed = ParsedResult()
        parts = self._split_to_parts(command_line, location)
        state = ParseState()
        deferred_args = []
        global_args = self._index.arg_names(lineage=[], command_name='aws')
        current_args = []
        current = None
        while parts:
            current = parts.pop(0)
            if current.startswith('--'):
                was_handled = self._handle_option(
                    current, parts, current_args, global_args, parsed, state)
                if not was_handled and not parts and current:
                    parsed.last_fragment = current
            else:
                current_args = self._handle_subcommand(current, state)
                if current_args is None:
                    if not parts:
                        # If this is the last chunk of the command line but
                        # it's not a subcommand then we'll mark it as the last
                        # fragment.  This is likely a partially entered
                        # command, e.g 'aws ec2 run-instan'
                        parsed.last_fragment = current
                    elif current:
                        parsed.unparsed_items = [current] + parts
                    break
        parsed.current_command = state.current_command
        parsed.lineage = state.lineage
        return parsed

    def _consume_value(self, parts, option_name, lineage, current_command):
        arg_data = self._index.get_argument_data(
            lineage=lineage,
            command_name=current_command,
            arg_name=option_name,
        )
        nargs = arg_data.nargs
        # We're making an assumption about nargs in order to simplify
        # its handling.  Handling nargs='*' and nargs='+' normally takes into
        # account specific 'stop words', in our case valid subcommands.  This
        # means we technically support edge cases such as
        # "aws ec2 --filters describe-instances", which will parse to
        # `['aws', 'ec2', 'describe-instances']`, {'filters': []}.  Our
        # assumption is non-global options typically come after the associated
        # subcommand, e.g. "aws ec2 describe-instances <params here>".  We
        # don't have to worry about global params because none of them use
        # nargs '*' or '+'.
        if arg_data.type_name == 'boolean':
            return None
        elif nargs is None:
            # The default behavior is to consume a single arg.
            return parts.pop(0)
        elif nargs == '?':
            if parts and not parts[0].startswith('--'):
                return parts.pop(0)
        elif nargs in '+*':
            # Technically nargs='+' requires one or more args, but
            # we don't validate this.  This will just result in
            # an empty list being returned.  This is acceptable
            # for auto-completion purposes.
            value = []
            while parts:
                if parts[0].startswith('--'):
                    break
                value.append(parts.pop(0))
            return value

    def _split_to_parts(self, command_line, location):
        if location is not None:
            # The original auto completer had this logic.
            # We could in theory still parse the entire command
            # line and only use the location value for determining
            # what to auto complete, but we're keeping the same logic
            # as the original for now.
            command_line = command_line[:location]
        parts = command_line.split()
        if command_line[-1].isspace():
            # If the command line ends with whitespace then we insert
            # an empty element in the parts list to ensure that the
            # last chunk isn't marked as the last fragment.  This is
            # because we can auto-complete a command such as:
            # "aws ec2 stop-<TAB>" but we can't auto-complete
            # a command like: "aws ec2 stop- <TAB>"
            parts.append('')
        return parts

    def _handle_option(self, current, parts, current_args,
                       global_args, parsed, state):
        # This is a command line option.
        option_name = current[2:]
        if option_name in global_args:
            value = self._consume_value(
                parts, option_name, lineage=[],
                current_command='aws')
            parsed.global_params[option_name] = value
            return True
        elif option_name in current_args:
            value = self._consume_value(
                parts, option_name, state.lineage,
                state.current_command
            )
            parsed.current_params[option_name] = value
            return True
        return False

    def _handle_subcommand(self, current, state):
        # This is a subcommand so we can check if this is a valid
        # subcommand given our lineage.
        # We're one off here, we need to compute a new *potential*
        # lineage.
        command_names = self._index.command_names(state.full_lineage)
        if current in command_names:
            state.current_command = current
            # We also need to get the next set of command line options.
            current_args = self._index.arg_names(
                lineage=state.lineage,
                command_name=state.current_command)
            return current_args
