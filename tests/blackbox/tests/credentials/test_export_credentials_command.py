import json
import os
from collections.abc import AsyncIterator, Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Final

import pytest
import pytest_asyncio
from localstub import AsyncTLSInterceptProxy, HTTPResponse

from credhelpers import (
    AMZ_DATE_PLACEHOLDER,
    COMPARED_HEADERS,
    LOGIN_TOKEN_CACHE,
    SAMPLE_DPOP_PEM,
    SCOPE_DATE_PLACEHOLDER,
    BytesStartingWith,
    CliRun,
    NormalizedRequest,
    RouteKey,
    Sandbox,
    Stub,
    assert_dpop,
    assert_signature,
    command_line,
    export_credentials_output,
    routed,
    run_export_credentials,
    sts_error_xml,
    unexpected_request,
    write_login_token,
)
from tests.blackbox.utils import mock_server

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("sts_routes_through_proxy"),
]

# How `aws configure export-credentials` frames what goes wrong before and
# around credential resolution: the entry-point and CLI handler chains
# (awscli/errorhandler.py:106-130), the error-format lookup
# (errorhandler.py:184-233), the startup stages from the first-pass parse
# to the export command, and the export command's own parse, recursion
# barrier, and formatters (awscli/customizations/configure/
# exportcreds.py:156-282). Every expected value below was observed with the
# bundled CLI; where an error's tail is CPython's or a library's wording,
# only its AWS-authored prefix is asserted. YAML and table error formats
# are never set here; nor are --query, --debug, --version,
# --cli-auto-prompt, or nested-block values.

# Placeholders a scenario may use in env values, file contents, and
# expected stderr; each becomes the sandbox path it names.
ROOT_PLACEHOLDER: Final = "<ROOT>"
HOME_PLACEHOLDER: Final = "<HOME>"

ACCOUNT: Final = "123456789012"
ROLE_ARN: Final = f"arn:aws:iam::{ACCOUNT}:role/framing"
STATIC_KEY: Final = "AKIDSTATIC"
STATIC_SECRET: Final = "STATIC-secret"
STATIC_KEYS: Final = (
    f"aws_access_key_id = {STATIC_KEY}\n"
    f"aws_secret_access_key = {STATIC_SECRET}\n"
)
STATIC_DEFAULT: Final = "[default]\n" + STATIC_KEYS
STATIC_OUTPUT: Final = export_credentials_output(STATIC_KEY, STATIC_SECRET)
ENV_KEY: Final = "AKIDENV"
ENV_SECRET: Final = "ENV-secret"
ENV_TOKEN: Final = "ENV-token"
ENV_CREDENTIALS: Final = {
    "AWS_ACCESS_KEY_ID": ENV_KEY,
    "AWS_SECRET_ACCESS_KEY": ENV_SECRET,
}
ENV_OUTPUT: Final = export_credentials_output(ENV_KEY, ENV_SECRET)
REGION_VARS: Final = ("AWS_REGION", "AWS_DEFAULT_REGION")
CHAIN_VAR: Final = "_AWS_CLI_PROFILE_CHAIN"
ERROR_FORMAT_VAR: Final = "AWS_CLI_ERROR_FORMAT"
ALIAS_FILE: Final = "home/.aws/cli/alias"

# awscli/errorformat.py:28-41 and errorhandler.py:179-182.
ERROR_PREFIX: Final = "\naws: [ERROR]: "
PARAM_VALIDATION_PREFIX: Final = (
    f"{ERROR_PREFIX}An error occurred (ParamValidation): "
)
# MainArgParser's usage (awscli/argparser.py:18-28), which CLIArgParser.
# error appends after two newlines (argparser.py:104-116).
MAIN_USAGE: Final = (
    "usage: aws [options] <command> <subcommand> [<subcommand> ...] "
    "[parameters]\n"
    "To see help text, you can run:\n"
    "\n"
    "  aws help\n"
    "  aws <command> help\n"
    "  aws <command> <subcommand> help\n"
)

# SSOProvider's load error for a profile with only sso_account_id
# (botocore credentials.py:2401-2433), wrapped by
# exportcreds.py:268-275 with the trailing newline. The error-format table
# below renders this one message in every format.
SSO_INCOMPLETE_CONFIG: Final = f"[default]\nsso_account_id = {ACCOUNT}\n"
SSO_LOAD_MESSAGE: Final = (
    'Unable to retrieve credentials: The profile "default" is configured '
    "to use SSO but is missing required configuration: sso_role_name, "
    "sso_start_url, sso_region\n"
)


def no_profile_message(name: str) -> str:
    """ProfileNotFound wrapped by exportcreds.py:268-275."""
    return (
        "Unable to retrieve credentials: The config profile "
        f"({name}) could not be found\n"
    )


UNPARSEABLE: Final = "Unable to parse config file: "
TIMESTAMP_TEMPLATE: Final = (
    'Unknown cli_timestamp_format value: {}, valid values are "wire" or '
    '"iso8601"'
)
ENDPOINT_TEMPLATE: Final = (
    'Bad value for --endpoint-url "{}": scheme is missing.  Must be of the '
    "form http://<hostname>/ or https://<hostname>/"
)
CYCLE_TEMPLATE: Final = (
    "Credential process resolution detected an infinite loop, profile "
    "cycle: {}\n"
)
MAX_RECURSION_TEMPLATE: Final = (
    "Maximum recursive credential process resolution reached (4).\n"
    "Profiles seen: {}"
)
NO_REGION_MESSAGE: Final = (
    "You must specify a region. You can also configure your region by "
    'running "aws configure".'
)


def enhanced(code: str, message: str) -> str:
    """Coded framing: `An error occurred (<code>): <message>` stripped."""
    return f"{ERROR_PREFIX}An error occurred ({code}): {message.strip()}\n"


def plain(message: str) -> str:
    """write_error's framing (errorformat.py:28-41): the stripped message."""
    return f"{ERROR_PREFIX}{message.strip()}\n"


def json_error(fields: Mapping[str, str]) -> str:
    """JSONFormatter over the error dict (awscli/formatter.py:94-110)."""
    return json.dumps(dict(fields), indent=4, ensure_ascii=False) + "\n"


def text_error(fields: Mapping[str, str]) -> str:
    """TextFormatter over a flat dict: values in sorted-key order, tab-joined
    (awscli/text.py:74-118)."""
    return "\t".join(fields[key] for key in sorted(fields)) + "\n"


def coded_formats(code: str, message: str) -> dict[str, str]:
    """A coded handler's stderr under each supported error format."""
    fields = {"Code": code, "Message": message}
    return {
        "enhanced": enhanced(code, message),
        "legacy": plain(message),
        "json": json_error(fields),
        "text": text_error(fields),
    }


def choice_error(argument: str, value: str, *, suggestion: str = "") -> str:
    """CLIArgParser._check_value's ArgumentError text (difflib suggestions
    at cutoff 0.8) and the usage tail (awscli/argparser.py:66-80, 104-116).
    """
    hint = f"\nMaybe you meant:\n\n  * {suggestion}" if suggestion else ""
    return (
        f"argument {argument}: Found invalid choice '{value}'\n{hint}\n\n"
        + MAIN_USAGE
    )


@dataclass(frozen=True)
class Scenario:
    """Fixtures and invocation for one run.

    `files` maps root-relative paths to contents; None makes a directory.
    `modes` sets the final mode of a written path. `env` values and file
    contents may use the ROOT/HOME placeholders; `unset` removes keys from
    the sandbox environment, and `cwd` is root-relative.
    """

    config: str | bytes = ""
    credentials: str | bytes = ""
    files: Mapping[str, str | bytes | None] = field(default_factory=dict)
    modes: Mapping[str, int] = field(default_factory=dict)
    env: Mapping[str, str] = field(default_factory=dict)
    unset: tuple[str, ...] = ()
    globals_: tuple[str, ...] = ()
    cmd_args: tuple[str, ...] = ()
    cwd: str | None = None


@dataclass(frozen=True)
class Outcome:
    """What the command must return; stderr may use placeholders.

    With `parts`, `stderr` is only the AWS-authored prefix: the rest is
    CPython's or a library's wording, and only `parts` must appear in it.
    """

    returncode: int
    stderr: str = ""
    stdout: bytes = b""
    parts: tuple[str, ...] | None = None


def fails(returncode: int, stderr: str) -> Outcome:
    return Outcome(returncode=returncode, stderr=stderr)


def fails_with_prefix(returncode: int, prefix: str, *parts: str) -> Outcome:
    """A failure whose stderr starts with `prefix` and contains `parts`."""
    return Outcome(returncode=returncode, stderr=prefix, parts=parts)


def succeeds(stdout: bytes = STATIC_OUTPUT) -> Outcome:
    return Outcome(returncode=0, stdout=stdout)


def expand(text: str, sandbox: Sandbox) -> str:
    return text.replace(ROOT_PLACEHOLDER, str(sandbox.root)).replace(
        HOME_PLACEHOLDER, str(sandbox.home)
    )


def write_content(
    sandbox: Sandbox, relative: str, content: str | bytes | None
) -> None:
    if content is None:
        (sandbox.root / relative).mkdir(parents=True, exist_ok=True)
    elif isinstance(content, bytes):
        sandbox.write(relative, content)
    else:
        sandbox.write(relative, expand(content, sandbox))


def build(sandbox: Sandbox, scenario: Scenario) -> None:
    """Write the scenario's files, apply its modes, and seal the sandbox."""
    write_content(sandbox, "config", scenario.config)
    write_content(sandbox, "credentials", scenario.credentials)
    for relative, content in scenario.files.items():
        write_content(sandbox, relative, content)
    for relative, mode in scenario.modes.items():
        (sandbox.root / relative).chmod(mode)
    sandbox.seal()


def scenario_env(
    sandbox: Sandbox, proxy: AsyncTLSInterceptProxy, scenario: Scenario
) -> dict[str, str]:
    env = sandbox.env(proxy)
    env.update(
        {key: expand(value, sandbox) for key, value in scenario.env.items()}
    )
    for key in scenario.unset:
        env.pop(key, None)
    return env


@pytest_asyncio.fixture
async def stub() -> AsyncIterator[Stub]:
    """The TLS intercept proxy and its server, answering 400 to anything.

    The tripwire makes any request a scenario does not plan for visible in
    the run's requests.
    """
    async with mock_server() as (server, proxy):
        server.set_default_response(unexpected_request())
        yield server, proxy


async def run_scenario(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    scenario: Scenario,
) -> CliRun:
    build(sandbox, scenario)
    return await run_built(aws_cli, sandbox, stub, scenario)


async def run_built(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    scenario: Scenario,
) -> CliRun:
    """Run `scenario` in a sandbox `build` already prepared."""
    server, proxy = stub
    cwd = None if scenario.cwd is None else sandbox.root / scenario.cwd
    return await run_export_credentials(
        aws_cli,
        sandbox,
        [server],
        scenario_env(sandbox, proxy, scenario),
        globals_=scenario.globals_,
        cmd_args=scenario.cmd_args,
        cwd=cwd,
    )


def assert_outcome(run: CliRun, outcome: Outcome, sandbox: Sandbox) -> None:
    """The run matched `outcome`, sent nothing, and wrote nothing."""
    report = run.describe()
    stderr: bytes | BytesStartingWith = expand(
        outcome.stderr, sandbox
    ).encode()
    if outcome.parts is not None:
        stderr = BytesStartingWith(
            stderr,
            tuple(expand(part, sandbox).encode() for part in outcome.parts),
        )
    assert run.returncode == outcome.returncode, report
    assert run.stdout == outcome.stdout, report
    assert run.stderr == stderr, report
    assert run.requests == (), report
    assert run.changes == {}, report


async def assert_scenario(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    scenario: Scenario,
    outcome: Outcome,
) -> None:
    run = await run_scenario(aws_cli, sandbox, stub, scenario)
    assert_outcome(run, outcome, sandbox)


# The format lookup of FilteredExceptionHandler (errorhandler.py:184-233)
# for one ConfigurationError: the flag, then AWS_CLI_ERROR_FORMAT, then
# the active profile's cli_error_format, lowercased; an unknown value
# logs an invisible warning and renders enhanced.
SSO_SCENARIO: Final = Scenario(config=SSO_INCOMPLETE_CONFIG)
SSO_FORMATS: Final = coded_formats("Configuration", SSO_LOAD_MESSAGE)
# The json and text rows spelled out once, anchoring json_error and
# text_error: indent 4, ensure_ascii off, the trailing newline kept inside
# Message, and the text form's extra blank line from that newline.
SSO_JSON: Final = (
    "{\n"
    '    "Code": "Configuration",\n'
    '    "Message": "Unable to retrieve credentials: The profile '
    '\\"default\\" is configured to use SSO but is missing required '
    'configuration: sso_role_name, sso_start_url, sso_region\\n"\n'
    "}\n"
)
SSO_TEXT: Final = "Configuration\t" + SSO_LOAD_MESSAGE + "\n"


@pytest.mark.parametrize(
    ("scenario", "stderr"),
    [
        pytest.param(SSO_SCENARIO, SSO_FORMATS["enhanced"], id="default"),
        pytest.param(
            replace(SSO_SCENARIO, globals_=("--cli-error-format", "legacy")),
            SSO_FORMATS["legacy"],
            id="flag-legacy",
        ),
        pytest.param(
            replace(SSO_SCENARIO, env={ERROR_FORMAT_VAR: "bogus"}),
            SSO_FORMATS["enhanced"],
            id="env-bogus",
        ),
        pytest.param(
            replace(SSO_SCENARIO, globals_=("--cli-error-format", "json")),
            SSO_JSON,
            id="flag-json",
        ),
        pytest.param(
            replace(SSO_SCENARIO, env={ERROR_FORMAT_VAR: "JSON"}),
            SSO_FORMATS["json"],
            id="env-json-uppercase",
        ),
        pytest.param(
            replace(
                SSO_SCENARIO,
                config=SSO_INCOMPLETE_CONFIG + "cli_error_format = json\n",
            ),
            SSO_FORMATS["json"],
            id="profile-json",
        ),
        pytest.param(
            replace(SSO_SCENARIO, globals_=("--cli-error-format", "text")),
            SSO_TEXT,
            id="flag-text",
        ),
        pytest.param(
            replace(
                SSO_SCENARIO,
                globals_=("--cli-error-format", "legacy"),
                env={ERROR_FORMAT_VAR: "json"},
            ),
            SSO_FORMATS["legacy"],
            id="flag-beats-env",
        ),
        pytest.param(
            replace(
                SSO_SCENARIO,
                config=SSO_INCOMPLETE_CONFIG + "cli_error_format = json\n",
                env={ERROR_FORMAT_VAR: "legacy"},
            ),
            SSO_FORMATS["legacy"],
            id="env-beats-profile",
        ),
    ],
)
async def test_error_format_setting_frames_configuration_error(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    scenario: Scenario,
    stderr: str,
) -> None:
    await assert_scenario(
        aws_cli,
        sandbox,
        stub,
        scenario,
        fails(253, stderr),
    )


# Service errors under --cli-error-format json, which renders the error
# dict's modeled members (errorhandler.py:283-313).
JSON_FORMAT: Final = ("--cli-error-format", "json")
STS_HOST: Final = "sts.us-east-1.amazonaws.com"
STS_ROUTE: Final[RouteKey] = ("POST", STS_HOST, "/")
SOURCE_KEY: Final = "AKIDSRC"
SOURCE_SECRET: Final = "SRC-secret"
ASSUME_ROLE_CONFIG: Final = (
    "[default]\n"
    f"role_arn = {ROLE_ARN}\n"
    "role_session_name = framing\n"
    "source_profile = base\n"
    "[profile base]\n"
    f"aws_access_key_id = {SOURCE_KEY}\n"
    f"aws_secret_access_key = {SOURCE_SECRET}\n"
)
ASSUME_ROLE_BODY: Final = (
    b"Action=AssumeRole&Version=2011-06-15&RoleSessionName=framing"
    b"&RoleArn=arn%3Aaws%3Aiam%3A%3A123456789012%3Arole%2Fframing"
)
# The query serializer's form body (botocore serialize.py:225-233).
FORM_CONTENT_TYPE: Final = "application/x-www-form-urlencoded; charset=utf-8"
SIGV4: Final = "AWS4-HMAC-SHA256"
# A 403 AccessDenied ErrorResponse: a ClientError (rc 254) whose modeled
# members are Code and Message only, so the json form drops the XML's
# Type.
STS_DENIED_JSON: Final = json_error(
    {"Code": "AccessDenied", "Message": "stubbed STS rejection"}
)


def header_values(
    values: Mapping[str, str],
) -> tuple[tuple[str, str | None], ...]:
    """Every compared header paired with its value in `values`, else None."""
    return tuple((name, values.get(name)) for name in COMPARED_HEADERS)


# The AssumeRole call SigV4-signed by the static source profile, so no
# X-Amz-Security-Token (botocore auth.py:454-466), in the us-east-1 STS
# scope.
ASSUME_ROLE_REQUEST: Final = NormalizedRequest(
    method="POST",
    host=STS_HOST,
    path="/",
    target="/",
    query=(),
    content_type=FORM_CONTENT_TYPE,
    body_bytes=ASSUME_ROLE_BODY,
    headers=header_values(
        {
            "authorization": SIGV4,
            "x-amz-date": AMZ_DATE_PLACEHOLDER,
            "content-type": FORM_CONTENT_TYPE,
        }
    ),
    user_agent=None,
    signing_scope=(SOURCE_KEY, SCOPE_DATE_PLACEHOLDER, "us-east-1", "sts"),
)


def assert_signed_by_source(run: CliRun) -> None:
    (request,) = run.raw_requests
    assert_signature(request, SOURCE_KEY, SOURCE_SECRET)


@dataclass(frozen=True)
class ServiceError:
    """One stubbed service rejection and the CLI's answer to it.

    `request` is the one request the CLI must send, `stderr` the expected
    stderr in the json error format, and `verify` checks the wire request
    (SigV4 or DPoP).
    """

    route: RouteKey
    response: Callable[[], HTTPResponse]
    request: NormalizedRequest
    stderr: str
    verify: Callable[[CliRun], None]


async def assert_service_error(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    error: ServiceError,
) -> None:
    """Seal the sandbox and run the command against `error`.

    The CLI sends exactly the one request, exits 254 with the json
    format's stderr, and leaves the sandbox as sealed.
    """
    server, proxy = stub
    sandbox.seal()
    script: dict[RouteKey, list[HTTPResponse]] = {
        error.route: [error.response()]
    }

    run = await run_export_credentials(
        aws_cli,
        sandbox,
        [server],
        sandbox.env(proxy),
        globals_=JSON_FORMAT,
        handlers={server: lambda: routed(script)},
    )

    report = run.describe()
    assert run.returncode == 254, report
    assert run.stdout == b"", report
    assert run.stderr == error.stderr.encode(), report
    assert run.requests == (error.request,), report
    error.verify(run)
    assert run.changes == {}, report


STS_DENIED: Final = ServiceError(
    route=STS_ROUTE,
    response=sts_error_xml,
    request=ASSUME_ROLE_REQUEST,
    stderr=STS_DENIED_JSON,
    verify=assert_signed_by_source,
)


async def test_sts_client_error_renders_as_json(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    sandbox.config.write_text(ASSUME_ROLE_CONFIG, encoding="utf-8")

    await assert_service_error(aws_cli, sandbox, stub, STS_DENIED)


SIGNIN_HOST: Final = "us-east-1.signin.aws.amazon.com"
SIGNIN_URL: Final = f"https://{SIGNIN_HOST}/v1/token"
SIGNIN_ROUTE: Final[RouteKey] = ("POST", SIGNIN_HOST, "/v1/token")
LOGIN_SESSION: Final = "framing-session"
# Expired long ago, so the first freeze refreshes through signin.
EXPIRED_LOGIN_TOKEN: Final = {
    "accessKeyId": "AKIDLOGIN",
    "secretAccessKey": "LOGIN-secret",
    "sessionToken": "LOGIN-token",
    "accountId": ACCOUNT,
    "expiresAt": "2000-01-01T00:00:00Z",
}
LOGIN_REFRESH_BODY: Final = (
    b'{"clientId": "framing-client", "refreshToken": "framing-refresh", '
    b'"grantType": "refresh_token"}'
)
# The rest-json serializer's Content-Type for a structured body (botocore
# serialize.py:1046-1056).
JSON_CONTENT_TYPE: Final = "application/json"
# The refresh client is UNSIGNED (botocore credentials.py:2560-2566), so
# CreateOAuth2Token carries no Authorization or X-Amz-Date and proves
# possession with the DPoP header alone (utils.py:4212-4258).
LOGIN_REFRESH_REQUEST: Final = NormalizedRequest(
    method="POST",
    host=SIGNIN_HOST,
    path="/v1/token",
    target="/v1/token",
    query=(),
    content_type=JSON_CONTENT_TYPE,
    body_bytes=LOGIN_REFRESH_BODY,
    headers=header_values({"content-type": JSON_CONTENT_TYPE}),
    user_agent=None,
    signing_scope=None,
)
# A modeled ValidationException (botocore data/signin service-2.json):
# the json form keeps the response's modeled keys, its extra `error`
# member included, in response order.
SIGNIN_INVALID_JSON: Final = json_error(
    {
        "Message": "bad request",
        "Code": "ValidationException",
        "error": "INVALID_REQUEST",
        "message": "bad request",
    }
)


def signin_validation_error() -> HTTPResponse:
    return HTTPResponse.json(
        {"error": "INVALID_REQUEST", "message": "bad request"},
        status=400,
        headers={"x-amzn-errortype": "ValidationException"},
    )


def assert_signin_dpop(run: CliRun) -> None:
    (request,) = run.raw_requests
    assert_dpop(request.headers["dpop"], SAMPLE_DPOP_PEM, SIGNIN_URL)


SIGNIN_INVALID: Final = ServiceError(
    route=SIGNIN_ROUTE,
    response=signin_validation_error,
    request=LOGIN_REFRESH_REQUEST,
    stderr=SIGNIN_INVALID_JSON,
    verify=assert_signin_dpop,
)


async def test_signin_client_error_renders_as_json(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    sandbox.config.write_text(
        f"[default]\nlogin_session = {LOGIN_SESSION}\n", encoding="utf-8"
    )
    write_login_token(
        sandbox.home / LOGIN_TOKEN_CACHE,
        LOGIN_SESSION,
        accessToken=EXPIRED_LOGIN_TOKEN,
        refreshToken="framing-refresh",
        clientId="framing-client",
        dpopKey=SAMPLE_DPOP_PEM,
    )

    await assert_service_error(aws_cli, sandbox, stub, SIGNIN_INVALID)


# NoRegionError from signing a configured-endpoint AssumeRole with no
# region (botocore signers.py:250-306), raised at freeze time outside the
# export try, without a request. `--region ""` is falsy, so it leaves the
# region unset (awscli/clidriver.py:634-639).
NO_REGION_SCENARIO: Final = Scenario(
    config=ASSUME_ROLE_CONFIG,
    env={"AWS_ENDPOINT_URL_STS": f"https://{STS_HOST}"},
    unset=REGION_VARS,
)


async def test_no_region_error_ignores_empty_region_flag(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    await assert_scenario(
        aws_cli,
        sandbox,
        stub,
        replace(NO_REGION_SCENARIO, globals_=("--region", "")),
        fails(253, enhanced("NoRegion", NO_REGION_MESSAGE)),
    )


# ProfileNotFound for the selected profile, wrapped by exportcreds.py:
# 268-275. AWS_PROFILE beats AWS_DEFAULT_PROFILE, and a profile that only
# the credentials file defines exists.
def missing_profile(name: str) -> Outcome:
    """ProfileNotFound for `name`, whatever its framing."""
    return fails_with_prefix(
        253, ERROR_PREFIX, no_profile_message(name).strip()
    )


@pytest.mark.parametrize(
    ("scenario", "outcome"),
    [
        # Upstream bug, matched for parity: the error-format lookup raises
        # ProfileNotFound again, outside the KeyError and AttributeError it
        # catches, so the coded handler falls back to plain framing without
        # "An error occurred (Configuration)" (errorhandler.py:190-198,
        # 229-234).
        pytest.param(
            Scenario(globals_=("--profile", "nosuch")),
            fails(253, plain(no_profile_message("nosuch"))),
            id="profile-flag",
        ),
        pytest.param(
            Scenario(env={"AWS_DEFAULT_PROFILE": "nosuch"}),
            missing_profile("nosuch"),
            id="aws-default-profile",
        ),
        pytest.param(
            Scenario(
                env={"AWS_PROFILE": "nosuch", "AWS_DEFAULT_PROFILE": "other"}
            ),
            missing_profile("nosuch"),
            id="aws-profile-beats-default-profile",
        ),
        pytest.param(
            Scenario(
                globals_=("--profile", "onlycreds"),
                credentials="[onlycreds]\n" + STATIC_KEYS,
            ),
            succeeds(),
            id="profile-only-in-credentials-file",
        ),
    ],
)
async def test_selected_profile_must_exist(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    scenario: Scenario,
    outcome: Outcome,
) -> None:
    await assert_scenario(aws_cli, sandbox, stub, scenario, outcome)


# From the session-initialized handlers on, the format lookup reads the
# --profile profile (errorhandler.py:184-200): the export parse's --format
# error renders in profile other's json format, not default's legacy.
LEGACY_DEFAULT_CONFIG: Final = (
    "[default]\ncli_error_format = legacy\n"
    "[profile other]\ncli_error_format = json\n" + STATIC_KEYS
)
OUTPUT_CHOICE_ERROR: Final = choice_error("--output", "bogus")
ENDPOINT_FOO_ERROR: Final = ENDPOINT_TEMPLATE.format("foo")
FORMAT_CHOICE_ERROR: Final = choice_error("--format", "bogus")


async def test_error_format_lookup_reads_profile_flag_profile(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    await assert_scenario(
        aws_cli,
        sandbox,
        stub,
        Scenario(
            config=LEGACY_DEFAULT_CONFIG,
            globals_=("--profile", "other"),
            cmd_args=("--format", "bogus"),
        ),
        fails(
            252,
            json_error(
                {"Code": "ParamValidation", "Message": FORMAT_CHOICE_ERROR}
            ),
        ),
    )


# The recursion barrier (exportcreds.py:223-264). `profile` is the session's
# profile variable, `default` only when it is None. The chain is one CSV
# row, so a quoted field keeps a profile name's comma; four or more
# entries, or the current profile among them, raise ConfigurationError
# outside the export try (the cycle text keeps its trailing newline).
STATIC_FILES: Final = Scenario(credentials=STATIC_DEFAULT)
CYCLE_DEFAULT: Final = CYCLE_TEMPLATE.format("default -> default")
COMMA_PROFILE: Final = Scenario(
    config="[profile bar,baz]\n" + STATIC_KEYS,
    globals_=("--profile", "bar,baz"),
)


@pytest.mark.parametrize(
    ("scenario", "outcome"),
    [
        pytest.param(
            replace(STATIC_FILES, env={CHAIN_VAR: "a,b,c,d"}),
            fails(
                253,
                enhanced(
                    "Configuration",
                    MAX_RECURSION_TEMPLATE.format("a -> b -> c -> d"),
                ),
            ),
            id="four-entries",
        ),
        pytest.param(
            replace(STATIC_FILES, env={CHAIN_VAR: "default"}),
            fails(253, enhanced("Configuration", CYCLE_DEFAULT)),
            id="default-cycle",
        ),
        pytest.param(
            Scenario(
                config="[profile p]\n" + STATIC_KEYS,
                globals_=("--profile", "p"),
                env={CHAIN_VAR: "x,p"},
            ),
            fails(
                253,
                enhanced(
                    "Configuration", CYCLE_TEMPLATE.format("x -> p -> p")
                ),
            ),
            id="named-profile-cycle",
        ),
        pytest.param(
            replace(
                STATIC_FILES,
                env={CHAIN_VAR: "default"},
                globals_=("--cli-error-format", "json"),
            ),
            fails(
                253,
                json_error(
                    {"Code": "Configuration", "Message": CYCLE_DEFAULT}
                ),
            ),
            id="json-keeps-trailing-newline",
        ),
        pytest.param(
            replace(STATIC_FILES, env={CHAIN_VAR: "a,b,c"}),
            succeeds(),
            id="three-entries",
        ),
        pytest.param(
            replace(COMMA_PROFILE, env={CHAIN_VAR: "foo,bar,baz"}),
            succeeds(),
            id="comma-name-no-cycle",
        ),
        pytest.param(
            replace(COMMA_PROFILE, env={CHAIN_VAR: 'foo,"bar,baz"'}),
            fails(
                253,
                enhanced(
                    "Configuration",
                    CYCLE_TEMPLATE.format("foo -> bar,baz -> bar,baz"),
                ),
            ),
            id="comma-name-cycle",
        ),
    ],
)
async def test_recursion_barrier_checks_chain_before_credentials(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    scenario: Scenario,
    outcome: Outcome,
) -> None:
    await assert_scenario(aws_cli, sandbox, stub, scenario, outcome)


# What _update_recursion_barrier hands the credential_process child: the
# chain plus the current profile as one CSV row (exportcreds.py:240-254).
# The helper returns the variable as its SessionToken.
CHAIN_HELPER: Final = (
    "import json, os\n"
    "print(json.dumps({'Version': 1, 'AccessKeyId': 'AKIDPROC', "
    "'SecretAccessKey': 'PROC-secret', "
    f"'SessionToken': os.environ.get({CHAIN_VAR!r})}}))\n"
)


@pytest.mark.parametrize(
    ("profile_section", "globals_", "chain", "seen"),
    [
        pytest.param("default", (), None, "default", id="unset"),
        pytest.param("default", (), "a,b,c", "a,b,c,default", id="three"),
        pytest.param("profile p", ("--profile", "p"), None, "p", id="named"),
        # Upstream bug, matched for parity: str.strip() of the serialized
        # chain drops a profile name's outer whitespace, so the child of
        # profile "p " sees "p" and cannot detect that cycle
        # (exportcreds.py:250-254).
        pytest.param(
            'profile "p "', ("--profile", "p "), None, "p", id="trailing-space"
        ),
    ],
)
async def test_recursion_barrier_passes_chain_to_credential_process(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    profile_section: str,
    globals_: tuple[str, ...],
    chain: str | None,
    seen: str,
) -> None:
    command = sandbox.helper("chain-helper.py", CHAIN_HELPER)
    scenario = Scenario(
        config=f"[{profile_section}]\ncredential_process = {command}\n",
        globals_=globals_,
        env={} if chain is None else {CHAIN_VAR: chain},
    )

    await assert_scenario(
        aws_cli,
        sandbox,
        stub,
        scenario,
        succeeds(export_credentials_output("AKIDPROC", "PROC-secret", seen)),
    )


def export_command(aws_cli: str, profile: str) -> str:
    """A credential_process running this CLI's export for `profile`."""
    return command_line(
        [aws_cli, "configure", "export-credentials", "--profile", profile]
    )


# A real nested run: each profile's credential_process is this CLI's own
# export-credentials for the next profile, so the chain reaches each child
# through its environment, the comma name quoted, until the third run
# finds profile a in it. Each level wraps its child's failure
# (credentials.py:1103-1118, exportcreds.py:266-275).
async def test_recursion_barrier_stops_nested_export_credentials(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    scenario = Scenario(
        config=(
            "[profile a]\n"
            f"credential_process = {export_command(aws_cli, 'b,c')}\n"
            "[profile b,c]\n"
            f"credential_process = {export_command(aws_cli, 'a')}\n"
        ),
        globals_=("--profile", "a"),
    )

    await assert_scenario(
        aws_cli,
        sandbox,
        stub,
        scenario,
        fails_with_prefix(
            253,
            f"{ERROR_PREFIX}An error occurred (Configuration): "
            "Unable to retrieve credentials: Error when retrieving "
            "credentials from custom-process: ",
            CYCLE_TEMPLATE.format("a -> b,c -> a").strip(),
        ),
    )


# Before any argument parsing, session.full_config parses the config file,
# then the credentials file (botocore session.py:384-418), each path
# through expandvars then expanduser and never made absolute
# (configloader.py:139-152). A configparser error or bad UTF-8 is
# ConfigParseError, framed by the entry-point chain whatever the error
# format (awscli/clidriver.py:117-137); a path that is not a regular file
# contributes nothing.
BROKEN: Final = "[broken\n"
# The sandbox names its files with the OS separator, as the CLI prints them.
CONFIG_UNPARSEABLE: Final = plain(
    UNPARSEABLE + os.path.join(ROOT_PLACEHOLDER, "config")
)
HOME_CFG_UNPARSEABLE: Final = plain(f"{UNPARSEABLE}{HOME_PLACEHOLDER}/cfg")


@pytest.mark.parametrize(
    ("scenario", "outcome"),
    [
        pytest.param(
            Scenario(config=BROKEN, credentials=STATIC_DEFAULT),
            fails(255, CONFIG_UNPARSEABLE),
            id="config-header",
        ),
        pytest.param(
            Scenario(credentials=BROKEN),
            fails(
                255,
                plain(
                    UNPARSEABLE
                    + os.path.join(ROOT_PLACEHOLDER, "credentials")
                ),
            ),
            id="credentials-header",
        ),
        pytest.param(
            Scenario(
                config="[default]\ns3 =\n  junk\n", credentials=STATIC_DEFAULT
            ),
            fails(255, CONFIG_UNPARSEABLE),
            id="nested-line-without-equals",
        ),
        pytest.param(
            Scenario(
                config=BROKEN,
                credentials=STATIC_DEFAULT,
                env={ERROR_FORMAT_VAR: "json"},
            ),
            fails(255, CONFIG_UNPARSEABLE),
            id="ignores-format-env",
        ),
        pytest.param(
            Scenario(
                files={"home/cfg": BROKEN},
                env={"AWS_CONFIG_FILE": "~/cfg"},
                credentials=STATIC_DEFAULT,
            ),
            fails(255, HOME_CFG_UNPARSEABLE),
            id="tilde-expanded",
        ),
    ],
)
async def test_config_parse_failure_frames_expanded_path(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    scenario: Scenario,
    outcome: Outcome,
) -> None:
    await assert_scenario(aws_cli, sandbox, stub, scenario, outcome)


# configparser's read() skips a file it cannot open, so a mode-000
# malformed alias file is an empty one. Where the runner can still read
# the file (root, or no POSIX modes), the check cannot be set up.
async def test_unreadable_malformed_alias_file_is_skipped(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    scenario = Scenario(
        credentials=STATIC_DEFAULT,
        files={ALIAS_FILE: BROKEN},
        modes={ALIAS_FILE: 0o000},
    )
    build(sandbox, scenario)
    if os.access(sandbox.root / ALIAS_FILE, os.R_OK):
        pytest.skip("the runner can read a mode-000 file")

    run = await run_built(aws_cli, sandbox, stub, scenario)

    assert_outcome(run, succeeds(), sandbox)


# The alias file `~/.aws/cli/alias` (expanded when awscli.alias is
# imported) is parsed without subsections when it exists
# (awscli/alias.py:43-67); a parse error is ConfigParseError and a directory
# is ConfigNotFound, both through the entry-point chain after the config
# files are parsed and before every later stage.
VALID_ALIASES: Final = "[toplevel]\nwhoami = sts get-caller-identity\n"
# alias.py:47 joins the alias path with the OS separator.
ALIAS_PATH: Final = os.path.join(HOME_PLACEHOLDER, ".aws", "cli", "alias")
ALIAS_UNPARSEABLE: Final = plain(f"{UNPARSEABLE}{ALIAS_PATH}")


@pytest.mark.parametrize(
    ("scenario", "outcome"),
    [
        pytest.param(
            Scenario(files={ALIAS_FILE: BROKEN}, credentials=STATIC_DEFAULT),
            fails(255, ALIAS_UNPARSEABLE),
            id="unclosed-header",
        ),
        pytest.param(
            Scenario(files={ALIAS_FILE: None}, credentials=STATIC_DEFAULT),
            fails(
                255,
                plain(
                    "The specified config file "
                    f"({ALIAS_PATH}) could not be found."
                ),
            ),
            id="directory",
        ),
        pytest.param(
            Scenario(
                files={ALIAS_FILE: VALID_ALIASES},
                credentials=STATIC_DEFAULT,
            ),
            succeeds(),
            id="valid",
        ),
    ],
)
async def test_alias_file_failure_frames_alias_path(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    scenario: Scenario,
    outcome: Outcome,
) -> None:
    await assert_scenario(aws_cli, sandbox, stub, scenario, outcome)


# add_timestamp_parser (awscli/customizations/timestampformat.py:
# 49-80): the scoped config's cli_timestamp_format must be exactly `wire`
# or `iso8601`, else a coded ConfigurationError, even with static
# credentials.
def timestamp_error(value: str) -> Outcome:
    return fails(
        253, enhanced("Configuration", TIMESTAMP_TEMPLATE.format(value))
    )


def timestamp_config(value: str) -> str:
    return f"[default]\ncli_timestamp_format = {value}\n" + STATIC_KEYS


@pytest.mark.parametrize(
    ("scenario", "outcome"),
    [
        pytest.param(
            Scenario(config=timestamp_config("bogus")),
            timestamp_error("bogus"),
            id="bogus",
        ),
        pytest.param(
            Scenario(config=timestamp_config("ISO8601")),
            timestamp_error("ISO8601"),
            id="case-sensitive",
        ),
        pytest.param(
            Scenario(config=timestamp_config("wire")), succeeds(), id="wire"
        ),
        pytest.param(
            Scenario(config=timestamp_config("iso8601")),
            succeeds(),
            id="iso8601",
        ),
    ],
)
async def test_cli_timestamp_format_validation(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    scenario: Scenario,
    outcome: Outcome,
) -> None:
    await assert_scenario(aws_cli, sandbox, stub, scenario, outcome)


# add_binary_formatter (awscli/customizations/binaryformat.py:70-91):
# --cli-binary-format when given, else the scoped cli_binary_format.
def binary_config(value: str) -> str:
    return f"[default]\ncli_binary_format = {value}\n" + STATIC_KEYS


@pytest.mark.parametrize(
    ("scenario", "outcome"),
    [
        # Upstream bug, matched for parity: an unknown name is a KeyError
        # from the format table, which the general handler prints with
        # rc 255 (binaryformat.py:70-91); its text is the key's repr.
        pytest.param(
            Scenario(config=binary_config("bogus")),
            fails_with_prefix(255, ERROR_PREFIX, "bogus"),
            id="bogus",
        ),
        pytest.param(
            Scenario(config=binary_config("raw-in-base64-out")),
            succeeds(),
            id="raw-in-base64-out",
        ),
        pytest.param(
            Scenario(
                config=binary_config("bogus"),
                globals_=("--cli-binary-format", "base64"),
            ),
            succeeds(),
            id="flag-overrides-profile",
        ),
    ],
)
async def test_cli_binary_format_validation(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    scenario: Scenario,
    outcome: Outcome,
) -> None:
    await assert_scenario(aws_cli, sandbox, stub, scenario, outcome)


# _resolve_timeout (awscli/customizations/globalargs.py:117-135) runs
# int() on --cli-read-timeout at top-level-args-parsed, so a bad value
# fails through the general handler (rc 255) even with static
# credentials. The rest of the message is int()'s.
async def test_non_integer_read_timeout_fails(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    await assert_scenario(
        aws_cli,
        sandbox,
        stub,
        Scenario(
            credentials=STATIC_DEFAULT,
            globals_=("--cli-read-timeout", "abc"),
        ),
        fails_with_prefix(255, ERROR_PREFIX, "abc"),
    )


# The export parse and its six formatters (exportcreds.py:30-166):
# `process` is the credential_process JSON, the others one line per
# variable; SessionToken and the expiry (isoformat) appear only when set.
FULL_ENV_CREDENTIALS: Final = {
    **ENV_CREDENTIALS,
    "AWS_SESSION_TOKEN": ENV_TOKEN,
    "AWS_CREDENTIAL_EXPIRATION": "2099-01-01T00:00:00Z",
}
EXPIRATION_TEXT: Final = "2099-01-01T00:00:00+00:00"
FULL_VALUES: Final = (
    ("AWS_ACCESS_KEY_ID", ENV_KEY),
    ("AWS_SECRET_ACCESS_KEY", ENV_SECRET),
    ("AWS_SESSION_TOKEN", ENV_TOKEN),
    ("AWS_CREDENTIAL_EXPIRATION", EXPIRATION_TEXT),
)
LINE_TEMPLATES: Final = {
    "env": "export {}={}\n",
    "env-no-export": "{}={}\n",
    "powershell": '$Env:{}="{}"\n',
    "windows-cmd": "set {}={}\n",
    "fish": 'set -gx {} "{}"\n',
}


# The process format spelled out once, anchoring
# export_credentials_output: two-space indent, `": "` separators, keys in
# this order, and a trailing newline (exportcreds.py:131-153).
FULL_PROCESS_OUTPUT: Final = (
    b"{\n"
    b'  "Version": 1,\n'
    b'  "AccessKeyId": "AKIDENV",\n'
    b'  "SecretAccessKey": "ENV-secret",\n'
    b'  "SessionToken": "ENV-token",\n'
    b'  "Expiration": "2099-01-01T00:00:00+00:00"\n'
    b"}\n"
)


def lines(template: str, values: tuple[tuple[str, str], ...]) -> bytes:
    return "".join(template.format(*pair) for pair in values).encode()


@pytest.mark.parametrize(
    ("cmd_args", "env", "stdout"),
    [
        pytest.param(
            ("--format", "process"),
            FULL_ENV_CREDENTIALS,
            FULL_PROCESS_OUTPUT,
            id="process",
        ),
        *(
            pytest.param(
                ("--format", name),
                FULL_ENV_CREDENTIALS,
                lines(template, FULL_VALUES),
                id=name,
            )
            for name, template in LINE_TEMPLATES.items()
        ),
        pytest.param((), ENV_CREDENTIALS, ENV_OUTPUT, id="default-process"),
        pytest.param(
            ("--format", "env"),
            ENV_CREDENTIALS,
            lines(LINE_TEMPLATES["env"], FULL_VALUES[:2]),
            id="env-keys-only",
        ),
    ],
)
async def test_format_renders_each_output(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    cmd_args: tuple[str, ...],
    env: Mapping[str, str],
    stdout: bytes,
) -> None:
    await assert_scenario(
        aws_cli,
        sandbox,
        stub,
        Scenario(env=env, cmd_args=cmd_args),
        succeeds(stdout),
    )


# Values are written verbatim: no shell quoting or escaping in the
# per-line formats (exportcreds.py:58-77), JSON string escaping in
# process. Keys and tokens use the base64 alphabet, so `/`, `+`, and `=`
# are real; `"` and `$` show that nothing else is escaped either.
SPECIAL_ENV_CREDENTIALS: Final = {
    "AWS_ACCESS_KEY_ID": "AKID/+=",
    "AWS_SECRET_ACCESS_KEY": 'se/cr+et="$HOME"',
    "AWS_SESSION_TOKEN": "To/k+en==",
}


@pytest.mark.parametrize(
    ("format_name", "stdout"),
    [
        pytest.param(
            "process",
            b"{\n"
            b'  "Version": 1,\n'
            b'  "AccessKeyId": "AKID/+=",\n'
            b'  "SecretAccessKey": "se/cr+et=\\"$HOME\\"",\n'
            b'  "SessionToken": "To/k+en=="\n'
            b"}\n",
            id="process",
        ),
        pytest.param(
            "env",
            b"export AWS_ACCESS_KEY_ID=AKID/+=\n"
            b'export AWS_SECRET_ACCESS_KEY=se/cr+et="$HOME"\n'
            b"export AWS_SESSION_TOKEN=To/k+en==\n",
            id="env",
        ),
        pytest.param(
            "env-no-export",
            b"AWS_ACCESS_KEY_ID=AKID/+=\n"
            b'AWS_SECRET_ACCESS_KEY=se/cr+et="$HOME"\n'
            b"AWS_SESSION_TOKEN=To/k+en==\n",
            id="env-no-export",
        ),
        pytest.param(
            "powershell",
            b'$Env:AWS_ACCESS_KEY_ID="AKID/+="\n'
            b'$Env:AWS_SECRET_ACCESS_KEY="se/cr+et="$HOME""\n'
            b'$Env:AWS_SESSION_TOKEN="To/k+en=="\n',
            id="powershell",
        ),
        pytest.param(
            "windows-cmd",
            b"set AWS_ACCESS_KEY_ID=AKID/+=\n"
            b'set AWS_SECRET_ACCESS_KEY=se/cr+et="$HOME"\n'
            b"set AWS_SESSION_TOKEN=To/k+en==\n",
            id="windows-cmd",
        ),
        pytest.param(
            "fish",
            b'set -gx AWS_ACCESS_KEY_ID "AKID/+="\n'
            b'set -gx AWS_SECRET_ACCESS_KEY "se/cr+et="$HOME""\n'
            b'set -gx AWS_SESSION_TOKEN "To/k+en=="\n',
            id="fish",
        ),
    ],
)
async def test_format_prints_values_verbatim(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    format_name: str,
    stdout: bytes,
) -> None:
    await assert_scenario(
        aws_cli,
        sandbox,
        stub,
        Scenario(
            env=SPECIAL_ENV_CREDENTIALS, cmd_args=("--format", format_name)
        ),
        succeeds(stdout),
    )


@pytest.mark.parametrize(
    ("scenario", "outcome"),
    [
        pytest.param(
            Scenario(cmd_args=("--format", "bogus")),
            fails(252, enhanced("ParamValidation", FORMAT_CHOICE_ERROR)),
            id="bogus",
        ),
        pytest.param(
            Scenario(cmd_args=("--format", "proces")),
            fails(
                252,
                enhanced(
                    "ParamValidation",
                    choice_error("--format", "proces", suggestion="process"),
                ),
            ),
            id="near-miss-suggestion",
        ),
        pytest.param(
            Scenario(cmd_args=("--format",)),
            fails_with_prefix(252, PARAM_VALIDATION_PREFIX, "--format"),
            id="missing-value",
        ),
    ],
)
async def test_format_choice_error(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    scenario: Scenario,
    outcome: Outcome,
) -> None:
    await assert_scenario(
        aws_cli,
        sandbox,
        stub,
        replace(scenario, env=ENV_CREDENTIALS),
        outcome,
    )


# Globals export-credentials accepts and ignores here: --output
# (exportcreds.py:185-193), --color, the pager, paginate, and auto-prompt
# switches, --cli-binary-format, a falsy --region, an --endpoint-url with
# a scheme (it never reaches credential clients), --no-verify-ssl (static
# credentials create no client), --no-sign-request, and the last
# --profile winning.
@pytest.mark.parametrize(
    "globals_",
    [
        pytest.param(("--no-sign-request",), id="no-sign-request"),
        pytest.param(
            ("--profile", "missing", "--profile", "default"),
            id="last-profile-wins",
        ),
        pytest.param(
            (
                "--output",
                "table",
                "--color",
                "off",
                "--no-paginate",
                "--no-cli-pager",
                "--no-cli-auto-prompt",
                "--cli-binary-format",
                "base64",
                "--region",
                "",
                "--endpoint-url",
                "https://x",
                "--no-verify-ssl",
            ),
            id="combined",
        ),
    ],
)
async def test_ignored_global_flags_keep_credentials_output(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    globals_: tuple[str, ...],
) -> None:
    await assert_scenario(
        aws_cli,
        sandbox,
        stub,
        Scenario(credentials=STATIC_DEFAULT, globals_=globals_),
        succeeds(),
    )


# Main-parse errors are coded ParamValidation (rc 252): an invalid choice
# with MainArgParser's usage, and a flag missing its value, whose wording
# is argparse's; a flag missing its value is the last token on the
# command line, so it sits after the command words. The --endpoint-url
# scheme check follows once the main parse succeeds.
@pytest.mark.parametrize(
    ("scenario", "outcome"),
    [
        pytest.param(
            Scenario(globals_=("--output", "bogus")),
            fails(252, enhanced("ParamValidation", OUTPUT_CHOICE_ERROR)),
            id="choice--output",
        ),
        pytest.param(
            Scenario(cmd_args=("--region",)),
            fails_with_prefix(252, PARAM_VALIDATION_PREFIX, "--region"),
            id="missing-value--region",
        ),
        pytest.param(
            Scenario(globals_=("--endpoint-url", "foo")),
            fails(252, enhanced("ParamValidation", ENDPOINT_FOO_ERROR)),
            id="endpoint-url-no-scheme",
        ),
    ],
)
async def test_global_argument_error_is_param_validation(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    scenario: Scenario,
    outcome: Outcome,
) -> None:
    await assert_scenario(
        aws_cli,
        sandbox,
        stub,
        replace(scenario, credentials=STATIC_DEFAULT),
        outcome,
    )


# Export-parse leftovers: `Unknown options: <a>, <b>`
# (awscli/argparser.py `format_unknown_options_error`). None of the
# names below is close enough to an option to draw a suggestion.
def unknown_options(*names: str) -> str:
    return f"Unknown options: {', '.join(names)}"


@pytest.mark.parametrize(
    ("scenario", "outcome"),
    [
        pytest.param(
            Scenario(globals_=("--bogus-flag",)),
            fails(
                252,
                enhanced("ParamValidation", unknown_options("--bogus-flag")),
            ),
            id="global-position",
        ),
        pytest.param(
            Scenario(cmd_args=("--bogus-flag", "v")),
            fails(
                252,
                enhanced(
                    "ParamValidation", unknown_options("--bogus-flag", "v")
                ),
            ),
            id="with-value",
        ),
        pytest.param(
            Scenario(cmd_args=("extra",)),
            fails(252, enhanced("ParamValidation", unknown_options("extra"))),
            id="positional",
        ),
    ],
)
async def test_unknown_options_are_reported(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    scenario: Scenario,
    outcome: Outcome,
) -> None:
    await assert_scenario(
        aws_cli,
        sandbox,
        stub,
        replace(scenario, credentials=STATIC_DEFAULT),
        outcome,
    )
