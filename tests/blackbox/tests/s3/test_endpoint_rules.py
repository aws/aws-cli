"""The S3 endpoint host the endpoint rules choose, and the requests they
refuse.

Without --endpoint-url, botocore's endpoint rules (the S3
endpoint-rule-set in botocore/data/s3/2006-03-01/) build each request's
host from the bucket, the region, and the profile's s3 settings. The TLS
intercept proxy answers any host with the in-memory bucket of s3store.py,
so the tests read the host each request was sent to. Some settings the
rules refuse outright: those commands fail before any request.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest

from credhelpers import run_command
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
DOTTED_BUCKET: Final = "bucket.with.dots"
UPLOAD_FILE: Final = pattern_bytes("upload", 3000)
SEED_OBJECTS: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, "key.txt"): pattern_bytes("key", 17),
    (DOTTED_BUCKET, "key.txt"): pattern_bytes("key", 17),
}
LISTED_LINE: Final = "2026-01-02 03:04:05         17 key.txt\n"
ACCELERATE: Final = "  use_accelerate_endpoint = true\n"


def s3_block(lines: str) -> str:
    return f"[default]\ns3 =\n{lines}"


@dataclass(frozen=True)
class Run:
    returncode: int
    stdout: str
    stderr: str
    local_files: dict[str, bytes]
    store: InMemoryS3

    def describe(self) -> str:
        return (
            f"exit {self.returncode}\n"
            f"stdout: {self.stdout!r}\n"
            f"stderr: {self.stderr!r}\n"
            f"responses: {self.store.responses}\n"
            f"failures: {self.store.failures}\n"
        )

    def hosts(self) -> set[str]:
        return {
            request.wire_request.headers.get("host", "")
            for request in self.store.received
        }


async def run_aws(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    *,
    config: str = "",
    environment: Mapping[str, str] | None = None,
    local_files: Mapping[str, bytes] | None = None,
) -> Run:
    work = tmp_path / "work"
    work.mkdir()
    write_tree(work, local_files or {})
    store = InMemoryS3(SEED_OBJECTS)
    async with s3_runtime(store, tmp_path) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(config, encoding="utf-8")
        env.update(environment or {})
        stdout, stderr, returncode = await run_command(
            [aws_cli, *arguments], env, cwd=work, stdin=None
        )
    return Run(
        returncode=returncode,
        stdout=decoded(stdout),
        stderr=decoded(stderr),
        local_files=read_tree(work),
        store=store,
    )


# `s3 ls` sends one ListObjectsV2 to the host the rules build. Path-style
# addressing is test_config_resolution.py's
# test_config_nested_s3_merge_keeps_or_replaces_whole_block[inherit-block].
@pytest.mark.parametrize(
    ("bucket", "config", "environment", "arguments", "host"),
    [
        pytest.param(
            BUCKET,
            s3_block(ACCELERATE),
            {},
            (),
            f"{BUCKET}.s3-accelerate.amazonaws.com",
            id="accelerate",
        ),
        # A dotted bucket cannot be a TLS host label, so it goes in the
        # path.
        pytest.param(
            DOTTED_BUCKET,
            "",
            {},
            (),
            "s3.us-east-1.amazonaws.com",
            id="dotted-bucket",
        ),
        pytest.param(
            BUCKET,
            s3_block("  use_dualstack_endpoint = true\n"),
            {},
            (),
            f"{BUCKET}.s3.dualstack.us-east-1.amazonaws.com",
            id="dual-stack",
        ),
        pytest.param(
            BUCKET,
            "",
            {"AWS_USE_FIPS_ENDPOINT": "true"},
            (),
            f"{BUCKET}.s3-fips.us-east-1.amazonaws.com",
            id="fips",
        ),
        # botocore turns a FIPS pseudo region into its region and the FIPS
        # flag (client.py:200-219).
        pytest.param(
            BUCKET,
            "",
            {},
            ("--region", "fips-us-west-2"),
            f"{BUCKET}.s3-fips.us-west-2.amazonaws.com",
            id="fips-pseudo-region",
        ),
        pytest.param(
            BUCKET,
            "",
            {},
            ("--region", "cn-north-1"),
            f"{BUCKET}.s3.cn-north-1.amazonaws.com.cn",
            id="china",
        ),
    ],
)
async def test_ls_sends_listing_to_the_host_the_rules_build(
    aws_cli: str,
    tmp_path: Path,
    bucket: str,
    config: str,
    environment: dict[str, str],
    arguments: tuple[str, ...],
    host: str,
) -> None:
    run = await run_aws(
        aws_cli,
        tmp_path,
        ("s3", "ls", f"s3://{bucket}/", *arguments),
        config=config,
        environment=environment,
    )
    report = run.describe()
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        LISTED_LINE,
        "",
    ), report
    assert run.store.operations() == ["ListObjectsV2"], report
    assert run.hosts() == {host}, report


DOTTED_KEY: Final = f"s3://{DOTTED_BUCKET}/key.txt"
# The rules' error messages (the S3 endpoint-rule-set), which the AWS CLI
# reports as a general error, or for `s3 cp` as the failed transfer or
# the fatal error of its HeadObject or listing.
PATH_STYLE: Final = "Path-style addressing cannot be used with S3 Accelerate"
NO_ACCELERATE: Final = "S3 Accelerate cannot be used in this region"
WITH_FIPS: Final = (
    "Unsupported configuration when using S3: Accelerate cannot be used "
    "with FIPS"
)
CUSTOM_ENDPOINT: Final = (
    "A custom endpoint cannot be combined with S3 Accelerate"
)


# Every case enables accelerate, which the rules refuse with a dotted
# bucket, in a partition without it, with FIPS, and with a custom
# endpoint. botocore raises the refusal while it resolves the endpoint,
# before it sends anything.
@pytest.mark.parametrize(
    ("arguments", "environment", "local_files", "returncode", "stderr"),
    [
        pytest.param(
            ("s3", "ls", f"s3://{DOTTED_BUCKET}/"),
            {},
            {},
            255,
            f"\naws: [ERROR]: {PATH_STYLE}\n",
            id="ls-dotted",
        ),
        pytest.param(
            ("s3", "ls", f"s3://{BUCKET}/", "--region", "cn-north-1"),
            {},
            {},
            255,
            f"\naws: [ERROR]: {NO_ACCELERATE}\n",
            id="ls-china",
        ),
        pytest.param(
            ("s3", "ls", f"s3://{BUCKET}/"),
            {"AWS_USE_FIPS_ENDPOINT": "true"},
            {},
            255,
            f"\naws: [ERROR]: {WITH_FIPS}\n",
            id="ls-fips",
        ),
        pytest.param(
            ("s3", "ls", f"s3://{BUCKET}/", "--region", "us-west-2-fips"),
            {},
            {},
            255,
            f"\naws: [ERROR]: {WITH_FIPS}\n",
            id="ls-fips-pseudo-region",
        ),
        pytest.param(
            (
                "s3",
                "ls",
                f"s3://{BUCKET}/",
                "--endpoint-url",
                "https://custom.example.com",
            ),
            {},
            {},
            255,
            f"\naws: [ERROR]: {CUSTOM_ENDPOINT}\n",
            id="ls-custom-endpoint",
        ),
        pytest.param(
            ("s3", "cp", DOTTED_KEY, "key.txt"),
            {},
            {},
            1,
            f"fatal error: {PATH_STYLE}\n",
            id="download-dotted",
        ),
        pytest.param(
            ("s3", "cp", "upload.txt", DOTTED_KEY),
            {},
            {"upload.txt": UPLOAD_FILE},
            1,
            f"upload failed: .{os.sep}upload.txt to {DOTTED_KEY} "
            f"{PATH_STYLE}\n",
            id="upload-dotted",
        ),
        pytest.param(
            ("s3", "cp", f"s3://{DOTTED_BUCKET}/", "down", "--recursive"),
            {},
            {},
            1,
            f"fatal error: {PATH_STYLE}\n",
            id="recursive-download-dotted",
        ),
        pytest.param(
            (
                "s3",
                "cp",
                f"s3://{BUCKET}/download/object.txt",
                "object.txt",
                "--region",
                "fips-us-west-2",
            ),
            {},
            {},
            1,
            f"fatal error: {WITH_FIPS}\n",
            id="download-fips-pseudo-region",
        ),
    ],
)
async def test_accelerate_rule_refusal_fails_before_any_request(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    environment: dict[str, str],
    local_files: dict[str, bytes],
    returncode: int,
    stderr: str,
) -> None:
    if arguments[1] == "cp":
        arguments = (*arguments, "--no-progress")
    run = await run_aws(
        aws_cli,
        tmp_path,
        arguments,
        config=s3_block(ACCELERATE),
        environment=environment,
        local_files=local_files,
    )
    report = run.describe()
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout, run.stderr) == (
        returncode,
        "",
        stderr,
    ), report
    assert run.local_files == local_files, report
    assert run.store.received == [], report
