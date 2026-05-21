# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import base64
import logging
from collections import namedtuple

from awscrt import checksums as crt_checksums
from botocore.httpchecksum import _CHECKSUM_CLS
from s3transfer.exceptions import S3DownloadChecksumError

logger = logging.getLogger(__name__)


CrcCombineInfo = namedtuple('CrcCombineInfo', ['combine_fn', 'byte_length'])


PartChecksum = namedtuple('PartChecksum', ['crc_int', 'data_length'])


FullObjectChecksum = namedtuple(
    'FullObjectChecksum', ['algorithm', 'expected_b64']
)


_CRC_COMBINE_FUNCTIONS = {
    'crc32': CrcCombineInfo(crt_checksums.combine_crc32, 4),
    'crc32c': CrcCombineInfo(crt_checksums.combine_crc32c, 4),
    'crc64nvme': CrcCombineInfo(crt_checksums.combine_crc64nvme, 8),
}


_CHECKSUM_KEY_TO_ALGORITHM = {
    'ChecksumCRC32': 'crc32',
    'ChecksumCRC32C': 'crc32c',
    'ChecksumCRC64NVME': 'crc64nvme',
}


def resolve_full_object_checksum(response):
    if response.get('ChecksumType', '').upper() != 'FULL_OBJECT':
        return None
    for key, algorithm in _CHECKSUM_KEY_TO_ALGORITHM.items():
        value = response.get(key)
        if value:
            return FullObjectChecksum(algorithm=algorithm, expected_b64=value)
    return None


def create_checksum_for_algorithm(algorithm):
    if checksum_cls := _CHECKSUM_CLS.get(algorithm):
        return checksum_cls()
    return None


class FullObjectChecksumCombiner:
    def __init__(self, algorithm, num_parts, expected_b64=None):
        self._algorithm = algorithm
        self._expected_b64 = expected_b64
        self._num_parts = num_parts
        self._combine_info = _CRC_COMBINE_FUNCTIONS[algorithm]
        self._parts = {}
        self._combined_bytes = None

    @property
    def algorithm(self):
        return self._algorithm

    def register_part(self, part_index, checksum, data_length):
        crc_int = int.from_bytes(checksum.digest(), byteorder='big')
        self._parts[part_index] = PartChecksum(crc_int, data_length)

    def combine_and_validate(self):
        if len(self._parts) != self._num_parts:
            logger.debug(
                f'Skipping full object checksum validation. '
                f'Expected {self._num_parts} parts but only '
                f'{len(self._parts)} were registered.'
            )
            return
        combined_bytes = self._get_combined_bytes()
        combined_b64 = base64.b64encode(combined_bytes).decode('ascii')
        expected_bytes = base64.b64decode(self._expected_b64)
        if combined_bytes != expected_bytes:
            raise S3DownloadChecksumError(
                f'Expected full object checksum '
                f'({self._algorithm}) {self._expected_b64} did not match '
                f'combined checksum: {combined_b64}'
            )
        logger.debug(
            f'Full object {self._algorithm} checksum validated: {combined_b64}'
        )

    @property
    def combined_b64(self):
        combined_bytes = self._get_combined_bytes()
        return base64.b64encode(combined_bytes).decode('ascii')

    def _get_combined_bytes(self):
        if self._combined_bytes is not None:
            return self._combined_bytes
        crc = self._parts[0].crc_int
        for i in range(1, self._num_parts):
            part = self._parts[i]
            crc = self._combine_info.combine_fn(
                crc, part.crc_int, part.data_length
            )
        self._combined_bytes = crc.to_bytes(
            self._combine_info.byte_length, byteorder='big'
        )
        return self._combined_bytes
