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
import re

from awscli.autocomplete.completer import BaseCompleter
from awscli.autocomplete.completer import CompletionResult
from awscli.utils import strip_html_tags


class ModelIndexCompleter(BaseCompleter):
    def __init__(self, index):
        self._index = index

    def complete(self, parsed):
        are_unparsed_items_paths = [bool(re.search('[./\\\\:]|(--)', item))
                                    for item in parsed.unparsed_items]
        if parsed.unparsed_items and all(are_unparsed_items_paths):
            # If all the unparsed items are file paths, then we auto-complete
            # options for the current fragment. This is to provide
            # auto-completion options for commands that take file paths, such
            # as `aws s3 mv ./path/to/file1 s3://path/to/file2`. We make an
            # exception for the last unparsed item if it starts with '--',
            # which indicates that the user is looking to complete an --option.
            #
            # Note that parsed.current_fragment may contain an empty string, so
            # we provide auto-completion options for the current_command
            # instead.
            if not parsed.current_fragment:
                parsed.current_fragment = parsed.current_command
            return self._complete_options(parsed)

        elif parsed.unparsed_items or parsed.current_fragment is None or \
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
            # We only offer completion of options if there are no
            # more commands to complete.
            commands = self._complete_command(parsed)
            if not commands:
                return self._complete_options(parsed)
            return commands

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
        results = []
        for arg_name in arg_names:
            if arg_name.startswith(fragment):
                arg_data = self._index.get_argument_data(
                    lineage=parsed.lineage,
                    command_name=parsed.current_command, arg_name=arg_name)
                clean_help_text = strip_html_tags(arg_data.help_text)
                results.append(CompletionResult('--%s' % arg_name,
                                                starting_index=offset,
                                                required=arg_data.required,
                                                cli_type_name=arg_data.type_name,
                                                help_text=clean_help_text))
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
            arg_data = self._index.get_global_arg_data()
            global_param_completions = []
            for arg_name, type_name, *_, help_text in arg_data:
                clean_help_text = strip_html_tags(help_text)
                if arg_name.startswith(fragment):
                    global_param_completions.append(
                        CompletionResult('--%s' % arg_name,
                                         starting_index=offset,
                                         required=False,
                                         cli_type_name=type_name,
                                         help_text=clean_help_text)
                    )
            results.extend(global_param_completions)
