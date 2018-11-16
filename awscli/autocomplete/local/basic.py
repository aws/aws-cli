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
from awscli.autocomplete.completer import BaseCompleter
from awscli.autocomplete.completer import CompletionResult


class ModelIndexCompleter(BaseCompleter):

    def __init__(self, index):
        self._index = index

    def complete(self, parsed):
        if parsed.unparsed_items or parsed.current_fragment is None or \
                parsed.current_param:
            # If there's ever any unparsed items, then the parser
            # encountered something it didn't understand.  We won't
            # attempt to auto-complete anything here.
            return
        current_fragment = parsed.current_fragment
        if current_fragment.startswith('--'):
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
        offset = -len(parsed.current_fragment)
        result = [CompletionResult(name, starting_index=offset)
                  for name in self._index.command_names(lineage)
                  if name.startswith(parsed.current_fragment)]
        return result

    def _complete_options(self, parsed):
        # '--endpoint' -> 'endpoint'
        offset = -len(parsed.current_fragment)
        fragment = parsed.current_fragment[2:]
        arg_names = self._index.arg_names(
            lineage=parsed.lineage, command_name=parsed.current_command)
        results = [
            CompletionResult('--%s' % arg_name, starting_index=offset)
            for arg_name in arg_names
            if arg_name.startswith(fragment)
        ]
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
            offset = -len(parsed.current_fragment)
            global_params = self._index.arg_names(
                lineage=[], command_name='aws')
            global_param_completions = [
                CompletionResult('--%s' % arg_name, starting_index=offset)
                for arg_name in global_params
                if arg_name.startswith(fragment)
            ]
            results.extend(global_param_completions)
