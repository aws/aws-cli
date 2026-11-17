"""AWS Config commands' requests (upstream tests/functional/configservice)."""

from typing import Any, Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

PUT_RECORDER: Final = "configservice put-configuration-recorder"


@pytest.mark.parametrize(
    ("args", "recorder"),
    [
        pytest.param(
            "",
            {"name": "myrecorder", "roleARN": "myarn"},
            id="only-configuration-recorder",
        ),
        pytest.param(
            " --recording-group allSupported=true,"
            "resourceTypes=AWS::EC2::Volume,AWS::EC2::VPC",
            {
                "name": "myrecorder",
                "roleARN": "myarn",
                "recordingGroup": {
                    "allSupported": True,
                    "resourceTypes": ["AWS::EC2::Volume", "AWS::EC2::VPC"],
                },
            },
            id="with-recording-group",
        ),
    ],
)
async def test_put_configuration_recorder_sends_recorder(
    api: ApiSession, args: str, recorder: dict[str, Any]
) -> None:
    await api.assert_params_for_cmd(
        f"{PUT_RECORDER} --configuration-recorder"
        " name=myrecorder,roleARN=myarn" + args,
        {"ConfigurationRecorder": recorder},
    )


async def test_put_configuration_recorder_requires_recorder(
    api: ApiSession,
) -> None:
    result = await api.run(PUT_RECORDER, expected_rc=252)
    assert "required" in result.stderr
    assert "--configuration-recorder" in result.stderr
    assert result.calls == ()


def subscribe_calls(
    topic_arn: str, create_topic: bool
) -> list[tuple[str, dict[str, Any]]]:
    """The requests `subscribe` sends for bucket mybucket and role
    myrole."""
    topic = [("CreateTopic", {"Name": "mytopic"})] if create_topic else []
    return [
        ("HeadBucket", {"Bucket": "mybucket"}),
        *topic,
        (
            "PutConfigurationRecorder",
            {
                "ConfigurationRecorder": {
                    "name": "default",
                    "roleARN": "myrole",
                }
            },
        ),
        (
            "PutDeliveryChannel",
            {
                "DeliveryChannel": {
                    "name": "default",
                    "s3BucketName": "mybucket",
                    "snsTopicARN": topic_arn,
                }
            },
        ),
        (
            "StartConfigurationRecorder",
            {"ConfigurationRecorderName": "default"},
        ),
        ("DescribeConfigurationRecorders", {}),
        ("DescribeDeliveryChannels", {}),
    ]


@pytest.mark.parametrize(
    ("topic", "topic_arn", "create_topic"),
    [
        pytest.param("mytopic", "my-topic-arn", True, id="new-sns-topic"),
        pytest.param(
            "arn:mytopic", "arn:mytopic", False, id="sns-topic-arn-provided"
        ),
    ],
)
async def test_subscribe_when_bucket_exists(
    api: ApiSession, topic: str, topic_arn: str, create_topic: bool
) -> None:
    # Upstream's describe fixtures give mappings; on the wire they are the
    # modeled empty lists.
    replies: list[dict[str, Any]] = [
        {},
        *([{"TopicArn": "my-topic-arn"}] if create_topic else []),
        {},
        {},
        {},
        {"ConfigurationRecorders": []},
        {"DeliveryChannels": []},
    ]
    result = await api.run(
        f"configservice subscribe --s3-bucket mybucket --sns-topic {topic}"
        " --iam-role myrole",
        replies=replies,
    )
    assert result.operations_with_params == subscribe_calls(
        topic_arn, create_topic
    )
