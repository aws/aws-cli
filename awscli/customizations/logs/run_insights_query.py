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
"""``aws logs run-insights-query`` -- run one Logs Insights query to completion.

Callers otherwise write their own ``start-query`` -> ``get-query-results`` polling
loops and get recurring things wrong: a blank ``queryId`` passed to
``get-query-results`` after a failed start, a window that falls outside a group's
retention, loops that stop on a partial window or the 100,000-row cap (so counts
come out low), and missed log groups from a guessed name or prefix.

Procedure (one call, read-only):

1. ``logs:ListLogGroups`` (all pages) resolves each input as an exact name, a
   prefix (trailing ``*`` or when no exact name exists) or a substring, using the
   server-side ``logGroupNamePattern`` match (no client-side, case-sensitive
   prefix comparison). ``logs:DescribeLogGroups`` is then called with
   ``logGroupIdentifiers`` (batches of 50) to fetch each matched group's
   retention -- the one API that reliably returns ``retentionInDays``. An input
   that is a log-group ARN is preserved as-is (only a trailing ``:*`` is stripped,
   which ``StartQuery`` rejects) and queried through ``logGroupIdentifiers`` so
   cross-account/cross-region ARNs are never rewritten to a same-named local
   group. The window is bounded to the queryable range: end to now, start to the
   earliest **retention** edge. Groups with no data in the window are skipped and
   reported. Alternatively a query may begin with a ``SOURCE`` command and select
   its own log groups; then ``--log-group-names`` is omitted and resolution,
   retention bounding and 50-group batching are all skipped.
2. The query string is validated locally before dispatch. On a server
   ``MalformedQueryException`` the parser line/position and offending token are
   returned.
3. ``logs:StartQuery`` (batches of at most 50 groups, retrying on throttling);
   the ``queryId`` is checked non-blank; ``logs:GetQueryResults`` is polled with
   the shared bounded poller. On the poll cap ``logs:StopQuery`` is called.
4. For a non-aggregate query that hits the row cap, the window is split in half,
   each half re-run, and results merged, de-duplicating on ``@ptr``. Any cap hit
   is reported through ``is_exhaustive=False`` and ``partial_reasons``.

Notes on retention and output size: the queryable-start bound uses retention
only -- a log group's *creation time* does not bound a Logs Insights query, so it
is intentionally NOT used to bound the window. The default row output is small
(``--max-rows`` ~50) and each ``@message`` is truncated to a bounded width
(``--max-message-length``); both bounds are reported so nothing is lost silently.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from awscli.customizations.commands import BasicCommand
from awscli.customizations.compositereadonly.helpers import (
    CONFLICT,
    CREDENTIALS_EXPIRED,
    INVALID_INPUT,
    NOT_FOUND,
    PERMISSION_DENIED,
    QUOTA_EXCEEDED,
    SERVICE_ERROR,
    THROTTLED,
    TIMEOUT,
    VALIDATION_ERROR,
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
from awscli.customizations.compositereadonly.output import (
    DEFAULT_MESSAGE_MAX_CHARS,
    truncate_field,
)
from awscli.customizations.compositereadonly.poll import drive_poll

_ROW_CAP = 100_000
_MAX_GROUPS_PER_QUERY = 50
_MAX_IDENTIFIERS_PER_DESCRIBE = 50
_MAX_QUERY_CHARS = 10_000
_DESCRIBE_PAGE_CAP = 100
_START_RETRIES = 5
_THROTTLE_RETRIES = 5
_DAY_MS = 86_400_000

_TERMINAL = frozenset(
    {"Complete", "Failed", "Cancelled", "Timeout", "Unknown"}
)
_KNOWN_COMMANDS = frozenset(
    {
        "fields",
        "display",
        "filter",
        "filterindex",
        "stats",
        "sort",
        "limit",
        "parse",
        "dedup",
        "unmask",
        "pattern",
        "diff",
        "anomaly",
        "unnest",
        "lookup",
        "source",
    }
)
_AGGREGATE_COMMANDS = frozenset({"stats", "pattern", "diff", "anomaly"})
# Aggregate functions whose per-key results CANNOT be correctly merged by
# concatenating per-batch rows (unlike additive count/sum/min/max). A query
# using any of these over >50 log groups (which forces batching) is flagged.
_NON_ADDITIVE = frozenset(
    {"avg", "pct", "percentile", "percentile_approx", "count_distinct"}
)
_GROUP_NAME_RE = re.compile(r"^[\.\-_/#A-Za-z0-9]+$")
_ARN_RE = re.compile(
    r"^arn:aws[\w-]*:logs:[^:]*:\d*:log-group:([^:]+)(?::\*)?$"
)
_LINE_POS_RE = re.compile(
    r"line\s+(\d+)\s*(?:and|,)?\s*position\s+(\d+)", re.IGNORECASE
)
_POS_RE = re.compile(r"position\s+(\d+)", re.IGNORECASE)
_THROTTLE_CODES = frozenset(
    {
        "LimitExceededException",
        "ThrottlingException",
        "ServiceUnavailableException",
        "TooManyRequestsException",
    }
)
_EXPIRED_CODES = frozenset(
    {"ExpiredTokenException", "ExpiredToken", "RequestExpired"}
)
# A relative duration like 30m / 1h / 24h / 7d / 2w (units m/h/d/w), used by
# --since and by the ``now-<duration>`` syntax accepted in start/end times.
_DURATION_RE = re.compile(r"^(\d+)\s*([mhdw])$", re.IGNORECASE)
_DURATION_SECONDS = {"m": 60, "h": 3_600, "d": 86_400, "w": 604_800}
# Commands an Essentials-class (INFREQUENT_ACCESS) log group does not support;
# if the query uses one and any resolved group is Essentials, warn up front.
_ESSENTIALS_UNSUPPORTED = frozenset({"pattern", "diff", "anomaly", "unmask"})


# --------------------------------------------------------------------------- small helpers


def _iso(epoch_seconds: int) -> str:
    return (
        datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _iso_ms(epoch_ms: int) -> str:
    return (
        datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _ceil_s(ms: int) -> int:
    return -(-ms // 1000)


def _parse_duration(
    value: Any, name: str
) -> tuple[timedelta | None, str | None]:
    """Parse a relative duration like ``30m``/``1h``/``24h``/``7d``/``2w``.

    Units are minutes (m), hours (h), days (d) and weeks (w), case-insensitive.
    Returns ``(timedelta, None)`` on success or ``(None, error)`` otherwise.
    """
    if not isinstance(value, str) or not value.strip():
        return (
            None,
            f"{name} is required as a duration, e.g. '1h', '30m' or '7d'.",
        )
    m = _DURATION_RE.match(value.strip())
    if not m:
        return (
            None,
            f"{name}={value!r} is not a duration; use e.g. '30m', '1h', "
            "'24h', '7d' or '2w' (units m/h/d/w).",
        )
    amount = int(m.group(1))
    if amount <= 0:
        return None, f"{name}={value!r} must be a positive duration."
    return (
        timedelta(seconds=amount * _DURATION_SECONDS[m.group(2).lower()]),
        None,
    )


def _time_given(value: Any) -> bool:
    """True when a start/end time argument was actually supplied."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _parse_time(
    value: Any, name: str, now: datetime | None = None
) -> tuple[datetime | None, str | None]:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        lowered = text.lower()
        if lowered == "now" or lowered.startswith(("now-", "now+")):
            # Relative to the 'now' reference (falls back to wall-clock now).
            base = now or datetime.now(timezone.utc)
            if lowered == "now":
                return base, None
            delta, derr = _parse_duration(text[4:], name)
            if derr is not None:
                return None, derr
            return (
                base - delta if lowered[3] == "-" else base + delta,
                None,
            )
        try:
            dt = datetime.fromisoformat(
                text.replace("Z", "+00:00").replace("z", "+00:00")
            )
        except ValueError:
            return (
                None,
                f"{name}={value!r} is not ISO-8601 or a relative time; use "
                "e.g. '2024-01-15T12:00:00Z' or 'now-1h'.",
            )
    else:
        return (
            None,
            f"{name} is required as an ISO-8601 string (e.g. "
            "'2024-01-15T12:00:00Z') or a relative time like 'now-1h'.",
        )
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt, None


def _is_throttle(res: dict[str, Any]) -> bool:
    return (
        res.get("code") in (THROTTLED, QUOTA_EXCEEDED)
        or (res.get("aws_code") or "") in _THROTTLE_CODES
    )


def _propagate(
    res: dict[str, Any],
    context: str,
    permission: str,
    extra: list[str] | None = None,
) -> dict[str, Any]:
    """Return an AWS failure as data, adding the fix the caller needs."""
    code = res.get("code") or SERVICE_ERROR
    guidance = list(res.get("guidance") or [])
    if (
        code == CREDENTIALS_EXPIRED
        or (res.get("aws_code") or "") in _EXPIRED_CODES
    ):
        code = CREDENTIALS_EXPIRED
        guidance.append(
            "AWS credentials expired: refresh the session, then re-run this command (it is idempotent)."
        )
    elif code == PERMISSION_DENIED:
        guidance.append(
            f"The caller lacks {permission}; use a role that grants it."
        )
    guidance.extend(extra or [])
    return err_result(
        code,
        f"{context}: {res.get('error')}",
        aws_code=res.get("aws_code"),
        retriable=bool(res.get("retriable"))
        or code in (THROTTLED, CREDENTIALS_EXPIRED),
        guidance=guidance,
    )


# --------------------------------------------------------------------------- query validation


def _blank_comments(query: str) -> str:
    """Replace `#` comment lines with spaces so offsets into the original string stay valid."""
    return "\n".join(
        " " * len(ln) if ln.lstrip().startswith("#") else ln
        for ln in query.split("\n")
    )


def _opens_regex(text: str, seg_start: int, i: int) -> bool:
    prev = text[seg_start:i].rstrip()
    if not prev:
        return True
    words = prev.split()
    return (
        prev[-1] in "(,=~!"
        or words[-1].lower() in {"like", "match", "rlike"}
        or words[0].lower() == "parse"
    )


def _split_pipeline(query: str) -> list[tuple[int, str]]:
    """Split on top-level `|`, ignoring pipes inside quotes, backticks, /regex/ literals and parentheses."""
    text = _blank_comments(query)
    segments: list[tuple[int, str]] = []
    seg_start, i, n = 0, 0, len(text)
    quote: str | None = None
    in_regex = False
    depth = 0
    while i < n:
        ch = text[i]
        if quote is not None or in_regex:
            if ch == "\\":
                i += 2
                continue
            if quote is not None and ch == quote:
                quote = None
            elif in_regex and ch == "/":
                in_regex = False
        elif ch in "\"'`":
            quote = ch
        elif ch == "/" and _opens_regex(text, seg_start, i):
            in_regex = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "|" and depth == 0:
            segments.append((seg_start, text[seg_start:i]))
            seg_start = i + 1
        i += 1
    segments.append((seg_start, text[seg_start:]))
    return segments


def _analyze_query(query: str) -> dict[str, Any]:
    """Analyse the pipeline's commands for guidance -- advisory only, never fatal.

    Returns an analysis dict: the recognized ``commands`` list, ``is_aggregate``,
    ``explicit_limit``, a ``non_additive`` flag (a non-mergeable aggregate such
    as avg/percentile/count_distinct, or a pattern/diff/anomaly command), an
    ``unknown_commands`` flag and the ``unknown_tokens`` that triggered it. A
    locally-unrecognized command (or an empty/stray stage) is recorded rather
    than rejected: the server validates the query, so we never refuse locally
    what the server might accept -- a MalformedQueryException from StartQuery
    handles a query that is truly invalid.
    """
    commands: list[str] = []
    unknown_tokens: list[str] = []
    non_additive = False
    for offset, seg in _split_pipeline(query):
        stripped = seg.strip()
        if not stripped:
            # A stray '|' / empty stage: record it, do not reject locally.
            unknown_tokens.append("|")
            continue
        m = re.match(r"[A-Za-z_]+", stripped)
        token = m.group(0) if m else stripped.split()[0]
        if not m or token.lower() not in _KNOWN_COMMANDS:
            # An unrecognized leading token: the server may still accept it, so
            # flag it for guidance instead of blocking the query.
            unknown_tokens.append(token)
            continue
        cmd = token.lower()
        commands.append(cmd)
        if cmd == "stats":
            # Non-additive aggregate functions produce per-key results that
            # cannot be merged by concatenating per-batch rows.
            for fn in re.findall(r"\b([A-Za-z_]+)\s*\(", stripped):
                if fn.lower() in _NON_ADDITIVE:
                    non_additive = True
        elif cmd in ("pattern", "diff", "anomaly"):
            # These commands' output also cannot be merged across batches.
            non_additive = True
    return {
        "commands": commands,
        "is_aggregate": any(c in _AGGREGATE_COMMANDS for c in commands),
        "explicit_limit": "limit" in commands,
        "unknown_commands": bool(unknown_tokens),
        "unknown_tokens": unknown_tokens,
        "non_additive": non_additive,
    }


def _starts_with_source(query: Any) -> bool:
    """True when the query's first (non-empty) pipeline stage is a ``SOURCE`` command.

    ``SOURCE`` lets the query select its own log groups (by name prefix, tags or
    data source), so ``StartQuery`` must be sent WITHOUT a ``logGroupNames`` /
    ``logGroupIdentifiers`` parameter. Comments are blanked and leading
    whitespace ignored (``_split_pipeline`` already handles quoting and regex
    literals), and the match is case-insensitive on a word boundary so a field
    literally named ``sourceType`` is not mistaken for the command.
    """
    if not isinstance(query, str):
        return False
    for _, seg in _split_pipeline(query):
        stripped = seg.strip()
        if not stripped:
            continue
        return bool(re.match(r"source\b", stripped, re.IGNORECASE))
    return False


def _compile_error_detail(res: dict[str, Any], query: str) -> dict[str, Any]:
    """Extract parser line/position and the offending token from a MalformedQueryException."""
    detail: dict[str, Any] = {"source": "server", "message": res.get("error")}
    offset: int | None = None
    body = res.get("value") if isinstance(res.get("value"), dict) else {}
    loc = (body.get("queryCompileError") or {}).get("location") or {}
    msg = res.get("error") or ""
    m_line = _LINE_POS_RE.search(msg)
    m_pos = _POS_RE.search(msg)
    if isinstance(loc.get("start"), int):
        offset = loc["start"]
        detail["position"] = offset
    elif m_line:
        line, col = int(m_line.group(1)), int(m_line.group(2))
        lines = query.split("\n")
        offset = sum(len(ln) + 1 for ln in lines[: max(line - 1, 0)]) + col
        detail.update({"line": line, "position": col})
    elif m_pos:
        offset = int(m_pos.group(1))
        detail["position"] = offset
    token = ""
    if offset is not None and 0 <= offset < len(query):
        mt = re.compile(r"\S+").search(query, offset)
        token = mt.group(0) if mt else ""
    detail["offset"] = offset
    detail["token"] = token
    return detail


# --------------------------------------------------------------------------- log group resolution


def _strip_star(arn: Any) -> Any:
    """Strip a trailing ``:*`` from a log-group ARN; ``StartQuery`` rejects it."""
    if isinstance(arn, str) and arn.endswith(":*"):
        return arn[:-2]
    return arn


def _group_arn(g: dict[str, Any]) -> str | None:
    """Return a group's ARN without the ``:*`` suffix.

    ``ListLogGroups`` returns ``logGroupArn`` (no suffix); ``DescribeLogGroups``
    returns both ``logGroupArn`` and the older ``arn`` (which carries ``:*``).
    Prefer the suffix-free field, falling back to the stripped legacy one.
    """
    arn = g.get("logGroupArn") or g.get("arn")
    return _strip_star(arn) if arn else None


def _normalize_entry(raw: Any) -> tuple[str, bool, bool] | None:
    """Normalise one ``--log-group-names`` value.

    Returns ``(value, is_prefix, is_arn)`` or ``None`` when the value is not a
    valid name/prefix/ARN. A log-group ARN is PRESERVED as-is (only a trailing
    ``:*`` is stripped) rather than reduced to its bare name, so a cross-account
    or cross-region ARN is queried through ``logGroupIdentifiers`` instead of
    silently resolving to a same-named group in the caller's own account/region.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    entry = raw.strip()
    if _ARN_RE.match(entry):
        # Keep the full ARN; only drop the ':*' suffix StartQuery rejects.
        return _strip_star(entry), False, True
    is_prefix = entry.endswith("*")
    name = entry.rstrip("*")
    if not name or not _GROUP_NAME_RE.match(name):
        return None
    return name, is_prefix, False


def _list_log_groups(
    call_op, pattern: str
) -> tuple[list[dict[str, Any]], bool, dict[str, Any] | None]:
    """ListLogGroups, following nextToken to the end (bounded). Returns (groups, complete, error).

    ``pattern`` is a ``logGroupNamePattern`` matched server-side: ``^prefix``
    anchors a prefix, a bare substring matches anywhere. This replaces the old
    client-side, case-sensitive prefix comparison against a DescribeLogGroups
    scan.
    """
    groups: list[dict[str, Any]] = []
    token: str | None = None
    for _ in range(_DESCRIBE_PAGE_CAP):
        params: dict[str, Any] = {
            "logGroupNamePattern": pattern,
            "limit": 1000,
        }
        if token:
            params["nextToken"] = token
        res = call_op("ListLogGroups", params)
        if not res["ok"]:
            return groups, False, res
        body = res.get("value") or {}
        groups.extend(
            g
            for g in (body.get("logGroups") or [])
            if isinstance(g, dict) and g.get("logGroupName")
        )
        token = body.get("nextToken")
        if not token:
            return groups, True, None
    return groups, False, None


def _describe_identifiers(
    call_op, identifiers: list[str]
) -> tuple[list[dict[str, Any]], bool, dict[str, Any] | None]:
    """DescribeLogGroups by logGroupIdentifiers, following nextToken (bounded).

    Only ``DescribeLogGroups`` reliably returns ``retentionInDays`` (ListLogGroups
    and the old ``logGroupNamePattern`` scan do not), so the matched groups are
    enriched here before the retention clamp. Returns (groups, complete, error).
    """
    groups: list[dict[str, Any]] = []
    token: str | None = None
    for _ in range(_DESCRIBE_PAGE_CAP):
        params: dict[str, Any] = {"logGroupIdentifiers": identifiers}
        if token:
            params["nextToken"] = token
        res = call_op("DescribeLogGroups", params)
        if not res["ok"]:
            return groups, False, res
        body = res.get("value") or {}
        groups.extend(
            g
            for g in (body.get("logGroups") or [])
            if isinstance(g, dict) and g.get("logGroupName")
        )
        token = body.get("nextToken")
        if not token:
            return groups, True, None
    return groups, False, None


def _resolve_groups(
    call_op, entries: list[tuple[str, bool, bool]]
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    list[str],
    bool,
    dict[str, Any] | None,
]:
    """Discover log groups with ListLogGroups, then enrich retention via DescribeLogGroups.

    Returns ``(resolution, groups, notes, complete, error)``. ``groups`` is keyed
    by log-group name (or the ARN itself for an ARN that could not be enriched)
    and each meta carries ``arn`` plus ``retentionInDays`` when known.
    """
    resolution: list[dict[str, Any]] = []
    notes: list[str] = []
    complete = True
    # Name-discovered groups, keyed by name: {logGroupName, arn}.
    matched: dict[str, dict[str, Any]] = {}
    # ARN inputs resolve after the enrichment call: (resolution_index, arn).
    arn_targets: list[tuple[int, str]] = []

    # ---- phase 1: discover name/prefix/substring entries via ListLogGroups
    for value, is_prefix, is_arn in entries:
        if is_arn:
            # An ARN is queried directly through logGroupIdentifiers; it is not a
            # name pattern, so skip discovery and resolve it from enrichment.
            resolution.append(
                {"input": value, "match": "arn", "log_groups": []}
            )
            arn_targets.append((len(resolution) - 1, value))
            continue
        name = value
        found, done, err = _list_log_groups(call_op, "^" + name)
        if err is not None:
            return (
                [],
                {},
                [],
                False,
                _propagate(
                    err,
                    f"ListLogGroups(pattern={'^' + name!r})",
                    "logs:ListLogGroups",
                ),
            )
        complete = complete and done
        exact = [g for g in found if g["logGroupName"] == name]
        if is_prefix:
            chosen, how = found, "prefix"
        elif exact:
            chosen, how = exact, "exact"
            siblings = len(found) - len(exact)
            if siblings:
                notes.append(
                    f"{siblings} other log group(s) share the prefix {name!r}; "
                    f"pass {name + '*'!r} to include them."
                )
        elif found:
            chosen, how = found, "prefix"
            notes.append(
                f"No log group is named exactly {name!r}; expanded it as a prefix to {len(found)} group(s)."
            )
        else:
            # No prefix match: fall back to an unanchored substring match.
            found, done, err = _list_log_groups(call_op, name)
            if err is not None and err.get("code") not in (
                INVALID_INPUT,
                VALIDATION_ERROR,
            ):
                return (
                    [],
                    {},
                    [],
                    False,
                    _propagate(
                        err,
                        f"ListLogGroups(pattern={name!r})",
                        "logs:ListLogGroups",
                    ),
                )
            chosen = found if err is None else []
            if err is None:
                complete = complete and done
            how = "pattern" if chosen else "none"
            if chosen:
                notes.append(
                    f"{name!r} is not a log group name or prefix; matched {len(chosen)} group(s) "
                    "containing it: "
                    + ", ".join(g["logGroupName"] for g in chosen[:5])
                    + (" ..." if len(chosen) > 5 else "")
                )
        for g in chosen:
            matched.setdefault(
                g["logGroupName"],
                {"logGroupName": g["logGroupName"], "arn": _group_arn(g)},
            )
        resolution.append(
            {
                "input": name + ("*" if is_prefix else ""),
                "match": how,
                "log_groups": [g["logGroupName"] for g in chosen],
            }
        )

    # ---- phase 2: enrich retention (and resolve ARNs) via DescribeLogGroups
    # Only the matched groups and the ARN inputs are enriched, <= 50 identifiers
    # per call. ListLogGroups does not return retentionInDays, so without this
    # step groups outside their retention edge would never be clamped/skipped.
    identifiers: list[str] = []
    seen_ids: set[str] = set()
    for meta in matched.values():
        ident = meta.get("arn") or meta["logGroupName"]
        if ident not in seen_ids:
            seen_ids.add(ident)
            identifiers.append(ident)
    for _, arn in arn_targets:
        if arn not in seen_ids:
            seen_ids.add(arn)
            identifiers.append(arn)

    enriched_by_name: dict[str, dict[str, Any]] = {}
    enriched_by_arn: dict[str, dict[str, Any]] = {}
    for i in range(0, len(identifiers), _MAX_IDENTIFIERS_PER_DESCRIBE):
        batch = identifiers[i : i + _MAX_IDENTIFIERS_PER_DESCRIBE]
        found, done, err = _describe_identifiers(call_op, batch)
        if err is not None:
            return (
                [],
                {},
                [],
                False,
                _propagate(
                    err,
                    "DescribeLogGroups(logGroupIdentifiers)",
                    "logs:DescribeLogGroups",
                ),
            )
        complete = complete and done
        for g in found:
            enriched_by_name[g["logGroupName"]] = g
            arn = _group_arn(g)
            if arn:
                enriched_by_arn[arn] = g

    groups: dict[str, dict[str, Any]] = {}
    # Attach retention (and a clean ARN) to each name-discovered group.
    for name, meta in matched.items():
        g = dict(meta)
        enriched = enriched_by_name.get(name)
        if enriched is not None:
            if enriched.get("retentionInDays") is not None:
                g["retentionInDays"] = enriched["retentionInDays"]
            if enriched.get("logGroupClass") is not None:
                g["logGroupClass"] = enriched["logGroupClass"]
            g["arn"] = _group_arn(enriched) or g.get("arn")
        groups[name] = g
    # Resolve ARN inputs from the enrichment response.
    for idx, arn in arn_targets:
        enriched = enriched_by_arn.get(arn)
        if enriched is not None:
            name = enriched["logGroupName"]
            g = {"logGroupName": name, "arn": _group_arn(enriched) or arn}
            if enriched.get("retentionInDays") is not None:
                g["retentionInDays"] = enriched["retentionInDays"]
            if enriched.get("logGroupClass") is not None:
                g["logGroupClass"] = enriched["logGroupClass"]
            groups.setdefault(name, g)
            resolution[idx]["log_groups"] = [name]
        else:
            # Unresolved ARN (e.g. a cross-account ARN without enrichment access):
            # still query it directly via logGroupIdentifiers, with no retention
            # bound since none could be fetched.
            groups.setdefault(arn, {"logGroupName": arn, "arn": arn})
            resolution[idx]["log_groups"] = [arn]
    return resolution, groups, notes, complete, None


# --------------------------------------------------------------------------- one query segment


def _run_segment(
    call_op,
    targets: list[str],
    start_s: int,
    end_s: int,
    query: str,
    limit: int | None,
    *,
    log_group_param: str | None,
    sleep,
    clock,
    poll_interval: float,
    max_polls: int,
    timeout_seconds: float,
    max_rows: int,
    in_flight: set[str],
) -> dict[str, Any]:
    """Run one StartQuery/poll cycle. Returns segment data, or an err_result (ok=False).

    ``log_group_param`` selects how the groups are passed to StartQuery:
    ``"logGroupNames"`` for plain names, ``"logGroupIdentifiers"`` when any input
    was an ARN, or ``None`` when the query selects its own groups via ``SOURCE``
    (StartQuery then carries neither parameter -- it rejects a query that has
    both a SOURCE command and a log-group parameter).
    """
    params: dict[str, Any] = {
        "startTime": start_s,
        "endTime": end_s,
        "queryString": query,
    }
    if log_group_param and targets:
        params[log_group_param] = targets
    if limit is not None:
        params["limit"] = limit
    attempt = 0
    while True:
        res = call_op("StartQuery", params)
        if res["ok"]:
            break
        if _is_throttle(res):
            if attempt < _START_RETRIES:
                sleep(min(max(poll_interval, 1.0) * (2**attempt), 30.0))
                attempt += 1
                continue
            return err_result(
                QUOTA_EXCEEDED,
                f"StartQuery still throttled after {_START_RETRIES} retries: {res.get('error')}",
                aws_code=res.get("aws_code"),
                retriable=True,
                guidance=[
                    "Logs Insights limits concurrent queries per account/region; wait for running queries "
                    "to finish (logs:DescribeQueries) and retry."
                ],
            )
        aws_code = res.get("aws_code") or ""
        if aws_code == "MalformedQueryException":
            detail = _compile_error_detail(res, query)
            where = f"line {detail.get('line', 1)}, position {detail.get('position')}"
            # Server-discovered malformed query: operational error (not a pre-dispatch param error).
            return err_result(
                INVALID_INPUT,
                f"MalformedQueryException at {where}: token {detail['token']!r}",
                value=detail,
                guidance=[
                    f"Fix the query near {detail['token']!r} ({where}) and re-run; nothing was executed.",
                    "Check quoting of regexes (/.../), string literals and field names with special "
                    "characters (wrap them in backticks).",
                ],
            )
        if aws_code == "InvalidParameterException":
            return err_result(
                INVALID_INPUT,
                f"StartQuery rejected the parameters: {res.get('error')}",
                aws_code=aws_code,
                guidance=[
                    f"Window used was {_iso(start_s)}..{_iso(end_s)} on {len(targets)} group(s); "
                    "narrow the window or check the group names in log_group_resolution."
                ],
            )
        if aws_code == "ResourceNotFoundException":
            return err_result(
                NOT_FOUND,
                f"StartQuery: {res.get('error')}",
                aws_code=aws_code,
                guidance=[
                    "A log group disappeared between resolution and StartQuery; re-run."
                ],
            )
        return _propagate(res, "StartQuery", "logs:StartQuery")

    qid = (res.get("value") or {}).get("queryId")
    if not isinstance(qid, str) or not qid.strip():
        return err_result(
            SERVICE_ERROR,
            "StartQuery returned no queryId; refusing to poll GetQueryResults with a blank id.",
            retriable=True,
            guidance=[
                "Re-run the command; if it persists, check logs:StartQuery permissions."
            ],
        )

    # Record the started query so the caller can StopQuery it if the whole
    # command is interrupted (KeyboardInterrupt/SystemExit) mid-poll. It is
    # removed again before every normal/handled return below; only an
    # exception propagating out leaves it in the set for _run's finally.
    in_flight.add(qid)

    body: dict[str, Any] = {}
    status = "Unknown"

    def _terminal(res: dict[str, Any]) -> str | None:
        nonlocal body, status
        body = res.get("value") or {}
        status = str(body.get("status") or "Unknown")
        return status if status in _TERMINAL else None

    def _on_timeout() -> None:
        # StopQuery cancels the query lifecycle; it does not mutate your data.
        call_op("StopQuery", {"queryId": qid})

    poll_result = drive_poll(
        call_op,
        "GetQueryResults",
        {"queryId": qid},
        terminal=_terminal,
        is_retriable=_is_throttle,
        on_timeout=_on_timeout,
        interval=poll_interval,
        max_wait=timeout_seconds,
        max_polls=max_polls,
        max_transient=_THROTTLE_RETRIES,
        clock=clock,
        sleep=sleep,
        key=qid,
    )
    polls = poll_result.get("polls_count", 0)

    if not poll_result["ok"]:
        if poll_result.get("code") == TIMEOUT:
            in_flight.discard(qid)
            return err_result(
                TIMEOUT,
                f"Query {qid} still {status} after {polls} polls; stopped it.",
                retriable=True,
                is_exhaustive=False,
                value={
                    "query_id": qid,
                    "status": status,
                    "polls": polls,
                    "window": {"start": _iso(start_s), "end": _iso(end_s)},
                    "log_groups": targets,
                },
                guidance=[
                    "Raise --timeout-seconds, narrow the time window, or add a selective "
                    "'filter' stage before 'stats'."
                ],
            )
        in_flight.discard(qid)
        return _propagate(
            poll_result,
            f"GetQueryResults(queryId={qid})",
            "logs:GetQueryResults",
            [
                f"Query {qid} may still be running; call logs:GetQueryResults with it later."
            ],
        )

    if status != "Complete":
        code = {"Timeout": TIMEOUT, "Cancelled": CONFLICT}.get(
            status, SERVICE_ERROR
        )
        in_flight.discard(qid)
        return err_result(
            code,
            f"Query {qid} ended with status {status}.",
            retriable=status in ("Timeout", "Unknown"),
            value={
                "query_id": qid,
                "status": status,
                "window": {"start": _iso(start_s), "end": _iso(end_s)},
            },
            guidance=[
                "Logs Insights queries time out after 60 minutes; narrow the window or filter earlier."
                if status == "Timeout"
                else "Re-run; if it fails again, simplify the query."
            ],
        )

    # The query is Complete and ``body`` carries the first page of results.
    # GetQueryResults returns up to 10,000 rows per page; page through nextToken
    # (which expires ~1 hour after the query completes, so this is done
    # immediately) to collect the full result set, stopping early once we hold
    # the caller's display cap (max_rows). Window splitting stays a fallback
    # only when recordsMatched exceeds the StartQuery row cap.
    raw_results: list[Any] = list(body.get("results") or [])
    token = body.get("nextToken")
    while token and len(raw_results) < max_rows:
        page = call_op(
            "GetQueryResults",
            {"queryId": qid, "maxItems": 10_000, "nextToken": token},
        )
        if not page["ok"]:
            # The query completed but a result page failed: propagate rather
            # than return a silently partial set.
            in_flight.discard(qid)
            return _propagate(
                page,
                f"GetQueryResults(queryId={qid}, nextToken)",
                "logs:GetQueryResults",
                [
                    f"Query {qid} completed but paginating its results failed after "
                    f"{len(raw_results)} row(s); the nextToken expires ~1 hour after completion."
                ],
            )
        page_body = page.get("value") or {}
        raw_results.extend(page_body.get("results") or [])
        token = page_body.get("nextToken")

    rows: list[dict[str, Any]] = []
    for raw in raw_results:
        if isinstance(raw, list):
            rows.append(
                {
                    c.get("field"): c.get("value")
                    for c in raw
                    if isinstance(c, dict) and c.get("field")
                }
            )
    stats = body.get("statistics") or {}
    # Segment data (no "ok" key) distinguishes success from an err_result.
    in_flight.discard(qid)
    return {
        "query_id": qid,
        "rows": rows,
        "statistics": {
            k: float(v)
            for k, v in stats.items()
            if isinstance(v, (int, float))
        },
        "polls": polls,
    }


# --------------------------------------------------------------------------- the command


def run_insights_query(
    call_op,
    log_group_names_or_prefix: list[str] | str | None,
    query_string: str,
    start_time: str | datetime | None = None,
    end_time: str | datetime | None = None,
    *,
    since: str | None = None,
    max_splits: int = 6,
    max_queries: int = 64,
    max_rows: int = 50,
    max_message_length: int = DEFAULT_MESSAGE_MAX_CHARS,
    poll_interval: float = 1.0,
    max_polls: int = 600,
    timeout_seconds: float = 900.0,
    max_deadline: float = 3600.0,
    now: str | datetime | None = None,
    sleep=None,
    clock=None,
) -> dict[str, Any]:
    """Run one Logs Insights query over one or more log groups to completion.

    ``call_op(operation, params)`` is the read-only call bridge bound to a Logs
    client. Returns the plain-dict result convention; never raises. The window is
    bounded to retention (NOT creation time). Row output is capped at ``max_rows``
    and each ``@message`` is truncated to ``max_message_length``; both bounds are
    reported. ``log_group_names_or_prefix`` may be omitted (``None``/empty) when
    ``query_string`` begins with a ``SOURCE`` command that selects its own log
    groups; passing both is an error. The window may be given as explicit
    ``start_time``/``end_time`` (ISO-8601 or ``now-1h``-style relative) or as a
    ``since`` duration (``'1h'``, ``'30m'``, ``'7d'``) ending at now; ``since``
    and explicit start/end are mutually exclusive. ``max_deadline`` bounds the
    total wall-clock seconds across all sub-queries.
    """
    sleep = time.sleep if sleep is None else sleep
    clock = time.monotonic if clock is None else clock
    try:
        return _run(
            call_op,
            log_group_names_or_prefix,
            query_string,
            start_time,
            end_time,
            since,
            max_splits,
            max_queries,
            max_rows,
            max_message_length,
            poll_interval,
            max_polls,
            timeout_seconds,
            max_deadline,
            now,
            sleep,
            clock,
        )
    except Exception as exc:  # noqa: BLE001 - contract: never raise
        # Only ordinary errors are normalized to data. A BaseException such as
        # KeyboardInterrupt/SystemExit propagates after _run's finally has
        # stopped any in-flight queries, so the interrupt is not swallowed.
        return err_result(
            SERVICE_ERROR,
            f"run-insights-query internal error: {exc!r}",
            guidance=[
                "Unexpected internal error; report it with the inputs used."
            ],
        )


def _validate(
    groups_in: list[str] | str | None,
    query_string: str,
    start_time: Any,
    end_time: Any,
    since: Any,
    now: Any,
    ints: dict[str, Any],
    max_splits: Any,
    floats: dict[str, Any],
    has_source: bool,
) -> tuple[
    list[tuple[str, bool, bool]],
    datetime | None,
    datetime | None,
    datetime | None,
    list[str],
]:
    problems: list[str] = []
    raw_entries = (
        [groups_in] if isinstance(groups_in, str) else list(groups_in or [])
    )
    entries: list[tuple[str, bool, bool]] = []
    # --log-group-names is optional, but it and a SOURCE command are mutually
    # exclusive: StartQuery takes the groups either in a parameter or in a SOURCE
    # clause, never both; and with neither there is nothing to query.
    if raw_entries and has_source:
        problems.append(
            "Both log_group_names and a SOURCE command were given; StartQuery accepts one or the "
            "other. Drop log_group_names, or remove the SOURCE command from the query."
        )
    elif not raw_entries and not has_source:
        problems.append(
            "No log groups given; pass at least one log_group_names value (name, prefix* or ARN), "
            "or begin the query with a SOURCE command."
        )
    for raw in raw_entries:
        norm = _normalize_entry(raw)
        if norm is None:
            problems.append(
                f"{raw!r} is not a valid log group name/prefix (allowed: letters, digits, . - _ / #, "
                "optional trailing '*', or a log-group ARN)."
            )
        elif norm not in entries:
            entries.append(norm)
    q_err = check_non_empty_str("query_string", query_string)
    if q_err is not None:
        problems.append(q_err)
    elif len(query_string) > _MAX_QUERY_CHARS:
        problems.append(
            f"query_string is {len(query_string)} chars; Logs Insights accepts at most {_MAX_QUERY_CHARS}."
        )
    # Resolve the 'now' reference first; relative times (--since and the
    # now-1h syntax) are computed against it.
    now_dt: datetime | None = datetime.now(timezone.utc)
    if now is not None:
        now_dt, err_n = _parse_time(now, "now")
        if err_n:
            problems.append(err_n)
    start_dt: datetime | None = None
    end_dt: datetime | None = None
    if _time_given(since):
        # --since gives a window ending at now; it is mutually exclusive with
        # an explicit start/end (StartQuery needs one window, not two sources).
        if _time_given(start_time) or _time_given(end_time):
            problems.append(
                "since conflicts with start_time/end_time; pass a relative "
                "--since window OR explicit --start-time/--end-time, not both."
            )
        delta, derr = _parse_duration(since, "since")
        if derr is not None:
            problems.append(derr)
        elif now_dt is not None:
            end_dt = now_dt
            start_dt = now_dt - delta
    else:
        start_dt, err_s = _parse_time(start_time, "start_time", now_dt)
        end_dt, err_e = _parse_time(end_time, "end_time", now_dt)
        problems.extend(e for e in (err_s, err_e) if e)
        if start_dt and end_dt and start_dt >= end_dt:
            problems.append(
                f"start_time ({start_dt.isoformat()}) must be before "
                f"end_time ({end_dt.isoformat()})."
            )
    for pname, pval in ints.items():
        err = check_positive_int(pname, pval)
        if err is not None:
            problems.append(err)
    err = check_positive_int("max_splits", max_splits, lo=0)
    if err is not None:
        problems.append(err)
    for pname, pval in floats.items():
        err = check_positive_number(pname, pval)
        if err is not None:
            problems.append(err)
    return entries, start_dt, end_dt, now_dt, problems


def _run(
    call_op,
    groups_in: list[str] | str,
    query_string: str,
    start_time: str | datetime | None,
    end_time: str | datetime | None,
    since: str | None,
    max_splits: int,
    max_queries: int,
    max_rows: int,
    max_message_length: int,
    poll_interval: float,
    max_polls: int,
    timeout_seconds: float,
    max_deadline: float,
    now: str | datetime | None,
    sleep,
    clock,
) -> dict[str, Any]:
    # ---- 0. validate everything before the first AWS call
    deadline_start = clock()
    has_source = _starts_with_source(query_string)
    entries, start_dt, end_dt, now_dt, problems = _validate(
        groups_in,
        query_string,
        start_time,
        end_time,
        since,
        now,
        {
            "max_queries": max_queries,
            "max_rows": max_rows,
            "max_polls": max_polls,
        },
        max_splits,
        {
            "poll_interval": poll_interval,
            "timeout_seconds": timeout_seconds,
            "max_deadline": max_deadline,
        },
        has_source,
    )
    if problems or start_dt is None or end_dt is None or now_dt is None:
        return invalid_input(
            "Invalid input: "
            + (problems[0] if problems else "bad time values"),
            problems,
        )

    analysis = _analyze_query(query_string)
    commands = analysis["commands"]
    is_aggregate = analysis["is_aggregate"]
    explicit_limit = analysis["explicit_limit"]

    guidance: list[str] = []
    partial_reasons: list[str] = []
    clamp_reasons: list[str] = []

    now_ms = int(now_dt.timestamp() * 1000)
    req_start_ms = int(start_dt.timestamp() * 1000)
    req_end_ms = int(end_dt.timestamp() * 1000)
    end_ms = req_end_ms
    if end_ms > now_ms:
        end_ms = now_ms
        clamp_reasons.append(
            f"end_time is in the future; clamped to now ({_iso_ms(now_ms)})."
        )

    # ---- 1. resolve groups (unless the query selects its own via SOURCE) and
    #         bound the window to retention.
    resolution: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    delivery_skipped: list[dict[str, Any]] = []
    if has_source:
        # SOURCE path: the query picks its own log groups, so skip resolution,
        # retention bounding and 50-group batching, and send StartQuery neither
        # logGroupNames nor logGroupIdentifiers.
        guidance.append(
            "Query begins with a SOURCE command and selects its own log groups; "
            "log-group resolution and retention bounding were skipped."
        )
        names: list[str] = []
        batches: list[list[str]] = [[]]
        log_group_param: str | None = None
        start_ms = req_start_ms
    else:
        resolution, groups, notes, resolution_complete, err = _resolve_groups(
            call_op, entries
        )
        if err is not None:
            return err
        if not groups:
            wanted = ", ".join(
                repr(v + ("*" if p else "")) for v, p, _ in entries
            )
            return err_result(
                NOT_FOUND,
                f"No log groups matched {wanted}.",
                guidance=[
                    "Check the region (log groups are regional) and try a shorter prefix ending in '*' or a "
                    "distinctive substring such as the function/service name."
                ],
                value={"log_group_resolution": resolution},
            )
        guidance.extend(notes)
        if not resolution_complete:
            partial_reasons.append(
                f"ListLogGroups listing stopped at the {_DESCRIBE_PAGE_CAP}-page cap; "
                "some matching groups may be missing. Use a narrower prefix."
            )
        # If ANY input was an ARN, query the whole batch through
        # logGroupIdentifiers (cross-account/region safe) rather than
        # logGroupNames; plain names are converted to their resolved ARNs.
        use_identifiers = any(is_arn for _, _, is_arn in entries)
        in_window: list[tuple[str, int]] = []
        for name, meta in groups.items():
            if meta.get("logGroupClass") == "DELIVERY":
                # DELIVERY-class groups cannot be queried with Logs Insights;
                # drop them from the query set and report them.
                delivery_skipped.append(
                    {
                        "log_group": name,
                        "log_group_class": "DELIVERY",
                        "reason": "DELIVERY class is not queryable with "
                        "Logs Insights",
                    }
                )
                continue
            # Retention-only bound. A log group's creationTime does NOT bound a
            # Logs Insights query (events can exist from before the group's
            # record was created), so it is intentionally excluded here.
            earliest = 0
            retention = meta.get("retentionInDays")
            if retention:
                earliest = now_ms - int(retention) * _DAY_MS
            if earliest > end_ms:
                skipped.append(
                    {
                        "log_group": name,
                        "queryable_from": _iso_ms(earliest),
                        "retention_in_days": retention,
                        "reason": "window ends before this group's retention edge",
                    }
                )
            else:
                in_window.append((name, earliest))
        if not in_window:
            return invalid_input(
                "None of the matched log groups hold data in the requested "
                "window.",
                [
                    f"{s['log_group']} is queryable from {s['queryable_from']}"
                    for s in skipped
                ]
                + [
                    f"{d['log_group']} has DELIVERY class (not queryable "
                    "with Insights)"
                    for d in delivery_skipped
                ]
                + ["Move start_time/end_time into the queryable range."],
                value={
                    "skipped_log_groups": skipped + delivery_skipped,
                    "log_group_resolution": resolution,
                },
            )
        start_ms = req_start_ms
        earliest_any = min(e for _, e in in_window)
        if earliest_any > start_ms:
            start_ms = earliest_any
            clamp_reasons.append(
                f"start_time precedes all retained data; clamped to {_iso_ms(start_ms)} "
                "(retention edge). Events before it no longer exist."
            )
        if skipped:
            guidance.append(
                f"Skipped {len(skipped)} group(s) with no data in the window: "
                + ", ".join(s["log_group"] for s in skipped[:5])
            )
        if delivery_skipped:
            guidance.append(
                f"Skipped {len(delivery_skipped)} log group(s) with DELIVERY "
                "class (not queryable with Insights): "
                + ", ".join(d["log_group"] for d in delivery_skipped[:5])
            )
        names = [n for n, _ in in_window]
        # Essentials-class (INFREQUENT_ACCESS) groups do not support the
        # pattern/diff/anomaly/unmask commands. Warn up front rather than
        # letting StartQuery return a server error for those groups.
        essentials = [
            n
            for n in names
            if groups[n].get("logGroupClass") == "INFREQUENT_ACCESS"
        ]
        if essentials and any(c in _ESSENTIALS_UNSUPPORTED for c in commands):
            guidance.append(
                f"{len(essentials)} resolved log group(s) are Essentials "
                "class (INFREQUENT_ACCESS), which does not support the "
                "pattern/diff/anomaly/unmask commands this query uses; "
                "the query will error for those groups: "
                + ", ".join(essentials[:5])
            )
        if use_identifiers:
            query_targets = [groups[n].get("arn") or n for n in names]
            log_group_param = "logGroupIdentifiers"
        else:
            query_targets = names
            log_group_param = "logGroupNames"
        batches = [
            query_targets[i : i + _MAX_GROUPS_PER_QUERY]
            for i in range(0, len(query_targets), _MAX_GROUPS_PER_QUERY)
        ]
        if len(batches) > 1:
            guidance.append(
                f"{len(names)} groups exceed the 50-per-query limit; ran {len(batches)} batches and merged."
            )

    if analysis["unknown_commands"]:
        guidance.append(
            "Query contains commands not recognized by this tool; results may vary."
        )

    if len(batches) > 1 and analysis["non_additive"]:
        # >50 log groups force batching, and non-additive aggregates (avg,
        # percentile, count_distinct) / pattern / diff / anomaly cannot be
        # merged across batches. Warn rather than refuse (review item 5).
        partial_reasons.append(
            "Query uses non-additive aggregates (avg/percentile/count_distinct) across multiple "
            "batches; per-batch results are concatenated but cannot be correctly merged. Use "
            "SOURCE with a prefix pattern to run the query across all groups in a single batch."
        )

    start_s, end_s = _ceil_s(start_ms), _ceil_s(end_ms)
    if start_s >= end_s:
        return invalid_input(
            f"Clamped window {_iso(start_s)}..{_iso(end_s)} is empty.",
            [
                "Choose a window that ends after start_time and is not entirely in the future."
            ],
        )
    guidance.extend(clamp_reasons)

    limit = None if explicit_limit else _ROW_CAP

    # ---- 2-4. run segments, splitting row-capped windows
    work: list[tuple[int, int, int, int]] = [
        (b, start_s, end_s, 0) for b in range(len(batches))
    ]
    segments: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    seen_ptrs: set[str] = set()
    totals: dict[str, float] = {}
    queries_run = 0
    split_count = 0
    rows_truncated = False
    in_flight: set[str] = set()
    try:
        while work:
            if queries_run >= max_queries:
                partial_reasons.append(
                    f"Stopped at max_queries={max_queries}; {len(work)} sub-window(s) not queried: "
                    + ", ".join(
                        f"{_iso(s)}..{_iso(e)}" for _, s, e, _ in work[:3]
                    )
                )
                break
            if queries_run > 0 and clock() - deadline_start >= max_deadline:
                # At least one sub-query always runs; the deadline then bounds
                # any further ones so worst case is not max_queries x timeout.
                partial_reasons.append(
                    f"Stopped after the overall deadline of {max_deadline:g}s; "
                    f"{len(work)} sub-window(s) not queried: "
                    + ", ".join(
                        f"{_iso(s)}..{_iso(e)}" for _, s, e, _ in work[:3]
                    )
                )
                break
            b, s, e, depth = work.pop(0)
            seg = _run_segment(
                call_op,
                batches[b],
                s,
                e,
                query_string,
                limit,
                log_group_param=log_group_param,
                sleep=sleep,
                clock=clock,
                poll_interval=poll_interval,
                max_polls=max_polls,
                timeout_seconds=timeout_seconds,
                max_rows=max_rows,
                in_flight=in_flight,
            )
            queries_run += 1
            if seg.get("ok") is False:
                done = [x["query_id"] for x in segments if not x["discarded"]]
                if done:
                    seg["guidance"] = list(seg.get("guidance") or []) + [
                        f"{len(done)} sub-query(ies) had completed before the failure: "
                        + ", ".join(done[:5])
                    ]
                return seg
            seg_rows: list[dict[str, Any]] = seg["rows"]
            matched = seg["statistics"].get("recordsMatched", 0.0)
            if is_aggregate:
                # Aggregate output is one row per group, capped at the
                # StartQuery limit; detect the cap from the returned count.
                capped = (
                    limit is not None
                    and len(seg_rows) >= limit
                    and matched > len(seg_rows)
                )
            else:
                # Non-aggregate: GetQueryResults is paginated to collect every
                # row up to the StartQuery limit, so the returned row count no
                # longer signals a cap. recordsMatched exceeding the limit does
                # -- the StartQuery limit dropped rows -- so split the window to
                # recover them (the fallback only when recordsMatched > cap).
                capped = limit is not None and matched > limit
            record = {
                "query_id": seg["query_id"],
                "start": _iso(s),
                "end": _iso(e),
                "log_group_batch": b,
                "rows": len(seg_rows),
                "records_matched": matched,
                "discarded": False,
            }
            if capped and not is_aggregate:
                if depth < max_splits and e - s >= 1:
                    mid = (s + e) // 2
                    # mid+1 is correct: Insights time range is inclusive on
                    # both ends, so [s, mid] and [mid+1, e] partition without
                    # overlap or gap.
                    work.extend(
                        [(b, s, mid, depth + 1), (b, mid + 1, e, depth + 1)]
                    )
                    record["discarded"] = True
                    segments.append(record)
                    split_count += 1
                    continue
                partial_reasons.append(
                    f"Sub-window {_iso(s)}..{_iso(e)} matched {int(matched)} records but returned "
                    f"{len(seg_rows)} (row cap) and max_splits={max_splits} was reached."
                )
            elif capped:
                partial_reasons.append(
                    f"Aggregate query returned {len(seg_rows)} groups (row cap); some groups are "
                    "missing. Coarsen the 'by' clause or bin() size."
                )
            segments.append(record)
            for k, v in seg["statistics"].items():
                totals[k] = totals.get(k, 0.0) + v
            for row in seg_rows:
                ptr = row.get("@ptr")
                if isinstance(ptr, str):
                    if ptr in seen_ptrs:
                        continue
                    seen_ptrs.add(ptr)
                if len(rows) >= max_rows:
                    rows_truncated = True
                    break
                rows.append(row)
    finally:
        # Interrupted mid-flight (KeyboardInterrupt/SystemExit): stop any query
        # still running so it does not hold one of the account's 100 concurrent
        # Insights query slots. Normal completion leaves in_flight empty.
        for qid in list(in_flight):
            try:
                call_op("StopQuery", {"queryId": qid})
            except BaseException:  # noqa: BLE001 - best-effort cleanup
                pass
    if rows_truncated:
        partial_reasons.append(
            f"Row output truncated at max_rows={max_rows}; statistics still reflect all matches."
        )
    if explicit_limit:
        guidance.append(
            "Query has an explicit 'limit'; results honour it and were not window-split."
        )
    kept = [x for x in segments if not x["discarded"]]
    if not is_aggregate and len(kept) > 1 and "sort" in commands:
        guidance.append(
            "Rows were merged from several sub-windows; 'sort' order holds within each sub-window only."
        )
    if is_aggregate and len(kept) > 1 and not analysis["non_additive"]:
        guidance.append(
            "Aggregate rows come from several batches/sub-windows; sum per-key counts across rows."
        )

    # ---- Truncate oversized @message fields (bounded output), recording the adjustment.
    truncated_messages = 0
    for row in rows:
        if "@message" in row:
            new_value, was_truncated = truncate_field(
                row["@message"], max_message_length
            )
            if was_truncated:
                row["@message"] = new_value
                truncated_messages += 1
    if truncated_messages:
        clamp_reasons.append(
            f"Truncated {truncated_messages} @message field(s) to {max_message_length} chars "
            "(--max-message-length); raise it to see full messages."
        )
        guidance.append(clamp_reasons[-1])

    fields: list[str] = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    value = {
        "rows": rows,
        "row_count": len(rows),
        "fields": fields,
        "statistics": totals,
        "window": {
            "start": _iso(start_s),
            "end": _iso(end_s),
            "start_epoch": start_s,
            "end_epoch": end_s,
        },
        "requested_window": {
            "start": _iso_ms(req_start_ms),
            "end": _iso_ms(req_end_ms),
        },
        "clamped": bool(clamp_reasons),
        "clamp_reasons": clamp_reasons,
        "log_groups": names,
        "log_group_resolution": resolution,
        "skipped_log_groups": skipped + delivery_skipped,
        "segments": segments,
        "split_count": split_count,
        "queries_run": queries_run,
        "is_aggregate": is_aggregate,
        "message_truncated_count": truncated_messages,
        "partial_reasons": partial_reasons,
        "query_string": query_string,
    }
    return ok_result(
        value,
        is_exhaustive=not partial_reasons,
        guidance=guidance + partial_reasons,
    )


class RunInsightsQueryCommand(BasicCommand):
    NAME = "run-insights-query"
    DESCRIPTION = (
        "Run a single CloudWatch Logs Insights query to completion over one or "
        "more log groups and return the full result set in one call.\n\n"
        "Use this command when you need to query CloudWatch Logs Insights across "
        "one or more log groups and get structured results in one step. It "
        "handles log group resolution, query submission, polling, time-window "
        "splitting for large result sets, and output capping.\n\n"
        "Resolves "
        "groups with ListLogGroups by exact name, prefix (trailing '*') or "
        "substring, then enriches retention with DescribeLogGroups; bounds the "
        "window to retention; polls to a terminal state; and splits row-capped "
        "windows to keep counts accurate. A log-group ARN is passed through "
        "unchanged (via logGroupIdentifiers), so cross-account/cross-region ARNs "
        "are not rewritten to a same-named local group. Alternatively, begin the "
        "query with a SOURCE command to select log groups yourself and omit "
        "--log-group-names. Read-only."
    )
    EXAMPLES = (
        "To run a query over a log group for the last hour's errors::\n\n"
        "  aws logs run-insights-query --log-group-names /aws/lambda/my-fn "
        "--query-string 'fields @timestamp, @message | filter @message like /ERROR/' "
        "--start-time 2024-01-15T00:00:00Z --end-time 2024-01-15T01:00:00Z\n\n"
        "To let the query select its own log groups with a SOURCE command "
        "(no --log-group-names)::\n\n"
        "  aws logs run-insights-query "
        "--query-string \"SOURCE logGroups(namePrefix: ['/aws/lambda']) | "
        "fields @timestamp, @message\" "
        "--start-time 2024-01-15T00:00:00Z --end-time 2024-01-15T01:00:00Z\n"
    )
    ARG_TABLE = [
        {
            "name": "log-group-names",
            "required": False,
            "nargs": "+",
            "help_text": (
                "One or more log group names, prefixes (trailing '*'), ARNs or "
                "substrings. Optional when the query begins with a SOURCE "
                "command (which selects log groups itself); exactly one of the "
                "two must be given, not both."
            ),
            "cli_type_name": "string",
        },
        {
            "name": "query-string",
            "required": True,
            "help_text": "The Logs Insights query to run.",
            "cli_type_name": "string",
        },
        {
            "name": "start-time",
            "required": False,
            "help_text": (
                "Window start: ISO-8601 (e.g. 2024-01-15T00:00:00Z) or "
                "relative to now (e.g. now-1h, now-30m). Required unless "
                "--since is given."
            ),
            "cli_type_name": "string",
        },
        {
            "name": "end-time",
            "required": False,
            "help_text": (
                "Window end: ISO-8601 or relative to now (e.g. now). "
                "Required unless --since is given."
            ),
            "cli_type_name": "string",
        },
        {
            "name": "since",
            "required": False,
            "cli_type_name": "string",
            "help_text": (
                "Relative window ending now, e.g. 1h, 30m, 24h, 7d, 2w "
                "(units m/h/d/w). Conflicts with --start-time/--end-time."
            ),
        },
        {
            "name": "max-rows",
            "default": 50,
            "cli_type_name": "integer",
            "help_text": "Maximum rows to return (default 50); statistics still reflect all matches.",
        },
        {
            "name": "max-message-length",
            "default": DEFAULT_MESSAGE_MAX_CHARS,
            "cli_type_name": "integer",
            "help_text": f"Truncate each @message to this many chars (default {DEFAULT_MESSAGE_MAX_CHARS}).",
        },
        {
            "name": "max-splits",
            "default": 6,
            "cli_type_name": "integer",
            "help_text": "Maximum times a row-capped window is split to recover counts (default 6).",
        },
        {
            "name": "poll-interval",
            "default": 1.0,
            "cli_type_name": "double",
            "help_text": "Initial seconds between GetQueryResults polls (default 1.0).",
        },
        {
            "name": "timeout-seconds",
            "default": 900.0,
            "cli_type_name": "double",
            "help_text": "Maximum seconds to wait per sub-query (default 900).",
        },
        {
            "name": "max-queries",
            "default": 64,
            "cli_type_name": "integer",
            "help_text": (
                "Maximum number of sub-queries (window splits/batches) to run "
                "(default 64)."
            ),
        },
        {
            "name": "max-polls",
            "default": 600,
            "cli_type_name": "integer",
            "help_text": (
                "Maximum GetQueryResults polls per sub-query (default 600)."
            ),
        },
        {
            "name": "max-deadline",
            "default": 3600.0,
            "cli_type_name": "double",
            "help_text": (
                "Overall wall-clock budget in seconds for the whole command "
                "(default 3600). Remaining sub-queries are skipped once it is "
                "exceeded and results come back marked not exhaustive."
            ),
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
            self._session, "logs", parsed_globals
        )

        def call_op(operation, params):
            return call(client, operation, params)

        result = run_insights_query(
            call_op,
            parsed_args.log_group_names,
            parsed_args.query_string,
            parsed_args.start_time,
            parsed_args.end_time,
            since=parsed_args.since,
            max_splits=parsed_args.max_splits,
            max_queries=parsed_args.max_queries,
            max_rows=parsed_args.max_rows,
            max_message_length=parsed_args.max_message_length,
            poll_interval=parsed_args.poll_interval,
            max_polls=parsed_args.max_polls,
            timeout_seconds=parsed_args.timeout_seconds,
            max_deadline=parsed_args.max_deadline,
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


def register(event_handlers):
    event_handlers.register('building-command-table.logs', _inject_commands)


def _inject_commands(command_table, session, **kwargs):
    command_table['run-insights-query'] = RunInsightsQueryCommand(session)
