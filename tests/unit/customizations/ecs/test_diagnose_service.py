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
"""Unit tests for ``aws ecs diagnose-service`` (diagnose_ecs_service logic).

These exercise the pure, read-only diagnosis function with a scripted call
bridge so no network, clients or wall clock are involved. The scripted bridge
mirrors the real one: it refuses any mutating operation, so a test fails if the
command ever reaches for a write API.
"""

from awscli.customizations.ecs.diagnose_service import (
    diagnose_ecs_service,
    redact_sensitive,
)
from awscli.customizations.compositereadonly.helpers import (
    assert_read_only,
    err_result,
    ok_result,
)

# Operations that would create, modify or delete state. No test ever queues one;
# the scripted bridge's assert_read_only would raise, and _no_writes() asserts
# the recorded calls never include one.
_MUTATING = {
    ("ecs", "UpdateService"),
    ("ecs", "CreateService"),
    ("ecs", "RegisterTaskDefinition"),
    ("ecs", "RunTask"),
    ("ecs", "DeleteService"),
    ("iam", "AttachRolePolicy"),
    ("elbv2", "RegisterTargets"),
    ("logs", "PutLogEvents"),
}

_TASK_DEF_ARN = "arn:aws:ecs:us-east-1:111122223333:task-definition/web:5"


class ScriptedECS:
    """A scripted (service, operation, params) read-only call bridge.

    Records every call and returns queued results keyed by (service, operation);
    an unqueued read returns an empty ok_result so optional sections degrade to
    "empty" rather than erroring.
    """

    def __init__(self):
        self.calls = []
        self._responses = {}

    def queue(self, service, operation, *results):
        self._responses.setdefault((service, operation), []).extend(results)
        return self

    def __call__(self, service, operation, params):
        # Mirror the real bridge: every operation must be read-only.
        assert_read_only(operation)
        self.calls.append((service, operation, params))
        queued = self._responses.get((service, operation))
        if queued:
            return queued.pop(0)
        return ok_result({})

    def ops(self):
        return [(s, o) for s, o, _ in self.calls]


def _fake_clock():
    # Fixed epoch so the log-evidence time window is deterministic.
    return lambda: 1_700_000_000.0


def _svc(
    *,
    status="ACTIVE",
    desired=2,
    running=2,
    pending=0,
    launch_type="FARGATE",
    task_def=_TASK_DEF_ARN,
    deployments=None,
    events=None,
    load_balancers=None,
    circuit=None,
):
    if deployments is None:
        deployments = [
            {
                "id": "ecs-svc/1",
                "status": "PRIMARY",
                "taskDefinition": task_def,
                "desiredCount": desired,
                "runningCount": running,
                "pendingCount": pending,
                "failedTasks": 0,
                "rolloutState": "COMPLETED",
                "rolloutStateReason": "ECS deployment completed.",
            }
        ]
    if events is None:
        events = [
            {
                "createdAt": "2026-01-01T00:00:00Z",
                "message": "has reached a steady state.",
            }
        ]
    svc = {
        "serviceName": "web",
        "serviceArn": "arn:aws:ecs:us-east-1:111122223333:service/prod/web",
        "status": status,
        "desiredCount": desired,
        "runningCount": running,
        "pendingCount": pending,
        "launchType": launch_type,
        "taskDefinition": task_def,
        "deployments": deployments,
        "events": events,
        "loadBalancers": load_balancers or [],
    }
    if circuit is not None:
        svc["deploymentConfiguration"] = {"deploymentCircuitBreaker": circuit}
    return svc


def _describe_services(*svcs, failures=None):
    return ok_result({"services": list(svcs), "failures": failures or []})


def _task_def(
    *,
    exec_role="arn:aws:iam::111122223333:role/ecsTaskExecutionRole",
    task_role=None,
    containers=None,
):
    if containers is None:
        containers = [
            {
                "name": "web",
                "image": "111122223333.dkr.ecr.us-east-1.amazonaws.com/web:1",
                "environment": [
                    {"name": "LOG_LEVEL", "value": "INFO"},
                    {"name": "DB_PASSWORD", "value": "hunter2"},
                ],
                "secrets": [
                    {
                        "name": "API_TOKEN",
                        "valueFrom": (
                            "arn:aws:ssm:us-east-1:111122223333:"
                            "parameter/api-token"
                        ),
                    }
                ],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": "/ecs/web",
                        "awslogs-stream-prefix": "ecs",
                        "awslogs-region": "us-east-1",
                    },
                },
            }
        ]
    td = {"family": "web", "revision": 5, "taskDefinitionArn": _TASK_DEF_ARN}
    if exec_role:
        td["executionRoleArn"] = exec_role
    if task_role:
        td["taskRoleArn"] = task_role
    td["containerDefinitions"] = containers
    return ok_result({"taskDefinition": td})


def _iam_with_policies():
    """IAM reads for a role that HAS policies (attached)."""
    return (
        ok_result({"AttachedPolicies": [{"PolicyName": "exec"}]}),
        ok_result({"PolicyNames": []}),
    )


def _diag(call, **kwargs):
    kwargs.setdefault("cluster", "prod")
    kwargs.setdefault("clock", _fake_clock())
    return diagnose_ecs_service(call, "web", **kwargs)


def _no_writes(call):
    assert not _MUTATING.intersection(call.ops())


def _healthy_call():
    """A fully healthy service with every optional section populated."""
    call = ScriptedECS()
    call.queue("ecs", "DescribeServices", _describe_services(_svc()))
    call.queue("ecs", "DescribeTaskDefinition", _task_def())
    attached, inline = _iam_with_policies()
    call.queue("iam", "ListAttachedRolePolicies", attached)
    call.queue("iam", "ListRolePolicies", inline)
    # STOPPED tasks: none.
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    # RUNNING tasks: one healthy.
    call.queue(
        "ecs",
        "ListTasks",
        ok_result({"taskArns": ["arn:aws:ecs:us-east-1:1:task/prod/t1"]}),
    )
    call.queue(
        "ecs",
        "DescribeTasks",
        ok_result(
            {
                "tasks": [
                    {
                        "taskArn": "arn:aws:ecs:us-east-1:1:task/prod/t1",
                        "lastStatus": "RUNNING",
                        "healthStatus": "HEALTHY",
                        "startedAt": "2026-01-01T00:00:00Z",
                        "containers": [
                            {"name": "web", "lastStatus": "RUNNING"}
                        ],
                    }
                ]
            }
        ),
    )
    return call


# --------------------------------------------------------------- redaction


def test_redact_sensitive_scrubs_keyed_values_and_aws_keys():
    assert redact_sensitive("DB_PASSWORD=hunter2") == "DB_PASSWORD=[REDACTED]"
    assert "[REDACTED]" in redact_sensitive("token: abc.def.ghi")
    assert redact_sensitive("key AKIAIOSFODNN7EXAMPLE here") == (
        "key [REDACTED] here"
    )
    # Non-sensitive text is returned unchanged.
    assert redact_sensitive("plain log line") == "plain log line"
    # Non-strings pass through.
    assert redact_sensitive(None) is None


# --------------------------------------------------------------- happy path


def test_healthy_service_reports_no_blockers_and_only_reads():
    call = _healthy_call()
    result = _diag(call)
    assert result["ok"] is True
    value = result["value"]
    assert value["healthy"] is True
    assert value["blockers"] == []
    assert value["service_summary"]["desired_count"] == 2
    assert value["service_summary"]["running_count"] == 2
    # Gating read comes first.
    assert call.ops()[0] == ("ecs", "DescribeServices")
    _no_writes(call)


def test_healthy_service_populates_optional_sections():
    call = _healthy_call()
    value = _diag(call)["value"]
    sections = value["sections"]
    # Every attempted optional section is available.
    assert sections["task_definition"]["available"] is True
    assert sections["stopped_tasks"]["available"] is True
    assert sections["running_tasks"]["available"] is True
    assert value["running_tasks"]["count"] == 1
    assert value["stopped_tasks"]["count"] == 0


# ------------------------------------------------------ redaction in config


def test_task_definition_config_emits_env_names_only_no_values():
    call = _healthy_call()
    value = _diag(call)["value"]
    container = value["task_definition"]["containers"][0]
    # Names surfaced; values never emitted.
    assert "DB_PASSWORD" in container["environment_names"]
    assert "LOG_LEVEL" in container["environment_names"]
    serialized = repr(value)
    assert "hunter2" not in serialized
    # Secret references surfaced by name only.
    assert container["secret_names"] == ["API_TOKEN"]


# ---------------------------------------------------- service missing / inactive


def test_missing_service_returns_not_found():
    call = ScriptedECS()
    call.queue(
        "ecs",
        "DescribeServices",
        _describe_services(failures=[{"reason": "MISSING"}]),
    )
    result = _diag(call)
    assert result["ok"] is False
    assert result["code"] == "NOT_FOUND"
    # No optional section was queried once the service is absent.
    assert call.ops() == [("ecs", "DescribeServices")]


def test_inactive_service_returns_not_found():
    call = ScriptedECS()
    call.queue(
        "ecs", "DescribeServices", _describe_services(_svc(status="INACTIVE"))
    )
    result = _diag(call)
    assert result["ok"] is False
    assert result["code"] == "NOT_FOUND"


# --------------------------------------------------------------- gating failure


def test_gating_describe_services_failure_propagates_and_stops():
    call = ScriptedECS()
    call.queue(
        "ecs",
        "DescribeServices",
        err_result(
            "PERMISSION_DENIED", "not authorized", aws_code="AccessDenied"
        ),
    )
    result = _diag(call)
    assert result["ok"] is False
    assert result["code"] == "PERMISSION_DENIED"
    # Gating failure means nothing else is attempted.
    assert call.ops() == [("ecs", "DescribeServices")]


# ---------------------------------------------------- partial optional failure


def test_optional_section_failure_degrades_but_continues():
    call = ScriptedECS()
    call.queue("ecs", "DescribeServices", _describe_services(_svc()))
    # Task definition read fails -> warning + section unavailable, run continues.
    call.queue(
        "ecs",
        "DescribeTaskDefinition",
        err_result("PERMISSION_DENIED", "denied", aws_code="AccessDenied"),
    )
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    result = _diag(call)
    assert result["ok"] is True
    value = result["value"]
    assert value["sections"]["task_definition"]["available"] is False
    # Stopped/running task sections were still attempted after the failure.
    assert value["sections"]["stopped_tasks"]["available"] is True
    # A degraded section makes the result non-exhaustive.
    assert result["is_exhaustive"] is False
    assert any(w["type"] == "TASK_DEF_UNREADABLE" for w in value["warnings"])


# --------------------------------------------------------- stopped / failed tasks


def test_stopped_tasks_surface_reasons_and_blocker():
    call = ScriptedECS()
    call.queue("ecs", "DescribeServices", _describe_services(_svc(running=0)))
    call.queue("ecs", "DescribeTaskDefinition", _task_def(exec_role=None))
    # STOPPED tasks with a CannotPull reason.
    call.queue(
        "ecs",
        "ListTasks",
        ok_result({"taskArns": ["arn:aws:ecs:us-east-1:1:task/prod/s1"]}),
    )
    call.queue(
        "ecs",
        "DescribeTasks",
        ok_result(
            {
                "tasks": [
                    {
                        "taskArn": "arn:aws:ecs:us-east-1:1:task/prod/s1",
                        "lastStatus": "STOPPED",
                        "stoppedReason": "CannotPullContainerError: not found",
                        "stopCode": "TaskFailedToStart",
                        "taskDefinitionArn": _TASK_DEF_ARN,
                        "containers": [
                            {
                                "name": "web",
                                "exitCode": 1,
                                "reason": "CannotPullContainerError",
                                "lastStatus": "STOPPED",
                            }
                        ],
                    }
                ]
            }
        ),
    )
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    value = _diag(call)["value"]
    assert value["stopped_tasks"]["count"] == 1
    task = value["stopped_tasks"]["tasks"][0]
    assert task["stop_code"] == "TaskFailedToStart"
    assert task["containers"][0]["exit_code"] == 1
    # Ground-truth stopped reason becomes a blocker.
    assert any(b["type"] == "STOPPED_TASK_ERRORS" for b in value["blockers"])


# --------------------------------------------------------------- deployment / events


def test_desired_count_zero_is_false_green_blocker():
    call = ScriptedECS()
    call.queue(
        "ecs",
        "DescribeServices",
        _describe_services(_svc(desired=0, running=0)),
    )
    call.queue("ecs", "DescribeTaskDefinition", _task_def())
    attached, inline = _iam_with_policies()
    call.queue("iam", "ListAttachedRolePolicies", attached)
    call.queue("iam", "ListRolePolicies", inline)
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    value = _diag(call)["value"]
    blockers = {b["type"]: b for b in value["blockers"]}
    assert "DESIRED_COUNT_ZERO" in blockers
    # The false-green note is present because rolloutState is COMPLETED.
    assert "vacuously true" in blockers["DESIRED_COUNT_ZERO"]["evidence"]


def test_circuit_breaker_and_events_surfaced():
    call = ScriptedECS()
    svc = _svc(
        circuit={"enable": True, "rollback": True},
        events=[
            {
                "createdAt": "2026-01-02T00:00:00Z",
                "message": "unable to place a task",
            }
        ],
    )
    call.queue("ecs", "DescribeServices", _describe_services(svc))
    call.queue("ecs", "DescribeTaskDefinition", _task_def())
    attached, inline = _iam_with_policies()
    call.queue("iam", "ListAttachedRolePolicies", attached)
    call.queue("iam", "ListRolePolicies", inline)
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    value = _diag(call)["value"]
    assert value["deployment"]["circuit_breaker"] == {
        "enabled": True,
        "rollback": True,
    }
    assert value["recent_events"][0]["message"] == "unable to place a task"


# --------------------------------------------------------------- target health


def test_target_group_without_healthy_targets_is_blocker():
    lb = [
        {
            "targetGroupArn": (
                "arn:aws:elasticloadbalancing:us-east-1:1:targetgroup/tg/abc"
            ),
            "containerName": "web",
            "containerPort": 8080,
        }
    ]
    call = ScriptedECS()
    call.queue(
        "ecs", "DescribeServices", _describe_services(_svc(load_balancers=lb))
    )
    call.queue("ecs", "DescribeTaskDefinition", _task_def())
    attached, inline = _iam_with_policies()
    call.queue("iam", "ListAttachedRolePolicies", attached)
    call.queue("iam", "ListRolePolicies", inline)
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue(
        "elbv2",
        "DescribeTargetHealth",
        ok_result(
            {
                "TargetHealthDescriptions": [
                    {
                        "Target": {"Id": "10.0.0.1"},
                        "TargetHealth": {
                            "State": "unhealthy",
                            "Reason": "Target.FailedHealthChecks",
                        },
                    }
                ]
            }
        ),
    )
    value = _diag(call)["value"]
    assert value["target_health"]["wired"] is True
    tg = value["target_health"]["target_groups"][0]
    assert tg["healthy"] == 0
    assert tg["total"] == 1
    assert any(
        b["type"] == "TARGET_GROUP_UNHEALTHY" for b in value["blockers"]
    )


def test_no_load_balancer_reports_not_wired():
    call = _healthy_call()
    value = _diag(call)["value"]
    assert value["target_health"]["wired"] is False
    # No target-health call was issued when no LB is attached.
    assert ("elbv2", "DescribeTargetHealth") not in call.ops()


# --------------------------------------------------------------- log evidence


def test_log_evidence_is_fetched_redacted_and_truncated():
    call = _healthy_call()
    call.queue(
        "logs",
        "FilterLogEvents",
        ok_result(
            {
                "events": [
                    {
                        "timestamp": 1_700_000_000_000,
                        "logStreamName": "ecs/web/t1",
                        "message": "ERROR DB_PASSWORD=hunter2 " + "x" * 5000,
                    }
                ]
            }
        ),
    )
    value = _diag(call, max_message_length=100)["value"]
    assert value["sections"]["log_evidence"]["available"] is True
    line = value["log_evidence"]["lines"][0]
    # Redacted and truncated.
    assert "hunter2" not in line["message"]
    assert "[REDACTED]" in line["message"]
    assert len(line["message"]) <= 100


def test_no_logs_flag_skips_log_fetch():
    call = _healthy_call()
    value = _diag(call, include_logs=False)["value"]
    assert ("logs", "FilterLogEvents") not in call.ops()
    assert value["sections"]["log_evidence"]["available"] is False


# --------------------------------------------------------------- pagination / bounds


def test_list_tasks_pagination_is_bounded():
    call = ScriptedECS()
    call.queue("ecs", "DescribeServices", _describe_services(_svc()))
    call.queue("ecs", "DescribeTaskDefinition", _task_def())
    attached, inline = _iam_with_policies()
    call.queue("iam", "ListAttachedRolePolicies", attached)
    call.queue("iam", "ListRolePolicies", inline)
    # STOPPED ListTasks keeps returning a nextToken; the loop must stop at
    # max_pages rather than spinning forever.
    for _ in range(50):
        call.queue(
            "ecs",
            "ListTasks",
            ok_result({"taskArns": [], "nextToken": "more"}),
        )
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    result = _diag(call, max_pages=3)
    assert result["ok"] is True
    stopped_list_calls = sum(
        1
        for s, o, p in call.calls
        if (s, o) == ("ecs", "ListTasks")
        and p.get("desiredStatus") == "STOPPED"
    )
    assert stopped_list_calls == 3


def test_stopped_tasks_capped():
    call = ScriptedECS()
    call.queue("ecs", "DescribeServices", _describe_services(_svc(running=0)))
    call.queue("ecs", "DescribeTaskDefinition", _task_def())
    attached, inline = _iam_with_policies()
    call.queue("iam", "ListAttachedRolePolicies", attached)
    call.queue("iam", "ListRolePolicies", inline)
    arns = [f"arn:aws:ecs:us-east-1:1:task/prod/s{i}" for i in range(10)]
    call.queue("ecs", "ListTasks", ok_result({"taskArns": arns}))
    call.queue(
        "ecs",
        "DescribeTasks",
        ok_result(
            {
                "tasks": [
                    {
                        "taskArn": a,
                        "lastStatus": "STOPPED",
                        "stoppedReason": "Essential container exited",
                        "stopCode": "EssentialContainerExited",
                        "containers": [],
                    }
                    for a in arns
                ]
            }
        ),
    )
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    value = _diag(call, max_stopped_tasks=3)["value"]
    assert value["stopped_tasks"]["count"] == 3
    assert value["stopped_tasks"]["truncated"] is True


# --------------------------------------------------------------- empty optional data


def test_empty_optional_data_still_healthy():
    call = ScriptedECS()
    call.queue("ecs", "DescribeServices", _describe_services(_svc()))
    call.queue("ecs", "DescribeTaskDefinition", _task_def())
    attached, inline = _iam_with_policies()
    call.queue("iam", "ListAttachedRolePolicies", attached)
    call.queue("iam", "ListRolePolicies", inline)
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    result = _diag(call)
    value = result["value"]
    assert value["healthy"] is True
    assert value["stopped_tasks"]["tasks"] == []
    assert value["target_health"]["wired"] is False
    # Nothing failed or truncated -> exhaustive.
    assert result["is_exhaustive"] is True


# --------------------------------------------------------------- IAM findings


def test_missing_execution_role_is_warning_when_running_at_desired():
    # running >= desired: the service evidently works without the role, so
    # EXECUTION_ROLE_MISSING is downgraded to a warning.
    call = ScriptedECS()
    call.queue("ecs", "DescribeServices", _describe_services(_svc()))
    call.queue("ecs", "DescribeTaskDefinition", _task_def(exec_role=None))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    value = _diag(call)["value"]
    assert any(
        w["type"] == "EXECUTION_ROLE_MISSING" for w in value["warnings"]
    )
    assert not any(
        b["type"] == "EXECUTION_ROLE_MISSING" for b in value["blockers"]
    )
    # No IAM call is made when there is no role to inspect.
    assert ("iam", "ListAttachedRolePolicies") not in call.ops()


def test_missing_execution_role_is_blocker_when_below_desired():
    call = ScriptedECS()
    call.queue(
        "ecs", "DescribeServices", _describe_services(_svc(running=0))
    )
    call.queue("ecs", "DescribeTaskDefinition", _task_def(exec_role=None))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    value = _diag(call)["value"]
    assert any(
        b["type"] == "EXECUTION_ROLE_MISSING" for b in value["blockers"]
    )
    # No IAM call is made when there is no role to inspect.
    assert ("iam", "ListAttachedRolePolicies") not in call.ops()


def test_execution_role_without_policies_is_warning():
    call = ScriptedECS()
    call.queue("ecs", "DescribeServices", _describe_services(_svc()))
    call.queue("ecs", "DescribeTaskDefinition", _task_def())
    call.queue(
        "iam", "ListAttachedRolePolicies", ok_result({"AttachedPolicies": []})
    )
    call.queue("iam", "ListRolePolicies", ok_result({"PolicyNames": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    value = _diag(call)["value"]
    assert any(
        w["type"] == "EXECUTION_ROLE_MISSING_PERMS" for w in value["warnings"]
    )


# --------------------------------------------------------------- no-write guarantee


def test_full_run_issues_no_mutating_operation():
    call = _healthy_call()
    call.queue("logs", "FilterLogEvents", ok_result({"events": []}))
    _diag(call)
    # Every recorded op is a read; not one mutating verb slipped through.
    _no_writes(call)
    for _, operation, _ in call.calls:
        # assert_read_only would have raised already; re-assert for clarity.
        assert_read_only(operation)


# ------------------------------------------------ extra findings / branches


def test_code_deploy_controller_adds_info_warning():
    call = ScriptedECS()
    svc = _svc()
    svc["deploymentController"] = {"type": "CODE_DEPLOY"}
    call.queue("ecs", "DescribeServices", _describe_services(svc))
    call.queue("ecs", "DescribeTaskDefinition", _task_def())
    attached, inline = _iam_with_policies()
    call.queue("iam", "ListAttachedRolePolicies", attached)
    call.queue("iam", "ListRolePolicies", inline)
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    value = _diag(call)["value"]
    assert any(w["type"] == "CODE_DEPLOY_SERVICE" for w in value["warnings"])


def test_task_role_without_policies_is_warning():
    call = ScriptedECS()
    call.queue("ecs", "DescribeServices", _describe_services(_svc()))
    call.queue(
        "ecs",
        "DescribeTaskDefinition",
        _task_def(task_role="arn:aws:iam::111122223333:role/app-task"),
    )
    # Execution role: has policies. Task role: no policies -> warning.
    call.queue(
        "iam",
        "ListAttachedRolePolicies",
        ok_result({"AttachedPolicies": [{"PolicyName": "exec"}]}),
    )
    call.queue("iam", "ListRolePolicies", ok_result({"PolicyNames": []}))
    call.queue(
        "iam", "ListAttachedRolePolicies", ok_result({"AttachedPolicies": []})
    )
    call.queue("iam", "ListRolePolicies", ok_result({"PolicyNames": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    value = _diag(call)["value"]
    assert any(
        w["type"] == "TASK_ROLE_MISSING_PERMS" for w in value["warnings"]
    )
    assert "task_role" not in value["verified_ok"]


def test_task_role_with_policies_is_verified_ok():
    call = ScriptedECS()
    call.queue("ecs", "DescribeServices", _describe_services(_svc()))
    call.queue(
        "ecs",
        "DescribeTaskDefinition",
        _task_def(task_role="arn:aws:iam::111122223333:role/app-task"),
    )
    for _ in range(2):
        call.queue(
            "iam",
            "ListAttachedRolePolicies",
            ok_result({"AttachedPolicies": [{"PolicyName": "p"}]}),
        )
        call.queue("iam", "ListRolePolicies", ok_result({"PolicyNames": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    value = _diag(call)["value"]
    assert "task_role" in value["verified_ok"]
    assert value["sections"]["iam"]["available"] is True


def test_iam_read_failure_degrades_iam_section():
    call = ScriptedECS()
    call.queue("ecs", "DescribeServices", _describe_services(_svc()))
    call.queue("ecs", "DescribeTaskDefinition", _task_def())
    call.queue(
        "iam",
        "ListAttachedRolePolicies",
        err_result("PERMISSION_DENIED", "denied", aws_code="AccessDenied"),
    )
    call.queue("iam", "ListRolePolicies", ok_result({"PolicyNames": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    result = _diag(call)
    value = result["value"]
    assert value["sections"]["iam"]["available"] is False
    assert any(w["type"] == "IAM_CHECK_DEGRADED" for w in value["warnings"])
    assert result["is_exhaustive"] is False


def test_no_task_definition_ref_skips_task_sections():
    call = ScriptedECS()
    svc = _svc(task_def="")
    call.queue("ecs", "DescribeServices", _describe_services(svc))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    value = _diag(call)["value"]
    # No task definition was referenced, so that section is absent and no IAM
    # read was issued.
    assert "task_definition" not in value["sections"]
    assert ("ecs", "DescribeTaskDefinition") not in call.ops()


# --------------------------------------------- optional-read failures


def test_stopped_tasks_list_failure_degrades_section():
    call = ScriptedECS()
    call.queue("ecs", "DescribeServices", _describe_services(_svc()))
    call.queue("ecs", "DescribeTaskDefinition", _task_def())
    attached, inline = _iam_with_policies()
    call.queue("iam", "ListAttachedRolePolicies", attached)
    call.queue("iam", "ListRolePolicies", inline)
    call.queue(
        "ecs",
        "ListTasks",
        err_result("THROTTLED", "slow down", aws_code="ThrottlingException"),
    )
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    result = _diag(call)
    assert result["value"]["sections"]["stopped_tasks"]["available"] is False
    assert result["is_exhaustive"] is False


def test_running_tasks_describe_failure_degrades_section():
    call = ScriptedECS()
    call.queue("ecs", "DescribeServices", _describe_services(_svc()))
    call.queue("ecs", "DescribeTaskDefinition", _task_def())
    attached, inline = _iam_with_policies()
    call.queue("iam", "ListAttachedRolePolicies", attached)
    call.queue("iam", "ListRolePolicies", inline)
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue(
        "ecs",
        "ListTasks",
        ok_result({"taskArns": ["arn:aws:ecs:us-east-1:1:task/prod/r1"]}),
    )
    call.queue(
        "ecs",
        "DescribeTasks",
        err_result("SERVICE_ERROR", "boom"),
    )
    result = _diag(call)
    assert result["value"]["sections"]["running_tasks"]["available"] is False


def test_target_health_read_failure_degrades_and_keeps_others():
    lb = [
        {"targetGroupArn": "arn:aws:elasticloadbalancing:us-east-1:1:tg/a/1"},
        {"targetGroupArn": "arn:aws:elasticloadbalancing:us-east-1:1:tg/b/2"},
    ]
    call = ScriptedECS()
    call.queue(
        "ecs", "DescribeServices", _describe_services(_svc(load_balancers=lb))
    )
    call.queue("ecs", "DescribeTaskDefinition", _task_def())
    attached, inline = _iam_with_policies()
    call.queue("iam", "ListAttachedRolePolicies", attached)
    call.queue("iam", "ListRolePolicies", inline)
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue(
        "elbv2",
        "DescribeTargetHealth",
        ok_result(
            {
                "TargetHealthDescriptions": [
                    {"TargetHealth": {"State": "healthy"}}
                ]
            }
        ),
    )
    call.queue(
        "elbv2",
        "DescribeTargetHealth",
        err_result("SERVICE_ERROR", "elb down"),
    )
    result = _diag(call)
    value = result["value"]
    assert value["sections"]["target_health"]["available"] is False
    # The group that resolved is still present alongside the errored one.
    groups = value["target_health"]["target_groups"]
    assert any("error" in g for g in groups)
    assert any(g.get("healthy") == 1 for g in groups)


def test_target_groups_capped_marks_degraded():
    lb = [
        {
            "targetGroupArn": f"arn:aws:elasticloadbalancing:us-east-1:1:tg/{i}/x"
        }
        for i in range(3)
    ]
    call = ScriptedECS()
    call.queue(
        "ecs", "DescribeServices", _describe_services(_svc(load_balancers=lb))
    )
    call.queue("ecs", "DescribeTaskDefinition", _task_def())
    attached, inline = _iam_with_policies()
    call.queue("iam", "ListAttachedRolePolicies", attached)
    call.queue("iam", "ListRolePolicies", inline)
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue(
        "elbv2",
        "DescribeTargetHealth",
        ok_result(
            {
                "TargetHealthDescriptions": [
                    {"TargetHealth": {"State": "healthy"}}
                ]
            }
        ),
    )
    result = _diag(call, max_target_groups=1)
    assert result["is_exhaustive"] is False
    # Only one target group was queried under the cap.
    assert sum(1 for s, o, _ in call.calls if o == "DescribeTargetHealth") == 1


def test_log_evidence_fetch_failure_degrades_section():
    call = _healthy_call()
    call.queue(
        "logs",
        "FilterLogEvents",
        err_result("PERMISSION_DENIED", "no logs:FilterLogEvents"),
    )
    result = _diag(call)
    assert result["value"]["sections"]["log_evidence"]["available"] is False
    assert result["is_exhaustive"] is False


def test_log_evidence_skipped_when_no_awslogs_driver():
    containers = [
        {
            "name": "web",
            "image": "web:1",
            "logConfiguration": {"logDriver": "json-file"},
        }
    ]
    call = ScriptedECS()
    call.queue("ecs", "DescribeServices", _describe_services(_svc()))
    call.queue(
        "ecs", "DescribeTaskDefinition", _task_def(containers=containers)
    )
    attached, inline = _iam_with_policies()
    call.queue("iam", "ListAttachedRolePolicies", attached)
    call.queue("iam", "ListRolePolicies", inline)
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    call.queue("ecs", "ListTasks", ok_result({"taskArns": []}))
    result = _diag(call)
    # No awslogs group -> section unavailable but not a loss -> still exhaustive.
    assert result["value"]["sections"]["log_evidence"]["available"] is False
    assert ("logs", "FilterLogEvents") not in call.ops()
    assert result["is_exhaustive"] is True


# --------------------------------------------- validation / internal error


def test_empty_service_rejected_before_dispatch():
    call = ScriptedECS()
    result = diagnose_ecs_service(call, "   ", cluster="prod")
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"
    assert call.calls == []


def test_non_positive_cap_rejected_before_dispatch():
    call = ScriptedECS()
    result = _diag(call, max_events=0)
    assert result["ok"] is False
    assert result["code"] == "INVALID_INPUT"
    assert call.calls == []


def test_internal_exception_is_returned_as_service_error():
    def exploding(service, operation, params):
        raise RuntimeError("kaboom")

    result = diagnose_ecs_service(exploding, "web", cluster="prod")
    assert result["ok"] is False
    assert result["code"] == "SERVICE_ERROR"
    assert "internal error" in result["error"]
