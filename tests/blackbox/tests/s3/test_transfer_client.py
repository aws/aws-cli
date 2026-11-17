# The transfer client `s3 cp` runs, and the CRT process lock the AWS CLI
# shares between its processes to choose it.
#
# Upstream's TransferManagerFactory resolves `auto` to the CRT client on
# every host, unless a setting only the classic client honors is configured
# or another AWS CLI process holds the CRT process lock, which it takes for
# every CRT client it builds and keeps until it exits; a preferred client
# runs whoever holds the lock (awscli/customizations/s3/factory.py). Each
# transfer request names the client in its User-Agent: botocore's feature ids
# for the S3 transfer client (botocore/useragent.py).
import contextlib
import json
import os
import signal
from collections.abc import Iterator
from pathlib import Path

import awscrt.s3
import pytest
from localstub import AsyncHTTPTestServer, HTTPResponse, ResponderContext
from localstub.server import TransmissionStrategy, Writer

from credhelpers import credential_process, process_credentials, write_config
from s3store import parse_byte_range
from tests.blackbox.utils import (
    get_object_response,
    head_object_response,
    put_object_response,
    run_cli,
)


# The name upstream's TransferManagerFactory locks while it runs the CRT
# client (`_CRT_PROCESS_LOCK_NAME`).
CRT_PROCESS_LOCK_NAME = "aws-cli"
CLASSIC_EXPLICIT = "Ad"
CRT_EXPLICIT = "Ae"
CLASSIC_AUTO = "Af"
CRT_AUTO = "Ag"
TRANSFER_CLIENT_FEATURES = frozenset(
    {CLASSIC_EXPLICIT, CRT_EXPLICIT, CLASSIC_AUTO, CRT_AUTO}
)
PAYLOAD = b"transfer client payload\n"
DIRECTIONS = ["upload", "download"]


def crt_process_lock_held() -> bool:
    """Whether a process other than this one holds the CRT process lock."""
    lock = awscrt.s3.CrossProcessLock(CRT_PROCESS_LOCK_NAME)
    try:
        lock.acquire()
    except RuntimeError:
        return True
    lock.release()
    return False


@pytest.fixture
def other_cli_running_crt() -> Iterator[None]:
    """Holds the CRT process lock, as an AWS CLI running the CRT client does."""
    lock = awscrt.s3.CrossProcessLock(CRT_PROCESS_LOCK_NAME)
    lock.acquire()
    yield
    lock.release()


def respond(context: ResponderContext) -> HTTPResponse:
    method = context.request.method
    if method == "PUT":
        return put_object_response()
    if method == "HEAD":
        return head_object_response(content_length=len(PAYLOAD))
    # A ranged GET, as the CRT client's first one of a download it splits
    # is, gets the bytes it asks for and the object's size, as S3 answers.
    byte_range = context.request.headers.get("range")
    if byte_range is None:
        return get_object_response(PAYLOAD)
    start, end = parse_byte_range(byte_range, len(PAYLOAD))
    response = get_object_response(
        PAYLOAD[start : end + 1],
        **{"Content-Range": f"bytes {start}-{end}/{len(PAYLOAD)}"},
    )
    return HTTPResponse.raw(response.body, status=206, headers=response.headers)


def write_s3_block(env: dict[str, str], settings: str) -> None:
    Path(env["AWS_CONFIG_FILE"]).write_text(
        f"[default]\ns3 =\n{settings}", encoding="utf-8"
    )


async def copy(
    aws_cli: str,
    server: AsyncHTTPTestServer,
    env: dict[str, str],
    tmp_path: Path,
    direction: str,
) -> None:
    server.handler = respond
    local = tmp_path / "local.txt"
    if direction == "upload":
        local.write_bytes(PAYLOAD)
        args = [str(local), "s3://bucket/key.txt"]
    else:
        args = ["s3://bucket/key.txt", str(local)]
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "cp", *args, "--no-progress"], env
    )
    assert rc == 0, stderr.decode()
    assert stderr == b""
    assert local.read_bytes() == PAYLOAD


def transfer_client_features(server: AsyncHTTPTestServer) -> set[str]:
    """The transfer-client feature ids of every PUT and GET request."""
    features: set[str] = set()
    for request in server.requests:
        if request.method not in ("PUT", "GET"):
            continue
        for component in request.headers["user-agent"].split():
            if component.startswith("m/"):
                ids = component.removeprefix("m/").split(",")
                features.update(TRANSFER_CLIENT_FEATURES.intersection(ids))
    return features


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", DIRECTIONS)
async def test_cp_auto_runs_crt_client(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    direction: str,
) -> None:
    server, env = transfer_runtime
    assert not crt_process_lock_held(), "another process holds the lock"
    await copy(aws_cli, server, env, tmp_path, direction)
    assert transfer_client_features(server) == {CRT_AUTO}


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", DIRECTIONS)
async def test_cp_auto_runs_classic_client_while_another_cli_runs_crt(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    direction: str,
    other_cli_running_crt: None,
) -> None:
    server, env = transfer_runtime
    await copy(aws_cli, server, env, tmp_path, direction)
    assert transfer_client_features(server) == {CLASSIC_AUTO}


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", DIRECTIONS)
@pytest.mark.parametrize(
    "client,feature",
    [("crt", CRT_EXPLICIT), ("classic", CLASSIC_EXPLICIT)],
)
async def test_cp_preferred_client_runs_whoever_holds_crt_lock(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    direction: str,
    client: str,
    feature: str,
    other_cli_running_crt: None,
) -> None:
    server, env = transfer_runtime
    write_s3_block(env, f"    preferred_transfer_client = {client}\n")
    await copy(aws_cli, server, env, tmp_path, direction)
    assert transfer_client_features(server) == {feature}


class _RecordLockMidBody(TransmissionStrategy):
    """Sends half of the GET body, records whether the CRT process lock is
    held while the download is in flight, then sends the rest."""

    def __init__(self) -> None:
        self.lock_held: bool | None = None

    async def write_body(self, writer: Writer, body: bytes) -> None:
        if body != PAYLOAD:
            writer.write(body)
            await writer.drain()
            return
        half = len(body) // 2
        writer.write(body[:half])
        await writer.drain()
        self.lock_held = crt_process_lock_held()
        writer.write(body[half:])
        await writer.drain()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "settings,held",
    [
        ("", True),
        ("    preferred_transfer_client = crt\n", True),
        ("    preferred_transfer_client = classic\n", False),
    ],
    ids=["auto", "crt", "classic"],
)
async def test_cp_holds_crt_lock_while_it_runs_crt_client(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    settings: str,
    held: bool,
) -> None:
    server, env = transfer_runtime
    assert not crt_process_lock_held(), "another process holds the lock"
    if settings:
        write_s3_block(env, settings)
    strategy = _RecordLockMidBody()
    server.set_transmission_strategy(strategy)
    await copy(aws_cli, server, env, tmp_path, "download")
    assert strategy.lock_held is held
    # The lock goes with the process.
    assert not crt_process_lock_held()


@pytest.fixture
def helper_child_pid_file(tmp_path: Path) -> Iterator[Path]:
    """Where a credential helper records the child it leaves running; the
    child is stopped when the test ends."""
    pid_file = tmp_path / "helper-child.pid"
    yield pid_file
    if pid_file.exists():
        with contextlib.suppress(ProcessLookupError):
            os.kill(int(pid_file.read_text()), signal.SIGTERM)


def lingering_helper(pid_file: Path) -> str:
    """A credential helper that leaves a child running, as one that starts an
    agent does. The child inherits every descriptor the helper was given
    except its standard streams, so the AWS CLI still reads to the end of
    the helper's output."""
    return (
        "import subprocess\n"
        "child = subprocess.Popen(\n"
        "    [sys.executable, '-c', 'import time; time.sleep(60)'],\n"
        "    stdin=subprocess.DEVNULL,\n"
        "    stdout=subprocess.DEVNULL,\n"
        "    stderr=subprocess.DEVNULL,\n"
        "    close_fds=False,\n"
        ")\n"
        f"Path({str(pid_file)!r}).write_text(str(child.pid))\n"
        f"print({json.dumps(process_credentials())!r})\n"
    )


def process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@pytest.mark.skipif(
    os.name != "posix",
    reason="a Windows child inherits every inheritable handle, so it holds "
    "the helper's output pipe; the CRT lock there is a named mutex no child "
    "inherits",
)
@pytest.mark.asyncio
@pytest.mark.parametrize("direction", DIRECTIONS)
async def test_cp_credential_helper_child_does_not_keep_crt_lock(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    direction: str,
    helper_child_pid_file: Path,
) -> None:
    server, env = transfer_runtime
    assert not crt_process_lock_held(), "another process holds the lock"
    del env["AWS_ACCESS_KEY_ID"], env["AWS_SECRET_ACCESS_KEY"]
    command, _ = credential_process(
        tmp_path, lingering_helper(helper_child_pid_file)
    )
    write_config(env, f"[default]\ncredential_process = {command}\n")
    await copy(aws_cli, server, env, tmp_path, direction)
    assert transfer_client_features(server) == {CRT_AUTO}
    # The helper's child outlives the AWS CLI; the lock does not.
    assert process_running(int(helper_child_pid_file.read_text()))
    assert not crt_process_lock_held()
