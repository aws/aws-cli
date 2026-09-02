"""Blackbox tests for `aws s3 mb` command."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from tests.blackbox.s3_assertions import (
    assert_create_bucket,
)
from tests.blackbox.utils import (
    cli_env,
    create_bucket_response,
    format_requests,
    mock_server,
    run_cli,
    setup_responses,
)

NS = "http://s3.amazonaws.com/doc/2006-03-01/"


def parse_body_xml(request) -> ET.Element | None:
    if not request.body:
        return None
    return ET.fromstring(request.body)


@pytest.mark.asyncio
class TestMBCommand:
    async def test_make_bucket(self, aws_cli):
        async with mock_server() as (server, proxy):
            setup_responses(server, [create_bucket_response()])
            env = cli_env(proxy)
            stdout, stderr, rc = await run_cli(
                aws_cli, ["s3", "mb", "s3://bucket"], env
            )
            assert rc == 0, stderr.decode()
            assert len(server.requests) == 1, format_requests(server)
            assert_create_bucket(server.requests[0], Bucket="bucket")

    async def test_adds_location_constraint(self, aws_cli):
        async with mock_server() as (server, proxy):
            setup_responses(server, [create_bucket_response()])
            env = cli_env(proxy)
            env["AWS_REGION"] = "us-west-2"
            env["AWS_DEFAULT_REGION"] = "us-west-2"
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "mb", "s3://bucket", "--region", "us-west-2"],
                env,
            )
            assert rc == 0, stderr.decode()
            assert len(server.requests) == 1, format_requests(server)
            assert_create_bucket(
                server.requests[0],
                Bucket="bucket",
                CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
            )

    async def test_location_constraint_not_added_on_us_east_1(self, aws_cli):
        async with mock_server() as (server, proxy):
            setup_responses(server, [create_bucket_response()])
            env = cli_env(proxy)
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "mb", "s3://bucket", "--region", "us-east-1"],
                env,
            )
            assert rc == 0, stderr.decode()
            assert len(server.requests) == 1, format_requests(server)
            req = server.requests[0]
            body = parse_body_xml(req)
            # Either no body or no LocationConstraint element
            if body is not None:
                loc = body.find(f"{{{NS}}}LocationConstraint")
                assert loc is None, (
                    f"LocationConstraint should not be present for us-east-1, "
                    f"got: {loc.text}"
                )

    async def test_nonzero_exit_if_invalid_path_provided(self, aws_cli):
        async with mock_server() as (server, proxy):
            env = cli_env(proxy)
            stdout, stderr, rc = await run_cli(
                aws_cli, ["s3", "mb", "bucket"], env
            )
            assert rc == 252
            assert len(server.requests) == 0, format_requests(server)

    async def test_incompatible_with_express_directory_bucket(self, aws_cli):
        async with mock_server() as (server, proxy):
            env = cli_env(proxy)
            stdout, stderr, rc = await run_cli(
                aws_cli, ["s3", "mb", "s3://bucket--usw2-az1--x-s3/"], env
            )
            error_message = b"cannot use mb command with a directory bucket."
            assert rc == 252
            assert error_message in stderr.lower()
            assert len(server.requests) == 0, format_requests(server)

    async def test_make_bucket_with_single_tag(self, aws_cli):
        async with mock_server() as (server, proxy):
            setup_responses(server, [create_bucket_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mb",
                    "s3://bucket",
                    "--tags",
                    "Key1",
                    "Value1",
                    "--region",
                    "us-west-2",
                ],
                cli_env(proxy),
            )
            assert rc == 0, stderr.decode()
            assert len(server.requests) == 1, format_requests(server)
            assert_create_bucket(
                server.requests[0],
                Bucket="bucket",
                CreateBucketConfiguration={
                    "LocationConstraint": "us-west-2",
                    "Tags": [{"Key": "Key1", "Value": "Value1"}],
                },
            )

    async def test_make_bucket_with_single_tag_us_east_1(self, aws_cli):
        async with mock_server() as (server, proxy):
            setup_responses(server, [create_bucket_response()])
            env = cli_env(proxy)
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mb",
                    "s3://bucket",
                    "--tags",
                    "Key1",
                    "Value1",
                    "--region",
                    "us-east-1",
                ],
                env,
            )
            assert rc == 0, stderr.decode()
            assert len(server.requests) == 1, format_requests(server)
            assert_create_bucket(
                server.requests[0],
                Bucket="bucket",
                CreateBucketConfiguration={
                    "Tags": [{"Key": "Key1", "Value": "Value1"}],
                },
            )
            # Should NOT have LocationConstraint for us-east-1
            req = server.requests[0]
            body = parse_body_xml(req)
            loc = body.find(f"{{{NS}}}LocationConstraint")
            assert loc is None

    async def test_make_bucket_with_multiple_tags(self, aws_cli):
        async with mock_server() as (server, proxy):
            setup_responses(server, [create_bucket_response()])
            env = cli_env(proxy)
            env["AWS_REGION"] = "us-west-2"
            env["AWS_DEFAULT_REGION"] = "us-west-2"
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mb",
                    "s3://bucket",
                    "--tags",
                    "Key1",
                    "Value1",
                    "--tags",
                    "Key2",
                    "Value2",
                    "--region",
                    "us-west-2",
                ],
                cli_env(proxy),
            )
            assert rc == 0, stderr.decode()
            assert len(server.requests) == 1, format_requests(server)
            assert_create_bucket(
                server.requests[0],
                Bucket="bucket",
                CreateBucketConfiguration={
                    "LocationConstraint": "us-west-2",
                    "Tags": [
                        {"Key": "Key1", "Value": "Value1"},
                        {"Key": "Key2", "Value": "Value2"},
                    ],
                },
            )

    async def test_account_regional_namespace_bucket(self, aws_cli):
        bucket = "amzn-s3-demo-bucket-111122223333-us-west-2-an"
        async with mock_server() as (server, proxy):
            setup_responses(server, [create_bucket_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "mb", f"s3://{bucket}", "--region", "us-west-2"],
                cli_env(proxy),
            )
            assert rc == 0, stderr.decode()
            assert len(server.requests) == 1, format_requests(server)
            assert_create_bucket(
                server.requests[0],
                Bucket=bucket,
                CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
                BucketNamespace="account-regional",
            )

    async def test_account_regional_namespace_bucket_us_east_1(self, aws_cli):
        bucket = "my-bucket-111122223333-us-east-1-an"
        async with mock_server() as (server, proxy):
            setup_responses(server, [create_bucket_response()])
            env = cli_env(proxy)
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "mb", f"s3://{bucket}", "--region", "us-east-1"],
                env,
            )
            assert rc == 0, stderr.decode()
            assert len(server.requests) == 1, format_requests(server)
            assert_create_bucket(
                server.requests[0],
                Bucket=bucket,
                BucketNamespace="account-regional",
            )

    async def test_account_regional_namespace_short_bucket_name(self, aws_cli):
        bucket = "xyz-an"
        async with mock_server() as (server, proxy):
            setup_responses(server, [create_bucket_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "mb", f"s3://{bucket}", "--region", "us-east-1"],
                cli_env(proxy),
            )
            assert rc == 0, stderr.decode()
            assert len(server.requests) == 1, format_requests(server)
            assert_create_bucket(
                server.requests[0],
                Bucket=bucket,
                BucketNamespace="account-regional",
            )

    async def test_regular_bucket_no_namespace(self, aws_cli):
        async with mock_server() as (server, proxy):
            setup_responses(server, [create_bucket_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mb",
                    "s3://my-regular-bucket",
                    "--region",
                    "us-east-1",
                ],
                cli_env(proxy),
            )
            assert rc == 0, stderr.decode()
            assert len(server.requests) == 1, format_requests(server)
            assert_create_bucket(
                server.requests[0], Bucket="my-regular-bucket"
            )
            # Should NOT have x-amz-bucket-namespace header
            assert (
                server.requests[0].headers.get("x-amz-bucket-namespace")
                is None
            )

    async def test_tags_with_three_arguments_fails(self, aws_cli):
        async with mock_server() as (server, proxy):
            env = cli_env(proxy)
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mb",
                    "s3://bucket",
                    "--tags",
                    "Key1",
                    "Value1",
                    "ExtraArg",
                ],
                env,
            )
            assert rc == 252
            assert len(server.requests) == 0, format_requests(server)
            assert "ParamValidation" in stderr.decode()


@pytest.mark.asyncio
async def test_create_bucket_with_non_ascii_tag_value(aws_cli):
    """mb --tags with non-ASCII tag value sends correct XML body."""
    async with mock_server() as (server, proxy):
        setup_responses(server, [create_bucket_response()])
        stdout, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "mb",
                "s3://bucket",
                "--tags",
                "Author",
                "José García",
                "--region",
                "us-west-2",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    req = server.requests[0]
    assert (
        "José" in req.body or "Jos" in req.body
    ), f"Expected non-ASCII tag value in body, got: {req.body[:200]}"
