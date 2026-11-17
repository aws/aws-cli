"""Elastic Load Balancing commands' requests (upstream
tests/functional/elb)."""

from typing import Any, Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

HEALTH_CHECK: Final = {
    "HealthyThreshold": 9,
    "Interval": 300,
    "Target": "HTTP:80/weather/us/wa/seattle",
    "Timeout": 60,
    "UnhealthyThreshold": 5,
}
REGISTER: Final = (
    "elb register-instances-with-load-balancer --load-balancer-name my-lb"
)
ONE_INSTANCE: Final = {
    "LoadBalancerName": "my-lb",
    "Instances": [{"InstanceId": "i-12345678"}],
}
TWO_INSTANCES: Final = {
    "LoadBalancerName": "my-lb",
    "Instances": [{"InstanceId": "i-12345678"}, {"InstanceId": "i-87654321"}],
}
# Upstream's test.json and test_with_spaces.json.
INSTANCES_JSON: Final = (
    '[{"InstanceId": "i-12345678"},\n {"InstanceId": "i-87654321"}]\n'
)


@pytest.mark.parametrize(
    ("health_check", "target"),
    [
        pytest.param(
            "Target=HTTP:80/weather/us/wa/seattle,Interval=300,Timeout=60,"
            "UnhealthyThreshold=5,HealthyThreshold=9",
            "HTTP:80/weather/us/wa/seattle",
            id="shorthand-basic",
        ),
        pytest.param(
            '{"Target":"HTTP:80/weather/us/wa/seattle?a=b","Interval":300,'
            '"Timeout":60,"UnhealthyThreshold":5,"HealthyThreshold":9}',
            "HTTP:80/weather/us/wa/seattle?a=b",
            id="json",
        ),
        pytest.param(
            'Target="HTTP:80/weather/us/wa/seattle?a=b",Interval=300,'
            "Timeout=60,UnhealthyThreshold=5,HealthyThreshold=9",
            "HTTP:80/weather/us/wa/seattle?a=b",
            id="shorthand-with-multiple-equals-for-value",
        ),
    ],
)
async def test_configure_health_check(
    api: ApiSession, health_check: str, target: str
) -> None:
    await api.assert_params_for_cmd(
        "elb configure-health-check --load-balancer-name my-lb"
        f" --health-check {health_check}",
        {
            "HealthCheck": {**HEALTH_CHECK, "Target": target},
            "LoadBalancerName": "my-lb",
        },
    )


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            "deregister-instances-from-load-balancer", id="deregister"
        ),
        pytest.param("describe-instance-health", id="describe-health"),
    ],
)
async def test_instances_shorthand(api: ApiSession, command: str) -> None:
    await api.assert_params_for_cmd(
        f"elb {command} --load-balancer-name foo --instances id1 id2 id3",
        {
            "LoadBalancerName": "foo",
            "Instances": [
                {"InstanceId": "id1"},
                {"InstanceId": "id2"},
                {"InstanceId": "id3"},
            ],
        },
    )


@pytest.mark.parametrize(
    ("instances", "params"),
    [
        pytest.param(
            '{"InstanceId":"i-12345678"}', ONE_INSTANCE, id="one-instance"
        ),
        pytest.param("i-12345678", ONE_INSTANCE, id="shorthand"),
        pytest.param(
            '{"InstanceId":"i-12345678"} {"InstanceId":"i-87654321"}',
            TWO_INSTANCES,
            id="two-instance",
        ),
        pytest.param(
            '[{"InstanceId":"i-12345678"},{"InstanceId":"i-87654321"}]',
            TWO_INSTANCES,
            id="two-instance-as-json",
        ),
        pytest.param(
            "i-12345678 i-87654321", TWO_INSTANCES, id="two-instance-shorthand"
        ),
    ],
)
async def test_register_instances(
    api: ApiSession, instances: str, params: dict[str, Any]
) -> None:
    await api.assert_params_for_cmd(
        f"{REGISTER} --instances {instances}", params
    )


@pytest.mark.parametrize(
    "contents",
    [
        pytest.param(INSTANCES_JSON, id="two-instance-from-file"),
        pytest.param(f"  {INSTANCES_JSON}", id="json-file-with-spaces"),
    ],
)
async def test_register_instances_from_file(
    api: ApiSession, contents: str
) -> None:
    instances = api.cwd / "instances.json"
    instances.write_text(contents, encoding="utf-8")
    await api.assert_params_for_cmd(
        [*REGISTER.split(), "--instances", f"file://{instances}"],
        TWO_INSTANCES,
    )


async def test_remove_tags_shorthand(api: ApiSession) -> None:
    await api.assert_params_for_cmd(
        "elb remove-tags --load-balancer-names foo --tags bar baz",
        {
            "LoadBalancerNames": ["foo"],
            "Tags": [{"Key": "bar"}, {"Key": "baz"}],
        },
    )
