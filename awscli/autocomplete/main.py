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

from awscli.autocomplete import parser, completer, filters
from awscli.autocomplete.local import model, basic, fetcher
from awscli.autocomplete import serverside
from awscli.autocomplete import custom


def create_autocompleter(index_filename=None, custom_completers=None,
                         driver=None, response_filter=None):
    if response_filter is None:
        response_filter = filters.startswith_filter
    if custom_completers is None:
        custom_completers = custom.get_custom_completers()
    index = model.ModelIndex(index_filename)
    cli_parser = parser.CLIParser(index)
    cli_driver_fetcher = None
    if driver is not None:
        cli_driver_fetcher = fetcher.CliDriverFetcher(driver)
    completers = [
        basic.RegionCompleter(response_filter=response_filter),
        basic.ProfileCompleter(response_filter=response_filter),
        basic.ModelIndexCompleter(index, cli_driver_fetcher,
                                  response_filter=response_filter),
        basic.FilePathCompleter(response_filter=response_filter),
        serverside.create_server_side_completer(
            index_filename, response_filter=response_filter),
        basic.ShorthandCompleter(cli_driver_fetcher,
                                 response_filter=response_filter),
        basic.QueryCompleter(cli_driver_fetcher,
                             response_filter=response_filter),
    ] + custom_completers
    cli_completer = completer.AutoCompleter(cli_parser, completers)
    return cli_completer


def autocomplete(command_line, position=None):
    completer = create_autocompleter()
    results = completer.autocomplete(command_line, position)
    print("\n".join([result.name for result in results]))
