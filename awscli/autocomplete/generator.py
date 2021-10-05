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
import os

from awscli.autocomplete.local import indexer
from awscli.autocomplete.serverside.indexer import APICallIndexer
from awscli.autocomplete import db
from awscli import clidriver


def generate_index(filename):
    """Generates the default auto-complete index"""
    filename = os.path.abspath(filename)
    index_dir = os.path.dirname(filename)
    if not os.path.isdir(index_dir):
        os.makedirs(index_dir)

    # Using a temporary name so if the index already exists, we'll
    # only replace the entire file once we successfully regenerate the
    # index.
    temp_name = f'{filename}.temp'
    try:
        _do_generate_index(temp_name)
    except BaseException:
        if os.path.exists(temp_name):
            os.remove(temp_name)
        raise

    os.rename(temp_name, filename)
    return filename


def _do_generate_index(filename):
    db_connection = db.DatabaseConnection(filename)
    indexers = [
        indexer.ModelIndexer(db_connection),
        APICallIndexer(db_connection),
    ]
    driver = clidriver.create_clidriver()
    index_gen = IndexGenerator(indexers=indexers)
    try:
        index_gen.generate_index(driver)
    finally:
        db_connection.close()


class IndexGenerator(object):
    """Generates auto completion index.

    This will generate an auto completion index for all the low level
    indexer used by the CLI.  This object primarily delegates to other
    objects that do the actual heavy lifting of generating auto completion
    indices.

    """
    def __init__(self, indexers):
        self._indexers = indexers

    def generate_index(self, clidriver):
        for indexer in self._indexers:
            indexer.generate_index(clidriver)
