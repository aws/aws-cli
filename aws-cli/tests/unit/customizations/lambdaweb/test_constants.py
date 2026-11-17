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

from awscli.customizations.lambdaweb.constants import FUNCTION_NAME_PATTERN


@pytest.mark.parametrize(
    'name',
    [
        'ab',
        'my-function',
        'my_function',
        'Web123',
        'a' * 64,
    ],
)
def test_function_name_pattern_accepts_valid_names(name):
    assert re.match(FUNCTION_NAME_PATTERN, name)


@pytest.mark.parametrize(
    'name',
    [
        'a',
        '',
        'a' * 65,
        '-foo',
        '_foo',
        'foo-',
        'foo_',
        'foo bar',
        'foo.bar',
        'foo!',
        'my-fn\n',
    ],
)
def test_function_name_pattern_rejects_invalid_names(name):
    assert re.match(FUNCTION_NAME_PATTERN, name) is None
