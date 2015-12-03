# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import time
import random

from awscli.arguments import CustomArgument
from awscli.customizations.utils import validate_mutually_exclusive_handler


def register(event_handler):
    """Provides a simpler --paths for ``aws cloudfront create-invalidation``"""

    event_handler.register(
        'building-argument-table.cloudfront.create-invalidation', _add_paths)
    event_handler.register(
        'operation-args-parsed.cloudfront.create-invalidation',
        validate_mutually_exclusive_handler(['invalidation_batch'], ['paths']))


def _add_paths(argument_table, **kwargs):
    argument_table['invalidation-batch'].required = False
    argument_table['paths'] = PathsArgument()


class PathsArgument(CustomArgument):

    def __init__(self):
        doc = """The space-separated paths to be invalidated.
            Note: --invalidation-batch and --paths are mututally exclusive."""
        super(PathsArgument, self).__init__('paths', nargs='+', help_text=doc)

    def add_to_params(self, parameters, value):
        if value is not None:
            caller_reference = 'cli-%s-%s' % (
                int(time.time()), random.randint(1, 1000000))
            parameters['InvalidationBatch'] = {
                "CallerReference": caller_reference,
                "Paths": {"Quantity": len(value), "Items": value},
                }
