import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Final

import pytest

from credhelpers import (
    CREATED_FILE_MODE,
    BytesStartingWith,
    CliRun,
    FileChanges,
    Sandbox,
    Stub,
    command_line,
    export_credentials_output,
    routed,
    run_export_credentials,
)

pytestmark = pytest.mark.asyncio

ACCESS_KEY: Final = "AKIDEXPIRY"
SECRET_KEY: Final = "EXPIRY-secret"
REFRESHED_KEY: Final = "AKIDREFRESHED"
REFRESHED_SECRET: Final = "REFRESHED-secret"
PROCESS_OUTPUT: Final = "process-output.json"
# The grammar rows' process source runs `cat` on a fixed JSON file: no
# interpreter, no HTTP, and the same file again on a refresh.
CAT: Final = shutil.which("cat") or "/bin/cat"
CALLS_LOG: Final = "calls.jsonl"
RESPONSES: Final = "responses.json"
# The refresh-window rows' process source: prints responses.json in order
# (the last one repeats) and appends its call index to calls.jsonl, so the
# run's file changes show whether a refresh spawned it again.
REPLAY_HELPER: Final = """\
import json
import sys
from pathlib import Path

here = Path(__file__).parent
log = here / "calls.jsonl"
calls = 0
if log.exists():
    calls = len(log.read_text(encoding="utf-8").splitlines())
with log.open("a", encoding="utf-8", newline="\\n") as stream:
    stream.write(json.dumps({"call": calls}) + "\\n")
responses = json.loads(
    (here / "responses.json").read_text(encoding="utf-8")
)
sys.stdout.write(responses[min(calls, len(responses) - 1)])
"""
# exportcreds.py:269-279 wraps every load-phase exception, and
# errorhandler.py:316-321 renders it enhanced (errorformat.py:28-41).
CONFIGURATION_PREFIX: Final = (
    "\naws: [ERROR]: An error occurred (Configuration): "
    "Unable to retrieve credentials: "
)
# The general handler's framing of a freeze-phase failure.
RAW_PREFIX: Final = "\naws: [ERROR]: "
STILL_EXPIRED: Final = (
    "Credentials were refreshed, but the refreshed credentials are still "
    "expired."
)


@dataclass(frozen=True)
class Outcome:
    """What the command must print and return."""

    returncode: int
    stdout: bytes = b""
    stderr: bytes | BytesStartingWith = b""


def printed(expiration: str | None) -> Outcome:
    """Success: the expiry printed as isoformat(), or no Expiration."""
    return Outcome(
        0,
        export_credentials_output(
            ACCESS_KEY, SECRET_KEY, expiration=expiration
        ),
    )


def rejected(value: str) -> Outcome:
    """A parse failure in load(): ConfigurationError, rc 253.

    The rest of the message is dateutil's or CPython's wording, so only
    the AWS-authored prefix and the rejected value are asserted.
    """
    return Outcome(
        253,
        stderr=BytesStartingWith(
            CONFIGURATION_PREFIX.encode(), (value.encode(),)
        ),
    )


def raw(message: str) -> Outcome:
    """A failure in get_frozen_credentials: raw, rc 255."""
    return Outcome(255, stderr=f"{RAW_PREFIX}{message}\n".encode())


@dataclass(frozen=True)
class Row:
    """One expiry value and its outcome."""

    value: str
    expected: Outcome


# How an expiry value parses and prints. The accepted rows are what real
# producers write: Python's str() with a space, JavaScript's
# toISOString() milliseconds, Go's RFC3339Nano nanoseconds (cut to six
# digits, never rounded), a shell's `%z` basic offset, and 9999 as
# "never expires". Each prints as isoformat(): `Z` and `-00:00` become
# `+00:00` and a zero fraction is dropped. Every accepted expiry lies far
# ahead of now, so no refresh window applies, except in the past row.
ROWS: Final[dict[str, Row]] = {
    "space-separator": Row(
        "2099-10-08 12:00:00Z", printed("2099-10-08T12:00:00+00:00")
    ),
    "fraction-milliseconds": Row(
        "2099-10-08T12:00:00.123Z",
        printed("2099-10-08T12:00:00.123000+00:00"),
    ),
    "fraction-nanoseconds-truncated": Row(
        "2099-10-08T12:00:00.123456789Z",
        printed("2099-10-08T12:00:00.123456+00:00"),
    ),
    "fraction-zero-omitted": Row(
        "2099-10-08T12:00:00.000000Z", printed("2099-10-08T12:00:00+00:00")
    ),
    "negative-zero-offset": Row(
        "2099-10-08T12:00:00-00:00", printed("2099-10-08T12:00:00+00:00")
    ),
    "offset-basic": Row(
        "2099-10-08T12:00:00+0530", printed("2099-10-08T12:00:00+05:30")
    ),
    "last-microsecond": Row(
        "9999-12-31T23:59:59.999999Z",
        printed("9999-12-31T23:59:59.999999+00:00"),
    ),
    # An empty variable means no expiry (credentials.py:1317-1320).
    "empty": Row("", printed(None)),
    # Aware but past: one refresh, then still expired.
    "past": Row("2000-01-01T00:00:00Z", raw(STILL_EXPIRED)),
    "second-60": Row("2099-10-08T12:00:60Z", rejected("2099-10-08T12:00:60Z")),
    "garbage": Row("garbage", rejected("garbage")),
    # Upstream bug, matched for parity: an expiry with no zone parses
    # naive, and the first comparison with the aware now raises TypeError
    # (credentials.py:274-275, 518-520), printed raw with rc 255.
    "naive-date-time": Row(
        "2099-10-08T12:00:00",
        Outcome(255, stderr=BytesStartingWith(RAW_PREFIX.encode())),
    ),
}
# The process path parses with the same dateutil call
# (credentials.py:1093-1098), so two printed rows show it is wired up.
PROCESS_ROWS: Final = ("fraction-nanoseconds-truncated", "offset-basic")


async def export(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    overrides: dict[str, str],
) -> CliRun:
    """Run export-credentials once; every request is a tripwire."""
    server, proxy = stub
    env = {**sandbox.env(proxy), **overrides}
    return await run_export_credentials(
        aws_cli,
        sandbox,
        [server],
        env,
        handlers={server: lambda: routed({})},
    )


def assert_outcome(
    run: CliRun, expected: Outcome, changes: FileChanges | None = None
) -> None:
    """Assert the output, no requests, and exactly `changes` on disk.

    Env and `cat` only read, so `changes` defaults to none.
    """
    assert (run.returncode, run.stdout, run.stderr) == (
        expected.returncode,
        expected.stdout,
        expected.stderr,
    ), run.describe()
    assert run.requests == (), run.describe()
    assert run.changes == ({} if changes is None else changes), run.describe()


def row_params(rows: dict[str, Row]) -> list[object]:
    return [pytest.param(row, id=name) for name, row in rows.items()]


def expire_through_env(value: str) -> dict[str, str]:
    """EnvProvider input: AWS_CREDENTIAL_EXPIRATION (credentials.py:1201)."""
    return {
        "AWS_ACCESS_KEY_ID": ACCESS_KEY,
        "AWS_SECRET_ACCESS_KEY": SECRET_KEY,
        "AWS_CREDENTIAL_EXPIRATION": value,
    }


def process_document(access_key: str, secret_key: str, value: str) -> str:
    """A credential_process document whose Expiration is `value`."""
    return json.dumps(
        {
            "Version": 1,
            "AccessKeyId": access_key,
            "SecretAccessKey": secret_key,
            "Expiration": value,
        }
    )


def use_credential_process(sandbox: Sandbox, command: str) -> None:
    sandbox.config.write_text(
        f"[default]\ncredential_process = {command}\n", encoding="utf-8"
    )


def expire_through_process(sandbox: Sandbox, value: str) -> None:
    """ProcessProvider input: `cat` of a JSON file with `value`."""
    output = sandbox.write(
        PROCESS_OUTPUT, process_document(ACCESS_KEY, SECRET_KEY, value)
    )
    use_credential_process(sandbox, command_line([CAT, str(output)]))


def expire_through_replay(
    sandbox: Sandbox, value: str, refreshed: str
) -> None:
    """ProcessProvider input: REPLAY_HELPER printing ACCESS_KEY expiring
    at `value`, then REFRESHED_KEY expiring at `refreshed` on every
    later call."""
    responses = [
        process_document(ACCESS_KEY, SECRET_KEY, value),
        process_document(REFRESHED_KEY, REFRESHED_SECRET, refreshed),
    ]
    sandbox.write(RESPONSES, json.dumps(responses))
    use_credential_process(sandbox, sandbox.helper("replay.py", REPLAY_HELPER))


def replay_calls(count: int) -> FileChanges:
    """The run's only change: calls.jsonl after `count` helper spawns."""
    log = "".join(json.dumps({"call": index}) + "\n" for index in range(count))
    return {CALLS_LOG: (CREATED_FILE_MODE, log.encode())}


def offset_expiry(seconds: int, hours: int, minutes: int) -> str:
    """`now + seconds` in whole seconds, written at UTC+hours:minutes.

    Fixed when the test builds its fixtures, so the expected output is
    known before the run.
    """
    zone = timezone(timedelta(hours=hours, minutes=minutes))
    moment = datetime.now(UTC).replace(microsecond=0)
    return (moment + timedelta(seconds=seconds)).astimezone(zone).isoformat()


def far_future_expiry(hours: int, minutes: int) -> str:
    """An expiry outside every window, written at UTC+hours:minutes."""
    zone = timezone(timedelta(hours=hours, minutes=minutes))
    return datetime(2099, 10, 8, 12, tzinfo=zone).isoformat()


# EnvProvider parses AWS_CREDENTIAL_EXPIRATION with dateutil in load()
# (credentials.py:1265-1276); export freezes, which compares the expiry
# with now, and prints isoformat() (exportcreds.py:30-46).
@pytest.mark.parametrize("row", row_params(ROWS))
async def test_env_expiration_follows_dateutil_grammar(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    row: Row,
) -> None:
    run = await export(aws_cli, sandbox, stub, expire_through_env(row.value))

    assert_outcome(run, row.expected)


# ProcessProvider builds RefreshableCredentials.create_from_metadata from
# the helper's Expiration (credentials.py:1093-1098, 440-464), whose
# dateutil parse runs in load(); a refresh runs the helper again.
@pytest.mark.parametrize(
    "row", row_params({name: ROWS[name] for name in PROCESS_ROWS})
)
async def test_process_expiration_follows_dateutil_grammar(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    row: Row,
) -> None:
    expire_through_process(sandbox, row.value)

    run = await export(aws_cli, sandbox, stub, {})

    assert_outcome(run, row.expected)


# The refresh windows compare aware instants, so the offset counts:
# refresh_needed subtracts _local_now() from the expiry
# (credentials.py:522-554). Every offset keeps at least 60 s from 0 and
# the 300, 600, and 900 s windows. EnvProvider's refresh rereads the
# same variables (credentials.py:1288-1333), so through env only the
# outcome shows: an expiry 20 minutes ahead written at -07:00 prints
# with its offset, and one 20 minutes past written at +05:30 is still
# expired after the refresh.
@pytest.mark.parametrize(
    ("seconds", "hours", "minutes"),
    [
        pytest.param(1200, -7, 0, id="ahead-20-min-at-minus-07-00"),
        pytest.param(-1200, 5, 30, id="past-20-min-at-plus-05-30"),
    ],
)
async def test_env_expiration_offset_decides_refresh_window(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    seconds: int,
    hours: int,
    minutes: int,
) -> None:
    value = offset_expiry(seconds, hours, minutes)

    run = await export(aws_cli, sandbox, stub, expire_through_env(value))

    expected = raw(STILL_EXPIRED) if seconds < 0 else printed(value)
    assert_outcome(run, expected)


# Through credential_process the refresh shows: ProcessProvider.load
# spawns REPLAY_HELPER once (credentials.py:1085-1098), export's freeze
# spawns it again only inside the 15-minute advisory window
# (credentials.py:560-627), and the second call answers REFRESHED_KEY.
# The spawn count is asserted from calls.jsonl, the run's only change.
async def test_process_expiration_offset_outside_windows_spawns_once(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    value = offset_expiry(1200, -7, 0)
    expire_through_replay(sandbox, value, far_future_expiry(-7, 0))

    run = await export(aws_cli, sandbox, stub, {})

    assert_outcome(run, printed(value), replay_calls(1))


# An expiry 12 minutes ahead written at +09:30 is inside the advisory
# window, so the freeze runs the helper again.
async def test_process_expiration_offset_inside_window_refreshes(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    refreshed = far_future_expiry(9, 30)
    expire_through_replay(sandbox, offset_expiry(720, 9, 30), refreshed)

    run = await export(aws_cli, sandbox, stub, {})

    assert_outcome(
        run,
        Outcome(
            0,
            export_credentials_output(
                REFRESHED_KEY, REFRESHED_SECRET, expiration=refreshed
            ),
        ),
        replay_calls(2),
    )
