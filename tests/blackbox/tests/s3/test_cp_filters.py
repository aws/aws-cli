"""What `s3 cp --include` and `--exclude` transfer.

Upstream's Filter (customizations/s3/filters.py) joins each pattern to the
source's root with os.path.join, then matches the path its file generator
names for each source file or object against every pattern in command-line
order with fnmatch: the last pattern that matches decides, and a source no
pattern matches is transferred. The root is a local source's abspath, or
its directory for a single file, and an S3 source's bucket and prefix as
the operand spells them, or a single object's parent prefix. Patterns are
not normalized, never match a directory, and `*` crosses separators;
fnmatch folds case on Windows only. The filter runs after the file
generator, so a single object is still headed and a skipped local source
still warned about, and before any transfer rule.

Each test runs one command against the in-memory bucket of s3store.py and
asserts the exit status, the output, what arrived, and what was requested.
"""

import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest

from credhelpers import run_command
from s3helpers import completion_lines
from s3store import (
    InMemoryS3,
    ObjectKey,
    decoded,
    pattern_bytes,
    read_tree,
    s3_runtime,
    write_tree,
)

BUCKET: Final = "bucket"
# The tree each recursive case copies, by its name below the source root.
NAMES: Final = (
    "a.txt",
    "ab.txt",
    "b.txt",
    "c.bin",
    "x.txt",
    "[x].txt",
    "é.txt",
    "nested/a.txt",
    "nested/d.bin",
)
TREE: Final = {
    name: pattern_bytes(name, 64 + index) for index, name in enumerate(NAMES)
}
BINARIES: Final = frozenset({"c.bin", "nested/d.bin"})


@dataclass(frozen=True)
class Run:
    returncode: int
    stdout: bytes
    stderr: bytes
    work: Path
    store: InMemoryS3

    def describe(self) -> str:
        return (
            f"rc={self.returncode}\nstdout={decoded(self.stdout)!r}\n"
            f"stderr={decoded(self.stderr)!r}\n"
            f"operations={self.store.operations()}"
        )

    def requested(self, operation: str) -> set[str]:
        """The keys `operation` was sent for."""
        return {
            request.params["Key"]
            for request in self.store.received
            if request.operation_model.name == operation
        }

    def stored(self) -> dict[str, bytes]:
        return {key: body for (_, key), body in self.store.objects.items()}


async def run_cp(
    aws_cli: str,
    tmp_path: Path,
    arguments: Sequence[str],
    *,
    local_files: Mapping[str, bytes] | None = None,
    objects: Mapping[ObjectKey, bytes] | None = None,
    storage: Mapping[str, tuple[str, str | None]] | None = None,
) -> Run:
    """Run `aws <arguments>` in tmp_path/work against a seeded bucket."""
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    write_tree(work, local_files or {})
    store = InMemoryS3(objects, storage=storage)
    async with s3_runtime(store, tmp_path) as (_, env):
        stdout, stderr, returncode = await run_command(
            [aws_cli, *arguments], env, cwd=work, stdin=None
        )
    assert not store.failures, store.failures
    return Run(returncode, stdout, stderr, work, store)


def local(name: str) -> str:
    """A relative local path as result lines show it, with os.sep: upstream
    joins the relpath of its directory, `.` for the working directory."""
    directory, _, basename = name.rpartition("/")
    return os.path.join(*(directory or ".").split("/"), basename)


def upload_line(source: str, key: str) -> str:
    return f"upload: {local(source)} to s3://{BUCKET}/{key}"


def download_line(key: str, destination: str) -> str:
    return f"download: s3://{BUCKET}/{key} to {local(destination)}"


def tree_objects(prefix: str) -> dict[ObjectKey, bytes]:
    return {(BUCKET, prefix + name): body for name, body in TREE.items()}


@dataclass(frozen=True)
class PatternCase:
    name: str
    flags: tuple[str, ...]
    # The names of TREE the filters keep from the transfer.
    excluded: frozenset[str]


def pattern_case(name: str, flags: tuple[str, ...], *excluded: str) -> PatternCase:
    return PatternCase(name, flags, frozenset(excluded))


PATTERN_CASES: Final = (
    # A pattern is joined to the source root, so a bare name matches only
    # the file directly below it.
    pattern_case("name-is-rooted", ("--exclude", "a.txt"), "a.txt"),
    pattern_case(
        "star-crosses-separators",
        ("--exclude", "*a.txt"),
        "a.txt",
        "nested/a.txt",
    ),
    # One character, which a two-byte UTF-8 name is too.
    pattern_case(
        "question-mark",
        ("--exclude", "?.txt"),
        "a.txt",
        "b.txt",
        "x.txt",
        "é.txt",
    ),
    pattern_case("set", ("--exclude", "[ab].txt"), "a.txt", "b.txt"),
    pattern_case("set-is-not-literal", ("--exclude", "[x].txt"), "x.txt"),
    pattern_case(
        "negated-set",
        ("--exclude", "[!a].txt"),
        "b.txt",
        "x.txt",
        "é.txt",
    ),
    pattern_case(
        "range", ("--exclude", "[a-b]*"), "a.txt", "ab.txt", "b.txt"
    ),
    pattern_case("bracket-in-set", ("--exclude", "[[]x].txt"), "[x].txt"),
    pattern_case("unclosed-bracket", ("--exclude", "[x*"), "[x].txt"),
    # fnmatch drops a reversed range, which leaves a set nothing matches.
    pattern_case("reversed-range", ("--exclude", "[z-a]*")),
    # Only files are matched, never the directories holding them.
    pattern_case("directory-name", ("--exclude", "nested")),
    pattern_case(
        "directory-contents",
        ("--exclude", "nested/*"),
        "nested/a.txt",
        "nested/d.bin",
    ),
    # The joined pattern keeps its `.` segment, which no path has.
    pattern_case("dot-segment", ("--exclude", "./a.txt")),
    pattern_case(
        "include-after-exclude",
        ("--exclude", "*", "--include", "*.bin"),
        *(set(NAMES) - BINARIES),
    ),
    pattern_case(
        "exclude-after-include", ("--include", "*.bin", "--exclude", "*"), *NAMES
    ),
    # argparse hands the filter each option's full name.
    pattern_case(
        "abbreviated-options",
        ("--exc=*", "--inc", "*.bin"),
        *(set(NAMES) - BINARIES),
    ),
    # ntpath.normcase lowercases both sides; posixpath's changes nothing.
    pattern_case(
        "case",
        ("--exclude", "A.TXT"),
        *(["a.txt"] if os.name == "nt" else []),
    ),
)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", PATTERN_CASES, ids=lambda case: case.name)
async def test_cp_recursive_upload_filters_walked_files(
    aws_cli: str, tmp_path: Path, case: PatternCase
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            "src",
            f"s3://{BUCKET}/prefix/",
            "--recursive",
            "--no-progress",
            *case.flags,
        ],
        local_files={f"src/{name}": body for name, body in TREE.items()},
    )
    kept = [name for name in NAMES if name not in case.excluded]
    assert (run.returncode, run.stderr) == (0, b""), run.describe()
    assert run.stored() == {f"prefix/{name}": TREE[name] for name in kept}
    assert run.requested("PutObject") == {f"prefix/{name}" for name in kept}
    assert sorted(completion_lines(run.stdout)) == sorted(
        upload_line(f"src/{name}", f"prefix/{name}") for name in kept
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("case", PATTERN_CASES, ids=lambda case: case.name)
async def test_cp_recursive_download_filters_listed_objects(
    aws_cli: str, tmp_path: Path, case: PatternCase
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            f"s3://{BUCKET}/tree/",
            "out",
            "--recursive",
            "--no-progress",
            *case.flags,
        ],
        objects=tree_objects("tree/"),
    )
    kept = [name for name in NAMES if name not in case.excluded]
    assert (run.returncode, run.stderr) == (0, b""), run.describe()
    assert read_tree(run.work / "out") == {name: TREE[name] for name in kept}
    assert run.requested("GetObject") == {f"tree/{name}" for name in kept}
    assert sorted(completion_lines(run.stdout)) == sorted(
        download_line(f"tree/{name}", f"out/{name}") for name in kept
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source", "root"),
    [
        pytest.param("s3://bucket/tree", "tree/", id="prefix"),
        pytest.param("s3://bucket/tree/", "tree/", id="prefix-with-slash"),
        pytest.param("s3://bucket", "", id="bucket"),
        pytest.param("s3://bucket/", "", id="bucket-with-slash"),
    ],
)
async def test_cp_recursive_download_roots_patterns_at_the_source_prefix(
    aws_cli: str, tmp_path: Path, source: str, root: str
) -> None:
    objects = {**tree_objects("tree/"), (BUCKET, "top.txt"): b"top"}
    # The same keys, each spelled relative to the listing's root.
    selected = ["tree/nested/a.txt", "tree/nested/d.bin"]
    pattern = "tree/nested/*".removeprefix(root)
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            source,
            "out",
            "--recursive",
            "--no-progress",
            "--exclude",
            "*",
            "--include",
            pattern,
        ],
        objects=objects,
    )
    assert (run.returncode, run.stderr) == (0, b""), run.describe()
    assert read_tree(run.work / "out") == {
        key.removeprefix(root): objects[(BUCKET, key)] for key in selected
    }
    assert run.requested("GetObject") == set(selected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source", "flags", "uploaded"),
    [
        pytest.param(
            "a.txt", ["--exclude", "a.txt"], False, id="rooted-at-its-directory"
        ),
        pytest.param(
            "nested/a.txt",
            ["--exclude", "a.txt"],
            False,
            id="rooted-at-a-nested-directory",
        ),
        # The root is the file's directory, not the working directory.
        pytest.param(
            "nested/a.txt",
            ["--exclude", "nested/a.txt"],
            True,
            id="operand-spelling-does-not-match",
        ),
        pytest.param(
            "a.txt",
            ["--exclude", "*", "--include", "a.*"],
            True,
            id="include-after-exclude",
        ),
    ],
)
async def test_cp_single_upload_filters_its_source(
    aws_cli: str,
    tmp_path: Path,
    source: str,
    flags: list[str],
    uploaded: bool,
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        ["s3", "cp", source, f"s3://{BUCKET}/key.txt", "--no-progress", *flags],
        local_files={source: TREE["a.txt"]},
    )
    assert (run.returncode, run.stderr) == (0, b""), run.describe()
    if uploaded:
        assert run.stored() == {"key.txt": TREE["a.txt"]}
        assert completion_lines(run.stdout) == [upload_line(source, "key.txt")]
    else:
        assert run.stored() == {}
        assert run.stdout == b""
        assert run.store.operations() == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("key", "flags", "downloaded"),
    [
        pytest.param(
            "tree/a.txt", ["--exclude", "a.txt"], False, id="rooted-at-its-prefix"
        ),
        pytest.param(
            "tree/a.txt",
            ["--exclude", "tree/a.txt"],
            True,
            id="key-spelling-does-not-match",
        ),
        pytest.param(
            "top.txt", ["--exclude", "top.txt"], False, id="rooted-at-the-bucket"
        ),
        pytest.param(
            "tree/a.txt",
            ["--exclude", "*", "--include", "*.txt"],
            True,
            id="include-after-exclude",
        ),
        # ntpath.join keeps a pattern on another drive whole, so it matches
        # neither root's sources. Windows CPython finds a drive's colon at
        # the second UTF-16 unit, which a code point past the BMP fills.
        pytest.param(
            "é:file",
            ["--exclude", "*", "--include", "é:*"],
            os.name != "nt",
            id="drive-relative-pattern",
        ),
        pytest.param(
            "\U00020000:file",
            ["--exclude", "*", "--include", "\U00020000:*"],
            True,
            id="no-drive-past-the-bmp",
        ),
    ],
)
async def test_cp_single_download_heads_its_object_before_filtering(
    aws_cli: str,
    tmp_path: Path,
    key: str,
    flags: list[str],
    downloaded: bool,
) -> None:
    body = pattern_bytes(key, 100)
    run = await run_cp(
        aws_cli,
        tmp_path,
        ["s3", "cp", f"s3://{BUCKET}/{key}", "local.txt", "--no-progress", *flags],
        objects={(BUCKET, key): body},
    )
    assert (run.returncode, run.stderr) == (0, b""), run.describe()
    # The file generator heads the object before the filter sees it.
    assert run.requested("HeadObject") == {key}, run.describe()
    if downloaded:
        assert read_tree(run.work) == {"local.txt": body}
        assert completion_lines(run.stdout) == [download_line(key, "local.txt")]
    else:
        assert read_tree(run.work) == {}
        assert run.stdout == b""
        assert run.requested("GetObject") == set()


@pytest.mark.asyncio
async def test_cp_recursive_upload_absolute_pattern_replaces_the_root(
    aws_cli: str, tmp_path: Path
) -> None:
    # An absolute operand keeps the working directory's spelling out of
    # the source path the pattern must equal.
    source = tmp_path / "work" / "src"
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            str(source),
            f"s3://{BUCKET}/prefix/",
            "--recursive",
            "--no-progress",
            "--exclude",
            str(source / "nested" / "a.txt"),
        ],
        local_files={f"src/{name}": body for name, body in TREE.items()},
    )
    kept = [name for name in NAMES if name != "nested/a.txt"]
    assert (run.returncode, run.stderr) == (0, b""), run.describe()
    assert run.stored() == {f"prefix/{name}": TREE[name] for name in kept}


@pytest.mark.asyncio
async def test_cp_recursive_download_excluded_archive_is_not_warned_about(
    aws_cli: str, tmp_path: Path
) -> None:
    # The filter drops the object before the Glacier rule could warn.
    objects = {
        (BUCKET, "tree/a.txt"): TREE["a.txt"],
        (BUCKET, "tree/frozen.txt"): b"frozen",
    }
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            f"s3://{BUCKET}/tree/",
            "out",
            "--recursive",
            "--no-progress",
            "--exclude",
            "frozen.txt",
        ],
        objects=objects,
        storage={"tree/frozen.txt": ("GLACIER", None)},
    )
    assert (run.returncode, run.stderr) == (0, b""), run.describe()
    assert read_tree(run.work / "out") == {"a.txt": TREE["a.txt"]}
    assert completion_lines(run.stdout) == [
        download_line("tree/a.txt", "out/a.txt")
    ]


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink fixture")
async def test_cp_recursive_upload_excluded_source_is_still_warned_about(
    aws_cli: str, tmp_path: Path
) -> None:
    # The file generator warns about a source it skips before the filter
    # sees anything, so excluding it changes neither the warning nor the
    # status.
    source = tmp_path / "work" / "src"
    source.mkdir(parents=True)
    (source / "dangling").symlink_to("absent")
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            str(source),
            f"s3://{BUCKET}/prefix/",
            "--recursive",
            "--no-progress",
            "--exclude",
            "*",
        ],
        local_files={"src/a.txt": TREE["a.txt"]},
    )
    assert run.returncode == 2, run.describe()
    assert run.stdout == b"", run.describe()
    assert decoded(run.stderr) == (
        f"warning: Skipping file {source}/dangling. File does not exist.\n"
    )
    assert run.store.operations() == []


@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.platform != "linux", reason="Linux names files with any bytes"
)
async def test_cp_recursive_upload_question_mark_matches_one_undecodable_byte(
    aws_cli: str, tmp_path: Path
) -> None:
    # Python decodes each byte that is not UTF-8 to one surrogate escape.
    # Its key could not be encoded, so the upload would fail unless the
    # filter excluded it.
    name = os.fsdecode(b"\xff.txt")
    run = await run_cp(
        aws_cli,
        tmp_path,
        [
            "s3",
            "cp",
            "src",
            f"s3://{BUCKET}/prefix/",
            "--recursive",
            "--no-progress",
            "--exclude",
            "?.txt",
        ],
        local_files={f"src/{name}": b"undecodable", "src/ab.txt": TREE["ab.txt"]},
    )
    assert (run.returncode, run.stderr) == (0, b""), run.describe()
    assert run.stored() == {"prefix/ab.txt": TREE["ab.txt"]}
