from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest

from credhelpers import (
    CliRun,
    Sandbox,
    Stub,
    assert_signed_as_exported,
    assert_signed_by,
    credential_runtime,
    export_credentials_output,
    file_credentials,
    list_bucket,
    routed,
    run_export_credentials,
    run_s3_ls,
    successes,
    without_s3,
    write_config,
)

from tests.blackbox.utils import run_cli

pytestmark = pytest.mark.asyncio

ENV_KEYS: Final = {
    "AWS_ACCESS_KEY_ID": "AKIDENV",
    "AWS_SECRET_ACCESS_KEY": "ENV-secret",
}
FUTURE: Final = "2099-01-01T00:00:00Z"
FUTURE_ISO: Final = "2099-01-01T00:00:00+00:00"
# Static keys in two credentials-file profiles, for the profile-selection
# rows.
PROFILE_CREDENTIALS: Final = """\
[default]
aws_access_key_id = AKIDDEFAULT
aws_secret_access_key = DEFAULT-secret

[envtest]
aws_access_key_id = AKIDPROFILE
aws_secret_access_key = PROFILE-secret
"""
CONFIG_KEYS: Final = """\
[default]
aws_access_key_id = AKIDCONFIG
aws_secret_access_key = CONFIG-secret
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


def exported(
    access_key: str = "AKIDENV",
    secret_key: str = "ENV-secret",
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


def assert_outcome(run: CliRun, expected: Outcome) -> None:
    assert (run.returncode, run.stdout, run.stderr) == (
        expected.returncode,
        expected.stdout,
        expected.stderr,
    ), run.describe()
    assert run.requests == (), run.describe()


async def export(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    overrides: Mapping[str, str],
    *,
    globals_: Sequence[str] = (),
) -> CliRun:
    """Run export-credentials once with `overrides` in the env.

    Every request is a tripwire: the env provider never makes one. The
    providers here only read, so the run must leave the sandbox exactly
    as it found it.
    """
    server, proxy = stub
    env = {**sandbox.env(proxy), **overrides}
    run = await run_export_credentials(
        aws_cli,
        sandbox,
        [server],
        env,
        globals_=globals_,
        handlers={server: lambda: routed({})},
    )
    assert run.changes == {}, run.describe()
    return run


async def listing(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    overrides: Mapping[str, str],
    *,
    globals_: Sequence[str] = (),
) -> CliRun:
    """Run `s3 ls` once with `overrides` in the env, as `export` does."""
    server, proxy = stub
    env = {**sandbox.env(proxy), **overrides}
    return await run_s3_ls(
        aws_cli, sandbox, [server], env, s3=server, globals_=globals_
    )


def assert_signs_like(run: CliRun, expected: Outcome) -> None:
    """The listing carries the keys `expected` exports, and the env
    provider sent no request of its own."""
    assert_signed_as_exported(run, expected.stdout)
    assert without_s3(run).requests == (), run.describe()


TOKEN_ROWS: Final = [
    pytest.param(
        {"AWS_SESSION_TOKEN": "SESS"},
        exported(token="SESS"),
        id="session-token",
    ),
    pytest.param(
        {"AWS_SECURITY_TOKEN": "ST", "AWS_SESSION_TOKEN": "SESS"},
        exported(token="ST"),
        id="security-token-wins",
    ),
    pytest.param(
        {"AWS_SECURITY_TOKEN": "", "AWS_SESSION_TOKEN": "SESS"},
        exported(token="SESS"),
        id="empty-security-token-skipped",
    ),
    pytest.param(
        {"AWS_SECURITY_TOKEN": "", "AWS_SESSION_TOKEN": ""},
        exported(),
        id="empty-tokens-mean-none",
    ),
    pytest.param(
        {"AWS_ACCOUNT_ID": "123456789012"},
        exported(),
        id="account-id-not-exported",
    ),
    pytest.param(
        {
            "AWS_ACCESS_KEY_ID": "AKID \u00e9\t",
            "AWS_SECRET_ACCESS_KEY": " spaced secret ",
        },
        exported("AKID \u00e9\t", " spaced secret "),
        id="values-kept-verbatim",
    ),
]


# EnvProvider.fetch_credentials (credentials.py:1293-1331): the token is
# the first non-empty of AWS_SECURITY_TOKEN, AWS_SESSION_TOKEN;
# AWS_ACCOUNT_ID is never printed (exportcreds.py:140-153).
@pytest.mark.parametrize(
    ("overrides", "expected"),
    TOKEN_ROWS,
)
async def test_env_keys_export_with_first_non_empty_token(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    overrides: dict[str, str],
    expected: Outcome,
) -> None:
    run = await export(aws_cli, sandbox, stub, {**ENV_KEYS, **overrides})

    assert_outcome(run, expected)


@pytest.mark.parametrize(("overrides", "expected"), successes(TOKEN_ROWS))
async def test_env_keys_sign_listing_with_first_non_empty_token(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    overrides: dict[str, str],
    expected: Outcome,
) -> None:
    run = await listing(aws_cli, sandbox, stub, {**ENV_KEYS, **overrides})

    assert_signs_like(run, expected)


FALL_THROUGH_ROWS: Final = [
    pytest.param(
        {"AWS_SECRET_ACCESS_KEY": "ENV-secret"},
        "",
        wrapped("no credentials found"),
        id="secret-only",
    ),
    pytest.param(
        {"AWS_ACCESS_KEY_ID": "", "AWS_SECRET_ACCESS_KEY": "ENV-secret"},
        CONFIG_KEYS,
        exported("AKIDCONFIG", "CONFIG-secret"),
        id="empty-access-key-falls-through-to-config",
    ),
]


# EnvProvider.load (credentials.py:1257-1286) returns None for an empty or
# unset access key, so the chain moves on.
@pytest.mark.parametrize(
    ("env", "config", "expected"),
    FALL_THROUGH_ROWS,
)
async def test_env_without_access_key_falls_through_chain(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    env: dict[str, str],
    config: str,
    expected: Outcome,
) -> None:
    sandbox.config.write_text(config, encoding="utf-8")

    run = await export(aws_cli, sandbox, stub, env)

    assert_outcome(run, expected)


@pytest.mark.parametrize(
    ("env", "config", "expected"), successes(FALL_THROUGH_ROWS)
)
async def test_env_without_access_key_signs_listing_from_later_provider(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    env: dict[str, str],
    config: str,
    expected: Outcome,
) -> None:
    sandbox.config.write_text(config, encoding="utf-8")

    run = await listing(aws_cli, sandbox, stub, env)

    assert_signs_like(run, expected)


# A present access key without a secret raises PartialCredentialsError
# (credentials.py:1303-1307), which
# aborts the chain even when a later provider has keys.
@pytest.mark.parametrize(
    ("secret", "config"),
    [
        pytest.param("", "", id="empty-secret"),
        pytest.param(None, CONFIG_KEYS, id="missing-secret-aborts-chain"),
    ],
)
async def test_env_partial_credentials_abort_chain(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    secret: str | None,
    config: str,
) -> None:
    sandbox.config.write_text(config, encoding="utf-8")
    env = {"AWS_ACCESS_KEY_ID": "AKIDENV"}
    if secret is not None:
        env["AWS_SECRET_ACCESS_KEY"] = secret

    run = await export(aws_cli, sandbox, stub, env)

    assert_outcome(
        run,
        wrapped(
            "Partial credentials found in env, missing: AWS_SECRET_ACCESS_KEY"
        ),
    )


# A non-empty AWS_CREDENTIAL_EXPIRATION makes the env credentials
# refreshable (credentials.py:1265-1276), and the printed value is
# isoformat() with the offset kept. test_expiration.py owns the
# timestamp grammar and the refresh windows.
async def test_env_expiration_exported_with_session_token(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    env = {
        **ENV_KEYS,
        "AWS_CREDENTIAL_EXPIRATION": FUTURE,
        "AWS_SESSION_TOKEN": "SESS",
    }

    run = await export(aws_cli, sandbox, stub, env)

    assert_outcome(run, exported(token="SESS", expiration=FUTURE_ISO))


async def test_env_expiration_signs_listing_with_session_token(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    env = {
        **ENV_KEYS,
        "AWS_CREDENTIAL_EXPIRATION": FUTURE,
        "AWS_SESSION_TOKEN": "SESS",
    }

    run = await listing(aws_cli, sandbox, stub, env)

    assert_signs_like(run, exported(token="SESS"))


# Upstream sends a single download's HeadObject through its botocore client
# (customizations/s3/filegenerator.py:401), which refreshes expired
# credentials as it signs. The environment's refresh reads the same expired
# values again, and botocore raises that (credentials.py:616-627): it is
# not a chain without credentials.
@pytest.mark.parametrize("download", [False, True], ids=["listing", "head"])
async def test_env_expired_credentials_fail_with_the_refresh_error(
    aws_cli: str, tmp_path: Path, download: bool
) -> None:
    downloaded = tmp_path / "downloaded"
    arguments = ["s3", "ls", "s3://credential-parity/"]
    if download:
        arguments = ["s3", "cp", "s3://credential-parity/key", str(downloaded)]
    async with credential_runtime(tmp_path) as (server, env):
        env.update(ENV_KEYS, AWS_CREDENTIAL_EXPIRATION="2000-01-01T00:00:00Z")
        stdout, stderr, rc = await run_cli(aws_cli, arguments, env, timeout=20)

    assert rc != 0, f"stdout={stdout!r}, stderr={stderr!r}"
    assert (
        b"Credentials were refreshed, but the refreshed credentials are "
        b"still expired." in stderr
    ), stderr.decode()
    assert b"Unable to locate credentials" not in stderr
    assert not server.requests
    assert not downloaded.exists()


PROFILE_ROWS: Final = [
    pytest.param(
        {"AWS_PROFILE": "envtest"},
        (),
        exported(),
        id="aws-profile-keeps-env",
    ),
    pytest.param(
        {},
        ("--profile", "default"),
        exported("AKIDDEFAULT", "DEFAULT-secret"),
        id="explicit-default-profile-removes-env",
    ),
    pytest.param(
        {},
        ("--profile", ""),
        exported(),
        id="empty-explicit-profile-keeps-env",
    ),
    pytest.param(
        {"AWS_PROFILE": "default"},
        ("--profile", "envtest"),
        exported("AKIDPROFILE", "PROFILE-secret"),
        id="explicit-profile-overrides-aws-profile",
    ),
]


# Only a non-empty --profile, a session instance variable, removes the
# EnvProvider (credentials.py:92, 151-171; clidriver.py:635-638).
# AWS_PROFILE only chooses the profile.
@pytest.mark.parametrize(
    ("overrides", "globals_", "expected"),
    PROFILE_ROWS,
)
async def test_env_provider_skipped_only_for_explicit_profile(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    overrides: dict[str, str],
    globals_: tuple[str, ...],
    expected: Outcome,
) -> None:
    sandbox.credentials.write_text(PROFILE_CREDENTIALS, encoding="utf-8")

    run = await export(
        aws_cli,
        sandbox,
        stub,
        {**ENV_KEYS, **overrides},
        globals_=globals_,
    )

    assert_outcome(run, expected)


@pytest.mark.parametrize(
    ("overrides", "globals_", "expected"), successes(PROFILE_ROWS)
)
async def test_env_provider_signs_listing_unless_profile_is_explicit(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    overrides: dict[str, str],
    globals_: tuple[str, ...],
    expected: Outcome,
) -> None:
    sandbox.credentials.write_text(PROFILE_CREDENTIALS, encoding="utf-8")

    run = await listing(
        aws_cli,
        sandbox,
        stub,
        {**ENV_KEYS, **overrides},
        globals_=globals_,
    )

    assert_signs_like(run, expected)


# Signing: these tests resolve credentials for `s3 ls` and check which
# keys signed its request, so they show the provider's credentials
# reaching a signed service call and not only the exported output.


ENV_SESSION = {**ENV_KEYS, "AWS_SESSION_TOKEN": "ENV-token"}
CONFIG_PROFILE = "[default]\n" + file_credentials("CONFIG", "CONFIG-token")
SHARED_PROFILE = "[default]\n" + file_credentials("SHARED", "SHARED-token")


# Adapted from botocore EnvProvider/SharedCredentialProvider/ConfigProvider
# tests. Distinct secrets catch mixed-source credentials as well as wrong keys.
@pytest.mark.parametrize(
    ("variables", "identity", "token"),
    [
        pytest.param(ENV_SESSION, "ENV", "ENV-token", id="environment"),
        pytest.param(ENV_KEYS, "ENV", None, id="environment-no-token"),
        pytest.param(
            {**ENV_KEYS, "AWS_SESSION_TOKEN": ""},
            "ENV",
            None,
            id="environment-empty-token",
        ),
        pytest.param(
            {
                "AWS_SECRET_ACCESS_KEY": "ENV-secret",
                "AWS_SESSION_TOKEN": "ENV-token",
            },
            "SHARED",
            "SHARED-token",
            id="environment-secret-only",
        ),
        pytest.param(
            {**ENV_SESSION, "AWS_ACCESS_KEY_ID": ""},
            "SHARED",
            "SHARED-token",
            id="environment-empty-key",
        ),
    ],
)
async def test_credentials_environment_signs_with_highest_priority_source(
    aws_cli: str,
    tmp_path: Path,
    variables: dict[str, str],
    identity: str,
    token: str | None,
) -> None:
    async with credential_runtime(tmp_path) as (server, env):
        env.update(variables)
        write_config(env, CONFIG_PROFILE)
        write_config(env, SHARED_PROFILE, shared=True)
        result = await list_bucket(aws_cli, server, env)
    assert_signed_by(result, server, identity, token)


# These settings are already guarded by native admission. In auto mode these
# are fallback regression tests; in forced-native mode they describe missing
# capabilities, not silent CRT parity bugs.
@pytest.mark.parametrize(
    ("variables", "token"),
    [
        pytest.param(
            {**ENV_KEYS, "AWS_SECURITY_TOKEN": "legacy-token"},
            "legacy-token",
            id="legacy-env-token",
        ),
        pytest.param(
            {
                **ENV_KEYS,
                "AWS_SECURITY_TOKEN": "legacy-token",
                "AWS_SESSION_TOKEN": "modern-token",
            },
            "legacy-token",
            id="env-token-priority",
        ),
        pytest.param(
            {**ENV_KEYS, "AWS_CREDENTIAL_EXPIRATION": "2099-01-01T00:00:00Z"},
            None,
            id="env-expiration",
        ),
    ],
)
async def test_credentials_guarded_environment_signs_with_environment_keys(
    aws_cli: str,
    tmp_path: Path,
    variables: dict[str, str],
    token: str | None,
) -> None:
    async with credential_runtime(tmp_path) as (server, env):
        env.update(variables)
        result = await list_bucket(aws_cli, server, env)
    assert_signed_by(result, server, "ENV", token)
