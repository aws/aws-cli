"""--generate-cli-skeleton's input and output skeletons (upstream
tests/functional/test_generatecliskeleton.py)."""

import json
from collections.abc import Callable
from typing import Any

import pytest
from ruamel.yaml import YAML

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

type Loader = Callable[[str], Any]


def load_yaml(text: str) -> Any:
    # Upstream's base class loads YAML this way.
    return YAML(typ="safe", pure=True).load(text)


@pytest.mark.parametrize(
    ("kind", "load"),
    [
        pytest.param([], json.loads, id="json"),
        pytest.param(["yaml-input"], load_yaml, id="yaml-input"),
    ],
)
@pytest.mark.parametrize(
    ("command", "skeleton"),
    [
        pytest.param(
            "s3api delete-object",
            {
                "Bucket": "",
                "BypassGovernanceRetention": True,
                "Key": "",
                "MFA": "",
                "RequestPayer": "requester",
            },
            id="s3api",
        ),
        pytest.param(
            "sqs change-message-visibility",
            {"QueueUrl": "", "ReceiptHandle": "", "VisibilityTimeout": 0},
            id="sqs",
        ),
        pytest.param(
            "iam create-group", {"Path": "", "GroupName": ""}, id="iam"
        ),
    ],
)
async def test_input_skeleton_has_operation_members(
    api: ApiSession,
    command: str,
    skeleton: dict[str, Any],
    kind: list[str],
    load: Loader,
) -> None:
    run = await api.run([*command.split(), "--generate-cli-skeleton", *kind])
    loaded = load(run.stdout)
    # Upstream checks these members only, so the model can add others.
    assert {name: loaded[name] for name in skeleton} == skeleton
    assert run.calls == ()


async def test_yaml_input_skeleton_labels_required_members(
    api: ApiSession,
) -> None:
    run = await api.run(
        "s3api delete-object --generate-cli-skeleton yaml-input"
    )
    assert "Bucket: ''  # [REQUIRED]" in run.stdout, run.describe()


async def test_output_skeleton_fills_response_shape(api: ApiSession) -> None:
    run = await api.run("ec2 describe-regions --generate-cli-skeleton output")
    regions = json.loads(run.stdout)["Regions"]
    # Upstream checks these members only, so the model can add others.
    assert regions[0]["RegionName"] == "RegionName"
    assert regions[0]["Endpoint"] == "Endpoint"
    assert run.calls == ()


@pytest.mark.parametrize(
    ("command", "path", "value"),
    [
        pytest.param(
            "s3api list-buckets",
            ("Buckets", 0, "CreationDate"),
            "1970-01-01T00:00:00",
            id="timestamps",
        ),
        pytest.param(
            "dynamodb list-tables",
            ("TableNames",),
            ["TableName"],
            id="list-of-min-length-strings",
        ),
    ],
)
async def test_output_skeleton_fills_member_types(
    api: ApiSession, command: str, path: tuple[str | int, ...], value: Any
) -> None:
    run = await api.run(f"{command} --generate-cli-skeleton output")
    member = json.loads(run.stdout)
    for step in path:
        member = member[step]
    assert member == value
    assert run.calls == ()


async def test_output_skeleton_respects_query_and_output(
    api: ApiSession,
) -> None:
    run = await api.run(
        "ec2 describe-regions --generate-cli-skeleton output"
        " --query Regions[].RegionName --output text"
    )
    assert run.stdout == "RegionName\n"
    assert run.calls == ()


@pytest.mark.parametrize(
    ("args", "messages"),
    [
        pytest.param(
            "ec2 start-instances",
            ("required", "--instance-ids"),
            id="command-line-level",
        ),
        # --filters' member is Values, not Value.
        pytest.param(
            "ec2 describe-instances --filters Name=instance-id,Value=foo",
            ("Unknown parameter in Filters[0]",),
            id="client-level",
        ),
    ],
)
async def test_output_skeleton_validates_input(
    api: ApiSession, args: str, messages: tuple[str, ...]
) -> None:
    run = await api.run(
        f"{args} --generate-cli-skeleton output", expected_rc=252
    )
    for message in messages:
        assert message in run.stderr, run.describe()
    assert run.stdout == ""
    assert run.calls == ()
