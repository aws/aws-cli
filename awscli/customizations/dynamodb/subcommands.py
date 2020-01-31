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
from base64 import b64decode
from decimal import Decimal
import logging
import sys

from ruamel.yaml import YAML

from awscli.formatter import YAMLFormatter
from awscli.utils import OutputStreamFactory
import awscli.customizations.dynamodb.params as parameters
from awscli.customizations.commands import BasicCommand, CustomArgument
from awscli.customizations.dynamodb.extractor import AttributeExtractor
from awscli.customizations.dynamodb.transform import (
    ParameterTransformer, TypeSerializer, TypeDeserializer
)
from awscli.customizations.dynamodb.formatter import DynamoYAMLDumper
from awscli.customizations.paginate import ensure_paging_params_not_set
from awscli.customizations.exceptions import ParamValidationError
from .types import Binary


LOGGER = logging.getLogger(__name__)


class DDBCommand(BasicCommand):
    def _run_main(self, parsed_args, parsed_globals):
        factory = self._session.get_component('response_parser_factory')
        factory.set_parser_defaults(blob_parser=None)
        self._client = self._session.create_client(
            'dynamodb', region_name=parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl
        )
        self._transformer = ParameterTransformer()
        self._serializer = TypeSerializer()
        self._deserializer = TypeDeserializer()
        self._extractor = AttributeExtractor()
        self._output_stream_factory = OutputStreamFactory(self._session)

    def _serialize(self, operation_name, data):
        service_model = self._client.meta.service_model
        operation_model = service_model.operation_model(
            self._client.meta.method_to_api_mapping.get(operation_name)
        )
        self._transformer.transform(
            data, operation_model.input_shape, self._serializer.serialize,
            'AttributeValue'
        )

    def _deserialize(self, operation_name, data):
        service_model = self._client.meta.service_model
        operation_model = service_model.operation_model(
            self._client.meta.method_to_api_mapping.get(operation_name)
        )
        self._transformer.transform(
            data, operation_model.output_shape, self._deserializer.deserialize,
            'AttributeValue'
        )

    def _make_api_call(self, operation_name, client_args,
                       should_paginate=True):
        self._serialize(operation_name, client_args)

        if self._client.can_paginate(operation_name) and should_paginate:
            paginator = self._client.get_paginator(operation_name)
            response = paginator.paginate(**client_args).build_full_result()
        else:
            response = getattr(self._client, operation_name)(**client_args)
        if 'ConsumedCapacity' in response and \
                response['ConsumedCapacity'] is None:
            del response['ConsumedCapacity']
        self._deserialize(operation_name, response)
        return response

    def _dump_yaml(self, operation_name, data, parsed_globals):
        if parsed_globals.output == 'yaml-stream':
            # TODO: In the future, we should support yaml-stream. However, it
            #  would require a larger refactoring. Right now we always build
            #  the full result when paginating prior to sending it to the
            #  formatter. We need to instead pass the page iterator and
            #  deserialize in the formatter. We cannot necessarily just
            #  convert these to client handlers because the DDB types we
            #  introduce do not play nicely with the pagination interfaces.
            #  For example, botocore cannot serialize our Binary types into
            #  a resume token when --max-items gets set.
            raise ParamValidationError(
                'yaml-stream output format is not supported for ddb commands'
            )
        formatter = YAMLFormatter(parsed_globals, DynamoYAMLDumper())
        with self._output_stream_factory.get_output_stream() as stream:
            formatter(operation_name, data, stream)

    def _add_expression_args(self, expression_name, expression, args,
                             substitution_count=0):
        result = self._extractor.extract(
            ' '.join(expression),
            substitution_count
        )
        args[expression_name] = result['expression']

        if result['identifiers']:
            if 'ExpressionAttributeNames' not in args:
                args['ExpressionAttributeNames'] = {}
            args['ExpressionAttributeNames'].update(result['identifiers'])

        if result['values']:
            if 'ExpressionAttributeValues' not in args:
                args['ExpressionAttributeValues'] = {}
            args['ExpressionAttributeValues'].update(result['values'])

        return result['substitution_count']


class PaginatedDDBCommand(DDBCommand):
    PAGING_ARGS = [
        parameters.STARTING_TOKEN, parameters.MAX_ITEMS, parameters.PAGE_SIZE
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
        parameters.TABLE_NAME,
        parameters.INDEX_NAME,
        parameters.PROJECTION_EXPRESSION,
        parameters.FILTER_EXPRESSION,
        parameters.KEY_CONDITION_EXPRESSION,
        parameters.SELECT,
        parameters.CONSISTENT_READ,
        parameters.NO_CONSISTENT_READ,
        parameters.RETURN_CONSUMED_CAPACITY,
        parameters.NO_RETURN_CONSUMED_CAPACITY,
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
        should_paginate = parsed_globals.paginate
        if not should_paginate:
            ensure_paging_params_not_set(parsed_args, {})
        client_args = self._get_client_args(parsed_args)
        response = self._make_api_call(operation, client_args, should_paginate)
        self._dump_yaml(operation, response, parsed_globals)

    def _get_client_args(self, parsed_args):
        client_args = super(SelectCommand, self)._get_client_args(parsed_args)
        client_args.update({
            'TableName': parsed_args.table_name,
            'ConsistentRead': parsed_args.consistent_read,
        })
        substitution_count = 0
        if parsed_args.index_name is not None:
            client_args['IndexName'] = parsed_args.index_name
        if parsed_args.projection is not None:
            substitution_count = self._add_expression_args(
                'ProjectionExpression', parsed_args.projection, client_args,
                substitution_count,
            )
        if parsed_args.filter is not None:
            substitution_count += self._add_expression_args(
                'FilterExpression', parsed_args.filter, client_args,
                substitution_count,
            )
        if parsed_args.key_condition is not None:
            self._add_expression_args(
                'KeyConditionExpression', parsed_args.key_condition,
                client_args, substitution_count,
            )
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


class PutCommand(DDBCommand):
    NAME = 'put'
    DESCRIPTION = (
        '``put`` puts one or more items into a table.'
    )
    ARG_TABLE = [
        parameters.TABLE_NAME,
        parameters.ITEMS,
        parameters.CONDITION_EXPRESSION,
    ]

    def _run_main(self, parsed_args, parsed_globals):
        super(PutCommand, self)._run_main(parsed_args, parsed_globals)
        self._yaml = YAML(typ='safe')
        self._yaml.constructor.add_constructor(
            'tag:yaml.org,2002:binary', self._load_binary
        )
        self._yaml.constructor.add_constructor(
            'tag:yaml.org,2002:float', self._load_number
        )
        self._put(parsed_args)
        return 0

    def _load_binary(self, loader, node):
        return Binary(b64decode(node.value))

    def _load_number(self, loader, node):
        return Decimal(node.value)

    def _put(self, parsed_args):
        items = self._get_items(parsed_args)

        # batch write does not support condition expressions, so if we use
        # that then we just have to call put_item for each item.
        if len(items) > 1 and parsed_args.condition is None:
            self._batch_write(items, parsed_args)
        else:
            if len(items) > 1:
                raise ParamValidationError(
                    '--condition is not supported for multiple items'
                )
            self._put_item(items, parsed_args)

    def _put_item(self, items, parsed_args):
        client_args = self._get_base_args(parsed_args)
        client_args['TableName'] = parsed_args.table_name
        for item in items:
            client_args['Item'] = item
            self._make_api_call('put_item', client_args)
        return {}

    def _batch_write(self, items, parsed_args):
        batch_size = 25
        client_args = self._get_base_args(parsed_args)

        put_requests = [{'PutRequest': {'Item': i}} for i in items]
        while len(put_requests) > 0:
            batch_items = put_requests[:batch_size]
            client_args['RequestItems'] = {
                parsed_args.table_name: batch_items
            }
            result = self._make_api_call('batch_write_item', client_args)

            put_requests = put_requests[batch_size:]

            unprocessed_items = result.get('UnprocessedItems', {})
            unprocessed_items = unprocessed_items.get(
                parsed_args.table_name, None
            )
            if unprocessed_items is not None:
                put_requests.extend(unprocessed_items)

    def _get_items(self, parsed_args):
        if parsed_args.items == '-':
            items = self._yaml.load(sys.stdin)
        else:
            items = self._yaml.load(parsed_args.items)
        if not isinstance(items, list):
            items = [items]
        return items

    def _get_base_args(self, parsed_args):
        client_args = {'ReturnConsumedCapacity': 'NONE'}
        if parsed_args.condition is not None:
            self._add_expression_args(
                'ConditionExpression', parsed_args.condition, client_args,
            )
        return client_args
