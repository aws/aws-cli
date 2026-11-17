from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final
from urllib.parse import quote_plus

import pytest
from localstub import HTTPResponse

from credhelpers import (
    AMZ_DATE_PLACEHOLDER,
    CACHE_FILE_MODE,
    CLI_CACHE,
    COMPARED_HEADERS,
    SCOPE_DATE_PLACEHOLDER,
    STS_NAMESPACE,
    BytesStartingWith,
    CliRun,
    FileChanges,
    NormalizedRequest,
    RoleCacheContent,
    RouteKey,
    Sandbox,
    Stub,
    assert_signature,
    created_cache_directories,
    export_credentials_output,
    role_cache_key,
    routed,
    run_export_credentials,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("sts_routes_through_proxy"),
]

# How botocore turns an STS AssumeRole or AssumeRoleWithWebIdentity answer
# into the role-cache entry or an error: QueryParser (parsers.py:252-326,
# 455-643) over ElementTree/expat, the endpoint's dispatch and retry loop
# (endpoint.py:190-346), ClientError (exceptions.py:509-541), and the
# fetcher's cache-then-read order (credentials.py:746-859). The rows are
# status dispatch (DISPATCH_ROWS) and error bodies (ERROR_BODY_ROWS). A
# nonstandard status line, which localstub cannot write, is tested in
# test_transport.py; three-attempt sequences live in test_retries.py.
# Retried rows here run with two attempts, which keeps each case's backoff
# below one second.
Members = dict[str, object]

ACCOUNT: Final = "123456789012"
WEB_ACCOUNT: Final = "210987654321"
ROLE_ARN: Final = f"arn:aws:iam::{ACCOUNT}:role/r"
WEB_ROLE_ARN: Final = f"arn:aws:iam::{WEB_ACCOUNT}:role/w"
SESSION_NAME: Final = "sess"
WEB_TOKEN: Final = "synthetic-web-token"
SOURCE_KEY: Final = "AKIDSOURCE"
SOURCE_SECRET: Final = "SOURCESECRET"
STS_HOST: Final = "sts.us-east-1.amazonaws.com"
STS_ROUTE: Final[RouteKey] = ("POST", STS_HOST, "/")
STS_VERSION: Final = "2011-06-15"
FORM_CONTENT_TYPE: Final = "application/x-www-form-urlencoded; charset=utf-8"
WIRE_EXPIRATION: Final = "2099-01-01T00:00:00Z"
FUTURE_EXPIRATION: Final = "2099-01-01T00:00:00+00:00"
ASSUMED_ARN: Final = f"arn:aws:sts::{ACCOUNT}:assumed-role/r/s"
REQUEST_ID: Final = "req-1"
GENERAL_RC: Final = 255
CLIENT_ERROR_RC: Final = 254
# botocore's JSONFileCache creates entries 0600 (utils.py:3991-4006).
CACHE_PREFIX: Final = f"home/{CLI_CACHE.as_posix()}/"
SIGV4_ALGORITHM: Final = "AWS4-HMAC-SHA256"
# AssumeRole is signed with the source profile's keys for STS in the
# default region.
SOURCE_SCOPE: Final = (
    SOURCE_KEY,
    SCOPE_DATE_PLACEHOLDER,
    "us-east-1",
    "sts",
)
TOKEN_FILE: Final = "web-identity-token"
WEB_PROFILE: Final = "wi"
SINGLE_ATTEMPT: Final = "1"
# Rows that retry run with two attempts (see the header comment).
TWO_ATTEMPTS: Final = "2"
THREE_ATTEMPTS: Final = "3"
CONFIG: Final = f"""\
[default]
role_arn = {ROLE_ARN}
source_profile = src
role_session_name = {SESSION_NAME}

[profile src]
aws_access_key_id = {SOURCE_KEY}
aws_secret_access_key = {SOURCE_SECRET}

[profile {WEB_PROFILE}]
role_arn = {WEB_ROLE_ARN}
web_identity_token_file = {{token}}
role_session_name = {SESSION_NAME}
"""
GENERAL_PREFIX: Final = b"\naws: [ERROR]: "
# parsers.py:537-549 frames expat's message and then the body's Python
# repr; only botocore's own words are asserted.
PARSE_ERROR: Final = BytesStartingWith(
    GENERAL_PREFIX + b"Unable to parse response (",
    (b"), invalid XML received. Further retries may succeed:\n",),
)
ROLE_USER_XML: Final = (
    "<AssumedRoleUser><AssumedRoleId>AROAEXAMPLE:s</AssumedRoleId>"
    f"<Arn>{ASSUMED_ARN}</Arn></AssumedRoleUser>"
)
METADATA_XML: Final = (
    f"<ResponseMetadata><RequestId>{REQUEST_ID}</RequestId></ResponseMetadata>"
)


@dataclass(frozen=True)
class Operation:
    """One STS operation as the CLI reaches it from a profile."""

    name: str
    profile: str | None
    cache_args: Mapping[str, str]
    body: bytes
    signed: bool

    @property
    def cache_path(self) -> str:
        return f"{CACHE_PREFIX}{role_cache_key(self.cache_args)}.json"


def form_body(action: str, *pairs: tuple[str, str]) -> bytes:
    """The query body: Action, Version, then the call's parameters."""
    fields = [("Action", action), ("Version", STS_VERSION), *pairs]
    return "&".join(
        f"{quote_plus(key)}={quote_plus(value)}" for key, value in fields
    ).encode()


ASSUME_ROLE: Final = Operation(
    name="AssumeRole",
    profile=None,
    cache_args={"RoleSessionName": SESSION_NAME, "RoleArn": ROLE_ARN},
    body=form_body(
        "AssumeRole", ("RoleSessionName", SESSION_NAME), ("RoleArn", ROLE_ARN)
    ),
    signed=True,
)
WEB_IDENTITY: Final = Operation(
    name="AssumeRoleWithWebIdentity",
    profile=WEB_PROFILE,
    cache_args={
        "RoleArn": WEB_ROLE_ARN,
        "RoleSessionName": SESSION_NAME,
        "WebIdentityToken": WEB_TOKEN,
    },
    body=form_body(
        "AssumeRoleWithWebIdentity",
        ("RoleSessionName", SESSION_NAME),
        ("RoleArn", WEB_ROLE_ARN),
        ("WebIdentityToken", WEB_TOKEN),
    ),
    signed=False,
)


@dataclass(frozen=True)
class Outcome:
    """What the run must show: exit, output, requests, cache entry."""

    returncode: int
    stderr: bytes | BytesStartingWith = b""
    stdout: bytes = b""
    requests: int = 1
    cache: RoleCacheContent | None = None


@dataclass(frozen=True)
class Case:
    """A 200 response body and what botocore makes of it.

    `members` is the parsed result with the AccountId the fetcher adds,
    or None when nothing is cached.
    """

    body: bytes
    members: Members | None
    returncode: int = 0
    stderr: bytes | BytesStartingWith = b""
    stdout: bytes = b""


def general_error(message: str) -> bytes:
    """`\\naws: [ERROR]: <message stripped>\\n` (errorformat.py:28-41)."""
    return GENERAL_PREFIX + f"{message.strip()}\n".encode()


def client_error(
    code: str,
    message: str,
    *,
    retries: int | None = 0,
    operation: Operation = ASSUME_ROLE,
) -> bytes:
    """ClientError's text (exceptions.py:509-541), framed.

    `retries` is RetryAttempts when MaxAttemptsReached is set, which adds
    the ` (reached max retries: N)` suffix; None leaves it out.
    """
    suffix = "" if retries is None else f" (reached max retries: {retries})"
    return general_error(
        f"An error occurred ({code}) when calling the {operation.name} "
        f"operation{suffix}: {message}"
    )


def xml_response(
    body: bytes | str,
    *,
    status: int = 200,
    headers: Sequence[tuple[str, str]] = (),
) -> HTTPResponse:
    """A text/xml response, plus `headers`."""
    data = body.encode() if isinstance(body, str) else body
    return HTTPResponse.raw(
        data,
        status=status,
        headers=[("Content-Type", "text/xml"), *headers],
    )


def empty_response(status: int) -> HTTPResponse:
    return HTTPResponse.raw(b"", status=status)


def credentials_xml(
    access_key: str = "ASIAEXAMPLE",
    secret_key: str = "SECRET",
    session_token: str = "TOKEN",
    expiration: str = WIRE_EXPIRATION,
) -> str:
    """A Credentials element with each value as raw XML text."""
    return (
        f"<Credentials><AccessKeyId>{access_key}</AccessKeyId>"
        f"<SecretAccessKey>{secret_key}</SecretAccessKey>"
        f"<SessionToken>{session_token}</SessionToken>"
        f"<Expiration>{expiration}</Expiration></Credentials>"
    )


def credentials(
    access_key: str = "ASIAEXAMPLE",
    secret_key: str = "SECRET",
    session_token: str = "TOKEN",
    expiration: str = FUTURE_EXPIRATION,
) -> Members:
    """Parsed Credentials plus the AccountId of ASSUMED_ARN."""
    return {
        "AccessKeyId": access_key,
        "SecretAccessKey": secret_key,
        "SessionToken": session_token,
        "Expiration": expiration,
        "AccountId": ACCOUNT,
    }


def credentials_without(*names: str) -> Members:
    return {
        key: value for key, value in credentials().items() if key not in names
    }


def result_body(
    result: str,
    *,
    action: str = "AssumeRole",
    metadata: str = METADATA_XML,
) -> bytes:
    """`<{action}Response>` holding `result` and then `metadata`."""
    return (
        f'<{action}Response xmlns="{STS_NAMESPACE}"><{action}Result>'
        f"{result}</{action}Result>{metadata}</{action}Response>"
    ).encode()


BASE_RESULT: Final = credentials_xml() + ROLE_USER_XML
BASE_BODY: Final = result_body(BASE_RESULT)
NAMESPACE_ATTRIBUTE: Final = f' xmlns="{STS_NAMESPACE}"'.encode()
BASE_MEMBERS: Final[Members] = {"Credentials": credentials()}


def exported(
    access_key: str = "ASIAEXAMPLE",
    secret_key: str = "SECRET",
    session_token: str | None = "TOKEN",
) -> bytes:
    return export_credentials_output(
        access_key, secret_key, session_token, FUTURE_EXPIRATION
    )


def error_body(error: str, *, request_id: str = "err-1") -> bytes:
    """An ErrorResponse holding `error`, then a RequestId."""
    return (
        f'<ErrorResponse xmlns="{STS_NAMESPACE}">{error}'
        f"<RequestId>{request_id}</RequestId></ErrorResponse>"
    ).encode()


def sts_request(operation: Operation) -> NormalizedRequest:
    """The request each attempt at `operation` sends.

    AssumeRole is SigV4-signed by the source profile's keys; the web
    identity client is UNSIGNED (credentials.py:1009-1020), so it sends
    neither Authorization nor X-Amz-Date. Neither carries a security
    token.
    """
    headers = {"content-type": FORM_CONTENT_TYPE}
    if operation.signed:
        headers["authorization"] = SIGV4_ALGORITHM
        headers["x-amz-date"] = AMZ_DATE_PLACEHOLDER
    return NormalizedRequest(
        method="POST",
        host=STS_HOST,
        path="/",
        target="/",
        query=(),
        content_type=FORM_CONTENT_TYPE,
        body_bytes=operation.body,
        headers=tuple((name, headers.get(name)) for name in COMPARED_HEADERS),
        user_agent=None,
        signing_scope=SOURCE_SCOPE if operation.signed else None,
    )


def cache_written(
    operation: Operation, cache: RoleCacheContent
) -> FileChanges:
    """A first cache write: the cache directories and the entry."""
    changes = created_cache_directories()
    changes[operation.cache_path] = (CACHE_FILE_MODE, cache)
    return changes


async def run_sts(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    responses: Sequence[HTTPResponse],
    *,
    max_attempts: str = SINGLE_ATTEMPT,
    operation: Operation = ASSUME_ROLE,
) -> CliRun:
    """Seal the sandbox and run once with STS scripted in order.

    The STS stub answers through the TLS intercept proxy at the default
    regional endpoint. A request past the script gets the harness's 400
    tripwire, so a call botocore does not make changes the outcome.
    """
    server, proxy = stub
    token = sandbox.write(TOKEN_FILE, WEB_TOKEN)
    sandbox.config.write_text(CONFIG.format(token=token), encoding="utf-8")
    sandbox.seal()
    script: dict[RouteKey, list[HTTPResponse]] = {STS_ROUTE: list(responses)}
    globals_ = () if operation.profile is None else ("--profile", WEB_PROFILE)
    return await run_export_credentials(
        aws_cli,
        sandbox,
        [server],
        sandbox.env(proxy, max_attempts=max_attempts),
        globals_=globals_,
        handlers={server: lambda: routed(script)},
    )


def assert_outcome(
    run: CliRun, outcome: Outcome, operation: Operation
) -> None:
    """Pin the run to `outcome`, every request, and every file change.

    The only change is the cache write, if any.
    """
    assert (run.returncode, run.stdout, run.stderr) == (
        outcome.returncode,
        outcome.stdout,
        outcome.stderr,
    ), run.describe()
    assert run.requests == (sts_request(operation),) * outcome.requests, (
        run.describe()
    )
    if operation.signed:
        for raw in run.raw_requests:
            assert_signature(raw, SOURCE_KEY, SOURCE_SECRET)
    changes: FileChanges = {}
    if outcome.cache is not None:
        changes = cache_written(operation, outcome.cache)
    assert run.changes == changes, run.describe()


async def assert_sts_outcome(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    responses: Sequence[HTTPResponse],
    outcome: Outcome,
    *,
    max_attempts: str = SINGLE_ATTEMPT,
    operation: Operation = ASSUME_ROLE,
) -> None:
    """Run once with `responses` and pin the run to `outcome`."""
    run = await run_sts(
        aws_cli,
        sandbox,
        stub,
        responses,
        max_attempts=max_attempts,
        operation=operation,
    )
    assert_outcome(run, outcome, operation)


async def assert_case(
    aws_cli: str, sandbox: Sandbox, stub: Stub, case: Case
) -> None:
    cache = None if case.members is None else RoleCacheContent(case.members)
    await assert_sts_outcome(
        aws_cli,
        sandbox,
        stub,
        [xml_response(case.body)],
        Outcome(case.returncode, case.stderr, case.stdout, cache=cache),
    )


@dataclass(frozen=True)
class Dispatch:
    """A status-dispatch row: responses in order, attempts, outcome."""

    responses: tuple[HTTPResponse, ...]
    outcome: Outcome
    max_attempts: str = SINGLE_ATTEMPT
    operation: Operation = ASSUME_ROLE


def dispatch_error(
    responses: Sequence[HTTPResponse],
    stderr: bytes | BytesStartingWith,
    *,
    returncode: int = CLIENT_ERROR_RC,
    max_attempts: str = SINGLE_ATTEMPT,
    requests: int = 1,
    operation: Operation = ASSUME_ROLE,
) -> Dispatch:
    return Dispatch(
        tuple(responses),
        Outcome(returncode, stderr, requests=requests),
        max_attempts,
        operation,
    )


def sts_error(
    code: str, message: str, *, status: int = 400, extra: str = ""
) -> HTTPResponse:
    return xml_response(
        error_body(
            f"<Error><Type>Sender</Type><Code>{code}</Code>"
            f"<Message>{message}</Message>{extra}</Error>"
        ),
        status=status,
    )


HTML_OK: Final = b"<html><body><b>Bad</b></body></html>"
SERVICE_UNAVAILABLE_HTML: Final = (
    b"<html><body><b>Http/1.1 Service Unavailable</b></body></html>"
)
UNKNOWN: Final = client_error("Unknown", "Unknown")
INTERNAL_SERVER_ERROR: Final = "Internal Server Error"


DISPATCH_ROWS: Final = [
    pytest.param(
        dispatch_error(
            [empty_response(400)], PARSE_ERROR, returncode=GENERAL_RC
        ),
        id="400-empty-unparseable",
    ),
    pytest.param(
        dispatch_error([xml_response(HTML_OK, status=400)], UNKNOWN),
        id="400-well-formed-html-is-xml",
    ),
    pytest.param(
        dispatch_error(
            [empty_response(500)], client_error("500", INTERNAL_SERVER_ERROR)
        ),
        id="500-empty-generic",
    ),
    pytest.param(
        dispatch_error(
            [xml_response(SERVICE_UNAVAILABLE_HTML, status=503)],
            client_error("503", "Service Unavailable"),
        ),
        id="503-html-generic",
    ),
    pytest.param(
        dispatch_error(
            [sts_error("InternalFailure", "internal", status=500)],
            client_error("InternalFailure", "internal"),
        ),
        id="500-xml-error",
    ),
    pytest.param(
        # Upstream bug, matched for parity: the message says further
        # retries may succeed, but the parse error is raised outside the
        # retry loop, so a 500 with a non-XML body is never retried
        # (endpoint.py:311-313, parsers.py:537-549).
        dispatch_error(
            [HTTPResponse.text("oops", status=500)],
            PARSE_ERROR,
            returncode=GENERAL_RC,
            max_attempts=THREE_ATTEMPTS,
        ),
        id="500-text-parse-error-never-retried",
    ),
    pytest.param(
        dispatch_error(
            [sts_error("NotImplemented", "nope", status=501)],
            client_error("NotImplemented", "nope", retries=None),
            max_attempts=THREE_ATTEMPTS,
        ),
        id="501-not-retried",
    ),
    pytest.param(
        dispatch_error(
            [sts_error("Throttling", "Rate exceeded")] * 2,
            client_error("Throttling", "Rate exceeded", retries=1),
            max_attempts=TWO_ATTEMPTS,
            requests=2,
        ),
        id="400-throttling-retried",
    ),
    pytest.param(
        dispatch_error(
            [sts_error("RequestTimeout", "slow")] * 2,
            client_error("RequestTimeout", "slow", retries=1),
            max_attempts=TWO_ATTEMPTS,
            requests=2,
        ),
        id="400-request-timeout-retried",
    ),
    pytest.param(
        dispatch_error(
            [sts_error("AccessDenied", "denied")],
            client_error("AccessDenied", "denied", retries=None),
            max_attempts=THREE_ATTEMPTS,
        ),
        id="400-access-denied-not-retried",
    ),
    pytest.param(
        dispatch_error(
            [sts_error("IDPCommunicationError", "idp down")] * 2,
            client_error(
                "IDPCommunicationError",
                "idp down",
                retries=1,
                operation=WEB_IDENTITY,
            ),
            max_attempts=TWO_ATTEMPTS,
            requests=2,
            operation=WEB_IDENTITY,
        ),
        id="400-idp-communication-retried-web-identity",
    ),
    pytest.param(
        # Upstream bug, matched for parity: the parser treats only
        # statuses from 301 up as errors while the client raises from 300
        # up, so a 300 carrying a success body fails as an Unknown error
        # (parsers.py:252, client.py:920).
        dispatch_error([xml_response(BASE_BODY, status=300)], UNKNOWN),
        id="300-success-body-raised",
    ),
    pytest.param(
        dispatch_error(
            [
                xml_response(
                    error_body(
                        "<Error><Code>PermanentRedirect</Code>"
                        "<Message>moved</Message></Error>"
                    ),
                    status=301,
                    headers=[("Location", "https://elsewhere.example/")],
                )
            ],
            client_error("PermanentRedirect", "moved"),
        ),
        id="301-redirect-not-followed",
    ),
    pytest.param(
        dispatch_error(
            [empty_response(200)], PARSE_ERROR, returncode=GENERAL_RC
        ),
        id="200-empty",
    ),
    pytest.param(
        Dispatch(
            (empty_response(500), xml_response(BASE_BODY)),
            Outcome(
                0,
                stdout=exported(),
                requests=2,
                cache=RoleCacheContent(BASE_MEMBERS),
            ),
            THREE_ATTEMPTS,
        ),
        id="500-then-200",
    ),
]


@pytest.mark.parametrize("row", DISPATCH_ROWS)
async def test_sts_status_dispatch_matches_botocore(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    row: Dispatch,
) -> None:
    await assert_sts_outcome(
        aws_cli,
        sandbox,
        stub,
        row.responses,
        row.outcome,
        max_attempts=row.max_attempts,
        operation=row.operation,
    )


def rejected(code: str, message: str) -> bytes:
    """A single-attempt ClientError: `(reached max retries: 0)`."""
    return client_error(code, message)


ERROR_BODY_ROWS: Final = [
    pytest.param(
        error_body(
            "<Error><Type>Sender</Type><Code>AccessDenied</Code>"
            "<Message>denied</Message></Error>"
        ),
        rejected("AccessDenied", "denied"),
        id="error-response",
    ),
    pytest.param(
        b"<Response><Errors><Error><Code>InvalidThing</Code>"
        b"<Message>ec2 style</Message></Error></Errors>"
        b"<RequestId>rid</RequestId></Response>",
        rejected("InvalidThing", "ec2 style"),
        id="errors-wrapper",
    ),
    pytest.param(
        b"<ErrorResponse><Error><Type>Sender</Type>"
        b"<Message>no code</Message></Error></ErrorResponse>",
        rejected("Unknown", "no code"),
        id="no-code",
    ),
    pytest.param(
        b"<ErrorResponse><Error><Type>Sender</Type>"
        b"<Code>OnlyCode</Code></Error></ErrorResponse>",
        rejected("OnlyCode", "Unknown"),
        id="no-message",
    ),
    pytest.param(
        b"<ErrorResponse><Error><Code>AccessDenied</Code>"
        b"<Message>a &amp; b &lt;c&gt; &#233; &#x263A;</Message></Error>"
        b"</ErrorResponse>",
        rejected("AccessDenied", "a & b <c> é ☺"),
        id="message-entities",
    ),
    pytest.param(
        b"<ErrorResponse><Error><Code>AccessDenied</Code><Message>m</Message>"
        b"<Detail>d</Detail><Foo><Bar>1</Bar></Foo><Extra/></Error>"
        b"<RequestId>r</RequestId></ErrorResponse>",
        rejected("AccessDenied", "m"),
        id="extra-fields-not-printed",
    ),
    pytest.param(
        b'<Foo xmlns="urn:x"><Error><Code>NsCode</Code><Message>ns</Message>'
        b"</Error></Foo>",
        rejected("NsCode", "ns"),
        id="foreign-namespace-root",
    ),
    pytest.param(
        f'<ErrorResponse xmlns="{STS_NAMESPACE}">\n  <Error>\n'
        "    <Type>Sender</Type>\n    <Code>AccessDenied</Code>\n"
        "    <Message>pretty</Message>\n  </Error>\n"
        "  <RequestId>r</RequestId>\n</ErrorResponse>\n".encode(),
        rejected("AccessDenied", "pretty"),
        id="pretty-printed",
    ),
]


@pytest.mark.parametrize(("body", "stderr"), ERROR_BODY_ROWS)
async def test_sts_error_body_matches_botocore(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    body: bytes,
    stderr: bytes,
) -> None:
    await assert_sts_outcome(
        aws_cli,
        sandbox,
        stub,
        [xml_response(body, status=400)],
        Outcome(CLIENT_ERROR_RC, stderr),
    )


# BASE_BODY cut after its Credentials element: every open element is
# still unclosed at the end of the input.
TRUNCATED_BODY: Final = BASE_BODY[: BASE_BODY.index(b"<AssumedRoleUser>")]


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(b"not xml", id="plain-text"),
        pytest.param(TRUNCATED_BODY, id="truncated-sts-body"),
    ],
)
async def test_sts_unparseable_body_is_a_parse_error(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    body: bytes,
) -> None:
    await assert_sts_outcome(
        aws_cli,
        sandbox,
        stub,
        [xml_response(body, status=400)],
        Outcome(GENERAL_RC, PARSE_ERROR),
    )


def parsed_case(result: str, members: Members) -> Case:
    """An AssumeRole success that caches and prints `members`."""
    printed = members["Credentials"]
    assert isinstance(printed, dict)
    return Case(
        body=result_body(result),
        members=members,
        stdout=export_credentials_output(
            printed["AccessKeyId"],
            printed["SecretAccessKey"],
            printed["SessionToken"],
            printed["Expiration"],
        ),
    )


def with_access_key(raw: str, parsed: str) -> Case:
    """BASE_BODY with AccessKeyId text `raw`, parsed as `parsed`."""
    return parsed_case(
        credentials_xml(access_key=raw) + ROLE_USER_XML,
        {"Credentials": credentials(parsed)},
    )


def base_variant(body: bytes) -> Case:
    """A body that parses exactly like BASE_BODY."""
    return Case(body=body, members=BASE_MEMBERS, stdout=exported())


SUCCESS_ROWS: Final = [
    pytest.param(base_variant(BASE_BODY), id="baseline"),
    pytest.param(
        base_variant(BASE_BODY.replace(NAMESPACE_ATTRIBUTE, b"")),
        id="no-namespace",
    ),
    pytest.param(
        base_variant(b'<?xml version="1.0" encoding="UTF-8"?>\n' + BASE_BODY),
        id="xml-declaration",
    ),
    pytest.param(
        base_variant(BASE_BODY + b" \r\n\t"), id="trailing-whitespace"
    ),
    pytest.param(
        base_variant(result_body(BASE_RESULT, metadata="")),
        id="response-metadata-absent",
    ),
    pytest.param(
        base_variant(
            result_body(
                "<Unknown>u</Unknown>"
                + credentials_xml().replace(
                    "<Expiration>", "<Extra>e</Extra><Expiration>"
                )
                + ROLE_USER_XML
                + "<Trailing><Nested/></Trailing>"
            )
        ),
        id="unknown-elements-ignored",
    ),
    pytest.param(
        with_access_key("a&amp;b&lt;c&gt;d&quot;e&apos;f", "a&b<c>d\"e'f"),
        id="predefined-entities",
    ),
    pytest.param(
        with_access_key("<![CDATA[<raw>&amp;]]>", "<raw>&amp;"),
        id="cdata-verbatim",
    ),
    pytest.param(
        with_access_key("café ☺", "café ☺"),
        id="utf-8-text",
    ),
]


@pytest.mark.parametrize("case", SUCCESS_ROWS)
async def test_sts_success_body_parse_matches_botocore(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    case: Case,
) -> None:
    await assert_case(aws_cli, sandbox, stub, case)


CACHED_CREDENTIALS_ROWS: Final = [
    pytest.param(
        # Without an AssumedRoleUser ARN the fetcher derives no AccountId
        # (credentials.py:852-859).
        parsed_case(
            credentials_xml() + "<AssumedRoleUser><AssumedRoleId>AROAEXAMPLE:s"
            "</AssumedRoleId></AssumedRoleUser>",
            {"Credentials": credentials_without("AccountId")},
        ),
        id="arn-absent",
    ),
    pytest.param(
        # Upstream bug, matched for parity: the response is cached before
        # its keys are read, so a partial one fails this run and stays
        # cached for the next (credentials.py:752-766).
        Case(
            body=result_body(
                credentials_xml().replace(
                    "<AccessKeyId>ASIAEXAMPLE</AccessKeyId>", ""
                )
                + ROLE_USER_XML
            ),
            members={"Credentials": credentials_without("AccessKeyId")},
            returncode=GENERAL_RC,
            stderr=BytesStartingWith(GENERAL_PREFIX, (b"AccessKeyId",)),
        ),
        id="access-key-absent-cached-before-read",
    ),
    pytest.param(
        parsed_case(
            credentials_xml(session_token="") + ROLE_USER_XML,
            {"Credentials": credentials(session_token="")},
        ),
        id="empty-session-token-exported",
    ),
]


@pytest.mark.parametrize("case", CACHED_CREDENTIALS_ROWS)
async def test_sts_cached_credentials_match_botocore(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    case: Case,
) -> None:
    await assert_case(aws_cli, sandbox, stub, case)
