"""Blackbox tests for `aws s3 cp` command."""

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
    assert_get_object,
    assert_get_object_annotation,
    assert_get_object_tagging,
    assert_head_object,
    assert_list_object_annotations,
    assert_list_objects_v2,
    assert_put_object,
    assert_put_object_annotation,
    assert_put_object_tagging,
    assert_upload_part_copy,
)
from tests.blackbox.utils import (
    abort_mpu_response,
    cli_env,
    complete_mpu_response,
    copy_object_response,
    create_mpu_response,
    create_session_response,
    empty_list_objects_response,
    error_response,
    format_requests,
    get_object_response,
    get_object_tagging_response,
    head_object_response,
    list_objects_xml,
    mock_server,
    put_object_response,
    put_object_tagging_response,
    run_cli,
    setup_responses,
    upload_part_copy_response,
    upload_part_response,
    xml_response,
)


def relative_path(filename):
    """Cross platform relative path of a filename."""
    try:
        dirname, basename = os.path.split(filename)
        relative_dir = os.path.relpath(dirname)
        return os.path.join(relative_dir, basename)
    except ValueError:
        return os.path.abspath(filename)


def list_object_annotations_response(names: list[str]) -> HTTPResponse:
    entries = ""
    for name in names:
        entries += f"<AnnotationEntry><AnnotationName>{name}</AnnotationName></AnnotationEntry>"
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<ListObjectAnnotationsOutput>"
        f"<Annotations>{entries}</Annotations>"
        "</ListObjectAnnotationsOutput>"
    )
    return HTTPResponse.raw(
        body.encode(), status=200, headers={"Content-Type": "application/xml"}
    )


def get_object_annotation_response(payload: bytes) -> HTTPResponse:
    return HTTPResponse.raw(
        payload,
        status=200,
        headers={"Content-Type": "application/octet-stream"},
    )


def put_object_annotation_response() -> HTTPResponse:
    return HTTPResponse.raw(b"", status=200)


@pytest.mark.asyncio
class TestCPCommand:
    async def test_operations_used_in_upload(self, aws_cli, tmp_path):
        """cp local_file s3://bucket/key.txt makes exactly one PUT request."""
        src = tmp_path / "foo.txt"
        src.write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", str(src), "s3://bucket/key.txt"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(req, Bucket="bucket", Key="key.txt")

    async def test_key_name_added_when_only_bucket_provided(
        self, aws_cli, tmp_path
    ):
        """cp foo.txt s3://bucket/ should use foo.txt as the key."""
        src = tmp_path / "foo.txt"
        src.write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli, ["s3", "cp", str(src), "s3://bucket/"], cli_env(proxy)
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(req, Bucket="bucket", Key="foo.txt")

    async def test_trailing_slash_appended(self, aws_cli, tmp_path):
        """cp foo.txt s3://bucket (no trailing slash) should still use foo.txt as key."""
        src = tmp_path / "foo.txt"
        src.write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli, ["s3", "cp", str(src), "s3://bucket"], cli_env(proxy)
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(req, Bucket="bucket", Key="foo.txt")

    async def test_dryrun_upload(self, aws_cli, tmp_path):
        """cp --dryrun should not make any requests."""
        src = tmp_path / "foo.txt"
        src.write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", str(src), "s3://bucket/key.txt", "--dryrun"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 0, format_requests(server)
        output = stdout.decode()
        assert (
            f"(dryrun) upload: {relative_path(str(src))} to s3://bucket/key.txt"
            in output
        )

    async def test_error_on_same_line_as_status(self, aws_cli, tmp_path):
        """Upload failure should show error in stderr."""
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
                        "BucketNotExists", "Bucket does not exist", status=400
                    )
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", str(src), "s3://bucket-not-exist/key.txt"],
                cli_env(proxy),
            )

        assert rc == 1
        err = stderr.decode()
        assert (
            f"upload failed: {relative_path(str(src))} to s3://bucket-not-exist/key.txt An error"
            in err
        )

    async def test_upload_grants(self, aws_cli, tmp_path):
        """cp --grants should send grant headers."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--grants",
                    "read=id=foo",
                    "full=id=bar",
                    "readacl=id=biz",
                    "writeacl=id=baz",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(
            req,
            Bucket="bucket",
            Key="key.txt",
            GrantRead="id=foo",
            GrantFullControl="id=bar",
            GrantReadACP="id=biz",
            GrantWriteACP="id=baz",
            ContentType="text/plain",
            ChecksumAlgorithm="CRC64NVME",
        )

    async def test_upload_expires(self, aws_cli, tmp_path):
        """cp --expires should send expires header."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--expires",
                    "90",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(
            req,
            Bucket="bucket",
            Key="key.txt",
            Expires="Thu, 01 Jan 1970 00:01:30 GMT",
        )

    async def test_upload_standard_ia(self, aws_cli, tmp_path):
        """cp --storage-class STANDARD_IA should send storage class header."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--storage-class",
                    "STANDARD_IA",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(
            req,
            Bucket="bucket",
            Key="key.txt",
            StorageClass="STANDARD_IA",
        )

    async def test_upload_onezone_ia(self, aws_cli, tmp_path):
        """cp --storage-class ONEZONE_IA should send storage class header."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--storage-class",
                    "ONEZONE_IA",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(
            req,
            Bucket="bucket",
            Key="key.txt",
            StorageClass="ONEZONE_IA",
        )

    async def test_upload_intelligent_tiering(self, aws_cli, tmp_path):
        """cp --storage-class INTELLIGENT_TIERING should send storage class header."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--storage-class",
                    "INTELLIGENT_TIERING",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(
            req,
            Bucket="bucket",
            Key="key.txt",
            StorageClass="INTELLIGENT_TIERING",
        )

    async def test_upload_glacier(self, aws_cli, tmp_path):
        """cp --storage-class GLACIER should send storage class header."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--storage-class",
                    "GLACIER",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(
            req,
            Bucket="bucket",
            Key="key.txt",
            StorageClass="GLACIER",
        )

    async def test_upload_deep_archive(self, aws_cli, tmp_path):
        """cp --storage-class DEEP_ARCHIVE should send storage class header."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--storage-class",
                    "DEEP_ARCHIVE",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(
            req,
            Bucket="bucket",
            Key="key.txt",
            StorageClass="DEEP_ARCHIVE",
        )

    async def test_operations_used_in_download_file(self, aws_cli, tmp_path):
        """cp s3://bucket/key.txt localdir uses HeadObject then GetObject."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    get_object_response(b"foo"),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", "s3://bucket/key.txt", str(tmp_path)],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_head_object(server.requests[0], Bucket="bucket", Key="key.txt")
        assert_get_object(server.requests[1], Bucket="bucket", Key="key.txt")

    async def test_operations_used_in_recursive_download(
        self, aws_cli, tmp_path
    ):
        """cp s3://bucket/key.txt localdir --recursive with no objects only calls ListObjectsV2."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [empty_list_objects_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket/key.txt",
                    str(tmp_path),
                    "--recursive",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_list_objects_v2(server.requests[0], Bucket="bucket")

    async def test_no_overwrite_flag_when_object_not_exists_on_target(
        self, aws_cli, tmp_path
    ):
        """cp --no-overwrite sends IfNoneMatch=* on PutObject."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(req, Bucket="bucket", Key="key.txt", IfNoneMatch="*")

    async def test_no_overwrite_flag_when_object_exists_on_target(
        self, aws_cli, tmp_path
    ):
        """cp --no-overwrite with 412 PreconditionFailed succeeds (file skipped)."""
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
                    )
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(req, Bucket="bucket", Key="key.txt", IfNoneMatch="*")

    async def test_no_overwrite_flag_multipart_upload_when_object_not_exists_on_target(
        self, aws_cli, tmp_path
    ):
        """cp --no-overwrite with large file sends IfNoneMatch=* on CompleteMultipartUpload."""
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
                    upload_part_response("foo-1"),
                    upload_part_response("foo-2"),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 4, format_requests(server)
        # CreateMultipartUpload
        assert_create_multipart_upload(
            server.requests[0],
            Bucket="bucket",
            Key="key.txt",
        )
        # CompleteMultipartUpload — should have if-none-match
        assert_complete_multipart_upload(
            server.requests[3],
            Bucket="bucket",
            Key="key.txt",
            UploadId="foo",
            IfNoneMatch="*",
        )

    async def test_no_overwrite_flag_multipart_upload_when_object_exists_on_target(
        self, aws_cli, tmp_path
    ):
        """cp --no-overwrite large file with 412 on Complete succeeds (file skipped) and aborts."""
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
                    upload_part_response("foo-1"),
                    upload_part_response("foo-2"),
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 5, format_requests(server)
        # Verify CompleteMultipartUpload had if-none-match
        assert_complete_multipart_upload(
            server.requests[3],
            Bucket="bucket",
            Key="key.txt",
            UploadId="foo",
            IfNoneMatch="*",
        )
        # Verify AbortMultipartUpload was called
        assert_abort_multipart_upload(
            server.requests[4],
            Bucket="bucket",
            Key="key.txt",
            UploadId="foo",
        )

    async def test_no_overwrite_flag_on_copy_when_small_object_does_not_exist_on_target(
        self, aws_cli, tmp_path
    ):
        """cp s3://src s3://dst --no-overwrite sends IfNoneMatch=* on CopyObject."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=5),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket1/key.txt",
                    "s3://bucket/key.txt",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_head_object(server.requests[0], Bucket="bucket1", Key="key.txt")
        assert_copy_object(
            server.requests[1],
            Bucket="bucket",
            Key="key.txt",
            CopySource="bucket1/key.txt",
            IfNoneMatch="*",
        )

    async def test_no_overwrite_flag_on_copy_when_small_object_exists_on_target(
        self, aws_cli, tmp_path
    ):
        """cp s3://src s3://dst --no-overwrite with 412 succeeds (file skipped)."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=5),
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
                    "cp",
                    "s3://bucket1/key.txt",
                    "s3://bucket/key.txt",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_head_object(server.requests[0], Bucket="bucket1", Key="key.txt")
        assert_copy_object(
            server.requests[1],
            Bucket="bucket",
            Key="key.txt",
            CopySource="bucket1/key.txt",
            IfNoneMatch="*",
        )

    async def test_dryrun_download(self, aws_cli, tmp_path):
        """cp s3://bucket/key.txt local --dryrun only calls HeadObject."""
        target = tmp_path / "file.txt"
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [head_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", "s3://bucket/key.txt", str(target), "--dryrun"],
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
        output = stdout.decode()
        assert (
            f"(dryrun) download: s3://bucket/key.txt to {relative_path(str(target))}"
            in output
        )

    async def test_website_redirect_ignore_paramfile(self, aws_cli, tmp_path):
        """cp --website-redirect sends the URL as header, not as paramfile."""
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
                    "cp",
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

    async def test_dryrun_copy(self, aws_cli, tmp_path):
        """cp s3://bucket/key.txt s3://bucket/key2.txt --dryrun only calls HeadObject."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [head_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
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
        output = stdout.decode()
        assert (
            "(dryrun) copy: s3://bucket/key.txt to s3://bucket/key2.txt"
            in output
        )

    async def test_metadata_copy(self, aws_cli, tmp_path):
        """cp s3://src s3://dst --metadata sends metadata on CopyObject."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket/key.txt",
                    "s3://bucket/key2.txt",
                    "--metadata",
                    "KeyName=Value",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_head_object(server.requests[0], Bucket="bucket", Key="key.txt")
        assert_copy_object(
            server.requests[1],
            Bucket="bucket",
            Key="key2.txt",
            CopySource="bucket/key.txt",
            Metadata={"keyname": "Value"},
        )

    async def test_metadata_copy_with_put_object(self, aws_cli, tmp_path):
        """cp local s3://dst --metadata sends metadata on PutObject."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key2.txt",
                    "--metadata",
                    "KeyName=Value",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(
            req,
            Bucket="bucket",
            Key="key2.txt",
            Metadata={"keyname": "Value"},
        )

    async def test_metadata_copy_with_multipart_upload(
        self, aws_cli, tmp_path
    ):
        """cp large_file s3://dst --metadata sends metadata on CreateMultipartUpload."""
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
                    upload_part_response("foo-1"),
                    upload_part_response("foo-2"),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    str(src),
                    "s3://bucket/key2.txt",
                    "--metadata",
                    "KeyName=Value",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) >= 3, format_requests(server)
        # CreateMultipartUpload should have the metadata header
        assert_create_multipart_upload(
            server.requests[0],
            Bucket="bucket",
            Key="key2.txt",
            Metadata={"keyname": "Value"},
        )

    async def test_metadata_directive_copy(self, aws_cli, tmp_path):
        """cp s3://src s3://dst --metadata-directive REPLACE sends directive on CopyObject."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket/key.txt",
                    "s3://bucket/key2.txt",
                    "--metadata-directive",
                    "REPLACE",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_head_object(server.requests[0], Bucket="bucket", Key="key.txt")
        assert_copy_object(
            server.requests[1],
            Bucket="bucket",
            Key="key2.txt",
            CopySource="bucket/key.txt",
            MetadataDirective="REPLACE",
        )

    async def test_no_metadata_directive_for_non_copy(self, aws_cli, tmp_path):
        """cp local s3://dst --metadata-directive REPLACE does not send directive on PutObject."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--metadata-directive",
                    "REPLACE",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(req, Bucket="bucket", Key="key.txt")
        assert req.headers.get("x-amz-metadata-directive") is None

    async def test_recursive_glacier_download_with_force_glacier(
        self, aws_cli, tmp_path
    ):
        """cp --recursive --force-glacier-transfer downloads GLACIER objects."""
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
                                    "Key": "foo/bar.txt",
                                    "Size": 100,
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                    "StorageClass": "GLACIER",
                                    "ETag": '"foo-1"',
                                }
                            ],
                            prefix="foo",
                        )
                    ),
                    get_object_response(b"foo"),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket/foo",
                    str(tmp_path),
                    "--recursive",
                    "--force-glacier-transfer",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_list_objects_v2(server.requests[0], Bucket="bucket")
        assert_get_object(
            server.requests[1], Bucket="bucket", Key="foo/bar.txt"
        )

    async def test_recursive_glacier_download_without_force_glacier(
        self, aws_cli, tmp_path
    ):
        """cp --recursive skips GLACIER objects and warns."""
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
                                    "Key": "foo/bar.txt",
                                    "Size": 100,
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                    "StorageClass": "GLACIER",
                                    "ETag": '"foo-1"',
                                }
                            ],
                            prefix="foo",
                        )
                    ),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", "s3://bucket/foo", str(tmp_path), "--recursive"],
                cli_env(proxy),
            )

        assert rc == 2
        assert len(server.requests) == 1, format_requests(server)
        assert_list_objects_v2(server.requests[0], Bucket="bucket")
        assert "GLACIER" in stderr.decode()

    async def test_warns_on_glacier_incompatible_operation(
        self, aws_cli, tmp_path
    ):
        """cp s3://bucket/key.txt . skips GLACIER objects and warns."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    HTTPResponse.raw(
                        b"",
                        status=200,
                        headers={
                            "Content-Length": "100",
                            "Last-Modified": "Thu, 01 Jan 1970 00:00:00 GMT",
                            "ETag": '"foo-1"',
                            "x-amz-storage-class": "GLACIER",
                        },
                    ),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", "s3://bucket/key.txt", str(tmp_path)],
                cli_env(proxy),
            )

        assert rc == 2
        assert len(server.requests) == 1, format_requests(server)
        assert_head_object(server.requests[0], Bucket="bucket", Key="key.txt")
        assert "GLACIER" in stderr.decode()

    async def test_warns_on_deep_archive_incompatible_operation(
        self, aws_cli, tmp_path
    ):
        """cp s3://bucket/key.txt . skips DEEP_ARCHIVE objects and warns."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    HTTPResponse.raw(
                        b"",
                        status=200,
                        headers={
                            "Content-Length": "100",
                            "Last-Modified": "Thu, 01 Jan 1970 00:00:00 GMT",
                            "ETag": '"foo-1"',
                            "x-amz-storage-class": "DEEP_ARCHIVE",
                        },
                    ),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", "s3://bucket/key.txt", str(tmp_path)],
                cli_env(proxy),
            )

        assert rc == 2
        assert len(server.requests) == 1, format_requests(server)
        assert_head_object(server.requests[0], Bucket="bucket", Key="key.txt")
        assert "GLACIER" in stderr.decode()

    async def test_turn_off_glacier_warnings(self, aws_cli, tmp_path):
        """cp --ignore-glacier-warnings skips GLACIER silently with rc=0."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    HTTPResponse.raw(
                        b"",
                        status=200,
                        headers={
                            "Content-Length": str(20 * (1024**2)),
                            "Last-Modified": "Thu, 01 Jan 1970 00:00:00 GMT",
                            "ETag": '"foo-1"',
                            "x-amz-storage-class": "GLACIER",
                        },
                    ),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket/key.txt",
                    str(tmp_path),
                    "--ignore-glacier-warnings",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_head_object(server.requests[0], Bucket="bucket", Key="key.txt")
        assert stderr.decode() == ""

    async def test_turn_off_glacier_warnings_for_deep_archive(
        self, aws_cli, tmp_path
    ):
        """cp --ignore-glacier-warnings skips DEEP_ARCHIVE silently with rc=0."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    HTTPResponse.raw(
                        b"",
                        status=200,
                        headers={
                            "Content-Length": str(20 * (1024**2)),
                            "Last-Modified": "Thu, 01 Jan 1970 00:00:00 GMT",
                            "ETag": '"foo-1"',
                            "x-amz-storage-class": "DEEP_ARCHIVE",
                        },
                    ),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket/key.txt",
                    str(tmp_path),
                    "--ignore-glacier-warnings",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_head_object(server.requests[0], Bucket="bucket", Key="key.txt")
        assert stderr.decode() == ""

    async def test_cp_with_sse_flag(self, aws_cli, tmp_path):
        """cp --sse sends ServerSideEncryption=AES256 header."""
        src = tmp_path / "foo.txt"
        src.write_text("contents")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", str(src), "s3://bucket/key.txt", "--sse"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(
            req,
            Bucket="bucket",
            Key="key.txt",
            ContentType="text/plain",
            ServerSideEncryption="AES256",
            ChecksumAlgorithm="CRC64NVME",
        )

    async def test_cp_with_sse_c_flag(self, aws_cli, tmp_path):
        """cp --sse-c --sse-c-key sends SSECustomerAlgorithm and SSECustomerKey headers."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--sse-c",
                    "--sse-c-key",
                    "foo",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(
            req,
            Bucket="bucket",
            Key="key.txt",
            ContentType="text/plain",
            SSECustomerAlgorithm="AES256",
            ChecksumAlgorithm="CRC64NVME",
        )
        assert (
            req.headers.get("x-amz-server-side-encryption-customer-key")
            is not None
        )

    async def test_cp_upload_with_sse_kms_and_key_id(self, aws_cli, tmp_path):
        """cp --sse aws:kms --sse-kms-key-id sends KMS headers."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--sse",
                    "aws:kms",
                    "--sse-kms-key-id",
                    "foo",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(
            req,
            Bucket="bucket",
            Key="key.txt",
            ContentType="text/plain",
            ServerSideEncryption="aws:kms",
            SSEKMSKeyId="foo",
            ChecksumAlgorithm="CRC64NVME",
        )

    async def test_cp_upload_large_file_with_sse_kms_and_key_id(
        self, aws_cli, tmp_path
    ):
        """cp large file --sse aws:kms --sse-kms-key-id sends KMS on CreateMultipartUpload."""
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
                    upload_part_response("foo-1"),
                    upload_part_response("foo-2"),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--sse",
                    "aws:kms",
                    "--sse-kms-key-id",
                    "foo",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 4, format_requests(server)
        create_req = server.requests[0]
        assert_create_multipart_upload(
            create_req,
            Bucket="bucket",
            Key="key.txt",
            ContentType="text/plain",
            ServerSideEncryption="aws:kms",
            SSEKMSKeyId="foo",
            ChecksumAlgorithm="CRC64NVME",
        )

    async def test_cannot_use_recursive_with_stream(self, aws_cli, tmp_path):
        """cp - s3://bucket/key.txt --recursive is rejected."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", "-", "s3://bucket/key.txt", "--recursive"],
                cli_env(proxy),
            )

        assert rc == 252
        assert (
            "Streaming currently is only compatible with non-recursive cp commands"
            in stderr.decode()
        )

    async def test_upload_with_checksum_algorithm_crc32(
        self, aws_cli, tmp_path
    ):
        """cp --checksum-algorithm CRC32 sends the algorithm header."""
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
                    "cp",
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

    async def test_upload_with_checksum_algorithm_sha256(
        self, aws_cli, tmp_path
    ):
        """cp --checksum-algorithm SHA256 sends the algorithm header."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--checksum-algorithm",
                    "SHA256",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(
            server.requests[0],
            Bucket="bucket",
            Key="key.txt",
            ChecksumAlgorithm="SHA256",
        )

    async def test_upload_with_checksum_algorithm_crc32c(
        self, aws_cli, tmp_path
    ):
        """cp --checksum-algorithm CRC32C sends the algorithm header."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--checksum-algorithm",
                    "CRC32C",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(
            server.requests[0],
            Bucket="bucket",
            Key="key.txt",
            ChecksumAlgorithm="CRC32C",
        )

    async def test_upload_with_checksum_algorithm_crc64nvme(
        self, aws_cli, tmp_path
    ):
        """cp --checksum-algorithm CRC64NVME sends the algorithm header."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--checksum-algorithm",
                    "CRC64NVME",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(
            server.requests[0],
            Bucket="bucket",
            Key="key.txt",
            ChecksumAlgorithm="CRC64NVME",
        )

    async def test_multipart_upload_with_checksum_algorithm_crc32(
        self, aws_cli, tmp_path
    ):
        """cp large file --checksum-algorithm CRC32 sends algorithm on CreateMultipartUpload."""
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
                    upload_part_response("foo-1"),
                    upload_part_response("foo-2"),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    str(src),
                    "s3://bucket/key2.txt",
                    "--checksum-algorithm",
                    "CRC32",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 4, format_requests(server)
        assert_create_multipart_upload(
            server.requests[0],
            Bucket="bucket",
            Key="key2.txt",
            ChecksumAlgorithm="CRC32",
        )

    async def test_cp_with_sse_c_fileb(self, aws_cli, tmp_path):
        """cp --sse-c --sse-c-key fileb:// reads binary key from file."""
        src = tmp_path / "foo.txt"
        src.write_text("contents")
        key_path = tmp_path / "foo.key"
        key_contents = (
            b'K\xc9G\xe1\xf9&\xee\xd1\x03\xf3\xd4\x10\x18o9E\xc2\xaeD'
            b'\x89(\x18\xea\xda\xf6\x81\xc3\xd2\x9d\\\xa8\xe6'
        )
        key_path.write_bytes(key_contents)
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--sse-c",
                    "--sse-c-key",
                    f"fileb://{key_path}",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(
            req,
            Bucket="bucket",
            Key="key.txt",
            ContentType="text/plain",
            SSECustomerAlgorithm="AES256",
            ChecksumAlgorithm="CRC64NVME",
        )
        assert (
            req.headers.get("x-amz-server-side-encryption-customer-key")
            is not None
        )

    async def test_cp_with_sse_c_copy_source_fileb(self, aws_cli, tmp_path):
        """cp s3->s3 --sse-c-copy-source --sse-c-copy-source-key fileb:// sends source SSE-C."""
        key_path = tmp_path / "foo.key"
        key_contents = (
            b'K\xc9G\xe1\xf9&\xee\xd1\x03\xf3\xd4\x10\x18o9E\xc2\xaeD'
            b'\x89(\x18\xea\xda\xf6\x81\xc3\xd2\x9d\\\xa8\xe6'
        )
        key_path.write_bytes(key_contents)
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=4),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket-one/key.txt",
                    "s3://bucket/key.txt",
                    "--sse-c-copy-source",
                    "--sse-c-copy-source-key",
                    f"fileb://{key_path}",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        # HeadObject should have SSE-C source params
        assert_head_object(
            server.requests[0],
            Bucket="bucket-one",
            Key="key.txt",
            ChecksumMode="ENABLED",
            SSECustomerAlgorithm="AES256",
        )
        # CopyObject should have copy-source SSE-C params
        assert_copy_object(
            server.requests[1],
            Bucket="bucket",
            Key="key.txt",
            CopySource="bucket-one/key.txt",
            CopySourceSSECustomerAlgorithm="AES256",
        )

    async def test_s3s3_cp_with_destination_sse_c(self, aws_cli, tmp_path):
        """S3->S3 copy with encrypted destination sends SSE-C on CopyObject."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket-one/key.txt",
                    "s3://bucket/key.txt",
                    "--sse-c",
                    "--sse-c-key",
                    "destination-key",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        # HeadObject should NOT have SSE-C params (source is unencrypted)
        assert_head_object(
            server.requests[0],
            Bucket="bucket-one",
            Key="key.txt",
            ChecksumMode="ENABLED",
        )
        assert (
            server.requests[0].headers.get(
                "x-amz-server-side-encryption-customer-algorithm"
            )
            is None
        )
        # CopyObject should have destination SSE-C
        assert_copy_object(
            server.requests[1],
            Bucket="bucket",
            Key="key.txt",
            CopySource="bucket-one/key.txt",
            SSECustomerAlgorithm="AES256",
            AnnotationDirective="EXCLUDE",
        )
        assert (
            server.requests[1].headers.get(
                "x-amz-server-side-encryption-customer-key"
            )
            is not None
        )

    async def test_s3s3_cp_with_different_sse_c_keys(self, aws_cli, tmp_path):
        """S3->S3 copy with different SSE-C keys for source and destination."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket-one/key.txt",
                    "s3://bucket/key.txt",
                    "--sse-c-copy-source",
                    "--sse-c-copy-source-key",
                    "foo",
                    "--sse-c",
                    "--sse-c-key",
                    "bar",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        # HeadObject should have source SSE-C
        assert_head_object(
            server.requests[0],
            Bucket="bucket-one",
            Key="key.txt",
            ChecksumMode="ENABLED",
            SSECustomerAlgorithm="AES256",
        )
        assert (
            server.requests[0].headers.get(
                "x-amz-server-side-encryption-customer-key"
            )
            is not None
        )
        # CopyObject should have both source and destination SSE-C
        assert_copy_object(
            server.requests[1],
            Bucket="bucket",
            Key="key.txt",
            CopySource="bucket-one/key.txt",
            SSECustomerAlgorithm="AES256",
            CopySourceSSECustomerAlgorithm="AES256",
        )

    async def test_cp_copy_with_sse_kms_and_key_id(self, aws_cli, tmp_path):
        """S3->S3 copy with --sse aws:kms --sse-kms-key-id sends KMS on CopyObject."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=5),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket/key1.txt",
                    "s3://bucket/key2.txt",
                    "--sse",
                    "aws:kms",
                    "--sse-kms-key-id",
                    "foo",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_copy_object(
            server.requests[1],
            Bucket="bucket",
            Key="key2.txt",
            CopySource="bucket/key1.txt",
            ServerSideEncryption="aws:kms",
            SSEKMSKeyId="foo",
            AnnotationDirective="EXCLUDE",
        )

    async def test_upload_unicode_path(self, aws_cli, tmp_path):
        """cp s3://bucket/\u2603 s3://bucket/\u2713 handles unicode paths."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=10),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", "s3://bucket/\u2603", "s3://bucket/\u2713"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        output = stdout.decode()
        assert "copy: s3://bucket/\u2603 to s3://bucket/\u2713" in output
        assert "Completed 10 Bytes" in output

    async def test_upload_with_checksum_algorithm_sha1(
        self, aws_cli, tmp_path
    ):
        """cp --checksum-algorithm SHA1 sends the algorithm header."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--checksum-algorithm",
                    "SHA1",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(
            server.requests[0],
            Bucket="bucket",
            Key="key.txt",
            ChecksumAlgorithm="SHA1",
        )

    async def test_upload_with_checksum_algorithm_sha512(
        self, aws_cli, tmp_path
    ):
        """cp --checksum-algorithm SHA512 sends the algorithm header."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--checksum-algorithm",
                    "SHA512",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(
            server.requests[0],
            Bucket="bucket",
            Key="key.txt",
            ChecksumAlgorithm="SHA512",
        )

    async def test_upload_with_checksum_algorithm_xxhash3(
        self, aws_cli, tmp_path
    ):
        """cp --checksum-algorithm XXHASH3 sends the algorithm header."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--checksum-algorithm",
                    "XXHASH3",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(
            server.requests[0],
            Bucket="bucket",
            Key="key.txt",
            ChecksumAlgorithm="XXHASH3",
        )

    async def test_upload_with_checksum_algorithm_xxhash64(
        self, aws_cli, tmp_path
    ):
        """cp --checksum-algorithm XXHASH64 sends the algorithm header."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--checksum-algorithm",
                    "XXHASH64",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(
            server.requests[0],
            Bucket="bucket",
            Key="key.txt",
            ChecksumAlgorithm="XXHASH64",
        )

    async def test_upload_with_checksum_algorithm_xxhash128(
        self, aws_cli, tmp_path
    ):
        """cp --checksum-algorithm XXHASH128 sends the algorithm header."""
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
                    "cp",
                    str(src),
                    "s3://bucket/key.txt",
                    "--checksum-algorithm",
                    "XXHASH128",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(
            server.requests[0],
            Bucket="bucket",
            Key="key.txt",
            ChecksumAlgorithm="XXHASH128",
        )

    async def test_copy_with_checksum_algorithm_crc32(self, aws_cli, tmp_path):
        """cp s3->s3 --checksum-algorithm CRC32 sends algorithm on CopyObject."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket1/key.txt",
                    "s3://bucket2/key.txt",
                    "--checksum-algorithm",
                    "CRC32",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_copy_object(
            server.requests[1],
            Bucket="bucket2",
            Key="key.txt",
            CopySource="bucket1/key.txt",
            ChecksumAlgorithm="CRC32",
        )

    async def test_download_with_checksum_mode_crc32(self, aws_cli, tmp_path):
        """cp s3://bucket/foo local --checksum-mode ENABLED sends ChecksumMode on GetObject."""
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
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket/foo",
                    str(tmp_path),
                    "--checksum-mode",
                    "ENABLED",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        get_req = server.requests[1]
        assert_get_object(
            get_req,
            Bucket="bucket",
            Key="foo",
            ChecksumMode="ENABLED",
        )

    async def test_download_with_checksum_mode_crc32c(self, aws_cli, tmp_path):
        """cp s3://bucket/foo local --checksum-mode ENABLED works with CRC32C objects."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    get_object_response(
                        b"foo", **{"x-amz-checksum-crc32c": "z8SuHQ=="}
                    ),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket/foo",
                    str(tmp_path),
                    "--checksum-mode",
                    "ENABLED",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_get_object(
            server.requests[1],
            Bucket="bucket",
            Key="foo",
            ChecksumMode="ENABLED",
        )

    async def test_no_overwrite_flag_on_copy_when_large_object_does_not_exist_on_target(
        self, aws_cli, tmp_path
    ):
        """cp s3->s3 --no-overwrite large object multipart copy sends IfNoneMatch=* on Complete."""
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
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket1/key.txt",
                    "s3://bucket/key1.txt",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 6, format_requests(server)
        # CompleteMultipartUpload should have if-none-match
        assert_complete_multipart_upload(
            server.requests[5],
            Bucket="bucket",
            Key="key1.txt",
            UploadId="foo",
            MultipartUpload=[{"PartNumber": "1"}, {"PartNumber": "2"}],
            IfNoneMatch="*",
        )

    async def test_no_overwrite_flag_on_copy_when_large_object_exists_on_target(
        self, aws_cli, tmp_path
    ):
        """cp s3->s3 --no-overwrite large object with 412 on Complete aborts."""
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
                    "cp",
                    "s3://bucket1/key.txt",
                    "s3://bucket/key.txt",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 7, format_requests(server)
        # CompleteMultipartUpload should have if-none-match
        assert_complete_multipart_upload(
            server.requests[5],
            Bucket="bucket",
            Key="key.txt",
            UploadId="foo",
            MultipartUpload=[{"PartNumber": "1"}, {"PartNumber": "2"}],
            IfNoneMatch="*",
        )
        # AbortMultipartUpload should have been called
        assert_abort_multipart_upload(
            server.requests[6],
            Bucket="bucket",
            Key="key.txt",
            UploadId="foo",
        )

    async def test_no_overwrite_flag_on_download_when_single_object_already_exists_at_target(
        self, aws_cli, tmp_path
    ):
        """cp s3://bucket/foo.txt local --no-overwrite skips if file exists locally."""
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
                    "cp",
                    "s3://bucket/foo.txt",
                    str(target),
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_head_object(server.requests[0], Bucket="bucket", Key="foo.txt")
        # File should not have been overwritten
        assert target.read_text() == "existing content"

    async def test_no_overwrite_flag_on_download_when_single_object_does_not_exist_at_target(
        self, aws_cli, tmp_path
    ):
        """cp s3://bucket/foo.txt local --no-overwrite downloads if file doesn't exist."""
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
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket/foo.txt",
                    str(target),
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_head_object(server.requests[0], Bucket="bucket", Key="foo.txt")
        assert_get_object(server.requests[1], Bucket="bucket", Key="foo.txt")
        assert target.read_text() == "foo"

    async def test_warns_on_deep_arhive_incompatible_operation(
        self, aws_cli, tmp_path
    ):
        """cp s3://bucket/key.txt . skips DEEP_ARCHIVE and warns (original typo preserved)."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    HTTPResponse.raw(
                        b"",
                        status=200,
                        headers={
                            "Content-Length": "100",
                            "Last-Modified": "Thu, 01 Jan 1970 00:00:00 GMT",
                            "ETag": '"foo-1"',
                            "x-amz-storage-class": "DEEP_ARCHIVE",
                        },
                    ),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", "s3://bucket/key.txt", str(tmp_path)],
                cli_env(proxy),
            )

        assert rc == 2
        assert len(server.requests) == 1, format_requests(server)
        assert_head_object(server.requests[0], Bucket="bucket", Key="key.txt")
        assert "GLACIER" in stderr.decode()

    async def test_warns_on_glacier_incompatible_operation_for_multipart_file(
        self, aws_cli, tmp_path
    ):
        """cp s3://bucket/key.txt . skips large GLACIER objects and warns."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    HTTPResponse.raw(
                        b"",
                        status=200,
                        headers={
                            "Content-Length": str(20 * (1024**2)),
                            "Last-Modified": "Thu, 01 Jan 1970 00:00:00 GMT",
                            "ETag": '"foo-1"',
                            "x-amz-storage-class": "GLACIER",
                        },
                    ),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", "s3://bucket/key.txt", str(tmp_path)],
                cli_env(proxy),
            )

        assert rc == 2
        assert len(server.requests) == 1, format_requests(server)
        assert_head_object(server.requests[0], Bucket="bucket", Key="key.txt")
        assert "GLACIER" in stderr.decode()

    async def test_warns_on_deep_archive_incompatible_op_for_multipart_file(
        self, aws_cli, tmp_path
    ):
        """cp s3://bucket/key.txt . skips large DEEP_ARCHIVE objects and warns."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    HTTPResponse.raw(
                        b"",
                        status=200,
                        headers={
                            "Content-Length": str(20 * (1024**2)),
                            "Last-Modified": "Thu, 01 Jan 1970 00:00:00 GMT",
                            "ETag": '"foo-1"',
                            "x-amz-storage-class": "DEEP_ARCHIVE",
                        },
                    ),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", "s3://bucket/key.txt", str(tmp_path)],
                cli_env(proxy),
            )

        assert rc == 2
        assert len(server.requests) == 1, format_requests(server)
        assert_head_object(server.requests[0], Bucket="bucket", Key="key.txt")
        assert "GLACIER" in stderr.decode()

    async def test_s3s3_cp_with_destination_sse_c_multipart(
        self, aws_cli, tmp_path
    ):
        """S3->S3 multipart copy with encrypted destination sends SSE-C on all parts."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=8 * (1024**2)),
                    get_object_tagging_response(),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket-one/key.txt",
                    "s3://bucket/key.txt",
                    "--sse-c",
                    "--sse-c-key",
                    "destination-key",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 5, format_requests(server)
        # HeadObject should NOT have SSE-C (source is unencrypted)
        assert_head_object(
            server.requests[0],
            Bucket="bucket-one",
            Key="key.txt",
            ChecksumMode="ENABLED",
        )
        assert (
            server.requests[0].headers.get(
                "x-amz-server-side-encryption-customer-algorithm"
            )
            is None
        )
        # CreateMultipartUpload should have destination SSE-C
        assert_create_multipart_upload(
            server.requests[2],
            Bucket="bucket",
            Key="key.txt",
            SSECustomerAlgorithm="AES256",
        )

    async def test_s3s3_cp_with_different_sse_c_keys_multipart(
        self, aws_cli, tmp_path
    ):
        """S3->S3 multipart copy with different SSE-C keys for source and destination."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=8 * (1024**2)),
                    get_object_tagging_response(),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket-one/key.txt",
                    "s3://bucket/key.txt",
                    "--sse-c-copy-source",
                    "--sse-c-copy-source-key",
                    "source-key",
                    "--sse-c",
                    "--sse-c-key",
                    "destination-key",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 5, format_requests(server)
        # HeadObject should have source SSE-C
        assert_head_object(
            server.requests[0],
            Bucket="bucket-one",
            Key="key.txt",
            ChecksumMode="ENABLED",
            SSECustomerAlgorithm="AES256",
        )
        assert (
            server.requests[0].headers.get(
                "x-amz-server-side-encryption-customer-key"
            )
            is not None
        )
        # CreateMultipartUpload should have destination SSE-C
        assert_create_multipart_upload(
            server.requests[2],
            Bucket="bucket",
            Key="key.txt",
            SSECustomerAlgorithm="AES256",
        )

    async def test_cp_copy_large_file_with_sse_kms_and_key_id(
        self, aws_cli, tmp_path
    ):
        """S3->S3 multipart copy with --sse aws:kms sends KMS on CreateMultipartUpload."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=10 * (1024**2)),
                    create_mpu_response("foo"),
                    upload_part_copy_response(),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket/key1.txt",
                    "s3://bucket/key2.txt",
                    "--copy-props",
                    "none",
                    "--sse",
                    "aws:kms",
                    "--sse-kms-key-id",
                    "foo",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 5, format_requests(server)
        # CreateMultipartUpload should have KMS headers
        assert_create_multipart_upload(
            server.requests[1],
            Bucket="bucket",
            Key="key2.txt",
            ServerSideEncryption="aws:kms",
            SSEKMSKeyId="foo",
        )


@pytest.mark.asyncio
class TestStreamingCPCommand:
    async def test_streaming_upload(self, aws_cli, tmp_path):
        """cp - s3://bucket/streaming.txt uploads stdin content."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", "-", "s3://bucket/streaming.txt"],
                cli_env(proxy),
                stdin=b"foo\n",
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        req = server.requests[0]
        assert_put_object(
            req,
            Bucket="bucket",
            Key="streaming.txt",
            ChecksumAlgorithm="CRC64NVME",
        )

    async def test_streaming_upload_with_expected_size(
        self, aws_cli, tmp_path
    ):
        """cp - s3://bucket/streaming.txt --expected-size 4 uploads stdin."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "-",
                    "s3://bucket/streaming.txt",
                    "--expected-size",
                    "4",
                ],
                cli_env(proxy),
                stdin=b"foo\n",
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(
            server.requests[0],
            Bucket="bucket",
            Key="streaming.txt",
            ChecksumAlgorithm="CRC64NVME",
        )

    async def test_streaming_upload_error(self, aws_cli, tmp_path):
        """cp - s3://bucket/streaming.txt with error shows error message."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    error_response(
                        "NoSuchBucket",
                        "The specified bucket does not exist",
                        status=404,
                    )
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", "-", "s3://bucket/streaming.txt"],
                cli_env(proxy),
                stdin=b"foo\n",
            )

        assert rc == 1
        err = stderr.decode()
        error_message = (
            'An error occurred (NoSuchBucket) when calling '
            'the PutObject operation (reached max retries: 0): '
            'The specified bucket does not exist'
        )
        assert error_message in err

    async def test_streaming_download(self, aws_cli, tmp_path):
        """cp s3://bucket/streaming.txt - outputs content to stdout."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(
                        content_length=4,
                        **{
                            "Accept-Ranges": "bytes",
                            "Content-Type": "binary/octet-stream",
                        },
                    ),
                    get_object_response(
                        b"foo\n",
                        **{
                            "Accept-Ranges": "bytes",
                            "Content-Type": "binary/octet-stream",
                        },
                    ),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", "s3://bucket/streaming.txt", "-"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert stdout == b"foo\n"
        assert len(server.requests) == 2, format_requests(server)
        assert_head_object(
            server.requests[0],
            Bucket="bucket",
            Key="streaming.txt",
        )
        assert_get_object(
            server.requests[1],
            Bucket="bucket",
            Key="streaming.txt",
        )

    async def test_no_overwrite_cannot_be_used_with_streaming_download(
        self, aws_cli, tmp_path
    ):
        """cp s3://bucket/streaming.txt - --no-overwrite is rejected."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket/streaming.txt",
                    "-",
                    "--no-overwrite",
                ],
                cli_env(proxy),
            )

        assert rc == 252
        assert (
            "--no-overwrite parameter is not supported for streaming downloads"
            in stderr.decode()
        )


@pytest.mark.asyncio
class TestCpCommandWithRequesterPayer:
    async def test_single_upload(self, aws_cli, tmp_path):
        """cp --request-payer sends x-amz-request-payer on PutObject."""
        src = tmp_path / "myfile"
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
                    "cp",
                    str(src),
                    "s3://mybucket/mykey",
                    "--request-payer",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(
            server.requests[0],
            Bucket="mybucket",
            Key="mykey",
            RequestPayer="requester",
            ChecksumAlgorithm="CRC64NVME",
        )

    async def test_multipart_upload(self, aws_cli, tmp_path):
        """cp --request-payer large file sends requester-payer on all MPU operations."""
        src = tmp_path / "myfile"
        src.write_bytes(b"a" * 10 * (1024**2))
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    create_mpu_response("myid"),
                    upload_part_response("myetag"),
                    upload_part_response("myetag"),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    str(src),
                    "s3://mybucket/mykey",
                    "--request-payer",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 4, format_requests(server)
        assert_create_multipart_upload(
            server.requests[0],
            Bucket="mybucket",
            Key="mykey",
            RequestPayer="requester",
            ChecksumAlgorithm="CRC64NVME",
        )
        # UploadPart requests should have requester-payer
        for req in server.requests[1:3]:
            assert req.headers.get("x-amz-request-payer") == "requester"
        assert_complete_multipart_upload(
            server.requests[3],
            Bucket="mybucket",
            Key="mykey",
            UploadId="myid",
            RequestPayer="requester",
        )

    async def test_recursive_upload(self, aws_cli, tmp_path):
        """cp --recursive --request-payer sends requester-payer on PutObject."""
        src = tmp_path / "myfile"
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
                    "cp",
                    str(tmp_path),
                    "s3://mybucket/",
                    "--request-payer",
                    "--recursive",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(
            server.requests[0],
            Bucket="mybucket",
            Key="myfile",
            RequestPayer="requester",
            ChecksumAlgorithm="CRC64NVME",
        )

    async def test_single_download(self, aws_cli, tmp_path):
        """cp s3://bucket/key local --request-payer sends requester-payer on Head+Get."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    get_object_response(b"foo"),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://mybucket/mykey",
                    str(tmp_path),
                    "--request-payer",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_head_object(
            server.requests[0],
            Bucket="mybucket",
            Key="mykey",
            RequestPayer="requester",
            ChecksumMode="ENABLED",
        )
        assert_get_object(
            server.requests[1],
            Bucket="mybucket",
            Key="mykey",
            RequestPayer="requester",
        )

    async def test_ranged_download(self, aws_cli, tmp_path):
        """cp s3://bucket/key local --request-payer with large file sends requester-payer on ranged Gets."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=10 * (1024**2)),
                    get_object_response(b"a" * 5 * (1024**2)),
                    get_object_response(b"a" * 5 * (1024**2)),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
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
            RequestPayer="requester",
            ChecksumMode="ENABLED",
        )
        # GetObject requests should have requester-payer and Range
        assert_get_object(
            server.requests[1],
            Bucket="mybucket",
            Key="mykey",
            RequestPayer="requester",
        )
        assert server.requests[1].headers.get("range") is not None
        assert_get_object(
            server.requests[2],
            Bucket="mybucket",
            Key="mykey",
            RequestPayer="requester",
        )
        assert server.requests[2].headers.get("range") is not None

    async def test_recursive_download(self, aws_cli, tmp_path):
        """cp s3://bucket/ local --recursive --request-payer sends requester-payer on List+Get."""
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
                                    "Key": "mykey",
                                    "Size": 4,
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                }
                            ],
                        )
                    ),
                    get_object_response(b"foo"),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://mybucket/",
                    str(tmp_path),
                    "--request-payer",
                    "--recursive",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_list_objects_v2(
            server.requests[0],
            Bucket="mybucket",
            RequestPayer="requester",
        )
        assert_get_object(
            server.requests[1],
            Bucket="mybucket",
            Key="mykey",
            RequestPayer="requester",
        )

    async def test_single_copy(self, aws_cli, tmp_path):
        """cp s3://src s3://dst --request-payer sends requester-payer on Head+Copy."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://sourcebucket/sourcekey",
                    "s3://mybucket/mykey",
                    "--request-payer",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_head_object(
            server.requests[0],
            Bucket="sourcebucket",
            Key="sourcekey",
            RequestPayer="requester",
            ChecksumMode="ENABLED",
        )
        assert_copy_object(
            server.requests[1],
            Bucket="mybucket",
            Key="mykey",
            CopySource="sourcebucket/sourcekey",
            RequestPayer="requester",
        )

    async def test_multipart_copy(self, aws_cli, tmp_path):
        """cp s3://src s3://dst --request-payer large file sends requester-payer on all MPU ops."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=10 * (1024**2)),
                    create_mpu_response("id"),
                    upload_part_copy_response(),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://sourcebucket/sourcekey",
                    "s3://mybucket/mykey",
                    "--copy-props",
                    "none",
                    "--request-payer",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 5, format_requests(server)
        assert_head_object(
            server.requests[0],
            Bucket="sourcebucket",
            Key="sourcekey",
            RequestPayer="requester",
            ChecksumMode="ENABLED",
        )
        assert_create_multipart_upload(
            server.requests[1],
            Bucket="mybucket",
            Key="mykey",
            RequestPayer="requester",
        )
        # UploadPartCopy requests should have requester-payer
        for req in server.requests[2:4]:
            assert req.headers.get("x-amz-request-payer") == "requester"
        assert_complete_multipart_upload(
            server.requests[4],
            Bucket="mybucket",
            Key="mykey",
            UploadId="id",
            MultipartUpload=[{"PartNumber": "1"}, {"PartNumber": "2"}],
            RequestPayer="requester",
        )

    async def test_recursive_copy(self, aws_cli, tmp_path):
        """cp s3://src/ s3://dst/ --recursive --request-payer sends requester-payer on List+Copy."""
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
                                    "Key": "mykey",
                                    "Size": 4,
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                }
                            ],
                        )
                    ),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://sourcebucket/",
                    "s3://mybucket/",
                    "--request-payer",
                    "--recursive",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_list_objects_v2(
            server.requests[0],
            Bucket="sourcebucket",
            RequestPayer="requester",
        )
        assert_copy_object(
            server.requests[1],
            Bucket="mybucket",
            Key="mykey",
            CopySource="sourcebucket/mykey",
            RequestPayer="requester",
        )

    async def test_mp_copy_object(self, aws_cli, tmp_path):
        """cp s3->s3 --request-payer multipart copy sends requester-payer on GetObjectTagging."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=8 * (1024**2)),
                    get_object_tagging_response(),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://sourcebucket/mykey",
                    "s3://mybucket/mykey",
                    "--request-payer",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 5, format_requests(server)
        assert_get_object_tagging(
            server.requests[1],
            Bucket="sourcebucket",
            Key="mykey",
            RequestPayer="requester",
        )
        assert_create_multipart_upload(
            server.requests[2],
            Bucket="mybucket",
            Key="mykey",
            RequestPayer="requester",
        )

    async def test_mp_copy_object_with_tags_exceed_2k(self, aws_cli, tmp_path):
        """cp s3->s3 --request-payer multipart copy with large tags sends PutObjectTagging."""
        large_value = "value" * (2 * 1024)
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=8 * (1024**2)),
                    get_object_tagging_response({"tag-key": large_value}),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                    put_object_tagging_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://sourcebucket/mykey",
                    "s3://mybucket/mykey",
                    "--request-payer",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 6, format_requests(server)
        assert_get_object_tagging(
            server.requests[1],
            Bucket="sourcebucket",
            Key="mykey",
            RequestPayer="requester",
        )
        assert_create_multipart_upload(
            server.requests[2],
            Bucket="mybucket",
            Key="mykey",
            RequestPayer="requester",
        )
        assert_put_object_tagging(
            server.requests[5],
            Bucket="mybucket",
            Key="mykey",
            Tagging={"TagSet": [{"Key": "tag-key", "Value": large_value}]},
            RequestPayer="requester",
        )


@pytest.mark.asyncio
class TestAccesspointCPCommand:
    """Tests for cp with S3 Access Point ARNs."""

    ARN = "arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint"
    HOST = "endpoint-123456789012.s3-accesspoint.us-west-2.amazonaws.com"

    async def test_upload(self, aws_cli, tmp_path):
        """cp local s3://<accesspoint-arn>/key uploads to accesspoint."""
        src = tmp_path / "myfile"
        src.write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", str(src), f"s3://{self.ARN}/mykey"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(server.requests[0], Bucket=self.ARN, Key="mykey")

    async def test_recursive_upload(self, aws_cli, tmp_path):
        """cp local s3://<accesspoint-arn>/ --recursive uploads to accesspoint."""
        (tmp_path / "myfile").write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    str(tmp_path),
                    f"s3://{self.ARN}/",
                    "--recursive",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(server.requests[0], Bucket=self.ARN, Key="myfile")

    async def test_download(self, aws_cli, tmp_path):
        """cp s3://<accesspoint-arn>/key local downloads from accesspoint."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    get_object_response(b"foo"),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", f"s3://{self.ARN}/mykey", str(tmp_path)],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_head_object(
            server.requests[0],
            Bucket=self.ARN,
            Key="mykey",
            ChecksumMode="ENABLED",
        )
        assert_get_object(server.requests[1], Bucket=self.ARN, Key="mykey")

    async def test_recursive_download(self, aws_cli, tmp_path):
        """cp s3://<accesspoint-arn> local --recursive downloads from accesspoint."""
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
                                    "Key": "mykey",
                                    "Size": 4,
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                }
                            ],
                        )
                    ),
                    get_object_response(b"foo"),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", f"s3://{self.ARN}", str(tmp_path), "--recursive"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_list_objects_v2(
            server.requests[0],
            Bucket=self.ARN,
        )
        assert_get_object(server.requests[1], Bucket=self.ARN, Key="mykey")

    async def test_copy(self, aws_cli, tmp_path):
        """cp s3://<arn>/key s3://<arn-dest>/key copies between accesspoints."""
        dest_arn = self.ARN + "-dest"
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    f"s3://{self.ARN}/mykey",
                    f"s3://{dest_arn}/mykey",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_head_object(
            server.requests[0],
            Bucket=self.ARN,
            Key="mykey",
            ChecksumMode="ENABLED",
        )
        assert_copy_object(server.requests[1], Bucket=dest_arn, Key="mykey")

    async def test_recursive_copy(self, aws_cli, tmp_path):
        """cp s3://<arn> s3://<arn-dest> --recursive copies between accesspoints."""
        dest_arn = self.ARN + "-dest"
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
                                    "Key": "mykey",
                                    "Size": 4,
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                }
                            ],
                        )
                    ),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    f"s3://{self.ARN}",
                    f"s3://{dest_arn}",
                    "--recursive",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_list_objects_v2(
            server.requests[0],
            Bucket=self.ARN,
        )
        assert_copy_object(server.requests[1], Bucket=dest_arn, Key="mykey")

    async def test_accepts_mrap_arns(self, aws_cli, tmp_path):
        """cp to MRAP ARN (colon separator) works."""
        mrap_arn = "arn:aws:s3::123456789012:accesspoint:mfzwi23gnjvgw.mrap"
        src = tmp_path / "myfile"
        src.write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", str(src), f"s3://{mrap_arn}/mykey"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(server.requests[0], Bucket=mrap_arn, Key="mykey")

    async def test_accepts_mrap_arns_with_slash(self, aws_cli, tmp_path):
        """cp to MRAP ARN (slash separator) works."""
        mrap_arn = "arn:aws:s3::123456789012:accesspoint/mfzwi23gnjvgw.mrap"
        src = tmp_path / "myfile"
        src.write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(server, [put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", str(src), f"s3://{mrap_arn}/mykey"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_put_object(server.requests[0], Bucket=mrap_arn, Key="mykey")


@pytest.mark.asyncio
class TestCopyPropsNoneCpCommand:
    """Tests for cp --copy-props none (S3->S3 copy)."""

    async def test_copy_object(self, aws_cli, tmp_path):
        """--copy-props none sends MetadataDirective=REPLACE and TaggingDirective=REPLACE."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "none",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_copy_object(
            server.requests[1],
            Bucket="target-bucket",
            Key="target-key",
            CopySource="source-bucket/source-key",
            MetadataDirective="REPLACE",
            TaggingDirective="REPLACE",
        )

    async def test_mp_copy_object(self, aws_cli, tmp_path):
        """--copy-props none multipart copy has no extra params on CreateMPU."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=8 * (1024**2)),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "none",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 4, format_requests(server)
        assert_create_multipart_upload(
            server.requests[1],
            Bucket="target-bucket",
            Key="target-key",
        )
        # Should NOT have metadata/tagging headers on CreateMPU
        req = server.requests[1]
        assert req.headers.get("x-amz-tagging") is None
        assert req.headers.get("cache-control") is None

    async def test_metadata_directive_disables_copy_props(
        self, aws_cli, tmp_path
    ):
        """--copy-props none --metadata-directive COPY bypasses copy-props entirely."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "none",
                    "--metadata-directive",
                    "COPY",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_copy_object(
            server.requests[1],
            Bucket="target-bucket",
            Key="target-key",
            CopySource="source-bucket/source-key",
            MetadataDirective="COPY",
        )
        # No tagging or annotation directives when --metadata-directive is used
        req = server.requests[1]
        assert req.headers.get("x-amz-tagging-directive") is None
        assert req.headers.get("x-amz-object-annotation-directive") is None


@pytest.mark.asyncio
class TestCopyPropsMetadataDirectiveCpCommand:
    """Tests for cp --copy-props metadata-directive (S3->S3 copy)."""

    ALL_METADATA_HEADERS = {
        "cache-control": "cache-control",
        "content-disposition": "content-disposition",
        "content-encoding": "content-encoding",
        "content-language": "content-language",
        "content-type": "content-type",
        "expires": "Tue, 07 Jan 2020 20:40:03 GMT",
        "x-amz-meta-key": "value",
    }

    def _head_with_metadata(self, content_length: int = 100) -> HTTPResponse:
        return head_object_response(
            content_length=content_length,
            **self.ALL_METADATA_HEADERS,
        )

    async def test_copy_object(self, aws_cli, tmp_path):
        """--copy-props metadata-directive sends TaggingDirective=REPLACE on CopyObject."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "metadata-directive",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_copy_object(
            server.requests[1],
            Bucket="target-bucket",
            Key="target-key",
            CopySource="source-bucket/source-key",
            TaggingDirective="REPLACE",
        )

    async def test_copy_object_overrides_with_cmdline_props(
        self, aws_cli, tmp_path
    ):
        """--copy-props metadata-directive with --content-type override."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    self._head_with_metadata(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "metadata-directive",
                    "--content-type",
                    "content-type-from-cmdline",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_copy_object(
            server.requests[1],
            Bucket="target-bucket",
            Key="target-key",
            CopySource="source-bucket/source-key",
            CacheControl="cache-control",
            ContentDisposition="content-disposition",
            ContentEncoding="content-encoding",
            ContentLanguage="content-language",
            ContentType="content-type-from-cmdline",
            Expires="Tue, 07 Jan 2020 20:40:03 GMT",
            Metadata={"key": "value"},
            MetadataDirective="REPLACE",
            TaggingDirective="REPLACE",
        )

    async def test_recursive_copy_object(self, aws_cli, tmp_path):
        """--copy-props metadata-directive --recursive sends TaggingDirective=REPLACE."""
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
                                    "Key": "source-key",
                                    "Size": 100,
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                }
                            ],
                        )
                    ),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/",
                    "s3://target-bucket/",
                    "--recursive",
                    "--copy-props",
                    "metadata-directive",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_copy_object(
            server.requests[1],
            Bucket="target-bucket",
            Key="source-key",
            CopySource="source-bucket/source-key",
            TaggingDirective="REPLACE",
        )

    async def test_recursive_copy_object_overrides_with_cmdline_props(
        self, aws_cli, tmp_path
    ):
        """--copy-props metadata-directive --recursive with --metadata override."""
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
                                    "Key": "source-key",
                                    "Size": 100,
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                }
                            ],
                        )
                    ),
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/",
                    "s3://target-bucket/",
                    "--recursive",
                    "--copy-props",
                    "metadata-directive",
                    "--metadata",
                    "key=val-from-cmdline",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)
        assert_copy_object(
            server.requests[2],
            Bucket="target-bucket",
            Key="source-key",
            CopySource="source-bucket/source-key",
            MetadataDirective="REPLACE",
            TaggingDirective="REPLACE",
            Metadata={"key": "val-from-cmdline"},
        )

    async def test_recursive_copy_maps_additional_head_object_headers(
        self, aws_cli, tmp_path
    ):
        """--copy-props metadata-directive --recursive --request-payer sends requester-payer on HeadObject."""
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
                                    "Key": "source-key",
                                    "Size": 100,
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                }
                            ],
                        )
                    ),
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/",
                    "s3://target-bucket/",
                    "--recursive",
                    "--copy-props",
                    "metadata-directive",
                    "--metadata",
                    "key=val-from-cmdline",
                    "--request-payer",
                    "requester",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3
        assert_head_object(
            server.requests[1],
            Bucket="source-bucket",
            Key="source-key",
            RequestPayer="requester",
        )

    async def test_mp_copy_object(self, aws_cli, tmp_path):
        """--copy-props metadata-directive multipart copy sends metadata on CreateMPU."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    self._head_with_metadata(content_length=8 * (1024**2)),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "metadata-directive",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 4, format_requests(server)
        assert_create_multipart_upload(
            server.requests[1],
            Bucket="target-bucket",
            Key="target-key",
            CacheControl="cache-control",
            ContentDisposition="content-disposition",
            ContentEncoding="content-encoding",
            ContentLanguage="content-language",
            ContentType="content-type",
            Expires="Tue, 07 Jan 2020 20:40:03 GMT",
            Metadata={"key": "value"},
        )

    async def test_mp_copy_object_with_prop_overrides(self, aws_cli, tmp_path):
        """--copy-props metadata-directive multipart copy with --content-type override."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    self._head_with_metadata(content_length=8 * (1024**2)),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "metadata-directive",
                    "--content-type",
                    "content-type-from-cmdline",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 4, format_requests(server)
        assert_create_multipart_upload(
            server.requests[1],
            Bucket="target-bucket",
            Key="target-key",
            CacheControl="cache-control",
            ContentDisposition="content-disposition",
            ContentEncoding="content-encoding",
            ContentLanguage="content-language",
            ContentType="content-type-from-cmdline",
            Expires="Tue, 07 Jan 2020 20:40:03 GMT",
            Metadata={"key": "value"},
        )

    async def test_recursive_mp_copy(self, aws_cli, tmp_path):
        """--copy-props metadata-directive --recursive multipart copy sends metadata on CreateMPU."""
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
                                    "Key": "source-key",
                                    "Size": 8 * (1024**2),
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                }
                            ],
                        )
                    ),
                    self._head_with_metadata(content_length=8 * (1024**2)),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/",
                    "s3://target-bucket/",
                    "--recursive",
                    "--copy-props",
                    "metadata-directive",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 5, format_requests(server)
        assert_create_multipart_upload(
            server.requests[2],
            Bucket="target-bucket",
            Key="source-key",
        )

    async def test_recursive_mp_copy_object_with_prop_overrides(
        self, aws_cli, tmp_path
    ):
        """--copy-props metadata-directive --recursive multipart with --content-type override."""
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
                                    "Key": "source-key",
                                    "Size": 8 * (1024**2),
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                }
                            ],
                        )
                    ),
                    self._head_with_metadata(content_length=8 * (1024**2)),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/",
                    "s3://target-bucket/",
                    "--recursive",
                    "--copy-props",
                    "metadata-directive",
                    "--content-type",
                    "content-type-from-cmdline",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 5, format_requests(server)
        assert_create_multipart_upload(
            server.requests[2],
            Bucket="target-bucket",
            Key="source-key",
            ContentType="content-type-from-cmdline",
        )

    async def test_recursive_mp_copy_maps_additional_head_object_headers(
        self, aws_cli, tmp_path
    ):
        """--copy-props metadata-directive --recursive multipart --request-payer on HeadObject."""
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
                                    "Key": "source-key",
                                    "Size": 8 * (1024**2),
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                }
                            ],
                        )
                    ),
                    head_object_response(content_length=8 * (1024**2)),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/",
                    "s3://target-bucket/",
                    "--recursive",
                    "--copy-props",
                    "metadata-directive",
                    "--request-payer",
                    "requester",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 5, format_requests(server)
        assert_head_object(
            server.requests[1],
            Bucket="source-bucket",
            Key="source-key",
            RequestPayer="requester",
        )

    async def test_fails_when_head_object_fails(self, aws_cli, tmp_path):
        """--copy-props metadata-directive --recursive fails when HeadObject returns 404."""
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
                                    "Key": "source-key",
                                    "Size": 8 * (1024**2),
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                }
                            ],
                        )
                    ),
                    error_response(
                        "NoSuchKey",
                        "The specified key does not exist.",
                        status=404,
                    ),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/",
                    "s3://target-bucket/",
                    "--recursive",
                    "--copy-props",
                    "metadata-directive",
                ],
                cli_env(proxy),
            )

        assert rc == 1
        assert "404" in stderr.decode() or "NoSuchKey" in stderr.decode()

    async def test_metadata_directive_disables_copy_props(
        self, aws_cli, tmp_path
    ):
        """--copy-props metadata-directive --metadata-directive REPLACE bypasses copy-props."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "metadata-directive",
                    "--metadata-directive",
                    "REPLACE",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_copy_object(
            server.requests[1],
            Bucket="target-bucket",
            Key="target-key",
            CopySource="source-bucket/source-key",
            MetadataDirective="REPLACE",
        )
        # No tagging or annotation directives when --metadata-directive is used
        req = server.requests[1]
        assert req.headers.get("x-amz-tagging-directive") is None
        assert req.headers.get("x-amz-object-annotation-directive") is None


@pytest.mark.asyncio
class TestCopyPropsDefaultCpCommand:
    """Tests for cp --copy-props default (S3->S3 copy)."""

    ALL_METADATA_HEADERS = {
        "cache-control": "cache-control",
        "content-disposition": "content-disposition",
        "content-encoding": "content-encoding",
        "content-language": "content-language",
        "content-type": "content-type",
        "expires": "Tue, 07 Jan 2020 20:40:03 GMT",
        "x-amz-meta-key": "value",
    }
    URLENCODED_TAGS = "tag-key=tag-value&tag-key2=tag-value2"
    TAGS = {"tag-key": "tag-value", "tag-key2": "tag-value2"}
    TAGS_OVER_2K = {"tag-key": "value" * (2 * 1024)}

    def _head_with_metadata(self, content_length: int = 100) -> HTTPResponse:
        return head_object_response(
            content_length=content_length,
            **self.ALL_METADATA_HEADERS,
        )

    async def test_copy_object(self, aws_cli, tmp_path):
        """--copy-props default single copy has no extra directives."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "default",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_copy_object(
            server.requests[1],
            Bucket="target-bucket",
            Key="target-key",
            CopySource="source-bucket/source-key",
        )

    async def test_is_default_value(self, aws_cli, tmp_path):
        """No --copy-props flag behaves same as --copy-props default."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_copy_object(
            server.requests[1],
            Bucket="target-bucket",
            Key="target-key",
            CopySource="source-bucket/source-key",
        )

    async def test_copy_object_with_prop_overrides(self, aws_cli, tmp_path):
        """--copy-props default with --content-language override sends REPLACE + all metadata."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    self._head_with_metadata(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "default",
                    "--content-language",
                    "content-lang-from-cmdline",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_copy_object(
            server.requests[1],
            Bucket="target-bucket",
            Key="target-key",
            CopySource="source-bucket/source-key",
            CacheControl="cache-control",
            ContentDisposition="content-disposition",
            ContentEncoding="content-encoding",
            ContentLanguage="content-lang-from-cmdline",
            ContentType="content-type",
            Expires="Tue, 07 Jan 2020 20:40:03 GMT",
            Metadata={"key": "value"},
            MetadataDirective="REPLACE",
        )

    async def test_recursive_copy_object(self, aws_cli, tmp_path):
        """--copy-props default --recursive single copy has no extra directives."""
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
                                    "Key": "source-key",
                                    "Size": 100,
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                }
                            ],
                        )
                    ),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/",
                    "s3://target-bucket/",
                    "--recursive",
                    "--copy-props",
                    "default",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_copy_object(
            server.requests[1],
            Bucket="target-bucket",
            Key="source-key",
            CopySource="source-bucket/source-key",
        )

    async def test_recursive_copy_object_with_prop_overrides(
        self, aws_cli, tmp_path
    ):
        """--copy-props default --recursive with --content-language override."""
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
                                    "Key": "source-key",
                                    "Size": 100,
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                }
                            ],
                        )
                    ),
                    self._head_with_metadata(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/",
                    "s3://target-bucket/",
                    "--recursive",
                    "--copy-props",
                    "default",
                    "--content-language",
                    "content-lang-from-cmdline",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)
        assert_copy_object(
            server.requests[2],
            Bucket="target-bucket",
            Key="source-key",
            CopySource="source-bucket/source-key",
            MetadataDirective="REPLACE",
            ContentLanguage="content-lang-from-cmdline",
        )

    async def test_mp_copy_object(self, aws_cli, tmp_path):
        """--copy-props default multipart copy sends metadata + tagging on CreateMPU."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    self._head_with_metadata(content_length=8 * (1024**2)),
                    get_object_tagging_response(self.TAGS),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "default",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 5, format_requests(server)
        assert_create_multipart_upload(
            server.requests[2],
            Bucket="target-bucket",
            Key="target-key",
            CacheControl="cache-control",
            ContentDisposition="content-disposition",
            ContentEncoding="content-encoding",
            ContentLanguage="content-language",
            ContentType="content-type",
            Expires="Tue, 07 Jan 2020 20:40:03 GMT",
            Metadata={"key": "value"},
            Tagging="tag-key=tag-value&tag-key2=tag-value2",
        )

    async def test_mp_copy_object_with_prop_overrides(self, aws_cli, tmp_path):
        """--copy-props default multipart copy with --cache-control override."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    self._head_with_metadata(content_length=8 * (1024**2)),
                    get_object_tagging_response(self.TAGS),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "default",
                    "--cache-control",
                    "cache-control-from-cmdline",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 5, format_requests(server)
        assert_create_multipart_upload(
            server.requests[2],
            Bucket="target-bucket",
            Key="target-key",
            CacheControl="cache-control-from-cmdline",
            ContentDisposition="content-disposition",
            ContentEncoding="content-encoding",
            ContentLanguage="content-language",
            ContentType="content-type",
            Expires="Tue, 07 Jan 2020 20:40:03 GMT",
            Metadata={"key": "value"},
            Tagging="tag-key=tag-value&tag-key2=tag-value2",
        )

    async def test_mp_copy_object_no_tags(self, aws_cli, tmp_path):
        """--copy-props default multipart copy with no tags omits x-amz-tagging."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=8 * (1024**2)),
                    get_object_tagging_response(),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "default",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 5, format_requests(server)
        assert_create_multipart_upload(
            server.requests[2],
            Bucket="target-bucket",
            Key="target-key",
        )
        assert server.requests[2].headers.get("x-amz-tagging") is None

    async def test_mp_copy_object_tags_exceed_2k(self, aws_cli, tmp_path):
        """--copy-props default multipart copy with >2k tags uses PutObjectTagging after copy."""
        large_value = "value" * (2 * 1024)
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=8 * (1024**2)),
                    get_object_tagging_response(self.TAGS_OVER_2K),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                    put_object_tagging_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "default",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 6, format_requests(server)
        assert_create_multipart_upload(
            server.requests[2],
            Bucket="target-bucket",
            Key="target-key",
        )
        assert server.requests[2].headers.get("x-amz-tagging") is None
        assert_put_object_tagging(
            server.requests[5],
            Bucket="target-bucket",
            Key="target-key",
            Tagging={"TagSet": [{"Key": "tag-key", "Value": large_value}]},
        )

    async def test_fails_when_get_tagging_object_fails(
        self, aws_cli, tmp_path
    ):
        """--copy-props default fails when GetObjectTagging returns 403."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=8 * (1024**2)),
                    error_response(
                        "AccessDenied", "Access Denied", status=403
                    ),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "default",
                ],
                cli_env(proxy),
            )

        assert rc == 1
        assert "AccessDenied" in stderr.decode()

    async def test_fails_and_cleans_up_when_put_tagging_object_fails(
        self, aws_cli, tmp_path
    ):
        """--copy-props default cleans up (DeleteObject) when PutObjectTagging fails."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=8 * (1024**2)),
                    get_object_tagging_response(self.TAGS_OVER_2K),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                    error_response(
                        "AccessDenied", "Access Denied", status=403
                    ),
                    HTTPResponse.raw(b"", status=204),  # DeleteObject
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "default",
                ],
                cli_env(proxy),
            )

        assert rc == 1
        assert "AccessDenied" in stderr.decode()
        assert_delete_object(
            server.requests[6],
            Bucket="target-bucket",
            Key="target-key",
        )

    async def test_clean_up_uses_requester_payer(self, aws_cli, tmp_path):
        """--copy-props default cleanup DeleteObject uses --request-payer."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=8 * (1024**2)),
                    get_object_tagging_response(self.TAGS_OVER_2K),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                    error_response(
                        "AccessDenied", "Access Denied", status=403
                    ),
                    HTTPResponse.raw(b"", status=204),  # DeleteObject
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "default",
                    "--request-payer",
                    "requester",
                ],
                cli_env(proxy),
            )

        assert rc == 1
        assert "AccessDenied" in stderr.decode()
        assert_delete_object(
            server.requests[6],
            Bucket="target-bucket",
            Key="target-key",
            RequestPayer="requester",
        )

    async def test_metadata_directive_disables_copy_props(
        self, aws_cli, tmp_path
    ):
        """--copy-props default --metadata-directive REPLACE bypasses copy-props."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "default",
                    "--metadata-directive",
                    "REPLACE",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_copy_object(
            server.requests[1],
            Bucket="target-bucket",
            Key="target-key",
            CopySource="source-bucket/source-key",
            MetadataDirective="REPLACE",
        )
        req = server.requests[1]
        assert req.headers.get("x-amz-tagging-directive") is None
        assert req.headers.get("x-amz-object-annotation-directive") is None


@pytest.mark.asyncio
class TestCopyPropsAllCpCommand:
    """Tests for cp --copy-props all (S3->S3 copy with annotations)."""

    ANNOTATION_PAYLOAD = b"annotation-payload"

    def _complete_mpu_response_with_version(self) -> HTTPResponse:
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<CompleteMultipartUploadResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
            "<Location>http://bucket.s3.amazonaws.com/key</Location>"
            "<Bucket>target-bucket</Bucket><Key>target-key</Key>"
            '<ETag>"dest-etag"</ETag>'
            "</CompleteMultipartUploadResult>"
        )
        return HTTPResponse.raw(
            body.encode(),
            status=200,
            headers={
                "Content-Type": "application/xml",
                "x-amz-version-id": "dest-version-id",
            },
        )

    async def test_copy_object_excludes_nothing_for_single_part(
        self, aws_cli, tmp_path
    ):
        """--copy-props all single-part copy does NOT set AnnotationDirective=EXCLUDE."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "all",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_copy_object(
            server.requests[1],
            Bucket="target-bucket",
            Key="target-key",
            CopySource="source-bucket/source-key",
        )
        # Should NOT have AnnotationDirective (relies on server default COPY)
        assert (
            server.requests[1].headers.get("x-amz-object-annotation-directive")
            is None
        )

    async def test_mp_copy_object_copies_annotations(self, aws_cli, tmp_path):
        """--copy-props all multipart copy reads and writes annotations."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=8 * (1024**2)),
                    get_object_tagging_response({"tag-key": "tag-value"}),
                    list_object_annotations_response(["ann1", "ann2"]),
                    get_object_annotation_response(self.ANNOTATION_PAYLOAD),
                    get_object_annotation_response(self.ANNOTATION_PAYLOAD),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    self._complete_mpu_response_with_version(),
                    put_object_annotation_response(),
                    put_object_annotation_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "all",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 10, format_requests(server)
        assert_list_object_annotations(
            server.requests[2],
            Bucket="source-bucket",
            Key="source-key",
        )
        assert_get_object_annotation(
            server.requests[3],
            Bucket="source-bucket",
            Key="source-key",
            AnnotationName="ann1",
        )
        assert_get_object_annotation(
            server.requests[4],
            Bucket="source-bucket",
            Key="source-key",
            AnnotationName="ann2",
        )
        assert_put_object_annotation(
            server.requests[8],
            Bucket="target-bucket",
            Key="target-key",
            AnnotationName="ann1",
            ObjectIfMatch='"dest-etag"',
            VersionId="dest-version-id",
        )
        assert_put_object_annotation(
            server.requests[9],
            Bucket="target-bucket",
            Key="target-key",
            AnnotationName="ann2",
            ObjectIfMatch='"dest-etag"',
            VersionId="dest-version-id",
        )

    async def test_mp_copy_object_no_annotations(self, aws_cli, tmp_path):
        """--copy-props all multipart copy with no annotations skips Get/PutObjectAnnotation."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=8 * (1024**2)),
                    get_object_tagging_response(),
                    list_object_annotations_response([]),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "all",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 6, format_requests(server)
        assert_list_object_annotations(
            server.requests[2],
            Bucket="source-bucket",
            Key="source-key",
        )
        # No GetObjectAnnotation or PutObjectAnnotation requests
        for r in server.requests[3:]:
            assert "annotationName" not in r.effective_path

    async def test_mp_copy_object_partial_annotation_failure(
        self, aws_cli, tmp_path
    ):
        """--copy-props all fails if PutObjectAnnotation fails, does NOT delete dest object."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=8 * (1024**2)),
                    get_object_tagging_response(),
                    list_object_annotations_response(["ann1", "ann2"]),
                    get_object_annotation_response(self.ANNOTATION_PAYLOAD),
                    get_object_annotation_response(self.ANNOTATION_PAYLOAD),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    self._complete_mpu_response_with_version(),
                    put_object_annotation_response(),  # ann1 succeeds
                    error_response(
                        "AccessDenied", "Access Denied", status=403
                    ),  # ann2 fails
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "all",
                ],
                cli_env(proxy),
            )

        assert rc == 1
        err = stderr.decode()
        assert "ann1" in err or "ann2" in err
        # No DeleteObject — partial annotation failure does not clean up
        for r in server.requests:
            if r.method == "DELETE":
                assert (
                    "annotation" in r.effective_path
                    or "uploadId" in r.effective_path
                ), f"Unexpected DELETE: {r.effective_path}"

    async def test_mp_copy_object_copies_annotations_with_source_version_id(
        self, aws_cli, tmp_path
    ):
        """--copy-props all multipart copy passes source versionId to annotation reads."""
        source_version_id = "src-version-id"
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    HTTPResponse.raw(
                        b"",
                        status=200,
                        headers={
                            "Content-Length": str(8 * (1024**2)),
                            "Last-Modified": "Thu, 01 Jan 1970 00:00:00 GMT",
                            "ETag": '"foo-1"',
                            "x-amz-version-id": source_version_id,
                        },
                    ),
                    get_object_tagging_response({"tag-key": "tag-value"}),
                    list_object_annotations_response(["ann1"]),
                    get_object_annotation_response(self.ANNOTATION_PAYLOAD),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    self._complete_mpu_response_with_version(),
                    put_object_annotation_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://source-bucket/source-key",
                    "s3://target-bucket/target-key",
                    "--copy-props",
                    "all",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 8, format_requests(server)
        assert_list_object_annotations(
            server.requests[2],
            Bucket="source-bucket",
            Key="source-key",
            VersionId=source_version_id,
        )
        assert_get_object_annotation(
            server.requests[3],
            Bucket="source-bucket",
            Key="source-key",
            AnnotationName="ann1",
            VersionId=source_version_id,
        )
        assert_put_object_annotation(
            server.requests[7],
            Bucket="target-bucket",
            Key="target-key",
            AnnotationName="ann1",
            ObjectIfMatch='"dest-etag"',
            VersionId="dest-version-id",
        )


@pytest.mark.asyncio
class TestCpSourceRegion:
    """Tests for cp --source-region routing requests to correct endpoints."""

    SOURCE_BUCKET = "sourcebucket"
    SOURCE_REGION = "af-south-1"
    TARGET_BUCKET = "bucket"
    TARGET_REGION = "us-east-1"
    SOURCE_HOST = f"{SOURCE_BUCKET}.s3.{SOURCE_REGION}.amazonaws.com"
    TARGET_HOST = f"{TARGET_BUCKET}.s3.{TARGET_REGION}.amazonaws.com"

    async def test_respects_source_region_for_single_copy(
        self, aws_cli, tmp_path
    ):
        """--source-region routes HeadObject to source region, CopyObject to target."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    f"s3://{self.SOURCE_BUCKET}/key",
                    f"s3://{self.TARGET_BUCKET}/",
                    "--source-region",
                    self.SOURCE_REGION,
                    "--region",
                    self.TARGET_REGION,
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_head_object(
            server.requests[0],
            Bucket=self.SOURCE_BUCKET,
            Key="key",
        )
        assert server.requests[0].headers.get("host") == self.SOURCE_HOST
        assert_copy_object(
            server.requests[1],
            Bucket=self.TARGET_BUCKET,
            Key="key",
        )
        assert server.requests[1].headers.get("host") == self.TARGET_HOST

    async def test_respects_source_region_for_recursive_copy(
        self, aws_cli, tmp_path
    ):
        """--source-region --recursive routes List to source, Copy to target."""
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
                                    "Key": "key",
                                    "Size": 100,
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                }
                            ],
                        )
                    ),
                    copy_object_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    f"s3://{self.SOURCE_BUCKET}/",
                    f"s3://{self.TARGET_BUCKET}/",
                    "--source-region",
                    self.SOURCE_REGION,
                    "--region",
                    self.TARGET_REGION,
                    "--recursive",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert server.requests[0].headers.get("host") == self.SOURCE_HOST
        assert server.requests[1].headers.get("host") == self.TARGET_HOST

    async def test_respects_source_region_for_copying_mp_object_tags(
        self, aws_cli, tmp_path
    ):
        """--source-region multipart copy routes tagging ops to correct regions."""
        large_tag_value = "value" * (2 * 1024)
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    head_object_response(content_length=8 * (1024**2)),
                    get_object_tagging_response({"tag": large_tag_value}),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                    put_object_tagging_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    f"s3://{self.SOURCE_BUCKET}/key",
                    f"s3://{self.TARGET_BUCKET}/",
                    "--source-region",
                    self.SOURCE_REGION,
                    "--region",
                    self.TARGET_REGION,
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 6, format_requests(server)
        # HeadObject + GetObjectTagging → source region
        assert server.requests[0].headers.get("host") == self.SOURCE_HOST
        assert server.requests[1].headers.get("host") == self.SOURCE_HOST
        # CreateMPU + UploadPartCopy + CompleteMPU + PutObjectTagging → target region
        assert server.requests[2].headers.get("host") == self.TARGET_HOST
        assert server.requests[3].headers.get("host") == self.TARGET_HOST
        assert server.requests[4].headers.get("host") == self.TARGET_HOST
        assert server.requests[5].headers.get("host") == self.TARGET_HOST

    async def test_respects_source_region_for_recursive_mp_copy(
        self, aws_cli, tmp_path
    ):
        """--source-region --recursive multipart copy routes to correct regions."""
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
                                    "Key": "key",
                                    "Size": 10 * (1024**2),
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                }
                            ],
                        )
                    ),
                    head_object_response(content_length=10 * (1024**2)),
                    get_object_tagging_response(),
                    create_mpu_response("upload_id"),
                    upload_part_copy_response(),
                    upload_part_copy_response(),
                    complete_mpu_response(),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    f"s3://{self.SOURCE_BUCKET}/",
                    f"s3://{self.TARGET_BUCKET}/",
                    "--source-region",
                    self.SOURCE_REGION,
                    "--region",
                    self.TARGET_REGION,
                    "--recursive",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 7, format_requests(server)
        # Source region: ListObjectsV2
        assert_list_objects_v2(server.requests[0], Bucket=self.SOURCE_BUCKET)
        assert server.requests[0].headers.get("host") == self.SOURCE_HOST
        # Source region: HeadObject (for metadata + size/etag)
        assert_head_object(
            server.requests[1],
            Bucket=self.SOURCE_BUCKET,
            Key="key",
        )
        assert server.requests[1].headers.get("host") == self.SOURCE_HOST
        # Source region: GetObjectTagging
        assert_get_object_tagging(
            server.requests[2],
            Bucket=self.SOURCE_BUCKET,
            Key="key",
        )
        assert server.requests[2].headers.get("host") == self.SOURCE_HOST
        # Target region: CreateMultipartUpload
        assert_create_multipart_upload(
            server.requests[3],
            Bucket=self.TARGET_BUCKET,
            Key="key",
        )
        assert server.requests[3].headers.get("host") == self.TARGET_HOST
        # Target region: UploadPartCopy x2
        assert_upload_part_copy(
            server.requests[4],
            Bucket=self.TARGET_BUCKET,
            Key="key",
            UploadId="upload_id",
        )
        assert server.requests[4].headers.get("host") == self.TARGET_HOST
        assert_upload_part_copy(
            server.requests[5],
            Bucket=self.TARGET_BUCKET,
            Key="key",
            UploadId="upload_id",
        )
        assert server.requests[5].headers.get("host") == self.TARGET_HOST
        # Target region: CompleteMultipartUpload
        assert_complete_multipart_upload(
            server.requests[6],
            Bucket=self.TARGET_BUCKET,
            Key="key",
            UploadId="upload_id",
        )
        assert server.requests[6].headers.get("host") == self.TARGET_HOST


@pytest.mark.asyncio
class TestCpRecursiveCaseConflict:
    """Tests for cp --recursive case conflict handling."""

    async def test_ignore_by_default(self, aws_cli, tmp_path):
        """cp --recursive downloads case-conflicting keys without error by default."""
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
                                    "Size": 100,
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                }
                            ],
                        )
                    ),
                    get_object_response(b"foo"),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "cp", "s3://bucket", str(tmp_path), "--recursive"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_list_objects_v2(server.requests[0], Bucket="bucket")
        assert_get_object(server.requests[1], Bucket="bucket", Key="A.txt")
        # No warnings in stderr
        assert not stderr.decode().strip()


@pytest.mark.asyncio
class TestS3ExpressCpRecursive:
    """Tests for cp --recursive with S3 Express directory buckets and --case-conflict."""

    async def test_s3_express_error_raises_exception(self, aws_cli, tmp_path):
        """--case-conflict error is not valid for S3 Express directory buckets."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket--usw2-az1--x-s3",
                    str(tmp_path),
                    "--recursive",
                    "--case-conflict",
                    "error",
                ],
                cli_env(proxy),
            )

        assert rc == 252
        assert "`error` is not a valid value" in stderr.decode()

    async def test_s3_express_skip_raises_exception(self, aws_cli, tmp_path):
        """--case-conflict skip is not valid for S3 Express directory buckets."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket--usw2-az1--x-s3",
                    str(tmp_path),
                    "--recursive",
                    "--case-conflict",
                    "skip",
                ],
                cli_env(proxy),
            )

        assert rc == 252
        assert "`skip` is not a valid value" in stderr.decode()

    @pytest.mark.skip(
        reason="S3 Express CreateSession race condition; fix pending in open PR"
    )
    async def test_s3_express_warn_emits_warning(self, aws_cli, tmp_path):
        """--case-conflict warn on S3 Express emits warning for case conflicts."""
        async with mock_server(on_headers_received=handle_expect_header) as (
            server,
            proxy,
        ):
            setup_responses(
                server,
                [
                    # CreateSession for the source/list client
                    create_session_response(),
                    xml_response(
                        list_objects_xml(
                            contents=[
                                {
                                    "Key": "a.txt",
                                    "Size": 100,
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                },
                                {
                                    "Key": "A.txt",
                                    "Size": 100,
                                    "LastModified": "2023-01-01T00:00:00.000Z",
                                },
                            ],
                        )
                    ),
                    # CreateSession for the transfer/download client
                    create_session_response(),
                    head_object_response(),
                    get_object_response(b"foo"),
                    head_object_response(),
                    get_object_response(b"bar"),
                ],
            )
            stdout, stderr, rc = await run_cli(
                aws_cli,
                [
                    "s3",
                    "cp",
                    "s3://bucket--usw2-az1--x-s3",
                    str(tmp_path),
                    "--recursive",
                    "--case-conflict",
                    "warn",
                ],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert "warning: Recursive copies/moves" in stderr.decode()


@pytest.mark.asyncio
async def test_upload_key_with_spaces(aws_cli, tmp_path):
    """cp uploads a file whose S3 key contains spaces."""
    src = tmp_path / "my file.txt"
    src.write_text("content")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(src), "s3://bucket/my file.txt"],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    # Space must be percent-encoded as %20, not + or literal space
    assert server.requests[0].effective_path == "/my%20file.txt"


@pytest.mark.asyncio
async def test_download_unicode_key_from_s3(aws_cli, tmp_path):
    """cp --recursive downloads an object with a Unicode key."""
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
                                "Key": "données.txt",
                                "Size": 5,
                                "LastModified": "2023-01-01T00:00:00Z",
                            }
                        ]
                    )
                ),
                get_object_response(b"hello"),
            ],
        )
        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", "s3://bucket/", str(tmp_path), "--recursive"],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 2, format_requests(server)
    assert (tmp_path / "données.txt").exists()


@pytest.mark.asyncio
async def test_upload_file_with_unicode_local_name(aws_cli, tmp_path):
    """cp uploads a local file with a Unicode filename."""
    src = tmp_path / "données.txt"
    src.write_text("content")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(src), "s3://bucket/"],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    # Unicode filename is percent-encoded as UTF-8 on the wire
    assert server.requests[0].effective_path == "/donn%C3%A9es.txt"


@pytest.mark.asyncio
async def test_user_agent_contains_cli_version(aws_cli, tmp_path):
    """Requests include a User-Agent with aws-cli version info."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(src), "s3://bucket/foo.txt"],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    ua = server.requests[0].headers.get("user-agent")
    assert ua is not None, "User-Agent header missing"
    assert "aws-cli/" in ua, f"Expected 'aws-cli/' in User-Agent: {ua}"


@pytest.mark.asyncio
async def test_user_agent_contains_command(aws_cli, tmp_path):
    """User-Agent includes the command being run (e.g. s3.cp)."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(src), "s3://bucket/foo.txt"],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    ua = server.requests[0].headers.get("user-agent")
    assert "s3.cp" in ua, f"Expected 's3.cp' in User-Agent: {ua}"


@pytest.mark.asyncio
async def test_acl_private(aws_cli, tmp_path):
    """cp --acl private sends x-amz-acl: private."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(src), "s3://bucket/foo.txt", "--acl", "private"],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0], Bucket="bucket", Key="foo.txt", ACL="private"
    )


@pytest.mark.asyncio
async def test_acl_public_read(aws_cli, tmp_path):
    """cp --acl public-read sends x-amz-acl: public-read."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(src),
                "s3://bucket/foo.txt",
                "--acl",
                "public-read",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0], Bucket="bucket", Key="foo.txt", ACL="public-read"
    )


@pytest.mark.asyncio
async def test_acl_bucket_owner_full_control(aws_cli, tmp_path):
    """cp --acl bucket-owner-full-control sends the correct header."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(src),
                "s3://bucket/foo.txt",
                "--acl",
                "bucket-owner-full-control",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="foo.txt",
        ACL="bucket-owner-full-control",
    )


@pytest.mark.asyncio
async def test_content_type_override(aws_cli, tmp_path):
    """cp --content-type overrides the guessed MIME type."""
    src = tmp_path / "data.bin"
    src.write_bytes(b"\x00\x01\x02")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(src),
                "s3://bucket/data.bin",
                "--content-type",
                "application/octet-stream",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="data.bin",
        ContentType="application/octet-stream",
    )


@pytest.mark.asyncio
async def test_content_type_html(aws_cli, tmp_path):
    """cp --content-type text/html sends the correct Content-Type."""
    src = tmp_path / "page.html"
    src.write_text("<html></html>")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(src),
                "s3://bucket/page.html",
                "--content-type",
                "text/html",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="page.html",
        ContentType="text/html",
    )


@pytest.mark.asyncio
async def test_content_disposition(aws_cli, tmp_path):
    """cp --content-disposition sends the Content-Disposition header."""
    src = tmp_path / "report.pdf"
    src.write_bytes(b"%PDF-1.4")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(src),
                "s3://bucket/report.pdf",
                "--content-disposition",
                "attachment; filename=\"report.pdf\"",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="report.pdf",
        ContentDisposition="attachment; filename=\"report.pdf\"",
    )


@pytest.mark.skip(
    reason="localstub 0.0.3 decodes non-ASCII header bytes; needs wire-level access"
)
@pytest.mark.asyncio
async def test_content_disposition_non_ascii(aws_cli, tmp_path):
    """cp --content-disposition with non-ASCII character (×) sends UTF-8 bytes."""
    src = tmp_path / "photo.jpg"
    src.write_bytes(b"\xff\xd8\xff")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(src),
                "s3://bucket/photo.jpg",
                "--content-disposition",
                'inline; filename="500\u00d7500.jpg"',
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    req = server.requests[0]
    # The × character (U+00D7) is sent as UTF-8 bytes on the wire
    cd = (
        req.headers.get("Content-Disposition")
        or req.headers.get("content-disposition")
    )
    assert cd is not None, "Content-Disposition header missing"
    assert "500\u00d7500.jpg" in cd, (
        f"Expected \u00d7 in Content-Disposition, got {cd!r}"
    )


@pytest.mark.asyncio
async def test_content_encoding(aws_cli, tmp_path):
    """cp --content-encoding sends the Content-Encoding header."""
    src = tmp_path / "data.gz"
    src.write_bytes(b"\x1f\x8b\x08")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(src),
                "s3://bucket/data.gz",
                "--content-encoding",
                "gzip",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    # Content-Encoding on the wire combines user value with aws-chunked
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="data.gz",
        ContentEncoding="gzip,aws-chunked",
    )


@pytest.mark.asyncio
async def test_content_language(aws_cli, tmp_path):
    """cp --content-language sends the Content-Language header."""
    src = tmp_path / "doc.txt"
    src.write_text("bonjour")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(src),
                "s3://bucket/doc.txt",
                "--content-language",
                "fr",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="doc.txt",
        ContentLanguage="fr",
    )


@pytest.mark.asyncio
async def test_cache_control(aws_cli, tmp_path):
    """cp --cache-control sends the Cache-Control header."""
    src = tmp_path / "index.html"
    src.write_text("<html></html>")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(src),
                "s3://bucket/index.html",
                "--cache-control",
                "max-age=3600, public",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="index.html",
        CacheControl="max-age=3600, public",
    )


@pytest.mark.asyncio
async def test_expires(aws_cli, tmp_path):
    """cp --expires sends the Expires header."""
    src = tmp_path / "temp.txt"
    src.write_text("temporary")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(src),
                "s3://bucket/temp.txt",
                "--expires",
                "2030-01-01T00:00:00Z",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="temp.txt",
        Expires="Tue, 01 Jan 2030 00:00:00 GMT",
    )


@pytest.mark.asyncio
async def test_metadata_single_key(aws_cli, tmp_path):
    """cp --metadata sends x-amz-meta-* headers."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(src),
                "s3://bucket/foo.txt",
                "--metadata",
                "author=jsmith",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="foo.txt",
        Metadata={"author": "jsmith"},
    )


@pytest.mark.asyncio
async def test_metadata_multiple_keys(aws_cli, tmp_path):
    """cp --metadata with multiple keys sends all x-amz-meta-* headers."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(src),
                "s3://bucket/foo.txt",
                "--metadata",
                "author=jsmith,project=alpha",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="foo.txt",
        Metadata={"author": "jsmith", "project": "alpha"},
    )


@pytest.mark.asyncio
async def test_metadata_directive_replace(aws_cli, tmp_path):
    """cp s3->s3 --metadata-directive REPLACE sends the directive header."""
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(
            server,
            [
                head_object_response(),
                copy_object_response(),
            ],
        )
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                "s3://src/key.txt",
                "s3://dst/key.txt",
                "--metadata-directive",
                "REPLACE",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 2, format_requests(server)
    assert_copy_object(
        server.requests[1],
        Bucket="dst",
        Key="key.txt",
        MetadataDirective="REPLACE",
    )


@pytest.mark.asyncio
async def test_metadata_directive_copy(aws_cli, tmp_path):
    """cp s3->s3 --metadata-directive COPY sends the directive header."""
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(
            server,
            [
                head_object_response(),
                copy_object_response(),
            ],
        )
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                "s3://src/key.txt",
                "s3://dst/key.txt",
                "--metadata-directive",
                "COPY",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 2, format_requests(server)
    assert_copy_object(
        server.requests[1],
        Bucket="dst",
        Key="key.txt",
        MetadataDirective="COPY",
    )


@pytest.mark.asyncio
async def test_metadata_directive_replace_with_metadata(aws_cli, tmp_path):
    """cp s3->s3 --metadata-directive REPLACE --metadata replaces metadata."""
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(
            server,
            [
                head_object_response(),
                copy_object_response(),
            ],
        )
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                "s3://src/key.txt",
                "s3://dst/key.txt",
                "--metadata-directive",
                "REPLACE",
                "--metadata",
                "env=prod",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 2, format_requests(server)
    assert_copy_object(
        server.requests[1],
        Bucket="dst",
        Key="key.txt",
        MetadataDirective="REPLACE",
        Metadata={"env": "prod"},
    )


@pytest.mark.asyncio
async def test_combined_metadata_params(aws_cli, tmp_path):
    """cp with multiple metadata params sends all headers together."""
    src = tmp_path / "app.js"
    src.write_text("console.log('hi')")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(src),
                "s3://bucket/app.js",
                "--content-type",
                "application/javascript",
                "--cache-control",
                "no-cache",
                "--content-language",
                "en",
                "--metadata",
                "version=1.0",
                "--acl",
                "public-read",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="app.js",
        ContentType="application/javascript",
        CacheControl="no-cache",
        ContentLanguage="en",
        ACL="public-read",
        Metadata={"version": "1.0"},
    )


@pytest.mark.asyncio
async def test_content_type_auto_guessed_from_extension(aws_cli, tmp_path):
    """cp without --content-type guesses MIME type from file extension."""
    src = tmp_path / "page.html"
    src.write_text("<html></html>")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(src), "s3://bucket/page.html"],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="page.html",
        ContentType="text/html",
    )


@pytest.mark.asyncio
async def test_content_type_auto_guessed_json(aws_cli, tmp_path):
    """cp without --content-type guesses application/json for .json files."""
    src = tmp_path / "data.json"
    src.write_text("{}")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(src), "s3://bucket/data.json"],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="data.json",
        ContentType="application/json",
    )


@pytest.mark.asyncio
async def test_metadata_value_with_spaces(aws_cli, tmp_path):
    """cp --metadata with spaces in value sends the full value."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(src),
                "s3://bucket/foo.txt",
                "--metadata",
                "description=hello world",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="foo.txt",
        Metadata={"description": "hello world"},
    )


@pytest.mark.asyncio
async def test_metadata_value_with_equals(aws_cli, tmp_path):
    """cp --metadata with equals in value preserves the full value."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(src),
                "s3://bucket/foo.txt",
                "--metadata",
                "formula=a=b+c",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="foo.txt",
        Metadata={"formula": "a=b+c"},
    )


@pytest.mark.asyncio
async def test_metadata_empty_value(aws_cli, tmp_path):
    """cp --metadata with empty value sends the header with empty value."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(src),
                "s3://bucket/foo.txt",
                "--metadata",
                "tag=",
            ],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="foo.txt",
        Metadata={"tag": ""},
    )


@pytest.mark.asyncio
async def test_expires_numeric_value(aws_cli, tmp_path):
    """cp --expires with a numeric string interprets it as a Unix timestamp."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(src), "s3://bucket/foo.txt", "--expires", "90"],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    # CLI interprets "90" as Unix timestamp (90 seconds since epoch)
    assert_put_object(
        server.requests[0],
        Bucket="bucket",
        Key="foo.txt",
        Expires="Thu, 01 Jan 1970 00:01:30 GMT",
    )


@pytest.mark.asyncio
async def test_download_checksum_mismatch_fails(aws_cli, tmp_path):
    """cp with --checksum-mode ENABLED fails if checksum doesn't match body."""
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(
            server,
            [
                head_object_response(),
                # Body is b"foo" but checksum is wrong
                get_object_response(
                    b"foo", **{"x-amz-checksum-crc32": "AAAAAA=="}
                ),
            ],
        )
        stdout, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
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
async def test_upload_checksum_rejected_by_server(aws_cli, tmp_path):
    """cp upload fails when server rejects with BadDigest."""
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
            ["s3", "cp", str(src), "s3://bucket/key.txt"],
            cli_env(proxy),
        )

    assert rc == 1
    assert len(server.requests) == 1, format_requests(server)
    assert (
        b"The CRC32 you specified did not "
        b"match the calculated checksum." in stderr
    )


@pytest.mark.asyncio
async def test_download_content_length_mismatch_fails(aws_cli, tmp_path):
    """cp download fails when body is shorter than Content-Length header."""
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(
            server,
            [
                head_object_response(content_length=100),
                # Content-Length says 100 but body is only 3 bytes
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
            # HeadObject completes
            await server.next_request()
            # Drop connection after sending the short body so the
            # CLI sees EOF instead of blocking for remaining bytes.
            server.set_transmission_strategy(
                FaultyTransmission([DropConnection(after_bytes=3)])
            )

        (stdout, stderr, rc), _ = await asyncio.gather(
            run_cli(
                aws_cli,
                ["s3", "cp", "s3://bucket/key.txt", str(tmp_path)],
                cli_env(proxy),
            ),
            inject_fault(),
        )

    assert rc == 1
    assert len(server.requests) == 2, format_requests(server)
    assert (
        b"download failed" in stderr
        and b"Connection broken: IncompleteRead" in stderr
    )


@pytest.mark.asyncio
async def test_multipart_upload_part_rejected_by_server(aws_cli, tmp_path):
    """cp multipart upload fails when server rejects a part with BadDigest."""
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
            ["s3", "cp", str(src), "s3://bucket/key.txt"],
            cli_env(proxy),
        )

    assert rc == 1
    assert len(server.requests) == 4, format_requests(server)
    assert (
        b"An error occurred (BadDigest) when "
        b"calling the UploadPart operation" in stderr
    )


@pytest.mark.asyncio
async def test_content_type_not_guessed_on_s3_to_s3_copy(aws_cli, tmp_path):
    """cp s3->s3 without --content-type does NOT guess Content-Type.

    Regression guard for GitHub issue #6078. Content-Type guessing
    only applies to uploads from local disk, not s3-to-s3 copies.
    """
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(
            server,
            [
                head_object_response(),
                copy_object_response(),
            ],
        )
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", "s3://src/page.html", "s3://dst/page.html"],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 2, format_requests(server)
    # CopyObject should NOT have a Content-Type header set by the CLI
    req = server.requests[1]
    ct = req.headers.get("Content-Type") or req.headers.get("content-type")
    # Content-Type should either be absent or not be "text/html"
    # (the CLI should not guess from the key extension on copies)
    assert (
        ct != "text/html"
    ), f"Content-Type should not be guessed on s3-to-s3 copy, got {ct!r}"
