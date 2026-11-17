#!/usr/bin/env python3
"""
Pack a tree of Python source + data files into a zipPy blob (`ZIPPY003`).

Usage:
    pack.py <output.blob> <root1>[:<prefix>] [<root2>[:<prefix>]] ...

Each input root is a directory of Python source. With a `:prefix` suffix,
modules under that root are renamed `<prefix>.<rel-module-path>`. Without a
prefix, modules are named by their path under the root. The separator is the
last colon in the spec, so a Windows drive-lettered root must carry it
explicitly (`C:\\stdlib:`); every caller here spells the empty prefix out.

Pure-Python files become bytecode (marshalled code object) entries with
FLAG_BYTECODE set. Data files (.json, .pem, .rst, etc.) become FLAG_RESOURCE
entries with raw bytes.

Compression policy
==================
- Code (FLAG_BYTECODE): RAW. Marshal-loaded zero-copy from .rodata at import.
- botocore service models (`awscli/botocore/data/**`): RAW. Hot-path: every
  command exercises `list_available_services` which iterates hundreds of
  models; decompressing on each lookup added ~50-100 ms of startup.
- RST resources (`*.rst`): zstd-compressed with the Python 3.14+ stdlib
  `compression.zstd`, or raw on older interpreters. These are cold
  help/example files.
- Autocomplete index entries (`awscli/autocomplete/index/*.json`, from
  gen_ac_index.py): zstd-compressed at level 19, or raw on older
  interpreters. Auto-prompt reads an entry once per session, so the slower
  level is spent at pack time only, and it stores the entries in about
  0.7 MB rather than 0.85 MB.
- Other resources (awscli/data, PEMs, dist-info text, etc.): RAW.

The `FLAG_COMPRESSED` bit on each entry tells the reader whether to
decompress. The reader pays decompression cost only on actual reads of
compressed entries — `_zippy_finder.exists()` and `list_prefix()` consult
the index without touching payloads.

Limitations:
- Bytecode-compiled with the host Python's `compile()`. Use a host CPython
  whose version matches the embedded target build.
- Doesn't pack PEP 420 namespace packages without an `__init__.py`; give
  such a package an `__init__.py` before packing it.
- Doesn't pack C extension `.so` files in the input tree (they're
  statically linked separately).
"""

from __future__ import annotations

import csv
import fnmatch
import io
import marshal
import os
import struct
import sys
from collections.abc import Iterator
from dataclasses import dataclass

try:
    import compression.zstd as zstd
except ModuleNotFoundError:
    zstd = None


# Format constants. Keep in sync with crates/pyload/src/format.rs.
MAGIC = b"ZIPPY003"
UINT32_MAX = 0xFFFFFFFF
UINT64_MASK = 0xFFFFFFFFFFFFFFFF
EMPTY_CONTROL = 0x80
GROUP_WIDTH = 16
FLAG_PACKAGE = 1 << 0
FLAG_BYTECODE = 1 << 1
FLAG_RESOURCE = 1 << 2
FLAG_COMPRESSED = 1 << 3

# EntryMetaV3: name span, data span, lengths, flags, reserved.
ENTRY_META_FMT = "<IIIIIHH"
ENTRY_META_SIZE = struct.calcsize(ENTRY_META_FMT)
assert ENTRY_META_SIZE == 24

# HeaderV3: magic, counts, flags, index width, offsets, reserved.
HEADER_FMT = "<8sIIIIQQQQQQ"
HEADER_SIZE = struct.calcsize(HEADER_FMT)
assert HEADER_SIZE == 72


@dataclass(frozen=True)
class EntryInput:
    key: bytes
    flags: int
    payload: bytes
    alias_of: int | None


@dataclass(frozen=True)
class StoredData:
    offset: int
    stored_len: int
    raw_len: int
    is_compressed: bool


@dataclass(frozen=True)
class LookupMetrics:
    bucket_count: int
    index_width: int
    max_probe_groups: int
    total_probe_groups: int
    candidate_name_checks: int


def fnv1a64(s: bytes) -> int:
    """64-bit FNV-1a hash. Mirrors fnv1a64 in crates/pyload/src/format.rs."""
    h = 0xCBF29CE484222325
    for b in s:
        h ^= b
        h = (h * 0x100000001B3) & UINT64_MASK
    return h


def h2(hash_value: int) -> int:
    return hash_value >> 57


def h1_bucket(hash_value: int, mask: int) -> int:
    return hash_value & mask


def next_probe_bucket(bucket: int, stride: int, mask: int) -> tuple[int, int]:
    stride = (stride + GROUP_WIDTH) & mask
    return (bucket + stride) & mask, stride


def require_u32(label: str, value: int) -> int:
    if value < 0 or value > UINT32_MAX:
        print(f"ERROR: {label} does not fit in u32: {value}", file=sys.stderr)
        sys.exit(1)
    return value


def index_width_for_entry_count(entry_count: int) -> int:
    return 2 if entry_count <= 0x10000 else 4


def bucket_count_for_entry_count(entry_count: int) -> int:
    bucket_count = GROUP_WIDTH
    while entry_count * 8 > bucket_count * 7:
        bucket_count *= 2
    return bucket_count


def write_index(
    index_bytes: bytearray, width: int, bucket: int, value: int
) -> None:
    offset = bucket * width
    if width == 2:
        index_bytes[offset : offset + 2] = struct.pack("<H", value)
    elif width == 4:
        index_bytes[offset : offset + 4] = struct.pack("<I", value)
    else:
        raise AssertionError(f"invalid index width: {width}")


def read_index(index_bytes: bytearray, width: int, bucket: int) -> int:
    offset = bucket * width
    if width == 2:
        return struct.unpack_from("<H", index_bytes, offset)[0]
    if width == 4:
        return struct.unpack_from("<I", index_bytes, offset)[0]
    raise AssertionError(f"invalid index width: {width}")


def measure_lookup(
    ordered_entries: list[tuple[int, EntryInput]],
    control: bytearray,
    index_bytes: bytearray,
    index_width: int,
    bucket_count: int,
) -> LookupMetrics:
    max_probe_groups = 0
    total_probe_groups = 0
    candidate_name_checks = 0
    mask = bucket_count - 1
    max_groups = bucket_count // GROUP_WIDTH

    for expected_index, (_orig_idx, entry) in enumerate(ordered_entries):
        hash_value = fnv1a64(entry.key)
        target_h2 = h2(hash_value)
        bucket = h1_bucket(hash_value, mask)
        probe_stride = 0
        found = False
        for probe_group in range(1, max_groups + 1):
            for bit_index in range(GROUP_WIDTH):
                candidate_bucket = (bucket + bit_index) & mask
                control_byte = control[candidate_bucket]
                if control_byte == target_h2:
                    candidate_name_checks += 1
                    entry_index = read_index(
                        index_bytes,
                        index_width,
                        candidate_bucket,
                    )
                    if entry_index == expected_index:
                        max_probe_groups = max(max_probe_groups, probe_group)
                        total_probe_groups += probe_group
                        found = True
                        break
                elif control_byte == EMPTY_CONTROL:
                    break
            if found:
                break
            bucket, probe_stride = next_probe_bucket(
                bucket,
                probe_stride,
                mask,
            )
        if not found:
            raise RuntimeError(f"lookup table cannot find {entry.key!r}")

    return LookupMetrics(
        bucket_count=bucket_count,
        index_width=index_width,
        max_probe_groups=max_probe_groups,
        total_probe_groups=total_probe_groups,
        candidate_name_checks=candidate_name_checks,
    )


def build_lookup(
    ordered_entries: list[tuple[int, EntryInput]],
    index_width: int,
) -> tuple[bytearray, bytearray, LookupMetrics]:
    bucket_count = bucket_count_for_entry_count(len(ordered_entries))
    control = bytearray([EMPTY_CONTROL] * (bucket_count + GROUP_WIDTH))
    index_bytes = bytearray(bucket_count * index_width)
    mask = bucket_count - 1
    max_groups = bucket_count // GROUP_WIDTH

    for entry_index, (_orig_idx, entry) in enumerate(ordered_entries):
        hash_value = fnv1a64(entry.key)
        bucket = h1_bucket(hash_value, mask)
        probe_stride = 0
        placed = False
        for _probe_group in range(1, max_groups + 1):
            for bit_index in range(GROUP_WIDTH):
                candidate_bucket = (bucket + bit_index) & mask
                if control[candidate_bucket] == EMPTY_CONTROL:
                    control[candidate_bucket] = h2(hash_value)
                    write_index(
                        index_bytes,
                        index_width,
                        candidate_bucket,
                        entry_index,
                    )
                    placed = True
                    break
            if placed:
                break
            bucket, probe_stride = next_probe_bucket(
                bucket,
                probe_stride,
                mask,
            )
        if not placed:
            raise RuntimeError(f"could not place lookup entry {entry.key!r}")

    control[bucket_count : bucket_count + GROUP_WIDTH] = control[:GROUP_WIDTH]
    metrics = measure_lookup(
        ordered_entries,
        control,
        index_bytes,
        index_width,
        bucket_count,
    )
    return control, index_bytes, metrics


# Non-Python files we pack as package data. The suffix allowlist covers normal
# resources; every file below `.dist-info` is package metadata.
DATA_EXT_ALLOWLIST = {
    ".json",
    ".pem",
    ".rst",
    ".txt",
    ".html",
    ".css",
    ".js",
    ".yml",
    ".yaml",
    ".tex",
    ".sty",
    ".odt",
    ".gz",
}

# Directories we never pack. Most of these are CPython stdlib bits that
# awscli doesn't need (test/, idlelib/, tkinter/, ...) plus venv tooling
# (pip, setuptools) that's never invoked from the bundled `aws` binary.
EXCLUDE_DIRS = frozenset(
    {
        "__pycache__",
        "test",
        "tests",
        "idlelib",
        "tkinter",
        "turtle",
        "turtledemo",
        "lib2to3",
        "ensurepip",
        "pip",
        "setuptools",
        "wheel",
        "_distutils_hack",
    }
)

# pip and setuptools carry their version in their .dist-info directory
# names, so exact entries silently stop matching after a CPython bump
# and the stale metadata lands in the blob. Match the whole family.
EXCLUDE_DIR_PATTERNS = ("pip-*", "setuptools-*")


def is_excluded_dir(name: str) -> bool:
    return name in EXCLUDE_DIRS or any(
        fnmatch.fnmatch(name, pattern) for pattern in EXCLUDE_DIR_PATTERNS
    )


def is_python_file(path: str) -> bool:
    return path.endswith(".py")


def is_data_file(path: str) -> bool:
    _, ext = os.path.splitext(path)
    if ext.lower() in DATA_EXT_ALLOWLIST:
        return True
    return any(
        component.endswith(".dist-info")
        for component in path.split(os.sep)[:-1]
    )


def is_model_file(key: str) -> bool:
    """Service model JSON. Stored raw to avoid decompression on hot path."""
    return key.startswith("awscli/botocore/data/") or key.startswith(
        "botocore/data/"
    )


def is_rst_file(key: str) -> bool:
    return key.endswith(".rst")


# Where gen_ac_index.py's entries sit; crates/python-fallback/python/runtime.py
# reads the same prefix.
AUTOCOMPLETE_INDEX_PREFIX = "awscli/autocomplete/index/"
AUTOCOMPLETE_INDEX_ZSTD_LEVEL = 19


def resource_zstd_level(key: str) -> int | None:
    """The zstd level a resource is stored at, or None to store it raw."""
    if zstd is None:
        return None
    if key.startswith(AUTOCOMPLETE_INDEX_PREFIX):
        return AUTOCOMPLETE_INDEX_ZSTD_LEVEL
    if is_rst_file(key):
        return zstd.COMPRESSION_LEVEL_DEFAULT
    return None


def module_name_from_path(rel_path: str, prefix: str) -> tuple[str, bool]:
    """(dotted_module_name, is_package) from a path-relative entry, or
    ('', False) if the file isn't a Python module."""
    if not is_python_file(rel_path):
        return "", False
    stem = rel_path[:-3]  # strip .py
    parts = stem.split(os.sep)
    if parts[-1] == "__init__":
        is_package = True
        parts = parts[:-1]
    else:
        is_package = False
    if prefix:
        full_parts = prefix.split(".") + parts
    else:
        full_parts = parts
    if not full_parts:
        return "", False
    return ".".join(full_parts), is_package


def payload_record(data: bytes) -> bytes:
    """Keep wheel records local to the payload's package root.

    pip's external console-script records hash shebangs containing its venv
    path. Those files never enter the payload; retaining their installation
    records would make the blob depend on that otherwise irrelevant path.
    """
    source = io.StringIO(data.decode("utf-8"), newline="")
    output = io.StringIO(newline="")
    csv.writer(output).writerows(
        row
        for row in csv.reader(source)
        if not row[0].startswith("../") and not os.path.isabs(row[0])
    )
    return output.getvalue().encode("utf-8")


def collect_files(
    root: str, prefix: str
) -> Iterator[tuple[str, str, int, bytes]]:
    """Yield (storage_key, abs_path, flags, payload_bytes) tuples.

    storage_key is what we hash and look up in the finder.
    """
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d
            for d in dirnames
            if not is_excluded_dir(d) and not d.startswith(".")
        )
        for fn in sorted(filenames):
            abs_path = os.path.join(dirpath, fn)
            rel_path = os.path.relpath(abs_path, root)
            if is_python_file(rel_path):
                modname, is_pkg = module_name_from_path(rel_path, prefix)
                if not modname:
                    continue
                try:
                    with open(abs_path, "rb") as f:
                        src = f.read()
                    # Keep tracebacks useful without embedding the build tree.
                    filename = rel_path.replace(os.sep, "/")
                    if prefix:
                        filename = f"{prefix.replace('.', '/')}/{filename}"
                    code = compile(
                        src, filename, "exec", dont_inherit=True, optimize=2
                    )
                    payload = marshal.dumps(code)
                except SyntaxError:
                    sys.stderr.write(f"  skip syntax error: {abs_path}\n")
                    continue
                flags = FLAG_BYTECODE | (FLAG_PACKAGE if is_pkg else 0)
                yield modname, abs_path, flags, payload
            elif is_data_file(rel_path):
                key = rel_path.replace(os.sep, "/")
                if prefix:
                    key = f"{prefix}/{key}"
                with open(abs_path, "rb") as f:
                    payload = f.read()
                if fn == "RECORD" and dirpath.endswith(".dist-info"):
                    payload = payload_record(payload)
                yield key, abs_path, FLAG_RESOURCE, payload


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    out_path = sys.argv[1]
    inputs = sys.argv[2:]

    entries: list[EntryInput] = []
    seen_keys: set[str] = set()
    for spec in inputs:
        if ":" in spec:
            root, prefix = spec.rsplit(":", 1)
        else:
            root, prefix = spec, ""
        if not os.path.isdir(root):
            print(f"ERROR: not a directory: {root}", file=sys.stderr)
            sys.exit(1)
        n_before = len(entries)
        for key, _path, flags, payload in collect_files(root, prefix):
            if key in seen_keys:
                continue  # first occurrence wins
            seen_keys.add(key)
            entries.append(
                EntryInput(key.encode("utf-8"), flags, payload, None)
            )
        print(
            f"  {root} (prefix={prefix!r}): {len(entries) - n_before} entries",
            file=sys.stderr,
        )

    print(f"total entries: {len(entries)}", file=sys.stderr)
    print(
        "zstd-compressing .rst and autocomplete index resources"
        if zstd is not None
        else "storing resources raw (no stdlib compression.zstd)",
        file=sys.stderr,
    )

    # Encode each unique primary payload. Compression policy:
    #   - Code (FLAG_BYTECODE): raw, zero-copy at import.
    #   - botocore service models: raw. Hot-path (existence check on every
    #     `list_available_services` iteration).
    #   - RST resources: zstd-compressed. Cold path for help/examples.
    #   - Autocomplete index entries: zstd-compressed at a higher level.
    #   - Other resources (awscli/data, PEMs, dist-info text): raw.
    primary_data: dict[int, StoredData] = {}
    payload_blobs: list[bytes] = []
    cursor = 0
    raw_code_bytes = 0
    raw_model_bytes = 0
    raw_other_resource_bytes = 0
    compressed_resource_count = 0
    compressed_resource_bytes = 0
    compressed_resource_raw_bytes = 0
    for orig_idx, entry in enumerate(entries):
        key_bytes = entry.key
        flags = entry.flags
        payload = entry.payload
        alias_of = entry.alias_of
        if alias_of is not None:
            continue  # alias: shares the primary's data
        key = key_bytes.decode("utf-8")
        is_model = (flags & FLAG_RESOURCE) and is_model_file(key)
        zstd_level = (
            resource_zstd_level(key) if flags & FLAG_RESOURCE else None
        )
        if (flags & FLAG_BYTECODE) or is_model:
            stored = payload
            is_compressed = False
            if flags & FLAG_BYTECODE:
                raw_code_bytes += len(stored)
            else:
                raw_model_bytes += len(stored)
        elif zstd_level is not None:
            stored = zstd.compress(payload, level=zstd_level)
            is_compressed = True
            compressed_resource_count += 1
            compressed_resource_bytes += len(stored)
            compressed_resource_raw_bytes += len(payload)
        else:
            stored = payload
            is_compressed = False
            raw_other_resource_bytes += len(stored)
        primary_data[orig_idx] = StoredData(
            require_u32("data offset", cursor),
            require_u32("stored length", len(stored)),
            require_u32("raw length", len(payload)),
            is_compressed,
        )
        payload_blobs.append(stored)
        cursor += len(stored)

    indexed = list(enumerate(entries))
    name_ordered = sorted(indexed, key=lambda kv: kv[1].key)

    # Build string table in name order so prefix walks read nearby names.
    string_table = bytearray()
    name_offsets_by_orig: dict[int, int] = {}
    for orig_idx, entry in name_ordered:
        name_offsets_by_orig[orig_idx] = require_u32(
            "name offset",
            len(string_table),
        )
        string_table.extend(entry.key)

    total_data_size = cursor
    print(
        f"strings:                  {len(string_table):>12,}", file=sys.stderr
    )
    print(
        f"unique payloads: {len(payload_blobs)} (entries: {len(entries)})",
        file=sys.stderr,
    )
    print(f"  raw code bytes:         {raw_code_bytes:>12,}", file=sys.stderr)
    print(f"  raw model bytes:        {raw_model_bytes:>12,}", file=sys.stderr)
    print(
        f"  raw other resources:    {raw_other_resource_bytes:>12,}",
        file=sys.stderr,
    )
    print(
        f"  compressed resources:   {compressed_resource_count:>12,}",
        file=sys.stderr,
    )
    print(
        f"  compressed stored:      {compressed_resource_bytes:>12,}",
        file=sys.stderr,
    )
    print(
        f"  compressed raw:         {compressed_resource_raw_bytes:>12,}",
        file=sys.stderr,
    )
    print(f"  total data section:     {total_data_size:>12,}", file=sys.stderr)

    index_width = index_width_for_entry_count(len(entries))
    control_bytes, lookup_index_bytes, lookup_metrics = build_lookup(
        name_ordered,
        index_width,
    )

    entry_meta_bytes = bytearray()
    for orig_idx, entry in name_ordered:
        primary_idx = (
            entry.alias_of if entry.alias_of is not None else orig_idx
        )
        data = primary_data[primary_idx]
        flags_out = entry.flags | (
            FLAG_COMPRESSED if data.is_compressed else 0
        )
        entry_meta_bytes.extend(
            struct.pack(
                ENTRY_META_FMT,
                name_offsets_by_orig[orig_idx],
                require_u32("name length", len(entry.key)),
                data.offset,
                data.stored_len,
                data.raw_len,
                flags_out,
                0,  # _reserved
            )
        )

    control_offset = HEADER_SIZE
    index_offset = control_offset + len(control_bytes)
    entry_meta_offset = index_offset + len(lookup_index_bytes)
    string_table_offset = entry_meta_offset + len(entry_meta_bytes)
    data_offset = string_table_offset + len(string_table)

    header = struct.pack(
        HEADER_FMT,
        MAGIC,
        require_u32("entry count", len(entries)),
        require_u32("bucket count", lookup_metrics.bucket_count),
        0,
        lookup_metrics.index_width,
        control_offset,
        index_offset,
        entry_meta_offset,
        string_table_offset,
        data_offset,
        0,
    )

    total = data_offset + total_data_size
    avg_probe_groups = (
        lookup_metrics.total_probe_groups / len(entries) if entries else 0
    )
    print(
        f"lookup buckets:           {lookup_metrics.bucket_count:>12,}",
        file=sys.stderr,
    )
    print(
        "lookup load:              "
        f"{len(entries) / lookup_metrics.bucket_count:>11.1%}",
        file=sys.stderr,
    )
    print(
        f"lookup index width:       {lookup_metrics.index_width:>12}",
        file=sys.stderr,
    )
    print(
        f"lookup control bytes:     {len(control_bytes):>12,}", file=sys.stderr
    )
    print(
        f"lookup index bytes:       {len(lookup_index_bytes):>12,}",
        file=sys.stderr,
    )
    print(
        f"max probe groups:         {lookup_metrics.max_probe_groups:>12,}",
        file=sys.stderr,
    )
    print(
        f"avg probe groups:         {avg_probe_groups:>12.3f}", file=sys.stderr
    )
    print(
        "candidate name checks:    "
        f"{lookup_metrics.candidate_name_checks:>12,}",
        file=sys.stderr,
    )
    print(f"output blob:              {total:>12,}", file=sys.stderr)

    with open(out_path, "wb") as f:
        f.write(header)
        f.write(control_bytes)
        f.write(lookup_index_bytes)
        f.write(entry_meta_bytes)
        f.write(string_table)
        for blob in payload_blobs:
            f.write(blob)
    print(f"wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
