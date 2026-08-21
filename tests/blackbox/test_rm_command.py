"""Blackbox tests for `aws s3 rm` command."""

from __future__ import annotations

import pytest

from tests.blackbox.s3_assertions import (
    assert_delete_object,
    assert_list_objects_v2,
)

from tests.blackbox.utils import (
    cli_env,
    delete_response,
    format_requests,
    list_objects_xml,
    run_cli,
    mock_server,
    setup_responses,
    xml_response,
)


def list_objects_response_xml(keys: list[str]) -> str:
    contents = [
        {"Key": k, "Size": 100, "LastModified": "2014-01-09T20:45:49.000Z"}
        for k in keys
    ]
    return list_objects_xml(contents=contents)


@pytest.mark.asyncio
async def test_operations_used(aws_cli: str) -> None:
    """rm s3://bucket/key.txt should make exactly one DELETE request."""
    async with mock_server() as (server, proxy):
        setup_responses(server, [delete_response()])

        stdout, stderr, rc = await run_cli(
            aws_cli, ["s3", "rm", "s3://bucket/key.txt"], cli_env(proxy)
        )

    assert (
        rc == 0
    ), f"stdout={stdout!r} stderr={stderr!r}\n{format_requests(server)}"
    assert len(server.requests) == 1
    assert_delete_object(
        server.requests[0], Bucket="bucket", Key="key.txt"
    )


@pytest.mark.asyncio
async def test_dryrun_delete(aws_cli: str) -> None:
    """rm --dryrun should not make any requests."""
    async with mock_server() as (server, proxy):
        # No responses needed — no requests should be made
        setup_responses(server, [])

        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "rm", "s3://bucket/key.txt", "--dryrun"],
            cli_env(proxy),
        )

    assert (
        rc == 0
    ), f"stdout={stdout!r} stderr={stderr!r}\n{format_requests(server)}"
    assert len(server.requests) == 0
    assert b"(dryrun) delete: s3://bucket/key.txt" in stdout


@pytest.mark.asyncio
async def test_delete_with_request_payer(aws_cli: str) -> None:
    """rm --request-payer should send x-amz-request-payer header."""
    async with mock_server() as (server, proxy):
        setup_responses(server, [delete_response()])

        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "rm", "s3://mybucket/mykey", "--request-payer"],
            cli_env(proxy),
        )

    assert (
        rc == 0
    ), f"stdout={stdout!r} stderr={stderr!r}\n{format_requests(server)}"
    assert len(server.requests) == 1
    assert_delete_object(
        server.requests[0],
        Bucket="mybucket",
        Key="mykey",
        RequestPayer="requester",
    )


@pytest.mark.asyncio
async def test_recursive_delete_with_request_payer(aws_cli: str) -> None:
    """rm --recursive --request-payer should list then delete with request-payer on both."""
    response_xml = list_objects_response_xml(["mykey"])

    async with mock_server() as (server, proxy):
        setup_responses(
            server,
            [
                xml_response(response_xml),
                delete_response(),
            ],
        )

        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "rm", "s3://mybucket/", "--recursive", "--request-payer"],
            cli_env(proxy),
        )

    assert (
        rc == 0
    ), f"stdout={stdout!r} stderr={stderr!r}\n{format_requests(server)}"
    assert len(server.requests) == 2

    # First request: ListObjectsV2
    assert_list_objects_v2(
        server.requests[0],
        Bucket="mybucket",
        RequestPayer="requester",
    )

    # Second request: DeleteObject
    assert_delete_object(
        server.requests[1],
        Bucket="mybucket",
        Key="mykey",
        RequestPayer="requester",
    )
