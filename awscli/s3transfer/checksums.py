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

from copy import copy


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
