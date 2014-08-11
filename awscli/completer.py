# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at

#     http://aws.amazon.com/apache2.0/

# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import awscli.clidriver
import sys
import logging
import copy

LOG = logging.getLogger(__name__)


class Completer(object):

    def __init__(self):
        self.driver = awscli.clidriver.create_clidriver()
        self.main_hc = self.driver.create_help_command()
        self.main_options = self._documented(self.main_hc.arg_table)
        self.cmdline = None
        self.point = None
        self.command_hc = None
        self.subcommand_hc = None
        self.command_name = None
        self.subcommand_name = None
        self.current_word = None
        self.previous_word = None
        self.non_options = None

    def _complete_option(self, option_name):
        if option_name == '--endpoint-url':
            return []
        if option_name == '--output':
            cli_data = self.driver.session.get_data('cli')
            return cli_data['options']['output']['choices']
        if option_name == '--profile':
            return self.driver.session.available_profiles
        return []

    def _complete_provider(self):
        retval = []
        if self.current_word.startswith('-'):
            cw = self.current_word.lstrip('-')
            l = ['--' + n for n in self.main_options
                 if n.startswith(cw)]
            retval = l
        elif self.current_word == 'aws':
            retval = self._documented(self.main_hc.command_table)
        else:
            # Otherwise, see if they have entered a partial command name
            retval = self._documented(self.main_hc.command_table,
                                      startswith=self.current_word)
        return retval

    def _complete_command(self):
        retval = []
        if self.current_word == self.command_name:
            if self.command_hc:
                retval = self._documented(self.command_hc.command_table)
        elif self.current_word.startswith('-'):
            retval = self._find_possible_options()
        else:
            # See if they have entered a partial command name
            if self.command_hc:
                retval = self._documented(self.command_hc.command_table,
                                          startswith=self.current_word)
        return retval

    def _documented(self, table, startswith=None):
        names = []
        for key, command in table.items():
            if getattr(command, '_UNDOCUMENTED', False):
                # Don't tab complete undocumented commands/params
                continue
            if startswith is not None and not key.startswith(startswith):
                continue
            if getattr(command, 'positional_arg', False):
                continue
            names.append(key)
        return names

    def _complete_subcommand(self):
        retval = []
        if self.current_word == self.subcommand_name:
            retval = []
        elif self.current_word.startswith('-'):
            retval = self._find_possible_options()
        return retval

    def _find_possible_options(self):
        all_options = copy.copy(self.main_options)
        if self.subcommand_hc:
            all_options = all_options + self._documented(self.subcommand_hc.arg_table)
        for opt in self.options:
            # Look thru list of options on cmdline. If there are
            # options that have already been specified and they are
            # not the current word, remove them from list of possibles.
            if opt != self.current_word:
                stripped_opt = opt.lstrip('-')
                if stripped_opt in all_options:
                    all_options.remove(stripped_opt)
        cw = self.current_word.lstrip('-')
        possibles = ['--' + n for n in all_options if n.startswith(cw)]
        if len(possibles) == 1 and possibles[0] == self.current_word:
            return self._complete_option(possibles[0])
        return possibles

    def _process_command_line(self):
        # Process the command line and try to find:
        #     - command_name
        #     - subcommand_name
        #     - words
        #     - current_word
        #     - previous_word
        #     - non_options
        #     - options
        self.command_name = None
        self.subcommand_name = None
        self.words = self.cmdline[0:self.point].split()
        self.current_word = self.words[-1]
        if len(self.words) >= 2:
            self.previous_word = self.words[-2]
        else:
            self.previous_word = None
        self.non_options = [w for w in self.words if not w.startswith('-')]
        self.options = [w for w in self.words if w.startswith('-')]
        # Look for a command name in the non_options
        for w in self.non_options:
            if w in self.main_hc.command_table:
                self.command_name = w
                cmd_obj = self.main_hc.command_table[self.command_name]
                self.command_hc = cmd_obj.create_help_command()
                if self.command_hc and self.command_hc.command_table:
                    # Look for subcommand name
                    for w in self.non_options:
                        if w in self.command_hc.command_table:
                            self.subcommand_name = w
                            cmd_obj = self.command_hc.command_table[self.subcommand_name]
                            self.subcommand_hc = cmd_obj.create_help_command()
                            break
                break

    def complete(self, cmdline, point):
        self.cmdline = cmdline
        self.command_name = None
        if point is None:
            point = len(cmdline)
        self.point = point
        self._process_command_line()
        if not self.command_name:
            # If we didn't find any command names in the cmdline
            # lets try to complete provider options
            return self._complete_provider()
        if self.command_name and not self.subcommand_name:
            return self._complete_command()
        return self._complete_subcommand()


def complete(cmdline, point):
    choices = Completer().complete(cmdline, point)
    print(' \n'.join(choices))


if __name__ == '__main__':
    if len(sys.argv) == 3:
        cmdline = sys.argv[1]
        point = int(sys.argv[2])
    elif len(sys.argv) == 2:
        cmdline = sys.argv[1]
    else:
        print('usage: %s <cmdline> <point>' % sys.argv[0])
        sys.exit(1)
    print(complete(cmdline, point))
