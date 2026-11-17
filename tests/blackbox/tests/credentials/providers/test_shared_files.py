import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest

from credhelpers import (
    BytesStartingWith,
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

pytestmark = pytest.mark.asyncio

# exportcreds.py:269-279 wraps every load-phase exception, and
# errorhandler.py:316-321 renders it enhanced (errorformat.py:28-41).
CONFIGURATION_PREFIX: Final = (
    "\naws: [ERROR]: An error occurred (Configuration): "
    "Unable to retrieve credentials: "
)
NO_CREDENTIALS: Final = "no credentials found"
SHARED_KEYS: Final = """\
[default]
aws_access_key_id = AKIDSHARED
aws_secret_access_key = SHARED-secret
"""
CONFIG_KEYS: Final = """\
[default]
aws_access_key_id = AKIDCONFIG
aws_secret_access_key = CONFIG-secret
"""
BOTO_KEYS: Final = """\
[Credentials]
aws_access_key_id = AKIDBOTO
aws_secret_access_key = BOTO-secret
"""
EC2_KEYS: Final = "AWSAccessKeyId=AKIDEC2\nAWSSecretKey=EC2-secret\n"
EC2_FILE: Final = "ec2-credentials"
BOTO_HOME_FILE: Final = "home/boto.cfg"
# BotoProvider reads /etc/boto.cfg before ~/.boto when BOTO_CONFIG is
# unset (credentials.py:1503, 1518-1521); a host file would decide those
# rows, so they skip where one exists.
needs_no_host_boto = pytest.mark.skipif(
    os.path.exists("/etc/boto.cfg"),
    reason="/etc/boto.cfg on this host is read before ~/.boto",
)


@dataclass(frozen=True)
class Outcome:
    """What the command must print and return."""

    returncode: int
    stdout: bytes = b""
    stderr: bytes | BytesStartingWith = b""


def exported(
    access_key: str,
    secret_key: str,
    token: str | None = None,
) -> Outcome:
    return Outcome(0, export_credentials_output(access_key, secret_key, token))


def wrapped(message: str) -> Outcome:
    """A load-phase failure: ConfigurationError, rc 253."""
    return Outcome(253, stderr=f"{CONFIGURATION_PREFIX}{message}\n".encode())


def profile_not_found(name: str) -> Outcome:
    """ProfileNotFound for `name`, rc 253.

    test_export_credentials_command.py owns how this error is framed
    (upstream drops the Configuration prefix, errorhandler.py:184-233);
    these rows assert only which profile is missing.
    """
    message = f"The config profile ({name}) could not be found"
    return Outcome(
        253,
        stderr=BytesStartingWith(b"\naws: [ERROR]: ", (message.encode(),)),
    )


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
    overrides: Mapping[str, str | None] | None = None,
    *,
    globals_: Sequence[str] = (),
) -> CliRun:
    """Run export-credentials once with `overrides` applied to the env.

    `overrides` sets environment variables, or removes them when None.
    Every request is a tripwire: no file provider makes one. The file
    providers only read, so the run must leave the sandbox exactly as it
    found it.
    """
    server, proxy = stub
    env = sandbox.env(proxy)
    for key, value in (overrides or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
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
    overrides: Mapping[str, str | None] | None = None,
) -> CliRun:
    """Run `s3 ls` once with `overrides` applied to the env, as `export`
    does, and require that the run left the sandbox unchanged."""
    server, proxy = stub
    env = sandbox.env(proxy)
    for key, value in (overrides or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    run = await run_s3_ls(aws_cli, sandbox, [server], env, s3=server)
    assert run.changes == {}, run.describe()
    return run


def assert_signs_like(run: CliRun, expected: Outcome) -> None:
    """The listing carries the keys `expected` exports, and the file
    providers sent no request of their own."""
    assert_signed_as_exported(run, expected.stdout)
    assert without_s3(run).requests == (), run.describe()


SHARED_SECTION_ROWS = [
    pytest.param(
        SHARED_KEYS + "aws_session_token = SESS\n",
        None,
        exported("AKIDSHARED", "SHARED-secret", "SESS"),
        id="session-token",
    ),
    pytest.param(
        SHARED_KEYS + "aws_security_token = ST\naws_session_token = SESS\n",
        None,
        exported("AKIDSHARED", "SHARED-secret", "ST"),
        id="security-token-wins",
    ),
    pytest.param(
        SHARED_KEYS + "aws_security_token =\naws_session_token = SESS\n",
        None,
        exported("AKIDSHARED", "SHARED-secret", ""),
        id="empty-security-token-kept",
    ),
    pytest.param(
        "[default]\nAWS_ACCESS_KEY_ID = AKIDUP\n"
        "Aws_Secret_Access_Key = UP-secret\n",
        None,
        exported("AKIDUP", "UP-secret"),
        id="option-names-lowercased",
    ),
    pytest.param(
        "[default]\naws_access_key_id =\naws_secret_access_key =\n",
        None,
        exported("", ""),
        id="empty-values",
    ),
    pytest.param(
        "[default]\naws_access_key_id = AKIDML\n"
        "aws_secret_access_key = first\n  second\n"
        "aws_session_token = tok # not a comment ; nor this\n",
        None,
        exported("AKIDML", "first\nsecond", "tok # not a comment ; nor this"),
        id="continuation-and-literal-comment-characters",
    ),
    pytest.param(
        SHARED_KEYS + "\n[dev]\naws_access_key_id = AKIDDEV\n"
        "aws_secret_access_key = DEV-secret\n",
        "dev",
        exported("AKIDDEV", "DEV-secret"),
        id="named-profile",
    ),
    pytest.param(
        "[profile credsonly]\naws_access_key_id = AKIDPX\n"
        "aws_secret_access_key = PX-secret\n",
        "profile credsonly",
        exported("AKIDPX", "PX-secret"),
        id="profile-prefix-is-part-of-the-name",
    ),
    pytest.param(
        "[profile credsonly]\naws_access_key_id = AKIDPX\n"
        "aws_secret_access_key = PX-secret\n",
        "credsonly",
        profile_not_found("credsonly"),
        id="profile-prefix-not-stripped",
    ),
]


# SharedCredentialProvider (credentials.py:1371-1424) reads the literal
# credentials-file section: options lowercased, values stripped and kept
# verbatim otherwise (no inline comments, continuation lines joined with
# a newline), the token from the first *present* of aws_security_token,
# aws_session_token. A `[profile x]` section there is profile `profile x`
# (session.py:384-418).
@pytest.mark.parametrize(
    ("credentials", "profile", "expected"),
    SHARED_SECTION_ROWS,
)
async def test_shared_credentials_file_section_keys_export(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    credentials: str,
    profile: str | None,
    expected: Outcome,
) -> None:
    sandbox.credentials.write_text(credentials, encoding="utf-8")

    run = await export(
        aws_cli,
        sandbox,
        stub,
        {"AWS_PROFILE": profile},
    )

    assert_outcome(run, expected)


@pytest.mark.parametrize(
    ("credentials", "profile", "expected"), successes(SHARED_SECTION_ROWS)
)
async def test_shared_credentials_file_section_keys_sign_listing(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    credentials: str,
    profile: str | None,
    expected: Outcome,
) -> None:
    sandbox.credentials.write_text(credentials, encoding="utf-8")

    run = await listing(aws_cli, sandbox, stub, {"AWS_PROFILE": profile})

    assert_signs_like(run, expected)


CONFIG_PROFILE_ROWS = [
    pytest.param(
        "[profile dev]\naws_access_key_id = AKIDDEV\n"
        "aws_secret_access_key = DEV-secret\n"
        "aws_session_token = DEV-token\n",
        "dev",
        exported("AKIDDEV", "DEV-secret", "DEV-token"),
        id="named-profile",
    ),
    pytest.param(
        CONFIG_KEYS + "aws_security_token =\naws_session_token = SESS\n",
        None,
        exported("AKIDCONFIG", "CONFIG-secret", ""),
        id="empty-security-token-kept",
    ),
    pytest.param(
        "[dev]\naws_access_key_id = AKIDDEV\n"
        "aws_secret_access_key = DEV-secret\n",
        "dev",
        profile_not_found("dev"),
        id="bare-section-is-not-a-profile",
    ),
]


# ConfigProvider (credentials.py:1427-1494) reads the config file only,
# through build_profile_map (configloader.py:220-288): `[profile x]` is
# profile x and a bare `[x]` section is not a profile.
@pytest.mark.parametrize(
    ("config", "profile", "expected"),
    CONFIG_PROFILE_ROWS,
)
async def test_config_file_profile_keys_export(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    config: str,
    profile: str | None,
    expected: Outcome,
) -> None:
    sandbox.config.write_text(config, encoding="utf-8")

    run = await export(
        aws_cli,
        sandbox,
        stub,
        {"AWS_PROFILE": profile},
    )

    assert_outcome(run, expected)


@pytest.mark.parametrize(
    ("config", "profile", "expected"), successes(CONFIG_PROFILE_ROWS)
)
async def test_config_file_profile_keys_sign_listing(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    config: str,
    profile: str | None,
    expected: Outcome,
) -> None:
    sandbox.config.write_text(config, encoding="utf-8")

    run = await listing(aws_cli, sandbox, stub, {"AWS_PROFILE": profile})

    assert_signs_like(run, expected)


# _extract_creds_from_mapping (credentials.py:1064-1073) raises
# PartialCredentialsError once the access key is present, which aborts
# the chain. Each file provider sees only its own file, so split keys are
# the later provider's partial error.
@pytest.mark.parametrize(
    ("credentials", "config", "message"),
    [
        pytest.param(
            "[default]\naws_secret_access_key = SHARED-secret\n",
            "[default]\naws_access_key_id = AKIDCONFIG\n",
            "Partial credentials found in config-file, "
            "missing: aws_secret_access_key",
            id="split-key-in-config",
        ),
        pytest.param(
            "[default]\naws_access_key_id = AKIDSHARED\n",
            "[default]\naws_secret_access_key = CONFIG-secret\n",
            "Partial credentials found in shared-credentials-file, "
            "missing: aws_secret_access_key",
            id="split-key-in-credentials",
        ),
        pytest.param(
            "[default]\naws_access_key_id = AKIDSHARED\n",
            CONFIG_KEYS,
            "Partial credentials found in shared-credentials-file, "
            "missing: aws_secret_access_key",
            id="credentials-file-partial-aborts-before-config",
        ),
    ],
)
async def test_static_partial_credentials_abort_chain(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    credentials: str,
    config: str,
    message: str,
) -> None:
    sandbox.credentials.write_text(credentials, encoding="utf-8")
    sandbox.config.write_text(config, encoding="utf-8")

    run = await export(aws_cli, sandbox, stub)

    assert_outcome(run, wrapped(message))


# A credentials file that is not a regular file or is unreadable
# contributes no sections (configloader.py:142-150, session.py:396-418):
# configparser.read skips what it cannot open.
@pytest.mark.parametrize(
    ("target", "mode"),
    [
        pytest.param("home", None, id="credentials-is-directory"),
        pytest.param("credentials", 0o000, id="credentials-unreadable"),
    ],
)
async def test_unusable_shared_file_contributes_no_profiles(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    target: str,
    mode: int | None,
) -> None:
    # The unusable file holds a partial key, which would abort the chain
    # if read; the config file holds the keys that must win.
    sandbox.credentials.write_text(
        "[default]\naws_access_key_id = AKIDHIDDEN\n", encoding="utf-8"
    )
    sandbox.config.write_text(CONFIG_KEYS, encoding="utf-8")
    path = sandbox.root / target
    if mode is not None:
        path.chmod(mode)
        if os.access(path, os.R_OK):
            pytest.skip("this user reads mode-000 files")

    run = await export(
        aws_cli,
        sandbox,
        stub,
        {"AWS_SHARED_CREDENTIALS_FILE": str(path)},
    )

    assert_outcome(run, exported("AKIDCONFIG", "CONFIG-secret"))


@pytest.mark.parametrize(
    ("target", "mode"),
    [
        pytest.param("home", None, id="credentials-is-directory"),
        pytest.param("credentials", 0o000, id="credentials-unreadable"),
    ],
)
async def test_unusable_shared_file_skipped_when_signing_listing(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    target: str,
    mode: int | None,
) -> None:
    sandbox.credentials.write_text(
        "[default]\naws_access_key_id = AKIDHIDDEN\n", encoding="utf-8"
    )
    sandbox.config.write_text(CONFIG_KEYS, encoding="utf-8")
    path = sandbox.root / target
    if mode is not None:
        path.chmod(mode)
        if os.access(path, os.R_OK):
            pytest.skip("this user reads mode-000 files")

    run = await listing(
        aws_cli,
        sandbox,
        stub,
        {"AWS_SHARED_CREDENTIALS_FILE": str(path)},
    )

    assert_signs_like(run, exported("AKIDCONFIG", "CONFIG-secret"))


EC2_PAIR_ROWS = [
    pytest.param(
        "AWSAccessKeyId = AKIDEC2 \nnot a pair\n"
        "AWSSecretKey= EC2=secret \nAWSSessionToken=ignored\n",
        EC2_FILE,
        exported("AKIDEC2", "EC2=secret"),
        id="stripped-split-once-no-token",
    ),
    pytest.param(
        "AWSAccessKeyId=AKIDOLD\n" + EC2_KEYS,
        EC2_FILE,
        exported("AKIDEC2", "EC2-secret"),
        id="later-key-wins",
    ),
    pytest.param(
        EC2_KEYS,
        f"~/{EC2_FILE}",
        exported("AKIDEC2", "EC2-secret"),
        id="tilde-expanded",
    ),
]


# OriginalEC2Provider (credentials.py:1336-1368) engages when
# AWS_CREDENTIAL_FILE is present and parses it with parse_key_val_file
# (utils.py:696-717): expanduser, lines without `=` skipped,
# split('=', 1), both sides stripped, later keys winning. It never
# returns a token.
@pytest.mark.parametrize(
    ("content", "path", "expected"),
    EC2_PAIR_ROWS,
)
async def test_ec2_credentials_file_key_value_pairs_export(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    content: str,
    path: str,
    expected: Outcome,
) -> None:
    sandbox.write(EC2_FILE, content)
    sandbox.write(f"home/{EC2_FILE}", content)
    variable = path if path.startswith("~") else str(sandbox.root / path)

    run = await export(
        aws_cli,
        sandbox,
        stub,
        {"AWS_CREDENTIAL_FILE": variable},
    )

    assert_outcome(run, expected)


@pytest.mark.parametrize(
    ("content", "path", "expected"), successes(EC2_PAIR_ROWS)
)
async def test_ec2_credentials_file_key_value_pairs_sign_listing(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    content: str,
    path: str,
    expected: Outcome,
) -> None:
    sandbox.write(EC2_FILE, content)
    sandbox.write(f"home/{EC2_FILE}", content)
    variable = path if path.startswith("~") else str(sandbox.root / path)

    run = await listing(
        aws_cli,
        sandbox,
        stub,
        {"AWS_CREDENTIAL_FILE": variable},
    )

    assert_signs_like(run, expected)


# Only an OSError from open() becomes ConfigNotFound (utils.py:701-702).
# Both are load-phase errors.
@pytest.mark.parametrize(
    ("variable", "message"),
    [
        pytest.param(
            "{root}/missing",
            "The specified config file ({root}/missing) could not be found.",
            id="missing",
        ),
        pytest.param(
            "",
            "The specified config file () could not be found.",
            id="empty-variable",
        ),
    ],
)
async def test_ec2_credentials_file_errors_abort_chain(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    variable: str,
    message: str,
) -> None:
    # Valid keys later in the chain do not rescue a raising provider.
    sandbox.boto.write_text(BOTO_KEYS, encoding="utf-8")
    root = str(sandbox.root)

    run = await export(
        aws_cli,
        sandbox,
        stub,
        {"AWS_CREDENTIAL_FILE": variable.format(root=root)},
    )

    assert_outcome(run, wrapped(message.format(root=root)))


# Upstream bug, matched for parity: an access key without AWSSecretKey
# escapes as a bare KeyError (credentials.py:1364), still a load-phase
# error that aborts the chain. Its text is CPython's KeyError repr.
async def test_ec2_credentials_file_without_secret_aborts_chain(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    path = sandbox.write(EC2_FILE, "AWSAccessKeyId=AKIDEC2\n")
    sandbox.boto.write_text(BOTO_KEYS, encoding="utf-8")

    run = await export(
        aws_cli,
        sandbox,
        stub,
        {"AWS_CREDENTIAL_FILE": str(path)},
    )

    assert_outcome(
        run,
        Outcome(
            253,
            stderr=BytesStartingWith(
                CONFIGURATION_PREFIX.encode(), (b"AWSSecretKey",)
            ),
        ),
    )


async def test_ec2_credentials_file_without_access_key_falls_through(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    path = sandbox.write(EC2_FILE, "AWSSecretKey=EC2-secret\n")
    sandbox.boto.write_text(BOTO_KEYS, encoding="utf-8")

    run = await export(
        aws_cli,
        sandbox,
        stub,
        {"AWS_CREDENTIAL_FILE": str(path)},
    )

    assert_outcome(run, exported("AKIDBOTO", "BOTO-secret"))


async def test_ec2_credentials_file_without_access_key_signs_from_boto(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    path = sandbox.write(EC2_FILE, "AWSSecretKey=EC2-secret\n")
    sandbox.boto.write_text(BOTO_KEYS, encoding="utf-8")

    run = await listing(
        aws_cli,
        sandbox,
        stub,
        {"AWS_CREDENTIAL_FILE": str(path)},
    )

    assert_signs_like(run, exported("AKIDBOTO", "BOTO-secret"))


BOTO_ROWS = [
    pytest.param(
        BOTO_KEYS + "aws_session_token = ignored\n",
        "{boto}",
        exported("AKIDBOTO", "BOTO-secret"),
        id="session-token-ignored",
    ),
    pytest.param(
        BOTO_KEYS,
        "~/boto.cfg",
        exported("AKIDBOTO", "BOTO-secret"),
        id="tilde-expanded",
    ),
    pytest.param(
        BOTO_KEYS,
        "$HOME/boto.cfg",
        exported("AKIDBOTO", "BOTO-secret"),
        id="home-variable-expanded",
    ),
    pytest.param(
        BOTO_KEYS.replace("[Credentials]", "[credentials]"),
        "{boto}",
        wrapped(NO_CREDENTIALS),
        id="section-name-case-sensitive",
    ),
    pytest.param(
        "[Credentials]\naws_secret_access_key = BOTO-secret\n",
        "{boto}",
        wrapped(NO_CREDENTIALS),
        id="secret-only-ignored",
    ),
    pytest.param(
        BOTO_KEYS,
        "",
        wrapped(NO_CREDENTIALS),
        id="empty-variable-skips-default-locations",
    ),
]


# BotoProvider (credentials.py:1497-1540) reads `[environ['BOTO_CONFIG']]`
# when the variable is present, even empty, else /etc/boto.cfg and
# ~/.boto, through raw_config_parse (expandvars, expanduser, not a file
# -> next location). Only a case-sensitive `[Credentials]` section with
# aws_access_key_id engages; it never returns a token.
@pytest.mark.parametrize(
    ("content", "variable", "expected"),
    BOTO_ROWS,
)
async def test_boto_config_credentials_section_exports(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    content: str,
    variable: str,
    expected: Outcome,
) -> None:
    sandbox.boto.write_text(content, encoding="utf-8")
    sandbox.write(BOTO_HOME_FILE, content)
    # The default location, which BOTO_CONFIG= must not consult.
    sandbox.write("home/.boto", content)
    value = variable.format(boto=sandbox.boto)

    run = await export(aws_cli, sandbox, stub, {"BOTO_CONFIG": value})

    assert_outcome(run, expected)


@pytest.mark.parametrize(
    ("content", "variable", "expected"), successes(BOTO_ROWS)
)
async def test_boto_config_credentials_section_signs_listing(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    content: str,
    variable: str,
    expected: Outcome,
) -> None:
    sandbox.boto.write_text(content, encoding="utf-8")
    sandbox.write(BOTO_HOME_FILE, content)
    sandbox.write("home/.boto", content)
    value = variable.format(boto=sandbox.boto)

    run = await listing(aws_cli, sandbox, stub, {"BOTO_CONFIG": value})

    assert_signs_like(run, expected)


@needs_no_host_boto
async def test_boto_config_unset_reads_home_boto(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    sandbox.write("home/.boto", BOTO_KEYS)

    run = await export(aws_cli, sandbox, stub, {"BOTO_CONFIG": None})

    assert_outcome(run, exported("AKIDBOTO", "BOTO-secret"))


@needs_no_host_boto
async def test_boto_config_unset_signs_listing_from_home_boto(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    sandbox.write("home/.boto", BOTO_KEYS)

    run = await listing(aws_cli, sandbox, stub, {"BOTO_CONFIG": None})

    assert_signs_like(run, exported("AKIDBOTO", "BOTO-secret"))


# A boto file is parsed only when BotoProvider runs, so its errors are
# load-phase errors, and earlier providers' keys win without reading
# it.
@pytest.mark.parametrize(
    ("content", "message"),
    [
        pytest.param(
            "[Credentials]\naws_access_key_id = AKIDBOTO\n",
            "Partial credentials found in boto-config, "
            "missing: aws_secret_access_key",
            id="partial",
        ),
        pytest.param(
            "[broken\n",
            "Unable to parse config file: {boto}",
            id="malformed",
        ),
    ],
)
async def test_boto_config_errors_abort_chain(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
    content: str,
    message: str,
) -> None:
    sandbox.boto.write_text(content, encoding="utf-8")

    run = await export(aws_cli, sandbox, stub)

    assert_outcome(run, wrapped(message.format(boto=sandbox.boto)))


async def test_boto_config_malformed_unread_when_config_has_keys(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    sandbox.boto.write_text("[broken\n", encoding="utf-8")
    sandbox.config.write_text(CONFIG_KEYS, encoding="utf-8")

    run = await export(aws_cli, sandbox, stub)

    assert_outcome(run, exported("AKIDCONFIG", "CONFIG-secret"))


async def test_boto_config_malformed_unread_when_signing_from_config(
    aws_cli: str,
    sandbox: Sandbox,
    stub: Stub,
) -> None:
    sandbox.boto.write_text("[broken\n", encoding="utf-8")
    sandbox.config.write_text(CONFIG_KEYS, encoding="utf-8")

    run = await listing(aws_cli, sandbox, stub)

    assert_signs_like(run, exported("AKIDCONFIG", "CONFIG-secret"))


# Signing: these tests resolve credentials for `s3 ls` and check which
# keys signed its request, so they show the provider's credentials
# reaching a signed service call and not only the exported output.


ENV_KEYS = {
    "AWS_ACCESS_KEY_ID": "AKIDENV",
    "AWS_SECRET_ACCESS_KEY": "ENV-secret",
}
ENV_SESSION = {**ENV_KEYS, "AWS_SESSION_TOKEN": "ENV-token"}
CONFIG_PROFILE = "[default]\n" + file_credentials("CONFIG", "CONFIG-token")
SHARED_PROFILE = "[default]\n" + file_credentials("SHARED", "SHARED-token")
SELECTED_PROFILE = "[selected]\n" + file_credentials(
    "SELECTED", "SELECTED-token"
)
MODERN_TOKEN = "aws_session_token = modern-token\n"


EC2_CREDENTIAL_FILE = (
    "AWSAccessKeyId=AKIDEC2FILE\nAWSSecretKey=EC2FILE-secret\n"
)
BOTO_CREDENTIALS = "[Credentials]\n" + file_credentials("BOTO")


def legacy_token_profile(identity: str) -> str:
    return (
        "[default]\n"
        + file_credentials(identity)
        + "aws_security_token = legacy-token\n"
    )


@pytest.mark.parametrize(
    ("config", "shared", "identity", "token"),
    [
        pytest.param(
            CONFIG_PROFILE,
            SHARED_PROFILE,
            "SHARED",
            "SHARED-token",
            id="shared",
        ),
        pytest.param(
            CONFIG_PROFILE,
            "[default]\n" + file_credentials("SHARED"),
            "SHARED",
            None,
            id="shared-no-token",
        ),
        pytest.param(
            CONFIG_PROFILE,
            "[default]\naws_secret_access_key = stray-secret\n",
            "CONFIG",
            "CONFIG-token",
            id="shared-secret-only",
        ),
        pytest.param(
            CONFIG_PROFILE, "", "CONFIG", "CONFIG-token", id="config"
        ),
        pytest.param(
            CONFIG_PROFILE,
            "[default]\naws_session_token = stray-token\n",
            "CONFIG",
            "CONFIG-token",
            id="shared-token-only",
        ),
        pytest.param(
            CONFIG_PROFILE,
            legacy_token_profile("SHARED"),
            "SHARED",
            "legacy-token",
            id="shared-legacy-token",
        ),
        pytest.param(
            CONFIG_PROFILE,
            legacy_token_profile("SHARED") + MODERN_TOKEN,
            "SHARED",
            "legacy-token",
            id="shared-both-tokens",
        ),
        pytest.param(
            legacy_token_profile("CONFIG"),
            "",
            "CONFIG",
            "legacy-token",
            id="config-legacy-token",
        ),
        pytest.param(
            legacy_token_profile("CONFIG") + MODERN_TOKEN,
            "",
            "CONFIG",
            "legacy-token",
            id="config-both-tokens",
        ),
    ],
)
async def test_credentials_files_sign_with_highest_priority_source(
    aws_cli: str,
    tmp_path: Path,
    config: str,
    shared: str,
    identity: str,
    token: str | None,
) -> None:
    async with credential_runtime(tmp_path) as (server, env):
        write_config(env, config)
        write_config(env, shared, shared=True)
        result = await list_bucket(aws_cli, server, env)
    assert_signed_by(result, server, identity, token)


@pytest.mark.parametrize(
    ("variables", "arguments", "identity", "token"),
    [
        pytest.param(
            {**ENV_SESSION, "AWS_PROFILE": "selected"},
            [],
            "ENV",
            "ENV-token",
            id="profile-env",
        ),
        pytest.param(
            {**ENV_SESSION, "AWS_PROFILE": "default"},
            ["--profile", "selected"],
            "SELECTED",
            "SELECTED-token",
            id="profile-flag",
        ),
        pytest.param(
            {**ENV_SESSION, "AWS_PROFILE": "selected"},
            ["--profile", ""],
            "ENV",
            "ENV-token",
            id="profile-empty-flag",
        ),
        pytest.param(
            {"AWS_DEFAULT_PROFILE": "selected"},
            [],
            "SELECTED",
            "SELECTED-token",
            id="profile-default-env",
        ),
        pytest.param(
            {"AWS_PROFILE": "selected", "AWS_DEFAULT_PROFILE": "default"},
            [],
            "SELECTED",
            "SELECTED-token",
            id="profile-env-priority",
        ),
    ],
)
async def test_credentials_profile_selection_signs_with_highest_priority(
    aws_cli: str,
    tmp_path: Path,
    variables: dict[str, str],
    arguments: list[str],
    identity: str,
    token: str | None,
) -> None:
    async with credential_runtime(tmp_path) as (server, env):
        env.update(variables)
        write_config(env, CONFIG_PROFILE)
        write_config(env, SHARED_PROFILE + SELECTED_PROFILE, shared=True)
        result = await list_bucket(aws_cli, server, env, *arguments)
    assert_signed_by(result, server, identity, token)


@pytest.mark.parametrize(
    ("ec2_file", "boto", "shared", "identity"),
    [
        pytest.param(EC2_CREDENTIAL_FILE, "", "", "EC2FILE", id="ec2-file"),
        pytest.param(None, BOTO_CREDENTIALS, "", "BOTO", id="boto"),
        pytest.param(
            EC2_CREDENTIAL_FILE,
            BOTO_CREDENTIALS,
            "",
            "EC2FILE",
            id="ec2-before-boto",
        ),
        pytest.param(
            EC2_CREDENTIAL_FILE,
            BOTO_CREDENTIALS,
            "[default]\n" + file_credentials("SHARED"),
            "SHARED",
            id="shared-before-legacy",
        ),
    ],
)
async def test_credentials_legacy_file_providers_sign_with_highest_priority(
    aws_cli: str,
    tmp_path: Path,
    ec2_file: str | None,
    boto: str,
    shared: str,
    identity: str,
) -> None:
    async with credential_runtime(tmp_path) as (server, env):
        if ec2_file is not None:
            path = tmp_path / "ec2-credentials"
            path.write_text(ec2_file)
            env["AWS_CREDENTIAL_FILE"] = str(path)
        Path(env["BOTO_CONFIG"]).write_text(boto)
        write_config(env, shared, shared=True)
        result = await list_bucket(aws_cli, server, env)
    assert_signed_by(result, server, identity)
