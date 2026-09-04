"""Blackbox tests for `aws s3 mv` command."""

from __future__ import annotations

import asyncio
import os

import pytest
from localstub.handlers import handle_expect_header
from localstub.server import DropConnection, FaultyTransmission, HTTPResponse

from tests.blackbox.s3_assertions import (
    assert_abort_multipart_upload,
    assert_complete_multipart_upload,
    assert_copy_object,
    assert_create_multipart_upload,
    assert_delete_object,
    assert_get_access_point,
    assert_get_caller_identity,
    assert_get_object,
    assert_get_object_tagging,
    assert_head_object,
    assert_put_object,
    assert_put_object_tagging,
    assert_upload_part_copy,
)
from tests.blackbox.utils import (
    abort_mpu_response,
    cli_env,
    complete_mpu_response,
    copy_object_response,
    create_mpu_response,
    delete_response,
    error_response,
    format_requests,
    get_object_response,
    get_object_tagging_response,
    head_object_response,
    list_objects_xml,
    put_object_response,
    put_object_tagging_response,
    run_cli,
    mock_server,
    setup_responses,
    upload_part_copy_response,
    upload_part_response,
    xml_response,
)


@pytest.mark.asyncio
class TestMvCommand:
    async def test_cant_mv_object_onto_itself(self, aws_cli, tmp_path):
        """mv s3://bucket/key s3://bucket/key should fail."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "mv", "s3://bucket/key", "s3://bucket/key"],
                cli_env(proxy),
            )

        assert rc == 252
        assert b"Cannot mv a file onto itself" in stderr

    async def test_cant_mv_object_with_implied_name(self, aws_cli, tmp_path):
        """mv s3://bucket/key s3://bucket/ implies same key name."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "mv", "s3://bucket/key", "s3://bucket/"],
                cli_env(proxy),
            )

        assert rc == 252
        assert b"Cannot mv a file onto itself" in stderr

    async def test_dryrun_move(self, aws_cli, tmp_path):
        """mv s3->s3 --dryrun only does HeadObject, no copy or delete."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [head_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key.txt",
                    "s3://bucket/key2.txt",
                    "--dryrun",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_head_object(
            server.requests[0],
            Bucket="bucket",
            Key="key.txt",
            ChecksumMode="ENABLED",
        )
        assert (
            b"(dryrun) move: s3://bucket/key.txt to s3://bucket/key2.txt"
            in stdout
        )

    async def test_website_redirect_ignore_paramfile(self, aws_cli, tmp_path):
        """mv local s3:// --website-redirect uses the URL, not its contents."""
        src = tmp_path / "foo.txt"
        src.write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    str(src),
                    "s3://bucket/key.txt",
                    "--website-redirect",
                    "http://someserver",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(
            server.requests[0],
            Bucket="bucket",
            Key="key.txt",
            WebsiteRedirectLocation="http://someserver",
        )
        # Source file should be deleted after successful move
        assert not src.exists()

    async def test_metadata_directive_copy(self, aws_cli, tmp_path):
        """mv s3->s3 --metadata-directive REPLACE sends the directive on CopyObject."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key.txt",
                    "s3://bucket/key2.txt",
                    "--metadata-directive",
                    "REPLACE",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)
        assert_head_object(
            server.requests[0], Bucket="bucket", Key="key.txt"
        )
        assert_copy_object(
            server.requests[1],
            Bucket="bucket",
            Key="key2.txt",
            MetadataDirective="REPLACE",
        )
        assert_delete_object(
            server.requests[2], Bucket="bucket", Key="key.txt"
        )

    async def test_no_metadata_directive_for_non_copy(self, aws_cli, tmp_path):
        """mv local s3:// --metadata-directive REPLACE does not send directive on PutObject."""
        src = tmp_path / "foo.txt"
        src.write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    str(src),
                    "s3://bucket/key.txt",
                    "--metadata-directive",
                    "REPLACE",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(
            server.requests[0], Bucket="bucket", Key="key.txt"
        )
        # MetadataDirective header should NOT be present for uploads
        assert (
            server.requests[0].headers.get("x-amz-metadata-directive") is None
        )

    async def test_download_move_with_request_payer(self, aws_cli, tmp_path):
        """mv s3://bucket/key local --request-payer sends RequestPayer on all ops."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    get_object_response(b"foo"),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://mybucket/mykey",
                    str(tmp_path),
                    "--request-payer",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)
        assert_head_object(
            server.requests[0],
            Bucket="mybucket",
            Key="mykey",
            ChecksumMode="ENABLED",
            RequestPayer="requester",
        )
        assert_get_object(
            server.requests[1],
            Bucket="mybucket",
            Key="mykey",
            RequestPayer="requester",
        )
        assert_delete_object(
            server.requests[2],
            Bucket="mybucket",
            Key="mykey",
            RequestPayer="requester",
        )

    async def test_copy_move_with_request_payer(self, aws_cli, tmp_path):
        """mv s3->s3 --request-payer sends RequestPayer on all ops."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://sourcebucket/sourcekey",
                    "s3://mybucket/mykey",
                    "--request-payer",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)
        assert_head_object(
            server.requests[0],
            Bucket="sourcebucket",
            Key="sourcekey",
            ChecksumMode="ENABLED",
            RequestPayer="requester",
        )
        assert_copy_object(
            server.requests[1],
            Bucket="mybucket",
            Key="mykey",
            CopySource="sourcebucket/sourcekey",
            RequestPayer="requester",
        )
        assert_delete_object(
            server.requests[2],
            Bucket="sourcebucket",
            Key="sourcekey",
            RequestPayer="requester",
        )

    async def test_with_copy_props(self, aws_cli, tmp_path):
        """mv s3->s3 --copy-props default preserves tags via multipart copy."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            large_tag_set = {"tag-key": "val" * 3000}
            setup_responses(
                server,
                [
                    head_object_response(content_length=8 * 1024**2),
                    get_object_tagging_response(large_tag_set),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                    put_object_tagging_response(),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://sourcebucket/sourcekey",
                    "s3://bucket/key",
                    "--copy-props",
                    "default",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 7, format_requests(server)
        assert_head_object(
            server.requests[0],
            Bucket="sourcebucket",
            Key="sourcekey",
            ChecksumMode="ENABLED",
        )
        assert_get_object_tagging(
            server.requests[1],
            Bucket="sourcebucket",
            Key="sourcekey",
        )
        assert_create_multipart_upload(
            server.requests[2],
            Bucket="bucket",
            Key="key",
        )
        assert_upload_part_copy(
            server.requests[3],
            Bucket="bucket",
            Key="key",
            CopySource="sourcebucket/sourcekey",
        )
        assert_complete_multipart_upload(
            server.requests[4],
            Bucket="bucket",
            Key="key",
            UploadId="upload_id",
        )
        assert_put_object_tagging(
            server.requests[5], Bucket="bucket", Key="key"
        )
        assert_delete_object(
            server.requests[6],
            Bucket="sourcebucket",
            Key="sourcekey",
        )

    async def test_mv_does_not_delete_source_on_failed_put_tagging(
        self, aws_cli, tmp_path
    ):
        """mv s3->s3 --copy-props default deletes dest (not source) on PutObjectTagging failure."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            large_tag_set = {"tag-key": "val" * 3000}
            setup_responses(
                server,
                [
                    head_object_response(content_length=8 * 1024**2),
                    get_object_tagging_response(large_tag_set),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                    error_response(
                        "AccessDenied", "Operation not allowed", status=403
                    ),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://sourcebucket/sourcekey",
                    "s3://bucket/key",
                    "--copy-props",
                    "default",
                ],
                cli_env(proxy),
            )

        assert rc == 1
        assert len(server.requests) == 7, format_requests(server)
        assert_head_object(
            server.requests[0],
            Bucket="sourcebucket",
            Key="sourcekey",
            ChecksumMode="ENABLED",
        )
        assert_get_object_tagging(
            server.requests[1],
            Bucket="sourcebucket",
            Key="sourcekey",
        )
        assert_create_multipart_upload(
            server.requests[2],
            Bucket="bucket",
            Key="key",
        )
        assert_upload_part_copy(
            server.requests[3],
            Bucket="bucket",
            Key="key",
            CopySource="sourcebucket/sourcekey",
        )
        assert_complete_multipart_upload(
            server.requests[4],
            Bucket="bucket",
            Key="key",
            UploadId="upload_id",
        )
        assert_put_object_tagging(
            server.requests[5], Bucket="bucket", Key="key"
        )
        # The delete should be for the destination (cleanup), not the source
        assert_delete_object(
            server.requests[6], Bucket="bucket", Key="key"
        )

    async def test_upload_with_checksum_algorithm_crc32(
        self, aws_cli, tmp_path
    ):
        """mv local s3:// --checksum-algorithm CRC32 sends the algorithm."""
        src = tmp_path / "foo.txt"
        src.write_text("contents")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    str(src),
                    "s3://bucket/key.txt",
                    "--checksum-algorithm",
                    "CRC32",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(
            server.requests[0],
            Bucket="bucket",
            Key="key.txt",
            ChecksumAlgorithm="CRC32",
        )
        assert not src.exists()

    async def test_download_with_checksum_mode_crc32(self, aws_cli, tmp_path):
        """mv s3://bucket/foo local --checksum-mode ENABLED sends ChecksumMode."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    get_object_response(
                        b"foo", **{"x-amz-checksum-crc32": "jHNlIQ=="}
                    ),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/foo",
                    str(tmp_path),
                    "--checksum-mode",
                    "ENABLED",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)
        assert_get_object(
            server.requests[1],
            Bucket="bucket",
            Key="foo",
            ChecksumMode="ENABLED",
        )
        assert_delete_object(
            server.requests[2], Bucket="bucket", Key="foo"
        )

    async def test_mv_no_overwrite_flag_when_object_not_exists_on_target(
        self, aws_cli, tmp_path
    ):
        """mv local s3:// --no-overwrite sends IfNoneMatch=* and deletes source on success."""
        src = tmp_path / "foo.txt"
        src.write_text("contents")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    str(src),
                    "s3://bucket/foo.txt",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(
            server.requests[0],
            Bucket="bucket",
            Key="foo.txt",
            IfNoneMatch="*",
        )
        assert not src.exists()

    async def test_mv_no_overwrite_flag_when_object_exists_on_target(
        self, aws_cli, tmp_path
    ):
        """mv local s3:// --no-overwrite with 412 keeps source file."""
        src = tmp_path / "foo.txt"
        src.write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    error_response(
                        "PreconditionFailed",
                        "At least one of the pre-conditions you specified did not hold",
                        status=412,
                    ),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    str(src),
                    "s3://bucket/foo.txt",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(
            server.requests[0],
            Bucket="bucket",
            Key="foo.txt",
            IfNoneMatch="*",
        )
        # Source file should NOT be deleted
        assert src.exists()

    async def test_mv_no_overwrite_flag_multipart_upload_when_object_not_exists_on_target(
        self, aws_cli, tmp_path
    ):
        """mv local s3:// --no-overwrite large file multipart sends IfNoneMatch on Complete."""
        src = tmp_path / "foo.txt"
        src.write_bytes(b"a" * 10 * (1024**2))
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    create_mpu_response("foo"),
                    upload_part_response("etag1"),
                    upload_part_response("etag2"),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    str(src),
                    "s3://bucket/foo.txt",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 4, format_requests(server)
        assert_create_multipart_upload(
            server.requests[0],
            Bucket="bucket",
            Key="foo.txt",
        )
        assert_complete_multipart_upload(
            server.requests[3],
            Bucket="bucket",
            Key="foo.txt",
            IfNoneMatch="*",
        )
        assert not src.exists()

    async def test_mv_no_overwrite_flag_multipart_upload_when_object_exists_on_target(
        self, aws_cli, tmp_path
    ):
        """mv local s3:// --no-overwrite large file with 412 on Complete aborts and keeps source."""
        src = tmp_path / "foo.txt"
        src.write_bytes(b"a" * 10 * (1024**2))
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    create_mpu_response("foo"),
                    upload_part_response("etag1"),
                    upload_part_response("etag2"),
                    error_response(
                        "PreconditionFailed",
                        "At least one of the pre-conditions you specified did not hold",
                        status=412,
                    ),
                    abort_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    str(src),
                    "s3://bucket/foo.txt",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 5, format_requests(server)
        assert_create_multipart_upload(
            server.requests[0],
            Bucket="bucket",
            Key="foo.txt",
        )
        assert_complete_multipart_upload(
            server.requests[3],
            Bucket="bucket",
            Key="foo.txt",
            IfNoneMatch="*",
        )
        assert_abort_multipart_upload(
            server.requests[4],
            Bucket="bucket",
            Key="foo.txt",
            UploadId="foo",
        )
        assert src.exists()

    async def test_mv_no_overwrite_flag_on_copy_when_small_object_does_not_exist_on_target(
        self, aws_cli, tmp_path
    ):
        """mv s3->s3 --no-overwrite small object sends IfNoneMatch on CopyObject and deletes source."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket1/key.txt",
                    "s3://bucket2/key1.txt",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)
        assert_head_object(
            server.requests[0], Bucket="bucket1", Key="key.txt"
        )
        assert_copy_object(
            server.requests[1],
            Bucket="bucket2",
            Key="key1.txt",
            IfNoneMatch="*",
        )
        assert_delete_object(
            server.requests[2], Bucket="bucket1", Key="key.txt"
        )

    async def test_mv_no_overwrite_flag_on_copy_when_small_object_exists_on_target(
        self, aws_cli, tmp_path
    ):
        """mv s3->s3 --no-overwrite small object with 412 does not delete source."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    error_response(
                        "PreconditionFailed",
                        "At least one of the pre-conditions you specified did not hold",
                        status=412,
                    ),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket1/key.txt",
                    "s3://bucket2/key.txt",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_head_object(
            server.requests[0], Bucket="bucket1", Key="key.txt"
        )
        assert_copy_object(
            server.requests[1],
            Bucket="bucket2",
            Key="key.txt",
            IfNoneMatch="*",
        )

    async def test_mv_no_overwrite_flag_when_large_object_does_not_exist_on_target(
        self, aws_cli, tmp_path
    ):
        """mv s3->s3 --no-overwrite large object multipart copy succeeds and deletes source."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=10 * (1024**2)),
                    get_object_tagging_response(),
                    create_mpu_response("foo"),
                    upload_part_copy_response(),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket1/key1.txt",
                    "s3://bucket/key.txt",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 7, format_requests(server)
        assert_head_object(
            server.requests[0], Bucket="bucket1", Key="key1.txt"
        )
        assert_get_object_tagging(
            server.requests[1],
            Bucket="bucket1",
            Key="key1.txt",
        )
        assert_create_multipart_upload(
            server.requests[2],
            Bucket="bucket",
            Key="key.txt",
        )
        assert_complete_multipart_upload(
            server.requests[5],
            Bucket="bucket",
            Key="key.txt",
            IfNoneMatch="*",
        )
        assert_delete_object(
            server.requests[6],
            Bucket="bucket1",
            Key="key1.txt",
        )

    async def test_mv_no_overwrite_flag_when_large_object_exists_on_target(
        self, aws_cli, tmp_path
    ):
        """mv s3->s3 --no-overwrite large object with 412 on Complete aborts."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=10 * (1024**2)),
                    get_object_tagging_response(),
                    create_mpu_response("foo"),
                    upload_part_copy_response(),
                    upload_part_copy_response(),
                    error_response(
                        "PreconditionFailed",
                        "At least one of the pre-conditions you specified did not hold",
                        status=412,
                    ),
                    abort_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket1/key1.txt",
                    "s3://bucket/key1.txt",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 7, format_requests(server)
        assert_head_object(
            server.requests[0], Bucket="bucket1", Key="key1.txt"
        )
        assert_get_object_tagging(
            server.requests[1],
            Bucket="bucket1",
            Key="key1.txt",
        )
        assert_create_multipart_upload(
            server.requests[2],
            Bucket="bucket",
            Key="key1.txt",
        )
        assert_complete_multipart_upload(
            server.requests[5],
            Bucket="bucket",
            Key="key1.txt",
            IfNoneMatch="*",
        )
        assert_abort_multipart_upload(
            server.requests[6],
            Bucket="bucket",
            Key="key1.txt",
            UploadId="foo",
        )

    async def test_no_overwrite_flag_on_mv_download_when_single_object_exists_at_target(
        self, aws_cli, tmp_path
    ):
        """mv s3://bucket/foo.txt local --no-overwrite skips if file exists locally."""
        target = tmp_path / "foo.txt"
        target.write_text("existing content")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [head_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/foo.txt",
                    str(target),
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_head_object(
            server.requests[0], Bucket="bucket", Key="foo.txt"
        )
        # File should retain original content (not overwritten)
        assert target.read_text() == "existing content"

    async def test_no_overwrite_flag_on_mv_download_when_single_object_does_not_exist_at_target(
        self, aws_cli, tmp_path
    ):
        """mv s3://bucket/foo.txt local --no-overwrite downloads and deletes source if no local file."""
        target = tmp_path / "foo.txt"
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    get_object_response(b"foo"),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/foo.txt",
                    str(target),
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)
        assert_head_object(
            server.requests[0], Bucket="bucket", Key="foo.txt"
        )
        assert_get_object(
            server.requests[1], Bucket="bucket", Key="foo.txt"
        )
        assert_delete_object(
            server.requests[2], Bucket="bucket", Key="foo.txt"
        )
        assert target.read_text() == "foo"


@pytest.mark.asyncio
async def test_mv_download_checksum_mismatch_fails(aws_cli, tmp_path):
    """mv s3->local --checksum-mode ENABLED fails if checksum doesn't match body."""
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(
            server,
            [
                head_object_response(),
                get_object_response(
                    b"foo", **{"x-amz-checksum-crc32": "AAAAAA=="}
                ),
            ],
        )
        stdout, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "mv",
                "s3://bucket/key.txt",
                str(tmp_path),
                "--checksum-mode",
                "ENABLED",
            ],
            cli_env(proxy),
        )

    assert rc == 1
    assert len(server.requests) == 2, format_requests(server)
    assert (
       b"Expected checksum AAAAAA== did not "
       b"match calculated checksum: jHNlIQ=="
   ) in stderr


@pytest.mark.asyncio
async def test_mv_upload_checksum_rejected_by_server(aws_cli, tmp_path):
    """mv upload fails when server rejects with BadDigest."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(
            server,
            [
                error_response(
                    "BadDigest",
                    "The CRC32 you specified did not match the calculated checksum.",
                    status=400,
                ),
            ],
        )
        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "mv", str(src), "s3://bucket/key.txt"],
            cli_env(proxy),
        )

    assert rc == 1
    assert len(server.requests) == 1, format_requests(server)
    assert (
            b"The CRC32 you specified did not "
            b"match the calculated checksum." in stderr
    )
    # Source file should NOT be deleted on failed upload
    assert src.exists()


@pytest.mark.asyncio
async def test_mv_download_content_length_mismatch_fails(aws_cli, tmp_path):
    """mv download fails when body is shorter than Content-Length header."""
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(
            server,
            [
                head_object_response(content_length=100),
                HTTPResponse.raw(
                    b"foo",
                    status=200,
                    headers={
                        "Content-Length": "100",
                        "ETag": '"foo-1"',
                    },
                ),
            ],
        )

        async def inject_fault():
            await server.next_request()  # HeadObject completes
            server.set_transmission_strategy(
                FaultyTransmission([DropConnection(after_bytes=3)])
            )

        (stdout, stderr, rc), _ = await asyncio.gather(
            run_cli(
                aws_cli,
                ["s3", "mv", "s3://bucket/key.txt", str(tmp_path)],
                cli_env(proxy),
            ),
            inject_fault(),
        )

    assert rc == 1
    assert len(server.requests) == 2, format_requests(server)
    assert b"move failed" in stderr


@pytest.mark.asyncio
async def test_mv_multipart_upload_part_rejected_by_server(aws_cli, tmp_path):
    """mv multipart upload fails when server rejects a part with BadDigest."""
    src = tmp_path / "foo.txt"
    src.write_bytes(b"a" * 10 * (1024**2))
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(
            server,
            [
                create_mpu_response("foo"),
                upload_part_response("etag1"),
                error_response(
                    "BadDigest",
                    "The CRC32 you specified did not match the calculated checksum.",
                    status=400,
                ),
                abort_mpu_response(),
            ],
        )
        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "mv", str(src), "s3://bucket/key.txt"],
            cli_env(proxy),
        )

    assert rc == 1
    assert len(server.requests) == 4, format_requests(server)
    assert (
        b"An error occurred (BadDigest) when "
        b"calling the UploadPart operation" in stderr
    )
    # Source file should NOT be deleted on failed upload
    assert src.exists()


def get_access_point_response(bucket: str) -> HTTPResponse:
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<GetAccessPointResult>"
        f"<Bucket>{bucket}</Bucket>"
        "</GetAccessPointResult>"
    )
    return HTTPResponse.raw(
        body.encode(), status=200, headers={"Content-Type": "application/xml"}
    )


def get_caller_identity_response(
    account: str = "123456789012",
) -> HTTPResponse:
    body = (
        '<GetCallerIdentityResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">'
        "<GetCallerIdentityResult>"
        f"<Account>{account}</Account>"
        "<Arn>arn:aws:iam::123456789012:user/test</Arn>"
        "<UserId>AIDATEST</UserId>"
        "</GetCallerIdentityResult>"
        "</GetCallerIdentityResponse>"
    )
    return HTTPResponse.raw(
        body.encode(), status=200, headers={"Content-Type": "text/xml"}
    )


def list_multi_region_access_points_response(
    alias: str, buckets: list[str]
) -> HTTPResponse:
    regions = "".join(
        f"<Region><Bucket>{b}</Bucket></Region>" for b in buckets
    )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<ListMultiRegionAccessPointsResult>"
        "<AccessPoints>"
        f"<AccessPoint><Alias>{alias}</Alias><Regions>{regions}</Regions></AccessPoint>"
        "</AccessPoints>"
        "</ListMultiRegionAccessPointsResult>"
    )
    return HTTPResponse.raw(
        body.encode(), status=200, headers={"Content-Type": "application/xml"}
    )


@pytest.mark.asyncio
class TestMvCommandWithValidateSameS3Paths:
    async def test_cant_mv_object_onto_itself_access_point_arn(
        self, aws_cli, tmp_path
    ):
        """mv with access point ARN resolving to same bucket fails."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [get_access_point_response("bucket")])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint/key",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 252
        assert b"Cannot mv a file onto itself" in stderr

    async def test_cant_mv_object_onto_itself_access_point_arn_as_source(
        self, aws_cli, tmp_path
    ):
        """mv with access point ARN as source resolving to same bucket fails."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [get_access_point_response("bucket")])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint/key",
                    "s3://bucket/key",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 252
        assert b"Cannot mv a file onto itself" in stderr

    async def test_cant_mv_object_onto_itself_access_point_arn_with_env_var(
        self, aws_cli, tmp_path
    ):
        """mv with access point ARN uses env var to enable validation."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [get_access_point_response("bucket")])
            env = cli_env(proxy)
            env["AWS_CLI_S3_MV_VALIDATE_SAME_S3_PATHS"] = "true"
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint/key",
                ],
                env,
            )

        assert rc == 252
        assert b"Cannot mv a file onto itself" in stderr

    async def test_cant_mv_object_onto_itself_access_point_arn_base_key(
        self, aws_cli, tmp_path
    ):
        """mv with access point ARN and implied key resolving to same bucket fails."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [get_access_point_response("bucket")])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint/",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 252
        assert b"Cannot mv a file onto itself" in stderr

    async def test_cant_mv_object_onto_itself_access_point_arn_base_prefix(
        self, aws_cli, tmp_path
    ):
        """mv with access point ARN and matching prefix resolving to same bucket fails."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [get_access_point_response("bucket")])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/prefix/key",
                    "s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint/prefix/",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 252
        assert b"Cannot mv a file onto itself" in stderr

    async def test_cant_mv_object_onto_itself_access_point_alias(
        self, aws_cli, tmp_path
    ):
        """mv with access point alias resolving to same bucket fails."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    get_caller_identity_response("123456789012"),
                    get_access_point_response("bucket"),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://myaccesspoint-foobar-s3alias/key",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 252
        assert b"Cannot mv a file onto itself" in stderr

    async def test_cant_mv_object_onto_itself_outpost_access_point_arn(
        self, aws_cli, tmp_path
    ):
        """mv with outpost access point ARN resolving to same bucket fails."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [get_access_point_response("bucket")])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://arn:aws:s3-outposts:us-east-1:123456789012:outpost/op-foobar/accesspoint/myaccesspoint/key",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 252
        assert b"Cannot mv a file onto itself" in stderr

    async def test_outpost_access_point_alias_raises_error(
        self, aws_cli, tmp_path
    ):
        """mv with outpost access point alias raises unresolvable error."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://myaccesspoint-foobar--op-s3/key",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 252
        assert b"Can't resolve underlying bucket name" in stderr

    async def test_cant_mv_object_onto_itself_mrap_arn(
        self, aws_cli, tmp_path
    ):
        """mv with MRAP ARN resolving to same bucket fails."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    list_multi_region_access_points_response(
                        "foobar.mrap", ["differentbucket", "bucket"]
                    ),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://arn:aws:s3::123456789012:accesspoint/foobar.mrap/key",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 252
        assert b"Cannot mv a file onto itself" in stderr

    async def test_get_mrap_buckets_raises_if_alias_not_found(
        self, aws_cli, tmp_path
    ):
        """mv with MRAP ARN where alias not found raises error."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    list_multi_region_access_points_response(
                        "baz.mrap", ["differentbucket", "bucket"]
                    ),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://arn:aws:s3::123456789012:accesspoint/foobar.mrap/key",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 252
        assert (
            b"Couldn't find multi-region access point with alias foobar.mrap"
            in stderr
        )

    async def test_mv_works_if_access_point_arn_resolves_to_different_bucket(
        self, aws_cli, tmp_path
    ):
        """mv with access point ARN resolving to different bucket succeeds."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    get_access_point_response("differentbucket"),
                    head_object_response(),
                    copy_object_response(),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint/key",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 4, format_requests(server)
        assert_get_access_point(server.requests[0])
        assert_head_object(
            server.requests[1], Bucket="bucket", Key="key"
        )
        assert_copy_object(
            server.requests[2],
            Bucket="arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint",
            Key="key",
        )
        assert_delete_object(
            server.requests[3], Bucket="bucket", Key="key"
        )

    async def test_mv_works_if_access_point_alias_resolves_to_different_bucket(
        self, aws_cli, tmp_path
    ):
        """mv with access point alias resolving to different bucket succeeds."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    get_caller_identity_response("123456789012"),
                    get_access_point_response("differentbucket"),
                    head_object_response(),
                    copy_object_response(),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://myaccesspoint-foobar-s3alias/key",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 5, format_requests(server)
        assert_get_caller_identity(server.requests[0])
        assert_get_access_point(server.requests[1])
        assert_head_object(
            server.requests[2], Bucket="bucket", Key="key"
        )
        assert_copy_object(
            server.requests[3],
            Bucket="myaccesspoint-foobar-s3alias",
            Key="key",
        )
        assert_delete_object(
            server.requests[4], Bucket="bucket", Key="key"
        )

    async def test_mv_works_if_outpost_access_point_arn_resolves_to_different_bucket(
        self, aws_cli, tmp_path
    ):
        """mv with outpost access point ARN resolving to different bucket succeeds."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    get_access_point_response("differentbucket"),
                    head_object_response(),
                    copy_object_response(),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://arn:aws:s3-outposts:us-east-1:123456789012:outpost/op-foobar/accesspoint/myaccesspoint/key",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 4, format_requests(server)
        assert_get_access_point(server.requests[0])
        assert_head_object(
            server.requests[1], Bucket="bucket", Key="key"
        )
        assert_copy_object(
            server.requests[2],
            Bucket="arn:aws:s3-outposts:us-east-1:123456789012:outpost/op-foobar/accesspoint/myaccesspoint",
            Key="key",
        )
        assert_delete_object(
            server.requests[3], Bucket="bucket", Key="key"
        )

    async def test_skips_validation_if_keys_are_different_accesspoint_arn(
        self, aws_cli, tmp_path
    ):
        """mv with access point ARN and different key skips validation."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint/key2",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)

    async def test_skips_validation_if_prefixes_are_different_accesspoint_arn(
        self, aws_cli, tmp_path
    ):
        """mv with access point ARN and different prefix skips validation."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint/prefix/",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)

    async def test_skips_validation_if_keys_are_different_accesspoint_alias(
        self, aws_cli, tmp_path
    ):
        """mv with access point alias and different key skips validation."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://myaccesspoint-foobar-s3alias/key2",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)

    async def test_skips_validation_if_keys_are_different_outpost_arn(
        self, aws_cli, tmp_path
    ):
        """mv with outpost ARN and different key skips validation."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://arn:aws:s3-outposts:us-east-1:123456789012:outpost/op-foobar/accesspoint/myaccesspoint/key2",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)

    async def test_skips_validation_if_keys_are_different_outpost_alias(
        self, aws_cli, tmp_path
    ):
        """mv with outpost alias and different key skips validation."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://myaccesspoint-foobar--op-s3/key2",
                    "--validate-same-s3-paths",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)

    async def test_raises_warning_if_validation_not_set(
        self, aws_cli, tmp_path
    ):
        """mv with access point ARN without --validate-same-s3-paths raises warning."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://bucket/key",
                    "s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint/key",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert b"warning: Provided s3 paths may resolve" in stderr

    async def test_raises_warning_if_validation_not_set_source(
        self, aws_cli, tmp_path
    ):
        """mv with access point ARN as source without --validate-same-s3-paths raises warning."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "s3://arn:aws:s3:us-west-2:123456789012:accesspoint/myaccesspoint/key",
                    "s3://bucket/key",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert b"warning: Provided s3 paths may resolve" in stderr


def _is_case_insensitive() -> bool:
    """Check if the filesystem is case-insensitive."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        upper = os.path.join(d, "A")
        open(upper, "w").close()
        return os.path.exists(os.path.join(d, "a"))


@pytest.mark.asyncio
class TestMvRecursiveCaseConflict:
    @pytest.mark.skipif(
        not _is_case_insensitive(),
        reason="Requires case-insensitive filesystem",
    )
    async def test_warn_with_existing_file(self, aws_cli, tmp_path):
        """mv --recursive s3->local --case-conflict warn warns on case conflict with existing file."""
        (tmp_path / "a.txt").write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    xml_response(
                        list_objects_xml(
                            contents=[
                                {
                                    "Key": "A.txt",
                                    "Size": 3,
                                    "LastModified": "2023-01-01T00:00:00Z",
                                }
                            ],
                        )
                    ),
                    get_object_response(b"foo"),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "--recursive",
                    "s3://bucket",
                    str(tmp_path),
                    "--case-conflict",
                    "warn",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert "warning: Downloading bucket/A.txt" in stderr.decode()

    async def test_skip_with_case_conflicts_in_s3(self, aws_cli, tmp_path):
        """mv --recursive s3->local --case-conflict skip skips conflicting keys."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    xml_response(
                        list_objects_xml(
                            contents=[
                                {
                                    "Key": "A.txt",
                                    "Size": 3,
                                    "LastModified": "2023-01-01T00:00:00Z",
                                },
                                {
                                    "Key": "a.txt",
                                    "Size": 3,
                                    "LastModified": "2023-01-01T00:00:00Z",
                                },
                            ],
                        )
                    ),
                    get_object_response(b"foo"),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "--recursive",
                    "s3://bucket",
                    str(tmp_path),
                    "--case-conflict",
                    "skip",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert "warning: Skipping bucket/a.txt" in stderr.decode()

    @pytest.mark.skipif(
        not _is_case_insensitive(),
        reason="Requires case-insensitive filesystem",
    )
    async def test_ignore_with_existing_file(self, aws_cli, tmp_path):
        """mv --recursive s3->local --case-conflict ignore proceeds without warning."""
        (tmp_path / "a.txt").write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    xml_response(
                        list_objects_xml(
                            contents=[
                                {
                                    "Key": "A.txt",
                                    "Size": 3,
                                    "LastModified": "2023-01-01T00:00:00Z",
                                }
                            ],
                        )
                    ),
                    get_object_response(b"foo"),
                    delete_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "--recursive",
                    "s3://bucket",
                    str(tmp_path),
                    "--case-conflict",
                    "ignore",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()


@pytest.mark.asyncio
class TestS3ExpressMvRecursive:
    async def test_s3_express_error_raises_exception(self, aws_cli, tmp_path):
        """mv --recursive with S3 Express bucket rejects --case-conflict error."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "--recursive",
                    "s3://bucket--usw2-az1--x-s3",
                    str(tmp_path),
                    "--case-conflict",
                    "error",
                ],
                cli_env(proxy),
            )

        assert rc == 252
        assert b"`error` is not a valid value" in stderr

    async def test_s3_express_skip_raises_exception(self, aws_cli, tmp_path):
        """mv --recursive with S3 Express bucket rejects --case-conflict skip."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "mv",
                    "--recursive",
                    "s3://bucket--usw2-az1--x-s3",
                    str(tmp_path),
                    "--case-conflict",
                    "skip",
                ],
                cli_env(proxy),
            )

        assert rc == 252
        assert b"`skip` is not a valid value" in stderr
