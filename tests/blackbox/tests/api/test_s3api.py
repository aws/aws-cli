"""s3api list-objects' requests (upstream tests/functional/s3api)."""

import base64
import json
from typing import Any, Final

import pytest

from apihelpers import ApiSession

pytestmark = pytest.mark.asyncio

LIST_OBJECTS_REPLY: Final = {"Contents": []}
# botocore asks S3 to URL-encode the keys it lists.
ENCODING: Final = {"EncodingType": "url"}


def starting_token(token: dict[str, str]) -> str:
    return base64.b64encode(json.dumps(token).encode()).decode()


@pytest.mark.parametrize(
    ("args", "params"),
    [
        pytest.param([], {"Bucket": "mybucket", **ENCODING}, id="simple"),
        # --max-items is the CLI's paginator limit, not the service's.
        pytest.param(
            ["--max-items", "100"],
            {"Bucket": "mybucket", **ENCODING},
            id="max-items",
        ),
        pytest.param(
            ["--page-size", "100"],
            {"Bucket": "mybucket", "MaxKeys": 100, **ENCODING},
            id="page-size",
        ),
        pytest.param(
            ["--starting-token", starting_token({"Marker": "foo"})],
            {"Bucket": "mybucket", "Marker": "foo", **ENCODING},
            id="starting-token",
        ),
        pytest.param(
            ["--no-paginate"],
            {"Bucket": "mybucket", **ENCODING},
            id="no-paginate",
        ),
        # The hidden --max-keys turns pagination off: one request.
        pytest.param(
            ["--max-keys", "1"],
            {"Bucket": "mybucket", "MaxKeys": 1, **ENCODING},
            id="max-keys",
        ),
    ],
)
async def test_list_objects_sends_params(
    api: ApiSession, args: list[str], params: dict[str, Any]
) -> None:
    run = await api.assert_params_for_cmd(
        ["s3api", "list-objects", "--bucket", "mybucket", *args],
        params,
        replies=LIST_OBJECTS_REPLY,
    )
    assert run.operations == ["ListObjects"]


async def test_list_objects_no_paginate_rejects_pagination_args(
    api: ApiSession,
) -> None:
    run = await api.assert_params_for_cmd(
        "s3api list-objects --bucket mybucket --no-paginate --max-items 100",
        expected_rc=252,
        stderr_contains=(
            "Cannot specify --no-paginate along with pagination arguments:"
            " --max-items"
        ),
        replies=LIST_OBJECTS_REPLY,
    )
    assert run.calls == ()
