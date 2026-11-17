"""Firehose commands' requests (upstream tests/functional/firehose)."""

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio


async def test_put_record_batch_shorthand(api: ApiSession) -> None:
    # Each record's Data is a blob given in base64: "foo" and "bar".
    await api.assert_params_for_cmd(
        "firehose put-record-batch --delivery-stream-name foo"
        " --records Zm9v YmFy",
        {
            "DeliveryStreamName": "foo",
            "Records": [{"Data": b"foo"}, {"Data": b"bar"}],
        },
    )
