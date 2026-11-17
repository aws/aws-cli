#!/usr/bin/env python3
"""Generate the autocomplete index and split it into payload entries.

Auto-prompt and the completer query upstream's SQLite autocomplete index,
`awscli/data/ac.index`, which upstream generates when it builds its release
package. Embedding that file would add about 22 MB to the binary. Every
index query filters on one exact `parent`, the dot-joined lineage of the
command it asks about, so this script groups the rows by the top-level
command their parent names and writes one JSON entry per command under
`awscli/autocomplete/index/`. `crates/python-fallback/python/runtime.py`
fills an in-memory database from an entry the first time a query names its
command. The packer compresses the entries to about 0.7 MB.

Each entry is a JSON object of rows, kept in their table order:

    {
      "commands": {parent: [[command, full_name], ...]},
      "params": {
        parent: {command: [first_param_id, [[argname, type_name, nargs,
                                              positional_arg, required],
                                             ...]]},
      },
      "apicalls": [[param_id, apicall_data], ...],
    }

A command's parameters have consecutive ids, so an entry stores only the
first. The root entry, `_root.json`, holds the rows whose parent is `""` or
`"aws"`, and its "schema" member holds the index's CREATE statements.
Before writing, the script rebuilds a database from the encoded entries
and fails unless every table matches the generated index row for row.

The rows come from upstream's own generator, which builds every command
table of a live CLI driver. Building them imports modules that use two
extensions the packing interpreter may not load: the static interpreter
has no CRT extension, and on static musl `import ctypes` fails for want of
a dynamic loader. Nothing calls into either while tables are built, so
stand-ins whose functions do nothing take their place; the rows are
identical to a run with the real CRT extension. The driver reads the
user's configuration, aliases, and models, so it runs with an empty home
directory and without `AWS_*` variables.

Usage:
    gen_ac_index.py --output-root DIR --python-path DIR [--python-path DIR]

The `--python-path` directories hold the `awscli` and `awscrt` packages.
They go to the front of `sys.path` in the order given; the interpreter's
own site-packages supply the remaining dependencies.
"""

from __future__ import annotations

import argparse
import collections
import importlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import types
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

# Payload key prefix of the entries. crates/python-fallback/python/runtime.py
# reads the same prefix, and pack.py chooses their compression by it.
ENTRY_DIR = ("awscli", "autocomplete", "index")
ROOT_ENTRY = "_root"
# Top-level command names become entry file names. The pattern keeps them
# path-safe and apart from ROOT_ENTRY.
ENTRY_NAME = re.compile(r"[a-z0-9][a-z0-9-]*")

# Each query reads one table in an order the rebuilt database must
# reproduce. Within a parent, upstream's queries return rows in table
# order, so command rows are compared in that order.
VERIFY_QUERIES = (
    "SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY name",
    "SELECT * FROM command_table ORDER BY parent, rowid",
    "SELECT * FROM param_table ORDER BY param_id",
    "SELECT * FROM apicall_table ORDER BY param_id",
)

Entry = dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--python-path", type=Path, action="append", required=True
    )
    return parser.parse_args()


def isolate_environment(home: Path) -> None:
    """Hide the caller's AWS configuration from the CLI driver.

    The driver loads aliases and models from the home directory, and
    plugins and data paths from the config file and `AWS_*` variables.
    Windows resolves `~` through USERPROFILE rather than HOME.
    """
    for name in [name for name in os.environ if name.startswith("AWS_")]:
        del os.environ[name]
    home.mkdir()
    os.environ["HOME"] = str(home)
    os.environ["USERPROFILE"] = str(home)


def unavailable_extension(name: str) -> types.ModuleType:
    """A module whose every attribute is a function that does nothing."""

    def attribute(attr: str) -> Callable[..., None]:
        if attr.startswith("__") and attr.endswith("__"):
            raise AttributeError(attr)

        def do_nothing(*args: object, **kwargs: object) -> None:
            return None

        return do_nothing

    module = types.ModuleType(name)
    # A module-level __getattr__ (PEP 562) answers every missing attribute.
    setattr(module, "__getattr__", attribute)
    return module


def install_stand_ins() -> None:
    """Replace extensions that building command tables imports but never
    calls."""
    sys.modules["_awscrt"] = unavailable_extension("_awscrt")
    try:
        importlib.import_module("ctypes")
    except OSError:
        sys.modules["ctypes"] = unavailable_extension("ctypes")


def generate_index(path: Path) -> None:
    # Imported here because the import needs the path and stand-ins set up
    # by main.
    from awscli.autocomplete import generator

    generator.generate_index(str(path))


def entry_name(parent: str) -> str:
    """The entry holding the rows whose parent is `parent`.

    Mirrors `_autocomplete_index_entry` in
    crates/python-fallback/python/runtime.py.
    """
    lineage = parent.split(".")
    if len(lineage) < 2:
        return ROOT_ENTRY
    return lineage[1]


def new_entry() -> Entry:
    return {"commands": {}, "params": {}, "apicalls": []}


def split_index(index: sqlite3.Connection) -> Mapping[str, Entry]:
    """The index rows grouped into entries by `entry_name`."""
    entries: dict[str, Entry] = collections.defaultdict(new_entry)
    entries[ROOT_ENTRY]["schema"] = [
        sql
        for (sql,) in index.execute(
            "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL "
            "ORDER BY rowid"
        )
    ]
    for command, full_name, parent in index.execute(
        "SELECT command, full_name, parent FROM command_table ORDER BY rowid"
    ):
        commands = entries[entry_name(parent)]["commands"]
        commands.setdefault(parent, []).append([command, full_name])

    param_entries: dict[int, str] = {}
    for param_id, command, parent, *row in index.execute(
        "SELECT param_id, command, parent, argname, type_name, nargs, "
        "positional_arg, required FROM param_table ORDER BY param_id"
    ):
        name = entry_name(parent)
        param_entries[param_id] = name
        params = entries[name]["params"]
        group = params.setdefault(parent, {}).setdefault(
            command, [param_id, []]
        )
        if group[0] + len(group[1]) != param_id:
            raise SystemExit(
                f"parameters of {parent} {command} do not have consecutive "
                f"ids: {param_id} follows {group[0] + len(group[1]) - 1}"
            )
        group[1].append(row)

    for apicall_data, param_id in index.execute(
        "SELECT apicall_data, param_id FROM apicall_table ORDER BY rowid"
    ):
        entries[param_entries[param_id]]["apicalls"].append(
            [param_id, apicall_data]
        )

    for name in entries:
        if name != ROOT_ENTRY and ENTRY_NAME.fullmatch(name) is None:
            raise SystemExit(f"unsupported top-level command name: {name!r}")
    return entries


def load_entry(database: sqlite3.Connection, entry: Entry) -> None:
    """Insert an entry's rows.

    Mirrors `_insert_autocomplete_index_rows` in
    crates/python-fallback/python/runtime.py.
    """
    database.executemany(
        "INSERT INTO command_table (command, full_name, parent) "
        "VALUES (?, ?, ?)",
        [
            (command, full_name, parent)
            for parent, rows in entry["commands"].items()
            for command, full_name in rows
        ],
    )
    database.executemany(
        "INSERT INTO param_table (param_id, command, parent, argname, "
        "type_name, nargs, positional_arg, required) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (first_param_id + offset, command, parent, *row)
            for parent, commands in entry["params"].items()
            for command, (first_param_id, rows) in commands.items()
            for offset, row in enumerate(rows)
        ],
    )
    database.executemany(
        "INSERT INTO apicall_table (param_id, apicall_data) VALUES (?, ?)",
        entry["apicalls"],
    )


def verify_entries(
    index: sqlite3.Connection, encoded: Mapping[str, bytes]
) -> None:
    """Fail unless the encoded entries rebuild the index row for row."""
    rebuilt = sqlite3.connect(":memory:")
    try:
        for statement in json.loads(encoded[ROOT_ENTRY])["schema"]:
            rebuilt.execute(statement)
        for name in sorted(encoded):
            load_entry(rebuilt, json.loads(encoded[name]))
        for query in VERIFY_QUERIES:
            expected = index.execute(query).fetchall()
            if rebuilt.execute(query).fetchall() != expected:
                raise SystemExit(
                    f"autocomplete index entries do not rebuild the index: "
                    f"{query!r} differs"
                )
    finally:
        rebuilt.close()


def write_entries(output_root: Path, encoded: Mapping[str, bytes]) -> None:
    if output_root.exists():
        shutil.rmtree(output_root)
    entry_dir = output_root.joinpath(*ENTRY_DIR)
    entry_dir.mkdir(parents=True)
    for name, data in encoded.items():
        (entry_dir / f"{name}.json").write_bytes(data)


def main() -> None:
    args = parse_args()
    # The AWS CLI source and its dependencies are read-only inputs.
    sys.dont_write_bytecode = True
    with tempfile.TemporaryDirectory(prefix="aws-ac-index-") as scratch_text:
        scratch = Path(scratch_text)
        isolate_environment(scratch / "home")
        sys.path[:0] = [str(path) for path in args.python_path]
        install_stand_ins()
        index_path = scratch / "ac.index"
        generate_index(index_path)
        index = sqlite3.connect(index_path)
        try:
            encoded = {
                name: json.dumps(entry, separators=(",", ":")).encode()
                for name, entry in split_index(index).items()
            }
            verify_entries(index, encoded)
        finally:
            index.close()
    write_entries(args.output_root, encoded)
    print(
        f"autocomplete index: {len(encoded)} entries, "
        f"{sum(map(len, encoded.values())):,} bytes",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
