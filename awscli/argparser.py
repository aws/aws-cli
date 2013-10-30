# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import argparse
from difflib import get_close_matches


class CLIArgParser(argparse.ArgumentParser):
    Formatter = argparse.RawTextHelpFormatter

    # When displaying invalid choice error messages,
    # this controls how many options to show per line.
    ChoicesPerLine = 2

    def _check_value(self, action, value):
        """
        It's probably not a great idea to override a "hidden" method
        but the default behavior is pretty ugly and there doesn't
        seem to be any other way to change it.
        """
        # converted value must be one of the choices (if specified)
        if action.choices is not None and value not in action.choices:
            msg = ['Invalid choice, valid choices are:\n']
            for i in range(len(action.choices))[::self.ChoicesPerLine]:
                current = []
                for choice in action.choices[i:i+self.ChoicesPerLine]:
                    current.append('%-40s' % choice)
                msg.append(' | '.join(current))
            possible = get_close_matches(value, action.choices, cutoff=0.8)
            if possible:
                extra = ['\n\nInvalid choice: %r, maybe you meant:\n' % value]
                for word in possible:
                    extra.append('  * %s' % word)
                msg.extend(extra)
            raise argparse.ArgumentError(action, '\n'.join(msg))


class MainArgParser(CLIArgParser):
    Formatter = argparse.RawTextHelpFormatter

    def __init__(self, command_table, version_string,
                 description, usage, argument_table):
        super(MainArgParser, self).__init__(
            formatter_class=self.Formatter,
            add_help=False,
            conflict_handler='resolve',
            description=description,
            usage=usage)
        self._build(command_table, version_string, argument_table)

    def _create_choice_help(self, choices):
        help_str = ''
        for choice in sorted(choices):
            help_str += '* %s\n' % choice
        return help_str

    def _build(self, command_table, version_string, argument_table):
        for argument_name in argument_table:
            argument = argument_table[argument_name]
            argument.add_to_parser(self)
        self.add_argument('--version', action="version",
                          version=version_string,
                          help='Display the version of this tool')
        self.add_argument('command', choices=list(command_table.keys()))


class ServiceArgParser(CLIArgParser):

    Usage = ("aws [options] <command> <subcommand> [parameters]")

    def __init__(self, operations_table, service_name):
        super(ServiceArgParser, self).__init__(
            formatter_class=argparse.RawTextHelpFormatter,
            add_help=False,
            conflict_handler='resolve',
            usage=self.Usage)
        self._build(operations_table)
        self._service_name = service_name

    def _build(self, operations_table):
        self.add_argument('operation', choices=list(operations_table.keys()))


class ArgTableArgParser(CLIArgParser):
    """CLI arg parser based on an argument table."""
    Usage = ("aws [options] <command> <subcommand> [parameters]")

    def __init__(self, argument_table):
        super(ArgTableArgParser, self).__init__(
            formatter_class=self.Formatter,
            add_help=False,
            usage=self.Usage,
            conflict_handler='resolve')
        self._build(argument_table)

    def _build(self, argument_table):
        for arg_name in argument_table:
            argument = argument_table[arg_name]
            argument.add_to_parser(self)

    def parse_known_args(self, args, namespace=None):
        if len(args) == 1 and args[0] == 'help':
            namespace = argparse.Namespace()
            namespace.help = 'help'
            return namespace, []
        else:
            return super(ArgTableArgParser, self).parse_known_args(
                args, namespace)
