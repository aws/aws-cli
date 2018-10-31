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
    """Main auto-completer object for the AWS CLI."""
    def __init__(self, parser, completers):
        self._parser = parser
        self._completers = completers

    def autocomplete(self, command_line, index=None):
        parsed = self._parser.parse(command_line, index)
        for completer in self._completers:
            result = completer.complete(parsed)
            if result is not None:
                return result


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
            * ``List[str]`` - If the completer is able to offer
              auto-completions it should return a list of strings that
              are valid suggestions for completing the command.  This
              indicates to the ``AutoCompleter`` to immediately return
              and to stop consulting other completers for results.
        """
        raise NotImplementedError("complete")


class ModelIndexCompleter(BaseCompleter):

    def __init__(self, index):
        self._index = index

    def complete(self, parsed):
        if parsed.unparsed_items or parsed.last_fragment is None:
            # If there's ever any unparsed items, then the parser
            # encountered something it didn't understand.  We won't
            # attempt to auto-complete anything here.
            return
        last_fragment = parsed.last_fragment
        if last_fragment.startswith('--'):
            # We could technically offer completion of options
            # if the last fragment is an empty string, but to avoid
            # dumping too much information back to the user, we only
            # offer completions for options if the value starts with
            # '--'.
            return self._complete_options(parsed)
        else:
            return self._complete_command(parsed)

    def _complete_command(self, parsed):
        lineage = parsed.lineage + [parsed.current_command]
        result = [name for name in self._index.command_names(lineage)
                  if name.startswith(parsed.last_fragment)]
        return result

    def _complete_options(self, parsed):
        # '--endpoint' -> 'endpoint'
        fragment = parsed.last_fragment[2:]
        arg_names = self._index.arg_names(
            lineage=parsed.lineage, command_name=parsed.current_command)
        results = [
            '--%s' % arg_name for arg_name in arg_names
            if arg_name.startswith(fragment)]
        # Global params apply to any scope, so if we're not
        # in the global scope, we need to add completions for
        # global params
        self._inject_global_params_if_needed(parsed, results, fragment)
        return results

    def _inject_global_params_if_needed(self, parsed, results, fragment):
        is_in_global_scope = (
            parsed.lineage == [] and
            parsed.current_command == 'aws'
        )
        if not is_in_global_scope:
            global_params = self._index.arg_names(
                lineage=[], command_name='aws')
            global_param_completions = [
                '--%s' % arg_name for arg_name in global_params
                if arg_name.startswith(fragment)]
            results.extend(global_param_completions)
