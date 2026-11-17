import os
import re
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
    s3_runtime,
    without_cwd,
    write_tree,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(os.name == "nt", reason="creates symlinks"),
]

# `--follow-symlinks` and `--no-follow-symlinks` on `s3 cp`, `s3 mv`, and
# `s3 sync`. Both share one destination, so the last one given wins, and
# links are followed by default (subcommands.py:121-147, 1763-1764).
#
# A local walk, an upload's source or a sync download's destination, drops
# each link it lists under `--no-follow-symlinks` before it checks anything
# else, so a broken link is not warned about (filegenerator.py:296-311). Its
# root is checked too, without the separator a directory's path ends in, so
# a root that is a link to a directory names nothing, and so does a single
# upload of a link. A link above the root is followed.
#
# A download is skipped, silently and before `--no-overwrite`, when its
# destination is a link or goes through one, starting at the destination the
# command names; a parent reference below it is never followed either
# (s3handler.py:482-546). Links above the destination are followed.

BUCKET: Final = "bucket"
# A segment of the progress line the default printer redraws.
PROGRESS_SEGMENT: Final = re.compile(r"Completed .* file\(s\) remaining.*")
REMOTE: Final = b"remote body"
TARGET: Final = b"target"


@dataclass(frozen=True)
class Command:
    name: str
    # What the command adds to name a recursive transfer.
    recursive: tuple[str, ...]
    # The verb of each result line, by direction.
    upload: str
    download: str
    # Whether each transferred source is deleted.
    moves: bool


CP: Final = Command("cp", ("--recursive",), "upload", "download", False)
MV: Final = Command("mv", ("--recursive",), "move", "move", True)
SYNC: Final = Command("sync", (), "upload", "download", False)
RECURSIVE_COMMANDS: Final = [
    pytest.param(CP, id="cp"),
    pytest.param(MV, id="mv"),
    pytest.param(SYNC, id="sync"),
]
SINGLE_COMMANDS: Final = [
    pytest.param(CP, id="cp"),
    pytest.param(MV, id="mv"),
]
# Each spelling of the option, and whether it leaves links followed.
FLAGS: Final = [
    pytest.param((), True, id="default"),
    pytest.param(("--follow-symlinks",), True, id="follow"),
    pytest.param(("--no-follow-symlinks",), False, id="no-follow"),
]
# The options' shared destination takes the last one given.
ORDERED_FLAGS: Final = [
    *FLAGS,
    pytest.param(
        ("--no-follow-symlinks", "--follow-symlinks"), True, id="follow-last"
    ),
    pytest.param(
        ("--follow-symlinks", "--no-follow-symlinks"),
        False,
        id="no-follow-last",
    ),
]
EXPLICIT_FLAGS: Final = [
    pytest.param(("--follow-symlinks",), True, id="follow"),
    pytest.param(("--no-follow-symlinks",), False, id="no-follow"),
]


@dataclass(frozen=True)
class Run:
    returncode: int
    stdout: str
    stderr: str
    store: InMemoryS3

    def report(self) -> str:
        return (
            f"exit {self.returncode}\n"
            f"stdout: {self.stdout!r}\n"
            f"stderr: {self.stderr!r}\n"
            f"requests: {self.requests()}\n"
            f"failures: {self.store.failures}\n"
        )

    def requests(self) -> list[tuple[str, str]]:
        """Each request's operation and key, or a listing's prefix."""
        return [
            (
                request.operation_model.name,
                request.params.get("Key", request.params.get("Prefix", "")),
            )
            for request in self.store.received
        ]

    def keys(self, operation: str) -> list[str]:
        """The keys `operation` named, sorted: transfers run concurrently."""
        return sorted(key for name, key in self.requests() if name == operation)

    def stdout_lines(self) -> list[str]:
        return result_lines(self.stdout)

    def stderr_lines(self) -> list[str]:
        return result_lines(self.stderr)


def result_lines(stream: str) -> list[str]:
    """The result lines a stream holds, sorted, with the progress the
    default printer redraws, and the padding that overwrites it
    (results.py:563-568), stripped."""
    return sorted(
        segment.rstrip(" ")
        for segment in re.split(r"\r\n|\r|\n", stream)
        if segment.strip() and not PROGRESS_SEGMENT.fullmatch(segment)
    )


@pytest.fixture
def work(tmp_path: Path) -> Path:
    """The working directory every command runs in."""
    path = tmp_path / "work"
    path.mkdir()
    return path


async def run_s3(
    aws_cli: str, work: Path, store: InMemoryS3, *arguments: str
) -> Run:
    """Run `aws s3 <arguments>` once in `work` against `store`."""
    async with s3_runtime(store, work.parent) as (_, env):
        stdout, stderr, returncode = await run_command(
            [aws_cli, "s3", *arguments], env, cwd=work, stdin=None
        )
    return Run(
        returncode=returncode,
        stdout=decoded(without_cwd(stdout, work)),
        stderr=decoded(without_cwd(stderr, work)),
        store=store,
    )


def local(*parts: str) -> str:
    """A local path as upstream's relative_path shows it, with os.sep."""
    return os.path.join(*parts)


def upload_line(verb: str, source: str, name: str) -> str:
    shown = local(*source.split("/"), *name.split("/"))
    return f"{verb}: {shown} to s3://{BUCKET}/up/{name}"


def download_line(verb: str, name: str, destination: str = "dest") -> str:
    shown = local(*destination.split("/"), *name.split("/"))
    return f"{verb}: s3://{BUCKET}/tree/{name} to {shown}"


def objects(prefix: str, files: Mapping[str, bytes]) -> dict[ObjectKey, bytes]:
    return {(BUCKET, prefix + name): body for name, body in files.items()}


def entries(root: Path) -> list[Path]:
    """Every entry below `root`, never reached through a link."""
    return [
        Path(directory, name)
        for directory, directories, names in os.walk(root)
        for name in directories + names
    ]


def files(root: Path) -> dict[str, bytes]:
    """Each regular file below `root`, by its relative path, with its body."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in entries(root)
        if path.is_file() and not path.is_symlink()
    }


def links(root: Path) -> dict[str, str]:
    """Each link below `root`, by its relative path, with its target."""
    return {
        path.relative_to(root).as_posix(): os.readlink(path)
        for path in entries(root)
        if path.is_symlink()
    }


def recursive_arguments(
    command: Command, source: str, destination: str, flags: tuple[str, ...]
) -> list[str]:
    return [
        command.name,
        source,
        destination,
        *command.recursive,
        "--no-progress",
        *flags,
    ]


# The files a recursive upload's source holds outside its links, and those
# its links reach: a file and a directory outside the source, and nothing.
SOURCE_FILES: Final = {"real.txt": b"real", "sub/deep.txt": b"deep"}
LINKED_FILES: Final = {"file-link": TARGET, "dir-link/inner.txt": b"inner"}
SOURCE_LINKS: Final = {
    "broken": "missing",
    "dir-link": "../outside/dir",
    "file-link": "../outside/target.txt",
}
OUTSIDE: Final = {"dir/inner.txt": b"inner", "target.txt": TARGET}


def write_linked_source(work: Path) -> None:
    write_tree(work / "src", SOURCE_FILES)
    write_tree(work / "outside", OUTSIDE)
    for name, target in SOURCE_LINKS.items():
        (work / "src" / name).symlink_to(target)


@pytest.mark.parametrize(("flags", "follows"), ORDERED_FLAGS)
@pytest.mark.parametrize("command", RECURSIVE_COMMANDS)
async def test_recursive_upload_follows_links_unless_told_not_to(
    aws_cli: str,
    work: Path,
    command: Command,
    flags: tuple[str, ...],
    follows: bool,
) -> None:
    # Followed, the walk uploads each link's target under the link's name
    # and warns about the broken link; otherwise it drops every link.
    write_linked_source(work)
    store = InMemoryS3()
    run = await run_s3(
        aws_cli,
        work,
        store,
        *recursive_arguments(command, "src", f"s3://{BUCKET}/up/", flags),
    )
    report = run.report()
    uploaded = {**SOURCE_FILES, **(LINKED_FILES if follows else {})}
    assert store.failures == [], report
    assert store.objects == objects("up/", uploaded), report
    broken = local("<cwd>", "src", "broken")
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        2 if follows else 0,
        sorted(upload_line(command.upload, "src", name) for name in uploaded),
        (
            [f"warning: Skipping file {broken}. File does not exist."]
            if follows
            else []
        ),
    ), report
    # A move removes each link it uploaded, and each file it walked to
    # through one; a link it never walked stays, as does its target.
    if not command.moves:
        moved: dict[str, bytes] = {}
    elif follows:
        moved = uploaded
    else:
        moved = SOURCE_FILES
    assert files(work / "src") == {
        name: body for name, body in SOURCE_FILES.items() if name not in moved
    }, report
    assert links(work / "src") == {
        name: target
        for name, target in SOURCE_LINKS.items()
        if name != "file-link" or "file-link" not in moved
    }, report
    assert files(work / "outside") == {
        name: body
        for name, body in OUTSIDE.items()
        if name != "dir/inner.txt" or "dir-link/inner.txt" not in moved
    }, report


ROOT_FILES: Final = {"a.txt": b"a", "sub/b.txt": b"b"}


@pytest.mark.parametrize(
    ("source", "linked"),
    [
        pytest.param("src", True, id="link"),
        pytest.param("src/", True, id="link-with-separator"),
        pytest.param("lnk/src", False, id="link-above"),
    ],
)
@pytest.mark.parametrize(("flags", "follows"), FLAGS)
@pytest.mark.parametrize("command", RECURSIVE_COMMANDS)
async def test_recursive_upload_from_a_linked_root(
    aws_cli: str,
    work: Path,
    command: Command,
    flags: tuple[str, ...],
    follows: bool,
    source: str,
    linked: bool,
) -> None:
    # `src` links to `real`, and `lnk` to `parent`, which holds `src`.
    write_tree(work / "real", ROOT_FILES)
    write_tree(work / "parent" / "src", ROOT_FILES)
    (work / "src").symlink_to("real")
    (work / "lnk").symlink_to("parent")
    store = InMemoryS3()
    run = await run_s3(
        aws_cli,
        work,
        store,
        *recursive_arguments(
            command, source.replace("/", os.sep), f"s3://{BUCKET}/up/", flags
        ),
    )
    report = run.report()
    uploaded = ROOT_FILES if follows or not linked else {}
    shown = source.rstrip("/")
    assert store.failures == [], report
    assert store.objects == objects("up/", uploaded), report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        sorted(upload_line(command.upload, shown, name) for name in uploaded),
        "",
    ), report
    reached = work / ("real" if linked else "parent/src")
    remaining = {} if command.moves and uploaded else ROOT_FILES
    assert files(reached) == remaining, report
    assert links(work) == {"lnk": "parent", "src": "real"}, report


@pytest.mark.parametrize(
    ("source", "linked"),
    [
        pytest.param("link.txt", True, id="link"),
        pytest.param("dlink/inner.txt", False, id="link-above"),
    ],
)
@pytest.mark.parametrize(("flags", "follows"), FLAGS)
@pytest.mark.parametrize("command", SINGLE_COMMANDS)
async def test_single_upload_of_a_link(
    aws_cli: str,
    work: Path,
    command: Command,
    flags: tuple[str, ...],
    follows: bool,
    source: str,
    linked: bool,
) -> None:
    # `link.txt` links to `target.txt`, and `dlink` to `dir`.
    write_tree(work, {"target.txt": TARGET, "dir/inner.txt": TARGET})
    (work / "link.txt").symlink_to("target.txt")
    (work / "dlink").symlink_to("dir")
    store = InMemoryS3()
    run = await run_s3(
        aws_cli,
        work,
        store,
        command.name,
        source.replace("/", os.sep),
        f"s3://{BUCKET}/key.txt",
        "--no-progress",
        *flags,
    )
    report = run.report()
    uploads = follows or not linked
    shown = local(".", "link.txt") if linked else local("dlink", "inner.txt")
    assert store.failures == [], report
    assert store.objects == (
        {(BUCKET, "key.txt"): TARGET} if uploads else {}
    ), report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        (
            [f"{command.upload}: {shown} to s3://{BUCKET}/key.txt"]
            if uploads
            else []
        ),
        "",
    ), report
    # A move removes the link it uploaded, never its target.
    moved = command.moves and uploads
    expected_tree = {"target.txt": TARGET, "dir/inner.txt": TARGET}
    if moved and not linked:
        del expected_tree["dir/inner.txt"]
    assert files(work) == expected_tree, report
    expected_links = {"dlink": "dir", "link.txt": "target.txt"}
    if moved and linked:
        del expected_links["link.txt"]
    assert links(work) == expected_links, report


@pytest.mark.parametrize("command", SINGLE_COMMANDS)
async def test_single_upload_of_a_directory_link_without_following_it(
    aws_cli: str, work: Path, command: Command
) -> None:
    # Followed, the directory is queued as a file and its upload fails; not
    # followed, it is dropped like any other link.
    write_tree(work, {"dir/inner.txt": TARGET})
    (work / "dlink").symlink_to("dir")
    store = InMemoryS3()
    run = await run_s3(
        aws_cli,
        work,
        store,
        command.name,
        "dlink",
        f"s3://{BUCKET}/key.txt",
        "--no-follow-symlinks",
    )
    report = run.report()
    assert (run.returncode, run.stdout, run.stderr) == (0, "", ""), report
    assert run.requests() == [], report
    assert files(work) == {"dir/inner.txt": TARGET}, report
    assert links(work) == {"dlink": "dir"}, report


@dataclass(frozen=True)
class Destination:
    # The destination operand, with "/" for the separator.
    operand: str
    # How the result line shows it.
    shown: str
    # Where the body lands once links are followed, below the working
    # directory.
    written: str
    # Whether the destination is a link or lies below one, so that
    # `--no-follow-symlinks` skips the download.
    linked: bool


SINGLE_DESTINATIONS: Final = [
    pytest.param(
        Destination("link.txt", "./link.txt", "link.txt", True), id="link"
    ),
    pytest.param(
        Destination("dlink", "dlink/key.txt", "dir/key.txt", True),
        id="directory-link",
    ),
    pytest.param(
        Destination("dlink/", "dlink/key.txt", "dir/key.txt", True),
        id="directory-link-with-separator",
    ),
    pytest.param(
        Destination("dlink/new.txt", "dlink/new.txt", "dir/new.txt", False),
        id="link-above",
    ),
]


@pytest.mark.parametrize("destination", SINGLE_DESTINATIONS)
@pytest.mark.parametrize(("flags", "follows"), EXPLICIT_FLAGS)
@pytest.mark.parametrize("command", SINGLE_COMMANDS)
async def test_single_download_onto_or_through_a_link(
    aws_cli: str,
    work: Path,
    command: Command,
    flags: tuple[str, ...],
    follows: bool,
    destination: Destination,
) -> None:
    # `link.txt` links to `target.txt`, and `dlink` to `dir`. A download
    # onto a link replaces the link, and leaves its target alone.
    write_tree(work, {"target.txt": TARGET, "dir/kept.txt": b"kept"})
    (work / "link.txt").symlink_to("target.txt")
    (work / "dlink").symlink_to("dir")
    seed = {(BUCKET, "key.txt"): REMOTE}
    store = InMemoryS3(seed)
    run = await run_s3(
        aws_cli,
        work,
        store,
        command.name,
        f"s3://{BUCKET}/key.txt",
        destination.operand.replace("/", os.sep),
        "--no-progress",
        *flags,
    )
    report = run.report()
    downloads = follows or not destination.linked
    assert store.failures == [], report
    assert run.keys("HeadObject") == ["key.txt"], report
    assert run.keys("GetObject") == (["key.txt"] if downloads else []), report
    shown = local(*destination.shown.split("/"))
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        (
            [f"{command.download}: s3://{BUCKET}/key.txt to {shown}"]
            if downloads
            else []
        ),
        "",
    ), report
    expected_tree = {"target.txt": TARGET, "dir/kept.txt": b"kept"}
    expected_links = {"dlink": "dir", "link.txt": "target.txt"}
    if downloads:
        expected_tree[destination.written] = REMOTE
        expected_links.pop(destination.written, None)
    assert files(work) == expected_tree, report
    assert links(work) == expected_links, report
    assert store.objects == ({} if command.moves and downloads else seed), report


# The objects a recursive download's source holds: one whose destination is
# plain, one below a link to a directory, and one onto a link to a file.
TREE: Final = {"a.txt": b"a", "sub/b.txt": b"b", "link.txt": REMOTE}
DESTINATION_LINKS: Final = {"link.txt": "../target.txt", "sub": "../outside"}


@pytest.mark.parametrize(("flags", "follows"), FLAGS)
@pytest.mark.parametrize("command", RECURSIVE_COMMANDS)
async def test_recursive_download_through_links_unless_told_not_to(
    aws_cli: str,
    work: Path,
    command: Command,
    flags: tuple[str, ...],
    follows: bool,
) -> None:
    # A sync downloads `link.txt` too when followed: the file its walk finds
    # there differs in size.
    (work / "dest").mkdir()
    (work / "outside").mkdir()
    (work / "target.txt").write_bytes(TARGET)
    for name, target in DESTINATION_LINKS.items():
        (work / "dest" / name).symlink_to(target)
    seed = objects("tree/", TREE)
    store = InMemoryS3(seed)
    run = await run_s3(
        aws_cli,
        work,
        store,
        *recursive_arguments(command, f"s3://{BUCKET}/tree/", "dest", flags),
    )
    report = run.report()
    downloaded = sorted(TREE) if follows else ["a.txt"]
    assert store.failures == [], report
    assert run.keys("GetObject") == [f"tree/{n}" for n in downloaded], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        sorted(download_line(command.download, n) for n in downloaded),
        "",
    ), report
    if follows:
        # The link to a file is replaced; the one to a directory is written
        # through.
        assert files(work) == {
            "dest/a.txt": b"a",
            "dest/link.txt": REMOTE,
            "outside/b.txt": b"b",
            "target.txt": TARGET,
        }, report
        assert links(work) == {"dest/sub": "../outside"}, report
    else:
        assert files(work) == {
            "dest/a.txt": b"a",
            "target.txt": TARGET,
        }, report
        assert links(work) == {
            f"dest/{name}": target for name, target in DESTINATION_LINKS.items()
        }, report
    moved = {f"tree/{name}" for name in downloaded} if command.moves else set()
    assert store.objects == {
        key: body for key, body in seed.items() if key[1] not in moved
    }, report


@pytest.mark.parametrize(
    "key",
    [
        pytest.param("sub/../c.txt", id="after-link"),
        pytest.param("missing/../sub/c.txt", id="before-link"),
        pytest.param("plain/../c.txt", id="no-link"),
    ],
)
@pytest.mark.parametrize("command", RECURSIVE_COMMANDS)
async def test_recursive_download_never_follows_a_parent_reference(
    aws_cli: str, work: Path, command: Command, key: str
) -> None:
    # A link check cannot resolve a path through a directory the download
    # has yet to create, so any `..` below the destination ends it.
    (work / "dest" / "plain").mkdir(parents=True)
    (work / "outside").mkdir()
    (work / "dest" / "sub").symlink_to("../outside")
    seed = objects("tree/", {"a.txt": b"a", key: REMOTE})
    store = InMemoryS3(seed)
    run = await run_s3(
        aws_cli,
        work,
        store,
        *recursive_arguments(
            command,
            f"s3://{BUCKET}/tree/",
            "dest",
            ("--no-follow-symlinks",),
        ),
    )
    report = run.report()
    assert store.failures == [], report
    assert run.keys("GetObject") == ["tree/a.txt"], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        [download_line(command.download, "a.txt")],
        "",
    ), report
    assert files(work) == {"dest/a.txt": b"a"}, report
    assert links(work) == {"dest/sub": "../outside"}, report
    moved = {(BUCKET, "tree/a.txt")} if command.moves else set()
    assert store.objects == {
        k: body for k, body in seed.items() if k not in moved
    }, report


@pytest.mark.parametrize(
    "destination",
    [
        pytest.param("dest-link", id="link"),
        pytest.param("dest-link/", id="link-with-separator"),
    ],
)
@pytest.mark.parametrize(("flags", "follows"), EXPLICIT_FLAGS)
@pytest.mark.parametrize("command", RECURSIVE_COMMANDS)
async def test_recursive_download_into_a_linked_root(
    aws_cli: str,
    work: Path,
    command: Command,
    flags: tuple[str, ...],
    follows: bool,
    destination: str,
) -> None:
    (work / "dest").mkdir()
    (work / "dest-link").symlink_to("dest")
    tree = {"a.txt": b"a", "sub/b.txt": b"b"}
    seed = objects("tree/", tree)
    store = InMemoryS3(seed)
    run = await run_s3(
        aws_cli,
        work,
        store,
        *recursive_arguments(
            command,
            f"s3://{BUCKET}/tree/",
            destination.replace("/", os.sep),
            flags,
        ),
    )
    report = run.report()
    downloaded = sorted(tree) if follows else []
    assert store.failures == [], report
    assert run.keys("GetObject") == [f"tree/{n}" for n in downloaded], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        sorted(
            download_line(command.download, n, "dest-link") for n in downloaded
        ),
        "",
    ), report
    assert files(work / "dest") == (tree if follows else {}), report
    assert links(work) == {"dest-link": "dest"}, report
    expected = {} if command.moves and follows else seed
    assert store.objects == expected, report


@pytest.mark.parametrize(("flags", "follows"), EXPLICIT_FLAGS)
async def test_sync_download_delete_removes_links_only_when_followed(
    aws_cli: str, work: Path, flags: tuple[str, ...], follows: bool
) -> None:
    # Followed, the walk lists a link to a file, which the delete removes,
    # and the files below a link to a directory, which it removes through
    # the link; not followed, it lists neither.
    write_tree(work, {"dest/only.txt": b"only", **OUTSIDE})
    (work / "dest" / "dir-link").symlink_to("../dir")
    (work / "dest" / "file-link").symlink_to("../target.txt")
    seed = objects("tree/", {"kept.txt": b"kept"})
    store = InMemoryS3(seed)
    run = await run_s3(
        aws_cli,
        work,
        store,
        "sync",
        f"s3://{BUCKET}/tree/",
        "dest",
        "--delete",
        "--no-progress",
        *flags,
    )
    report = run.report()
    deleted = ["dir-link/inner.txt", "file-link", "only.txt"]
    if not follows:
        deleted = ["only.txt"]
    assert store.failures == [], report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        sorted(
            [download_line("download", "kept.txt")]
            + [f"delete: {local('dest', *n.split('/'))}" for n in deleted]
        ),
        "",
    ), report
    expected_tree = {
        "dest/kept.txt": b"kept",
        **({} if follows else {"dir/inner.txt": b"inner"}),
        "target.txt": TARGET,
    }
    assert files(work) == expected_tree, report
    assert links(work) == {
        "dest/dir-link": "../dir",
        **({} if follows else {"dest/file-link": "../target.txt"}),
    }, report
    assert store.objects == seed, report


@pytest.mark.parametrize(("flags", "follows"), EXPLICIT_FLAGS)
async def test_sync_upload_delete_removes_objects_named_by_unfollowed_links(
    aws_cli: str, work: Path, flags: tuple[str, ...], follows: bool
) -> None:
    # Not followed, a link is no source at all, so the object of its name is
    # one only the destination holds, which the delete removes.
    write_linked_source(work)
    (work / "src" / "broken").unlink()
    seed = objects("up/", {"file-link": b"old", "dir-link/inner.txt": b"old"})
    store = InMemoryS3(seed)
    run = await run_s3(
        aws_cli,
        work,
        store,
        "sync",
        "src",
        f"s3://{BUCKET}/up/",
        "--delete",
        "--no-progress",
        *flags,
    )
    report = run.report()
    uploaded = {**SOURCE_FILES, **(LINKED_FILES if follows else {})}
    deleted = [] if follows else sorted(key for _, key in seed)
    assert store.failures == [], report
    assert run.keys("DeleteObject") == deleted, report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        sorted(
            [upload_line("upload", "src", name) for name in uploaded]
            + [f"delete: s3://{BUCKET}/{key}" for key in deleted]
        ),
        "",
    ), report
    assert store.objects == objects("up/", uploaded), report


@pytest.mark.parametrize(("flags", "follows"), EXPLICIT_FLAGS)
async def test_dryrun_reports_only_what_the_links_allow(
    aws_cli: str, work: Path, flags: tuple[str, ...], follows: bool
) -> None:
    # A dry run reports what its transfer would do, so a download the links
    # rule out is not reported either.
    write_linked_source(work)
    (work / "dest").mkdir()
    (work / "target.txt").write_bytes(TARGET)
    (work / "dest" / "link.txt").symlink_to("../target.txt")
    store = InMemoryS3(objects("tree/", {"a.txt": b"a", "link.txt": REMOTE}))
    upload = await run_s3(
        aws_cli,
        work,
        InMemoryS3(),
        *recursive_arguments(
            CP, "src", f"s3://{BUCKET}/up/", ("--dryrun", *flags)
        ),
    )
    download = await run_s3(
        aws_cli,
        work,
        store,
        *recursive_arguments(
            CP, f"s3://{BUCKET}/tree/", "dest", ("--dryrun", *flags)
        ),
    )
    report = upload.report() + download.report()
    uploaded = {**SOURCE_FILES, **(LINKED_FILES if follows else {})}
    downloaded = ["a.txt", "link.txt"] if follows else ["a.txt"]
    assert upload.returncode == (2 if follows else 0), report
    assert upload.stdout_lines() == sorted(
        f"(dryrun) {upload_line('upload', 'src', name)}" for name in uploaded
    ), report
    assert download.stdout_lines() == sorted(
        f"(dryrun) {download_line('download', name)}" for name in downloaded
    ), report
    assert (download.returncode, download.stderr) == (0, ""), report
    assert store.failures == [], report
    assert [name for name, _ in download.requests()] == [
        "ListObjectsV2"
    ], report
    assert links(work / "dest") == {"link.txt": "../target.txt"}, report
