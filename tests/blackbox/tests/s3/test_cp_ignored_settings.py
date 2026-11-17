"""The settings the CRT transfer client ignores, when `s3 cp` prefers it.

With `preferred_transfer_client = crt` the AWS CLI builds the CRT client
whatever else the profile sets, and prints one warning naming each setting
that client has no counterpart for (customizations/s3/factory.py:303-321):
the classic client's max_bandwidth, max_queue_size, and io_chunksize, the
adaptive retry mode, and a max_attempts outside the 2 to 64 the CRT client
takes (factory.py:242-251). The transfer then runs as if they were unset.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import pytest

from credhelpers import run_command
from s3store import (
    ObjectKey,
    ScriptedS3,
    decoded,
    pattern_bytes,
    read_tree,
    s3_runtime,
    write_tree,
)

pytestmark = pytest.mark.asyncio

BUCKET: Final = "bucket"
DOWNLOAD_BODY: Final = pattern_bytes("object", 2048)
UPLOAD_FILE: Final = pattern_bytes("upload", 3000)
TREE: Final[dict[str, bytes]] = {
    "tree/a.txt": pattern_bytes("tree a", 100),
    "tree/b.txt": pattern_bytes("tree b", 1500),
    "tree/nested/c.txt": pattern_bytes("tree c", 700),
}
SEED_OBJECTS: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, "download/object.txt"): DOWNLOAD_BODY,
    **{(BUCKET, key): body for key, body in TREE.items()},
}
WARNING: Final = (
    "warning: The following configuration values are not supported by the "
    "'crt' s3 transfer client and will be ignored: "
)
CRT_BLOCK: Final = "[default]\ns3 =\n  preferred_transfer_client = crt\n"
TRANSFER_KEYS: Final = (
    "  max_queue_size = 5\n  io_chunksize = 1MB\n  max_bandwidth = 10MB/s\n"
)
# The order the warning names them in: the classic client's settings in
# UNSUPPORTED_OPTIONS order, the retry mode, then the attempts
# (factory.py:70-82, 303-314).
TRANSFER_KEYS_NAMED: Final = "max_bandwidth, max_queue_size, io_chunksize"
ALL_SETTINGS_ENV: Final = {
    "AWS_RETRY_MODE": "adaptive",
    "AWS_MAX_ATTEMPTS": "1",
}
ALL_SETTINGS_NAMED: Final = (
    f"{TRANSFER_KEYS_NAMED}, retry_mode = adaptive, "
    "max_attempts = 1 (must be between 2 and 64)"
)


@dataclass(frozen=True)
class Command:
    name: str
    arguments: tuple[str, ...]
    stdout: tuple[str, ...]
    local_files: Mapping[str, bytes] = field(default_factory=dict[str, bytes])
    downloaded_files: Mapping[str, bytes] = field(
        default_factory=dict[str, bytes]
    )
    uploaded_objects: Mapping[ObjectKey, bytes] = field(
        default_factory=dict[ObjectKey, bytes]
    )


DOWNLOAD: Final = Command(
    "download",
    ("s3", "cp", f"s3://{BUCKET}/download/object.txt", "object.txt"),
    (f"download: s3://{BUCKET}/download/object.txt to .{os.sep}object.txt",),
    downloaded_files={"object.txt": DOWNLOAD_BODY},
)
UPLOAD: Final = Command(
    "upload",
    ("s3", "cp", "upload.txt", f"s3://{BUCKET}/up/upload.txt"),
    (f"upload: .{os.sep}upload.txt to s3://{BUCKET}/up/upload.txt",),
    local_files={"upload.txt": UPLOAD_FILE},
    uploaded_objects={(BUCKET, "up/upload.txt"): UPLOAD_FILE},
)
RECURSIVE_DOWNLOAD: Final = Command(
    "recursive-download",
    ("s3", "cp", f"s3://{BUCKET}/tree/", "tree", "--recursive"),
    tuple(
        sorted(
            f"download: s3://{BUCKET}/{key} to {os.path.join(*key.split('/'))}"
            for key in TREE
        )
    ),
    downloaded_files=TREE,
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


async def run_cp(
    aws_cli: str,
    tmp_path: Path,
    command: Command,
    store: ScriptedS3,
    config: str,
    environment: Mapping[str, str],
) -> Run:
    work = tmp_path / "work"
    work.mkdir()
    write_tree(work, command.local_files)
    async with s3_runtime(store, tmp_path) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(config, encoding="utf-8")
        env.update(environment)
        stdout, stderr, returncode = await run_command(
            [aws_cli, *command.arguments, "--no-progress"],
            env,
            cwd=work,
            stdin=None,
        )
    return Run(
        returncode=returncode,
        stdout=decoded(stdout),
        stderr=decoded(stderr),
        local_files=read_tree(work),
        store=store,
    )


def assert_transferred_with_warning(
    run: Run, command: Command, named: str
) -> None:
    report = run.describe()
    assert run.store.failures == [], report
    # Concurrent transfers finish, and print, in any order.
    assert (run.returncode, sorted(run.stdout.splitlines()), run.stderr) == (
        0,
        list(command.stdout),
        f"{WARNING}{named}.\n",
    ), report
    assert run.local_files == {
        **command.local_files,
        **command.downloaded_files,
    }, report
    assert run.store.objects == {
        **SEED_OBJECTS,
        **command.uploaded_objects,
    }, report


# The client is built once per command, so a recursive download warns once
# however many objects it moves.
@pytest.mark.parametrize(
    ("config", "environment", "named"),
    [
        pytest.param(
            CRT_BLOCK + TRANSFER_KEYS, {}, TRANSFER_KEYS_NAMED, id="keys"
        ),
        pytest.param(
            CRT_BLOCK + TRANSFER_KEYS,
            ALL_SETTINGS_ENV,
            ALL_SETTINGS_NAMED,
            id="all-settings",
        ),
        pytest.param(
            CRT_BLOCK + "  max_queue_size = 5\n",
            {"AWS_MAX_ATTEMPTS": "100"},
            "max_queue_size, max_attempts = 100 (must be between 2 and 64)",
            id="key-and-attempts",
        ),
        pytest.param(
            CRT_BLOCK + "  io_chunksize = 1MB\n  max_bandwidth = 10MB/s\n",
            {},
            "max_bandwidth, io_chunksize",
            id="key-subset",
        ),
    ],
)
async def test_cp_crt_preferred_warns_once_about_ignored_settings(
    aws_cli: str,
    tmp_path: Path,
    config: str,
    environment: dict[str, str],
    named: str,
) -> None:
    store = ScriptedS3(SEED_OBJECTS)
    run = await run_cp(
        aws_cli, tmp_path, RECURSIVE_DOWNLOAD, store, config, environment
    )
    assert_transferred_with_warning(run, RECURSIVE_DOWNLOAD, named)


@pytest.mark.parametrize(
    "command",
    [pytest.param(DOWNLOAD, id="download"), pytest.param(UPLOAD, id="upload")],
)
async def test_cp_single_transfer_warns_about_ignored_settings(
    aws_cli: str, tmp_path: Path, command: Command
) -> None:
    store = ScriptedS3(SEED_OBJECTS)
    run = await run_cp(
        aws_cli,
        tmp_path,
        command,
        store,
        CRT_BLOCK + TRANSFER_KEYS,
        ALL_SETTINGS_ENV,
    )
    assert_transferred_with_warning(run, command, ALL_SETTINGS_NAMED)


# 3 failures: more than the single attempt max_attempts = 1 asks for, or
# botocore's default 3 attempts allow. The CRT client keeps its own 5
# retries for an ignored setting (factory.py:431-435), so the transfer
# succeeds on its fourth attempt.
CRT_RETRIED_FAILURES: Final = 3


@pytest.mark.parametrize(
    ("command", "operation", "environment", "named"),
    [
        pytest.param(
            DOWNLOAD,
            "GetObject",
            {"AWS_MAX_ATTEMPTS": "1"},
            "max_attempts = 1 (must be between 2 and 64)",
            id="download-1",
        ),
        pytest.param(
            DOWNLOAD,
            "GetObject",
            {"AWS_RETRY_MODE": "adaptive"},
            "retry_mode = adaptive",
            id="download-adaptive",
        ),
        pytest.param(
            UPLOAD,
            "PutObject",
            {"AWS_MAX_ATTEMPTS": "1"},
            "max_attempts = 1 (must be between 2 and 64)",
            id="upload-1",
        ),
    ],
)
async def test_cp_crt_preferred_keeps_its_attempts_for_ignored_retries(
    aws_cli: str,
    tmp_path: Path,
    command: Command,
    operation: str,
    environment: dict[str, str],
    named: str,
) -> None:
    store = ScriptedS3(
        SEED_OBJECTS,
        failing=frozenset({operation}),
        failures=CRT_RETRIED_FAILURES,
    )
    run = await run_cp(
        aws_cli, tmp_path, command, store, CRT_BLOCK, environment
    )
    assert_transferred_with_warning(run, command, named)
    assert store.operations().count(operation) == CRT_RETRIED_FAILURES + 1, (
        run.describe()
    )
