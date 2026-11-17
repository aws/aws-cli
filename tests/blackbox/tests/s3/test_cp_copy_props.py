"""What `s3 cp --copy-props` copies from an S3 source object (upstream
tests/functional/s3/test_cp_command.py, TestCopyPropsNoneCpCommand,
TestCopyPropsMetadataDirectiveCpCommand, TestCopyPropsDefaultCpCommand,
and TestCopyPropsAllCpCommand).

A single-part copy is one CopyObject, which copies the source's metadata
and tags server-side unless its directives say otherwise. A multipart
copy creates a new upload, so the command reads what it carries over:
the metadata from a HeadObject, the tags from GetObjectTagging (put on the
new object afterwards when they do not fit a header), and with `all` the
annotations, each read and written again. Arguments that set metadata
replace what is copied, and --metadata-directive turns copy-props off.
Copies run on the classic client whichever client is preferred.

Upstream compares the operations it asserts with the parameters botocore
is given; these compare every request with what the wire carries, where
botocore has also asked for URL-encoded listings and named the checksum
PutObjectTagging requires.
"""

import base64
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

import awscrt.checksums
import pytest

from apihelpers import ApiSession, Reply, ReplyLike
from s3params import (
    Request,
    access_denied_error_response,
    complete_mpu_request,
    copy_object_request,
    create_mpu_request,
    create_mpu_response,
    delete_object_request,
    get_object_annotation_request,
    get_object_annotation_response,
    get_object_tagging_request,
    get_object_tagging_response,
    head_object_request,
    head_object_response,
    list_object_annotations_request,
    list_object_annotations_response,
    list_objects_request,
    list_objects_response,
    mp_copy_responses,
    no_such_key_error_response,
    put_object_annotation_request,
    put_object_tagging_request,
    upload_part_copy_request,
    upload_part_copy_response,
)

pytestmark = pytest.mark.asyncio

MB: Final = 1024**2
MULTIPART_THRESHOLD: Final = 8 * MB
SOURCE_BUCKET: Final = "source-bucket"
SOURCE_KEY: Final = "source-key"
TARGET_BUCKET: Final = "target-bucket"
TARGET_KEY: Final = "target-key"
TAGS: Final = {"tag-key": "tag-value", "tag-key2": "tag-value2"}
URLENCODED_TAGS: Final = "tag-key=tag-value&tag-key2=tag-value2"
TAGS_OVER_2K: Final = {"tag-key": "value" * (2 * 1024)}
EXPIRES: Final = "Tue, 07 Jan 2020 20:40:03 GMT"
# The metadata a HeadObject reports and a copy that replaces it sends.
METADATA_PROPS: Final[dict[str, Any]] = {
    "CacheControl": "cache-control",
    "ContentDisposition": "content-disposition",
    "ContentEncoding": "content-encoding",
    "ContentLanguage": "content-language",
    "ContentType": "content-type",
    "Expires": EXPIRES,
    "Metadata": {"key": "value"},
}
# The same as a request carries it: awswire parses the Expires header.
SENT_PROPS: Final[dict[str, Any]] = {
    **METADATA_PROPS,
    "Expires": datetime(2020, 1, 7, 20, 40, 3, tzinfo=UTC),
}
PAYER: Final = {"RequestPayer": "requester"}


def crc64nvme(body: bytes) -> str:
    digest = awscrt.checksums.crc64nvme(body).to_bytes(8, byteorder="big")
    return base64.b64encode(digest).decode()


@dataclass(frozen=True)
class Case:
    """One copy: the arguments after `s3 cp`, the replies in order, and
    the requests the wire must show."""

    args: Sequence[str]
    replies: Sequence[ReplyLike]
    expected: Sequence[Request]


def single(copy_props: str | None, *extra: str) -> list[str]:
    args = [
        f"s3://{SOURCE_BUCKET}/{SOURCE_KEY}",
        f"s3://{TARGET_BUCKET}/{TARGET_KEY}",
    ]
    if copy_props is not None:
        args += ["--copy-props", copy_props]
    return [*args, *extra]


def recursive(copy_props: str, *extra: str) -> list[str]:
    return [
        f"s3://{SOURCE_BUCKET}/",
        f"s3://{TARGET_BUCKET}/",
        "--recursive",
        "--copy-props",
        copy_props,
        *extra,
    ]


def source_head(**override: Any) -> Request:
    """The HeadObject a single copy sends for the source's size."""
    return head_object_request(
        SOURCE_BUCKET, SOURCE_KEY, ChecksumMode="ENABLED", **override
    )


def props_head(**override: Any) -> Request:
    """The HeadObject a recursive copy sends for the source's metadata."""
    return head_object_request(SOURCE_BUCKET, SOURCE_KEY, **override)


def listing() -> Request:
    return list_objects_request(SOURCE_BUCKET, EncodingType="url")


def copy(key: str = TARGET_KEY, **override: Any) -> Request:
    return copy_object_request(
        SOURCE_BUCKET, SOURCE_KEY, TARGET_BUCKET, key, **override
    )


def directive_copy(directive: str) -> Request:
    """A CopyObject that --metadata-directive left to itself."""
    return (
        "CopyObject",
        {
            "Bucket": TARGET_BUCKET,
            "Key": TARGET_KEY,
            "CopySource": {"Bucket": SOURCE_BUCKET, "Key": SOURCE_KEY},
            "MetadataDirective": directive,
        },
    )


def mp_copy(
    key: str = TARGET_KEY,
    payer: dict[str, str] | None = None,
    **create: Any,
) -> list[Request]:
    """A one-part multipart copy of the 8 MiB source onto `key`."""
    extra = payer or {}
    return [
        create_mpu_request(TARGET_BUCKET, key, **extra, **create),
        upload_part_copy_request(
            SOURCE_BUCKET,
            SOURCE_KEY,
            TARGET_BUCKET,
            key,
            "upload_id",
            PartNumber=1,
            CopySourceRange="bytes=0-8388607",
            CopySourceIfMatch='"foo-1"',
            **extra,
        ),
        complete_mpu_request(TARGET_BUCKET, key, "upload_id", 1, **extra),
    ]


def get_tagging(payer: dict[str, str] | None = None) -> Request:
    operation, params = get_object_tagging_request(SOURCE_BUCKET, SOURCE_KEY)
    return operation, {**params, **(payer or {})}


def put_tagging(
    key: str = TARGET_KEY, payer: dict[str, str] | None = None
) -> Request:
    operation, params = put_object_tagging_request(
        TARGET_BUCKET, key, TAGS_OVER_2K
    )
    return operation, {
        **params,
        "ChecksumAlgorithm": "CRC64NVME",
        **(payer or {}),
    }


def big_head(**override: Any) -> dict[str, Any]:
    return head_object_response(ContentLength=MULTIPART_THRESHOLD, **override)


def big_listing() -> dict[str, Any]:
    return list_objects_response([SOURCE_KEY], Size=MULTIPART_THRESHOLD)


def head_failure() -> Reply:
    # A HEAD response has no body, so botocore names the error by its
    # status: the wire cannot carry upstream's parsed NoSuchKey.
    return Reply(no_such_key_error_response(), status=404)


SINGLE_PART: Final = [
    pytest.param(
        Case(
            single("none"),
            [head_object_response(), {}],
            [
                source_head(),
                copy(MetadataDirective="REPLACE", TaggingDirective="REPLACE"),
            ],
        ),
        id="none-copy-object",
    ),
    pytest.param(
        Case(
            single("none", "--metadata-directive", "COPY"),
            [head_object_response(), {}],
            [source_head(), directive_copy("COPY")],
        ),
        id="none-metadata-directive-disables-copy-props",
    ),
    pytest.param(
        Case(
            single("metadata-directive"),
            [head_object_response(), {}],
            [source_head(), copy(TaggingDirective="REPLACE")],
        ),
        id="metadata-directive-copy-object",
    ),
    pytest.param(
        Case(
            single(
                "metadata-directive",
                "--content-type",
                "content-type-from-cmdline",
            ),
            [head_object_response(**METADATA_PROPS), {}],
            [
                source_head(),
                copy(
                    **{
                        **SENT_PROPS,
                        "ContentType": "content-type-from-cmdline",
                    },
                    MetadataDirective="REPLACE",
                    TaggingDirective="REPLACE",
                ),
            ],
        ),
        id="metadata-directive-copy-object-overrides-with-cmdline-props",
    ),
    pytest.param(
        Case(
            single("metadata-directive", "--metadata-directive", "REPLACE"),
            [head_object_response(), {}],
            [source_head(), directive_copy("REPLACE")],
        ),
        id="metadata-directive-metadata-directive-disables-copy-props",
    ),
    pytest.param(
        Case(
            single("default"),
            [head_object_response(), {}],
            [source_head(), copy()],
        ),
        id="default-copy-object",
    ),
    pytest.param(
        Case(
            single(None),
            [head_object_response(), {}],
            [source_head(), copy()],
        ),
        id="default-is-default-value",
    ),
    pytest.param(
        Case(
            single(
                "default",
                "--content-language",
                "content-lang-from-cmdline",
            ),
            [head_object_response(**METADATA_PROPS), {}],
            [
                source_head(),
                copy(
                    **{
                        **SENT_PROPS,
                        "ContentLanguage": "content-lang-from-cmdline",
                    },
                    MetadataDirective="REPLACE",
                ),
            ],
        ),
        id="default-copy-object-with-prop-overrides",
    ),
    pytest.param(
        Case(
            single("default", "--metadata-directive", "REPLACE"),
            [head_object_response(), {}],
            [source_head(), directive_copy("REPLACE")],
        ),
        id="default-metadata-directive-disables-copy-props",
    ),
    # A single-part copy keeps the annotations server-side through the
    # AnnotationDirective's default, COPY, so `all` sets none.
    pytest.param(
        Case(
            single("all"),
            [head_object_response(), {}],
            [
                source_head(),
                (
                    "CopyObject",
                    {
                        "Bucket": TARGET_BUCKET,
                        "Key": TARGET_KEY,
                        "CopySource": {
                            "Bucket": SOURCE_BUCKET,
                            "Key": SOURCE_KEY,
                        },
                    },
                ),
            ],
        ),
        id="all-copy-object-excludes-nothing-for-single-part",
    ),
]

# A recursive copy has the listing's size and ETag, so it reads the
# source's metadata only when it must send it.
RECURSIVE_SINGLE_PART: Final = [
    pytest.param(
        Case(
            recursive("metadata-directive"),
            [list_objects_response([SOURCE_KEY]), {}],
            [listing(), copy(SOURCE_KEY, TaggingDirective="REPLACE")],
        ),
        id="metadata-directive-recursive-copy-object",
    ),
    pytest.param(
        Case(
            recursive(
                "metadata-directive", "--metadata", "key=val-from-cmdline"
            ),
            [
                list_objects_response([SOURCE_KEY]),
                head_object_response(**METADATA_PROPS),
                {},
            ],
            [
                listing(),
                props_head(),
                copy(
                    SOURCE_KEY,
                    **{**SENT_PROPS, "Metadata": {"key": "val-from-cmdline"}},
                    MetadataDirective="REPLACE",
                    TaggingDirective="REPLACE",
                ),
            ],
        ),
        id="metadata-directive-recursive-copy-overrides-with-cmdline-props",
    ),
    pytest.param(
        Case(
            recursive(
                "metadata-directive",
                "--metadata",
                "key=val-from-cmdline",
                "--request-payer",
                "requester",
            ),
            [list_objects_response([SOURCE_KEY]), head_object_response(), {}],
            [
                (listing()[0], {**listing()[1], **PAYER}),
                props_head(**PAYER),
                copy(
                    SOURCE_KEY,
                    Metadata={"key": "val-from-cmdline"},
                    MetadataDirective="REPLACE",
                    TaggingDirective="REPLACE",
                    **PAYER,
                ),
            ],
        ),
        id="metadata-directive-recursive-copy-maps-additional-head-headers",
    ),
    # Upstream also queues a HeadObject reply this copy never asks for.
    pytest.param(
        Case(
            recursive("default"),
            [list_objects_response([SOURCE_KEY]), {}],
            [listing(), copy(SOURCE_KEY)],
        ),
        id="default-recursive-copy-object",
    ),
    pytest.param(
        Case(
            recursive(
                "default",
                "--content-language",
                "content-lang-from-cmdline",
            ),
            [
                list_objects_response([SOURCE_KEY]),
                head_object_response(**METADATA_PROPS),
                {},
            ],
            [
                listing(),
                props_head(),
                copy(
                    SOURCE_KEY,
                    **{
                        **SENT_PROPS,
                        "ContentLanguage": "content-lang-from-cmdline",
                    },
                    MetadataDirective="REPLACE",
                ),
            ],
        ),
        id="default-recursive-copy-object-with-prop-overrides",
    ),
]

MULTIPART: Final = [
    pytest.param(
        Case(
            single("none"),
            [big_head(), *mp_copy_responses()],
            [source_head(), *mp_copy()],
        ),
        id="none-mp-copy-object",
    ),
    pytest.param(
        Case(
            single("metadata-directive"),
            [big_head(**METADATA_PROPS), *mp_copy_responses()],
            [source_head(), *mp_copy(**SENT_PROPS)],
        ),
        id="metadata-directive-mp-copy-object",
    ),
    pytest.param(
        Case(
            single(
                "metadata-directive",
                "--content-type",
                "content-type-from-cmdline",
            ),
            [big_head(**METADATA_PROPS), *mp_copy_responses()],
            [
                source_head(),
                *mp_copy(
                    **{
                        **SENT_PROPS,
                        "ContentType": "content-type-from-cmdline",
                    }
                ),
            ],
        ),
        id="metadata-directive-mp-copy-object-with-prop-overrides",
    ),
    pytest.param(
        Case(
            recursive("metadata-directive"),
            [
                big_listing(),
                head_object_response(**METADATA_PROPS),
                *mp_copy_responses(),
            ],
            [listing(), props_head(), *mp_copy(SOURCE_KEY, **SENT_PROPS)],
        ),
        id="metadata-directive-recursive-mp-copy",
    ),
    pytest.param(
        Case(
            recursive(
                "metadata-directive",
                "--content-type",
                "content-type-from-cmdline",
            ),
            [
                big_listing(),
                head_object_response(**METADATA_PROPS),
                *mp_copy_responses(),
            ],
            [
                listing(),
                props_head(),
                *mp_copy(
                    SOURCE_KEY,
                    **{
                        **SENT_PROPS,
                        "ContentType": "content-type-from-cmdline",
                    },
                ),
            ],
        ),
        id="metadata-directive-recursive-mp-copy-object-with-prop-overrides",
    ),
    pytest.param(
        Case(
            recursive(
                "metadata-directive", "--request-payer", "requester"
            ),
            [big_listing(), head_object_response(), *mp_copy_responses()],
            [
                (listing()[0], {**listing()[1], **PAYER}),
                props_head(**PAYER),
                *mp_copy(SOURCE_KEY, payer=PAYER),
            ],
        ),
        id="metadata-directive-recursive-mp-copy-maps-additional-head-headers",
    ),
    pytest.param(
        Case(
            single("default"),
            [
                big_head(**METADATA_PROPS),
                get_object_tagging_response(TAGS),
                *mp_copy_responses(),
            ],
            [
                source_head(),
                get_tagging(),
                *mp_copy(**SENT_PROPS, Tagging=URLENCODED_TAGS),
            ],
        ),
        id="default-mp-copy-object",
    ),
    pytest.param(
        Case(
            single(
                "default", "--cache-control", "cache-control-from-cmdline"
            ),
            [
                big_head(**METADATA_PROPS),
                get_object_tagging_response(TAGS),
                *mp_copy_responses(),
            ],
            [
                source_head(),
                get_tagging(),
                *mp_copy(
                    **{
                        **SENT_PROPS,
                        "CacheControl": "cache-control-from-cmdline",
                    },
                    Tagging=URLENCODED_TAGS,
                ),
            ],
        ),
        id="default-mp-copy-object-with-prop-overrides",
    ),
    pytest.param(
        Case(
            single("default"),
            [
                big_head(),
                get_object_tagging_response({}),
                *mp_copy_responses(),
            ],
            [source_head(), get_tagging(), *mp_copy()],
        ),
        id="default-mp-copy-object-no-tags",
    ),
    pytest.param(
        Case(
            single("default"),
            [
                big_head(),
                get_object_tagging_response(TAGS_OVER_2K),
                *mp_copy_responses(),
                {},
            ],
            [source_head(), get_tagging(), *mp_copy(), put_tagging()],
        ),
        id="default-mp-copy-object-tags-exceed-2k",
    ),
    pytest.param(
        Case(
            recursive("default"),
            [
                big_listing(),
                head_object_response(**METADATA_PROPS),
                get_object_tagging_response(TAGS),
                *mp_copy_responses(),
            ],
            [
                listing(),
                props_head(),
                get_tagging(),
                *mp_copy(SOURCE_KEY, **SENT_PROPS, Tagging=URLENCODED_TAGS),
            ],
        ),
        id="default-recursive-mp-copy-object",
    ),
    pytest.param(
        Case(
            recursive(
                "default", "--cache-control", "cache-control-from-cmdline"
            ),
            [
                big_listing(),
                head_object_response(**METADATA_PROPS),
                get_object_tagging_response(TAGS),
                *mp_copy_responses(),
            ],
            [
                listing(),
                props_head(),
                get_tagging(),
                *mp_copy(
                    SOURCE_KEY,
                    **{
                        **SENT_PROPS,
                        "CacheControl": "cache-control-from-cmdline",
                    },
                    Tagging=URLENCODED_TAGS,
                ),
            ],
        ),
        id="default-recursive-mp-copy-object-with-prop-overrides",
    ),
    pytest.param(
        Case(
            recursive("default"),
            [
                big_listing(),
                head_object_response(),
                get_object_tagging_response(TAGS_OVER_2K),
                *mp_copy_responses(),
                {},
            ],
            [
                listing(),
                props_head(),
                get_tagging(),
                *mp_copy(SOURCE_KEY),
                put_tagging(SOURCE_KEY),
            ],
        ),
        id="default-recursive-mp-copy-tags-exceed-2k",
    ),
]


@pytest.mark.parametrize("case", SINGLE_PART + RECURSIVE_SINGLE_PART)
async def test_copy_object(s3api: ApiSession, case: Case) -> None:
    run = await s3api.run(["s3", "cp", *case.args], replies=case.replies)
    assert run.operations_with_params == list(case.expected), run.describe()


@pytest.mark.parametrize("case", MULTIPART)
async def test_mp_copy_object(s3api: ApiSession, case: Case) -> None:
    run = await s3api.run(["s3", "cp", *case.args], replies=case.replies)
    assert run.operations_with_params == list(case.expected), run.describe()


# Each failure is an error response that is not retried, so the error
# tests drop the base environment's single attempt, as upstream's run has
# none: with it botocore notes the exhausted attempts in the message.
FAILURES: Final = [
    pytest.param(
        Case(
            recursive("metadata-directive"),
            [big_listing(), head_failure()],
            [listing(), props_head()],
        ),
        "An error occurred (404) when calling the HeadObject operation: "
        "Not Found",
        id="metadata-directive-fails-when-head-object-fails",
    ),
    pytest.param(
        Case(
            recursive("default"),
            [big_listing(), head_failure()],
            [listing(), props_head()],
        ),
        "An error occurred (404) when calling the HeadObject operation: "
        "Not Found",
        id="default-fails-when-head-object-fails",
    ),
    pytest.param(
        Case(
            single("default"),
            [big_head(), Reply(access_denied_error_response(), status=403)],
            [source_head(), get_tagging()],
        ),
        "An error occurred (AccessDenied) when calling the GetObjectTagging "
        "operation: Operation not allowed",
        id="default-fails-when-get-tagging-object-fails",
    ),
    # The new object's tags failing, the copy deletes the new object.
    pytest.param(
        Case(
            single("default"),
            [
                big_head(),
                get_object_tagging_response(TAGS_OVER_2K),
                *mp_copy_responses(),
                Reply(access_denied_error_response(), status=403),
                {},
            ],
            [
                source_head(),
                get_tagging(),
                *mp_copy(),
                put_tagging(),
                delete_object_request(TARGET_BUCKET, TARGET_KEY),
            ],
        ),
        "An error occurred (AccessDenied) when calling the PutObjectTagging "
        "operation: Operation not allowed",
        id="default-fails-and-cleans-up-when-put-tagging-object-fails",
    ),
    pytest.param(
        Case(
            single("default", "--request-payer", "requester"),
            [
                big_head(),
                get_object_tagging_response(TAGS_OVER_2K),
                *mp_copy_responses(),
                Reply(access_denied_error_response(), status=403),
                {},
            ],
            [
                source_head(**PAYER),
                get_tagging(PAYER),
                *mp_copy(payer=PAYER),
                put_tagging(payer=PAYER),
                delete_object_request(TARGET_BUCKET, TARGET_KEY, **PAYER),
            ],
        ),
        "An error occurred (AccessDenied) when calling the PutObjectTagging "
        "operation: Operation not allowed",
        id="default-clean-up-uses-requester-payer",
    ),
]


@pytest.mark.parametrize(("case", "error"), FAILURES)
async def test_copy_fails(s3api: ApiSession, case: Case, error: str) -> None:
    del s3api.env["AWS_MAX_ATTEMPTS"]
    run = await s3api.run(
        ["s3", "cp", *case.args], replies=case.replies, expected_rc=1
    )
    assert error in run.stderr, run.describe()
    assert run.operations_with_params == list(case.expected), run.describe()


DEST_ETAG: Final = '"dest-etag"'
DEST_VERSION_ID: Final = "dest-version-id"
PAYLOAD: Final = b"annotation-payload"


def mp_copy_responses_with_dest_identity() -> list[dict[str, Any]]:
    return [
        create_mpu_response("upload_id"),
        upload_part_copy_response(),
        {"ETag": DEST_ETAG, "VersionId": DEST_VERSION_ID},
    ]


def annotations_read(
    names: Sequence[str], **version: str
) -> list[Request]:
    """The source's annotation listing and reads; botocore enables each
    read's checksum mode after upstream's capture."""
    return [
        list_object_annotations_request(SOURCE_BUCKET, SOURCE_KEY, **version),
        *[
            get_object_annotation_request(
                SOURCE_BUCKET,
                SOURCE_KEY,
                name,
                ChecksumMode="ENABLED",
                **version,
            )
            for name in names
        ],
    ]


def annotation_written(name: str) -> Request:
    """An annotation put on the new object, conditioned on its identity,
    with the payload's checksum botocore adds after upstream's capture."""
    return put_object_annotation_request(
        TARGET_BUCKET,
        TARGET_KEY,
        name,
        PAYLOAD,
        ObjectIfMatch=DEST_ETAG,
        VersionId=DEST_VERSION_ID,
        ChecksumAlgorithm="CRC64NVME",
        ChecksumCRC64NVME=crc64nvme(PAYLOAD),
    )


@pytest.mark.parametrize(
    ("version", "names"),
    [
        pytest.param({}, ["ann1", "ann2"], id="copies-annotations"),
        # The source's annotations are read at the version copied.
        pytest.param(
            {"VersionId": "src-version-id"},
            ["ann1"],
            id="copies-annotations-with-source-version-id",
        ),
    ],
)
async def test_all_mp_copy_object(
    s3api: ApiSession, version: dict[str, str], names: list[str]
) -> None:
    run = await s3api.run(
        ["s3", "cp", *single("all")],
        replies=[
            big_head(**version),
            get_object_tagging_response(TAGS),
            list_object_annotations_response(names),
            *[get_object_annotation_response(PAYLOAD) for _ in names],
            *mp_copy_responses_with_dest_identity(),
            *[{} for _ in names],
        ],
    )
    assert run.operations_with_params == [
        source_head(),
        get_tagging(),
        *annotations_read(names, **version),
        *mp_copy(Tagging=URLENCODED_TAGS),
        *[annotation_written(name) for name in names],
    ], run.describe()


async def test_all_mp_copy_object_no_annotations(s3api: ApiSession) -> None:
    run = await s3api.run(
        ["s3", "cp", *single("all")],
        replies=[
            big_head(),
            get_object_tagging_response({}),
            list_object_annotations_response([]),
            *mp_copy_responses(),
        ],
    )
    assert run.operations_with_params == [
        source_head(),
        get_tagging(),
        *annotations_read([]),
        *mp_copy(),
    ], run.describe()


async def test_all_mp_copy_object_partial_annotation_failure(
    s3api: ApiSession,
) -> None:
    # One attempt, as test_copy_fails has it.
    del s3api.env["AWS_MAX_ATTEMPTS"]
    names = ["ann1", "ann2"]
    run = await s3api.run(
        ["s3", "cp", *single("all")],
        replies=[
            big_head(),
            get_object_tagging_response({}),
            list_object_annotations_response(names),
            *[get_object_annotation_response(PAYLOAD) for _ in names],
            *mp_copy_responses_with_dest_identity(),
            {},
            Reply(access_denied_error_response(), status=403),
        ],
        expected_rc=1,
    )
    # The new object stays: no DeleteObject follows the failure.
    assert run.operations_with_params == [
        source_head(),
        get_tagging(),
        *annotations_read(names),
        *mp_copy(),
        *[annotation_written(name) for name in names],
    ], run.describe()
    assert "ann1" in run.stderr, run.describe()
    assert "ann2" in run.stderr, run.describe()
