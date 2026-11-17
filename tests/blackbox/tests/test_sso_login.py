import asyncio
import shlex
import sys
import urllib.request
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
import pytest_asyncio
from localstub import AsyncHTTPTestServer, HTTPResponse

from credhelpers import credential_env, write_config
from harness_plugin import child_environment
from tests.blackbox.utils import mock_server

START_URL = "https://d-0000000000.awsapps.com/start"
AUTH_CODE = "callback-auth-code"
DECOY_PAGE = b"<p>not the CLI's page</p>\n"
# An sso-session profile logs in with the authorization code flow.
SSO_CONFIG = (
    "[profile login]\n"
    "sso_session = callback\n"
    "[sso-session callback]\n"
    f"sso_start_url = {START_URL}\n"
    "sso_region = us-east-1\n"
    "sso_registration_scopes = sso:account:access\n"
)
REGISTER_CLIENT_RESPONSE = HTTPResponse.json(
    {
        "clientId": "callback-client",
        "clientSecret": "callback-secret",
        "clientIdIssuedAt": 1767225600,
        "clientSecretExpiresAt": 4102444800,
    }
)
CREATE_TOKEN_RESPONSE = HTTPResponse.json(
    {
        "accessToken": "callback-access-token",
        "tokenType": "Bearer",
        "expiresIn": 3600,
        "refreshToken": "callback-refresh-token",
    }
)
# The CLI opens the browser in well under a second, but a cold start on a
# slow host can take longer.
STARTUP_TIMEOUT_SECONDS = 15
# A CLI that missed the auth code waits ten minutes for another callback.
# One that got it finishes against the local server in tens of milliseconds.
CALLBACK_TIMEOUT_SECONDS = 5
# `webbrowser` waits for a $BROWSER command to exit, and the CLI serves its
# callback only after that, so this browser records the URL it is opened
# with and leaves the redirect to the test. The rename keeps the test from
# reading a partial URL.
BROWSER_SCRIPT = (
    "import os, sys\n"
    "path, url = sys.argv[1:]\n"
    "with open(path + '.tmp', 'w') as stream:\n"
    "    stream.write(url)\n"
    "os.replace(path + '.tmp', path)\n"
)


@dataclass
class SSORuntime:
    server: AsyncHTTPTestServer
    env: dict[str, str]
    opened_url: Path


@dataclass
class PendingLogin:
    """An `aws sso login` that has opened the browser, and its output."""

    process: asyncio.subprocess.Process
    authorize_url: str
    output: Path

    async def wait(self) -> tuple[int | None, str]:
        """The exit status, None if still running after the timeout."""
        try:
            returncode = await asyncio.wait_for(
                self.process.wait(), CALLBACK_TIMEOUT_SECONDS
            )
        except TimeoutError:
            returncode = None
        return returncode, self.output.read_text(encoding="utf-8")


StartLogin = Callable[[], Awaitable[PendingLogin]]


def fake_browser_command(script: Path, opened_url: Path) -> str:
    # `webbrowser` splits a command line holding %s with POSIX shell rules,
    # which would eat a Windows path's backslashes.
    python, script_path, url_path = (
        path.as_posix() for path in (Path(sys.executable), script, opened_url)
    )
    return f"{shlex.join([python, '-I', script_path, url_path])} %s"


async def browser_opened(
    opened_url: Path, process: asyncio.subprocess.Process, output: Path
) -> str:
    while not opened_url.exists():
        if process.returncode is not None:
            pytest.fail(
                f"aws sso login exited {process.returncode} without opening "
                f"a browser:\n{output.read_text(encoding='utf-8')}"
            )
        await asyncio.sleep(0.05)
    return opened_url.read_text(encoding="utf-8")


async def redirect_to_callback(authorize_url: str) -> bytes:
    """Follow the sign-in page's redirect to the CLI's callback server.

    Returns the page the callback serves.
    """
    query = parse_qs(urlsplit(authorize_url).query)
    params = urlencode({"code": AUTH_CODE, "state": query["state"][0]})
    callback = f"{query['redirect_uri'][0]}?{params}"
    # The callback is local, whatever proxy the runner's shell sets.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def get() -> bytes:
        with opener.open(callback, timeout=10) as response:
            return response.read()

    return await asyncio.to_thread(get)


@pytest.fixture
def sign_in_page(pytestconfig: pytest.Config) -> bytes:
    # run.py roots pytest at the aws-cli source tree.
    root = pytestconfig.rootpath
    page = root / "awscli" / "customizations" / "sso" / "index.html"
    return page.read_bytes()


@pytest.fixture
def working_directory(tmp_path: Path) -> Path:
    path = tmp_path / "cwd"
    path.mkdir()
    return path


@pytest_asyncio.fixture
async def sso_runtime(tmp_path: Path) -> AsyncIterator[SSORuntime]:
    script = tmp_path / "browser.py"
    script.write_text(BROWSER_SCRIPT, encoding="utf-8")
    opened_url = tmp_path / "opened-url"
    # The token cache is under the home directory.
    home = tmp_path / "home"
    home.mkdir()
    async with mock_server() as (server, proxy):
        server.set_response_sequence(
            [REGISTER_CLIENT_RESPONSE, CREATE_TOKEN_RESPONSE]
        )
        env = credential_env(proxy, tmp_path)
        write_config(env, SSO_CONFIG)
        env.update(
            HOME=str(home),
            USERPROFILE=str(home),
            BROWSER=fake_browser_command(script, opened_url),
        )
        yield SSORuntime(server, child_environment(env), opened_url)


@pytest_asyncio.fixture
async def start_login(
    aws_cli: str,
    sso_runtime: SSORuntime,
    working_directory: Path,
    tmp_path: Path,
) -> AsyncIterator[StartLogin]:
    processes: list[asyncio.subprocess.Process] = []

    async def start() -> PendingLogin:
        # A file keeps the output of a login killed at teardown.
        output = tmp_path / "login.log"
        with output.open("wb") as stream:
            process = await asyncio.create_subprocess_exec(
                aws_cli,
                "sso",
                "login",
                "--profile",
                "login",
                env=sso_runtime.env,
                cwd=working_directory,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=stream,
                stderr=asyncio.subprocess.STDOUT,
            )
        processes.append(process)
        authorize_url = await asyncio.wait_for(
            browser_opened(sso_runtime.opened_url, process, output),
            STARTUP_TIMEOUT_SECONDS,
        )
        return PendingLogin(process, authorize_url, output)

    yield start
    for process in processes:
        if process.returncode is None:
            process.kill()
        await process.wait()


@pytest.mark.asyncio
async def test_sso_login_callback_serves_sign_in_page_from_payload(
    start_login: StartLogin, working_directory: Path, sign_in_page: bytes
) -> None:
    # Upstream serves only the page bundled with the CLI, so one in the
    # working directory must never reach the browser.
    (working_directory / "index.html").write_bytes(DECOY_PAGE)
    login = await start_login()
    assert await redirect_to_callback(login.authorize_url) == sign_in_page


@pytest.mark.asyncio
async def test_sso_login_callback_with_auth_code_completes_login(
    start_login: StartLogin, sso_runtime: SSORuntime
) -> None:
    login = await start_login()
    await redirect_to_callback(login.authorize_url)
    returncode, output = await login.wait()
    assert returncode == 0, output
    assert f"Successfully logged into Start URL: {START_URL}" in (
        output.splitlines()
    )
    token_request = sso_runtime.server.requests[-1]
    assert token_request.effective_path == "/token"
    assert token_request.json_body["code"] == AUTH_CODE
