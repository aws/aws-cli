"""What `s3 cp` reports first when its client setup, its sources, and its
endpoint each have something to say.

Upstream's command builds its transfer client before anything else
(customizations/s3/subcommands.py CpCommand, factory.py:131-141): a CRT
client that cannot be built fails the command with the general handler's
status 255 before any warning or source check. The built client then
prints its warning about the settings it ignores (factory.py:303-321).
Only then does the file generator inspect each local source, skipping one
it cannot read with a warning (filegenerator.py:323-341), and only a
transfer it submits meets the endpoint rule that refuses its request. No
case here sends a request.
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
    decoded,
    pattern_bytes,
    read_tree,
    s3_runtime,
    without_cwd,
    write_tree,
)

pytestmark = pytest.mark.asyncio

BUCKET: Final = "bucket"
DOTTED_KEY: Final = "s3://bucket.with.dots/key.txt"
UPLOAD_FILE: Final = pattern_bytes("upload", 3000)
MALFORMED_CA_BUNDLE: Final = b"not a certificate\n"
# The AwsCrtError the CRT client's construction raises for the bundle,
# which the general handler prints (clidriver.py).
UNBUILDABLE_CLIENT: Final = (
    "\naws: [ERROR]: 34 (AWS_ERROR_INVALID_ARGUMENT): An invalid argument "
    "was passed to a function.\n"
)
ACCELERATE: Final = "  use_accelerate_endpoint = true\n"
CRT_BLOCK: Final = "[default]\ns3 =\n  preferred_transfer_client = crt\n"
IGNORED_KEYS: Final = (
    "  max_queue_size = 5\n  io_chunksize = 1MB\n  max_bandwidth = 10MB/s\n"
)
IGNORED_WARNING: Final = (
    "warning: The following configuration values are not supported by the "
    "'crt' s3 transfer client and will be ignored: "
    "max_bandwidth, max_queue_size, io_chunksize.\n"
)
# Local sources the file generator skips, by kind.
FIFO: Final = "fifo"
UNREADABLE_FILE: Final = "unreadable-file"
# Its reasons (filegenerator.py:323-341).
SPECIAL_REASON: Final = (
    "File is character special device, block special device, FIFO, or socket."
)
UNREADABLE_REASON: Final = "File/Directory is not readable."


def skipped_line(source: str, reason: str) -> str:
    """A skipped source's warning, by absolute path (utils.py:308-319)."""
    return (
        f"warning: Skipping file {os.path.join('<cwd>', source)}. {reason}\n"
    )


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


def make_special(path: Path, kind: str) -> None:
    """Create a source the file generator skips; skip where it cannot be.

    A privileged identity reads a file its mode denies, so the case skips
    rather than assert on a readable source.
    """
    if os.name == "nt":
        pytest.skip("FIFOs and unreadable files are POSIX fixtures")
    if kind == FIFO:
        os.mkfifo(path)
        return
    path.write_bytes(UPLOAD_FILE)
    path.chmod(0)
    if os.access(path, os.R_OK):
        path.chmod(0o600)
        pytest.skip("this identity reads files their mode denies")


async def run_cp(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    *,
    config: str,
    environment: Mapping[str, str] | None = None,
    local_files: Mapping[str, bytes] | None = None,
    specials: Mapping[str, str] | None = None,
    ca_bundle: bytes | None = None,
) -> Run:
    """Run `aws s3 cp <arguments>` once in tmp_path/work.

    `ca_bundle` replaces the proxy's CA bundle with bundle.pem holding
    those bytes, or a copy of the proxy's CA if they are empty.
    """
    work = tmp_path / "work"
    work.mkdir()
    write_tree(work, local_files or {})
    for name, kind in (specials or {}).items():
        make_special(work / name, kind)
    store = InMemoryS3()
    try:
        async with s3_runtime(store, tmp_path) as (_, env):
            Path(env["AWS_CONFIG_FILE"]).write_text(config, encoding="utf-8")
            if ca_bundle is not None:
                proxy_ca = Path(env["AWS_CA_BUNDLE"]).read_bytes()
                (work / "bundle.pem").write_bytes(ca_bundle or proxy_ca)
                env["AWS_CA_BUNDLE"] = "bundle.pem"
            env.update(environment or {})
            # Bounded by run_command's timeout, so a CLI that opened a
            # FIFO fails instead of hanging.
            stdout, stderr, returncode = await run_command(
                [aws_cli, "s3", "cp", *arguments, "--no-progress"],
                env,
                cwd=work,
                stdin=None,
            )
    finally:
        for name, kind in (specials or {}).items():
            if kind == UNREADABLE_FILE:
                (work / name).chmod(0o600)
    local = read_tree(work)
    local.pop("bundle.pem", None)
    return Run(
        returncode=returncode,
        stdout=decoded(without_cwd(stdout, work)),
        stderr=decoded(without_cwd(stderr, work)),
        local_files=local,
        store=store,
    )


SKIPPED_SOURCES: Final = [
    pytest.param("pipe", FIFO, SPECIAL_REASON, id="pipe"),
    pytest.param(
        "locked.txt", UNREADABLE_FILE, UNREADABLE_REASON, id="locked"
    ),
]


# A skipped source is inspected after the client printed its warning and
# before any request, so it never meets the rule error its request would
# raise: the command exits 2 for the skip alone.
@pytest.mark.parametrize(("source", "kind", "reason"), SKIPPED_SOURCES)
@pytest.mark.parametrize(
    ("config", "destination", "warning"),
    [
        pytest.param(
            CRT_BLOCK + IGNORED_KEYS,
            f"s3://{BUCKET}/up/skipped",
            IGNORED_WARNING,
            id="ignored-settings",
        ),
        pytest.param(
            "[default]\ns3 =\n" + ACCELERATE, DOTTED_KEY, "", id="rule-error"
        ),
        pytest.param(
            CRT_BLOCK + IGNORED_KEYS + ACCELERATE,
            DOTTED_KEY,
            IGNORED_WARNING,
            id="ignored-settings-and-rule-error",
        ),
    ],
)
async def test_cp_skipped_source_follows_client_setup(
    aws_cli: str,
    tmp_path: Path,
    config: str,
    destination: str,
    warning: str,
    source: str,
    kind: str,
    reason: str,
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        (source, destination),
        config=config,
        specials={source: kind},
    )
    report = run.describe()
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout, run.stderr) == (
        2,
        "",
        warning + skipped_line(source, reason),
    ), report
    assert run.store.received == [], report


# Refused requests whose client still builds: the accelerate rules refuse
# a dotted bucket, and the rules refuse a partition's FIPS variant. A
# malformed request proxy is only resolved for a request.
PATH_STYLE: Final = "Path-style addressing cannot be used with S3 Accelerate"
REFUSALS: Final = {
    "accelerate": (ACCELERATE, {}, PATH_STYLE),
    "partition-fips": (
        "",
        {"AWS_REGION": "cn-north-1", "AWS_USE_FIPS_ENDPOINT": "true"},
        "Partition does not support FIPS",
    ),
    "accelerate-request-proxy": (
        ACCELERATE,
        {"HTTPS_PROXY": "http://proxy:bad"},
        PATH_STYLE,
    ),
}
OPERANDS: Final = [
    pytest.param(("pipe", DOTTED_KEY), id="skipped-upload"),
    pytest.param(("src/upload.txt", DOTTED_KEY), id="upload"),
    pytest.param(("src", DOTTED_KEY, "--recursive"), id="recursive-upload"),
    pytest.param((DOTTED_KEY, "out.txt"), id="download"),
    pytest.param(
        (DOTTED_KEY, "outdir", "--recursive"), id="recursive-download"
    ),
]


def refusal_output(operands: tuple[str, ...], message: str) -> tuple[int, str]:
    """The status and stderr of a command whose transfers are refused."""
    if operands[0] == "pipe":
        return 2, skipped_line("pipe", SPECIAL_REASON)
    if operands[0] == DOTTED_KEY:
        # The HeadObject or the listing is refused (results.py:448-451).
        return 1, f"fatal error: {message}\n"
    key = DOTTED_KEY if operands[0] != "src" else f"{DOTTED_KEY}/upload.txt"
    source = os.path.join("src", "upload.txt")
    return 1, f"upload failed: {source} to {key} {message}\n"


@pytest.mark.parametrize("operands", OPERANDS)
@pytest.mark.parametrize("refusal", REFUSALS)
async def test_cp_endpoint_refusal_follows_client_setup(
    aws_cli: str, tmp_path: Path, refusal: str, operands: tuple[str, ...]
) -> None:
    block, environment, message = REFUSALS[refusal]
    run = await run_cp(
        aws_cli,
        tmp_path,
        operands,
        config=CRT_BLOCK + block,
        environment=environment,
        local_files={"src/upload.txt": UPLOAD_FILE},
        specials={"pipe": FIFO},
        ca_bundle=b"",
    )
    report = run.describe()
    assert run.store.failures == [], report
    returncode, stderr = refusal_output(operands, message)
    assert (run.returncode, run.stdout, run.stderr) == (
        returncode,
        "",
        stderr,
    ), report
    assert run.local_files == {"src/upload.txt": UPLOAD_FILE}, report
    assert run.store.received == [], report


# A CRT client that cannot load its CA bundle fails every command alike,
# whatever its operands and whether or not its requests would be refused.
@pytest.mark.parametrize("operands", OPERANDS)
async def test_cp_unbuildable_client_fails_before_endpoint_refusal(
    aws_cli: str, tmp_path: Path, operands: tuple[str, ...]
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        operands,
        config=CRT_BLOCK + ACCELERATE,
        local_files={"src/upload.txt": UPLOAD_FILE},
        specials={"pipe": FIFO},
        ca_bundle=MALFORMED_CA_BUNDLE,
    )
    report = run.describe()
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout, run.stderr) == (
        255,
        "",
        UNBUILDABLE_CLIENT,
    ), report
    assert run.local_files == {"src/upload.txt": UPLOAD_FILE}, report
    assert run.store.received == [], report


# Nor does it print its warning or inspect a source first.
@pytest.mark.parametrize(
    ("source", "kind"),
    [
        pytest.param("upload.txt", None, id="file"),
        pytest.param("pipe", FIFO, id="pipe"),
        pytest.param("locked.txt", UNREADABLE_FILE, id="locked"),
    ],
)
async def test_cp_unbuildable_client_fails_before_source_checks(
    aws_cli: str, tmp_path: Path, source: str, kind: str | None
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        (source, f"s3://{BUCKET}/up/key"),
        config=CRT_BLOCK + IGNORED_KEYS,
        local_files={"upload.txt": UPLOAD_FILE} if kind is None else {},
        specials={} if kind is None else {source: kind},
        ca_bundle=MALFORMED_CA_BUNDLE,
    )
    report = run.describe()
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout, run.stderr) == (
        255,
        "",
        UNBUILDABLE_CLIENT,
    ), report
    assert run.store.received == [], report
