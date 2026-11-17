"""Which credentials sign the requests of `s3 cp`, by profile selection.

The credential provider tests sign `s3 ls` under each way to select a
profile (credentials/providers/test_shared_files.py
test_credentials_profile_selection_signs_with_highest_priority and
test_credentials_files_sign_with_highest_priority_source,
credentials/providers/test_environment.py
test_env_provider_signs_listing_unless_profile_is_explicit). These run the
same selections through a download and an upload, whose requests the
transfer client signs, and list under the selections those tests leave
out. Each identity has its own access key and session token, so a correct
key paired with another source's token fails too.
"""

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Final

import pytest

from credhelpers import file_credentials, run_command
from s3store import (
    InMemoryS3,
    ObjectKey,
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
SEED_OBJECTS: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, "download/object.txt"): DOWNLOAD_BODY,
    (BUCKET, "tree/a.txt"): pattern_bytes("tree a", 100),
}
# The command line, its stdout, and the local files and objects after it.
COMMANDS: Final[
    dict[
        str,
        tuple[
            tuple[str, ...],
            str,
            Mapping[str, bytes],
            Mapping[ObjectKey, bytes],
        ],
    ]
] = {
    "ls": (
        ("s3", "ls", f"s3://{BUCKET}/tree/"),
        "2026-01-02 03:04:05        100 a.txt\n",
        {},
        SEED_OBJECTS,
    ),
    "download": (
        (
            "s3",
            "cp",
            f"s3://{BUCKET}/download/object.txt",
            "object.txt",
            "--no-progress",
        ),
        f"download: s3://{BUCKET}/download/object.txt to "
        f".{os.sep}object.txt\n",
        {"object.txt": DOWNLOAD_BODY},
        SEED_OBJECTS,
    ),
    "upload": (
        (
            "s3",
            "cp",
            "upload.txt",
            f"s3://{BUCKET}/up/upload.txt",
            "--no-progress",
        ),
        f"upload: .{os.sep}upload.txt to s3://{BUCKET}/up/upload.txt\n",
        {"upload.txt": UPLOAD_FILE},
        {**SEED_OBJECTS, (BUCKET, "up/upload.txt"): UPLOAD_FILE},
    ),
}


def identity(name: str) -> str:
    return file_credentials(name, f"{name}-token")


CONFIG: Final = (
    "[default]\n"
    + identity("DEFAULTCONFIG")
    + "[profile selected]\n"
    + identity("CONFIG")
)
ENV_KEYS: Final = {
    "AWS_ACCESS_KEY_ID": "AKIDENV",
    "AWS_SECRET_ACCESS_KEY": "ENV-secret",
    "AWS_SESSION_TOKEN": "ENV-token",
}
NO_ENV_KEYS: Final = {name: "" for name in ENV_KEYS}

# (selector, environment keys, shared keys for `selected`, the identity).
# botocore skips the environment provider only for a non-empty --profile
# (botocore/credentials.py:92, 151-171; clidriver.py:639-640), and the
# shared credentials file answers before the config file
# (credentials.py:202-213).
SELECTIONS: Final = [
    pytest.param("--profile", True, True, "SHARED", id="flag-shared"),
    pytest.param("--profile", True, False, "CONFIG", id="flag-config"),
    pytest.param("AWS_PROFILE", True, True, "ENV", id="profile-env"),
    pytest.param("AWS_PROFILE", False, True, "SHARED", id="profile-shared"),
    pytest.param("AWS_PROFILE", False, False, "CONFIG", id="profile-config"),
    pytest.param("empty-flag", True, True, "ENV", id="empty-flag-env"),
    pytest.param("empty-flag", False, True, "SHARED", id="empty-flag-shared"),
    pytest.param(
        "AWS_DEFAULT_PROFILE", True, True, "ENV", id="default-profile-env"
    ),
]
# The selections the listing tests above already sign `s3 ls` under.
LISTED_ELSEWHERE: Final = frozenset(
    {"flag-shared", "profile-env", "profile-shared", "empty-flag-env"}
)


def cases() -> list[object]:
    params: list[object] = []
    for command in COMMANDS:
        for selection in SELECTIONS:
            case_id = selection.id
            if command == "ls" and case_id in LISTED_ELSEWHERE:
                continue
            params.append(
                pytest.param(
                    command, *selection.values, id=f"{command}-{case_id}"
                )
            )
    return params


@pytest.mark.parametrize(
    ("command", "selector", "environment_keys", "shared_keys", "expected"),
    cases(),
)
async def test_selected_profile_signs_every_request(
    aws_cli: str,
    tmp_path: Path,
    command: str,
    selector: str,
    environment_keys: bool,
    shared_keys: bool,
    expected: str,
) -> None:
    arguments, stdout_expected, files, objects = COMMANDS[command]
    work = tmp_path / "work"
    work.mkdir()
    write_tree(
        work, {"upload.txt": UPLOAD_FILE} if command == "upload" else {}
    )
    store = InMemoryS3(SEED_OBJECTS)
    selection: dict[str, str] = {"AWS_PROFILE": "selected"}
    extra: tuple[str, ...] = ()
    if selector == "--profile":
        selection["AWS_PROFILE"] = "default"
        extra = ("--profile", "selected")
    elif selector == "empty-flag":
        extra = ("--profile", "")
    elif selector == "AWS_DEFAULT_PROFILE":
        selection = {"AWS_DEFAULT_PROFILE": "selected"}
    shared = "[default]\n" + identity("DEFAULTSHARED")
    if shared_keys:
        shared += "[selected]\n" + identity("SHARED")
    async with s3_runtime(store, tmp_path) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(CONFIG, encoding="utf-8")
        Path(env["AWS_SHARED_CREDENTIALS_FILE"]).write_text(
            shared, encoding="utf-8"
        )
        env.update(ENV_KEYS if environment_keys else NO_ENV_KEYS)
        env.update(selection)
        stdout, stderr, returncode = await run_command(
            [aws_cli, *arguments, *extra], env, cwd=work, stdin=None
        )
    report = (
        f"exit {returncode}\nstdout: {stdout!r}\nstderr: {stderr!r}\n"
        f"failures: {store.failures}\n"
    )
    assert store.failures == [], report
    assert (returncode, decoded(stdout), decoded(stderr)) == (
        0,
        stdout_expected,
        "",
    ), report
    assert read_tree(work) == files, report
    assert store.objects == objects, report
    signers = {
        (
            request.wire_request.headers.get("Authorization", "")
            .partition("Credential=")[2]
            .partition("/")[0],
            request.wire_request.headers.get("x-amz-security-token"),
        )
        for request in store.received
    }
    assert store.received, report
    assert signers == {(f"AKID{expected}", f"{expected}-token")}, report


# A credential helper wins over the static keys the same profile holds
# (credentials.py:2238-2256), so a helper that cannot start fails the
# command before any request, even beside keys that would sign it.
@pytest.mark.parametrize(
    "arguments",
    [
        ("s3", "ls", f"s3://{BUCKET}"),
        ("s3", "cp", f"s3://{BUCKET}/download/object.txt", "./never-written"),
    ],
    ids=["ls", "cp"],
)
async def test_a_missing_credential_helper_fails_before_any_request(
    aws_cli: str, tmp_path: Path, arguments: tuple[str, ...]
) -> None:
    async with s3_runtime(InMemoryS3(SEED_OBJECTS), tmp_path) as (
        server,
        env,
    ):
        Path(env["AWS_CONFIG_FILE"]).write_text(
            "[profile work]\n"
            "region = us-east-1\n"
            "credential_process = ./missing-credential-helper\n"
            "aws_access_key_id = config-key\n"
            "aws_secret_access_key = config-secret\n",
            encoding="utf-8",
        )
        del env["AWS_ACCESS_KEY_ID"], env["AWS_SECRET_ACCESS_KEY"]
        stdout, stderr, rc = await run_command(
            [aws_cli, "--profile", "work", *arguments], env, cwd=tmp_path
        )
    missing = (
        "The system cannot find the file specified"
        if os.name == "nt"
        else "No such file or directory"
    )
    assert (rc, stdout) == (255, b""), stderr.decode()
    assert missing in decoded(stderr)
    assert not server.requests
    assert not (tmp_path / "never-written").exists()
