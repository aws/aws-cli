"""Blackbox tests for `aws s3 sync` command."""
from __future__ import annotations

import base64
import os

import pytest
from localstub.handlers import handle_expect_header
from localstub.server import HTTPResponse

from tests.blackbox.s3_assertions import (
    assert_copy_object,
    assert_delete_object,
    assert_get_object,
    assert_get_object_tagging,
    assert_head_object,
    assert_list_objects_v2,
    assert_put_object,
    assert_put_object_tagging,
    assert_upload_part_copy,
    assert_complete_multipart_upload,
    assert_create_multipart_upload,
)
from tests.blackbox.utils import (
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
    mock_server,
    put_object_response,
    put_object_tagging_response,
    run_cli,
    setup_responses,
    upload_part_copy_response,
    xml_response,
)


def _b64(value: str) -> str:
    """Base64-encode a string, as the CLI does for SSE-C keys on the wire."""
    return base64.b64encode(value.encode()).decode()


def _list_response(keys, **overrides):
    """Build a ListObjectsV2 XML response with the given keys."""
    contents = []
    for k in keys:
        entry = {
            "Key": k,
            "Size": overrides.get("Size", 100),
            "LastModified": "2014-01-09T20:45:49.000Z",
            "ETag": overrides.get("ETag", '"c8afdb36c52cf4727836669019e69222"'),
        }
        if "StorageClass" in overrides:
            entry["StorageClass"] = overrides["StorageClass"]
        contents.append(entry)
    return xml_response(list_objects_xml(contents=contents if keys else None))


def _empty_list_response():
    return xml_response(list_objects_xml())


@pytest.mark.asyncio
class TestSyncCommand:
    async def test_website_redirect_ignore_paramfile(self, aws_cli, tmp_path):
        """sync local s3:// --website-redirect uses the URL value."""
        src = tmp_path / "foo.txt"
        src.write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _empty_list_response(),
                put_object_response(),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", str(tmp_path), "s3://bucket/key.txt",
                 "--website-redirect", "http://someserver"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_list_objects_v2(server.requests[0], Bucket="bucket")
        assert_put_object(server.requests[1], Bucket="bucket", Key="key.txt/foo.txt",
                          WebsiteRedirectLocation="http://someserver")

    async def test_no_recursive_option(self, aws_cli, tmp_path):
        """sync does not accept --recursive."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", ".", "s3://mybucket", "--recursive"],
                cli_env(proxy),
            )

        assert rc == 252

    async def test_sync_from_non_existent_directory(self, aws_cli, tmp_path):
        """sync from non-existent local dir fails."""
        fakedir = str(tmp_path / "fakedir")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [_empty_list_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", fakedir, "s3://bucket/"],
                cli_env(proxy),
            )

        assert rc == 255
        assert b"does not exist" in stderr

    async def test_sync_to_non_existent_directory(self, aws_cli, tmp_path):
        """sync s3->local creates the target directory."""
        target = tmp_path / "fakedir"
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _list_response(["foo.txt"]),
                get_object_response(b"foo"),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket/", str(target)],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert (target / "foo.txt").exists()

    async def test_dryrun_sync(self, aws_cli, tmp_path):
        """sync --dryrun only lists, does not transfer."""
        src = tmp_path / "file.txt"
        src.write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [_empty_list_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", str(tmp_path), "s3://bucket/", "--dryrun"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_list_objects_v2(server.requests[0], Bucket="bucket")
        assert b"(dryrun) upload:" in stdout

    async def test_glacier_sync_with_force_glacier(self, aws_cli, tmp_path):
        """sync s3->local --force-glacier-transfer downloads glacier objects."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _list_response(["foo/bar.txt"], StorageClass="GLACIER"),
                get_object_response(b"foo"),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket/foo", str(tmp_path),
                 "--force-glacier-transfer"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_list_objects_v2(server.requests[0], Bucket="bucket")
        assert_get_object(server.requests[1], Bucket="bucket", Key="foo/bar.txt")

    async def test_handles_glacier_incompatible_operations(self, aws_cli, tmp_path):
        """sync s3->local skips glacier/deep archive objects with warning."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                xml_response(list_objects_xml(contents=[
                    {"Key": "foo", "Size": 100, "LastModified": "2014-01-09T20:45:49.000Z",
                     "StorageClass": "GLACIER"},
                    {"Key": "bar", "Size": 100, "LastModified": "2014-01-09T20:45:49.000Z",
                     "StorageClass": "DEEP_ARCHIVE"},
                ])),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket/", str(tmp_path)],
                cli_env(proxy),
            )

        assert rc == 2
        assert len(server.requests) == 1, format_requests(server)
        assert b"GLACIER" in stderr
        assert b"s3://bucket/foo" in stderr
        assert b"s3://bucket/bar" in stderr

    async def test_turn_off_glacier_warnings(self, aws_cli, tmp_path):
        """sync s3->local --ignore-glacier-warnings suppresses warnings."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                xml_response(list_objects_xml(contents=[
                    {"Key": "foo", "Size": 100, "LastModified": "2014-01-09T20:45:49.000Z",
                     "StorageClass": "GLACIER"},
                    {"Key": "bar", "Size": 100, "LastModified": "2014-01-09T20:45:49.000Z",
                     "StorageClass": "DEEP_ARCHIVE"},
                ])),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket/", str(tmp_path),
                 "--ignore-glacier-warnings"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert stderr.decode().strip() == ""

    async def test_sync_with_delete_on_downloads(self, aws_cli, tmp_path):
        """sync s3->local --delete removes local files not in S3."""
        local_file = tmp_path / "foo.txt"
        local_file.write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [_empty_list_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket", str(tmp_path), "--delete"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_list_objects_v2(server.requests[0], Bucket="bucket")
        assert not local_file.exists()

    async def test_request_payer(self, aws_cli, tmp_path):
        """sync s3->s3 --request-payer sends RequestPayer on all ops."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _list_response(["mykey"]),
                _empty_list_response(),
                copy_object_response(),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://sourcebucket/", "s3://mybucket",
                 "--request-payer"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)
        assert_list_objects_v2(server.requests[0], Bucket="sourcebucket",
                              RequestPayer="requester")
        assert_list_objects_v2(server.requests[1], Bucket="mybucket",
                              RequestPayer="requester")
        assert_copy_object(server.requests[2], Bucket="mybucket", Key="mykey",
                           RequestPayer="requester")

    async def test_request_payer_with_deletes(self, aws_cli, tmp_path):
        """sync s3->s3 --request-payer --delete sends RequestPayer on delete."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _empty_list_response(),
                _list_response(["key-to-delete"]),
                delete_response(),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://sourcebucket/", "s3://mybucket",
                 "--request-payer", "--delete"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)
        assert_list_objects_v2(server.requests[0], Bucket="sourcebucket",
                              RequestPayer="requester")
        assert_list_objects_v2(server.requests[1], Bucket="mybucket",
                              RequestPayer="requester")
        assert_delete_object(server.requests[2], Bucket="mybucket", Key="key-to-delete",
                             RequestPayer="requester")

    async def test_s3s3_sync_with_destination_sse_c(self, aws_cli, tmp_path):
        """sync s3->s3 --sse-c sends SSE-C headers on CopyObject."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _list_response(["mykey"]),
                _empty_list_response(),
                copy_object_response(),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://sourcebucket/", "s3://mybucket",
                 "--sse-c", "AES256", "--sse-c-key", "destination-key"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)
        # SSE-C key is base64-encoded on the wire
        assert_copy_object(server.requests[2], Bucket="mybucket", Key="mykey",
                           SSECustomerAlgorithm="AES256",
                           SSECustomerKey=_b64("destination-key"))

    async def test_s3s3_sync_with_different_sse_c_keys(self, aws_cli, tmp_path):
        """sync s3->s3 with both source and destination SSE-C keys."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _list_response(["mykey"]),
                _empty_list_response(),
                copy_object_response(),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://sourcebucket/", "s3://mybucket",
                 "--sse-c-copy-source", "AES256",
                 "--sse-c-copy-source-key", "source-key",
                 "--sse-c", "AES256", "--sse-c-key", "destination-key"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)
        # SSE-C keys are base64-encoded on the wire
        assert_copy_object(server.requests[2], Bucket="mybucket", Key="mykey",
                           SSECustomerAlgorithm="AES256",
                           SSECustomerKey=_b64("destination-key"),
                           CopySourceSSECustomerAlgorithm="AES256",
                           CopySourceSSECustomerKey=_b64("source-key"))

    async def test_upload_with_checksum_algorithm_crc32(self, aws_cli, tmp_path):
        """sync local->s3 --checksum-algorithm CRC32 sends the algorithm."""
        (tmp_path / "foo.txt").write_text("contents")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [_empty_list_response(), put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", str(tmp_path), "s3://bucket/",
                 "--checksum-algorithm", "CRC32"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert_put_object(server.requests[1], Bucket="bucket", Key="foo.txt",
                          ChecksumAlgorithm="CRC32")

    async def test_upload_with_checksum_algorithm_sha256(self, aws_cli, tmp_path):
        """sync local->s3 --checksum-algorithm SHA256."""
        (tmp_path / "foo.txt").write_text("contents")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [_empty_list_response(), put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", str(tmp_path), "s3://bucket/",
                 "--checksum-algorithm", "SHA256"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert_put_object(server.requests[1], Bucket="bucket", Key="foo.txt",
                          ChecksumAlgorithm="SHA256")

    async def test_upload_with_checksum_algorithm_sha1(self, aws_cli, tmp_path):
        """sync local->s3 --checksum-algorithm SHA1."""
        (tmp_path / "foo.txt").write_text("contents")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [_empty_list_response(), put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", str(tmp_path), "s3://bucket/",
                 "--checksum-algorithm", "SHA1"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert_put_object(server.requests[1], Bucket="bucket", Key="foo.txt",
                          ChecksumAlgorithm="SHA1")

    async def test_download_with_checksum_mode_enabled(self, aws_cli, tmp_path):
        """sync s3->local --checksum-mode ENABLED sends ChecksumMode on GetObject."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _list_response(["foo.txt"]),
                get_object_response(b"foo", **{"x-amz-checksum-crc32": "jHNlIQ=="}),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket/foo", str(tmp_path),
                 "--checksum-mode", "ENABLED"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert_get_object(server.requests[1], Bucket="bucket", Key="foo.txt",
                          ChecksumMode="ENABLED")

    async def test_sync_upload_no_overwrite_file_not_at_destination(self, aws_cli, tmp_path):
        """sync local->s3 --no-overwrite uploads files not at destination."""
        (tmp_path / "new_file.txt").write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _list_response(["file.txt"]),
                put_object_response(),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", str(tmp_path), "s3://bucket", "--no-overwrite"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_list_objects_v2(server.requests[0], Bucket="bucket")
        assert_put_object(server.requests[1], Bucket="bucket", Key="new_file.txt")

    async def test_sync_upload_no_overwrite_file_exists_at_destination(self, aws_cli, tmp_path):
        """sync local->s3 --no-overwrite skips files already at destination."""
        (tmp_path / "new_file.txt").write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [_list_response(["new_file.txt"])])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", str(tmp_path), "s3://bucket", "--no-overwrite"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)
        assert_list_objects_v2(server.requests[0], Bucket="bucket")

    async def test_sync_download_no_overwrite_file_not_at_destination(self, aws_cli, tmp_path):
        """sync s3->local --no-overwrite downloads files not present locally."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _list_response(["new_file.txt"]),
                get_object_response(b"foo"),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket/", str(tmp_path), "--no-overwrite"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert (tmp_path / "new_file.txt").exists()

    async def test_sync_download_no_overwrite_file_exists_at_destination(self, aws_cli, tmp_path):
        """sync s3->local --no-overwrite skips files already present locally."""
        (tmp_path / "file.txt").write_text("My content")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [_list_response(["file.txt"])])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket/", str(tmp_path), "--no-overwrite"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 1, format_requests(server)

    async def test_sync_copy_no_overwrite_file_not_at_destination(self, aws_cli, tmp_path):
        """sync s3->s3 --no-overwrite copies files not at destination."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _list_response(["new_file.txt"]),
                _list_response(["file1.txt"]),
                copy_object_response(),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket/", "s3://bucket2/", "--no-overwrite"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)
        assert_copy_object(server.requests[2], Bucket="bucket2", Key="new_file.txt")

    async def test_sync_copy_no_overwrite_file_exists_at_destination(self, aws_cli, tmp_path):
        """sync s3->s3 --no-overwrite skips files already at destination."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _list_response(["new_file.txt"]),
                _list_response(["new_file.txt", "file1.txt"]),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket/", "s3://bucket2/", "--no-overwrite"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)

    async def test_with_accesspoint_arn(self, aws_cli, tmp_path):
        """sync s3://<arn>/ local downloads from access point."""
        arn = "arn:aws:s3:us-west-2:123456789012:accesspoint/endpoint"
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _list_response(["mykey"]),
                get_object_response(b"foo"),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", f"s3://{arn}", str(tmp_path)],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_list_objects_v2(server.requests[0], Bucket=arn)
        assert_get_object(server.requests[1], Bucket=arn, Key="mykey")

    async def test_upload_sync(self, aws_cli, tmp_path):
        """sync local->s3 uploads new files."""
        (tmp_path / "myfile").write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [_empty_list_response(), put_object_response()])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", str(tmp_path), "s3://bucket/"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_list_objects_v2(server.requests[0], Bucket="bucket")
        assert_put_object(server.requests[1], Bucket="bucket", Key="myfile")

    async def test_download_sync(self, aws_cli, tmp_path):
        """sync s3->local downloads new files."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _list_response(["key"]),
                get_object_response(b"content"),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket/", str(tmp_path)],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 2, format_requests(server)
        assert_list_objects_v2(server.requests[0], Bucket="bucket")
        assert_get_object(server.requests[1], Bucket="bucket", Key="key")
        assert (tmp_path / "key").exists()

    async def test_upload_sync_with_delete(self, aws_cli, tmp_path):
        """sync local->s3 --delete uploads new files and deletes remote extras."""
        (tmp_path / "a-file").write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _list_response(["delete-this"]),
                put_object_response(),
                delete_response(),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", str(tmp_path), "s3://bucket/", "--delete"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)
        assert_list_objects_v2(server.requests[0], Bucket="bucket")
        # Upload and delete are submitted concurrently; order is not guaranteed
        non_list = server.requests[1:]
        put_reqs = [r for r in non_list if r.method == "PUT"]
        del_reqs = [r for r in non_list if r.method == "DELETE"]
        assert len(put_reqs) == 1, format_requests(server)
        assert len(del_reqs) == 1, format_requests(server)
        assert_put_object(put_reqs[0], Bucket="bucket", Key="a-file")
        assert_delete_object(del_reqs[0], Bucket="bucket", Key="delete-this")

    async def test_download_sync_with_delete(self, aws_cli, tmp_path):
        """sync s3->local --delete downloads files and deletes local extras."""
        (tmp_path / "delete-this").write_text("content")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _list_response(["key"]),
                get_object_response(b"content"),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket/", str(tmp_path), "--delete"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert_get_object(server.requests[1], Bucket="bucket", Key="key")
        assert not (tmp_path / "delete-this").exists()

    async def test_copy_sync(self, aws_cli, tmp_path):
        """sync s3->s3 copies objects."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _list_response(["key"]),
                _empty_list_response(),
                copy_object_response(),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket/", "s3://otherbucket/"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)
        assert_copy_object(server.requests[2], Bucket="otherbucket", Key="key")

    async def test_respects_source_region(self, aws_cli, tmp_path):
        """sync s3->s3 --source-region routes list to source region."""
        source_host = "sourcebucket.s3.af-south-1.amazonaws.com"
        target_host = "bucket.s3.us-east-1.amazonaws.com"
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                _list_response(["key"]),
                _empty_list_response(),
                copy_object_response(),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://sourcebucket/", "s3://bucket/",
                 "--region", "us-east-1", "--source-region", "af-south-1"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert len(server.requests) == 3, format_requests(server)
        assert server.requests[0].headers.get("host") == source_host
        assert server.requests[1].headers.get("host") == target_host
        assert server.requests[2].headers.get("host") == target_host


@pytest.mark.asyncio
class TestSyncCommandWithS3Express:
    async def test_incompatible_with_sync_upload(self, aws_cli, tmp_path):
        """sync local->s3 with directory bucket is rejected."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", str(tmp_path),
                 "s3://testdirectorybucket--usw2-az1--x-s3/"],
                cli_env(proxy),
            )

        assert rc == 252
        assert b"Cannot use sync command with a directory bucket" in stderr

    async def test_incompatible_with_sync_download(self, aws_cli, tmp_path):
        """sync s3->local with directory bucket is rejected."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync",
                 "s3://testdirectorybucket--usw2-az1--x-s3/",
                 str(tmp_path)],
                cli_env(proxy),
            )

        assert rc == 252
        assert b"Cannot use sync command with a directory bucket" in stderr

    async def test_incompatible_with_sync_copy(self, aws_cli, tmp_path):
        """sync s3->s3 with directory bucket as destination is rejected."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket/",
                 "s3://testdirectorybucket--usw2-az1--x-s3/"],
                cli_env(proxy),
            )

        assert rc == 252
        assert b"Cannot use sync command with a directory bucket" in stderr

    async def test_incompatible_with_sync_with_delete(self, aws_cli, tmp_path):
        """sync s3->s3 --delete with directory bucket is rejected."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket/",
                 "s3://testdirectorybucket--usw2-az1--x-s3/", "--delete"],
                cli_env(proxy),
            )

        assert rc == 252
        assert b"Cannot use sync command with a directory bucket" in stderr


def _is_case_insensitive() -> bool:
    """Check if the filesystem is case-insensitive."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        upper = os.path.join(d, "A")
        open(upper, "w").close()
        return os.path.exists(os.path.join(d, "a"))


@pytest.mark.asyncio
class TestSyncCaseConflict:
    @pytest.mark.skipif(
        not _is_case_insensitive(),
        reason="Requires case-insensitive filesystem",
    )
    async def test_error_with_existing_file(self, aws_cli, tmp_path):
        """sync s3->local --case-conflict error fails on case conflict with existing file."""
        (tmp_path / "a.txt").write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                xml_response(list_objects_xml(
                    contents=[{"Key": "A.txt", "Size": 100,
                               "LastModified": "2023-01-01T00:00:00Z"}],
                )),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket", str(tmp_path),
                 "--case-conflict", "error"],
                cli_env(proxy),
            )

        assert rc == 1
        assert b"Failed to download bucket/A.txt" in stderr

    async def test_error_with_case_conflicts_in_s3(self, aws_cli, tmp_path):
        """sync s3->local --case-conflict error fails on conflicting keys in S3."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                xml_response(list_objects_xml(
                    contents=[
                        {"Key": "A.txt", "Size": 100, "LastModified": "2023-01-01T00:00:00Z"},
                        {"Key": "a.txt", "Size": 100, "LastModified": "2023-01-01T00:00:00Z"},
                    ],
                )),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket", str(tmp_path),
                 "--case-conflict", "error"],
                cli_env(proxy),
            )

        assert rc == 1
        assert b"Failed to download bucket/a.txt" in stderr

    @pytest.mark.skipif(
        not _is_case_insensitive(),
        reason="Requires case-insensitive filesystem",
    )
    async def test_warn_with_existing_file(self, aws_cli, tmp_path):
        """sync s3->local --case-conflict warn warns on conflict with existing file."""
        (tmp_path / "a.txt").write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                xml_response(list_objects_xml(
                    contents=[{"Key": "A.txt", "Size": 100,
                               "LastModified": "2023-01-01T00:00:00Z"}],
                )),
                get_object_response(b"foo"),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket", str(tmp_path),
                 "--case-conflict", "warn"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert b"warning: Downloading bucket/A.txt" in stderr

    async def test_warn_with_case_conflicts_in_s3(self, aws_cli, tmp_path):
        """sync s3->local --case-conflict warn warns on conflicting keys."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                xml_response(list_objects_xml(
                    contents=[
                        {"Key": "A.txt", "Size": 100, "LastModified": "2023-01-01T00:00:00Z"},
                        {"Key": "a.txt", "Size": 100, "LastModified": "2023-01-01T00:00:00Z"},
                    ],
                )),
                get_object_response(b"foo"),
                get_object_response(b"bar"),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket", str(tmp_path),
                 "--case-conflict", "warn"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert b"warning: Downloading bucket/a.txt" in stderr

    @pytest.mark.skipif(
        not _is_case_insensitive(),
        reason="Requires case-insensitive filesystem",
    )
    async def test_skip_with_existing_file(self, aws_cli, tmp_path):
        """sync s3->local --case-conflict skip skips conflicting file."""
        (tmp_path / "a.txt").write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                xml_response(list_objects_xml(
                    contents=[{"Key": "A.txt", "Size": 100,
                               "LastModified": "2023-01-01T00:00:00Z"}],
                )),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket", str(tmp_path),
                 "--case-conflict", "skip"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert b"warning: Skipping bucket/A.txt" in stderr

    async def test_skip_with_case_conflicts_in_s3(self, aws_cli, tmp_path):
        """sync s3->local --case-conflict skip skips conflicting keys."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                xml_response(list_objects_xml(
                    contents=[
                        {"Key": "A.txt", "Size": 100, "LastModified": "2023-01-01T00:00:00Z"},
                        {"Key": "a.txt", "Size": 100, "LastModified": "2023-01-01T00:00:00Z"},
                    ],
                )),
                get_object_response(b"foo"),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket", str(tmp_path),
                 "--case-conflict", "skip"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()
        assert b"warning: Skipping bucket/a.txt" in stderr

    @pytest.mark.skipif(
        not _is_case_insensitive(),
        reason="Requires case-insensitive filesystem",
    )
    async def test_ignore_with_existing_file(self, aws_cli, tmp_path):
        """sync s3->local --case-conflict ignore proceeds without warning."""
        (tmp_path / "a.txt").write_text("mycontent")
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                xml_response(list_objects_xml(
                    contents=[{"Key": "A.txt", "Size": 100,
                               "LastModified": "2023-01-01T00:00:00Z"}],
                )),
                get_object_response(b"foo"),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket", str(tmp_path),
                 "--case-conflict", "ignore"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()

    async def test_ignore_with_case_conflicts_in_s3(self, aws_cli, tmp_path):
        """sync s3->local --case-conflict ignore downloads all without warning."""
        async with mock_server(on_headers_received=handle_expect_header) as (server, proxy):
            setup_responses(server, [
                xml_response(list_objects_xml(
                    contents=[
                        {"Key": "A.txt", "Size": 100, "LastModified": "2023-01-01T00:00:00Z"},
                        {"Key": "a.txt", "Size": 100, "LastModified": "2023-01-01T00:00:00Z"},
                    ],
                )),
                get_object_response(b"foo"),
                get_object_response(b"bar"),
            ])
            stdout, stderr, rc = await run_cli(
                aws_cli,
                ["s3", "sync", "s3://bucket", str(tmp_path),
                 "--case-conflict", "ignore"],
                cli_env(proxy),
            )

        assert rc == 0, stderr.decode()



@pytest.mark.asyncio
async def test_download_url_encoded_key_from_list(aws_cli, tmp_path):
    """sync downloads objects whose keys contain spaces from ListObjectsV2."""
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
                                "Key": "my file.txt",
                                "Size": 3,
                                "LastModified": "2023-01-01T00:00:00Z",
                            }
                        ]
                    )
                ),
                get_object_response(b"foo"),
            ],
        )
        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "sync", "s3://bucket/", str(tmp_path)],
            cli_env(proxy),
        )

    assert rc == 0, stderr.decode()
    assert (tmp_path / "my file.txt").exists()
