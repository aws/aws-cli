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
"""``aws ecs diagnose-service`` -- explain why an ECS service is unhealthy.

Callers otherwise hand-roll a long traversal to answer "why is my service not
running?": DescribeServices, DescribeTaskDefinition, ListTasks/DescribeTasks for
both running and stopped tasks, ELBv2 target health, the execution/task role
policies, and the container log stream -- each read paginated and bounded by
hand. This command runs that traversal once, read-only, and returns one
structured diagnosis: the blockers it found, non-fatal warnings, the checks that
passed, ordered remediations, and a per-section availability map so one flaky
optional read never sinks the whole answer.

This command returns a result object from every call and never raises; it keeps
an "errors as data" control flow via the shared
:mod:`awscli.customizations.compositereadonly.helpers` bridge and maps the final result
to a CLI exit code.

Scope note: this command's read surface is deliberately ECS + ELBv2 +
CloudWatch Logs + IAM (the APIs these commands declare). ECR image-existence,
EC2/VPC egress and Auto Scaling capacity checks need clients outside that
surface and are therefore not included here; the accuracy decisions that fit
this surface ARE kept --
the desiredCount=0 "false green", the conservative IAM check (only an outright
missing execution role or a zero-policy role is flagged), target health that is
only a blocker when the service is meant to run tasks, and stopped-task reasons
as ground-truth corroboration. A log-evidence section is added (Logs scope).

Behaviour contract:

* **Gating vs optional reads** -- ``DescribeServices`` is the single gating read;
  a transport/permission failure there is returned verbatim and a missing or
  INACTIVE service is a structured NOT_FOUND. Every other section is optional: a
  failure degrades that section (recorded in ``sections`` and as a warning) and
  the diagnosis continues rather than discarding the evidence already gathered.
* **Bounded fan-out / pagination** -- ``ListTasks`` follows ``nextToken`` under a
  ``--max-pages`` cap; stopped tasks, target groups, log groups and log lines are
  each capped; ``DescribeTasks`` is issued in batches of 100. Every clamp is
  reflected in ``is_exhaustive``.
* **Redaction** -- container environment values are never emitted (names only),
  secret references are surfaced by name only, and every surfaced log line is run
  through :func:`redact_sensitive` before truncation so a password or access key
  in a log message is scrubbed.

Strictly read-only: it only issues ``Describe*`` / ``Get*`` / ``List*`` /
``Filter*`` calls, and the shared :func:`call` bridge refuses any mutating
operation by construction.
"""

from __future__ import annotations

import re
import time
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
from awscli.customizations.compositereadonly.output import (
    DEFAULT_MESSAGE_MAX_CHARS,
    cap_series,
    truncate_field,
)

# A call bridge is (service, operation, params) -> result dict. Unlike the
# single-service sibling commands, diagnose-service spans four services, so the
# bridge is keyed by service and each client is created lazily.
CallFn = Callable[[str, str, dict[str, Any]], dict[str, Any]]

# --- Bounds (defaults; all overridable on the CLI) ---------------------------
_MAX_DESCRIBE_TASKS = 100  # ECS DescribeTasks accepts at most 100 task ARNs.
# Stopped-task reasons that mean the task could not start/stay up. A match
# corroborates an image/network/IAM problem with ground-truth evidence.
_FATAL_TASK_REASONS = (
    "CannotPull",
    "ResourceInitialization",
    "AccessDenied",
    "CannotStart",
    "CannotCreate",
    "OutOfMemory",
    "EssentialContainerExited",
)
# A CloudWatch Logs filter pattern that matches common error markers. The fake
# bridge ignores it in tests; in production it narrows the fetch to error lines.
_ERROR_FILTER = (
    "?ERROR ?Error ?error ?Exception ?Fatal ?FATAL ?fatal ?Traceback"
)

# --- Redaction patterns ------------------------------------------------------
# AWS access-key-id style tokens (AKIA/ASIA/... + 16 upper-alnum chars).
_AWS_KEY_RE = re.compile(
    r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ABIA|ACCA)[0-9A-Z]{16}\b"
)
# A key=value / key: value pair whose key looks sensitive -> scrub the value.
# The key and separator are preserved so the shape of the log stays legible. The
# optional identifier-prefix/suffix lets a sensitive word match even when it is
# embedded in a longer name (e.g. DB_PASSWORD, APP_SECRET_KEY).
_SECRET_KV_RE = re.compile(
    r"(?i)([a-z0-9_]*"
    r"(?:password|passwd|pwd|secret|token|apikey|api[_-]key|"
    r"accesskey|access[_-]key|authorization|bearer)"
    r"[a-z0-9_]*)"
    r"(\s*[=:]\s*|\s+)"
    r"([^\s,;]+)"
)
# The ``\s+`` branch of the separator group matches a secret-like key followed
# only by whitespace and then any token, so free text such as "password is
# required" redacts the following word. This over-redaction of legitimate text
# is intentional: a false positive is preferred over leaking a real secret.


def redact_sensitive(text: Any) -> Any:
    """Scrub secret-looking substrings from free text.

    Redacts AWS access-key-id tokens and the value of any ``key=value`` /
    ``key: value`` pair whose key names a credential (password, secret, token,
    api-key, authorization, ...). Non-strings pass through untouched so callers
    can apply it blindly. This is intentionally conservative -- it never tries to
    guess that an arbitrary opaque string is a secret -- to avoid mangling
    legitimate log content.

    Redaction is best-effort: unlabeled secrets (e.g. bare secret access keys or
    session tokens without a key= prefix) may not be caught.
    """
    if not isinstance(text, str):
        return text
    text = _AWS_KEY_RE.sub("[REDACTED]", text)
    # Replace only the value group, keeping the key and separator verbatim.
    text = _SECRET_KV_RE.sub(
        lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text
    )
    return text


def _blocker(
    kind: str, severity: str, evidence: str, fix: str
) -> dict[str, Any]:
    """Build a blocker/warning dict with a stable shape."""
    return {
        "type": kind,
        "severity": severity,
        "evidence": evidence,
        "fix": fix,
    }


def _chunks(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _task_id(arn: str) -> str:
    return arn.rsplit("/", 1)[-1] if "/" in arn else arn


class _Diagnosis:
    """Accumulator for findings, per-section availability and the degraded flag.

    ``degraded`` records that SOME evidence was lost -- an optional read failed or
    output was capped/truncated -- which is exactly what flips ``is_exhaustive``
    to False. A section deliberately skipped (e.g. ``--no-logs``) is recorded as
    unavailable but does NOT set ``degraded``, because nothing was lost.
    """

    def __init__(self) -> None:
        self.blockers: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.verified_ok: list[str] = []
        self.sections: dict[str, dict[str, Any]] = {}
        self.degraded = False

    def merge(self, findings: tuple[list, list, list]) -> None:
        self.blockers.extend(findings[0])
        self.warnings.extend(findings[1])
        self.verified_ok.extend(findings[2])

    def section_ok(self, name: str) -> None:
        self.sections[name] = {"available": True, "error": None, "code": None}

    def section_skipped(self, name: str) -> None:
        # Intentional skip: unavailable but not a loss of evidence.
        self.sections[name] = {
            "available": False,
            "error": None,
            "code": "SKIPPED",
        }

    def section_failed(self, name: str, res: dict[str, Any]) -> None:
        self.sections[name] = {
            "available": False,
            "error": res.get("error"),
            "code": res.get("code"),
        }
        self.degraded = True


# --------------------------------------------------------------- findings


def _check_desired_count(svc: dict[str, Any]) -> tuple[list, list, list]:
    """desiredCount=0 is the single most common blocker and a 'false green':
    a deployment can report rolloutState=COMPLETED while running zero tasks
    (including the false-positive healthy note when data is partial)."""
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    ok: list[str] = []
    desired = svc.get("desiredCount", 0)
    running = svc.get("runningCount", 0)
    if desired == 0:
        rollout = ""
        deployments = svc.get("deployments", [])
        if deployments:
            rollout = deployments[0].get("rolloutState", "")
        false_green = (
            " (deployment reports COMPLETED, but that is vacuously true at "
            "desiredCount=0)"
            if rollout == "COMPLETED"
            else ""
        )
        blockers.append(
            _blocker(
                "DESIRED_COUNT_ZERO",
                "critical",
                f"desiredCount=0, runningCount={running}{false_green}",
                "Set desiredCount > 0 (UpdateService). For CODE_DEPLOY "
                "services, scale via the deployment, not UpdateService.",
            )
        )
    else:
        ok.append("desired_count")
    if svc.get("deploymentController", {}).get("type") == "CODE_DEPLOY":
        warnings.append(
            _blocker(
                "CODE_DEPLOY_SERVICE",
                "info",
                "Service uses the CODE_DEPLOY deployment controller.",
                "Scale/roll out via CodeDeploy, not a plain UpdateService "
                "desiredCount change.",
            )
        )
    return blockers, warnings, ok


def _role_has_no_policies(
    role_arn: str, call_op: CallFn
) -> tuple[bool | None, bool]:
    """Return (is_empty, read_ok).

    ``is_empty`` is True when the role has neither attached nor inline policies,
    None when it could not be determined. ``read_ok`` is False when either IAM
    read failed, so the caller can mark the IAM section degraded.
    """
    role_name = role_arn.rsplit("/", 1)[-1]
    attached = call_op(
        "iam", "ListAttachedRolePolicies", {"RoleName": role_name}
    )
    inline = call_op("iam", "ListRolePolicies", {"RoleName": role_name})
    if not attached["ok"] or not inline["ok"]:
        return None, False
    has_attached = bool((attached.get("value") or {}).get("AttachedPolicies"))
    has_inline = bool((inline.get("value") or {}).get("PolicyNames"))
    return (not (has_attached or has_inline)), True


def _check_iam(
    task_def: dict[str, Any],
    call_op: CallFn,
    svc: dict[str, Any] | None = None,
) -> tuple[list, list, list, bool, bool]:
    """Conservative IAM check (ported). Only the unambiguous cases are flagged:
    a missing execution role (blocker) or a role with zero policies (warning).
    Deep policy simulation is false-positive prone, so it is deliberately
    avoided. Returns findings plus (attempted, failed) for section bookkeeping.

    When *svc* is provided and the service is running at its desired count, a
    missing execution role is downgraded from a blocker to a warning: the
    service is evidently working without it (e.g. public images, no log driver).
    """
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    ok: list[str] = []
    attempted = False
    failed = False
    exec_arn = task_def.get("executionRoleArn", "")
    if not exec_arn:
        # Downgrade to a warning when the service is running fine without
        # the role (e.g. public images with no awslogs).
        running = (svc or {}).get("runningCount", 0)
        desired = (svc or {}).get("desiredCount", 0)
        service_healthy = (
            svc is not None and desired > 0 and running >= desired
        )
        if service_healthy:
            warnings.append(
                _blocker(
                    "EXECUTION_ROLE_MISSING",
                    "warning",
                    "Task definition has no executionRoleArn. The service "
                    "is running, but an execution role is needed for "
                    "private image pulls and log delivery.",
                    "Attach an execution role with ecr:GetAuthorizationToken, "
                    "ECR pull, and logs:CreateLogStream/PutLogEvents.",
                )
            )
        else:
            blockers.append(
                _blocker(
                    "EXECUTION_ROLE_MISSING",
                    "critical",
                    "Task definition has no executionRoleArn; ECS cannot "
                    "pull images or write logs.",
                    "Attach an execution role with ecr:GetAuthorizationToken, ECR "
                    "pull, and logs:CreateLogStream/PutLogEvents.",
                )
            )
    else:
        attempted = True
        empty, read_ok = _role_has_no_policies(exec_arn, call_op)
        if not read_ok:
            failed = True
            warnings.append(
                _blocker(
                    "IAM_CHECK_DEGRADED",
                    "info",
                    f"Could not read policies for execution role "
                    f"{exec_arn.rsplit('/', 1)[-1]}.",
                    "Re-run with iam:ListAttachedRolePolicies and "
                    "iam:ListRolePolicies permission.",
                )
            )
        elif empty is True:
            warnings.append(
                _blocker(
                    "EXECUTION_ROLE_MISSING_PERMS",
                    "warning",
                    f"Execution role {exec_arn.rsplit('/', 1)[-1]} has no "
                    "attached or inline policies.",
                    "Grant ecr:GetAuthorizationToken, ECR pull, and logs write "
                    "permissions.",
                )
            )
        else:
            ok.append("execution_role")
    task_arn = task_def.get("taskRoleArn", "")
    if task_arn:
        attempted = True
        empty, read_ok = _role_has_no_policies(task_arn, call_op)
        if not read_ok:
            failed = True
        elif empty is True:
            warnings.append(
                _blocker(
                    "TASK_ROLE_MISSING_PERMS",
                    "warning",
                    f"Task role {task_arn.rsplit('/', 1)[-1]} has zero "
                    "policies; the app will have no AWS permissions.",
                    "Attach the permissions the container needs, or remove the "
                    "task role if unused.",
                )
            )
        elif empty is False:
            ok.append("task_role")
    return blockers, warnings, ok, attempted, failed


# --------------------------------------------------------------- tasks


def _list_task_arns(
    call_op: CallFn,
    cluster: str,
    service: str,
    desired_status: str,
    max_pages: int,
) -> tuple[list[str], bool, dict[str, Any] | None]:
    """ListTasks for a service, following nextToken under ``max_pages``.

    Returns (task_arns, pages_truncated, error). ``pages_truncated`` is True when
    the bounded loop stopped with a token still outstanding, so the caller can
    mark the diagnosis non-exhaustive rather than spin forever.
    """
    # The ECS call bridge is ``call_op(service, operation, params)``; the shared
    # helper expects ``call_op(operation, params)``, so bind the "ecs" service.
    # taskArns are strings (not dicts), so keep only the truthy ones, and ECS
    # uses the lower-camel ``nextToken`` field.
    arns, is_exhaustive, err = paginate(
        lambda operation, params: call_op("ecs", operation, params),
        "ListTasks",
        {
            "cluster": cluster,
            "serviceName": service,
            "desiredStatus": desired_status,
        },
        "taskArns",
        max_pages,
        token_field="nextToken",
        item_filter=lambda a: bool(a),
    )
    # A clean finish or an error is not a truncation; only a page-cap stop with a
    # token still pending is. (Callers check ``err`` first, so this value is only
    # consulted on the no-error path.)
    pages_truncated = err is None and not is_exhaustive
    return arns, pages_truncated, err


def _describe_tasks(
    call_op: CallFn, cluster: str, arns: list[str]
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """DescribeTasks in batches of 100 (the API maximum)."""
    tasks: list[dict[str, Any]] = []
    for batch in _chunks(arns, _MAX_DESCRIBE_TASKS):
        res = call_op(
            "ecs", "DescribeTasks", {"cluster": cluster, "tasks": batch}
        )
        if not res["ok"]:
            return tasks, res
        tasks.extend((res.get("value") or {}).get("tasks", []))
    return tasks, None


def _running_tasks(
    call_op: CallFn,
    cluster: str,
    service: str,
    diag: _Diagnosis,
    *,
    max_tasks: int,
    max_pages: int,
) -> dict[str, Any]:
    """Running-task status/health (optional section)."""
    arns, pages_truncated, err = _list_task_arns(
        call_op, cluster, service, "RUNNING", max_pages
    )
    if err is not None:
        diag.section_failed("running_tasks", err)
        return {"count": 0, "tasks": [], "truncated": False}
    capped = len(arns) > max_tasks
    arns, _ = cap_series(arns, max_tasks)
    truncated = capped or pages_truncated
    tasks_out: list[dict[str, Any]] = []
    if arns:
        described, derr = _describe_tasks(call_op, cluster, arns)
        if derr is not None:
            diag.section_failed("running_tasks", derr)
            return {"count": 0, "tasks": [], "truncated": truncated}
        # Cap defensively so the bound stays authoritative.
        described = described[:max_tasks]
        for t in described:
            tasks_out.append(
                {
                    "task_id": _task_id(t.get("taskArn", "")),
                    "status": t.get("lastStatus", "UNKNOWN"),
                    "health": t.get("healthStatus", "UNKNOWN"),
                    "started_at": str(t.get("startedAt", "")),
                    "containers": [
                        {
                            "name": c.get("name"),
                            "last_status": c.get("lastStatus"),
                            "exit_code": c.get("exitCode"),
                            "reason": c.get("reason"),
                        }
                        for c in t.get("containers", [])
                    ],
                }
            )
    diag.section_ok("running_tasks")
    if truncated:
        diag.degraded = True
    return {
        "count": len(tasks_out),
        "tasks": tasks_out,
        "truncated": truncated,
    }


def _stopped_tasks(
    call_op: CallFn,
    cluster: str,
    service: str,
    diag: _Diagnosis,
    *,
    max_stopped_tasks: int,
    max_pages: int,
) -> dict[str, Any]:
    """Stopped tasks + their stop reasons/exit codes (optional section).

    Also derives the STOPPED_TASK_ERRORS blocker from the same data (no extra
    calls): a stopped reason naming an image-pull, init or permission failure is
    ground-truth corroboration of a blocker.
    """
    arns, pages_truncated, err = _list_task_arns(
        call_op, cluster, service, "STOPPED", max_pages
    )
    if err is not None:
        diag.section_failed("stopped_tasks", err)
        return {"count": 0, "tasks": [], "truncated": False}
    capped = len(arns) > max_stopped_tasks
    arns, _ = cap_series(arns, max_stopped_tasks)
    truncated = capped or pages_truncated
    tasks_out: list[dict[str, Any]] = []
    fatal_reasons: list[str] = []
    if arns:
        described, derr = _describe_tasks(call_op, cluster, arns)
        if derr is not None:
            diag.section_failed("stopped_tasks", derr)
            return {"count": 0, "tasks": [], "truncated": truncated}
        # Cap the described tasks defensively (DescribeTasks returns only the
        # ARNs we asked for, but the cap stays authoritative regardless).
        described = described[:max_stopped_tasks]
        for t in described:
            reason = t.get("stoppedReason", "") or ""
            stop_code = t.get("stopCode", "") or ""
            # Check both stoppedReason (human text, e.g. "Essential
            # container in task exited") and stopCode (enum, e.g.
            # "EssentialContainerExited") — either may carry the signal.
            if any(k in reason or k in stop_code for k in _FATAL_TASK_REASONS):
                fatal_reasons.append(reason or stop_code)
            tasks_out.append(
                {
                    "task_id": _task_id(t.get("taskArn", "")),
                    "last_status": t.get("lastStatus", "UNKNOWN"),
                    "stopped_reason": t.get("stoppedReason"),
                    "stop_code": t.get("stopCode"),
                    "task_definition": t.get("taskDefinitionArn"),
                    "containers": [
                        {
                            "name": c.get("name"),
                            "exit_code": c.get("exitCode"),
                            "reason": c.get("reason"),
                            "last_status": c.get("lastStatus"),
                        }
                        for c in t.get("containers", [])
                    ],
                }
            )
    diag.section_ok("stopped_tasks")
    if truncated:
        diag.degraded = True
    if fatal_reasons:
        diag.blockers.append(
            _blocker(
                "STOPPED_TASK_ERRORS",
                "critical",
                f"Recent stopped tasks failed to start: {fatal_reasons[:3]}",
                "Resolve the stopped-task reason (image pull, init, or "
                "permissions) shown in the evidence.",
            )
        )
    # Crash-loop detection: if multiple stopped tasks exited with a non-zero
    # exit code on an essential container, the service is cycling tasks that
    # start successfully but die immediately — different from an image-pull
    # or init failure where the task never starts at all.
    crash_exits = []
    for t in tasks_out:
        sc = t.get("stop_code") or ""
        if "EssentialContainerExited" in sc:
            for c in t.get("containers", []):
                ec = c.get("exit_code")
                if ec is not None and ec != 0:
                    crash_exits.append(
                        {
                            "task": t.get("task_id"),
                            "container": c.get("name"),
                            "exit_code": ec,
                        }
                    )
                    break  # one non-zero exit per task is enough
    if len(crash_exits) >= 2 and "STOPPED_TASK_ERRORS" not in {
        b.get("type") for b in diag.blockers
    }:
        # Only add if STOPPED_TASK_ERRORS didn't already fire — avoid
        # double-flagging when stoppedReason also matched a fatal substring.
        samples = crash_exits[:3]
        codes = ", ".join(
            f"{s['container']}(exit {s['exit_code']})" for s in samples
        )
        diag.blockers.append(
            _blocker(
                "CRASH_LOOP",
                "critical",
                f"Service is crash-looping: {len(crash_exits)} stopped "
                f"tasks exited with non-zero codes: {codes}.",
                "Check container logs and fix the application error. "
                "The container starts but crashes immediately. "
                "Enable the deployment circuit breaker to stop the retry loop.",
            )
        )
    elif crash_exits and "STOPPED_TASK_ERRORS" in {
        b.get("type") for b in diag.blockers
    }:
        # STOPPED_TASK_ERRORS already fired; enrich its evidence with crash
        # info so the user sees both the stopped reason and the exit codes.
        codes = ", ".join(
            f"{s['container']}(exit {s['exit_code']})" for s in crash_exits[:3]
        )
        for b in diag.blockers:
            if b.get("type") == "STOPPED_TASK_ERRORS":
                b["evidence"] += (
                    f" Crash-loop detected: {len(crash_exits)} tasks "
                    f"exited with non-zero codes: {codes}."
                )
                break
    return {
        "count": len(tasks_out),
        "tasks": tasks_out,
        "truncated": truncated,
    }


# --------------------------------------------------------------- target health


def _target_health(
    svc: dict[str, Any],
    call_op: CallFn,
    diag: _Diagnosis,
    *,
    max_target_groups: int,
) -> dict[str, Any]:
    """ELBv2 target-group health for the service's load balancers (optional).

    Also derives the TARGET_GROUP_UNHEALTHY blocker, but only when the service is
    meant to run tasks (desiredCount>0) -- an empty target group at
    desiredCount=0 is expected, not a blocker (ported accuracy guard).
    """
    tg_arns = [
        lb.get("targetGroupArn")
        for lb in svc.get("loadBalancers", [])
        if lb.get("targetGroupArn")
    ]
    if not tg_arns:
        # No load balancer wired: not an error, nothing to query.
        diag.section_ok("target_health")
        return {"wired": False, "target_groups": []}
    capped = len(tg_arns) > max_target_groups
    tg_arns, _ = cap_series(tg_arns, max_target_groups)
    if capped:
        diag.degraded = True
    desired = svc.get("desiredCount", 0)
    groups: list[dict[str, Any]] = []
    any_failed = False
    for tg in tg_arns:
        th = call_op("elbv2", "DescribeTargetHealth", {"TargetGroupArn": tg})
        if not th["ok"]:
            any_failed = True
            groups.append({"target_group_arn": tg, "error": th.get("error")})
            continue
        descriptions = (th.get("value") or {}).get(
            "TargetHealthDescriptions", []
        )
        healthy = 0
        unhealthy: list[dict[str, Any]] = []
        for d in descriptions:
            health = d.get("TargetHealth", {}) or {}
            state = health.get("State", "")
            if state == "healthy":
                healthy += 1
            else:
                unhealthy.append(
                    {
                        "target": (d.get("Target", {}) or {}).get("Id"),
                        "state": state,
                        "reason": health.get("Reason"),
                        "description": health.get("Description"),
                    }
                )
        groups.append(
            {
                "target_group_arn": tg,
                "healthy": healthy,
                "total": len(descriptions),
                "unhealthy": unhealthy,
            }
        )
        # Only a blocker when the service should have running, healthy targets.
        if desired > 0 and healthy == 0:
            diag.blockers.append(
                _blocker(
                    "TARGET_GROUP_UNHEALTHY",
                    "critical",
                    f"Target group {tg.rsplit('/', 1)[-1]} has no healthy "
                    f"targets ({len(descriptions)} registered).",
                    "Fix the task health so targets pass health checks; verify "
                    "the health-check path/port and SG rules.",
                )
            )
    if any_failed:
        # Record a degraded section but keep the groups that did resolve.
        diag.sections["target_health"] = {
            "available": False,
            "error": "one or more DescribeTargetHealth calls failed",
            "code": SERVICE_ERROR,
        }
        diag.degraded = True
    else:
        diag.section_ok("target_health")
    return {"wired": True, "target_groups": groups}


# --------------------------------------------------------------- log evidence


def _awslogs_groups(containers: list[dict[str, Any]], cap: int) -> list[str]:
    """Distinct awslogs log-group names from the container definitions (capped).

    Order-preserving de-dup so the output is stable; only the ``awslogs`` driver
    is understood (other drivers write elsewhere).
    """
    groups: list[str] = []
    for c in containers:
        log_cfg = c.get("logConfiguration") or {}
        if log_cfg.get("logDriver") != "awslogs":
            continue
        group = (log_cfg.get("options") or {}).get("awslogs-group")
        if group and group not in groups:
            groups.append(group)
    return groups[:cap]


def _log_evidence(
    containers: list[dict[str, Any]],
    call_op: CallFn,
    diag: _Diagnosis,
    *,
    include_logs: bool,
    clock: Callable[[], float],
    max_log_groups: int,
    max_log_lines: int,
    log_window_minutes: int,
    max_message_length: int,
) -> dict[str, Any]:
    """Recent error-ish log lines from the task's awslogs groups (optional).

    Every surfaced message is redacted (:func:`redact_sensitive`) and then
    truncated to ``max_message_length`` so a secret cannot leak and one huge line
    cannot dominate the output. The total is capped at ``max_log_lines``.
    """
    if not include_logs:
        diag.section_skipped("log_evidence")
        return {"groups": [], "lines": [], "truncated": False}
    groups = _awslogs_groups(containers, max_log_groups)
    if not groups:
        # Nothing to fetch (no awslogs driver); report as unavailable, no loss.
        diag.section_skipped("log_evidence")
        return {"groups": [], "lines": [], "truncated": False}
    now_ms = int(clock() * 1000)
    start_ms = now_ms - log_window_minutes * 60 * 1000
    lines: list[dict[str, Any]] = []
    truncated = False
    any_failed = False
    for group in groups:
        if len(lines) >= max_log_lines:
            truncated = True
            break
        res = call_op(
            "logs",
            "FilterLogEvents",
            {
                "logGroupName": group,
                "startTime": start_ms,
                "endTime": now_ms,
                "filterPattern": _ERROR_FILTER,
                "limit": max_log_lines,
            },
        )
        if not res["ok"]:
            any_failed = True
            continue
        for ev in (res.get("value") or {}).get("events", []):
            if len(lines) >= max_log_lines:
                truncated = True
                break
            # Redact THEN truncate: redaction must see the whole token, and the
            # truncation keeps the (already-scrubbed) head where the error is.
            message = redact_sensitive(ev.get("message", ""))
            message, _ = truncate_field(message, max_message_length)
            lines.append(
                {
                    "log_group": group,
                    "log_stream": ev.get("logStreamName"),
                    "timestamp": ev.get("timestamp"),
                    "message": message,
                }
            )
    if any_failed:
        diag.sections["log_evidence"] = {
            "available": False,
            "error": "one or more FilterLogEvents calls failed",
            "code": SERVICE_ERROR,
        }
        diag.degraded = True
    else:
        diag.section_ok("log_evidence")
    if truncated:
        diag.degraded = True
    return {"groups": groups, "lines": lines, "truncated": truncated}


# --------------------------------------------------------------- task definition


def _task_definition_section(
    task_def: dict[str, Any],
) -> dict[str, Any]:
    """Shape the task definition for output: images, roles and a redacted
    container config (environment NAMES only -- values are never emitted -- and
    secret references by name only)."""
    containers = []
    for c in task_def.get("containerDefinitions", []):
        log_cfg = c.get("logConfiguration") or {}
        containers.append(
            {
                "name": c.get("name"),
                "image": c.get("image"),
                # Command and entrypoint help diagnose crash loops where the
                # container starts but exits immediately.
                "command": c.get("command"),
                "entry_point": c.get("entryPoint"),
                # Names only: an environment value may be a secret, so it is
                # never surfaced.
                "environment_names": [
                    e.get("name")
                    for e in c.get("environment", [])
                    if e.get("name")
                ],
                "secret_names": [
                    s.get("name")
                    for s in c.get("secrets", [])
                    if s.get("name")
                ],
                "log_configuration": {
                    "log_driver": log_cfg.get("logDriver"),
                    "awslogs_group": (log_cfg.get("options") or {}).get(
                        "awslogs-group"
                    ),
                },
            }
        )
    return {
        "family": task_def.get("family"),
        "revision": task_def.get("revision"),
        "arn": task_def.get("taskDefinitionArn"),
        "execution_role": task_def.get("executionRoleArn"),
        "task_role": task_def.get("taskRoleArn"),
        "containers": containers,
    }


# --------------------------------------------------------------- the diagnosis


def _validate(
    service: Any,
    cluster: Any,
    caps: dict[str, Any],
) -> dict[str, Any] | None:
    """Pre-dispatch input validation (makes no AWS calls)."""
    svc_err = check_non_empty_str("service", service, required=False)
    if svc_err is not None:
        return invalid_input(
            f"{svc_err} (the ECS service name or ARN).",
            ["Pass --service <name>."],
        )
    cluster_err = check_non_empty_str("cluster", cluster, required=False)
    if cluster_err is not None:
        return invalid_input(
            cluster_err,
            ["Pass --cluster <name> (default 'default')."],
        )
    for name, val in caps.items():
        err = check_positive_int(name, val)
        if err is not None:
            return invalid_input(
                err,
                [f"Pass a positive {name}."],
            )
    return None


def diagnose_ecs_service(
    call_op: CallFn,
    service: str,
    *,
    cluster: str = "default",
    region: str | None = None,
    include_logs: bool = True,
    max_events: int = 10,
    max_stopped_tasks: int = 20,
    max_tasks: int = 100,
    max_target_groups: int = 10,
    max_log_lines: int = 20,
    max_log_groups: int = 5,
    log_window_minutes: int = 60,
    max_message_length: int = DEFAULT_MESSAGE_MAX_CHARS,
    max_pages: int = 10,
    clock: Callable[[], float] | None = None,
) -> dict[str, Any]:
    """Diagnose why an ECS service is unhealthy -- in ONE read-only call.

    ``call_op(service, operation, params)`` is the shared read-only call bridge
    keyed by service (ecs/elbv2/logs/iam). Returns the plain-dict result
    convention (see :mod:`...compositereadonly.helpers`); never raises. ``DescribeServices``
    is the only gating read: a failure there is returned verbatim and a missing or
    INACTIVE service is a structured NOT_FOUND. Every other section is optional
    and degrades independently. ``is_exhaustive`` is False whenever any optional
    read failed or output was capped/truncated.
    """
    clock = time.time if clock is None else clock
    try:
        bad = _validate(
            service,
            cluster,
            {
                "max_events": max_events,
                "max_stopped_tasks": max_stopped_tasks,
                "max_tasks": max_tasks,
                "max_target_groups": max_target_groups,
                "max_log_lines": max_log_lines,
                "max_log_groups": max_log_groups,
                "log_window_minutes": log_window_minutes,
                "max_message_length": max_message_length,
                "max_pages": max_pages,
            },
        )
        if bad is not None:
            return bad
        return _run(
            call_op,
            service.strip(),
            cluster=cluster.strip(),
            region=region,
            include_logs=include_logs,
            max_events=max_events,
            max_stopped_tasks=max_stopped_tasks,
            max_tasks=max_tasks,
            max_target_groups=max_target_groups,
            max_log_lines=max_log_lines,
            max_log_groups=max_log_groups,
            log_window_minutes=log_window_minutes,
            max_message_length=max_message_length,
            max_pages=max_pages,
            clock=clock,
        )
    except Exception as exc:  # noqa: BLE001 - contract: never raise
        return err_result(
            SERVICE_ERROR,
            f"diagnose-service internal error: {exc!r}",
            guidance=[
                "Unexpected response shape; retry once, then fall back to "
                "ecs:DescribeServices by hand."
            ],
        )


def _run(
    call_op: CallFn,
    service: str,
    *,
    cluster: str,
    region: str | None,
    include_logs: bool,
    max_events: int,
    max_stopped_tasks: int,
    max_tasks: int,
    max_target_groups: int,
    max_log_lines: int,
    max_log_groups: int,
    log_window_minutes: int,
    max_message_length: int,
    max_pages: int,
    clock: Callable[[], float],
) -> dict[str, Any]:
    # --- gating read: DescribeServices -------------------------------------
    svc_res = call_op(
        "ecs",
        "DescribeServices",
        {"cluster": cluster, "services": [service]},
    )
    if not svc_res["ok"]:
        return svc_res  # propagate transport/permission errors verbatim
    services = (svc_res.get("value") or {}).get("services", [])
    if not services or services[0].get("status") == "INACTIVE":
        return err_result(
            NOT_FOUND,
            f"Service '{service}' not found in cluster '{cluster}'",
            key=service,
            guidance=[
                "Check the cluster (--cluster) and region; list services with "
                "ecs:ListServices."
            ],
        )
    svc = services[0]
    diag = _Diagnosis()

    # 1. Cheapest + most common blocker first (pure logic, no API call).
    diag.merge(_check_desired_count(svc))

    # 2. Task definition drives the IAM check, the config summary and the log
    #    groups. Its failure is a warning, not fatal.
    task_def: dict[str, Any] = {}
    container_defs: list[dict[str, Any]] = []
    td_ref = svc.get("taskDefinition", "")
    task_definition_out: dict[str, Any] = {}
    if td_ref:
        td = call_op(
            "ecs", "DescribeTaskDefinition", {"taskDefinition": td_ref}
        )
        if td["ok"]:
            task_def = (td.get("value") or {}).get("taskDefinition", {})
            container_defs = task_def.get("containerDefinitions", [])
            task_definition_out = _task_definition_section(task_def)
            diag.section_ok("task_definition")
        else:
            diag.section_failed("task_definition", td)
            diag.warnings.append(
                _blocker(
                    "TASK_DEF_UNREADABLE",
                    "info",
                    f"Could not read task definition ({td.get('code')}: "
                    f"{td.get('error')}).",
                    "Re-run with ecs:DescribeTaskDefinition permission.",
                )
            )

    # 3. IAM check (only if the task definition was readable).
    if task_def:
        blockers, warnings, ok, attempted, failed = _check_iam(
            task_def, call_op, svc=svc
        )
        diag.merge((blockers, warnings, ok))
        if attempted and failed:
            diag.sections["iam"] = {
                "available": False,
                "error": "an IAM policy read failed",
                "code": SERVICE_ERROR,
            }
            diag.degraded = True
        elif attempted:
            diag.section_ok("iam")

    # 4. Stopped tasks (ground-truth failure reasons + blocker) then running
    #    tasks. Each is optional and degrades independently.
    stopped = _stopped_tasks(
        call_op,
        cluster,
        service,
        diag,
        max_stopped_tasks=max_stopped_tasks,
        max_pages=max_pages,
    )
    # Enrich crash-loop or STOPPED_TASK_ERRORS blockers with the container
    # command from the task definition — the root cause an agent needs.
    if task_def:
        for b in diag.blockers:
            if b.get("type") in ("CRASH_LOOP", "STOPPED_TASK_ERRORS") and (
                "Crash-loop" in b.get("evidence", "")
                or b.get("type") == "CRASH_LOOP"
            ):
                cmds = []
                for c in task_def.get("containerDefinitions", []):
                    cmd = c.get("command")
                    ep = c.get("entryPoint")
                    if cmd or ep:
                        parts = []
                        if ep:
                            parts.append(f"entryPoint={ep}")
                        if cmd:
                            parts.append(f"command={cmd}")
                        cmds.append(
                            f"{c.get('name', '?')}: {', '.join(parts)}"
                        )
                if cmds:
                    b["evidence"] += f" Container config: {'; '.join(cmds)}."
                break  # only one crash-loop blocker per run
    running = _running_tasks(
        call_op,
        cluster,
        service,
        diag,
        max_tasks=max_tasks,
        max_pages=max_pages,
    )

    # 5. Target health (+ blocker when desiredCount>0 and no healthy targets).
    target_health = _target_health(
        svc, call_op, diag, max_target_groups=max_target_groups
    )

    # 6. Log evidence from the task's awslogs groups (redacted + capped).
    log_evidence = _log_evidence(
        container_defs,
        call_op,
        diag,
        include_logs=include_logs,
        clock=clock,
        max_log_groups=max_log_groups,
        max_log_lines=max_log_lines,
        log_window_minutes=log_window_minutes,
        max_message_length=max_message_length,
    )

    # --- assemble the diagnosis --------------------------------------------
    deployment_config = svc.get("deploymentConfiguration", {}) or {}
    cb = deployment_config.get("deploymentCircuitBreaker", {}) or {}
    deployment = {
        "service_status": svc.get("status", "UNKNOWN"),
        "circuit_breaker": {
            "enabled": bool(cb.get("enable", False)),
            "rollback": bool(cb.get("rollback", False)),
        },
        "deployments": [
            {
                "id": d.get("id"),
                "status": d.get("status"),
                "task_definition": d.get("taskDefinition"),
                "desired_count": d.get("desiredCount"),
                "running_count": d.get("runningCount"),
                "pending_count": d.get("pendingCount"),
                "failed_tasks": d.get("failedTasks"),
                "rollout_state": d.get("rolloutState"),
                "rollout_state_reason": d.get("rolloutStateReason"),
            }
            for d in svc.get("deployments", [])
        ],
    }
    recent_events, events_dropped = cap_series(
        [
            {
                "created_at": str(e.get("createdAt", "")),
                "message": e.get("message", ""),
            }
            for e in svc.get("events", [])
        ],
        max_events,
    )

    recommendations = [f"[{b['type']}] {b['fix']}" for b in diag.blockers]
    value = {
        "service": service,
        "cluster": cluster,
        "region": region,
        "healthy": not diag.blockers,
        "service_summary": {
            "desired_count": svc.get("desiredCount", 0),
            "running_count": svc.get("runningCount", 0),
            "pending_count": svc.get("pendingCount", 0),
            "launch_type": svc.get("launchType", ""),
            "status": svc.get("status", ""),
            "task_definition": svc.get("taskDefinition"),
        },
        "blockers": diag.blockers,
        "warnings": diag.warnings,
        "verified_ok": diag.verified_ok,
        "recommendations": recommendations,
        "deployment": deployment,
        "recent_events": recent_events,
        "stopped_tasks": stopped,
        "running_tasks": running,
        "target_health": target_health,
        "task_definition": task_definition_out,
        "log_evidence": log_evidence,
        "sections": diag.sections,
    }
    return ok_result(
        value,
        key=service,
        is_exhaustive=not diag.degraded,
        guidance=recommendations,
    )


# ------------------------------------------------------------- CLI plumbing


def register(event_handlers):
    """Inject the ``diagnose-service`` verb into the ecs command table."""
    event_handlers.register("building-command-table.ecs", _inject_commands)


def _inject_commands(command_table, session, **kwargs):
    command_table["diagnose-service"] = DiagnoseServiceCommand(session)


# ------------------------------------------------------------ cluster discovery


def _find_cluster_for_service(
    call_op: CallFn,
    service: str,
    *,
    max_pages: int = 10,
) -> str | None:
    """Find which cluster owns a service by scanning all clusters.

    Returns the cluster ARN if found, None otherwise (falls back to the
    default cluster). Short-circuits on the first match.
    """

    def ecs_call(op, params):
        return call_op("ecs", op, params)

    cluster_arns, _, err = paginate(
        ecs_call,
        "ListClusters",
        {},
        "clusterArns",
        max_pages,
        token_field="nextToken",
    )
    if err is not None or not cluster_arns:
        return None

    for cluster_arn in cluster_arns:
        svc_arns, _, svc_err = paginate(
            ecs_call,
            "ListServices",
            {"cluster": cluster_arn},
            "serviceArns",
            max_pages,
            token_field="nextToken",
        )
        if svc_err is not None:
            continue
        # Match by service name or full ARN
        for arn in svc_arns:
            svc_name = arn.split("/")[-1] if "/" in arn else arn
            if svc_name == service or arn == service:
                return cluster_arn
    return None


# ------------------------------------------------------------ triage mode

_DESCRIBE_BATCH = 10  # ECS DescribeServices limit


def _triage_mode(
    call_op: CallFn,
    *,
    region: str | None,
    include_logs: bool,
    max_clusters: int,
    max_events: int,
    max_stopped_tasks: int,
    max_tasks: int,
    max_target_groups: int,
    max_log_lines: int,
    max_log_groups: int,
    log_window_minutes: int,
    max_message_length: int,
    max_pages: int,
    clock: Callable[[], float] | None = None,
) -> dict[str, Any]:
    """Triage mode: discover all services, find unhealthy ones, diagnose only those.

    Returns a multi-service result envelope with a triage summary.
    """
    import time as _time

    clock = _time.time if clock is None else clock

    # -- Step 1: Discover clusters ------------------------------------------
    cluster_arns, cl_exhaustive, cl_err = paginate(
        lambda op, params: call_op("ecs", op, params),
        "ListClusters",
        {},
        "clusterArns",
        max_pages,
        token_field="nextToken",
    )
    if cl_err is not None:
        return cl_err
    cluster_arns = cluster_arns[:max_clusters]

    if not cluster_arns:
        return ok_result(
            {
                "mode": "triage",
                "region": region,
                "clusters_scanned": 0,
                "services_scanned": 0,
                "unhealthy": [],
                "healthy_count": 0,
                "diagnoses": [],
            },
            is_exhaustive=True,
            guidance=["No ECS clusters found in this region."],
        )

    # -- Step 2: List + describe services per cluster, find broken ones ------
    all_services: list[dict[str, Any]] = []
    unhealthy_targets: list[tuple[str, str]] = []  # (cluster, service_name)

    def ecs_call(op, params):
        return call_op("ecs", op, params)

    for cluster_arn in cluster_arns:
        svc_arns, _, svc_err = paginate(
            ecs_call,
            "ListServices",
            {"cluster": cluster_arn},
            "serviceArns",
            max_pages,
            token_field="nextToken",
        )
        if svc_err is not None:
            continue  # skip clusters we can't list

        if not svc_arns:
            continue

        # Describe in batches of 10
        for i in range(0, len(svc_arns), _DESCRIBE_BATCH):
            batch = svc_arns[i : i + _DESCRIBE_BATCH]
            res = ecs_call(
                "DescribeServices",
                {"cluster": cluster_arn, "services": batch},
            )
            if not res["ok"]:
                continue

            for svc in (res.get("value") or {}).get("services", []):
                desired = svc.get("desiredCount", 0)
                running = svc.get("runningCount", 0)
                svc_name = svc.get("serviceName", "")
                cluster_name = (
                    cluster_arn.split("/")[-1]
                    if "/" in cluster_arn
                    else cluster_arn
                )

                all_services.append(
                    {
                        "cluster": cluster_name,
                        "service": svc_name,
                        "desired": desired,
                        "running": running,
                        "status": svc.get("status", ""),
                    }
                )

                if desired > 0 and running < desired:
                    unhealthy_targets.append((cluster_arn, svc_name))

    # -- Step 2b: Catch crash loops that pass the count check ---------------
    # A crash-looping service may briefly show running == desired between
    # restarts.  Check for recent stopped tasks on services not already
    # flagged — a service with stopped tasks and a suspicious deployment
    # (recent events cycling "started" / "steady state") is crash-looping.
    already_flagged = {s for _, s in unhealthy_targets}
    for svc_info in all_services:
        svc_name = svc_info["service"]
        if svc_name in already_flagged:
            continue
        cluster_name = svc_info["cluster"]
        # Find the full cluster ARN for this service
        cluster_arn_for_svc = None
        for ca in cluster_arns:
            short = ca.split("/")[-1] if "/" in ca else ca
            if short == cluster_name:
                cluster_arn_for_svc = ca
                break
        if cluster_arn_for_svc is None:
            continue
        # Quick check: any stopped tasks at all?
        stopped_arns, _, stopped_err = paginate(
            ecs_call,
            "ListTasks",
            {
                "cluster": cluster_arn_for_svc,
                "serviceName": svc_name,
                "desiredStatus": "STOPPED",
            },
            "taskArns",
            1,  # just 1 page to see if any exist
            token_field="nextToken",
        )
        if stopped_err is not None:
            continue
        if len(stopped_arns) >= 3:
            # 3+ stopped tasks on a "healthy" service = likely crash loop
            unhealthy_targets.append((cluster_arn_for_svc, svc_name))

    # -- Step 3: Deep diagnose only the broken services ---------------------
    diagnoses: list[dict[str, Any]] = []
    for cluster_arn, svc_name in unhealthy_targets:
        cluster_short = (
            cluster_arn.split("/")[-1] if "/" in cluster_arn else cluster_arn
        )
        diag_result = _run(
            call_op,
            svc_name,
            cluster=cluster_arn,
            region=region,
            include_logs=include_logs,
            max_events=max_events,
            max_stopped_tasks=max_stopped_tasks,
            max_tasks=max_tasks,
            max_target_groups=max_target_groups,
            max_log_lines=max_log_lines,
            max_log_groups=max_log_groups,
            log_window_minutes=log_window_minutes,
            max_message_length=max_message_length,
            max_pages=max_pages,
            clock=clock,
        )
        # Wrap the _run result into the envelope
        if diag_result.get("ok"):
            diagnoses.append(diag_result.get("value", {}))
        else:
            diagnoses.append(
                {
                    "service": svc_name,
                    "cluster": cluster_short,
                    "error": diag_result.get("error"),
                    "code": diag_result.get("code"),
                }
            )

    guidance = []
    if not unhealthy_targets:
        guidance.append("All services are running at their desired count.")

    return ok_result(
        {
            "mode": "triage",
            "region": region,
            "clusters_scanned": len(cluster_arns),
            "services_scanned": len(all_services),
            "unhealthy_count": len(unhealthy_targets),
            "healthy_count": len(all_services) - len(unhealthy_targets),
            "unhealthy": [
                {"cluster": c.split("/")[-1] if "/" in c else c, "service": s}
                for c, s in unhealthy_targets
            ],
            "diagnoses": diagnoses,
        },
        is_exhaustive=cl_exhaustive,
        guidance=guidance,
    )


class DiagnoseServiceCommand(BasicCommand):
    NAME = "diagnose-service"
    DESCRIPTION = (
        "Explain why an ECS service is unhealthy in one read-only call.\n\n"
        "Use this command when you need a full diagnostic view of an ECS "
        "service. It gathers the service configuration, task definitions, "
        "running and stopped tasks, recent events, "
        "log evidence, and load balancer health in one call with automatic "
        "secret redaction.\n\n"
        "Reads "
        "the service (the gating read), its task definition, running and "
        "stopped tasks (with stop reasons and container exit codes), ELBv2 "
        "target health, the execution/task role policies and recent error log "
        "lines, and returns one structured diagnosis: blockers, warnings, the "
        "checks that passed, ordered remediations and a per-section "
        "availability map. Environment values and secret-looking log tokens are "
        "redacted; output is bounded. A missing/INACTIVE service is NOT_FOUND; "
        "any optional read failing degrades only its section. Strictly "
        "read-only: only Describe/Get/List/Filter calls are ever issued."
    )
    EXAMPLES = (
        "To diagnose a service in the default cluster::\n\n"
        "  aws ecs diagnose-service --service my-svc\n\n"
        "To diagnose a service in a named cluster without fetching logs::\n\n"
        "  aws ecs diagnose-service --service my-svc --cluster prod "
        "--no-logs\n"
    )
    ARG_TABLE = [
        {
            "name": "service",
            "cli_type_name": "string",
            "help_text": (
                "ECS service name (or ARN) to diagnose. If omitted, "
                "discovers all services across clusters, identifies "
                "unhealthy ones (running < desired), and diagnoses only those."
            ),
        },
        {
            "name": "cluster",
            "default": "default",
            "cli_type_name": "string",
            "help_text": (
                "ECS cluster name (default 'default'). When --service is "
                "omitted, ignored in favour of scanning all clusters."
            ),
        },
        {
            "name": "max-clusters",
            "default": 10,
            "cli_type_name": "integer",
            "help_text": (
                "Maximum clusters to scan in triage mode (default 10). "
                "Ignored when --service is provided."
            ),
        },
        {
            "name": "max-events",
            "default": 10,
            "cli_type_name": "integer",
            "help_text": "Maximum recent service events to return (default 10).",
        },
        {
            "name": "max-stopped-tasks",
            "default": 20,
            "cli_type_name": "integer",
            "help_text": "Maximum stopped tasks to inspect (default 20).",
        },
        {
            "name": "max-tasks",
            "default": 100,
            "cli_type_name": "integer",
            "help_text": "Maximum running tasks to inspect (default 100).",
        },
        {
            "name": "max-target-groups",
            "default": 10,
            "cli_type_name": "integer",
            "help_text": "Maximum target groups to check (default 10).",
        },
        {
            "name": "max-log-lines",
            "default": 20,
            "cli_type_name": "integer",
            "help_text": "Maximum log lines to return (default 20).",
        },
        {
            "name": "max-log-groups",
            "default": 5,
            "cli_type_name": "integer",
            "help_text": "Maximum awslogs groups to read (default 5).",
        },
        {
            "name": "log-window-minutes",
            "default": 60,
            "cli_type_name": "integer",
            "help_text": "Look-back window for log evidence in minutes (default 60).",
        },
        {
            "name": "max-message-length",
            "default": DEFAULT_MESSAGE_MAX_CHARS,
            "cli_type_name": "integer",
            "help_text": (
                "Truncate each log message to this many chars "
                f"(default {DEFAULT_MESSAGE_MAX_CHARS})."
            ),
        },
        {
            "name": "max-pages",
            "default": 10,
            "cli_type_name": "integer",
            "help_text": "Maximum nextToken pages per paginated read (default 10).",
        },
        {
            "name": "no-logs",
            "action": "store_true",
            "default": False,
            "help_text": "Skip the CloudWatch Logs evidence fetch.",
        },
    ]

    def __init__(
        self, session, clients=None, stdout=None, stderr=None, clock=None
    ):
        super().__init__(session)
        self._clients = clients or {}
        self._stdout = stdout
        self._stderr = stderr
        self._clock = clock

    def _run_main(self, parsed_args, parsed_globals):
        # Lazily create one read-only client per service, honouring
        # --region/--endpoint-url/--verify-ssl via the shared helper.
        cache = dict(self._clients)

        def call_op(service, operation, params):
            client = cache.get(service)
            if client is None:
                client = cache[service] = create_read_client(
                    self._session, service, parsed_globals
                )
            return call(client, operation, params)

        service = getattr(parsed_args, "service", None)
        region = getattr(parsed_globals, "region", None)

        if service:
            # --- Single-service mode (original behaviour) ------------------
            cluster = parsed_args.cluster
            # Auto-discover cluster when the user didn't specify one
            # (default is "default", which rarely exists).
            if cluster == "default":
                found = _find_cluster_for_service(
                    call_op, service, max_pages=parsed_args.max_pages
                )
                if found is not None:
                    cluster = found
            result = diagnose_ecs_service(
                call_op,
                service,
                cluster=cluster,
                region=region,
                include_logs=not parsed_args.no_logs,
                max_events=parsed_args.max_events,
                max_stopped_tasks=parsed_args.max_stopped_tasks,
                max_tasks=parsed_args.max_tasks,
                max_target_groups=parsed_args.max_target_groups,
                max_log_lines=parsed_args.max_log_lines,
                max_log_groups=parsed_args.max_log_groups,
                log_window_minutes=parsed_args.log_window_minutes,
                max_message_length=parsed_args.max_message_length,
                max_pages=parsed_args.max_pages,
                clock=self._clock,
            )
        else:
            # --- Triage mode: discover → filter → diagnose broken only -----
            result = _triage_mode(
                call_op,
                region=region,
                include_logs=not parsed_args.no_logs,
                max_clusters=parsed_args.max_clusters,
                max_events=parsed_args.max_events,
                max_stopped_tasks=parsed_args.max_stopped_tasks,
                max_tasks=parsed_args.max_tasks,
                max_target_groups=parsed_args.max_target_groups,
                max_log_lines=parsed_args.max_log_lines,
                max_log_groups=parsed_args.max_log_groups,
                log_window_minutes=parsed_args.log_window_minutes,
                max_message_length=parsed_args.max_message_length,
                max_pages=parsed_args.max_pages,
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
