# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import gzip
import io
import sys

import pytest

import botocore
from botocore.compress import COMPRESSION_MAPPING, maybe_compress_request
from botocore.config import Config
from tests import mock


def _make_op(
    request_compression=None,
    has_streaming_input=False,
    streaming_metadata=None,
):
    op = mock.Mock()
    op.request_compression = request_compression
    op.has_streaming_input = has_streaming_input
    if streaming_metadata is not None:
        streaming_shape = mock.Mock()
        streaming_shape.metadata = streaming_metadata
        op.get_streaming_input.return_value = streaming_shape
    return op


OP_NO_COMPRESSION = _make_op()
OP_WITH_COMPRESSION = _make_op({'encodings': ['gzip']})
OP_UNKNOWN_COMPRESSION = _make_op({'encodings': ['foo']})
OP_MULTIPLE_COMPRESSIONS = _make_op({'encodings': ['gzip', 'foo']})
STREAMING_OP_WITH_COMPRESSION = _make_op(
    {'encodings': ['gzip']},
    True,
    {},
)
STREAMING_OP_WITH_COMPRESSION_REQUIRES_LENGTH = _make_op(
    {'encodings': ['gzip']},
    True,
    {'requiresLength': True},
)


REQUEST_BODY = (
    b'Action=PutMetricData&Version=2010-08-01&Namespace=Namespace'
    b'&MetricData.member.1.MetricName=metric&MetricData.member.1.Unit=Bytes'
    b'&MetricData.member.1.Value=128'
)
REQUEST_BODY_COMPRESSED = (
    b'\x1f\x8b\x08\x00\x01\x00\x00\x00\x02\xffsL.\xc9\xcc\xcf\xb3\r(-\xf1M-)'
    b'\xcaLvI,IT\x0bK-*\x06\x89\x1a\x19\x18\x1a\xe8\x1aX\xe8\x1a\x18\xaa\xf9%'
    b'\xe6\xa6\x16\x17$&\xa7\xda\xc2Yj\x08\x1dz\xb9\xa9\xb9I\xa9Ez\x86z\x101\x90'
    b'\x1a\xdb\\0\x13\xab\xaa\xd0\xbc\xcc\x12[\xa7\xca\x92\xd4b\xac\xd2a\x899\xa5'
    b'\xa9\xb6\x86F\x16\x00\x1e\xdd\t\xfd\x9e\x00\x00\x00'
)


COMPRESSION_CONFIG_128_BYTES = Config(
    disable_request_compression=False,
    request_min_compression_size_bytes=128,
)
COMPRESSION_CONFIG_1_BYTE = Config(
    disable_request_compression=False,
    request_min_compression_size_bytes=1,
)


class NonSeekableStream:
    def __init__(self, buffer):
        self._buffer = buffer

    def read(self, size=None):
        return self._buffer.read(size)


def _request_dict(body=REQUEST_BODY, headers=None):
    if headers is None:
        headers = {}

    return {
        'body': body,
        'headers': headers,
    }


def request_dict_non_seekable_text_stream():
    stream = NonSeekableStream(io.StringIO(REQUEST_BODY.decode('utf-8')))
    return _request_dict(stream)


def request_dict_non_seekable_bytes_stream():
    return _request_dict(NonSeekableStream(io.BytesIO(REQUEST_BODY)))


class StaticGzipFile(gzip.GzipFile):
    def __init__(self, *args, **kwargs):
        kwargs['mtime'] = 1
        super().__init__(*args, **kwargs)


def static_compress(*args, **kwargs):
    kwargs['mtime'] = 1
    return gzip.compress(*args, **kwargs)


def _bad_compression(body):
    raise ValueError('Reached unintended compression algorithm "foo"')


MOCK_COMPRESSION = {'foo': _bad_compression}
MOCK_COMPRESSION.update(COMPRESSION_MAPPING)


def _assert_compression_body(compressed_body, expected_body):
    data = compressed_body
    if hasattr(compressed_body, 'read'):
        data = compressed_body.read()
    assert data == expected_body


def _assert_compression_header(headers, encoding='gzip'):
    assert 'Content-Encoding' in headers
    assert encoding in headers['Content-Encoding']


def assert_request_compressed(request_dict, expected_body):
    _assert_compression_body(request_dict['body'], expected_body)
    _assert_compression_header(request_dict['headers'])


@pytest.mark.parametrize(
    'request_dict, operation_model',
    [
        (
            _request_dict(),
            OP_WITH_COMPRESSION,
        ),
        (
            _request_dict(),
            OP_MULTIPLE_COMPRESSIONS,
        ),
        (
            _request_dict(),
            STREAMING_OP_WITH_COMPRESSION,
        ),
        (
            _request_dict(bytearray(REQUEST_BODY)),
            OP_WITH_COMPRESSION,
        ),
        (
            _request_dict(headers={'Content-Encoding': 'identity'}),
            OP_WITH_COMPRESSION,
        ),
        (
            _request_dict(REQUEST_BODY.decode('utf-8')),
            OP_WITH_COMPRESSION,
        ),
        (
            _request_dict(io.BytesIO(REQUEST_BODY)),
            OP_WITH_COMPRESSION,
        ),
        (
            _request_dict(io.StringIO(REQUEST_BODY.decode('utf-8'))),
            OP_WITH_COMPRESSION,
        ),
        (
            request_dict_non_seekable_bytes_stream(),
            STREAMING_OP_WITH_COMPRESSION,
        ),
        (
            request_dict_non_seekable_text_stream(),
            STREAMING_OP_WITH_COMPRESSION,
        ),
    ],
)
@mock.patch.object(botocore.compress, 'GzipFile', StaticGzipFile)
@mock.patch.object(botocore.compress, 'gzip_compress', static_compress)
@pytest.mark.skipif(
    sys.version_info < (3, 8), reason='requires python3.8 or higher'
)
def test_compression(request_dict, operation_model):
    maybe_compress_request(
        COMPRESSION_CONFIG_128_BYTES, request_dict, operation_model
    )
    assert_request_compressed(request_dict, REQUEST_BODY_COMPRESSED)


@pytest.mark.parametrize(
    'config, request_dict, operation_model',
    [
        (
            Config(
                disable_request_compression=True,
                request_min_compression_size_bytes=1,
            ),
            _request_dict(),
            OP_WITH_COMPRESSION,
        ),
        (
            Config(
                disable_request_compression=False,
                request_min_compression_size_bytes=256,
            ),
            _request_dict(),
            OP_WITH_COMPRESSION,
        ),
        (
            Config(
                disable_request_compression=False,
                request_min_compression_size_bytes=1,
                signature_version='v2',
            ),
            _request_dict(),
            OP_WITH_COMPRESSION,
        ),
        (
            COMPRESSION_CONFIG_128_BYTES,
            _request_dict(),
            STREAMING_OP_WITH_COMPRESSION_REQUIRES_LENGTH,
        ),
        (
            COMPRESSION_CONFIG_128_BYTES,
            _request_dict(),
            OP_NO_COMPRESSION,
        ),
        (
            COMPRESSION_CONFIG_128_BYTES,
            _request_dict(),
            OP_UNKNOWN_COMPRESSION,
        ),
        (
            COMPRESSION_CONFIG_128_BYTES,
            _request_dict(headers={'Content-Encoding': 'identity'}),
            OP_UNKNOWN_COMPRESSION,
        ),
        (
            COMPRESSION_CONFIG_128_BYTES,
            request_dict_non_seekable_bytes_stream(),
            OP_WITH_COMPRESSION,
        ),
    ],
)
def test_no_compression(config, request_dict, operation_model):
    ce_header = request_dict['headers'].get('Content-Encoding')
    original_body = request_dict['body']
    maybe_compress_request(config, request_dict, operation_model)
    assert request_dict['body'] == original_body
    assert ce_header == request_dict['headers'].get('Content-Encoding')


@pytest.mark.parametrize(
    'operation_model, expected_body',
    [
        (
            OP_WITH_COMPRESSION,
            (
                b'\x1f\x8b\x08\x00\x01\x00\x00\x00\x02\xffK\xcb'
                b'\xcf\xb7MJ,\x02\x00v\x8e5\x1c\x07\x00\x00\x00'
            ),
        ),
        (OP_NO_COMPRESSION, {'foo': 'bar'}),
    ],
)
@mock.patch.object(botocore.compress, 'gzip_compress', static_compress)
@pytest.mark.skipif(
    sys.version_info < (3, 8), reason='requires python3.8 or higher'
)
def test_dict_compression(operation_model, expected_body):
    request_dict = _request_dict({'foo': 'bar'})
    maybe_compress_request(
        COMPRESSION_CONFIG_1_BYTE, request_dict, operation_model
    )
    body = request_dict['body']
    assert body == expected_body


@pytest.mark.parametrize('body', [1, object(), True, 1.0])
def test_maybe_compress_bad_types(body):
    request_dict = _request_dict(body)
    maybe_compress_request(
        COMPRESSION_CONFIG_1_BYTE, request_dict, OP_WITH_COMPRESSION
    )
    assert request_dict['body'] == body


@mock.patch.object(botocore.compress, 'GzipFile', StaticGzipFile)
def test_body_streams_position_reset():
    request_dict = _request_dict(io.BytesIO(REQUEST_BODY))
    maybe_compress_request(
        COMPRESSION_CONFIG_128_BYTES,
        request_dict,
        OP_WITH_COMPRESSION,
    )
    assert request_dict['body'].tell() == 0
    assert_request_compressed(request_dict, REQUEST_BODY_COMPRESSED)


@mock.patch.object(botocore.compress, 'gzip_compress', static_compress)
@mock.patch.object(botocore.compress, 'COMPRESSION_MAPPING', MOCK_COMPRESSION)
@pytest.mark.skipif(
    sys.version_info < (3, 8), reason='requires python3.8 or higher'
)
def test_only_compress_once():
    request_dict = _request_dict()
    maybe_compress_request(
        COMPRESSION_CONFIG_128_BYTES,
        request_dict,
        OP_MULTIPLE_COMPRESSIONS,
    )
    assert_request_compressed(request_dict, REQUEST_BODY_COMPRESSED)
