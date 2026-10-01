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
import pytest

from awscli.customizations.lambdaweb.exceptions import InvalidKeyValueError
from awscli.customizations.lambdaweb.utils import parse_kv, strip_empty


class TestParseKv:
    def test_none_returns_empty_dict(self):
        assert parse_kv(None) == {}

    def test_empty_list_returns_empty_dict(self):
        assert parse_kv([]) == {}

    def test_single_entry(self):
        assert parse_kv(['A=1']) == {'A': '1'}

    def test_multiple_entries(self):
        assert parse_kv(['A=1', 'B=2']) == {'A': '1', 'B': '2'}

    def test_value_with_equals(self):
        assert parse_kv(['KEY=a=b=c']) == {'KEY': 'a=b=c'}

    def test_missing_equals_raises(self):
        # InvalidKeyValueError is a LambdaWebError, so the deploy orchestrator
        # catches and formats it rather than surfacing a raw traceback.
        with pytest.raises(InvalidKeyValueError):
            parse_kv(['NOEQUALS'])

    def test_missing_equals_uses_label(self):
        with pytest.raises(InvalidKeyValueError, match='--env'):
            parse_kv(['NOEQUALS'], label='--env')

    def test_empty_key_raises(self):
        with pytest.raises(
            InvalidKeyValueError, match='key must not be empty'
        ):
            parse_kv(['=value'], label='--env')

    def test_empty_value_allowed_by_default(self):
        # Tags (TagsValueString min:0) may be empty, so the default keeps the
        # empty string rather than rejecting it.
        assert parse_kv(['KEY=']) == {'KEY': ''}

    def test_empty_value_rejected_when_opted_in(self):
        # --env values map to EnvironmentVariablesValueString (min:1),
        # so an empty value is a contract violation and must be rejected up
        # front rather than silently dropped by strip_empty (which would also
        # wipe inherited env vars on the update path).
        with pytest.raises(InvalidKeyValueError, match='must not be empty'):
            parse_kv(['KEY='], label='--env', reject_empty_values=True)

    def test_nonempty_value_passes_when_reject_empty_set(self):
        assert parse_kv(
            ['KEY=v'], label='--env', reject_empty_values=True
        ) == {'KEY': 'v'}


class TestStripEmpty:
    def test_preserves_zero(self):
        assert strip_empty({'a': 0}) == {'a': 0}

    def test_preserves_false(self):
        assert strip_empty({'a': False}) == {'a': False}

    def test_drops_none(self):
        assert strip_empty({'a': None}) == {}

    def test_drops_empty_string(self):
        assert strip_empty({'a': ''}) == {}

    def test_drops_empty_list(self):
        assert strip_empty({'a': []}) == {}

    def test_drops_empty_dict(self):
        assert strip_empty({'a': {}}) == {}

    def test_mixed(self):
        result = strip_empty(
            {
                'a': 0,
                'b': '',
                'c': False,
                'd': 'x',
                'e': None,
                'f': [],
                'g': {},
            }
        )
        assert result == {'a': 0, 'c': False, 'd': 'x'}

    def test_nested_dict(self):
        result = strip_empty({'outer': {'inner': None, 'keep': 1}})
        assert result == {'outer': {'keep': 1}}

    def test_nested_list(self):
        result = strip_empty({'items': ['a', '', None, 'b']})
        assert result == {'items': ['a', 'b']}
