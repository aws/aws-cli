"""`s3 rm`'s requests (upstream tests/functional/s3/test_rm_command.py).

Each of upstream's classic-client tests runs on both clients. Its CRT
client tests assert what the CRT client was asked to send; here the
requests on the wire are asserted, the CRT client's told apart by their
User-Agent.
"""

from typing import Final

import pytest

from apihelpers import ApiSession, Call, Reply
from s3params import (
    delete_object_request,
    list_objects_request,
    list_objects_response,
)

pytestmark = pytest.mark.asyncio

# Upstream's CRT client tests run in this region.
CRT_REGION: Final = "us-west-2"
CRT_HOST: Final = f"bucket.s3.{CRT_REGION}.amazonaws.com"
# The CRT client appends its name to the User-Agent of each request it
# sends.
CRT_USER_AGENT: Final = "CRTS3NativeClient/"
# S3's DeleteObject answer: 204 with its request ids. The CRT client
# rejects a 204 without headers.
DELETED: Final = Reply(
    headers={"x-amz-request-id": "REQUESTID", "x-amz-id-2": "HOSTID"}
)


def sent_by_crt(call: Call) -> bool:
    return CRT_USER_AGENT in call.request.headers.get("user-agent", "")


def wire_requests(
    calls: tuple[Call, ...],
) -> list[tuple[str, str, str, bool]]:
    """Each request's method, host, and target, and whether the CRT client
    sent it: upstream's CRT tests tell the CRT client's requests from
    botocore's."""
    return [
        (
            call.request.method,
            call.request.headers.get("host", ""),
            call.request.target,
            sent_by_crt(call),
        )
        for call in calls
    ]


async def test_rm_sends_only_delete_object(transfer_api: ApiSession) -> None:
    result = await transfer_api.run(
        "s3 rm s3://bucket/key.txt", replies=DELETED
    )
    assert result.operations == ["DeleteObject"], result.describe()


async def test_rm_dryrun_sends_nothing(transfer_api: ApiSession) -> None:
    result = await transfer_api.run("s3 rm s3://bucket/key.txt --dryrun")
    assert result.operations_with_params == [], result.describe()
    assert (
        "(dryrun) delete: s3://bucket/key.txt" in result.stdout
    ), result.describe()


async def test_rm_with_request_payer(transfer_api: ApiSession) -> None:
    result = await transfer_api.run(
        "s3 rm s3://mybucket/mykey --request-payer", replies=DELETED
    )
    assert result.operations_with_params == [
        delete_object_request("mybucket", "mykey", RequestPayer="requester")
    ], result.describe()


async def test_rm_recursive_with_request_payer(
    transfer_api: ApiSession,
) -> None:
    result = await transfer_api.run(
        "s3 rm s3://mybucket/ --recursive --request-payer",
        replies=[list_objects_response(["mykey"]), DELETED],
    )
    # botocore asks for URL-encoded keys after upstream's capture.
    assert result.operations_with_params == [
        list_objects_request(
            "mybucket", EncodingType="url", RequestPayer="requester"
        ),
        delete_object_request("mybucket", "mykey", RequestPayer="requester"),
    ], result.describe()


async def test_rm_on_crt_client_deletes_the_key(s3crt: ApiSession) -> None:
    s3crt.env["AWS_DEFAULT_REGION"] = CRT_REGION
    result = await s3crt.run(["s3", "rm", "s3://bucket/key"], replies=DELETED)
    assert wire_requests(result.calls) == [
        ("DELETE", CRT_HOST, "/key", True)
    ], result.describe()


async def test_rm_recursive_on_crt_client_deletes_each_key(
    s3crt: ApiSession,
) -> None:
    s3crt.env["AWS_DEFAULT_REGION"] = CRT_REGION
    result = await s3crt.run(
        ["s3", "rm", "s3://bucket/", "--recursive"],
        replies=[list_objects_response(["key1", "key2"]), DELETED, DELETED],
    )
    listing, *deletes = result.calls
    assert (listing.operation, sent_by_crt(listing)) == (
        "ListObjectsV2",
        False,
    ), result.describe()
    # The CRT client may send its deletes in either order.
    assert sorted(wire_requests(tuple(deletes))) == [
        ("DELETE", CRT_HOST, "/key1", True),
        ("DELETE", CRT_HOST, "/key2", True),
    ], result.describe()
