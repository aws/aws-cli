import base64
from functools import cached_property

from botocore.httpchecksum import (
    CrtCrc32cChecksum,
    CrtCrc32Checksum,
    CrtCrc64NvmeChecksum,
)


class StreamingChecksumBody:
    def __init__(self, stream, starting_index, checksum_validator):
        self._stream = stream
        self._starting_index = starting_index
        self._checksum = _CRC_CHECKSUM_CLS[
            checksum_validator.checksum_algorithm
        ]()
        self._checksum_validator = checksum_validator

    def read(self, *args, **kwargs):
        value = self._stream.read(*args, **kwargs)
        self._checksum.update(value)
        if not value:
            self._checksum_validator.set_part_checksums(
                self._starting_index, self._checksum.int_crc
            )
        return value


class ChecksumValidator:
    def __init__(self, stored_checksum, content_length):
        self.checksum_algorithm = list(stored_checksum.keys())[0]
        self._checksum_value = stored_checksum[self.checksum_algorithm]
        self._combine_function = _CRC_CHECKSUM_TO_COMBINE_FUNCTION[
            self.checksum_algorithm
        ]
        self._part_checksums = None
        self._calculated_checksum = None
        self._content_length = content_length

    @cached_property
    def calculated_checksum(self):
        if self._calculated_checksum is None:
            self._combine_part_checksums()
        return self._calculated_checksum

    def set_part_checksums(self, offset, checksum):
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
        if not self._checksum_value:
            return
        if self.calculated_checksum != self._checksum_value:
            raise Exception(
                f"stored: {self._checksum_value} != calculated: {self.calculated_checksum}"
            )


def combine_crc32(crc1, crc2, len2):
    """
    Combine two CRC32 checksums computed with binascii.crc32.

    This implementation follows the algorithm used in zlib's crc32_combine.

    Args:
        crc1: CRC32 checksum of the first data block (from binascii.crc32)
        crc2: CRC32 checksum of the second data block (from binascii.crc32)
        len2: Length in bytes of the second data block

    Returns:
        Combined CRC32 checksum as if the two blocks were concatenated
    """

    # CRC-32 polynomial in reversed bit order
    POLY = 0xEDB88320

    def gf2_matrix_times(mat, vec):
        """Multiply matrix by vector over GF(2)"""
        result = 0
        for i in range(32):
            if vec & (1 << i):
                result ^= mat[i]
        return result & 0xFFFFFFFF

    def gf2_matrix_square(square, mat):
        """Square matrix over GF(2)"""
        for n in range(32):
            square[n] = gf2_matrix_times(mat, mat[n])

    # Create initial CRC matrix for 1 bit
    odd = [0] * 32
    even = [0] * 32

    # Build odd matrix (for 1 bit shift)
    odd[0] = POLY
    for n in range(1, 32):
        odd[n] = 1 << (n - 1)

    # Square to get even matrix (for 2 bit shift), then keep squaring
    gf2_matrix_square(even, odd)
    gf2_matrix_square(odd, even)

    # Process len2 bytes (8 * len2 bits)
    length = len2

    # Process chunks of 3 bits at a time (since we have matrices for 4 and 8 bit shifts)
    while length != 0:
        # Square matrices to advance to next power of 2
        gf2_matrix_square(even, odd)
        if length & 1:
            crc1 = gf2_matrix_times(even, crc1)
        length >>= 1

        if length == 0:
            break

        gf2_matrix_square(odd, even)
        if length & 1:
            crc1 = gf2_matrix_times(odd, crc1)
        length >>= 1

    # XOR the two CRCs
    crc1 ^= crc2

    return crc1 & 0xFFFFFFFF


_CRC_CHECKSUM_TO_COMBINE_FUNCTION = {
    "ChecksumCRC64NVME": None,
    "ChecksumCRC32C": None,
    "ChecksumCRC32": combine_crc32,
}


_CRC_CHECKSUM_CLS = {
    "ChecksumCRC64NVME": CrtCrc64NvmeChecksum,
    "ChecksumCRC32C": CrtCrc32cChecksum,
    "ChecksumCRC32": CrtCrc32Checksum,
}


CRC_CHECKSUMS = _CRC_CHECKSUM_TO_COMBINE_FUNCTION.keys()
