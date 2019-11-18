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
WORD_BOUNDARY = ''


class ParsedResult(object):
    def __init__(self, current_command=None, current_param=None,
                 global_params=None, parsed_params=None,
                 lineage=None, current_fragment=None, unparsed_items=None):
        """

        :param current_command: The name of the leaf command; the most
            specific subcommand that was parsed.
        :param current_param: The name of the current parameter; this is the
            last known parameter we've parsed.  This value is set when we
            have parsed a known parameter and are parsing values associated
            with this parameter, and will be set to None once we're no longer
            parsing parameter values for the param.
        :param global_params: A dictionary of global CLI params.
        :param parsed_params: A dictionary of parameters that apply to
            the current command (non global params).
        :param lineage: A list of the lineage, with the ``aws`` portion
            included as the first element if necessary.
        :param current_fragment: The last fragment of a word that was not
            parsed.  This can happen if the user types only part of a command.
            The ``current_fragment`` is only populated if the cursor is on
            the current word.  If there is a space between the last word
            and the cursor it is not considered a fragment.  If this value
            is non ``None``, it typically indicates the value that needs to
            be auto-completed.
        :param unparsed_items: A list of items that we were not able to
            parse.  This can happen if the user types a command that's not
            in the index (e.g ``aws foo bar``).

        """
        # Example:
        #  aws --debug ec2 describe-instances --instance-ids i-123 i-124 \
        #    --region us-west-2
        #
        # This would parse to:
        # ParsedResult(
        #  current_command='describe-instances',
        #  global_params={'debug': None, 'region': 'us-west-2'},
        #  parsed_params={'instance-ids': ['i-123', 'i-124']},
        #  lineage=['aws', 'ec2'],
        #  current_fragment=None
        # )
        #
        # An example of last fragment is:
        #
        # "aws ec2 describe-"
        #
        # This would parse to:
        #
        # ParsedResult(current_command='ec2', lineage=['aws'],
        #              current_fragment='describe-')
        self.current_command = current_command
        self.current_param = current_param
        if global_params is None:
            global_params = {}
        self.global_params = global_params
        if parsed_params is None:
            parsed_params = {}
        self.parsed_params = parsed_params
        if lineage is None:
            lineage = []
        self.lineage = lineage
        # current_fragment is used to indicate that the value
        # is not a known subcommand/option.  It will only
        # ever apply to the last word in the command line.
        self.current_fragment = current_fragment
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
        self.current_param = None
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
        state, remaining_parts = self._split_to_parts(command_line, location)
        global_args = self._index.arg_names(lineage=[], command_name='aws')
        current_args = []
        current = state.current_command
        while remaining_parts:
            current = remaining_parts.pop(0)
            if current.startswith('--'):
                self._handle_option(current, remaining_parts,
                                    current_args, global_args, parsed, state)
            else:
                current_args = self._handle_positional(
                    current, state, remaining_parts, parsed)
        parsed.current_command = state.current_command
        parsed.current_param = state.current_param
        parsed.lineage = state.lineage
        return parsed

    def _consume_value(self, remaining_parts, option_name,
                       lineage, current_command, state):
        # We have a special case where a user is trying to complete
        # a value for an option, which is the last fragment of the command,
        # e.g. 'aws ec2 describe-instances --instance-ids '
        # Note the space at the end.  In this case we don't have a value
        # to consume so we special case this and short circuit.
        if remaining_parts == [WORD_BOUNDARY]:
            return ''
        elif len(remaining_parts) <= 1:
            return None
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
            result = remaining_parts.pop(0)
            state.current_param = None
            return result
        elif nargs == '?':
            if remaining_parts and not remaining_parts[0].startswith('--'):
                result = remaining_parts.pop(0)
                state.current_param = None
                return result
        elif nargs in '+*':
            # Technically nargs='+' requires one or more args, but
            # we don't validate this.  This will just result in
            # an empty list being returned.  This is acceptable
            # for auto-completion purposes.
            value = []
            while len(remaining_parts) > 1 and \
                    not remaining_parts == [WORD_BOUNDARY]:
                if remaining_parts[0].startswith('--'):
                    state.current_param = None
                    break
                value.append(remaining_parts.pop(0))
            return value

    def _split_to_parts(self, command_line, location):
        state = ParseState()
        if location is not None:
            # The original auto completer had this logic.
            # We could in theory still parse the entire command
            # line and only use the location value for determining
            # what to auto complete, but we're keeping the same logic
            # as the original for now.
            command_line = command_line[:location]
        parts = command_line.split()
        if command_line and command_line[-1].isspace():
            # If the command line ends with whitespace then we insert
            # an empty element in the parts list to ensure that the
            # last chunk isn't marked as the last fragment.  This is
            # because we can auto-complete a command such as:
            # "aws ec2 stop-<TAB>" but we can't auto-complete
            # a command like: "aws ec2 stop- <TAB>"
            parts.append(WORD_BOUNDARY)
        if parts:
            # If parts are returned, we are assuming that the first argument
            # will always be the executable name. However the executable name
            # can be anything (e.g. aws2), so we normalize the first
            # current_command to be aws as the autocomplete index expects the
            # first command to be aws.
            parts.pop(0)
            state.current_command = 'aws'
        return state, parts

    def _handle_option(self, current, remaining_parts, current_args,
                       global_args, parsed, state):
        if current_args is None:
            # If there are no arguments found for this current scope,
            # it usually indicates we've encounted a command we don't know.
            # In this case we don't try to handle this option.
            parsed.unparsed_items.append(current)
            return
        # This is a command line option, remove the `--` portion so we
        # just have the option name.
        option_name = current[2:]
        if option_name in global_args:
            state.current_param = option_name
            value = self._consume_value(
                remaining_parts, option_name, lineage=[],
                state=state,
                current_command='aws')
            parsed.global_params[option_name] = value
        elif option_name in current_args:
            state.current_param = option_name
            value = self._consume_value(
                remaining_parts, option_name, state.lineage,
                state.current_command, state=state,
            )
            parsed.parsed_params[option_name] = value
        elif self._is_last_word(remaining_parts, current):
            # If the option wasn't handled, there's two cases.
            # Either it's the last word (without a space) so it's
            # something we should auto-complete.  In that case
            # we denote it as the last fragment.
            parsed.current_fragment = current
        else:
            # It's not a known option in our index and it's not
            # a partially completed words.  This goes into the
            # unparsed_items list.
            parsed.unparsed_items.append(current)

    def _is_last_word(self, remaining_parts, current):
        return not remaining_parts and current

    def _handle_positional(self, current, state, remaining_parts, parsed):
        # This is can either be a subcommand or a positional argument
        #
        # First we can check if this is a valid subcommand given our lineage.
        # We're one off here, we need to compute a new *potential*
        # lineage.
        command_names = self._index.command_names(state.full_lineage)
        positional_argname = None
        if current in command_names:
            state.current_command = current
            # We also need to get the next set of command line options.
            current_args = self._index.arg_names(
                lineage=state.lineage,
                command_name=state.current_command)
            return current_args
        if not command_names:
            # If there are no more command names check. See if the command
            # has a positional argument. This will require an additional
            # select on the argument index.
            positional_argname = self._get_positional_argname(state)
        if (positional_argname and
            positional_argname not in parsed.parsed_params):
            # Parse the current string to be a positional argument
            # if the command has the a positional arg and the positional arg
            # has not already been parsed.
            if not remaining_parts:
                # We are currently parsing the positional argument
                parsed.current_fragment = current
                state.current_param = positional_argname
            elif current:
                # At this point, the positional argument is fully
                # written out so it should be saved to the parsed
                # params
                parsed.parsed_params[positional_argname] = current
                state.current_param = None
            return self._index.arg_names(
                lineage=state.lineage,
                command_name=state.current_command)
        else:
            if not remaining_parts:
                # If this is the last chunk of the command line but
                # it's not a subcommand then we'll mark it as the last
                # fragment.  This is likely a partially entered
                # command, e.g 'aws ec2 run-instan'
                parsed.current_fragment = current
            elif current:
                # Otherwise this is some command we don't know about
                # so we add it to the list of unparsed_items.
                parsed.unparsed_items.append(current)
            return None

    def _get_positional_argname(self, state):
        positional_args = self._index.arg_names(
            lineage=state.lineage,
            command_name=state.current_command,
            positional_arg=True
        )
        if positional_args:
            # We are assuming there is only ever one positional
            # argument for a command.
            return positional_args[0]
        return None
