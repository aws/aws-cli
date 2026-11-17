"""How many attempts `s3 ls` and `s3 cp` make, and what they report.

Each test runs one command against a ScriptedS3 bucket (s3store.py) that
answers the first requests of one operation with botocore's 500
InternalError or with a 429, or loses the connection partway through a
response body, and asserts the attempts the bucket answered, the result
lines, the exit status, and what was moved.

`s3 ls` retries through botocore's standard retry mode, 3 attempts unless
max_attempts says otherwise (botocore/retries/standard.py). `s3 cp`
transfers through the CRT client, whose retries the AWS CLI configures
from max_attempts only where it sets the client up with the classic
client's defaults: on a host the CRT is not tuned for, or when max_attempts
is set (customizations/s3/factory.py:253-259, 431-435). Otherwise the
client keeps the CRT's own 5 retries (aws-c-s3 s3_client.c
s_default_max_retries).
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import awscrt.s3
import pytest
from localstub import HTTPResponse

from awswire import ReconstructedRequest
from credhelpers import run_command
from s3store import (
    ObjectKey,
    ScriptedS3,
    ScriptedTransmission,
    decoded,
    pattern_bytes,
    read_tree,
    s3_runtime,
    write_tree,
)

pytestmark = pytest.mark.asyncio

BUCKET: Final = "bucket"
MIB: Final = 1024 * 1024
LISTED_TIME: Final = "2026-01-02 03:04:05"
DOWNLOAD_BODY: Final = pattern_bytes("object", 2048)
UPLOAD_FILE: Final = pattern_bytes("upload", 3000)
SEED_OBJECTS: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, "download/object.txt"): DOWNLOAD_BODY,
    (BUCKET, "tree/a.txt"): pattern_bytes("tree a", 100),
    (BUCKET, "tree/b.txt"): pattern_bytes("tree b", 1500),
}
# More failures than any case allows attempts, so every attempt fails.
EXHAUSTING: Final = 1000
# The attempts the CRT client makes when the AWS CLI leaves its retries
# alone: its first and 5 retries.
CRT_DEFAULT_ATTEMPTS: Final = 6
# The attempts `s3 cp` makes when nothing sets max_attempts: botocore's 3
# where the AWS CLI applies the classic defaults, else the CRT's own.
DEFAULT_TRANSFER_ATTEMPTS: Final = (
    CRT_DEFAULT_ATTEMPTS if awscrt.s3.is_optimized_for_system() else 3
)
INTERNAL_ERROR_MESSAGE: Final = (
    "We encountered an internal error. Please try again."
)
CRT_CONFIG: Final = "[default]\ns3 =\n  preferred_transfer_client = crt\n"


@dataclass(frozen=True)
class Command:
    name: str
    arguments: tuple[str, ...]
    stdout: str
    local_files: Mapping[str, bytes] = field(default_factory=dict[str, bytes])
    downloaded_files: Mapping[str, bytes] = field(
        default_factory=dict[str, bytes]
    )
    uploaded_objects: Mapping[ObjectKey, bytes] = field(
        default_factory=dict[ObjectKey, bytes]
    )


LS: Final = Command(
    "ls",
    ("s3", "ls", f"s3://{BUCKET}/tree/", "--recursive"),
    f"{LISTED_TIME}        100 tree/a.txt\n"
    f"{LISTED_TIME}       1500 tree/b.txt\n",
)
DOWNLOAD: Final = Command(
    "download",
    (
        "s3",
        "cp",
        f"s3://{BUCKET}/download/object.txt",
        "object.txt",
        "--no-progress",
    ),
    f"download: s3://{BUCKET}/download/object.txt to .{os.sep}object.txt\n",
    downloaded_files={"object.txt": DOWNLOAD_BODY},
)
UPLOAD: Final = Command(
    "upload",
    (
        "s3",
        "cp",
        "upload.txt",
        f"s3://{BUCKET}/up/upload.txt",
        "--no-progress",
    ),
    f"upload: .{os.sep}upload.txt to s3://{BUCKET}/up/upload.txt\n",
    local_files={"upload.txt": UPLOAD_FILE},
    uploaded_objects={(BUCKET, "up/upload.txt"): UPLOAD_FILE},
)


@dataclass(frozen=True)
class Run:
    returncode: int
    stdout: str
    stderr: str
    local_files: dict[str, bytes]
    store: ScriptedS3

    def describe(self) -> str:
        return (
            f"exit {self.returncode}\n"
            f"stdout: {self.stdout!r}\n"
            f"stderr: {self.stderr!r}\n"
            f"responses: {self.store.responses}\n"
            f"failures: {self.store.failures}\n"
        )

    def attempts(self, operation: str) -> int:
        return self.store.operations().count(operation)


async def run_aws(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    store: ScriptedS3,
    *,
    local_files: Mapping[str, bytes] | None = None,
    environment: Mapping[str, str] | None = None,
    config: str = "",
    plain_endpoint: bool = False,
) -> Run:
    """Run `aws <arguments>` once in tmp_path/work against `store`.

    The TLS intercept proxy relays a response only once it has read all
    of it, so a body cut short never reaches the CLI as one. A cut needs
    `plain_endpoint`: the bucket's own plain-HTTP address, reached
    directly.
    """
    work = tmp_path / "work"
    work.mkdir()
    write_tree(work, local_files or {})
    async with s3_runtime(store, tmp_path) as (server, env):
        server.set_transmission_strategy(ScriptedTransmission(store))
        Path(env["AWS_CONFIG_FILE"]).write_text(config, encoding="utf-8")
        env.update(environment or {})
        endpoint: list[str] = []
        if plain_endpoint:
            endpoint = ["--endpoint-url", server.url.rstrip("/")]
            env["NO_PROXY"] = "127.0.0.1"
        stdout, stderr, returncode = await run_command(
            [aws_cli, *arguments, *endpoint], env, cwd=work, stdin=None
        )
    return Run(
        returncode=returncode,
        stdout=decoded(stdout),
        stderr=decoded(stderr),
        local_files=read_tree(work),
        store=store,
    )


def listing_error(retries: int) -> str:
    """botocore's ClientError once every attempt failed (exceptions.py)."""
    return (
        "\naws: [ERROR]: An error occurred (InternalError) when calling the "
        f"ListObjectsV2 operation (reached max retries: {retries}): "
        f"{INTERNAL_ERROR_MESSAGE}\n"
    )


@pytest.mark.parametrize(
    ("environment", "failures", "attempts", "stderr"),
    [
        pytest.param({}, 1, 2, "", id="default-once"),
        pytest.param({}, EXHAUSTING, 3, listing_error(2), id="default"),
        pytest.param(
            {"AWS_MAX_ATTEMPTS": "2"}, EXHAUSTING, 2, listing_error(1), id="2"
        ),
        pytest.param(
            {"AWS_MAX_ATTEMPTS": "5"}, EXHAUSTING, 5, listing_error(4), id="5"
        ),
    ],
)
async def test_ls_retries_internal_errors_up_to_max_attempts(
    aws_cli: str,
    tmp_path: Path,
    environment: dict[str, str],
    failures: int,
    attempts: int,
    stderr: str,
) -> None:
    store = ScriptedS3(
        SEED_OBJECTS,
        failing=frozenset({"ListObjectsV2"}),
        failures=failures,
    )
    run = await run_aws(
        aws_cli, tmp_path, LS.arguments, store, environment=environment
    )
    report = run.describe()
    assert store.failures == [], report
    assert run.attempts("ListObjectsV2") == attempts, report
    if failures < attempts:
        assert (run.returncode, run.stdout, run.stderr) == (
            0,
            LS.stdout,
            "",
        ), report
    else:
        # botocore's ClientError status (clidriver.py).
        assert (run.returncode, run.stdout, run.stderr) == (
            254,
            "",
            stderr,
        ), report


TRANSFERS: Final = [
    pytest.param(DOWNLOAD, "GetObject", id="download"),
    pytest.param(UPLOAD, "PutObject", id="upload"),
]


@pytest.mark.parametrize(("command", "operation"), TRANSFERS)
async def test_cp_retried_internal_error_is_invisible(
    aws_cli: str, tmp_path: Path, command: Command, operation: str
) -> None:
    store = ScriptedS3(
        SEED_OBJECTS, failing=frozenset({operation}), failures=1
    )
    run = await run_aws(
        aws_cli,
        tmp_path,
        command.arguments,
        store,
        local_files=command.local_files,
    )
    report = run.describe()
    assert store.failures == [], report
    assert run.attempts(operation) == 2, report
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        command.stdout,
        "",
    ), report
    assert run.local_files == {
        **command.local_files,
        **command.downloaded_files,
    }, report
    assert store.objects == {**SEED_OBJECTS, **command.uploaded_objects}


def transfer_failed(command: Command) -> str:
    """The failed transfer's line with the error the CRT client reports.

    The CRT reports the 500 it stopped retrying as its own
    AWS_ERROR_S3_INTERNAL_ERROR, not as an S3ResponseError the AWS CLI
    would translate into botocore's error (s3transfer/crt.py:1023-1027).
    """
    if command is DOWNLOAD:
        line = (
            f"download failed: s3://{BUCKET}/download/object.txt to "
            f".{os.sep}object.txt"
        )
    else:
        line = (
            f"upload failed: .{os.sep}upload.txt to "
            f"s3://{BUCKET}/up/upload.txt"
        )
    return (
        f"{line} AWS_ERROR_S3_INTERNAL_ERROR: Response code indicates "
        "internal server error\n"
    )


@pytest.mark.parametrize(("command", "operation"), TRANSFERS)
async def test_cp_exhausted_retries_fail_the_transfer(
    aws_cli: str, tmp_path: Path, command: Command, operation: str
) -> None:
    store = ScriptedS3(
        SEED_OBJECTS, failing=frozenset({operation}), failures=EXHAUSTING
    )
    run = await run_aws(
        aws_cli,
        tmp_path,
        command.arguments,
        store,
        local_files=command.local_files,
    )
    report = run.describe()
    assert store.failures == [], report
    assert run.attempts(operation) == DEFAULT_TRANSFER_ATTEMPTS, report
    assert (run.returncode, run.stdout, run.stderr) == (
        1,
        "",
        transfer_failed(command),
    ), report
    assert run.local_files == command.local_files, report
    assert store.objects == SEED_OBJECTS, report


# Every ListObjectsV2 attempt answers a 500 and loses the connection
# halfway through its error body. botocore checks the body's length itself
# (2.39), so the status line decides: each attempt is a retried 500, and
# the last one is reported as a ClientError named by the status alone, as
# botocore names an error whose body it cannot parse (parsers.py:291-326).
async def test_ls_cut_during_error_body_fails_with_client_error(
    aws_cli: str, tmp_path: Path
) -> None:
    probe = ScriptedS3()
    size = probe.failure_body_size("ListObjectsV2")
    store = ScriptedS3(
        SEED_OBJECTS,
        failing=frozenset({"ListObjectsV2"}),
        failures=EXHAUSTING,
        cut=(size, size // 2, EXHAUSTING),
    )
    run = await run_aws(
        aws_cli,
        tmp_path,
        LS.arguments,
        store,
        environment={"AWS_MAX_ATTEMPTS": "2"},
        plain_endpoint=True,
    )
    report = run.describe()
    assert store.failures == [], report
    assert run.attempts("ListObjectsV2") == 2, report
    assert (run.returncode, run.stdout, run.stderr) == (
        254,
        "",
        "\naws: [ERROR]: An error occurred (500) when calling the "
        "ListObjectsV2 operation (reached max retries: 1): Internal Server "
        "Error\n",
    ), report


# An object above every default multipart threshold and within the 16 MiB
# part the profile sets, so its download is one ranged GET.
INTERRUPTED_SIZE: Final = 9 * MIB + 3
INTERRUPTED_BODY: Final = pattern_bytes("nine.bin", INTERRUPTED_SIZE)
INTERRUPTED_KEY: Final = "interrupted/nine.bin"


@pytest.mark.parametrize("validation", ["when_supported", "when_required"])
@pytest.mark.parametrize(
    ("arguments", "destination", "shown"),
    [
        pytest.param(
            ("s3", "cp", f"s3://{BUCKET}/{INTERRUPTED_KEY}", "nine.bin"),
            "nine.bin",
            f".{os.sep}nine.bin",
            id="single",
        ),
        pytest.param(
            (
                "s3",
                "cp",
                f"s3://{BUCKET}/interrupted/",
                "down",
                "--recursive",
            ),
            "down/nine.bin",
            f"down{os.sep}nine.bin",
            id="recursive",
        ),
    ],
)
async def test_cp_interrupted_download_fails_after_its_attempts(
    aws_cli: str,
    tmp_path: Path,
    validation: str,
    arguments: tuple[str, ...],
    destination: str,
    shown: str,
) -> None:
    # Every GET of the object loses its connection halfway through the
    # body, so both attempts fail and no partial file stays behind.
    store = ScriptedS3(
        {(BUCKET, INTERRUPTED_KEY): INTERRUPTED_BODY},
        cut=(INTERRUPTED_SIZE, INTERRUPTED_SIZE // 2, EXHAUSTING),
    )
    run = await run_aws(
        aws_cli,
        tmp_path,
        (*arguments, "--no-progress"),
        store,
        environment={
            "AWS_MAX_ATTEMPTS": "2",
            "AWS_RESPONSE_CHECKSUM_VALIDATION": validation,
        },
        config=CRT_CONFIG + "  multipart_chunksize = 16MB\n",
        plain_endpoint=True,
    )
    report = run.describe()
    assert store.failures == [], report
    assert run.attempts("GetObject") == 2, report
    assert (run.returncode, run.stdout) == (1, ""), report
    assert run.stderr == (
        f"download failed: s3://{BUCKET}/{INTERRUPTED_KEY} to {shown} "
        "AWS_IO_SOCKET_CLOSED: socket is closed.\n"
    ), report
    assert destination not in run.local_files, report
    assert run.local_files == {}, report


class CutThenDeniedS3(ScriptedS3):
    """ScriptedS3 that cuts the first GetObject's body as `cut` says and
    answers every later GetObject with AccessDenied."""

    def __init__(
        self, objects: Mapping[ObjectKey, bytes], cut: tuple[int, int, int]
    ) -> None:
        super().__init__(objects, cut=cut)
        self.gets = 0

    def dispatch(self, reconstructed: ReconstructedRequest) -> HTTPResponse:
        if reconstructed.operation_model.name == "GetObject":
            self.gets += 1
            if self.gets > 1:
                return self.error(
                    reconstructed, "AccessDenied", "Access Denied", 403
                )
        return super().dispatch(reconstructed)


# The first GetObject loses its connection 3 bytes into the body, and its
# retry is denied: the denial is the transfer's error, and the partial
# download leaves no file behind.
async def test_cp_download_cut_then_denied_reports_the_denial(
    aws_cli: str, tmp_path: Path
) -> None:
    store = CutThenDeniedS3(SEED_OBJECTS, cut=(len(DOWNLOAD_BODY), 3, 1))
    run = await run_aws(
        aws_cli, tmp_path, DOWNLOAD.arguments, store, plain_endpoint=True
    )
    report = run.describe()
    assert store.failures == [], report
    assert run.attempts("GetObject") == 2, report
    assert (run.returncode, run.stdout, run.stderr) == (
        1,
        "",
        f"download failed: s3://{BUCKET}/download/object.txt to "
        f".{os.sep}object.txt An error occurred (AccessDenied) when calling "
        "the GetObject operation: Access Denied\n",
    ), report
    assert run.local_files == {}, report


class ThrottlingS3(ScriptedS3):
    """ScriptedS3 that answers the first `throttles` requests of `operation`
    with a 429: one with no body, as a rate limiter in front of a bucket may
    send, or one naming the error `code`."""

    def __init__(
        self, operation: str, throttles: int, code: str | None = None
    ) -> None:
        super().__init__(SEED_OBJECTS)
        self.operation = operation
        self.throttles_left = throttles
        self.code = code

    def dispatch(self, reconstructed: ReconstructedRequest) -> HTTPResponse:
        name = reconstructed.operation_model.name
        if name == self.operation and self.throttles_left > 0:
            self.throttles_left -= 1
            if self.code is None:
                return HTTPResponse.raw(b"", status=429)
            return self.error(reconstructed, self.code, "Slow down", 429)
        return super().dispatch(reconstructed)


MOVE: Final = Command(
    "move",
    (
        "s3",
        "mv",
        f"s3://{BUCKET}/download/object.txt",
        "object.txt",
        "--no-progress",
    ),
    f"move: s3://{BUCKET}/download/object.txt to .{os.sep}object.txt\n",
    downloaded_files={"object.txt": DOWNLOAD_BODY},
)
MOVED_OBJECTS: Final = {
    key: body
    for key, body in SEED_OBJECTS.items()
    if key != (BUCKET, "download/object.txt")
}
# The requests the AWS CLI sends through botocore, which native sends in
# its place.
BOTOCORE_REQUESTS: Final = [
    pytest.param(LS, "ListObjectsV2", SEED_OBJECTS, id="ls"),
    pytest.param(DOWNLOAD, "HeadObject", SEED_OBJECTS, id="download"),
    pytest.param(MOVE, "DeleteObject", MOVED_OBJECTS, id="move"),
]


# Since 2.40.0 botocore retries a 429 as a throttling error when the
# operation models none of its code (retries/standard.py
# `ThrottlingStatusCodeChecker`); a 429 without a body has its status for a
# code.
@pytest.mark.parametrize(("command", "operation", "objects"), BOTOCORE_REQUESTS)
async def test_a_throttled_botocore_request_is_retried(
    aws_cli: str,
    tmp_path: Path,
    command: Command,
    operation: str,
    objects: Mapping[ObjectKey, bytes],
) -> None:
    store = ThrottlingS3(operation, throttles=1)
    run = await run_aws(aws_cli, tmp_path, command.arguments, store)
    report = run.describe()
    assert store.failures == [], report
    assert run.attempts(operation) == 2, report
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        command.stdout,
        "",
    ), report
    assert run.local_files == {
        **command.local_files,
        **command.downloaded_files,
    }, report
    assert store.objects == objects, report


def throttled_error(operation: str, retries: int) -> str:
    """botocore's ClientError for a 429 without a body, which it names by
    its status, once every attempt was throttled (parsers.py
    `_parse_error_from_http_status`)."""
    return (
        f"An error occurred (429) when calling the {operation} operation "
        f"(reached max retries: {retries}): Too Many Requests"
    )


@pytest.mark.parametrize(
    ("command", "operation", "returncode", "stderr", "local_files"),
    [
        pytest.param(
            LS,
            "ListObjectsV2",
            254,
            f"\naws: [ERROR]: {throttled_error('ListObjectsV2', 2)}\n",
            {},
            id="ls",
        ),
        pytest.param(
            DOWNLOAD,
            "HeadObject",
            1,
            f"fatal error: {throttled_error('HeadObject', 2)}\n",
            {},
            id="download",
        ),
        # The move downloaded the object before its source delete failed.
        pytest.param(
            MOVE,
            "DeleteObject",
            1,
            f"move failed: s3://{BUCKET}/download/object.txt to "
            f".{os.sep}object.txt {throttled_error('DeleteObject', 2)}\n",
            MOVE.downloaded_files,
            id="move",
        ),
    ],
)
async def test_a_botocore_request_throttled_on_every_attempt_names_its_retries(
    aws_cli: str,
    tmp_path: Path,
    command: Command,
    operation: str,
    returncode: int,
    stderr: str,
    local_files: Mapping[str, bytes],
) -> None:
    store = ThrottlingS3(operation, throttles=EXHAUSTING)
    run = await run_aws(aws_cli, tmp_path, command.arguments, store)
    report = run.describe()
    assert store.failures == [], report
    assert run.attempts(operation) == 3, report
    assert (run.returncode, run.stdout, run.stderr) == (
        returncode,
        "",
        stderr,
    ), report
    assert run.local_files == local_files, report
    assert store.objects == SEED_OBJECTS, report


# A 429 whose code the operation models is the model's to retry, and no
# listing error is retryable.
async def test_a_429_with_a_modeled_code_is_not_retried(
    aws_cli: str, tmp_path: Path
) -> None:
    store = ThrottlingS3("ListObjectsV2", throttles=1, code="NoSuchBucket")
    run = await run_aws(aws_cli, tmp_path, LS.arguments, store)
    report = run.describe()
    assert store.failures == [], report
    assert run.attempts("ListObjectsV2") == 1, report
    assert (run.returncode, run.stdout, run.stderr) == (
        254,
        "",
        "\naws: [ERROR]: An error occurred (NoSuchBucket) when calling the "
        "ListObjectsV2 operation: Slow down\n",
    ), report
