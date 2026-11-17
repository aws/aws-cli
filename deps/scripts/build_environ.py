"""The environment a build driver hands to every tool it runs.

Every driver receives the caller's environment; its child tools inherit only
variables listed in tool_environ.txt. Compilers, flags, and SDK paths are
explicit stage inputs. LC_ALL=C keeps diagnostics deterministic.

pip is the one tool that talks to the network. network_environ() returns
the proxy, certificate, and index settings pip needs to reach its index;
--require-hashes pins every artifact it downloads, so where it came from
cannot change the output.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path

ALLOWLIST_FILE = "tool_environ.txt"

# Everything pip reads to reach an index: proxies in both spellings, the
# certificate bundle overrides the urllib3 and requests stacks honor, and
# pip's own index, mirror, and transport settings.
NETWORK_VARIABLES = (
    "http_proxy",
    "https_proxy",
    "no_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
    "PIP_CONFIG_FILE",
    "PIP_NO_INDEX",
    "PIP_FIND_LINKS",
    "PIP_INDEX_URL",
    "PIP_EXTRA_INDEX_URL",
    "PIP_TRUSTED_HOST",
    "PIP_CERT",
    "PIP_CLIENT_CERT",
    "PIP_PROXY",
    "PIP_TIMEOUT",
    "PIP_RETRIES",
)


def allowlist() -> list[str]:
    """The variable names in tool_environ.txt, in file order."""
    text = (Path(__file__).resolve().parent / ALLOWLIST_FILE).read_text(
        encoding="utf-8"
    )
    names: list[str] = []
    for line in text.splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        names.append(entry)
    return names


def tool_environ(
    source: Mapping[str, str] | None = None,
    *,
    msvc_environ: Path | None = None,
) -> dict[str, str]:
    """The allowlisted variables of `source` (os.environ by default) plus
    LC_ALL=C."""
    parent = os.environ if source is None else source
    names = allowlist()
    if os.name == "nt":
        allowed = {name.upper() for name in names}
        environ = {
            name: value
            for name, value in parent.items()
            if name.upper() in allowed
        }
    else:
        environ = {name: parent[name] for name in names if name in parent}
    if msvc_environ is not None:
        captured = json.loads(msvc_environ.read_text(encoding="utf-8"))
        if not isinstance(captured, dict) or not all(
            isinstance(name, str) and isinstance(value, str)
            for name, value in captured.items()
        ):
            raise ValueError(
                "captured MSVC environment must map names to strings"
            )
        environ = {name.upper(): value for name, value in environ.items()}
        environ.update(
            (name.upper(), value)
            for name, value in captured.items()
            if name.upper() != "HOME"
        )
    environ["LC_ALL"] = "C"
    return environ


def network_environ(
    source: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """The network settings present in `source` (os.environ by default),
    for the pip invocation alone."""
    parent = os.environ if source is None else source
    return {name: parent[name] for name in NETWORK_VARIABLES if name in parent}
