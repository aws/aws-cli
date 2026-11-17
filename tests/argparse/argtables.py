#!/usr/bin/env python3
"""Compare native tables with the in-tree AWS CLI's registered argument tables.

xtask supplies the dependency source path. The worker imports that source in a
cached venv holding the upstream AWS CLI's hash-pinned runtime lock.
"""

import argparse
import difflib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Final

# This checker is executed by path, so its only import path is its own
# directory. The venv helpers live one level up, in tests/; append rather
# than prepend, as tests/blackbox/run.py does.
sys.path.append(str(Path(__file__).resolve().parents[1]))

import harness_venv

VENV_DEPS_REVISION: Final = "1"
UPSTREAM_RUNTIME_REQUIREMENTS: Final = (
    "requirements/download-deps/system-sandbox-lock.txt"
)


def describe_table(
    parser: Any, cli_types: dict[str, str]
) -> list[dict[str, Any]]:
    """Describe each argparse action in the form the drift check compares."""
    actions = {
        "_StoreAction": "store",
        "_StoreTrueAction": "store_true",
        "_StoreFalseAction": "store_false",
        "_AppendAction": "append",
        "_VersionAction": "version",
        "AppendFilter": "append_named",
        "CommandAction": "command",
    }
    result = []
    for action in parser._actions:
        name = (
            action.option_strings[0][2:]
            if action.option_strings
            else action.dest
        )
        kind = actions[type(action).__name__]
        cli_type = cli_types.get(name)
        result.append(
            {
                "name": name,
                "positional": not action.option_strings,
                "action": kind,
                "nargs": action.nargs if action.nargs != 0 else None,
                "const": (
                    action.const
                    if kind not in {"store_true", "store_false"}
                    else None
                ),
                "default": (
                    None
                    if action.default == argparse.SUPPRESS
                    else action.default
                ),
                "choices": list(action.choices or []),
                "dest": action.dest,
                "required": action.required,
                "cli_type": (
                    cli_type
                    if cli_type in {"integer", "map", "blob"}
                    else None
                ),
            }
        )
    return result


def upstream_tables() -> dict[str, Any]:
    """Build only parser tables; no command is called or credential resolved."""
    import awscli
    from awscli.argparser import ArgTableArgParser, CLIArgParser
    from awscli.arguments import CustomArgument
    from awscli.customizations.s3.s3 import (
        S3,
        register_s3_sync_strategies,
    )
    from botocore.loaders import Loader
    from botocore.session import Session

    session = Session()
    session.register_component(
        "data_loader",
        Loader(
            extra_search_paths=[str(Path(awscli.__file__).parent / "data")],
            include_default_search_paths=False,
        ),
    )
    register_s3_sync_strategies(session)
    source = session.get_component("data_loader").load_data("cli")["options"]
    globals_parser = CLIArgParser(add_help=False, conflict_handler="resolve")
    cli_types = {}
    for name, definition in source.items():
        data = {
            key: value
            for key, value in definition.items()
            if key not in {"type", "help"}
        }
        CustomArgument(name, **data).add_to_parser(globals_parser)
        if definition.get("type") == "int":
            cli_types[name] = "integer"

    def command_table(command: Any) -> dict[str, Any]:
        # This property fires sync-strategy registration before arg_table.
        children = command.subcommand_table
        arguments = command.arg_table
        parser = ArgTableArgParser(arguments)
        return {
            "name": command.name,
            "kind": "basic",
            "usage": getattr(command, "USAGE", None),
            "arguments": describe_table(
                parser,
                {name: arg.cli_type_name for name, arg in arguments.items()},
            ),
            "subcommands": (
                [command_table(child) for child in children.values()]
                if children
                else None
            ),
        }

    return {
        "globals": describe_table(globals_parser, cli_types),
        "s3": command_table(S3(session)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--aws-cli-source")
    parser.add_argument("--cache-dir")
    parser.add_argument("--native-tables", type=Path)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(upstream_tables()))
        return
    if not all(
        (
            args.aws_cli_source,
            args.cache_dir,
            args.native_tables,
        )
    ):
        parser.error("source, cache-dir and native-tables are required")
    harness_venv.validate_host_python("the argument table check")
    source = Path(args.aws_cli_source).resolve()
    cache_dir = Path(args.cache_dir).resolve()
    python = harness_venv.ensure_venv(
        cache_dir / "venv",
        [source / UPSTREAM_RUNTIME_REQUIREMENTS],
        VENV_DEPS_REVISION,
    )
    env = os.environ.copy()
    python_paths = [str(source)]
    if existing := env.get("PYTHONPATH"):
        python_paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(python_paths)
    env["PYTHONPYCACHEPREFIX"] = str(cache_dir / "pycache")
    completed = subprocess.run(
        [str(python), str(Path(__file__).resolve()), "--worker"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    upstream = json.loads(completed.stdout)
    native = json.loads(args.native_tables.read_text())
    if native != upstream:
        left = json.dumps(upstream, indent=2).splitlines(keepends=True)
        right = json.dumps(native, indent=2).splitlines(keepends=True)
        sys.stderr.writelines(
            difflib.unified_diff(
                left, right, fromfile="in-tree AWS CLI", tofile="native tables"
            )
        )
        raise SystemExit(1)
    print(
        "Argument tables match in-tree AWS CLI globals and all nine S3 commands."
    )


if __name__ == "__main__":
    main()
