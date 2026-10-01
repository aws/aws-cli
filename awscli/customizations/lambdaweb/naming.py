# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import hashlib

from awscli.customizations.lambdaweb import constants

_ROLE_PREFIX = 'awscli-lambdaweb-'
_BUCKET_PREFIX = 'awscli-lambdaweb-'
_ROLE_MAX_LENGTH = 64

# Hash suffix length used to keep truncated role names unique.
_ROLE_HASH_LEN = 8


def bucket_name(account_id, region):
    """Return the S3 bucket name for a given account and region."""
    if not account_id:
        raise ValueError('account_id must not be empty')
    if not region:
        raise ValueError('region must not be empty')
    return f'{_BUCKET_PREFIX}{account_id}-{region}-an'


def role_name(function_name):
    """Return the IAM role name for ``function_name`` (<= 64 chars).

    Names that exceed the IAM limit are truncated with a hash suffix to avoid
    collisions.
    """
    if not function_name:
        raise ValueError('function_name must not be empty')
    budget = _ROLE_MAX_LENGTH - len(_ROLE_PREFIX)
    if len(function_name) <= budget:
        return f'{_ROLE_PREFIX}{function_name}'
    digest = hashlib.sha256(function_name.encode('utf-8')).hexdigest()
    suffix = f'-{digest[:_ROLE_HASH_LEN]}'
    keep = budget - len(suffix)
    return f'{_ROLE_PREFIX}{function_name[:keep]}{suffix}'


def log_group_name(function_name):
    """Return the CloudWatch log group name for a function."""
    if not function_name:
        raise ValueError('function_name must not be empty')
    return f'{constants.LOG_GROUP_PREFIX}/{function_name}'
