# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import _awscrt


def crc32(input: bytes, previous_crc32: int = 0) -> int:
    """
    Perform a CRC32 (Ethernet, gzip) computation.

    If continuing to update a running CRC, pass its value into `previous_crc32`.
    Returns an unsigned 32-bit integer.
    """
    return _awscrt.checksums_crc32(input, previous_crc32)


def crc32c(input: bytes, previous_crc32c: int = 0) -> int:
    """
    Perform a Castagnoli CRC32c (iSCSI) computation.
    If continuing to update a running CRC, pass its value into `previous_crc32c`.
    Returns an unsigned 32-bit integer.
    """
    return _awscrt.checksums_crc32c(input, previous_crc32c)


def crc64nvme(input: bytes, previous_crc64nvme: int = 0) -> int:
    """
    Perform a CRC64 NVME computation.
    If continuing to update a running CRC, pass its value into `previous_crc64nvme`.
    Returns an unsigned 64-bit integer.
    """
    return _awscrt.checksums_crc64nvme(input, previous_crc64nvme)
