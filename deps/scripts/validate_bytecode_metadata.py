#!/usr/bin/env python3
"""Reject stale or mixed Python payload/runtime bytecode artifacts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--expected-magic", required=True)
    parser.add_argument("--stamp", type=Path, required=True)
    args = parser.parse_args()

    metadata = json.loads(args.metadata.read_text())
    actual_magic = int.from_bytes(importlib.util.MAGIC_NUMBER, "little")
    if str(actual_magic) != args.expected_magic:
        raise SystemExit(
            "selected Python magic changed during validation: "
            f"expected {args.expected_magic}, found {actual_magic}"
        )
    expected = {
        "implementation": sys.implementation.name,
        "cache_tag": sys.implementation.cache_tag,
        "magic_number": importlib.util.MAGIC_NUMBER.hex(),
        "payload_sha256": sha256(args.payload),
        "runtime_sha256": sha256(args.runtime),
    }
    mismatches = [
        f"{key}: expected {value!r}, found {metadata.get(key)!r}"
        for key, value in expected.items()
        if metadata.get(key) != value
    ]
    if mismatches:
        raise SystemExit(
            "bytecode metadata validation failed: " + "; ".join(mismatches)
        )

    args.stamp.write_text("validated\n")


if __name__ == "__main__":
    main()
