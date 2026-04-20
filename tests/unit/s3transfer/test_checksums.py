# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import base64

import pytest
from awscrt import checksums as crt_checksums
from s3transfer.checksums import (
    FullObjectChecksum,
    FullObjectChecksumCombiner,
    create_checksum_for_algorithm,
    resolve_full_object_checksum,
)
from s3transfer.exceptions import S3DownloadChecksumError


def _compute_expected_b64(data, algorithm):
    crc_fns = {
        'crc32': (crt_checksums.crc32, 4),
        'crc32c': (crt_checksums.crc32c, 4),
        'crc64nvme': (crt_checksums.crc64nvme, 8),
    }
    fn, byte_length = crc_fns[algorithm]
    crc = fn(data)
    return base64.b64encode(crc.to_bytes(byte_length, byteorder='big')).decode(
        'ascii'
    )


def _register_parts(combiner, parts, algorithm):
    for i, part_data in enumerate(parts):
        checksum = create_checksum_for_algorithm(algorithm)
        checksum.update(part_data)
        combiner.register_part(i, checksum, len(part_data))


class TestResolveFullObjectChecksum:
    def test_full_object_crc32(self):
        response = {
            'ChecksumType': 'FULL_OBJECT',
            'ChecksumCRC32': 'abc123==',
        }
        result = resolve_full_object_checksum(response)
        assert result == FullObjectChecksum(
            algorithm='crc32', expected_b64='abc123=='
        )

    def test_full_object_crc32c(self):
        response = {
            'ChecksumType': 'FULL_OBJECT',
            'ChecksumCRC32C': 'xyz789==',
        }
        result = resolve_full_object_checksum(response)
        assert result == FullObjectChecksum(
            algorithm='crc32c', expected_b64='xyz789=='
        )

    def test_full_object_crc64nvme(self):
        response = {
            'ChecksumType': 'FULL_OBJECT',
            'ChecksumCRC64NVME': 'nvme64==',
        }
        result = resolve_full_object_checksum(response)
        assert result == FullObjectChecksum(
            algorithm='crc64nvme', expected_b64='nvme64=='
        )

    def test_missing_checksum_type(self):
        assert resolve_full_object_checksum({}) is None

    def test_composite_checksum(self):
        response = {
            'ChecksumType': 'COMPOSITE',
            'ChecksumCRC32': 'abc123==',
        }
        assert resolve_full_object_checksum(response) is None

    def test_full_object_sha_only(self):
        response = {
            'ChecksumType': 'FULL_OBJECT',
            'ChecksumSHA256': 'sha256value==',
        }
        assert resolve_full_object_checksum(response) is None

    def test_case_insensitive_checksum_type(self):
        response = {
            'ChecksumType': 'full_object',
            'ChecksumCRC32': 'abc123==',
        }
        result = resolve_full_object_checksum(response)
        assert result is not None
        assert result.algorithm == 'crc32'


class TestCreateChecksumForAlgorithm:
    @pytest.mark.parametrize('algorithm', ['crc32', 'crc32c', 'crc64nvme'])
    def test_known_algorithm(self, algorithm):
        checksum = create_checksum_for_algorithm(algorithm)
        assert checksum is not None
        assert hasattr(checksum, 'update')
        assert hasattr(checksum, 'digest')

    def test_unknown_algorithm(self):
        assert create_checksum_for_algorithm('unknown') is None


class TestFullObjectChecksumCombiner:
    def test_combine_and_validate_crc32(self):
        data = b'hello world, this is a test of CRC combining'
        parts = [data[:15], data[15:30], data[30:]]
        expected = _compute_expected_b64(data, 'crc32')

        combiner = FullObjectChecksumCombiner(
            'crc32', len(parts), expected_b64=expected
        )
        _register_parts(combiner, parts, 'crc32')
        combiner.combine_and_validate()

    def test_combine_and_validate_crc32c(self):
        data = b'testing crc32c combining across parts'
        parts = [data[:10], data[10:]]
        expected = _compute_expected_b64(data, 'crc32c')

        combiner = FullObjectChecksumCombiner(
            'crc32c', len(parts), expected_b64=expected
        )
        _register_parts(combiner, parts, 'crc32c')
        combiner.combine_and_validate()

    def test_combine_and_validate_crc64nvme(self):
        data = b'testing crc64nvme combining across parts'
        parts = [data[:10], data[10:20], data[20:]]
        expected = _compute_expected_b64(data, 'crc64nvme')

        combiner = FullObjectChecksumCombiner(
            'crc64nvme', len(parts), expected_b64=expected
        )
        _register_parts(combiner, parts, 'crc64nvme')
        combiner.combine_and_validate()

    def test_checksum_mismatch_raises(self):
        combiner = FullObjectChecksumCombiner(
            'crc32', 1, expected_b64='AAAABB=='
        )
        checksum = create_checksum_for_algorithm('crc32')
        checksum.update(b'some data')
        combiner.register_part(0, checksum, 9)

        with pytest.raises(S3DownloadChecksumError, match='did not match'):
            combiner.combine_and_validate()

    def test_combined_b64_without_expected(self):
        data = b'upload use case'
        parts = [data[:5], data[5:]]
        expected = _compute_expected_b64(data, 'crc32')

        combiner = FullObjectChecksumCombiner('crc32', len(parts))
        _register_parts(combiner, parts, 'crc32')
        assert combiner.combined_b64 == expected

    def test_combined_bytes_are_cached(self):
        combiner = FullObjectChecksumCombiner('crc32', 1)
        checksum = create_checksum_for_algorithm('crc32')
        checksum.update(b'cache test')
        combiner.register_part(0, checksum, 10)

        assert combiner.combined_b64 == combiner.combined_b64

    def test_chunked_update_matches_single_update(self):
        data = b'streaming chunk test data for verification'
        expected = _compute_expected_b64(data, 'crc32')

        combiner = FullObjectChecksumCombiner(
            'crc32', 1, expected_b64=expected
        )
        checksum = create_checksum_for_algorithm('crc32')
        length = 0
        for i in range(0, len(data), 5):
            chunk = data[i : i + 5]
            checksum.update(chunk)
            length += len(chunk)
        combiner.register_part(0, checksum, length)
        combiner.combine_and_validate()
