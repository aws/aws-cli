"""Produce relocation-independent sysconfig metadata for the payload only.

The installed interpreter still needs its physical build metadata to run
venv and pip. These copies live outside its stdlib and are consumed only
by the fallback packer, ahead of the unmodified stdlib.
"""

from __future__ import annotations

import ast
import json
import pprint
import re
import shlex
import shutil
from collections.abc import Sequence
from pathlib import Path

RUNTIME_PREFIX = "/aws-cli-python"
PAYLOAD_DIRECTORY = "lib/payload-sysconfig"

# These sysconfig values are shell argument lists, not opaque runtime strings.
SHELL_VARIABLES = frozenset(
    {
        "CONFIG_ARGS",
        "PROFILE_TASK",
        "CC",
        "CXX",
        "CPP",
        "AR",
        "RANLIB",
        "LLVM_AR",
        "LLVM_PROFDATA",
        "BLDSHARED",
        "LDSHARED",
        "LDCXXSHARED",
        "LINKCC",
        "LIBS",
        "MODLIBS",
        "SYSLIBS",
    }
)


def normalize_vars(
    values: dict[str, object], roots: Sequence[tuple[Path, str]]
) -> dict[str, object]:
    """Replace known roots in string values, never keys or nonpath values.

    Match entire roots or descendants, not similarly named siblings or
    substrings of unrelated paths. Attached compiler -I/-L/-F arguments
    are path boundaries too. One substitution pass, longest root first,
    prevents nested roots and logical replacements from being remapped.
    """
    mappings: dict[str, str] = {}
    known_roots = list(roots)
    # CPython's JSON snapshot includes the build user's computed userbase.
    # It is not a configured build input and sysconfig recomputes it at
    # runtime, but its stored copy must not disclose that user's home.
    userbase = values.get("userbase")
    if isinstance(userbase, str) and userbase:
        known_roots.append((Path(userbase), "/aws-cli-python-user"))
    for root, logical in known_roots:
        for spelling in {str(root), root.as_posix()}:
            # CONFIG_ARGS and CFLAGS can shell-escape apostrophes in roots.
            quoted = shlex.quote(spelling)
            spellings = {spelling, spelling.replace("'", "'\\''")}
            if quoted.startswith("'"):
                spellings.add(quoted[1:-1])
            for variant in spellings:
                mappings[variant] = logical
    if not mappings:
        return dict(values)
    alternatives = "|".join(
        re.escape(root)
        for root in sorted(mappings, key=lambda root: (-len(root), root))
    )
    pattern = re.compile(
        r"(?<![\w./\\-])(?P<flag>-[ILF])?"
        f"(?P<root>{alternatives})"
        r"(?=$|[/\\\s'\"=:;,()])"
    )
    result: dict[str, object] = {}
    for key, value in values.items():
        if isinstance(value, dict):
            result[key] = normalize_vars(value, roots)
            continue
        if not isinstance(value, str):
            result[key] = value
            continue
        normalized = pattern.sub(
            lambda match: (match["flag"] or "") + mappings[match["root"]],
            value,
        )
        if normalized != value and (
            "FLAGS" in key or key in SHELL_VARIABLES or key.endswith("_LIBS")
        ):
            # A physical root containing spaces needs shell quotes while
            # the same logical root does not. Canonicalize that spelling
            # so changing the kind of checkout path cannot change bytes.
            normalized = shlex.join(shlex.split(normalized))
        result[key] = normalized
    return result


def read_python_vars(source: Path) -> dict[str, object]:
    """Read CPython's literal build_time_vars without executing its module."""
    module = ast.parse(source.read_text(encoding="utf-8"))
    assignments = [
        node
        for node in module.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "build_time_vars"
            for target in node.targets
        )
    ]
    if len(assignments) != 1:
        raise ValueError(f"expected one build_time_vars assignment: {source}")
    values = ast.literal_eval(assignments[0].value)
    if not isinstance(values, dict):
        raise TypeError(f"expected a sysconfig dictionary: {source}")
    if not all(isinstance(key, str) for key in values):
        raise TypeError(f"expected string sysconfig keys: {source}")
    return values


def write_payload_sysconfig(
    stdlib: Path,
    prefix: Path,
    roots: Sequence[tuple[Path, str]],
    *,
    required: bool,
) -> None:
    """Emit stable Python/JSON copies beside the installation, not into it.

    POSIX CPython 3.14 installs both formats; missing either is a producer
    failure. Windows computes sysconfig at runtime and installs neither,
    so it still publishes an empty override directory for the packer.
    """
    sources = sorted(stdlib.glob("_sysconfigdata_*.py"))
    snapshots = sorted(stdlib.glob("_sysconfig_vars_*.json"))
    if required and (not sources or not snapshots):
        raise ValueError(f"missing installed sysconfig metadata: {stdlib}")
    # CPython 3.14's PEP 739 metadata nests library/header installation paths.
    details = stdlib / "build-details.json"
    if details.is_file():
        snapshots.append(details)
    destination = prefix / PAYLOAD_DIRECTORY
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for source in sources:
        values = normalize_vars(read_python_vars(source), roots)
        text = (
            "# Payload-only sysconfig metadata; do not use for building.\n"
            f"build_time_vars = {pprint.pformat(values, width=79)}\n"
        )
        (destination / source.name).write_text(text, encoding="utf-8")
    for source in snapshots:
        values = json.loads(source.read_text(encoding="utf-8"))
        text = (
            json.dumps(normalize_vars(values, roots), sort_keys=True, indent=2)
            + "\n"
        )
        (destination / source.name).write_text(text, encoding="utf-8")
