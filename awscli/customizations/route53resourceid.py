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
import logging


logger = logging.getLogger(__name__)


def register_resource_id(cli):
    cli.register('process-cli-arg.route53.*',
                 _check_for_resource_id)


def _check_for_resource_id(param, value, **kwargs):
    if hasattr(param, 'shape_name'):
        if param.shape_name == 'ResourceId':
            orig_value = value
            value = value.split('/')[-1]
            logger.debug('ResourceId %s -> %s', orig_value, value)
            return value
