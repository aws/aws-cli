from pathlib import Path

import pytest
from localstub import AsyncHTTPTestServer, HTTPResponse, RecordedHTTPRequest

from credhelpers import (
    credential_runtime,
    file_credentials,
    json_process,
    list_bucket,
    process_credentials,
    write_config,
)
from tests.blackbox.utils import (
    list_objects_xml,
    put_object_response,
    run_cli,
    xml_response,
)

pytestmark = pytest.mark.asyncio


ENV_KEYS = {
    "AWS_ACCESS_KEY_ID": "AKIDENV",
    "AWS_SECRET_ACCESS_KEY": "ENV-secret",
}


def process_profile(command: str, section: str = "default") -> str:
    return f"[{section}]\ncredential_process = {command}\n"


# botocore resolves the session's credentials while it creates the listing
# client, and the provider that answers registers its User-Agent feature id
# then: `g` for the environment variables, `n` for a profile's static keys
# in either shared file, and `v` and `w` for `credential_process`. Every
# request that client sends carries them in the `m/` component, whose order
# is a Python set's, so the tests compare sets.
CREDENTIAL_FEATURES = frozenset(
    "e g v w h i k n o p q r s t u x z 0 AC AD".split()
)


def features(request: RecordedHTTPRequest) -> set[str]:
    return {
        feature
        for part in request.headers["user-agent"].split()
        if part.startswith("m/")
        for feature in part[2:].split(",")
    }


def credential_features(server: AsyncHTTPTestServer) -> list[set[str]]:
    return [
        features(request) & CREDENTIAL_FEATURES for request in server.requests
    ]


def two_pages() -> list[HTTPResponse]:
    first = {"Key": "a", "Size": 1, "LastModified": "2026-01-02T03:04:05Z"}
    second = {"Key": "b", "Size": 1, "LastModified": "2026-01-02T03:04:05Z"}
    return [
        xml_response(
            list_objects_xml(
                contents=[first],
                is_truncated=True,
                next_continuation_token="page-2",
            )
        ),
        xml_response(list_objects_xml(contents=[second])),
    ]


# Every page of the listing comes from the one client, so each carries `g`.
async def test_credentials_user_agent_names_environment_on_every_page(
    aws_cli: str, tmp_path: Path
) -> None:
    async with credential_runtime(tmp_path) as (server, env):
        env.update(ENV_KEYS)
        stdout, stderr, rc = await list_bucket(
            aws_cli, server, env, responses=two_pages()
        )
    assert (rc, stderr) == (0, b""), stdout
    assert credential_features(server) == [{"g"}, {"g"}]


@pytest.mark.parametrize(
    ("variables", "config", "shared", "arguments", "expected"),
    [
        pytest.param(
            {},
            "",
            "[default]\n" + file_credentials("FILE"),
            (),
            {"n"},
            id="credentials-file",
        ),
        pytest.param(
            {},
            "[default]\n" + file_credentials("CONFIG"),
            "",
            (),
            {"n"},
            id="config-file",
        ),
        # --profile skips the environment provider.
        pytest.param(
            ENV_KEYS,
            "",
            "[work]\n" + file_credentials("WORK"),
            ("--profile", "work"),
            {"n"},
            id="explicit-profile",
        ),
        # An empty access key leaves the environment provider silent.
        pytest.param(
            {**ENV_KEYS, "AWS_ACCESS_KEY_ID": ""},
            "",
            "[default]\n" + file_credentials("FILE"),
            (),
            {"n"},
            id="empty-environment-key",
        ),
        # The environment answers before the credentials file.
        pytest.param(
            ENV_KEYS,
            "",
            "[default]\n" + file_credentials("FILE"),
            (),
            {"g"},
            id="environment-and-file",
        ),
    ],
)
async def test_credentials_user_agent_names_answering_provider(
    aws_cli: str,
    tmp_path: Path,
    variables: dict[str, str],
    config: str,
    shared: str,
    arguments: tuple[str, ...],
    expected: set[str],
) -> None:
    async with credential_runtime(tmp_path) as (server, env):
        env.update(variables)
        write_config(env, config)
        write_config(env, shared, shared=True)
        stdout, stderr, rc = await list_bucket(
            aws_cli, server, env, *arguments
        )
    assert (rc, stderr) == (0, b""), stdout
    assert credential_features(server) == [expected]


async def test_credentials_user_agent_names_process_provider(
    aws_cli: str, tmp_path: Path
) -> None:
    command, _ = json_process(tmp_path, process_credentials())
    async with credential_runtime(tmp_path) as (server, env):
        write_config(env, process_profile(command))
        stdout, stderr, rc = await list_bucket(aws_cli, server, env)
    assert (rc, stderr) == (0, b""), stdout
    assert credential_features(server) == [{"v", "w"}]


# An unsigned listing resolves no credentials.
async def test_credentials_user_agent_unsigned_listing_names_no_provider(
    aws_cli: str, tmp_path: Path
) -> None:
    async with credential_runtime(tmp_path) as (server, env):
        env.update(ENV_KEYS)
        stdout, stderr, rc = await list_bucket(
            aws_cli, server, env, "--no-sign-request"
        )
    assert (rc, stderr) == (0, b""), stdout
    assert credential_features(server) == [set()]


# `s3 cp` sends its requests from a transfer client created after its source
# client, once the session has cached the credentials, so they carry no
# credential feature id.
async def test_credentials_user_agent_transfer_names_no_provider(
    aws_cli: str, tmp_path: Path
) -> None:
    source = tmp_path / "source"
    source.write_bytes(b"foo")
    async with credential_runtime(tmp_path) as (server, env):
        env.update(ENV_KEYS)
        # The upload then runs on the CRT client.
        write_config(
            env, "[default]\ns3 =\n  preferred_transfer_client = crt\n"
        )
        server.set_default_response(put_object_response())
        stdout, stderr, rc = await run_cli(
            aws_cli,
            ["s3", "cp", str(source), "s3://bucket/key"],
            env,
            timeout=30,
        )
    assert (rc, stderr) == (0, b""), stdout
    assert credential_features(server) == [set()]
