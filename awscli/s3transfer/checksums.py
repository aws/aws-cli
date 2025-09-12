# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""
NOTE: All classes and functions in this module are considered private and are
subject to abrupt breaking changes. Please do not use them directly.
"""

import base64
from copy import copy
from functools import cached_property

from botocore.httpchecksum import CrtCrc32cChecksum


class PartStreamingChecksumBody:
    def __init__(self, stream, starting_index, full_object_checksum):
        self._stream = stream
        self._starting_index = starting_index
        self._checksum = CRC_CHECKSUM_CLS[
            full_object_checksum.checksum_algorithm
        ]()
        self._full_object_checksum = full_object_checksum
        # If the underlying stream already has a checksum object
        # it's updating (eg `botocore.httpchecksum.StreamingChecksumBody`),
        # reuse its calculated value.
        self._reuse_checksum = hasattr(self._stream, 'checksum')

    def read(self, *args, **kwargs):
        value = self._stream.read(*args, **kwargs)
        if not self._reuse_checksum:
            self._checksum.update(value)
        if not value:
            self._set_part_checksum()
        return value

    def _set_part_checksum(self):
        if not self._reuse_checksum:
            value = self._checksum.int_crc
        else:
            value = self._stream.checksum.int_crc
        self._full_object_checksum.set_part_checksum(
            self._starting_index,
            value,
        )


class FullObjectChecksum:
    def __init__(self, checksum_algorithm, content_length):
        self.checksum_algorithm = checksum_algorithm
        self._content_length = content_length
        self._combine_function = _CRC_CHECKSUM_TO_COMBINE_FUNCTION[
            self.checksum_algorithm
        ]
        self._stored_checksum = None
        self._part_checksums = None
        self._calculated_checksum = None

    @cached_property
    def calculated_checksum(self):
        if self._calculated_checksum is None:
            self._combine_part_checksums()
        return self._calculated_checksum

    def set_stored_checksum(self, stored_checksum):
        self._stored_checksum = stored_checksum

    def set_part_checksum(self, offset, checksum):
        if self._part_checksums is None:
            self._part_checksums = {}
        self._part_checksums[offset] = checksum

    def _combine_part_checksums(self):
        if self._part_checksums is None:
            return
        sorted_keys = sorted(self._part_checksums.keys())
        combined = self._part_checksums[sorted_keys[0]]
        for i, offset in enumerate(sorted_keys[1:]):
            part_checksum = self._part_checksums[offset]
            if i + 1 == len(sorted_keys) - 1:
                next_offset = self._content_length
            else:
                next_offset = sorted_keys[i + 2]
            offset_len = next_offset - offset
            combined = self._combine_function(
                combined, part_checksum, offset_len
            )
        self._calculated_checksum = base64.b64encode(
            combined.to_bytes(4, byteorder='big')
        ).decode('ascii')

    def validate(self):
        if self.calculated_checksum != self._stored_checksum:
            raise ValueError(
                f"Calculated checksum {self.calculated_checksum} does not match "
                f"stored checksum {self._stored_checksum}"
            )


def provide_checksum_to_meta(response, transfer_meta):
    stored_checksum = None
    checksum_algorithm = None
    checksum_type = response.get("ChecksumType")
    if checksum_type and checksum_type == "FULL_OBJECT":
        for crc_checksum in _CRC_CHECKSUM_TO_COMBINE_FUNCTION.keys():
            if checksum_value := response.get(crc_checksum):
                stored_checksum = checksum_value
                checksum_algorithm = crc_checksum
                break
    transfer_meta.provide_checksum_algorithm(checksum_algorithm)
    transfer_meta.provide_stored_checksum(stored_checksum)


def combine_crc32(crc1, crc2, len2):
    """Combine two CRC32 values.

    :type crc1: int
    :param crc1: Current CRC32 integer value.

    :type crc2: int
    :param crc2: Second CRC32 integer value to combine.

    :type len2: int
    :param len2: Length of data that produced `crc2`.

    :rtype: int
    :returns: Combined CRC32 integer value.
    """
    _GF2_DIM = 32
    _CRC32_POLY = 0xEDB88320
    _MASK_32BIT = 0xFFFFFFFF

    def _gf2_matrix_times(mat, vec):
        res = 0
        idx = 0
        while vec != 0:
            if vec & 1:
                res ^= mat[idx]
            vec >>= 1
            idx += 1
        return res

    def _gf2_matrix_square(square, mat):
        res = copy(square)
        for n in range(_GF2_DIM):
            d = mat[n]
            res[n] = _gf2_matrix_times(mat, d)
        return res

    even = [0] * _GF2_DIM
    odd = [0] * _GF2_DIM

    if len2 <= 0:
        return crc1

    odd[0] = _CRC32_POLY
    row = 1
    for i in range(1, _GF2_DIM):
        odd[i] = row
        row <<= 1

    even = _gf2_matrix_square(even, odd)
    odd = _gf2_matrix_square(odd, even)

    while True:
        even = _gf2_matrix_square(even, odd)
        if len2 & 1:
            crc1 = _gf2_matrix_times(even, crc1)
        len2 >>= 1

        if len2 == 0:
            break

        odd = _gf2_matrix_square(odd, even)
        if len2 & 1:
            crc1 = _gf2_matrix_times(odd, crc1)
        len2 >>= 1

        if len2 == 0:
            break

    return (crc1 ^ crc2) & _MASK_32BIT


_CRC_CHECKSUM_TO_COMBINE_FUNCTION = {
    "ChecksumCRC32": combine_crc32,
}


CRC_CHECKSUM_CLS = {
    "ChecksumCRC32": CrtCrc32Checksum,
}
