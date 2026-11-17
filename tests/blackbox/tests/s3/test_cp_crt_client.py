"""`s3 cp` on the CRT client (upstream
tests/functional/s3/test_cp_command.py, TestCpWithCRTClient).

Upstream replaces s3transfer's CRT S3Client with a mock and asserts the
requests handed to it and the arguments it was built with. Here the CRT
client sends its requests, and the tests assert what reaches the wire:
each request's operation, host, and path, the bodies uploaded and the
files written, the region each request is signed for, and how the client
connected. The proxy only tunnels CONNECT traffic, which it serves over
TLS, and refuses a plain request, so a request reaching the server for a
named host went over TLS; one reaching the server's own plain-HTTP
address, past the proxy, went without it. The run is upstream's CLIRunner
environment: region us-west-2 and the CRT client, run serially. A command
native supports runs on native by default and on upstream's CRT client on
the Python route.
"""

import re
from collections.abc import AsyncIterator
from typing import Final

import pytest
import pytest_asyncio
from localstub import HTTPResponse

from apihelpers import ApiSession, CommandRun
from s3params import (
    get_object_response,
    head_object_response,
    list_objects_response,
)

pytestmark = pytest.mark.asyncio

REGION: Final = "us-west-2"
HOST: Final = f"bucket.s3.{REGION}.amazonaws.com"
CONTENT: Final = b"mycontent"
# What upstream's mock writes for every download.
DOWNLOAD_CONTENT: Final = b"content"
CREDENTIAL_SCOPE: Final = re.compile(r"Credential=[^/]+/[0-9]+/([^/]+)/s3/")
ETAG: Final = '"foo-1"'

type Sent = tuple[str, str, str]


@pytest_asyncio.fixture
async def crt_api(s3crt: ApiSession) -> AsyncIterator[ApiSession]:
    s3crt.env["AWS_DEFAULT_REGION"] = REGION
    yield s3crt


def sent(run: CommandRun) -> list[Sent]:
    """Each request's operation, host, and path."""
    return [
        (
            call.operation,
            call.request.headers.get("host", ""),
            call.request.effective_path.partition("?")[0],
        )
        for call in run.calls
    ]


def signing_regions(run: CommandRun) -> list[str]:
    regions = []
    for call in run.calls:
        match = CREDENTIAL_SCOPE.search(
            call.request.headers.get("authorization", "")
        )
        regions.append(match[1] if match else "")
    return regions


def bodies(run: CommandRun, operation: str) -> list[bytes]:
    return [
        call.params["Body"]
        for call in run.calls
        if call.operation == operation
    ]


def whole_object() -> HTTPResponse:
    """The download's object, answering the GET of the CRT client's first
    part, which covers it, as S3 does: with the object's range and size.
    The CRT client sends those of several objects in no fixed order."""
    return HTTPResponse.raw(
        DOWNLOAD_CONTENT,
        status=206,
        headers={
            "ETag": ETAG,
            "Content-Range": (
                f"bytes 0-{len(DOWNLOAD_CONTENT) - 1}/{len(DOWNLOAD_CONTENT)}"
            ),
            "Last-Modified": "Thu, 11 Feb 2021 04:24:23 GMT",
        },
    )


def write_file(api: ApiSession, name: str) -> str:
    path = api.cwd / name
    path.write_bytes(CONTENT)
    return str(path)


async def test_upload_using_crt_client(crt_api: ApiSession) -> None:
    filename = write_file(crt_api, "myfile")
    run = await crt_api.run(["s3", "cp", filename, "s3://bucket/key"])
    assert sent(run) == [("PutObject", HOST, "/key")], run.describe()
    assert bodies(run, "PutObject") == [CONTENT], run.describe()


async def test_recursive_upload_using_crt_client(crt_api: ApiSession) -> None:
    write_file(crt_api, "myfile1")
    write_file(crt_api, "myfile2")
    run = await crt_api.run(
        ["s3", "cp", str(crt_api.cwd), "s3://bucket/", "--recursive"]
    )
    # The CRT client runs the two uploads concurrently.
    assert sorted(sent(run)) == [
        ("PutObject", HOST, "/myfile1"),
        ("PutObject", HOST, "/myfile2"),
    ], run.describe()
    assert bodies(run, "PutObject") == [CONTENT, CONTENT], run.describe()


async def test_download_using_crt_client(crt_api: ApiSession) -> None:
    filename = crt_api.cwd / "myfile"
    head = head_object_response(ContentLength=len(DOWNLOAD_CONTENT))
    run = await crt_api.run(
        ["s3", "cp", "s3://bucket/key", str(filename)],
        replies=[head, get_object_response(DOWNLOAD_CONTENT)],
    )
    # The command's HEAD, then the CRT client's GET. The HEAD reported no
    # full-object checksum, so the CRT client sends no HEAD of its own.
    assert sent(run) == [
        ("HeadObject", HOST, "/key"),
        ("GetObject", HOST, "/key"),
    ], run.describe()
    assert filename.read_bytes() == DOWNLOAD_CONTENT
    assert sorted(path.name for path in crt_api.cwd.iterdir()) == ["myfile"]


async def test_recursive_download_using_crt_client(
    crt_api: ApiSession,
) -> None:
    run = await crt_api.run(
        ["s3", "cp", "s3://bucket/", str(crt_api.cwd), "--recursive"],
        replies=[
            list_objects_response(
                ["key1", "key2"], Size=len(DOWNLOAD_CONTENT)
            ),
            *[whole_object() for _ in range(2)],
        ],
    )
    # The listing reported no checksums, so the CRT client sends no HEAD.
    first, *transfers = sent(run)
    assert first == ("ListObjectsV2", HOST, "/"), run.describe()
    assert sorted(transfers) == [
        ("GetObject", HOST, "/key1"),
        ("GetObject", HOST, "/key2"),
    ], run.describe()
    assert {
        path.name: path.read_bytes() for path in crt_api.cwd.iterdir()
    } == {"key1": DOWNLOAD_CONTENT, "key2": DOWNLOAD_CONTENT}


async def test_does_not_use_crt_client_for_copies(
    crt_api: ApiSession,
) -> None:
    run = await crt_api.run(
        "s3 cp s3://bucket/key s3://otherbucket/",
        replies=[head_object_response(), {}],
    )
    assert sent(run) == [
        ("HeadObject", HOST, "/key"),
        ("CopyObject", f"otherbucket.s3.{REGION}.amazonaws.com", "/key"),
    ], run.describe()
    # The CRT client names itself in every request's User-Agent.
    assert not any(
        "CRTS3NativeClient" in call.request.headers.get("user-agent", "")
        for call in run.calls
    ), run.describe()


async def test_streaming_upload_using_crt_client(
    crt_api: ApiSession,
) -> None:
    run = await crt_api.run(
        "s3 cp - s3://bucket/key",
        replies=[{"UploadId": "upload-id"}, {"ETag": '"etag"'}, {}],
        stdin=b"foo",
    )
    # The CRT client uploads a stream of unknown length in parts.
    assert sent(run) == [
        ("CreateMultipartUpload", HOST, "/key"),
        ("UploadPart", HOST, "/key"),
        ("CompleteMultipartUpload", HOST, "/key"),
    ], run.describe()
    assert bodies(run, "UploadPart") == [b"foo"], run.describe()


async def test_streaming_download_using_crt_client(
    crt_api: ApiSession,
) -> None:
    run = await crt_api.run(
        "s3 cp s3://bucket/key -",
        replies=[
            head_object_response(ContentLength=len(DOWNLOAD_CONTENT)),
            get_object_response(DOWNLOAD_CONTENT),
        ],
    )
    # The command sends no HEAD of its own: both are the CRT client's.
    assert sent(run) == [
        ("HeadObject", HOST, "/key"),
        ("GetObject", HOST, "/key"),
    ], run.describe()
    assert run.stdout == DOWNLOAD_CONTENT.decode(), run.describe()


async def test_upload_without_region_redirects_from_global_endpoint(
    crt_api: ApiSession,
) -> None:
    del crt_api.env["AWS_DEFAULT_REGION"]
    filename = write_file(crt_api, "myfile")
    redirect = HTTPResponse.raw(
        b"<Error><Code>PermanentRedirect</Code></Error>",
        status=301,
        headers={
            "Content-Type": "application/xml",
            "x-amz-bucket-region": "eu-central-1",
        },
    )
    run = await crt_api.run(
        ["s3", "cp", filename, "s3://bucket/key"], replies=[redirect, {}]
    )
    assert sent(run) == [
        ("PutObject", "bucket.s3.amazonaws.com", "/key"),
        ("PutObject", "bucket.s3.eu-central-1.amazonaws.com", "/key"),
    ], run.describe()
    assert signing_regions(run) == ["us-east-1", "eu-central-1"], (
        run.describe()
    )
    assert bodies(run, "PutObject") == [CONTENT, CONTENT], run.describe()


async def test_respects_region_parameter(crt_api: ApiSession) -> None:
    filename = write_file(crt_api, "myfile")
    run = await crt_api.run(
        ["s3", "cp", filename, "s3://bucket/key", "--region", "us-west-1"]
    )
    assert sent(run) == [
        ("PutObject", "bucket.s3.us-west-1.amazonaws.com", "/key")
    ], run.describe()
    assert signing_regions(run) == ["us-west-1"], run.describe()
    assert bodies(run, "PutObject") == [CONTENT], run.describe()


async def test_respects_endpoint_url_parameter(crt_api: ApiSession) -> None:
    filename = write_file(crt_api, "myfile")
    run = await crt_api.run(
        [
            "s3",
            "cp",
            filename,
            "s3://bucket/key",
            "--endpoint-url",
            "https://my.endpoint.com",
        ]
    )
    # The request reached the server through the proxy's TLS tunnel.
    assert sent(run) == [
        ("PutObject", "my.endpoint.com", "/bucket/key")
    ], run.describe()
    assert bodies(run, "PutObject") == [CONTENT], run.describe()


def plain_endpoint(api: ApiSession) -> str:
    """The server's own plain-HTTP address, which the command reaches
    straight, past the proxy."""
    api.env["NO_PROXY"] = "127.0.0.1"
    return api.server.url.rstrip("/")


@pytest.mark.parametrize(
    "setting",
    [
        pytest.param("--endpoint-url", id="endpoint-url-parameter"),
        pytest.param("AWS_ENDPOINT_URL", id="global-endpoint-url-env-var"),
        pytest.param("AWS_ENDPOINT_URL_S3", id="s3-endpoint-url-env-var"),
    ],
)
async def test_can_disable_ssl_using_endpoint_url(
    crt_api: ApiSession, setting: str
) -> None:
    filename = write_file(crt_api, "myfile")
    endpoint = plain_endpoint(crt_api)
    cmd = ["s3", "cp", filename, "s3://bucket/key"]
    if setting.startswith("--"):
        cmd += [setting, endpoint]
    else:
        crt_api.env[setting] = endpoint
    run = await crt_api.run(cmd)
    # The server's own address speaks only plain HTTP.
    assert sent(run) == [
        ("PutObject", endpoint.removeprefix("http://"), "/bucket/key")
    ], run.describe()
    assert bodies(run, "PutObject") == [CONTENT], run.describe()


async def test_ignores_configured_endpoint_url_when_requested(
    crt_api: ApiSession,
) -> None:
    crt_api.env["AWS_ENDPOINT_URL"] = "http://my.endpoint.com"
    crt_api.env["AWS_IGNORE_CONFIGURED_ENDPOINT_URLS"] = "true"
    filename = write_file(crt_api, "myfile")
    run = await crt_api.run(["s3", "cp", filename, "s3://bucket/key"])
    # The request went over TLS to the bucket's own endpoint.
    assert sent(run) == [("PutObject", HOST, "/key")], run.describe()


async def test_respects_no_sign_request_parameter(
    crt_api: ApiSession,
) -> None:
    filename = write_file(crt_api, "myfile")
    run = await crt_api.run(
        ["s3", "cp", filename, "s3://bucket/key", "--no-sign-request"]
    )
    assert sent(run) == [("PutObject", HOST, "/key")], run.describe()
    assert [
        call.request.headers.get("authorization") for call in run.calls
    ] == [None], run.describe()


async def test_respects_ca_bundle_parameter(crt_api: ApiSession) -> None:
    """The client trusts the proxy's CA only through the bundle
    --ca-bundle names: the environment no longer names it."""
    filename = write_file(crt_api, "myfile")
    ca_bundle = crt_api.env.pop("AWS_CA_BUNDLE")
    run = await crt_api.run(
        ["s3", "cp", filename, "s3://bucket/key", "--ca-bundle", ca_bundle]
    )
    assert sent(run) == [("PutObject", HOST, "/key")], run.describe()


async def test_respects_ca_bundle_parameter_no_verify(
    crt_api: ApiSession,
) -> None:
    filename = write_file(crt_api, "myfile")
    # Not a certificate: only a client that verifies nothing connects.
    ca_bundle = crt_api.cwd / "fake_ca"
    ca_bundle.write_bytes(CONTENT)
    run = await crt_api.run(
        [
            "s3",
            "cp",
            filename,
            "s3://bucket/key",
            "--ca-bundle",
            str(ca_bundle),
            "--no-verify-ssl",
        ]
    )
    assert sent(run) == [("PutObject", HOST, "/key")], run.describe()
