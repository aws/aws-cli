# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import logging
import json
import os

from prompt_toolkit.completion import Completion, Completer
from prompt_toolkit.history import FileHistory

from awscli.autocomplete.completer import CompletionResult
from awscli.autocomplete.filters import fuzzy_filter


LOG = logging.getLogger(__name__)


class HistoryDriver(FileHistory):
    HISTORY_VERSION = 1

    def __init__(self, filename, max_commands=500):
        super().__init__(filename)
        self._max_commands = max_commands

    def load_history_strings(self):
        try:
            with open(self.filename, 'r') as f:
                commands = json.load(f).get('commands', [])
            return reversed(commands)
        except Exception as e:
            LOG.debug('Exception on loading prompt history: %s' % e,
                      exc_info=True)
            return []

    def store_string(self, string):
        history = {'version': self.HISTORY_VERSION, 'commands': []}
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    history = json.load(f)
            elif not os.path.exists(os.path.dirname(self.filename)):
                os.makedirs(os.path.dirname(self.filename))
            history['commands'].append(string)
            history['commands'] = history['commands'][-self._max_commands:]
            with open(self.filename, 'w') as f:
                json.dump(history, f)
        except Exception:
            LOG.debug('Exception on loading prompt history:', exc_info=True)


class HistoryCompleter(Completer):

    def __init__(self, buffer):
        self.buffer = buffer
        self.working_lines = buffer.history.get_strings()

    def get_completions(self, document, *args):
        found_completions = set()
        completions = []
        current_line = document.current_line_before_cursor.lstrip()
        try:
            # going backwards from newest commands to oldest
            for line in self.working_lines[::-1]:
                s_line = line.strip()
                if s_line and s_line not in found_completions:
                    found_completions.add(s_line)
                    completions.append(CompletionResult(
                        s_line,
                        starting_index=-len(current_line)))
            if current_line:
                completions = fuzzy_filter(current_line, completions)
            yield from (Completion(c.name, start_position=c.starting_index)
                        for c in completions)
        except Exception:
            LOG.debug('Exception on loading prompt history:', exc_info=True)
