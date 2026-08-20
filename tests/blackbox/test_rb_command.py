"""Blackbox tests for `aws s3 rb` command."""

from __future__ import annotations

import pytest

from tests.blackbox.utils import (
    assert_s3_operation,
    cli_env,
    delete_bucket_response,
    delete_response,
    error_response,
    format_requests,
    list_objects_xml,
    run_cli,
    mock_server,
    setup_responses,
    xml_response,
)


def list_objects_response_xml(keys: list[str]) -> str:
    contents = [
        {"Key": k, "Size": 100, "LastModified": "2016-03-01T23:50:13.000Z"}
        for k in keys
    ]
    return list_objects_xml(contents=contents)


def empty_list_response_xml() -> str:
    return list_objects_xml()


@pytest.mark.asyncio
class TestRBCommand:
    async def test_rb(self, aws_cli):
        async with mock_server() as (server, proxy):
            setup_responses(server, [delete_bucket_response()])
            env = cli_env(proxy)
            stdout, stderr, rc = await run_cli(
                aws_cli, ["s3", "rb", "s3://bucket"], env
            )
            assert rc == 0, stderr.decode()
            assert len(server.requests) == 1, format_requests(server)
            assert_s3_operation(
                server.requests[0], "DeleteBucket", Bucket="bucket"
            )

    async def test_rb_force_empty_bucket(self, aws_cli):
        async with mock_server() as (server, proxy):
            setup_responses(
                server,
                [
                    xml_response(empty_list_response_xml()),
                    delete_bucket_response(),
                ],
            )
            env = cli_env(proxy)
            stdout, stderr, rc = await run_cli(
                aws_cli, ["s3", "rb", "s3://bucket", "--force"], env
            )
            assert rc == 0, stderr.decode()
            assert len(server.requests) == 2, format_requests(server)
            # First: ListObjectsV2
            assert_s3_operation(
                server.requests[0], "ListObjectsV2", Bucket="bucket"
            )
            # Second: DeleteBucket
            assert_s3_operation(
                server.requests[1], "DeleteBucket", Bucket="bucket"
            )

    async def test_rb_force_non_empty_bucket(self, aws_cli):
        async with mock_server() as (server, proxy):
            setup_responses(
                server,
                [
                    xml_response(list_objects_response_xml(["foo"])),
                    delete_response(),
                    delete_bucket_response(),
                ],
            )
            env = cli_env(proxy)
            stdout, stderr, rc = await run_cli(
                aws_cli, ["s3", "rb", "s3://bucket", "--force"], env
            )
            assert rc == 0, stderr.decode()
            assert len(server.requests) == 3, format_requests(server)
            # ListObjectsV2
            assert_s3_operation(
                server.requests[0], "ListObjectsV2", Bucket="bucket"
            )
            # DeleteObject
            assert_s3_operation(
                server.requests[1], "DeleteObject", Bucket="bucket", Key="foo"
            )
            # DeleteBucket
            assert_s3_operation(
                server.requests[2], "DeleteBucket", Bucket="bucket"
            )

    async def test_rb_failed_rc(self, aws_cli):
        async with mock_server() as (server, proxy):
            setup_responses(server, [error_response()])
            env = cli_env(proxy)
            stdout, stderr, rc = await run_cli(
                aws_cli, ["s3", "rb", "s3://bucket"], env
            )
            assert rc == 1
            assert b"remove_bucket failed:" in stderr

    async def test_rb_force_with_failed_rm(self, aws_cli):
        async with mock_server() as (server, proxy):
            setup_responses(server, [error_response()])
            env = cli_env(proxy)
            stdout, stderr, rc = await run_cli(
                aws_cli, ["s3", "rb", "s3://bucket", "--force"], env
            )
            assert rc == 255
            assert b"remove_bucket failed:" in stderr
            # Should have attempted ListObjectsV2 only (failed there)
            assert len(server.requests) == 1, format_requests(server)
            assert_s3_operation(
                server.requests[0], "ListObjectsV2", Bucket="bucket"
            )

    async def test_nonzero_exit_if_uri_scheme_not_provided(self, aws_cli):
        async with mock_server() as (server, proxy):
            env = cli_env(proxy)
            stdout, stderr, rc = await run_cli(
                aws_cli, ["s3", "rb", "bucket"], env
            )
            assert rc == 252
            assert len(server.requests) == 0, format_requests(server)

    async def test_nonzero_exit_if_key_provided(self, aws_cli):
        async with mock_server() as (server, proxy):
            env = cli_env(proxy)
            # With --force
            stdout, stderr, rc = await run_cli(
                aws_cli, ["s3", "rb", "s3://bucket/key", "--force"], env
            )
            assert rc == 252
            assert len(server.requests) == 0, format_requests(server)

            # Without --force
            stdout, stderr, rc = await run_cli(
                aws_cli, ["s3", "rb", "s3://bucket/key"], env
            )
            assert rc == 252
            assert len(server.requests) == 0, format_requests(server)
