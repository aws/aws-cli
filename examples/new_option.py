# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""
Add a new top-level option
--------------------------

This example adds a new top-level option called ``--foobar``.
"""
from awscli.clidriver import BuiltInArgument

# TODO
# Not sure that we want people to have to understand and insert
# markup.  It's probably best to remove the markup from the options
# in cli.json and then change the doc code to do the right formatting.
HELP = "<p>This will enable the dreaded foobar mode.</p>"


def add_arg(argument_table, **kwargs):
    """
    This is our event handler.  It will get called as the top-level
    parameters are getting built.  We can add our custom options to
    the ``argument_table``.  The easiest way to do this is to just
    create an instance of the ``BuiltInArgument`` class defined in
    ``clidriver.py``.
    """
    # When we create the new BuiltInArgument, we pass in it's name
    # and, optionally, any additional parameters we want to pass to
    # argparse when this argument is added to the parser.  Since we
    # want this to be a boolean option, we do need to do some extra
    # configuration.
    # Also, if you want to add a help string that gets printed
    # when the user does ``aws help`` you should add that to the
    # dictionary, too.
    argument = BuiltInArgument('foobar', {'action': 'store_true',
                                          'help': HELP})
    argument.add_to_arg_table(argument_table)


def do_foobar(parsed_args, **kwargs):
    # Should this be called with something more than just the
    # parsed_args?  How about a session or a CLIDriver object?
    if parsed_args.foobar:
        print('Enable foobar mode here')


def awscli_initialize(cli):
    cli.register('building-top-level-params', handler=add_arg)
    cli.register('top-level-args-parsed', handler=do_foobar)
