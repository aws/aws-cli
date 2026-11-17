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
import re

import pytest

from awscli.customizations.lambdaweb.naming import (
    bucket_name,
    log_group_name,
    role_name,
)


def test_bucket_name_pattern():
    result = bucket_name('123456789012', 'us-west-2')
    assert result == 'awscli-lambdaweb-123456789012-us-west-2-an'


def test_role_name_truncates_to_64():
    # Names longer than the 47-char budget cannot fit verbatim. The result is
    # still a legal IAM role name (<= 64). Function names are capped at 64,
    # so a 100-char name never reaches this in production; the truncation
    # still holds as a defensive invariant.
    result = role_name('a' * 100)
    assert len(result) <= 64
    assert result.startswith('awscli-lambdaweb-')


def test_role_name_uses_name_verbatim_when_it_fits():
    # 47 chars is exactly the budget (64 - len('awscli-lambdaweb-')).
    name = 'a' * 47
    assert role_name(name) == f'awscli-lambdaweb-{name}'
    assert len(role_name(name)) == 64


def test_role_name_short_name_unchanged():
    assert role_name('my-fn') == 'awscli-lambdaweb-my-fn'


def test_role_name_appends_hash_suffix_when_truncated():
    # A name one over the budget must NOT be used verbatim; it is truncated
    # and a hash suffix is appended so the result stays <= 64.
    name = 'a' * 48
    result = role_name(name)
    assert len(result) <= 64
    assert result.startswith('awscli-lambdaweb-')
    assert re.search(r'-[0-9a-f]{8}$', result), result


def test_role_name_collision_avoided_for_shared_prefix():
    # Two distinct function names that share the first 47 chars previously
    # truncated to the SAME role name, so the second function silently reused
    # the first function's role. Their full-name hashes must differ.
    prefix = 'z' * 47
    name_a = prefix + 'aaaaa'
    name_b = prefix + 'bbbbb'
    role_a = role_name(name_a)
    role_b = role_name(name_b)
    assert role_a != role_b
    assert len(role_a) <= 64
    assert len(role_b) <= 64


def test_role_name_is_deterministic():
    # Same input -> same role name (hash is not salted/random), so repeat
    # deploys of the same function resolve to the same managed role.
    name = 'q' * 60
    assert role_name(name) == role_name(name)


def test_log_group_name_uses_web_prefix():
    result = log_group_name('foo')
    assert result == '/aws/lambda/web/foo'


def test_naming_raises_on_empty_input():
    with pytest.raises(ValueError):
        bucket_name('', 'us-east-1')
    with pytest.raises(ValueError):
        bucket_name('123', '')
    with pytest.raises(ValueError):
        role_name('')
    with pytest.raises(ValueError):
        log_group_name('')
