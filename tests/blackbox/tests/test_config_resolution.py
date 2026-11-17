import os
import sys
from collections.abc import AsyncIterator, Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
import pytest_asyncio
from localstub import AsyncHTTPTestServer, AsyncTLSInterceptProxy
from localstub.handlers import handle_expect_header

from credhelpers import (
    CommandTimeoutError,
    assert_signature,
    credential_env,
    file_credentials,
    list_bucket,
    run_command,
    write_config,
)
from nethelpers import ClientHelloRecorder
from s3helpers import completion_lines
from tests.blackbox.utils import (
    get_object_response,
    head_object_response,
    mock_server,
    put_object_response,
    run_cli,
)


REGION_PROFILE = "[default]\nregion = ap-south-1\n"
CA_CENTRAL_PROFILE = "[default]\nregion = ca-central-1\n"
SELECTED_PROFILE = (
    REGION_PROFILE
    + "[profile selected]\nregion = eu-central-1\n"
    + file_credentials("CONFIG")
)
QUOTED_PROFILE = (
    REGION_PROFILE
    + '[profile "space name"]\nregion = eu-central-1\n'
    + file_credentials("CONFIG")
)
SHARED_SELECTED_PROFILE = (
    "[selected]\nregion = eu-central-1\n" + file_credentials("CONFIG")
)
SETTINGS_NAME = "settings with spaces"
MALFORMED = "not an INI file"
BAD_CLI_ENDPOINT = ("--endpoint-url", "not-a-url")
PROFILE_ENDPOINT = (
    "[default]\nendpoint_url = https://profile.invalid/profile-base\n"
)
SERVICES_CHOSEN = "services = chosen\n"
S3_SERVICE_CONFIG = (
    "[services chosen]\ns3 =\n"
    "    endpoint_url = https://service-config.invalid/service-config-base\n"
)
CHOSEN_SERVICES = PROFILE_ENDPOINT + SERVICES_CHOSEN + S3_SERVICE_CONFIG
IGNORE_PROFILE = (
    PROFILE_ENDPOINT
    + SERVICES_CHOSEN
    + "ignore_configured_endpoint_urls = true\n"
    + S3_SERVICE_CONFIG
)
SELECTED_ENDPOINT_PROFILE = (
    "[default]\nendpoint_url = https://unused.invalid\n"
    "[profile selected]\n"
    "endpoint_url = https://profile.invalid/profile-base\n"
    + SERVICES_CHOSEN
    + file_credentials("CONFIG")
    + S3_SERVICE_CONFIG
)
ABSENT_SERVICES = (
    "[default]\nservices = absent\nendpoint_url = https://unused.invalid\n"
)
GLOBAL_ENV_ENDPOINT = {
    "AWS_ENDPOINT_URL": "https://global-env.invalid/global-env-base"
}
S3_ENV_ENDPOINT = {
    "AWS_ENDPOINT_URL_S3": "https://service-env.invalid/service-env-base"
}
IGNORE_ENV = {
    "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS": "true",
    "AWS_ENDPOINT_URL_S3": "https://ignored.invalid/ignored",
}
CLI_ENDPOINT = ("--endpoint-url", "https://cli.invalid/cli-base")
# Endpoint URLs the AWS CLI refuses before any request: the S3 endpoint
# rules refuse a scheme other than http or https, a query, and a port that
# is not a number from 0 to 65535, and botocore refuses a URL whose host it
# cannot read.
FTP_ENDPOINT = "ftp://127.0.0.1:1"
QUERY_ENDPOINT = "https://127.0.0.1:9/?a=b"
PORT_TEXT_ENDPOINT = "https://127.0.0.1:abc"
PORT_RANGE_ENDPOINT = "https://127.0.0.1:70000"
NO_HOST_ENDPOINT = "http:x://127.0.0.1:9/p"

each_settings_file = pytest.mark.parametrize(
    "key",
    ["AWS_CONFIG_FILE", "AWS_SHARED_CREDENTIALS_FILE"],
    ids=["config", "shared-file"],
)


@dataclass(frozen=True)
class Scenario:
    """The settings files, environment changes, and arguments of a run."""

    config: str = ""
    shared: str = ""
    # A None value removes the variable.
    env: Mapping[str, str | None] = field(default_factory=dict)
    arguments: tuple[str, ...] = ()


@pytest_asyncio.fixture
async def config_runtime(
    tmp_path: Path,
) -> AsyncIterator[tuple[AsyncHTTPTestServer, dict[str, str]]]:
    # An upload waits for the 100 Continue only this handler sends.
    async with mock_server(handle_expect_header) as (server, proxy):
        yield server, config_env(proxy, tmp_path)


def config_env(
    proxy: AsyncTLSInterceptProxy, tmp_path: Path
) -> dict[str, str]:
    env = credential_env(proxy, tmp_path)
    env.update(
        AWS_ACCESS_KEY_ID="AKIDCONFIG",
        AWS_SECRET_ACCESS_KEY="CONFIG-secret",
        AWS_REGION="eu-west-1",
    )
    del env["AWS_DEFAULT_REGION"]
    return env


def apply_scenario(env: dict[str, str], scenario: Scenario) -> None:
    for key, value in scenario.env.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    write_config(env, scenario.config)
    write_config(env, scenario.shared, shared=True)


async def list_scenario(
    aws_cli: str,
    server: AsyncHTTPTestServer,
    env: dict[str, str],
    scenario: Scenario,
) -> tuple[bytes, bytes, int]:
    apply_scenario(env, scenario)
    return await list_bucket(aws_cli, server, env, *scenario.arguments)


async def upload_scenario(
    aws_cli: str,
    server: AsyncHTTPTestServer,
    env: dict[str, str],
    scenario: Scenario,
    source: Path,
    *,
    timeout: float = 20,
) -> tuple[bytes, bytes, int]:
    apply_scenario(env, scenario)
    server.set_default_response(put_object_response())
    return await run_cli(
        aws_cli, upload_arguments(scenario, source), env, timeout=timeout
    )


def upload_arguments(scenario: Scenario, source: Path) -> list[str]:
    return [
        "s3",
        "cp",
        str(source),
        "s3://credential-parity/key",
        "--no-progress",
        *scenario.arguments,
    ]


def regional_host(region: str) -> str:
    return f"credential-parity.s3.{region}.amazonaws.com"


def assert_config_request(
    result: tuple[bytes, bytes, int],
    server: AsyncHTTPTestServer,
    region: str,
    host: str,
    path: str = "/",
) -> None:
    stdout, stderr, rc = result
    assert (rc, stdout, stderr) == (0, b"", b"")
    assert len(server.requests) == 1
    request = server.requests[0]
    assert request.method == "GET"
    assert request.headers["host"] == host
    assert urlsplit(request.effective_path).path == path
    assert parse_qs(urlsplit(request.effective_path).query)["list-type"] == [
        "2"
    ]
    scope = (
        request.headers["authorization"]
        .split("Credential=", 1)[1]
        .split(",", 1)[0]
        .split("/")
    )
    assert scope[2:] == [region, "s3", "aws4_request"]
    assert_signature(request, "AKIDCONFIG", "CONFIG-secret")


def assert_upload_request(
    result: tuple[bytes, bytes, int],
    server: AsyncHTTPTestServer,
    host: str,
    base: str,
) -> None:
    _, stderr, rc = result
    assert (rc, stderr) == (0, b""), stderr.decode()
    assert [r.method for r in server.requests] == ["PUT"]
    request = server.requests[0]
    assert request.headers["host"] == host
    path = urlsplit(request.effective_path).path
    assert path == f"{base}/credential-parity/key"


def assert_config_error(
    result: tuple[bytes, bytes, int],
    server: AsyncHTTPTestServer,
    status: int,
    diagnostic: str,
) -> None:
    stdout, stderr, rc = result
    assert rc == status, stderr.decode()
    assert stdout == b""
    assert diagnostic in stderr.decode(), stderr.decode()
    assert b"native implementation unavailable" not in stderr
    assert not server.requests


# Botocore's session config chain: explicit arguments, AWS_REGION,
# AWS_DEFAULT_REGION, merged profile, then the S3 default region.
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario,expected",
    [
        pytest.param(
            Scenario(REGION_PROFILE, arguments=("--region", "eu-central-1")),
            "eu-central-1",
            id="cli-eu-central-1",
        ),
        pytest.param(
            Scenario(REGION_PROFILE),
            "eu-west-1",
            id="environment-eu-west-1",
        ),
        pytest.param(
            Scenario(REGION_PROFILE, env={"AWS_REGION": None}),
            "ap-northeast-1",
            id="default-environment-ap-northeast-1",
        ),
        pytest.param(
            Scenario(
                REGION_PROFILE,
                env={"AWS_REGION": None, "AWS_DEFAULT_REGION": None},
            ),
            "ap-south-1",
            id="profile-ap-south-1",
        ),
        pytest.param(
            Scenario(
                REGION_PROFILE,
                CA_CENTRAL_PROFILE,
                env={"AWS_REGION": None, "AWS_DEFAULT_REGION": None},
            ),
            "ca-central-1",
            id="shared-over-config-ca-central-1",
        ),
        pytest.param(
            Scenario(REGION_PROFILE, CA_CENTRAL_PROFILE),
            "eu-west-1",
            id="environment-over-shared-eu-west-1",
        ),
    ],
)
async def test_config_region_precedence_selects_highest_priority_source(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    scenario: Scenario,
    expected: str,
) -> None:
    server, env = config_runtime
    env["AWS_DEFAULT_REGION"] = "ap-northeast-1"
    result = await list_scenario(aws_cli, server, env, scenario)
    assert_config_request(result, server, expected, regional_host(expected))


@pytest.mark.asyncio
async def test_config_region_without_any_source_defaults_to_us_east_1(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = config_runtime
    del env["AWS_REGION"]
    result = await list_bucket(aws_cli, server, env)
    assert_config_request(
        result, server, "us-east-1", "credential-parity.s3.amazonaws.com"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(
            Scenario(
                SELECTED_PROFILE,
                env={"AWS_PROFILE": "default"},
                arguments=("--profile", "selected"),
            ),
            id="flag",
        ),
        pytest.param(
            Scenario(SELECTED_PROFILE, env={"AWS_PROFILE": "selected"}),
            id="environment",
        ),
        pytest.param(
            Scenario(
                SELECTED_PROFILE,
                env={"AWS_PROFILE": None, "AWS_DEFAULT_PROFILE": "selected"},
            ),
            id="default-environment",
        ),
        pytest.param(
            Scenario(
                SELECTED_PROFILE,
                env={
                    "AWS_PROFILE": "selected",
                    "AWS_DEFAULT_PROFILE": "default",
                },
            ),
            id="env-priority",
        ),
        pytest.param(
            Scenario(
                SELECTED_PROFILE,
                env={"AWS_PROFILE": "selected"},
                arguments=("--profile", ""),
            ),
            id="empty-flag",
        ),
        pytest.param(
            Scenario(
                QUOTED_PROFILE,
                env={"AWS_PROFILE": "default"},
                arguments=("--profile", "space name"),
            ),
            id="quoted-name",
        ),
        pytest.param(
            Scenario(
                REGION_PROFILE,
                SHARED_SELECTED_PROFILE,
                env={"AWS_PROFILE": "selected"},
            ),
            id="shared-file-only",
        ),
    ],
)
async def test_config_selected_profile_supplies_region(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    scenario: Scenario,
) -> None:
    server, env = config_runtime
    del env["AWS_REGION"]
    result = await list_scenario(aws_cli, server, env, scenario)
    assert_config_request(
        result, server, "eu-central-1", regional_host("eu-central-1")
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "setting",
    [
        "role_arn = arn:aws:iam::123456789012:role/unused",
        "s3 =\n    addressing_style = invalid",
        "services = missing-services",
    ],
    ids=["role", "addressing-style", "services"],
)
async def test_config_unselected_profile_does_not_affect_request(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    setting: str,
) -> None:
    server, env = config_runtime
    write_config(
        env, f"[default]\nregion = ap-south-1\n[profile unused]\n{setting}\n"
    )
    result = await list_bucket(aws_cli, server, env)
    assert_config_request(
        result,
        server,
        "eu-west-1",
        "credential-parity.s3.eu-west-1.amazonaws.com",
    )


@pytest.mark.asyncio
@each_settings_file
@pytest.mark.parametrize(
    "prepare",
    [
        pytest.param(lambda path: None, id="missing"),
        pytest.param(lambda path: path.write_text(""), id="empty"),
        pytest.param(Path.mkdir, id="directory"),
    ],
)
async def test_config_unusable_file_path_falls_back_to_environment_region(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    key: str,
    prepare: Callable[[Path], object],
) -> None:
    server, env = config_runtime
    del env["AWS_REGION"]
    path = tmp_path / SETTINGS_NAME
    prepare(path)
    env["AWS_DEFAULT_REGION"] = "eu-west-1"
    env[key] = str(path)
    result = await list_bucket(aws_cli, server, env)
    assert_config_request(
        result, server, "eu-west-1", regional_host("eu-west-1")
    )


# Root reads a mode-000 file, so each host runs the test for its own
# privilege: denied access, or a readable file under its own name.
@pytest.mark.asyncio
@each_settings_file
async def test_config_unreadable_file_path_falls_back_to_default_region(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    key: str,
) -> None:
    server, env = config_runtime
    del env["AWS_REGION"]
    path = tmp_path / SETTINGS_NAME
    path.write_text(CA_CENTRAL_PROFILE)
    path.chmod(0)
    if os.access(path, os.R_OK):
        pytest.skip("this process reads mode-000 files")
    env[key] = str(path)
    result = await list_bucket(aws_cli, server, env)
    assert_config_request(
        result, server, "us-east-1", "credential-parity.s3.amazonaws.com"
    )


@pytest.mark.asyncio
@each_settings_file
async def test_config_privileged_mode_000_file_path_resolves_region(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    key: str,
) -> None:
    server, env = config_runtime
    del env["AWS_REGION"]
    path = tmp_path / SETTINGS_NAME
    path.write_text(CA_CENTRAL_PROFILE)
    path.chmod(0)
    if not os.access(path, os.R_OK):
        pytest.skip("this process cannot read mode-000 files")
    env[key] = str(path)
    result = await list_bucket(aws_cli, server, env)
    assert_config_request(
        result, server, "ca-central-1", regional_host("ca-central-1")
    )


# A settings file the CLI cannot read is skipped as a missing one is, so a
# download still runs on the environment's settings.
@pytest.mark.asyncio
@pytest.mark.parametrize("unreadable", [False, True], ids=["missing", "000"])
async def test_config_unusable_file_path_still_downloads(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    unreadable: bool,
) -> None:
    server, env = config_runtime
    path = tmp_path / SETTINGS_NAME
    if unreadable:
        path.write_text(CA_CENTRAL_PROFILE)
        path.chmod(0)
        if os.access(path, os.R_OK):
            pytest.skip("this process reads mode-000 files")
    env["AWS_CONFIG_FILE"] = str(path)
    body = b"config fixture\n"
    server.set_response_sequence(
        [head_object_response(len(body)), get_object_response(body)]
    )
    destination = tmp_path / "output"
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            "s3://credential-parity/key",
            str(destination),
            "--no-progress",
        ],
        env,
        timeout=20,
    )
    assert (rc, stderr) == (0, b""), stderr.decode()
    assert stdout.decode() == (
        "download: s3://credential-parity/key to "
        f"{os.path.relpath(destination)}\n"
    )
    assert destination.read_bytes() == body
    assert [r.method for r in server.requests] == ["HEAD", "GET"]


def absolute_path(path: Path, home: str) -> str:
    return str(path)


def relative_path(path: Path, home: str) -> str:
    return os.path.relpath(path)


def home_relative_path(path: Path, home: str) -> str:
    return "~/" + os.path.relpath(path, home)


@pytest.mark.asyncio
@each_settings_file
@pytest.mark.parametrize(
    "spell",
    [
        pytest.param(absolute_path, id="absolute"),
        pytest.param(relative_path, id="relative"),
        pytest.param(
            home_relative_path,
            id="tilde",
            marks=pytest.mark.skipif(
                os.name == "nt",
                reason="the workspace and home can sit on different drives",
            ),
        ),
    ],
)
async def test_config_file_path_spellings_resolve_region_from_file(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    key: str,
    spell: Callable[[Path, str], str],
) -> None:
    server, env = config_runtime
    del env["AWS_REGION"]
    path = tmp_path / SETTINGS_NAME
    path.write_text(CA_CENTRAL_PROFILE)
    env[key] = spell(path, env["HOME"])
    result = await list_bucket(aws_cli, server, env)
    assert_config_request(
        result, server, "ca-central-1", regional_host("ca-central-1")
    )


@pytest.mark.asyncio
@each_settings_file
async def test_config_file_path_expands_environment_variables(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    key: str,
) -> None:
    server, env = config_runtime
    del env["AWS_REGION"]
    (tmp_path / SETTINGS_NAME).write_text(CA_CENTRAL_PROFILE)
    env["CONFIG_PARITY_DIR"] = str(tmp_path)
    env[key] = f"$CONFIG_PARITY_DIR/{SETTINGS_NAME}"
    result = await list_bucket(aws_cli, server, env)
    assert_config_request(
        result, server, "ca-central-1", regional_host("ca-central-1")
    )


@pytest.mark.asyncio
@each_settings_file
@pytest.mark.parametrize(
    "text",
    [
        b"region = eu-west-1\n",
        b"[default]\nregion=x\nregion=y\n",
        b"[default]\n[default]\n",
        pytest.param(
            b"[default]\nregion=\xff\n",
            # botocore reads the shared files in the ANSI code page there,
            # which decodes the byte, so neither route has an error to show.
            marks=pytest.mark.skipif(
                sys.platform == "win32",
                reason="Windows decodes the shared files without UTF-8",
            ),
        ),
    ],
    ids=["no-section", "duplicate-key", "duplicate-section", "invalid-utf8"],
)
async def test_config_malformed_files_fail_with_parse_error(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    key: str,
    text: bytes,
) -> None:
    server, env = config_runtime
    Path(env[key]).write_bytes(text)
    result = await list_bucket(aws_cli, server, env)
    assert_config_error(result, server, 255, "Unable to parse config file")
    assert env[key] in result[1].decode()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario,diagnostic",
    [
        pytest.param(
            Scenario(
                REGION_PROFILE,
                env={"AWS_REGION": "", "AWS_DEFAULT_REGION": "eu-west-1"},
            ),
            "Invalid endpoint",
            id="empty-region-env",
        ),
        pytest.param(
            Scenario(
                REGION_PROFILE,
                env={"AWS_REGION": None, "AWS_DEFAULT_REGION": ""},
            ),
            "Invalid endpoint",
            id="empty-default-region-env",
        ),
        pytest.param(
            Scenario("[default]\nregion =\n", env={"AWS_REGION": None}),
            "Invalid endpoint",
            id="empty-region-profile",
        ),
        pytest.param(
            Scenario(REGION_PROFILE, arguments=("--region", "")),
            "Invalid endpoint",
            id="empty-region-flag",
        ),
        pytest.param(
            Scenario(REGION_PROFILE, env={"AWS_REGION": "bad_region"}),
            "doesn't match a supported format",
            id="invalid-region",
        ),
    ],
)
async def test_config_empty_or_invalid_region_fails_before_request(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    scenario: Scenario,
    diagnostic: str,
) -> None:
    server, env = config_runtime
    result = await list_scenario(aws_cli, server, env, scenario)
    assert_config_error(result, server, 255, diagnostic)


# Two profile settings the AWS CLI validates as its session starts, so a
# value it does not know fails every command before a request. For
# cli_timestamp_format, anything but `wire` and `iso8601` is a
# ConfigurationError (customizations/timestampformat.py:49-80). For
# cli_binary_format, anything but `base64` and `raw-in-base64-out` is a
# KeyError from the table of formats, which the general handler prints as
# the value's repr (customizations/binaryformat.py:28-34, 81-84). An s3 command
# has no use for either, and the native route does not read them:
# failures.txt, `parity-gap`.
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "setting,status,diagnostic",
    [
        pytest.param(
            "cli_timestamp_format",
            253,
            "\naws: [ERROR]: An error occurred (Configuration): Unknown "
            'cli_timestamp_format value: bogus, valid values are "wire" or '
            '"iso8601"\n',
            id="timestamp-format",
        ),
        pytest.param(
            "cli_binary_format",
            255,
            "\naws: [ERROR]: 'bogus'\n",
            id="binary-format",
        ),
    ],
)
async def test_config_unknown_cli_format_fails_before_request(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    setting: str,
    status: int,
    diagnostic: str,
) -> None:
    server, env = config_runtime
    scenario = Scenario(f"[default]\n{setting} = bogus\n")
    result = await list_scenario(aws_cli, server, env, scenario)
    assert_config_error(result, server, status, diagnostic)
    assert result[1].decode() == diagnostic


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(
            Scenario(REGION_PROFILE, arguments=("--profile", "absent")),
            id="missing-profile",
        ),
        pytest.param(
            Scenario(REGION_PROFILE, env={"AWS_PROFILE": ""}),
            id="empty-profile-env",
        ),
        pytest.param(
            Scenario(REGION_PROFILE, env={"AWS_DEFAULT_PROFILE": ""}),
            id="empty-profile-default-env",
        ),
    ],
)
async def test_config_missing_or_empty_profile_fails_before_request(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    scenario: Scenario,
) -> None:
    server, env = config_runtime
    result = await list_scenario(aws_cli, server, env, scenario)
    assert_config_error(result, server, 255, "could not be found")


# Without a bucket, `s3 ls` lists the buckets, and the missing profile
# fails it before the request with botocore's ProfileNotFound.
@pytest.mark.asyncio
async def test_config_missing_profile_fails_bucket_listing(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = config_runtime
    write_config(env, REGION_PROFILE)
    stdout, stderr, rc = await run_cli(
        aws_cli, ["s3", "ls", "--profile", "absent"], env, timeout=20
    )
    assert (rc, stdout, stderr) == (
        255,
        b"",
        b"\naws: [ERROR]: The config profile (absent) could not be found\n",
    )
    assert not server.requests


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario,status,diagnostic",
    [
        pytest.param(
            Scenario(MALFORMED, arguments=(*BAD_CLI_ENDPOINT, "--bogus")),
            255,
            "Unable to parse config file",
            id="malformed-before-argv",
        ),
        pytest.param(
            Scenario(
                MALFORMED,
                arguments=(*BAD_CLI_ENDPOINT, "--profile", "absent"),
            ),
            255,
            "Unable to parse config file",
            id="malformed-before-profile",
        ),
        pytest.param(
            Scenario(arguments=(*BAD_CLI_ENDPOINT, "--profile", "absent")),
            252,
            'Bad value for --endpoint-url "not-a-url"',
            id="cli-endpoint-before-profile",
        ),
        pytest.param(
            Scenario(arguments=(*BAD_CLI_ENDPOINT, "--bogus")),
            252,
            'Bad value for --endpoint-url "not-a-url"',
            id="cli-endpoint-before-unknown-option",
        ),
        pytest.param(
            Scenario(
                env={"AWS_ENDPOINT_URL_S3": "not-a-url"},
                arguments=("--profile", "absent"),
            ),
            255,
            "could not be found",
            id="profile-before-configured-endpoint",
        ),
        pytest.param(
            Scenario(
                env={"AWS_ENDPOINT_URL_S3": "not-a-url"},
                arguments=("--bogus",),
            ),
            252,
            "Unknown options",
            id="argv-before-configured-endpoint",
        ),
    ],
)
async def test_config_error_ordering_reports_highest_priority_error(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    scenario: Scenario,
    status: int,
    diagnostic: str,
) -> None:
    server, env = config_runtime
    result = await list_scenario(aws_cli, server, env, scenario)
    assert_config_error(result, server, status, diagnostic)


# CPython's int() refuses a literal of more than 4300 digits however small
# its value, so a zero-padded count fails before any request.
OVER_DIGIT_LIMIT = "0" * 4300 + "5"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "config,diagnostic",
    [
        pytest.param(
            f"[default]\nmax_attempts = {OVER_DIGIT_LIMIT}\n",
            "Exceeds the limit (4300 digits) for integer string conversion: "
            "value has 4301 digits",
            id="max-attempts",
        ),
        pytest.param(
            f"[default]\ns3 =\n    max_queue_size = {OVER_DIGIT_LIMIT}\n",
            "Value for max_queue_size must be a positive integer",
            id="max-queue-size",
        ),
    ],
)
async def test_config_integer_past_digit_limit_fails_before_request(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    config: str,
    diagnostic: str,
) -> None:
    server, env = config_runtime
    source = tmp_path / "source"
    source.write_bytes(b"payload")
    result = await upload_scenario(
        aws_cli, server, env, Scenario(config), source
    )
    assert_config_error(result, server, 255, diagnostic)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario,winner",
    [
        pytest.param(
            Scenario(
                CHOSEN_SERVICES,
                env={**GLOBAL_ENV_ENDPOINT, **S3_ENV_ENDPOINT},
                arguments=CLI_ENDPOINT,
            ),
            "cli",
            id="cli-cli",
        ),
        pytest.param(
            Scenario(
                CHOSEN_SERVICES,
                env={**GLOBAL_ENV_ENDPOINT, **S3_ENV_ENDPOINT},
            ),
            "service-env",
            id="service-env-service-env",
        ),
        pytest.param(
            Scenario(CHOSEN_SERVICES, env=GLOBAL_ENV_ENDPOINT),
            "global-env",
            id="global-env-global-env",
        ),
        pytest.param(
            Scenario(CHOSEN_SERVICES),
            "service-config",
            id="service-config-service-config",
        ),
        pytest.param(
            Scenario(PROFILE_ENDPOINT + S3_SERVICE_CONFIG),
            "profile",
            id="profile-profile",
        ),
        pytest.param(
            Scenario(
                CHOSEN_SERVICES,
                env={**GLOBAL_ENV_ENDPOINT, "AWS_ENDPOINT_URL_S3": ""},
            ),
            "global-env",
            id="empty-service-env-global-env",
        ),
        pytest.param(
            Scenario(CHOSEN_SERVICES, env={"AWS_ENDPOINT_URL": ""}),
            "service-config",
            id="empty-global-env-service-config",
        ),
        pytest.param(
            Scenario(
                PROFILE_ENDPOINT
                + SERVICES_CHOSEN
                + "[services chosen]\ns3 =\n    endpoint_url =\n"
            ),
            "profile",
            id="empty-service-config-profile",
        ),
        pytest.param(
            Scenario(
                PROFILE_ENDPOINT
                + SERVICES_CHOSEN
                + "[services chosen]\nsts =\n"
                "    endpoint_url = https://unused.invalid\n"
            ),
            "profile",
            id="other-service-profile",
        ),
        pytest.param(
            Scenario(
                IGNORE_PROFILE,
                env={"AWS_IGNORE_CONFIGURED_ENDPOINT_URLS": "false"},
            ),
            "service-config",
            id="env-false-over-ignore-profile-service-config",
        ),
        pytest.param(
            Scenario(CHOSEN_SERVICES, env=IGNORE_ENV, arguments=CLI_ENDPOINT),
            "cli",
            id="cli-over-ignore-cli",
        ),
        pytest.param(
            Scenario(PROFILE_ENDPOINT + SERVICES_CHOSEN, env=S3_ENV_ENDPOINT),
            "service-env",
            id="missing-services-shadowed-service-env",
        ),
        pytest.param(
            Scenario(
                PROFILE_ENDPOINT + S3_SERVICE_CONFIG,
                "[default]\n"
                "endpoint_url = https://shared.invalid/shared-base\n",
            ),
            "shared",
            id="shared-profile-endpoint-shared",
        ),
        pytest.param(
            Scenario(
                CHOSEN_SERVICES
                + "[services shared]\ns3 =\n    endpoint_url = "
                "https://shared-service.invalid/shared-service-base\n",
                "[default]\nservices = shared\n",
            ),
            "shared-service",
            id="shared-services-selector-shared-service",
        ),
        pytest.param(
            Scenario(CHOSEN_SERVICES, env={"AWS_USE_FIPS_ENDPOINT": "true"}),
            "service-config",
            id="custom-clears-fips-service-config",
        ),
        pytest.param(
            Scenario(
                CHOSEN_SERVICES, env={"AWS_USE_DUALSTACK_ENDPOINT": "true"}
            ),
            "service-config",
            id="custom-clears-dualstack-service-config",
        ),
        pytest.param(
            Scenario(
                SELECTED_ENDPOINT_PROFILE, env={"AWS_PROFILE": "selected"}
            ),
            "service-config",
            id="selected-profile-env-service-config",
        ),
        pytest.param(
            Scenario(
                SELECTED_ENDPOINT_PROFILE,
                arguments=("--profile", "selected"),
            ),
            "service-config",
            id="selected-profile-flag-service-config",
        ),
    ],
)
async def test_config_endpoint_precedence_selects_winning_endpoint(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    scenario: Scenario,
    winner: str,
) -> None:
    server, env = config_runtime
    result = await list_scenario(aws_cli, server, env, scenario)
    assert_config_request(
        result,
        server,
        "eu-west-1",
        f"{winner}.invalid",
        f"/{winner}-base/credential-parity",
    )


# The FIPS and dual-stack variables select the endpoint variant the S3
# endpoint rules build for the region.
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "variable,host",
    [
        pytest.param(
            "AWS_USE_FIPS_ENDPOINT",
            "credential-parity.s3-fips.us-east-1.amazonaws.com",
            id="fips",
        ),
        pytest.param(
            "AWS_USE_DUALSTACK_ENDPOINT",
            "credential-parity.s3.dualstack.us-east-1.amazonaws.com",
            id="dualstack",
        ),
    ],
)
async def test_config_endpoint_variant_variable_selects_host(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    variable: str,
    host: str,
) -> None:
    server, env = config_runtime
    env.update({"AWS_REGION": "us-east-1", variable: "true"})
    result = await list_bucket(aws_cli, server, env)
    assert_config_request(result, server, "us-east-1", host)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(
            Scenario(CHOSEN_SERVICES, env=IGNORE_ENV), id="ignore-env"
        ),
        pytest.param(Scenario(IGNORE_PROFILE), id="ignore-profile"),
    ],
)
async def test_config_ignored_endpoint_settings_use_default_endpoint(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    scenario: Scenario,
) -> None:
    server, env = config_runtime
    result = await list_scenario(aws_cli, server, env, scenario)
    assert_config_request(
        result, server, "eu-west-1", regional_host("eu-west-1")
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario,status,diagnostic",
    [
        pytest.param(
            Scenario(ABSENT_SERVICES),
            255,
            '"absent" services configuration does not exist',
            id="missing-services",
        ),
        pytest.param(
            Scenario(ABSENT_SERVICES + "[services absent]\n"),
            255,
            '"absent" services configuration does not exist',
            id="empty-services",
        ),
        pytest.param(
            Scenario(arguments=BAD_CLI_ENDPOINT),
            252,
            "Bad value for --endpoint-url",
            id="invalid-cli",
        ),
        pytest.param(
            Scenario(
                env={
                    "AWS_ENDPOINT_URL_S3": "not-a-url",
                    "AWS_ENDPOINT_URL": "https://unused.invalid",
                }
            ),
            255,
            "Invalid endpoint",
            id="invalid-env",
        ),
        pytest.param(
            Scenario(arguments=("--endpoint-url", "")),
            252,
            "Bad value for --endpoint-url",
            id="empty-cli",
        ),
        pytest.param(
            Scenario(arguments=("--endpoint-url", FTP_ENDPOINT)),
            255,
            FTP_ENDPOINT,
            id="refused-scheme-cli",
        ),
        pytest.param(
            Scenario(env={"AWS_ENDPOINT_URL": FTP_ENDPOINT}),
            255,
            FTP_ENDPOINT,
            id="refused-scheme-env",
        ),
        pytest.param(
            Scenario(arguments=("--endpoint-url", QUERY_ENDPOINT)),
            255,
            QUERY_ENDPOINT,
            id="refused-query-cli",
        ),
        pytest.param(
            Scenario(arguments=("--endpoint-url", PORT_TEXT_ENDPOINT)),
            255,
            PORT_TEXT_ENDPOINT,
            id="refused-port-text-cli",
        ),
        pytest.param(
            Scenario(arguments=("--endpoint-url", PORT_RANGE_ENDPOINT)),
            255,
            PORT_RANGE_ENDPOINT,
            id="refused-port-range-cli",
        ),
        pytest.param(
            Scenario(arguments=("--endpoint-url", NO_HOST_ENDPOINT)),
            255,
            NO_HOST_ENDPOINT,
            id="refused-host-cli",
        ),
        pytest.param(
            Scenario(env={"AWS_ENDPOINT_URL": NO_HOST_ENDPOINT}),
            255,
            NO_HOST_ENDPOINT,
            id="refused-host-env",
        ),
    ],
)
async def test_config_endpoint_errors_fail_before_request(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    scenario: Scenario,
    status: int,
    diagnostic: str,
) -> None:
    server, env = config_runtime
    result = await list_scenario(aws_cli, server, env, scenario)
    assert_config_error(result, server, status, diagnostic)


# `s3 cp` builds its client first, so a URL the rules refuse fails the
# command with status 1 and a fatal error that names the URL.
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url,scenario",
    [
        pytest.param(
            FTP_ENDPOINT,
            Scenario(arguments=("--endpoint-url", FTP_ENDPOINT)),
            id="scheme-cli",
        ),
        pytest.param(
            FTP_ENDPOINT,
            Scenario(env={"AWS_ENDPOINT_URL": FTP_ENDPOINT}),
            id="scheme-env",
        ),
        pytest.param(
            QUERY_ENDPOINT,
            Scenario(arguments=("--endpoint-url", QUERY_ENDPOINT)),
            id="query-cli",
        ),
        pytest.param(
            PORT_TEXT_ENDPOINT,
            Scenario(arguments=("--endpoint-url", PORT_TEXT_ENDPOINT)),
            id="port-text-cli",
        ),
        pytest.param(
            PORT_RANGE_ENDPOINT,
            Scenario(arguments=("--endpoint-url", PORT_RANGE_ENDPOINT)),
            id="port-range-cli",
        ),
    ],
)
async def test_config_refused_endpoint_fails_download(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    url: str,
    scenario: Scenario,
) -> None:
    server, env = config_runtime
    apply_scenario(env, scenario)
    destination = tmp_path / "out"
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", "s3://credential-parity/key", str(destination)]
        + list(scenario.arguments),
        env,
        timeout=20,
    )
    assert (rc, stdout) == (1, b""), stderr.decode()
    assert stderr.decode().startswith("fatal error: ")
    assert url in stderr.decode()
    assert not server.requests
    assert not destination.exists()


# botocore cannot build a client for a URL whose host it cannot read, so
# `s3 cp` fails in the general error frame with status 255.
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(
            Scenario(arguments=("--endpoint-url", NO_HOST_ENDPOINT)), id="cli"
        ),
        pytest.param(
            Scenario(env={"AWS_ENDPOINT_URL": NO_HOST_ENDPOINT}), id="env"
        ),
    ],
)
async def test_config_endpoint_without_host_fails_download(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    scenario: Scenario,
) -> None:
    server, env = config_runtime
    apply_scenario(env, scenario)
    destination = tmp_path / "out"
    stdout, stderr, rc = await run_cli(
        aws_cli,
        ["s3", "cp", "s3://credential-parity/key", str(destination)]
        + list(scenario.arguments),
        env,
        timeout=20,
    )
    assert (rc, stdout) == (255, b""), stderr.decode()
    assert NO_HOST_ENDPOINT in stderr.decode()
    assert not server.requests
    assert not destination.exists()


# An upload reports a URL the rules refuse as its one failed transfer, with
# status 1.
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url", [FTP_ENDPOINT, QUERY_ENDPOINT], ids=["scheme", "query"]
)
async def test_config_refused_endpoint_fails_upload(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    url: str,
) -> None:
    server, env = config_runtime
    source = tmp_path / "f"
    source.write_bytes(b"data\n")
    stdout, stderr, rc = await run_cli(
        aws_cli,
        [
            "s3",
            "cp",
            str(source),
            "s3://credential-parity/key",
            "--endpoint-url",
            url,
        ],
        env,
        timeout=20,
    )
    assert rc == 1, stderr.decode()
    # The CRT client `auto` runs the upload on reports its progress before
    # the rule fails it.
    assert completion_lines(stdout) == []
    assert stderr.decode().startswith(
        f"upload failed: {os.path.relpath(source)} "
        "to s3://credential-parity/key "
    )
    assert url in stderr.decode()
    assert not server.requests


# botocore lowercases the endpoint's scheme before the rules read it.
@pytest.mark.asyncio
async def test_config_endpoint_uppercase_scheme_lists_bucket(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
) -> None:
    server, env = config_runtime
    scenario = Scenario(
        arguments=("--endpoint-url", "HTTPS://s3.us-east-1.amazonaws.com")
    )
    result = await list_scenario(aws_cli, server, env, scenario)
    assert_config_request(
        result,
        server,
        "eu-west-1",
        "s3.us-east-1.amazonaws.com",
        "/credential-parity",
    )


# botocore ends an endpoint's userinfo at the authority's last literal @,
# where the CRT client ends it at the first: at `u`, leaving host
# `v@cli.invalid`, or port `1@cli.invalid` where a colon follows `v`.
USERINFO_HOST_ENDPOINTS = [
    pytest.param(
        Scenario(
            arguments=("--endpoint-url", "https://u@v@cli.invalid/cli-base")
        ),
        id="cli",
    ),
    pytest.param(
        Scenario(
            "[default]\nendpoint_url = https://u@v@cli.invalid/cli-base\n"
        ),
        id="profile",
    ),
]
USERINFO_PORT_ENDPOINTS = [
    pytest.param(
        Scenario(
            arguments=(
                "--endpoint-url",
                "https://u@v:1@cli.invalid/cli-base",
            )
        ),
        id="cli-colon",
    ),
    pytest.param(
        Scenario(
            env={"AWS_ENDPOINT_URL_S3": "https://u@v:1@cli.invalid/cli-base"}
        ),
        id="env",
    ),
]
USERINFO_ENDPOINTS = [*USERINFO_HOST_ENDPOINTS, *USERINFO_PORT_ENDPOINTS]


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", USERINFO_ENDPOINTS)
async def test_config_endpoint_userinfo_ends_at_last_at_for_list(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    scenario: Scenario,
) -> None:
    server, env = config_runtime
    result = await list_scenario(aws_cli, server, env, scenario)
    assert_config_request(
        result,
        server,
        "eu-west-1",
        "cli.invalid",
        "/cli-base/credential-parity",
    )


# The CRT client, which runs `s3 cp` transfers, asks the proxy for host
# `v@cli.invalid` in its ClientHello, then rejects the certificate issued
# for that name, so no request reaches the server. A rejected handshake
# waits out s2n's blinding delay, 10 to 30 seconds, before the CLI hears of
# it, so the upload is killed at this deadline instead; the ClientHello
# comes well within it, as the trusted runs of test_client_transport.py's
# handshake tests show.
USERINFO_HOST_DEADLINE_SECONDS = 5.0


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", USERINFO_HOST_ENDPOINTS)
async def test_config_endpoint_userinfo_ends_at_first_at_for_upload(
    aws_cli: str, tmp_path: Path, scenario: Scenario
) -> None:
    source = tmp_path / "source"
    source.write_bytes(b"payload")
    recorder = ClientHelloRecorder()
    returncode: int | None
    async with (
        AsyncHTTPTestServer(
            on_headers_received=handle_expect_header
        ) as server,
        AsyncTLSInterceptProxy(server=server, ca=recorder) as proxy,
    ):
        env = config_env(proxy, tmp_path)
        apply_scenario(env, scenario)
        server.set_default_response(put_object_response())
        try:
            _, _, returncode = await run_command(
                [aws_cli, *upload_arguments(scenario, source)],
                env,
                cwd=tmp_path,
                stdin=None,
                timeout=USERINFO_HOST_DEADLINE_SECONDS,
            )
        except CommandTimeoutError:
            returncode = None
    assert returncode != 0
    assert set(recorder.server_names) == {"v@cli.invalid"}
    assert not server.requests


# Where a colon follows `v`, the CRT client reads `1@cli.invalid` as the
# port and fails before connecting.
USERINFO_PORT_FAILURE = (
    "36 (AWS_ERROR_MALFORMED_INPUT_STRING): An input string was passed to a "
    "parser and the string was incorrectly formatted."
)


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", USERINFO_PORT_ENDPOINTS)
async def test_config_endpoint_userinfo_port_ends_at_first_at_for_upload(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    scenario: Scenario,
) -> None:
    server, env = config_runtime
    source = tmp_path / "source"
    source.write_bytes(b"payload")
    stdout, stderr, rc = await upload_scenario(
        aws_cli, server, env, scenario, source
    )
    assert (rc, stdout) == (1, b""), stderr.decode()
    assert stderr.decode() == (
        f"upload failed: {os.path.relpath(source)} to "
        f"s3://credential-parity/key {USERINFO_PORT_FAILURE}\n"
    )
    assert not server.requests


# botocore reads an empty port as none and sends no colon in Host, where
# native would send the endpoint's authority as spelled. Upstream's CRT
# client, which runs `s3 cp` transfers, sends it as spelled too.
EMPTY_PORT_ENDPOINTS = [
    pytest.param(
        Scenario(
            arguments=("--endpoint-url", "https://cli.invalid:/cli-base")
        ),
        id="cli",
    ),
    pytest.param(
        Scenario(env={"AWS_ENDPOINT_URL": "https://cli.invalid:/cli-base"}),
        id="env",
    ),
    pytest.param(
        Scenario(
            "[default]\n"
            + SERVICES_CHOSEN
            + "[services chosen]\ns3 =\n"
            + "    endpoint_url = https://cli.invalid:/cli-base\n"
        ),
        id="services",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", EMPTY_PORT_ENDPOINTS)
async def test_config_endpoint_empty_port_omits_colon_for_list(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    scenario: Scenario,
) -> None:
    server, env = config_runtime
    result = await list_scenario(aws_cli, server, env, scenario)
    assert_config_request(
        result,
        server,
        "eu-west-1",
        "cli.invalid",
        "/cli-base/credential-parity",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", EMPTY_PORT_ENDPOINTS)
async def test_config_endpoint_empty_port_keeps_colon_for_upload(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    scenario: Scenario,
) -> None:
    server, env = config_runtime
    source = tmp_path / "source"
    source.write_bytes(b"payload")
    result = await upload_scenario(aws_cli, server, env, scenario, source)
    assert_upload_request(result, server, "cli.invalid:", "/cli-base")


# botocore's HTTP client leaves the scheme's default port out of Host, where
# native would send the endpoint's authority as spelled. Upstream's CRT
# client, which runs `s3 cp` transfers, sends it as spelled too.
DEFAULT_PORT_ENDPOINTS = [
    pytest.param(
        Scenario(
            arguments=("--endpoint-url", "https://cli.invalid:443/cli-base")
        ),
        id="cli",
    ),
    pytest.param(
        Scenario(
            env={"AWS_ENDPOINT_URL_S3": "https://cli.invalid:0443/cli-base"}
        ),
        id="env-padded",
    ),
    pytest.param(
        Scenario(
            "[default]\nendpoint_url = https://cli.invalid:443/cli-base\n"
        ),
        id="profile",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", DEFAULT_PORT_ENDPOINTS)
async def test_config_endpoint_default_port_omitted_for_list(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    scenario: Scenario,
) -> None:
    server, env = config_runtime
    result = await list_scenario(aws_cli, server, env, scenario)
    assert_config_request(
        result,
        server,
        "eu-west-1",
        "cli.invalid",
        "/cli-base/credential-parity",
    )


# Each default-port endpoint with the authority it spells.
DEFAULT_PORT_UPLOADS = [
    pytest.param(*param.values, host, id=param.id)
    for param, host in zip(
        DEFAULT_PORT_ENDPOINTS,
        ["cli.invalid:443", "cli.invalid:0443", "cli.invalid:443"],
        strict=True,
    )
]


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario,host", DEFAULT_PORT_UPLOADS)
async def test_config_endpoint_default_port_kept_for_upload(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    tmp_path: Path,
    scenario: Scenario,
    host: str,
) -> None:
    server, env = config_runtime
    source = tmp_path / "source"
    source.write_bytes(b"payload")
    result = await upload_scenario(aws_cli, server, env, scenario, source)
    assert_upload_request(result, server, host, "/cli-base")


# Profile dictionaries merge by top-level key, not recursively: replacing
# s3 must discard the old dualstack flag, not just its addressing style.
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "shared,host,path",
    [
        pytest.param(
            CA_CENTRAL_PROFILE,
            "s3.dualstack.eu-west-1.amazonaws.com",
            "/credential-parity",
            id="inherit-block",
        ),
        pytest.param(
            CA_CENTRAL_PROFILE + "s3 =\n    addressing_style = virtual\n",
            regional_host("eu-west-1"),
            "/",
            id="replace-block",
        ),
    ],
)
async def test_config_nested_s3_merge_keeps_or_replaces_whole_block(
    aws_cli: str,
    config_runtime: tuple[AsyncHTTPTestServer, dict[str, str]],
    shared: str,
    host: str,
    path: str,
) -> None:
    server, env = config_runtime
    write_config(
        env,
        "[default]\ns3 =\n    addressing_style = path\n"
        "    use_dualstack_endpoint = true\n",
    )
    write_config(env, shared, shared=True)
    result = await list_bucket(aws_cli, server, env)
    assert_config_request(result, server, "eu-west-1", host, path)
