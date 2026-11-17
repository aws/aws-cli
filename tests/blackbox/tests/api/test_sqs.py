"""SQS commands' requests (upstream tests/functional/sqs)."""

from typing import Any, Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

QUEUE_URL: Final = "https://queue.amazonaws.com/4444/testcli"
RECEIPT_HANDLE: Final = "abcedfghijklmnopqrstuvwxyz"


@pytest.mark.parametrize(
    ("args", "operation", "params"),
    [
        pytest.param(
            f"add-permission --queue-url {QUEUE_URL}"
            " --aws-account-ids 888888888888 --actions SendMessage"
            " --label FooBarLabel",
            "AddPermission",
            {
                "QueueUrl": QUEUE_URL,
                "Actions": ["SendMessage"],
                "AWSAccountIds": ["888888888888"],
                "Label": "FooBarLabel",
            },
            id="add-permission",
        ),
        pytest.param(
            f"add-permission --queue-url {QUEUE_URL}"
            " --aws-account-ids 888888888888 999999999999"
            " --actions SendMessage --label FooBarLabel",
            "AddPermission",
            {
                "QueueUrl": QUEUE_URL,
                "Actions": ["SendMessage"],
                "AWSAccountIds": ["888888888888", "999999999999"],
                "Label": "FooBarLabel",
            },
            id="add-permission-multiple-accounts",
        ),
        pytest.param(
            f"add-permission --queue-url {QUEUE_URL}"
            " --aws-account-ids 888888888888"
            " --actions SendMessage ReceiveMessage --label FooBarLabel",
            "AddPermission",
            {
                "QueueUrl": QUEUE_URL,
                "Actions": ["SendMessage", "ReceiveMessage"],
                "AWSAccountIds": ["888888888888"],
                "Label": "FooBarLabel",
            },
            id="add-permission-multiple-actions",
        ),
        pytest.param(
            f"change-message-visibility --queue-url {QUEUE_URL}"
            f" --receipt-handle {RECEIPT_HANDLE} --visibility-timeout 30",
            "ChangeMessageVisibility",
            {
                "QueueUrl": QUEUE_URL,
                "ReceiptHandle": RECEIPT_HANDLE,
                "VisibilityTimeout": 30,
            },
            id="change-message-visibility",
        ),
        pytest.param(
            "create-queue --queue-name foobar",
            "CreateQueue",
            {"QueueName": "foobar"},
            id="create-queue",
        ),
        pytest.param(
            f"get-queue-attributes --queue-url {QUEUE_URL}",
            "GetQueueAttributes",
            {"QueueUrl": QUEUE_URL},
            id="get-queue-attributes-no-attr",
        ),
        pytest.param(
            f"get-queue-attributes --queue-url {QUEUE_URL}"
            " --attribute-names All",
            "GetQueueAttributes",
            {"QueueUrl": QUEUE_URL, "AttributeNames": ["All"]},
            id="get-queue-attributes-all",
        ),
        pytest.param(
            f"get-queue-attributes --queue-url {QUEUE_URL}"
            " --attribute-names VisibilityTimeout",
            "GetQueueAttributes",
            {"QueueUrl": QUEUE_URL, "AttributeNames": ["VisibilityTimeout"]},
            id="get-queue-attributes-one",
        ),
        pytest.param(
            f"get-queue-attributes --queue-url {QUEUE_URL}"
            " --attribute-names VisibilityTimeout QueueArn",
            "GetQueueAttributes",
            {
                "QueueUrl": QUEUE_URL,
                "AttributeNames": ["VisibilityTimeout", "QueueArn"],
            },
            id="get-queue-attributes-two",
        ),
        pytest.param(
            "list-queues", "ListQueues", {}, id="list-queues-no-param"
        ),
        pytest.param(
            "list-queues --queue-name-prefix test",
            "ListQueues",
            {"QueueNamePrefix": "test"},
            id="list-queues-prefix",
        ),
        pytest.param(
            "purge-queue --queue-url https://foo.bar/queue",
            "PurgeQueue",
            {"QueueUrl": "https://foo.bar/queue"},
            id="purge-queue",
        ),
        pytest.param(
            f"set-queue-attributes --queue-url {QUEUE_URL}"
            ' --attributes {"VisibilityTimeout":"15"}',
            "SetQueueAttributes",
            {"QueueUrl": QUEUE_URL, "Attributes": {"VisibilityTimeout": "15"}},
            id="set-queue-attributes-json",
        ),
        pytest.param(
            f"set-queue-attributes --queue-url {QUEUE_URL}"
            " --attributes VisibilityTimeout=15",
            "SetQueueAttributes",
            {"QueueUrl": QUEUE_URL, "Attributes": {"VisibilityTimeout": "15"}},
            id="set-queue-attributes-shorthand",
        ),
    ],
)
async def test_sqs_command_sends_params(
    api: ApiSession, args: str, operation: str, params: dict[str, Any]
) -> None:
    run = await api.assert_params_for_cmd(f"sqs {args}", params)
    assert run.operations == [operation]
