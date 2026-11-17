#!/usr/bin/env python3
"""Check the tool environment contract from a staged directory.

tests/deps/test_build_checks.py copies this script beside the shared driver
modules, build_environ.py and tool_environ.txt among them, into an
otherwise empty directory and runs it under the interpreter flags every
driver runs under. The checks below prove that interpreter is isolated
from the caller's Python configuration, that the allowlist parses to
tool-discovery variables only, that the tool and pip environments are
built from it as documented, and that a sitecustomize reachable through
PYTHONPATH runs under a plain interpreter but not under the isolated one.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from build_environ import allowlist, network_environ, tool_environ

# Variables that must never be retained: each one changes what a compiler,
# a configure script, or the interpreter produces.
DROPPED = (
    "CPATH",
    "C_INCLUDE_PATH",
    "CFLAGS",
    "CXXFLAGS",
    "CPPFLAGS",
    "LDFLAGS",
    "LIBRARY_PATH",
    "PKG_CONFIG_PATH",
    "PYTHONPATH",
    "PERL5OPT",
    "MAKEFLAGS",
    "LC_ALL",
    "LANG",
    "SDKROOT",
    "CC",
    # The MSVC equivalents of the header, library, and flag injection
    # above. The one builder that needs the MSVC environment discovers the
    # installation itself and exports these from inside its own step, where
    # the toolchain version joins that step's hashed arguments.
    "INCLUDE",
    "LIB",
    "LIBPATH",
    "CL",
    "_CL_",
)


def interpreter_flags() -> list[str]:
    """The flags the build passed to this interpreter, from its original
    command line: everything between the executable and the script."""
    script = sys.orig_argv.index(sys.argv[0])
    return sys.orig_argv[1:script]


def check_interpreter_is_isolated() -> None:
    expected = {
        "-E": sys.flags.ignore_environment,
        "-s": sys.flags.no_user_site,
        "-B": sys.flags.dont_write_bytecode,
    }
    missing = [flag for flag, present in expected.items() if not present]
    if missing:
        raise SystemExit(
            f"the driver interpreter is missing {missing}: "
            f"started as {sys.orig_argv!r}"
        )


def check_allowlist_parses() -> None:
    names = allowlist()
    if "PATH" not in names:
        raise SystemExit(f"the allowlist does not retain PATH: {names}")
    if len(names) != len(set(names)):
        raise SystemExit(f"the allowlist repeats a name: {names}")
    retained = [name for name in DROPPED if name in names]
    if retained:
        raise SystemExit(f"the allowlist retains {retained}")
    malformed = [name for name in names if any(c in name for c in "=# \t")]
    if malformed:
        raise SystemExit(f"the allowlist holds malformed entries {malformed}")


def check_tool_environ_filters() -> None:
    parent = {
        "PATH": "/usr/bin",
        "HOME": "/home/build",
        "CPATH": "/opt/include",
        "CFLAGS": "-O3",
        "PYTHONPATH": "/tmp/site",
        "LANG": "en_US.UTF-8",
        "LC_ALL": "de_DE.UTF-8",
    }
    environ = tool_environ(parent)
    expected = {"PATH": "/usr/bin", "HOME": "/home/build", "LC_ALL": "C"}
    if environ != expected:
        raise SystemExit(f"tool_environ built {environ}, expected {expected}")
    if "PATH" not in tool_environ():
        raise SystemExit("tool_environ() did not read PATH from os.environ")


def check_network_environ_is_pip_only() -> None:
    parent = {
        "PATH": "/usr/bin",
        "https_proxy": "http://proxy:3128",
        "PIP_INDEX_URL": "https://mirror/simple",
        "PIP_NO_BINARY": ":all:",
        "CFLAGS": "-O3",
    }
    environ = network_environ(parent)
    expected = {
        "https_proxy": "http://proxy:3128",
        "PIP_INDEX_URL": "https://mirror/simple",
    }
    if environ != expected:
        raise SystemExit(
            f"network_environ built {environ}, expected {expected}"
        )


def check_sitecustomize_is_blocked() -> None:
    with tempfile.TemporaryDirectory(prefix="buildkit-site-") as tmp:
        site_dir = Path(tmp) / "site"
        site_dir.mkdir()
        marker = Path(tmp) / "marker"
        (site_dir / "sitecustomize.py").write_text(
            "import pathlib\n"
            f"pathlib.Path({str(marker)!r}).write_text('ran')\n",
            encoding="utf-8",
        )
        environ = {**os.environ, "PYTHONPATH": str(site_dir)}
        # The positive control: a plain interpreter runs it. Without this
        # the check below could pass because nothing was observable.
        subprocess.run([sys.executable, "-c", "pass"], env=environ, check=True)
        if not marker.exists():
            raise SystemExit(
                "a plain interpreter did not run the PYTHONPATH sitecustomize;"
                " the isolation check cannot observe anything"
            )
        marker.unlink()
        subprocess.run(
            [sys.executable, *interpreter_flags(), "-c", "pass"],
            env=environ,
            check=True,
        )
        if marker.exists():
            raise SystemExit(
                "the PYTHONPATH sitecustomize ran under the isolated "
                f"interpreter ({interpreter_flags()})"
            )


def main() -> None:
    check_interpreter_is_isolated()
    check_allowlist_parses()
    check_tool_environ_filters()
    check_network_environ_is_pip_only()
    check_sitecustomize_is_blocked()
    print("build_environ: allowlist, tool environment, and isolation checked")


if __name__ == "__main__":
    main()
