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
import logging
import os
import sys

from awscli.autocomplete import (
    completer,
    custom,
    db,
    filters,
    parser,
    serverside,
)
from awscli.autocomplete.local import basic, fetcher, model

LOG = logging.getLogger(__name__)


def create_autocompleter(
    index_filename=None,
    custom_completers=None,
    driver=None,
    response_filter=None,
):
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
        basic.ModelIndexCompleter(
            index, cli_driver_fetcher, response_filter=response_filter
        ),
        basic.FilePathCompleter(response_filter=response_filter),
        serverside.create_server_side_completer(
            index_filename, response_filter=response_filter
        ),
        basic.ShorthandCompleter(
            cli_driver_fetcher, response_filter=response_filter
        ),
        basic.QueryCompleter(
            cli_driver_fetcher, response_filter=response_filter
        ),
    ] + custom_completers
    cli_completer = completer.AutoCompleter(cli_parser, completers)
    return cli_completer


def refresh_user_index(
    index_filename=None, builtin_index_filename=None, models_dir=None
):
    """Rebuild the user completion index if custom models changed.

    Models installed with ``aws configure add-model`` live in
    ``~/.aws/models``.  The user index (``~/.aws/cli/cache/<version>.index``)
    is the bundled index plus those models, and it records a fingerprint of
    the models it was built from.  When the fingerprint no longer matches
    (a model was added, replaced or removed, or the CLI was upgraded and
    there is no index for the new version yet), the index is rebuilt here,
    on the next completion.

    When no custom models are installed and there is no user index, this
    only lists ``~/.aws/models``.  Otherwise it also reads one row from the
    user index.  A rebuild takes a fraction of a second because it starts
    from the bundled index, so nothing is rebuilt if the bundled index is
    missing (as in a source checkout).  If it fails, completion falls back to the bundled
    index and a marker file prevents retrying on every Tab press until the
    installed models change again.
    """
    if index_filename is None:
        index_filename = db.INDEX_FILE
    if builtin_index_filename is None:
        builtin_index_filename = db.BUILTIN_INDEX_FILE
    fingerprint = db.custom_models_fingerprint(
        db.list_custom_models(models_dir)
    )
    indexed = db.get_index_custom_models_fingerprint(index_filename)
    if indexed == fingerprint:
        return
    if not os.path.isfile(builtin_index_filename):
        return
    marker = _failure_marker_filename(index_filename)
    if _read_file(marker) == fingerprint:
        return
    if not _is_writable_location(index_filename):
        return
    # Imported lazily because it loads botocore and the full CLI, which is
    # only needed when the index has to be rebuilt.
    from awscli.autocomplete import generator

    try:
        generator.update_user_index(
            index_filename=index_filename,
            builtin_index_filename=builtin_index_filename,
        )
    except Exception:
        LOG.debug('Unable to update completion index', exc_info=True)
        _write_file(marker, fingerprint)
        return
    _remove_file(marker)


def _failure_marker_filename(index_filename):
    return f'{index_filename}.failed'


def _read_file(filename):
    try:
        with open(filename) as f:
            return f.read()
    except OSError:
        return None


def _write_file(filename, contents):
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            f.write(contents)
    except OSError:
        pass


def _remove_file(filename):
    try:
        os.remove(filename)
    except OSError:
        pass


def _is_writable_location(filename):
    path = os.path.dirname(os.path.abspath(filename))
    while not os.path.isdir(path):
        parent = os.path.dirname(path)
        if parent == path:
            return False
        path = parent
    return os.access(path, os.W_OK)


def autocomplete(command_line, position=None):
    refresh_user_index()
    completer = create_autocompleter()
    results = completer.autocomplete(command_line, position)
    # On Windows, stdout translates "\n" to "\r\n", and shells such as
    # Git Bash keep the trailing "\r" as part of each completion.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(newline='\n')
    print("\n".join([result.name for result in results]))
