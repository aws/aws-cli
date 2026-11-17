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
        f"  [{i}] {r.method} {r.effective_path} Host={r.headers.get('host')}"
        for i, r in enumerate(server.requests)
    ]
    return (
        f"requests({len(server.requests)}):\n" + "\n".join(lines)
        if lines
        else "requests(0): <none>"
    )


def get_query_params(request) -> dict[str, list[str]]:
    """Parse query string params from a recorded request's path."""
    parsed = urlparse(request.effective_path)
    return parse_qs(parsed.query)


async def run_cli(
    aws_cli: str,
    args: list[str],
    env: dict,
    stdin: bytes | None = None,
    timeout: float = 60,
) -> tuple[bytes, bytes, int]:
    proc = await asyncio.create_subprocess_exec(
        aws_cli,
        *args,
        env=env,
        stdin=asyncio.subprocess.PIPE if stdin is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=stdin), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise AssertionError(
            f"CLI process timed out after {timeout}s. "
            f"Command: {aws_cli} {' '.join(args)}"
        )
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


def put_object_response() -> HTTPResponse:
    return HTTPResponse.raw(
        b"", status=200, headers={"ETag": '"c8afdb36c52cf4727836669019e69222"'}
    )


def head_object_response(
    content_length: int = 100, **extra_headers
) -> HTTPResponse:
    headers = {
        "Content-Length": str(content_length),
        "Last-Modified": "Thu, 01 Jan 1970 00:00:00 GMT",
        "ETag": '"foo-1"',
    }
    headers.update(extra_headers)
    return HTTPResponse.raw(b"", status=200, headers=headers)


def get_object_response(body: bytes = b"foo", **extra_headers) -> HTTPResponse:
    headers = {
        "Content-Length": str(len(body)),
        "ETag": '"foo-1"',
    }
    headers.update(extra_headers)
    return HTTPResponse.raw(body, status=200, headers=headers)


def empty_list_objects_response() -> HTTPResponse:
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        "<Name>bucket</Name><Prefix></Prefix><IsTruncated>false</IsTruncated>"
        "</ListBucketResult>"
    )
    return HTTPResponse.raw(
        body.encode(), status=200, headers={"Content-Type": "application/xml"}
    )


def create_mpu_response(upload_id: str) -> HTTPResponse:
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<InitiateMultipartUploadResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f"<Bucket>bucket</Bucket><Key>key.txt</Key><UploadId>{upload_id}</UploadId>"
        "</InitiateMultipartUploadResult>"
    )
    return HTTPResponse.raw(
        body.encode(), status=200, headers={"Content-Type": "application/xml"}
    )


def upload_part_response(etag: str) -> HTTPResponse:
    return HTTPResponse.raw(b"", status=200, headers={"ETag": f'"{etag}"'})


def complete_mpu_response() -> HTTPResponse:
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CompleteMultipartUploadResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        "<Location>http://bucket.s3.amazonaws.com/key.txt</Location>"
        "<Bucket>bucket</Bucket><Key>key.txt</Key>"
        '<ETag>"etag"</ETag>'
        "</CompleteMultipartUploadResult>"
    )
    return HTTPResponse.raw(
        body.encode(), status=200, headers={"Content-Type": "application/xml"}
    )


def abort_mpu_response() -> HTTPResponse:
    return HTTPResponse.raw(b"", status=204)


def copy_object_response() -> HTTPResponse:
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CopyObjectResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        '<ETag>"etag"</ETag>'
        "<LastModified>2023-01-01T00:00:00.000Z</LastModified>"
        "</CopyObjectResult>"
    )
    return HTTPResponse.raw(
        body.encode(), status=200, headers={"Content-Type": "application/xml"}
    )


def get_object_tagging_response(tags: dict | None = None) -> HTTPResponse:
    tag_xml = ""
    if tags:
        for k, v in tags.items():
            tag_xml += f"<Tag><Key>{k}</Key><Value>{v}</Value></Tag>"
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Tagging xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f"<TagSet>{tag_xml}</TagSet></Tagging>"
    )
    return HTTPResponse.raw(
        body.encode(), status=200, headers={"Content-Type": "application/xml"}
    )


def put_object_tagging_response() -> HTTPResponse:
    return HTTPResponse.raw(b"", status=200)


def upload_part_copy_response() -> HTTPResponse:
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CopyPartResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        '<ETag>"etag"</ETag>'
        "<LastModified>2023-01-01T00:00:00.000Z</LastModified>"
        "</CopyPartResult>"
    )
    return HTTPResponse.raw(
        body.encode(), status=200, headers={"Content-Type": "application/xml"}
    )


def create_session_response() -> HTTPResponse:
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CreateSessionResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        '<Credentials>'
        '<AccessKeyId>ASIATESTSESSIONKEY</AccessKeyId>'
        '<SecretAccessKey>testsessionsecret</SecretAccessKey>'
        '<SessionToken>testsessiontoken</SessionToken>'
        '<Expiration>2099-01-01T00:00:00Z</Expiration>'
        '</Credentials>'
        '</CreateSessionResult>'
    )
    return HTTPResponse.raw(
        body.encode(), status=200, headers={"Content-Type": "application/xml"}
    )


def get_path(request) -> str:
    """Get the path portion without query string."""
    return urlparse(request.effective_path).path


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
