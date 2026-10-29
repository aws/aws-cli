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
"""``aws athena run-query`` -- run one Athena statement and return every row.

Callers otherwise hand-roll the Athena lifecycle:
``StartQueryExecution`` -> ``GetQueryExecution`` (poll) -> ``GetQueryResults``
(paginate). This command runs it once and returns the full, typed result set in
one call.

This command is mutative (read-write): it submits whatever SQL it is given --
SELECT/WITH/SHOW/DESCRIBE as well as INSERT, CREATE, DROP, MERGE, UNLOAD and
other DDL/write statements -- without inspecting or restricting the SQL. The
shared call bridge still refuses mutating *API operations* by name, but
``StartQueryExecution`` is allowed through, so a statement's effect on your data
is not constrained here; choose the workgroup and database with that in mind.

Procedure:

0. Validate the parameters (workgroup/catalog/database shape, S3 URI, row cap and
   polling parameters), all before any AWS call. The SQL itself is passed through
   verbatim and is neither inspected nor restricted.
1. ``athena:GetWorkGroup`` -- honour the workgroup's enforced output location and
   engine version. When no workgroup is given, auto-resolve one whose effective
   configuration actually has an output location.
2. ``athena:StartQueryExecution``.
3. ``athena:GetQueryExecution`` -- poll with backoff to SUCCEEDED, FAILED or
   CANCELLED, using the shared bounded poller.
4. ``athena:GetQueryResults`` -- paginate on NextToken, drop the header row, and
   return column types, ``DataScannedInBytes`` and an exact resume token if
   ``--max-rows`` truncates the result.
"""

from __future__ import annotations

import time
from typing import Any, Callable, NamedTuple

from awscli.customizations.commands import BasicCommand
from awscli.customizations.compositereadonly.helpers import (
    CONFLICT,
    CREDENTIALS_EXPIRED,
    INVALID_INPUT,
    NETWORK_ERROR,
    NOT_FOUND,
    NOT_READY,
    PERMISSION_DENIED,
    SERVICE_ERROR,
    THROTTLED,
    TIMEOUT,
    call,
    check_non_empty_str,
    check_positive_int,
    check_positive_number,
    create_read_client,
    emit_result,
    err_result,
    invalid_input,
    ok_result,
)
from awscli.customizations.compositereadonly.poll import drive_poll

_TERMINAL_STATES = frozenset({"SUCCEEDED", "FAILED", "CANCELLED"})
_INTEGER_TYPES = frozenset({"tinyint", "smallint", "integer", "int", "bigint"})
_MAX_PAGE_SIZE = 1000
_MAX_POLL_INTERVAL = 5.0
_MAX_POLLS = 10_000
_MAX_TRANSIENT_POLL_ERRORS = 5
_NOT_SUPPORTED_MSG = "queries of this type are not supported"

_VERBATIM_GUIDANCE = (
    "Cell values are verbatim Athena strings (timestamps such as "
    "'2024-01-15 00:00:00.000' and ids are untouched); print them exactly as "
    "returned, do not round, abbreviate or relabel them."
)
_NULL_GUIDANCE = "SQL NULL is returned as JSON null; render it explicitly as NULL in any report."


CallFn = Callable[[str, dict[str, Any]], dict[str, Any]]

# Bounded paging for workgroup enumeration so auto-resolution can never run away
# on an account with thousands of workgroups.
_MAX_WORKGROUP_PAGES = 10


def _workgroup_output(cfg: dict[str, Any]) -> tuple[str | None, bool]:
    """Return (effective_output_location, has_managed_results) for a WG config."""
    loc = (cfg.get("ResultConfiguration") or {}).get("OutputLocation")
    managed = bool(
        (cfg.get("ManagedQueryResultsConfiguration") or {}).get("Enabled")
    )
    return loc, managed


def resolve_workgroup_with_output(
    call_op: CallFn, requested: str | None
) -> dict[str, Any]:
    """Resolve a workgroup whose effective config can place query results.

    ``call_op(operation, params)`` is the read-only call bridge bound to an
    Athena client. When ``requested`` is given it is returned untouched (the
    caller's explicit choice always wins). When it is ``None`` we read
    ``primary`` first and, only if it has neither an output location nor managed
    results, enumerate other enabled workgroups (bounded) and pick the first that
    does -- reporting the choice in ``guidance``.

    The value is ``{"workgroup": name, "auto_resolved": bool,
    "output_location": loc, "managed_results": bool}``.
    """
    if requested:
        # Honour an explicit workgroup verbatim; its output location (or an
        # enforced one) is resolved later when the query runs.
        return ok_result(
            {
                "workgroup": requested,
                "auto_resolved": False,
                "output_location": None,
                "managed_results": False,
            }
        )

    guidance: list[str] = []
    primary = call_op("GetWorkGroup", {"WorkGroup": "primary"})
    if primary["ok"]:
        cfg = ((primary.get("value") or {}).get("WorkGroup") or {}).get(
            "Configuration"
        ) or {}
        loc, managed = _workgroup_output(cfg)
        if loc or managed:
            return ok_result(
                {
                    "workgroup": "primary",
                    "auto_resolved": False,
                    "output_location": loc,
                    "managed_results": managed,
                }
            )

    # 'primary' cannot place results (or could not be read); look for a workgroup
    # that can. Enumerate enabled workgroups and read each effective config.
    token: str | None = None
    for _ in range(_MAX_WORKGROUP_PAGES):
        params: dict[str, Any] = {}
        if token:
            params["NextToken"] = token
        listing = call_op("ListWorkGroups", params)
        if not listing["ok"]:
            # Fall back to 'primary'; the query step will surface a precise
            # "no output location" error if it truly has none.
            guidance.append(
                "Could not list workgroups to auto-resolve an output location; "
                "falling back to 'primary'. Pass --workgroup or --output-location."
            )
            return ok_result(
                {
                    "workgroup": "primary",
                    "auto_resolved": False,
                    "output_location": None,
                    "managed_results": False,
                },
                guidance=guidance,
            )
        summaries = (listing.get("value") or {}).get("WorkGroups") or []
        for summ in summaries:
            name = summ.get("Name")
            if not name or summ.get("State") == "DISABLED":
                continue
            wg = call_op("GetWorkGroup", {"WorkGroup": name})
            if not wg["ok"]:
                continue
            cfg = ((wg.get("value") or {}).get("WorkGroup") or {}).get(
                "Configuration"
            ) or {}
            loc, managed = _workgroup_output(cfg)
            if loc or managed:
                guidance.append(
                    f"No --workgroup given and 'primary' has no result output "
                    f"location; auto-selected workgroup {name!r} "
                    f"({'managed results' if managed and not loc else loc})."
                )
                return ok_result(
                    {
                        "workgroup": name,
                        "auto_resolved": True,
                        "output_location": loc,
                        "managed_results": managed,
                    },
                    guidance=guidance,
                )
        token = (listing.get("value") or {}).get("NextToken")
        if not token:
            break

    # Nothing better than 'primary' was found; return it and let the query step
    # emit the precise "no output location" error if applicable.
    guidance.append(
        "No workgroup with a result output location was found; using 'primary'. "
        "Pass --output-location='s3://<bucket>/<prefix>/' to run the query."
    )
    return ok_result(
        {
            "workgroup": "primary",
            "auto_resolved": False,
            "output_location": None,
            "managed_results": False,
        },
        guidance=guidance,
    )


def _validate_params(
    sql: Any,
    workgroup: Any,
    database: Any,
    catalog: Any,
    output_location: Any,
    max_rows: Any,
    poll_interval: Any,
    max_wait: Any,
) -> dict[str, Any] | None:
    # sql is required and must never be empty; catch it client-side so an empty
    # statement is a ParamValidation error (exit 252) rather than slipping
    # through to a SERVICE_ERROR from Athena (exit 255).
    err = check_non_empty_str("sql", sql, required=True)
    if err is not None:
        return invalid_input(
            err,
            ["Pass --sql with a non-empty SQL statement."],
        )
    # workgroup may be None here (auto-resolved later); only reject an explicit
    # empty string.
    err = check_non_empty_str("workgroup", workgroup, required=False)
    if err is not None:
        return invalid_input(
            err,
            ["Pass --workgroup <name> or omit it to auto-resolve one."],
        )
    err = check_non_empty_str("catalog", catalog, required=True)
    if err is not None:
        return invalid_input(
            err,
            ["Pass --catalog AwsDataCatalog unless the task names another."],
        )
    err = check_non_empty_str("database", database, required=False)
    if err is not None:
        return invalid_input(
            err,
            ["Omit --database or pass the Glue database name."],
        )
    if output_location is not None and (
        not isinstance(output_location, str)
        or not output_location.startswith("s3://")
        or len(output_location) <= 5
    ):
        return invalid_input(
            f"output_location {output_location!r} is not an s3:// URI.",
            [
                "Pass --output-location s3://<bucket>/<prefix>/ or omit it to use "
                "the workgroup's location."
            ],
        )
    err = check_positive_int("max_rows", max_rows)
    if err is not None:
        return invalid_input(
            err,
            ["Pass e.g. --max-rows 10000."],
        )
    for name, val in (
        ("poll_interval", poll_interval),
        ("max_wait", max_wait),
    ):
        err = check_positive_number(name, val)
        if err is not None:
            return invalid_input(
                err,
                [f"Pass a positive {name}."],
            )
    return None


def _read_workgroup(
    call_op, workgroup: str
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    info: dict[str, Any] = {
        "read": False,
        "output_location": None,
        "enforced": False,
        "managed_results": False,
        "engine_version": None,
        "state": None,
        "note": None,
    }
    res = call_op("GetWorkGroup", {"WorkGroup": workgroup})
    if res["ok"]:
        wg = (res.get("value") or {}).get("WorkGroup") or {}
        cfg = wg.get("Configuration") or {}
        info["read"] = True
        info["state"] = wg.get("State")
        info["output_location"] = (cfg.get("ResultConfiguration") or {}).get(
            "OutputLocation"
        )
        info["enforced"] = bool(cfg.get("EnforceWorkGroupConfiguration"))
        info["managed_results"] = bool(
            (cfg.get("ManagedQueryResultsConfiguration") or {}).get("Enabled")
        )
        ev = cfg.get("EngineVersion") or {}
        info["engine_version"] = ev.get("EffectiveEngineVersion") or ev.get(
            "SelectedEngineVersion"
        )
        if info["state"] == "DISABLED":
            return (
                err_result(
                    NOT_READY,
                    f"Workgroup '{workgroup}' is DISABLED; queries cannot run in it.",
                    key=workgroup,
                    guidance=[
                        "Use another workgroup (athena:ListWorkGroups) or ask an admin to enable it."
                    ],
                ),
                info,
            )
        return None, info
    err = res.get("error") or ""
    low = err.lower()
    if res.get("code") == NOT_FOUND or (
        "not found" in low and "workgroup" in low
    ):
        return (
            err_result(
                NOT_FOUND,
                f"Workgroup '{workgroup}' not found: {err}",
                aws_code=res.get("aws_code"),
                key=workgroup,
                guidance=[
                    "List workgroups with athena:ListWorkGroups, or use the workgroup named by the task."
                ],
            ),
            info,
        )
    if res.get("code") == CREDENTIALS_EXPIRED:
        return (
            err_result(
                CREDENTIALS_EXPIRED,
                err,
                aws_code=res.get("aws_code"),
                retriable=True,
                guidance=[
                    "Credentials may have expired; refresh them and retry."
                ],
            ),
            info,
        )
    info["note"] = (
        f"Could not read workgroup '{workgroup}' ({res.get('code')}: {err}); proceeding without its "
        "enforced output location / engine version."
    )
    return None, info


def _coerce(value: str | None, col_type: str | None) -> Any:
    if value is None:
        return None
    t = (col_type or "").lower()
    if t in _INTEGER_TYPES:
        try:
            return int(value)
        except ValueError:
            return value
    if t == "boolean" and value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


def _row_keys(columns: list[dict[str, Any]]) -> tuple[list[str], bool]:
    keys: list[str] = []
    seen: dict[str, int] = {}
    renamed = False
    for idx, col in enumerate(columns):
        base = col.get("label") or col.get("name") or f"_col{idx}"
        count = seen.get(base, 0) + 1
        seen[base] = count
        if count > 1:
            renamed = True
            keys.append(f"{base}_{count}")
        else:
            keys.append(base)
    return keys, renamed


def _stats(qe: dict[str, Any]) -> dict[str, Any]:
    st = qe.get("Statistics") or {}
    return {
        "data_scanned_bytes": st.get("DataScannedInBytes"),
        "engine_execution_time_ms": st.get("EngineExecutionTimeInMillis"),
        "total_execution_time_ms": st.get("TotalExecutionTimeInMillis"),
        "queue_time_ms": st.get("QueryQueueTimeInMillis"),
    }


def _failure_code(qe: dict[str, Any], reason: str) -> tuple[str, bool]:
    """Best-effort mapping of an Athena query failure to an error code.

    Athena reports a query-level failure as a status of ``FAILED`` plus a
    free-text ``StateChangeReason``; the API exposes no structured,
    machine-readable error codes for query-level failures. The checks below
    therefore string-match that reason (and the optional ``AthenaError``
    category, when present) to hand the caller an actionable error code. This
    matching is deliberately best-effort: if Athena changes its error-message
    wording, an unmatched reason falls back to ``SERVICE_ERROR``.

    Returns a ``(code, retriable)`` tuple.
    """
    low = reason.lower()
    if _NOT_SUPPORTED_MSG in low:
        return INVALID_INPUT, False
    if (
        "access denied" in low
        or "not authorized" in low
        or "accessdenied" in low
    ):
        return PERMISSION_DENIED, False
    athena_error = (qe.get("Status") or {}).get("AthenaError") or {}
    category = athena_error.get("ErrorCategory")
    if category == 2:  # USER error: bad SQL, missing column/table
        return INVALID_INPUT, False
    if category == 1:  # SYSTEM error: retriable
        return SERVICE_ERROR, True
    return SERVICE_ERROR, False


class _ResolvedLocation(NamedTuple):
    """Where a query's results are written, plus how that was decided.

    ``error`` is a pre-dispatch failure result (or ``None`` to proceed);
    ``location`` is the effective S3 output location (``None`` for managed
    results, or when the workgroup places results itself); ``source`` says where
    the location came from ('caller', 'workgroup_enforced', 'workgroup_default',
    'workgroup_managed', 'unknown'); ``send_location`` is True only when the
    caller's ``ResultConfiguration`` override should be sent on
    StartQueryExecution. The field order matches the historical 4-tuple, so
    index-unpacking call sites keep working unchanged.
    """

    error: dict[str, Any] | None
    location: str | None
    source: str
    send_location: bool


def _resolve_location(
    wg: dict[str, Any],
    workgroup: str,
    output_location: str | None,
    notes: list[str],
) -> _ResolvedLocation:
    """Resolve the effective result location (see :class:`_ResolvedLocation`)."""
    if wg["enforced"]:
        loc = wg["output_location"]
        source = (
            "workgroup_managed"
            if (wg["managed_results"] and not loc)
            else "workgroup_enforced"
        )
        if output_location and output_location != loc:
            notes.append(
                f"Workgroup '{workgroup}' enforces its configuration; output_location "
                f"{output_location!r} was ignored and results go to {loc or 'managed query results'}."
            )
        return _ResolvedLocation(None, loc, source, False)
    if output_location:
        return _ResolvedLocation(None, output_location, "caller", True)
    if wg["output_location"]:
        return _ResolvedLocation(
            None, wg["output_location"], "workgroup_default", False
        )
    if wg["managed_results"]:
        return _ResolvedLocation(None, None, "workgroup_managed", False)
    if wg["read"]:
        return _ResolvedLocation(
            invalid_input(
                f"Workgroup '{workgroup}' has no result output location and none was passed.",
                [
                    "Pass --output-location s3://<athena-results-bucket>/<prefix>/ (a bucket the role can write to)."
                ],
                value={"workgroup": workgroup},
            ),
            None,
            "",
            False,
        )
    return _ResolvedLocation(None, None, "unknown", False)


def _start_failure(start: dict[str, Any]) -> dict[str, Any]:
    err = start.get("error") or ""
    if _NOT_SUPPORTED_MSG in err.lower():
        return err_result(
            INVALID_INPUT,
            f"Athena rejected the statement: {err}. Usual causes: more than one statement, an "
            "unsupported statement type (USE/SET/transactions/GRANT), or DDL for a table "
            "format/catalog that does not support it.",
            aws_code=start.get("aws_code"),
            guidance=[
                "Send exactly one SELECT/WITH/SHOW/DESCRIBE statement per call.",
                "Pass --database/--catalog instead of USE; drop SET/BEGIN/COMMIT.",
                "For DDL, check the target catalog/table format supports the operation in this engine version.",
            ],
        )
    by_code = {
        CREDENTIALS_EXPIRED: [
            "Credentials may have expired; refresh them and retry."
        ],
        PERMISSION_DENIED: [
            "The role lacks athena:StartQueryExecution on this workgroup, or the glue/s3 access it "
            "needs; use the role named by the task or another workgroup."
        ],
        THROTTLED: [
            "Athena throttled StartQueryExecution; wait a few seconds and run again."
        ],
    }
    code = start.get("code") or SERVICE_ERROR
    guidance = by_code.get(
        code, [f"StartQueryExecution failed ({code}); fix and retry."]
    )
    return err_result(
        code,
        err,
        aws_code=start.get("aws_code"),
        retriable=bool(start.get("retriable"))
        or code in (THROTTLED, CREDENTIALS_EXPIRED),
        guidance=guidance,
    )


def run_athena_query(
    call_op,
    sql: str,
    *,
    workgroup: str | None = None,
    database: str | None = None,
    catalog: str = "AwsDataCatalog",
    output_location: str | None = None,
    max_rows: int = 10_000,
    coerce_types: bool = True,
    poll_interval: float = 1.0,
    max_wait: float = 300.0,
    cancel_on_timeout: bool = False,
    sleep=None,
    clock=None,
) -> dict[str, Any]:
    """Run one Athena SQL statement to a terminal state and return all rows.

    ``call_op(operation, params)`` is the read-only call bridge bound to an
    Athena client. Returns the plain-dict result convention; never raises. When
    ``workgroup`` is ``None`` a workgroup with an output location is auto-resolved.
    """
    sleep = time.sleep if sleep is None else sleep
    clock = time.monotonic if clock is None else clock
    try:
        bad = _validate_params(
            sql,
            workgroup,
            database,
            catalog,
            output_location,
            max_rows,
            poll_interval,
            max_wait,
        )
        if bad is not None:
            return bad
        # The SQL is submitted verbatim; run-query no longer inspects or
        # restricts it (see the module docstring -- this command is mutative).
        statement = sql
        resolve_guidance: list[str] = []
        if not workgroup:
            resolved = resolve_workgroup_with_output(call_op, None)
            # resolve never fails hard; it always yields a workgroup to try.
            workgroup = (resolved.get("value") or {}).get(
                "workgroup", "primary"
            )
            resolve_guidance = resolved.get("guidance") or []
        return _run(
            call_op,
            statement,
            workgroup=workgroup,
            database=database,
            catalog=catalog,
            output_location=output_location,
            max_rows=max_rows,
            coerce_types=coerce_types,
            poll_interval=float(poll_interval),
            max_wait=float(max_wait),
            cancel_on_timeout=cancel_on_timeout,
            sleep=sleep,
            clock=clock,
            extra_guidance=resolve_guidance,
        )
    except Exception as exc:  # noqa: BLE001 - the command contract is "never raises"
        return err_result(
            SERVICE_ERROR,
            f"run-query internal error: {exc!r}",
            guidance=[
                "Unexpected response shape; retry once, then fall back to athena:GetQueryExecution by hand."
            ],
        )


def _start_query(
    call_op, params: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    """StartQueryExecution; return ``(error_result_or_None, query_execution_id)``.

    ``params`` is the fully-built StartQueryExecution request (QueryString,
    WorkGroup, QueryExecutionContext and an optional ResultConfiguration). Never
    raises: a failed start, or a start that returns no QueryExecutionId, comes
    back as an error result in the first slot (and ``None`` id); a successful
    start returns ``(None, qid)``.
    """
    start = call_op("StartQueryExecution", params)
    if not start["ok"]:
        return _start_failure(start), None
    qid = (start.get("value") or {}).get("QueryExecutionId")
    if not qid:
        return (
            err_result(
                SERVICE_ERROR,
                "StartQueryExecution returned no QueryExecutionId.",
                guidance=[
                    "Retry the call; if it persists, check the workgroup in the Athena console."
                ],
            ),
            None,
        )
    return None, qid


def _fetch_results(
    call_op,
    qid: str,
    *,
    max_rows: int,
    coerce_types: bool,
    expect_header: bool,
    base: dict[str, Any],
    effective_location: str | None,
    notes: list[str],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Paginate GetQueryResults for ``qid``; return ``(error_or_None, data)``.

    Follows NextToken, drops the header row, coerces integer/boolean cells (when
    ``coerce_types``) and stops at ``max_rows``. On a page failure it returns an
    ``err_result`` (carrying the rows already gathered and a resume token) as the
    first element and an empty ``data``; on success the first element is ``None``
    and ``data`` holds the decoded ``columns``/``rows``/``header_row_dropped``/
    ``pages_fetched``/``is_truncated``/``next_token``/``update_count`` fields the
    orchestrator folds into the final result. ``notes`` is appended to in place
    (duplicate-column and repeated-token notes).
    """
    columns: list[dict[str, Any]] | None = None
    keys: list[str] = []
    rows: list[dict[str, Any]] = []
    header_dropped = False
    pages = 0
    token: str | None = None
    update_count: int | None = None
    seen_tokens: set[str] = set()
    while True:
        remaining = max_rows - len(rows)
        page_size = min(
            _MAX_PAGE_SIZE,
            remaining + (1 if pages == 0 and expect_header else 0),
        )
        rparams: dict[str, Any] = {
            "QueryExecutionId": qid,
            "MaxResults": page_size,
        }
        if token:
            rparams["NextToken"] = token
        res = call_op("GetQueryResults", rparams)
        if not res["ok"]:
            err = err_result(
                res.get("code") or SERVICE_ERROR,
                f"GetQueryResults failed after {pages} page(s) for query {qid}: {res.get('error')}",
                aws_code=res.get("aws_code"),
                retriable=bool(res.get("retriable")),
                key=qid,
                is_exhaustive=False,
                value={
                    **base,
                    "columns": columns or [],
                    "rows": rows,
                    "row_count": len(rows),
                    "pages_fetched": pages,
                    "next_token": token,
                    "is_truncated": True,
                },
                guidance=[
                    f"Resume with athena:GetQueryResults QueryExecutionId={qid} NextToken={token!r}, or "
                    f"read the CSV at {effective_location}."
                ],
            )
            return err, {}
        pages += 1
        body = res.get("value") or {}
        if update_count is None and body.get("UpdateCount") is not None:
            update_count = body.get("UpdateCount")
        rs = body.get("ResultSet") or {}
        if columns is None:
            columns = [
                {
                    "name": c.get("Name"),
                    "label": c.get("Label") or c.get("Name"),
                    "type": c.get("Type"),
                    "nullable": c.get("Nullable"),
                    "precision": c.get("Precision"),
                    "scale": c.get("Scale"),
                }
                for c in (rs.get("ResultSetMetadata") or {}).get("ColumnInfo")
                or []
            ]
            keys, renamed = _row_keys(columns)
            if renamed:
                notes.append(
                    "Duplicate column labels were suffixed (_2, _3, ...) in row keys; alias them in SQL."
                )
        raw_rows = rs.get("Rows") or []
        if pages == 1 and raw_rows:
            first = [
                d.get("VarCharValue") for d in raw_rows[0].get("Data") or []
            ]
            labels = [c["label"] for c in columns]
            names = [c["name"] for c in columns]
            if expect_header or (
                columns and (first == labels or first == names)
            ):
                raw_rows = raw_rows[1:]
                header_dropped = True
        for raw in raw_rows:
            if len(rows) >= max_rows:
                break
            cells = [d.get("VarCharValue") for d in raw.get("Data") or []]
            cells += [None] * (len(keys) - len(cells))
            rows.append(
                {
                    k: (_coerce(v, columns[i]["type"]) if coerce_types else v)
                    for i, (k, v) in enumerate(zip(keys, cells))
                }
            )
        token = body.get("NextToken")
        if not token:
            break
        if token in seen_tokens:
            notes.append(
                "GetQueryResults repeated a NextToken; pagination stopped to avoid a loop."
            )
            token = None
            break
        seen_tokens.add(token)
        if len(rows) >= max_rows:
            break

    truncated = bool(token)
    return None, {
        "columns": columns or [],
        "rows": rows,
        "header_row_dropped": header_dropped,
        "pages_fetched": pages,
        "is_truncated": truncated,
        "next_token": token,
        "update_count": update_count,
    }


def _run(
    call_op,
    statement: str,
    *,
    workgroup: str,
    database: str | None,
    catalog: str,
    output_location: str | None,
    max_rows: int,
    coerce_types: bool,
    poll_interval: float,
    max_wait: float,
    cancel_on_timeout: bool,
    sleep,
    clock,
    extra_guidance: list[str],
) -> dict[str, Any]:
    notes: list[str] = list(extra_guidance)

    # 1. Workgroup.
    wg_err, wg = _read_workgroup(call_op, workgroup)
    if wg_err is not None:
        return wg_err
    if wg["note"]:
        notes.append(wg["note"])
    resolved = _resolve_location(wg, workgroup, output_location, notes)
    if resolved.error is not None:
        return resolved.error
    effective_location = resolved.location
    source = resolved.source
    send_location = resolved.send_location

    # 2. Start.
    ctx: dict[str, str] = {"Catalog": catalog}
    if database:
        ctx["Database"] = database
    params: dict[str, Any] = {
        "QueryString": statement,
        "WorkGroup": workgroup,
        "QueryExecutionContext": ctx,
    }
    if send_location and effective_location:
        params["ResultConfiguration"] = {"OutputLocation": effective_location}
    start_err, qid = _start_query(call_op, params)
    if start_err is not None:
        return start_err

    base: dict[str, Any] = {
        "query_execution_id": qid,
        "workgroup": workgroup,
        "database": database,
        "catalog": catalog,
        "engine_version": wg["engine_version"],
        "output_location": effective_location,
        "output_location_source": source,
        "submitted_sql": statement,
    }

    # 3. Poll to a terminal state using the shared bounded poller.
    qe: dict[str, Any] = {}
    state = "QUEUED"

    def _terminal(res: dict[str, Any]) -> str | None:
        nonlocal qe, state
        qe = (res.get("value") or {}).get("QueryExecution") or {}
        # State persists across polls (defaults to the last observed value).
        state = (qe.get("Status") or {}).get("State") or state
        return state if state in _TERMINAL_STATES else None

    def _is_retriable(res: dict[str, Any]) -> bool:
        return bool(res.get("retriable")) or res.get("code") in (
            THROTTLED,
            NETWORK_ERROR,
        )

    cancelled = False

    def _on_timeout() -> None:
        nonlocal cancelled
        if cancel_on_timeout:
            # StopQueryExecution cancels a running query (read-only w.r.t.
            # your data; it does not create or modify resources).
            stop = call_op("StopQueryExecution", {"QueryExecutionId": qid})
            cancelled = stop["ok"]

    poll_result = drive_poll(
        call_op,
        "GetQueryExecution",
        {"QueryExecutionId": qid},
        terminal=_terminal,
        is_retriable=_is_retriable,
        on_timeout=_on_timeout,
        interval=poll_interval,
        max_wait=max_wait,
        max_polls=_MAX_POLLS,
        max_transient=_MAX_TRANSIENT_POLL_ERRORS,
        clock=clock,
        sleep=sleep,
        key=qid,
    )
    polls = poll_result.get("polls_count", 0)

    if not poll_result["ok"]:
        if poll_result.get("code") == TIMEOUT:
            if cancelled:
                guidance = [
                    f"Query {qid} was cancelled after {max_wait:g}s (--cancel-on-timeout); narrow the "
                    "query (partition/time predicates) and run again."
                ]
            else:
                guidance = [
                    f"Query {qid} is still {state}; call athena:GetQueryExecution later or re-run with a "
                    "larger --max-wait. Do not re-submit the same SQL (it would be billed twice)."
                ]
            return err_result(
                TIMEOUT,
                f"Query {qid} did not finish within {max_wait:g}s (last state {state}).",
                retriable=not cancelled,
                key=qid,
                value={
                    **base,
                    "state": "CANCELLED" if cancelled else state,
                    "polls": polls,
                    "cancelled": cancelled,
                    **_stats(qe),
                },
                guidance=guidance,
            )
        return err_result(
            poll_result.get("code") or SERVICE_ERROR,
            poll_result.get("error") or "GetQueryExecution failed.",
            aws_code=poll_result.get("aws_code"),
            retriable=bool(poll_result.get("retriable")),
            key=qid,
            value={**base, "state": state, "polls": polls},
            guidance=[
                f"Query {qid} was started; poll athena:GetQueryExecution for it later instead of "
                "starting a new one."
            ],
        )

    stmt_type = qe.get("StatementType")
    effective_location = (qe.get("ResultConfiguration") or {}).get(
        "OutputLocation"
    ) or effective_location
    base["output_location"] = effective_location
    base["engine_version"] = (qe.get("EngineVersion") or {}).get(
        "EffectiveEngineVersion"
    ) or base["engine_version"]
    base.update(
        {
            "state": state,
            "statement_type": stmt_type,
            "polls": polls,
            **_stats(qe),
        }
    )

    if state == "FAILED":
        reason = (qe.get("Status") or {}).get(
            "StateChangeReason"
        ) or "no StateChangeReason returned"
        code, retriable = _failure_code(qe, reason)
        return err_result(
            code,
            f"Athena query {qid} FAILED: {reason}",
            retriable=retriable,
            key=qid,
            aws_code="QueryFailed",
            value={**base, "state_change_reason": reason},
            guidance=[
                f"Fix the cause named in StateChangeReason: {reason}",
                "Use DESCRIBE <table> / SHOW COLUMNS to check column and table names before re-running.",
            ],
        )
    if state == "CANCELLED":
        reason = (qe.get("Status") or {}).get(
            "StateChangeReason"
        ) or "cancelled"
        return err_result(
            CONFLICT,
            f"Athena query {qid} was CANCELLED: {reason}",
            key=qid,
            value={**base, "state_change_reason": reason},
            guidance=[
                "The query was cancelled (by a user or the workgroup's BytesScannedCutoffPerQuery); "
                "narrow it with partition predicates and run again."
            ],
        )

    # 4. Paginate results.
    fetch_err, data = _fetch_results(
        call_op,
        qid,
        max_rows=max_rows,
        coerce_types=coerce_types,
        expect_header=stmt_type == "DML",
        base=base,
        effective_location=effective_location,
        notes=notes,
    )
    if fetch_err is not None:
        return fetch_err

    truncated = data["is_truncated"]
    token = data["next_token"]
    guidance = [_VERBATIM_GUIDANCE, _NULL_GUIDANCE, *notes]
    if truncated:
        guidance.insert(
            0,
            (
                f"Result truncated at max_rows={max_rows}; more rows exist. Re-run with a larger "
                f"--max-rows, add a tighter WHERE, or resume with athena:GetQueryResults "
                f"QueryExecutionId={qid} NextToken={token!r}."
            ),
        )
    value = {
        **base,
        "columns": data["columns"],
        "rows": data["rows"],
        "row_count": len(data["rows"]),
        "header_row_dropped": data["header_row_dropped"],
        "pages_fetched": data["pages_fetched"],
        "is_truncated": truncated,
        "next_token": token if truncated else None,
        "max_rows": max_rows,
        "update_count": data["update_count"],
        "null_representation": "SQL NULL -> JSON null (render as NULL)",
    }
    return ok_result(
        value, key=qid, is_exhaustive=not truncated, guidance=guidance
    )


class RunQueryCommand(BasicCommand):
    NAME = "run-query"
    DESCRIPTION = (
        "Run a single Athena statement to completion and return every row in one "
        "call.\n\n"
        "Use this command when you need to run an Athena SQL query and get the "
        "results in one step, without managing the poll-and-paginate lifecycle "
        "yourself. It handles query submission, polling for completion, result "
        "pagination, and output formatting.\n\n"
        "Submits the query, polls it to a terminal state, and paginates all "
        "result pages. The SQL is passed through verbatim and is not restricted, "
        "so this command is mutative (read-write): writes and DDL (INSERT, "
        "CREATE, DROP, MERGE, UNLOAD, ...) run against real tables. When no "
        "--workgroup is given, a workgroup with a result output location is "
        "auto-resolved."
    )
    EXAMPLES = (
        "To run a query in the default workgroup::\n\n"
        "  aws athena run-query --sql \"SELECT * FROM mydb.mytable LIMIT 100\"\n\n"
        "To target a workgroup and database with a row cap::\n\n"
        "  aws athena run-query --sql \"SELECT count(*) FROM logs\" "
        "--workgroup analytics --database mydb --max-rows 1\n"
    )
    ARG_TABLE = [
        {
            "name": "sql",
            "required": True,
            "help_text": "The SQL statement to run (submitted verbatim; may be a write/DDL statement).",
            "cli_type_name": "string",
        },
        {
            "name": "workgroup",
            "help_text": "Athena workgroup. Omit to auto-resolve one with an output location.",
            "cli_type_name": "string",
        },
        {
            "name": "database",
            "help_text": "Glue database for unqualified names.",
            "cli_type_name": "string",
        },
        {
            "name": "catalog",
            "default": "AwsDataCatalog",
            "help_text": "Data catalog (default AwsDataCatalog).",
            "cli_type_name": "string",
        },
        {
            "name": "output-location",
            "help_text": "s3:// URI for results; overrides the workgroup default unless enforced.",
            "cli_type_name": "string",
        },
        {
            "name": "max-rows",
            "default": 10000,
            "cli_type_name": "integer",
            "help_text": "Maximum rows to return (default 10000).",
        },
        {
            "name": "poll-interval",
            "default": 1.0,
            "cli_type_name": "double",
            "help_text": "Initial seconds between GetQueryExecution polls (default 1.0).",
        },
        {
            "name": "max-wait",
            "default": 300.0,
            "cli_type_name": "double",
            "help_text": "Maximum seconds to wait for the query (default 300).",
        },
        {
            "name": "cancel-on-timeout",
            "action": "store_true",
            "default": False,
            "help_text": "Cancel the query (StopQueryExecution) if --max-wait is exceeded.",
        },
        {
            "name": "no-coerce-types",
            "action": "store_true",
            "default": False,
            "help_text": "Return all cells as strings instead of coercing integer/boolean columns.",
        },
    ]

    def __init__(
        self,
        session,
        client=None,
        stdout=None,
        stderr=None,
        sleep=None,
        clock=None,
    ):
        super().__init__(session)
        self._client = client
        self._stdout = stdout
        self._stderr = stderr
        self._sleep = sleep
        self._clock = clock

    def _run_main(self, parsed_args, parsed_globals):
        client = self._client or create_read_client(
            self._session, "athena", parsed_globals
        )

        def call_op(operation, params):
            return call(client, operation, params)

        result = run_athena_query(
            call_op,
            parsed_args.sql,
            workgroup=parsed_args.workgroup,
            database=parsed_args.database,
            catalog=parsed_args.catalog,
            output_location=parsed_args.output_location,
            max_rows=parsed_args.max_rows,
            coerce_types=not parsed_args.no_coerce_types,
            poll_interval=parsed_args.poll_interval,
            max_wait=parsed_args.max_wait,
            cancel_on_timeout=parsed_args.cancel_on_timeout,
            sleep=self._sleep,
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
