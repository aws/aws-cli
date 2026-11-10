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
"""Generates auto completion index."""

import contextlib
import logging
import os
import shutil
import tempfile
import time

from awscli import clidriver
from awscli.autocomplete import db
from awscli.autocomplete.local import indexer
from awscli.autocomplete.serverside.indexer import APICallIndexer
from awscli.compat import is_windows

LOG = logging.getLogger(__name__)

# Windows does not allow replacing a file that another process (such as a
# running completer) has open, so the final rename is retried briefly.
_REPLACE_ATTEMPTS = 50
_REPLACE_RETRY_INTERVAL = 0.1


def generate_index(filename):
    """Generates the default auto-complete index"""
    filename = os.path.abspath(filename)
    _ensure_parent_dir(filename)
    # The index is generated under a unique temporary name and only moved
    # into place once it is complete, so readers never see a partial index.
    with _temporary_index(filename) as temp_name:
        _do_generate_index(temp_name)
    return filename


def update_user_index(index_filename=None, builtin_index_filename=None):
    """Regenerate the user's completion index to include custom models.

    The user index (``~/.aws/cli/cache/<cli-version>.index`` by default)
    starts as a copy of the bundled index.  Every top level command whose
    service has a model in ``~/.aws/models`` is then removed and reindexed
    from the CLI command tree, so entries from replaced or removed models
    never linger and overridden builtin services are not duplicated.

    The index records a fingerprint of the models it was built from so the
    completer can tell when it is out of date.  The fingerprint is taken
    before any model is loaded, so if models change during the update (for
    example, a concurrent ``add-model`` or another update) the index is
    simply rebuilt on the next completion.  The new index atomically
    replaces the old one.
    """
    if index_filename is None:
        index_filename = db.INDEX_FILE
    if builtin_index_filename is None:
        builtin_index_filename = db.BUILTIN_INDEX_FILE
    index_filename = os.path.abspath(index_filename)
    models = db.list_custom_models()
    driver = clidriver.create_clidriver()
    custom_services = {model[0] for model in models}
    command_names = sorted(
        name
        for name, command in driver.subcommand_table.items()
        if isinstance(command, clidriver.ServiceCommand)
        and command.service_name in custom_services
    )
    _ensure_parent_dir(index_filename)
    with _temporary_index(index_filename) as temp_name:
        shutil.copyfile(builtin_index_filename, temp_name)
        db_connection = db.DatabaseConnection(temp_name)
        try:
            db_connection.execute('BEGIN')
            _create_index_generator(db_connection).reindex_commands(
                driver, command_names
            )
            db_connection.execute(
                'CREATE TABLE IF NOT EXISTS index_metadata '
                '(key TEXT PRIMARY KEY, value TEXT)'
            )
            db_connection.execute(
                'INSERT OR REPLACE INTO index_metadata (key, value) '
                'VALUES (:key, :value)',
                key=db.CUSTOM_MODELS_KEY,
                value=db.custom_models_fingerprint(models),
            )
            db_connection.execute('COMMIT')
        finally:
            db_connection.close()


def _do_generate_index(filename):
    db_connection = db.DatabaseConnection(filename)
    driver = clidriver.create_clidriver()
    index_gen = _create_index_generator(db_connection)
    try:
        db_connection.execute('BEGIN')
        index_gen.generate_index(driver)
        db_connection.execute('COMMIT')
    finally:
        db_connection.close()


def _create_index_generator(db_connection):
    return IndexGenerator(
        indexers=[
            indexer.ModelIndexer(db_connection),
            APICallIndexer(db_connection),
        ]
    )


def _ensure_parent_dir(filename):
    # exist_ok because concurrent processes may create it at the same time.
    os.makedirs(os.path.dirname(filename), exist_ok=True)


@contextlib.contextmanager
def _temporary_index(filename):
    fd, temp_name = tempfile.mkstemp(
        dir=os.path.dirname(filename),
        prefix=f'{os.path.basename(filename)}.',
        suffix='.temp',
    )
    os.close(fd)
    try:
        yield temp_name
        _replace(temp_name, filename)
    except BaseException:
        if os.path.exists(temp_name):
            os.remove(temp_name)
        raise


def _replace(source, destination):
    for attempt in range(_REPLACE_ATTEMPTS):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if not is_windows or attempt == _REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(_REPLACE_RETRY_INTERVAL)


class IndexGenerator:
    """Generates auto completion index.

    This will generate an auto completion index for all the low level
    indexer used by the CLI.  This object primarily delegates to other
    objects that do the actual heavy lifting of generating auto completion
    indices.

    """

    def __init__(self, indexers):
        self._indexers = indexers

    def generate_index(self, clidriver):
        for index_builder in self._indexers:
            index_builder.generate_index(clidriver)

    def reindex_commands(self, clidriver, command_names):
        """Replace the index entries for the given top level commands."""
        # Removal runs in reverse so dependent tables (e.g. apicall_table)
        # are cleaned up before the rows they reference.
        for index_builder in reversed(self._indexers):
            index_builder.remove_commands(command_names)
        for index_builder in self._indexers:
            index_builder.index_commands(clidriver, command_names)
