"""`--case-conflict` on downloads by `s3 cp --recursive` (upstream
tests/functional/s3/test_cp_command.py, TestCpRecursiveCaseConflict).
Upstream's module also collects the sync case-conflict tests it imports,
which test_sync_requests.py ports.

A key that differs from a local file, or from another key downloaded, only
by case conflicts: `error` fails the command, `warn` downloads it with a
warning, `skip` skips it with one, and `ignore`, the default, downloads it
silently. A conflict with a local file exists only on a case-insensitive
filesystem, and two keys differing only by case download to one file
there, so those cases skip as upstream's do, on the same conditions.
"""

import platform
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest
from localstub import HTTPResponse

from apihelpers import ApiSession
from s3params import list_objects_response

pytestmark = pytest.mark.asyncio

LOWER_KEY: Final = "a.txt"
UPPER_KEY: Final = "A.txt"
BODY: Final = b"foo"

# Upstream probes its temporary directory once (awscli/testutils.py).
with tempfile.TemporaryDirectory() as probe:
    (Path(probe) / "aws-cli-tmp-file").write_bytes(b"")
    CASE_INSENSITIVE: Final = (Path(probe) / "AWS-CLI-TMP-FILE").exists()

CASE_INSENSITIVE_ONLY: Final = pytest.mark.skipif(
    not CASE_INSENSITIVE,
    reason="This test requires a case-insensitive filesystem.",
)
NOT_WINDOWS: Final = pytest.mark.skipif(
    platform.system() not in ("Darwin", "Linux"),
    reason="Can't rename to same file",
)


@dataclass(frozen=True)
class Conflict:
    """A download with a case conflict: the --case-conflict value, whether
    `a.txt` exists locally, the keys listed, and the exit status and
    stderr text upstream checks."""

    mode: str | None
    existing_file: bool
    keys: tuple[str, ...]
    rc: int = 0
    message: str | None = None


CASES: Final = [
    pytest.param(
        Conflict(
            "error",
            True,
            (UPPER_KEY,),
            rc=1,
            message=f"Failed to download bucket/{UPPER_KEY}",
        ),
        id="error-with-existing-file",
        marks=CASE_INSENSITIVE_ONLY,
    ),
    pytest.param(
        Conflict(
            "error",
            False,
            (UPPER_KEY, LOWER_KEY),
            rc=1,
            message=f"Failed to download bucket/{LOWER_KEY}",
        ),
        id="error-with-case-conflicts-in-s3",
    ),
    pytest.param(
        Conflict(
            "warn",
            True,
            (UPPER_KEY,),
            message=f"warning: Downloading bucket/{UPPER_KEY}",
        ),
        id="warn-with-existing-file",
        marks=CASE_INSENSITIVE_ONLY,
    ),
    pytest.param(
        Conflict(
            "warn",
            False,
            (UPPER_KEY, LOWER_KEY),
            message=f"warning: Downloading bucket/{LOWER_KEY}",
        ),
        id="warn-with-case-conflicts-in-s3",
        marks=NOT_WINDOWS,
    ),
    pytest.param(
        Conflict(
            "skip",
            True,
            (UPPER_KEY,),
            message=f"warning: Skipping bucket/{UPPER_KEY}",
        ),
        id="skip-with-existing-file",
        marks=CASE_INSENSITIVE_ONLY,
    ),
    pytest.param(
        Conflict(
            "skip",
            False,
            (UPPER_KEY, LOWER_KEY),
            message=f"warning: Skipping bucket/{LOWER_KEY}",
        ),
        id="skip-with-case-conflicts-in-s3",
    ),
    pytest.param(
        Conflict("ignore", True, (UPPER_KEY,)),
        id="ignore-with-existing-file",
    ),
    pytest.param(
        Conflict("ignore", False, (UPPER_KEY, LOWER_KEY)),
        id="ignore-with-case-conflicts-in-s3",
        marks=NOT_WINDOWS,
    ),
]


def on_crt(api: ApiSession) -> bool:
    return "preferred_transfer_client = crt" in api.config_path.read_text()


def stored_object(api: ApiSession) -> HTTPResponse:
    """A listed object, answering its GET. The CRT client ranges its GETs
    by its part size and sends them for several objects in no fixed order;
    S3 answers a range covering the whole object with the object's range
    and size."""
    headers = {
        "ETag": '"foo-1"',
        "Last-Modified": "Thu, 11 Feb 2021 04:24:23 GMT",
    }
    if not on_crt(api):
        return HTTPResponse.raw(BODY, headers=headers)
    headers["Content-Range"] = f"bytes 0-{len(BODY) - 1}/{len(BODY)}"
    return HTTPResponse.raw(BODY, status=206, headers=headers)


async def download(
    api: ApiSession, command: list[str], case: Conflict
) -> str:
    """Run `command` against the listing and return its stderr."""
    if case.existing_file:
        (api.cwd / LOWER_KEY).write_text("mycontent")
    options = [] if case.mode is None else ["--case-conflict", case.mode]
    # The listed Size is the body served. Each key may be fetched, so
    # each gets a reply. The listing reports no checksums, so the CRT client
    # sends no HEAD of its own.
    run = await api.run(
        [*command, "s3://bucket", str(api.cwd), *options],
        replies=[
            list_objects_response(list(case.keys), Size=len(BODY)),
            *[stored_object(api) for _ in case.keys],
        ],
        expected_rc=case.rc,
    )
    if case.message is not None:
        assert case.message in run.stderr, run.describe()
    return run.stderr


@pytest.mark.parametrize("case", CASES)
async def test_cp_recursive_case_conflict(
    transfer_api: ApiSession, case: Conflict
) -> None:
    await download(transfer_api, ["s3", "cp", "--recursive"], case)


async def test_cp_recursive_ignores_case_conflicts_by_default(
    transfer_api: ApiSession,
) -> None:
    stderr = await download(
        transfer_api,
        ["s3", "cp", "--recursive"],
        Conflict(None, True, (UPPER_KEY,)),
    )
    # Neither the error nor a warning: `ignore`.
    assert stderr == ""
