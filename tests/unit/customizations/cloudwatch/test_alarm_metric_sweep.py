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
"""Unit tests for ``aws cloudwatch alarm-metric-sweep`` (core sweep logic)."""

from datetime import datetime, timezone

from awscli.customizations.cloudwatch_alarm_metric_sweep import (
    alarm_metric_sweep,
)
from awscli.customizations.compositereadonly.helpers import (
    assert_read_only,
    err_result,
    ok_result,
)

UTC = timezone.utc


class ScriptedCW:
    """A scripted read-only call bridge: records calls, returns queued results.

    Mirrors the real :func:`call` bridge by refusing any mutating operation, so
    a test fails loudly if the sweep ever attempts a write.
    """

    def __init__(self):
        self.calls = []
        self._responses = {}

    def queue(self, operation, *results):
        self._responses.setdefault(operation, []).extend(results)
        return self

    def __call__(self, operation, params):
        assert_read_only(operation)  # read-only guarantee under test
        self.calls.append((operation, params))
        queued = self._responses.get(operation)
        if queued:
            return queued.pop(0)
        return ok_result({})

    def ops(self):
        return [op for op, _ in self.calls]


# ------------------------------------------------------------------- fixtures


def _metric_alarm(name="cpu-high", dims=None):
    dims = (
        dims if dims is not None else [{"Name": "InstanceId", "Value": "i-1"}]
    )
    return {
        "AlarmName": name,
        "AlarmArn": f"arn:aws:cloudwatch:us-east-1:1:alarm:{name}",
        "StateValue": "ALARM",
        "Namespace": "AWS/EC2",
        "MetricName": "CPUUtilization",
        "Dimensions": dims,
        "Statistic": "Average",
        "Period": 300,
        "Threshold": 80.0,
        "ComparisonOperator": "GreaterThanThreshold",
        "EvaluationPeriods": 1,
    }


def _describe(metric=None, composite=None, next_token=None):
    body = {
        "MetricAlarms": list(metric or []),
        "CompositeAlarms": list(composite or []),
    }
    if next_token:
        body["NextToken"] = next_token
    return ok_result(body)


def _history(items=None, next_token=None):
    body = {"AlarmHistoryItems": list(items or [])}
    if next_token:
        body["NextToken"] = next_token
    return ok_result(body)


def _list_metrics(metrics=None, next_token=None):
    body = {"Metrics": list(metrics or [])}
    if next_token:
        body["NextToken"] = next_token
    return ok_result(body)


def _series(id_, values, start=1_700_000_000, period=300, status="Complete"):
    # GetMetricData returns ISO-8601 / datetime timestamps (not raw epochs), so
    # the fixture mirrors that; _dt() only parses datetimes and ISO strings.
    ts = [
        datetime.fromtimestamp(start + i * period, UTC).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        for i in range(len(values))
    ]
    return {
        "Id": id_,
        "Label": id_,
        "Timestamps": ts,
        "Values": list(values),
        "StatusCode": status,
    }


def _metric_data(results=None, next_token=None):
    body = {"MetricDataResults": list(results or [])}
    if next_token:
        body["NextToken"] = next_token
    return ok_result(body)


def _fixed_clock(t=1_700_030_000.0):
    return lambda: t


def _run(call, alarm_name="cpu-high", **kwargs):
    kwargs.setdefault("clock", _fixed_clock())
    # Deterministic window so period/time-window math is stable in assertions.
    kwargs.setdefault("start_time", "2023-11-14T18:00:00Z")
    kwargs.setdefault("end_time", "2023-11-14T21:00:00Z")
    # Dimension/sibling enumeration is now opt-in; most existing cases exercise
    # it, so default it on here. New default-behaviour tests call
    # alarm_metric_sweep directly (or pass fan_out=False) to assert the default.
    kwargs.setdefault("fan_out", True)
    return alarm_metric_sweep(call, alarm_name, **kwargs)


# ------------------------------------------------------- resolution: exact


def test_exact_match_resolves_and_issues_only_read_ops():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm()]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue(
        "ListMetrics",
        _list_metrics(
            [
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": "i-1"}],
                }
            ]
        ),
    )
    call.queue("GetMetricData", _metric_data([_series("alarm_metric", [1.0])]))
    call.queue("GetMetricData", _metric_data([_series("zs0", [1.0])]))
    result = _run(call)
    assert result["ok"] is True
    assert result["value"]["target"]["match"] == "exact"
    # First resolution call is an exact DescribeAlarms by name (no prefix).
    first_op, first_params = call.calls[0]
    assert first_op == "DescribeAlarms"
    assert first_params["AlarmNames"] == ["cpu-high"]
    # Strictly read-only: no mutating verb ever reached the bridge.
    assert all(op.startswith(("Describe", "Get", "List")) for op in call.ops())


# ------------------------------------------------------- resolution: prefix


def test_unique_prefix_resolves_with_guidance():
    call = ScriptedCW()
    # Exact miss, then a single prefix candidate.
    call.queue("DescribeAlarms", _describe())
    call.queue(
        "DescribeAlarms", _describe(metric=[_metric_alarm("cpu-high-1")])
    )
    call.queue("DescribeAlarmHistory", _history())
    call.queue("ListMetrics", _list_metrics())
    result = _run(call, alarm_name="cpu-high", fuzzy=True)
    assert result["ok"] is True
    assert result["value"]["target"]["match"] == "prefix"
    assert any("prefix" in g for g in result["guidance"])


def test_ambiguous_prefix_returns_not_found_with_candidates():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe())  # exact miss
    call.queue(
        "DescribeAlarms",
        _describe(
            metric=[
                _metric_alarm("db-writer-latency"),
                _metric_alarm("db-reader-errors"),
            ]
        ),
    )
    result = _run(call, alarm_name="db", fuzzy=True)
    assert result["ok"] is False
    assert result["code"] == "NOT_FOUND"
    assert "ambiguous" in result["error"]
    # No data calls after an unresolved name.
    assert "GetMetricData" not in call.ops()


def test_missing_alarm_returns_not_found():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe())  # exact miss
    call.queue("DescribeAlarms", _describe())  # prefix miss
    result = _run(call, alarm_name="ghost")
    assert result["ok"] is False
    assert result["code"] == "NOT_FOUND"
    assert "GetMetricData" not in call.ops()


# ------------------------------------------------------- param validation


def test_malformed_pin_dimensions_rejected_before_dispatch():
    call = ScriptedCW()
    result = _run(call, pin_dimensions=[123])
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"
    assert result.get("param_error") is True
    assert call.calls == []  # nothing dispatched


def test_bad_period_rejected_before_dispatch():
    call = ScriptedCW()
    result = _run(call, period_s=0)
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"
    assert call.calls == []


def test_start_after_end_rejected():
    call = ScriptedCW()
    result = alarm_metric_sweep(
        call,
        "cpu-high",
        start_time="2023-11-14T21:00:00Z",
        end_time="2023-11-14T18:00:00Z",
        clock=_fixed_clock(),
    )
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"
    assert call.calls == []


# ------------------------------------------------------- pagination / bounds


def test_history_pagination_follows_next_token():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm()]))
    item = {
        "AlarmName": "cpu-high",
        "Timestamp": "2023-11-14T19:00:00Z",
        "HistoryItemType": "StateUpdate",
        "HistoryData": "{}",
    }
    call.queue("DescribeAlarmHistory", _history([item], next_token="h2"))
    call.queue("DescribeAlarmHistory", _history([item]))
    call.queue("ListMetrics", _list_metrics())
    result = _run(call)
    assert result["ok"] is True
    assert result["value"]["state_history"]["count"] == 2
    assert call.ops().count("DescribeAlarmHistory") == 2


def test_listmetrics_pagination_bounded_marks_partial():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm()]))
    call.queue("DescribeAlarmHistory", _history())
    # ListMetrics never stops returning a token; the bounded loop must stop.
    for _ in range(10):
        call.queue(
            "ListMetrics",
            _list_metrics(
                [
                    {
                        "Namespace": "AWS/EC2",
                        "MetricName": "CPUUtilization",
                        "Dimensions": [{"Name": "InstanceId", "Value": "i-1"}],
                    }
                ],
                next_token="more",
            ),
        )
    call.queue("GetMetricData", _metric_data([_series("alarm_metric", [1.0])]))
    call.queue("GetMetricData", _metric_data([_series("zs0", [1.0])]))
    result = _run(call, max_pages=3)
    assert result["ok"] is True
    assert result["is_exhaustive"] is False
    assert call.ops().count("ListMetrics") == 3  # capped at max_pages


# ------------------------------------------------------- empty / composite


def test_composite_alarm_has_no_metrics_lists_children():
    call = ScriptedCW()
    composite = {
        "AlarmName": "parent",
        "AlarmArn": "arn:aws:cloudwatch:us-east-1:1:alarm:parent",
        "StateValue": "ALARM",
        "AlarmRule": 'ALARM("child-a") OR ALARM("child-b")',
    }
    call.queue("DescribeAlarms", _describe(composite=[composite]))
    # History is still fetched for the composite and its children.
    call.queue("DescribeAlarmHistory", _history())
    result = _run(call)
    assert result["ok"] is True
    assert result["value"]["target"]["kind"] == "composite_alarm"
    assert result["value"]["target"]["child_alarms"] == ["child-a", "child-b"]
    assert result["value"]["series"] == []
    assert "GetMetricData" not in call.ops()


def test_metric_alarm_with_no_datapoints_reports_series_without_data():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm()]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue(
        "ListMetrics",
        _list_metrics(
            [
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": "i-1"}],
                }
            ]
        ),
    )
    call.queue("GetMetricData", _metric_data([]))  # originals: no data
    call.queue("GetMetricData", _metric_data([]))  # series: no data
    result = _run(call)
    assert result["ok"] is True
    assert result["value"]["summary"]["series_with_data"] == 0
    assert result["value"]["summary"]["series_without_data"]


# ------------------------------------------------------- output capping


def test_per_series_datapoint_cap_truncates_and_reports():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm()]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue(
        "ListMetrics",
        _list_metrics(
            [
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": "i-1"}],
                }
            ]
        ),
    )
    many = [float(i) for i in range(12)]
    call.queue("GetMetricData", _metric_data([_series("alarm_metric", many)]))
    call.queue("GetMetricData", _metric_data([_series("zs0", many)]))
    result = _run(call, period_s=300, max_datapoints=5)
    series = result["value"]["series"][0]
    assert len(series["datapoints"]) == 5
    assert series["datapoints_truncated"] is True
    assert result["is_exhaustive"] is False
    assert any(
        "max-datapoints" in g or "max_datapoints" in g
        for g in result["guidance"]
    )


def test_total_output_cap_drops_later_datapoint_arrays():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm()]))
    call.queue("DescribeAlarmHistory", _history())
    # Two sibling series under the same dimension-name set.
    call.queue(
        "ListMetrics",
        _list_metrics(
            [
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": "i-1"}],
                },
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": "i-2"}],
                },
            ]
        ),
    )
    vals = [1.0, 2.0, 3.0, 4.0]
    call.queue("GetMetricData", _metric_data([_series("alarm_metric", vals)]))
    call.queue(
        "GetMetricData",
        _metric_data([_series("zs0", vals), _series("zs1", vals)]),
    )
    # Budget only allows the first series' datapoints in full; the next series
    # straddles the boundary and keeps only its most-recent point (tail).
    result = _run(call, max_total_datapoints=5)
    series = result["value"]["series"]
    assert "datapoints" in series[0]
    assert len(series[0]["datapoints"]) == 4
    assert series[-1]["datapoints_truncated"] is True
    assert len(series[-1]["datapoints"]) == 1
    assert series[-1]["datapoints"][0][1] == 4.0  # newest value kept
    assert result["value"]["summary"]["output_capped"] is True


def test_no_datapoints_flag_omits_arrays_but_keeps_summary():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm()]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue(
        "ListMetrics",
        _list_metrics(
            [
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": "i-1"}],
                }
            ]
        ),
    )
    call.queue(
        "GetMetricData", _metric_data([_series("alarm_metric", [1.0, 2.0])])
    )
    call.queue("GetMetricData", _metric_data([_series("zs0", [1.0, 2.0])]))
    result = _run(call, include_datapoints=False)
    series = result["value"]["series"][0]
    assert "datapoints" not in series
    assert series["datapoint_count"] == 2  # summary stats preserved


# ------------------------------------------------------- partial failure


def test_history_failure_degrades_but_sweep_continues():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm()]))
    call.queue(
        "DescribeAlarmHistory",
        err_result("PERMISSION_DENIED", "no cloudwatch:DescribeAlarmHistory"),
    )
    call.queue(
        "ListMetrics",
        _list_metrics(
            [
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": "i-1"}],
                }
            ]
        ),
    )
    call.queue("GetMetricData", _metric_data([_series("alarm_metric", [1.0])]))
    call.queue("GetMetricData", _metric_data([_series("zs0", [1.0])]))
    result = _run(call)
    assert result["ok"] is True  # sweep still returns a result
    assert result["is_exhaustive"] is False
    assert any(
        "DescribeAlarmHistory" in w for w in result["value"]["warnings"]
    )


def test_all_metric_data_batches_failing_is_operational_error():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm()]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue(
        "ListMetrics",
        _list_metrics(
            [
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": "i-1"}],
                }
            ]
        ),
    )
    call.queue(
        "GetMetricData",
        err_result("THROTTLED", "rate exceeded", retriable=True),
    )
    call.queue(
        "GetMetricData",
        err_result("THROTTLED", "rate exceeded", retriable=True),
    )
    result = _run(call)
    assert result["ok"] is False
    assert result["code"] == "THROTTLED"
    assert result["retriable"] is True
    # The partial value is still attached so an agent can inspect it.
    assert result["value"]["target"]["alarm_name"] == "cpu-high"


# ------------------------------------------------------- error-rate siblings


def _lm_entry(metric_name, dims):
    return {
        "Namespace": "AWS/ApplicationELB",
        "MetricName": metric_name,
        "Dimensions": dims,
    }


def test_error_rate_alarm_sweeps_sibling_metrics():
    call = ScriptedCW()
    dims = [{"Name": "LoadBalancer", "Value": "app/x"}]
    alarm = _metric_alarm("target-5xx-errors", dims=dims)
    alarm["Namespace"] = "AWS/ApplicationELB"
    alarm["MetricName"] = "HTTPCode_Target_5XX_Count"
    call.queue("DescribeAlarms", _describe(metric=[alarm]))
    call.queue("DescribeAlarmHistory", _history())
    # 1st ListMetrics: dimension enumeration for the target metric.
    call.queue(
        "ListMetrics",
        _list_metrics([_lm_entry("HTTPCode_Target_5XX_Count", dims)]),
    )
    # 2nd ListMetrics: namespace-wide sibling scan at the same dimensions.
    call.queue(
        "ListMetrics",
        _list_metrics(
            [
                _lm_entry("HTTPCode_Target_5XX_Count", dims),
                _lm_entry("RequestCount", dims),
            ]
        ),
    )
    call.queue("GetMetricData", _metric_data([_series("alarm_metric", [1.0])]))
    call.queue(
        "GetMetricData",
        _metric_data([_series("zs0", [1.0]), _series("zs1", [2.0])]),
    )
    result = _run(call, alarm_name="target-5xx-errors")
    assert result["ok"] is True
    assert result["value"]["summary"]["error_rate_target"] is True
    assert result["value"]["enumeration"]["sibling_metric_names"] == [
        "RequestCount"
    ]
    roles = {s["role"] for s in result["value"]["series"]}
    assert "metric_sibling" in roles
    assert call.ops().count("ListMetrics") == 2


def test_no_sibling_metrics_flag_skips_sibling_scan():
    call = ScriptedCW()
    dims = [{"Name": "LoadBalancer", "Value": "app/x"}]
    alarm = _metric_alarm("target-5xx-errors", dims=dims)
    alarm["Namespace"] = "AWS/ApplicationELB"
    alarm["MetricName"] = "HTTPCode_Target_5XX_Count"
    call.queue("DescribeAlarms", _describe(metric=[alarm]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue(
        "ListMetrics",
        _list_metrics([_lm_entry("HTTPCode_Target_5XX_Count", dims)]),
    )
    call.queue("GetMetricData", _metric_data([_series("alarm_metric", [1.0])]))
    call.queue("GetMetricData", _metric_data([_series("zs0", [1.0])]))
    result = _run(
        call, alarm_name="target-5xx-errors", include_sibling_metrics=False
    )
    assert result["ok"] is True
    # Only the dimension-enumeration ListMetrics ran; no sibling scan.
    assert call.ops().count("ListMetrics") == 1
    assert result["value"]["enumeration"]["sibling_metric_names"] == []


# --------------------------------------------------- metric-math alarm


def test_metric_math_alarm_replays_expression_and_inputs():
    call = ScriptedCW()
    math_alarm = {
        "AlarmName": "math-alarm",
        "AlarmArn": "arn:aws:cloudwatch:us-east-1:1:alarm:math-alarm",
        "StateValue": "OK",
        "Metrics": [
            {
                "Id": "m1",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EC2",
                        "MetricName": "CPUUtilization",
                        "Dimensions": [{"Name": "InstanceId", "Value": "i-1"}],
                    },
                    "Period": 300,
                    "Stat": "Average",
                },
            },
            {"Id": "e1", "Expression": "m1/100", "Label": "ratio"},
        ],
    }
    call.queue("DescribeAlarms", _describe(metric=[math_alarm]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue(
        "ListMetrics",
        _list_metrics(
            [
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": "i-1"}],
                }
            ]
        ),
    )
    call.queue(
        "GetMetricData",
        _metric_data([_series("m1", [50.0]), _series("e1", [0.5])]),
    )
    call.queue("GetMetricData", _metric_data([_series("zs0", [50.0])]))
    result = _run(call, alarm_name="math-alarm")
    assert result["ok"] is True
    roles = {q["role"] for q in result["value"]["original_queries"]}
    assert roles == {"original_metric", "expression"}


# --------------------------------------------- period / window clamps


def test_old_window_raises_period_for_retention_and_point_budget():
    # ~40 days old: retention forces >=300s, and a 40d span forces a wider
    # period to stay within the 1,440-points-per-series budget.
    now = 1_700_030_000.0
    start = datetime.fromtimestamp(now - 40 * 86400, UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm()]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue("ListMetrics", _list_metrics())
    result = alarm_metric_sweep(
        call,
        "cpu-high",
        start_time=start,
        end_time=None,
        period_s=60,
        clock=lambda: now,
    )
    assert result["ok"] is True
    assert result["value"]["window"]["period_s"] > 60
    joined = " ".join(result["guidance"])
    assert "retained at" in joined
    assert "points per series" in joined


# --------------------------------------------- timeline analytics


def _series_iso(id_, points, status="Complete"):
    return {
        "Id": id_,
        "Label": id_,
        "Timestamps": [p[0] for p in points],
        "Values": [p[1] for p in points],
        "StatusCode": status,
    }


def test_timeline_reports_gaps_zero_peak_and_trailing():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm()]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue(
        "ListMetrics",
        _list_metrics(
            [
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": "i-1"}],
                }
            ]
        ),
    )
    # Window 18:00..19:00 @300s = 13 grid points; data only at the first three,
    # one of which is a zero and one a peak, so the rest are trailing gaps.
    pts = [
        ("2023-11-14T18:00:00Z", 5.0),
        ("2023-11-14T18:05:00Z", 99.0),
        ("2023-11-14T18:10:00Z", 0.0),
    ]
    call.queue(
        "GetMetricData", _metric_data([_series_iso("alarm_metric", pts)])
    )
    call.queue("GetMetricData", _metric_data([_series_iso("zs0", pts)]))
    result = alarm_metric_sweep(
        call,
        "cpu-high",
        start_time="2023-11-14T18:00:00Z",
        end_time="2023-11-14T19:00:00Z",
        period_s=300,
        clock=lambda: 1_700_030_000.0,
    )
    series = result["value"]["series"][0]
    assert series["datapoint_count"] == 3
    assert series["zero_count"] == 1
    assert series["max"] == 99.0
    assert series["peak_timestamp"] == "2023-11-14T18:05:00Z"
    assert series["missing_count"] > 0
    assert series["trailing_missing_count"] > 0
    assert series["longest_nonzero_run"] == 2
    summary = result["value"]["summary"]
    assert summary["series_with_gaps"] >= 1
    assert summary["series_stopped_reporting"]


# --------------------------------------------- enumeration edges


def test_other_dimension_sets_are_reported_not_swept():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm()]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue(
        "ListMetrics",
        _list_metrics(
            [
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": "i-1"}],
                },
                # Different dimension-name set: counted, not swept.
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [
                        {"Name": "AutoScalingGroupName", "Value": "g"}
                    ],
                },
            ]
        ),
    )
    call.queue("GetMetricData", _metric_data([_series("alarm_metric", [1.0])]))
    call.queue("GetMetricData", _metric_data([_series("zs0", [1.0])]))
    result = _run(call)
    report = result["value"]["enumeration"]["metrics"][0]
    assert report["unswept_dimension_sets"]
    assert any("other dimension sets" in g for g in result["guidance"])


def test_max_series_cap_drops_and_marks_partial():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm()]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue(
        "ListMetrics",
        _list_metrics(
            [
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": f"i-{n}"}],
                }
                for n in range(3)
            ]
        ),
    )
    call.queue("GetMetricData", _metric_data([_series("alarm_metric", [1.0])]))
    call.queue("GetMetricData", _metric_data([_series("zs0", [1.0])]))
    result = _run(call, max_series=1)
    assert len(result["value"]["series"]) == 1
    assert result["value"]["enumeration"]["series_dropped"] == 2
    assert result["is_exhaustive"] is False
    assert any("max-series" in g for g in result["guidance"])


# --------------------------------------------- internal error boundary


def test_internal_exception_is_returned_as_service_error():
    # Contract: alarm_metric_sweep "never raises". If the injected call bridge
    # blows up with something that is NOT an errors-as-data result (an
    # unexpected botocore shape, a bug), the outer boundary must convert it into
    # a SERVICE_ERROR result -- mirroring the Athena/Logs/ECS siblings -- rather
    # than let the traceback escape to the caller.
    def exploding(operation, params):
        raise RuntimeError("kaboom")

    result = _run(exploding, alarm_name="cpu-high")
    assert result["ok"] is False
    assert result["code"] == "SERVICE_ERROR"
    assert "internal error" in result["error"]
    assert "kaboom" in result["error"]  # original cause preserved for triage


def test_normal_structured_errors_are_not_swallowed_by_the_boundary():
    # The never-raise boundary must NOT turn a legitimate structured error (an
    # errors-as-data result returned by the bridge) into a generic SERVICE_ERROR:
    # a NOT_FOUND from resolution must still surface verbatim.
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe())  # exact miss
    call.queue("DescribeAlarms", _describe())  # prefix miss
    result = _run(call, alarm_name="ghost")
    assert result["ok"] is False
    assert result["code"] == "NOT_FOUND"


# --------------------------------------------- ITEM 1: window anchoring


def test_window_anchored_to_state_updated_timestamp():
    call = ScriptedCW()
    alarm = _metric_alarm()
    alarm["StateValue"] = "ALARM"
    alarm["StateUpdatedTimestamp"] = "2023-11-14T20:00:00Z"
    alarm["Period"] = 300
    alarm["EvaluationPeriods"] = 2
    call.queue("DescribeAlarms", _describe(metric=[alarm]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue("GetMetricData", _metric_data([_series("alarm_metric", [1.0])]))
    call.queue("GetMetricData", _metric_data([_series("zs0", [1.0])]))
    # No explicit start/end/period -> all anchored to the alarm.
    result = alarm_metric_sweep(call, "cpu-high", clock=_fixed_clock())
    assert result["ok"] is True
    window = result["value"]["window"]
    # End = StateUpdatedTimestamp; span = Period * EvaluationPeriods * 3 = 1800s.
    assert window["end"] == "2023-11-14T20:00:00Z"
    assert window["start"] == "2023-11-14T19:30:00Z"
    assert window["period_s"] == 300  # the alarm's own Period
    assert any("StateUpdatedTimestamp" in g for g in result["guidance"])


def test_insufficient_data_alarm_anchors_window_end_to_now():
    call = ScriptedCW()
    alarm = _metric_alarm()
    alarm["StateValue"] = "INSUFFICIENT_DATA"
    alarm["StateUpdatedTimestamp"] = "2020-01-01T00:00:00Z"  # must be ignored
    call.queue("DescribeAlarms", _describe(metric=[alarm]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue("GetMetricData", _metric_data([_series("alarm_metric", [1.0])]))
    call.queue("GetMetricData", _metric_data([_series("zs0", [1.0])]))
    result = alarm_metric_sweep(
        call, "cpu-high", clock=_fixed_clock(1_700_030_000.0)
    )
    assert result["ok"] is True
    # End defaults to "now", not the stale StateUpdatedTimestamp.
    assert result["value"]["window"]["end"].startswith("2023-11-15")


# --------------------------------------------- ITEM 2: pin by default / fan-out


def test_pinned_dimensions_by_default_no_fan_out():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm()]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue("GetMetricData", _metric_data([_series("alarm_metric", [1.0])]))
    call.queue("GetMetricData", _metric_data([_series("zs0", [1.0])]))
    # fan_out omitted -> default (no enumeration).
    result = alarm_metric_sweep(
        call,
        "cpu-high",
        start_time="2023-11-14T18:00:00Z",
        end_time="2023-11-14T21:00:00Z",
        clock=_fixed_clock(),
    )
    assert result["ok"] is True
    assert "ListMetrics" not in call.ops()  # no fan-out
    series = result["value"]["series"]
    assert len(series) == 1
    assert series[0]["role"] == "target"
    assert series[0]["dimensions"] == [{"Name": "InstanceId", "Value": "i-1"}]


def test_fan_out_flag_enables_enumeration():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm()]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue(
        "ListMetrics",
        _list_metrics(
            [
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": "i-1"}],
                },
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": "i-2"}],
                },
            ]
        ),
    )
    call.queue("GetMetricData", _metric_data([_series("alarm_metric", [1.0])]))
    call.queue(
        "GetMetricData",
        _metric_data([_series("zs0", [1.0]), _series("zs1", [2.0])]),
    )
    result = alarm_metric_sweep(
        call,
        "cpu-high",
        start_time="2023-11-14T18:00:00Z",
        end_time="2023-11-14T21:00:00Z",
        clock=_fixed_clock(),
        fan_out=True,
    )
    assert result["ok"] is True
    assert "ListMetrics" in call.ops()
    assert len(result["value"]["series"]) == 2
    assert "dimension_sibling" in {
        s["role"] for s in result["value"]["series"]
    }


# --------------------------------------------- ITEM 4: unsupported alarm types


def test_unsupported_promql_alarm_type_is_detected():
    call = ScriptedCW()
    promql = {
        "AlarmName": "promql-alarm",
        "AlarmArn": "arn:aws:cloudwatch:us-east-1:1:alarm:promql-alarm",
        "StateValue": "ALARM",
        "Metrics": [
            {
                "Id": "q1",
                "Expression": "rate(http_requests_total[5m])",
                "Period": 60,
            }
        ],
    }
    call.queue("DescribeAlarms", _describe(metric=[promql]))
    result = _run(call, alarm_name="promql-alarm")
    assert result["ok"] is False
    assert result["code"] == "UNSUPPORTED_ALARM_TYPE"
    assert result["value"]["raw_metrics"]  # raw config attached for triage
    assert "GetMetricData" not in call.ops()  # bailed before any data call


def test_unsupported_log_alarm_type_is_detected():
    call = ScriptedCW()
    log_alarm = {
        "AlarmName": "log-alarm",
        "AlarmArn": "arn:aws:cloudwatch:us-east-1:1:alarm:log-alarm",
        "StateValue": "ALARM",
        "Metrics": [
            {"Id": "q1", "Period": 60}
        ],  # no MetricStat, no Expression
    }
    call.queue("DescribeAlarms", _describe(metric=[log_alarm]))
    result = _run(call, alarm_name="log-alarm")
    assert result["ok"] is False
    assert result["code"] == "UNSUPPORTED_ALARM_TYPE"
    assert "Log" in result["value"]["detected_type"]


# --------------------------------------------- ITEM 5: exact match by default


def test_exact_match_required_by_default_lists_candidates():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe())  # exact miss
    call.queue(
        "DescribeAlarms",
        _describe(metric=[_metric_alarm("cpu-high-1")]),  # prefix candidate
    )
    result = alarm_metric_sweep(
        call,
        "cpu-high",
        start_time="2023-11-14T18:00:00Z",
        end_time="2023-11-14T21:00:00Z",
        clock=_fixed_clock(),
    )
    assert result["ok"] is False
    assert result["code"] == "NOT_FOUND"
    assert any("cpu-high-1" in g for g in result["guidance"])
    assert any("--fuzzy" in g for g in result["guidance"])
    assert "GetMetricData" not in call.ops()


# --------------------------------------------- ITEM 6: AccountId preserved


def test_account_id_preserved_in_get_metric_data():
    call = ScriptedCW()
    math_alarm = {
        "AlarmName": "xacct",
        "AlarmArn": "arn:aws:cloudwatch:us-east-1:1:alarm:xacct",
        "StateValue": "ALARM",
        "Metrics": [
            {
                "Id": "m1",
                "AccountId": "222233334444",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EC2",
                        "MetricName": "CPUUtilization",
                        "Dimensions": [{"Name": "InstanceId", "Value": "i-1"}],
                    },
                    "Period": 300,
                    "Stat": "Average",
                },
            }
        ],
    }
    call.queue("DescribeAlarms", _describe(metric=[math_alarm]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue(
        "ListMetrics",
        _list_metrics(
            [
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": "i-1"}],
                }
            ]
        ),
    )
    call.queue("GetMetricData", _metric_data([_series("m1", [1.0])]))
    call.queue("GetMetricData", _metric_data([_series("zs0", [1.0])]))
    result = _run(call, alarm_name="xacct")
    assert result["ok"] is True
    gmd = [params for op, params in call.calls if op == "GetMetricData"]
    # Replay (original) query carries the alarm's AccountId...
    assert gmd[0]["MetricDataQueries"][0]["AccountId"] == "222233334444"
    # ...and so does the enumerated series query.
    assert gmd[1]["MetricDataQueries"][0]["AccountId"] == "222233334444"


# --------------------------------------------- ITEM 7: tail truncation


def test_per_series_truncation_keeps_tail_newest():
    call = ScriptedCW()
    call.queue("DescribeAlarms", _describe(metric=[_metric_alarm()]))
    call.queue("DescribeAlarmHistory", _history())
    call.queue(
        "ListMetrics",
        _list_metrics(
            [
                {
                    "Namespace": "AWS/EC2",
                    "MetricName": "CPUUtilization",
                    "Dimensions": [{"Name": "InstanceId", "Value": "i-1"}],
                }
            ]
        ),
    )
    many = [float(i) for i in range(12)]
    call.queue("GetMetricData", _metric_data([_series("alarm_metric", many)]))
    call.queue("GetMetricData", _metric_data([_series("zs0", many)]))
    result = _run(call, period_s=300, max_datapoints=5)
    dps = result["value"]["series"][0]["datapoints"]
    assert len(dps) == 5
    # Tail (most recent) kept, not the head.
    assert [v for _, v in dps] == [7.0, 8.0, 9.0, 10.0, 11.0]


# --------------------------------------------- ITEM 3: composite child parsing


def test_composite_children_handle_parens_and_arns():
    call = ScriptedCW()
    rule = (
        'ALARM("weird-)-name") OR '
        'OK("arn:aws:cloudwatch:us-east-1:1:alarm:child-b") OR '
        "INSUFFICIENT_DATA(plain-child)"
    )
    composite = {
        "AlarmName": "parent",
        "AlarmArn": "arn:aws:cloudwatch:us-east-1:1:alarm:parent",
        "StateValue": "ALARM",
        "AlarmRule": rule,
    }
    call.queue("DescribeAlarms", _describe(composite=[composite]))
    call.queue("DescribeAlarmHistory", _history())
    result = _run(call, alarm_name="parent")
    assert result["ok"] is True
    assert result["value"]["target"]["child_alarms"] == [
        "weird-)-name",
        "arn:aws:cloudwatch:us-east-1:1:alarm:child-b",
        "plain-child",
    ]
    assert "GetMetricData" not in call.ops()
