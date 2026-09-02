"""Blackbox tests for S3 configuration options.

These config options affect how the CLI constructs requests on the wire:
endpoint selection, multipart behavior, payload signing, etc.
"""

from __future__ import annotations

import pytest
from localstub.handlers import handle_expect_header
from localstub.server import HTTPResponse

from tests.blackbox.s3_assertions import (
    assert_complete_multipart_upload,
    assert_create_multipart_upload,
    assert_put_object,
    assert_upload_part,
)
from tests.blackbox.utils import (
    cli_env,
    complete_mpu_response,
    create_mpu_response,
    format_requests,
    head_object_response,
    mock_server,
    put_object_response,
    run_cli,
    setup_responses,
    upload_part_response,
)


def _cli_env_with_config(proxy, config_path):
    env = cli_env(proxy)
    env["AWS_CONFIG_FILE"] = config_path
    return env


@pytest.mark.asyncio
async def test_multipart_threshold_single_put_below(
    aws_cli, aws_config, tmp_path
):
    """File below multipart_threshold uses single PutObject."""
    src = tmp_path / "small.bin"
    src.write_bytes(b"x" * (4 * 1024 * 1024))
    config_path = aws_config(
        {"default": {"s3": "\n    multipart_threshold = 5MB"}}
    )
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(src), "s3://bucket/small.bin"],
            _cli_env_with_config(proxy, config_path),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 1, format_requests(server)
    assert_put_object(server.requests[0], Bucket="bucket", Key="small.bin")


@pytest.mark.asyncio
async def test_multipart_threshold_multipart_above(
    aws_cli, aws_config, tmp_path
):
    """File above multipart_threshold uses multipart upload."""
    src = tmp_path / "big.bin"
    src.write_bytes(b"x" * (6 * 1024 * 1024))
    config_path = aws_config(
        {"default": {"s3": "\n    multipart_threshold = 5MB"}}
    )
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(
            server,
            [
                create_mpu_response("upload-id"),
                upload_part_response("etag1"),
                complete_mpu_response(),
            ],
        )
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(src), "s3://bucket/big.bin"],
            _cli_env_with_config(proxy, config_path),
        )

    assert rc == 0, stderr.decode()
    assert len(server.requests) == 3, format_requests(server)
    assert_create_multipart_upload(
        server.requests[0], Bucket="bucket", Key="big.bin"
    )
    assert_upload_part(server.requests[1], Bucket="bucket", Key="big.bin")
    assert_complete_multipart_upload(
        server.requests[2],
        Bucket="bucket",
        Key="big.bin",
        UploadId="upload-id",
    )


@pytest.mark.asyncio
async def test_multipart_chunksize_controls_part_count(
    aws_cli, aws_config, tmp_path
):
    """multipart_chunksize controls the size of each part."""
    src = tmp_path / "big.bin"
    src.write_bytes(b"x" * (12 * 1024 * 1024))
    config_path = aws_config(
        {
            "default": {
                "s3": "\n    multipart_threshold = 5MB\n    multipart_chunksize = 5MB"
            }
        }
    )
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(
            server,
            [
                create_mpu_response("upload-id"),
                upload_part_response("etag1"),
                upload_part_response("etag2"),
                upload_part_response("etag3"),
                complete_mpu_response(),
            ],
        )
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(src), "s3://bucket/big.bin"],
            _cli_env_with_config(proxy, config_path),
        )

    assert rc == 0, stderr.decode()
    assert_create_multipart_upload(
        server.requests[0], Bucket="bucket", Key="big.bin"
    )
    part_reqs = [
        r
        for r in server.requests
        if r.method == "PUT" and "partNumber" in r.path
    ]
    assert len(part_reqs) == 3, format_requests(server)
    assert_complete_multipart_upload(
        server.requests[4],
        Bucket="bucket",
        Key="big.bin",
        UploadId="upload-id",
    )


@pytest.mark.asyncio
async def test_addressing_style_path(aws_cli, aws_config, tmp_path):
    """addressing_style=path puts bucket in the path, not the host."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    config_path = aws_config(
        {"default": {"s3": "\n    addressing_style = path"}}
    )
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(src), "s3://bucket/foo.txt"],
            _cli_env_with_config(proxy, config_path),
        )

    assert rc == 0, stderr.decode()
    req = server.requests[0]
    assert req.headers.get("host") == "s3.us-east-1.amazonaws.com"
    assert req.path.startswith("/bucket/foo.txt")


@pytest.mark.asyncio
async def test_addressing_style_virtual(aws_cli, aws_config, tmp_path):
    """addressing_style=virtual puts bucket in the host."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    config_path = aws_config(
        {"default": {"s3": "\n    addressing_style = virtual"}}
    )
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(src), "s3://bucket/foo.txt"],
            _cli_env_with_config(proxy, config_path),
        )

    assert rc == 0, stderr.decode()
    req = server.requests[0]
    assert "bucket" in req.headers.get("host", "")
    assert req.path == "/foo.txt" or req.path.startswith("/foo.txt")


@pytest.mark.asyncio
async def test_use_accelerate_endpoint(aws_cli, aws_config, tmp_path):
    """use_accelerate_endpoint=true routes to s3-accelerate.amazonaws.com."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    config_path = aws_config(
        {"default": {"s3": "\n    use_accelerate_endpoint = true"}}
    )
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(src), "s3://bucket/foo.txt"],
            _cli_env_with_config(proxy, config_path),
        )

    assert rc == 0, stderr.decode()
    host = server.requests[0].headers.get("host", "")
    assert (
        "s3-accelerate" in host
    ), f"Expected s3-accelerate in host, got {host}"


@pytest.mark.asyncio
async def test_payload_signing_disabled(aws_cli, aws_config, tmp_path):
    """payload_signing_enabled=false sends UNSIGNED-PAYLOAD."""
    config_path = aws_config(
        {"default": {"s3": "\n    payload_signing_enabled = false"}}
    )
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [head_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3api", "head-object", "--bucket", "bucket", "--key", "foo.txt"],
            _cli_env_with_config(proxy, config_path),
        )

    assert rc == 0, stderr.decode()
    sha256 = server.requests[0].headers.get("x-amz-content-sha256")
    assert (
        sha256 == "UNSIGNED-PAYLOAD"
    ), f"Expected UNSIGNED-PAYLOAD, got {sha256}"


@pytest.mark.asyncio
async def test_payload_signing_enabled(aws_cli, aws_config, tmp_path):
    """payload_signing_enabled=true sends the actual SHA256 hash."""
    config_path = aws_config(
        {"default": {"s3": "\n    payload_signing_enabled = true"}}
    )
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [head_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3api", "head-object", "--bucket", "bucket", "--key", "foo.txt"],
            _cli_env_with_config(proxy, config_path),
        )

    assert rc == 0, stderr.decode()
    sha256 = server.requests[0].headers.get("x-amz-content-sha256")
    # SHA256 of empty body
    assert (
        sha256
        == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    ), f"Expected SHA256 of empty body, got {sha256}"


@pytest.mark.asyncio
async def test_use_dualstack_endpoint(aws_cli, aws_config, tmp_path):
    """use_dualstack_endpoint=true routes to dualstack endpoint."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    config_path = aws_config(
        {"default": {"s3": "\n    use_dualstack_endpoint = true"}}
    )
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(src), "s3://bucket/foo.txt"],
            _cli_env_with_config(proxy, config_path),
        )

    assert rc == 0, stderr.decode()
    host = server.requests[0].headers.get("host", "")
    assert "dualstack" in host, f"Expected dualstack in host, got {host}"


@pytest.mark.asyncio
async def test_use_dualstack_endpoint_false(aws_cli, aws_config, tmp_path):
    """use_dualstack_endpoint=false uses the standard endpoint."""
    src = tmp_path / "foo.txt"
    src.write_text("content")
    config_path = aws_config(
        {"default": {"s3": "\n    use_dualstack_endpoint = false"}}
    )
    async with mock_server(on_headers_received=handle_expect_header) as (
        server,
        proxy,
    ):
        setup_responses(server, [put_object_response()])
        _, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(src), "s3://bucket/foo.txt"],
            _cli_env_with_config(proxy, config_path),
        )

    assert rc == 0, stderr.decode()
    host = server.requests[0].headers.get("host", "")
    assert (
        "dualstack" not in host
    ), f"Expected no dualstack in host, got {host}"
