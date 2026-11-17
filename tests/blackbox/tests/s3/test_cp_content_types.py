"""The Content-Type `s3 cp` gives an uploaded object.

Upstream guesses it from the source file's name with the interpreter's
mimetypes (customizations/s3/utils.py:340-346, guess_content_type), which
reads the host's mime.types files after its own table, and sends it on
the PutObject of a single upload or the CreateMultipartUpload of a
multipart one. Some keys' extensions differ from their sources' to show
that the source's name decides. --no-guess-mime-type turns the guess off.
"""

import mimetypes
import os
from collections.abc import Collection, Mapping
from pathlib import Path
from typing import Final

import pytest

from credhelpers import run_command
from s3store import InMemoryS3, decoded, pattern_bytes, s3_runtime, write_tree

pytestmark = pytest.mark.asyncio

BUCKET: Final = "bucket"
MIB: Final = 1024 * 1024
PREFIX: Final = "typed/"
CHUNKED_CONFIG: Final = (
    "[default]\ns3 =\n  preferred_transfer_client = crt\n"
    "  multipart_chunksize = 5MB\n  multipart_threshold = 6MB\n"
)
# Each source, the key a single upload names, and its type: what
# mimetypes.guess_type returns first, None where it knows no type.
KEYS: Final[Mapping[str, str]] = {
    "index.html": "index.html",
    "NOTES.TXT": "notes.txt",
    "page.html": "page.bin",
    "archive.tar.gz": "archive.tar.gz",
    "bundle.tgz": "bundle.tgz",
    "drawing.svgz": "drawing.svgz",
    "lone.gz": "lone.gz",
    "upper.GZ": "upper.GZ",
    "report.PDF": "report",
    "data.unknownext": "data.json",
    "Makefile": "Makefile",
    "sound.wav": "sound.wav",
    "strings.ts": "strings.ts",
    "package.deb": "package.deb",
}
# The types the AWS CLI's own table, CPython 3.14's
# (crates/s3/src/mime/defaults.rs), gives the extensions that hosts'
# mime.types files and Windows registries commonly type differently. It has
# none for .ts.
CLI_TABLE_TYPES: Final[Mapping[str, str]] = {
    ".wav": "audio/vnd.wave",
    ".deb": "application/x-debian-package",
}


def host_overlaid_types(names: Collection[str]) -> dict[str, str | None]:
    """The type of each of `names`: `CLI_TABLE_TYPES`, overridden by the
    host's registry types on Windows and then by its mime.types files, in
    the order the AWS CLI's `mimetypes.init` reads them.

    The pytest interpreter's own table need not match the CLI's (3.12
    types .wav as audio/x-wav and has no .deb), so the database holds only
    `CLI_TABLE_TYPES` before the registry and the files.
    """
    database = mimetypes.MimeTypes()
    strict = database.types_map[True]
    strict.clear()
    strict.update(CLI_TABLE_TYPES)
    # Reads nothing off Windows, where CPython reads no registry.
    database.read_windows_registry()
    for path in mimetypes.knownfiles:
        if os.path.isfile(path):
            database.read(path)
    return {name: database.guess_type(name)[0] for name in names}


TYPES: Final[Mapping[str, str | None]] = {
    "index.html": "text/html",
    # The suffix maps without regard to case.
    "NOTES.TXT": "text/plain",
    "page.html": "text/html",
    # A compression suffix names the encoding, and the type comes from the
    # suffix before it; alone, it leaves no type.
    "archive.tar.gz": "application/x-tar",
    "bundle.tgz": "application/x-tar",
    "drawing.svgz": "image/svg+xml",
    "lone.gz": None,
    # Encodings match case, so .GZ is the gzip type instead.
    "upper.GZ": "application/gzip",
    "report.PDF": "application/pdf",
    "data.unknownext": None,
    "Makefile": None,
    # Hosts' mime.types files and Windows registries commonly type these
    # differently, and their entries win over the CLI's table, so the host
    # decides.
    **host_overlaid_types(("sound.wav", "strings.ts", "package.deb")),
}
# The sources a single upload carries, and a multipart upload: their size
# takes them past the 6 MiB threshold.
SINGLE_SOURCES: Final = (
    "index.html",
    "page.html",
    "archive.tar.gz",
    "data.unknownext",
)
SIZES: Final[Mapping[str, int]] = {
    "PutObject": 1024,
    "CreateMultipartUpload": 6 * MIB + 1,
}


async def upload(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    local_files: Mapping[str, bytes],
) -> tuple[InMemoryS3, dict[str, tuple[str, str | None]]]:
    """Run one upload; return the bucket and each object's typing request:
    its operation and the Content-Type it sent."""
    work = tmp_path / "work"
    work.mkdir(parents=True)
    write_tree(work, local_files)
    store = InMemoryS3()
    async with s3_runtime(store, tmp_path) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(
            CHUNKED_CONFIG, encoding="utf-8"
        )
        stdout, stderr, returncode = await run_command(
            [aws_cli, "s3", "cp", *arguments, "--no-progress"],
            env,
            cwd=work,
            stdin=None,
        )
    report = (
        f"exit {returncode}\nstdout: {decoded(stdout)!r}\n"
        f"stderr: {decoded(stderr)!r}\nfailures: {store.failures}\n"
    )
    assert store.failures == [], report
    assert (returncode, stderr) == (0, b""), report
    typed = {
        request.params["Key"]: (
            request.operation_model.name,
            request.params.get("ContentType"),
        )
        for request in store.received
        if request.operation_model.name in SIZES
    }
    return store, typed


@pytest.mark.parametrize("operation", SIZES)
async def test_cp_single_upload_types_object_by_source_name(
    aws_cli: str, tmp_path: Path, operation: str
) -> None:
    for name in SINGLE_SOURCES:
        body = pattern_bytes(name, SIZES[operation])
        key = f"{PREFIX}{KEYS[name]}"
        store, typed = await upload(
            aws_cli,
            tmp_path / name,
            (name, f"s3://{BUCKET}/{key}"),
            {name: body},
        )
        assert store.objects == {(BUCKET, key): body}
        assert typed == {key: (operation, TYPES[name])}


@pytest.mark.parametrize(
    ("operation", "names"),
    [
        pytest.param(
            "PutObject",
            tuple(KEYS),
            id="PutObject",
            # The public AWS CLI does the same there.
            marks=pytest.mark.skipif(
                os.name != "posix",
                reason="Windows takes MIME types from the registry, "
                "which maps some suffixes differently",
            ),
        ),
        pytest.param(
            "CreateMultipartUpload", SINGLE_SOURCES, id="CreateMultipartUpload"
        ),
    ],
)
async def test_cp_recursive_upload_types_each_object_by_source_name(
    aws_cli: str, tmp_path: Path, operation: str, names: tuple[str, ...]
) -> None:
    files = {name: pattern_bytes(name, SIZES[operation]) for name in names}
    store, typed = await upload(
        aws_cli,
        tmp_path,
        ("typed", f"s3://{BUCKET}/{PREFIX}", "--recursive"),
        {f"typed/{name}": body for name, body in files.items()},
    )
    assert store.objects == {
        (BUCKET, f"{PREFIX}{name}"): body for name, body in files.items()
    }
    assert typed == {
        f"{PREFIX}{name}": (operation, TYPES[name]) for name in names
    }


# --no-guess-mime-type leaves an object untyped unless --content-type types
# it: upstream adds the subscriber that guesses only when guessing is on and
# no type is given (s3handler.py:327-330, 394-396).
NO_GUESS: Final = [
    pytest.param(("--no-guess-mime-type",), None, id="untyped"),
    pytest.param(
        ("--no-guess-mime-type", "--content-type", "text/x-explicit"),
        "text/x-explicit",
        id="explicit-type",
    ),
]


@pytest.mark.parametrize(("flags", "sent"), NO_GUESS)
@pytest.mark.parametrize("operation", SIZES)
async def test_cp_single_upload_without_guessing_sends_only_an_explicit_type(
    aws_cli: str,
    tmp_path: Path,
    operation: str,
    flags: tuple[str, ...],
    sent: str | None,
) -> None:
    name = "index.html"
    body = pattern_bytes(name, SIZES[operation])
    key = f"{PREFIX}{KEYS[name]}"
    store, typed = await upload(
        aws_cli,
        tmp_path,
        (name, f"s3://{BUCKET}/{key}", *flags),
        {name: body},
    )
    assert store.objects == {(BUCKET, key): body}
    assert typed == {key: (operation, sent)}


@pytest.mark.parametrize(("flags", "sent"), NO_GUESS)
async def test_cp_recursive_upload_without_guessing_sends_only_an_explicit_type(
    aws_cli: str,
    tmp_path: Path,
    flags: tuple[str, ...],
    sent: str | None,
) -> None:
    files = {
        name: pattern_bytes(name, SIZES["PutObject"])
        for name in SINGLE_SOURCES
    }
    store, typed = await upload(
        aws_cli,
        tmp_path,
        ("typed", f"s3://{BUCKET}/{PREFIX}", "--recursive", *flags),
        {f"typed/{name}": body for name, body in files.items()},
    )
    assert store.objects == {
        (BUCKET, f"{PREFIX}{name}"): body for name, body in files.items()
    }
    assert typed == {
        f"{PREFIX}{name}": ("PutObject", sent) for name in SINGLE_SOURCES
    }
