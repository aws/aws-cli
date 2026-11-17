"""An in-memory S3 bucket store for the S3 transfer blackbox tests.

`InMemoryS3` answers the calls `s3 cp`, `s3 ls`, and `s3 rm` make from an
object map, parsing each request and serializing each response with the
botocore S3 model (tests/awswire.py), so its answers are well-formed for any
request shape a client sends: path or virtual-hosted addressing, aws-chunked
bodies, checksum trailers. Serve it behind the TLS intercept proxy with
`s3_runtime`, the same way the other blackbox tests reach S3.
`ScriptedS3` adds scripted 500s, cut response bodies, and stored
checksums.
"""

import functools
import hashlib
import os
import traceback
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final
from urllib.parse import quote

from localstub import (
    AsyncHTTPTestServer,
    DropConnection,
    FaultyTransmission,
    HTTPResponse,
    ResponderContext,
)
from localstub.handlers import handle_expect_header
from localstub.server import AbortTransmission, TransmissionStrategy, Writer

from awswire import (
    AwsWireProtocol,
    ReconstructedRequest,
    create_aws_wire_protocol,
)
from credhelpers import credential_env
from tests.blackbox.utils import mock_server

LAST_MODIFIED: Final = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
MULTIPART_OPERATIONS: Final = frozenset(
    {
        "CreateMultipartUpload",
        "UploadPart",
        "CompleteMultipartUpload",
        "AbortMultipartUpload",
    }
)
# The request ids S3 answers every request with. The CRT client records a
# response's status with its headers, so it rejects a 204 that has none.
REQUEST_IDS: Final = {
    "x-amz-request-id": "REQUESTID",
    "x-amz-id-2": "HOSTID",
}
# botocore's 500 error, which every client retries.
INTERNAL_ERROR: Final = {
    "Error": {
        "Code": "InternalError",
        "Message": "We encountered an internal error. Please try again.",
    }
}

ObjectKey = tuple[str, str]


def pattern_bytes(label: str, size: int) -> bytes:
    """`size` bytes of a repeated line naming `label`."""
    unit = f"{label} payload\n".encode()
    return (unit * (size // len(unit) + 1))[:size]


def etag_of(body: bytes) -> str:
    return f'"{hashlib.md5(body, usedforsecurity=False).hexdigest()}"'


def write_tree(root: Path, files: Mapping[str, bytes]) -> None:
    for relative, body in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)


def read_tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def decoded(stream: bytes) -> str:
    """Lossless text, so distinct bytes never compare equal."""
    return stream.decode("utf-8", errors="surrogateescape")


def parse_byte_range(value: str, length: int) -> tuple[int, int]:
    unit, _, span = value.partition("=")
    start_text, separator, end_text = span.partition("-")
    if unit.strip().lower() != "bytes" or not separator or not start_text:
        raise ValueError(f"unsupported Range header: {value}")
    start = int(start_text)
    end = min(int(end_text), length - 1) if end_text else length - 1
    if start > end:
        raise ValueError(f"unsatisfiable Range header: {value}")
    return start, end


@functools.cache
def s3_wire_protocol() -> AwsWireProtocol:
    """The S3-only protocol every store shares.

    A store answers only S3, which it names to `reconstruct`, so it loads
    no other model, and it loads S3's once: parsing the model costs more
    than most of the commands a test runs. The protocol holds no state
    past its models, so stores in any test can share it.
    """
    return create_aws_wire_protocol(("s3",))


class InMemoryS3:
    """Answers PutObject, HeadObject, GetObject, ListObjectsV2 by pages,
    DeleteObject, and multipart uploads.

    `storage` gives a key its storage class and, optionally, the HeadObject
    Restore value; unlisted keys are STANDARD. `last_modified` gives an
    object its LastModified, which is otherwise LAST_MODIFIED, the time
    every write stamps too. Every PutObject and
    DeleteObject in a `denied_buckets` bucket is refused with AccessDenied,
    and a PutObject with `If-None-Match: *` of a key the store holds with
    PreconditionFailed, as S3 refuses it. A request the store cannot answer,
    including an operation it does not model, gets a 500 and is recorded in
    `failures`, so the test can fail on it. Every request it parsed is kept
    in `received`, in arrival order.
    """

    def __init__(
        self,
        objects: Mapping[ObjectKey, bytes] | None = None,
        *,
        storage: Mapping[str, tuple[str, str | None]] | None = None,
        last_modified: Mapping[ObjectKey, datetime] | None = None,
        denied_buckets: frozenset[str] = frozenset(),
        protocol: AwsWireProtocol | None = None,
    ) -> None:
        self.protocol = protocol or s3_wire_protocol()
        self.objects: dict[ObjectKey, bytes] = dict(objects or {})
        self.storage = dict(storage or {})
        self.last_modified = dict(last_modified or {})
        self.denied_buckets = denied_buckets
        self.failures: list[str] = []
        # (operation, status) of every answered request, in order.
        self.responses: list[tuple[str, int]] = []
        self.received: list[ReconstructedRequest] = []
        # The parts of each multipart upload in progress, by upload id.
        self.uploads: dict[str, dict[int, bytes]] = {}
        self._started_uploads = 0
        # Each object's ETag with the body it was computed from: every
        # ranged GET of a large object names it, and hashing the whole
        # body for each one stalls the transfer.
        self._etags: dict[ObjectKey, tuple[bytes, str]] = {}

    def etag(self, key: ObjectKey, body: bytes) -> str:
        """The ETag of `body`, stored under `key`."""
        cached = self._etags.get(key)
        if cached is not None and cached[0] is body:
            return cached[1]
        etag = etag_of(body)
        self._etags[key] = (body, etag)
        return etag

    def operations(self) -> list[str]:
        return [name for name, _ in self.responses]

    def modified(self, key: ObjectKey) -> datetime:
        """The LastModified of the object at `key`."""
        return self.last_modified.get(key, LAST_MODIFIED)

    def store(self, key: ObjectKey, body: bytes) -> None:
        """Write `body` to `key`, stamped LAST_MODIFIED."""
        self.objects[key] = body
        self.last_modified.pop(key, None)

    def storage_class(self, key: str) -> str:
        return self.storage.get(key, ("STANDARD", None))[0]

    def listed_checksum(self, key: ObjectKey) -> dict[str, Any]:
        """What a listing names of the object's checksum: none stored."""
        return {}

    def readable(self, key: str) -> bool:
        """Whether a GET succeeds: not archived, or restored."""
        storage_class, restore = self.storage.get(key, ("STANDARD", None))
        return storage_class not in {"GLACIER", "DEEP_ARCHIVE"} or (
            'ongoing-request="false"' in (restore or "")
        )

    async def respond(self, context: ResponderContext) -> HTTPResponse:
        request = context.request
        try:
            reconstructed = self.protocol.reconstruct(
                request, service_hint="s3"
            )
            self.received.append(reconstructed)
            response = self.dispatch(reconstructed)
        except Exception as error:
            self.failures.append(
                f"{request.method} {request.target}: "
                f"{type(error).__name__}: {error}\n"
                f"{traceback.format_exc()}"
            )
            return HTTPResponse.raw(
                b"the in-memory S3 store failed to answer the request",
                status=500,
                headers={"Content-Type": "text/plain"},
            )
        self.responses.append(
            (reconstructed.operation_model.name, response.status)
        )
        return response

    def dispatch(self, reconstructed: ReconstructedRequest) -> HTTPResponse:
        """Answer one parsed request from the object map.

        Subclasses override it to observe or script requests before the
        bucket answers them.
        """
        name = reconstructed.operation_model.name
        if name == "PutObject":
            return self._put_object(reconstructed)
        if name == "HeadObject":
            return self._head_object(reconstructed)
        if name == "GetObject":
            return self._get_object(reconstructed)
        if name == "ListObjectsV2":
            return self._list_objects_v2(reconstructed)
        if name == "DeleteObject":
            return self._delete_object(reconstructed)
        if name in MULTIPART_OPERATIONS:
            return self._multipart(reconstructed)
        raise NotImplementedError(f"unmodeled operation {name}")

    def serialize(
        self,
        reconstructed: ReconstructedRequest,
        parsed: Mapping[str, Any],
        *,
        status_code: int | None = None,
    ) -> HTTPResponse:
        return self.protocol.serialize_parsed_response(
            reconstructed.operation_model, parsed, status_code=status_code
        )

    def error(
        self,
        reconstructed: ReconstructedRequest,
        code: str,
        message: str,
        status_code: int,
    ) -> HTTPResponse:
        return self.serialize(
            reconstructed,
            {"Error": {"Code": code, "Message": message}},
            status_code=status_code,
        )

    def _key(self, reconstructed: ReconstructedRequest) -> ObjectKey:
        params = reconstructed.params
        return (params["Bucket"], params["Key"])

    def _lookup(self, reconstructed: ReconstructedRequest) -> bytes | None:
        return self.objects.get(self._key(reconstructed))

    def _put_object(self, reconstructed: ReconstructedRequest) -> HTTPResponse:
        params = reconstructed.params
        if params["Bucket"] in self.denied_buckets:
            return self.error(
                reconstructed, "AccessDenied", "Access Denied", 403
            )
        key = (params["Bucket"], params["Key"])
        if params.get("IfNoneMatch") == "*" and key in self.objects:
            return self.error(
                reconstructed,
                "PreconditionFailed",
                "At least one of the pre-conditions you specified did not "
                "hold",
                412,
            )
        body = params.get("Body", b"")
        if not isinstance(body, bytes):
            raise TypeError(f"PutObject body is {type(body).__name__}")
        self.store(key, body)
        return self.serialize(reconstructed, {"ETag": etag_of(body)})

    def _delete_object(
        self, reconstructed: ReconstructedRequest
    ) -> HTTPResponse:
        """S3 answers 204 whether or not the key exists."""
        params = reconstructed.params
        if params["Bucket"] in self.denied_buckets:
            return self.error(
                reconstructed, "AccessDenied", "Access Denied", 403
            )
        self.objects.pop((params["Bucket"], params["Key"]), None)
        return self.protocol.serialize_parsed_response(
            reconstructed.operation_model, {}, headers=REQUEST_IDS
        )

    def _multipart(self, reconstructed: ReconstructedRequest) -> HTTPResponse:
        """A multipart upload stores the joined parts when it completes."""
        params = reconstructed.params
        name = reconstructed.operation_model.name
        parsed: dict[str, Any] = {}
        if name == "CreateMultipartUpload":
            self._started_uploads += 1
            upload_id = f"upload-{self._started_uploads}"
            self.uploads[upload_id] = {}
            parsed = {
                "Bucket": params["Bucket"],
                "Key": params["Key"],
                "UploadId": upload_id,
            }
            for member in ("ChecksumAlgorithm", "ChecksumType"):
                if member in params:
                    parsed[member] = params[member]
        elif name == "UploadPart":
            body = params.get("Body", b"")
            if not isinstance(body, bytes):
                raise TypeError(f"UploadPart body is {type(body).__name__}")
            self.uploads[params["UploadId"]][params["PartNumber"]] = body
            parsed = {"ETag": etag_of(body)}
        elif name == "CompleteMultipartUpload":
            parts = self.uploads.pop(params["UploadId"])
            body = b"".join(parts[number] for number in sorted(parts))
            self.store((params["Bucket"], params["Key"]), body)
            parsed = {
                "Bucket": params["Bucket"],
                "Key": params["Key"],
                "ETag": etag_of(body),
            }
        else:
            self.uploads.pop(params["UploadId"], None)
        return self.serialize(reconstructed, parsed)

    def _head_object(
        self, reconstructed: ReconstructedRequest
    ) -> HTTPResponse:
        body = self._lookup(reconstructed)
        if body is None:
            # S3 answers a missing key's HEAD with a bare 404 and no body.
            return HTTPResponse.raw(b"", status=404)
        parsed: dict[str, Any] = {
            "ContentLength": len(body),
            "ContentType": "text/plain",
            "ETag": self.etag(self._key(reconstructed), body),
            "LastModified": self.modified(self._key(reconstructed)),
            "AcceptRanges": "bytes",
        }
        key = reconstructed.params["Key"]
        if key in self.storage:
            parsed["StorageClass"], restore = self.storage[key]
            if restore is not None:
                parsed["Restore"] = restore
        return self.serialize(reconstructed, parsed)

    def _get_object(self, reconstructed: ReconstructedRequest) -> HTTPResponse:
        body = self._lookup(reconstructed)
        if body is None:
            return self.error(
                reconstructed,
                "NoSuchKey",
                "The specified key does not exist.",
                404,
            )
        if not self.readable(reconstructed.params["Key"]):
            return self.error(
                reconstructed,
                "InvalidObjectState",
                "The operation is not valid for the object's storage class",
                403,
            )
        parsed: dict[str, Any] = {
            "ContentType": "text/plain",
            "ETag": self.etag(self._key(reconstructed), body),
            "LastModified": self.modified(self._key(reconstructed)),
            "AcceptRanges": "bytes",
        }
        params = reconstructed.params
        part_number = params.get("PartNumber")
        byte_range = params.get("Range")
        if part_number is not None:
            # Every object here was stored whole, so it has exactly one
            # part, answered as a range over the object.
            if part_number != 1 or byte_range is not None:
                return self.error(
                    reconstructed,
                    "InvalidPartNumber",
                    "The requested partnumber is not satisfiable",
                    416,
                )
            byte_range = "bytes=0-"
        if byte_range is None:
            parsed["Body"] = body
            return self.serialize(reconstructed, parsed)
        start, end = parse_byte_range(byte_range, len(body))
        parsed["Body"] = body[start : end + 1]
        parsed["ContentRange"] = f"bytes {start}-{end}/{len(body)}"
        return self.serialize(reconstructed, parsed, status_code=206)

    def _list_objects_v2(
        self, reconstructed: ReconstructedRequest
    ) -> HTTPResponse:
        """A page of at most MaxKeys keys and common prefixes, in key order.

        A truncated page's continuation token is its last key or common
        prefix, and the next page lists what follows it.
        """
        params = reconstructed.params
        bucket = params["Bucket"]
        prefix = params.get("Prefix", "")
        delimiter = params.get("Delimiter")
        url_encoded = params.get("EncodingType") == "url"
        max_keys = params.get("MaxKeys", 1000)
        after = params.get("ContinuationToken")

        def encoded(text: str) -> str:
            return quote(text, safe="/") if url_encoded else text

        # Each key or common prefix the listing names, with the object a
        # key names; a common prefix names none.
        entries: dict[str, bytes | None] = {}
        for (owner, key), body in self.objects.items():
            if owner != bucket or not key.startswith(prefix):
                continue
            rest = key[len(prefix) :]
            if delimiter and delimiter in rest:
                common = prefix + rest.split(delimiter, 1)[0] + delimiter
                entries[common] = None
            else:
                entries[key] = body
        names = sorted(
            name for name in entries if after is None or name > after
        )
        page = names[:max_keys]
        truncated = len(names) > len(page)
        contents = []
        prefixes: list[str] = []
        for name in page:
            body = entries[name]
            if body is None:
                prefixes.append(name)
                continue
            contents.append(
                {
                    "Key": encoded(name),
                    "Size": len(body),
                    "ETag": self.etag((bucket, name), body),
                    "LastModified": self.modified((bucket, name)),
                    "StorageClass": self.storage_class(name),
                    **self.listed_checksum((bucket, name)),
                }
            )
        parsed: dict[str, Any] = {
            "Name": bucket,
            "Prefix": encoded(prefix),
            "KeyCount": len(page),
            "MaxKeys": max_keys,
            "IsTruncated": truncated,
        }
        if contents:
            parsed["Contents"] = contents
        if prefixes:
            parsed["CommonPrefixes"] = [
                {"Prefix": encoded(common)} for common in prefixes
            ]
        if delimiter:
            parsed["Delimiter"] = delimiter
        if url_encoded:
            parsed["EncodingType"] = "url"
        if after is not None:
            parsed["ContinuationToken"] = after
        if truncated:
            parsed["NextContinuationToken"] = page[-1]
        return self.serialize(reconstructed, parsed)


class ScriptedS3(InMemoryS3):
    """InMemoryS3 that fails the first requests of chosen operations, cuts
    chosen response bodies, and names stored checksums.

    The first `failures` requests of any operation in `failing` get
    botocore's 500 InternalError. `cut` = (size, after, count) loses the
    connection after `after` bytes of the first `count` response bodies of
    exactly `size` bytes, once the server runs `ScriptedTransmission`; the
    body length is what singles out the scripted responses. `checksums`
    gives an object the full-object CRC64NVME a HeadObject or a GetObject
    without a Range answers with in checksum mode, as S3 does.
    """

    def __init__(
        self,
        objects: Mapping[ObjectKey, bytes] | None = None,
        *,
        failing: frozenset[str] = frozenset(),
        failures: int = 0,
        cut: tuple[int, int, int] | None = None,
        checksums: Mapping[ObjectKey, str] | None = None,
    ) -> None:
        super().__init__(objects)
        self.failing = failing
        self.failures_left = failures
        self.cut = cut
        self.cuts_left = cut[2] if cut is not None else 0
        self.checksums = dict(checksums or {})

    def dispatch(self, reconstructed: ReconstructedRequest) -> HTTPResponse:
        name = reconstructed.operation_model.name
        if name in self.failing and self.failures_left > 0:
            self.failures_left -= 1
            return self.serialize(
                reconstructed, INTERNAL_ERROR, status_code=500
            )
        response = super().dispatch(reconstructed)
        params = reconstructed.params
        mode = reconstructed.wire_request.headers.get("x-amz-checksum-mode")
        checksum = self.checksums.get(
            (params.get("Bucket", ""), params.get("Key", ""))
        )
        if (
            name in {"HeadObject", "GetObject"}
            and "Range" not in params
            and (mode or "").lower() == "enabled"
            and response.status < 300
            and checksum is not None
        ):
            headers = response.headers.patch_set(
                {
                    "x-amz-checksum-crc64nvme": checksum,
                    "x-amz-checksum-type": "FULL_OBJECT",
                }
            )
            response = replace(response, headers=headers)
        return response

    def listed_checksum(self, key: ObjectKey) -> dict[str, Any]:
        """What a listing names of an object's stored checksum: S3 lists its
        algorithm and type, never its value."""
        if key not in self.checksums:
            return super().listed_checksum(key)
        return {"ChecksumAlgorithm": ["CRC64NVME"], "ChecksumType": "FULL_OBJECT"}

    def failure_body_size(self, operation: str) -> int:
        """The size of the scripted 500's body for `operation`."""
        model = self.protocol.service_models["s3"].operation_model(operation)
        body = self.protocol.serialize_parsed_response(
            model, INTERNAL_ERROR, status_code=500
        ).body
        if not isinstance(body, bytes):
            raise TypeError(f"failure body is {type(body).__name__}")
        return len(body)

    def cut_after(self, body: bytes) -> int | None:
        """How many bytes of this body to send before closing, if any."""
        if self.cut is None or self.cuts_left == 0:
            return None
        size, after, _ = self.cut
        if len(body) != size:
            return None
        self.cuts_left -= 1
        return after


class ScriptedTransmission(TransmissionStrategy):
    """Writes each body whole unless `store` scripts a cut for it."""

    def __init__(self, store: ScriptedS3) -> None:
        self._store = store

    async def write_body(
        self, writer: Writer, body: bytes
    ) -> AbortTransmission | None:
        after = self._store.cut_after(body)
        if after is None:
            writer.write(body)
            await writer.drain()
            return None
        # The server closes the connection on the returned abort.
        return await FaultyTransmission([DropConnection(after)]).write_body(
            writer, body
        )


@asynccontextmanager
async def s3_runtime(
    store: InMemoryS3, tmp_path: Path
) -> AsyncIterator[tuple[AsyncHTTPTestServer, dict[str, str]]]:
    """`store` behind the TLS intercept proxy, and the command environment.

    The environment is the repo tests' (`credential_env`) with fixed keys,
    so the AWS CLI resolves `auto` to the CRT client; `run_command` adds
    the OS plumbing a Windows child needs to start. TZ is UTC: the
    AWS CLI lists LastModified in local time, and the tests expect the UTC
    time the store gives.
    """
    async with mock_server(handle_expect_header) as (server, proxy):
        server.handler = store.respond
        env = credential_env(proxy, tmp_path)
        env.update(
            AWS_ACCESS_KEY_ID="AKIDS3STORE",
            AWS_SECRET_ACCESS_KEY="s3store-secret",
            TZ="UTC",
        )
        yield server, env


def without_cwd(stream: bytes, cwd: Path) -> bytes:
    """`stream` with the working directory a line names replaced.

    A skipped source's warning names the source by its absolute path, which
    starts with the test's own directory.
    """
    return stream.replace(os.fsencode(os.path.realpath(cwd)), b"<cwd>")
