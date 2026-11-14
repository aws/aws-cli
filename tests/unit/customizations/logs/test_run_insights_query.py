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
"""Unit tests for ``aws logs run-insights-query`` (run_insights_query logic).

Discovery uses ``ListLogGroups`` (server-side ``logGroupNamePattern`` match);
retention is then fetched with ``DescribeLogGroups(logGroupIdentifiers=[...])``.
So a straightforward resolution issues ``ListLogGroups`` followed by one
``DescribeLogGroups`` enrichment call before the StartQuery/GetQueryResults
lifecycle.
"""

from awscli.customizations.compositereadonly.helpers import (
    CONFLICT,
    CREDENTIALS_EXPIRED,
    NOT_FOUND,
    PERMISSION_DENIED,
    QUOTA_EXCEEDED,
    SERVICE_ERROR,
    THROTTLED,
    TIMEOUT,
    VALIDATION_ERROR,
    assert_read_only,
    err_result,
    ok_result,
)
from awscli.customizations.logs import run_insights_query as mod

NOW = "2026-10-28T12:00:00Z"


class ScriptedLogs:
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

    def params_for(self, operation):
        return [p for op, p in self.calls if op == operation]


def _arn(name, account="123456789012", region="us-east-1"):
    return f"arn:aws:logs:{region}:{account}:log-group:{name}"


def _group(name, creation_ms=0, retention=None):
    """A DescribeLogGroups enrichment entry: carries arn and retentionInDays."""
    g = {
        "logGroupName": name,
        "creationTime": creation_ms,
        "arn": _arn(name) + ":*",
    }
    if retention:
        g["retentionInDays"] = retention
    return g


def _llg(*names, next_token=None):
    """ListLogGroups discovery response (name + logGroupArn, no retention)."""
    body = {
        "logGroups": [
            {"logGroupName": n, "logGroupArn": _arn(n)} for n in names
        ]
    }
    if next_token:
        body["nextToken"] = next_token
    return ok_result(body)


def _dlg(*groups, next_token=None):
    """DescribeLogGroups enrichment response built from _group(...) dicts."""
    body = {"logGroups": list(groups)}
    if next_token:
        body["nextToken"] = next_token
    return ok_result(body)


def _discover(call, *groups):
    """Queue ListLogGroups discovery + DescribeLogGroups enrichment for the
    common case where both return the same set of groups. Each arg is a
    ``_group(...)`` dict (its retention is returned by the enrichment call)."""
    names = [g["logGroupName"] for g in groups]
    call.queue("ListLogGroups", _llg(*names))
    call.queue("DescribeLogGroups", _dlg(*groups))


def _qr(status="Complete", rows=None, stats=None):
    results = [
        [{"field": k, "value": v} for k, v in row.items()]
        for row in (rows or [])
    ]
    return ok_result(
        {"status": status, "results": results, "statistics": stats or {}}
    )


def _qr_page(status="Complete", rows=None, stats=None, next_token=None):
    """A GetQueryResults response that can carry a ``nextToken`` for paging."""
    body = _qr(status=status, rows=rows, stats=stats)["value"]
    if next_token:
        body["nextToken"] = next_token
    return ok_result(body)


def _run(
    call,
    groups="/aws/lambda/fn",
    query="fields @timestamp, @message",
    start="2026-10-28T10:00:00Z",
    end="2026-10-28T11:00:00Z",
    **kwargs,
):
    return mod.run_insights_query(
        call,
        groups,
        query,
        start,
        end,
        now=NOW,
        sleep=lambda _s: None,
        clock=_clock(),
        **kwargs,
    )


def _clock():
    state = {"t": 0.0}

    def clock():
        state["t"] += 0.001
        return state["t"]

    return clock


# --------------------------------------------------------------- happy path / read-only


def test_success_only_read_ops():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue(
        "GetQueryResults", _qr(rows=[{"@message": "hello", "@ptr": "p1"}])
    )
    result = _run(call)
    assert result["ok"] is True
    assert result["value"]["row_count"] == 1
    assert result["value"]["rows"][0]["@message"] == "hello"
    # Read-only lifecycle only: discover, enrich retention, start, poll.
    assert call.ops() == [
        "ListLogGroups",
        "DescribeLogGroups",
        "StartQuery",
        "GetQueryResults",
    ]


def test_success_sends_log_group_names_not_identifiers():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call)
    assert result["ok"] is True
    start = call.params_for("StartQuery")[0]
    # Plain names go through logGroupNames (no ARN present).
    assert start["logGroupNames"] == ["/aws/lambda/fn"]
    assert "logGroupIdentifiers" not in start


def test_empty_results():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[]))
    result = _run(call)
    assert result["ok"] is True
    assert result["value"]["row_count"] == 0


def test_polls_until_terminal():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(status="Running"))
    call.queue("GetQueryResults", _qr(status="Scheduled"))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call)
    assert result["ok"] is True
    assert call.ops().count("GetQueryResults") == 3


# --- creation time must NOT clamp the query window


def test_creation_time_does_not_clamp_window():
    # Group was recorded (creationTime) AFTER start_time, but with no retention
    # its data is still queryable from start_time. The window must NOT be clamped
    # up to creationTime.
    call = ScriptedLogs()
    creation = _ms("2026-10-28T10:30:00Z")  # after the 10:00 start
    _discover(call, _group("/aws/lambda/fn", creation_ms=creation))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call)
    assert result["ok"] is True
    # Window start stays at the requested 10:00, not clamped to 10:30 creation.
    assert result["value"]["window"]["start"] == "2026-10-28T10:00:00Z"
    assert not any(
        "creation" in r.lower() for r in result["value"]["clamp_reasons"]
    )


# --- retention period clamps the query window (retention comes from enrichment)


def test_retention_clamps_start():
    # start far in the past; a 1-day retention edge is after it, so the window
    # start is clamped UP to the retention edge (this clamp is kept).
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn", retention=1))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = mod.run_insights_query(
        call,
        "/aws/lambda/fn",
        "fields @message",
        "2026-10-01T00:00:00Z",
        "2026-10-28T11:00:00Z",
        now=NOW,
        sleep=lambda _s: None,
        clock=_clock(),
    )
    assert result["ok"] is True
    assert result["value"]["clamped"] is True
    assert any("retention edge" in r for r in result["value"]["clamp_reasons"])
    # Clamped to now - 1 day = 2026-10-27T12:00:00Z.
    assert result["value"]["window"]["start"] == "2026-10-27T12:00:00Z"


def test_group_skipped_when_window_before_retention_edge():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn", retention=1))
    # Window entirely before the 1-day retention edge (now-1day = 10-27T12:00).
    result = mod.run_insights_query(
        call,
        "/aws/lambda/fn",
        "fields @message",
        "2026-10-20T00:00:00Z",
        "2026-10-21T00:00:00Z",
        now=NOW,
        sleep=lambda _s: None,
        clock=_clock(),
    )
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"
    # Retention was fetched (DescribeLogGroups) but nothing was queried.
    assert "DescribeLogGroups" in call.ops()
    assert "StartQuery" not in call.ops()


# --- default max_rows caps at ~50 rows


def test_default_max_rows_is_50():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    many = [{"@ptr": f"p{i}", "@message": f"m{i}"} for i in range(60)]
    call.queue("GetQueryResults", _qr(rows=many, stats={"recordsMatched": 60}))
    result = _run(call)
    assert result["value"]["row_count"] == 50
    assert result["is_exhaustive"] is False
    assert any("max_rows=50" in r for r in result["value"]["partial_reasons"])


# --- @message field is truncated at limit


def test_message_is_truncated_and_recorded():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    long_msg = "x" * 500
    call.queue(
        "GetQueryResults", _qr(rows=[{"@message": long_msg, "@ptr": "p1"}])
    )
    result = _run(call, max_message_length=20)
    msg = result["value"]["rows"][0]["@message"]
    assert len(msg) <= 20
    assert msg.endswith("...[truncated]")
    assert result["value"]["message_truncated_count"] == 1
    assert any("@message" in r for r in result["value"]["clamp_reasons"])


# --------------------------------------------------------------- resolution


def test_prefix_resolution_when_no_exact_match():
    call = ScriptedLogs()
    # Discovery returns two groups under the prefix; no exact '/aws/lambda/fn'.
    call.queue("ListLogGroups", _llg("/aws/lambda/fn-a", "/aws/lambda/fn-b"))
    call.queue(
        "DescribeLogGroups",
        _dlg(_group("/aws/lambda/fn-a"), _group("/aws/lambda/fn-b")),
    )
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call, groups="/aws/lambda/fn")
    assert result["ok"] is True
    res = result["value"]["log_group_resolution"][0]
    assert res["match"] == "prefix"
    assert len(res["log_groups"]) == 2


def test_no_groups_matched_is_not_found():
    call = ScriptedLogs()
    call.queue("ListLogGroups", _llg())  # prefix (^) miss
    call.queue("ListLogGroups", _llg())  # substring fallback miss
    result = _run(call, groups="nonexistent")
    assert result["ok"] is False
    assert result["code"] == "NOT_FOUND"
    # Nothing matched, so no enrichment and no query.
    assert "DescribeLogGroups" not in call.ops()
    assert "StartQuery" not in call.ops()


# --------------------------------------------------------------- validation / malformed


def test_unknown_command_is_advisory_not_fatal():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call, query="boguscmd @message")
    # An unrecognized leading token no longer blocks the query locally; it runs
    # and the server would reject it if it were truly invalid.
    assert result["ok"] is True
    assert "StartQuery" in call.ops()
    assert any("not recognized by this tool" in g for g in result["guidance"])


def test_empty_query_rejected():
    call = ScriptedLogs()
    result = _run(call, query="   ")
    assert result["ok"] is False
    assert result["param_error"] is True
    assert call.calls == []


def test_malformed_query_from_server_is_operational_error():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue(
        "StartQuery",
        err_result(
            "INVALID_INPUT",
            "line 1, position 5: bad",
            aws_code="MalformedQueryException",
        ),
    )
    result = _run(call)
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"
    # Server-discovered: NOT flagged as a pre-dispatch param error.
    assert result.get("param_error") is not True


def test_blank_query_id_refuses_to_poll():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "  "}))
    result = _run(call)
    assert result["ok"] is False
    assert result["code"] == "SERVICE_ERROR"
    assert "GetQueryResults" not in call.ops()


# --------------------------------------------------------------- SOURCE command path


def test_source_query_skips_resolution():
    call = ScriptedLogs()
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(
        call,
        groups=None,
        query="SOURCE logGroups(namePrefix: ['/aws/lambda']) | fields @message",
    )
    assert result["ok"] is True
    # No resolution: StartQuery is the first call.
    assert "ListLogGroups" not in call.ops()
    assert "DescribeLogGroups" not in call.ops()
    start = call.params_for("StartQuery")[0]
    assert "logGroupNames" not in start
    assert "logGroupIdentifiers" not in start
    assert any("SOURCE command" in g for g in result["guidance"])


def test_source_query_is_case_insensitive_and_ignores_comments():
    call = ScriptedLogs()
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(
        call,
        groups=None,
        query="# pick groups\nsource logGroups(namePrefix: ['/svc']) | stats count()",
    )
    assert result["ok"] is True
    assert "ListLogGroups" not in call.ops()


def test_source_and_log_group_names_conflict_rejected():
    call = ScriptedLogs()
    result = _run(
        call,
        groups="/aws/lambda/fn",
        query="SOURCE logGroups(namePrefix: ['/x']) | fields @message",
    )
    assert result["ok"] is False
    assert result["param_error"] is True
    assert call.calls == []
    assert any("one or the" in g for g in result["guidance"])


def test_no_source_and_no_log_groups_rejected():
    call = ScriptedLogs()
    result = _run(call, groups=None, query="fields @message")
    assert result["ok"] is False
    assert result["param_error"] is True
    assert call.calls == []
    assert any("No log groups given" in g for g in result["guidance"])


def test_source_query_still_clamps_future_end():
    call = ScriptedLogs()
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = mod.run_insights_query(
        call,
        None,
        "SOURCE logGroups(namePrefix: ['/svc']) | fields @message",
        "2026-10-28T11:00:00Z",
        "2026-10-28T13:00:00Z",
        now=NOW,
        sleep=lambda _s: None,
        clock=_clock(),
    )
    assert result["ok"] is True
    assert result["value"]["window"]["end"] == "2026-10-28T12:00:00Z"
    assert result["value"]["log_groups"] == []


# --------------------------------------------------------------- splitting (row cap)


def test_row_capped_window_splits(monkeypatch):
    # Shrink the per-query row cap so a small fixture triggers a split.
    monkeypatch.setattr(mod, "_ROW_CAP", 2)
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    # First segment hits the cap (2 rows, more matched) -> split into two halves.
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "a"}, {"@ptr": "b"}], stats={"recordsMatched": 10}),
    )
    # Two sub-windows, each returns a small, non-capped result.
    call.queue("StartQuery", ok_result({"queryId": "q2"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "c"}], stats={"recordsMatched": 1}),
    )
    call.queue("StartQuery", ok_result({"queryId": "q3"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "d"}], stats={"recordsMatched": 1}),
    )
    result = _run(call, query="fields @message")
    assert result["ok"] is True
    assert result["value"]["split_count"] >= 1
    # @ptr de-duplication across merged sub-windows.
    ptrs = [r["@ptr"] for r in result["value"]["rows"]]
    assert len(ptrs) == len(set(ptrs))


def _ms(iso):
    from datetime import datetime, timezone

    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _run_window(call, start, end, **kwargs):
    kwargs.setdefault("groups", "/aws/lambda/fn")
    kwargs.setdefault("query", "fields @timestamp, @message")
    return mod.run_insights_query(
        call,
        kwargs.pop("groups"),
        kwargs.pop("query"),
        start,
        end,
        now=NOW,
        sleep=lambda _s: None,
        clock=_clock(),
        **kwargs,
    )


# --------------------------------------------------------------- input validation


def test_accepts_datetime_objects_for_times():
    from datetime import datetime, timezone

    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    start = datetime(2026, 10, 28, 10, tzinfo=timezone.utc)
    end = datetime(2026, 10, 28, 11, tzinfo=timezone.utc)
    result = _run_window(call, start, end)
    assert result["ok"] is True


def test_naive_datetime_is_treated_as_utc():
    from datetime import datetime

    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    # No tzinfo -> assumed UTC; the query still runs.
    result = _run_window(
        call,
        datetime(2026, 10, 28, 10),
        datetime(2026, 10, 28, 11),
    )
    assert result["ok"] is True


def test_non_iso_start_time_rejected():
    call = ScriptedLogs()
    result = _run(call, start="not-a-time")
    assert result["ok"] is False
    assert result["param_error"] is True
    assert call.calls == []


def test_missing_start_time_rejected():
    call = ScriptedLogs()
    result = _run(call, start="")
    assert result["ok"] is False
    assert result["param_error"] is True


def test_start_not_before_end_rejected():
    call = ScriptedLogs()
    result = _run(
        call,
        start="2026-10-28T11:00:00Z",
        end="2026-10-28T10:00:00Z",
    )
    assert result["ok"] is False
    assert "before end_time" in result["error"]


def test_invalid_now_rejected():
    call = ScriptedLogs()
    result = mod.run_insights_query(
        call,
        "/aws/lambda/fn",
        "fields @message",
        "2026-10-28T10:00:00Z",
        "2026-10-28T11:00:00Z",
        now="garbage",
        sleep=lambda _s: None,
        clock=_clock(),
    )
    assert result["ok"] is False


def test_empty_group_list_rejected():
    call = ScriptedLogs()
    result = _run(call, groups=[])
    assert result["ok"] is False
    assert any("No log groups given" in p for p in result["guidance"])


def test_invalid_group_name_rejected():
    call = ScriptedLogs()
    result = _run(call, groups="has a space")
    assert result["ok"] is False
    assert result["param_error"] is True
    assert call.calls == []


def test_nonpositive_max_rows_rejected():
    call = ScriptedLogs()
    result = _run(call, max_rows=0)
    assert result["ok"] is False


def test_boolean_max_queries_rejected():
    call = ScriptedLogs()
    result = _run(call, max_queries=True)
    assert result["ok"] is False


def test_negative_max_splits_rejected():
    call = ScriptedLogs()
    result = _run(call, max_splits=-1)
    assert result["ok"] is False


def test_nonpositive_timeout_rejected():
    call = ScriptedLogs()
    result = _run(call, timeout_seconds=0)
    assert result["ok"] is False


def test_query_too_long_rejected():
    call = ScriptedLogs()
    result = _run(call, query="fields @message " + "x" * 11000)
    assert result["ok"] is False


# --------------------------------------------------------------- query analysis


def test_pipe_inside_regex_is_not_a_stage_separator():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    # The '|' lives inside the /ERROR|WARN/ regex, so there are two stages
    # (fields, filter), both valid -- not three.
    result = _run(
        call,
        query="fields @message | filter @message like /ERROR|WARN/",
    )
    assert result["ok"] is True


def test_pipe_inside_quotes_is_not_a_stage_separator():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(
        call,
        query="fields @message | filter @message = 'a|b'",
    )
    assert result["ok"] is True


def test_pipe_inside_parens_is_not_a_stage_separator():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(
        call,
        query="fields @message | stats count() by (a)",
    )
    assert result["ok"] is True


def test_parse_command_opens_a_regex_literal():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    # 'parse' opens a /.../ literal that itself contains a '|'.
    result = _run(
        call,
        query="fields @message | parse @message /a|b/ as x",
    )
    assert result["ok"] is True


def test_empty_pipeline_stage_is_advisory_not_fatal():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call, query="fields @message | | stats count()")
    # A stray '|' is no longer rejected locally; it is flagged as advisory.
    assert result["ok"] is True
    assert any("not recognized by this tool" in g for g in result["guidance"])


# --------------------------------------------------------------- group resolution


def test_arn_input_uses_log_group_identifiers():
    call = ScriptedLogs()
    arn = "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/fn:*"
    # An ARN skips name discovery; it is resolved and enriched via
    # DescribeLogGroups(logGroupIdentifiers) using the ':*'-stripped ARN.
    call.queue("DescribeLogGroups", _dlg(_group("/aws/lambda/fn")))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call, groups=arn)
    assert result["ok"] is True
    # No ListLogGroups: an ARN is not a name pattern.
    assert "ListLogGroups" not in call.ops()
    stripped = "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/fn"
    enrich = call.params_for("DescribeLogGroups")[0]
    assert enrich["logGroupIdentifiers"] == [stripped]
    start = call.params_for("StartQuery")[0]
    assert start["logGroupIdentifiers"] == [stripped]
    assert "logGroupNames" not in start


def test_cross_account_arn_passed_through_unchanged():
    call = ScriptedLogs()
    # A source-account ARN from a monitoring account: account/region differ from
    # the caller's. It must NOT be rewritten to a same-named local group.
    arn = "arn:aws:logs:us-west-2:444455556666:log-group:/aws/lambda/fn"
    call.queue(
        "DescribeLogGroups",
        ok_result(
            {
                "logGroups": [
                    {"logGroupName": "/aws/lambda/fn", "arn": arn + ":*"}
                ]
            }
        ),
    )
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call, groups=arn)
    assert result["ok"] is True
    start = call.params_for("StartQuery")[0]
    # Account, region and name preserved; ':*' stripped.
    assert start["logGroupIdentifiers"] == [arn]
    assert "logGroupNames" not in start


def test_mixed_names_and_arns_all_use_identifiers():
    call = ScriptedLogs()
    arn = "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/arn-fn"
    # One plain name (discovered) and one ARN (direct). The whole batch must go
    # through logGroupIdentifiers, with the plain name converted to its ARN.
    call.queue("ListLogGroups", _llg("/aws/lambda/name-fn"))
    call.queue(
        "DescribeLogGroups",
        _dlg(_group("/aws/lambda/name-fn"), _group("/aws/lambda/arn-fn")),
    )
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call, groups=["/aws/lambda/name-fn", arn])
    assert result["ok"] is True
    start = call.params_for("StartQuery")[0]
    assert "logGroupNames" not in start
    ids = start["logGroupIdentifiers"]
    assert _arn("/aws/lambda/name-fn") in ids
    assert arn in ids


def test_unresolved_arn_is_still_queried_directly():
    call = ScriptedLogs()
    arn = "arn:aws:logs:us-west-2:444455556666:log-group:/aws/lambda/fn"
    # Enrichment returns nothing for the ARN (e.g. no cross-account access), but
    # the explicit ARN is still queried directly with no retention bound.
    call.queue("DescribeLogGroups", ok_result({"logGroups": []}))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call, groups=arn)
    assert result["ok"] is True
    start = call.params_for("StartQuery")[0]
    assert start["logGroupIdentifiers"] == [arn]


def test_exact_match_with_siblings_adds_note():
    call = ScriptedLogs()
    call.queue("ListLogGroups", _llg("/aws/lambda/fn", "/aws/lambda/fn-2"))
    call.queue("DescribeLogGroups", _dlg(_group("/aws/lambda/fn")))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call, groups="/aws/lambda/fn")
    res = result["value"]["log_group_resolution"][0]
    assert res["match"] == "exact"
    # Only the exact group is queried, but a note flags the siblings.
    assert res["log_groups"] == ["/aws/lambda/fn"]
    assert any("share the prefix" in g for g in result["guidance"])


def test_explicit_prefix_star_matches_all():
    call = ScriptedLogs()
    call.queue("ListLogGroups", _llg("/aws/lambda/fn-a", "/aws/lambda/fn-b"))
    call.queue(
        "DescribeLogGroups",
        _dlg(_group("/aws/lambda/fn-a"), _group("/aws/lambda/fn-b")),
    )
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call, groups="/aws/lambda/fn*")
    res = result["value"]["log_group_resolution"][0]
    assert res["match"] == "prefix"
    assert len(res["log_groups"]) == 2


def test_substring_pattern_fallback():
    call = ScriptedLogs()
    call.queue("ListLogGroups", _llg())  # prefix (^) miss
    call.queue("ListLogGroups", _llg("/aws/lambda/my-fn", "/aws/ecs/my-fn"))
    call.queue(
        "DescribeLogGroups",
        _dlg(_group("/aws/lambda/my-fn"), _group("/aws/ecs/my-fn")),
    )
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call, groups="my-fn")
    res = result["value"]["log_group_resolution"][0]
    assert res["match"] == "pattern"
    assert any("containing it" in g for g in result["guidance"])


def test_substring_pattern_many_matches_elided():
    call = ScriptedLogs()
    call.queue("ListLogGroups", _llg())  # prefix (^) miss
    names = [f"/svc/fn-{i}" for i in range(7)]
    call.queue("ListLogGroups", _llg(*names))
    call.queue("DescribeLogGroups", _dlg(*[_group(n) for n in names]))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call, groups="fn")
    # More than 5 matches -> the note lists the first 5 and elides the rest.
    assert any("..." in g for g in result["guidance"])


def test_pattern_unsupported_is_treated_as_no_match():
    call = ScriptedLogs()
    call.queue("ListLogGroups", _llg())  # prefix (^) miss
    # logGroupNamePattern unsupported -> VALIDATION error is swallowed on the
    # substring fallback and the input resolves to no groups (NOT_FOUND).
    call.queue(
        "ListLogGroups",
        err_result(VALIDATION_ERROR, "pattern not supported"),
    )
    result = _run(call, groups="weird")
    assert result["ok"] is False
    assert result["code"] == NOT_FOUND


def test_list_prefix_error_propagates():
    call = ScriptedLogs()
    call.queue("ListLogGroups", err_result(PERMISSION_DENIED, "denied"))
    result = _run(call, groups="/aws/lambda/fn")
    assert result["ok"] is False
    assert result["code"] == PERMISSION_DENIED
    assert any("lacks logs:ListLogGroups" in g for g in result["guidance"])


def test_list_pattern_hard_error_propagates():
    call = ScriptedLogs()
    call.queue("ListLogGroups", _llg())  # prefix miss
    call.queue("ListLogGroups", err_result(PERMISSION_DENIED, "denied"))
    result = _run(call, groups="substr")
    assert result["ok"] is False
    assert result["code"] == PERMISSION_DENIED


def test_enrichment_error_propagates():
    call = ScriptedLogs()
    # Discovery succeeds but the DescribeLogGroups retention enrichment fails.
    call.queue("ListLogGroups", _llg("/aws/lambda/fn"))
    call.queue("DescribeLogGroups", err_result(PERMISSION_DENIED, "denied"))
    result = _run(call, groups="/aws/lambda/fn")
    assert result["ok"] is False
    assert result["code"] == PERMISSION_DENIED
    assert any("lacks logs:DescribeLogGroups" in g for g in result["guidance"])


def test_discovery_paging_is_followed():
    call = ScriptedLogs()
    call.queue("ListLogGroups", _llg("/aws/lambda/fn-a", next_token="t2"))
    call.queue("ListLogGroups", _llg("/aws/lambda/fn-b"))
    call.queue(
        "DescribeLogGroups",
        _dlg(_group("/aws/lambda/fn-a"), _group("/aws/lambda/fn-b")),
    )
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call, groups="/aws/lambda/fn*")
    assert sorted(result["value"]["log_groups"]) == [
        "/aws/lambda/fn-a",
        "/aws/lambda/fn-b",
    ]


def test_discovery_page_cap_reports_incomplete(monkeypatch):
    monkeypatch.setattr(mod, "_DESCRIBE_PAGE_CAP", 1)
    call = ScriptedLogs()
    # One page with a nextToken, but the cap stops listing -> incomplete.
    call.queue("ListLogGroups", _llg("/aws/lambda/fn", next_token="more"))
    call.queue("DescribeLogGroups", _dlg(_group("/aws/lambda/fn")))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call, groups="/aws/lambda/fn*")
    assert result["is_exhaustive"] is False
    assert any("page cap" in p for p in result["value"]["partial_reasons"])


# --------------------------------------------------------------- window clamping


def test_future_end_time_clamped_to_now():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run_window(call, "2026-10-28T11:00:00Z", "2026-10-28T13:00:00Z")
    assert result["value"]["clamped"] is True
    assert result["value"]["window"]["end"] == "2026-10-28T12:00:00Z"
    assert any("future" in r for r in result["value"]["clamp_reasons"])


def test_some_groups_skipped_others_queried():
    call = ScriptedLogs()
    call.queue("ListLogGroups", _llg("/aws/lambda/keep", "/aws/lambda/drop"))
    call.queue(
        "DescribeLogGroups",
        _dlg(
            _group("/aws/lambda/keep"),
            _group("/aws/lambda/drop", retention=1),
        ),
    )
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    # Window entirely before the 1-day retention edge for 'drop' but '0'
    # retention 'keep' is always queryable.
    result = mod.run_insights_query(
        call,
        "/aws/lambda/*",
        "fields @message",
        "2026-10-20T00:00:00Z",
        "2026-10-21T00:00:00Z",
        now=NOW,
        sleep=lambda _s: None,
        clock=_clock(),
    )
    assert result["ok"] is True
    skipped = [s["log_group"] for s in result["value"]["skipped_log_groups"]]
    assert "/aws/lambda/drop" in skipped
    assert result["value"]["log_groups"] == ["/aws/lambda/keep"]
    assert any("Skipped" in g for g in result["guidance"])


# --------------------------------------------------------------- segment lifecycle


def test_start_query_throttled_then_succeeds():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", err_result(THROTTLED, "slow"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call)
    assert result["ok"] is True
    assert call.ops().count("StartQuery") == 2


def test_start_query_throttled_beyond_retries():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    for _ in range(mod._START_RETRIES + 1):
        call.queue("StartQuery", err_result(THROTTLED, "slow"))
    result = _run(call)
    assert result["ok"] is False
    assert result["code"] == QUOTA_EXCEEDED
    assert result["retriable"] is True


def test_malformed_query_with_line_position_detail():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue(
        "StartQuery",
        err_result(
            SERVICE_ERROR,
            "line 1, position 8: unexpected token",
            aws_code="MalformedQueryException",
        ),
    )
    result = _run(call, query="fields @badtoken")
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"
    assert result["value"]["source"] == "server"
    assert result["value"]["position"] == 8


def test_malformed_query_with_compile_error_location():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue(
        "StartQuery",
        err_result(
            SERVICE_ERROR,
            "bad query",
            aws_code="MalformedQueryException",
            value={"queryCompileError": {"location": {"start": 7}}},
        ),
    )
    result = _run(call, query="fields @timestamp")
    assert result["value"]["position"] == 7
    # Offset 7 lands on '@timestamp', so that token is extracted.
    assert result["value"]["token"]


def test_malformed_query_position_only_detail():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue(
        "StartQuery",
        err_result(
            SERVICE_ERROR,
            "syntax error at position 3",
            aws_code="MalformedQueryException",
        ),
    )
    result = _run(call)
    assert result["value"]["position"] == 3


def test_invalid_parameter_from_start_query():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue(
        "StartQuery",
        err_result(
            SERVICE_ERROR,
            "bad window",
            aws_code="InvalidParameterException",
        ),
    )
    result = _run(call)
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"


def test_resource_not_found_from_start_query():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue(
        "StartQuery",
        err_result(
            NOT_FOUND,
            "group vanished",
            aws_code="ResourceNotFoundException",
        ),
    )
    result = _run(call)
    assert result["ok"] is False
    assert result["code"] == NOT_FOUND


def test_generic_start_query_error_propagates():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", err_result(PERMISSION_DENIED, "denied"))
    result = _run(call)
    assert result["ok"] is False
    assert result["code"] == PERMISSION_DENIED
    assert any("logs:StartQuery" in g for g in result["guidance"])


def test_get_query_results_throttled_then_completes():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", err_result(THROTTLED, "slow"))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call)
    assert result["ok"] is True
    assert call.ops().count("GetQueryResults") == 2


def test_get_query_results_error_propagates():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", err_result(PERMISSION_DENIED, "denied"))
    result = _run(call)
    assert result["ok"] is False
    assert result["code"] == PERMISSION_DENIED
    assert any("may still be running" in g for g in result["guidance"])


def test_credentials_expired_is_flagged_retriable():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue(
        "GetQueryResults",
        err_result(SERVICE_ERROR, "expired", aws_code="ExpiredTokenException"),
    )
    result = _run(call)
    assert result["code"] == CREDENTIALS_EXPIRED
    assert result["retriable"] is True


def test_poll_timeout_stops_query():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(status="Running"))
    call.queue("StopQuery", ok_result({}))
    # max_polls=1 forces the poller to exhaust after a single non-terminal poll.
    result = _run(call, max_polls=1)
    assert result["ok"] is False
    assert result["code"] == TIMEOUT
    assert "StopQuery" in call.ops()


def test_terminal_failed_status_is_service_error():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(status="Failed"))
    result = _run(call)
    assert result["ok"] is False
    assert result["code"] == SERVICE_ERROR


def test_terminal_timeout_status():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(status="Timeout"))
    result = _run(call)
    assert result["code"] == TIMEOUT
    assert result["retriable"] is True
    assert any("time out" in g for g in result["guidance"])


def test_terminal_cancelled_status_is_conflict():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(status="Cancelled"))
    result = _run(call)
    assert result["code"] == CONFLICT


def test_statistics_are_summed_and_floated():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue(
        "GetQueryResults",
        _qr(
            rows=[{"@ptr": "p1"}],
            stats={"recordsMatched": 5, "bytesScanned": 100},
        ),
    )
    result = _run(call)
    assert result["value"]["statistics"]["recordsMatched"] == 5.0
    assert result["value"]["statistics"]["bytesScanned"] == 100.0


# --------------------------------------------------------------- splitting / caps


def test_aggregate_query_capped_reports_without_splitting(monkeypatch):
    monkeypatch.setattr(mod, "_ROW_CAP", 2)
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue(
        "GetQueryResults",
        _qr(
            rows=[{"g": "a"}, {"g": "b"}],
            stats={"recordsMatched": 99},
        ),
    )
    result = _run(call, query="stats count() by g")
    assert result["value"]["is_aggregate"] is True
    assert result["value"]["split_count"] == 0
    assert any(
        "Aggregate query returned" in p
        for p in result["value"]["partial_reasons"]
    )


def test_max_splits_reached_reports_partial(monkeypatch):
    monkeypatch.setattr(mod, "_ROW_CAP", 2)
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "a"}, {"@ptr": "b"}], stats={"recordsMatched": 9}),
    )
    # max_splits=0 forbids splitting, so the cap is reported as partial.
    result = _run(call, query="fields @message", max_splits=0)
    assert result["ok"] is True
    assert result["is_exhaustive"] is False
    assert any(
        "max_splits=0 was reached" in p
        for p in result["value"]["partial_reasons"]
    )


def test_max_queries_reached_breaks_with_partial(monkeypatch):
    monkeypatch.setattr(mod, "_ROW_CAP", 2)
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "a"}, {"@ptr": "b"}], stats={"recordsMatched": 9}),
    )
    # The first segment caps and schedules a split, but max_queries=1 stops us
    # before the sub-windows run.
    result = _run(call, query="fields @message", max_queries=1)
    assert result["ok"] is True
    assert any(
        "max_queries=1" in p for p in result["value"]["partial_reasons"]
    )


def test_explicit_limit_disables_splitting(monkeypatch):
    monkeypatch.setattr(mod, "_ROW_CAP", 2)
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "a"}, {"@ptr": "b"}], stats={"recordsMatched": 9}),
    )
    result = _run(call, query="fields @message | limit 5")
    assert result["value"]["split_count"] == 0
    assert any("explicit 'limit'" in g for g in result["guidance"])
    # No limit parameter is forced onto StartQuery when the query sets one.
    start = call.params_for("StartQuery")[0]
    assert "limit" not in start


def test_row_output_truncated_at_max_rows():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    rows = [{"@ptr": f"p{i}"} for i in range(5)]
    call.queue("GetQueryResults", _qr(rows=rows, stats={"recordsMatched": 5}))
    result = _run(call, max_rows=2)
    assert result["value"]["row_count"] == 2
    assert any(
        "Row output truncated" in p for p in result["value"]["partial_reasons"]
    )


def test_sort_across_subwindows_warns(monkeypatch):
    monkeypatch.setattr(mod, "_ROW_CAP", 2)
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    # First segment caps and splits into two sub-windows, each small.
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "a"}, {"@ptr": "b"}], stats={"recordsMatched": 9}),
    )
    call.queue("StartQuery", ok_result({"queryId": "q2"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "c"}], stats={"recordsMatched": 1}),
    )
    call.queue("StartQuery", ok_result({"queryId": "q3"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "d"}], stats={"recordsMatched": 1}),
    )
    result = _run(call, query="fields @message | sort @timestamp desc")
    assert any("sort' order holds" in g for g in result["guidance"])


def test_more_than_50_groups_are_batched():
    call = ScriptedLogs()
    names = [f"/svc/fn-{i}" for i in range(51)]
    call.queue("ListLogGroups", _llg(*names))
    # Enrichment runs in batches of 50 identifiers -> two DescribeLogGroups.
    call.queue("DescribeLogGroups", _dlg(*[_group(n) for n in names[:50]]))
    call.queue("DescribeLogGroups", _dlg(*[_group(n) for n in names[50:]]))
    # One StartQuery + GetQueryResults per 50-group query batch (2 batches).
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"c": "1"}]))
    call.queue("StartQuery", ok_result({"queryId": "q2"}))
    call.queue("GetQueryResults", _qr(rows=[{"c": "2"}]))
    result = _run(call, groups="/svc/*", query="stats count()")
    assert result["ok"] is True
    assert call.ops().count("StartQuery") == 2
    assert call.ops().count("DescribeLogGroups") == 2
    assert any("exceed the 50-per-query" in g for g in result["guidance"])
    assert any("several batches" in g for g in result["guidance"])


# --------------------------------------------------------------- never-raises guard


def test_internal_error_is_normalized_not_raised():
    def exploding(operation, params):
        raise RuntimeError("kaboom")

    result = mod.run_insights_query(
        exploding,
        "/aws/lambda/fn",
        "fields @message",
        "2026-10-28T10:00:00Z",
        "2026-10-28T11:00:00Z",
        now=NOW,
        sleep=lambda _s: None,
        clock=_clock(),
    )
    assert result["ok"] is False
    assert result["code"] == SERVICE_ERROR
    assert "internal error" in result["error"]


# --------------------------------------------------------------- remaining branches


def test_propagate_generic_code_has_no_extra_guidance():
    # A plain SERVICE_ERROR from StartQuery goes through _propagate without the
    # credentials/permission-specific guidance branches.
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", err_result(SERVICE_ERROR, "transient blip"))
    result = _run(call)
    assert result["ok"] is False
    assert result["code"] == SERVICE_ERROR
    assert not any("lacks" in g for g in result["guidance"])


def test_stage_beginning_with_regex_is_advisory_not_fatal():
    # A '/' at the very start of a stage opens a regex literal (prev is empty);
    # the resulting stage is not a known command, but that is advisory now, not
    # a local rejection -- the query still runs.
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call, query="fields @message | /oops/")
    assert result["ok"] is True
    assert "StartQuery" in call.ops()
    assert any("not recognized by this tool" in g for g in result["guidance"])


def test_escaped_slash_inside_regex_literal():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    # The backslash escapes the '/', so the regex does not close early and the
    # trailing '|' is still inside it (two stages, both valid).
    result = _run(
        call,
        query="fields @message | filter @message like /a\\/b|c/",
    )
    assert result["ok"] is True


def test_malformed_query_without_position_info():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue(
        "StartQuery",
        err_result(
            SERVICE_ERROR,
            "the query could not be compiled",
            aws_code="MalformedQueryException",
        ),
    )
    result = _run(call)
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"
    # No position anywhere -> offset is None and no token is extracted.
    assert result["value"]["offset"] is None
    assert result["value"]["token"] == ""


def test_whitespace_group_entry_rejected():
    call = ScriptedLogs()
    result = _run(call, groups=["   "])
    assert result["ok"] is False
    assert result["param_error"] is True
    assert call.calls == []


def test_non_list_result_rows_are_skipped():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    # The second entry is not a list (malformed) and must be skipped, not crash.
    body = ok_result(
        {
            "status": "Complete",
            "results": [
                [{"field": "@ptr", "value": "p1"}],
                "garbage-not-a-list",
            ],
            "statistics": {},
        }
    )
    call.queue("GetQueryResults", body)
    result = _run(call)
    assert result["ok"] is True
    assert result["value"]["row_count"] == 1


def test_duplicate_group_entries_are_deduped():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    # The same group listed twice is normalized once -> one ListLogGroups.
    result = _run(call, groups=["/aws/lambda/fn", "/aws/lambda/fn"])
    assert result["ok"] is True
    assert call.ops().count("ListLogGroups") == 1


def test_subsecond_window_clamps_to_empty():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    # start < end by 800ms, but both ceil to the same whole second -> the
    # clamped integer-second window is empty.
    result = _run_window(
        call,
        "2026-10-28T10:00:00.100000Z",
        "2026-10-28T10:00:00.900000Z",
    )
    assert result["ok"] is False
    assert "empty" in result["error"]


def test_later_subwindow_failure_notes_completed_subqueries(monkeypatch):
    monkeypatch.setattr(mod, "_ROW_CAP", 2)
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    # Parent segment caps and splits into two sub-windows.
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "a"}, {"@ptr": "b"}], stats={"recordsMatched": 9}),
    )
    # First sub-window succeeds...
    call.queue("StartQuery", ok_result({"queryId": "q2"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "c"}], stats={"recordsMatched": 1}),
    )
    # ...the second sub-window fails after a completed one exists.
    call.queue("StartQuery", ok_result({"queryId": "q3"}))
    call.queue("GetQueryResults", err_result(PERMISSION_DENIED, "denied"))
    result = _run(call, query="fields @message")
    assert result["ok"] is False
    assert any(
        "had completed before the failure" in g for g in result["guidance"]
    )


def test_duplicate_ptr_across_subwindows_deduped(monkeypatch):
    monkeypatch.setattr(mod, "_ROW_CAP", 2)
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "a"}, {"@ptr": "b"}], stats={"recordsMatched": 9}),
    )
    # Both sub-windows return the SAME @ptr; the second occurrence is skipped.
    call.queue("StartQuery", ok_result({"queryId": "q2"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "dup"}], stats={"recordsMatched": 1}),
    )
    call.queue("StartQuery", ok_result({"queryId": "q3"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "dup"}], stats={"recordsMatched": 1}),
    )
    result = _run(call, query="fields @message")
    ptrs = [r["@ptr"] for r in result["value"]["rows"]]
    assert ptrs == ["dup"]


# --------------------------------------------------------------- GetQueryResults pagination


def test_get_query_results_paginates_next_token():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    # The terminal (first) page carries a nextToken; page until it is absent.
    call.queue(
        "GetQueryResults",
        _qr_page(
            rows=[{"@ptr": "p1"}],
            next_token="t1",
            stats={"recordsMatched": 3},
        ),
    )
    call.queue(
        "GetQueryResults", _qr_page(rows=[{"@ptr": "p2"}], next_token="t2")
    )
    call.queue("GetQueryResults", _qr_page(rows=[{"@ptr": "p3"}]))
    result = _run(call, max_rows=100)
    assert result["ok"] is True
    ptrs = [r["@ptr"] for r in result["value"]["rows"]]
    assert ptrs == ["p1", "p2", "p3"]
    # Terminal page + two pagination pages.
    assert call.ops().count("GetQueryResults") == 3
    # Pagination uses maxItems + nextToken.
    paged = [p for p in call.params_for("GetQueryResults") if "nextToken" in p]
    assert [p["nextToken"] for p in paged] == ["t1", "t2"]
    assert all(p["maxItems"] == 10000 for p in paged)


def test_pagination_stops_early_at_max_rows():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    # The terminal page already has >= max_rows rows (and a nextToken), so no
    # further page is fetched.
    call.queue(
        "GetQueryResults",
        _qr_page(rows=[{"@ptr": "p1"}, {"@ptr": "p2"}], next_token="t1"),
    )
    call.queue("GetQueryResults", _qr_page(rows=[{"@ptr": "p3"}]))
    result = _run(call, max_rows=2)
    assert result["ok"] is True
    assert result["value"]["row_count"] == 2
    # Only the terminal GetQueryResults ran; pagination stopped at max_rows.
    assert call.ops().count("GetQueryResults") == 1


def test_pagination_error_propagates():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue(
        "GetQueryResults", _qr_page(rows=[{"@ptr": "p1"}], next_token="t1")
    )
    call.queue("GetQueryResults", err_result(PERMISSION_DENIED, "denied"))
    result = _run(call, max_rows=100)
    assert result["ok"] is False
    assert result["code"] == PERMISSION_DENIED


# --------------------------------------------------------------- 100K row cap / split threshold


def test_records_matched_at_100k_does_not_split():
    # Exactly at the cap is not over it -> no split.
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "p1"}], stats={"recordsMatched": 100000}),
    )
    result = _run(call, query="fields @message")
    assert result["ok"] is True
    assert result["value"]["split_count"] == 0


def test_records_matched_10k_does_not_split_anymore():
    # 10K was the old cap; it is now well within the 100K cap.
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "p1"}], stats={"recordsMatched": 10000}),
    )
    result = _run(call, query="fields @message")
    assert result["value"]["split_count"] == 0


def test_records_matched_above_100k_triggers_split():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    # First segment exceeds the 100K cap -> split into two sub-windows.
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "a"}], stats={"recordsMatched": 150000}),
    )
    call.queue("StartQuery", ok_result({"queryId": "q2"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "b"}], stats={"recordsMatched": 10}),
    )
    call.queue("StartQuery", ok_result({"queryId": "q3"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "c"}], stats={"recordsMatched": 10}),
    )
    result = _run(call, query="fields @message")
    assert result["ok"] is True
    assert result["value"]["split_count"] >= 1


# --------------------------------------------------------------- non-additive aggregates (multi-batch)


def _batched_51_groups(call):
    names = [f"/svc/fn-{i}" for i in range(51)]
    call.queue("ListLogGroups", _llg(*names))
    call.queue("DescribeLogGroups", _dlg(*[_group(n) for n in names[:50]]))
    call.queue("DescribeLogGroups", _dlg(*[_group(n) for n in names[50:]]))


def test_non_additive_aggregate_multi_batch_warns():
    call = ScriptedLogs()
    _batched_51_groups(call)
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"host": "a", "p95": "1"}]))
    call.queue("StartQuery", ok_result({"queryId": "q2"}))
    call.queue("GetQueryResults", _qr(rows=[{"host": "b", "p95": "2"}]))
    result = _run(call, groups="/svc/*", query="stats avg(duration) by host")
    assert result["ok"] is True
    assert result["is_exhaustive"] is False
    assert any(
        "non-additive aggregates" in p
        for p in result["value"]["partial_reasons"]
    )
    # The misleading additive "sum per-key counts" advice is suppressed.
    assert not any("sum per-key counts" in g for g in result["guidance"])


def test_pattern_command_multi_batch_warns():
    call = ScriptedLogs()
    _batched_51_groups(call)
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@pattern": "a"}]))
    call.queue("StartQuery", ok_result({"queryId": "q2"}))
    call.queue("GetQueryResults", _qr(rows=[{"@pattern": "b"}]))
    result = _run(call, groups="/svc/*", query="pattern @message")
    assert result["is_exhaustive"] is False
    assert any(
        "non-additive aggregates" in p
        for p in result["value"]["partial_reasons"]
    )


def test_non_additive_aggregate_single_batch_no_warning():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"host": "a", "p95": "1"}]))
    result = _run(call, query="stats avg(duration) by host")
    assert result["ok"] is True
    assert not any(
        "non-additive aggregates" in p
        for p in result["value"]["partial_reasons"]
    )


def test_additive_aggregate_multi_batch_keeps_sum_guidance():
    # count is additive -> no non-additive warning, and the "sum per-key counts"
    # guidance is still offered.
    call = ScriptedLogs()
    _batched_51_groups(call)
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"c": "1"}]))
    call.queue("StartQuery", ok_result({"queryId": "q2"}))
    call.queue("GetQueryResults", _qr(rows=[{"c": "2"}]))
    result = _run(call, groups="/svc/*", query="stats count() by host")
    assert not any(
        "non-additive aggregates" in p
        for p in result["value"]["partial_reasons"]
    )
    assert any("sum per-key counts" in g for g in result["guidance"])


# --------------------------------------------------------------- 6a: log group class (DELIVERY / Essentials)


def _group_cls(name, cls, retention=None):
    """A _group(...) dict that also carries a logGroupClass (from enrichment)."""
    g = _group(name, retention=retention)
    g["logGroupClass"] = cls
    return g


def test_delivery_class_group_is_filtered_out():
    call = ScriptedLogs()
    # Prefix match returns a STANDARD group and a DELIVERY group.
    call.queue("ListLogGroups", _llg("/aws/lambda/keep", "/aws/delivery/dg"))
    call.queue(
        "DescribeLogGroups",
        _dlg(
            _group("/aws/lambda/keep"),
            _group_cls("/aws/delivery/dg", "DELIVERY"),
        ),
    )
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call, groups="/aws/*", query="fields @message")
    assert result["ok"] is True
    # The DELIVERY group is never queried.
    assert result["value"]["log_groups"] == ["/aws/lambda/keep"]
    start = call.params_for("StartQuery")[0]
    assert start["logGroupNames"] == ["/aws/lambda/keep"]
    # It is reported in skipped_log_groups with its class and in guidance.
    assert any(
        s["log_group"] == "/aws/delivery/dg"
        and s.get("log_group_class") == "DELIVERY"
        for s in result["value"]["skipped_log_groups"]
    )
    assert any("DELIVERY class" in g for g in result["guidance"])


def test_all_delivery_groups_is_invalid_input():
    call = ScriptedLogs()
    call.queue("ListLogGroups", _llg("/aws/delivery/dg"))
    call.queue(
        "DescribeLogGroups", _dlg(_group_cls("/aws/delivery/dg", "DELIVERY"))
    )
    result = _run(call, groups="/aws/delivery/*", query="fields @message")
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"
    # Nothing queryable remained, so StartQuery never runs.
    assert "StartQuery" not in call.ops()
    assert any("DELIVERY" in g for g in result["guidance"])


def test_essentials_class_warns_on_pattern_command():
    call = ScriptedLogs()
    call.queue("ListLogGroups", _llg("/aws/lambda/ia"))
    call.queue(
        "DescribeLogGroups",
        _dlg(_group_cls("/aws/lambda/ia", "INFREQUENT_ACCESS")),
    )
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@pattern": "x"}]))
    result = _run(call, groups="/aws/lambda/ia", query="pattern @message")
    assert result["ok"] is True
    assert any(
        "Essentials class" in g and "INFREQUENT_ACCESS" in g
        for g in result["guidance"]
    )


def test_essentials_class_warns_on_unmask_command():
    call = ScriptedLogs()
    call.queue("ListLogGroups", _llg("/aws/lambda/ia"))
    call.queue(
        "DescribeLogGroups",
        _dlg(_group_cls("/aws/lambda/ia", "INFREQUENT_ACCESS")),
    )
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(
        call,
        groups="/aws/lambda/ia",
        query="fields @message | unmask @message",
    )
    assert result["ok"] is True
    assert any("Essentials class" in g for g in result["guidance"])


def test_essentials_class_no_warning_for_plain_query():
    call = ScriptedLogs()
    call.queue("ListLogGroups", _llg("/aws/lambda/ia"))
    call.queue(
        "DescribeLogGroups",
        _dlg(_group_cls("/aws/lambda/ia", "INFREQUENT_ACCESS")),
    )
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call, groups="/aws/lambda/ia", query="fields @message")
    assert result["ok"] is True
    assert not any("Essentials class" in g for g in result["guidance"])


def test_unmask_is_a_known_command():
    # Item 6a.3: unmask must be recognized so the Essentials check can see it.
    assert "unmask" in mod._KNOWN_COMMANDS


# --------------------------------------------------------------- 6b: relative time (--since / now-1h)


def test_since_sets_window_to_last_hour():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = mod.run_insights_query(
        call,
        "/aws/lambda/fn",
        "fields @message",
        None,
        None,
        since="1h",
        now=NOW,
        sleep=lambda _s: None,
        clock=_clock(),
    )
    assert result["ok"] is True
    # NOW is 12:00:00Z -> window is 11:00:00Z .. 12:00:00Z.
    assert result["value"]["window"]["start"] == "2026-10-28T11:00:00Z"
    assert result["value"]["window"]["end"] == "2026-10-28T12:00:00Z"


def test_since_minutes():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = mod.run_insights_query(
        call,
        "/aws/lambda/fn",
        "fields @message",
        None,
        None,
        since="30m",
        now=NOW,
        sleep=lambda _s: None,
        clock=_clock(),
    )
    assert result["ok"] is True
    assert result["value"]["window"]["start"] == "2026-10-28T11:30:00Z"


def test_since_days_is_case_insensitive():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = mod.run_insights_query(
        call,
        "/aws/lambda/fn",
        "fields @message",
        None,
        None,
        since="7D",
        now=NOW,
        sleep=lambda _s: None,
        clock=_clock(),
    )
    assert result["ok"] is True
    assert result["value"]["window"]["start"] == "2026-10-21T12:00:00Z"


def test_since_conflicts_with_start_time():
    call = ScriptedLogs()
    result = mod.run_insights_query(
        call,
        "/aws/lambda/fn",
        "fields @message",
        "2026-10-28T10:00:00Z",
        None,
        since="1h",
        now=NOW,
        sleep=lambda _s: None,
        clock=_clock(),
    )
    assert result["ok"] is False
    assert result["param_error"] is True
    assert call.calls == []
    assert any("conflicts" in g for g in result["guidance"])


def test_invalid_since_duration_rejected():
    call = ScriptedLogs()
    result = mod.run_insights_query(
        call,
        "/aws/lambda/fn",
        "fields @message",
        None,
        None,
        since="banana",
        now=NOW,
        sleep=lambda _s: None,
        clock=_clock(),
    )
    assert result["ok"] is False
    assert result["param_error"] is True
    assert call.calls == []


def test_now_relative_syntax_in_start_and_end_time():
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = mod.run_insights_query(
        call,
        "/aws/lambda/fn",
        "fields @message",
        "now-2h",
        "now",
        now=NOW,
        sleep=lambda _s: None,
        clock=_clock(),
    )
    assert result["ok"] is True
    assert result["value"]["window"]["start"] == "2026-10-28T10:00:00Z"
    assert result["value"]["window"]["end"] == "2026-10-28T12:00:00Z"


# --------------------------------------------------------------- 6c: overall deadline


def test_deadline_exceeded_returns_partial_results():
    call = ScriptedLogs()
    names = [f"/svc/fn-{i}" for i in range(51)]
    call.queue("ListLogGroups", _llg(*names))
    call.queue("DescribeLogGroups", _dlg(*[_group(n) for n in names[:50]]))
    call.queue("DescribeLogGroups", _dlg(*[_group(n) for n in names[50:]]))
    # Only the first of the two batches runs; the deadline trips before the
    # second sub-query starts.
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue(
        "GetQueryResults",
        _qr(rows=[{"@ptr": "p1"}], stats={"recordsMatched": 1}),
    )
    result = _run(
        call, groups="/svc/*", query="fields @message", max_deadline=0.001
    )
    assert result["ok"] is True
    assert result["is_exhaustive"] is False
    # At least one sub-query always runs; further ones are skipped.
    assert result["value"]["queries_run"] == 1
    assert call.ops().count("StartQuery") == 1
    assert result["value"]["row_count"] == 1
    assert any(
        "overall deadline" in p for p in result["value"]["partial_reasons"]
    )


def test_max_queries_is_exposed_as_kwarg():
    # Item 6c: max_queries is now CLI-exposed; confirm the plumbed param caps
    # the number of sub-queries run (also guards against regressions).
    call = ScriptedLogs()
    import awscli.customizations.logs.run_insights_query as m

    old = m._ROW_CAP
    m._ROW_CAP = 2
    try:
        _discover(call, _group("/aws/lambda/fn"))
        call.queue("StartQuery", ok_result({"queryId": "q1"}))
        call.queue(
            "GetQueryResults",
            _qr(
                rows=[{"@ptr": "a"}, {"@ptr": "b"}],
                stats={"recordsMatched": 9},
            ),
        )
        result = _run(call, query="fields @message", max_queries=1)
    finally:
        m._ROW_CAP = old
    assert result["value"]["queries_run"] == 1
    assert any(
        "max_queries=1" in p for p in result["value"]["partial_reasons"]
    )


# --------------------------------------------------------------- 6d: StopQuery on interrupt


def test_keyboard_interrupt_triggers_stop_query():
    import pytest

    inner = ScriptedLogs()
    _discover(inner, _group("/aws/lambda/fn"))
    inner.queue("StartQuery", ok_result({"queryId": "q1"}))

    def call(operation, params):
        # Simulate Ctrl-C while polling: the query is already started and
        # in-flight, so cleanup must StopQuery it.
        if operation == "GetQueryResults":
            raise KeyboardInterrupt
        return inner(operation, params)

    with pytest.raises(KeyboardInterrupt):
        mod.run_insights_query(
            call,
            "/aws/lambda/fn",
            "fields @message",
            "2026-10-28T10:00:00Z",
            "2026-10-28T11:00:00Z",
            now=NOW,
            sleep=lambda _s: None,
            clock=_clock(),
        )
    # The in-flight query id was stopped during the finally cleanup.
    assert inner.params_for("StopQuery") == [{"queryId": "q1"}]


def test_normal_completion_does_not_stop_query():
    # The finally cleanup must not StopQuery a query that finished normally.
    call = ScriptedLogs()
    _discover(call, _group("/aws/lambda/fn"))
    call.queue("StartQuery", ok_result({"queryId": "q1"}))
    call.queue("GetQueryResults", _qr(rows=[{"@ptr": "p1"}]))
    result = _run(call)
    assert result["ok"] is True
    assert "StopQuery" not in call.ops()
