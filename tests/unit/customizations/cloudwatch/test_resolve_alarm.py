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
"""Unit tests for CloudWatch's alarm resolver.

``resolve_alarm`` used to live in the shared compositereadonly ``resolve``
module; it now lives with its owning command in
:mod:`awscli.customizations.cloudwatch_alarm_metric_sweep`, so its tests live
here too.
"""

from awscli.customizations import cloudwatch_alarm_metric_sweep as cw
from awscli.customizations.compositereadonly.helpers import (
    NOT_FOUND,
    PERMISSION_DENIED,
    assert_read_only,
    err_result,
    ok_result,
)


class Scripted:
    """A scripted read-only call bridge; records calls, returns queued dicts."""

    def __init__(self):
        self.calls = []
        self._responses = {}

    def queue(self, operation, *results):
        self._responses.setdefault(operation, []).extend(results)
        return self

    def __call__(self, operation, params):
        assert_read_only(operation)
        self.calls.append((operation, params))
        queued = self._responses.get(operation)
        if queued:
            return queued.pop(0)
        return ok_result({})

    def ops(self):
        return [op for op, _ in self.calls]


# --------------------------------------------------------------- resolve_alarm


def _metric_alarm(name, rule=False):
    a = {"AlarmName": name}
    if rule:
        a["AlarmRule"] = "ALARM(x)"
    return a


def _describe(metric=None, composite=None, token=None):
    body = {
        "MetricAlarms": list(metric or []),
        "CompositeAlarms": list(composite or []),
    }
    if token:
        body["NextToken"] = token
    return ok_result(body)


def test_alarm_prefix_paging_stops_at_page_cap():
    call = Scripted()
    call.queue("DescribeAlarms", _describe())  # exact miss
    # Every prefix page returns a candidate and a NextToken; _describe_prefix
    # must stop after _MAX_ALARM_PAGES reads rather than chase the last token,
    # whatever the eventual match decision is.
    for i in range(cw._MAX_ALARM_PAGES + 2):
        call.queue(
            "DescribeAlarms",
            _describe(metric=[_metric_alarm(f"svc-{i}")], token="more"),
        )
    cw.resolve_alarm(call, "svc")
    # 1 exact + exactly _MAX_ALARM_PAGES prefix reads (the cap held); the
    # surplus queued pages were never requested.
    assert call.ops().count("DescribeAlarms") == (1 + cw._MAX_ALARM_PAGES)


def test_alarm_exact_metric_hit_short_circuits():
    call = Scripted()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm("cpu-high")]))
    r = cw.resolve_alarm(call, "cpu-high")
    assert r["ok"] is True
    assert r["value"]["match"] == "exact"
    assert r["value"]["kind"] == "metric_alarm"
    # Exact hit means no prefix fallback was attempted.
    assert call.ops() == ["DescribeAlarms"]


def test_alarm_exact_composite_hit():
    call = Scripted()
    call.queue(
        "DescribeAlarms",
        _describe(composite=[_metric_alarm("agg", rule=True)]),
    )
    r = cw.resolve_alarm(call, "agg")
    assert r["value"]["kind"] == "composite_alarm"
    assert r["value"]["match"] == "exact"


def test_alarm_exact_describe_error_is_returned():
    call = Scripted()
    call.queue("DescribeAlarms", err_result(PERMISSION_DENIED, "denied"))
    r = cw.resolve_alarm(call, "cpu")
    assert r["ok"] is False
    assert r["code"] == PERMISSION_DENIED


def test_alarm_prefix_single_candidate():
    call = Scripted()
    call.queue("DescribeAlarms", _describe())  # exact miss
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm("cpu-high")]))
    r = cw.resolve_alarm(call, "cpu", fuzzy=True)
    assert r["ok"] is True
    assert r["value"]["match"] == "prefix"
    assert any("prefix match" in g for g in r["value"]["guidance"])


def test_alarm_prefix_describe_error_propagates():
    call = Scripted()
    call.queue("DescribeAlarms", _describe())  # exact miss
    call.queue("DescribeAlarms", err_result(PERMISSION_DENIED, "denied"))
    r = cw.resolve_alarm(call, "cpu")
    assert r["ok"] is False
    assert r["code"] == PERMISSION_DENIED


def test_alarm_no_candidates_is_not_found():
    call = Scripted()
    call.queue("DescribeAlarms", _describe())  # exact miss
    call.queue("DescribeAlarms", _describe())  # prefix miss
    r = cw.resolve_alarm(call, "ghost")
    assert r["ok"] is False
    assert r["code"] == NOT_FOUND
    assert r["key"] == "ghost"


def test_alarm_prefix_paging_is_followed():
    call = Scripted()
    call.queue("DescribeAlarms", _describe())  # exact miss
    call.queue(
        "DescribeAlarms",
        _describe(metric=[_metric_alarm("cpu-a")], token="more"),
    )
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm("cpu-b")]))
    r = cw.resolve_alarm(call, "cpu-a", fuzzy=True)
    # Two prefix candidates fetched across pages; exact-ci picks 'cpu-a'.
    assert r["ok"] is True
    assert r["value"]["alarm"]["AlarmName"] == "cpu-a"


def test_alarm_case_insensitive_exact_among_several():
    call = Scripted()
    call.queue("DescribeAlarms", _describe())  # exact miss (case differs)
    call.queue(
        "DescribeAlarms",
        _describe(
            metric=[_metric_alarm("CPU-High"), _metric_alarm("cpu-low")]
        ),
    )
    r = cw.resolve_alarm(call, "cpu-high", fuzzy=True)
    assert r["ok"] is True
    assert r["value"]["alarm"]["AlarmName"] == "CPU-High"
    assert any("case-insensitive" in g for g in r["value"]["guidance"])


def test_alarm_fuzzy_single_close_match():
    call = Scripted()
    call.queue("DescribeAlarms", _describe())  # exact miss
    call.queue(
        "DescribeAlarms",
        _describe(
            metric=[
                _metric_alarm("cpu-utilization-high"),
                _metric_alarm("totally-different-name"),
            ]
        ),
    )
    # 'cpu-utilisation-high' (British spelling) fuzzily matches the first only.
    r = cw.resolve_alarm(call, "cpu-utilisation-high", fuzzy=True)
    assert r["ok"] is True
    assert r["value"]["match"] == "fuzzy"
    assert r["value"]["alarm"]["AlarmName"] == "cpu-utilization-high"


def test_alarm_ambiguous_prefix_is_not_found_with_candidates():
    call = Scripted()
    call.queue("DescribeAlarms", _describe())  # exact miss
    # Many similar names, none an unambiguous match.
    names = [f"svc-alarm-{i}" for i in range(12)]
    call.queue(
        "DescribeAlarms",
        _describe(metric=[_metric_alarm(n) for n in names]),
    )
    r = cw.resolve_alarm(call, "svc", fuzzy=True)
    assert r["ok"] is False
    assert r["code"] == NOT_FOUND
    assert "ambiguous" in r["error"]
    # More than 10 candidates -> the guidance list is elided with "...".
    assert any("..." in g for g in r["guidance"])


def test_alarm_exact_only_default_lists_candidates():
    call = Scripted()
    call.queue("DescribeAlarms", _describe())  # exact miss
    call.queue(
        "DescribeAlarms",
        _describe(
            metric=[_metric_alarm("cpu-high-1"), _metric_alarm("cpu-high-2")]
        ),
    )
    # Default (no fuzzy): an exact miss returns NOT_FOUND listing candidates
    # instead of silently resolving by prefix/fuzzy.
    r = cw.resolve_alarm(call, "cpu-high")
    assert r["ok"] is False
    assert r["code"] == NOT_FOUND
    assert any("cpu-high-1" in g for g in r["guidance"])
    assert any("--fuzzy" in g for g in r["guidance"])
