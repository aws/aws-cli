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
"""This module has customizations to unify paging paramters.

For any operation that can be paginated, we will:

    * Remove the service specific pagination params.  This can vary across
    services and we're going to replace them with a consistent set of
    arguments.
    * Add a ``--starting-token`` and a ``--max-items`` argument.

"""
import logging

from awscli.arguments import BaseCLIArgument
from botocore.parameters import StringParameter

logger = logging.getLogger(__name__)


STARTING_TOKEN_HELP = """
<p>A token to specify where to start paginating.  This is the
<code>NextToken</code> from a previously truncated response.</p>
"""

MAX_ITEMS_HELP = """
<p>The total number of items to return.  If the total number
of items available is more than the value specified in
max-items then a <code>NextMarker</code> will
be provided in the output that you can use to resume pagination.
"""


def unify_paging_params(argument_table, operation, **kwargs):
    if not operation.can_paginate:
        # We only apply these customizations to paginated responses.
        return
    logger.debug("Modifying paging parameters for operation: %s", operation)
    _remove_existing_paging_arguments(argument_table, operation)
    argument_table['starting-token'] = PageArgument('starting-token',
                                                    STARTING_TOKEN_HELP,
                                                    operation,
                                                    parse_type='string')
    argument_table['max-items'] = PageArgument('max-items', MAX_ITEMS_HELP,
                                               operation, parse_type='integer')


def _remove_existing_paging_arguments(argument_table, operation):
    tokens = _get_input_tokens(operation)
    for token_name in tokens:
        cli_name = _get_cli_name(operation.params, token_name)
        del argument_table[cli_name]
    if 'limit_key' in operation.pagination:
        key_name = operation.pagination['limit_key']
        cli_name = _get_cli_name(operation.params, key_name)
        del argument_table[cli_name]


def _get_input_tokens(operation):
    config = operation.pagination
    tokens = config['input_token']
    if not isinstance(tokens, list):
        return [tokens]
    return tokens


def _get_cli_name(param_objects, token_name):
    for param in param_objects:
        if param.name == token_name:
            return param.cli_name.lstrip('-')


class PageArgument(BaseCLIArgument):
    type_map = {
        'string': str,
        'integer': int,
    }

    def __init__(self, name, documentation, operation, parse_type):
        param = StringParameter(operation, name=name, type=parse_type)
        self._name = name
        self.argument_object = param
        self._name = name
        self._documentation = documentation
        self._parse_type = parse_type

    @property
    def cli_name(self):
        return '--' + self._name

    @property
    def cli_type_name(self):
        return self._parse_type

    @property
    def required(self):
        return False

    @property
    def documentation(self):
        return self._documentation

    def add_to_parser(self, parser):
        parser.add_argument(self.cli_name, dest=self.py_name,
                            type=self.type_map[self._parse_type])

    def add_to_params(self, parameters, value):
        if value is not None:
            parameters[self.py_name] = value
