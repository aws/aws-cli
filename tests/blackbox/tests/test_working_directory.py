"""The directory a command runs from never changes what it does.

The AWS CLI reads its service models, endpoint rules, installer metadata,
and modules from its own installation. A repository that holds files at
those relative locations must not change a command run inside it: before
this was fixed, planted endpoint rules sent signed requests to a host of
the repository's choosing. Every file here sits where a build that resolved
those locations against the working directory read it.
"""

import contextlib
import json
import sys
from pathlib import Path

import pytest
from localstub import AsyncHTTPTestServer, HTTPResponse

from credhelpers import credential_runtime, run_command, write_config
from tests.blackbox.utils import run_cli, xml_response

MARKER = "zippy-planted"
PLANTED_SERVICE = "zippyplanted"
PLANTED_API_VERSION = "2020-01-01"
# Newer than any STS API version the CLI ships.
FUTURE_STS_API_VERSION = "9999-01-01"
CALLER_IDENTITY = """\
<GetCallerIdentityResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
  <GetCallerIdentityResult>
    <Arn>arn:aws:iam::123456789012:user/blackbox</Arn>
    <UserId>AIDABLACKBOX</UserId>
    <Account>123456789012</Account>
  </GetCallerIdentityResult>
  <ResponseMetadata><RequestId>blackbox</RequestId></ResponseMetadata>
</GetCallerIdentityResponse>
"""
# A CLI plugin, loaded from outside the working directory, that imports a
# botocore submodule the CLI does not ship.
PROBE_PLUGIN = """\
import importlib


def awscli_initialize(event_hooks):
    event_hooks.register("top-level-args-parsed", _probe)


def _probe(**kwargs):
    try:
        importlib.import_module("botocore.zippy_planted")
    except ImportError:
        print("botocore.zippy_planted absent")
    raise SystemExit(0)
"""


@pytest.fixture
def planted(tmp_path: Path) -> Path:
    cwd = tmp_path / "planted"
    url = f"https://{MARKER}.example/"
    write_rules(cwd / "awscli/data", "sts", "2011-06-15", url)
    write_planted_service(cwd / "awscli/data", url)
    write_json(cwd / "sts" / FUTURE_STS_API_VERSION / "service-2.json", {})
    write_json(cwd / "data/metadata.json", {"distribution_source": MARKER})
    vendored = cwd / "__ZIPPY_VENDORED__/awscli.botocore"
    vendored.mkdir(parents=True)
    (vendored / "zippy_planted.py").write_text(f"print({MARKER!r})\n")
    return cwd


@pytest.mark.asyncio
async def test_planted_endpoint_rules_and_metadata_do_not_change_requests(
    aws_cli: str, tmp_path: Path, planted: Path
) -> None:
    clean = tmp_path / "clean"
    clean.mkdir()
    async with credential_runtime(tmp_path) as (server, env):
        add_credentials(env)
        server.set_default_response(xml_response(CALLER_IDENTITY))
        from_clean = await caller_identity(aws_cli, clean, server, env)
        from_planted = await caller_identity(aws_cli, planted, server, env)
    assert from_clean["host"] == "sts.us-east-1.amazonaws.com"
    assert from_planted == from_clean


@pytest.mark.asyncio
async def test_empty_aws_data_path_entry_does_not_name_the_working_directory(
    aws_cli: str, tmp_path: Path, planted: Path
) -> None:
    # An empty entry names no directory, so the STS API version planted at
    # the top of the working directory is not one the CLI can choose.
    clean = tmp_path / "clean"
    clean.mkdir()
    async with credential_runtime(tmp_path) as (server, env):
        add_credentials(env)
        env["AWS_DATA_PATH"] = ""
        server.set_default_response(xml_response(CALLER_IDENTITY))
        from_clean = await caller_identity(aws_cli, clean, server, env)
        from_planted = await caller_identity(aws_cli, planted, server, env)
    assert from_clean["host"] == "sts.us-east-1.amazonaws.com"
    assert from_planted == from_clean


@pytest.mark.asyncio
async def test_planted_service_model_is_not_a_command(
    aws_cli: str, tmp_path: Path, planted: Path
) -> None:
    async with credential_runtime(tmp_path) as (server, env):
        add_credentials(env)
        stdout, stderr, rc = await run_cli_in(
            planted, aws_cli, [PLANTED_SERVICE, "planted-op"], env
        )
    assert (rc, stdout) == (252, b"")
    assert f"Found invalid choice '{PLANTED_SERVICE}'" in stderr.decode()
    assert not server.requests


@pytest.mark.asyncio
async def test_aws_data_path_models_load_in_a_planted_directory(
    aws_cli: str, tmp_path: Path, planted: Path
) -> None:
    # The control for the test above: models on disk still load when the
    # user names their directory.
    models = tmp_path / "models"
    write_planted_service(models, "https://user-models.example/")
    async with credential_runtime(tmp_path) as (server, env):
        add_credentials(env)
        env["AWS_DATA_PATH"] = str(models)
        server.set_default_response(HTTPResponse.raw(b"{}"))
        _, stderr, rc = await run_cli_in(
            planted, aws_cli, [PLANTED_SERVICE, "planted-op"], env
        )
    assert rc == 0, stderr.decode()
    assert [r.headers["host"] for r in server.requests] == [
        "user-models.example"
    ]


@pytest.mark.asyncio
async def test_planted_module_is_not_importable(
    aws_cli: str, tmp_path: Path, planted: Path
) -> None:
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    (plugin / "zippy_probe.py").write_text(PROBE_PLUGIN)
    async with credential_runtime(tmp_path) as (_, env):
        add_credentials(env)
        write_config(
            env,
            "[plugins]\n"
            f"cli_legacy_plugin_path = {plugin}\n"
            "zippyprobe = zippy_probe\n",
        )
        stdout, stderr, rc = await run_cli_in(
            planted, aws_cli, ["sts", "get-caller-identity"], env
        )
    assert (rc, stdout, stderr) == (0, b"botocore.zippy_planted absent\n", b"")


async def caller_identity(
    aws_cli: str, cwd: Path, server: AsyncHTTPTestServer, env: dict[str, str]
) -> dict[str, object]:
    """What `sts get-caller-identity` sends and prints, run from `cwd`."""
    seen = len(server.requests)
    stdout, stderr, rc = await run_cli_in(
        cwd, aws_cli, ["sts", "get-caller-identity"], env
    )
    assert rc == 0, stderr.decode()
    [request] = server.requests[seen:]
    # Feature IDs (m/) come from a set, so their order varies between runs.
    user_agent = [
        part
        for part in request.headers["user-agent"].split()
        if not part.startswith("m/")
    ]
    return {
        "stdout": stdout,
        "host": request.headers["host"],
        "path": request.effective_path,
        "body": request.body,
        "user-agent": user_agent,
    }


async def run_cli_in(
    cwd: Path, aws_cli: str, args: list[str], env: dict[str, str]
) -> tuple[bytes, bytes, int]:
    """`run_cli`, run from `cwd`.

    The command inherits the runner's working directory, so change that for
    the launch and keep the harness's launcher, which supplies the OS
    environment a Windows command needs and folds its line endings.
    """
    with contextlib.chdir(cwd):
        return await run_cli(aws_cli, args, env)


def add_credentials(env: dict[str, str]) -> None:
    env.update(AWS_ACCESS_KEY_ID="AKIDCWD", AWS_SECRET_ACCESS_KEY="CWD-secret")


def write_planted_service(base: Path, url: str) -> None:
    service = base / PLANTED_SERVICE / PLANTED_API_VERSION
    write_rules(base, PLANTED_SERVICE, PLANTED_API_VERSION, url)
    write_json(
        service / "service-2.json",
        {
            "version": "2.0",
            "metadata": {
                "apiVersion": PLANTED_API_VERSION,
                "endpointPrefix": PLANTED_SERVICE,
                "jsonVersion": "1.1",
                "protocol": "json",
                "serviceId": "Zippy Planted",
                "signatureVersion": "v4",
                "targetPrefix": "ZippyPlanted",
            },
            "operations": {
                "PlantedOp": {
                    "name": "PlantedOp",
                    "http": {"method": "POST", "requestUri": "/"},
                }
            },
            "shapes": {},
        },
    )


def write_rules(base: Path, service: str, api_version: str, url: str) -> None:
    """Endpoint rules that send every request to `url`."""
    write_json(
        base / service / api_version / "endpoint-rule-set-1.json",
        {
            "version": "1.0",
            "parameters": {},
            "rules": [
                {
                    "conditions": [],
                    "endpoint": {"url": url, "properties": {}, "headers": {}},
                    "type": "endpoint",
                }
            ],
        },
    )


def write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


# A recursive upload of an empty absolute source sends nothing and prints
# nothing, so it needs neither a request nor the working directory, which
# may have been removed.
@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.platform == "win32", reason="Windows cannot remove a process's cwd"
)
@pytest.mark.parametrize("flags", [[], ["--quiet"]], ids=["default", "quiet"])
async def test_recursive_upload_of_nothing_from_a_removed_directory(
    aws_cli: str, tmp_path: Path, flags: list[str]
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    removed = tmp_path / "removed"
    removed.mkdir()
    async with credential_runtime(tmp_path) as (server, env):
        env.update(AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test")
        result = await run_command(
            [
                "sh",
                "-c",
                'cd "$1" && rmdir "$1" && shift && exec "$@"',
                "sh",
                str(removed),
                aws_cli,
                "s3",
                "cp",
                str(source),
                "s3://bucket/",
                "--recursive",
                *flags,
            ],
            env,
            cwd=tmp_path,
        )
    assert result == (b"", b"", 0), result[1].decode()
    assert not server.requests
