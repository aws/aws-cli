import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from xml.sax.saxutils import escape

import pytest
import pytest_asyncio
from localstub import (
    AsyncHTTPTestServer,
    HTTPResponse,
    RecordedHTTPRequest,
    ResponderContext,
)

from credhelpers import credential_env
from harness_plugin import child_environment
from s3helpers import (
    FAILING_STDERRS,
    FAILING_STDOUTS,
    assert_refused_before_request,
    failing_stream,
    run_cli_with_stdout,
    run_cli_with_streams,
    run_cli_without_stdout,
)
from tests.blackbox.utils import (
    error_response,
    list_objects_xml,
    mock_server,
    run_cli,
    xml_response,
)

# The indented `PRE` marker `s3 ls` prints before a common prefix.
DIRECTORY = " " * 27 + "PRE "
LATER_PAGE_TOKEN = "next/page+="
# The first page of `s3://bucket/prefix/`, one `prefix/key` of 17 bytes, as
# a flat and a recursive listing print it.
FIRST_OBJECT_PAGE_OUTPUT = [
    pytest.param([], "2026-01-02 03:04:05         17 key\n", id="flat"),
    pytest.param(
        ["--recursive"],
        "2026-01-02 03:04:05         17 prefix/key\n",
        id="recursive",
    ),
]
FIRST_BUCKET_PAGE_OUTPUT = "2026-01-02 03:04:05 project-a\n"


@pytest_asyncio.fixture
async def listing_runtime(
    tmp_path: Path,
) -> AsyncIterator[tuple[AsyncHTTPTestServer, dict[str, str]]]:
    async with mock_server() as (server, proxy):
        env = credential_env(proxy, tmp_path)
        env.update(
            AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test", TZ="UTC"
        )
        yield server, env


def object_page(
    objects: list[tuple[str, int]],
    *,
    prefixes: list[str] | None = None,
    token: str | None = None,
    encoded: bool = False,
) -> HTTPResponse:
    body = list_objects_xml(
        contents=[
            {
                "Key": escape(key),
                "Size": size,
                "LastModified": "2026-01-02T03:04:05Z",
            }
            for key, size in objects
        ],
        common_prefixes=[escape(p) for p in prefixes or []],
        is_truncated=token is not None,
        next_continuation_token=escape(token) if token is not None else None,
    )
    if encoded:
        body = body.replace(
            "</ListBucketResult>",
            "<EncodingType>url</EncodingType></ListBucketResult>",
        )
    return xml_response(body)


def bucket_page(names: list[str], token: str | None = None) -> HTTPResponse:
    buckets = "".join(
        f"<Bucket><Name>{escape(name)}</Name>"
        "<CreationDate>2026-01-02T03:04:05Z</CreationDate></Bucket>"
        for name in names
    )
    continuation = (
        f"<ContinuationToken>{escape(token)}</ContinuationToken>"
        if token is not None
        else ""
    )
    return xml_response(
        '<ListAllMyBucketsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f"<Buckets>{buckets}</Buckets>{continuation}</ListAllMyBucketsResult>"
    )


def serve_token_pages(
    server: AsyncHTTPTestServer, pages: list[list[tuple[str, int]]]
) -> None:
    first, middle, last = pages
    server.set_response_sequence(
        [
            object_page(first, token="next-1"),
            object_page(middle, token="next-2"),
            object_page(last),
        ]
    )


def continuation_tokens(
    server: AsyncHTTPTestServer,
) -> list[list[str] | None]:
    return [
        parse_qs(urlsplit(r.effective_path).query).get("continuation-token")
        for r in server.requests
    ]


def serve_first_object_page(server: AsyncHTTPTestServer) -> None:
    server.set_response_sequence(
        [object_page([("prefix/key", 17)], token=LATER_PAGE_TOKEN)]
    )


def serve_first_bucket_page(server: AsyncHTTPTestServer) -> None:
    server.set_response_sequence(
        [bucket_page(["project-a"], LATER_PAGE_TOKEN)]
    )


def rejected_page_error(operation: str, retries: int = 2) -> bytes:
    # botocore makes a 200 it cannot parse a 500, retries it, and reports
    # the 500 with the retries it ran out of.
    return (
        "\naws: [ERROR]: An error occurred (500) when calling the "
        f"{operation} operation (reached max retries: {retries}): "
        "Internal Server Error\n"
    ).encode()


def assert_unparsable_page_fails(
    result: tuple[bytes, bytes, int],
    server: AsyncHTTPTestServer,
    expected: str,
    operation: str = "ListObjectsV2",
) -> None:
    # The later page is requested three times from its token, then fails
    # as a 500. The earlier pages stay printed, nothing of the failed one
    # is, and no summary follows.
    stdout, stderr, rc = result
    assert (rc, stderr) == (254, rejected_page_error(operation))
    assert stdout.decode() == expected
    assert continuation_tokens(server) == [None] + [[LATER_PAGE_TOKEN]] * 3


def truncated_page(context: ResponderContext) -> HTTPResponse:
    # Every later page is a 200 whose document ends mid-element.
    return xml_response("<ListBucketResult><Contents>")


def assert_later_page_denied(
    result: tuple[bytes, bytes, int],
    server: AsyncHTTPTestServer,
    expected: str,
    operation: bytes,
) -> None:
    stdout, stderr, rc = result
    assert rc == 254, stderr.decode()
    assert stdout.decode() == expected
    assert b"AccessDenied" in stderr
    assert b"page denied" in stderr
    assert operation in stderr
    assert len(server.requests) == 2
    assert parse_qs(urlsplit(server.requests[1].effective_path).query)[
        "continuation-token"
    ] == [LATER_PAGE_TOKEN]


def denied_page(context: ResponderContext) -> HTTPResponse:
    return error_response("AccessDenied", "page denied", 403)


def undefined_entity(page: HTTPResponse) -> str:
    # The entity is undefined in XML, so the page does not parse.
    return page.body.decode().replace("bad-name", "bad&nbsp;name")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "recursive,human,expected",
    [
        pytest.param(
            False,
            False,
            f"{DIRECTORY}dir-a/\n"
            "2026-01-02 03:04:05          1 a file\n"
            f"{DIRECTORY}dir-b/\n"
            "2026-01-02 03:04:05       2048 b+file\n"
            "2026-01-02 03:04:05          7 c%file\n"
            "\nTotal Objects: 3\n   Total Size: 2056\n",
            id="bytes-flat",
        ),
        pytest.param(
            True,
            False,
            "2026-01-02 03:04:05          1 base /+%/a file\n"
            "2026-01-02 03:04:05       2048 base /+%/b+file\n"
            "2026-01-02 03:04:05          7 base /+%/c%file\n"
            "\nTotal Objects: 3\n   Total Size: 2056\n",
            id="bytes-recursive",
        ),
        pytest.param(
            False,
            True,
            f"{DIRECTORY}dir-a/\n"
            "2026-01-02 03:04:05     1 Byte a file\n"
            f"{DIRECTORY}dir-b/\n"
            "2026-01-02 03:04:05    2.0 KiB b+file\n"
            "2026-01-02 03:04:05    7 Bytes c%file\n"
            "\nTotal Objects: 3\n   Total Size: 2.0 KiB\n",
            id="human-flat",
        ),
        pytest.param(
            True,
            True,
            "2026-01-02 03:04:05     1 Byte base /+%/a file\n"
            "2026-01-02 03:04:05    2.0 KiB base /+%/b+file\n"
            "2026-01-02 03:04:05    7 Bytes base /+%/c%file\n"
            "\nTotal Objects: 3\n   Total Size: 2.0 KiB\n",
            id="human-recursive",
        ),
    ],
)
async def test_ls_pages_preserve_arguments_order_and_summary(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    recursive: bool,
    human: bool,
    expected: str,
) -> None:
    server, env = listing_runtime
    prefix = "base /+%/"
    wire_prefix = "base%20%2F%2B%25%2F"
    tokens = ["a/+== %2F&x", "b/+= %25&y"]
    server.set_response_sequence(
        [
            object_page(
                [(wire_prefix + "a%20file", 1)],
                token=tokens[0],
                encoded=True,
                prefixes=[] if recursive else [wire_prefix + "dir-a%2F"],
            ),
            object_page(
                [(wire_prefix + "b%2Bfile", 2048)],
                token=tokens[1],
                encoded=True,
                prefixes=[] if recursive else [wire_prefix + "dir-b%2F"],
            ),
            object_page([(wire_prefix + "c%25file", 7)], encoded=True),
        ]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "ls",
            f"s3://bucket/{prefix}",
            "--page-size",
            "2",
            "--request-payer",
            "requester",
            "--summarize",
            *(["--recursive"] if recursive else []),
            *(["--human-readable"] if human else []),
        ],
        env,
        timeout=20,
    )
    assert (rc, stderr) == (0, b"")
    assert stdout.decode() == expected
    assert len(server.requests) == 3
    for request, token in zip(server.requests, [None, *tokens], strict=True):
        assert request.method == "GET"
        query = parse_qs(
            urlsplit(request.effective_path).query, keep_blank_values=True
        )
        assert query["list-type"] == ["2"]
        assert query["prefix"] == [prefix]
        assert query["max-keys"] == ["2"]
        assert query.get("delimiter") == (None if recursive else ["/"])
        assert query.get("continuation-token") == (
            None if token is None else [token]
        )
        assert request.headers["x-amz-request-payer"] == "requester"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "pages,flags,expected",
    [
        pytest.param(
            [[], [("prefix/a", 3)], [("prefix/b", 8)]],
            [],
            "2026-01-02 03:04:05          3 a\n"
            "2026-01-02 03:04:05          8 b\n",
            id="first-flat",
        ),
        pytest.param(
            [[], [("prefix/a", 3)], [("prefix/b", 8)]],
            ["--recursive"],
            "2026-01-02 03:04:05          3 prefix/a\n"
            "2026-01-02 03:04:05          8 prefix/b\n",
            id="first-recursive",
        ),
        pytest.param(
            [[("prefix/a", 3)], [], [("prefix/b", 8)]],
            [],
            "2026-01-02 03:04:05          3 a\n"
            "2026-01-02 03:04:05          8 b\n",
            id="middle-flat",
        ),
        pytest.param(
            [[("prefix/a", 3)], [], [("prefix/b", 8)]],
            ["--recursive"],
            "2026-01-02 03:04:05          3 prefix/a\n"
            "2026-01-02 03:04:05          8 prefix/b\n",
            id="middle-recursive",
        ),
    ],
)
async def test_ls_empty_pages_do_not_end_pagination(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    pages: list[list[tuple[str, int]]],
    flags: list[str],
    expected: str,
) -> None:
    server, env = listing_runtime
    serve_token_pages(server, pages)
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "ls", "s3://bucket/prefix/", "--summarize", *flags],
        env,
        timeout=20,
    )
    assert (rc, stderr) == (0, b"")
    assert stdout.decode() == (
        f"{expected}\nTotal Objects: 2\n   Total Size: 11\n"
    )
    assert continuation_tokens(server) == [None, ["next-1"], ["next-2"]]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "flags", [[], ["--recursive"]], ids=["flat", "recursive"]
)
async def test_ls_all_empty_pages_summarize_nothing_and_exit_1(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    flags: list[str],
) -> None:
    server, env = listing_runtime
    serve_token_pages(server, [[], [], []])
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "ls", "s3://bucket/prefix/", "--summarize", *flags],
        env,
        timeout=20,
    )
    assert (rc, stderr) == (1, b"")
    assert stdout.decode() == "\nTotal Objects: 0\n   Total Size: 0\n"
    assert continuation_tokens(server) == [None, ["next-1"], ["next-2"]]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "paths,expected_rc",
    [
        pytest.param([], 0, id="buckets"),
        pytest.param(["s3://bucket/"], 0, id="bucket"),
        pytest.param(["s3://bucket/prefix"], 1, id="prefix"),
    ],
)
async def test_ls_empty_page_body_is_an_empty_final_page(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    paths: list[str],
    expected_rc: int,
) -> None:
    server, env = listing_runtime
    server.set_default_response(xml_response(""))
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", *paths], env, timeout=20
    )
    assert (rc, stdout, stderr) == (expected_rc, b"", b"")
    assert len(server.requests) == 1


def listing_query(request: RecordedHTTPRequest) -> dict[str, list[str]]:
    return parse_qs(
        urlsplit(request.effective_path).query, keep_blank_values=True
    )


@pytest.mark.asyncio
async def test_ls_without_path_lists_buckets_with_no_parameters(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    server.set_response_sequence([bucket_page(["bucket"])])
    stdout, stderr, rc = await run_cli(aws_cli, ["s3", "ls"], env, timeout=20)
    assert (rc, stdout, stderr) == (0, b"2026-01-02 03:04:05 bucket\n", b"")
    assert [
        (r.method, urlsplit(r.effective_path).path) for r in server.requests
    ] == [("GET", "/")]
    assert listing_query(server.requests[0]) == {}


# A path that does not end in `/` is a key prefix, which lists each object
# whose key starts with it under the key's last segment.
@pytest.mark.asyncio
async def test_ls_partial_key_lists_objects_starting_with_it(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    server.set_response_sequence([object_page([("object", 20)])])
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "s3://bucket/obj"], env, timeout=20
    )
    assert (rc, stdout, stderr) == (
        0,
        b"2026-01-02 03:04:05         20 object\n",
        b"",
    )
    assert len(server.requests) == 1
    assert listing_query(server.requests[0]) == {
        "list-type": ["2"],
        "prefix": ["obj"],
        "delimiter": ["/"],
        "encoding-type": ["url"],
    }


# A recursive listing prints each key as S3 stores it: a folder marker as
# its own zero-byte row, and `..` segments as they are.
@pytest.mark.asyncio
async def test_ls_recursive_prints_keys_as_stored(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    objects = [
        ("../escape", 7),
        ("folder/", 0),
        ("nested/a b+%", 11),
        ("safe/../normalized", 7),
    ]
    server.set_response_sequence([object_page(objects)])
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "bucket", "--recursive"], env, timeout=20
    )
    assert (rc, stderr) == (0, b"")
    assert stdout.decode() == "".join(
        f"2026-01-02 03:04:05 {size:>10} {key}\n" for key, size in objects
    )
    assert len(server.requests) == 1
    assert listing_query(server.requests[0]) == {
        "list-type": ["2"],
        "prefix": [""],
        "encoding-type": ["url"],
    }


@pytest.mark.asyncio
async def test_ls_human_readable_summary_names_zero_bytes(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    server.set_response_sequence([object_page([("empty", 0), ("object", 20)])])
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "ls", "bucket", "--human-readable", "--summarize"],
        env,
        timeout=20,
    )
    assert (rc, stderr) == (0, b"")
    assert stdout.decode() == (
        "2026-01-02 03:04:05    0 Bytes empty\n"
        "2026-01-02 03:04:05   20 Bytes object\n"
        "\nTotal Objects: 2\n   Total Size: 20 Bytes\n"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        pytest.param(
            b"<Error><Code>Bad\xffCode</Code><Message>bad</Message></Error>",
            id="not-utf8-code",
        ),
        pytest.param(
            b"<Error><Code>AccessDenied</Code><Message>caf\xe9</Message></Error>",
            id="not-utf8-message",
        ),
        pytest.param(
            b"<Error><Code>AccessDenied</Code><Message>denied</Message>",
            id="cut-short",
        ),
    ],
)
async def test_ls_unparsable_error_body_reports_the_status(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    body: bytes,
) -> None:
    server, env = listing_runtime
    # botocore reads the code and message only from a whole UTF-8 document
    # and otherwise names the status and its reason phrase.
    server.set_default_response(
        HTTPResponse.raw(
            body, status=403, headers={"Content-Type": "application/xml"}
        )
    )
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "s3://bucket/"], env, timeout=20
    )
    assert (rc, stdout) == (254, b"")
    assert stderr == (
        b"\naws: [ERROR]: An error occurred (403) when calling the "
        b"ListObjectsV2 operation: Forbidden\n"
    )
    assert len(server.requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body,message",
    [
        pytest.param(
            b"<Error><Code>AccessDenied</Code><Message>denied</Message>"
            b"<RequestId>id</RequestId ></Error>",
            b"denied",
            id="space-in-end-tag",
        ),
        pytest.param(
            b"<Error\n><Code>AccessDenied</Code\n><Message>denied</Message>"
            b"</Error>",
            b"denied",
            id="newline-in-tags",
        ),
        pytest.param(
            b"<Error><Code>AccessDenied</Code>"
            b"<Message><![CDATA[bad & x]]></Message></Error>",
            b"bad & x",
            id="cdata",
        ),
        pytest.param(
            b"<!-- a > b --><Error><Code>Access<!-- c -->Denied</Code>"
            b"<Message>denied</Message></Error>",
            b"denied",
            id="comments",
        ),
    ],
)
async def test_ls_well_formed_error_body_reports_its_code(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    body: bytes,
    message: bytes,
) -> None:
    server, env = listing_runtime
    server.set_default_response(
        HTTPResponse.raw(
            body, status=403, headers={"Content-Type": "application/xml"}
        )
    )
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "s3://bucket/"], env, timeout=20
    )
    assert (rc, stdout) == (254, b"")
    assert stderr == (
        b"\naws: [ERROR]: An error occurred (AccessDenied) when calling the "
        b"ListObjectsV2 operation: " + message + b"\n"
    )
    assert len(server.requests) == 1


@pytest.mark.asyncio
async def test_ls_precondition_failed_reports_the_service_error(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    message = "At least one of the pre-conditions you specified did not hold"
    server.set_default_response(
        error_response("PreconditionFailed", message, 400)
    )
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "s3://bucket/"], env, timeout=20
    )
    assert (rc, stdout) == (254, b"")
    assert stderr.decode() == (
        "\naws: [ERROR]: An error occurred (PreconditionFailed) when calling "
        f"the ListObjectsV2 operation: {message}\n"
    )
    assert len(server.requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message",
    [
        pytest.param("m" * 5000, id="ascii"),
        pytest.param("a" * 1023 + "é tail", id="multibyte"),
    ],
)
async def test_ls_long_error_message_is_printed_whole(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    message: str,
) -> None:
    server, env = listing_runtime
    server.set_default_response(error_response("AccessDenied", message, 403))
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "s3://bucket/"], env, timeout=20
    )
    assert (rc, stdout) == (254, b"")
    assert stderr.decode() == (
        "\naws: [ERROR]: An error occurred (AccessDenied) when calling the "
        f"ListObjectsV2 operation: {message}\n"
    )
    assert len(server.requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,body",
    [
        pytest.param(
            301,
            b"<Error><Code>PermanentRedirect</Code><Message>moved</Message>"
            b"<Region><![CDATA[eu-west-1]]></Region></Error>",
            id="region",
        ),
        pytest.param(
            301,
            b"<Error><Code>PermanentRedirect</Code>"
            b"<Message><![CDATA[a & b]]></Message>"
            b"<Region>eu-west-1</Region></Error>",
            id="message",
        ),
        pytest.param(
            301,
            b"<Error><Code>PermanentRedirect</Code>"
            b"<Message><!-- <![CDATA[ -->moved</Message>"
            b"<Region>eu-west-1</Region></Error>",
            id="comment",
        ),
        pytest.param(
            301,
            b"<Error><Code>PermanentRedirect</Code>"
            b"<Message><?pi <![CDATA[ ?>moved</Message>"
            b"<Region>eu-west-1</Region></Error>",
            id="processing-instruction",
        ),
        pytest.param(
            301,
            b"<Error><Code>PermanentRedirect</Code><Message>moved</Message>"
            b"<Region>eu-west-1<!-- c --></Region></Error>",
            id="region-comment",
        ),
        pytest.param(
            301,
            b"<Error><Code>PermanentRedirect</Code><Message>moved</Message>"
            b"<Region>eu-<?pi x?>west-1</Region></Error>",
            id="region-processing-instruction",
        ),
        pytest.param(
            301,
            b"<Error><Code>PermanentRedirect</Code>"
            b"<Message><!-- a & b -->moved</Message>"
            b"<Region>eu-west-1</Region></Error>",
            id="message-comment",
        ),
        pytest.param(
            400,
            b"<Error><Code>AuthorizationHeaderMalformed</Code>"
            b"<Message>bad</Message>"
            b"<Region><![CDATA[eu-west-1]]></Region></Error>",
            id="authorization-header-malformed",
        ),
    ],
)
async def test_ls_redirects_to_error_body_region_beside_markup(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    status: int,
    body: bytes,
) -> None:
    server, env = listing_runtime
    # botocore reads a CDATA section's payload literally and drops comments
    # and processing instructions, so the body names the region the retry
    # goes to when no header does.
    server.set_response_sequence(
        [
            HTTPResponse.raw(
                body,
                status=status,
                headers={"Content-Type": "application/xml"},
            ),
            object_page([("key", 13)]),
        ]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "ls", "s3://bucket/", "--region", "us-east-1"],
        env,
        timeout=20,
    )
    assert (rc, stderr) == (0, b"")
    assert stdout == b"2026-01-02 03:04:05         13 key\n"
    assert [request.headers.get("host") for request in server.requests] == [
        "bucket.s3.us-east-1.amazonaws.com",
        "bucket.s3.eu-west-1.amazonaws.com",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("recursive", [False, True], ids=["flat", "recursive"])
@pytest.mark.parametrize(
    "wire,decoded",
    [
        ("sp%20ace%2Bplus", "sp ace+plus"),
        ("literal%252Fpercent", "literal%2Fpercent"),
        ("%E9%9B%AA%F0%9F%93%84", "雪📄"),
        ("nested%2Fleaf", "nested/leaf"),
        ("a%26b%3Cc%3E", "a&b<c>"),
    ],
    ids=["space-plus", "decode-once", "unicode", "slash", "xml-characters"],
)
async def test_ls_explicit_url_encoding_decodes_keys_and_prefixes(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    recursive: bool,
    wire: str,
    decoded: str,
) -> None:
    server, env = listing_runtime
    token = "opaque%2F+ /="
    server.set_response_sequence(
        [
            object_page(
                [("root%2F" + wire, 13)],
                encoded=True,
                token=token,
                prefixes=[] if recursive else ["root%2F" + wire + "%2F"],
            ),
            object_page([("root%2Ftail", 0)], encoded=True),
        ]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "ls",
            "s3://bucket/root/",
            *(["--recursive"] if recursive else []),
        ],
        env,
        timeout=20,
    )
    assert (rc, stderr) == (0, b"")
    basename = decoded.rsplit("/", 1)[-1]
    name = "root/" + decoded if recursive else basename
    tail = "root/tail" if recursive else "tail"
    expected = "" if recursive else " " * 27 + f"PRE {basename}/\n"
    expected += f"2026-01-02 03:04:05         13 {name}\n"
    expected += f"2026-01-02 03:04:05          0 {tail}\n"
    assert stdout.decode() == expected
    assert len(server.requests) == 2
    query = parse_qs(urlsplit(server.requests[1].effective_path).query)
    assert query["continuation-token"] == [token]
    assert query["encoding-type"] == ["url"]


@pytest.mark.asyncio
@pytest.mark.parametrize("filtered", [False, True], ids=["all", "filtered"])
@pytest.mark.parametrize(
    "empty_first", [False, True], ids=["nonempty", "empty-first"]
)
async def test_ls_bucket_pages_preserve_filters_and_output(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    filtered: bool,
    empty_first: bool,
) -> None:
    server, env = listing_runtime
    token = "bucket/+== %2F&token"
    server.set_response_sequence(
        [
            bucket_page([] if empty_first else ["project-a"], token),
            bucket_page(["project-b", "project-c"]),
        ]
    )
    flags = (
        ["--bucket-name-prefix", "project-", "--bucket-region", "us-east-1"]
        if filtered
        else []
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "ls", "--page-size", "2", *flags],
        env,
        timeout=20,
    )
    assert (rc, stderr) == (0, b"")
    names = (
        ["project-b", "project-c"]
        if empty_first
        else ["project-a", "project-b", "project-c"]
    )
    assert stdout.decode() == "".join(
        f"2026-01-02 03:04:05 {name}\n" for name in names
    )
    assert len(server.requests) == 2
    for request, continuation in zip(
        server.requests, [None, token], strict=True
    ):
        assert request.method == "GET"
        query = parse_qs(urlsplit(request.effective_path).query)
        assert query["max-buckets"] == ["2"]
        assert query.get("continuation-token") == (
            None if continuation is None else [continuation]
        )
        assert query.get("prefix") == (["project-"] if filtered else None)
        assert query.get("bucket-region") == (
            ["us-east-1"] if filtered else None
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("flags,expected", FIRST_OBJECT_PAGE_OUTPUT)
async def test_ls_unparsable_later_object_page_keeps_output_without_summary(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    flags: list[str],
    expected: str,
) -> None:
    server, env = listing_runtime
    serve_first_object_page(server)
    server.handler = truncated_page
    result = await run_cli(
        aws_cli,
        ["s3", "ls", "s3://bucket/prefix/", *flags, "--summarize"],
        env,
        timeout=20,
    )
    assert_unparsable_page_fails(result, server, expected)


@pytest.mark.asyncio
async def test_ls_unparsable_later_bucket_page_keeps_output_without_summary(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    serve_first_bucket_page(server)
    server.handler = truncated_page
    result = await run_cli(
        aws_cli, ["s3", "ls", "--summarize"], env, timeout=20
    )
    assert_unparsable_page_fails(
        result, server, FIRST_BUCKET_PAGE_OUTPUT, "ListBuckets"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("flags,expected", FIRST_OBJECT_PAGE_OUTPUT)
async def test_ls_rejected_object_page_lists_once_a_retry_parses(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    flags: list[str],
    expected: str,
) -> None:
    server, env = listing_runtime
    server.set_response_sequence(
        [
            object_page([("prefix/key", 17)], token=LATER_PAGE_TOKEN),
            xml_response("<ListBucketResult><Contents>"),
            object_page([("prefix/later", 5)]),
        ]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "s3://bucket/prefix/", *flags], env, timeout=20
    )
    # The retry repeats the request, and the rejected attempt printed
    # nothing to repeat.
    later = expected.replace("17 ", " 5 ").replace("key", "later")
    assert (rc, stderr) == (0, b"")
    assert stdout.decode() == expected + later
    assert continuation_tokens(server) == [None] + [[LATER_PAGE_TOKEN]] * 2


@pytest.mark.asyncio
async def test_ls_rejected_bucket_page_lists_once_a_retry_parses(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    server.set_response_sequence(
        [
            bucket_page(["project-a"], LATER_PAGE_TOKEN),
            xml_response("<html>oops"),
            bucket_page(["project-b"]),
        ]
    )
    stdout, stderr, rc = await run_cli(aws_cli, ["s3", "ls"], env, timeout=20)
    assert (rc, stderr) == (0, b"")
    assert stdout.decode() == (
        FIRST_BUCKET_PAGE_OUTPUT + "2026-01-02 03:04:05 project-b\n"
    )
    assert continuation_tokens(server) == [None] + [[LATER_PAGE_TOKEN]] * 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args,operation",
    [
        (["s3://bucket/prefix/"], "ListObjectsV2"),
        ([], "ListBuckets"),
    ],
    ids=["objects", "buckets"],
)
async def test_ls_rejected_page_takes_the_configured_attempts(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    args: list[str],
    operation: str,
) -> None:
    server, env = listing_runtime
    # An unclosed root does not parse, whatever its name.
    server.set_default_response(xml_response("<html>oops"))
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "ls", *args],
        {**env, "AWS_MAX_ATTEMPTS": "4"},
        timeout=20,
    )
    assert (rc, stdout) == (254, b"")
    assert stderr == rejected_page_error(operation, retries=3)
    assert len(server.requests) == 4


@pytest.mark.asyncio
async def test_ls_redirect_counts_among_a_rejected_page_attempts(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    # botocore counts the redirect's resend among the call's attempts, so
    # two rejected pages after it use up the three.
    server.set_response_sequence(
        [
            HTTPResponse.raw(
                b"<Error><Code>PermanentRedirect</Code>"
                b"<Message>moved</Message><Region>eu-west-1</Region></Error>",
                status=301,
                headers={"Content-Type": "application/xml"},
            ),
            xml_response("<html>oops"),
            xml_response("<html>oops"),
            object_page([("key", 13)]),
        ]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "ls", "s3://bucket/", "--region", "us-east-1"],
        env,
        timeout=20,
    )
    assert (rc, stdout) == (254, b"")
    assert stderr == rejected_page_error("ListObjectsV2")
    assert [request.headers.get("host") for request in server.requests] == [
        "bucket.s3.us-east-1.amazonaws.com",
        "bucket.s3.eu-west-1.amazonaws.com",
        "bucket.s3.eu-west-1.amazonaws.com",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "denial,error",
    [
        (
            ("AccessDenied", "Access Denied"),
            (
                b"(AccessDenied) when calling the ListObjectsV2 operation "
                b"(reached max retries: 2): Access Denied"
            ),
        ),
        (
            None,
            (
                b"(403) when calling the ListObjectsV2 operation "
                b"(reached max retries: 2): Forbidden"
            ),
        ),
    ],
    ids=["error-body", "bodiless"],
)
async def test_ls_error_at_a_page_last_attempt_names_the_retries(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    denial: tuple[str, str] | None,
    error: bytes,
) -> None:
    server, env = listing_runtime
    # botocore marks any error at the last attempt, one it does not retry
    # as well, so a denial after two rejected pages names both retries.
    denied = (
        error_response(*denial, 403)
        if denial is not None
        else HTTPResponse.raw(b"", status=403)
    )
    server.set_response_sequence(
        [xml_response("<html>oops"), xml_response("<html>oops"), denied]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "s3://bucket/"], env, timeout=20
    )
    assert (rc, stdout) == (254, b"")
    assert stderr == b"\naws: [ERROR]: An error occurred " + error + b"\n"
    assert len(server.requests) == 3


@pytest.mark.asyncio
async def test_ls_unreadable_timestamp_is_not_retried(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    # botocore parses the document, so its 200 stands; only reading the
    # value fails.
    page = object_page([("prefix/key", 17)])
    body = page.body.replace(b"2026-01-02T03:04:05Z", b"not-a-date")
    server.set_default_response(
        HTTPResponse.raw(body, headers={"Content-Type": "application/xml"})
    )
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "s3://bucket/prefix/"], env, timeout=20
    )
    assert (rc, stdout) == (255, b""), stderr.decode()
    assert len(server.requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("recursive", [False, True], ids=["flat", "recursive"])
async def test_ls_encoding_type_is_read_with_entities_decoded(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    recursive: bool,
) -> None:
    server, env = listing_runtime
    body = object_page(
        [("dir%2Fa%2Bb+c", 5)],
        prefixes=[] if recursive else ["dir%2Fp+q%2F"],
    ).body.decode()
    # A character reference spells the value; botocore reads it as url.
    body = body.replace(
        "</ListBucketResult>",
        "<EncodingType>u&#114;l</EncodingType></ListBucketResult>",
    )
    server.set_response_sequence([xml_response(body)])
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "ls",
            "s3://bucket/dir/",
            *(["--recursive"] if recursive else []),
        ],
        env,
        timeout=20,
    )
    assert (rc, stderr) == (0, b"")
    expected = (
        "2026-01-02 03:04:05          5 dir/a+b c\n"
        if recursive
        else " " * 27 + "PRE p q/\n2026-01-02 03:04:05          5 a+b c\n"
    )
    assert stdout.decode() == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("flags,expected", FIRST_OBJECT_PAGE_OUTPUT)
@pytest.mark.parametrize(
    "summary", [[], ["--summarize"]], ids=["plain", "summary"]
)
async def test_ls_later_object_page_failure_keeps_output_without_summary(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    flags: list[str],
    expected: str,
    summary: list[str],
) -> None:
    server, env = listing_runtime
    serve_first_object_page(server)
    server.handler = denied_page
    result = await run_cli(
        aws_cli,
        ["s3", "ls", "s3://bucket/prefix/", *flags, *summary],
        env,
        timeout=20,
    )
    assert_later_page_denied(result, server, expected, b"ListObjectsV2")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "summary", [[], ["--summarize"]], ids=["plain", "summary"]
)
async def test_ls_later_bucket_page_failure_keeps_output_without_summary(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    summary: list[str],
) -> None:
    server, env = listing_runtime
    serve_first_bucket_page(server)
    server.handler = denied_page
    result = await run_cli(aws_cli, ["s3", "ls", *summary], env, timeout=20)
    assert_later_page_denied(
        result, server, FIRST_BUCKET_PAGE_OUTPUT, b"ListBuckets"
    )


@pytest.mark.asyncio
async def test_ls_prints_a_page_while_the_next_page_is_pending(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    first_row_read = asyncio.Event()

    async def held_later_page(context: ResponderContext) -> HTTPResponse:
        await first_row_read.wait()
        return object_page([("prefix/later", 5)])

    serve_first_object_page(server)
    server.handler = held_later_page
    process = await asyncio.create_subprocess_exec(
        aws_cli,
        "s3",
        "ls",
        "s3://bucket/prefix/",
        env=child_environment(env),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        # Upstream's `uni_print` flushes each row, so the first page's row
        # reaches the pipe while the second page is still held. This reads
        # the pipe directly, so it folds Windows line endings itself.
        assert process.stdout is not None
        first_row = await asyncio.wait_for(
            process.stdout.readline(), timeout=30
        )
        first_row_read.set()
        rest, stderr = await asyncio.wait_for(
            process.communicate(), timeout=60
        )
    finally:
        first_row_read.set()
        if process.returncode is None:
            process.kill()
            await process.wait()
    assert first_row.replace(b"\r\n", b"\n") == (
        b"2026-01-02 03:04:05         17 key\n"
    )
    assert (process.returncode, stderr) == (0, b"")
    assert rest.replace(b"\r\n", b"\n") == (
        b"2026-01-02 03:04:05          5 later\n"
    )
    assert len(server.requests) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("flags,expected", FIRST_OBJECT_PAGE_OUTPUT)
async def test_ls_undefined_entity_fails_its_whole_object_page(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    flags: list[str],
    expected: str,
) -> None:
    server, env = listing_runtime
    body = undefined_entity(
        object_page([("prefix/good", 1), ("prefix/bad-name", 2)])
    )
    serve_first_object_page(server)
    server.handler = lambda context: xml_response(body)
    result = await run_cli(
        aws_cli, ["s3", "ls", "s3://bucket/prefix/", *flags], env, timeout=20
    )
    assert_unparsable_page_fails(result, server, expected)


@pytest.mark.asyncio
async def test_ls_undefined_entity_fails_its_whole_bucket_page(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    body = undefined_entity(bucket_page(["project-b", "bad-name"]))
    serve_first_bucket_page(server)
    server.handler = lambda context: xml_response(body)
    result = await run_cli(aws_cli, ["s3", "ls"], env, timeout=20)
    assert_unparsable_page_fails(
        result, server, FIRST_BUCKET_PAGE_OUTPUT, "ListBuckets"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "spelling",
    [b"\xff", b"&#xD800;"],
    ids=["raw-byte", "surrogate-reference"],
)
@pytest.mark.parametrize("flags,expected", FIRST_OBJECT_PAGE_OUTPUT)
async def test_ls_non_utf8_key_fails_its_whole_object_page(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    flags: list[str],
    expected: str,
    spelling: bytes,
) -> None:
    server, env = listing_runtime
    # The page names no EncodingType, so the key's bytes are its name.
    page = object_page([("prefix/good", 1), ("prefix/bad-name", 2)])
    body = page.body.replace(b"bad-name", b"bad" + spelling)
    serve_first_object_page(server)
    server.handler = lambda context: HTTPResponse.raw(
        body, headers={"Content-Type": "application/xml"}
    )
    result = await run_cli(
        aws_cli, ["s3", "ls", "s3://bucket/prefix/", *flags], env, timeout=20
    )
    assert_unparsable_page_fails(result, server, expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,spelling",
    [
        ("Key", b"\x01"),
        ("Key", b"&#x1;"),
        ("ETag", b"\x0b"),
        ("ETag", b"&#XD800;"),
        ("ETag", b"&nbsp;"),
    ],
    ids=[
        "raw-control-key",
        "control-reference-key",
        "raw-control-etag",
        "malformed-reference-etag",
        "undefined-entity-etag",
    ],
)
@pytest.mark.parametrize("flags,expected", FIRST_OBJECT_PAGE_OUTPUT)
async def test_ls_character_xml_disallows_fails_its_whole_object_page(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    flags: list[str],
    expected: str,
    field: str,
    spelling: bytes,
) -> None:
    server, env = listing_runtime
    page = object_page([("prefix/good", 1), ("prefix/bad-name", 2)])
    if field == "Key":
        body = page.body.replace(b"bad-name", b"bad" + spelling)
    else:
        # Only the last object's ETag, a field no listing prints.
        head, etag, tail = page.body.rpartition(
            b"<ETag>d41d8cd98f00b204e9800998ecf8427e</ETag>"
        )
        assert etag
        body = head + b"<ETag>" + spelling + b"</ETag>" + tail
    serve_first_object_page(server)
    server.handler = lambda context: HTTPResponse.raw(
        body, headers={"Content-Type": "application/xml"}
    )
    result = await run_cli(
        aws_cli, ["s3", "ls", "s3://bucket/prefix/", *flags], env, timeout=20
    )
    assert_unparsable_page_fails(result, server, expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "prefixes,flags,expected",
    [
        pytest.param(
            ["dir/x&y/"],
            [],
            f"{DIRECTORY}x&y/\n2026-01-02 03:04:05          5 a&b <c>\n",
            id="flat",
        ),
        pytest.param(
            [],
            ["--recursive"],
            "2026-01-02 03:04:05          5 dir/a&b <c>\n",
            id="recursive",
        ),
    ],
)
async def test_ls_decodes_xml_entities_in_keys_and_prefixes(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    prefixes: list[str],
    flags: list[str],
    expected: str,
) -> None:
    server, env = listing_runtime
    server.set_response_sequence(
        [object_page([("dir/a&b <c>", 5)], prefixes=prefixes)]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "s3://bucket/dir/", *flags], env, timeout=20
    )
    assert (rc, stderr) == (0, b"")
    assert stdout.decode() == expected


@pytest.mark.asyncio
async def test_ls_decodes_xml_entities_before_url_decoding(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    # Entities decode first, so the escaped "%26amp%3B" stays "&amp;".
    server.set_response_sequence(
        [
            object_page(
                [("dir%2Fx%26amp%3B&y", 5)],
                prefixes=["dir%2Fp%26q%2F"],
                encoded=True,
            )
        ]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "s3://bucket/dir/"], env, timeout=20
    )
    assert (rc, stderr) == (0, b"")
    assert stdout.decode() == (
        f"{DIRECTORY}p&q/\n2026-01-02 03:04:05          5 x&amp;&y\n"
    )


@pytest.mark.asyncio
async def test_ls_decodes_xml_entities_in_bucket_names(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    server.set_response_sequence([bucket_page(["team&a"])])
    stdout, stderr, rc = await run_cli(aws_cli, ["s3", "ls"], env, timeout=20)
    assert (rc, stderr) == (0, b"")
    assert stdout.decode() == "2026-01-02 03:04:05 team&a\n"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "wire,decoded",
    [
        ("bad%zz%20x", "bad%zz x"),
        ("trailing%", "trailing%"),
        ("short%2+x", "short%2 x"),
        ("double%%41", "double%A"),
        ("invalid%FFutf8", "invalid�utf8"),
        ("truncated%E9%9B", "truncated�"),
        ("surrogate%ED%A0%80", "surrogate���"),
    ],
    ids=[
        "not-hex",
        "trailing",
        "short",
        "double-percent",
        "invalid-byte",
        "truncated",
        "surrogate",
    ],
)
async def test_ls_url_decoding_keeps_malformed_escapes(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    wire: str,
    decoded: str,
) -> None:
    server, env = listing_runtime
    server.set_response_sequence(
        [
            object_page(
                [("root%2F" + wire, 13)],
                encoded=True,
                prefixes=["root%2F" + wire + "%2F"],
            )
        ]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "s3://bucket/root/"], env, timeout=20
    )
    assert (rc, stderr) == (0, b"")
    assert stdout.decode() == (
        " " * 27 + f"PRE {decoded}/\n"
        f"2026-01-02 03:04:05         13 {decoded}\n"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "plain,escaped",
    [
        ("<Size>13</Size>", "<Size>&#49;3</Size>"),
        ("03:04:05Z", "03:04:05&#90;"),
    ],
    ids=["size", "last-modified"],
)
async def test_ls_decodes_xml_character_references_in_scalar_fields(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    plain: str,
    escaped: str,
) -> None:
    server, env = listing_runtime
    # Character references and literal characters represent the same XML
    # text, including in numeric and timestamp fields, not only object keys.
    body = object_page([("key", 13)]).body.decode().replace(plain, escaped)
    server.set_default_response(xml_response(body))
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "ls", "s3://bucket/", "--summarize"],
        env,
        timeout=20,
    )
    assert (rc, stderr) == (0, b"")
    assert stdout == (
        b"2026-01-02 03:04:05         13 key\n"
        b"\nTotal Objects: 1\n   Total Size: 13\n"
    )
    assert [request.method for request in server.requests] == ["GET"]


@pytest.mark.asyncio
async def test_ls_repeated_continuation_token_stops_with_error(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    server.set_response_sequence(
        [
            object_page([("first", 3)], token="same-token"),
            object_page([("second", 7)], token="same-token"),
            # A terminating page bounds a client that misses the repeated
            # token instead of leaving the test in an endless request loop.
            object_page([("unexpected", 11)]),
        ]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "ls", "s3://bucket/", "--summarize"],
        env,
        timeout=20,
    )
    assert rc == 255, (stdout, stderr)
    assert b"The same next token was received twice" in stderr
    assert stdout == (
        b"2026-01-02 03:04:05          3 first\n"
        b"2026-01-02 03:04:05          7 second\n"
    )
    assert len(server.requests) == 2
    query = parse_qs(urlsplit(server.requests[1].effective_path).query)
    assert query["continuation-token"] == ["same-token"]


@pytest.mark.asyncio
async def test_ls_repeated_long_continuation_token_is_reported_whole(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    # 5000 bytes, with a two-byte character across byte 4096.
    token = "a" * 4095 + "é" + "b" * 903
    server.set_response_sequence(
        [
            object_page([("first", 3)], token=token),
            object_page([("second", 7)], token=token),
            object_page([("unexpected", 11)]),
        ]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "s3://bucket/"], env, timeout=20
    )
    assert rc == 255, (stdout, stderr)
    assert stderr.decode() == (
        "\naws: [ERROR]: Error during pagination: The same next token was "
        f"received twice: {{'ContinuationToken': '{token}'}}\n"
    )


@pytest.mark.asyncio
async def test_ls_accepts_namespace_prefixed_xml_elements(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    # A namespace prefix changes the XML spelling, not the S3 element names.
    server.set_default_response(
        xml_response(
            '<s:ListBucketResult '
            'xmlns:s="http://s3.amazonaws.com/doc/2006-03-01/">'
            "<s:Contents><s:Key>key</s:Key><s:Size>13</s:Size>"
            "<s:LastModified>2026-01-02T03:04:05Z</s:LastModified>"
            "</s:Contents></s:ListBucketResult>"
        )
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "ls", "s3://bucket/", "--summarize"],
        env,
        timeout=20,
    )
    assert (rc, stderr) == (0, b"")
    assert stdout == (
        b"2026-01-02 03:04:05         13 key\n"
        b"\nTotal Objects: 1\n   Total Size: 13\n"
    )
    assert [request.method for request in server.requests] == ["GET"]


@pytest.mark.asyncio
async def test_ls_key_drops_comments_and_processing_instructions(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    body = (
        object_page([("placeholder", 13)])
        .body.decode()
        .replace("placeholder", "a<!-- <![CDATA[ & -->b<?pi x?>c")
    )
    server.set_default_response(xml_response(body))
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "ls", "s3://bucket/", "--summarize"],
        env,
        timeout=20,
    )
    assert (rc, stderr) == (0, b"")
    assert stdout == (
        b"2026-01-02 03:04:05         13 abc\n"
        b"\nTotal Objects: 1\n   Total Size: 13\n"
    )
    assert [request.method for request in server.requests] == ["GET"]


@pytest.mark.asyncio
async def test_ls_cdata_key_is_rendered_as_literal_text(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    body = (
        object_page([("placeholder", 13)])
        .body.decode()
        .replace("placeholder", "<![CDATA[dir/a&b<c>]]>")
    )
    server.set_default_response(xml_response(body))
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "ls", "s3://bucket/", "--summarize"],
        env,
        timeout=20,
    )
    assert (rc, stderr) == (0, b"")
    assert stdout == (
        b"2026-01-02 03:04:05         13 a&b<c>\n"
        b"\nTotal Objects: 1\n   Total Size: 13\n"
    )
    assert [request.method for request in server.requests] == ["GET"]


@pytest.mark.asyncio
async def test_ls_accepts_whitespace_around_object_size(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    body = (
        object_page([("key", 13)])
        .body.decode()
        .replace("<Size>13</Size>", "<Size> \n13\t </Size>")
    )
    server.set_default_response(xml_response(body))
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "ls", "s3://bucket/", "--summarize"],
        env,
        timeout=20,
    )
    assert (rc, stderr) == (0, b"")
    assert stdout == (
        b"2026-01-02 03:04:05         13 key\n"
        b"\nTotal Objects: 1\n   Total Size: 13\n"
    )
    assert [request.method for request in server.requests] == ["GET"]


@pytest.mark.asyncio
@pytest.mark.skipif(os.name != "posix", reason="requires POSIX byte arguments")
@pytest.mark.parametrize(
    "target,flags",
    [
        pytest.param("s3://bucket/key-", [], id="uri"),
        pytest.param("bucket/key-", [], id="path"),
        pytest.param("s3://bucket/key-", ["--recursive"], id="recursive"),
    ],
)
async def test_ls_refuses_non_utf8_prefix_before_any_request(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    target: str,
    flags: list[str],
) -> None:
    server, env = listing_runtime
    server.set_default_response(object_page([("key", 13)]))
    result = await run_cli(
        aws_cli,
        ["s3", "ls", target + os.fsdecode(b"\xff"), *flags],
        env,
        timeout=20,
    )
    assert_refused_before_request(result, server)


@pytest.mark.asyncio
@pytest.mark.skipif(os.name != "posix", reason="requires POSIX byte arguments")
@pytest.mark.parametrize(
    "flags",
    [
        pytest.param([b"--bucket-name-prefix", b"p\xff"], id="name-prefix"),
        pytest.param([b"--bucket-region", b"r\xff"], id="region"),
        pytest.param(
            [b"--bucket-region", b"r\xff", b"--bucket-name-prefix", b"pp\xff"],
            id="both",
        ),
    ],
)
async def test_ls_refuses_non_utf8_bucket_filter_before_any_request(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    flags: list[bytes],
) -> None:
    server, env = listing_runtime
    server.set_default_response(bucket_page(["project-a"]))
    result = await run_cli(
        aws_cli, ["s3", "ls", *map(os.fsdecode, flags)], env, timeout=20
    )
    assert_refused_before_request(result, server)


@pytest.mark.asyncio
@pytest.mark.skipif(os.name != "posix", reason="requires POSIX byte arguments")
async def test_ls_object_listing_refuses_non_utf8_bucket_filters(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    server.set_default_response(object_page([("key", 13)]))
    # The AWS CLI reads the bucket filters only to list buckets, but the
    # arguments stop it before it reads any.
    invalid = os.fsdecode(b"\xff")
    result = await run_cli(
        aws_cli,
        [
            "s3",
            "ls",
            "s3://bucket/",
            "--bucket-name-prefix",
            invalid,
            "--bucket-region",
            invalid,
        ],
        env,
        timeout=20,
    )
    assert_refused_before_request(result, server)


@pytest.mark.asyncio
@pytest.mark.parametrize(("stdout_kind", "exception", "text"), FAILING_STDOUTS)
async def test_ls_failed_stdout_write_is_reported_again_at_exit_with_120(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    stdout_kind: str,
    exception: str,
    text: str,
) -> None:
    server, env = listing_runtime
    server.set_default_response(object_page([("key", 17)]))
    with failing_stream(stdout_kind) as stdout:
        stderr, rc = await run_cli_with_stdout(
            aws_cli, ["s3", "ls", "s3://bucket/"], env, stdout
        )
    # The general handler reports the listing's write, and CPython's flush
    # of the output it left in stdout's buffer fails the same way at exit.
    assert (rc, stderr.decode()) == (
        120,
        (
            f"\naws: [ERROR]: {text}\n"
            "Exception ignored while flushing sys.stdout:\n"
            f"{exception}: {text}\n"
        ),
    )
    assert [request.method for request in server.requests] == ["GET"]


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="requires a POSIX shell")
async def test_ls_stdout_closed_at_start_reports_none_write_with_255(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = listing_runtime
    server.set_default_response(object_page([("key", 17)]))
    stderr, rc = await run_cli_without_stdout(
        aws_cli, ["s3", "ls", "s3://bucket/"], env
    )
    # CPython runs without a sys.stdout, so the first row's write raises
    # AttributeError and nothing is left to flush at exit.
    assert (rc, stderr.decode()) == (
        255,
        "\naws: [ERROR]: 'NoneType' object has no attribute 'write'\n",
    )
    assert [request.method for request in server.requests] == ["GET"]


@pytest.mark.asyncio
@pytest.mark.parametrize("stderr_kind", FAILING_STDERRS)
async def test_ls_failure_report_stderr_refuses_exits_1(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    stderr_kind: str,
) -> None:
    server, env = listing_runtime
    server.set_default_response(
        error_response("AccessDenied", "page denied", 403)
    )
    with failing_stream(stderr_kind) as stderr:
        rc = await run_cli_with_streams(
            aws_cli,
            ["s3", "ls", "s3://bucket/"],
            env,
            asyncio.subprocess.DEVNULL,
            stderr,
        )
    # The handler's write of the service error raises out of the AWS CLI's
    # main, and the release's launcher returns 1 instead of the handler's 254.
    assert rc == 1
    assert [request.method for request in server.requests] == ["GET"]


@pytest.mark.asyncio
@pytest.mark.parametrize("stream_kind", FAILING_STDERRS)
async def test_ls_stdout_failure_report_stderr_refuses_exits_1(
    aws_cli: str,
    listing_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    stream_kind: str,
) -> None:
    server, env = listing_runtime
    server.set_default_response(object_page([("key", 17)]))
    with (
        failing_stream(stream_kind) as stdout,
        failing_stream(stream_kind) as stderr,
    ):
        rc = await run_cli_with_streams(
            aws_cli, ["s3", "ls", "s3://bucket/"], env, stdout, stderr
        )
    # The report of the failed stdout write cannot reach stderr either, so
    # the AWS CLI never reaches `Py_Exit`, whose failed flush of the listing
    # left in stdout's buffer would otherwise make the status 120.
    assert rc == 1
    assert [request.method for request in server.requests] == ["GET"]
