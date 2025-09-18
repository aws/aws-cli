from io import BytesIO

import pytest
from botocore.httpchecksum import CrtCrc32Checksum
from s3transfer.checksums import (
    FullObjectChecksum,
    PartStreamingChecksumBody,
    provide_checksum_to_meta,
)
from s3transfer.exceptions import S3ValidationError

from tests import mock


def read_from_stream(stream):
    data = b""
    val = stream.read()
    while val:
        data += val
        val = stream.read()
    return data


@pytest.fixture
def stream():
    return BytesIO(b'hello world')


@pytest.fixture
def mock_full_object_checksum():
    mock_full_object_checksum = mock.MagicMock(FullObjectChecksum)
    mock_full_object_checksum.checksum_algorithm = 'ChecksumCRC32'
    return mock_full_object_checksum


@pytest.fixture
def part_streaming_checksum_body(stream, mock_full_object_checksum):
    return PartStreamingChecksumBody(stream, 0, mock_full_object_checksum)


class TestPartStreamingChecksumBody:
    def test_basic_read(self, part_streaming_checksum_body):
        read_data = read_from_stream(part_streaming_checksum_body)
        assert read_data == b'hello world'

    def test_sets_part_checksum(
        self, stream, mock_full_object_checksum, part_streaming_checksum_body
    ):
        read_from_stream(part_streaming_checksum_body)
        mock_full_object_checksum.set_part_checksum.assert_called_with(
            0, 222957957
        )

    def test_reuses_checksum(self, stream, mock_full_object_checksum):
        mock_checksum = mock.MagicMock(CrtCrc32Checksum)
        mock_checksum.int_crc = 111111111
        stream.checksum = mock_checksum

        part_streaming_checksum_body = PartStreamingChecksumBody(
            stream, 0, mock_full_object_checksum
        )
        read_from_stream(part_streaming_checksum_body)
        mock_full_object_checksum.set_part_checksum.assert_called_with(
            0, 111111111
        )


class TestFullObjectChecksum:
    def generate_part_checksum_bodies(self, n, full_object_checksum):
        parts = []
        for i in range(n):
            parts.append(
                PartStreamingChecksumBody(
                    BytesIO(f"Part{i}".encode()),
                    i * 5,
                    full_object_checksum,
                )
            )
        return parts

    @pytest.mark.parametrize(
        "n_parts,expected", [(2, "Fd9B+g=="), (10, "eywYgg==")]
    )
    def test_calculated_checksum(self, n_parts, expected):
        full_object_checksum = FullObjectChecksum("ChecksumCRC32", 5 * n_parts)
        parts = self.generate_part_checksum_bodies(
            n_parts, full_object_checksum
        )
        for part in parts:
            read_from_stream(part)
        assert full_object_checksum.calculated_checksum == expected

    def test_checksum_mismatch_raises(self):
        n_parts = 10
        full_object_checksum = FullObjectChecksum("ChecksumCRC32", 5 * n_parts)
        parts = self.generate_part_checksum_bodies(
            n_parts, full_object_checksum
        )
        for part in parts:
            read_from_stream(part)
        full_object_checksum.set_stored_checksum('foobar')
        with pytest.raises(S3ValidationError) as exc_info:
            full_object_checksum.validate()
        assert "does not match stored checksum" in str(exc_info.value)

    @pytest.mark.parametrize("content_length", [0, 49, 51])
    def test_wrong_content_length_raises(self, content_length):
        n_parts = 10
        # Note that total content length should be `50`.
        full_object_checksum = FullObjectChecksum(
            "ChecksumCRC32", content_length
        )
        parts = self.generate_part_checksum_bodies(
            n_parts, full_object_checksum
        )
        for part in parts:
            read_from_stream(part)
        full_object_checksum.set_stored_checksum("eywYgg==")
        with pytest.raises(S3ValidationError) as exc_info:
            full_object_checksum.validate()
        assert "does not match stored checksum" in str(exc_info.value)


class TestProvideChecksumToMeta:
    def test_provides_checksum_to_meta(self):
        response = {
            "ChecksumType": "FULL_OBJECT",
            "ChecksumCRC32": "foobar",
        }
        mock_transfer_meta = mock.Mock()
        provide_checksum_to_meta(response, mock_transfer_meta)
        mock_transfer_meta.provide_checksum_algorithm.assert_called_with(
            "ChecksumCRC32"
        )
        mock_transfer_meta.provide_stored_checksum.assert_called_with("foobar")

    def test_provides_none_if_composite(self):
        response = {
            "ChecksumType": "COMPOSITE",
            "ChecksumCRC32": "foobar",
        }
        mock_transfer_meta = mock.Mock()
        provide_checksum_to_meta(response, mock_transfer_meta)
        mock_transfer_meta.provide_checksum_algorithm.assert_called_with(None)
        mock_transfer_meta.provide_stored_checksum.assert_called_with(None)

    def test_provides_none_if_not_crc(self):
        response = {
            "ChecksumType": "FULL_OBJECT",
            "ChecksumFooBar": "foobar",
        }
        mock_transfer_meta = mock.Mock()
        provide_checksum_to_meta(response, mock_transfer_meta)
        mock_transfer_meta.provide_checksum_algorithm.assert_called_with(None)
        mock_transfer_meta.provide_stored_checksum.assert_called_with(None)
