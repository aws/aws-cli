"""The object settings `s3 cp` sends with the requests of a transfer.

Upstream copies each setting the command line gives onto the request
parameters of the operations it applies to (customizations/s3/utils.py:
488-598, RequestParamsMapper), skipping any whose value is empty. An
upload's PutObject, or its CreateMultipartUpload, carries them all: the
object's headers, its metadata, its canned ACL, its storage class, its
encryption, and the request payer. The CRT client builds each UploadPart and
CompleteMultipartUpload from that message and keeps only what those
operations take, the customer key and the request payer
(aws-c-s3 s3_request_messages.c). A download's HeadObject and every
GetObject send the customer key and the request payer, and a recursive
download's listing the request payer; the settings only an upload uses are
accepted and ignored. botocore sends the customer key base64-encoded with
its MD5 (botocore/handlers.py:282-296), --expires as an HTTP date, and one
header per metadata name, ignoring case. Each --grants pair sends its
grantee, as given, in the header of its permission.
"""

import base64
import hashlib
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import pytest

from awswire import ReconstructedRequest
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
MIB: Final = 1024 * 1024
# 5 MiB parts above 6 MiB, so a 6 MiB object is a multipart transfer.
CHUNKED_CONFIG: Final = (
    "[default]\ns3 =\n  preferred_transfer_client = crt\n"
    "  multipart_chunksize = 5MB\n  multipart_threshold = 6MB\n"
)
SMALL: Final = pattern_bytes("small", 1024)
LARGE: Final = pattern_bytes("large", 6 * MIB + 1)
# The request members the settings below map to.
SETTING_MEMBERS: Final = (
    "ACL",
    "CacheControl",
    "ContentDisposition",
    "ContentEncoding",
    "ContentLanguage",
    "ContentType",
    "Expires",
    "GrantFullControl",
    "GrantRead",
    "GrantReadACP",
    "GrantWriteACP",
    "Metadata",
    "RequestPayer",
    "SSECustomerAlgorithm",
    "SSECustomerKey",
    "SSECustomerKeyMD5",
    "SSEKMSKeyId",
    "ServerSideEncryption",
    "StorageClass",
    "WebsiteRedirectLocation",
)
# The members compared as sent: awswire parses Expires as a timestamp,
# decodes the customer key, and drops its MD5.
WIRE_MEMBERS: Final = {
    "Expires": "expires",
    "SSECustomerAlgorithm": "x-amz-server-side-encryption-customer-algorithm",
    "SSECustomerKey": "x-amz-server-side-encryption-customer-key",
    "SSECustomerKeyMD5": "x-amz-server-side-encryption-customer-key-md5",
}
READ_OPERATIONS: Final = frozenset({"HeadObject", "GetObject"})
OBJECT_FLAGS: Final = (
    "--content-type",
    "application/x-settings",
    "--cache-control",
    "max-age=60",
    "--content-disposition",
    'attachment; filename="report.txt"',
    "--content-encoding",
    "identity",
    "--content-language",
    "en-US",
    "--expires",
    "Wed, 21 Oct 2037 07:28:00 GMT",
    "--website-redirect",
    "/elsewhere.html",
    "--metadata",
    "origin=settings,Mixed-Case=Value",
    "--acl",
    "bucket-owner-full-control",
    "--storage-class",
    "STANDARD_IA",
    "--sse",
    "aws:kms",
    "--sse-kms-key-id",
    "alias/settings",
)
OBJECT_PARAMS: Final[Mapping[str, Any]] = {
    "ContentType": "application/x-settings",
    "CacheControl": "max-age=60",
    "ContentDisposition": 'attachment; filename="report.txt"',
    "ContentEncoding": "identity",
    "ContentLanguage": "en-US",
    "Expires": "Wed, 21 Oct 2037 07:28:00 GMT",
    "WebsiteRedirectLocation": "/elsewhere.html",
    "Metadata": {"origin": "settings", "Mixed-Case": "Value"},
    "ACL": "bucket-owner-full-control",
    "StorageClass": "STANDARD_IA",
    "ServerSideEncryption": "aws:kms",
    "SSEKMSKeyId": "alias/settings",
}
# A customer key as the command line gives it, and one in a file whose
# bytes are not UTF-8.
TEXT_KEY: Final = "0123456789abcdef0123456789abcdef"
BINARY_KEY: Final = bytes(range(0x80, 0xA0))


def customer_key_params(key: bytes) -> dict[str, str]:
    return {
        "SSECustomerAlgorithm": "AES256",
        "SSECustomerKey": base64.b64encode(key).decode(),
        "SSECustomerKeyMD5": base64.b64encode(
            hashlib.md5(key).digest()
        ).decode(),
    }


PAYER_PARAMS: Final = {"RequestPayer": "requester"}
TEXT_KEY_PARAMS: Final = customer_key_params(TEXT_KEY.encode())


@dataclass(frozen=True)
class Run:
    returncode: int
    stdout: str
    stderr: str
    local_files: dict[str, bytes]
    store: InMemoryS3

    def report(self) -> str:
        return (
            f"exit {self.returncode}\nstdout: {self.stdout!r}\n"
            f"stderr: {self.stderr!r}\nresponses: {self.store.responses}\n"
            f"failures: {self.store.failures}\n"
        )

    def settings(self) -> list["Sent"]:
        """Each request's operation, key, and setting members, sorted."""
        return ordered(
            (
                request.operation_model.name,
                request.params.get("Key", ""),
                setting_params(request),
            )
            for request in self.store.received
        )


Sent = tuple[str, str, dict[str, Any]]


def ordered(sent: Iterable[Sent]) -> list[Sent]:
    """`sent` by operation, key, and members."""
    return sorted(
        sent, key=lambda item: (item[0], item[1], repr(sorted(item[2].items())))
    )


def setting_params(request: ReconstructedRequest) -> dict[str, Any]:
    """The request's setting members, as awswire parses them, except those
    of `WIRE_MEMBERS`, which are taken as sent. awswire leaves out the
    aws-chunked coding the CRT client adds to Content-Encoding for its
    checksum trailer, as S3 stores the object without it."""
    headers = request.wire_request.headers
    params = {
        member: request.params[member]
        for member in SETTING_MEMBERS
        if member in request.params and member not in WIRE_MEMBERS
    }
    params.update(
        (member, value)
        for member, name in WIRE_MEMBERS.items()
        if (value := headers.get(name)) is not None
    )
    return params


async def run_cp(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    store: InMemoryS3,
    *,
    local_files: Mapping[str, bytes] | None = None,
) -> Run:
    work = tmp_path / "work"
    work.mkdir(parents=True)
    write_tree(work, local_files or {})
    async with s3_runtime(store, tmp_path) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(
            CHUNKED_CONFIG, encoding="utf-8"
        )
        stdout, stderr, returncode = await run_command(
            [aws_cli, "s3", "cp", *arguments, "--no-progress"],
            env,
            cwd=work,
            stdin=None,
            timeout=60.0,
        )
    return Run(
        returncode=returncode,
        stdout=decoded(stdout),
        stderr=decoded(stderr),
        local_files=read_tree(work),
        store=store,
    )


@dataclass(frozen=True)
class Upload:
    """A command uploading `files`, and the lines it prints, sorted."""

    arguments: tuple[str, ...]
    files: Mapping[str, bytes]
    lines: tuple[str, ...]


UPLOADS: Final = [
    pytest.param(
        Upload(
            ("small.txt", f"s3://{BUCKET}/up/small.txt"),
            {"small.txt": SMALL},
            (f"upload: .{os.sep}small.txt to s3://{BUCKET}/up/small.txt",),
        ),
        id="put",
    ),
    pytest.param(
        Upload(
            ("large.txt", f"s3://{BUCKET}/up/large.txt"),
            {"large.txt": LARGE},
            (f"upload: .{os.sep}large.txt to s3://{BUCKET}/up/large.txt",),
        ),
        id="multipart",
    ),
    pytest.param(
        Upload(
            ("tree", f"s3://{BUCKET}/up/", "--recursive"),
            {"tree/small.txt": SMALL, "tree/nested/large.txt": LARGE},
            (
                f"upload: tree{os.sep}nested{os.sep}large.txt to "
                f"s3://{BUCKET}/up/nested/large.txt",
                f"upload: tree{os.sep}small.txt to s3://{BUCKET}/up/small.txt",
            ),
        ),
        id="recursive",
    ),
]


def uploaded_objects(upload: Upload) -> dict[ObjectKey, bytes]:
    if "--recursive" in upload.arguments:
        return {
            (BUCKET, f"up/{name.removeprefix('tree/')}"): body
            for name, body in upload.files.items()
        }
    ((name, body),) = upload.files.items()
    return {(BUCKET, f"up/{name}"): body}


def expected_upload_settings(
    upload: Upload,
    create: Mapping[str, Any],
    parts: Mapping[str, Any],
) -> list[Sent]:
    """Each upload request's setting members: `create` on the request that
    creates an object, `parts` on each UploadPart and on the
    CompleteMultipartUpload of a multipart upload."""
    sent: list[Sent] = []
    for (_, key), body in uploaded_objects(upload).items():
        if len(body) <= 6 * MIB:
            sent.append(("PutObject", key, dict(create)))
            continue
        sent.append(("CreateMultipartUpload", key, dict(create)))
        part_count = -(-len(body) // (5 * MIB))
        sent += [("UploadPart", key, dict(parts))] * part_count
        sent.append(("CompleteMultipartUpload", key, dict(parts)))
    return ordered(sent)


def assert_uploaded(run: Run, upload: Upload) -> None:
    report = run.report()
    assert run.store.failures == [], report
    assert (run.returncode, run.stderr) == (0, ""), report
    assert tuple(sorted(run.stdout.splitlines())) == upload.lines, report
    assert run.store.objects == uploaded_objects(upload), report


@pytest.mark.parametrize("upload", UPLOADS)
async def test_cp_upload_sends_object_settings(
    aws_cli: str, tmp_path: Path, upload: Upload
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        (*upload.arguments, *OBJECT_FLAGS, "--request-payer"),
        InMemoryS3(),
        local_files=upload.files,
    )
    assert_uploaded(run, upload)
    assert run.settings() == expected_upload_settings(
        upload, {**OBJECT_PARAMS, **PAYER_PARAMS}, PAYER_PARAMS
    ), run.report()


# Each spelling of an encryption setting, and the members it sends with
# the request that creates the object and with each later part request.
ENCRYPTION: Final = [
    pytest.param(
        ("--sse",),
        {"ServerSideEncryption": "AES256"},
        {},
        {},
        id="sse-bare",
    ),
    pytest.param(
        ("--sse", "AES256"),
        {"ServerSideEncryption": "AES256"},
        {},
        {},
        id="sse-aes256",
    ),
    pytest.param(
        ("--sse", "aws:kms", "--sse-kms-key-id", "arn:aws:kms:key/settings"),
        {
            "ServerSideEncryption": "aws:kms",
            "SSEKMSKeyId": "arn:aws:kms:key/settings",
        },
        {},
        {},
        id="sse-kms-key",
    ),
    # Upstream sends a key id without --sse as it is, for S3 to judge.
    pytest.param(
        ("--sse-kms-key-id", "alias/alone"),
        {"SSEKMSKeyId": "alias/alone"},
        {},
        {},
        id="kms-key-alone",
    ),
    pytest.param(
        ("--sse-c", "--sse-c-key", TEXT_KEY),
        TEXT_KEY_PARAMS,
        TEXT_KEY_PARAMS,
        {},
        id="sse-c-bare",
    ),
    pytest.param(
        ("--sse-c", "AES256", "--sse-c-key", "fileb://key.bin"),
        customer_key_params(BINARY_KEY),
        customer_key_params(BINARY_KEY),
        {"key.bin": BINARY_KEY},
        id="sse-c-binary-file",
    ),
    pytest.param(
        ("--sse-c-key", "file://key.txt", "--sse-c"),
        TEXT_KEY_PARAMS,
        TEXT_KEY_PARAMS,
        {"key.txt": TEXT_KEY.encode()},
        id="sse-c-text-file",
    ),
]


@pytest.mark.parametrize(("flags", "create", "parts", "key_files"), ENCRYPTION)
@pytest.mark.parametrize("upload", UPLOADS)
async def test_cp_upload_sends_encryption_settings(
    aws_cli: str,
    tmp_path: Path,
    upload: Upload,
    flags: tuple[str, ...],
    create: dict[str, str],
    parts: dict[str, str],
    key_files: dict[str, bytes],
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        (*upload.arguments, *flags),
        InMemoryS3(),
        local_files={**upload.files, **key_files},
    )
    assert_uploaded(run, upload)
    assert run.settings() == expected_upload_settings(
        upload, {**create, "ContentType": "text/plain"}, parts
    ), run.report()


async def test_cp_recursive_upload_gives_every_object_the_explicit_type(
    aws_cli: str, tmp_path: Path
) -> None:
    files = {
        "tree/index.html": SMALL,
        "tree/data.json": SMALL,
        "tree/Makefile": SMALL,
    }
    upload = Upload(
        ("tree", f"s3://{BUCKET}/up/", "--recursive"),
        files,
        tuple(
            sorted(
                f"upload: tree{os.sep}{name} to s3://{BUCKET}/up/{name}"
                for name in ("index.html", "data.json", "Makefile")
            )
        ),
    )
    run = await run_cp(
        aws_cli,
        tmp_path,
        (*upload.arguments, "--content-type", "text/x-explicit"),
        InMemoryS3(),
        local_files=files,
    )
    assert_uploaded(run, upload)
    assert run.settings() == expected_upload_settings(
        upload, {"ContentType": "text/x-explicit"}, {}
    ), run.report()


# Upstream copies only settings whose value is truthy, so an empty value
# sends nothing, and an empty --content-type leaves the guessed type.
EMPTY_FLAGS: Final = (
    "--content-type",
    "",
    "--cache-control",
    "",
    "--content-disposition",
    "",
    "--content-encoding",
    "",
    "--content-language",
    "",
    "--expires",
    "",
    "--website-redirect",
    "",
    "--metadata",
    "{}",
    "--sse-kms-key-id",
    "",
    "--sse-c-key",
    "",
)


@pytest.mark.parametrize("upload", UPLOADS)
async def test_cp_upload_sends_no_empty_setting(
    aws_cli: str, tmp_path: Path, upload: Upload
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        (*upload.arguments, *EMPTY_FLAGS),
        InMemoryS3(),
        local_files=upload.files,
    )
    assert_uploaded(run, upload)
    assert run.settings() == expected_upload_settings(
        upload, {"ContentType": "text/plain"}, {}
    ), run.report()


# Each spelling of --metadata, and the metadata it sends.
METADATA: Final = [
    pytest.param(
        ("--metadata", "a=1,b=two words"),
        {},
        {"a": "1", "b": "two words"},
        id="shorthand",
    ),
    pytest.param(
        ("--metadata", '{"Origin": "json", "empty": ""}'),
        {},
        {"Origin": "json", "empty": ""},
        id="json",
    ),
    pytest.param(
        ("--metadata", "file://metadata.json"),
        {"metadata.json": b'{"from": "file"}'},
        {"from": "file"},
        id="file",
    ),
]


@pytest.mark.parametrize(("flags", "key_files", "metadata"), METADATA)
async def test_cp_upload_sends_metadata_as_given(
    aws_cli: str,
    tmp_path: Path,
    flags: tuple[str, ...],
    key_files: dict[str, bytes],
    metadata: dict[str, str],
) -> None:
    upload = UPLOADS[0].values[0]
    run = await run_cp(
        aws_cli,
        tmp_path,
        (*upload.arguments, *flags),
        InMemoryS3(),
        local_files={**upload.files, **key_files},
    )
    assert_uploaded(run, upload)
    assert run.settings() == [
        (
            "PutObject",
            "up/small.txt",
            {"ContentType": "text/plain", "Metadata": metadata},
        )
    ], run.report()


# Each spelling of --expires, and the HTTP date botocore sends for it: its
# merged S3 model types Expires as a timestamp (service-2.sdk-extras.json),
# which it reads with dateutil, as UTC without a zone, and sends in GMT to
# the whole second.
EXPIRES: Final = [
    pytest.param(
        "2037-10-21T07:28:00Z", "Wed, 21 Oct 2037 07:28:00 GMT", id="iso-utc"
    ),
    pytest.param(
        "2037-10-21T07:28:00.5+05:30",
        "Wed, 21 Oct 2037 01:58:00 GMT",
        id="iso-offset",
    ),
    pytest.param("2037-10-21", "Wed, 21 Oct 2037 00:00:00 GMT", id="iso-date"),
    # dateutil ignores a weekday the date contradicts.
    pytest.param(
        "Mon, 21 Oct 2037 07:28:00 GMT",
        "Wed, 21 Oct 2037 07:28:00 GMT",
        id="http-date",
    ),
]


@pytest.mark.parametrize(("value", "sent"), EXPIRES)
@pytest.mark.parametrize("upload", UPLOADS)
async def test_cp_upload_sends_expires_as_an_http_date(
    aws_cli: str, tmp_path: Path, upload: Upload, value: str, sent: str
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        (*upload.arguments, "--expires", value),
        InMemoryS3(),
        local_files=upload.files,
    )
    assert_uploaded(run, upload)
    assert run.settings() == expected_upload_settings(
        upload, {"ContentType": "text/plain", "Expires": sent}, {}
    ), run.report()


async def test_cp_upload_sends_one_header_per_metadata_name(
    aws_cli: str, tmp_path: Path
) -> None:
    """botocore's case-insensitive HeadersDict keeps the first spelling of
    names equal but for case, with the last value (awsrequest.py:585-629)."""
    upload = UPLOADS[0].values[0]
    run = await run_cp(
        aws_cli,
        tmp_path,
        (
            *upload.arguments,
            "--metadata",
            "Foo=old,bar=kept,foo=new,FOO=newest",
        ),
        InMemoryS3(),
        local_files=upload.files,
    )
    assert_uploaded(run, upload)
    (request,) = run.store.received
    sent = sorted(
        (name, value)
        for name, value in request.wire_request.headers.items()
        if name.lower().startswith("x-amz-meta-")
    )
    assert sent == [
        ("x-amz-meta-Foo", "newest"),
        ("x-amz-meta-bar", "kept"),
    ], run.report()


# Each spelling of --grants, and the members it sends: each pair's grantee,
# as given, in the member of its permission, with a later pair of the same
# permission replacing an earlier one (customizations/s3/utils.py:640-660).
# A second --grants replaces the first, as argparse stores the last list.
GRANTS: Final = [
    pytest.param(
        (
            "--grants",
            "read=uri=http://acs.amazonaws.com/groups/global/AllUsers",
            "full=id=owner",
            "readacl=id=first,id=second",
            "writeacl=emailaddress=writer@example.com",
        ),
        {
            "GrantRead": "uri=http://acs.amazonaws.com/groups/global/AllUsers",
            "GrantFullControl": "id=owner",
            "GrantReadACP": "id=first,id=second",
            "GrantWriteACP": "emailaddress=writer@example.com",
        },
        id="each-permission",
    ),
    pytest.param(
        ("--grants", "read=id=first", "full=id=owner", "read=id=last"),
        {"GrantRead": "id=last", "GrantFullControl": "id=owner"},
        id="last-pair-wins",
    ),
    pytest.param(
        ("--grants", "read=id=first", "--grants", "full=id=owner"),
        {"GrantFullControl": "id=owner"},
        id="last-option-wins",
    ),
    # Unlike the other settings, a grant is sent even when its grantee is
    # empty.
    pytest.param(("--grants", "read="), {"GrantRead": ""}, id="empty-grantee"),
]


@pytest.mark.parametrize(("flags", "grants"), GRANTS)
@pytest.mark.parametrize("upload", UPLOADS)
async def test_cp_upload_sends_grants(
    aws_cli: str,
    tmp_path: Path,
    upload: Upload,
    flags: tuple[str, ...],
    grants: dict[str, str],
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        (*upload.arguments, *flags),
        InMemoryS3(),
        local_files=upload.files,
    )
    assert_uploaded(run, upload)
    assert run.settings() == expected_upload_settings(
        upload, {**grants, "ContentType": "text/plain"}, {}
    ), run.report()


# The grants upstream refuses as it maps an upload's request parameters,
# for the first file it would upload, even in a dry run
# (s3handler.py:259-266).
GRANT_REFUSALS: Final = [
    pytest.param(
        ("--grants", "read=id=reader", "everyone"),
        "grants should be of the form permission=principal",
        id="no-separator",
    ),
    pytest.param(
        ("--grants", "write=id=writer"),
        "permission must be one of: read|readacl|writeacl|full",
        id="unknown-permission",
    ),
    pytest.param(
        ("--grants", "READ=id=reader"),
        "permission must be one of: read|readacl|writeacl|full",
        id="permission-case",
    ),
]
GRANT_REFUSED_UPLOADS: Final = [
    pytest.param(
        ("small.txt", f"s3://{BUCKET}/up/small.txt"), id="upload"
    ),
    pytest.param(
        ("tree", f"s3://{BUCKET}/up/", "--recursive"), id="recursive-upload"
    ),
    pytest.param(
        ("small.txt", f"s3://{BUCKET}/up/small.txt", "--dryrun"),
        id="dryrun",
    ),
]


@pytest.mark.parametrize("arguments", GRANT_REFUSED_UPLOADS)
@pytest.mark.parametrize(("flags", "message"), GRANT_REFUSALS)
async def test_cp_upload_refuses_a_malformed_grant(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    flags: tuple[str, ...],
    message: str,
) -> None:
    store = InMemoryS3()
    run = await run_cp(
        aws_cli,
        tmp_path,
        (*arguments, *flags),
        store,
        local_files={"small.txt": SMALL, "tree/small.txt": SMALL},
    )
    report = run.report()
    assert (run.returncode, run.stdout, run.stderr) == (
        1,
        "",
        f"fatal error: {message}\n",
    ), report
    assert store.received == [], report


DOWNLOAD_OBJECTS: Final[dict[ObjectKey, bytes]] = {
    (BUCKET, "down/small.txt"): SMALL,
    (BUCKET, "down/nested/large.txt"): LARGE,
}


@dataclass(frozen=True)
class Download:
    """A command downloading `files`, and the lines it prints, sorted."""

    arguments: tuple[str, ...]
    files: Mapping[str, bytes]
    lines: tuple[str, ...]


DOWNLOADS: Final = [
    pytest.param(
        Download(
            (f"s3://{BUCKET}/down/small.txt", "small.txt"),
            {"small.txt": SMALL},
            (f"download: s3://{BUCKET}/down/small.txt to .{os.sep}small.txt",),
        ),
        id="single",
    ),
    pytest.param(
        Download(
            (f"s3://{BUCKET}/down/nested/large.txt", "large.txt"),
            {"large.txt": LARGE},
            (
                f"download: s3://{BUCKET}/down/nested/large.txt to "
                f".{os.sep}large.txt",
            ),
        ),
        id="ranged",
    ),
    pytest.param(
        Download(
            (f"s3://{BUCKET}/down/", "tree", "--recursive"),
            {"tree/small.txt": SMALL, "tree/nested/large.txt": LARGE},
            (
                f"download: s3://{BUCKET}/down/nested/large.txt to "
                f"tree{os.sep}nested{os.sep}large.txt",
                f"download: s3://{BUCKET}/down/small.txt to "
                f"tree{os.sep}small.txt",
            ),
        ),
        id="recursive",
    ),
]


def assert_downloaded(run: Run, download: Download) -> None:
    report = run.report()
    assert run.store.failures == [], report
    assert (run.returncode, run.stderr) == (0, ""), report
    assert tuple(sorted(run.stdout.splitlines())) == download.lines, report
    assert run.local_files == download.files, report


def sent_settings(run: Run) -> set[tuple[str, str]]:
    """Each operation the command sent, with the setting members it sent
    them with, spelled for comparison."""
    return {
        (operation, repr(sorted(members.items())))
        for operation, _, members in run.settings()
    }


# The download settings, and the members each object read and listing sends.
DOWNLOAD_SETTINGS: Final = [
    pytest.param(
        ("--request-payer",), PAYER_PARAMS, PAYER_PARAMS, id="payer"
    ),
    pytest.param(
        ("--sse-c", "--sse-c-key", TEXT_KEY),
        TEXT_KEY_PARAMS,
        {},
        id="sse-c",
    ),
    pytest.param(
        ("--sse-c", "--sse-c-key", TEXT_KEY, "--request-payer", "requester"),
        {**TEXT_KEY_PARAMS, **PAYER_PARAMS},
        PAYER_PARAMS,
        id="sse-c-payer",
    ),
]


@pytest.mark.parametrize(("flags", "reads", "listing"), DOWNLOAD_SETTINGS)
@pytest.mark.parametrize("download", DOWNLOADS)
async def test_cp_download_sends_customer_key_and_request_payer(
    aws_cli: str,
    tmp_path: Path,
    download: Download,
    flags: tuple[str, ...],
    reads: dict[str, str],
    listing: dict[str, str],
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        (*download.arguments, *flags),
        InMemoryS3(DOWNLOAD_OBJECTS),
    )
    assert_downloaded(run, download)
    operations = {name for name, _ in sent_settings(run)}
    expected = {
        (name, repr(sorted(reads.items())))
        for name in operations & READ_OPERATIONS
    }
    if "ListObjectsV2" in operations:
        expected.add(("ListObjectsV2", repr(sorted(listing.items()))))
    assert "GetObject" in operations, run.report()
    assert sent_settings(run) == expected, run.report()


@pytest.mark.parametrize("download", DOWNLOADS)
async def test_cp_download_ignores_upload_settings(
    aws_cli: str, tmp_path: Path, download: Download
) -> None:
    run = await run_cp(
        aws_cli,
        tmp_path,
        (*download.arguments, *OBJECT_FLAGS),
        InMemoryS3(DOWNLOAD_OBJECTS),
    )
    assert_downloaded(run, download)
    assert {members for _, members in sent_settings(run)} == {"[]"}, (
        run.report()
    )


@pytest.mark.parametrize("download", DOWNLOADS)
async def test_cp_download_ignores_grants_even_malformed(
    aws_cli: str, tmp_path: Path, download: Download
) -> None:
    """Only an upload maps --grants (utils.py:487-505), so a download
    neither sends nor checks them."""
    run = await run_cp(
        aws_cli,
        tmp_path,
        (*download.arguments, "--grants", "read=id=reader", "everyone"),
        InMemoryS3(DOWNLOAD_OBJECTS),
    )
    assert_downloaded(run, download)
    assert {members for _, members in sent_settings(run)} == {"[]"}, (
        run.report()
    )


# The customer key settings upstream refuses unless both are given
# (customizations/s3/subcommands.py:2018-2033), before any request.
SSE_C_REFUSALS: Final = [
    pytest.param(
        ("--sse-c",),
        "If --sse-c is specified, --sse-c-key must be specified as well.",
        id="algorithm-alone",
    ),
    pytest.param(
        ("--sse-c", "AES256", "--sse-c-key", ""),
        "If --sse-c is specified, --sse-c-key must be specified as well.",
        id="empty-key",
    ),
    pytest.param(
        ("--sse-c-key", TEXT_KEY),
        "If --sse-c-key is specified, --sse-c must be specified as well.",
        id="key-alone",
    ),
]
REFUSED_SHAPES: Final = [
    pytest.param(
        ("small.txt", f"s3://{BUCKET}/up/small.txt"), id="upload"
    ),
    pytest.param(
        ("tree", f"s3://{BUCKET}/up/", "--recursive"), id="recursive-upload"
    ),
    pytest.param(
        (f"s3://{BUCKET}/down/small.txt", "small.txt"), id="download"
    ),
    pytest.param(
        (f"s3://{BUCKET}/down/", "down", "--recursive"),
        id="recursive-download",
    ),
    pytest.param(
        ("small.txt", f"s3://{BUCKET}/up/small.txt", "--dryrun"),
        id="dryrun",
    ),
]


@pytest.mark.parametrize("arguments", REFUSED_SHAPES)
@pytest.mark.parametrize(("flags", "message"), SSE_C_REFUSALS)
async def test_cp_refuses_one_customer_key_setting_without_the_other(
    aws_cli: str,
    tmp_path: Path,
    arguments: tuple[str, ...],
    flags: tuple[str, ...],
    message: str,
) -> None:
    store = InMemoryS3(DOWNLOAD_OBJECTS)
    run = await run_cp(
        aws_cli,
        tmp_path,
        (*arguments, *flags),
        store,
        local_files={"small.txt": SMALL, "tree/small.txt": SMALL},
    )
    report = run.report()
    assert (run.returncode, run.stdout, run.stderr) == (
        252,
        "",
        f"\naws: [ERROR]: An error occurred (ParamValidation): {message}\n",
    ), report
    assert store.received == [], report


async def test_cp_reports_a_missing_source_before_the_customer_key(
    aws_cli: str, tmp_path: Path
) -> None:
    store = InMemoryS3()
    run = await run_cp(
        aws_cli,
        tmp_path,
        ("missing.txt", f"s3://{BUCKET}/up/missing.txt", "--sse-c"),
        store,
    )
    report = run.report()
    assert (run.returncode, run.stdout, run.stderr) == (
        255,
        "",
        "\naws: [ERROR]: The user-provided path missing.txt does not "
        "exist.\n",
    ), report
    assert store.received == [], report
