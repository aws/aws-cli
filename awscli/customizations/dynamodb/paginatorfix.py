# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import base64
import binascii
import logging

logger = logging.getLogger(__name__)


def register_dynamodb_paginator_fix(event_emitter):
    DynamoDBPaginatorFix(event_emitter).register_events()


def parse_last_evaluated_key_binary(parsed, **kwargs):
    # Because we disable parsing blobs into a binary type and leave them as
    # a base64 string if a binary field is present in the continuation token
    # as is the case with dynamodb the binary will be double encoded. This
    # ensures that the continuation token is properly converted to binary to
    # avoid double encoding the contination token.
    last_evaluated_key = parsed.get('LastEvaluatedKey', None)
    if last_evaluated_key is None:
        return
    for key, val in last_evaluated_key.items():
        if 'B' in val:
            val['B'] = base64.b64decode(val['B'])


class DynamoDBPaginatorFix(object):
    def __init__(self, event_emitter):
        self._event_emitter = event_emitter

    def register_events(self):
        self._event_emitter.register(
            'calling-command.dynamodb.*', self._maybe_register_pagination_fix
        )

    def _maybe_register_pagination_fix(self, parsed_globals, **kwargs):
        if parsed_globals.paginate:
            self._event_emitter.register(
                'after-call.dynamodb.*', parse_last_evaluated_key_binary
            )
