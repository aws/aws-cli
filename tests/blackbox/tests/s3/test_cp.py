import asyncio
import errno
import hashlib
import os
import signal
from collections.abc import Callable
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit
from xml.etree import ElementTree

import pytest
from localstub import (
    AsyncHTTPTestServer,
    HTTPResponse,
    RecordedHTTPRequest,
    ResponderContext,
)
from localstub.server import TransmissionStrategy, Writer

from harness_plugin import command_environment
from s3helpers import (
    FAILING_STDERRS,
    FAILING_STDOUTS,
    assert_refused_before_request,
    completion_lines,
    failing_stream,
    run_cli_with_stdout,
    run_cli_with_streams,
    run_cli_without_stdout,
)
from tests.blackbox.utils import (
    abort_mpu_response,
    complete_mpu_response,
    create_mpu_response,
    error_response,
    get_object_response,
    head_object_response,
    list_objects_xml,
    put_object_response,
    run_cli,
    upload_part_response,
    xml_response,
)

MIB = 1024 * 1024
UPLOAD_PAYLOAD = b"uneven payload\n"
# Each upload that succeeds, with the flag that makes it a dry run, the
# prefix its completion line gains, and the requests it sends.
UPLOAD_SUCCESSES = [
    pytest.param([], "", ["PUT"], id="success"),
    pytest.param(["--dryrun"], "(dryrun) ", [], id="dryrun"),
]
DOWNLOAD_PAYLOAD = b"payload"
# Each download that fails, with the HEAD headers and GET response that fail
# it, its exit status, its requests, and the cause stderr names.
DOWNLOAD_ERRORS = [
    pytest.param(
        {"x-amz-storage-class": "GLACIER"},
        get_object_response(DOWNLOAD_PAYLOAD),
        2,
        ["HEAD"],
        "GLACIER",
        id="glacier",
    ),
    pytest.param(
        {},
        error_response("AccessDenied", "download denied", 403),
        1,
        ["HEAD", "GET"],
        "AccessDenied",
        id="failure",
    ),
]


def multipart_operation(request: RecordedHTTPRequest) -> str:
    query = parse_qs(
        urlsplit(request.effective_path).query, keep_blank_values=True
    )
    if request.method == "POST" and "uploads" in query:
        return "CreateMultipartUpload"
    if request.method == "PUT" and "partNumber" in query:
        return "UploadPart"
    if request.method == "POST" and "uploadId" in query:
        return "CompleteMultipartUpload"
    if request.method == "DELETE" and "uploadId" in query:
        return "AbortMultipartUpload"
    return request.method


def aws_chunked_payload(body: bytes) -> bytes:
    payload = bytearray()
    offset = 0
    while True:
        line_end = body.index(b"\r\n", offset)
        size = int(body[offset:line_end].split(b";", 1)[0], 16)
        if size == 0:
            # Only trailers, such as a checksum, follow the final frame.
            return bytes(payload)
        offset = line_end + 2
        payload += body[offset : offset + size]
        offset += size + 2


class MultipartUploadResponder:
    # Answers one multipart upload and keeps what S3 would store: each
    # part's decoded payload and the object a completion assembles. Every
    # error it answers with is kept too, since that is why a client fails.
    def __init__(self) -> None:
        self.parts: dict[int, bytes] = {}
        self.completed_parts: list[int] = []
        self.stored: bytes | None = None
        self.errors: list[str] = []

    def __call__(self, context: ResponderContext) -> HTTPResponse:
        request = context.request
        operation = multipart_operation(request)
        if operation == "CreateMultipartUpload":
            return create_mpu_response("upload-id")
        if operation == "UploadPart":
            return self._upload_part(request)
        if operation == "CompleteMultipartUpload":
            return self._complete(request)
        if operation == "AbortMultipartUpload":
            return abort_mpu_response()
        return self._error(operation, "NotImplemented", "unexpected", 501)

    def part_sizes(self) -> dict[int, int]:
        return {number: len(payload) for number, payload in self.parts.items()}

    def _upload_part(self, request: RecordedHTTPRequest) -> HTTPResponse:
        query = parse_qs(urlsplit(request.effective_path).query)
        number = int(query["partNumber"][0])
        payload = request.body or b""
        if "aws-chunked" in request.headers.get("content-encoding", ""):
            payload = aws_chunked_payload(payload)
        declared = request.headers.get("x-amz-decoded-content-length")
        if declared is not None and int(declared) != len(payload):
            return self._error(
                f"UploadPart {number}",
                "IncompleteBody",
                f"body has {len(payload)} of {declared} bytes",
                400,
            )
        self.parts[number] = payload
        return upload_part_response(f"part-{number}")

    def _complete(self, request: RecordedHTTPRequest) -> HTTPResponse:
        root = ElementTree.fromstring(request.body or b"")
        numbers = [
            int(node.text or "0") for node in root.findall(".//{*}PartNumber")
        ]
        if not numbers or any(number not in self.parts for number in numbers):
            return self._error(
                "CompleteMultipartUpload",
                "InvalidPart",
                f"names parts {numbers}, uploaded {sorted(self.parts)}",
                400,
            )
        stored = b"".join(self.parts[number] for number in numbers)
        declared = request.headers.get("x-amz-mp-object-size")
        if declared is not None and int(declared) != len(stored):
            return self._error(
                "CompleteMultipartUpload",
                "InvalidRequest",
                f"parts {numbers} hold {len(stored)} bytes, "
                f"x-amz-mp-object-size is {declared}",
                400,
            )
        self.completed_parts = numbers
        self.stored = stored
        return complete_mpu_response()

    def _error(
        self, request: str, code: str, message: str, status: int
    ) -> HTTPResponse:
        self.errors.append(f"{request}: {code}: {message}")
        return error_response(code, message, status)


@pytest.fixture
def upload_source(tmp_path: Path) -> Path:
    source = tmp_path / "sp ace-λ.txt"
    source.write_bytes(UPLOAD_PAYLOAD)
    return source


@pytest.fixture
def download_destination(tmp_path: Path) -> Path:
    return tmp_path / "download λ.txt"


async def upload_with_flags(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    source: Path,
    response: HTTPResponse,
    flags: list[str],
) -> tuple[bytes, bytes, int]:
    server, env = transfer_runtime
    server.set_default_response(response)
    result = await run_cli(
        aws_cli, ["s3", "cp", str(source), "s3://bucket/key", *flags], env
    )
    assert source.read_bytes() == UPLOAD_PAYLOAD
    return result


async def download_with_flags(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    destination: Path,
    head_headers: dict[str, str],
    response: HTTPResponse,
    flags: list[str],
) -> tuple[bytes, bytes, int]:
    server, env = transfer_runtime
    server.set_response_sequence([head_object_response(7, **head_headers)])
    server.handler = lambda context: response
    return await run_cli(
        aws_cli,
        ["s3", "cp", "s3://bucket/key", str(destination), *flags],
        env,
    )


def assert_no_progress(stdout: bytes) -> None:
    assert b"Completed " not in stdout
    assert b"\r" not in stdout


def assert_upload_failure_reported(
    result: tuple[bytes, bytes, int], server: AsyncHTTPTestServer
) -> None:
    stdout, stderr, rc = result
    assert rc == 1, stderr.decode()
    assert [r.method for r in server.requests] == ["PUT"]
    assert completion_lines(stdout) == []
    assert "upload failed:" in stderr.decode()
    assert "AccessDenied" in stderr.decode()
    assert "denied by test" in stderr.decode()


def assert_download_failure_reported(
    result: tuple[bytes, bytes, int],
    server: AsyncHTTPTestServer,
    destination: Path,
    status: int,
    methods: list[str],
    cause: str,
) -> None:
    stdout, stderr, rc = result
    assert rc == status, stderr
    assert [r.method for r in server.requests] == methods
    assert not destination.exists()
    assert completion_lines(stdout) == []
    assert cause in stderr.decode()


@pytest.mark.asyncio
@pytest.mark.parametrize(("dryrun", "prefix", "methods"), UPLOAD_SUCCESSES)
async def test_cp_upload_success_reports_completion_line(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    upload_source: Path,
    dryrun: list[str],
    prefix: str,
    methods: list[str],
) -> None:
    server, _ = transfer_runtime
    stdout, stderr, rc = await upload_with_flags(
        aws_cli, transfer_runtime, upload_source, put_object_response(), dryrun
    )
    assert (rc, stderr) == (0, b"")
    assert [r.method for r in server.requests] == methods
    assert completion_lines(stdout) == [
        f"{prefix}upload: {os.path.relpath(upload_source)} to s3://bucket/key"
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(("dryrun", "prefix", "methods"), UPLOAD_SUCCESSES)
async def test_cp_upload_success_no_progress_reports_only_completion_line(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    upload_source: Path,
    dryrun: list[str],
    prefix: str,
    methods: list[str],
) -> None:
    server, _ = transfer_runtime
    stdout, stderr, rc = await upload_with_flags(
        aws_cli,
        transfer_runtime,
        upload_source,
        put_object_response(),
        ["--no-progress", *dryrun],
    )
    assert (rc, stderr) == (0, b"")
    assert [r.method for r in server.requests] == methods
    assert completion_lines(stdout) == [
        f"{prefix}upload: {os.path.relpath(upload_source)} to s3://bucket/key"
    ]
    assert_no_progress(stdout)


@pytest.mark.asyncio
async def test_cp_upload_success_only_show_errors_hides_completion_line(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    upload_source: Path,
) -> None:
    server, _ = transfer_runtime
    stdout, stderr, rc = await upload_with_flags(
        aws_cli,
        transfer_runtime,
        upload_source,
        put_object_response(),
        ["--only-show-errors"],
    )
    assert (rc, stderr) == (0, b"")
    assert [r.method for r in server.requests] == ["PUT"]
    assert completion_lines(stdout) == []
    assert_no_progress(stdout)


@pytest.mark.asyncio
async def test_cp_upload_dryrun_only_show_errors_reports_dryrun_line(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    upload_source: Path,
) -> None:
    # --only-show-errors hides completed transfers, not dry-run lines.
    server, _ = transfer_runtime
    stdout, stderr, rc = await upload_with_flags(
        aws_cli,
        transfer_runtime,
        upload_source,
        put_object_response(),
        ["--only-show-errors", "--dryrun"],
    )
    assert (rc, stderr) == (0, b"")
    assert not server.requests
    assert completion_lines(stdout) == [
        f"(dryrun) upload: {os.path.relpath(upload_source)} to s3://bucket/key"
    ]
    assert_no_progress(stdout)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "dryrun", "status", "methods"),
    [
        pytest.param(put_object_response(), [], 0, ["PUT"], id="success"),
        pytest.param(put_object_response(), ["--dryrun"], 0, [], id="dryrun"),
        pytest.param(
            error_response("AccessDenied", "denied by test", 403),
            [],
            1,
            ["PUT"],
            id="failure",
        ),
    ],
)
async def test_cp_upload_quiet_prints_nothing(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    upload_source: Path,
    response: HTTPResponse,
    dryrun: list[str],
    status: int,
    methods: list[str],
) -> None:
    server, _ = transfer_runtime
    stdout, stderr, rc = await upload_with_flags(
        aws_cli,
        transfer_runtime,
        upload_source,
        response,
        ["--quiet", *dryrun],
    )
    assert rc == status, stderr.decode()
    assert [r.method for r in server.requests] == methods
    assert (stdout, stderr) == (b"", b"")


@pytest.mark.asyncio
async def test_cp_upload_failure_reports_error_without_completion_line(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    upload_source: Path,
) -> None:
    server, _ = transfer_runtime
    result = await upload_with_flags(
        aws_cli,
        transfer_runtime,
        upload_source,
        error_response("AccessDenied", "denied by test", 403),
        [],
    )
    assert_upload_failure_reported(result, server)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "flags",
    [["--no-progress"], ["--only-show-errors"]],
    ids=["no-progress", "errors-only"],
)
async def test_cp_upload_failure_without_progress_reports_only_error(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    upload_source: Path,
    flags: list[str],
) -> None:
    server, _ = transfer_runtime
    result = await upload_with_flags(
        aws_cli,
        transfer_runtime,
        upload_source,
        error_response("AccessDenied", "denied by test", 403),
        flags,
    )
    assert_upload_failure_reported(result, server)
    assert_no_progress(result[0])


@pytest.mark.asyncio
async def test_cp_download_success_reports_completion_line(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    download_destination: Path,
) -> None:
    server, _ = transfer_runtime
    stdout, stderr, rc = await download_with_flags(
        aws_cli,
        transfer_runtime,
        download_destination,
        {},
        get_object_response(DOWNLOAD_PAYLOAD),
        [],
    )
    assert (rc, stderr) == (0, b"")
    assert [r.method for r in server.requests] == ["HEAD", "GET"]
    assert download_destination.read_bytes() == DOWNLOAD_PAYLOAD
    assert completion_lines(stdout) == [
        f"download: s3://bucket/key to {os.path.relpath(download_destination)}"
    ]


@pytest.mark.asyncio
async def test_cp_download_success_no_progress_reports_only_completion_line(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    download_destination: Path,
) -> None:
    server, _ = transfer_runtime
    stdout, stderr, rc = await download_with_flags(
        aws_cli,
        transfer_runtime,
        download_destination,
        {},
        get_object_response(DOWNLOAD_PAYLOAD),
        ["--no-progress"],
    )
    assert (rc, stderr) == (0, b"")
    assert [r.method for r in server.requests] == ["HEAD", "GET"]
    assert download_destination.read_bytes() == DOWNLOAD_PAYLOAD
    assert completion_lines(stdout) == [
        f"download: s3://bucket/key to {os.path.relpath(download_destination)}"
    ]
    assert_no_progress(stdout)


@pytest.mark.asyncio
async def test_cp_download_success_only_show_errors_hides_completion_line(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    download_destination: Path,
) -> None:
    server, _ = transfer_runtime
    stdout, stderr, rc = await download_with_flags(
        aws_cli,
        transfer_runtime,
        download_destination,
        {},
        get_object_response(DOWNLOAD_PAYLOAD),
        ["--only-show-errors"],
    )
    assert (rc, stderr) == (0, b"")
    assert [r.method for r in server.requests] == ["HEAD", "GET"]
    assert download_destination.read_bytes() == DOWNLOAD_PAYLOAD
    assert completion_lines(stdout) == []
    assert_no_progress(stdout)


@pytest.mark.asyncio
async def test_cp_download_success_quiet_prints_nothing(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    download_destination: Path,
) -> None:
    server, _ = transfer_runtime
    stdout, stderr, rc = await download_with_flags(
        aws_cli,
        transfer_runtime,
        download_destination,
        {},
        get_object_response(DOWNLOAD_PAYLOAD),
        ["--quiet"],
    )
    assert rc == 0, stderr
    assert [r.method for r in server.requests] == ["HEAD", "GET"]
    assert download_destination.read_bytes() == DOWNLOAD_PAYLOAD
    assert (stdout, stderr) == (b"", b"")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("head_headers", "response", "status", "methods", "cause"),
    DOWNLOAD_ERRORS,
)
async def test_cp_download_error_quiet_prints_nothing(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    download_destination: Path,
    head_headers: dict[str, str],
    response: HTTPResponse,
    status: int,
    methods: list[str],
    cause: str,
) -> None:
    server, _ = transfer_runtime
    stdout, stderr, rc = await download_with_flags(
        aws_cli,
        transfer_runtime,
        download_destination,
        head_headers,
        response,
        ["--quiet"],
    )
    assert rc == status, stderr
    assert [r.method for r in server.requests] == methods
    assert not download_destination.exists()
    assert (stdout, stderr) == (b"", b"")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("head_headers", "response", "status", "methods", "cause"),
    DOWNLOAD_ERRORS,
)
async def test_cp_download_error_reports_cause_without_completion_line(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    download_destination: Path,
    head_headers: dict[str, str],
    response: HTTPResponse,
    status: int,
    methods: list[str],
    cause: str,
) -> None:
    server, _ = transfer_runtime
    result = await download_with_flags(
        aws_cli,
        transfer_runtime,
        download_destination,
        head_headers,
        response,
        [],
    )
    assert_download_failure_reported(
        result, server, download_destination, status, methods, cause
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("head_headers", "response", "status", "methods", "cause"),
    DOWNLOAD_ERRORS,
)
@pytest.mark.parametrize(
    "flags",
    [["--no-progress"], ["--only-show-errors"]],
    ids=["no-progress", "errors-only"],
)
async def test_cp_download_error_without_progress_reports_only_cause(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    download_destination: Path,
    flags: list[str],
    head_headers: dict[str, str],
    response: HTTPResponse,
    status: int,
    methods: list[str],
    cause: str,
) -> None:
    server, _ = transfer_runtime
    result = await download_with_flags(
        aws_cli,
        transfer_runtime,
        download_destination,
        head_headers,
        response,
        flags,
    )
    assert_download_failure_reported(
        result, server, download_destination, status, methods, cause
    )
    assert_no_progress(result[0])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        pytest.param(
            b"<Error><Code>AccessDenied</Code><Message>caf\xe9</Message></Error>",
            id="not-utf8",
        ),
        pytest.param(
            b"<Error><Code>AccessDenied</Code><Message>denied</Message>",
            id="cut-short",
        ),
    ],
)
async def test_cp_download_unparsable_error_body_reports_the_status(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    download_destination: Path,
    body: bytes,
) -> None:
    server, _ = transfer_runtime
    response = HTTPResponse.raw(
        body, status=403, headers={"Content-Type": "application/xml"}
    )
    result = await download_with_flags(
        aws_cli, transfer_runtime, download_destination, {}, response, []
    )
    assert_download_failure_reported(
        result,
        server,
        download_destination,
        1,
        ["HEAD", "GET"],
        "An error occurred (403) when calling the GetObject operation: "
        "Forbidden\n",
    )


@pytest.mark.asyncio
async def test_cp_download_well_formed_error_body_reports_its_code(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    download_destination: Path,
) -> None:
    server, _ = transfer_runtime
    response = HTTPResponse.raw(
        b"<Error><Code>AccessDenied</Code><Message>denied</Message>"
        b"<RequestId>id</RequestId ></Error>",
        status=403,
        headers={"Content-Type": "application/xml"},
    )
    result = await download_with_flags(
        aws_cli, transfer_runtime, download_destination, {}, response, []
    )
    assert_download_failure_reported(
        result,
        server,
        download_destination,
        1,
        ["HEAD", "GET"],
        "An error occurred (AccessDenied) when calling the GetObject "
        "operation: denied\n",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message",
    [
        pytest.param("m" * 5000, id="ascii"),
        pytest.param("a" * 1023 + "é tail", id="multibyte"),
    ],
)
async def test_cp_download_long_error_message_is_printed_whole(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    download_destination: Path,
    message: str,
) -> None:
    server, _ = transfer_runtime
    response = error_response("AccessDenied", message, 403)
    result = await download_with_flags(
        aws_cli, transfer_runtime, download_destination, {}, response, []
    )
    assert_download_failure_reported(
        result,
        server,
        download_destination,
        1,
        ["HEAD", "GET"],
        "An error occurred (AccessDenied) when calling the GetObject "
        f"operation: {message}\n",
    )


@pytest.mark.asyncio
async def test_cp_download_redirects_to_error_body_region_in_cdata(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    download_destination: Path,
) -> None:
    server, env = transfer_runtime
    # botocore reads a CDATA section's payload literally, so the GET's error
    # body names the region the retry goes to.
    server.set_response_sequence(
        [
            head_object_response(len(DOWNLOAD_PAYLOAD)),
            HTTPResponse.raw(
                b"<Error><Code>PermanentRedirect</Code><Message>moved</Message>"
                b"<Region><![CDATA[eu-west-1]]></Region></Error>",
                status=301,
                headers={"Content-Type": "application/xml"},
            ),
            get_object_response(DOWNLOAD_PAYLOAD),
        ]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            "s3://bucket/key",
            str(download_destination),
            "--region",
            "us-east-1",
            "--no-progress",
        ],
        env,
    )
    assert (rc, stderr) == (0, b""), stdout
    assert download_destination.read_bytes() == DOWNLOAD_PAYLOAD
    assert [(r.method, r.headers.get("host")) for r in server.requests] == [
        ("HEAD", "bucket.s3.us-east-1.amazonaws.com"),
        ("GET", "bucket.s3.us-east-1.amazonaws.com"),
        ("GET", "bucket.s3.eu-west-1.amazonaws.com"),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("existing", [False, True], ids=["new", "overwrite"])
async def test_cp_empty_download_creates_or_truncates_file(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    existing: bool,
) -> None:
    server, env = transfer_runtime
    destination = tmp_path / "empty"
    if existing:
        destination.write_bytes(b"must be removed")
    server.set_response_sequence(
        [head_object_response(0), get_object_response(b"")]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", "s3://bucket/empty", str(destination), "--no-progress"],
        env,
    )
    assert (rc, stderr) == (0, b"")
    assert destination.read_bytes() == b""
    assert completion_lines(stdout) == [
        f"download: s3://bucket/empty to {os.path.relpath(destination)}"
    ]
    assert [r.method for r in server.requests] == ["HEAD", "GET"]


@pytest.mark.asyncio
@pytest.mark.parametrize("stream", [False, True], ids=["file", "stdin"])
async def test_cp_empty_upload_issues_put(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    stream: bool,
) -> None:
    server, env = transfer_runtime
    source = tmp_path / "empty"
    source.write_bytes(b"")
    server.set_default_response(put_object_response())
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            "-" if stream else str(source),
            "s3://bucket/empty",
            "--no-progress",
        ],
        env,
        stdin=b"" if stream else None,
    )
    assert (rc, stderr) == (0, b"")
    assert [r.method for r in server.requests] == ["PUT"]
    headers = server.requests[0].headers
    assert (
        headers.get(
            "x-amz-decoded-content-length", headers.get("content-length")
        )
        == "0"
    )
    assert (
        unquote(urlsplit(server.requests[0].effective_path).path) == "/empty"
    )
    assert completion_lines(stdout) == (
        []
        if stream
        else [f"upload: {os.path.relpath(source)} to s3://bucket/empty"]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "flags,selected",
    [
        ([], ["link.txt", "real.txt"]),
        (["--follow-symlinks"], ["link.txt", "real.txt"]),
        (["--no-follow-symlinks"], ["real.txt"]),
    ],
    ids=["default", "follow", "no-follow"],
)
async def test_cp_recursive_upload_symlink_flags_select_uploaded_files(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    flags: list[str],
    selected: list[str],
) -> None:
    server, env = transfer_runtime
    source = tmp_path / "source"
    source.mkdir()
    (source / "real.txt").write_bytes(b"linked content")
    (source / "link.txt").symlink_to("real.txt")
    server.set_default_response(put_object_response())
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            str(source),
            "s3://bucket/",
            "--recursive",
            "--no-progress",
            *flags,
        ],
        env,
    )
    assert (rc, stderr) == (0, b"")
    assert sorted(
        (r.method, unquote(urlsplit(r.effective_path).path))
        for r in server.requests
    ) == [("PUT", f"/{name}") for name in selected]
    assert sorted(completion_lines(stdout)) == sorted(
        f"upload: {os.path.relpath(source / name)} to s3://bucket/{name}"
        for name in selected
    )
    assert (source / "link.txt").is_symlink()


# A recursive upload follows a symlink to a file or a directory by
# default. A source it cannot read is skipped with a warning naming its
# absolute path, which makes the status 2 while its siblings upload: a
# broken symlink, or a file made unreadable, which takes its symlink with
# it (filegenerator.py:323-341).
@pytest.mark.asyncio
@pytest.mark.skipif(os.name != "posix", reason="symlinks and a mode-000 file")
@pytest.mark.parametrize(
    "defect,uploaded,skipped,reason",
    [
        (None, ["dir-link/deep", "file", "file-link", "nested/deep"], [], ""),
        (
            "broken",
            ["dir-link/deep", "file", "file-link", "nested/deep"],
            ["broken"],
            "File does not exist.",
        ),
        (
            "unreadable",
            ["dir-link/deep", "nested/deep"],
            ["file", "file-link"],
            "File/Directory is not readable.",
        ),
    ],
    ids=["links", "broken-link", "unreadable"],
)
async def test_cp_recursive_upload_follows_links_and_skips_unreadable(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    defect: str | None,
    uploaded: list[str],
    skipped: list[str],
    reason: str,
) -> None:
    server, env = transfer_runtime
    source = tmp_path / "inputs"
    (source / "nested").mkdir(parents=True)
    (source / "file").write_bytes(b"file")
    (source / "nested" / "deep").write_bytes(b"deep")
    (source / "file-link").symlink_to("file")
    (source / "dir-link").symlink_to("nested", target_is_directory=True)
    if defect == "broken":
        (source / "broken").symlink_to("missing")
    elif defect == "unreadable":
        (source / "file").chmod(0)
        if os.access(source / "file", os.R_OK):
            pytest.skip("this process reads mode-000 files")
    server.set_default_response(put_object_response())
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            str(source),
            "s3://bucket/upload/",
            "--recursive",
            "--no-progress",
        ],
        env,
    )
    assert rc == (2 if skipped else 0), stderr.decode()
    assert sorted(
        (r.method, unquote(urlsplit(r.effective_path).path))
        for r in server.requests
    ) == [("PUT", f"/upload/{name}") for name in uploaded]
    assert sorted(stdout.decode().splitlines()) == [
        f"upload: {os.path.relpath(source / name)} to "
        f"s3://bucket/upload/{name}"
        for name in uploaded
    ]
    # Skips are warned about in the order the OS lists the directory, which
    # varies by filesystem (filegenerator.py:219-228).
    assert sorted(stderr.decode().splitlines()) == sorted(
        f"warning: Skipping file {source / name}. {reason}" for name in skipped
    )


@pytest.mark.asyncio
@pytest.mark.skipif(os.name != "posix", reason="creates a symlink")
async def test_cp_recursive_upload_stops_at_symlink_loop(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    source = tmp_path / "source"
    (source / "t").mkdir(parents=True)
    (source / "t" / "b.txt").write_bytes(b"payload\n")
    (source / "t" / "loop").symlink_to(".")
    server.set_default_response(put_object_response())
    # Upstream joins each name onto the full path, so the OS's symlink limit
    # ends the loop: `isdir` and `exists` fail on the first path past it.
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", str(source), "s3://bucket/", "--recursive", "--no-progress"],
        env,
        timeout=30,
    )
    assert rc == 2, stderr[-500:]
    warnings = [line for line in stderr.splitlines() if line.startswith(b"warning:")]
    assert len(warnings) == 1, warnings[:3]
    prefix = f"warning: Skipping file {source / 't'}{os.sep}".encode()
    assert warnings[0].startswith(prefix)
    assert warnings[0].endswith(b". File does not exist.")
    loops = warnings[0][len(prefix) : -len(b". File does not exist.")]
    depth = len(loops.split(os.sep.encode()))
    assert loops == os.sep.encode().join([b"loop"] * depth)
    # Every level below the failing one holds b.txt.
    keys = sorted(
        unquote(urlsplit(r.effective_path).path) for r in server.requests
    )
    assert keys == sorted(
        "/t/" + "loop/" * level + "b.txt" for level in range(depth)
    )
    assert 8 <= depth <= 64


def devnull_config(tmp_path: Path, config: Path) -> str:
    return os.devnull


def directory_config(tmp_path: Path, config: Path) -> str:
    directory = tmp_path / "config-dir"
    directory.mkdir()
    return str(directory)


def unreadable_config(tmp_path: Path, config: Path) -> str:
    config.write_text("[default]\n", encoding="utf-8")
    config.chmod(0)
    return str(config)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "make_config",
    [
        pytest.param(devnull_config, id="devnull"),
        pytest.param(directory_config, id="directory"),
        pytest.param(
            unreadable_config,
            id="unreadable",
            marks=pytest.mark.skipif(
                os.name != "posix" or os.geteuid() == 0,
                reason="needs a file the caller cannot read",
            ),
        ),
    ],
)
async def test_cp_upload_reads_unusable_config_file_as_empty(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    make_config: Callable[[Path, Path], str],
) -> None:
    server, env = transfer_runtime
    # Botocore reads a config file it can't parse as a regular file as empty.
    env["AWS_CONFIG_FILE"] = make_config(
        tmp_path, Path(env["AWS_CONFIG_FILE"])
    )
    source = tmp_path / "a.txt"
    source.write_bytes(b"payload\n")
    server.set_default_response(put_object_response())
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", str(source), "s3://bucket/a.txt", "--no-progress"],
        env,
    )
    assert (rc, stderr) == (0, b"")
    assert [r.method for r in server.requests] == ["PUT"]
    assert completion_lines(stdout) == [
        f"upload: {os.path.relpath(source)} to s3://bucket/a.txt"
    ]


# The README's tuned profile plus the other download-only keys, and the same
# keys with values the native parser rejects. Upstream ignores keys it
# doesn't know, so neither may affect an upload.
DOWNLOAD_TUNING_PROFILES = {
    "tuned": {
        "target_bandwidth": "100Gb/s",
        "download_writer_numa": "same-node",
        "download_writer_node": "auto",
        "download_writer": "mmap",
        "download_writer_copy": "nt",
        "download_writer_prefault": "enabled",
        "io_workers": "2",
        "download_numa_pool": "enabled",
    },
    "invalid": {
        "download_writer_numa": "bogus",
        "download_writer_node": "bogus",
        "download_writer": "bogus",
        "download_writer_copy": "bogus",
        "download_writer_prefault": "bogus",
        "io_workers": "0",
        "download_numa_pool": "bogus",
    },
}


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", sorted(DOWNLOAD_TUNING_PROFILES))
@pytest.mark.parametrize("recursive", [False, True], ids=["single", "recursive"])
async def test_cp_upload_ignores_download_tuning_settings(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    recursive: bool,
    profile: str,
) -> None:
    server, env = transfer_runtime
    # `auto` runs the CRT client, which reads target_bandwidth; the classic
    # client would warn about it.
    settings = "".join(
        f"    {key} = {value}\n"
        for key, value in DOWNLOAD_TUNING_PROFILES[profile].items()
    )
    Path(env["AWS_CONFIG_FILE"]).write_text(
        f"[default]\ns3 =\n{settings}", encoding="utf-8"
    )
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.txt").write_bytes(b"payload\n")
    server.set_default_response(put_object_response())
    args = (
        [str(source), "s3://bucket/", "--recursive"]
        if recursive
        else [str(source / "a.txt"), "s3://bucket/a.txt"]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "cp", *args, "--no-progress"], env
    )
    assert (rc, stderr) == (0, b"")
    assert [
        (r.method, unquote(urlsplit(r.effective_path).path))
        for r in server.requests
    ] == [("PUT", "/a.txt")]
    assert completion_lines(stdout) == [
        f"upload: {os.path.relpath(source / 'a.txt')} to s3://bucket/a.txt"
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure,warning,status",
    [
        (False, False, 0),
        (False, True, 2),
        (True, False, 1),
        (True, True, 1),
    ],
    ids=["success", "warning", "failure", "failure-and-warning"],
)
async def test_cp_recursive_download_status_prefers_failure_over_warning(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    failure: bool,
    warning: bool,
    status: int,
) -> None:
    server, env = transfer_runtime
    destination = tmp_path / "downloads"
    objects = [
        {"Key": "good.txt", "Size": 4, "LastModified": "2026-01-01T00:00:00Z"}
    ]
    if failure:
        objects.append(
            {
                "Key": "bad.txt",
                "Size": 4,
                "LastModified": "2026-01-01T00:00:00Z",
            }
        )
    if warning:
        objects.append(
            {
                "Key": "cold.txt",
                "Size": 4,
                "LastModified": "2026-01-01T00:00:00Z",
                "StorageClass": "GLACIER",
            }
        )
    server.set_response_sequence([xml_response(list_objects_xml(objects))])

    def respond(context: ResponderContext) -> HTTPResponse:
        if urlsplit(context.request.effective_path).path == "/good.txt":
            return get_object_response(b"good")
        return error_response("AccessDenied", "bad object denied", 403)

    server.handler = respond
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            "s3://bucket/",
            str(destination),
            "--recursive",
            "--no-progress",
        ],
        env,
    )
    assert rc == status, stderr.decode()
    assert (destination / "good.txt").read_bytes() == b"good"
    assert not (destination / "bad.txt").exists()
    assert not (destination / "cold.txt").exists()
    assert completion_lines(stdout) == [
        (
            "download: s3://bucket/good.txt to "
            f"{os.path.relpath(destination / 'good.txt')}"
        )
    ]
    assert (b"AccessDenied" in stderr) == failure
    assert (b"GLACIER" in stderr) == warning
    assert sorted(
        urlsplit(r.effective_path).path for r in server.requests[1:]
    ) == (["/bad.txt", "/good.txt"] if failure else ["/good.txt"])


class _HoldUntilTempFiles(TransmissionStrategy):
    """Sends half of each GET body, then holds it until every download's
    temp file exists, recording the temp names."""

    def __init__(self, directory: Path, payload: bytes, count: int) -> None:
        self.directory = directory
        self.payload = payload
        self.count = count
        self.temp_names: set[str] = set()

    async def write_body(self, writer: Writer, body: bytes) -> None:
        if body != self.payload:
            writer.write(body)
            await writer.drain()
            return
        half = len(body) // 2
        writer.write(body[:half])
        await writer.drain()
        for _ in range(200):
            names = {
                path.name
                for path in self.directory.glob("*.*.*")
                if path.is_file()
            }
            self.temp_names |= names
            if len(self.temp_names) >= self.count:
                break
            await asyncio.sleep(0.05)
        writer.write(body[half:])
        await writer.drain()


@pytest.mark.asyncio
async def test_cp_recursive_download_temp_names_are_not_sequential(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    # Seeing one temp name must not reveal the next: a local user who could
    # predict one could plant a symlink there for the download to follow.
    server, env = transfer_runtime
    destination = tmp_path / "downloads"
    destination.mkdir()
    # Upstream's classic path reads 256 KiB before it opens the temp file.
    payload = b"x" * (1024 * 1024)
    keys = [f"f{index}.bin" for index in range(3)]
    objects = [
        {
            "Key": key,
            "Size": len(payload),
            "LastModified": "2026-01-01T00:00:00Z",
        }
        for key in keys
    ]
    server.set_response_sequence([xml_response(list_objects_xml(objects))])
    server.handler = lambda context: get_object_response(payload)
    strategy = _HoldUntilTempFiles(destination, payload, len(keys))
    server.set_transmission_strategy(strategy)
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", "s3://bucket/", str(destination), "--recursive"],
        env,
    )
    assert rc == 0, stderr.decode()
    assert sorted(path.name for path in destination.iterdir()) == keys
    assert len(strategy.temp_names) == len(keys), strategy.temp_names
    suffixes = sorted(name.rsplit(".", 1)[1] for name in strategy.temp_names)

    def close(first: str, second: str) -> bool:
        try:
            return abs(int(first, 16) - int(second, 16)) < 1024
        except ValueError:
            return False

    for index, first in enumerate(suffixes):
        for second in suffixes[index + 1 :]:
            assert not close(first, second), suffixes


@pytest.mark.asyncio
async def test_cp_empty_local_directories_do_not_create_objects(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    source = tmp_path / "empty-tree"
    (source / "nested").mkdir(parents=True)
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", str(source), "s3://bucket/", "--recursive"],
        env,
    )
    assert (rc, stdout, stderr) == (0, b"", b"")
    assert not server.requests


@pytest.mark.asyncio
async def test_cp_directory_marker_is_not_an_empty_file(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    destination = tmp_path / "download"
    server.set_response_sequence(
        [
            xml_response(
                list_objects_xml(
                    [
                        {
                            "Key": name,
                            "Size": 0,
                            "LastModified": "2026-01-01T00:00:00Z",
                        }
                        for name in ["prefix/dir/", "prefix/empty"]
                    ]
                )
            )
        ]
    )
    server.handler = lambda context: get_object_response(b"")
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            "s3://bucket/prefix/",
            str(destination),
            "--recursive",
            "--no-progress",
        ],
        env,
    )
    assert (rc, stderr) == (0, b"")
    assert (destination / "empty").read_bytes() == b""
    assert not (destination / "dir").exists()
    assert [
        (r.method, urlsplit(r.effective_path).path)
        for r in server.requests[1:]
    ] == [("GET", "/prefix/empty")]
    assert completion_lines(stdout) == [
        (
            "download: s3://bucket/prefix/empty to "
            f"{os.path.relpath(destination / 'empty')}"
        )
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "directory", [False, True], ids=["explicit-file", "trailing-slash"]
)
async def test_cp_download_nonexistent_destination_path_creates_parents(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    directory: bool,
) -> None:
    server, env = transfer_runtime
    destination = tmp_path / "missing" / "target"
    # Upstream reads only a trailing os.sep as naming a directory, so on
    # Windows a trailing '/' names a file.
    argument = str(destination) + (os.sep if directory else "")
    expected = destination / "key.txt" if directory else destination
    server.set_response_sequence(
        [head_object_response(5), get_object_response(b"bytes")]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", "s3://bucket/nested/key.txt", argument, "--no-progress"],
        env,
    )
    assert (rc, stderr) == (0, b"")
    assert expected.read_bytes() == b"bytes"
    assert [r.method for r in server.requests] == ["HEAD", "GET"]
    assert completion_lines(stdout) == [
        f"download: s3://bucket/nested/key.txt to {os.path.relpath(expected)}"
    ]


@pytest.mark.asyncio
async def test_cp_missing_source_validation_is_not_silenced(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    output_flags: list[str],
) -> None:
    server, env = transfer_runtime
    missing = tmp_path / "missing.txt"
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", str(missing), "s3://bucket/key", *output_flags],
        env,
    )
    assert rc == 255, stderr.decode()
    assert stdout == b""
    assert (
        f"The user-provided path {missing} does not exist." in stderr.decode()
    )
    assert not server.requests


async def copy_broken_symlink(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    flags: list[str],
) -> tuple[bytes, bytes, int]:
    server, env = transfer_runtime
    source = tmp_path / "source"
    source.mkdir()
    (source / "broken").symlink_to("absent")
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", str(source), "s3://bucket/", "--recursive", *flags],
        env,
    )
    assert rc == 2, stderr.decode()
    assert not server.requests
    assert (source / "broken").is_symlink()
    return stdout, stderr, rc


def assert_broken_symlink_warning(stderr: bytes) -> None:
    assert b"warning: Skipping file" in stderr
    assert b"broken" in stderr
    assert b"does not exist" in stderr


@pytest.mark.asyncio
async def test_cp_broken_symlink_warns_and_exits_2(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    stdout, stderr, _ = await copy_broken_symlink(
        aws_cli, transfer_runtime, tmp_path, []
    )
    assert completion_lines(stdout) == []
    assert_broken_symlink_warning(stderr)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "flags",
    [["--no-progress"], ["--only-show-errors"]],
    ids=["no-progress", "errors-only"],
)
async def test_cp_broken_symlink_without_progress_warns_with_empty_stdout(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    flags: list[str],
) -> None:
    stdout, stderr, _ = await copy_broken_symlink(
        aws_cli, transfer_runtime, tmp_path, flags
    )
    assert stdout == b""
    assert_broken_symlink_warning(stderr)


@pytest.mark.asyncio
async def test_cp_broken_symlink_quiet_exits_2_silently(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    stdout, stderr, _ = await copy_broken_symlink(
        aws_cli, transfer_runtime, tmp_path, ["--quiet"]
    )
    assert (stdout, stderr) == (b"", b"")


async def download_unlistable_prefix(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    flags: list[str],
) -> bytes:
    server, env = transfer_runtime
    destination = tmp_path / "destination"
    server.set_default_response(error_response("AccessDenied", "no list", 403))
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            "s3://bucket/",
            str(destination),
            "--recursive",
            *flags,
        ],
        env,
    )
    assert rc == 1, stderr.decode()
    assert stdout == b""
    assert [r.method for r in server.requests] == ["GET"]
    # Python creates the recursive destination before it starts listing.
    assert destination.is_dir()
    assert list(destination.iterdir()) == []
    return stderr


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "flags",
    [[], ["--no-progress"], ["--only-show-errors"]],
    ids=["default", "no-progress", "errors-only"],
)
async def test_cp_listing_error_reports_fatal_error_without_transfers(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    flags: list[str],
) -> None:
    stderr = await download_unlistable_prefix(
        aws_cli, transfer_runtime, tmp_path, flags
    )
    assert b"fatal error:" in stderr
    assert b"AccessDenied" in stderr
    assert b"ListObjectsV2" in stderr


@pytest.mark.asyncio
async def test_cp_listing_error_quiet_fails_silently_without_transfers(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    stderr = await download_unlistable_prefix(
        aws_cli, transfer_runtime, tmp_path, ["--quiet"]
    )
    assert stderr == b""


def assert_rejected_listing_page_fails(
    result: tuple[bytes, bytes, int],
    server: AsyncHTTPTestServer,
    destination: Path,
) -> None:
    # botocore makes a 200 it cannot parse a 500 and retries it, three
    # attempts in all; the file generator then raises that 500, and no
    # object of the page downloads.
    stdout, stderr, rc = result
    assert (rc, stdout) == (1, b""), stderr.decode()
    assert stderr == (
        b"fatal error: An error occurred (500) when calling the "
        b"ListObjectsV2 operation (reached max retries: 2): "
        b"Internal Server Error\n"
    )
    paths = [urlsplit(r.effective_path).path for r in server.requests]
    assert paths == ["/"] * 3
    assert list(destination.iterdir()) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "spelling",
    [b"\xff", b"&#xD800;"],
    ids=["raw-byte", "surrogate-reference"],
)
async def test_cp_recursive_non_utf8_listing_page_downloads_nothing(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    spelling: bytes,
) -> None:
    server, env = transfer_runtime
    destination = tmp_path / "destination"
    objects = [
        {"Key": key, "Size": 4, "LastModified": "2026-01-01T00:00:00Z"}
        for key in ["good.txt", "bad-name"]
    ]
    # The page names no EncodingType, so the key's bytes are its name.
    page = list_objects_xml(objects).encode()
    listing = page.replace(b"bad-name", b"bad" + spelling)

    def respond(context: ResponderContext) -> HTTPResponse:
        if urlsplit(context.request.effective_path).path == "/":
            return HTTPResponse.raw(
                listing, headers={"Content-Type": "application/xml"}
            )
        return get_object_response(b"data")

    server.handler = respond
    result = await run_cli(
        aws_cli,
        ["s3", "cp", "s3://bucket/", str(destination), "--recursive"],
        env,
        timeout=20,
    )
    assert_rejected_listing_page_fails(result, server, destination)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "old,new",
    [
        (b"bad-name", b"bad\x01"),
        (b"bad-name", b"bad&#x1;"),
        (b"<ETag>bad-etag</ETag>", b"<ETag>&#XD800;</ETag>"),
    ],
    ids=[
        "raw-control-key",
        "control-reference-key",
        "malformed-reference-etag",
    ],
)
async def test_cp_recursive_listing_page_xml_disallows_downloads_nothing(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    old: bytes,
    new: bytes,
) -> None:
    server, env = transfer_runtime
    destination = tmp_path / "destination"
    objects = [
        {"Key": "good.txt", "Size": 4, "LastModified": "2026-01-01T00:00:00Z"},
        {
            "Key": "bad-name",
            "Size": 4,
            "LastModified": "2026-01-01T00:00:00Z",
            "ETag": "bad-etag",
        },
    ]
    listing = list_objects_xml(objects).encode().replace(old, new)

    def respond(context: ResponderContext) -> HTTPResponse:
        if urlsplit(context.request.effective_path).path == "/":
            return HTTPResponse.raw(
                listing, headers={"Content-Type": "application/xml"}
            )
        return get_object_response(b"data")

    server.handler = respond
    result = await run_cli(
        aws_cli,
        ["s3", "cp", "s3://bucket/", str(destination), "--recursive"],
        env,
        timeout=20,
    )
    # XML forbids the character, so no object of the page downloads, even
    # one whose own fields are well-formed.
    assert_rejected_listing_page_fails(result, server, destination)


@pytest.mark.asyncio
async def test_cp_recursive_rejected_page_downloads_once_a_retry_parses(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    destination = tmp_path / "destination"
    objects = [
        {"Key": key, "Size": 4, "LastModified": "2026-01-01T00:00:00Z"}
        for key in ["a.txt", "b.txt"]
    ]
    listing = list_objects_xml(objects).encode()
    listings = 0

    def respond(context: ResponderContext) -> HTTPResponse:
        nonlocal listings
        if urlsplit(context.request.effective_path).path == "/":
            listings += 1
            # The first attempt's document is cut short.
            body = listing if listings > 1 else listing[: len(listing) // 2]
            return HTTPResponse.raw(
                body, headers={"Content-Type": "application/xml"}
            )
        return get_object_response(b"data")

    server.handler = respond
    _, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", "s3://bucket/", str(destination), "--recursive"],
        env,
        timeout=20,
    )
    assert rc == 0, stderr.decode()
    assert listings == 2
    assert sorted(p.name for p in destination.iterdir()) == ["a.txt", "b.txt"]
    assert (destination / "a.txt").read_bytes() == b"data"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "denial,error",
    [
        (
            ("AccessDenied", "Access Denied"),
            (
                b"(AccessDenied) when calling the ListObjectsV2 operation "
                b"(reached max retries: 2): Access Denied"
            ),
        ),
        (
            None,
            (
                b"(403) when calling the ListObjectsV2 operation "
                b"(reached max retries: 2): Forbidden"
            ),
        ),
    ],
    ids=["error-body", "bodiless"],
)
async def test_cp_recursive_error_at_a_page_last_attempt_names_the_retries(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    denial: tuple[str, str] | None,
    error: bytes,
) -> None:
    server, env = transfer_runtime
    destination = tmp_path / "destination"
    # botocore marks any error at the last attempt, one it does not retry
    # as well, so a denial after two rejected pages names both retries.
    denied = (
        error_response(*denial, 403)
        if denial is not None
        else HTTPResponse.raw(b"", status=403)
    )
    server.set_response_sequence(
        [xml_response("<html>oops"), xml_response("<html>oops"), denied]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", "s3://bucket/", str(destination), "--recursive"],
        env,
        timeout=20,
    )
    assert (rc, stdout) == (1, b""), stderr.decode()
    assert stderr == b"fatal error: An error occurred " + error + b"\n"
    assert len(server.requests) == 3
    assert list(destination.iterdir()) == []


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="Ctrl-C is a console event")
async def test_cp_recursive_ctrl_c_ends_a_rejected_page_retries(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    destination = tmp_path / "destination"
    process = await asyncio.create_subprocess_exec(
        aws_cli,
        *["s3", "cp", "s3://bucket/", str(destination), "--recursive"],
        env=command_environment({**env, "AWS_MAX_ATTEMPTS": "5"}),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        # A suite started in the background leaves SIGINT ignored, which
        # the CLI would inherit.
        preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL),
    )

    interrupted = False

    async def respond(context: ResponderContext) -> HTTPResponse:
        nonlocal interrupted
        # Ctrl-C arrives while the first page is on its way, and the page
        # is one botocore's parser rejects, so it cancels the retries.
        if not interrupted:
            interrupted = True
            process.send_signal(signal.SIGINT)
            await asyncio.sleep(0.2)
        return xml_response("<ListBucketResult><Contents>")

    server.handler = respond
    try:
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=20)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise
    # The routes word a Ctrl-C during the listing differently; only the
    # status and the attempts it ends are compared.
    assert process.returncode == 1, stderr.decode()
    assert len(server.requests) == 1
    assert [p for p in destination.rglob("*") if p.is_file()] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("symlink", [False, True], ids=["file", "symlink"])
async def test_cp_failed_download_preserves_existing_destination(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    symlink: bool,
) -> None:
    server, env = transfer_runtime
    destination = tmp_path / "destination"
    target = tmp_path / "original"
    target.write_bytes(b"original content")
    if symlink:
        destination.symlink_to(target)
    else:
        destination.write_bytes(b"original content")
    original_paths = set(tmp_path.iterdir())
    server.set_response_sequence(
        [
            head_object_response(7),
            error_response("AccessDenied", "no get", 403),
        ]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", "s3://bucket/key", str(destination), "--no-progress"],
        env,
    )
    assert rc == 1, stderr.decode()
    assert stdout == b""
    assert b"download failed:" in stderr
    assert b"AccessDenied" in stderr
    assert destination.read_bytes() == b"original content"
    assert destination.is_symlink() == symlink
    assert target.read_bytes() == b"original content"
    assert [r.method for r in server.requests] == ["HEAD", "GET"]
    assert set(tmp_path.iterdir()) == original_paths


async def download_after_get(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    source: str,
    destination: Path,
) -> bytes:
    server, env = transfer_runtime
    server.set_response_sequence(
        [head_object_response(7), get_object_response(b"payload")]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", source, str(destination), "--no-progress"],
        env,
    )
    assert rc == 1, stderr.decode()
    assert stdout == b""
    assert [r.method for r in server.requests] == ["HEAD", "GET"]
    return stderr


@pytest.mark.asyncio
async def test_cp_download_parent_reference_key_fails_after_get(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    directory = tmp_path / "directory"
    directory.mkdir()
    # Upstream joins a bare `..` basename to a directory destination, then
    # fails to rename its temp file onto the parent, after the GET. Native
    # reports the failed rename with its own diagnostic line.
    await download_after_get(
        aws_cli, transfer_runtime, "s3://bucket/prefix/..", directory
    )
    assert list(directory.iterdir()) == []


@pytest.mark.asyncio
async def test_cp_download_folder_marker_into_directory_fails_after_get(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    directory = tmp_path / "directory"
    directory.mkdir()
    original_paths = set(tmp_path.iterdir())
    # Upstream appends the marker's empty basename to the directory with its
    # trailing separator, so the temp file opens inside the directory and
    # the rename onto the directory fails, after the GET.
    stderr = await download_after_get(
        aws_cli, transfer_runtime, "s3://bucket/folder/", directory
    )
    assert list(directory.iterdir()) == []
    assert set(tmp_path.iterdir()) == original_paths
    destination = f"{directory}{os.sep}"
    assert stderr.decode().startswith(
        "download failed: s3://bucket/folder/ to "
        f"{os.path.relpath(directory)}{os.sep} "
    )
    assert stderr.decode().endswith(f"{destination!r}\n")
    # Upstream's Windows rename first removes the destination, and that
    # error names nothing else; the POSIX rename names the temp file too.
    if os.name != "nt":
        assert f": '{destination}." in stderr.decode()


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.name == "nt" or os.geteuid() == 0,
    reason="mode 600 does not deny directory search on Windows or to root",
)
async def test_cp_download_into_unsearchable_directory_fails_before_get(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    directory = tmp_path / "directory"
    directory.mkdir()
    destination = directory / "out"
    # Under a directory it cannot search, upstream's CRT client fails to
    # open the file it downloads into, before it sends the GET.
    server.set_response_sequence(
        [head_object_response(7), get_object_response(b"payload")]
    )
    directory.chmod(0o600)
    try:
        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", "s3://bucket/key", str(destination), "--no-progress"],
            env,
        )
    finally:
        directory.chmod(0o700)
    assert rc == 1, stderr.decode()
    assert stdout == b""
    assert [r.method for r in server.requests] == ["HEAD"]
    assert list(directory.iterdir()) == []
    assert stderr.decode().startswith(
        f"download failed: s3://bucket/key to {os.path.relpath(destination)} "
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "key,outside",
    [("prefix/../outside/..", ["outside"]), ("prefix/../", [])],
    ids=["sibling", "parent"],
)
async def test_cp_recursive_download_of_key_normalizing_to_parent_fails(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    key: str,
    outside: list[str],
) -> None:
    server, env = transfer_runtime
    work = tmp_path / "work"
    destination = work / "destination"
    destination.mkdir(parents=True)
    # Each key normalizes to a bare `..`, which the AWS CLI's parent-reference
    # check does not flag: the GET goes out and the rename onto `..` fails.
    # On the way, the AWS CLI creates the directory a key maps through, outside
    # the destination, and leaves it empty.
    objects = [{"Key": key, "Size": 7, "LastModified": "2026-01-01T00:00:00Z"}]
    server.set_response_sequence(
        [
            xml_response(list_objects_xml(objects)),
            get_object_response(b"payload"),
        ]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            "s3://bucket/prefix/",
            str(destination),
            "--recursive",
            "--no-progress",
        ],
        env,
    )
    assert sorted(path.name for path in work.iterdir()) == sorted(
        ["destination", *outside]
    )
    for name in outside:
        assert list((work / name).iterdir()) == []
    assert list(destination.iterdir()) == []
    assert [urlsplit(r.effective_path).path for r in server.requests[1:]] == [
        f"/{key}"
    ]
    assert rc == 1, stderr.decode()
    assert stdout == b""
    # The rest names the temp file the rename failed to move.
    assert stderr.decode().startswith(f"download failed: s3://bucket/{key} ")


@pytest.mark.asyncio
async def test_cp_download_sets_access_time_to_object_time(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    destination = tmp_path / "download"
    server.set_response_sequence(
        [
            head_object_response(
                7, **{"Last-Modified": "Sat, 01 Jan 2000 00:00:00 GMT"}
            ),
            get_object_response(b"payload"),
        ]
    )
    _, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", "s3://bucket/key", str(destination), "--no-progress"],
        env,
    )
    assert (rc, stderr) == (0, b"")
    # Stat before reading: reading the file can itself update its atime.
    stat = destination.stat()
    assert stat.st_mtime_ns == 946684800_000000000
    assert stat.st_atime_ns == 946684800_000000000
    assert destination.read_bytes() == b"payload"
    assert [request.method for request in server.requests] == ["HEAD", "GET"]


@pytest.mark.asyncio
async def test_cp_directory_upload_to_bucket_root_reports_empty_key(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    source = tmp_path / "directory"
    source.mkdir()
    server.set_default_response(put_object_response())
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", str(source), "s3://bucket/", "--no-progress"],
        env,
        timeout=20,
    )
    assert rc == 1, (stdout, stderr)
    assert not server.requests
    assert stdout == b""
    # An existing directory gains a trailing separator, so its basename is
    # empty. Python rejects the resulting empty key before attempting PUT.
    assert stderr.decode() == (
        f"upload failed: {os.path.relpath(source)}{os.sep} to s3://bucket/ "
        "Parameter validation failed:\n"
        "Invalid length for parameter Key, value: 0, valid min length: 1\n"
    )


@pytest.mark.asyncio
async def test_cp_recursive_nonempty_prefix_object_is_not_silently_skipped(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    destination = tmp_path / "download"
    server.set_response_sequence(
        [
            xml_response(
                list_objects_xml(
                    [
                        {
                            "Key": "prefix/",
                            "Size": 7,
                            "LastModified": "2026-01-01T00:00:00Z",
                        },
                    ]
                )
            ),
            get_object_response(b"payload"),
        ]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            "s3://bucket/prefix/",
            str(destination),
            "--recursive",
            "--no-progress",
        ],
        env,
    )
    assert [request.method for request in server.requests] == ["GET", "GET"]
    assert rc == 1, (stdout, stderr)
    assert b"download failed:" in stderr
    assert b"s3://bucket/prefix/" in stderr
    assert urlsplit(server.requests[1].effective_path).path == "/prefix/"
    assert destination.is_dir()
    assert list(destination.iterdir()) == []


@pytest.mark.asyncio
async def test_cp_recursive_repeated_continuation_token_cancels_downloads(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    # A transfer window of one leaves most of the listed objects waiting to
    # be submitted when the listing fails. The connections stay uncapped, so
    # the listing's pages never wait behind a held GET.
    Path(env["AWS_CONFIG_FILE"]).write_text(
        "[default]\ns3 =\n    max_in_flight = 1\n",
        encoding="utf-8",
    )
    destination = tmp_path / "download"
    pages = 0

    async def respond(context: ResponderContext) -> HTTPResponse:
        nonlocal pages
        if "list-type=" in context.request.effective_path:
            pages += 1
            return xml_response(
                list_objects_xml(
                    [
                        {
                            "Key": f"prefix/page{pages}-key{index}",
                            "Size": 1,
                            "LastModified": "2026-01-01T00:00:00Z",
                        }
                        for index in range(3)
                    ],
                    is_truncated=True,
                    next_continuation_token="same-token",
                )
            )
        # Hold each GET until the repeated token has failed the listing.
        await asyncio.sleep(1)
        return get_object_response(b"x")

    server.handler = respond
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            "s3://bucket/prefix/",
            str(destination),
            "--recursive",
            "--no-progress",
        ],
        env,
    )
    assert rc == 1, (stdout, stderr)
    # The pagination error cancels the transfers the listing started, so
    # none reports success and none leaves a file. Upstream's CRT client
    # reports each cancellation, in no fixed order, before the error.
    assert stdout == b""
    *cancelled, fatal = stderr.decode().splitlines(keepends=True)
    assert fatal == (
        "fatal error: Error during pagination: The same next token was "
        "received twice: {'ContinuationToken': 'same-token'}\n"
    )
    names = [f"page{page}-key{index}" for page in (1, 2) for index in range(3)]
    assert sorted(cancelled) == [
        f"download failed: s3://bucket/prefix/{name} to "
        f"{os.path.relpath(destination / name)} "
        "AWS_ERROR_S3_CANCELED: Request successfully cancelled\n"
        for name in names
    ]
    assert [path for path in destination.rglob("*") if path.is_file()] == []


@pytest.mark.asyncio
async def test_cp_recursive_repeated_long_continuation_token_is_reported_whole(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    # 5000 bytes, with a two-byte character across byte 4096.
    token = "a" * 4095 + "é" + "b" * 903
    server.set_default_response(
        xml_response(
            list_objects_xml(is_truncated=True, next_continuation_token=token)
        )
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            "s3://bucket/prefix/",
            str(tmp_path / "download"),
            "--recursive",
            "--no-progress",
        ],
        env,
    )
    assert rc == 1, (stdout, stderr)
    assert stdout == b""
    assert stderr.decode() == (
        "fatal error: Error during pagination: The same next token was "
        f"received twice: {{'ContinuationToken': '{token}'}}\n"
    )
    assert len(server.requests) == 2


# Upstream converts each listed object's LastModified to local time
# (utils.py:404-405), and dateutil's `tzlocal` takes it to `time.localtime`.
# On Windows the UCRT's `localtime_s` refuses a time before 1970, so the
# listing fails with `[Errno 22] Invalid argument` before any GET; native
# downloads the object there too.
@pytest.mark.asyncio
@pytest.mark.native_only(os.name == "nt")
async def test_cp_recursive_download_restores_pre_epoch_mtime(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    env["TZ"] = "UTC"
    destination = tmp_path / "download"
    server.set_response_sequence(
        [
            xml_response(
                list_objects_xml(
                    [
                        {
                            "Key": "prefix/key",
                            "Size": 7,
                            "LastModified": "1969-12-31T23:59:00Z",
                        },
                    ]
                )
            ),
            get_object_response(b"payload"),
        ]
    )
    _, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            "s3://bucket/prefix/",
            str(destination),
            "--recursive",
            "--no-progress",
        ],
        env,
    )
    assert (rc, stderr) == (0, b"")
    assert (destination / "key").read_bytes() == b"payload"
    assert (destination / "key").stat().st_mtime_ns == -60_000000000
    assert [request.method for request in server.requests] == ["GET", "GET"]


@pytest.mark.asyncio
@pytest.mark.skipif(os.name != "posix", reason="requires POSIX byte filenames")
async def test_cp_recursive_upload_rejects_non_utf8_object_key(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    source = tmp_path / "source"
    source.mkdir()
    invalid = source / os.fsdecode(b"invalid-\xff.txt")
    try:
        invalid.write_bytes(b"payload")
    except OSError as error:
        # APFS and HFS+ reject names that are not valid UTF-8.
        if error.errno != errno.EILSEQ:
            raise
        pytest.skip("filesystem rejects non-UTF-8 filenames")
    server.set_default_response(put_object_response())
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            str(source),
            "s3://bucket/",
            "--recursive",
            "--no-progress",
        ],
        env,
    )
    assert not server.requests
    assert rc == 1, (stdout, stderr)
    assert b"upload failed:" in stderr
    assert b"surrogates not allowed" in stderr
    assert stdout == b""
    assert invalid.read_bytes() == b"payload"


@pytest.mark.asyncio
@pytest.mark.skipif(os.name != "posix", reason="requires POSIX byte arguments")
@pytest.mark.parametrize(
    "flags,responses",
    [
        pytest.param(
            [],
            [
                head_object_response(len(DOWNLOAD_PAYLOAD)),
                get_object_response(DOWNLOAD_PAYLOAD),
            ],
            id="single",
        ),
        pytest.param(
            ["--recursive"],
            [xml_response(list_objects_xml([]))],
            id="recursive",
        ),
    ],
)
async def test_cp_download_refuses_non_utf8_source_before_any_request(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    flags: list[str],
    responses: list[HTTPResponse],
) -> None:
    server, env = transfer_runtime
    server.set_response_sequence(responses)
    destination = tmp_path / "out"
    destination.mkdir()
    source = "s3://bucket/key-" + os.fsdecode(b"\xff")
    result = await run_cli(
        aws_cli, ["s3", "cp", source, str(destination), *flags], env
    )
    assert_refused_before_request(result, server)
    assert not any(destination.iterdir())


@pytest.mark.asyncio
@pytest.mark.skipif(os.name != "posix", reason="requires POSIX byte arguments")
@pytest.mark.parametrize(
    "flags", [[], ["--recursive"]], ids=["single", "recursive"]
)
async def test_cp_download_non_utf8_source_outranks_client_failure(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    flags: list[str],
) -> None:
    server, env = transfer_runtime
    # The CRT client cannot load this bundle, and it ignores the queue size.
    bundle = tmp_path / "bundle.pem"
    bundle.write_text("not a certificate\n", encoding="utf-8")
    env["AWS_CA_BUNDLE"] = str(bundle)
    Path(env["AWS_CONFIG_FILE"]).write_text(
        "[default]\ns3 =\n"
        "    preferred_transfer_client = crt\n"
        "    max_queue_size = 5\n",
        encoding="utf-8",
    )
    destination = tmp_path / "out"
    destination.mkdir()
    source = "s3://bucket/key-" + os.fsdecode(b"\xff")
    result = await run_cli(
        aws_cli, ["s3", "cp", source, str(destination), *flags], env
    )
    assert_refused_before_request(result, server)
    assert not any(destination.iterdir())


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.name != "posix" or os.geteuid() == 0,
    reason="requires unprivileged POSIX permission checks",
)
async def test_cp_recursive_upload_skips_unreadable_subdirectory(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    source = tmp_path / "source"
    blocked = source / "blocked"
    blocked.mkdir(parents=True)
    (blocked / "hidden.txt").write_bytes(b"hidden")
    (source / "visible.txt").write_bytes(b"visible")
    server.set_default_response(put_object_response())
    blocked.chmod(0o000)
    try:
        stdout, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                str(source),
                "s3://bucket/",
                "--recursive",
                "--no-progress",
            ],
            env,
        )
    finally:
        blocked.chmod(0o700)
    assert rc == 2, (stdout, stderr)
    assert b"warning: Skipping file" in stderr
    assert b"blocked" in stderr
    assert b"File/Directory is not readable" in stderr
    assert [
        (request.method, urlsplit(request.effective_path).path)
        for request in server.requests
    ] == [("PUT", "/visible.txt")]
    assert completion_lines(stdout) == [
        f"upload: {os.path.relpath(source / 'visible.txt')} "
        "to s3://bucket/visible.txt"
    ]


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.name != "posix" or os.geteuid() == 0,
    reason="requires unprivileged POSIX permission checks",
)
@pytest.mark.parametrize(
    ("flags", "warned"),
    [
        pytest.param(["--no-progress"], True, id="default"),
        pytest.param(["--quiet"], False, id="quiet"),
    ],
)
async def test_cp_recursive_upload_skips_unreadable_root(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    flags: list[str],
    warned: bool,
) -> None:
    server, env = transfer_runtime
    source = tmp_path / "source"
    source.mkdir()
    (source / "hidden.txt").write_bytes(b"hidden")
    server.set_default_response(put_object_response())
    source.chmod(0o000)
    try:
        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(source), "s3://bucket/", "--recursive", *flags],
            env,
        )
    finally:
        source.chmod(0o700)
    assert rc == 2, (stdout, stderr)
    assert stdout == b""
    warning = (
        f"warning: Skipping file {source}{os.sep}. "
        "File/Directory is not readable.\n"
    ).encode()
    assert stderr == (warning if warned else b"")
    assert not server.requests


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.name != "posix" or os.geteuid() == 0,
    reason="requires unprivileged POSIX permission checks",
)
async def test_cp_recursive_upload_skips_root_below_unsearchable_directory(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    # The operand exists through the link, but the root it normalizes to
    # lies below a directory that denies the search, so the existence check
    # the walk makes first fails.
    server, env = transfer_runtime
    (tmp_path / "real" / "a").mkdir(parents=True)
    (tmp_path / "real" / "blocked" / "root").mkdir(parents=True)
    (tmp_path / "real" / "blocked" / "root" / "file.txt").write_bytes(b"x")
    blocked = tmp_path / "blocked"
    (blocked / "root").mkdir(parents=True)
    (tmp_path / "link").symlink_to(Path("real") / "a")
    source = os.path.join(tmp_path, "link", os.pardir, "blocked", "root")
    server.set_default_response(put_object_response())
    blocked.chmod(0o000)
    try:
        stdout, stderr, rc = await run_cli(
            aws_cli,
            [
                "s3",
                "cp",
                source,
                "s3://bucket/",
                "--recursive",
                "--no-progress",
            ],
            env,
        )
    finally:
        blocked.chmod(0o700)
    assert rc == 2, (stdout, stderr)
    assert stdout == b""
    warning = (
        f"warning: Skipping file {blocked / 'root'}{os.sep}. "
        "File does not exist.\n"
    ).encode()
    assert stderr == warning
    assert not server.requests


@pytest.mark.asyncio
# On Windows the open itself fails, and both routes report the errno the host
# maps that refusal to, so there is no fixed text to expect.
@pytest.mark.skipif(
    os.name != "posix",
    reason="Windows reports the host's directory-open error, not EISDIR",
)
@pytest.mark.parametrize(
    "name",
    [
        pytest.param("d", id="directory"),
        pytest.param(f"d{os.sep}", id="trailing-separator"),
        pytest.param("link", id="symlink"),
    ],
)
@pytest.mark.parametrize(
    ("flags", "reported"),
    [
        pytest.param(["--no-progress"], True, id="default"),
        pytest.param(["--quiet"], False, id="quiet"),
    ],
)
async def test_cp_upload_of_directory_fails_opening_it(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    name: str,
    flags: list[str],
    reported: bool,
) -> None:
    # Upstream queues the directory as a file, and its CRT client fails to
    # read it as the body, an error the CRT reports with no code.
    server, env = transfer_runtime
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "file.txt").write_bytes(b"x")
    (tmp_path / "link").symlink_to("d")
    server.set_default_response(put_object_response())
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            os.path.join(str(tmp_path), name),
            "s3://bucket/key",
            "--endpoint-url",
            server.url,
            *flags,
        ],
        env,
    )
    assert rc == 1, (stdout, stderr)
    assert stdout == b""
    # The path stays lexical, so the link keeps its own name.
    source = tmp_path / name.rstrip(os.sep)
    line = (
        f"upload failed: {os.path.relpath(source)}{os.sep} to s3://bucket/key "
        "Unknown Error Code: Unknown Error Code\n"
    ).encode()
    assert stderr == (line if reported else b"")
    assert not server.requests


@pytest.mark.asyncio
async def test_cp_multipart_download_conditions_gets_on_the_command_head_etag(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    destination = tmp_path / "download"
    head_calls = 0

    def respond(context: ResponderContext) -> HTTPResponse:
        nonlocal head_calls
        # The object changes after the command's HEAD, which reports no
        # checksum of it. Upstream's CRT client conditions every GET on the
        # command's ETag, and, as the object has no full-object checksum,
        # validates each part alone and sends no HEAD of its own
        # (s3transfer/crt.py `_get_make_request_args_get_object`). A second
        # HEAD would see the changed ETag.
        if context.request.method == "HEAD":
            head_calls += 1
            etag = '"original"' if head_calls == 1 else '"changed"'
            return head_object_response(9 * 1024 * 1024, ETag=etag)
        # Only the request condition is under test; stop before body transfer.
        return error_response("AccessDenied", "GET blocked by test", 403)

    server.handler = respond
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", "s3://bucket/key", str(destination), "--no-progress"],
        env,
    )
    assert rc == 1, (stdout, stderr)
    assert server.requests[0].method == "HEAD"
    gets = [request for request in server.requests if request.method == "GET"]
    assert gets
    assert [request.headers.get("if-match") for request in gets] == [
        '"original"'
    ] * len(gets)
    assert head_calls == 1
    assert not destination.exists()


THRESHOLD_CONFIG = "[default]\ns3 =\n  multipart_threshold = 8MB\n"
CRT_PREFERRED_CONFIG = (
    "[default]\ns3 =\n  preferred_transfer_client = crt\n"
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("config", "size", "conditioned"),
    [
        pytest.param(THRESHOLD_CONFIG, 8 * MIB, False, id="at-threshold"),
        pytest.param(
            THRESHOLD_CONFIG, 8 * MIB + 1, True, id="above-threshold"
        ),
        pytest.param(CRT_PREFERRED_CONFIG, 8 * MIB, True, id="no-threshold"),
    ],
)
async def test_cp_download_is_conditioned_when_the_crt_splits_it(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    config: str,
    size: int,
    conditioned: bool,
) -> None:
    # The CRT client gets an object no larger than the multipart threshold
    # with one unconditioned GET, and conditions every GET of a larger one
    # (s3transfer/crt.py `_should_download_in_single_request`). The
    # threshold is set here: unset, it defaults to 8 MiB only on a host the
    # CRT is not tuned for, and a CRT-preferred client, like one on a tuned
    # host, has none, so it conditions every download
    # (customizations/s3/factory.py `_create_crt_transfer_config`).
    server, env = transfer_runtime
    Path(env["AWS_CONFIG_FILE"]).write_text(config, encoding="utf-8")
    destination = tmp_path / "download"

    def respond(context: ResponderContext) -> HTTPResponse:
        if context.request.method == "HEAD":
            return head_object_response(size, ETag='"original"')
        return error_response("AccessDenied", "GET blocked by test", 403)

    server.handler = respond
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", "s3://bucket/key", str(destination), "--no-progress"],
        env,
    )
    assert rc == 1, (stdout, stderr)
    gets = [request for request in server.requests if request.method == "GET"]
    assert gets
    expected = '"original"' if conditioned else None
    assert [request.headers.get("if-match") for request in gets] == [
        expected
    ] * len(gets)


def listing_with_checksum(etag: str, size: int, checksum: str) -> HTTPResponse:
    """A listing of one object, `key`, with its ETag and checksum fields."""
    return xml_response(
        '<?xml version="1.0" ?>'
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        "<Prefix/><IsTruncated>false</IsTruncated><Contents><Key>key</Key>"
        f"<Size>{size}</Size><LastModified>2026-01-02T03:04:05.000Z"
        f"</LastModified><ETag>{etag}</ETag>{checksum}</Contents>"
        "</ListBucketResult>"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("checksum", "crt_heads"),
    [
        pytest.param("", 0, id="none"),
        pytest.param(
            "<ChecksumAlgorithm>CRC32</ChecksumAlgorithm>"
            "<ChecksumType>COMPOSITE</ChecksumType>",
            0,
            id="composite",
        ),
        pytest.param(
            "<ChecksumAlgorithm>CRC64NVME</ChecksumAlgorithm>"
            "<ChecksumType>FULL_OBJECT</ChecksumType>",
            1,
            id="full-object",
        ),
        pytest.param(
            "<ChecksumAlgorithm>CRC32</ChecksumAlgorithm>", 1, id="algorithm"
        ),
    ],
)
async def test_cp_recursive_multipart_download_conditions_gets_on_the_listed_etag(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    checksum: str,
    crt_heads: int,
) -> None:
    # A listed object's GETs are conditioned on the ETag its listing
    # reported. A listing names no checksum value, so a validating CRT
    # client looks the object up itself only when the listing shows it may
    # have a full-object checksum (s3handler.py
    # `_may_have_full_object_checksum`); otherwise it validates each part
    # alone.
    server, env = transfer_runtime
    destination = tmp_path / "download"
    size = 9 * MIB

    def respond(context: ResponderContext) -> HTTPResponse:
        query = parse_qs(urlsplit(context.request.effective_path).query)
        if context.request.method == "GET" and "list-type" in query:
            return listing_with_checksum("&quot;listed&quot;", size, checksum)
        if context.request.method == "HEAD":
            return head_object_response(size, ETag='"listed"')
        return error_response("AccessDenied", "GET blocked by test", 403)

    server.handler = respond
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            "s3://bucket/",
            str(destination),
            "--recursive",
            "--no-progress",
        ],
        env,
    )
    assert rc == 1, (stdout, stderr)
    gets = [
        request
        for request in server.requests[1:]
        if request.method == "GET"
    ]
    assert gets
    assert [request.headers.get("if-match") for request in gets] == [
        '"listed"'
    ] * len(gets)
    heads = [request for request in server.requests if request.method == "HEAD"]
    assert [request.headers.get("x-amz-checksum-mode") for request in heads] == [
        "enabled"
    ] * crt_heads


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "error"),
    [
        pytest.param(
            "GET",
            "An error occurred (PreconditionFailed) when calling the GetObject "
            "operation: At least one of the pre-conditions you specified did "
            "not hold",
            id="get",
        ),
        pytest.param(
            "HEAD",
            "An error occurred (412) when calling the HeadObject operation: "
            "Precondition Failed",
            id="crt-head",
        ),
    ],
)
async def test_cp_multipart_download_reports_a_failed_condition(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    operation: str,
    error: str,
) -> None:
    # The listed object changed: a GET, or the HeadObject the CRT client
    # sends to learn its full-object checksum, fails its condition. The
    # download fails with the service's error, as upstream's CRT client
    # reports any other.
    server, env = transfer_runtime
    destination = tmp_path / "download"
    size = 9 * MIB
    checksum = (
        "<ChecksumAlgorithm>CRC64NVME</ChecksumAlgorithm>"
        "<ChecksumType>FULL_OBJECT</ChecksumType>"
    )

    def respond(context: ResponderContext) -> HTTPResponse:
        query = parse_qs(urlsplit(context.request.effective_path).query)
        if context.request.method == "GET" and "list-type" in query:
            return listing_with_checksum("&quot;listed&quot;", size, checksum)
        if context.request.method == operation:
            return error_response(
                "PreconditionFailed",
                "At least one of the pre-conditions you specified did not hold",
                412,
            )
        if context.request.method == "HEAD":
            return head_object_response(size, ETag='"listed"')
        return error_response("AccessDenied", "GET blocked by test", 403)

    server.handler = respond
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            "s3://bucket/",
            str(destination),
            "--recursive",
            "--no-progress",
        ],
        env,
    )
    shown = os.path.relpath(destination / "key")
    line = f"download failed: s3://bucket/key to {shown} {error}\n"
    assert (rc, stdout, stderr.decode()) == (1, b"", line)
    assert not (destination / "key").exists()


@pytest.mark.asyncio
async def test_cp_missing_head_last_modified_fails_before_get(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    destination = tmp_path / "download"
    server.set_response_sequence(
        [
            HTTPResponse.raw(
                b"",
                status=200,
                headers={"Content-Length": "7", "ETag": '"original"'},
            ),
            get_object_response(b"payload"),
        ]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", "s3://bucket/key", str(destination), "--no-progress"],
        env,
    )
    assert rc == 1, (stdout, stderr)
    assert b"LastModified" in stderr
    assert stdout == b""
    assert [request.method for request in server.requests] == ["HEAD"]
    assert not destination.exists()


LARGE_OBJECT_SIZE = 65 * 1024 * 1024


def null_key_responder(key: str, body: bytes):
    """Lists `key` URL-encoded, the only way a NUL reaches the CLI, and serves
    `body` to its GETs, ranged or not."""
    listing = list_objects_xml(
        [
            {
                "Key": quote(key, safe="/"),
                "Size": len(body),
                "LastModified": "2026-01-01T00:00:00Z",
            }
        ]
    ).replace("<Prefix/>", "<Prefix/><EncodingType>url</EncodingType>", 1)

    def respond(context: ResponderContext) -> HTTPResponse:
        if "list-type=2" in urlsplit(context.request.effective_path).query:
            return xml_response(listing)
        return object_response(context.request, body)

    return respond


def object_response(
    request: RecordedHTTPRequest, body: bytes
) -> HTTPResponse:
    """Serves `body` to a GET, ranged or not."""
    byte_range = request.headers.get("range")
    if byte_range is None:
        return get_object_response(body)
    first, last = byte_range.removeprefix("bytes=").split("-")
    start, end = int(first), min(int(last), len(body) - 1)
    return HTTPResponse.raw(
        body[start : end + 1],
        status=206,
        headers={
            "Content-Length": str(end - start + 1),
            "Content-Range": f"bytes {start}-{end}/{len(body)}",
            "ETag": '"foo-1"',
        },
    )


def write_download_writer(env: dict[str, str], writer: str | None) -> None:
    """Selects the native `download_writer`, or leaves the default."""
    if writer is not None:
        Path(env["AWS_CONFIG_FILE"]).write_text(
            f"[default]\ns3 =\n    download_writer = {writer}\n", encoding="utf-8"
        )


async def run_null_key_download(
    aws_cli: str, env: dict[str, str], destination: Path, *extra: str
) -> None:
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            "s3://bucket/",
            str(destination),
            "--recursive",
            "--no-progress",
            *extra,
        ],
        env,
    )
    assert rc == 1, stderr
    assert stdout == b""
    assert stderr


@pytest.mark.asyncio
@pytest.mark.skipif(os.name != "posix", reason="creates a symlink")
@pytest.mark.parametrize(
    "no_overwrite", [False, True], ids=["overwrite", "no-overwrite"]
)
@pytest.mark.parametrize("prefix", ["file", "symlink"])
@pytest.mark.parametrize(
    "size,writer",
    [
        (0, None),
        (7, None),
        (LARGE_OBJECT_SIZE, None),
        (7, "pwrite"),
        (LARGE_OBJECT_SIZE, "crt"),
    ],
    ids=["empty", "small", "large", "small-pwrite", "large-crt"],
)
async def test_cp_recursive_download_null_key_leaves_prefix_file(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    size: int,
    writer: str | None,
    prefix: str,
    no_overwrite: bool,
) -> None:
    server, env = transfer_runtime
    write_download_writer(env, writer)
    destination = tmp_path / "destination"
    destination.mkdir()
    # The C library would open the path cut at the NUL, which names the
    # existing `report`, or the target outside the root its symlink names.
    target = tmp_path / "outside"
    target.write_bytes(b"original")
    report = destination / "report"
    if prefix == "symlink":
        report.symlink_to(target)
    else:
        report.write_bytes(b"original")
    original_paths = set(tmp_path.iterdir())
    server.handler = null_key_responder("report\x00.backup", b"x" * size)
    extra = ["--no-overwrite"] if no_overwrite else []
    await run_null_key_download(aws_cli, env, destination, *extra)
    assert report.is_symlink() == (prefix == "symlink")
    assert report.read_bytes() == b"original"
    assert target.read_bytes() == b"original"
    assert set(tmp_path.iterdir()) == original_paths
    assert list(destination.iterdir()) == [report]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "key",
    ["dir\x00x/report", "a" * 237 + "\x00.backup", "a" * 248 + "\x00.backup"],
    ids=["parent", "name", "past-temp-name"],
)
async def test_cp_recursive_download_null_key_leaves_other_files(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    key: str,
) -> None:
    server, env = transfer_runtime
    destination = tmp_path / "destination"
    destination.mkdir()
    # A NUL in a parent, or in a name within or past what the temp name
    # keeps, fails the download and leaves the file its prefix names.
    existing = destination / key.split("\x00")[0]
    existing.write_bytes(b"original")
    server.handler = null_key_responder(key, b"payload")
    await run_null_key_download(aws_cli, env, destination)
    assert list(destination.iterdir()) == [existing]
    assert existing.read_bytes() == b"original"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "listed_size,body,settings",
    [
        (7, b"hello", {"download_writer": "pwrite"}),
        (5, b"hello world", {"download_writer": "pwrite"}),
        (
            LARGE_OBJECT_SIZE,
            b"x" * (LARGE_OBJECT_SIZE - MIB),
            {"multipart_threshold": "128MB"},
        ),
    ],
    ids=["shorter", "longer", "shorter-large"],
)
async def test_cp_recursive_download_commits_object_resized_after_listing(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    listed_size: int,
    body: bytes,
    settings: dict[str, str],
) -> None:
    server, env = transfer_runtime
    # The object is replaced between the listing and its one GET, which
    # returns the whole new object. Upstream commits it, as the native
    # route must, even when the listed size chose its native writer.
    nested = "".join(
        f"    {name} = {value}\n" for name, value in settings.items()
    )
    Path(env["AWS_CONFIG_FILE"]).write_text(
        f"[default]\ns3 =\n{nested}", encoding="utf-8"
    )
    listing = list_objects_xml(
        [
            {
                "Key": "key",
                "Size": listed_size,
                "LastModified": "2026-01-01T00:00:00Z",
            }
        ]
    )

    def respond(context: ResponderContext) -> HTTPResponse:
        if "list-type=2" in urlsplit(context.request.effective_path).query:
            return xml_response(listing)
        return object_response(context.request, body)

    server.handler = respond
    destination = tmp_path / "destination"
    destination.mkdir()
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            "s3://bucket/",
            str(destination),
            "--recursive",
            "--no-progress",
        ],
        env,
    )
    assert rc == 0, stderr
    assert stderr == b""
    assert stdout.startswith(b"download: s3://bucket/key to "), stdout
    assert list(destination.iterdir()) == [destination / "key"]
    assert (destination / "key").read_bytes() == body


@pytest.mark.asyncio
async def test_cp_recursive_upload_of_regular_file_warns_and_skips(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    source = tmp_path / "source.txt"
    source.write_bytes(b"payload")
    server.set_default_response(put_object_response())
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            str(source),
            "s3://bucket/",
            "--recursive",
            "--no-progress",
        ],
        env,
        timeout=20,
    )
    assert rc == 2, (stdout, stderr)
    assert stdout == b""
    assert (
        stderr
        == (
            f"warning: Skipping file {source}{os.sep}. File does not exist.\n"
        ).encode()
    )
    assert not server.requests
    assert source.read_bytes() == b"payload"


@pytest.mark.asyncio
async def test_cp_recursive_empty_listing_preserves_regular_file_destination(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
) -> None:
    server, env = transfer_runtime
    destination = tmp_path / "destination"
    # Upstream creates only a missing destination. An existing file stays
    # untouched unless a downloaded object needs a parent directory there.
    destination.write_bytes(b"original content")
    server.set_default_response(xml_response(list_objects_xml()))
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            "s3://bucket/",
            str(destination),
            "--recursive",
            "--no-progress",
        ],
        env,
        timeout=20,
    )
    assert (rc, stdout, stderr) == (0, b"", b"")
    assert destination.read_bytes() == b"original content"
    assert [request.method for request in server.requests] == ["GET"]


@pytest.mark.asyncio
@pytest.mark.parametrize("tail", [3, 2], ids=["odd-tail", "even-tail"])
async def test_cp_streaming_multipart_upload_stores_the_whole_file(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    tail: int,
) -> None:
    server, env = transfer_runtime
    # A streaming reader has sent an odd final part empty; an even tail is
    # the control.
    Path(env["AWS_CONFIG_FILE"]).write_text(
        "[default]\n"
        "s3 =\n"
        "  should_stream = true\n"
        "  multipart_threshold = 8MB\n"
        "  multipart_chunksize = 8MB\n",
        encoding="utf-8",
    )
    source = tmp_path / "stream.bin"
    size = 17 * MIB + tail
    # A 251-byte cycle doesn't divide a part, so a misplaced part shows.
    body = (bytes(range(251)) * (size // 251 + 1))[:size]
    source.write_bytes(body)
    responder = MultipartUploadResponder()
    server.handler = responder
    stdout, _, rc = await run_cli(
        aws_cli,
        ["s3", "cp", str(source), "s3://bucket/key", "--no-progress"],
        env,
    )
    # One comparison, so a failed upload shows its exit status beside the
    # requests, the part sizes, and the errors the server answered with.
    assert {
        "exit status": rc,
        "requests": [multipart_operation(r) for r in server.requests],
        "part sizes": responder.part_sizes(),
        "server errors": responder.errors,
    } == {
        "exit status": 0,
        "requests": [
            "CreateMultipartUpload",
            "UploadPart",
            "UploadPart",
            "UploadPart",
            "CompleteMultipartUpload",
        ],
        "part sizes": {1: 8 * MIB, 2: 8 * MIB, 3: MIB + tail},
        "server errors": [],
    }
    assert {urlsplit(r.effective_path).path for r in server.requests} == {
        "/key"
    }
    assert completion_lines(stdout) == [
        f"upload: {os.path.relpath(source)} to s3://bucket/key"
    ]
    assert responder.completed_parts == [1, 2, 3]
    # Compare digests so a mismatch doesn't diff 17 MiB of bytes.
    assert responder.stored is not None
    assert (
        hashlib.sha256(responder.stored).hexdigest()
        == hashlib.sha256(body).hexdigest()
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(("stdout_kind", "exception", "text"), FAILING_STDOUTS)
async def test_cp_upload_failed_stdout_write_is_reported_at_exit_with_120(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    upload_source: Path,
    stdout_kind: str,
    exception: str,
    text: str,
) -> None:
    server, env = transfer_runtime
    server.set_default_response(put_object_response())
    with failing_stream(stdout_kind) as stdout:
        stderr, rc = await run_cli_with_stdout(
            aws_cli,
            ["s3", "cp", str(upload_source), "s3://bucket/key"],
            env,
            stdout,
        )
    # The result printer swallows the write's error and the upload finishes;
    # only CPython's flush of stdout at exit reports it.
    assert (rc, stderr.decode()) == (
        120,
        f"Exception ignored while flushing sys.stdout:\n{exception}: {text}\n",
    )
    assert [r.method for r in server.requests] == ["PUT"]


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="requires a POSIX shell")
async def test_cp_upload_stdout_closed_at_start_uploads_silently(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    upload_source: Path,
) -> None:
    server, env = transfer_runtime
    server.set_default_response(put_object_response())
    stderr, rc = await run_cli_without_stdout(
        aws_cli, ["s3", "cp", str(upload_source), "s3://bucket/key"], env
    )
    # The result printer swallows each write to CPython's None stdout, and
    # nothing is flushed at exit, so the command keeps its status.
    assert (rc, stderr) == (0, b"")
    assert [r.method for r in server.requests] == ["PUT"]


@pytest.mark.asyncio
@pytest.mark.parametrize("stderr_kind", FAILING_STDERRS)
async def test_cp_missing_source_report_stderr_refuses_exits_1(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    stderr_kind: str,
) -> None:
    server, env = transfer_runtime
    with failing_stream(stderr_kind) as stderr:
        rc = await run_cli_with_streams(
            aws_cli,
            ["s3", "cp", str(tmp_path / "missing.txt"), "s3://bucket/key"],
            env,
            asyncio.subprocess.DEVNULL,
            stderr,
        )
    # The general handler's write raises out of the AWS CLI's main, and the
    # release's launcher returns 1 instead of the handler's 255.
    assert rc == 1
    assert not server.requests


@pytest.mark.asyncio
@pytest.mark.parametrize("stderr_kind", FAILING_STDERRS)
async def test_cp_upload_failure_stderr_refuses_exits_120(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    upload_source: Path,
    stderr_kind: str,
) -> None:
    server, env = transfer_runtime
    server.set_default_response(
        error_response("AccessDenied", "denied by test", 403)
    )
    with failing_stream(stderr_kind) as stderr:
        rc = await run_cli_with_streams(
            aws_cli,
            ["s3", "cp", str(upload_source), "s3://bucket/key"],
            env,
            asyncio.subprocess.DEVNULL,
            stderr,
        )
    # The result printer swallows its failed write of `upload failed:`, and
    # the command returns 1. CPython's flush at exit of the line stderr kept
    # fails again, and `Py_Exit` makes the status 120.
    assert rc == 120
    assert [r.method for r in server.requests] == ["PUT"]
