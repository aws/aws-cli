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


# This is the main entry point for auto-completion.  This is imported
# everytime a user hits <TAB>.  Try to avoid any expensive module level
# work or really heavyweight imports.  Prefer to lazy load as much as possible.
import os

from awscli import __version__ as cli_version
from awscli.autocomplete import parser, completer
from awscli.autocomplete.local import model, basic
from awscli.autocomplete import serverside
from awscli.autocomplete import custom


# We may eventually include a pre-generated version of this index as part
# of our shipped distributable, but for now we'll add this to our cache
# dir.
INDEX_DIR = os.path.expanduser(os.path.join('~', '.aws', 'cli', 'cache'))
INDEX_FILE = os.path.join(INDEX_DIR, '%s.index' % cli_version)
BUILTIN_INDEX_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'ac.index'
)


def create_autocompleter(index_filename=None, custom_completers=None):
    if custom_completers is None:
        custom_completers = custom.get_custom_completers()
    if index_filename is None:
        index_filename = _get_index_filename()
    index = model.ModelIndex(index_filename)
    cli_parser = parser.CLIParser(index)
    completers = [
        basic.ModelIndexCompleter(index),
        serverside.create_server_side_completer(index_filename)
    ] + custom_completers
    cli_completer = completer.AutoCompleter(cli_parser, completers)
    return cli_completer


def _get_index_filename():
    if os.path.isfile(INDEX_FILE):
        return INDEX_FILE
    return BUILTIN_INDEX_FILE


def autocomplete(command_line, position=None):
    completer = create_autocompleter()
    results = completer.autocomplete(command_line, position)
    print("\n".join([result.result for result in results]))
