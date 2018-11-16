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


class AutoCompleter(object):
    """Main auto-completer object for the AWS CLI.

    This object delegates to concrete completers that can perform
    completions for specific cases (e.g model-based completions,
    server-side completions, etc).
    """
    def __init__(self, parser, completers):
        """

        :param parser: A parser.CLIParser instance.
        :param completers: A list of ``BaseCompleter`` instances.

        """
        self._parser = parser
        self._completers = completers

    def autocomplete(self, command_line, index=None):
        """Attempt to find completion suggestions.

        :param command_line: The currently entered command line as a string.
        :param index: An optional integer that indicates the location where
            the cursor is located (0 based index).

        :return: A list of ``CompletionResult`` objects.

        """
        parsed = self._parser.parse(command_line, index)
        for completer in self._completers:
            result = completer.complete(parsed)
            if result is not None:
                return result
        return []


class CompletionResult(object):
    """A data object for a single completion result.

    In addition to storing the completion string, this object also
    stores metadata about the completion.

    """
    def __init__(self, result, starting_index=0):
        self.result = result
        self.starting_index = starting_index

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__) and
            self.result == other.result and
            self.starting_index == other.starting_index
        )

    def __repr__(self):
        return '%s(%s, %s)' % (self.__class__.__name__,
                               self.result, self.starting_index)


class BaseCompleter(object):
    def complete(self, parsed):
        """Attempt to autocomplete parsed on parsed result.

        Subclasses should implement this method.

        :param parsed: A ParsedResult from the auto complete CLI parser.
        :return: This method should return one of two values:

            * ``None`` - If the completer doesn't understand how to
              complete the command, it should return ``None``.  This
              signals to the ``AutoCompleter`` that it should move on
              to the next completer.
            * ``List[CompletionResult]`` - If the completer is able to offer
              auto-completions it should return a list of strings that
              are valid suggestions for completing the command.  This
              indicates to the ``AutoCompleter`` to immediately return
              and to stop consulting other completers for results.
        """
        raise NotImplementedError("complete")
