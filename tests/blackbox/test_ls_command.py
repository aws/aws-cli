"""Blackbox tests for `aws s3 ls` command."""

from __future__ import annotations

import os

import pytest
from dateutil import parser, tz
from dateutil import parser as dateutil_parser

from tests.blackbox.s3_assertions import (
    assert_list_buckets,
    assert_list_objects_v2,
)

from tests.blackbox.utils import (
    cli_env,
    format_requests,
    get_query_params,
    list_objects_xml,
    run_cli,
    mock_server,
    setup_responses,
    xml_response,
)


def list_buckets_xml() -> str:
    return (
        '<?xml version="1.0" ?>'
        '<ListAllMyBucketsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        "<Buckets/>"
        "</ListAllMyBucketsResult>"
    )


@pytest.mark.asyncio
async def test_errors_out_with_extra_arguments(aws_cli: str) -> None:
    env = {
        **os.environ,
        "AWS_ACCESS_KEY_ID": "test",
        "AWS_SECRET_ACCESS_KEY": "test",
        "AWS_DEFAULT_REGION": "us-east-1",
    }
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "--extra-argument-foo"], env
    )
    assert rc == 252
    assert b"--extra-argument-foo" in stderr


@pytest.mark.asyncio
async def test_operations_used_in_recursive_list(aws_cli: str) -> None:
    time_utc = "2014-01-09T20:45:49.000Z"
    response_xml = list_objects_xml(
        contents=[
            {"Key": "foo/bar.txt", "Size": 100, "LastModified": time_utc}
        ]
    )

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "ls", "s3://bucket/", "--recursive"],
            cli_env(proxy),
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"

    # Should have made exactly one request (ListObjectsV2)
    assert len(server.requests) == 1
    req = server.requests[0]
    assert_list_objects_v2(req, Bucket="bucket")

    params = get_query_params(req)
    # Recursive listing should not include a delimiter
    assert "delimiter" not in params

    # Time is stored in UTC but displayed in local timezone
    time_local = dateutil_parser.parse(time_utc).astimezone(tz.tzlocal())
    expected_stdout = (
        f"{time_local.strftime('%Y-%m-%d %H:%M:%S')}        100 foo/bar.txt\n"
    )
    assert stdout.decode() == expected_stdout


@pytest.mark.asyncio
async def test_list_buckets_use_page_size(aws_cli: str) -> None:
    response_xml = list_buckets_xml()

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli, ["s3", "ls", "--page-size", "8"], cli_env(proxy)
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"
    assert len(server.requests) == 1
    req = server.requests[0]
    assert_list_buckets(req, MaxBuckets="8")


@pytest.mark.asyncio
async def test_operations_use_page_size(aws_cli: str) -> None:
    time_utc = "2014-01-09T20:45:49.000Z"
    response_xml = list_objects_xml(
        contents=[
            {"Key": "foo/bar.txt", "Size": 100, "LastModified": time_utc}
        ]
    )

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "ls", "s3://bucket/", "--page-size", "8"],
            cli_env(proxy),
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"
    assert len(server.requests) == 1
    req = server.requests[0]
    assert_list_objects_v2(req, Bucket="bucket", MaxKeys="8")


@pytest.mark.asyncio
async def test_operations_use_page_size_recursive(aws_cli: str) -> None:
    time_utc = "2014-01-09T20:45:49.000Z"
    response_xml = list_objects_xml(
        contents=[
            {"Key": "foo/bar.txt", "Size": 100, "LastModified": time_utc}
        ]
    )

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "ls", "s3://bucket/", "--page-size", "8", "--recursive"],
            cli_env(proxy),
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"
    assert len(server.requests) == 1
    req = server.requests[0]
    assert_list_objects_v2(req, Bucket="bucket", MaxKeys="8")
    params = get_query_params(req)
    assert "delimiter" not in params


@pytest.mark.asyncio
async def test_success_rc_has_prefixes_and_objects(aws_cli: str) -> None:
    time_utc = "2014-01-09T20:45:49.000Z"
    response_xml = list_objects_xml(
        contents=[
            {"Key": "foo/bar.txt", "Size": 100, "LastModified": time_utc}
        ],
        common_prefixes=["foo/"],
    )

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli, ["s3", "ls", "s3://bucket/foo"], cli_env(proxy)
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"


@pytest.mark.asyncio
async def test_success_rc_has_only_prefixes(aws_cli: str) -> None:
    response_xml = list_objects_xml(common_prefixes=["foo/"])

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli, ["s3", "ls", "s3://bucket/foo"], cli_env(proxy)
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"


@pytest.mark.asyncio
async def test_success_rc_has_only_objects(aws_cli: str) -> None:
    time_utc = "2014-01-09T20:45:49.000Z"
    response_xml = list_objects_xml(
        contents=[
            {"Key": "foo/bar.txt", "Size": 100, "LastModified": time_utc}
        ]
    )

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli, ["s3", "ls", "s3://bucket/foo"], cli_env(proxy)
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"


@pytest.mark.asyncio
async def test_success_rc_with_pagination(aws_cli: str) -> None:
    # Pagination should not affect a successful return code of zero, even
    # if there are no results on the second page because there were
    # results in previous pages.
    time_utc = "2014-01-09T20:45:49.000Z"
    page1_xml = list_objects_xml(
        contents=[
            {"Key": "foo/bar.txt", "Size": 100, "LastModified": time_utc}
        ],
        common_prefixes=["foo/"],
        is_truncated=True,
        next_continuation_token="token123",
    )
    page2_xml = list_objects_xml()

    async with mock_server() as (server, proxy):
        setup_responses(
            server,
            [
                xml_response(page1_xml),
                xml_response(page2_xml),
            ],
        )

        stdout, stderr, rc = await run_cli(
            aws_cli, ["s3", "ls", "s3://bucket/foo"], cli_env(proxy)
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"
    assert len(server.requests) == 2


@pytest.mark.asyncio
async def test_success_rc_empty_bucket_no_key_given(aws_cli: str) -> None:
    response_xml = list_objects_xml()

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli, ["s3", "ls", "s3://bucket"], cli_env(proxy)
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"


@pytest.mark.asyncio
async def test_fail_rc_no_objects_nor_prefixes(aws_cli: str) -> None:
    # Empty response with no Contents or CommonPrefixes, but a key prefix was given
    response_xml = list_objects_xml()

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli, ["s3", "ls", "s3://bucket/foo"], cli_env(proxy)
        )

    assert rc == 1


@pytest.mark.asyncio
async def test_human_readable_file_size(aws_cli: str) -> None:
    time_utc = "2014-01-09T20:45:49.000Z"
    response_xml = list_objects_xml(
        contents=[
            {"Key": "onebyte.txt", "Size": 1, "LastModified": time_utc},
            {"Key": "onekilobyte.txt", "Size": 1024, "LastModified": time_utc},
            {
                "Key": "onemegabyte.txt",
                "Size": 1024**2,
                "LastModified": time_utc,
            },
            {
                "Key": "onegigabyte.txt",
                "Size": 1024**3,
                "LastModified": time_utc,
            },
            {
                "Key": "oneterabyte.txt",
                "Size": 1024**4,
                "LastModified": time_utc,
            },
            {
                "Key": "onepetabyte.txt",
                "Size": 1024**5,
                "LastModified": time_utc,
            },
        ]
    )

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "ls", "s3://bucket/", "--human-readable"],
            cli_env(proxy),
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"
    stdout_str = stdout.decode()
    # Time is stored in UTC timezone, but the actual time displayed
    # is specific to your tzinfo, so shift the timezone to your local's.
    time_local = parser.parse(time_utc).astimezone(tz.tzlocal())
    time_fmt = time_local.strftime('%Y-%m-%d %H:%M:%S')
    assert f"{time_fmt}     1 Byte onebyte.txt" in stdout_str
    assert f"{time_fmt}    1.0 KiB onekilobyte.txt" in stdout_str
    assert f"{time_fmt}    1.0 MiB onemegabyte.txt" in stdout_str
    assert f"{time_fmt}    1.0 GiB onegigabyte.txt" in stdout_str
    assert f"{time_fmt}    1.0 TiB oneterabyte.txt" in stdout_str
    assert f"{time_fmt}    1.0 PiB onepetabyte.txt" in stdout_str


@pytest.mark.asyncio
async def test_summarize(aws_cli: str) -> None:
    time_utc = "2014-01-09T20:45:49.000Z"
    response_xml = list_objects_xml(
        contents=[
            {"Key": "onebyte.txt", "Size": 1, "LastModified": time_utc},
            {"Key": "onekilobyte.txt", "Size": 1024, "LastModified": time_utc},
            {
                "Key": "onemegabyte.txt",
                "Size": 1024**2,
                "LastModified": time_utc,
            },
            {
                "Key": "onegigabyte.txt",
                "Size": 1024**3,
                "LastModified": time_utc,
            },
            {
                "Key": "oneterabyte.txt",
                "Size": 1024**4,
                "LastModified": time_utc,
            },
            {
                "Key": "onepetabyte.txt",
                "Size": 1024**5,
                "LastModified": time_utc,
            },
        ]
    )

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "ls", "s3://bucket/", "--summarize"],
            cli_env(proxy),
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"
    stdout_str = stdout.decode()
    assert "Total Objects: 6\n" in stdout_str
    assert "Total Size: 1127000493261825\n" in stdout_str


@pytest.mark.asyncio
async def test_summarize_with_human_readable(aws_cli: str) -> None:
    time_utc = "2014-01-09T20:45:49.000Z"
    response_xml = list_objects_xml(
        contents=[
            {"Key": "onebyte.txt", "Size": 1, "LastModified": time_utc},
            {"Key": "onekilobyte.txt", "Size": 1024, "LastModified": time_utc},
            {
                "Key": "onemegabyte.txt",
                "Size": 1024**2,
                "LastModified": time_utc,
            },
            {
                "Key": "onegigabyte.txt",
                "Size": 1024**3,
                "LastModified": time_utc,
            },
            {
                "Key": "oneterabyte.txt",
                "Size": 1024**4,
                "LastModified": time_utc,
            },
            {
                "Key": "onepetabyte.txt",
                "Size": 1024**5,
                "LastModified": time_utc,
            },
        ]
    )

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "ls", "s3://bucket/", "--human-readable", "--summarize"],
            cli_env(proxy),
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"
    stdout_str = stdout.decode()
    assert "Total Objects: 6\n" in stdout_str
    assert "Total Size: 1.0 PiB\n" in stdout_str


@pytest.mark.asyncio
async def test_requester_pays(aws_cli: str) -> None:
    time_utc = "2014-01-09T20:45:49.000Z"
    response_xml = list_objects_xml(
        contents=[{"Key": "onebyte.txt", "Size": 1, "LastModified": time_utc}]
    )

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "ls", "s3://mybucket/foo/", "--request-payer", "requester"],
            cli_env(proxy),
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"
    assert len(server.requests) == 1
    req = server.requests[0]
    params = get_query_params(req)
    assert req.headers.get("host") == "mybucket.s3.us-east-1.amazonaws.com"
    assert params.get("delimiter") == ["/"]
    assert params.get("prefix") == ["foo/"]
    assert params.get("encoding-type") == ["url"]
    assert req.headers.get("x-amz-request-payer") == "requester"


@pytest.mark.asyncio
async def test_requester_pays_with_no_args(aws_cli: str) -> None:
    time_utc = "2014-01-09T20:45:49.000Z"
    response_xml = list_objects_xml(
        contents=[{"Key": "onebyte.txt", "Size": 1, "LastModified": time_utc}]
    )

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "ls", "s3://mybucket/foo/", "--request-payer"],
            cli_env(proxy),
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"
    assert len(server.requests) == 1
    req = server.requests[0]
    params = get_query_params(req)
    assert req.headers.get("host") == "mybucket.s3.us-east-1.amazonaws.com"
    assert params.get("delimiter") == ["/"]
    assert params.get("prefix") == ["foo/"]
    assert params.get("encoding-type") == ["url"]
    assert req.headers.get("x-amz-request-payer") == "requester"


@pytest.mark.asyncio
async def test_accesspoint_arn(aws_cli: str) -> None:
    time_utc = "2014-01-09T20:45:49.000Z"
    response_xml = list_objects_xml(
        contents=[{"Key": "bar.txt", "Size": 100, "LastModified": time_utc}]
    )

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        arn = "arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint"
        stdout, stderr, rc = await run_cli(
            aws_cli, ["s3", "ls", f"s3://{arn}"], cli_env(proxy)
        )

    assert (
        rc == 0
    ), f"stdout={stdout!r} stderr={stderr!r}\n{format_requests(server)}"
    assert len(server.requests) == 1
    req = server.requests[0]
    # For accesspoint ARNs: AccessPointName-AccountId.s3-accesspoint.Region.amazonaws.com
    assert (
        req.headers.get("host")
        == "endpoint-123456789012.s3-accesspoint.us-west-2.amazonaws.com"
    )


@pytest.mark.asyncio
async def test_list_buckets_uses_bucket_name_prefix(aws_cli: str) -> None:
    response_xml = list_buckets_xml()

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "ls", "--bucket-name-prefix", "myprefix"],
            cli_env(proxy),
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"
    assert len(server.requests) == 1
    req = server.requests[0]
    assert_list_buckets(req, Prefix="myprefix")


@pytest.mark.asyncio
async def test_list_buckets_uses_bucket_region(aws_cli: str) -> None:
    response_xml = list_buckets_xml()

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "ls", "--bucket-region", "us-west-1"],
            cli_env(proxy),
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"
    assert len(server.requests) == 1
    req = server.requests[0]
    assert_list_buckets(req, BucketRegion="us-west-1")


@pytest.mark.asyncio
async def test_list_objects_ignores_bucket_name_prefix(aws_cli: str) -> None:
    response_xml = list_objects_xml()

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "ls", "s3://mybucket", "--bucket-name-prefix", "myprefix"],
            cli_env(proxy),
        )

    assert (
        rc == 0
    ), f"stdout={stdout!r} stderr={stderr!r}\n{format_requests(server)}"
    assert len(server.requests) == 1
    req = server.requests[0]
    params = get_query_params(req)
    # --bucket-name-prefix should be ignored for object listings;
    # prefix is either absent or empty on the wire
    assert params.get("prefix", [""]) == [""]


@pytest.mark.asyncio
async def test_list_objects_ignores_bucket_region(aws_cli: str) -> None:
    response_xml = list_objects_xml()

    async with mock_server() as (server, proxy):
        setup_responses(server, [xml_response(response_xml)])

        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "ls", "s3://mybucket", "--bucket-region", "us-west-1"],
            cli_env(proxy),
        )

    assert rc == 0, f"stdout={stdout!r} stderr={stderr!r}"
    assert len(server.requests) == 1
    req = server.requests[0]
    params = get_query_params(req)
    assert "bucket-region" not in params



@pytest.mark.asyncio
async def test_list_objects_with_unicode_keys(aws_cli):
    """ls handles objects with Unicode keys (CJK, emoji)."""
    async with mock_server() as (server, proxy):
        setup_responses(
            server,
            [
                xml_response(
                    list_objects_xml(
                        contents=[
                            {
                                "Key": "文件.txt",
                                "Size": 100,
                                "LastModified": "2023-01-01T00:00:00Z",
                            },
                            {
                                "Key": "📄data.csv",
                                "Size": 200,
                                "LastModified": "2023-01-01T00:00:00Z",
                            },
                        ]
                    )
                ),
            ],
        )
        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "ls", "s3://bucket/"],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    output = stdout.decode()
    assert "文件.txt" in output
    assert "📄data.csv" in output


@pytest.mark.asyncio
async def test_list_objects_with_url_encoded_keys(aws_cli):
    """ls handles keys that S3 returns with URL encoding."""
    async with mock_server() as (server, proxy):
        setup_responses(
            server,
            [
                xml_response(
                    list_objects_xml(
                        contents=[
                            {
                                "Key": "my+file.txt",
                                "Size": 100,
                                "LastModified": "2023-01-01T00:00:00Z",
                            },
                            {
                                "Key": "path/to/my%20doc.pdf",
                                "Size": 200,
                                "LastModified": "2023-01-01T00:00:00Z",
                            },
                        ]
                    )
                ),
            ],
        )
        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "ls", "s3://bucket/"],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    output = stdout.decode()
    assert "my+file.txt" in output
    assert "my%20doc.pdf" in output
