from collections.abc import Mapping, Sequence
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
    BytesStartingWith,
    CliRun,
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
    sts_success_xml,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("sts_routes_through_proxy"),
]

# What `session.create_client` checks when a credential provider builds
# its client on a cache miss (session.py:788-964, args.py:82-320,
# endpoint.py:388-460), and the request-time checks before the first byte
# (client.py:830-934). Every such error is raised outside the export try
# (exportcreds.py:266-283). The retry settings' checks are
# test_retries.py's.
EnvChanges = Mapping[str, str | None]

ACCOUNT: Final = "123456789012"
ROLE_A: Final = f"arn:aws:iam::{ACCOUNT}:role/RoleA"
WEB_ROLE: Final = f"arn:aws:iam::{ACCOUNT}:role/web"
STS_HOST: Final = "sts.us-east-1.amazonaws.com"
STS_ROUTE: Final[RouteKey] = ("POST", STS_HOST, "/")
FORM_CONTENT_TYPE: Final = "application/x-www-form-urlencoded; charset=utf-8"
SIGV4_ALGORITHM: Final = "AWS4-HMAC-SHA256"
SOURCE_SCOPE: Final = ("AKIDSRC", SCOPE_DATE_PLACEHOLDER, "us-east-1", "sts")
WEB_TOKEN: Final = "synthetic-web-token"
FUTURE_EXPIRATION: Final = "2099-01-01T00:00:00+00:00"
GENERATED_NAME: Final = "botocore-session-<epoch>"
GENERAL_RC: Final = 255
GENERAL_PREFIX: Final = b"\naws: [ERROR]: "
INVALID_CA_BUNDLE: Final = (
    "Invalid CA bundle: the configured value (ca_bundle, AWS_CA_BUNDLE, "
    "REQUESTS_CA_BUNDLE, or verify) resolved to an empty or whitespace-only "
    "string. Provide a valid path to a CA bundle file."
)
ROLE_CONFIG: Final = f"""\
[default]
role_arn = {ROLE_A}
source_profile = src
{{settings}}
[profile src]
aws_access_key_id = AKIDSRC
aws_secret_access_key = SRC-secret
{{source_settings}}"""
WEB_CONFIG: Final = f"""\
[default]
role_arn = {WEB_ROLE}
web_identity_token_file = {{token}}
{{settings}}"""


def role_response() -> HTTPResponse:
    return sts_success_xml(
        access_key="ASIAROLEA",
        secret_key="ROLEA-secret",
        session_token="ROLEA-token",
        assumed_role_id="AROAROLEA:s",
        arn=f"arn:aws:sts::{ACCOUNT}:assumed-role/RoleA/s",
    )


ROLE_OUTPUT: Final = export_credentials_output(
    "ASIAROLEA", "ROLEA-secret", "ROLEA-token", FUTURE_EXPIRATION
)
# The role cache's Credentials for role_response() (credentials.py:
# 759-766); the account comes from the assumed-role ARN.
ROLE_CACHE: Final = RoleCacheContent(
    {
        "Credentials": {
            "AccessKeyId": "ASIAROLEA",
            "SecretAccessKey": "ROLEA-secret",
            "SessionToken": "ROLEA-token",
            "Expiration": FUTURE_EXPIRATION,
            "AccountId": ACCOUNT,
        }
    }
)


def role_config(settings: str = "", source_settings: str = "") -> str:
    return ROLE_CONFIG.format(
        settings=settings, source_settings=source_settings
    )


def general_error(message: str) -> bytes:
    return GENERAL_PREFIX + f"{message}\n".encode()


def form_body(action: str, *pairs: tuple[str, str]) -> bytes:
    fields = [("Action", action), ("Version", "2011-06-15"), *pairs]
    return "&".join(
        f"{quote_plus(key)}="
        + (value if value == GENERATED_NAME else quote_plus(value))
        for key, value in fields
    ).encode()


async def run_scenario(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    script: Mapping[RouteKey, Sequence[HTTPResponse]] | None = None,
    *,
    env: EnvChanges | None = None,
    globals_: Sequence[str] = (),
) -> CliRun:
    """Seal the sandbox and run once with STS scripted by route.

    Unscripted requests get the harness's 400 tripwire, so a client
    check that should have stopped the call shows up as a request.
    """
    server, proxy = stub
    run_env = sandbox.env(proxy)
    for key, value in (env or {}).items():
        if value is None:
            run_env.pop(key, None)
        else:
            run_env[key] = value
    sandbox.seal()
    routes = dict(script or {})
    return await run_export_credentials(
        aws_cli,
        sandbox,
        [server],
        run_env,
        globals_=globals_,
        handlers={server: lambda: routed(routes)},
    )


def assert_failed(
    run: CliRun, returncode: int, stderr: bytes | BytesStartingWith
) -> None:
    """A failure before any request that leaves the sandbox untouched."""
    assert (run.returncode, run.stdout, run.stderr) == (
        returncode,
        b"",
        stderr,
    ), run.describe()
    assert run.requests == (), run.describe()
    assert run.changes == {}, run.describe()


def sts_request(body: bytes, *, host: str = STS_HOST) -> NormalizedRequest:
    """The one AssumeRole call: a form POST with no security token.

    It is SigV4-signed by the source profile's keys for STS in us-east-1,
    whatever the endpoint.
    """
    headers = {
        "content-type": FORM_CONTENT_TYPE,
        "authorization": SIGV4_ALGORITHM,
        "x-amz-date": AMZ_DATE_PLACEHOLDER,
    }
    return NormalizedRequest(
        method="POST",
        host=host,
        path="/",
        target="/",
        query=(),
        content_type=FORM_CONTENT_TYPE,
        body_bytes=body,
        headers=tuple((name, headers.get(name)) for name in COMPARED_HEADERS),
        user_agent=None,
        signing_scope=SOURCE_SCOPE,
    )


def assert_assumed(
    run: CliRun, request: NormalizedRequest, cache_key: str
) -> None:
    """One STS call, ROLE_OUTPUT printed, and only the cache entry written.

    The first cache write makes the cache directory and its parents in
    HOME (utils.py:4000-4001).
    """
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        ROLE_OUTPUT,
        b"",
    ), run.describe()
    assert run.requests == (request,), run.describe()
    assert_signature(run.raw_requests[0], "AKIDSRC", "SRC-secret")
    changes = created_cache_directories()
    changes[f"home/{CLI_CACHE.as_posix()}/{cache_key}.json"] = (
        CACHE_FILE_MODE,
        ROLE_CACHE,
    )
    assert run.changes == changes, run.describe()


SERVICES_MISSING: Final = (
    "The profile is configured to use the services section but the "
    '"{name}" services configuration does not exist.'
)


@pytest.mark.parametrize(
    ("settings", "env", "globals_", "stderr"),
    [
        pytest.param(
            "",
            {"AWS_REGION": "bad region"},
            (),
            general_error(
                "Provided region_name 'bad region' doesn't match a supported "
                "format."
            ),
            id="env-region",
        ),
        pytest.param(
            "",
            {"AWS_REGION": "12345"},
            (),
            general_error(
                "Provided region_name '12345' doesn't match a supported "
                "format."
            ),
            id="all-digits",
        ),
        pytest.param(
            "services = missing\n",
            {},
            (),
            general_error(SERVICES_MISSING.format(name="missing")),
            id="services-missing",
        ),
        pytest.param(
            "",
            {"AWS_ENDPOINT_URL_STS": "https://bad host.example.test"},
            (),
            general_error("Invalid endpoint: https://bad host.example.test"),
            id="invalid-endpoint-url",
        ),
        pytest.param(
            "",
            {"AWS_CA_BUNDLE": ""},
            (),
            general_error(INVALID_CA_BUNDLE),
            id="empty-env-ca-bundle",
        ),
        pytest.param(
            "",
            {"AWS_CA_BUNDLE": ""},
            ("--no-verify-ssl",),
            general_error(INVALID_CA_BUNDLE),
            id="no-verify-ssl-does-not-help",
        ),
        pytest.param(
            "",
            {},
            ("--cli-connect-timeout", "-1"),
            # urllib3's Timeout wording, naming the rejected value.
            BytesStartingWith(GENERAL_PREFIX, (b"-1",)),
            id="connect-timeout",
        ),
        pytest.param(
            "sts =\n  signature_version = bogus\n",
            {},
            (),
            general_error("Unknown Signature Version: bogus."),
            id="unknown-signature-version",
        ),
    ],
)
async def test_client_config_invalid_setting_fails_sts_client_creation(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    settings: str,
    env: EnvChanges,
    globals_: tuple[str, ...],
    stderr: bytes | BytesStartingWith,
) -> None:
    sandbox.config.write_text(role_config(settings))

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        env=env,
        globals_=globals_,
    )

    # Plain framing: GeneralExceptionHandler prints str(e) for every
    # format (errorhandler.py:391-399).
    assert_failed(run, GENERAL_RC, stderr)


async def test_client_config_unsigned_web_identity_client_checks_ca_bundle(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    token = sandbox.write("token", WEB_TOKEN)
    sandbox.config.write_text(WEB_CONFIG.format(token=token, settings=""))

    run = await run_scenario(aws_cli, sandbox, stub, env={"AWS_CA_BUNDLE": ""})

    # The UNSIGNED web identity client goes through the same client
    # creation (credentials.py:1009-1020).
    assert_failed(run, GENERAL_RC, general_error(INVALID_CA_BUNDLE))


@pytest.mark.parametrize(
    ("source_settings", "env", "globals_"),
    [
        pytest.param(
            "",
            {"REQUESTS_CA_BUNDLE": " "},
            (),
            id="aws-ca-bundle-shadows-requests-ca-bundle",
        ),
        pytest.param(
            "ca_bundle =\nmax_attempts = abc\nregion = bad region\n",
            {"AWS_MAX_ATTEMPTS": None},
            (),
            id="source-profile-settings-ignored",
        ),
        pytest.param(
            "",
            {},
            ("--cli-connect-timeout", "0", "--cli-read-timeout", "0"),
            id="zero-timeouts-mean-none",
        ),
        pytest.param(
            "",
            {"AWS_BEARER_TOKEN_STS": "tok"},
            (),
            id="bearer-token-has-no-effect",
        ),
    ],
)
async def test_client_config_tolerated_setting_still_assumes_role(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    source_settings: str,
    env: EnvChanges,
    globals_: tuple[str, ...],
) -> None:
    sandbox.config.write_text(role_config(source_settings=source_settings))

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        {STS_ROUTE: [role_response()]},
        env=env,
        globals_=globals_,
    )

    assert_assumed(
        run,
        sts_request(
            form_body(
                "AssumeRole",
                ("RoleArn", ROLE_A),
                ("RoleSessionName", GENERATED_NAME),
            )
        ),
        role_cache_key({"RoleArn": ROLE_A}),
    )


async def test_client_config_parameter_validation_off_sends_invalid_value(
    aws_cli: str, sandbox: Sandbox, stub: Stub
) -> None:
    sandbox.config.write_text(
        role_config("external_id =\nparameter_validation = false\n")
    )

    run = await run_scenario(
        aws_cli,
        sandbox,
        stub,
        {STS_ROUTE: [role_response()]},
    )

    # With validation off (args.py:209-216) the empty ExternalId, below
    # its minimum length, is sent and keys the cache.
    assert_assumed(
        run,
        sts_request(
            form_body(
                "AssumeRole",
                ("ExternalId", ""),
                ("RoleArn", ROLE_A),
                ("RoleSessionName", GENERATED_NAME),
            )
        ),
        role_cache_key({"ExternalId": "", "RoleArn": ROLE_A}),
    )
