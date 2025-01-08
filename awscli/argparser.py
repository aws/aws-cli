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
import copy
import sys
from difflib import get_close_matches


HELP_BLURB = (
    "To see help text, you can run:\n"
    "\n"
    "  aws help\n"
    "  aws <command> help\n"
    "  aws <command> <subcommand> help\n"
)
USAGE = (
    "aws [options] <command> <subcommand> [<subcommand> ...] [parameters]\n"
    "%s" % HELP_BLURB
)


class ArgParseException(Exception):
    pass


class CommandAction(argparse.Action):
    """Custom action for CLI command arguments

    Allows the choices for the argument to be mutable. The choices
    are dynamically retrieved from the keys of the referenced command
    table
    """
    def __init__(self, option_strings, dest, command_table, **kwargs):
        self.command_table = command_table
        super(CommandAction, self).__init__(
            option_strings, dest, choices=self.choices, **kwargs
        )

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)

    @property
    def choices(self):
        return list(self.command_table.keys())

    @choices.setter
    def choices(self, val):
        # argparse.Action will always try to set this value upon
        # instantiation, but this value should be dynamically
        # generated from the command table keys. So make this a
        # NOOP if argparse.Action tries to set this value.
        pass


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

    def parse_known_args(self, args, namespace=None):
        parsed, remaining = super(CLIArgParser, self).parse_known_args(args, namespace)
        terminal_encoding = getattr(sys.stdin, 'encoding', 'utf-8')
        if terminal_encoding is None:
            # In some cases, sys.stdin won't have an encoding set,
            # (e.g if it's set to a StringIO).  In this case we just
            # default to utf-8.
            terminal_encoding = 'utf-8'
        for arg, value in vars(parsed).items():
            if isinstance(value, bytes):
                setattr(parsed, arg, value.decode(terminal_encoding))
            elif isinstance(value, list):
                encoded = []
                for v in value:
                    if isinstance(v, bytes):
                        encoded.append(v.decode(terminal_encoding))
                    else:
                        encoded.append(v)
                setattr(parsed, arg, encoded)
        return parsed, remaining

    def error(self, message):
        """error(message: string)

        NOTE: This is lifted directly from argparse, the only difference being
        we use 252 for parsing errors.

        Raises exception with a usage message incorporating the message.

        If you override this in a subclass, it should not return -- it
        should raise an exception.
        """
        usage_message = self.format_usage()
        error_message = f'{self.prog}: error: {message}\n'
        raise ArgParseException(f'{usage_message}\n{error_message}')


class MainArgParser(CLIArgParser):
    Formatter = argparse.RawTextHelpFormatter

    def __init__(self, command_table, version_string,
                 description, argument_table, prog=None):
        super(MainArgParser, self).__init__(
            formatter_class=self.Formatter,
            add_help=False,
            conflict_handler='resolve',
            description=description,
            usage=USAGE,
            prog=prog)
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
        self.add_argument('command', action=CommandAction,
                          command_table=command_table)


class ServiceArgParser(CLIArgParser):

    def __init__(self, operations_table, service_name):
        super(ServiceArgParser, self).__init__(
            formatter_class=argparse.RawTextHelpFormatter,
            add_help=False,
            conflict_handler='resolve',
            usage=USAGE)
        self._build(operations_table)
        self._service_name = service_name

    def _build(self, operations_table):
        self.add_argument('operation', action=CommandAction,
                          command_table=operations_table)


class ArgTableArgParser(CLIArgParser):
    """CLI arg parser based on an argument table."""

    def __init__(self, argument_table, command_table=None):
        # command_table is an optional subcommand_table.  If it's passed
        # in, then we'll update the argparse to parse a 'subcommand' argument
        # and populate the choices field with the command table keys.
        super(ArgTableArgParser, self).__init__(
            formatter_class=self.Formatter,
            add_help=False,
            usage=USAGE,
            conflict_handler='resolve')
        if command_table is None:
            command_table = {}
        self._build(argument_table, command_table)

    def _build(self, argument_table, command_table):
        for arg_name in argument_table:
            argument = argument_table[arg_name]
            argument.add_to_parser(self)
        if command_table:
            self.add_argument('subcommand', action=CommandAction,
                              command_table=command_table, nargs='?')

    def parse_known_args(self, args, namespace=None):
        if len(args) == 1 and args[0] == 'help':
            namespace = argparse.Namespace()
            namespace.help = 'help'
            return namespace, []
        else:
            return super(ArgTableArgParser, self).parse_known_args(
                args, namespace)


class SubCommandArgParser(ArgTableArgParser):
    """Parse args for a subcommand but do not consume the arg table.

    This is similar to the ArgTableArgParser, except it doesn't consume
    any args from the provided arg table, though it will respect the
    arg table when looking for a subcommand.

    """

    def parse_known_args(self, args, namespace=None):
        parsed_args, remaining = super(
            SubCommandArgParser, self).parse_known_args(args, namespace)
        if getattr(parsed_args, 'subcommand', None) is not None:
            new_args = self._remove_subcommand(args, parsed_args)
            return new_args, parsed_args.subcommand
        return None

    def _remove_subcommand(self, args, parsed_args):
        # We want to remove only the subcommand from the args list
        # and keep everything else.  We should be safe to remove
        # the first argument that matches the subcommand name.
        #
        # .parse_known_args() assumes that any args that it doesn't
        # understand do not consume any values.  For example:
        #
        # aws ecs --cluster mycluster describe-tasks --tasks foo
        #
        # is not a valid command, because we ignore `--cluster`
        # and assume that `mycluster` is a subcommand.
        #
        # However, this command works:
        #
        # aws ecs --cluster=mycluster desribe-tasks --tasks foo
        #
        # Therefore we don't have to worry about the case where
        # a param *value* shadows the parsed subcommand because
        # the existing parser would have already errored out.
        new_args = args[:]
        new_args.remove(parsed_args.subcommand)
        return new_args

    def _build(self, argument_table, command_table):
        # In order to check for a subcommand while still respecting
        # the arg table, we do need to consider the arg table, but not
        # fail if any of the required args aren't provided.  We don't
        # want to mutate the arg table that's provided to us, so we
        # make a copy of it and then set all the required to not required.
        non_required_arg_table = self._non_required_arg_table(
            argument_table)
        for arg_name in non_required_arg_table:
            argument = non_required_arg_table[arg_name]
            argument.add_to_parser(self)
        if command_table:
            self.add_argument('subcommand', action=CommandAction,
                              command_table=command_table, nargs='?')

    def _non_required_arg_table(self, argument_table):
        arg_table_copy = {}
        for key, value in argument_table.items():
            copied = copy.copy(value)
            copied.required = False
            arg_table_copy[key] = copied
        return arg_table_copy


class FirstPassGlobalArgParser(CLIArgParser):
    def __init__(self, *args, **kwargs):
        kwargs['add_help'] = False
        super().__init__(*args, **kwargs)
        self._build()

    def _build(self):
        self.add_argument('--profile', type=str)
        self.add_argument('--debug', action='store_true', default=False)
