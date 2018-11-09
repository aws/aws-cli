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
