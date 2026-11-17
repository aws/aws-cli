"""What `s3 rm` deletes, what it prints, and the requests it sends.

Most tests run one command against the in-memory bucket of s3store.py and
assert the result lines, the exit status, the objects left in the bucket,
and the operations sent. `s3 rm` has no progress options, so upstream's
handler gives it the printer that draws no progress (s3handler.py:120-134)
and its stdout is exactly its result lines. A recursive delete sends its
deletes concurrently, so their lines are compared sorted.

`s3 rm` lists with botocore and deletes through the transfer manager
`s3 cp` builds (subcommands.py:1069-1090), which these tests' environment
resolves to the CRT client.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from urllib.parse import unquote, urlsplit

import awscrt.s3
import pytest
from localstub import AsyncHTTPTestServer, HTTPResponse

from awswire import ReconstructedRequest
from credhelpers import run_command
from s3helpers import CRT_SUFFIX, completion_lines, user_agent_parts
from s3store import (
    LAST_MODIFIED,
    REQUEST_IDS,
    InMemoryS3,
    ObjectKey,
    ScriptedS3,
    decoded,
    pattern_bytes,
    s3_runtime,
)
from tests.blackbox.utils import (
    list_objects_xml,
    run_cli,
    xml_response,
)


def delete_object_response() -> HTTPResponse:
    """S3's DeleteObject answer: 204 with its request ids.

    The CRT client records a response's status with its headers, so it
    rejects a 204 that has none.
    """
    return HTTPResponse.raw(
        b"",
        status=204,
        headers={"x-amz-request-id": "REQUESTID", "x-amz-id-2": "HOSTID"},
    )


@pytest.mark.asyncio
async def test_rm_recursive_filters_delete_only_selected_objects(
    aws_cli: str,
    transfer_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    filter_case: tuple[list[str], list[str]],
) -> None:
    server, env = transfer_runtime
    names = ["a.txt", "ignored.bin", "nested/b.txt", "nested/c.bin"]
    server.set_response_sequence(
        [
            xml_response(
                list_objects_xml(
                    [
                        {
                            "Key": f"prefix/{name}",
                            "Size": 3,
                            "LastModified": "2026-01-01T00:00:00Z",
                        }
                        for name in names
                    ]
                )
            )
        ]
    )
    server.handler = lambda context: delete_object_response()
    flags, selected = filter_case
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "rm",
            "s3://bucket/prefix/",
            "--recursive",
            *flags,
        ],
        env,
    )
    assert (rc, stderr) == (0, b"")
    assert server.requests[0].method == "GET"
    assert sorted(
        (r.method, unquote(urlsplit(r.effective_path).path))
        for r in server.requests[1:]
    ) == [("DELETE", f"/prefix/{name}") for name in selected]
    assert sorted(completion_lines(stdout)) == [
        f"delete: s3://bucket/prefix/{name}" for name in selected
    ]


BUCKET: Final = "bucket"
# Every DeleteObject in this bucket is refused with AccessDenied.
DENIED_BUCKET: Final = "denied-bucket"
# The objects under "tree/", the folder marker of the prefix itself and of
# a subfolder included: zero-size keys ending in "/", as the S3 console
# creates them.
TREE: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, "tree/"): b"",
    (BUCKET, "tree/a.txt"): pattern_bytes("tree a", 100),
    (BUCKET, "tree/b.txt"): pattern_bytes("tree b", 1500),
    (BUCKET, "tree/folder/"): b"",
    (BUCKET, "tree/nested/c.txt"): pattern_bytes("tree c", 700),
}
# Keys a delete of "tree/" leaves alone, one sharing its first characters.
OUTSIDE: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, "treehouse.txt"): pattern_bytes("treehouse", 10),
    (BUCKET, "other/d.txt"): pattern_bytes("other d", 20),
}
SEED_OBJECTS: Final = {**TREE, **OUTSIDE}
DENIED_OBJECTS: Final[dict[ObjectKey, bytes]] = {
    (DENIED_BUCKET, key): body for (_, key), body in TREE.items()
}
ACCESS_DENIED: Final = (
    "An error occurred (AccessDenied) when calling the {operation} "
    "operation: Access Denied"
)
CRT_CONFIG: Final = "[default]\ns3 =\n  preferred_transfer_client = crt\n"
# More failures than any case allows attempts, so every attempt fails.
EXHAUSTING: Final = 1000
# The attempts a delete makes when nothing sets max_attempts: botocore's 3
# where the AWS CLI gives the CRT client the classic client's defaults,
# else the CRT's own first attempt and 5 retries
# (customizations/s3/factory.py:253-259, 431-435).
DEFAULT_DELETE_ATTEMPTS: Final = (
    6 if awscrt.s3.is_optimized_for_system() else 3
)


@dataclass(frozen=True)
class OutputMode:
    name: str
    flags: tuple[str, ...]
    # --only-show-errors drops successes and --quiet installs no printer
    # at all (s3handler.py:120-134).
    shows_successes: bool = True
    shows_errors: bool = True


DEFAULT: Final = OutputMode("default", ())
ONLY_SHOW_ERRORS: Final = OutputMode(
    "only-show-errors", ("--only-show-errors",), shows_successes=False
)
QUIET: Final = OutputMode(
    "quiet", ("--quiet",), shows_successes=False, shows_errors=False
)
MODES: Final = [
    pytest.param(mode, id=mode.name)
    for mode in (DEFAULT, ONLY_SHOW_ERRORS, QUIET)
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
            f"responses: {self.store.responses}\n"
            f"failures: {self.store.failures}\n"
        )

    def requests(self) -> list[tuple[str, str]]:
        """Each request's operation and key, or a listing's prefix, in
        arrival order."""
        return [
            (
                request.operation_model.name,
                request.params.get("Key", request.params.get("Prefix", "")),
            )
            for request in self.store.received
        ]

    def deletes(self) -> list[str]:
        """The keys deleted, sorted: deletes run concurrently."""
        return sorted(
            key
            for operation, key in self.requests()
            if operation == "DeleteObject"
        )

    def stdout_lines(self) -> list[str]:
        return sorted(self.stdout.splitlines())

    def stderr_lines(self) -> list[str]:
        return sorted(self.stderr.splitlines())


async def run_rm(
    aws_cli: str,
    tmp_path: Path,
    store: InMemoryS3,
    *arguments: str,
    config: str = "",
    environment: Mapping[str, str] | None = None,
) -> Run:
    """Run `aws s3 rm <arguments>` once in tmp_path/work against `store`."""
    work = tmp_path / "work"
    work.mkdir()
    async with s3_runtime(store, tmp_path) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(config, encoding="utf-8")
        env.update(environment or {})
        stdout, stderr, returncode = await run_command(
            [aws_cli, "s3", "rm", *arguments], env, cwd=work, stdin=None
        )
    return Run(
        returncode=returncode,
        stdout=decoded(stdout),
        stderr=decoded(stderr),
        store=store,
    )


def without(
    objects: Mapping[ObjectKey, bytes], *keys: str
) -> dict[ObjectKey, bytes]:
    return {
        (bucket, key): body
        for (bucket, key), body in objects.items()
        if key not in keys
    }


def tree_keys() -> list[str]:
    return sorted(key for _, key in TREE)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    ("key", "deleted"),
    [
        pytest.param("tree/a.txt", True, id="object"),
        # S3 answers 204 for a key it does not hold.
        pytest.param("tree/missing.txt", False, id="missing"),
        # A key ending in "/" names one object without --recursive.
        pytest.param("tree/folder/", True, id="folder-marker"),
        # A prefix that is no key names one object too: nothing is listed.
        pytest.param("tree", False, id="prefix"),
    ],
)
async def test_rm_single_object_sends_one_delete(
    aws_cli: str, tmp_path: Path, mode: OutputMode, key: str, deleted: bool
) -> None:
    run = await run_rm(
        aws_cli,
        tmp_path,
        InMemoryS3(SEED_OBJECTS),
        f"s3://{BUCKET}/{key}",
        *mode.flags,
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.requests() == [("DeleteObject", key)], report
    expected = f"delete: s3://{BUCKET}/{key}\n"
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        expected if mode.shows_successes else "",
        "",
    ), report
    remaining = without(SEED_OBJECTS, key) if deleted else SEED_OBJECTS
    assert run.store.objects == remaining, report


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "target",
    [
        pytest.param("tree", id="prefix"),
        pytest.param("tree/", id="trailing-slash"),
    ],
)
async def test_rm_recursive_deletes_every_object_under_the_prefix(
    aws_cli: str, tmp_path: Path, mode: OutputMode, target: str
) -> None:
    # The prefix is listed as a directory: "tree" lists "tree/", so
    # "treehouse.txt" stays.
    run = await run_rm(
        aws_cli,
        tmp_path,
        InMemoryS3(SEED_OBJECTS),
        f"s3://{BUCKET}/{target}",
        "--recursive",
        *mode.flags,
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.requests()[0] == ("ListObjectsV2", "tree/"), report
    assert run.deletes() == tree_keys(), report
    expected = (
        [f"delete: s3://{BUCKET}/{key}" for key in tree_keys()]
        if mode.shows_successes
        else []
    )
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        expected,
        "",
    ), report
    assert run.store.objects == OUTSIDE, report


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "target",
    [
        pytest.param(f"s3://{BUCKET}", id="bucket"),
        pytest.param(f"s3://{BUCKET}/", id="trailing-slash"),
    ],
)
async def test_rm_recursive_bucket_deletes_every_object(
    aws_cli: str, tmp_path: Path, target: str
) -> None:
    run = await run_rm(
        aws_cli,
        tmp_path,
        InMemoryS3(SEED_OBJECTS),
        target,
        "--recursive",
    )
    report = run.report()
    keys = sorted(key for _, key in SEED_OBJECTS)
    assert run.store.failures == [], report
    assert run.requests()[0] == ("ListObjectsV2", ""), report
    assert run.deletes() == keys, report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        [f"delete: s3://{BUCKET}/{key}" for key in keys],
        "",
    ), report
    assert run.store.objects == {}, report


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "target",
    [
        pytest.param(f"s3://{BUCKET}", id="bucket"),
        pytest.param(f"s3://{BUCKET}/", id="trailing-slash"),
    ],
)
async def test_rm_bucket_without_recursive_deletes_only_folder_markers(
    aws_cli: str, tmp_path: Path, target: str
) -> None:
    """A bucket names no key, so upstream lists the whole bucket, and its
    file generator still yields every folder marker for a delete
    (filegenerator.py:344-379): a zero-size key ending in "/". A zero-size
    key without the slash, and a sized one with it, stay."""
    objects = {
        **SEED_OBJECTS,
        (BUCKET, "empty.txt"): b"",
        (BUCKET, "sized/"): b"not a marker",
    }
    run = await run_rm(aws_cli, tmp_path, InMemoryS3(objects), target)
    report = run.report()
    markers = ["tree/", "tree/folder/"]
    assert run.store.failures == [], report
    assert run.requests()[0] == ("ListObjectsV2", ""), report
    assert run.deletes() == markers, report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        [f"delete: s3://{BUCKET}/{key}" for key in markers],
        "",
    ), report
    assert run.store.objects == without(objects, *markers), report


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    ("arguments", "keys", "listed"),
    [
        pytest.param(
            (f"s3://{BUCKET}/tree/a.txt",), ["tree/a.txt"], False, id="object"
        ),
        pytest.param(
            (f"s3://{BUCKET}/tree/", "--recursive"),
            tree_keys(),
            True,
            id="recursive",
        ),
    ],
)
async def test_rm_dryrun_reports_deletes_and_sends_none(
    aws_cli: str,
    tmp_path: Path,
    mode: OutputMode,
    arguments: tuple[str, ...],
    keys: list[str],
    listed: bool,
) -> None:
    """A dry run still lists. --only-show-errors drops successes, not dry
    run lines (results.py:551-560)."""
    run = await run_rm(
        aws_cli,
        tmp_path,
        InMemoryS3(SEED_OBJECTS),
        *arguments,
        "--dryrun",
        *mode.flags,
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.requests() == (
        [("ListObjectsV2", "tree/")] if listed else []
    ), report
    expected = (
        [f"(dryrun) delete: s3://{BUCKET}/{key}" for key in keys]
        if mode.shows_errors
        else []
    )
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        expected,
        "",
    ), report
    assert run.store.objects == SEED_OBJECTS, report


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    ("arguments", "keys"),
    [
        pytest.param(
            (f"s3://{DENIED_BUCKET}/tree/a.txt",), ["tree/a.txt"], id="object"
        ),
        pytest.param(
            (f"s3://{DENIED_BUCKET}/tree/", "--recursive"),
            tree_keys(),
            id="recursive",
        ),
    ],
)
async def test_rm_refused_delete_fails_the_command(
    aws_cli: str,
    tmp_path: Path,
    mode: OutputMode,
    arguments: tuple[str, ...],
    keys: list[str],
) -> None:
    store = InMemoryS3(
        DENIED_OBJECTS, denied_buckets=frozenset({DENIED_BUCKET})
    )
    run = await run_rm(aws_cli, tmp_path, store, *arguments, *mode.flags)
    report = run.report()
    error = ACCESS_DENIED.format(operation="DeleteObject")
    expected = (
        [f"delete failed: s3://{DENIED_BUCKET}/{key} {error}" for key in keys]
        if mode.shows_errors
        else []
    )
    assert store.failures == [], report
    assert run.deletes() == keys, report
    assert (run.returncode, run.stdout, run.stderr_lines()) == (
        1,
        "",
        expected,
    ), report
    assert store.objects == DENIED_OBJECTS, report


class LockedKeysS3(InMemoryS3):
    """Refuses every DeleteObject of a key with "locked" in its name, and
    every ListObjectsV2 of a prefix with "locked" in it, with AccessDenied."""

    def dispatch(self, reconstructed: ReconstructedRequest) -> HTTPResponse:
        name = reconstructed.operation_model.name
        params = reconstructed.params
        locked = (name == "DeleteObject" and "locked" in params["Key"]) or (
            name == "ListObjectsV2" and "locked" in params.get("Prefix", "")
        )
        if locked:
            return self.error(
                reconstructed, "AccessDenied", "Access Denied", 403
            )
        return super().dispatch(reconstructed)


@pytest.mark.asyncio
async def test_rm_recursive_reports_each_refused_delete_and_deletes_the_rest(
    aws_cli: str, tmp_path: Path
) -> None:
    objects = {
        **SEED_OBJECTS,
        (BUCKET, "tree/locked.txt"): pattern_bytes("locked", 30),
        (BUCKET, "tree/nested/locked/x.txt"): pattern_bytes("x", 40),
    }
    store = LockedKeysS3(objects)
    run = await run_rm(
        aws_cli, tmp_path, store, f"s3://{BUCKET}/tree", "--recursive"
    )
    report = run.report()
    locked = ["tree/locked.txt", "tree/nested/locked/x.txt"]
    error = ACCESS_DENIED.format(operation="DeleteObject")
    assert store.failures == [], report
    assert run.deletes() == sorted([*tree_keys(), *locked]), report
    assert (run.returncode, run.stdout_lines(), run.stderr_lines()) == (
        1,
        [f"delete: s3://{BUCKET}/{key}" for key in tree_keys()],
        [f"delete failed: s3://{BUCKET}/{key} {error}" for key in locked],
    ), report
    assert store.objects == {
        **OUTSIDE,
        **{(BUCKET, key): objects[(BUCKET, key)] for key in locked},
    }, report


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", MODES)
async def test_rm_recursive_refused_listing_is_fatal(
    aws_cli: str, tmp_path: Path, mode: OutputMode
) -> None:
    store = LockedKeysS3(SEED_OBJECTS)
    run = await run_rm(
        aws_cli,
        tmp_path,
        store,
        f"s3://{BUCKET}/locked/",
        "--recursive",
        *mode.flags,
    )
    report = run.report()
    error = ACCESS_DENIED.format(operation="ListObjectsV2")
    assert store.failures == [], report
    assert run.requests() == [("ListObjectsV2", "locked/")], report
    # The listing's error ends the command as its fatal error, which the
    # printer reports and --quiet does not (results.py:707-716).
    assert (run.returncode, run.stdout, run.stderr) == (
        1,
        "",
        f"fatal error: {error}\n" if mode.shows_errors else "",
    ), report
    assert store.objects == SEED_OBJECTS, report


SPECIAL_KEYS: Final = [
    "odd/a b+c.txt",
    "odd/café 日本.txt",
    "odd/q?x=1&y=2#z.txt",
    "odd/%41%2F.txt",
    "odd/tilde~star*paren().txt",
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "recursive", [False, True], ids=["object", "recursive"]
)
async def test_rm_deletes_keys_that_need_encoding(
    aws_cli: str, tmp_path: Path, recursive: bool
) -> None:
    objects = {(BUCKET, key): key.encode() for key in SPECIAL_KEYS}
    store = InMemoryS3({**objects, **OUTSIDE})
    if recursive:
        runs = [
            await run_rm(
                aws_cli, tmp_path, store, f"s3://{BUCKET}/odd/", "--recursive"
            )
        ]
    else:
        runs = []
        for index, key in enumerate(SPECIAL_KEYS):
            scratch = tmp_path / str(index)
            scratch.mkdir()
            runs.append(
                await run_rm(aws_cli, scratch, store, f"s3://{BUCKET}/{key}")
            )
    report = "".join(run.report() for run in runs)
    assert store.failures == [], report
    assert sorted(
        key
        for request in store.received
        if request.operation_model.name == "DeleteObject"
        for key in [request.params["Key"]]
    ) == sorted(SPECIAL_KEYS), report
    lines = sorted(line for run in runs for line in run.stdout_lines())
    assert lines == sorted(
        f"delete: s3://{BUCKET}/{key}" for key in SPECIAL_KEYS
    ), report
    statuses = [(run.returncode, run.stderr) for run in runs]
    assert statuses == [(0, "")] * len(runs), report
    assert store.objects == OUTSIDE, report


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "flags",
    [
        pytest.param(("--request-payer",), id="bare"),
        pytest.param(("--request-payer", "requester"), id="requester"),
    ],
)
@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param((f"s3://{BUCKET}/tree/a.txt",), id="object"),
        pytest.param((f"s3://{BUCKET}/tree/", "--recursive"), id="recursive"),
    ],
)
async def test_rm_request_payer_is_sent_with_every_request(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    flags: tuple[str, ...],
) -> None:
    run = await run_rm(
        aws_cli, tmp_path, InMemoryS3(SEED_OBJECTS), *arguments, *flags
    )
    report = run.report()
    assert run.store.failures == [], report
    assert run.returncode == 0, report
    assert run.store.received, report
    assert [
        request.params.get("RequestPayer") for request in run.store.received
    ] == ["requester"] * len(run.store.received), report


class PagedS3(InMemoryS3):
    """Lists MaxKeys keys a page; a page's token is the offset of the
    next. The pages are cut from the bucket as the first page found it, so
    a delete that lands between two pages shifts no offset."""

    def __init__(self, objects: Mapping[ObjectKey, bytes]) -> None:
        super().__init__(objects)
        self.listed: list[tuple[str, int]] = []

    def _list_objects_v2(
        self, reconstructed: ReconstructedRequest
    ) -> HTTPResponse:
        params = reconstructed.params
        prefix = params.get("Prefix", "")
        if "ContinuationToken" not in params:
            self.listed = sorted(
                (key, len(body))
                for (bucket, key), body in self.objects.items()
                if bucket == params["Bucket"] and key.startswith(prefix)
            )
        start = int(params.get("ContinuationToken", "0"))
        size = int(params.get("MaxKeys", 1000))
        page = self.listed[start : start + size]
        truncated = start + size < len(self.listed)
        parsed = {
            "Name": params["Bucket"],
            "Prefix": prefix,
            "KeyCount": len(page),
            "MaxKeys": size,
            "IsTruncated": truncated,
            "Contents": [
                {
                    "Key": key,
                    "Size": length,
                    "LastModified": LAST_MODIFIED,
                }
                for key, length in page
            ],
        }
        if truncated:
            parsed["NextContinuationToken"] = str(start + size)
        return self.serialize(reconstructed, parsed)


@pytest.mark.asyncio
async def test_rm_recursive_page_size_lists_in_pages(
    aws_cli: str, tmp_path: Path
) -> None:
    objects = {(BUCKET, f"many/{index:02}.txt"): b"x" for index in range(5)}
    store = PagedS3(objects)
    run = await run_rm(
        aws_cli,
        tmp_path,
        store,
        f"s3://{BUCKET}/many/",
        "--recursive",
        "--page-size",
        "2",
    )
    report = run.report()
    listings = [
        (
            request.params.get("MaxKeys"),
            request.params.get("ContinuationToken"),
        )
        for request in store.received
        if request.operation_model.name == "ListObjectsV2"
    ]
    keys = sorted(key for _, key in objects)
    assert store.failures == [], report
    assert listings == [(2, None), (2, "2"), (2, "4")], report
    assert run.deletes() == keys, report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        [f"delete: s3://{BUCKET}/{key}" for key in keys],
        "",
    ), report
    assert store.objects == {}, report


@pytest.mark.asyncio
async def test_rm_recursive_deletes_more_objects_than_fit_in_flight(
    aws_cli: str, tmp_path: Path
) -> None:
    objects = {
        (BUCKET, f"many/{index:03}.txt"): pattern_bytes(str(index), index)
        for index in range(150)
    }
    store = InMemoryS3({**objects, **OUTSIDE})
    run = await run_rm(
        aws_cli, tmp_path, store, f"s3://{BUCKET}/many", "--recursive"
    )
    report = run.report()
    keys = sorted(key for _, key in objects)
    assert store.failures == [], report
    assert run.deletes() == keys, report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        [f"delete: s3://{BUCKET}/{key}" for key in keys],
        "",
    ), report
    assert store.objects == OUTSIDE, report


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("arguments", "keys"),
    [
        # Without --recursive the patterns are rooted at the key's
        # directory (filters.py:56-68).
        pytest.param(
            (f"s3://{BUCKET}/tree/a.txt", "--exclude", "*"), [], id="excluded"
        ),
        pytest.param(
            (
                f"s3://{BUCKET}/tree/a.txt",
                "--exclude",
                "*",
                "--include",
                "a.txt",
            ),
            ["tree/a.txt"],
            id="included",
        ),
        pytest.param(
            (f"s3://{BUCKET}/tree/a.txt", "--exclude", "tree/a.txt"),
            ["tree/a.txt"],
            id="rooted-at-directory",
        ),
        # A recursive delete roots them at the prefix. "*/" matches the
        # subfolder's marker but not the prefix's own, "bucket/tree/".
        pytest.param(
            (
                f"s3://{BUCKET}/tree",
                "--recursive",
                "--exclude",
                "*/",
                "--exclude",
                "nested/*",
            ),
            ["tree/", "tree/a.txt", "tree/b.txt"],
            id="recursive",
        ),
    ],
)
async def test_rm_filters_select_what_is_deleted(
    aws_cli: str, tmp_path: Path, arguments: tuple[str, ...], keys: list[str]
) -> None:
    store = InMemoryS3(SEED_OBJECTS)
    run = await run_rm(aws_cli, tmp_path, store, *arguments)
    report = run.report()
    assert run.store.failures == [], report
    assert run.deletes() == keys, report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        [f"delete: s3://{BUCKET}/{key}" for key in keys],
        "",
    ), report
    assert run.store.objects == without(SEED_OBJECTS, *keys), report


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failures", "attempts", "returncode", "stdout", "stderr"),
    [
        pytest.param(
            1, 2, 0, f"delete: s3://{BUCKET}/tree/a.txt\n", "", id="once"
        ),
        # The CRT reports the 500 it stopped retrying as its own error, not
        # as an S3ResponseError the AWS CLI would translate
        # (s3transfer/crt.py:1023-1027).
        pytest.param(
            EXHAUSTING,
            DEFAULT_DELETE_ATTEMPTS,
            1,
            "",
            f"delete failed: s3://{BUCKET}/tree/a.txt "
            "AWS_ERROR_S3_INTERNAL_ERROR: Response code indicates internal "
            "server error\n",
            id="exhausted",
        ),
    ],
)
async def test_rm_retries_internal_errors(
    aws_cli: str,
    tmp_path: Path,
    failures: int,
    attempts: int,
    returncode: int,
    stdout: str,
    stderr: str,
) -> None:
    store = ScriptedS3(
        SEED_OBJECTS, failing=frozenset({"DeleteObject"}), failures=failures
    )
    run = await run_rm(
        aws_cli, tmp_path, store, f"s3://{BUCKET}/tree/a.txt"
    )
    report = run.report()
    assert store.failures == [], report
    assert store.operations().count("DeleteObject") == attempts, report
    assert (run.returncode, run.stdout, run.stderr) == (
        returncode,
        stdout,
        stderr,
    ), report
    deleted = returncode == 0
    assert store.objects == (
        without(SEED_OBJECTS, "tree/a.txt") if deleted else SEED_OBJECTS
    ), report


# botocore's feature ids (useragent.py:56-122).
PAGINATOR: Final = "C"
RETRY_STANDARD: Final = "E"
S3_TRANSFER: Final = "G"
REQUEST_WHEN_SUPPORTED: Final = "Z"
RESPONSE_WHEN_SUPPORTED: Final = "b"
CRT_EXPLICIT: Final = "Ae"
CRT_AUTO: Final = "Ag"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("config", "crt_feature"),
    [
        pytest.param("", CRT_AUTO, id="auto"),
        pytest.param(CRT_CONFIG, CRT_EXPLICIT, id="crt-preferred"),
    ],
)
async def test_rm_user_agent_names_the_command_and_transfer_client(
    aws_cli: str, tmp_path: Path, config: str, crt_feature: str
) -> None:
    store = InMemoryS3(SEED_OBJECTS)
    run = await run_rm(
        aws_cli,
        tmp_path,
        store,
        f"s3://{BUCKET}/tree/",
        "--recursive",
        config=config,
        # The session id would open the session database under HOME.
        environment={"AWS_CLI_SESSION_ID_DISABLED": "true"},
    )
    report = run.report()
    assert store.failures == [], report
    assert run.returncode == 0, report
    transfer = {
        RETRY_STANDARD,
        REQUEST_WHEN_SUPPORTED,
        RESPONSE_WHEN_SUPPORTED,
        S3_TRANSFER,
        crt_feature,
    }
    extras = frozenset({"md/prompt#off", "md/command#s3.rm"})
    seen = []
    for request in store.received:
        operation = request.operation_model.name
        user_agent = request.wire_request.headers.get("user-agent", "")
        seen.append(operation)
        expected = (
            transfer | {PAGINATOR}
            if operation == "ListObjectsV2"
            else transfer
        )
        assert user_agent_parts(user_agent) == (
            frozenset(expected),
            extras,
        ), f"{operation}: {user_agent}\n{report}"
        # What the CRT appends is its own, so only its presence on the
        # transfer client's requests is checked.
        if operation == "DeleteObject":
            assert f" {CRT_SUFFIX}" in user_agent, (
                f"{operation}: {user_agent}\n{report}"
            )
    assert seen[0] == "ListObjectsV2", report
    assert sorted(seen[1:]) == ["DeleteObject"] * len(TREE), report


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("environment", "config", "warning"),
    [
        pytest.param(
            {"AWS_RETRY_MODE": "adaptive"},
            CRT_CONFIG,
            "retry_mode = adaptive",
            id="adaptive",
        ),
        pytest.param(
            {},
            CRT_CONFIG + "  max_queue_size = 10\n",
            "max_queue_size",
            id="max-queue-size",
        ),
    ],
)
async def test_rm_warns_about_settings_the_crt_client_ignores(
    aws_cli: str,
    tmp_path: Path,
    environment: Mapping[str, str],
    config: str,
    warning: str,
) -> None:
    store = InMemoryS3(SEED_OBJECTS)
    run = await run_rm(
        aws_cli,
        tmp_path,
        store,
        f"s3://{BUCKET}/tree/a.txt",
        "--quiet",
        config=config,
        environment=environment,
    )
    report = run.report()
    assert store.failures == [], report
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        "",
        "warning: The following configuration values are not supported by "
        f"the 'crt' s3 transfer client and will be ignored: {warning}.\n",
    ), report
    assert store.objects == without(SEED_OBJECTS, "tree/a.txt"), report


DOTTED_BUCKET: Final = "bucket.with.dots"
ACCELERATE_CONFIG: Final = (
    "[default]\ns3 =\n  use_accelerate_endpoint = true\n"
)
# The endpoint rules refuse accelerate with a dotted bucket (the S3
# endpoint-rule-set).
PATH_STYLE: Final = "Path-style addressing cannot be used with S3 Accelerate"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("arguments", "returncode", "stdout", "stderr"),
    [
        # The CRT transfer manager resolves a delete's endpoint as it
        # serializes the request, and fails that transfer
        # (s3transfer/crt.py:633-686).
        pytest.param(
            (f"s3://{DOTTED_BUCKET}/tree/a.txt",),
            1,
            "",
            f"delete failed: s3://{DOTTED_BUCKET}/tree/a.txt {PATH_STYLE}\n",
            id="object",
        ),
        # A dry run never reaches the transfer manager.
        pytest.param(
            (f"s3://{DOTTED_BUCKET}/tree/a.txt", "--dryrun"),
            0,
            f"(dryrun) delete: s3://{DOTTED_BUCKET}/tree/a.txt\n",
            "",
            id="object-dryrun",
        ),
        # The listing's client resolves it first, in the file generator.
        pytest.param(
            (f"s3://{DOTTED_BUCKET}/tree/", "--recursive"),
            1,
            "",
            f"fatal error: {PATH_STYLE}\n",
            id="recursive",
        ),
        pytest.param(
            (f"s3://{DOTTED_BUCKET}",),
            1,
            "",
            f"fatal error: {PATH_STYLE}\n",
            id="folder-markers",
        ),
    ],
)
async def test_rm_endpoint_rule_refusal_sends_nothing(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    returncode: int,
    stdout: str,
    stderr: str,
) -> None:
    objects = {(DOTTED_BUCKET, key): body for (_, key), body in TREE.items()}
    store = InMemoryS3(objects)
    run = await run_rm(
        aws_cli, tmp_path, store, *arguments, config=ACCELERATE_CONFIG
    )
    report = run.report()
    assert store.failures == [], report
    assert (run.returncode, run.stdout, run.stderr) == (
        returncode,
        stdout,
        stderr,
    ), report
    assert store.received == [], report
    assert store.objects == objects, report


# The region the redirecting bucket lives in; the CLI is configured for
# us-east-1.
TARGET_REGION: Final = "us-west-2"
SIGNING_REGION: Final = re.compile(r"Credential=[^/]+/[^/]+/([^/]+)/s3/")


class RegionalS3(InMemoryS3):
    """A bucket in TARGET_REGION: a request signed for any other region gets
    S3's PermanentRedirect naming the region in its header. Records each
    request's operation, signing region, and status."""

    def __init__(self, objects: Mapping[ObjectKey, bytes]) -> None:
        super().__init__(objects)
        self.signed: list[tuple[str, str, int]] = []

    def dispatch(self, reconstructed: ReconstructedRequest) -> HTTPResponse:
        operation = reconstructed.operation_model.name
        match = SIGNING_REGION.search(
            reconstructed.wire_request.headers.get("Authorization", "")
        )
        if match is None:
            raise AssertionError("request did not carry an S3 signing region")
        if operation == "HeadBucket":
            response = HTTPResponse.raw(
                b"", headers={"x-amz-bucket-region": TARGET_REGION}
            )
        elif match[1] != TARGET_REGION:
            response = HTTPResponse.raw(
                b"<Error><Code>PermanentRedirect</Code>"
                b"<Message>Wrong region</Message></Error>",
                status=301,
                headers={
                    "Content-Type": "application/xml",
                    "x-amz-bucket-region": TARGET_REGION,
                    **REQUEST_IDS,
                },
            )
        else:
            response = super().dispatch(reconstructed)
        self.signed.append((operation, match[1], response.status))
        return response


@pytest.mark.asyncio
async def test_rm_follows_a_region_redirect_for_one_object(
    aws_cli: str, tmp_path: Path
) -> None:
    """The CRT transfer manager replays a redirected delete once in the
    bucket's region (s3transfer/crt.py:266-421)."""
    store = RegionalS3(SEED_OBJECTS)
    run = await run_rm(aws_cli, tmp_path, store, f"s3://{BUCKET}/tree/a.txt")
    report = f"{run.report()}signed: {store.signed}\n"
    assert store.failures == [], report
    assert store.signed == [
        ("DeleteObject", "us-east-1", 301),
        ("DeleteObject", TARGET_REGION, 204),
    ], report
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        f"delete: s3://{BUCKET}/tree/a.txt\n",
        "",
    ), report
    assert store.objects == without(SEED_OBJECTS, "tree/a.txt"), report


@pytest.mark.asyncio
async def test_rm_recursive_follows_a_region_redirect(
    aws_cli: str, tmp_path: Path
) -> None:
    """The listing and the deletes each end up in the bucket's region. How
    many requests are redirected first, and whether a HeadBucket looks the
    region up, depends on which client learned the region, so only the
    answered requests to the bucket's objects are compared."""
    store = RegionalS3(SEED_OBJECTS)
    run = await run_rm(
        aws_cli, tmp_path, store, f"s3://{BUCKET}/tree/", "--recursive"
    )
    report = f"{run.report()}signed: {store.signed}\n"
    answered = sorted(
        (operation, region, status)
        for operation, region, status in store.signed
        if status != 301 and operation != "HeadBucket"
    )
    assert store.failures == [], report
    assert answered == sorted(
        [("ListObjectsV2", TARGET_REGION, 200)]
        + [("DeleteObject", TARGET_REGION, 204)] * len(TREE)
    ), report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        [f"delete: s3://{BUCKET}/{key}" for key in tree_keys()],
        "",
    ), report
    assert store.objects == OUTSIDE, report


@pytest.mark.asyncio
async def test_rm_recursive_deletes_archived_objects_without_a_warning(
    aws_cli: str, tmp_path: Path
) -> None:
    """Upstream's delete submitter has no Glacier rule
    (s3handler.py:670-691), so archived objects are deleted like any other."""
    storage = {
        "tree/a.txt": ("GLACIER", None),
        "tree/b.txt": ("DEEP_ARCHIVE", None),
    }
    store = InMemoryS3(SEED_OBJECTS, storage=storage)
    run = await run_rm(
        aws_cli, tmp_path, store, f"s3://{BUCKET}/tree/", "--recursive"
    )
    report = run.report()
    assert store.failures == [], report
    assert run.deletes() == tree_keys(), report
    assert (run.returncode, run.stdout_lines(), run.stderr) == (
        0,
        [f"delete: s3://{BUCKET}/{key}" for key in tree_keys()],
        "",
    ), report
    assert store.objects == OUTSIDE, report


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", MODES)
async def test_rm_recursive_of_an_empty_prefix_deletes_nothing(
    aws_cli: str, tmp_path: Path, mode: OutputMode
) -> None:
    store = InMemoryS3(SEED_OBJECTS)
    run = await run_rm(
        aws_cli,
        tmp_path,
        store,
        f"s3://{BUCKET}/nothing/",
        "--recursive",
        *mode.flags,
    )
    report = run.report()
    assert store.failures == [], report
    assert run.requests() == [("ListObjectsV2", "nothing/")], report
    assert (run.returncode, run.stdout, run.stderr) == (0, "", ""), report
    assert store.objects == SEED_OBJECTS, report
