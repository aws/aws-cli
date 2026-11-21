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
"""Unit tests for ``aws athena run-query`` (run_athena_query logic)."""

from awscli.customizations.athena.run_query import run_athena_query
from awscli.customizations.compositereadonly.helpers import (
    CREDENTIALS_EXPIRED,
    PERMISSION_DENIED,
    THROTTLED,
    assert_read_only,
    err_result,
    ok_result,
)


class ScriptedAthena:
    """A scripted read-only call bridge: records calls, returns queued results."""

    def __init__(self):
        self.calls = []
        self._responses = {}

    def queue(self, operation, *results):
        self._responses.setdefault(operation, []).extend(results)
        return self

    def __call__(self, operation, params):
        # Every scripted operation must be read-only, mirroring the real bridge.
        assert_read_only(operation)
        self.calls.append((operation, params))
        queued = self._responses.get(operation)
        if queued:
            return queued.pop(0)
        return ok_result({})

    def ops(self):
        return [op for op, _ in self.calls]


def _wg(
    output_location="s3://results/",
    enforced=False,
    state="ENABLED",
    engine="Athena engine version 3",
    managed=False,
):
    cfg = {
        "EnforceWorkGroupConfiguration": enforced,
        "EngineVersion": {"EffectiveEngineVersion": engine},
    }
    if output_location is not None:
        cfg["ResultConfiguration"] = {"OutputLocation": output_location}
    if managed:
        cfg["ManagedQueryResultsConfiguration"] = {"Enabled": True}
    return ok_result({"WorkGroup": {"State": state, "Configuration": cfg}})


def _exec(state="SUCCEEDED", stmt_type="DML", reason=None, category=None):
    status = {"State": state}
    if reason:
        status["StateChangeReason"] = reason
    if category is not None:
        status["AthenaError"] = {"ErrorCategory": category}
    return ok_result(
        {
            "QueryExecution": {
                "Status": status,
                "StatementType": stmt_type,
                "Statistics": {"DataScannedInBytes": 123},
                "ResultConfiguration": {
                    "OutputLocation": "s3://results/q.csv"
                },
            }
        }
    )


def _results(rows, columns=None, next_token=None, with_header=True):
    columns = columns or [{"Name": "c1", "Type": "varchar"}]
    data_rows = []
    if with_header:
        data_rows.append(
            {"Data": [{"VarCharValue": c["Name"]} for c in columns]}
        )
    for r in rows:
        data_rows.append({"Data": [{"VarCharValue": v} for v in r]})
    body = {
        "ResultSet": {
            "ResultSetMetadata": {"ColumnInfo": columns},
            "Rows": data_rows,
        }
    }
    if next_token:
        body["NextToken"] = next_token
    return ok_result(body)


def _run(call_op, sql="SELECT 1", **kwargs):
    kwargs.setdefault("workgroup", "primary")
    return run_athena_query(
        call_op, sql, sleep=lambda _s: None, clock=_fake_clock(), **kwargs
    )


def _fake_clock():
    state = {"t": 0.0}

    def clock():
        state["t"] += 0.001
        return state["t"]

    return clock


def _expired_clock():
    # First call (poller construction) returns 0.0, so the deadline is max_wait;
    # every later call returns a time well past it, forcing a timeout.
    calls = {"n": 0}

    def clock():
        calls["n"] += 1
        return 0.0 if calls["n"] == 1 else 1000.0

    return clock


# --------------------------------------------------------------- input validation


def test_rejects_non_s3_output_location():
    call = ScriptedAthena()
    result = _run(call, sql="SELECT 1", output_location="/tmp/x")
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"


def test_rejects_bad_max_rows():
    call = ScriptedAthena()
    result = _run(call, sql="SELECT 1", max_rows=0)
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"


def test_rejects_empty_sql():
    # An empty --sql is caught client-side as a ParamValidation error (exit 252,
    # param_error=True) instead of slipping through to Athena as a SERVICE_ERROR.
    call = ScriptedAthena()
    result = _run(call, sql="")
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"
    assert result["param_error"] is True
    assert "sql is an empty string" in result["error"]
    # No AWS call is made for an empty statement.
    assert call.ops() == []


# --------------------------------------------------------------- happy path


def test_success_returns_rows_and_only_read_ops():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue("GetQueryResults", _results([["a"], ["b"]]))
    result = _run(call, sql="SELECT c1 FROM t")
    assert result["ok"] is True
    value = result["value"]
    assert value["query_execution_id"] == "q1"
    assert value["row_count"] == 2
    assert value["rows"] == [{"c1": "a"}, {"c1": "b"}]
    assert value["header_row_dropped"] is True
    assert result["is_exhaustive"] is True
    # Read-only: only the query lifecycle read ops were issued.
    assert call.ops() == [
        "GetWorkGroup",
        "StartQueryExecution",
        "GetQueryExecution",
        "GetQueryResults",
    ]


def test_integer_columns_are_coerced():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue(
        "GetQueryResults",
        _results([["42"]], columns=[{"Name": "n", "Type": "bigint"}]),
    )
    result = _run(call, sql="SELECT n FROM t")
    assert result["value"]["rows"] == [{"n": 42}]


def test_no_coerce_keeps_strings():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue(
        "GetQueryResults",
        _results([["42"]], columns=[{"Name": "n", "Type": "bigint"}]),
    )
    result = _run(call, sql="SELECT n FROM t", coerce_types=False)
    assert result["value"]["rows"] == [{"n": "42"}]


def test_empty_result_set():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue("GetQueryResults", _results([]))
    result = _run(call, sql="SELECT c1 FROM t")
    assert result["ok"] is True
    assert result["value"]["row_count"] == 0


# --------------------------------------------------------------- pagination / cap


def test_pagination_follows_next_token():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue("GetQueryResults", _results([["a"]], next_token="t2"))
    call.queue("GetQueryResults", _results([["b"]], with_header=False))
    result = _run(call, sql="SELECT c1 FROM t")
    assert result["value"]["row_count"] == 2
    assert result["value"]["pages_fetched"] == 2


def test_row_cap_truncates_and_exposes_resume_token():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue(
        "GetQueryResults", _results([["a"], ["b"], ["c"]], next_token="more")
    )
    result = _run(call, sql="SELECT c1 FROM t", max_rows=2)
    assert result["value"]["is_truncated"] is True
    assert result["value"]["next_token"] == "more"
    assert result["is_exhaustive"] is False
    assert result["value"]["row_count"] == 2


# --------------------------------------------------------------- failures


def test_workgroup_not_found():
    call = ScriptedAthena()
    call.queue(
        "GetWorkGroup",
        err_result(
            "NOT_FOUND",
            "WorkGroup not found",
            aws_code="InvalidRequestException",
        ),
    )
    result = _run(call, sql="SELECT 1", workgroup="ghost")
    assert result["ok"] is False
    assert result["code"] == "NOT_FOUND"
    # No query was started against a missing workgroup.
    assert "StartQueryExecution" not in call.ops()


def test_failed_query_surfaces_state_change_reason():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue(
        "GetQueryExecution",
        _exec(
            state="FAILED", reason="Column 'x' cannot be resolved", category=2
        ),
    )
    result = _run(call, sql="SELECT x FROM t")
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"
    assert "cannot be resolved" in result["value"]["state_change_reason"]


def test_cancelled_query_is_conflict():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec(state="CANCELLED", reason="by user"))
    result = _run(call, sql="SELECT 1 FROM t")
    assert result["ok"] is False
    assert result["code"] == "CONFLICT"


def test_timeout_returns_query_id_and_does_not_resubmit():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    # Always RUNNING -> never terminal; deadline forces a timeout.
    for _ in range(50):
        call.queue("GetQueryExecution", _exec(state="RUNNING"))
    result = run_athena_query(
        call,
        "SELECT 1 FROM t",
        workgroup="primary",
        max_wait=1.0,
        sleep=lambda _s: None,
        clock=_expired_clock(),
    )
    assert result["ok"] is False
    assert result["code"] == "TIMEOUT"
    assert result["key"] == "q1"
    assert call.ops().count("StartQueryExecution") == 1


def test_cancel_on_timeout_stops_the_query():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    for _ in range(50):
        call.queue("GetQueryExecution", _exec(state="RUNNING"))
    call.queue("StopQueryExecution", ok_result({}))
    result = run_athena_query(
        call,
        "SELECT 1 FROM t",
        workgroup="primary",
        max_wait=1.0,
        cancel_on_timeout=True,
        sleep=lambda _s: None,
        clock=_expired_clock(),
    )
    assert result["code"] == "TIMEOUT"
    assert result["value"]["cancelled"] is True
    assert "StopQueryExecution" in call.ops()


# --- workgroup output-location auto-resolution


def test_workgroup_auto_resolved_when_primary_lacks_output_location():
    call = ScriptedAthena()
    # resolve step: primary has no output location, then list + pick 'analytics'.
    call.queue("GetWorkGroup", _wg(output_location=None))  # resolve: primary
    call.queue(
        "ListWorkGroups",
        ok_result({"WorkGroups": [{"Name": "analytics", "State": "ENABLED"}]}),
    )
    call.queue(
        "GetWorkGroup", _wg(output_location="s3://picked/")
    )  # resolve: analytics
    # run step re-reads the chosen workgroup.
    call.queue("GetWorkGroup", _wg(output_location="s3://picked/"))
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue("GetQueryResults", _results([["a"]]))
    result = run_athena_query(
        call,
        "SELECT 1 FROM t",
        workgroup=None,
        sleep=lambda _s: None,
        clock=_fake_clock(),
    )
    assert result["ok"] is True
    assert result["value"]["workgroup"] == "analytics"
    assert any("auto-selected workgroup" in g for g in result["guidance"])


def test_enforced_workgroup_ignores_caller_output_location():
    call = ScriptedAthena()
    call.queue(
        "GetWorkGroup",
        _wg(output_location="s3://enforced/", enforced=True),
    )
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue("GetQueryResults", _results([["a"]]))
    result = _run(
        call,
        sql="SELECT 1 FROM t",
        output_location="s3://caller/",
        workgroup="wg",
    )
    assert result["ok"] is True
    start_params = dict(call.calls)["StartQueryExecution"]
    # Enforced config: we do NOT send a ResultConfiguration override.
    assert "ResultConfiguration" not in start_params


# --------------------------------------------------------------- param validation (direct)


def test_empty_workgroup_string_rejected():
    result = run_athena_query(
        lambda *a: ok_result({}),
        "SELECT 1",
        workgroup="  ",
        sleep=lambda _s: None,
        clock=_fake_clock(),
    )
    assert result["ok"] is False
    assert "workgroup is empty" in result["error"]


def test_empty_catalog_rejected():
    result = run_athena_query(
        lambda *a: ok_result({}),
        "SELECT 1",
        workgroup="primary",
        catalog="  ",
        sleep=lambda _s: None,
        clock=_fake_clock(),
    )
    assert result["ok"] is False
    assert "catalog is empty" in result["error"]


def test_empty_database_string_rejected():
    result = run_athena_query(
        lambda *a: ok_result({}),
        "SELECT 1",
        workgroup="primary",
        database="",
        sleep=lambda _s: None,
        clock=_fake_clock(),
    )
    assert result["ok"] is False
    assert "database is an empty string" in result["error"]


def test_output_location_too_short_rejected():
    call = ScriptedAthena()
    result = _run(call, sql="SELECT 1", output_location="s3://")
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"


def test_boolean_max_rows_rejected():
    # bool is a subclass of int; it must be rejected, not accepted as 1.
    call = ScriptedAthena()
    result = _run(call, sql="SELECT 1", max_rows=True)
    assert result["ok"] is False
    assert "max_rows" in result["error"]


def test_nonpositive_poll_interval_rejected():
    result = run_athena_query(
        lambda *a: ok_result({}),
        "SELECT 1",
        workgroup="primary",
        poll_interval=0,
        sleep=lambda _s: None,
        clock=_fake_clock(),
    )
    assert result["ok"] is False
    assert "poll_interval" in result["error"]


def test_nonpositive_max_wait_rejected():
    result = run_athena_query(
        lambda *a: ok_result({}),
        "SELECT 1",
        workgroup="primary",
        max_wait=-1.0,
        sleep=lambda _s: None,
        clock=_fake_clock(),
    )
    assert result["ok"] is False
    assert "max_wait" in result["error"]


# --------------------------------------------------------------- workgroup read


def test_disabled_workgroup_is_not_ready():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg(state="DISABLED"))
    result = _run(call, sql="SELECT 1", workgroup="wg")
    assert result["ok"] is False
    assert result["code"] == "NOT_READY"
    assert "StartQueryExecution" not in call.ops()


def test_workgroup_not_found_via_error_message():
    call = ScriptedAthena()
    call.queue(
        "GetWorkGroup",
        err_result(
            "SERVICE_ERROR",
            "WorkGroup ghost not found",
        ),
    )
    result = _run(call, sql="SELECT 1", workgroup="ghost")
    assert result["ok"] is False
    assert result["code"] == "NOT_FOUND"


def test_workgroup_credentials_expired():
    call = ScriptedAthena()
    call.queue(
        "GetWorkGroup",
        err_result(CREDENTIALS_EXPIRED, "token expired"),
    )
    result = _run(call, sql="SELECT 1", workgroup="wg")
    assert result["ok"] is False
    assert result["code"] == CREDENTIALS_EXPIRED
    assert result["retriable"] is True


def test_unreadable_workgroup_proceeds_with_note():
    # A non-fatal GetWorkGroup error: proceed, but with no enforced location
    # the caller must supply one, which we do.
    call = ScriptedAthena()
    call.queue("GetWorkGroup", err_result("SERVICE_ERROR", "flaky"))
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue("GetQueryResults", _results([["a"]]))
    result = _run(
        call,
        sql="SELECT 1",
        workgroup="wg",
        output_location="s3://caller/",
    )
    assert result["ok"] is True
    assert any("proceeding without" in g for g in result["guidance"])


def test_selected_engine_version_used_when_no_effective():
    call = ScriptedAthena()
    wg = ok_result(
        {
            "WorkGroup": {
                "State": "ENABLED",
                "Configuration": {
                    "ResultConfiguration": {"OutputLocation": "s3://r/"},
                    "EngineVersion": {
                        "SelectedEngineVersion": "Athena engine version 2"
                    },
                },
            }
        }
    )
    call.queue("GetWorkGroup", wg)
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    # The terminal execution carries no EngineVersion, so the workgroup's
    # selected version survives into the result.
    call.queue(
        "GetQueryExecution",
        ok_result(
            {
                "QueryExecution": {
                    "Status": {"State": "SUCCEEDED"},
                    "StatementType": "DML",
                    "Statistics": {"DataScannedInBytes": 1},
                }
            }
        ),
    )
    call.queue("GetQueryResults", _results([["a"]]))
    result = _run(call, sql="SELECT 1", workgroup="wg")
    assert result["value"]["engine_version"] == "Athena engine version 2"


def test_managed_results_workgroup_sends_no_result_config():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg(output_location=None, managed=True))
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue("GetQueryResults", _results([["a"]]))
    result = _run(call, sql="SELECT 1", workgroup="wg")
    assert result["ok"] is True
    assert result["value"]["output_location_source"] == "workgroup_managed"
    start = dict(call.calls)["StartQueryExecution"]
    assert "ResultConfiguration" not in start


def test_enforced_managed_results_source():
    call = ScriptedAthena()
    call.queue(
        "GetWorkGroup",
        _wg(output_location=None, managed=True, enforced=True),
    )
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue("GetQueryResults", _results([["a"]]))
    result = _run(
        call,
        sql="SELECT 1",
        workgroup="wg",
        output_location="s3://caller/",
    )
    assert result["ok"] is True
    assert result["value"]["output_location_source"] == "workgroup_managed"
    assert any("enforces its configuration" in g for g in result["guidance"])


def test_no_output_location_anywhere_is_invalid_input():
    # Workgroup read OK, not enforced, no default/managed location, and no
    # caller output -> a precise INVALID_INPUT before starting the query.
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg(output_location=None))
    result = _run(call, sql="SELECT 1", workgroup="wg")
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"
    assert "no result output location" in result["error"]
    assert "StartQueryExecution" not in call.ops()


# --------------------------------------------------------------- start failures


def test_start_not_supported_maps_to_invalid_input():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue(
        "StartQueryExecution",
        err_result(
            "SERVICE_ERROR",
            "Queries of this type are not supported",
            aws_code="InvalidRequestException",
        ),
    )
    result = _run(call, sql="SELECT 1", workgroup="wg")
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"


def test_start_permission_denied_guidance():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue(
        "StartQueryExecution",
        err_result(PERMISSION_DENIED, "not authorized"),
    )
    result = _run(call, sql="SELECT 1", workgroup="wg")
    assert result["code"] == PERMISSION_DENIED
    assert any("StartQueryExecution" in g for g in result["guidance"])


def test_start_throttled_is_retriable():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", err_result(THROTTLED, "slow down"))
    result = _run(call, sql="SELECT 1", workgroup="wg")
    assert result["code"] == THROTTLED
    assert result["retriable"] is True


def test_start_credentials_expired_is_retriable():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue(
        "StartQueryExecution", err_result(CREDENTIALS_EXPIRED, "expired")
    )
    result = _run(call, sql="SELECT 1", workgroup="wg")
    assert result["code"] == CREDENTIALS_EXPIRED
    assert result["retriable"] is True


def test_start_generic_failure():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", err_result("SERVICE_ERROR", "boom"))
    result = _run(call, sql="SELECT 1", workgroup="wg")
    assert result["code"] == "SERVICE_ERROR"


def test_start_returns_no_query_id():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({}))  # no QueryExecutionId
    result = _run(call, sql="SELECT 1", workgroup="wg")
    assert result["ok"] is False
    assert result["code"] == "SERVICE_ERROR"
    assert "no QueryExecutionId" in result["error"]


# --------------------------------------------------------------- polling edge cases


def test_transient_poll_errors_then_success():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    # Two retriable poll errors are tolerated before a terminal success.
    call.queue("GetQueryExecution", err_result(THROTTLED, "slow"))
    call.queue(
        "GetQueryExecution",
        err_result("NETWORK_ERROR", "reset", retriable=True),
    )
    call.queue("GetQueryExecution", _exec())
    call.queue("GetQueryResults", _results([["a"]]))
    result = _run(call, sql="SELECT 1", workgroup="wg")
    assert result["ok"] is True
    assert call.ops().count("GetQueryExecution") == 3


def test_non_retriable_poll_error_returns_started_guidance():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", err_result(PERMISSION_DENIED, "denied"))
    result = _run(call, sql="SELECT 1", workgroup="wg")
    assert result["ok"] is False
    assert result["code"] == PERMISSION_DENIED
    assert result["key"] == "q1"
    assert any("was started" in g for g in result["guidance"])


def test_cancel_on_timeout_stop_fails_stays_retriable():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    for _ in range(50):
        call.queue("GetQueryExecution", _exec(state="RUNNING"))
    # StopQueryExecution itself fails, so the query is NOT confirmed cancelled.
    call.queue("StopQueryExecution", err_result("SERVICE_ERROR", "nope"))
    result = run_athena_query(
        call,
        "SELECT 1 FROM t",
        workgroup="primary",
        max_wait=1.0,
        cancel_on_timeout=True,
        sleep=lambda _s: None,
        clock=_expired_clock(),
    )
    assert result["code"] == "TIMEOUT"
    assert result["value"]["cancelled"] is False
    assert result["retriable"] is True


# --------------------------------------------------------------- result decoding


def test_boolean_column_is_coerced():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue(
        "GetQueryResults",
        _results(
            [["true"], ["false"]],
            columns=[{"Name": "flag", "Type": "boolean"}],
        ),
    )
    result = _run(call, sql="SELECT flag FROM t")
    assert result["value"]["rows"] == [{"flag": True}, {"flag": False}]


def test_non_integer_value_in_integer_column_stays_string():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue(
        "GetQueryResults",
        _results([["NaN"]], columns=[{"Name": "n", "Type": "bigint"}]),
    )
    result = _run(call, sql="SELECT n FROM t")
    # int("NaN") raises -> value is left as the verbatim string.
    assert result["value"]["rows"] == [{"n": "NaN"}]


def test_null_cell_is_preserved_as_none():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    # A cell with no VarCharValue decodes to SQL NULL -> None.
    body = ok_result(
        {
            "ResultSet": {
                "ResultSetMetadata": {
                    "ColumnInfo": [{"Name": "c1", "Type": "varchar"}]
                },
                "Rows": [
                    {"Data": [{"VarCharValue": "c1"}]},
                    {"Data": [{}]},
                ],
            }
        }
    )
    call.queue("GetQueryResults", body)
    result = _run(call, sql="SELECT c1 FROM t")
    assert result["value"]["rows"] == [{"c1": None}]


def test_duplicate_column_labels_are_suffixed_with_note():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue(
        "GetQueryResults",
        _results(
            [["1", "2"]],
            columns=[
                {"Name": "c", "Type": "varchar"},
                {"Name": "c", "Type": "varchar"},
            ],
        ),
    )
    result = _run(call, sql="SELECT a AS c, b AS c FROM t")
    assert result["value"]["rows"] == [{"c": "1", "c_2": "2"}]
    assert any("Duplicate column" in g for g in result["guidance"])


def test_non_dml_header_dropped_when_first_row_matches_names():
    # SHOW/DESCRIBE are non-DML (expect_header False); the header is dropped
    # only because the first row equals the column names.
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec(stmt_type="UTILITY"))
    call.queue(
        "GetQueryResults",
        _results(
            [["partition_a"]],
            columns=[{"Name": "partition", "Type": "varchar"}],
        ),
    )
    result = _run(call, sql="SHOW PARTITIONS t")
    assert result["value"]["header_row_dropped"] is True
    assert result["value"]["rows"] == [{"partition": "partition_a"}]


def test_get_query_results_failure_midway_returns_partial():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue("GetQueryResults", _results([["a"]], next_token="t2"))
    call.queue(
        "GetQueryResults",
        err_result(THROTTLED, "throttled on page 2", retriable=True),
    )
    result = _run(call, sql="SELECT c1 FROM t")
    assert result["ok"] is False
    assert result["code"] == THROTTLED
    # The already-fetched page and a resume token are surfaced, not discarded.
    assert result["value"]["row_count"] == 1
    assert result["value"]["is_truncated"] is True
    assert result["is_exhaustive"] is False


def test_repeated_next_token_stops_pagination():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    # Server repeats the same NextToken; the loop must break, not spin.
    call.queue("GetQueryResults", _results([["a"]], next_token="dup"))
    call.queue(
        "GetQueryResults",
        _results([["b"]], next_token="dup", with_header=False),
    )
    result = _run(call, sql="SELECT c1 FROM t")
    assert result["ok"] is True
    assert any("repeated a NextToken" in g for g in result["guidance"])


def test_truncation_guidance_names_resume_token():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue(
        "GetQueryResults",
        _results([["a"], ["b"]], next_token="RESUME"),
    )
    result = _run(call, sql="SELECT c1 FROM t", max_rows=1)
    assert result["value"]["is_truncated"] is True
    assert result["value"]["next_token"] == "RESUME"
    assert any("RESUME" in g for g in result["guidance"])


def test_statistics_are_surfaced():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    exec_body = ok_result(
        {
            "QueryExecution": {
                "Status": {"State": "SUCCEEDED"},
                "StatementType": "DML",
                "Statistics": {
                    "DataScannedInBytes": 1000,
                    "EngineExecutionTimeInMillis": 50,
                    "TotalExecutionTimeInMillis": 70,
                    "QueryQueueTimeInMillis": 5,
                },
            }
        }
    )
    call.queue("GetQueryExecution", exec_body)
    call.queue("GetQueryResults", _results([["a"]]))
    result = _run(call, sql="SELECT c1 FROM t")
    assert result["value"]["data_scanned_bytes"] == 1000
    assert result["value"]["engine_execution_time_ms"] == 50
    assert result["value"]["queue_time_ms"] == 5


# --------------------------------------------------------------- never-raises guard


def test_internal_error_is_normalized_not_raised():
    # call_op raising an unexpected exception is caught and returned as data.
    def exploding(operation, params):
        raise RuntimeError("kaboom")

    result = run_athena_query(
        exploding,
        "SELECT 1",
        workgroup="primary",
        sleep=lambda _s: None,
        clock=_fake_clock(),
    )
    assert result["ok"] is False
    assert result["code"] == "SERVICE_ERROR"
    assert "internal error" in result["error"]


# --------------------------------------------------------------- failure classification


def test_failed_query_access_denied_is_permission_denied():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue(
        "GetQueryExecution",
        _exec(state="FAILED", reason="Access Denied writing results to S3"),
    )
    result = _run(call, sql="SELECT 1 FROM t")
    assert result["ok"] is False
    assert result["code"] == PERMISSION_DENIED


def test_failed_query_not_supported_reason_is_invalid_input():
    # A terminal FAILED whose reason is "not supported" classifies as bad input.
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue(
        "GetQueryExecution",
        _exec(
            state="FAILED",
            reason="Queries of this type are not supported here",
        ),
    )
    result = _run(call, sql="SELECT 1 FROM t")
    assert result["code"] == "INVALID_INPUT"


def test_failed_query_not_authorized_is_permission_denied():
    # Matches the 'not authorized' disjunct (no 'access denied' substring).
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue(
        "GetQueryExecution",
        _exec(
            state="FAILED",
            reason="User arn:...:role/x is not authorized to perform glue",
        ),
    )
    result = _run(call, sql="SELECT 1 FROM t")
    assert result["code"] == PERMISSION_DENIED


def test_failed_query_system_error_is_retriable():
    # AthenaError ErrorCategory 1 is a SYSTEM error -> retriable SERVICE_ERROR.
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue(
        "GetQueryExecution",
        _exec(state="FAILED", reason="internal error", category=1),
    )
    result = _run(call, sql="SELECT 1 FROM t")
    assert result["code"] == "SERVICE_ERROR"
    assert result["retriable"] is True


def test_failed_query_no_category_is_non_retriable_service_error():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue(
        "GetQueryExecution",
        _exec(state="FAILED", reason="something odd happened"),
    )
    result = _run(call, sql="SELECT 1 FROM t")
    assert result["code"] == "SERVICE_ERROR"
    assert result["retriable"] is False


# --------------------------------------------------------------- location edge cases


def test_enforced_workgroup_without_caller_output_adds_no_note():
    # Enforced config but no caller output_location -> no "ignored" note.
    call = ScriptedAthena()
    call.queue(
        "GetWorkGroup",
        _wg(output_location="s3://enforced/", enforced=True),
    )
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue("GetQueryResults", _results([["a"]]))
    result = _run(call, sql="SELECT 1 FROM t", workgroup="wg")
    assert result["ok"] is True
    assert not any("was ignored" in g for g in result["guidance"])
    start = dict(call.calls)["StartQueryExecution"]
    assert "ResultConfiguration" not in start


def test_unreadable_workgroup_without_output_uses_unknown_source():
    # Workgroup unreadable AND no caller output: proceed with an "unknown"
    # location source and let Athena surface any real "no location" error.
    call = ScriptedAthena()
    call.queue("GetWorkGroup", err_result("SERVICE_ERROR", "flaky"))
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue("GetQueryResults", _results([["a"]]))
    result = _run(call, sql="SELECT 1 FROM t", workgroup="wg")
    assert result["ok"] is True
    assert result["value"]["output_location_source"] == "unknown"
    start = dict(call.calls)["StartQueryExecution"]
    assert "ResultConfiguration" not in start


def test_database_is_sent_in_query_execution_context():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    call.queue("GetQueryResults", _results([["a"]]))
    result = _run(call, sql="SELECT 1 FROM t", workgroup="wg", database="mydb")
    assert result["ok"] is True
    start = dict(call.calls)["StartQueryExecution"]
    assert start["QueryExecutionContext"]["Database"] == "mydb"
    assert result["value"]["database"] == "mydb"


# --------------------------------------------------------------- misc result fields


def test_update_count_is_surfaced():
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec())
    body = ok_result(
        {
            "UpdateCount": 7,
            "ResultSet": {
                "ResultSetMetadata": {
                    "ColumnInfo": [{"Name": "c1", "Type": "varchar"}]
                },
                "Rows": [
                    {"Data": [{"VarCharValue": "c1"}]},
                    {"Data": [{"VarCharValue": "a"}]},
                ],
            },
        }
    )
    call.queue("GetQueryResults", body)
    result = _run(call, sql="SELECT c1 FROM t")
    assert result["value"]["update_count"] == 7


def test_non_dml_header_not_dropped_when_first_row_differs():
    # A non-DML result whose first row is NOT the column names keeps every row
    # (no header is stripped).
    call = ScriptedAthena()
    call.queue("GetWorkGroup", _wg())
    call.queue("StartQueryExecution", ok_result({"QueryExecutionId": "q1"}))
    call.queue("GetQueryExecution", _exec(stmt_type="UTILITY"))
    body = ok_result(
        {
            "ResultSet": {
                "ResultSetMetadata": {
                    "ColumnInfo": [{"Name": "col", "Type": "varchar"}]
                },
                "Rows": [
                    {"Data": [{"VarCharValue": "actual-data-row"}]},
                ],
            }
        }
    )
    call.queue("GetQueryResults", body)
    result = _run(call, sql="SHOW TABLES")
    assert result["value"]["header_row_dropped"] is False
    assert result["value"]["rows"] == [{"col": "actual-data-row"}]
