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

LOG = logging.getLogger(__name__)


class Completer(object):

    def __init__(self):
        self.driver = awscli.clidriver.create_clidriver()
        self.main_hc = self.driver.create_help_command()
        self.main_options = [n for n in self.main_hc.arg_table]
        self.cmdline = None
        self.point = None
        self.command_hc = None
        self.subcommand_hc = None
        self.command_name = None
        self.subcommand_name = None
        self.current_word = None
        self.previous_word = None
        self.non_options = None

    def complete(self, cmdline, point):
        self.command_name = None
        if point is None:
            point = len(cmdline)
        self.point = point
        self.words = cmdline[0:point].split()
        self.current_word = self.words[-1]
        if len(self.words) >= 2:
            self.previous_word = self.words[-2]
        else:
            self.previous_word = None
        self.non_options = [w for w in self.words if not w.startswith('-')]
        # Look for a service name in the non_options
        for w in self.non_options:
            if w in self.main_hc.command_table:
                self.command_name = w
                break
        if not self.command_name:
            # If we didn't find any command names in the cmdline
            # lets try to complete provider options
            return self._complete_provider()
        return self._complete_command()

    def _find_possible_options(self, arg_table=None):
        all_options = self.main_options
        if arg_table:
            all_options = all_options + arg_table.keys()
        cw = self.current_word.lstrip('-')
        return ['--' + n for n in all_options if n.startswith(cw)]

    def _complete_provider(self):
        retval = []
        if self.current_word.startswith('-'):
            cw = self.current_word.lstrip('-')
            l = ['--' + n for n in self.main_options
                 if n.startswith(cw)]
            retval = l
        elif self.current_word == 'aws':
            retval = self.main_hc.command_table.keys()
        else:
            # Otherwise, see if they have entered a partial command name
            retval = [n for n in self.main_hc.command_table
                      if n.startswith(self.current_word)]
        return retval

    def _complete_command(self):
        retval = []
        self.subcommand_name = None
        self.command_hc = self.main_hc.command_table[self.command_name].create_help_command()
        # Look for complete subcommand name in cmdline
        for w in self.non_options:
            if w in self.command_hc.command_table:
                self.subcommand_name = w
                break
        if self.subcommand_name:
            return self._complete_subcommand()
        if self.current_word == self.command_name:
            retval = self.command_hc.command_table.keys()
        elif self.current_word.startswith('-'):
            retval = self._find_possible_options()
        else:
            # See if they have entered a partial command name
            retval = [n for n in self.command_hc.command_table
                      if n.startswith(self.current_word)]
        return retval

    def _complete_subcommand(self):
        retval = []
        self.subcommand_hc = self.command_hc.command_table[self.subcommand_name].create_help_command()
        if self.current_word == self.subcommand_name:
            retval = []
        elif self.current_word.startswith('-'):
            retval = self._find_possible_options(self.subcommand_hc.arg_table)
        return retval
        
if __name__ == '__main__':
    if len(sys.argv) == 3:
        cmdline = sys.argv[1]
        point = int(sys.argv[2])
    elif len(sys.argv) == 2:
        cmdline = sys.argv[1]
    else:
        print('usage: %s <cmdline> <point>' % sys.argv[0])
        sys.exit(1)
    completer = Completer()
    print(completer.complete(cmdline, point))
