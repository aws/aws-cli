"""S3 region redirects, HeadBucket region lookups, and the region cache.

Each test runs one command against a bucket of s3store.py that lives in
us-west-2 while the CLI is configured for us-east-1. The bucket answers a
request signed for any other region with a scripted redirect, and records
every request it answers: the operation, the region it was signed for, its
continuation token, the status it got, and its key. The tests assert those
requests, the result lines, the exit status, and what was moved.

The AWS CLI follows a redirect in two places. botocore's S3RegionRedirectorv2
(botocore/utils.py:1577-1806) follows it for the calls the command makes
itself: ListObjectsV2, HeadObject, and the HeadBucket lookup. The CRT
transfer manager follows it for PutObject and GetObject with
CRTS3RegionRedirectPolicy (s3transfer/crt.py:266-421), which classifies the
error with the same redirector but keeps its own region cache
(s3transfer/crt.py:885-916).
"""

import asyncio
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Final

import pytest
from localstub import HTTPResponse, ResponderContext

from awswire import ReconstructedRequest
from credhelpers import run_command
from s3store import (
    LAST_MODIFIED,
    InMemoryS3,
    ObjectKey,
    decoded,
    etag_of,
    pattern_bytes,
    read_tree,
    s3_runtime,
    write_tree,
)

BUCKET: Final = "bucket"
REGION: Final = "us-east-1"
# The region the bucket lives in.
TARGET_REGION: Final = "us-west-2"
SIGNING_REGION: Final = re.compile(r"Credential=[^/]+/[^/]+/([^/]+)/s3/")
CRT_CONFIG: Final = "[default]\ns3 =\n  preferred_transfer_client = crt\n"
# The CLI writes LastModified in local time, and s3_runtime pins TZ=UTC.
LISTED_TIME: Final = "2026-01-02 03:04:05"
# How long the bucket holds a request back for another one to arrive.
HOLD_SECONDS: Final = 5.0

SEED_OBJECTS: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, "download/object.txt"): pattern_bytes("object", 2048),
    (BUCKET, "tree/a.txt"): pattern_bytes("tree a", 100),
    (BUCKET, "tree/b.txt"): pattern_bytes("tree b", 1500),
    (BUCKET, "tree/nested/c.txt"): pattern_bytes("tree c", 700),
}
TREE: Final = {
    key: body
    for (_, key), body in SEED_OBJECTS.items()
    if key.startswith("tree/")
}
UPLOAD_FILE: Final = pattern_bytes("upload", 3000)
UPLOAD_TREE: Final[dict[str, bytes]] = {
    "src/one.txt": pattern_bytes("one", 400),
    "src/two.txt": pattern_bytes("two", 1200),
    "src/sub/three.txt": pattern_bytes("three", 50),
}


@dataclass(frozen=True)
class Redirect:
    """How the bucket answers a request signed for the wrong region."""

    name: str
    status: int = 301
    code: str = "PermanentRedirect"
    # The x-amz-bucket-region header, and the error body's Region.
    header: str | None = TARGET_REGION
    xml_region: str | None = None
    # Redirect only requests that carry a continuation token.
    later_page: bool = False
    # Redirect every request, even one signed for the bucket's region.
    repeated: bool = False
    # Hold the HeadBucket lookup until two uploads have been redirected.
    concurrent: bool = False
    # Refuse the first HeadBucket lookup with a bare 403, and hold every
    # later upload until it has been answered.
    fail_first_lookup: bool = False
    # Replaces the error body.
    raw_body: bytes | None = None


# The region is in the header (utils.py:1743-1744).
HEADER: Final = Redirect("header")
# The region is in the error body only (utils.py:1746-1747).
XML: Final = Redirect(
    "xml", 400, "AuthorizationHeaderMalformed", None, TARGET_REGION
)
# The response names no region, so the CLI looks the bucket up with
# HeadBucket (utils.py:1748-1755).
LOOKUP: Final = Redirect("lookup", 307, "TemporaryRedirect", None)
# The header wins over the body (utils.py:1743-1747).
PRECEDENCE: Final = Redirect(
    "header-precedence",
    400,
    "AuthorizationHeaderMalformed",
    TARGET_REGION,
    "eu-west-1",
)


@dataclass(frozen=True)
class Request:
    operation: str
    region: str
    token: str | None
    status: int
    key: str | None


class RedirectS3(InMemoryS3):
    """The bucket, in TARGET_REGION, scripted to redirect by `script`."""

    def __init__(
        self,
        objects: Mapping[ObjectKey, bytes],
        script: Redirect,
        *,
        base_path: str = "",
    ) -> None:
        super().__init__(objects)
        self.script = script
        self.base_path = base_path
        self.requests: list[Request] = []
        # The bucket answers on the test's event loop, so these need no lock.
        self.redirected_uploads = asyncio.Event()
        self.lookup_answered = asyncio.Event()
        self.upload_arrived = False

    async def respond(self, context: ResponderContext) -> HTTPResponse:
        request = context.request
        if self.base_path:
            path = request.target.partition("?")[0]
            if not path.startswith(f"{self.base_path}/{BUCKET}") or (
                path.split("/").count(BUCKET) != 1
            ):
                self.failures.append(f"base path lost: {request.target}")
            context = context.clone_request(
                target=request.target.removeprefix(self.base_path)
            )
        # A HEAD of the bucket itself: "/" when virtual-hosted.
        path = context.request.target.partition("?")[0]
        is_lookup = request.method == "HEAD" and path.strip("/") in {
            "",
            BUCKET,
        }
        if self.script.concurrent and is_lookup:
            await self.hold(self.redirected_uploads, "two redirected PUTs")
        if self.script.fail_first_lookup and request.method == "PUT":
            if self.upload_arrived:
                await self.hold(self.lookup_answered, "the first lookup")
            self.upload_arrived = True
        return await super().respond(context)

    async def hold(self, event: asyncio.Event, what: str) -> None:
        try:
            await asyncio.wait_for(event.wait(), timeout=HOLD_SECONDS)
        except TimeoutError:
            self.failures.append(f"timed out waiting for {what}")

    def dispatch(self, reconstructed: ReconstructedRequest) -> HTTPResponse:
        operation = reconstructed.operation_model.name
        match = SIGNING_REGION.search(
            reconstructed.wire_request.headers.get("Authorization", "")
        )
        if match is None:
            raise AssertionError("request did not carry an S3 signing region")
        region = match[1]
        token = reconstructed.params.get("ContinuationToken")
        if operation == "HeadBucket":
            # A HeadBucket answers with headers only, whatever its region.
            if self.script.fail_first_lookup and not any(
                r.operation == "HeadBucket" for r in self.requests
            ):
                response = HTTPResponse.raw(b"", status=403)
            else:
                response = HTTPResponse.raw(
                    b"", headers={"x-amz-bucket-region": TARGET_REGION}
                )
            self.lookup_answered.set()
        elif (region != TARGET_REGION or self.script.repeated) and (
            not self.script.later_page or token is not None
        ):
            response = self.redirect_response()
        elif operation == "ListObjectsV2":
            response = self.list_page(reconstructed)
        else:
            response = super().dispatch(reconstructed)
        self.requests.append(
            Request(
                operation,
                region,
                token,
                response.status,
                reconstructed.params.get("Key"),
            )
        )
        redirected = {
            r.key
            for r in self.requests
            if r.operation == "PutObject" and r.status == 307
        }
        if len(redirected) >= 2:
            self.redirected_uploads.set()
        return response

    def redirect_response(self) -> HTTPResponse:
        script = self.script
        region = (
            f"<Region>{script.xml_region}</Region>"
            if script.xml_region is not None
            else ""
        )
        body = (
            f"<Error><Code>{script.code}</Code>"
            f"<Message>Wrong region</Message>{region}</Error>"
        ).encode()
        if script.raw_body is not None:
            body = script.raw_body
        headers = {"Content-Type": "application/xml"}
        if script.header is not None:
            headers["x-amz-bucket-region"] = script.header
        return HTTPResponse.raw(body, status=script.status, headers=headers)

    def list_page(self, reconstructed: ReconstructedRequest) -> HTTPResponse:
        """A ListObjectsV2 page of MaxKeys keys; its token is an offset."""
        params = reconstructed.params
        matches = sorted(
            (key, body)
            for (bucket, key), body in self.objects.items()
            if bucket == params["Bucket"]
            and key.startswith(params.get("Prefix", ""))
        )
        start = int(params.get("ContinuationToken", "0"))
        size = int(params.get("MaxKeys", 1000))
        page = matches[start : start + size]
        more = start + len(page) < len(matches)
        parsed: dict[str, Any] = {
            "Name": BUCKET,
            "Prefix": params.get("Prefix", ""),
            "MaxKeys": size,
            "KeyCount": len(page),
            "IsTruncated": more,
            "Contents": [
                {
                    "Key": key,
                    "Size": len(body),
                    "ETag": etag_of(body),
                    "LastModified": LAST_MODIFIED,
                    "StorageClass": "STANDARD",
                }
                for key, body in page
            ],
        }
        if more:
            parsed["NextContinuationToken"] = str(start + len(page))
        return self.serialize(reconstructed, parsed)


@dataclass(frozen=True)
class Case:
    name: str
    arguments: tuple[str, ...]
    local_files: Mapping[str, bytes] = field(default_factory=dict[str, bytes])
    downloaded_files: Mapping[str, bytes] = field(
        default_factory=dict[str, bytes]
    )
    uploaded_objects: Mapping[ObjectKey, bytes] = field(
        default_factory=dict[ObjectKey, bytes]
    )
    # The keys a successful run downloads.
    downloaded_keys: tuple[str, ...] = ()
    # The stdout lines of a successful run.
    successes: tuple[str, ...] = ()
    # Result lines complete in a nondeterministic order, so they are sorted.
    multi_file: bool = False
    # Successful ListObjectsV2 pages the command reads.
    list_pages: int = 0


@dataclass(frozen=True)
class Run:
    returncode: int
    stdout: str
    stderr: str
    local_files: dict[str, bytes]
    store: RedirectS3

    def describe(self) -> str:
        requests = "\n".join(f"  {r}" for r in self.store.requests)
        return (
            f"exit {self.returncode}\n"
            f"stdout: {self.stdout!r}\n"
            f"stderr: {self.stderr!r}\n"
            f"requests:\n{requests}\n"
            f"failures: {self.store.failures}\n"
        )


def local(*parts: str) -> str:
    """A local path as upstream's relative_path shows it, with os.sep."""
    return os.path.join(*parts)


def upload_line(source: str, key: str) -> str:
    return f"upload: {source} to s3://{BUCKET}/{key}\n"


def download_line(key: str, destination: str) -> str:
    return f"download: s3://{BUCKET}/{key} to {destination}\n"


def listed_line(key: str) -> str:
    """A recursive listing's object line (awscli/customizations/s3/
    subcommands.py:868)."""
    size = len(SEED_OBJECTS[(BUCKET, key)])
    return f"{LISTED_TIME} {size:>10} {key}\n"


def upload_failure_line(source: str, key: str, code: str) -> str:
    """A failed upload (results.py:432-440), with the redirect's message."""
    return (
        f"upload failed: {source} to s3://{BUCKET}/{key} An error occurred "
        f"({code}) when calling the PutObject operation: Wrong region\n"
    )


LIST_CASE: Final = Case(
    "paginated-list",
    ("s3", "ls", f"s3://{BUCKET}/tree/", "--recursive", "--page-size", "1"),
    successes=tuple(listed_line(key) for key in sorted(TREE)),
    list_pages=3,
)
UPLOAD_SINGLE: Final = Case(
    "upload-single",
    ("s3", "cp", "upload.txt", f"s3://{BUCKET}/up/upload.txt"),
    local_files={"upload.txt": UPLOAD_FILE},
    uploaded_objects={(BUCKET, "up/upload.txt"): UPLOAD_FILE},
    successes=(upload_line(local(".", "upload.txt"), "up/upload.txt"),),
)
DOWNLOAD_SINGLE: Final = Case(
    "download-single",
    ("s3", "cp", f"s3://{BUCKET}/download/object.txt", "object.txt"),
    downloaded_files={
        "object.txt": SEED_OBJECTS[(BUCKET, "download/object.txt")]
    },
    downloaded_keys=("download/object.txt",),
    successes=(
        download_line("download/object.txt", local(".", "object.txt")),
    ),
)
DOWNLOAD_RECURSIVE: Final = Case(
    "download-recursive",
    ("s3", "cp", f"s3://{BUCKET}/tree/", "tree", "--recursive"),
    downloaded_files=TREE,
    downloaded_keys=tuple(TREE),
    successes=tuple(
        sorted(download_line(key, local(*key.split("/"))) for key in TREE)
    ),
    multi_file=True,
    list_pages=1,
)
UPLOAD_RECURSIVE: Final = Case(
    "upload-recursive",
    ("s3", "cp", "src", f"s3://{BUCKET}/up/", "--recursive"),
    local_files=UPLOAD_TREE,
    uploaded_objects={
        (BUCKET, f"up/{path.removeprefix('src/')}"): body
        for path, body in UPLOAD_TREE.items()
    },
    successes=tuple(
        sorted(
            upload_line(local(*path.split("/")), f"up/{path[len('src/') :]}")
            for path in UPLOAD_TREE
        )
    ),
    multi_file=True,
)


async def run_aws(
    aws_cli: str,
    tmp_path: Path,
    case: Case,
    script: Redirect,
    *,
    endpoint_url: str | None = None,
    base_path: str = "",
    config: str = CRT_CONFIG,
    region: str = REGION,
) -> Run:
    """Run `case` once in tmp_path/work against the redirecting bucket."""
    work = tmp_path / "work"
    work.mkdir()
    write_tree(work, case.local_files)
    store = RedirectS3(SEED_OBJECTS, script, base_path=base_path)
    arguments = [*case.arguments]
    if arguments[1] == "cp":
        arguments.append("--no-progress")
    if endpoint_url is not None:
        arguments += ["--endpoint-url", endpoint_url]
    async with s3_runtime(store, tmp_path) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(config, encoding="utf-8")
        env.update(AWS_REGION=region, AWS_DEFAULT_REGION=region)
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


def assert_redirected(
    run: Run, case: Case, script: Redirect, lookups: int
) -> None:
    """The command succeeded in the bucket's region after redirects.

    Concurrent transfers can each be redirected before any of them has
    cached the region, so how many fail varies; where each one is sent
    does not.
    """
    report = run.describe()
    assert run.store.failures == [], report
    assert (run.returncode, run.stderr) == (0, ""), report
    stdout = run.stdout.splitlines(keepends=True)
    if case.multi_file:
        stdout.sort()
    assert stdout == list(case.successes), report
    assert run.local_files == {
        **case.local_files,
        **case.downloaded_files,
    }, report
    assert run.store.objects == {
        **SEED_OBJECTS,
        **case.uploaded_objects,
    }, report
    records = run.store.requests
    heads = [r for r in records if r.operation == "HeadBucket"]
    # The lookup is signed for the configured region and finds the bucket.
    assert [(r.region, r.status) for r in heads] == [
        (REGION, 200)
    ] * lookups, report
    failed = [r for r in records if r.status >= 300]
    assert failed, report
    assert {r.region for r in failed} == {REGION}, report
    successful = [
        r for r in records if r.status < 300 and r.operation != "HeadBucket"
    ]
    # Only a first page before the redirect succeeds in the client region.
    assert all(
        r.region == TARGET_REGION or (script.later_page and r.token is None)
        for r in successful
    ), report
    # Each object moves once, in the bucket's region.
    puts = [r.key for r in successful if r.operation == "PutObject"]
    assert sorted(puts) == sorted(key for _, key in case.uploaded_objects), (
        report
    )
    gets = [r.key for r in successful if r.operation == "GetObject"]
    assert sorted(gets) == sorted(case.downloaded_keys), report
    if case.list_pages:
        list_failures = [r for r in failed if r.operation == "ListObjectsV2"]
        assert len(list_failures) == 1, report
        pages = [r for r in successful if r.operation == "ListObjectsV2"]
        assert len(pages) == case.list_pages, report
        if script.later_page:
            assert list_failures[0].token == "1", report


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("script", "lookups"),
    [
        pytest.param(HEADER, 0, id="header"),
        pytest.param(XML, 0, id="xml"),
        pytest.param(LOOKUP, 1, id="lookup"),
        pytest.param(PRECEDENCE, 0, id="header-precedence"),
        pytest.param(
            Redirect("later-page", later_page=True), 0, id="later-page"
        ),
    ],
)
async def test_ls_paginated_listing_redirects_and_caches_region(
    aws_cli: str, tmp_path: Path, script: Redirect, lookups: int
) -> None:
    # One page is redirected; the redirector caches the bucket's region
    # (utils.py:1650), so every later page is signed for it from the
    # start (utils.py:1767-1778).
    run = await run_aws(aws_cli, tmp_path, LIST_CASE, script)
    assert_redirected(run, LIST_CASE, script, lookups)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "script", "lookups"),
    [
        pytest.param(UPLOAD_SINGLE, HEADER, 0, id="upload-single-header"),
        pytest.param(UPLOAD_SINGLE, XML, 0, id="upload-single-xml"),
        pytest.param(UPLOAD_SINGLE, LOOKUP, 1, id="upload-single-lookup"),
        pytest.param(DOWNLOAD_SINGLE, HEADER, 0, id="download-single-header"),
        # botocore's redirector and the CRT transfer manager each keep
        # their own region cache (s3transfer/crt.py:885-916), so the
        # command's HeadObject or ListObjectsV2 and then the CRT client's
        # download each look the bucket up. A HEAD response has no body to
        # name the region in, so the command's HeadObject's 400 needs a
        # lookup (utils.py:1697-1700). The CRT client sends no HeadObject of
        # its own, as the command's reported no checksum of the object
        # (s3transfer/crt.py `_configure_full_object_checksum_validation`),
        # so its download starts with a GET, whose 400 names the region.
        pytest.param(DOWNLOAD_SINGLE, XML, 1, id="download-single-xml"),
        pytest.param(DOWNLOAD_SINGLE, LOOKUP, 2, id="download-single-lookup"),
        pytest.param(
            DOWNLOAD_RECURSIVE, HEADER, 0, id="download-recursive-header"
        ),
        pytest.param(
            DOWNLOAD_RECURSIVE, LOOKUP, 2, id="download-recursive-lookup"
        ),
        pytest.param(
            UPLOAD_RECURSIVE, HEADER, 0, id="upload-recursive-header"
        ),
    ],
)
async def test_cp_transfer_redirects_to_bucket_region(
    aws_cli: str, tmp_path: Path, case: Case, script: Redirect, lookups: int
) -> None:
    run = await run_aws(aws_cli, tmp_path, case, script)
    assert_redirected(run, case, script, lookups)


@pytest.mark.asyncio
async def test_cp_concurrent_redirected_uploads_share_one_lookup(
    aws_cli: str, tmp_path: Path
) -> None:
    # The bucket holds the lookup until two uploads have been redirected.
    # The policy looks a bucket up under a lock and rereads the cache once
    # it holds it (s3transfer/crt.py:334-361), so the waiting upload uses
    # the region the first one found.
    script = Redirect(
        "concurrent", 307, "TemporaryRedirect", None, concurrent=True
    )
    run = await run_aws(aws_cli, tmp_path, UPLOAD_RECURSIVE, script)
    assert_redirected(run, UPLOAD_RECURSIVE, script, lookups=1)
    redirected = {r.key for r in run.store.requests if r.status == 307}
    assert len(redirected) >= 2, run.describe()


def listing_error(code: str) -> str:
    return (
        f"\naws: [ERROR]: An error occurred ({code}) when calling the "
        "ListObjectsV2 operation: Wrong region\n"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("script", "regions"),
    [
        # A request already redirected is not redirected again
        # (utils.py:1620-1624), and a 307 is not retried.
        pytest.param(
            Redirect("repeated", 307, "TemporaryRedirect", repeated=True),
            [REGION, TARGET_REGION],
            id="repeated",
        ),
        # A 403 is not a redirect, whatever region header it carries
        # (utils.py:1687-1726).
        pytest.param(
            Redirect("denied", 403, "AccessDenied"),
            [REGION],
            id="access-denied",
        ),
    ],
)
async def test_ls_does_not_replay_terminal_errors(
    aws_cli: str, tmp_path: Path, script: Redirect, regions: list[str]
) -> None:
    run = await run_aws(aws_cli, tmp_path, LIST_CASE, script)
    report = run.describe()
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout) == (254, ""), report
    assert run.stderr == listing_error(script.code), report
    assert [(r.operation, r.region, r.status) for r in run.store.requests] == [
        ("ListObjectsV2", region, script.status) for region in regions
    ]
    assert run.store.objects == SEED_OBJECTS
    assert run.local_files == {}


@pytest.mark.asyncio
async def test_ls_malformed_redirect_region_is_not_used_for_a_request(
    aws_cli: str, tmp_path: Path
) -> None:
    # botocore validates the region before it re-resolves the endpoint
    # (utils.py:1756, 1169-1176), so nothing is sent for it, and the
    # InvalidRegionError ends the command (botocore/exceptions.py
    # InvalidRegionError).
    script = Redirect("malformed", header="bad/region")
    run = await run_aws(aws_cli, tmp_path, LIST_CASE, script)
    report = run.describe()
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout) == (255, ""), report
    assert run.stderr == (
        "\naws: [ERROR]: Provided region_name 'bad/region' doesn't match a "
        "supported format.\n"
    ), report
    assert [(r.operation, r.region, r.status) for r in run.store.requests] == [
        ("ListObjectsV2", REGION, 301)
    ], report
    assert run.store.objects == SEED_OBJECTS
    assert run.local_files == {}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case", [LIST_CASE, UPLOAD_SINGLE], ids=lambda case: case.name
)
async def test_custom_endpoint_base_path_survives_redirect_and_lookup(
    aws_cli: str, tmp_path: Path, case: Case
) -> None:
    # A custom endpoint keeps its path through the lookup and the
    # redirected request; RedirectS3 records any request without it.
    base_path = "/proxy/s3"
    run = await run_aws(
        aws_cli,
        tmp_path,
        case,
        LOOKUP,
        endpoint_url=f"https://s3.example.test{base_path}",
        base_path=base_path,
        config=CRT_CONFIG + "  addressing_style = path\n",
    )
    assert_redirected(run, case, LOOKUP, lookups=1)


@pytest.mark.asyncio
async def test_cp_failed_region_lookup_is_not_cached_for_later_uploads(
    aws_cli: str, tmp_path: Path
) -> None:
    # The first redirected upload's lookup is refused without a region
    # (utils.py:1748-1756), so that upload fails with its redirect
    # (s3transfer/crt.py:400-401). Nothing is cached, so
    # the next redirected upload looks the bucket up again and caches it
    # (s3transfer/crt.py:381-421). The bucket holds every later upload until
    # the first lookup has been answered.
    script = replace(LOOKUP, fail_first_lookup=True)
    run = await run_aws(aws_cli, tmp_path, UPLOAD_RECURSIVE, script)
    report = run.describe()
    records = run.store.requests
    assert run.store.failures == [], report
    assert run.returncode == 1, report
    heads = [
        (r.region, r.status) for r in records if r.operation != "PutObject"
    ]
    assert heads == [(REGION, 403), (REGION, 200)], report
    puts = [r for r in records if r.operation == "PutObject"]
    failed_key = puts[0].key
    assert failed_key is not None, report
    assert [(r.region, r.status) for r in puts if r.key == failed_key] == [
        (REGION, 307)
    ], report
    for key in {r.key for r in puts} - {failed_key}:
        attempts = [(r.region, r.status) for r in puts if r.key == key]
        assert attempts[-1] == (TARGET_REGION, 200), report
        assert set(attempts[:-1]) <= {(REGION, 307)}, report
    source = local("src", *failed_key.removeprefix("up/").split("/"))
    assert run.stderr == upload_failure_line(
        source, failed_key, "TemporaryRedirect"
    ), report
    assert sorted(run.stdout.splitlines(keepends=True)) == [
        line
        for line in UPLOAD_RECURSIVE.successes
        if not line.startswith(f"upload: {source} ")
    ], report
    assert run.store.objects == {
        **SEED_OBJECTS,
        **{
            key: body
            for key, body in UPLOAD_RECURSIVE.uploaded_objects.items()
            if key[1] != failed_key
        },
    }, report
    assert run.local_files == UPLOAD_RECURSIVE.local_files


def assert_upload_not_replayed(run: Run) -> None:
    """The single upload failed with its redirect, and nothing was stored."""
    report = run.describe()
    assert run.store.failures == [], report
    assert (run.returncode, run.stdout) == (1, ""), report
    assert run.stderr == upload_failure_line(
        local(".", "upload.txt"), "up/upload.txt", "PermanentRedirect"
    ), report
    assert run.store.objects == SEED_OBJECTS
    assert run.local_files == UPLOAD_SINGLE.local_files


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("script", "regions"),
    [
        # A transfer already redirected is not redirected again
        # (s3transfer/crt.py:300-306).
        pytest.param(
            replace(HEADER, repeated=True),
            [REGION, TARGET_REGION],
            id="repeated-redirect",
        ),
        # A redirect to the region the upload was made in would fail the
        # same way, so it is not followed (s3transfer/crt.py:404-415).
        pytest.param(
            replace(HEADER, header=REGION), [REGION], id="same-region"
        ),
    ],
)
async def test_cp_upload_does_not_replay_unsafe_redirects(
    aws_cli: str, tmp_path: Path, script: Redirect, regions: Sequence[str]
) -> None:
    run = await run_aws(aws_cli, tmp_path, UPLOAD_SINGLE, script)
    assert_upload_not_replayed(run)
    assert [(r.operation, r.region, r.status) for r in run.store.requests] == [
        ("PutObject", region, 301) for region in regions
    ], run.describe()


@pytest.mark.asyncio
@pytest.mark.parametrize("region", ["fips-us-east-1", "us-east-1-fips"])
async def test_cp_fips_alias_does_not_bypass_same_region_upload_veto(
    aws_cli: str, tmp_path: Path, region: str
) -> None:
    # botocore strips a FIPS pseudo region to us-east-1 (client.py:200-219),
    # the region the veto compares a redirect with (s3transfer/crt.py:
    # 404-415, 1070-1071), so a redirect to us-east-1 is not followed. The
    # region the upload is signed for is not asserted: the AWS CLI's CRT
    # client signs for the pseudo region as configured
    # (customizations/s3/factory.py:526-528).
    run = await run_aws(
        aws_cli,
        tmp_path,
        UPLOAD_SINGLE,
        replace(HEADER, header=REGION),
        region=region,
    )
    assert_upload_not_replayed(run)
    assert [(r.operation, r.status) for r in run.store.requests] == [
        ("PutObject", 301)
    ], run.describe()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        b"<Error><Code>PermanentRedirect</Code><Region>us-west-2",
        b"<Error><Region>us-west-2&invalid;</Region></Error>",
    ],
    ids=["truncated-region", "invalid-entity"],
)
@pytest.mark.parametrize(
    "case", [LIST_CASE, UPLOAD_SINGLE], ids=lambda case: case.name
)
async def test_unparseable_redirect_body_falls_back_to_lookup(
    aws_cli: str, tmp_path: Path, body: bytes, case: Case
) -> None:
    # botocore cannot parse the body, so the error has no Region and its
    # code is the 301 status (botocore/parsers.py:537-548, 1429-1454). A
    # 301 is a redirect
    # (utils.py:1709-1711), so the region comes from a HeadBucket lookup
    # (utils.py:1748-1755) and is never read from the body.
    script = replace(HEADER, header=None, raw_body=body)
    run = await run_aws(aws_cli, tmp_path, case, script)
    assert_redirected(run, case, script, lookups=1)
