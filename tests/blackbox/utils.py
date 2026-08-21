"""Shared test utilities for blackbox tests."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from urllib.parse import parse_qs, urlparse

from localstub.server import AsyncHTTPTestServer, HTTPResponse
from localstub.tlsproxy import AsyncTLSInterceptProxy


def cli_env(proxy: AsyncTLSInterceptProxy) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", "/tmp"),
        "AWS_ACCESS_KEY_ID": "test",
        "AWS_SECRET_ACCESS_KEY": "test",
        "AWS_REGION": "us-east-1",
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_MAX_ATTEMPTS": "1",
        "AWS_CONFIG_FILE": "",
        "AWS_SHARED_CREDENTIALS_FILE": "",
        "HTTPS_PROXY": proxy.endpoint_url,
        "HTTP_PROXY": proxy.endpoint_url,
        "AWS_CA_BUNDLE": str(proxy.ca.ca_pem_path()),
    }


@asynccontextmanager
async def mock_server(on_headers_received=None):
    """Async context manager that yields (server, proxy) for blackbox tests.

    All CLI traffic must go through this proxy. If the binary under test
    does not respect HTTPS_PROXY, requests will fail to connect (the env
    has no real credentials and NO_PROXY is empty).
    """
    async with (
        AsyncHTTPTestServer(on_headers_received=on_headers_received) as server,
        AsyncTLSInterceptProxy(server=server) as proxy,
    ):
        yield server, proxy


def setup_responses(
    server: AsyncHTTPTestServer, responses: list[HTTPResponse]
) -> None:
    """Configure server to return responses in order."""
    server.set_response_sequence(responses)


def xml_response(xml: str) -> HTTPResponse:
    return HTTPResponse.raw(
        xml.encode(), headers={"Content-Type": "application/xml"}
    )


def format_requests(server: AsyncHTTPTestServer) -> str:
    """Format captured requests for inclusion in assertion messages."""
    lines = [
        f"  [{i}] {r.method} {r.path} Host={r.headers.get('host')}"
        for i, r in enumerate(server.requests)
    ]
    return (
        f"requests({len(server.requests)}):\n" + "\n".join(lines)
        if lines
        else "requests(0): <none>"
    )


def get_query_params(request) -> dict[str, list[str]]:
    """Parse query string params from a recorded request's path."""
    parsed = urlparse(request.path)
    return parse_qs(parsed.query)


async def run_cli(
    aws_cli: str, args: list[str], env: dict, stdin: bytes | None = None
) -> tuple[bytes, bytes, int]:
    proc = await asyncio.create_subprocess_exec(
        aws_cli,
        *args,
        env=env,
        stdin=asyncio.subprocess.PIPE if stdin is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=stdin)
    return stdout, stderr, proc.returncode


def list_objects_xml(
    contents: list[dict] | None = None,
    common_prefixes: list[str] | None = None,
    is_truncated: bool = False,
    next_continuation_token: str | None = None,
    prefix: str | None = None,
) -> str:
    xml = (
        '<?xml version="1.0" ?>'
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
    )
    if prefix is None:
        xml += "<Prefix/>"
    else:
        xml += f"<Prefix>{prefix}</Prefix>"
    if is_truncated:
        xml += "<IsTruncated>true</IsTruncated>"
    if next_continuation_token:
        xml += f"<NextContinuationToken>{next_continuation_token}</NextContinuationToken>"
    if contents:
        for obj in contents:
            xml += "<Contents>"
            xml += f"<Key>{obj['Key']}</Key>"
            xml += f"<Size>{obj['Size']}</Size>"
            xml += f"<LastModified>{obj['LastModified']}</LastModified>"
            xml += f"<ETag>{obj.get('ETag', 'd41d8cd98f00b204e9800998ecf8427e')}</ETag>"
            if "StorageClass" in obj:
                xml += f"<StorageClass>{obj['StorageClass']}</StorageClass>"
            xml += "</Contents>"
    if common_prefixes:
        for prefix in common_prefixes:
            xml += (
                f"<CommonPrefixes><Prefix>{prefix}</Prefix></CommonPrefixes>"
            )
    xml += "</ListBucketResult>"
    return xml


def delete_response() -> HTTPResponse:
    return HTTPResponse.raw(b"", status=204)


def error_response(
    code: str = "InternalError",
    message: str = "Internal Server Error",
    status: int = 500,
) -> HTTPResponse:
    body = (
        '<?xml version="1.0" ?>'
        f"<Error><Code>{code}</Code><Message>{message}</Message></Error>"
    )
    return HTTPResponse.raw(
        body.encode(),
        status=status,
        headers={"Content-Type": "application/xml"},
    )


def create_bucket_response() -> HTTPResponse:
    return HTTPResponse.raw(b"", status=200, headers={"Location": "/bucket"})


def delete_bucket_response() -> HTTPResponse:
    return HTTPResponse.raw(b"", status=204)
