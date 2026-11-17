"""ECS commands: deploy's CodeDeploy flow and the express gateway
service's request (upstream tests/functional/ecs)."""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

SERVICE: Final = "serviceTest"
SERVICE_ARN: Final = "arn:aws:ecs:::service/serviceTest"
CLUSTER: Final = "default"
CLUSTER_ARN: Final = "arn:aws:ecs:::cluster/default"
# deploy names the CodeDeploy application and deployment group after the
# cluster and service unless told otherwise.
APP: Final = "AppECS-default-serviceTest"
DEPLOYMENT_GROUP: Final = "DgpECS-default-serviceTest"
TASK_DEFINITION: Final = {
    "family": "test",
    "containerDefinitions": [],
    "cpu": "256",
    "memory": "512",
}
TASK_DEFINITION_ARN: Final = "arn:aws:ecs::1234567890:task-definition\\test:2"
DEPLOYMENT_ID: Final = "d-1234567XX"
JSON_APPSPEC: Final = """
    {
        "version": 0.0,
        "resources": [{
            "TestService": {
                "type": "AWS::ECS::Service",
                "properties": {
                    "taskDefinition": "arn:aws:ecs::123:task-definition:1",
                    "loadBalancerInfo": {
                        "containerName": "web",
                        "containerPort": 80
                    }
                }
            }
        }]
    }
    """
YAML_APPSPEC: Final = """
    version: 0.0
    resources:
      - TestService:
          type: AWS::ECS::Service
          properties:
            taskDefinition: arn:aws:ecs::123:task-definition:1
            loadBalancerInfo:
              containerName: web
              containerPort: 80
    """
# Its one resource has no taskDefinition property.
BAD_APPSPEC: Final = """
    version: 0.0
    resources:
      - TestService:
          type: AWS::Lambda::Function
          properties:
            name: myFunction
    """
# Either appspec, with the task definition deploy registered.
DEPLOYED_APPSPEC: Final = json.dumps(
    {
        "version": 0.0,
        "resources": [
            {
                "TestService": {
                    "type": "AWS::ECS::Service",
                    "properties": {
                        "taskDefinition": TASK_DEFINITION_ARN,
                        "loadBalancerInfo": {
                            "containerName": "web",
                            "containerPort": 80,
                        },
                    },
                }
            }
        ],
    }
)
REGISTERED: Final = (
    f"Successfully registered new ECS task definition {TASK_DEFINITION_ARN}\n"
)


def service_reply(cluster: str) -> dict[str, Any]:
    return {
        "services": [
            {
                "serviceArn": SERVICE_ARN,
                "serviceName": SERVICE,
                "clusterArn": f"arn:aws:ecs:::cluster/{cluster}",
            }
        ]
    }


def application_reply(app: str, platform: str = "ECS") -> dict[str, Any]:
    return {
        "application": {
            "applicationId": "876uyh6-45tdfg",
            "applicationName": app,
            "computePlatform": platform,
        }
    }


def deployment_group_reply(
    cluster: str, app: str, group: str, waits: tuple[int, int] | None
) -> dict[str, Any]:
    """The deployment group; `waits` are its ready and blue-termination
    waits in minutes, None for no blue/green configuration."""
    info: dict[str, Any] = {
        "applicationName": app,
        "deploymentGroupName": group,
        "computePlatform": "ECS",
        "ecsServices": [{"serviceName": SERVICE, "clusterName": cluster}],
    }
    if waits is not None:
        ready, termination = waits
        info["blueGreenDeploymentConfiguration"] = {
            "deploymentReadyOption": {"waitTimeInMinutes": ready},
            "terminateBlueInstancesOnDeploymentSuccess": {
                "terminationWaitTimeInMinutes": termination
            },
        }
    return {"deploymentGroupInfo": info}


TASK_DEFINITION_REPLY: Final = {
    "taskDefinition": {
        "taskDefinitionArn": TASK_DEFINITION_ARN,
        "family": "test",
        "containerDefinitions": [],
    }
}


def validation_calls(
    service: str, cluster: str, app: str, group: str
) -> list[tuple[str, dict[str, Any]]]:
    """The requests deploy checks the service and CodeDeploy with."""
    return [
        ("DescribeServices", {"cluster": cluster, "services": [service]}),
        ("GetApplication", {"applicationName": app}),
        (
            "GetDeploymentGroup",
            {"applicationName": app, "deploymentGroupName": group},
        ),
    ]


@dataclass(frozen=True)
class DeployCase:
    """One successful deploy: the arguments past the required ones, the
    names its requests carry, and its deployment group's waits.

    `replied_cluster` is the cluster the replies name. `wait_minutes` is
    how long deploy says it waits: the group's two waits plus 10 minutes,
    kept between 30 minutes and 6 hours.
    """

    args: Sequence[str] = ()
    appspec_name: str = "appspec.yaml"
    appspec: str = YAML_APPSPEC
    service: str = SERVICE
    cluster: str = CLUSTER
    replied_cluster: str = CLUSTER
    app: str = APP
    group: str = DEPLOYMENT_GROUP
    waits: tuple[int, int] = (5, 10)
    wait_minutes: int = 30


def write_files(
    api: ApiSession, appspec_name: str, appspec: str
) -> tuple[Path, Path]:
    task_definition = api.cwd / "taskDef.json"
    task_definition.write_text(json.dumps(TASK_DEFINITION), encoding="utf-8")
    appspec_file = api.cwd / appspec_name
    appspec_file.write_text(appspec, encoding="utf-8")
    return task_definition, appspec_file


def deploy_argv(
    service: str, task_definition: Path, appspec: Path, *args: str
) -> list[str]:
    return [
        "ecs",
        "deploy",
        "--service",
        service,
        "--task-definition",
        str(task_definition),
        "--codedeploy-appspec",
        str(appspec),
        *args,
    ]


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(DeployCase(), id="defaults"),
        pytest.param(
            DeployCase(
                args=("--cluster", CLUSTER_ARN),
                service=SERVICE_ARN,
                cluster=CLUSTER_ARN,
            ),
            id="default-arns",
        ),
        pytest.param(
            DeployCase(appspec_name="appspec.json", appspec=JSON_APPSPEC),
            id="json-appspec",
        ),
        pytest.param(
            DeployCase(waits=(5, 60), wait_minutes=75), id="custom-timeout"
        ),
        pytest.param(
            DeployCase(waits=(90, 300), wait_minutes=360), id="max-timeout"
        ),
        # The last --cluster wins.
        pytest.param(
            DeployCase(
                args=(
                    "--cluster",
                    CLUSTER,
                    "--codedeploy-application",
                    "myOtherApp",
                    "--codedeploy-deployment-group",
                    "myOtherDgp",
                    "--cluster",
                    "myOtherCluster",
                ),
                cluster="myOtherCluster",
                replied_cluster="myOtherCluster",
                app="myOtherApp",
                group="myOtherDgp",
            ),
            id="optional-values",
        ),
    ],
)
async def test_deploy(api: ApiSession, case: DeployCase) -> None:
    task_definition, appspec = write_files(
        api, case.appspec_name, case.appspec
    )
    result = await api.run(
        deploy_argv(case.service, task_definition, appspec, *case.args),
        replies=[
            service_reply(case.replied_cluster),
            application_reply(case.app),
            deployment_group_reply(
                case.replied_cluster, case.app, case.group, case.waits
            ),
            TASK_DEFINITION_REPLY,
            {"deploymentId": DEPLOYMENT_ID},
            {
                "deploymentInfo": {
                    "applicationName": case.app,
                    "status": "Succeeded",
                }
            },
        ],
    )
    assert result.operations_with_params == [
        *validation_calls(case.service, case.cluster, case.app, case.group),
        ("RegisterTaskDefinition", TASK_DEFINITION),
        (
            "CreateDeployment",
            {
                "applicationName": case.app,
                "deploymentGroupName": case.group,
                "revision": {
                    "revisionType": "AppSpecContent",
                    "appSpecContent": {
                        "content": DEPLOYED_APPSPEC,
                        "sha256": hashlib.sha256(
                            DEPLOYED_APPSPEC.encode()
                        ).hexdigest(),
                    },
                },
            },
        ),
        ("GetDeployment", {"deploymentId": DEPLOYMENT_ID}),
    ]
    assert result.stdout == (
        f"{REGISTERED}"
        f"Successfully created deployment {DEPLOYMENT_ID}\n"
        f"Waiting for {DEPLOYMENT_ID} to succeed (will wait up to"
        f" {case.wait_minutes} minutes)...\n"
        f"Successfully deployed {TASK_DEFINITION_ARN} to service"
        f" '{SERVICE}'\n"
    )


async def test_deploy_error_missing_appspec_property(
    api: ApiSession,
) -> None:
    task_definition, appspec = write_files(
        api, "appspec_bad.yaml", BAD_APPSPEC
    )
    result = await api.run(
        deploy_argv(SERVICE, task_definition, appspec),
        replies=[
            service_reply(CLUSTER),
            application_reply(APP),
            deployment_group_reply(CLUSTER, APP, DEPLOYMENT_GROUP, (5, 10)),
            TASK_DEFINITION_REPLY,
        ],
        expected_rc=255,
    )
    # The appspec's resource is checked only as deploy puts the
    # registered task definition in it.
    assert result.operations_with_params == [
        *validation_calls(SERVICE, CLUSTER, APP, DEPLOYMENT_GROUP),
        ("RegisterTaskDefinition", TASK_DEFINITION),
    ]
    assert result.stdout == REGISTERED
    assert result.stderr == (
        "\naws: [ERROR]: Resource 'properties' must include property"
        " 'taskDefinition'\n"
    )


async def test_deploy_error_invalid_platform(api: ApiSession) -> None:
    task_definition, appspec = write_files(
        api, "appspec_bad.yaml", BAD_APPSPEC
    )
    result = await api.run(
        deploy_argv(SERVICE, task_definition, appspec),
        replies=[
            service_reply(CLUSTER),
            application_reply(APP, platform="Server"),
            deployment_group_reply(CLUSTER, APP, DEPLOYMENT_GROUP, None),
        ],
        expected_rc=255,
    )
    assert result.operations_with_params == validation_calls(
        SERVICE, CLUSTER, APP, DEPLOYMENT_GROUP
    )
    assert result.stdout == ""
    assert result.stderr == (
        f"\naws: [ERROR]: Application '{APP}' must support 'ECS' compute"
        " platform\n"
    )


async def test_express_gateway_service_api_parameters_not_modified(
    api: ApiSession,
) -> None:
    result = await api.run(
        "ecs create-express-gateway-service --service-name test-service"
        " --cluster test-cluster"
        " --execution-role-arn arn:aws:iam::123456789:role/exec"
        " --infrastructure-role-arn arn:aws:iam::123456789:role/infra"
        " --primary-container image=nginx",
        replies=[
            {
                "service": {
                    "serviceArn": (
                        "arn:aws:ecs:us-east-1:123456789:service/"
                        "test-cluster/test-service"
                    ),
                    "serviceName": "test-service",
                }
            }
        ],
    )
    body = json.loads(result.calls[-1].request.body)
    # The CLI's own monitoring option never reaches the service.
    assert "monitorResources" not in body
    assert "monitor-resources" not in body
    assert result.operations_with_params == [
        (
            "CreateExpressGatewayService",
            {
                "serviceName": "test-service",
                "cluster": "test-cluster",
                "executionRoleArn": "arn:aws:iam::123456789:role/exec",
                "infrastructureRoleArn": "arn:aws:iam::123456789:role/infra",
                "primaryContainer": {"image": "nginx"},
            },
        )
    ]
