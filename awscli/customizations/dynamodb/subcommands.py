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
from awscli.customizations.commands import BasicCommand
import awscli.customizations.dynamodb.params as params


class DDBCommand(BasicCommand):
    def _run_main(self, parsed_args, parsed_globals):
        self.client = self._session.create_client(
            'dynamodb', parsed_globals.region,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl,
        )


class SelectCommand(DDBCommand):
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
