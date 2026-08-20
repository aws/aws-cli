"""Blackbox tests for `aws s3 presign` command.

NOTE: The original tests freeze time to assert exact signature values.
In blackbox mode we cannot control the binary's clock, so we assert URL
structure (hostname, path, query param keys, credential format, expires)
but NOT exact X-Amz-Signature or X-Amz-Date values.
"""

from __future__ import annotations

import os
import re
from urllib.parse import urlsplit

import pytest

from tests.blackbox.utils import run_cli

EXPECTED_SIGV4_KEYS = {
    "X-Amz-Algorithm",
    "X-Amz-Credential",
    "X-Amz-Date",
    "X-Amz-Expires",
    "X-Amz-SignedHeaders",
    "X-Amz-Signature",
}


def presign_env() -> dict[str, str]:
    """Minimal env for presign -- no proxy needed since no HTTP requests are made."""
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", "/tmp"),
        "AWS_ACCESS_KEY_ID": "access_key",
        "AWS_SECRET_ACCESS_KEY": "secret_key",
        "AWS_REGION": "us-east-1",
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_CONFIG_FILE": "",
        "AWS_SHARED_CREDENTIALS_FILE": "",
    }


def parse_presigned_url(url: str) -> dict:
    parts = urlsplit(url)
    query_params = {}
    for part in parts.query.split("&"):
        k, v = part.split("=", 1)
        query_params[k] = v
    return {
        "hostname": parts.netloc,
        "path": parts.path,
        "query_params": query_params,
    }


def assert_sigv4_query_params(
    query_params: dict, expected_expires: str = "3600"
):
    assert set(query_params.keys()) == EXPECTED_SIGV4_KEYS
    assert query_params["X-Amz-Algorithm"] == "AWS4-HMAC-SHA256"
    # Credential format: access_key/YYYYMMDD/region/s3/aws4_request (url-encoded)
    cred = query_params["X-Amz-Credential"]
    assert cred.startswith("access_key%2F")
    assert "%2Fus-east-1%2Fs3%2Faws4_request" in cred
    # Date format: YYYYMMDDTHHMMSSZ
    assert re.match(r"\d{8}T\d{6}Z", query_params["X-Amz-Date"])
    assert query_params["X-Amz-Expires"] == expected_expires
    assert query_params["X-Amz-SignedHeaders"] == "host"


@pytest.mark.asyncio
class TestPresignCommand:
    async def test_generates_a_url(self, aws_cli):
        env = presign_env()
        stdout, stderr, rc = await run_cli(
            aws_cli, ["s3", "presign", "s3://bucket/key"], env
        )
        assert rc == 0, stderr.decode()
        url = stdout.decode().strip()
        parsed = parse_presigned_url(url)
        assert parsed["hostname"] == "bucket.s3.us-east-1.amazonaws.com"
        assert parsed["path"] == "/key"
        assert_sigv4_query_params(parsed["query_params"])

    async def test_handles_non_dns_compatible_buckets(self, aws_cli):
        env = presign_env()
        stdout, stderr, rc = await run_cli(
            aws_cli, ["s3", "presign", "s3://bucket.dots/key"], env
        )
        assert rc == 0, stderr.decode()
        url = stdout.decode().strip()
        parsed = parse_presigned_url(url)
        assert parsed["hostname"] == "s3.us-east-1.amazonaws.com"
        assert parsed["path"] == "/bucket.dots/key"
        assert_sigv4_query_params(parsed["query_params"])

    async def test_handles_expires_in(self, aws_cli):
        env = presign_env()
        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "presign", "s3://bucket/key", "--expires-in", "1000"],
            env,
        )
        assert rc == 0, stderr.decode()
        url = stdout.decode().strip()
        parsed = parse_presigned_url(url)
        assert parsed["hostname"] == "bucket.s3.us-east-1.amazonaws.com"
        assert parsed["path"] == "/key"
        assert_sigv4_query_params(
            parsed["query_params"], expected_expires="1000"
        )

    async def test_handles_sigv4(self, aws_cli, aws_config):
        """sigv4 is the default, so this should produce same structure as test_generates_a_url."""
        config_path = aws_config(
            {"default": {"s3": "\n    signature_version = s3v4"}}
        )
        env = presign_env()
        env["AWS_CONFIG_FILE"] = config_path
        stdout, stderr, rc = await run_cli(
            aws_cli, ["s3", "presign", "s3://bucket/key"], env
        )
        assert rc == 0, stderr.decode()
        url = stdout.decode().strip()
        parsed = parse_presigned_url(url)
        assert parsed["hostname"] == "bucket.s3.us-east-1.amazonaws.com"
        assert parsed["path"] == "/key"
        assert_sigv4_query_params(parsed["query_params"])

    async def test_s3_prefix_not_needed(self, aws_cli):
        env = presign_env()
        stdout, stderr, rc = await run_cli(
            aws_cli, ["s3", "presign", "bucket/key"], env
        )
        assert rc == 0, stderr.decode()
        url = stdout.decode().strip()
        parsed = parse_presigned_url(url)
        assert parsed["hostname"] == "bucket.s3.us-east-1.amazonaws.com"
        assert parsed["path"] == "/key"
        assert_sigv4_query_params(parsed["query_params"])

    async def test_can_support_addressing_mode_path(self, aws_cli, aws_config):
        config_path = aws_config(
            {"default": {"s3": "\n    addressing_style = path"}}
        )
        env = presign_env()
        env["AWS_CONFIG_FILE"] = config_path
        stdout, stderr, rc = await run_cli(
            aws_cli, ["s3", "presign", "s3://bucket/key"], env
        )
        assert rc == 0, stderr.decode()
        url = stdout.decode().strip()
        parsed = parse_presigned_url(url)
        assert parsed["hostname"] == "s3.us-east-1.amazonaws.com"
        assert parsed["path"] == "/bucket/key"
        assert_sigv4_query_params(parsed["query_params"])
