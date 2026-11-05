# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


def help_requested(parsed_globals):
    """Return True if --help was given.

    The main parser sets ``help`` to True or False. Anything else, such as
    an attribute of a mock or another stand-in object, is not a request.
    """
    return getattr(parsed_globals, 'help', False) is True


def call_command(command, args, parsed_globals):
    """Call a command, giving it ``--help`` if it needs it.

    The main parser consumes ``--help`` as a global argument and sets
    ``parsed_globals.help``. Commands that check that value set
    ``_HANDLES_HELP_FLAG = True``. Other commands, such as plugins and
    external aliases, get ``--help`` added back to their arguments, as
    they received it before ``--help`` was a global argument.
    """
    if help_requested(parsed_globals) and not getattr(
        command, '_HANDLES_HELP_FLAG', False
    ):
        args = list(args) + ['--help']
    return command(args, parsed_globals)


class CLICommand:
    """Interface for a CLI command.

    This class represents a top level CLI command
    (``aws ec2``, ``aws s3``, ``aws config``).

    """

    # Internal to the CLI's command classes, which set it to True
    # because their __call__ renders help when parsed_globals.help is
    # set. Other commands, such as plugins, leave it unset and receive
    # --help in their arguments.
    _HANDLES_HELP_FLAG = False

    @property
    def name(self):
        # Subclasses must implement a name.
        raise NotImplementedError("name")

    @name.setter
    def name(self, value):
        # Subclasses must implement setting/changing the cmd name.
        raise NotImplementedError("name")

    @property
    def lineage(self):
        # Represents how to get to a specific command using the CLI.
        # It includes all commands that came before it and itself in
        # a list.
        return [self]

    @property
    def lineage_names(self):
        # Represents the lineage of a command in terms of command ``name``
        return [cmd.name for cmd in self.lineage]

    def __call__(self, args, parsed_globals):
        """Invoke CLI operation.

        :type args: str
        :param args: The remaining command line args.

        :type parsed_globals: ``argparse.Namespace``
        :param parsed_globals: The parsed arguments so far.

        :rtype: int
        :return: The return code of the operation.  This will be used
            as the RC code for the ``aws`` process.

        """
        # Subclasses are expected to implement this method.
        pass

    def create_help_command(self):
        # Subclasses are expected to implement this method if they want
        # help docs.
        return None

    @property
    def arg_table(self):
        return {}
