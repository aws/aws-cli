from botocore.awsrequest import AWSResponse
from botocore.retries import special, standard
from tests import mock, unittest


def create_fake_op_model(service_name):
    model = mock.Mock()
    model.service_model.service_name = service_name
    return model


class TestRetryIDPCommunicationError(unittest.TestCase):
    def setUp(self):
        self.checker = special.RetryIDPCommunicationError()

    def test_only_retries_error_for_sts(self):
        context = standard.RetryContext(
            attempt_number=1,
            operation_model=create_fake_op_model('s3'),
            parsed_response={
                'Error': {
                    'Code': 'IDPCommunicationError',
                    'Message': 'message',
                }
            },
            http_response=AWSResponse(
                status_code=400, raw=None, headers={}, url='https://foo'
            ),
            caught_exception=None,
        )
        self.assertFalse(self.checker.is_retryable(context))

    def test_can_retry_idp_communication_error(self):
        context = standard.RetryContext(
            attempt_number=1,
            operation_model=create_fake_op_model('sts'),
            parsed_response={
                'Error': {
                    'Code': 'IDPCommunicationError',
                    'Message': 'message',
                }
            },
            http_response=AWSResponse(
                status_code=400, raw=None, headers={}, url='https://foo'
            ),
            caught_exception=None,
        )
        self.assertTrue(self.checker.is_retryable(context))

    def test_not_idp_communication_error(self):
        context = standard.RetryContext(
            attempt_number=1,
            operation_model=create_fake_op_model('sts'),
            parsed_response={
                'Error': {
                    'Code': 'NotIDPCommunicationError',
                    'Message': 'message',
                }
            },
            http_response=AWSResponse(
                status_code=400, raw=None, headers={}, url='https://foo'
            ),
            caught_exception=None,
        )
        self.assertFalse(self.checker.is_retryable(context))


class TestRetryDDBChecksumError(unittest.TestCase):
    def setUp(self):
        self.checker = special.RetryDDBChecksumError()

    def raw_stream(self, contents):
        raw = mock.Mock()
        raw.stream.return_value = [contents]
        return raw

    def test_checksum_not_in_header(self):
        context = standard.RetryContext(
            attempt_number=1,
            operation_model=create_fake_op_model('dynamodb'),
            parsed_response={
                'Anything': ["foo"],
            },
            http_response=AWSResponse(
                status_code=200,
                raw=self.raw_stream(b'foo'),
                headers={},
                url='https://foo',
            ),
            caught_exception=None,
        )
        self.assertFalse(self.checker.is_retryable(context))

    def test_checksum_matches(self):
        context = standard.RetryContext(
            attempt_number=1,
            operation_model=create_fake_op_model('dynamodb'),
            parsed_response={
                'Anything': ["foo"],
            },
            http_response=AWSResponse(
                status_code=200,
                raw=self.raw_stream(b'foo'),
                headers={'x-amz-crc32': '2356372769'},
                url='https://foo',
            ),
            caught_exception=None,
        )
        self.assertFalse(self.checker.is_retryable(context))

    def test_checksum_not_matches(self):
        context = standard.RetryContext(
            attempt_number=1,
            operation_model=create_fake_op_model('dynamodb'),
            parsed_response={
                'Anything': ["foo"],
            },
            http_response=AWSResponse(
                status_code=200,
                raw=self.raw_stream(b'foo'),
                headers={'x-amz-crc32': '2356372768'},
                url='https://foo',
            ),
            caught_exception=None,
        )
        self.assertTrue(self.checker.is_retryable(context))

    def test_checksum_check_only_for_dynamodb(self):
        context = standard.RetryContext(
            attempt_number=1,
            operation_model=create_fake_op_model('s3'),
            parsed_response={
                'Anything': ["foo"],
            },
            http_response=AWSResponse(
                status_code=200,
                raw=self.raw_stream(b'foo'),
                headers={'x-amz-crc32': '2356372768'},
                url='https://foo',
            ),
            caught_exception=None,
        )
        self.assertFalse(self.checker.is_retryable(context))
