import itertools
import json
import shlex
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final
from urllib.parse import parse_qs

import pytest
import pytest_asyncio
from localstub import AsyncHTTPTestServer, HTTPResponse, ResponderContext

from credhelpers import (
    AMZ_DATE_PLACEHOLDER,
    CACHE_FILE_MODE,
    CLI_CACHE,
    CREATED_FILE_MODE,
    LOGIN_TOKEN_CACHE,
    SAMPLE_DPOP_PEM,
    SCOPE_DATE_PLACEHOLDER,
    CliRun,
    FileChanges,
    Handler,
    NormalizedRequest,
    RoleCacheContent,
    RouteKey,
    Sandbox,
    Stub,
    Tree,
    assert_credential_error,
    assert_signature,
    created_cache_directories,
    credential_runtime,
    expected_request,
    export_credentials_output,
    file_credentials,
    list_bucket,
    metadata_credentials,
    role_cache_key,
    route_key,
    routed,
    run_export_credentials,
    sso_role_cache_key,
    sso_role_credentials,
    sts_success_xml,
    unexpected_request,
    write_config,
    write_login_token,
    write_sso_token,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("sts_routes_through_proxy"),
]

ACCOUNT: Final = "123456789012"
FUTURE: Final = "2099-01-01T00:00:00Z"
FUTURE_ISO: Final = "2099-01-01T00:00:00+00:00"
DEFAULT_PROFILE: Final = "default"
STS_HOST: Final = "sts.us-east-1.amazonaws.com"
STS_ROUTE: Final[RouteKey] = ("POST", STS_HOST, "/")
STS_FORM: Final = "application/x-www-form-urlencoded; charset=utf-8"
AR_ROLE_ARN: Final = f"arn:aws:iam::{ACCOUNT}:role/ChainRole"
AR_SESSION: Final = "chain"
AR_SOURCE_PROFILE: Final = "profile arsource"
AR_ASSUMED_ARN: Final = f"arn:aws:sts::{ACCOUNT}:assumed-role/ChainRole/chain"
WEB_ROLE_ARN: Final = f"arn:aws:iam::{ACCOUNT}:role/ChainWeb"
WEB_SESSION: Final = "chain-web"
WEB_TOKEN: Final = "chain-web-token"
WEB_ASSUMED_ARN: Final = (
    f"arn:aws:sts::{ACCOUNT}:assumed-role/ChainWeb/chain-web"
)
SSO_SESSION: Final = "chain-sso"
SSO_START_URL: Final = "https://chain.invalid/start"
SSO_ROLE: Final = "ChainSso"
SSO_ACCESS_TOKEN: Final = "SSO-ACCESS"
SSO_HOST: Final = "portal.sso.us-west-2.amazonaws.com"
SSO_ROUTE: Final[RouteKey] = ("GET", SSO_HOST, "/federation/credentials")
LOGIN_SESSION: Final = "chain-login"
IMDS_HOST: Final = "169.254.169.254"
IMDS_ROLE: Final = "chain-role"
IMDS_TOKEN: Final = "chain-imds-token"
IMDS_TOKEN_TTL: Final = "21600"
IMDS_CREDENTIALS_PATH: Final = "/latest/meta-data/iam/security-credentials/"
IMDS_ROUTES: Final[tuple[RouteKey, ...]] = (
    ("PUT", IMDS_HOST, "/latest/api/token"),
    ("GET", IMDS_HOST, IMDS_CREDENTIALS_PATH),
    ("GET", IMDS_HOST, IMDS_CREDENTIALS_PATH + IMDS_ROLE),
)
CONTAINER_PATH: Final = "/chain-creds"
PROCESS_LOG: Final = "process-calls.log"
# A credential_process helper: logs its argv next to itself, then prints
# static credentials named after argv[1], or fails with argv[2] on
# stderr. It lives in the sandbox, so every run starts with no log.
PROCESS_HELPER: Final = """\
import json
import sys
from pathlib import Path

log = Path(__file__).with_name("process-calls.log")
with log.open("a", encoding="utf-8", newline="\\n") as stream:
    stream.write(json.dumps(sys.argv[1:]) + "\\n")
if len(sys.argv) > 2:
    sys.stderr.write(sys.argv[2] + "\\n")
    sys.exit(1)
name = sys.argv[1]
print(
    json.dumps(
        {
            "Version": 1,
            "AccessKeyId": f"AKID{name}",
            "SecretAccessKey": f"{name}-secret",
        }
    )
)
"""
# exportcreds.py:269-279 wraps every load-phase exception, and
# errorhandler.py:316-321 renders it enhanced (errorformat.py:28-41).
CONFIGURATION_PREFIX: Final = (
    "\naws: [ERROR]: An error occurred (Configuration): "
    "Unable to retrieve credentials: "
)


@dataclass(frozen=True)
class Outcome:
    """What the command must print and return."""

    returncode: int
    stdout: bytes = b""
    stderr: bytes = b""


@dataclass(frozen=True)
class Winner:
    """What the run shows when one provider supplies credentials.

    `requests` are the requests it makes, in server order; `cache` the
    `~/.aws/cli/cache` entries it writes, by file name, as the documents
    RoleCacheContent compares; `calls` the
    credential_process helper's argv log, None when never spawned;
    `check` a verification of the raw requests (SigV4 signature, Accept).
    """

    outcome: Outcome
    requests: tuple[NormalizedRequest, ...] = ()
    cache: Mapping[str, object] = field(default_factory=dict)
    calls: bytes | None = None
    check: Callable[[CliRun], None] | None = None


@dataclass
class World:
    """Fixtures for one scenario, assembled by the provider arrangers."""

    sandbox: Sandbox
    container: AsyncHTTPTestServer
    metadata: AsyncHTTPTestServer
    env: dict[str, str] = field(default_factory=dict)
    config: dict[str, dict[str, str]] = field(default_factory=dict)
    credentials: dict[str, dict[str, str]] = field(default_factory=dict)
    sts: dict[str, list[HTTPResponse]] = field(default_factory=dict)
    tls_routes: dict[RouteKey, list[HTTPResponse]] = field(
        default_factory=dict
    )
    container_routes: dict[RouteKey, list[HTTPResponse]] = field(
        default_factory=dict
    )
    metadata_routes: dict[RouteKey, list[HTTPResponse]] = field(
        default_factory=dict
    )
    # The sandbox as sealed, set by run_world.
    sealed: Tree = field(default_factory=dict)

    def profile(self, section: str = DEFAULT_PROFILE) -> dict[str, str]:
        return self.config.setdefault(section, {})


def exported(
    access_key: str,
    secret_key: str,
    token: str | None = None,
    expiration: str | None = None,
) -> Outcome:
    return Outcome(
        0,
        export_credentials_output(access_key, secret_key, token, expiration),
    )


def wrapped(message: str) -> Outcome:
    """A load-phase failure: ConfigurationError, rc 253."""
    return Outcome(253, stderr=f"{CONFIGURATION_PREFIX}{message}\n".encode())


def raw(message: str) -> Outcome:
    """A freeze-phase failure through GeneralExceptionHandler, rc 255."""
    return Outcome(255, stderr=f"\naws: [ERROR]: {message}\n".encode())


def sts_cache(
    access_key: str, secret_key: str, session_token: str
) -> dict[str, object]:
    """An STS role-cache entry's Credentials, as botocore reads them back.

    The account comes from the AssumedRoleUser ARN (credentials.py:
    852-859) and Expiration is serialized with isoformat().
    """
    return {
        "Credentials": {
            "AccessKeyId": access_key,
            "SecretAccessKey": secret_key,
            "SessionToken": session_token,
            "Expiration": FUTURE_ISO,
            "AccountId": ACCOUNT,
        }
    }


def render_ini(sections: Mapping[str, Mapping[str, str]]) -> str:
    return "".join(
        f"[{name}]\n"
        + "".join(f"{key} = {value}\n" for key, value in options.items())
        + "\n"
        for name, options in sections.items()
    )


def helper_command(world: World, *args: str) -> str:
    """The helper's credential_process command line, with `args`."""
    command = world.sandbox.helper("process-helper.py", PROCESS_HELPER)
    return f"{command} {shlex.join(args)}"


def helper_calls(*argvs: Sequence[str]) -> bytes:
    return "".join(json.dumps(list(argv)) + "\n" for argv in argvs).encode()


def assert_assume_role_signed_by_source(run: CliRun) -> None:
    (signed,) = [
        request
        for request in run.raw_requests
        if route_key(request) == STS_ROUTE
    ]
    assert_signature(signed, "AKIDARSOURCE", "ARSOURCE-secret")


def arrange_env(world: World) -> Winner:
    """EnvProvider, the first provider (credentials.py:135-138)."""
    world.env.update(
        AWS_ACCESS_KEY_ID="AKIDENV", AWS_SECRET_ACCESS_KEY="ENV-secret"
    )
    return Winner(exported("AKIDENV", "ENV-secret"))


def arrange_assume_role(world: World) -> Winner:
    """AssumeRoleProvider with a static source profile.

    load() engages for role_arn without web_identity_token_file
    (credentials.py:1626-1642); the STS call, SigV4-signed with the
    source profile's keys, is deferred to the freeze and its result
    cached in ~/.aws/cli/cache.
    """
    world.profile().update(
        role_arn=AR_ROLE_ARN,
        role_session_name=AR_SESSION,
        source_profile=AR_SOURCE_PROFILE.removeprefix("profile "),
    )
    world.profile(AR_SOURCE_PROFILE).update(
        aws_access_key_id="AKIDARSOURCE",
        aws_secret_access_key="ARSOURCE-secret",
    )
    world.sts["AssumeRole"] = [
        sts_success_xml(
            access_key="AKIDROLE",
            secret_key="ROLE-secret",
            session_token="ROLE-token",
            arn=AR_ASSUMED_ARN,
        )
    ]
    key = role_cache_key(
        {"RoleArn": AR_ROLE_ARN, "RoleSessionName": AR_SESSION}
    )
    request = expected_request(
        "POST",
        STS_HOST,
        "/",
        body=(
            b"Action=AssumeRole&Version=2011-06-15&RoleSessionName=chain"
            b"&RoleArn=arn%3Aaws%3Aiam%3A%3A123456789012%3Arole%2FChainRole"
        ),
        headers={
            "authorization": "AWS4-HMAC-SHA256",
            "x-amz-date": AMZ_DATE_PLACEHOLDER,
            "content-type": STS_FORM,
        },
        signing_scope=(
            "AKIDARSOURCE",
            SCOPE_DATE_PLACEHOLDER,
            "us-east-1",
            "sts",
        ),
    )
    return Winner(
        exported("AKIDROLE", "ROLE-secret", "ROLE-token", FUTURE_ISO),
        requests=(request,),
        cache={
            f"{key}.json": sts_cache("AKIDROLE", "ROLE-secret", "ROLE-token")
        },
        check=assert_assume_role_signed_by_source,
    )


def web_identity_winner() -> Winner:
    """One AssumeRoleWithWebIdentity without SigV4 material.

    The fetcher's client uses signature_version=UNSIGNED
    (credentials.py:1012-1017), so neither Authorization nor a security
    token is sent.
    """
    key = role_cache_key(
        {
            "RoleArn": WEB_ROLE_ARN,
            "RoleSessionName": WEB_SESSION,
            "WebIdentityToken": WEB_TOKEN,
        }
    )
    request = expected_request(
        "POST",
        STS_HOST,
        "/",
        body=(
            b"Action=AssumeRoleWithWebIdentity&Version=2011-06-15"
            b"&RoleSessionName=chain-web"
            b"&RoleArn=arn%3Aaws%3Aiam%3A%3A123456789012%3Arole%2FChainWeb"
            b"&WebIdentityToken=chain-web-token"
        ),
        headers={"content-type": STS_FORM},
    )
    return Winner(
        exported("AKIDWEB", "WEB-secret", "WEB-token", FUTURE_ISO),
        requests=(request,),
        cache={f"{key}.json": sts_cache("AKIDWEB", "WEB-secret", "WEB-token")},
    )


def script_web_identity(world: World) -> Path:
    world.sts["AssumeRoleWithWebIdentity"] = [
        sts_success_xml(
            action="AssumeRoleWithWebIdentity",
            access_key="AKIDWEB",
            secret_key="WEB-secret",
            session_token="WEB-token",
            arn=WEB_ASSUMED_ARN,
        )
    ]
    return world.sandbox.write("web-identity-token", WEB_TOKEN)


def arrange_web_identity(world: World) -> Winner:
    """AssumeRoleWithWebIdentityProvider through its env inputs.

    The env inputs compose with any profile (credentials.py:1915-1985);
    the STS call is unsigned and deferred to the freeze.
    """
    token = script_web_identity(world)
    world.env.update(
        AWS_WEB_IDENTITY_TOKEN_FILE=str(token),
        AWS_ROLE_ARN=WEB_ROLE_ARN,
        AWS_ROLE_SESSION_NAME=WEB_SESSION,
    )
    return web_identity_winner()


def arrange_sso(world: World) -> Winner:
    """SSOProvider for an sso-session profile with a valid cached token.

    GetRoleCredentials, unsigned with the cached token as bearer
    (credentials.py:2315-2345) and the account and role in the query
    (sso service-2.json GetRoleCredentials), is deferred to the freeze;
    the top-level SSO provider caches the role credentials in
    ~/.aws/cli/cache (awscli/customizations/sso/__init__.py:38-44).
    """
    world.profile().update(
        sso_session=SSO_SESSION,
        sso_account_id=ACCOUNT,
        sso_role_name=SSO_ROLE,
    )
    world.profile(f"sso-session {SSO_SESSION}").update(
        sso_start_url=SSO_START_URL, sso_region="us-west-2"
    )
    write_sso_token(
        world.sandbox.home,
        SSO_SESSION,
        startUrl=SSO_START_URL,
        region="us-west-2",
        accessToken=SSO_ACCESS_TOKEN,
        expiresAt=FUTURE,
        clientId="chain-client",
        clientSecret="chain-client-secret",
        registrationExpiresAt=FUTURE,
        refreshToken="chain-refresh",
    )
    world.tls_routes[SSO_ROUTE] = [sso_role_credentials()]
    key = sso_role_cache_key(
        {
            "accountId": ACCOUNT,
            "roleName": SSO_ROLE,
            "sessionName": SSO_SESSION,
        }
    )
    request = expected_request(
        "GET",
        SSO_HOST,
        f"/federation/credentials?role_name={SSO_ROLE}&account_id={ACCOUNT}",
        headers={"x-amz-sso_bearer_token": SSO_ACCESS_TOKEN},
    )
    # credentials.py:2349-2358 writes the account, and _parse_timestamp
    # turns the epoch milliseconds into an ISO string.
    cached = {
        "Credentials": {
            "AccessKeyId": "AKIDSSO",
            "SecretAccessKey": "SSOSECRET",
            "SessionToken": "SSOTOKEN",
            "Expiration": FUTURE,
            "AccountId": ACCOUNT,
        },
    }
    return Winner(
        exported("AKIDSSO", "SSOSECRET", "SSOTOKEN", FUTURE_ISO),
        requests=(request,),
        cache={f"{key}.json": cached},
    )


def arrange_shared(world: World) -> Winner:
    """SharedCredentialProvider (credentials.py:1371-1424)."""
    world.credentials.setdefault(DEFAULT_PROFILE, {}).update(
        aws_access_key_id="AKIDSHARED", aws_secret_access_key="SHARED-secret"
    )
    return Winner(exported("AKIDSHARED", "SHARED-secret"))


def arrange_login(world: World) -> Winner:
    """LoginProvider with an unexpired cached token: no refresh request.

    load() returns the cached credentials (credentials.py:2680-2715).
    """
    world.profile()["login_session"] = LOGIN_SESSION
    write_login_token(
        world.sandbox.home / LOGIN_TOKEN_CACHE,
        LOGIN_SESSION,
        accessToken={
            "accessKeyId": "AKIDLOGIN",
            "secretAccessKey": "LOGIN-secret",
            "sessionToken": "LOGIN-token",
            "accountId": ACCOUNT,
            "expiresAt": FUTURE,
        },
        refreshToken="chain-refresh",
        dpopKey=SAMPLE_DPOP_PEM,
        clientId="chain-client",
    )
    return Winner(
        exported("AKIDLOGIN", "LOGIN-secret", "LOGIN-token", FUTURE_ISO)
    )


def arrange_process(world: World) -> Winner:
    """ProcessProvider from the config file (credentials.py:1076-1106)."""
    world.profile()["credential_process"] = helper_command(world, "PROCESS")
    return Winner(
        exported("AKIDPROCESS", "PROCESS-secret"),
        calls=helper_calls(["PROCESS"]),
    )


def arrange_config(world: World) -> Winner:
    """ConfigProvider (credentials.py:1427-1494)."""
    world.profile().update(
        aws_access_key_id="AKIDCONFIG", aws_secret_access_key="CONFIG-secret"
    )
    return Winner(exported("AKIDCONFIG", "CONFIG-secret"))


def arrange_ec2_file(world: World) -> Winner:
    """OriginalEC2Provider (credentials.py:1336-1368)."""
    path = world.sandbox.write(
        "ec2-credentials", "AWSAccessKeyId=AKIDEC2\nAWSSecretKey=EC2-secret\n"
    )
    world.env["AWS_CREDENTIAL_FILE"] = str(path)
    return Winner(exported("AKIDEC2", "EC2-secret"))


def arrange_boto(world: World) -> Winner:
    """BotoProvider through BOTO_CONFIG (credentials.py:1497-1540)."""
    world.sandbox.boto.write_text(
        "[Credentials]\naws_access_key_id = AKIDBOTO\n"
        "aws_secret_access_key = BOTO-secret\n",
        encoding="utf-8",
    )
    return Winner(exported("AKIDBOTO", "BOTO-secret"))


def assert_container_accepts_json(run: CliRun) -> None:
    (request,) = run.raw_requests
    assert request.headers.get("accept") == "application/json", run.describe()


def arrange_container(world: World) -> Winner:
    """ContainerProvider with a loopback full URI (credentials.py:2075-2153).

    The container fetcher connects directly, never through a proxy, and
    sends Accept: application/json with no Authorization when no token
    is configured (utils.py:2974-2977).
    """
    host = f"127.0.0.1:{world.container.port}"
    world.env["AWS_CONTAINER_CREDENTIALS_FULL_URI"] = (
        f"http://{host}{CONTAINER_PATH}"
    )
    route = ("GET", host, CONTAINER_PATH)
    world.container_routes[route] = [
        HTTPResponse.json(metadata_credentials("CONTAINER"))
    ]
    return Winner(
        exported(
            "AKIDCONTAINER", "CONTAINER-secret", "CONTAINER-token", FUTURE_ISO
        ),
        requests=(expected_request("GET", host, CONTAINER_PATH),),
        check=assert_container_accepts_json,
    )


def arrange_imds(world: World) -> Winner:
    """InstanceMetadataProvider through the HTTP_PROXY stub, IMDSv2.

    The token PUT, role list, and role credentials (utils.py:408-430,
    539-574) go to the stub in absolute form, never to the link-local
    endpoint. The PUT asks for a 21600 s TTL and carries no token; each
    GET carries the token and no TTL (utils.py:408-416, 444-470).
    """
    world.env.update(
        AWS_EC2_METADATA_DISABLED="false", HTTP_PROXY=world.metadata.url
    )
    token, roles, credentials = IMDS_ROUTES
    world.metadata_routes[token] = [HTTPResponse.text(IMDS_TOKEN)]
    world.metadata_routes[roles] = [HTTPResponse.text(IMDS_ROLE)]
    world.metadata_routes[credentials] = [
        HTTPResponse.json(metadata_credentials("IMDS"))
    ]
    token_url, roles_url, credentials_url = (
        f"http://{host}{path}" for _, host, path in IMDS_ROUTES
    )
    with_token = {"x-aws-ec2-metadata-token": IMDS_TOKEN}
    requests = (
        expected_request(
            "PUT",
            IMDS_HOST,
            token_url,
            headers={"x-aws-ec2-metadata-token-ttl-seconds": IMDS_TOKEN_TTL},
        ),
        expected_request("GET", IMDS_HOST, roles_url, headers=with_token),
        expected_request(
            "GET", IMDS_HOST, credentials_url, headers=with_token
        ),
    )
    return Winner(
        exported("AKIDIMDS", "IMDS-secret", "IMDS-token", FUTURE_ISO),
        requests=requests,
    )


# The default chain, in order (credentials.py:135-149, 202-213).
ARRANGERS: Final[dict[str, Callable[[World], Winner]]] = {
    "env": arrange_env,
    "assume-role": arrange_assume_role,
    "web-identity": arrange_web_identity,
    "sso": arrange_sso,
    "shared-credentials-file": arrange_shared,
    "login": arrange_login,
    "custom-process": arrange_process,
    "config-file": arrange_config,
    "ec2-credentials-file": arrange_ec2_file,
    "boto-config": arrange_boto,
    "container-role": arrange_container,
    "iam-role": arrange_imds,
}
ORDER: Final = tuple(ARRANGERS)
ADJACENT_PAIRS: Final = tuple(itertools.pairwise(ORDER))
IMDS_NAME: Final = "iam-role"


def sts_by_action(
    responses: Mapping[str, Sequence[HTTPResponse]],
    fallback: Handler,
) -> Handler:
    """STS answers keyed by the form body's Action, else `fallback`.

    AssumeRole and AssumeRoleWithWebIdentity share one route, so a run
    calling the wrong one gets the 400 tripwire instead of the other's
    credentials.
    """
    queues = {action: list(items) for action, items in responses.items()}

    def handler(context: ResponderContext) -> HTTPResponse:
        if route_key(context.request) != STS_ROUTE:
            return fallback(context)
        body = (context.request.body or b"").decode("utf-8", "replace")
        actions = parse_qs(body).get("Action", [""])
        queue = queues.get(actions[0])
        if not queue:
            return unexpected_request()
        return queue.pop(0)

    return handler


@pytest_asyncio.fixture
async def container() -> AsyncIterator[AsyncHTTPTestServer]:
    async with AsyncHTTPTestServer() as server:
        yield server


@pytest_asyncio.fixture
async def metadata() -> AsyncIterator[AsyncHTTPTestServer]:
    async with AsyncHTTPTestServer() as server:
        yield server


@pytest.fixture
def world(
    sandbox: Sandbox,
    container: AsyncHTTPTestServer,
    metadata: AsyncHTTPTestServer,
) -> World:
    return World(sandbox=sandbox, container=container, metadata=metadata)


async def run_world(
    aws_cli: str,
    world: World,
    stub: Stub,
    *,
    globals_: Sequence[str] = (),
) -> CliRun:
    """Write the world's files, seal, and run export-credentials once.

    Every server answers only what the arrangers scripted; anything else
    gets the 400 tripwire.
    """
    server, proxy = stub
    sandbox = world.sandbox
    sandbox.config.write_text(render_ini(world.config), encoding="utf-8")
    sandbox.credentials.write_text(
        render_ini(world.credentials), encoding="utf-8"
    )
    sandbox.seal()
    assert sandbox.sealed is not None
    world.sealed = sandbox.sealed
    env = {**sandbox.env(proxy), **world.env}
    return await run_export_credentials(
        aws_cli,
        sandbox,
        [server, world.container, world.metadata],
        env,
        globals_=globals_,
        handlers={
            server: lambda: sts_by_action(world.sts, routed(world.tls_routes)),
            world.container: lambda: routed(world.container_routes),
            world.metadata: lambda: routed(world.metadata_routes),
        },
    )


def expected_changes(world: World, winner: Winner) -> FileChanges:
    """The winner's cache files and the helper's call log, nothing else.

    A cache write also creates whichever cache directories the sealed
    sandbox lacked; the role and SSO caches are mode 0600
    (utils.py:3991-4006).
    """
    changes: FileChanges = {}
    if winner.cache:
        changes.update(created_cache_directories(world.sealed))
    for name, value in winner.cache.items():
        changes[f"home/{CLI_CACHE.as_posix()}/{name}"] = (
            CACHE_FILE_MODE,
            RoleCacheContent(value),
        )
    if winner.calls is not None:
        changes[PROCESS_LOG] = (CREATED_FILE_MODE, winner.calls)
    return dict(sorted(changes.items()))


def assert_outcome(run: CliRun, expected: Outcome) -> None:
    assert (run.returncode, run.stdout, run.stderr) == (
        expected.returncode,
        expected.stdout,
        expected.stderr,
    ), run.describe()


def assert_winner(world: World, run: CliRun, winner: Winner) -> None:
    """The winner's output, requests, and file changes.

    The only files the run may change are the winner's ~/.aws/cli/cache
    entries (and the directories they need) and the helper's call log.
    """
    assert_outcome(run, winner.outcome)
    assert run.requests == winner.requests, run.describe()
    assert run.changes == expected_changes(world, winner), run.describe()
    if winner.check is not None:
        winner.check(run)


async def run_precedence(
    aws_cli: str,
    world: World,
    stub: Stub,
    names: Sequence[str],
) -> None:
    """Arrange every named provider; the first in chain order must win."""
    winners = {name: ARRANGERS[name](world) for name in names}
    first = min(names, key=ORDER.index)
    run = await run_world(aws_cli, world, stub)
    assert_winner(world, run, winners[first])


def precedence_params(
    rows: Sequence[Sequence[str]], *, with_imds: bool
) -> Sequence[object]:
    return [
        pytest.param(tuple(row), id="-over-".join(row))
        for row in rows
        if (IMDS_NAME in row) == with_imds
    ]


# One row per adjacent pair of the default chain (credentials.py:135-149,
# 202-213), each provider valid on its own, so only precedence decides
# the winner. The higher provider's credentials print, and the lower one
# makes no request, writes no cache, and spawns no helper.
PRECEDENCE_ROWS: Final = (
    *ADJACENT_PAIRS,
    # role_arn + source_profile + static keys in one profile.
    ("assume-role", "config-file"),
    # Credentials-file keys beat a configured credential_process.
    ("shared-credentials-file", "custom-process"),
)


@pytest.mark.parametrize(
    "names", precedence_params(PRECEDENCE_ROWS, with_imds=False)
)
async def test_chain_higher_provider_wins_over_valid_lower_provider(
    aws_cli: str,
    world: World,
    stub: Stub,
    names: tuple[str, ...],
) -> None:
    await run_precedence(aws_cli, world, stub, names)


@pytest.mark.usefixtures("imds_routes_through_proxy")
@pytest.mark.parametrize(
    "names", precedence_params(PRECEDENCE_ROWS, with_imds=True)
)
async def test_chain_container_wins_over_valid_instance_metadata(
    aws_cli: str,
    world: World,
    stub: Stub,
    names: tuple[str, ...],
) -> None:
    await run_precedence(aws_cli, world, stub, names)


# iam-role is last in the chain, so no precedence row shows its fixture
# supplies credentials on its own.
@pytest.mark.usefixtures("imds_routes_through_proxy")
async def test_chain_instance_metadata_alone_supplies_credentials(
    aws_cli: str,
    world: World,
    stub: Stub,
) -> None:
    await run_precedence(aws_cli, world, stub, (IMDS_NAME,))


# A web_identity_token_file in the profile disables AssumeRoleProvider
# for that profile (credentials.py:1633-1642), so web identity wins over
# role_arn + source_profile and the profile's own static keys.
async def test_chain_profile_web_identity_wins_over_role_and_static_keys(
    aws_cli: str,
    world: World,
    stub: Stub,
) -> None:
    arrange_assume_role(world)
    arrange_config(world)
    token = script_web_identity(world)
    world.profile().update(
        role_arn=WEB_ROLE_ARN,
        role_session_name=WEB_SESSION,
        web_identity_token_file=str(token),
    )

    run = await run_world(aws_cli, world, stub)

    assert_winner(world, run, web_identity_winner())


# Only a non-empty --profile disables the web-identity env inputs
# (credentials.py:92, 139-142, 1925-1931); AWS_PROFILE only picks the
# profile, so the env inputs still win over its static keys.
@pytest.mark.parametrize(
    ("overrides", "globals_", "web_identity_wins"),
    [
        pytest.param({"AWS_PROFILE": "dev"}, (), True, id="aws-profile"),
        pytest.param(
            {"AWS_DEFAULT_PROFILE": "dev"},
            (),
            True,
            id="aws-default-profile",
        ),
        pytest.param({}, ("--profile", "dev"), False, id="explicit-profile"),
    ],
)
async def test_chain_explicit_profile_drops_web_identity_env_inputs(
    aws_cli: str,
    world: World,
    stub: Stub,
    overrides: dict[str, str],
    globals_: tuple[str, ...],
    web_identity_wins: bool,
) -> None:
    web_identity = arrange_web_identity(world)
    world.env.update(overrides)
    world.credentials["dev"] = {
        "aws_access_key_id": "AKIDDEV",
        "aws_secret_access_key": "DEV-secret",
    }

    run = await run_world(aws_cli, world, stub, globals_=globals_)

    winner = (
        web_identity
        if web_identity_wins
        else Winner(exported("AKIDDEV", "DEV-secret"))
    )
    assert_winner(world, run, winner)


# ProcessProvider reads session.full_config, where each credentials-file
# section is merged over the config profile of the same name, the
# credentials file winning per key (session.py:384-418).
async def test_chain_credentials_file_credential_process_wins_over_config(
    aws_cli: str,
    world: World,
    stub: Stub,
) -> None:
    world.profile()["credential_process"] = helper_command(world, "CONFIGPROC")
    world.credentials[DEFAULT_PROFILE] = {
        "credential_process": helper_command(world, "CREDPROC")
    }

    run = await run_world(aws_cli, world, stub)

    assert_winner(
        world,
        run,
        Winner(
            exported("AKIDCREDPROC", "CREDPROC-secret"),
            calls=helper_calls(["CREDPROC"]),
        ),
    )


# The resolver returns the first non-None result and lets any exception
# escape (credentials.py:2238-2256), so a raising provider aborts the
# chain before a later valid one runs.
async def test_chain_failing_credential_process_aborts_before_config_keys(
    aws_cli: str,
    world: World,
    stub: Stub,
) -> None:
    arrange_config(world)
    world.profile()["credential_process"] = helper_command(
        world, "FAILING", "chain-failure"
    )

    run = await run_world(aws_cli, world, stub)

    # A nonzero exit raises CredentialRetrievalError with the decoded
    # stderr (credentials.py:1117-1120), stripped by exportcreds.py:272.
    assert_winner(
        world,
        run,
        Winner(
            wrapped(
                "Error when retrieving credentials from custom-process: "
                "chain-failure"
            ),
            calls=helper_calls(["FAILING", "chain-failure"]),
        ),
    )


# SSOProvider sits before the credentials file: a legacy SSO profile
# without a cached token returns deferred credentials at load and fails
# at the freeze (credentials.py:2460-2496, 2259-2360), which proves it
# ran before SharedCredentialProvider's valid keys.
async def test_chain_sso_token_error_shows_sso_ran_before_shared_keys(
    aws_cli: str,
    world: World,
    stub: Stub,
) -> None:
    arrange_shared(world)
    world.profile().update(
        sso_start_url=SSO_START_URL,
        sso_region="us-west-2",
        sso_account_id=ACCOUNT,
        sso_role_name=SSO_ROLE,
    )

    run = await run_world(aws_cli, world, stub)

    assert_winner(
        world,
        run,
        Winner(
            raw(
                "Error loading SSO Token: Token for "
                f"{SSO_START_URL} does not exist"
            )
        ),
    )


# Signing: these tests resolve credentials for `s3 ls` and check which
# keys signed its request, so they show the provider's credentials
# reaching a signed service call and not only the exported output.


FALLBACK_PROFILE = "[default]\n" + file_credentials("FALLBACK")
PARTIAL_PROFILE = "[default]\naws_access_key_id = AKIDPARTIAL\n"


@pytest.mark.parametrize(
    ("variables", "config", "shared"),
    [
        pytest.param(
            {"AWS_ACCESS_KEY_ID": "AKIDPARTIAL"},
            "",
            FALLBACK_PROFILE,
            id="env-missing-secret",
        ),
        pytest.param(
            {"AWS_ACCESS_KEY_ID": "AKIDPARTIAL", "AWS_SECRET_ACCESS_KEY": ""},
            "",
            FALLBACK_PROFILE,
            id="env-empty-secret",
        ),
        pytest.param(
            {},
            FALLBACK_PROFILE,
            PARTIAL_PROFILE,
            id="shared-missing-secret",
        ),
        pytest.param(
            {},
            "[default]\naws_secret_access_key = other-secret\n",
            PARTIAL_PROFILE,
            id="split-pair",
        ),
        pytest.param({}, PARTIAL_PROFILE, "", id="config-missing-secret"),
        pytest.param({}, "", "", id="no-credentials"),
    ],
)
async def test_credentials_partial_values_stop_chain(
    aws_cli: str,
    tmp_path: Path,
    variables: dict[str, str],
    config: str,
    shared: str,
) -> None:
    async with credential_runtime(tmp_path) as (server, env):
        env.update(variables)
        write_config(env, config)
        write_config(env, shared, shared=True)
        result = await list_bucket(aws_cli, server, env)
    assert_credential_error(result, server)


# These settings are already guarded by native admission: in auto mode
# these are fallback regression tests, and in forced-native mode they
# describe missing capabilities.
@pytest.mark.parametrize(
    "config,diagnostic",
    [
        (
            (
                "role_arn = arn:aws:iam::123456789012:role/test\n"
                "source_profile = absent\n"
            ),
            "source_profile",
        ),
        (
            (
                "role_arn = arn:aws:iam::123456789012:role/test\n"
                "credential_source = Unknown\n"
            ),
            "credential source",
        ),
        ("sso_session = missing-session\n", "sso_session"),
        (
            (
                "sso_start_url = https://credential-parity.invalid/start\n"
                "sso_region = us-east-1\nsso_role_name = TestRole\n"
            ),
            "sso_account_id",
        ),
        ("login_session = synthetic-login\n", "login"),
    ],
    ids=[
        "missing-source-profile",
        "invalid-credential-source",
        "missing-sso-session",
        "incomplete-sso",
        "missing-login-token",
    ],
)
async def test_credentials_guarded_configuration_errors_fail_before_request(
    aws_cli: str, tmp_path: Path, config: str, diagnostic: str
) -> None:
    async with credential_runtime(tmp_path) as (server, env):
        write_config(env, "[default]\n" + config)
        result = await list_bucket(aws_cli, server, env)
    assert_credential_error(result, server)
    assert diagnostic in result[1].decode(), result[1].decode()
