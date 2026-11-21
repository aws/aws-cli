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
"""Unit tests for the compositereadonly output caps (truncation + series capping)."""

from awscli.customizations.compositereadonly import output

# --------------------------------------------------------------- truncate_field


def test_truncate_field_keeps_head_and_flags():
    value, truncated = output.truncate_field("x" * 100, 20)
    assert truncated is True
    assert len(value) <= 20
    assert value.endswith("...[truncated]")
    # The kept portion is the head of the original string.
    assert value.startswith("x")


def test_truncate_field_under_limit_untouched():
    value, truncated = output.truncate_field("short", 20)
    assert truncated is False
    assert value == "short"


def test_truncate_field_exact_length_untouched():
    text = "x" * 20
    value, truncated = output.truncate_field(text, 20)
    assert truncated is False
    assert value == text


def test_truncate_field_disabled_with_nonpositive_max():
    # max_chars <= 0 disables truncation entirely.
    value, truncated = output.truncate_field("x" * 100, 0)
    assert truncated is False
    assert len(value) == 100
    value2, truncated2 = output.truncate_field("x" * 100, -5)
    assert truncated2 is False
    assert len(value2) == 100


def test_truncate_field_passes_through_non_strings():
    for val in (123, None, ["a"], {"k": "v"}):
        result, truncated = output.truncate_field(val, 5)
        assert result == val
        assert truncated is False


def test_truncate_field_tiny_max_smaller_than_suffix():
    # When max_chars is smaller than the suffix, the head is empty but the
    # function still returns the suffix (max(0, ...) guards the negative slice).
    value, truncated = output.truncate_field("abcdef", 3)
    assert truncated is True
    assert value == "...[truncated]"


# -------------------------------------------------------------------- cap_series


def test_cap_series_under_limit_untouched():
    kept, dropped = output.cap_series([1, 2, 3], 5)
    assert kept == [1, 2, 3]
    assert dropped == 0


def test_cap_series_truncates_and_reports_dropped():
    kept, dropped = output.cap_series([1, 2, 3, 4, 5], 2)
    assert kept == [1, 2]
    assert dropped == 3


def test_cap_series_exact_length_untouched():
    kept, dropped = output.cap_series([1, 2], 2)
    assert kept == [1, 2]
    assert dropped == 0


def test_cap_series_negative_max_disables_cap():
    items = [1, 2, 3]
    kept, dropped = output.cap_series(items, -1)
    assert kept == items
    assert dropped == 0
