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
import os
import re

from awscli.autocomplete.completer import BaseCompleter
from awscli.autocomplete.completer import CompletionResult
from awscli.autocomplete.filters import startswith_filter
from awscli.autocomplete import LazyClientCreator


def strip_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


class ProfileCompleter(BaseCompleter):
    def __init__(self, session=None, response_filter=startswith_filter,
                 session_creator=None):
        self._session = session
        self._filter = response_filter
        self._session_creator = session_creator
        if self._session_creator is None:
            self._session_creator = LazyClientCreator()

    def complete(self, parsed):
        if parsed.current_param == 'profile':
            return self._filter(parsed.current_fragment, self._get_profiles())

    def _get_profiles(self):
        return map(
            lambda x: CompletionResult(name=x),
            self._get_session().available_profiles
         )

    def _get_session(self):
        if self._session is None:
            self._session = self._session_creator.create_session()
        return self._session


class RegionCompleter(BaseCompleter):
    def __init__(self, session=None, response_filter=startswith_filter,
                 session_creator=None):
        self._session = session
        self._filter = response_filter
        self._session_creator = session_creator
        if self._session_creator is None:
            self._session_creator = LazyClientCreator()

    def complete(self, parsed):
        if parsed.current_param == 'region':
            if len(parsed.lineage) > 1:
                service_name = parsed.lineage[1]
            else:
                service_name = 'ec2'
            return self._filter(parsed.current_fragment,
                                self._get_region_completions(service_name))

    def _get_region_completions(self, service_name):
        return map(
            lambda x: CompletionResult(name=x),
            self._get_regions(service_name)
        )

    def _get_regions(self, service_name):
        if self._session is None:
            self._session = self._session_creator.create_session()
        return self._session.get_available_regions(
                service_name=service_name
            )


class FilePathCompleter(BaseCompleter):
    def __init__(self, path_completer=None, response_filter=startswith_filter):
        self._path_completer = path_completer
        self._filter = response_filter

    @property
    def path_completer(self):
        if self._path_completer is None:
            from prompt_toolkit.completion import PathCompleter
            self._path_completer = PathCompleter(expanduser=True)
        return self._path_completer

    def complete(self, parsed):
        if parsed.current_fragment and \
                parsed.current_fragment.startswith(('file://', 'fileb://')):
            from prompt_toolkit.document import Document
            for prefix in ['file://', 'fileb://']:
                if parsed.current_fragment.startswith(prefix):
                    filename_part = parsed.current_fragment[len(prefix):]
                    break
            # PathCompleter makes really strange suggestions for lonely ~
            # "username/", so in this case we handle it by ourselves
            if filename_part == '~':
                return [CompletionResult(''.join([prefix, '~%s' % os.sep]))]
            dirname = os.path.dirname(filename_part)
            if dirname and dirname != os.sep:
                dirname = f'{dirname}{os.sep}'
            document = Document(
                text=dirname,
                cursor_position=len(dirname))
            completions = self.path_completer.get_completions(document, None)
            results = [
                CompletionResult(
                    f'{prefix}'
                    f'{os.path.join(dirname, completion.display[0][1])}',
                    display_text=completion.display[0][1])
                for completion in completions]
            return self._filter(os.path.basename(filename_part), results)


class ModelIndexCompleter(BaseCompleter):
    def __init__(self, index, cli_driver_fetcher=None,
                 response_filter=startswith_filter):
        self._index = index
        self._cli_driver_fetcher = cli_driver_fetcher
        self._filter = response_filter

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
            return self._filter(parsed.current_fragment,
                                self._complete_options(parsed))

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
            prefix = parsed.current_fragment
            if prefix == '--':
                prefix = ''
            return self._filter(prefix, self._complete_options(parsed))
        else:
            # We only offer completion of options if there are no
            # more commands to complete.
            commands = self._complete_command(parsed)
            if not commands:
                return self._filter(parsed.current_fragment,
                                    self._complete_options(parsed))
            return self._filter(parsed.current_fragment, commands)

    def _complete_command(self, parsed):
        lineage = parsed.lineage + [parsed.current_command]
        offset = -len(parsed.current_fragment)
        result = [CompletionResult(name,
                                   help_text=full_name,
                                   starting_index=offset)
                  for name, full_name in self._index.commands_with_full_name(lineage)]
        return result

    def _outfile_filter(self, completion):
        if completion.name == '--outfile':
            completion.name = 'outfile'
            completion.display_text = 'outfile (required)'
        return completion

    def _complete_options(self, parsed):
        # '--endpoint' -> 'endpoint'
        offset = -len(parsed.current_fragment)
        # In case fragment doesn't start from --
        # we use the original fragment
        if parsed.current_fragment.startswith('--'):
            fragment = parsed.current_fragment[2:]
        else:
            fragment = parsed.current_fragment
        arg_names = self._index.arg_names(
            lineage=parsed.lineage, command_name=parsed.current_command)
        results = []
        for arg_name in arg_names:
            arg_data = self._index.get_argument_data(
                lineage=parsed.lineage,
                command_name=parsed.current_command, arg_name=arg_name)
            help_text = None
            if self._cli_driver_fetcher:
                help_text = strip_html_tags(
                    self._cli_driver_fetcher.get_argument_documentation(
                        parsed.lineage, parsed.current_command, arg_name
                    )
                )
            results.append(self._outfile_filter(
                                CompletionResult(
                                    '--%s' % arg_name,
                                    starting_index=offset,
                                    required=arg_data.required,
                                    cli_type_name=arg_data.type_name,
                                    help_text=help_text)
                                )
            )
        # Global params apply to any scope, so if we're not
        # in the global scope, we need to add completions for
        # global params
        self._inject_global_params_if_needed(parsed, results, fragment)

        return [result for result in results
                if result.name.strip('--') not in (list(parsed.parsed_params) +
                                                   list(parsed.global_params))]

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
                help_text = None
                if self._cli_driver_fetcher:
                    help_text = strip_html_tags(
                        self._cli_driver_fetcher.get_global_arg_documentation(
                            arg_name
                        )
                    )
                global_param_completions.append(
                    CompletionResult('--%s' % arg_name,
                                     starting_index=offset,
                                     required=False,
                                     cli_type_name=type_name,
                                     help_text=help_text)
                )

            results.extend(global_param_completions)


class ShorthandCompleter(BaseCompleter):
    _PARENS = {
        "[": "]",
        "{": "}"
    }
    _DUMMY_KEY_VALUE = 'cli_placeholder_for_key_value_replacement'
    _DUMMY_VALUE = 'cli_placeholder_for_value_replacement'
    _DUMMY_EQ_VALUE = 'cli_placeholder_for_key_eq_replacement'
    _VALUE_PREFIXES = {
        'structure': '{',
        'list': '[',
        'map': '{'
    }

    def __init__(self, cli_driver_fetcher=None,
                 response_filter=startswith_filter):
        self._filter = response_filter
        self._cli_driver_fetcher = cli_driver_fetcher
        self._shorthand_parser = None

    @property
    def shorthand_parser(self):
        if self._shorthand_parser is None:
            from awscli.shorthand import ShorthandParser
            self._shorthand_parser = ShorthandParser()
        return self._shorthand_parser

    def complete(self, parsed):
        if parsed.current_param and self._cli_driver_fetcher:
            results = []
            arg_model = self._cli_driver_fetcher.get_argument_model(
                parsed.lineage, parsed.current_command, parsed.current_param
            )
            if arg_model is None:
                return None
            parsed_input = self._parse_fragment(parsed.current_fragment)
            if parsed_input is not None:
                results = self._get_completion(arg_model, parsed_input)
                # prefix all the completions name property with the
                # current_fragment to make correct insert into the user
                # input line
                fragment = parsed.current_fragment or ''
                for result in results:
                    name_part_len = len(fragment) - len(result.name)
                    result.name = "%s%s" % (
                        fragment[:name_part_len],
                        result.display_text
                    )
            brackets_completion = self._get_close_brackets_completion(
                parsed.current_fragment
            )
            if brackets_completion is not None:
                results.append(brackets_completion)
            return results or None

    def _close_brackets(self, fragment):
        # If there any unclosed brackets in the text we try to close them
        # and we return part with closing brackets if they are "closable"
        stack = []
        for char in fragment:
            if char in self._PARENS.keys():
                stack.append(char)
            elif char in self._PARENS.values():
                if stack and self._PARENS[stack[-1]] == char:
                    stack.pop()
                else:
                    return ''
        return ''.join(self._PARENS[paren] for paren in reversed(stack))

    def _parse_fragment(self, fragment, attempt=1):
        # Try complete fragment to make it parsable and we handle such cases
        #
        # you just started typing input it will return a dict with input as key
        # --option foo -> {'foo': ''}
        #
        # you typed a comma
        # --option foo=1, -> foo=1,DUMMY_KEY_VALUE=DUMMY_KEY_VALUE
        #
        # you typed equal sign
        # --option foo= -> foo=DUMMY_VALUE
        #
        # after that we close all the brackets if needed and try to parse
        # if we get a parsing error it can be that you have some partially
        # entered nested structure in such a case we'll try to complete it
        # and make one more attempt
        # --option foo={bar -> foo={bar=DUMMY_EQ_VALUE
        from awscli.shorthand import ShorthandParseError
        if not fragment:
            return {}
        if '=' not in fragment:
            return {fragment: None}
        if fragment.endswith(','):
            fragment += f'{self._DUMMY_KEY_VALUE}={self._DUMMY_KEY_VALUE}'
        elif fragment.endswith('='):
            fragment += self._DUMMY_VALUE
        try:
            return self.shorthand_parser.parse(
                f'{fragment}{self._close_brackets(fragment)}'
            )
        except ShorthandParseError:
            if attempt == 1:
                return self._parse_fragment(
                    f'{fragment}={self._DUMMY_EQ_VALUE}', attempt + 1)
        # if we get here it means that we can't make it parsable and can't
        # suggest anything so the only solution is to wait till user enter more
        return

    def _get_completion(self, arg_model, parsed_input):
        completion = getattr(
            self, "_get_prompt_for_%s" % arg_model.type_name, self._no_prompt
        )(arg_model, parsed_input)
        if completion is None:
            return []
        return completion

    def _get_last_key_value(self, parsed_input):
        # returns last key and its value in top level structure
        # from parsed_input
        # - if value is not None the next step will be to autopropmt value
        # if possible, value='' - means that user typed '=' but hasn't
        # started typing value yet
        # - if value is None but key is not None the next step will be to
        # autopropmt key if possible, key='' - means that user
        # typed ',' after previous key=value pair but hasn't started typing
        # key yet
        # - if both None - it means it's not a dict (maybe string or integer)
        # and we won't prompt anything
        if not isinstance(parsed_input, dict):
            return None, None
        if not parsed_input:
            return '', None
        key = list(parsed_input)[-1]
        value = parsed_input[key]
        # if get in situation when foo=a,bar it will parsed as
        # foo=['a','bar'] and we will assume that "bar" is the next key
        if value and isinstance(value, list):
            key = value[-1]
            value = None
        # remove dummy_parts if they were added before
        elif value == key == self._DUMMY_KEY_VALUE:
            key = ''
            value = None
        elif value == self._DUMMY_EQ_VALUE:
            value = None
        return key, value

    def _no_prompt(self, *args, **kwargs):
        # for all types we do not support
        return None

    def _get_close_brackets_completion(self, fragment):
        if not fragment:
            return
        close_brackets = self._close_brackets(fragment)
        if close_brackets:
            return CompletionResult(
                f'{fragment}{close_brackets}',
                display_text='Autoclose brackets'
            )

    def _get_prompt_for_string(self, arg_model, parsed_input):
        if arg_model.enum:
            prefix = parsed_input
            if prefix == self._DUMMY_VALUE:
                prefix = ''
            return self._filter(prefix,
                                [CompletionResult(prefix, display_text=enum)
                                 for enum in arg_model.enum])

    def _get_prompt_for_boolean(self, arg_model, parsed_input):
        all_results = ['true', 'false']
        prefix = parsed_input
        if prefix == self._DUMMY_VALUE:
            prefix = ''
        return self._filter(prefix,
                            [CompletionResult(prefix, display_text=result)
                             for result in all_results])

    def _get_prompt_for_list(self, arg_model, parsed_input):
        # we have two way we can enter lists:
        # - if it's a top level structure it will be space separated and
        # parsed_input will contain the last element of the list
        # - if it's a nested structure we'll get the whole list as an input
        if not isinstance(parsed_input, list):
            parsed_input = [parsed_input]
        return self._get_completion(arg_model.member, parsed_input[-1])

    def _get_prompt_for_map(self, arg_model, parsed_input):
        last_key, last_value = self._get_last_key_value(parsed_input)
        if last_value:
            return self._get_completion(arg_model.value, last_value)
        return self._get_completion(arg_model.key, last_key)

    def _get_prompt_for_structure(self, arg_model, parsed_input):
        last_key, last_value = self._get_last_key_value(parsed_input)
        if last_key is None and last_value is None:
            return None
        # if we have a last_value it can be nested structure so let's try
        # to get suggestion for it
        if last_key and last_value is not None:
            if not arg_model.members.get(last_key):
                # key exists but we don't have such key in model
                return None
            return self._get_completion(
                arg_model.members[last_key], last_value)
        entered_keys = set(parsed_input) - set(last_key)
        return self._get_struct_keys_completions(
            arg_model, entered_keys, last_key)

    def _get_struct_keys_completions(self, arg_model, entered_keys,
                                     last_key):
        # get suggestions for the structure keys, as CompletionResult.name
        # we return only part of the suggestion that has not been entered yet
        results = []
        for member_name, member in arg_model.members.items():
            if member_name not in entered_keys:
                display_text = '%s=%s' % (
                    member_name,
                    self._VALUE_PREFIXES.get(member.type_name, '')
                )
                results.append(CompletionResult(
                    last_key,
                    help_text=strip_html_tags(member.documentation),
                    cli_type_name=member.type_name,
                    display_text=display_text
                    )
                )
            results = self._filter(last_key, results)
        return results
