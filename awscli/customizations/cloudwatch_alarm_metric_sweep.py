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
"""``aws cloudwatch alarm-metric-sweep``: investigate a CloudWatch alarm in ONE call.

Replaces the hand-rolled ``describe-alarms -> describe-alarm-history -> list-metrics
-> get-metric-data`` chain that callers otherwise assemble by hand. A single
read-only verb resolves the alarm, reads its state history, pulls per-series
timelines for the alarm's own metric(s) on a period-aligned grid, and -- with
``--fan-out`` -- also enumerates every series that shares the alarm metric's
dimension-name set (plus error-rate siblings).

This command returns a result object from every call and never raises; it keeps
an "errors as data" control flow via the shared
:mod:`awscli.customizations.compositereadonly.helpers` bridge and maps the final result
to a CLI exit code.

Behaviour contract:

* **Resolution** -- an exact alarm name is required by default and never
  silently rerouted; a miss returns a clear not-found result listing the closest
  candidate names. ``--fuzzy`` opts into the bounded, deterministic prefix/fuzzy
  fallback (shared :func:`resolve_alarm`).
* **Pagination / bounds** -- ``DescribeAlarmHistory``, ``ListMetrics`` and
  ``GetMetricData`` all follow ``NextToken`` under a ``--max-pages`` cap; a
  partial read degrades ``is_exhaustive`` instead of failing.
* **Period / time-window** -- by default the window ends at the alarm's
  ``StateUpdatedTimestamp`` (or now for INSUFFICIENT_DATA), spans 3x the alarm's
  evaluation window, and uses the alarm's own ``Period``; it is aligned to the
  period, which is raised for retention and the 1,440-points-per-series budget.
  Every adjustment is reported in ``guidance``.
* **Output capping** -- series are capped by ``--max-series`` and per-series
  datapoints by ``--max-datapoints`` (keeping the most recent points); a global
  ``--max-total-datapoints`` budget trims later datapoint arrays to the most
  recent points that still fit, then drops the rest (keeping their summaries) so
  a wide sweep returns a bounded response. Every adjustment is recorded.

The command is strictly read-only: it only issues ``Describe*`` / ``Get*`` /
``List*`` calls, and the shared :func:`call` bridge refuses any mutating
operation by construction.
"""

from __future__ import annotations

import difflib
import json
import math
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from awscli.customizations.commands import BasicCommand
from awscli.customizations.compositereadonly.helpers import (
    NOT_FOUND,
    SERVICE_ERROR,
    call,
    check_non_empty_str,
    check_positive_int,
    create_read_client,
    emit_result,
    err_result,
    invalid_input,
    ok_result,
    paginate,
)

UTC = timezone.utc

# --- GetMetricData bounds ----------------------------------------------------
# GetMetricData accepts at most 500 MetricDataQueries and ~100,800 datapoints
# per call; a single series is capped at 1,440 points (the window is re-perioded
# to fit). These keep one call from running away.
_MAX_QUERIES = 500
_MAX_POINTS_PER_CALL = 100_800
_MAX_POINTS = 1_440
# Default global budget for emitted datapoints across the enumerated series. A
# wide alarm (many dimension values x sibling metrics) can list hundreds of
# series; without a ceiling the JSON grows without bound. 0 disables.
_DEFAULT_MAX_TOTAL_DATAPOINTS = 50_000
# Period ladder used when re-perioding to honour the per-series point budget.
_LADDER = (60, 120, 300, 600, 900, 1800, 3600, 10800, 21600, 43200, 86400)
# Accepted CloudWatch statistics (standard + percentile/trimmed forms).
_STAT_RE = re.compile(
    r"^(SampleCount|Average|Sum|Minimum|Maximum|IQM|p\d{1,2}(\.\d+)?|p100|"
    r"(tm|wm|tc|ts)\d{1,2}(\.\d+)?|(TM|WM|TC|TS|PR)\([^)]*\))$"
)
# An alarm/metric whose name looks like an error-rate target; only then do we
# also sweep its sibling status-code/success metrics (keeps the sweep focused).
_ERR_RE = re.compile(
    r"(error|fault|fail|5xx|4xx|5\d\d|success|availability)", re.IGNORECASE
)
_SIB_RE = re.compile(
    r"(error|fault|fail|5xx|4xx|5\d\d|4\d\d|2xx|success|request|count|"
    r"invocation|throttl)",
    re.IGNORECASE,
)
# Composite-alarm child extraction: a small scanner (not a regex) so a child
# name containing ')' inside quotes, or a full ARN, survives intact. Scan for
# ALARM(/OK(/INSUFFICIENT_DATA(, then read a quoted name to its closing quote or
# an unquoted name to the matching ')'.
_CHILD_TOKENS = ("ALARM(", "OK(", "INSUFFICIENT_DATA(")


def _composite_children(rule: str) -> list[str]:
    """Extract child alarm names/ARNs from a composite alarm rule expression.

    Handles quoted names (read between quotes, so an embedded ``)`` is kept),
    bare unquoted names (read to the closing ``)``), and ARN references
    (preserved whole). Nested composites are not recursed into; only directly
    referenced children are returned, de-duplicated in first-seen order.
    """
    out: list[str] = []
    i, n = 0, len(rule or "")
    while i < n:
        tok = next((t for t in _CHILD_TOKENS if rule.startswith(t, i)), None)
        if tok is None:
            i += 1
            continue
        j = i + len(tok)
        while j < n and rule[j].isspace():
            j += 1
        if j < n and rule[j] == '"':
            j += 1
            start = j
            while j < n and rule[j] != '"':
                j += 1
            name = rule[start:j]
            j += 1  # skip the closing quote
        else:
            start = j
            while j < n and rule[j] != ")":
                j += 1
            name = rule[start:j].strip()
        if name and name not in out:
            out.append(name)
        i = j + 1
    return out


# GetMetricData per-page status precedence (a later page's status supersedes an
# earlier PartialData, but never downgrades a hard Forbidden/InternalError).
_RANK = {
    "Complete": 0,
    "PartialData": 1,
    "Forbidden": 2,
    "InternalError": 3,
    "NoResult": 3,
}
# Alarm fields surfaced verbatim in the target definition.
_ALARM_FIELDS = (
    "AlarmName",
    "AlarmArn",
    "AlarmDescription",
    "StateValue",
    "StateReason",
    "StateUpdatedTimestamp",
    "Namespace",
    "MetricName",
    "Dimensions",
    "Statistic",
    "ExtendedStatistic",
    "Period",
    "Unit",
    "EvaluationPeriods",
    "DatapointsToAlarm",
    "Threshold",
    "ComparisonOperator",
    "TreatMissingData",
    "Metrics",
    "AlarmRule",
)

CallFn = Callable[[str, dict[str, Any]], dict[str, Any]]


# ----------------------------------------------------------------- time helpers
def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(int(epoch), UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _dt(v: Any) -> datetime | None:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=UTC)
    if isinstance(v, str) and v.strip():
        text = v.strip()
        text = text[:-1] + "+00:00" if text[-1] in "Zz" else text
        try:
            d = datetime.fromisoformat(text)
        except ValueError:
            return None
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    return None


def _js(o: Any) -> Any:
    """Recursively JSON-normalize datetimes so the payload is plain CLI JSON."""
    if isinstance(o, datetime):
        return _iso(_dt(o).timestamp())  # type: ignore[union-attr]
    if isinstance(o, dict):
        return {str(k): _js(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_js(v) for v in o]
    return o


def _pages(
    call_op: CallFn, op: str, params: dict[str, Any], key: str, max_pages: int
) -> tuple[list[dict[str, Any]], bool, dict[str, Any] | None]:
    """Follow NextToken to the end (or max_pages). Returns (items, complete, err).

    ``complete`` is False when the bounded loop stopped on ``max_pages`` with a
    token still outstanding, so the caller can mark the sweep partial.
    """
    # Thin service-scoped wrapper over the shared helper: ListMetrics /
    # DescribeAlarmHistory / GetMetricData all return dict-shaped items, so a
    # non-dict entry is filtered out as it was before.
    return paginate(
        call_op,
        op,
        params,
        key,
        max_pages,
        item_filter=lambda i: isinstance(i, dict),
    )


# Bounded paging / fuzzy cutoff for alarm resolution so a lookup can never run
# away on an account with thousands of alarms.
_MAX_ALARM_PAGES = 5
_FUZZY_CUTOFF = 0.6
_ALARM_TYPES = ["MetricAlarm", "CompositeAlarm"]


def _alarms_from(value: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten DescribeAlarms metric + composite alarms into one list."""
    return list(value.get("MetricAlarms") or []) + list(
        value.get("CompositeAlarms") or []
    )


def _describe_prefix(
    call_op: CallFn, prefix: str
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """DescribeAlarms by name prefix, following NextToken (bounded)."""
    alarms: list[dict[str, Any]] = []
    token: str | None = None
    for _ in range(_MAX_ALARM_PAGES):
        params: dict[str, Any] = {
            "AlarmNamePrefix": prefix,
            "AlarmTypes": _ALARM_TYPES,
        }
        if token:
            params["NextToken"] = token
        res = call_op("DescribeAlarms", params)
        if not res["ok"]:
            return alarms, res
        value = res.get("value") or {}
        alarms.extend(_alarms_from(value))
        token = value.get("NextToken")
        if not token:
            break
    return alarms, None


def resolve_alarm(
    call_op: CallFn, name: str, *, fuzzy: bool = False
) -> dict[str, Any]:
    """Resolve a CloudWatch alarm by exact name (prefix/fuzzy only with ``fuzzy``).

    ``call_op(operation, params)`` is the read-only call bridge bound to a
    CloudWatch client. Resolution order:

    1. **Exact** -- ``DescribeAlarms AlarmNames=[name]``. A hit short-circuits
       with no fallback, so an exact name is never silently rerouted.
    2. **Prefix** -- ``DescribeAlarms AlarmNamePrefix=name`` (bounded paging). A
       single candidate is used; a case-insensitive exact match among several is
       preferred before considering it ambiguous.
    3. **Fuzzy** -- a bounded, deterministic ``difflib`` ranking over the prefix
       candidates only (no extra scan). The closest fuzzy match above the cutoff
       is used; if no match, NOT_FOUND with the candidate list.

    The value is ``{"alarm": <alarm dict>, "kind": "metric_alarm"|
    "composite_alarm", "match": "exact"|"prefix"|"fuzzy", "guidance": [...]}``.
    """
    # 1. Exact.
    exact = call_op(
        "DescribeAlarms", {"AlarmNames": [name], "AlarmTypes": _ALARM_TYPES}
    )
    if not exact["ok"]:
        return exact
    metric = (exact.get("value") or {}).get("MetricAlarms") or []
    composite = (exact.get("value") or {}).get("CompositeAlarms") or []
    if metric or composite:
        alarm = (metric or composite)[0]
        return ok_result(
            {
                "alarm": alarm,
                "kind": "metric_alarm" if metric else "composite_alarm",
                "match": "exact",
                "guidance": [],
            }
        )

    # 2. Prefix.
    candidates, err = _describe_prefix(call_op, name)
    if err is not None:
        return err
    if not candidates:
        return err_result(
            NOT_FOUND,
            f"No alarm named or prefixed by {name!r}.",
            key=name,
            guidance=[
                "Alarm names are exact and case-sensitive; list candidates with "
                "'aws cloudwatch describe-alarms --alarm-name-prefix <prefix>'.",
                "Alarms are regional: pass --region.",
            ],
        )
    by_name = {a.get("AlarmName"): a for a in candidates if a.get("AlarmName")}
    if not fuzzy:
        # Exact-match-only (default): the exact DescribeAlarms above missed, so
        # report the closest candidates and let the caller correct, rather than
        # silently resolving to a prefix/fuzzy hit.
        names_sorted = sorted(by_name)
        ranked = difflib.get_close_matches(
            name, names_sorted, n=5, cutoff=_FUZZY_CUTOFF
        )
        listed = ranked or names_sorted[:5]
        return err_result(
            NOT_FOUND,
            f"No alarm named exactly {name!r}.",
            key=name,
            guidance=[
                f"Did you mean: {', '.join(listed)}"
                + (" ..." if len(names_sorted) > len(listed) else ""),
                "Pass the exact --alarm-name, or add --fuzzy to allow "
                "prefix/fuzzy resolution.",
            ],
        )
    if len(candidates) == 1:
        return _prefix_hit(candidates[0], name)
    # Several share the prefix: prefer a unique case-insensitive exact match.
    ci_matches = [
        a
        for a in candidates
        if (a.get("AlarmName") or "").casefold() == name.casefold()
    ]
    if len(ci_matches) == 1:
        return _prefix_hit(ci_matches[0], name, note="case-insensitive exact")

    # 3. Fuzzy over the already-fetched candidate names (bounded, deterministic).
    names_sorted = sorted(by_name)
    close = difflib.get_close_matches(
        name, names_sorted, n=2, cutoff=_FUZZY_CUTOFF
    )
    if close:
        chosen = by_name[close[0]]
        return _prefix_hit(chosen, name, match="fuzzy")
    # Ambiguous: report the candidates rather than guessing.
    listed = ", ".join(names_sorted[:10])
    return err_result(
        NOT_FOUND,
        f"{name!r} is ambiguous: {len(candidates)} alarms share this prefix "
        "and none is an unambiguous match.",
        key=name,
        guidance=[
            f"Matching alarms: {listed}"
            + (" ..." if len(names_sorted) > 10 else ""),
            "Pass --alarm-name with one of these exact names.",
        ],
    )


def _prefix_hit(
    alarm: dict[str, Any],
    requested: str,
    *,
    match: str = "prefix",
    note: str = "",
) -> dict[str, Any]:
    kind = "composite_alarm" if alarm.get("AlarmRule") else "metric_alarm"
    resolved = alarm.get("AlarmName")
    detail = f" ({note})" if note else ""
    guidance = (
        []
        if match == "exact"
        else [
            f"No alarm named exactly {requested!r}; resolved to {resolved!r} "
            f"by {match} match{detail}."
        ]
    )
    return ok_result(
        {"alarm": alarm, "kind": kind, "match": match, "guidance": guidance}
    )


# ------------------------------------------------------------------- validation
def _validate(
    alarm_name: Any,
    stat: Any,
    pins: Any,
    max_series: Any,
    max_pages: Any,
    max_datapoints: Any,
    max_total_datapoints: Any,
) -> list[str]:
    """Validate inputs that are checkable before any API call."""
    p: list[str] = []
    name_err = check_non_empty_str("alarm_name", alarm_name, required=True)
    if name_err is not None:
        p.append(f"{name_err} Pass the exact alarm name, or a unique prefix.")
    if stat is not None and (
        not isinstance(stat, str) or not _STAT_RE.match(stat)
    ):
        p.append(
            f"stat={stat!r} is not a CloudWatch statistic; use Sum, Average, "
            "Minimum, Maximum, SampleCount or a percentile like p99 (lowercase p)."
        )
    # pin_dimensions is a list of dimension NAMES; a non-string entry is the
    # "malformed pin" case and is rejected rather than silently dropped.
    if pins is not None and (
        not isinstance(pins, (list, tuple))
        or not all(isinstance(x, str) for x in pins)
    ):
        p.append(
            "pin_dimensions must be a list of dimension names, e.g. "
            "['AvailabilityZone']."
        )
    for name, v, hi in (
        ("max_series", max_series, 2000),
        ("max_pages", max_pages, 500),
    ):
        err = check_positive_int(name, v, lo=1, hi=hi)
        if err is not None:
            p.append(err)
    for name, v in (
        ("max_datapoints", max_datapoints),
        ("max_total_datapoints", max_total_datapoints),
    ):
        err = check_positive_int(name, v, lo=0)
        if err is not None:
            p.append(f"{err} (0 disables the cap).")
    return p


def _window(
    start_time: Any,
    end_time: Any,
    period_s: Any,
    now: float,
    *,
    anchor_end: float | None = None,
    eval_span: int | None = None,
) -> dict[str, Any] | list[str]:
    """Resolve/validate the time window and period, returning errors as a list.

    The returned dict carries the aligned epochs, the effective period (raised
    for retention and for the per-series point budget) and every adjustment/alignment
    note so the caller can surface them in ``guidance``.
    """
    if (
        isinstance(period_s, bool)
        or not isinstance(period_s, int)
        or period_s <= 0
    ):
        return [
            f"period_s must be a positive int (got {period_s!r}); use 60, 300 or 3600."
        ]
    errs: list[str] = []
    if period_s not in (1, 5, 10, 30) and period_s % 60:
        errs.append(
            f"period_s={period_s} is invalid: use 1, 5, 10, 30 or a multiple of "
            f"60 (e.g. {max(60, round(period_s / 60) * 60)})."
        )
    s, e = _dt(start_time), _dt(end_time)
    for name, raw, parsed in (
        ("start_time", start_time, s),
        ("end_time", end_time, e),
    ):
        if raw not in (None, "") and parsed is None:
            errs.append(
                f"{name}={raw!r} is not ISO-8601; use e.g. '2024-01-15T21:00:00Z'."
            )
    if errs:
        return errs
    now_dt = datetime.fromtimestamp(now, UTC)
    notes: list[str] = []
    if e is None:
        if anchor_end is not None:
            e = datetime.fromtimestamp(anchor_end, UTC)
            notes.append(
                "end_time defaulted to the alarm's StateUpdatedTimestamp "
                f"({_iso(anchor_end)})."
            )
        else:
            e = now_dt
            notes.append(f"end_time defaulted to now ({_iso(now)}).")
    if s is None:
        if eval_span:
            # 3x the alarm's evaluation window (Period * EvaluationPeriods) so
            # the sweep brackets the state change with context on either side.
            s = e - timedelta(seconds=eval_span)
            notes.append(
                f"start_time defaulted to end_time - {eval_span}s "
                "(3x the alarm's Period * EvaluationPeriods)."
            )
        else:
            s = e - timedelta(hours=3)
            notes.append("start_time defaulted to end_time - 3h.")
    if s >= e:
        return [
            f"start_time ({_iso(s.timestamp())}) must be before end_time "
            f"({_iso(e.timestamp())})."
        ]
    if e > now_dt:
        e = now_dt
        notes.append(
            f"end_time is in the future: clamped to now ({_iso(now)})."
        )
        if s >= e:
            return [
                "start_time is in the future; choose a window ending at or before now."
            ]
    age = now - s.timestamp()
    if age > 455 * 86400:
        return [
            "start_time is older than CloudWatch's 455-day retention; move start_time later."
        ]
    # CloudWatch only retains sub-minute/minute resolution for a limited age;
    # raise the period to the finest resolution still available for this window.
    min_p = (
        3600
        if age > 63 * 86400
        else 300
        if age > 15 * 86400
        else 60
        if age > 3 * 3600
        else 1
    )
    period, clamped = period_s, []
    if period < min_p:
        clamped.append(
            f"period_s raised from {period} to {min_p}: data this old is only "
            f"retained at {min_p}s."
        )
        period = min_p
    span = e.timestamp() - s.timestamp()
    # Keep each series within the per-series point budget by widening the period.
    if math.ceil(span / period) > _MAX_POINTS:
        new = next(
            (
                c
                for c in _LADDER
                if c >= period and math.ceil(span / c) <= _MAX_POINTS
            ),
            86400,
        )
        clamped.append(
            f"period_s raised from {period} to {new} to keep <= {_MAX_POINTS} "
            "points per series; narrow the window for finer resolution."
        )
        period = new
    # Align the window to period boundaries so timestamps line up across series.
    s_ep = int(math.floor(s.timestamp() / period) * period)
    e_ep = max(int(math.ceil(e.timestamp() / period) * period), s_ep + period)
    if (s_ep, e_ep) != (s.timestamp(), e.timestamp()):
        notes.append(
            f"Window aligned to {period}s boundaries: {_iso(s_ep)} .. {_iso(e_ep)}."
        )
    return {
        "start": _iso(s_ep),
        "end": _iso(e_ep),
        "start_epoch": s_ep,
        "end_epoch": e_ep,
        "period_s_requested": period_s,
        "period_s": period,
        "min_period_s": min_p,
        "expected_points_per_series": (e_ep - s_ep) // period,
        "clamped": clamped,
        "notes": notes,
    }


def _validate_window_inputs(
    start_time: Any, end_time: Any, period_s: Any
) -> list[str]:
    """Pre-dispatch window/period checks that need no alarm data.

    Only format-level problems are reported here (bad period, non-ISO times, an
    explicit start at/after an explicit end) so they fail fast as INVALID_INPUT
    with nothing dispatched. Anchor-based defaulting happens later in
    :func:`_window`, once the alarm has been resolved.
    """
    errs: list[str] = []
    if period_s is not None:
        if (
            isinstance(period_s, bool)
            or not isinstance(period_s, int)
            or period_s <= 0
        ):
            errs.append(
                f"period_s must be a positive int (got {period_s!r}); use 60, "
                "300 or 3600."
            )
        elif period_s not in (1, 5, 10, 30) and period_s % 60:
            errs.append(
                f"period_s={period_s} is invalid: use 1, 5, 10, 30 or a "
                f"multiple of 60 (e.g. {max(60, round(period_s / 60) * 60)})."
            )
    s, e = _dt(start_time), _dt(end_time)
    for name, raw, parsed in (
        ("start_time", start_time, s),
        ("end_time", end_time, e),
    ):
        if raw not in (None, "") and parsed is None:
            errs.append(
                f"{name}={raw!r} is not ISO-8601; use e.g. "
                "'2024-01-15T21:00:00Z'."
            )
    if not errs and s is not None and e is not None and s >= e:
        errs.append(
            f"start_time ({_iso(s.timestamp())}) must be before end_time "
            f"({_iso(e.timestamp())})."
        )
    return errs


def _anchor(
    alarm: dict[str, Any], period_s: Any
) -> tuple[float | None, int | None, int]:
    """Derive (anchor_end, eval_span, period) window defaults from the alarm.

    * ``anchor_end`` -- the alarm's ``StateUpdatedTimestamp`` when it is in
      ALARM/OK (so the window ends at the state change); ``None`` for
      INSUFFICIENT_DATA or a missing timestamp, which defers to ``now``.
    * ``eval_span`` -- ``Period * EvaluationPeriods * 3`` seconds, the default
      look-back, or ``None`` when the alarm carries neither.
    * ``period`` -- the explicit ``period_s`` when given, else the alarm's own
      ``Period``, else 300s.
    """
    sut = _dt(alarm.get("StateUpdatedTimestamp"))
    anchor_end = (
        sut.timestamp()
        if alarm.get("StateValue") in ("ALARM", "OK") and sut is not None
        else None
    )
    ap = alarm.get("Period")
    alarm_period = (
        ap
        if isinstance(ap, int) and not isinstance(ap, bool) and ap > 0
        else None
    )
    ep = alarm.get("EvaluationPeriods")
    eval_span = (
        alarm_period * ep * 3
        if alarm_period
        and isinstance(ep, int)
        and not isinstance(ep, bool)
        and ep > 0
        else None
    )
    period = (
        period_s
        if isinstance(period_s, int) and not isinstance(period_s, bool)
        else (alarm_period or 300)
    )
    return anchor_end, eval_span, period


# ------------------------------------------------------------ step 1: target
def _target_metric(
    ms: Any, qid: str, account_id: str | None = None
) -> dict[str, Any] | None:
    m = (ms or {}).get("Metric") or {} if isinstance(ms, dict) else {}
    if not m.get("Namespace") or not m.get("MetricName"):
        return None
    return {
        "namespace": m["Namespace"],
        "metric_name": m["MetricName"],
        "dimensions": list(m.get("Dimensions") or []),
        "stat": ms.get("Stat") or "Average",
        "unit": ms.get("Unit"),
        "account_id": account_id,
        "source_id": qid,
    }


def _load_from_alarm(
    alarm: dict[str, Any],
    kind: str,
    match: str,
    resolve_guidance: list[str],
    requested: str,
) -> dict[str, Any]:
    """Build the sweep target + replay queries from a resolved alarm.

    ``resolve_alarm`` has already issued ``DescribeAlarms``; this takes the
    returned alarm dict and shapes it into the command's target descriptor.
    """
    name = alarm.get("AlarmName", requested)
    out: dict[str, Any] = {
        "target": {
            "kind": kind,
            "alarm_name": name,
            "alarm_arn": alarm.get("AlarmArn"),
            "match": match,
            "definition": _js(
                {
                    k: alarm[k]
                    for k in _ALARM_FIELDS
                    if alarm.get(k) is not None
                }
            ),
        },
        "originals": [],
        "metrics": [],
        "history": [name],
        "notes": list(resolve_guidance),
    }
    if kind == "composite_alarm":
        # A composite alarm owns no metrics of its own; surface its children so
        # the caller can re-run the sweep against one of them.
        children = _composite_children(alarm.get("AlarmRule") or "")
        out["target"]["child_alarms"] = children
        out["notes"].append(
            "Composite alarm has no metrics of its own; re-run with "
            f"--alarm-name set to one of its children: {children}."
        )
        return out
    if alarm.get("MetricName"):
        # Single-metric alarm: one replay query.
        ms = {
            "Metric": {
                "Namespace": alarm.get("Namespace"),
                "MetricName": alarm["MetricName"],
                "Dimensions": list(alarm.get("Dimensions") or []),
            },
            "Period": int(alarm.get("Period") or 60),
            "Stat": alarm.get("ExtendedStatistic")
            or alarm.get("Statistic")
            or "Average",
            **({"Unit": alarm["Unit"]} if alarm.get("Unit") else {}),
        }
        out["originals"].append(
            {
                "Id": "alarm_metric",
                "MetricStat": ms,
                "Label": name,
                "ReturnData": True,
                # Preserve the alarm's source account so a monitoring-account
                # alarm replays against the alarm's account, not the caller's.
                **(
                    {"AccountId": alarm["AccountId"]}
                    if alarm.get("AccountId")
                    else {}
                ),
            }
        )
    else:
        # Metric-math alarm: replay each query (expose the inputs behind the math).
        for m in alarm.get("Metrics") or []:
            q = {
                k: json.loads(json.dumps(m[k], default=str))
                for k in (
                    "Id",
                    "MetricStat",
                    "Expression",
                    "Label",
                    "Period",
                    "AccountId",
                )
                if k in m
            }
            out["originals"].append({**q, "ReturnData": True})
    out["metrics"] = [
        t
        for q in out["originals"]
        if (
            t := _target_metric(
                q.get("MetricStat"), q["Id"], q.get("AccountId")
            )
        )
    ]
    return out


# ----------------------------------------------------------- step 2: history
def _history(
    call_op: CallFn, names: list[str], w: dict[str, Any], max_pages: int
) -> tuple[dict[str, Any], list[str]]:
    """Read alarm state transitions in the window (bounded NextToken paging)."""
    transitions: list[dict[str, Any]] = []
    warns: list[str] = []
    for name in names:
        items, done, err = _pages(
            call_op,
            "DescribeAlarmHistory",
            {
                "AlarmName": name,
                "HistoryItemType": "StateUpdate",
                "StartDate": w["start"],
                "EndDate": w["end"],
                "ScanBy": "TimestampAscending",
            },
            "AlarmHistoryItems",
            max_pages,
        )
        if err is not None:
            # A history read failure degrades the sweep to partial; it does not
            # abort it (the metric data is still worth returning).
            warns.append(
                f"DescribeAlarmHistory({name}) failed ({err['code']}: "
                f"{err['error']}); state history missing."
            )
        elif not done:
            warns.append(
                f"DescribeAlarmHistory({name}) stopped at max_pages={max_pages}; "
                "history is partial."
            )
        for it in items:
            try:
                data = json.loads(it.get("HistoryData") or "{}")
            except ValueError:
                data = {}
            new, old = data.get("newState") or {}, data.get("oldState") or {}
            ts = _dt(it.get("Timestamp"))
            transitions.append(
                {
                    "alarm_name": it.get("AlarmName"),
                    "timestamp": _iso(ts.timestamp()) if ts else None,
                    "old_state": old.get("stateValue"),
                    "new_state": new.get("stateValue"),
                    "reason": new.get("stateReason"),
                    "summary": it.get("HistorySummary"),
                    "recent_datapoints": _js(
                        (new.get("stateReasonData") or {}).get(
                            "recentDatapoints"
                        )
                    ),
                }
            )
    transitions.sort(key=lambda t: t["timestamp"] or "")
    return (
        {
            "alarm_names": names,
            "transitions": transitions,
            "count": len(transitions),
            "is_exhaustive": not warns,
        },
        warns,
    )


# --------------------------------------------------------- step 3: enumerate
def _spec(
    ns: str,
    name: str,
    dims: list[dict[str, Any]],
    stat: str,
    unit: str | None,
    role: str,
    account: str | None = None,
) -> dict[str, Any]:
    d = sorted(
        (
            {"Name": str(x.get("Name")), "Value": str(x.get("Value"))}
            for x in dims
        ),
        key=lambda x: x["Name"],
    )
    label = name + (
        " " + ",".join(f"{x['Name']}={x['Value']}" for x in d) if d else ""
    )
    return {
        "namespace": ns,
        "metric_name": name,
        "dimensions": d,
        "stat": stat,
        "unit": unit,
        "account_id": account,
        "role": role,
        "is_target": role == "target",
        "label": label,
    }


def _enumerate(
    call_op: CallFn,
    targets: list[dict[str, Any]],
    stat: str | None,
    pins: set[str],
    siblings: bool,
    max_series: int,
    max_pages: int,
) -> dict[str, Any]:
    """Enumerate every series sharing each target's dimension-name set.

    ``pins`` are dimension names kept at their target value while the rest are
    wildcarded, so the ListMetrics filter finds sibling dimension values. For an
    error-rate target the sibling status-code/success metrics are added too.
    """
    specs: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    warns: list[str] = []
    guidance: list[str] = []
    report: list[dict[str, Any]] = []
    cache: dict[
        str, tuple[list[dict[str, Any]], bool, dict[str, Any] | None]
    ] = {}
    complete = True

    def add(s: dict[str, Any]) -> None:
        k = (
            s["namespace"],
            s["metric_name"],
            tuple((d["Name"], d["Value"]) for d in s["dimensions"]),
            s["stat"],
        )
        if k not in seen:
            seen.add(k)
            specs.append(s)

    def listed(params):
        ck = json.dumps(params, sort_keys=True)
        if ck not in cache:
            cache[ck] = _pages(
                call_op, "ListMetrics", params, "Metrics", max_pages
            )
        return cache[ck]

    # The target series themselves always come first.
    for t in targets:
        add(
            _spec(
                t["namespace"],
                t["metric_name"],
                t["dimensions"],
                stat or t["stat"],
                t["unit"],
                "target",
                t.get("account_id"),
            )
        )
    for t in targets:
        names = {str(d.get("Name")) for d in t["dimensions"]}
        filt = [
            {"Name": d["Name"], "Value": d["Value"]}
            if d.get("Name") in pins
            else {"Name": d["Name"]}
            for d in t["dimensions"]
        ]
        found, done, err = listed(
            {
                "Namespace": t["namespace"],
                "MetricName": t["metric_name"],
                "Dimensions": filt,
            }
        )
        if err is not None or not done:
            complete = False
            warns.append(
                f"ListMetrics({t['namespace']}/{t['metric_name']}) incomplete "
                f"({err['code'] if err else f'max_pages={max_pages}'}); "
                "dimension enumeration is partial."
            )
        other: dict[str, int] = {}
        swept = 0
        for m in found:
            dn = {str(d.get("Name")) for d in m.get("Dimensions") or []}
            if dn == names:
                swept += 1
                add(
                    _spec(
                        t["namespace"],
                        t["metric_name"],
                        m.get("Dimensions") or [],
                        stat or t["stat"],
                        t["unit"],
                        "dimension_sibling",
                        t.get("account_id"),
                    )
                )
            else:
                other[",".join(sorted(dn))] = (
                    other.get(",".join(sorted(dn)), 0) + 1
                )
        if other:
            guidance.append(
                f"{sum(other.values())} more {t['metric_name']} series use other "
                f"dimension sets {sorted(other)}; they were not swept."
            )
        report.append(
            {
                "namespace": t["namespace"],
                "metric_name": t["metric_name"],
                "dimension_names": sorted(names),
                "pinned": sorted(names & pins),
                "series_listed": swept,
                "list_complete": err is None and done,
                "unswept_dimension_sets": [
                    {
                        "dimension_names": k.split(",") if k else [],
                        "series_count": v,
                    }
                    for k, v in sorted(other.items())
                ],
            }
        )
    sib_names: set[str] = set()
    if siblings:
        target_names = {(t["namespace"], t["metric_name"]) for t in targets}
        groups = {
            json.dumps(
                [t["namespace"], t["dimensions"]], sort_keys=True, default=str
            ): t
            for t in targets
        }
        for t in groups.values():
            dims = [
                {"Name": d["Name"], "Value": d["Value"]}
                for d in t["dimensions"]
            ]
            found, done, err = listed(
                {"Namespace": t["namespace"], "Dimensions": dims}
            )
            if err is not None or not done:
                complete = False
                warns.append(
                    f"Sibling ListMetrics in {t['namespace']} incomplete; "
                    "status-code metrics may be missing."
                )
            want = {(d["Name"], d["Value"]) for d in dims}
            for m in found:
                n = str(m.get("MetricName") or "")
                got = {
                    (str(d.get("Name")), str(d.get("Value")))
                    for d in m.get("Dimensions") or []
                }
                if (
                    n
                    and (t["namespace"], n) not in target_names
                    and _SIB_RE.search(n)
                    and got == want
                ):
                    sib_names.add(n)
                    add(
                        _spec(
                            t["namespace"],
                            n,
                            m.get("Dimensions") or [],
                            "Sum",
                            None,
                            "metric_sibling",
                        )
                    )
    # Cap the series count last (siblings dropped first via list order).
    dropped = max(0, len(specs) - max_series)
    if dropped:
        complete = False
        guidance.append(
            f"{dropped} series dropped by max_series={max_series} (siblings "
            "last); raise --max-series or pin a dimension with --pin-dimensions."
        )
    return {
        "series": specs[:max_series],
        "complete": complete,
        "warnings": warns,
        "guidance": guidance,
        "report": {
            "metrics": report,
            "sibling_metric_names": sorted(sib_names),
            "series_enumerated": len(specs),
            "series_dropped": dropped,
        },
    }


def _target_only_series(
    targets: list[dict[str, Any]], stat: str | None, max_series: int
) -> dict[str, Any]:
    """Build series for the alarm's own dimensions only (no ListMetrics fan-out).

    The default when ``--fan-out`` is off: every dimension stays pinned to the
    alarm's value, so the result is exactly the alarm's own metric(s). Shaped
    like :func:`_enumerate`'s return so the caller is agnostic to which ran.
    """
    specs: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for t in targets:
        s = _spec(
            t["namespace"],
            t["metric_name"],
            t["dimensions"],
            stat or t["stat"],
            t["unit"],
            "target",
            t.get("account_id"),
        )
        k = (
            s["namespace"],
            s["metric_name"],
            tuple((d["Name"], d["Value"]) for d in s["dimensions"]),
            s["stat"],
        )
        if k not in seen:
            seen.add(k)
            specs.append(s)
    dropped = max(0, len(specs) - max_series)
    guidance = (
        [
            f"{dropped} series dropped by max_series={max_series}; raise "
            "--max-series."
        ]
        if dropped
        else []
    )
    report = [
        {
            "namespace": t["namespace"],
            "metric_name": t["metric_name"],
            "dimension_names": sorted(
                str(d.get("Name")) for d in t["dimensions"]
            ),
            "pinned": sorted(str(d.get("Name")) for d in t["dimensions"]),
            "series_listed": 1,
            "list_complete": True,
            "unswept_dimension_sets": [],
        }
        for t in targets
    ]
    return {
        "series": specs[:max_series],
        "complete": dropped == 0,
        "warnings": [],
        "guidance": guidance,
        "report": {
            "metrics": report,
            "sibling_metric_names": [],
            "series_enumerated": len(specs),
            "series_dropped": dropped,
        },
    }


# -------------------------------------------------------------- step 4: data
def _fetch(
    call_op: CallFn,
    queries: list[dict[str, Any]],
    w: dict[str, Any],
    max_pages: int,
) -> tuple[dict[tuple[str, str], dict[str, Any]], bool, dict[str, Any] | None]:
    """Run GetMetricData for a batch of queries, following NextToken (bounded)."""
    items, done, err = _pages(
        call_op,
        "GetMetricData",
        {
            "MetricDataQueries": queries,
            "StartTime": w["start"],
            "EndTime": w["end"],
            "ScanBy": "TimestampAscending",
        },
        "MetricDataResults",
        max_pages,
    )
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for r in items:
        rid = str(r.get("Id") or "")
        e = out.setdefault(
            (rid, str(r.get("Label") or rid)),
            {
                "label": str(r.get("Label") or rid),
                "timestamps": [],
                "values": [],
                "status": "Complete",
                "messages": [],
            },
        )
        e["timestamps"] += r.get("Timestamps") or []
        e["values"] += r.get("Values") or []
        # PartialData on an earlier page is superseded by the final page's status.
        if _RANK.get(e["status"], 0) < 2:
            e["status"] = str(r.get("StatusCode") or "Complete")
        e["messages"] += [
            str(m.get("Value") or m.get("Code"))
            for m in r.get("Messages") or []
        ]
    return out, done, err


def _timeline(
    ts: list[Any],
    vals: list[Any],
    period: int,
    s_ep: int,
    e_ep: int,
    include: bool,
    max_datapoints: int,
) -> dict[str, Any]:
    """Build a per-series timeline on the aligned grid.

    Missing timestamps are reported separately from zeros; trailing gaps, peak
    and longest non-zero run are computed. When ``include`` is set the raw
    datapoints are emitted, truncated to ``max_datapoints`` (0 = no per-series
    cap) with the adjustment flagged so trimming is never silent.
    """
    g0 = s_ep // period * period
    grid = list(range(g0, -(-e_ep // period) * period, period))
    pts: dict[int, float] = {}
    off_grid = 0
    for t, v in zip(ts, vals):
        d = _dt(t)
        if d is not None and isinstance(v, (int, float)) and not math.isnan(v):
            ep = int(d.timestamp())
            off_grid += bool((ep - g0) % period)
            pts[ep] = float(v)
    missing = [g for g in grid if g not in pts]
    ranges: list[list[Any]] = []
    for g in missing:
        if ranges and g - ranges[-1][1] == period:
            ranges[-1][1], ranges[-1][2] = g, ranges[-1][2] + 1
        else:
            ranges.append([g, g, 1])
    trailing = next(
        (i for i, g in enumerate(reversed(grid)) if g in pts), len(grid)
    )
    run = best = 0
    for g in grid:
        run = run + 1 if pts.get(g, 0.0) != 0.0 else 0
        best = max(best, run)
    seq = sorted(pts.items())
    peak = max(seq, key=lambda kv: kv[1]) if seq else None
    out = {
        "period_s": period,
        "expected_count": len(grid),
        "datapoint_count": len(pts),
        "missing_count": len(missing),
        "missing_ranges": [[_iso(a), _iso(b), n] for a, b, n in ranges],
        "zero_count": sum(v == 0.0 for v in pts.values()),
        "off_grid_count": off_grid,
        "trailing_missing_count": trailing if seq else len(grid),
        "first_datapoint": _iso(seq[0][0]) if seq else None,
        "last_datapoint": _iso(seq[-1][0]) if seq else None,
        "sum": sum(v for _, v in seq) if seq else None,
        "min": min(v for _, v in seq) if seq else None,
        "max": peak[1] if peak else None,
        "peak_timestamp": _iso(peak[0]) if peak else None,
        "longest_nonzero_run": best,
        "longest_nonzero_run_s": best * period,
    }
    if include:
        dps = [[_iso(t), v] for t, v in seq]
        truncated = False
        # Per-series datapoint cap: keep the tail (most recent) because alarm
        # investigation focuses on what happened around the state change, which
        # sits at the end of the window.
        if max_datapoints and len(dps) > max_datapoints:
            dps = dps[-max_datapoints:]
            truncated = True
        out["datapoints"] = dps
        out["datapoints_truncated"] = truncated
    return out


def _qperiod(q: dict[str, Any], fallback: int) -> int:
    p = (
        (q.get("MetricStat") or {}).get("Period")
        if isinstance(q.get("MetricStat"), dict)
        else q.get("Period")
    )
    return p if isinstance(p, int) and p > 0 else fallback


# ------------------------------------------------------------------- the sweep
def alarm_metric_sweep(
    call_op: CallFn,
    alarm_name: str | None,
    *,
    start_time: str | None = None,
    end_time: str | None = None,
    period_s: int | None = None,
    stat: str | None = None,
    pin_dimensions: list[str] | None = None,
    fan_out: bool = False,
    fuzzy: bool = False,
    include_sibling_metrics: bool = True,
    include_datapoints: bool = True,
    max_series: int = 200,
    max_pages: int = 20,
    max_datapoints: int = _MAX_POINTS,
    max_total_datapoints: int = _DEFAULT_MAX_TOTAL_DATAPOINTS,
    clock: Callable[[], float] | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """Sweep a CloudWatch alarm: definition, state history, every matching series.

    ``call_op(operation, params)`` is the shared read-only call bridge. Returns a
    result dict (see :mod:`...compositereadonly.helpers`); never raises. ``is_exhaustive``
    is False whenever a page cap, series/datapoint cap, or failed sub-call left
    the sweep partial.
    """
    clock = time.time if clock is None else clock
    # Outer never-raise boundary (mirrors run_athena_query / run_insights_query /
    # diagnose_ecs_service): the sweep makes many bounded sub-calls over botocore
    # responses whose exact shape it cannot guarantee. Any unexpected exception
    # is converted into an errors-as-data SERVICE_ERROR result so the documented
    # "never raises" contract holds instead of a traceback escaping to the caller.
    try:
        return _run_sweep(
            call_op,
            alarm_name,
            start_time=start_time,
            end_time=end_time,
            period_s=period_s,
            stat=stat,
            pin_dimensions=pin_dimensions,
            fan_out=fan_out,
            fuzzy=fuzzy,
            include_sibling_metrics=include_sibling_metrics,
            include_datapoints=include_datapoints,
            max_series=max_series,
            max_pages=max_pages,
            max_datapoints=max_datapoints,
            max_total_datapoints=max_total_datapoints,
            clock=clock,
            region=region,
        )
    except Exception as exc:  # noqa: BLE001 - contract: never raise
        return err_result(
            SERVICE_ERROR,
            f"alarm-metric-sweep internal error: {exc!r}",
            guidance=[
                "Unexpected response shape; retry once, then fall back to "
                "cloudwatch:DescribeAlarms / get-metric-data by hand."
            ],
        )


def _run_sweep(
    call_op: CallFn,
    alarm_name: str | None,
    *,
    start_time: str | None = None,
    end_time: str | None = None,
    period_s: int | None = None,
    stat: str | None = None,
    pin_dimensions: list[str] | None = None,
    fan_out: bool = False,
    fuzzy: bool = False,
    include_sibling_metrics: bool = True,
    include_datapoints: bool = True,
    max_series: int = 200,
    max_pages: int = 20,
    max_datapoints: int = _MAX_POINTS,
    max_total_datapoints: int = _DEFAULT_MAX_TOTAL_DATAPOINTS,
    clock: Callable[[], float] = time.time,
    region: str | None = None,
) -> dict[str, Any]:
    """Run the sweep body; wrapped by :func:`alarm_metric_sweep`'s never-raise boundary."""
    problems = _validate(
        alarm_name,
        stat,
        pin_dimensions,
        max_series,
        max_pages,
        max_datapoints,
        max_total_datapoints,
    )
    problems += _validate_window_inputs(start_time, end_time, period_s)
    if problems:
        # Pre-dispatch bad input -> ParamValidationError (exit code 252).
        return invalid_input("; ".join(problems), guidance=list(problems))

    # 1. Resolve the alarm. Exact match is required by default; --fuzzy opts
    #    back into the bounded prefix/fuzzy fallback.
    resolved = resolve_alarm(call_op, alarm_name.strip(), fuzzy=fuzzy)
    if not resolved["ok"]:
        # NOT_FOUND / ambiguous / permission errors are returned verbatim.
        return resolved
    rv = resolved["value"]
    alarm = rv["alarm"]
    loaded = _load_from_alarm(
        alarm,
        rv["kind"],
        rv["match"],
        rv.get("guidance") or [],
        alarm_name.strip(),
    )

    # Detect alarm types this command cannot replay (PromQL / Log / Metrics
    # Insights): a metric alarm that carries a Metrics list from which no
    # standard MetricStat target could be extracted.
    if (
        rv["kind"] == "metric_alarm"
        and alarm.get("Metrics")
        and not alarm.get("MetricName")
        and not loaded["metrics"]
    ):
        has_expr = any(
            isinstance(m, dict) and m.get("Expression")
            for m in alarm.get("Metrics") or []
        )
        detected = (
            "metric-math or PromQL (an Expression with no resolvable MetricStat)"
            if has_expr
            else "Log or Metrics Insights (a Metrics entry with no MetricStat)"
        )
        return err_result(
            "UNSUPPORTED_ALARM_TYPE",
            f"Alarm {loaded['target']['alarm_name']!r} looks like a {detected} "
            "alarm; alarm-metric-sweep supports standard metric and metric-math "
            "alarms only in this version.",
            value={
                "target": loaded["target"],
                "detected_type": detected,
                "raw_metrics": _js(alarm.get("Metrics")),
            },
            guidance=[
                "Inspect the raw metric configuration with 'aws cloudwatch "
                "describe-alarms --alarm-names "
                f"{loaded['target']['alarm_name']}'.",
                "Query the underlying data directly (get-metric-data for "
                "metric-math, or the owning service for PromQL/Log alarms).",
            ],
            key=loaded["target"].get("alarm_arn"),
        )

    # Resolve the time window, anchoring its end to the alarm's state change and
    # its default period to the alarm's own Period (ITEM 1).
    anchor_end, eval_span, period_resolved = _anchor(alarm, period_s)
    w = _window(
        start_time,
        end_time,
        period_resolved,
        float(clock()),
        anchor_end=anchor_end,
        eval_span=eval_span,
    )
    if isinstance(w, list):
        return invalid_input("; ".join(w), guidance=list(w))
    guidance = [*w["clamped"], *w["notes"], *loaded["notes"]]
    originals: list[dict[str, Any]] = loaded["originals"]
    for q in originals:
        holder = (
            q["MetricStat"] if isinstance(q.get("MetricStat"), dict) else q
        )
        if (
            isinstance(holder.get("Period"), int)
            and holder["Period"] < w["min_period_s"]
        ):
            guidance.append(
                f"Query {q['Id']} period raised from {holder['Period']}s to "
                f"{w['min_period_s']}s (retention)."
            )
            holder["Period"] = w["min_period_s"]

    # 2. State history (bounded paging).
    history, warnings = _history(call_op, loaded["history"], w, max_pages)

    # 3. Enumerate sibling series; sweep metric siblings only for error-rate targets.
    texts = [
        loaded["target"]["alarm_name"],
        *(t["metric_name"] for t in loaded["metrics"]),
        *(str(q.get("Expression") or "") for q in originals),
    ]
    error_rate = any(_ERR_RE.search(t) for t in texts if t)
    if fan_out:
        # Opt-in fan-out: wildcard unpinned dimensions and sweep siblings.
        enum = _enumerate(
            call_op,
            loaded["metrics"],
            stat,
            set(pin_dimensions or []),
            include_sibling_metrics and error_rate,
            max_series,
            max_pages,
        )
    else:
        # Default: every dimension stays pinned to the alarm's own values, so
        # there is no ListMetrics fan-out and --pin-dimensions is irrelevant.
        enum = _target_only_series(loaded["metrics"], stat, max_series)
    warnings += enum["warnings"]
    guidance += enum["guidance"]

    # 4. Fetch metric data for the replay queries and the enumerated series.
    period, s_ep, e_ep = w["period_s"], w["start_epoch"], w["end_epoch"]
    errors: list[dict[str, Any]] = []
    complete, attempted = True, 0
    orig_res: dict[tuple[str, str], dict[str, Any]] = {}
    if originals:
        attempted += 1
        orig_res, done, err = _fetch(call_op, originals, w, max_pages)
        complete &= done
        if err is not None:
            errors.append(err)
            warnings.append(
                f"GetMetricData for the original queries failed "
                f"({err['code']}: {err['error']})."
            )
    specs = enum["series"]
    queries = [
        {
            "Id": f"zs{i}",
            "Label": s["label"],
            "ReturnData": True,
            "MetricStat": {
                "Metric": {
                    "Namespace": s["namespace"],
                    "MetricName": s["metric_name"],
                    "Dimensions": s["dimensions"],
                },
                "Period": period,
                "Stat": s["stat"],
                **({"Unit": s["unit"]} if s["unit"] else {}),
            },
            # Replay against the series' source account when one was captured
            # from the alarm (monitoring-account alarms).
            **({"AccountId": s["account_id"]} if s.get("account_id") else {}),
        }
        for i, s in enumerate(specs)
    ]
    # Batch so no single GetMetricData call exceeds the per-call point budget.
    batch = max(
        1,
        min(
            _MAX_QUERIES,
            _MAX_POINTS_PER_CALL // max(1, w["expected_points_per_series"]),
        ),
    )
    series_res: dict[str, dict[str, Any]] = {}
    for b in range(0, len(queries), batch):
        attempted += 1
        res, done, err = _fetch(call_op, queries[b : b + batch], w, max_pages)
        complete &= done
        for (rid, _), entry in res.items():
            series_res.setdefault(rid, entry)
        if err is not None:
            errors.append(err)
            warnings.append(
                f"GetMetricData batch {b // batch + 1} failed "
                f"({err['code']}: {err['error']})."
            )
    if not complete:
        guidance.append(
            f"GetMetricData pagination stopped at max_pages={max_pages}; later "
            "datapoints are missing. Raise --max-pages or narrow the window."
        )

    empty = {
        "timestamps": [],
        "values": [],
        "status": "NoResult",
        "messages": [],
    }
    fallback = next(
        (_qperiod(q, period) for q in originals if "MetricStat" in q), period
    )
    original_out = []
    for q in originals:
        matches = [
            r for (rid, _), r in orig_res.items() if rid == q["Id"]
        ] or [{**empty, "label": q["Id"]}]
        for r in matches:
            original_out.append(
                {
                    "id": q["Id"],
                    "label": r["label"],
                    "query": _js(q),
                    "status_code": r["status"],
                    "role": "expression"
                    if "Expression" in q
                    else "original_metric",
                    "messages": r["messages"],
                    **_timeline(
                        r["timestamps"],
                        r["values"],
                        _qperiod(q, fallback),
                        s_ep,
                        e_ep,
                        include_datapoints,
                        max_datapoints,
                    ),
                }
            )

    # Global emitted-datapoint budget across the enumerated series (the fan-out
    # that can overflow). 0 disables. Originals are O(1) and exempt.
    remaining = max_total_datapoints if max_total_datapoints > 0 else None
    output_capped = False
    series_out = []
    for i, s in enumerate(specs):
        r = series_res.get(f"zs{i}", empty)
        tl = _timeline(
            r["timestamps"],
            r["values"],
            period,
            s_ep,
            e_ep,
            include_datapoints,
            max_datapoints,
        )
        if include_datapoints and "datapoints" in tl and remaining is not None:
            n = len(tl["datapoints"])
            if n > remaining:
                # Budget spent: keep the most recent datapoints that still fit
                # (the tail, where the state change is) and drop the older ones;
                # once nothing fits, later arrays are dropped entirely.
                if remaining > 0:
                    tl["datapoints"] = tl["datapoints"][-remaining:]
                else:
                    del tl["datapoints"]
                tl["datapoints_truncated"] = True
                output_capped = True
                remaining = 0
            else:
                remaining -= n
        series_out.append(
            {
                "id": f"zs{i}",
                **s,
                "status_code": r["status"],
                "messages": r["messages"],
                **tl,
            }
        )

    any_truncated = any(
        x.get("datapoints_truncated") for x in original_out + series_out
    )
    if any_truncated and not output_capped:
        guidance.append(
            f"Per-series datapoints truncated to max_datapoints={max_datapoints}; "
            "raise --max-datapoints or narrow the window for the full series."
        )
    if output_capped:
        guidance.append(
            f"Total emitted datapoints reached max_total_datapoints="
            f"{max_total_datapoints}; later series return summary stats only. "
            "Raise --max-total-datapoints or narrow the sweep."
        )

    with_data = [s for s in series_out if s["datapoint_count"]]
    not_complete = [
        s["id"]
        for s in original_out + series_out
        if s["status_code"] != "Complete"
    ]
    if not_complete:
        warnings.append(f"Series without a Complete status: {not_complete}.")
    summary = {
        "series_count": len(series_out),
        "series_with_data": len(with_data),
        "series_without_data": [
            s["label"] for s in series_out if not s["datapoint_count"]
        ],
        "series_with_gaps": sum(bool(s["missing_count"]) for s in series_out),
        "series_stopped_reporting": [
            {
                "id": s["id"],
                "label": s["label"],
                "last_datapoint": s["last_datapoint"],
                "trailing_missing_count": s["trailing_missing_count"],
            }
            for s in with_data
            if s["trailing_missing_count"]
        ],
        "total_datapoints": sum(s["datapoint_count"] for s in series_out),
        "top_by_peak": [
            {
                "id": s["id"],
                "label": s["label"],
                "peak_value": s["max"],
                "peak_timestamp": s["peak_timestamp"],
            }
            for s in sorted(with_data, key=lambda s: s["max"], reverse=True)[
                :10
            ]
        ],
        "state_transitions": history["count"],
        "error_rate_target": error_rate,
        "output_capped": output_capped,
    }
    value = {
        "target": loaded["target"],
        "region": region,
        "window": {k: v for k, v in w.items() if k != "notes"},
        "state_history": history,
        "original_queries": original_out,
        "series": series_out,
        "summary": summary,
        "enumeration": enum["report"],
        "warnings": warnings,
    }
    # If every GetMetricData batch failed, this is an operational error (the
    # partial value is still attached so the caller can inspect what was gathered).
    if attempted and len(errors) == attempted:
        first = errors[0]
        return err_result(
            first.get("code") or SERVICE_ERROR,
            f"GetMetricData failed for every batch: {first.get('error')}",
            value=value,
            aws_code=first.get("aws_code"),
            retriable=bool(first.get("retriable")),
            guidance=[*guidance, *warnings],
            is_exhaustive=False,
            key=loaded["target"].get("alarm_arn"),
        )
    exhaustive = (
        enum["complete"]
        and history["is_exhaustive"]
        and complete
        and not errors
        and not not_complete
        and not any_truncated
        and not output_capped
    )
    return ok_result(
        value,
        is_exhaustive=exhaustive,
        guidance=guidance + warnings,
        key=loaded["target"].get("alarm_arn"),
    )


# ------------------------------------------------------------- CLI plumbing
def register(event_handlers):
    """Inject the ``alarm-metric-sweep`` verb into the cloudwatch command table."""
    event_handlers.register(
        "building-command-table.cloudwatch", _inject_commands
    )


def _inject_commands(command_table, session, **kwargs):
    command_table["alarm-metric-sweep"] = AlarmMetricSweepCommand(session)


class AlarmMetricSweepCommand(BasicCommand):
    NAME = "alarm-metric-sweep"
    # User-agent attribution for this customization's calls (mirrors ecs-deploy).
    USER_AGENT_EXTRA = "md/customization#alarm-metric-sweep"
    DESCRIPTION = (
        "Investigate a CloudWatch alarm in one read-only call: resolve it by "
        "exact name, read its state history, pull per-series timelines for the "
        "alarm's own metric(s), and report gaps, peaks and trailing-gap "
        "detection.\n\n"
        "By default the time window is anchored to the alarm's own "
        "configuration: it ends at the alarm's StateUpdatedTimestamp (or now for "
        "INSUFFICIENT_DATA), spans 3x the alarm's evaluation window "
        "(Period * EvaluationPeriods), and uses the alarm's own Period. Pass "
        "--start-time / --end-time / --period-s to override.\n\n"
        "By default every dimension is pinned to the alarm's own values, so the "
        "sweep returns exactly the alarm's series and issues no ListMetrics "
        "fan-out. Pass --fan-out to wildcard unpinned dimensions and enumerate "
        "sibling series (plus error-rate sibling metrics); --pin-dimensions then "
        "keeps named dimensions at the alarm's value.\n\n"
        "Resolution requires an exact alarm name; a miss returns NOT_FOUND with "
        "candidate names. Pass --fuzzy to allow the prefix/fuzzy fallback.\n\n"
        "Output is capped (series, per-series datapoints, and a global datapoint "
        "budget) so a wide sweep cannot overflow; per-series datapoints keep the "
        "most recent points. Strictly read-only: only Describe/Get/List calls "
        "are ever issued."
    )
    EXAMPLES = (
        "To sweep an alarm over the last 3 hours::\n\n"
        "  aws cloudwatch alarm-metric-sweep --alarm-name my-5xx-alarm\n\n"
        "To pin a dimension and bound output over an explicit window::\n\n"
        "  aws cloudwatch alarm-metric-sweep --alarm-name my-5xx-alarm "
        "--start-time 2024-01-15T18:00:00Z --end-time 2024-01-15T21:00:00Z "
        "--pin-dimensions LoadBalancer --max-series 50 --max-datapoints 500\n"
    )
    ARG_TABLE = [
        {
            "name": "alarm-name",
            "required": True,
            "cli_type_name": "string",
            "help_text": "Exact alarm name (or a unique prefix) to investigate.",
        },
        {
            "name": "start-time",
            "cli_type_name": "string",
            "help_text": (
                "Window start (ISO-8601). Default: end-time minus 3x the "
                "alarm's Period * EvaluationPeriods."
            ),
        },
        {
            "name": "end-time",
            "cli_type_name": "string",
            "help_text": (
                "Window end (ISO-8601). Default: the alarm's "
                "StateUpdatedTimestamp, or now for INSUFFICIENT_DATA."
            ),
        },
        {
            "name": "period-s",
            "cli_type_name": "integer",
            "help_text": (
                "Requested period in seconds. Default: the alarm's own Period "
                "(raised for retention / point budget)."
            ),
        },
        {
            "name": "stat",
            "cli_type_name": "string",
            "help_text": "Override the statistic (Sum, Average, Maximum, p99, ...).",
        },
        {
            "name": "pin-dimensions",
            "nargs": "+",
            "cli_type_name": "string",
            "help_text": (
                "With --fan-out, dimension names to pin to the alarm's value "
                "while enumerating siblings. Ignored without --fan-out (every "
                "dimension is already pinned)."
            ),
        },
        {
            "name": "fan-out",
            "action": "store_true",
            "default": False,
            "help_text": (
                "Wildcard unpinned dimensions and enumerate sibling series via "
                "ListMetrics. Off by default (only the alarm's own series)."
            ),
        },
        {
            "name": "fuzzy",
            "action": "store_true",
            "default": False,
            "help_text": (
                "Allow prefix/fuzzy alarm-name resolution. Off by default "
                "(exact name required)."
            ),
        },
        {
            "name": "no-sibling-metrics",
            "action": "store_true",
            "default": False,
            "help_text": "Do not sweep error-rate sibling metrics (status-code/success).",
        },
        {
            "name": "no-datapoints",
            "action": "store_true",
            "default": False,
            "help_text": "Return summary stats only; omit raw per-series datapoint arrays.",
        },
        {
            "name": "max-series",
            "default": 200,
            "cli_type_name": "integer",
            "help_text": "Maximum number of series to return (default 200).",
        },
        {
            "name": "max-pages",
            "default": 20,
            "cli_type_name": "integer",
            "help_text": "Maximum NextToken pages per paginated read (default 20).",
        },
        {
            "name": "max-datapoints",
            "default": _MAX_POINTS,
            "cli_type_name": "integer",
            "help_text": "Maximum datapoints per series (default 1440; 0 disables).",
        },
        {
            "name": "max-total-datapoints",
            "default": _DEFAULT_MAX_TOTAL_DATAPOINTS,
            "cli_type_name": "integer",
            "help_text": "Global emitted-datapoint budget across series (default 50000; 0 disables).",
        },
    ]

    def __init__(
        self, session, client=None, stdout=None, stderr=None, clock=None
    ):
        super().__init__(session)
        self._client = client
        self._stdout = stdout
        self._stderr = stderr
        self._clock = clock

    def _run_main(self, parsed_args, parsed_globals):
        client = self._client or create_read_client(
            self._session, "cloudwatch", parsed_globals
        )
        # Best-effort call attribution. The shared read client doesn't accept a
        # user_agent_extra, so append the marker to the client's config after
        # creation; attribution must never break the command.
        try:
            cfg = client.meta.config
            existing = getattr(cfg, "user_agent_extra", "") or ""
            if self.USER_AGENT_EXTRA not in existing:
                cfg.user_agent_extra = (
                    f"{existing} {self.USER_AGENT_EXTRA}".strip()
                )
        except Exception:  # noqa: BLE001 - attribution must never be fatal
            pass

        def call_op(operation, params):
            return call(client, operation, params)

        result = alarm_metric_sweep(
            call_op,
            parsed_args.alarm_name,
            start_time=parsed_args.start_time,
            end_time=parsed_args.end_time,
            period_s=parsed_args.period_s,
            stat=parsed_args.stat,
            pin_dimensions=parsed_args.pin_dimensions,
            fan_out=parsed_args.fan_out,
            fuzzy=parsed_args.fuzzy,
            include_sibling_metrics=not parsed_args.no_sibling_metrics,
            include_datapoints=not parsed_args.no_datapoints,
            max_series=parsed_args.max_series,
            max_pages=parsed_args.max_pages,
            max_datapoints=parsed_args.max_datapoints,
            max_total_datapoints=parsed_args.max_total_datapoints,
            region=getattr(parsed_globals, "region", None),
            clock=self._clock,
        )
        return emit_result(
            self.NAME,
            result,
            parsed_globals,
            self._session,
            self._stdout,
            self._stderr,
        )
