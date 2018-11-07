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
import logging

import awscli.customizations.dynamodb.params as params
from awscli.clidriver import CLIOperationCaller
from awscli.customizations.commands import BasicCommand, CustomArgument
from awscli.customizations.paginate import ensure_paging_params_not_set


LOGGER = logging.getLogger(__name__)


class DDBCommand(BasicCommand):
    def _run_main(self, parsed_args, parsed_globals):
        # Only YAML is supported because we need to support bytes and sets.
        if parsed_globals.output != 'yaml':
            LOGGER.debug(
                'Output was %s, but only yaml is supported. Switching to '
                'yaml.' % parsed_globals.output
            )
            parsed_globals.output = 'yaml'
        self._caller = CLIOperationCaller(self._session)

    def _run_operation(self, operation_name, parsed_args, parsed_globals):
        if not parsed_globals.paginate:
            ensure_paging_params_not_set(parsed_args, {})
        client_args = self._get_client_args(parsed_args)
        self._caller.invoke(
            'dynamodb', operation_name, client_args, parsed_globals
        )

    def _get_client_args(self, parsed_args):
        raise NotImplementedError('_get_client_args')


class PaginatedDDBCommand(DDBCommand):
    PAGING_ARGS = [
        params.STARTING_TOKEN, params.MAX_ITEMS, params.PAGE_SIZE
    ]

    def _build_arg_table(self):
        arg_table = super(PaginatedDDBCommand, self)._build_arg_table()
        for arg_data in self.PAGING_ARGS:
            paging_arg = CustomArgument(**arg_data)
            arg_table[arg_data['name']] = paging_arg
        return arg_table

    def _get_client_args(self, parsed_args):
        pagination_config = {}
        if parsed_args.starting_token:
            pagination_config['StartingToken'] = parsed_args.starting_token
        if parsed_args.max_items:
            pagination_config['MaxItems'] = parsed_args.max_items
        if parsed_args.page_size:
            pagination_config['PageSize'] = parsed_args.page_size

        args = {}
        if pagination_config:
            args['PaginationConfig'] = pagination_config
        return args


class SelectCommand(PaginatedDDBCommand):
    NAME = 'select'
    DESCRIPTION = (
        '``select`` searches a table or index.\n\n'
        'Under the hood, this operation will use ``query`` if '
        '``--key-condition`` is specified, or ``scan`` otherwise.'
    )
    ARG_TABLE = [
        params.TABLE_NAME,
        params.INDEX_NAME,
        params.PROJECTION_EXPRESSION,
        params.FILTER_EXPRESSION,
        params.KEY_CONDITION_EXPRESSION,
        params.SELECT,
        params.CONSISTENT_READ, params.NO_CONSISTENT_READ,
        params.RETURN_CONSUMED_CAPACITY, params.NO_RETURN_CONSUMED_CAPACITY,
    ]

    def _run_main(self, parsed_args, parsed_globals):
        super(SelectCommand, self)._run_main(parsed_args, parsed_globals)
        self._select(parsed_args, parsed_globals)
        return 0

    def _select(self, parsed_args, parsed_globals):
        if parsed_args.key_condition:
            LOGGER.debug(
                "select command using query because --key-condition was "
                "specified"
            )
            operation = 'query'
        else:
            LOGGER.debug(
                "select command using scan because --key-condition was not "
                "specified"
            )
            operation = 'scan'
        self._run_operation(operation, parsed_args, parsed_globals)

    def _get_client_args(self, parsed_args):
        client_args = super(SelectCommand, self)._get_client_args(parsed_args)
        client_args.update({
            'TableName': parsed_args.table_name,
            'ConsistentRead': parsed_args.consistent_read,
        })
        if parsed_args.index_name is not None:
            client_args['IndexName'] = parsed_args.index_name
        if parsed_args.projection is not None:
            client_args['ProjectionExpression'] = parsed_args.projection
        if parsed_args.filter is not None:
            client_args['FilterExpression'] = parsed_args.filter
        if parsed_args.key_condition is not None:
            client_args['KeyConditionExpression'] = parsed_args.key_condition
        if parsed_args.attributes is not None:
            select_map = {
                'ALL': 'ALL_ATTRIBUTES',
                'ALL_PROJECTED': 'ALL_PROJECTED_ATTRIBUTES',
            }
            attrs = parsed_args.attributes
            client_args['Select'] = select_map.get(attrs, attrs)

        if parsed_args.return_consumed_capacity:
            # Only return index info when using an index.
            if parsed_args.index_name is not None:
                client_args['ReturnConsumedCapacity'] = 'INDEXES'
            else:
                client_args['ReturnConsumedCapacity'] = 'TOTAL'
        else:
            client_args['ReturnConsumedCapacity'] = 'NONE'

        return client_args
