# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import unittest
from io import BytesIO

from tests import requires_crt, mock

from botocore.awsrequest import AWSResponse
from botocore.model import OperationModel
from botocore.exceptions import AwsChunkedWrapperError
from botocore.exceptions import FlexibleChecksumError
from botocore.httpchecksum import AwsChunkedWrapper
from botocore.httpchecksum import StreamingChecksumBody
from botocore.httpchecksum import (
    Crc32Checksum,
    Sha256Checksum,
    Sha1Checksum,
    CrtCrc32Checksum,
    CrtCrc32cChecksum,
)
from botocore.httpchecksum import _CHECKSUM_CLS
from botocore.httpchecksum import (
    apply_request_checksum,
    resolve_request_checksum_algorithm,
    resolve_response_checksum_algorithms,
    handle_checksum_body,
)


class TestHttpChecksumHandlers(unittest.TestCase):
    def _make_operation_model(
        self,
        http_checksum=None,
        streaming_output=False,
        streaming_input=False,
        required=False,
    ):
        operation = mock.Mock(spec=OperationModel)
        if http_checksum is None:
            http_checksum = {}
        operation.http_checksum = http_checksum
        operation.http_checksum_required = required
        operation.has_streaming_output = streaming_output
        operation.has_streaming_input = streaming_input
        return operation

    def _make_http_response(
        self, body, headers=None, context=None, streaming=False,
    ):
        if context is None:
            context = {}

        if headers is None:
            headers = {}

        http_response = mock.Mock(spec=AWSResponse)
        http_response.raw = BytesIO(body)
        http_response.content = body
        http_response.status_code = 200
        http_response.headers = headers
        response_dict = {
            "headers": http_response.headers,
            "status_code": http_response.status_code,
            "context": context,
        }
        if streaming:
            response_dict["body"] = BytesIO(body)
        else:
            response_dict["body"] = body
        return http_response, response_dict

    def _build_request(self, body):
        request = {
            "headers": {},
            "body": body,
            "context": {},
            "url": "https://example.com",
        }
        return request

    def test_request_checksum_algorithm_no_model(self):
        request = self._build_request(b"")
        operation_model = self._make_operation_model()
        params = {}
        resolve_request_checksum_algorithm(request, operation_model, params)
        self.assertNotIn("checksum", request["context"])

    def test_request_checksum_algorithm_model_opt_in(self):
        operation_model = self._make_operation_model(
            http_checksum={"requestAlgorithmMember": "Algorithm"}
        )

        # Param is not present, no checksum will be set
        params = {}
        request = self._build_request(b"")
        resolve_request_checksum_algorithm(request, operation_model, params)
        self.assertNotIn("checksum", request["context"])

        # Param is present, crc32 checksum will be set
        params = {"Algorithm": "crc32"}
        request = self._build_request(b"")
        resolve_request_checksum_algorithm(request, operation_model, params)
        expected_algorithm = {
            "algorithm": "crc32",
            "in": "header",
            "name": "x-amz-checksum-crc32",
        }
        actual_algorithm = request["context"]["checksum"]["request_algorithm"]
        self.assertEqual(actual_algorithm, expected_algorithm)

        # Param present but header already set, checksum should be skipped
        params = {"Algorithm": "crc32"}
        request = self._build_request(b"")
        request["headers"]["x-amz-checksum-crc32"] = "foo"
        resolve_request_checksum_algorithm(request, operation_model, params)
        self.assertNotIn("checksum", request["context"])

    def test_request_checksum_algorithm_model_opt_in_streaming(self):
        request = self._build_request(b"")
        operation_model = self._make_operation_model(
            http_checksum={"requestAlgorithmMember": "Algorithm"},
            streaming_input=True,
        )

        # Param is not present, no checksum will be set
        params = {}
        resolve_request_checksum_algorithm(request, operation_model, params)
        self.assertNotIn("checksum", request["context"])

        # Param is present, crc32 checksum will be set in the trailer
        params = {"Algorithm": "crc32"}
        resolve_request_checksum_algorithm(request, operation_model, params)
        expected_algorithm = {
            "algorithm": "crc32",
            "in": "trailer",
            "name": "x-amz-checksum-crc32",
        }
        actual_algorithm = request["context"]["checksum"]["request_algorithm"]
        self.assertEqual(actual_algorithm, expected_algorithm)

        # Trailer should not be used for http endpoints
        request = self._build_request(b"")
        request["url"] = "http://example.com"
        resolve_request_checksum_algorithm(request, operation_model, params)
        expected_algorithm = {
            "algorithm": "crc32",
            "in": "header",
            "name": "x-amz-checksum-crc32",
        }
        actual_algorithm = request["context"]["checksum"]["request_algorithm"]
        self.assertEqual(actual_algorithm, expected_algorithm)

    def test_request_checksum_algorithm_model_unsupported_algorithm(self):
        request = self._build_request(b"")
        operation_model = self._make_operation_model(
            http_checksum={"requestAlgorithmMember": "Algorithm"},
        )
        params = {"Algorithm": "crc32"}

        with self.assertRaises(FlexibleChecksumError):
            resolve_request_checksum_algorithm(
                request, operation_model, params, supported_algorithms=[]
            )

    def test_request_checksum_algorithm_model_legacy_md5(self):
        request = self._build_request(b"")
        operation_model = self._make_operation_model(required=True)
        params = {}

        resolve_request_checksum_algorithm(request, operation_model, params)
        actual_algorithm = request["context"]["checksum"]["request_algorithm"]
        expected_algorithm = "conditional-md5"
        self.assertEqual(actual_algorithm, expected_algorithm)

    def test_request_checksum_algorithm_model_new_md5(self):
        request = self._build_request(b"")
        operation_model = self._make_operation_model(
            http_checksum={"requestChecksumRequired": True}
        )
        params = {}

        resolve_request_checksum_algorithm(request, operation_model, params)
        actual_algorithm = request["context"]["checksum"]["request_algorithm"]
        expected_algorithm = "conditional-md5"
        self.assertEqual(actual_algorithm, expected_algorithm)

    def test_apply_request_checksum_handles_no_checksum_context(self):
        request = self._build_request(b"")
        apply_request_checksum(request)
        # Build another request and assert the original request is the same
        expected_request = self._build_request(b"")
        self.assertEqual(request, expected_request)

    def test_apply_request_checksum_handles_invalid_context(self):
        request = self._build_request(b"")
        request["context"]["checksum"] = {
            "request_algorithm": {
                "in": "http-trailer",
                "algorithm": "crc32",
                "name": "x-amz-checksum-crc32",
            }
        }
        with self.assertRaises(FlexibleChecksumError):
            apply_request_checksum(request)

    def test_apply_request_checksum_conditional_md5(self):
        request = self._build_request(b"")
        request["context"]["checksum"] = {
            "request_algorithm": "conditional-md5"
        }
        apply_request_checksum(request)
        self.assertIn("Content-MD5", request["headers"])

    def test_apply_request_checksum_flex_header_bytes(self):
        request = self._build_request(b"")
        request["context"]["checksum"] = {
            "request_algorithm": {
                "in": "header",
                "algorithm": "crc32",
                "name": "x-amz-checksum-crc32",
            }
        }
        apply_request_checksum(request)
        self.assertIn("x-amz-checksum-crc32", request["headers"])

    def test_apply_request_checksum_flex_header_readable(self):
        request = self._build_request(BytesIO(b""))
        request["context"]["checksum"] = {
            "request_algorithm": {
                "in": "header",
                "algorithm": "crc32",
                "name": "x-amz-checksum-crc32",
            }
        }
        apply_request_checksum(request)
        self.assertIn("x-amz-checksum-crc32", request["headers"])

    def test_apply_request_checksum_flex_header_explicit_digest(self):
        request = self._build_request(b"")
        request["context"]["checksum"] = {
            "request_algorithm": {
                "in": "header",
                "algorithm": "crc32",
                "name": "x-amz-checksum-crc32",
            }
        }
        request["headers"]["x-amz-checksum-crc32"] = "foo"
        apply_request_checksum(request)
        # The checksum should not have been modified
        self.assertEqual(request["headers"]["x-amz-checksum-crc32"], "foo")

    def test_apply_request_checksum_flex_trailer_bytes(self):
        request = self._build_request(b"")
        request["context"]["checksum"] = {
            "request_algorithm": {
                "in": "trailer",
                "algorithm": "crc32",
                "name": "x-amz-checksum-crc32",
            }
        }
        apply_request_checksum(request)
        self.assertNotIn("x-amz-checksum-crc32", request["headers"])
        self.assertIsInstance(request["body"], AwsChunkedWrapper)

    def test_apply_request_checksum_flex_trailer_readable(self):
        request = self._build_request(BytesIO(b""))
        request["context"]["checksum"] = {
            "request_algorithm": {
                "in": "trailer",
                "algorithm": "crc32",
                "name": "x-amz-checksum-crc32",
            }
        }
        apply_request_checksum(request)
        self.assertNotIn("x-amz-checksum-crc32", request["headers"])
        self.assertIsInstance(request["body"], AwsChunkedWrapper)

    def test_apply_request_checksum_flex_header_trailer_explicit_digest(self):
        request = self._build_request(b"")
        request["context"]["checksum"] = {
            "request_algorithm": {
                "in": "trailer",
                "algorithm": "crc32",
                "name": "x-amz-checksum-crc32",
            }
        }
        request["headers"]["x-amz-checksum-crc32"] = "foo"
        apply_request_checksum(request)
        # The checksum should not have been modified
        self.assertEqual(request["headers"]["x-amz-checksum-crc32"], "foo")
        # The body should not have been wrapped
        self.assertIsInstance(request["body"], bytes)

    def test_response_checksum_algorithm_no_model(self):
        request = self._build_request(b"")
        operation_model = self._make_operation_model()
        params = {}
        resolve_response_checksum_algorithms(request, operation_model, params)
        self.assertNotIn("checksum", request["context"])

    def test_response_checksum_algorithm_model_opt_in(self):
        request = self._build_request(b"")
        operation_model = self._make_operation_model(
            http_checksum={
                "responseAlgorithms": ["crc32", "sha1", "sha256"],
                "requestValidationModeMember": "ChecksumMode",
            }
        )

        # Param is not present, no algorithms will be set
        params = {}
        resolve_response_checksum_algorithms(request, operation_model, params)
        self.assertNotIn("checksum", request["context"])

        # Param is present, algorithms will be set
        params = {"ChecksumMode": "enabled"}
        resolve_response_checksum_algorithms(
            request,
            operation_model,
            params,
            supported_algorithms=["sha1", "sha256"],
        )
        # CRC32 should have been filtered it out as it was not supported
        expected_algorithms = ["sha1", "sha256"]
        actual_algorithms = request["context"]["checksum"][
            "response_algorithms"
        ]
        self.assertEqual(actual_algorithms, expected_algorithms)

    def test_handle_checksum_body_checksum(self):
        context = {"checksum": {"response_algorithms": ["sha1", "crc32"]}}
        headers = {"x-amz-checksum-crc32": "DUoRhQ=="}
        http_response, response_dict = self._make_http_response(
            b"hello world", headers=headers, context=context,
        )
        operation_model = self._make_operation_model()
        handle_checksum_body(
            http_response, response_dict, context, operation_model,
        )
        body = response_dict["body"]
        self.assertEqual(body, b"hello world")
        algorithm = response_dict["context"]["checksum"]["response_algorithm"]
        self.assertEqual(algorithm, "crc32")

        headers = {"x-amz-checksum-crc32": "WrOonG=="}
        http_response, response_dict = self._make_http_response(
            b"hello world", headers=headers, context=context,
        )
        with self.assertRaises(FlexibleChecksumError):
            handle_checksum_body(
                http_response, response_dict, context, operation_model,
            )

        # This header should not be checked, we won't calculate a checksum
        # but a proper body should still come out at the end
        headers = {"x-amz-checksum-foo": "FOO=="}
        http_response, response_dict = self._make_http_response(
            b"hello world", headers=headers, context=context,
        )
        handle_checksum_body(
            http_response, response_dict, context, operation_model,
        )
        body = response_dict["body"]
        self.assertEqual(body, b"hello world")
        algorithm = response_dict["context"]["checksum"]["response_algorithm"]
        self.assertEqual(algorithm, "crc32")

    def test_handle_checksum_body_checksum_streaming(self):
        context = {"checksum": {"response_algorithms": ["sha1", "crc32"]}}
        headers = {"x-amz-checksum-crc32": "DUoRhQ=="}
        http_response, response_dict = self._make_http_response(
            b"hello world", headers=headers, context=context, streaming=True,
        )
        operation_model = self._make_operation_model(streaming_output=True)
        handle_checksum_body(
            http_response, response_dict, context, operation_model,
        )
        body = response_dict["body"]
        self.assertEqual(body.read(), b"hello world")
        algorithm = response_dict["context"]["checksum"]["response_algorithm"]
        self.assertEqual(algorithm, "crc32")

        headers = {"x-amz-checksum-crc32": "WrOonG=="}
        http_response, response_dict = self._make_http_response(
            b"hello world", headers=headers, context=context, streaming=True,
        )
        handle_checksum_body(
            http_response, response_dict, context, operation_model,
        )
        body = response_dict["body"]
        with self.assertRaises(FlexibleChecksumError):
            body.read()

        # This header should not be checked, we won't calculate a checksum
        # but a proper body should still come out at the end
        headers = {"x-amz-checksum-foo": "FOOO=="}
        http_response, response_dict = self._make_http_response(
            b"hello world", headers=headers, context=context, streaming=True,
        )
        handle_checksum_body(
            http_response, response_dict, context, operation_model,
        )
        body = response_dict["body"]
        self.assertEqual(body.read(), b"hello world")
        algorithm = response_dict["context"]["checksum"]["response_algorithm"]
        self.assertEqual(algorithm, "crc32")

    def test_handle_checksum_body_checksum_skip_non_streaming(self):
        context = {"checksum": {"response_algorithms": ["sha1", "crc32"]}}
        # S3 will return checksums over the checksums of parts which are a
        # special case that end with -#. These cannot be validated and are
        # instead skipped
        headers = {"x-amz-checksum-crc32": "FOOO==-123"}
        http_response, response_dict = self._make_http_response(
            b"hello world", headers=headers, context=context,
        )
        operation_model = self._make_operation_model()
        handle_checksum_body(
            http_response, response_dict, context, operation_model,
        )
        body = response_dict["body"]
        self.assertEqual(body, b"hello world")

    def test_handle_checksum_body_checksum_skip_streaming(self):
        context = {"checksum": {"response_algorithms": ["sha1", "crc32"]}}
        # S3 will return checksums over the checksums of parts which are a
        # special case that end with -#. These cannot be validated and are
        # instead skipped
        headers = {"x-amz-checksum-crc32": "FOOO==-123"}
        http_response, response_dict = self._make_http_response(
            b"hello world", headers=headers, context=context, streaming=True,
        )
        operation_model = self._make_operation_model(streaming_output=True)
        handle_checksum_body(
            http_response, response_dict, context, operation_model,
        )
        body = response_dict["body"]
        self.assertEqual(body.read(), b"hello world")


class TestAwsChunkedWrapper(unittest.TestCase):
    def test_single_chunk_body(self):
        # Test a small body that fits in a single chunk
        bytes = BytesIO(b"abcdefghijklmnopqrstuvwxyz")
        wrapper = AwsChunkedWrapper(bytes)
        body = wrapper.read()
        expected = b"1a\r\n" b"abcdefghijklmnopqrstuvwxyz\r\n" b"0\r\n\r\n"
        self.assertEqual(body, expected)

    def test_multi_chunk_body(self):
        # Test a body that requires multiple chunks
        bytes = BytesIO(b"abcdefghijklmnopqrstuvwxyz")
        wrapper = AwsChunkedWrapper(bytes, chunk_size=10)
        body = wrapper.read()
        expected = (
            b"a\r\n"
            b"abcdefghij\r\n"
            b"a\r\n"
            b"klmnopqrst\r\n"
            b"6\r\n"
            b"uvwxyz\r\n"
            b"0\r\n\r\n"
        )
        self.assertEqual(body, expected)

    def test_read_returns_less_data(self):
        class OneLessBytesIO(BytesIO):
            def read(self, size=-1):
                # Return 1 less byte than was asked for
                return super(OneLessBytesIO, self).read(size - 1)

        bytes = OneLessBytesIO(b"abcdefghijklmnopqrstuvwxyz")
        wrapper = AwsChunkedWrapper(bytes, chunk_size=10)
        body = wrapper.read()
        # NOTE: This particular body is not important, but it is important that
        # the actual size of the chunk matches the length sent which may not
        # always be the configured chunk_size if the read does not return that
        # much data.
        expected = (
            b"9\r\n"
            b"abcdefghi\r\n"
            b"9\r\n"
            b"jklmnopqr\r\n"
            b"8\r\n"
            b"stuvwxyz\r\n"
            b"0\r\n\r\n"
        )
        self.assertEqual(body, expected)

    def test_single_chunk_body_with_checksum(self):
        wrapper = AwsChunkedWrapper(
            BytesIO(b"hello world"),
            checksum_cls=Crc32Checksum,
            checksum_name="checksum",
        )
        body = wrapper.read()
        expected = (
            b"b\r\n" b"hello world\r\n" b"0\r\n" b"checksum:DUoRhQ==\r\n\r\n"
        )
        self.assertEqual(body, expected)

    def test_multi_chunk_body_with_checksum(self):
        wrapper = AwsChunkedWrapper(
            BytesIO(b"hello world"),
            chunk_size=5,
            checksum_cls=Crc32Checksum,
            checksum_name="checksum",
        )
        body = wrapper.read()
        expected = (
            b"5\r\n"
            b"hello\r\n"
            b"5\r\n"
            b" worl\r\n"
            b"1\r\n"
            b"d\r\n"
            b"0\r\n"
            b"checksum:DUoRhQ==\r\n\r\n"
        )
        self.assertEqual(body, expected)

    def test_multi_chunk_body_with_checksum_iter(self):
        wrapper = AwsChunkedWrapper(
            BytesIO(b"hello world"),
            chunk_size=5,
            checksum_cls=Crc32Checksum,
            checksum_name="checksum",
        )
        expected_chunks = [
            b"5\r\nhello\r\n",
            b"5\r\n worl\r\n",
            b"1\r\nd\r\n",
            b"0\r\nchecksum:DUoRhQ==\r\n\r\n",
        ]
        self.assertListEqual(expected_chunks, list(wrapper))

    def test_wrapper_can_be_reset(self):
        wrapper = AwsChunkedWrapper(
            BytesIO(b"hello world"),
            chunk_size=5,
            checksum_cls=Crc32Checksum,
            checksum_name="checksum",
        )
        first_read = wrapper.read()
        self.assertEqual(b"", wrapper.read())
        wrapper.seek(0)
        second_read = wrapper.read()
        self.assertEqual(first_read, second_read)
        self.assertIn(b"checksum:DUoRhQ==", first_read)

    def test_wrapper_can_only_seek_to_start(self):
        wrapper = AwsChunkedWrapper(BytesIO())
        with self.assertRaises(AwsChunkedWrapperError):
            wrapper.seek(1)
        with self.assertRaises(AwsChunkedWrapperError):
            wrapper.seek(0, whence=1)
        with self.assertRaises(AwsChunkedWrapperError):
            wrapper.seek(1, whence=2)


class TestChecksumImplementations(unittest.TestCase):
    def assert_base64_checksum(self, checksum_cls, expected_digest):
        checksum = checksum_cls()
        checksum.update(b"hello world")
        actual_digest = checksum.b64digest()
        self.assertEqual(actual_digest, expected_digest)

    def test_crc32(self):
        self.assert_base64_checksum(Crc32Checksum, "DUoRhQ==")

    def test_sha1(self):
        self.assert_base64_checksum(
            Sha1Checksum, "Kq5sNclPz7QV2+lfQIuc6R7oRu0=",
        )

    def test_sha256(self):
        self.assert_base64_checksum(
            Sha256Checksum, "uU0nuZNNPgilLlLX2n2r+sSE7+N6U4DukIj3rOLvzek=",
        )

    @requires_crt()
    def test_crt_crc32(self):
        self.assert_base64_checksum(CrtCrc32Checksum, "DUoRhQ==")

    @requires_crt()
    def test_crt_crc32c(self):
        self.assert_base64_checksum(CrtCrc32cChecksum, "yZRlqg==")


class TestCrtChecksumOverrides(unittest.TestCase):
    @requires_crt()
    def test_crt_crc32_available(self):
        actual_cls = _CHECKSUM_CLS.get("crc32")
        self.assertEqual(actual_cls, CrtCrc32Checksum)

    @requires_crt()
    def test_crt_crc32c_available(self):
        actual_cls = _CHECKSUM_CLS.get("crc32c")
        self.assertEqual(actual_cls, CrtCrc32cChecksum)


class TestStreamingChecksumBody(unittest.TestCase):
    def setUp(self):
        self.raw_bytes = b"hello world"
        self.fake_body = BytesIO(self.raw_bytes)
        self._make_wrapper("DUoRhQ==")

    def _make_wrapper(self, checksum):
        self.wrapper = StreamingChecksumBody(
            self.fake_body, None, Crc32Checksum(), checksum,
        )

    def test_basic_read_good(self):
        actual = self.wrapper.read()
        self.assertEqual(actual, self.raw_bytes)

    def test_many_reads_good(self):
        actual = b""
        actual += self.wrapper.read(5)
        actual += self.wrapper.read(5)
        actual += self.wrapper.read(1)
        self.assertEqual(actual, self.raw_bytes)

    def test_basic_read_bad(self):
        self._make_wrapper("duorhq==")
        with self.assertRaises(FlexibleChecksumError):
            self.wrapper.read()

    def test_many_reads_bad(self):
        self._make_wrapper("duorhq==")
        self.wrapper.read(5)
        self.wrapper.read(6)
        # Whole body has been read, next read signals the end of the stream and
        # validates the checksum of the body contents read
        with self.assertRaises(FlexibleChecksumError):
            self.wrapper.read(1)

    def test_handles_variable_padding(self):
        # This digest is equivalent but with more padding
        self._make_wrapper("DUoRhQ=====")
        actual = self.wrapper.read()
        self.assertEqual(actual, self.raw_bytes)

    def test_iter_raises_error(self):
        self._make_wrapper("duorhq==")
        with self.assertRaises(FlexibleChecksumError):
            for chunk in self.wrapper:
                pass
