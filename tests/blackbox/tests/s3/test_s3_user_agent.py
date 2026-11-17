"""The User-Agent header of every request `s3 ls` and `s3 cp` send.

botocore builds the header from its components
(botocore/useragent.py UserAgentString.to_string): the CLI and CRT
versions, the platform, the language, the execution environment, the m/
feature ids, the retry mode, the app id, and the CLI's md/ extras
(awscli/clidriver.py). The CRT transfer client appends its own components,
from CRTS3NativeClient/ on, to the requests it sends, and moves the m/
feature ids after them, merged with its own.

The tests compare what the settings decide: which components appear and
the values a setting chooses. The components' order carries no meaning, so
they are compared as a set, and the feature ids as one set gathered from
every m/ section. Values that name the build or the host, the CLI and CRT
versions, the platform, the installer, and the distribution, are compared
by name only; the language and interpreter components name the
implementation itself and are left out, as are the session id the tests
disable and the reason the built binary's Python route names
(test_fallback_user_agent.py). What the CRT appends, its components and its own feature ids, is
the CRT's own, so it is left out too, and only its presence on the
transfer client's requests is checked.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import pytest

from credhelpers import run_command
from s3helpers import CRT_FEATURES, CRT_SUFFIX
from s3store import InMemoryS3, pattern_bytes, s3_runtime, write_tree

pytestmark = pytest.mark.asyncio

BUCKET: Final = "bucket"
DOWNLOAD_BODY: Final = pattern_bytes("object", 2048)
OBJECTS: Final = {
    (BUCKET, "download/object.txt"): DOWNLOAD_BODY,
    (BUCKET, "tree/a.txt"): pattern_bytes("tree a", 100),
}
CRT_BLOCK: Final = "[default]\ns3 =\n  preferred_transfer_client = crt\n"
# Components compared by name: their values name the build or the host.
NAMED_ONLY: Final = (
    "aws-cli/",
    "md/awscrt#",
    "os/",
    "md/arch#",
    "md/installer#",
)
# Components left out: the implementation's language and interpreter, the
# disabled session id, the reason the built binary's Python route names,
# the host's distribution, which only some hosts report, and the CRT's own
# components.
LEFT_OUT: Final = (
    "lang/",
    "md/pyimpl#",
    "sid/",
    "md/fallback#",
    "md/distrib#",
    CRT_SUFFIX,
    "platform/",
)
TRANSFER_OPERATIONS: Final = frozenset({"GetObject", "PutObject"})

# botocore's feature ids (useragent.py:56-122).
PAGINATOR: Final = "C"
RETRY_STANDARD: Final = "E"
RETRY_ADAPTIVE: Final = "F"
S3_TRANSFER: Final = "G"
REQUEST_CRC64: Final = "W"
REQUEST_WHEN_SUPPORTED: Final = "Z"
REQUEST_WHEN_REQUIRED: Final = "a"
RESPONSE_WHEN_SUPPORTED: Final = "b"
RESPONSE_WHEN_REQUIRED: Final = "c"
CREDENTIALS_ENV_VARS: Final = "g"
CLAUDE_CODE: Final = "AN"
OPENCODE: Final = "AR"
CRT_EXPLICIT: Final = "Ae"
CRT_AUTO: Final = "Ag"
IGNORED_ADAPTIVE: Final = (
    "warning: The following configuration values are not supported by the "
    "'crt' s3 transfer client and will be ignored: retry_mode = adaptive.\n"
)

Component = str | frozenset[str]


def shape(user_agent: str) -> frozenset[Component]:
    """The botocore components of a User-Agent, as the module docstring says.

    The feature ids are one member, wherever their m/ sections sit: the CRT
    client moves botocore's after its own components, merged with its own
    ids.
    """
    components: set[Component] = set()
    features: set[str] = set()
    for component in user_agent.split():
        if component.startswith(LEFT_OUT):
            continue
        named = [
            prefix for prefix in NAMED_ONLY if component.startswith(prefix)
        ]
        if named:
            components.add(named[0])
        elif component.startswith("m/"):
            features.update(component[2:].split(","))
        else:
            components.add(component)
    return frozenset({*components, frozenset(features - CRT_FEATURES)})


@dataclass(frozen=True)
class Case:
    environment: Mapping[str, str] = field(default_factory=dict[str, str])
    config: str = ""
    exec_env: str | None = None
    app: str | None = None
    checksums: str = "when_supported"
    retry_mode: str = "standard"
    agentic: frozenset[str] = frozenset()
    crt_explicit: bool = False

    def expected(self, command: str, operation: str) -> frozenset[Component]:
        supported = self.checksums == "when_supported"
        features = {
            RETRY_STANDARD
            if self.retry_mode == "standard"
            else RETRY_ADAPTIVE,
            REQUEST_WHEN_SUPPORTED if supported else REQUEST_WHEN_REQUIRED,
            RESPONSE_WHEN_SUPPORTED if supported else RESPONSE_WHEN_REQUIRED,
            *self.agentic,
        }
        if command == "ls":
            # The listing client resolves the credentials and pages.
            features |= {PAGINATOR, CREDENTIALS_ENV_VARS}
        else:
            # The transfer clients are built after the credentials are
            # cached, so they name no provider
            # (credentials/test_user_agent.py).
            features |= {
                S3_TRANSFER,
                CRT_EXPLICIT if self.crt_explicit else CRT_AUTO,
            }
            if operation == "PutObject" and supported:
                features.add(REQUEST_CRC64)
        components: set[Component] = {
            "aws-cli/",
            "md/awscrt#",
            "ua/2.1",
            "os/",
            "md/arch#",
            frozenset(features),
            f"cfg/retry-mode#{self.retry_mode}",
            "md/installer#",
            "md/prompt#off",
            f"md/command#s3.{'ls' if command == 'ls' else 'cp'}",
        }
        if self.exec_env is not None:
            components.add(f"exec-env/{self.exec_env}")
        if self.app is not None:
            components.add(f"app/{self.app}")
        return frozenset(components)


CASES: Final = {
    "defaults": Case(),
    # botocore replaces every character outside its allowed set with `-`
    # (useragent.py sanitize_user_agent_string_component); the app id
    # keeps `#` and `,`.
    "sanitized-values": Case(
        environment={
            "AWS_EXECUTION_ENV": "a b#c/é",
            "AWS_SDK_UA_APP_ID": "x y#z/é,ok",
        },
        exec_env="a-b-c--",
        app="x-y#z--,ok",
    ),
    "profile-app-id": Case(
        config="[default]\nsdk_ua_app_id = app\n", app="app"
    ),
    # An empty variable hides the profile's app id.
    "empty-app-id-variable": Case(
        environment={"AWS_SDK_UA_APP_ID": ""},
        config="[default]\nsdk_ua_app_id = hidden\n",
    ),
    "checksums-when-required": Case(
        environment={
            "AWS_REQUEST_CHECKSUM_CALCULATION": "when_required",
            "AWS_RESPONSE_CHECKSUM_VALIDATION": "when_required",
        },
        checksums="when_required",
    ),
    "agentic-callers": Case(
        environment={"CLAUDECODE": "1", "OPENCODE": "x"},
        agentic=frozenset({CLAUDE_CODE, OPENCODE}),
    ),
    "crt-preferred": Case(config=CRT_BLOCK, crt_explicit=True),
    # The CRT client runs without adaptive retries and warns about them.
    "crt-preferred-adaptive": Case(
        environment={"AWS_RETRY_MODE": "adaptive"},
        config=CRT_BLOCK,
        retry_mode="adaptive",
        crt_explicit=True,
    ),
}
COMMANDS: Final = {
    "ls": ("s3", "ls", f"s3://{BUCKET}/tree/"),
    "download": (
        "s3",
        "cp",
        f"s3://{BUCKET}/download/object.txt",
        "object.txt",
        "--no-progress",
    ),
    "upload": (
        "s3",
        "cp",
        "upload.txt",
        f"s3://{BUCKET}/up/upload.txt",
        "--no-progress",
    ),
}


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize("case", CASES)
async def test_user_agent_names_the_settings(
    aws_cli: str, tmp_path: Path, case: str, command: str
) -> None:
    settings = CASES[case]
    work = tmp_path / "work"
    work.mkdir()
    write_tree(work, {"upload.txt": b"upload\n"})
    store = InMemoryS3(OBJECTS)
    async with s3_runtime(store, tmp_path) as (_, env):
        Path(env["AWS_CONFIG_FILE"]).write_text(
            settings.config, encoding="utf-8"
        )
        # The session id would open the session database under HOME.
        env["AWS_CLI_SESSION_ID_DISABLED"] = "true"
        env.update(settings.environment)
        stdout, stderr, returncode = await run_command(
            [aws_cli, *COMMANDS[command]], env, cwd=work, stdin=None
        )
    user_agents = [
        (
            request.operation_model.name,
            request.wire_request.headers.get("user-agent", ""),
        )
        for request in store.received
    ]
    report = (
        f"exit {returncode}\nstdout: {stdout!r}\nstderr: {stderr!r}\n"
        f"user agents: {user_agents}\nfailures: {store.failures}\n"
    )
    assert store.failures == [], report
    warning = (
        IGNORED_ADAPTIVE
        if command != "ls" and settings.retry_mode == "adaptive"
        else ""
    )
    assert (returncode, stderr.decode()) == (0, warning), report
    assert user_agents, report
    for operation, user_agent in user_agents:
        assert shape(user_agent) == settings.expected(
            command, operation
        ), report
        if operation in TRANSFER_OPERATIONS:
            assert f" {CRT_SUFFIX}" in user_agent, report
