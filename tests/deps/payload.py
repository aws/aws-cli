import struct
from pathlib import Path

try:
    from compression import zstd
except ImportError:
    zstd = None


def read_payload_entries(blob: Path) -> dict[str, tuple[int, bytes]]:
    # Decode the documented ZIPPY003 format without importing the packer.
    data = blob.read_bytes()
    header = struct.unpack_from("<8sIIIIQQQQQQ", data)
    assert header[0] == b"ZIPPY003"
    metadata_offset, names_offset, payload_offset = header[7:10]
    entries: dict[str, tuple[int, bytes]] = {}
    for index in range(header[1]):
        name_start, name_len, start, size, raw_size, flags, reserved = (
            struct.unpack_from("<IIIIIHH", data, metadata_offset + index * 24)
        )
        name = data[names_offset + name_start :][:name_len].decode()
        stored = data[payload_offset + start :][:size]
        assert reserved == 0
        if flags & 8:
            assert zstd is not None
            stored = zstd.decompress(stored)
        assert len(stored) == raw_size
        assert name not in entries
        entries[name] = (flags, stored)
    return entries
