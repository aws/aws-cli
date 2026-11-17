from collections.abc import AsyncIterator, Callable
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
import pytest_asyncio
import trustme
from localstub import AsyncHTTPTestServer

from credhelpers import assert_signature, credential_env, write_config
from tests.blackbox.utils import (
    get_object_response,
    head_object_response,
    list_objects_xml,
    mock_server,
    run_cli,
    xml_response,
)


@pytest_asyncio.fixture
async def global_runtime(
    tmp_path: Path,
) -> AsyncIterator[tuple[AsyncHTTPTestServer, dict[str, str]]]:
    async with mock_server() as (server, proxy):
        env = credential_env(proxy, tmp_path)
        env.update(
            AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test", TZ="UTC"
        )
        server.set_default_response(
            xml_response(
                list_objects_xml(
                    [
                        {
                            "Key": "entry.txt",
                            "Size": 17,
                            "LastModified": "2026-01-02T03:04:05Z",
                        }
                    ]
                )
            )
        )
        yield server, env


def assert_listing(result: tuple[bytes, bytes, int]) -> None:
    stdout, stderr, rc = result
    assert (rc, stderr) == (0, b"")
    assert stdout == b"2026-01-02 03:04:05         17 entry.txt\n"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "position",
    [0, 1, 3],
    ids=["before-service", "before-command", "after-operands"],
)
@pytest.mark.parametrize("equals", [False, True], ids=["split", "equals"])
async def test_global_region_placement_and_spelling_select_region(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    position: int,
    equals: bool,
) -> None:
    server, env = global_runtime
    arguments = ["s3", "ls", "s3://bucket/"]
    option = ["--region=eu-west-1"] if equals else ["--region", "eu-west-1"]
    arguments[position:position] = option
    assert_listing(await run_cli(aws_cli, arguments, env, timeout=20))
    assert len(server.requests) == 1
    request = server.requests[0]
    assert request.headers["host"] == "bucket.s3.eu-west-1.amazonaws.com"
    assert "/eu-west-1/s3/aws4_request" in request.headers["authorization"]
    assert_signature(request, "test", "test")


@pytest.mark.asyncio
@pytest.mark.parametrize("last", ["eu-west-1", "ap-south-1"])
@pytest.mark.parametrize(
    "equals", [False, True], ids=["split-last", "equals-last"]
)
async def test_global_duplicate_regions_use_last_occurrence(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    last: str,
    equals: bool,
) -> None:
    server, env = global_runtime
    final = [f"--region={last}"] if equals else ["--region", last]
    result = await run_cli(
        aws_cli,
        [
            "--region",
            "ca-central-1",
            "s3",
            "--region=us-west-2",
            "ls",
            "s3://bucket/",
            *final,
        ],
        env,
        timeout=20,
    )
    assert_listing(result)
    assert len(server.requests) == 1
    request = server.requests[0]
    assert request.headers["host"] == f"bucket.s3.{last}.amazonaws.com"
    assert f"/{last}/s3/aws4_request" in request.headers["authorization"]
    assert_signature(request, "test", "test")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "flags",
    [
        ["--output=json"],
        ["--output=text"],
        ["--output=table"],
        ["--output=yaml"],
        ["--output=yaml-stream"],
        ["--output=off"],
        ["--query=Contents[?Size > `99999`].Key"],
        ["--query=length(Contents)"],
        ["--query=@"],
        ["--color=on"],
        ["--color=off"],
        ["--color=auto"],
        ["--no-cli-pager"],
        ["--output=json", "--output=off"],
    ],
    ids=[
        "json",
        "text",
        "table",
        "yaml",
        "yaml-stream",
        "off",
        "filter-all",
        "scalar-query",
        "identity-query",
        "color-on",
        "color-off",
        "color-auto",
        "no-pager",
        "duplicate-output",
    ],
)
async def test_global_formatting_flags_leave_s3_listing_text_unchanged(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    flags: list[str],
) -> None:
    server, env = global_runtime
    result = await run_cli(
        aws_cli,
        [*flags, "s3", "ls", "s3://bucket/"],
        env,
        timeout=20,
    )
    assert_listing(result)
    assert len(server.requests) == 1
    assert server.requests[0].method == "GET"


# Global options parse anywhere on the command line, so after the operand
# they leave the listing as they do before the service.
@pytest.mark.asyncio
async def test_global_flags_after_operand_leave_s3_listing_text_unchanged(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = global_runtime
    result = await run_cli(
        aws_cli,
        ["s3", "ls", "s3://bucket/", "--output", "text", "--no-paginate"],
        env,
        timeout=20,
    )
    assert_listing(result)
    assert len(server.requests) == 1
    assert server.requests[0].method == "GET"


def assert_second_page_requested(server: AsyncHTTPTestServer) -> None:
    assert len(server.requests) == 2
    assert parse_qs(urlsplit(server.requests[1].effective_path).query)[
        "continuation-token"
    ] == ["next"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "flags", [[], ["--recursive"]], ids=["flat", "recursive"]
)
async def test_global_no_paginate_does_not_truncate_object_listing(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    flags: list[str],
) -> None:
    server, env = global_runtime
    server.set_response_sequence(
        [
            xml_response(
                list_objects_xml(
                    [
                        {
                            "Key": "a",
                            "Size": 3,
                            "LastModified": "2026-01-02T03:04:05Z",
                        }
                    ],
                    is_truncated=True,
                    next_continuation_token="next",
                )
            ),
            xml_response(
                list_objects_xml(
                    [
                        {
                            "Key": "b",
                            "Size": 8,
                            "LastModified": "2026-01-02T03:04:05Z",
                        }
                    ]
                )
            ),
        ]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["--no-paginate", "s3", "ls", "s3://bucket/", *flags],
        env,
        timeout=20,
    )
    assert (rc, stdout, stderr) == (
        0,
        b"2026-01-02 03:04:05          3 a\n"
        b"2026-01-02 03:04:05          8 b\n",
        b"",
    )
    assert_second_page_requested(server)


@pytest.mark.asyncio
async def test_global_no_paginate_does_not_truncate_bucket_listing(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = global_runtime
    server.set_response_sequence(
        [
            xml_response(
                "<ListAllMyBucketsResult><Buckets><Bucket>"
                "<Name>bucket-a</Name>"
                "<CreationDate>2026-01-02T03:04:05Z</CreationDate></Bucket>"
                "</Buckets><ContinuationToken>next</ContinuationToken>"
                "</ListAllMyBucketsResult>"
            ),
            xml_response(
                "<ListAllMyBucketsResult><Buckets><Bucket>"
                "<Name>bucket-b</Name>"
                "<CreationDate>2026-01-02T03:04:05Z</CreationDate></Bucket>"
                "</Buckets></ListAllMyBucketsResult>"
            ),
        ]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli, ["--no-paginate", "s3", "ls"], env, timeout=20
    )
    assert (rc, stdout, stderr) == (
        0,
        b"2026-01-02 03:04:05 bucket-a\n2026-01-02 03:04:05 bucket-b\n",
        b"",
    )
    assert_second_page_requested(server)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "option", ["--region", "--output", "--query", "--color"]
)
@pytest.mark.parametrize(
    "next_option", [False, True], ids=["end", "before-option"]
)
async def test_global_missing_values_fail_before_requests(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    option: str,
    next_option: bool,
) -> None:
    server, env = global_runtime
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "ls",
            "s3://bucket/",
            option,
            *(["--no-cli-pager"] if next_option else []),
        ],
        env,
        timeout=20,
    )
    assert rc == 252, stderr.decode()
    assert stdout == b""
    assert option.encode() in stderr
    assert b"expected one argument" in stderr
    assert not server.requests


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "flags,diagnostic",
    [
        (["--output=csv"], "Found invalid choice 'csv'"),
        (["--output="], "Found invalid choice ''"),
        (["--color=always"], "Found invalid choice 'always'"),
        (["--color="], "Found invalid choice ''"),
        (["--debug=1"], "ignored explicit argument"),
        (["--no-paginate=true"], "ignored explicit argument"),
        (["--no-cli-pager=true"], "ignored explicit argument"),
        (["--output=csv", "--output=json"], "Found invalid choice 'csv'"),
        (["--output=json", "--output=csv"], "Found invalid choice 'csv'"),
    ],
    ids=[
        "output-choice",
        "empty-output",
        "color-choice",
        "empty-color",
        "valued-debug",
        "valued-pagination",
        "valued-pager",
        "invalid-output-first",
        "invalid-output-last",
    ],
)
async def test_global_invalid_options_fail_before_requests(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    flags: list[str],
    diagnostic: str,
) -> None:
    server, env = global_runtime
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [*flags, "s3", "ls", "s3://bucket/"],
        env,
        timeout=20,
    )
    assert rc == 252, stderr.decode()
    assert stdout == b""
    assert diagnostic in stderr.decode()
    assert not server.requests


# CPython's int() checks the whole literal, then refuses one of more than
# 4300 digits however small its value, and only then converts it.
DIGIT_LIMIT = (
    "Exceeds the limit (4300 digits) for integer string conversion: value "
    "has 4301 digits; use sys.set_int_max_str_digits() to increase the limit"
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "flags,diagnostic",
    [
        (["--cli-read-timeout", "1" * 4301], DIGIT_LIMIT),
        (["--page-size", "0" * 4300 + "5"], DIGIT_LIMIT),
        (
            ["--page-size", "99999999999999999999x"],
            "invalid literal for int() with base 10: '99999999999999999999x'",
        ),
    ],
    ids=["read-timeout-ones", "zero-padded-page-size", "overflow-then-text"],
)
async def test_global_integers_follow_int_before_requests(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    flags: list[str],
    diagnostic: str,
) -> None:
    server, env = global_runtime
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "ls", "s3://bucket/", *flags],
        env,
        timeout=20,
    )
    assert rc == 255, stderr.decode()
    assert stdout == b""
    assert diagnostic in stderr.decode()
    assert not server.requests


# shutil.get_terminal_size reads COLUMNS that int() refuses as unset, so the
# usage keeps the 80-column fallback instead of wrapping at 25.
@pytest.mark.asyncio
async def test_global_columns_past_digit_limit_keep_default_width(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = global_runtime
    env["COLUMNS"] = "0" * 4300 + "25"
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "--profile"], env, timeout=20
    )
    assert rc == 252, stderr.decode()
    assert stdout == b""
    # One line, whatever the executable's name on the host.
    usage = stderr.decode().rsplit("\n\n", 1)[-1]
    assert usage.startswith("usage: aws")
    assert usage.endswith(" [--profile PROFILE] [--debug]\n"), usage
    assert not server.requests


def query_arguments(queries: list[str]) -> list[str]:
    arguments = [f"--query={queries[0]}", "s3", "ls", "s3://bucket/"]
    for query in queries[1:]:
        arguments.extend(["--query", query])
    return arguments


@pytest.mark.asyncio
async def test_global_query_ignores_invalid_earlier_expression_for_s3(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = global_runtime
    result = await run_cli(
        aws_cli, query_arguments(["[", "@"]), env, timeout=20
    )
    assert_listing(result)
    assert len(server.requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "queries",
    [["["], [""], ["foo[?"], ["@", "["]],
    ids=["unclosed", "empty", "bad-filter", "invalid-last"],
)
async def test_global_query_invalid_final_expression_fails_s3_before_requests(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    queries: list[str],
) -> None:
    server, env = global_runtime
    stdout, stderr, rc = await run_cli(
        aws_cli, query_arguments(queries), env, timeout=20
    )
    assert rc == 252, stderr.decode()
    assert stdout == b""
    assert b"Bad value for --query" in stderr
    assert not server.requests


@pytest.mark.asyncio
@pytest.mark.parametrize("error_format", ["legacy", "enhanced"])
async def test_global_query_validation_precedes_subcommand_validation(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    error_format: str,
) -> None:
    server, env = global_runtime
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "ls",
            "s3://bucket/",
            "--unknown-option",
            "--query=[",
            f"--cli-error-format={error_format}",
        ],
        env,
        timeout=20,
    )
    assert rc == 252, stderr.decode()
    assert stdout == b""
    assert b"Bad value for --query" in stderr
    assert b"Unknown options" not in stderr
    # Query-validation errors carry this prefix in both requested formats.
    assert b"aws: [ERROR]" in stderr
    assert not server.requests


def assert_debug_on_stderr(stderr: bytes) -> None:
    assert stderr
    assert b"DEBUG" in stderr
    assert b"https://" in stderr


@pytest.mark.asyncio
async def test_global_debug_listing_keeps_diagnostics_off_stdout(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = global_runtime
    stdout, stderr, rc = await run_cli(
        aws_cli, ["--debug", "s3", "ls", "s3://bucket/"], env, timeout=20
    )
    assert rc == 0, stderr.decode()
    assert stdout == b"2026-01-02 03:04:05         17 entry.txt\n"
    assert_debug_on_stderr(stderr)
    assert [r.method for r in server.requests] == ["GET"]


@pytest.mark.asyncio
async def test_global_debug_download_to_stdout_keeps_diagnostics_off_stdout(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = global_runtime
    payload = b"binary\x00payload\xff\n"
    server.set_response_sequence(
        [head_object_response(len(payload)), get_object_response(payload)]
    )
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["--debug", "s3", "cp", "s3://bucket/key", "-"],
        env,
        timeout=20,
    )
    assert rc == 0, stderr.decode()
    assert stdout == payload
    assert_debug_on_stderr(stderr)
    assert [r.method for r in server.requests] == ["HEAD", "GET"]


# Bundles of the proxy's CA certificate and more, which the AWS CLI's OpenSSL
# loads: it keeps a certificate under any of its labels and skips a key.
CERTIFICATE_BUNDLES = [
    pytest.param(lambda ca, key: ca + key, id="certificate-then-key"),
    pytest.param(lambda ca, key: key + ca, id="key-then-certificate"),
    pytest.param(
        lambda ca, key: ca.replace(b"CERTIFICATE", b"TRUSTED CERTIFICATE"),
        id="trusted-label",
    ),
    pytest.param(
        lambda ca, key: ca.replace(b"CERTIFICATE", b"X509 CERTIFICATE"),
        id="x509-label",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("bundle", CERTIFICATE_BUNDLES)
async def test_global_ca_bundle_trusts_certificates_beside_other_blocks(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    bundle: Callable[[bytes, bytes], bytes],
) -> None:
    server, env = global_runtime
    ca = Path(env["AWS_CA_BUNDLE"]).read_bytes()
    key = trustme.CA().private_key_pem.bytes()
    path = tmp_path / "bundle.pem"
    path.write_bytes(bundle(ca, key))
    assert_listing(
        await run_cli(
            aws_cli,
            ["--ca-bundle", str(path), "s3", "ls", "s3://bucket/"],
            env,
            timeout=20,
        )
    )
    assert len(server.requests) == 1


# The ways to name a CA bundle: the environment variable, a profile setting,
# and the global argument. Each returns the arguments it adds to the command.
def ca_bundle_variable(env: dict[str, str], path: Path) -> list[str]:
    env["AWS_CA_BUNDLE"] = str(path)
    return []


def ca_bundle_profile(env: dict[str, str], path: Path) -> list[str]:
    write_config(env, f"[default]\nca_bundle = {path}\n")
    return []


def ca_bundle_argument(env: dict[str, str], path: Path) -> list[str]:
    return ["--ca-bundle", str(path)]


CA_BUNDLE_SOURCES = [
    pytest.param(ca_bundle_variable, id="env"),
    pytest.param(ca_bundle_profile, id="profile"),
    pytest.param(ca_bundle_argument, id="flag"),
]


def name_ca_bundle(
    env: dict[str, str],
    tmp_path: Path,
    source: Callable[[dict[str, str], Path], list[str]],
    contents: bytes,
) -> list[str]:
    """Names a file holding `contents` as the CA bundle through `source`, in
    place of the harness's own bundle, and returns the arguments it adds."""
    path = tmp_path / "bundle.pem"
    path.write_bytes(contents)
    del env["AWS_CA_BUNDLE"]
    return source(env, path)


# Bundles with no certificate in them: text that is not PEM, and a PEM
# private key alone.
BUNDLES_WITHOUT_CERTIFICATE = [
    pytest.param(lambda: b"this is not a PEM certificate\n", id="not-pem"),
    pytest.param(lambda: trustme.CA().private_key_pem.bytes(), id="key-only"),
]


# The listing cannot trust the endpoint, so it fails with status 255 before
# any request.
@pytest.mark.asyncio
@pytest.mark.parametrize("source", CA_BUNDLE_SOURCES)
@pytest.mark.parametrize("contents", BUNDLES_WITHOUT_CERTIFICATE)
async def test_global_ca_bundle_without_certificate_fails_listing(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    source: Callable[[dict[str, str], Path], list[str]],
    contents: Callable[[], bytes],
) -> None:
    server, env = global_runtime
    extra = name_ca_bundle(env, tmp_path, source, contents())
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "s3://bucket/", *extra], env, timeout=30
    )
    assert (rc, stdout) == (255, b""), stderr.decode()
    assert not server.requests


# The download cannot build a client that trusts the endpoint, so it fails
# with status 255 before any request and writes no file.
@pytest.mark.asyncio
@pytest.mark.parametrize("source", CA_BUNDLE_SOURCES)
@pytest.mark.parametrize("contents", BUNDLES_WITHOUT_CERTIFICATE)
async def test_global_ca_bundle_without_certificate_fails_download(
    aws_cli: str,
    global_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    source: Callable[[dict[str, str], Path], list[str]],
    contents: Callable[[], bytes],
) -> None:
    server, env = global_runtime
    extra = name_ca_bundle(env, tmp_path, source, contents())
    destination = tmp_path / "out.txt"
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", "s3://bucket/a.txt", str(destination), *extra],
        env,
        timeout=30,
    )
    assert (rc, stdout) == (255, b""), stderr.decode()
    assert not server.requests
    assert not destination.exists()
