# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import datetime
import io
import socket

import pytest

import botocore.endpoint
from botocore.config import Config
from botocore.endpoint import DEFAULT_TIMEOUT, Endpoint, EndpointCreator
from botocore.exceptions import HTTPClientError
from botocore.httpsession import URLLib3Session
from botocore.model import (
    OperationModel,
    ServiceId,
    ServiceModel,
    StructureShape,
)
from tests import mock, unittest


def request_dict(**kwargs):
    base = {
        'headers': {},
        'body': '',
        'url_path': '/',
        'query_string': '',
        'method': 'POST',
        'url': 'https://example.com',
        'context': {},
    }
    base.update(kwargs)
    return base


class RecordStreamResets(io.StringIO):
    def __init__(self, value):
        io.StringIO.__init__(self, value)
        self.total_resets = 0

    def seek(self, where, whence=0):
        self.total_resets += 1
        io.StringIO.seek(self, where, whence)


class TestEndpointBase(unittest.TestCase):
    def setUp(self):
        self.op = mock.Mock()
        self.op.has_streaming_output = False
        self.op.has_event_stream_output = False
        self.op.metadata = {'protocol': 'json'}
        self.event_emitter = mock.Mock()
        self.event_emitter.emit.return_value = []
        self.factory_patch = mock.patch(
            'botocore.parsers.ResponseParserFactory'
        )
        self.factory = self.factory_patch.start()
        self.endpoint = Endpoint(
            'https://ec2.us-west-2.amazonaws.com/',
            endpoint_prefix='ec2',
            event_emitter=self.event_emitter,
        )
        self.http_session = mock.Mock()
        self.http_session.send.return_value = mock.Mock(
            status_code=200,
            headers={},
            content=b'{"Foo": "bar"}',
        )
        self.endpoint.http_session = self.http_session

    def tearDown(self):
        self.factory_patch.stop()

    def get_emitter_responses(self, num_retries=0, sleep_time=0, num_events=4):
        emitter_responses = []
        # We emit the following events:
        # 1. request-created
        # 2. before-send
        # 3. before-parse (may not be emitted if certain errors are thrown)
        # 4. response-received
        response_request_emitter_responses = [
            [(None, None)]  # emit() response for each emitted event
        ] * num_events
        for _ in range(num_retries):
            emitter_responses.extend(response_request_emitter_responses)
            # emit() response for retry for sleep time
            emitter_responses.append([(None, sleep_time)])
        emitter_responses.extend(response_request_emitter_responses)
        # emit() response for no retry
        emitter_responses.append([(None, None)])
        return emitter_responses

    def get_events_emitted(self, event_emitter):
        return [
            call_arg[0][0] for call_arg in event_emitter.emit.call_args_list
        ]


class TestEndpointFeatures(TestEndpointBase):
    def test_make_request_with_no_auth(self):
        self.endpoint.auth = None
        self.endpoint.make_request(self.op, request_dict())

        # http_session should be used to send the request.
        self.assertTrue(self.http_session.send.called)
        prepared_request = self.http_session.send.call_args[0][0]
        self.assertNotIn('Authorization', prepared_request.headers)

    def test_make_request_no_signature_version(self):
        self.endpoint.make_request(self.op, request_dict())

        # http_session should be used to send the request.
        self.assertTrue(self.http_session.send.called)
        prepared_request = self.http_session.send.call_args[0][0]
        self.assertNotIn('Authorization', prepared_request.headers)

    def test_make_request_with_context(self):
        r = request_dict()
        r['context'] = {'signing': {'region': 'us-west-2'}}
        with mock.patch(
            'botocore.endpoint.Endpoint.prepare_request'
        ) as prepare:
            self.endpoint.make_request(self.op, r)
        request = prepare.call_args[0][0]
        self.assertEqual(request.context['signing']['region'], 'us-west-2')

    def test_make_request_sets_retries_config_in_context(self):
        r = request_dict()
        r['context'] = {'signing': {'region': 'us-west-2'}}
        with mock.patch(
            'botocore.endpoint.Endpoint.prepare_request'
        ) as prepare:
            self.endpoint.make_request(self.op, r)
        request = prepare.call_args[0][0]
        self.assertIn('retries', request.context)

    def test_exception_caught_when_constructing_retries_context(self):
        r = request_dict()
        datetime_patcher = mock.patch.object(
            botocore.endpoint.datetime,
            'datetime',
            mock.Mock(wraps=datetime.datetime),
        )
        r['context'] = {'signing': {'region': 'us-west-2'}}
        with mock.patch(
            'botocore.endpoint.Endpoint.prepare_request'
        ) as prepare:
            mocked_datetime = datetime_patcher.start()
            mocked_datetime.side_effect = Exception()
            self.endpoint.make_request(self.op, r)
            datetime_patcher.stop()
        request = prepare.call_args[0][0]
        self.assertIn('retries', request.context)

    def test_parses_modeled_exception_fields(self):
        # Setup the service model to have exceptions to generate the mapping
        self.service_model = mock.Mock(spec=ServiceModel)
        self.op.service_model = self.service_model
        self.exception_shape = mock.Mock(spec=StructureShape)
        shape_for_error_code = self.service_model.shape_for_error_code
        shape_for_error_code.return_value = self.exception_shape

        r = request_dict()
        self.http_session.send.return_value = mock.Mock(
            status_code=400,
            headers={},
            content=b'',
        )
        parser = mock.Mock()
        parser.parse.side_effect = [
            {
                'Error': {
                    'Code': 'ExceptionShape',
                    'Message': 'Some message',
                }
            },
            {'SomeField': 'Foo'},
        ]
        self.factory.return_value.create_parser.return_value = parser
        _, response = self.endpoint.make_request(self.op, r)
        # The parser should be called twice, once for the original
        # error parse and once again for the modeled exception parse
        self.assertEqual(parser.parse.call_count, 2)
        parse_calls = parser.parse.call_args_list
        self.assertEqual(parse_calls[1][0][1], self.exception_shape)
        self.assertEqual(parse_calls[0][0][1], self.op.output_shape)
        expected_response = {
            'Error': {
                'Code': 'ExceptionShape',
                'Message': 'Some message',
            },
            'SomeField': 'Foo',
        }
        self.assertEqual(response, expected_response)

    def test_close(self):
        self.endpoint.close()
        self.endpoint.http_session.close.assert_called_once_with()


class TestRetryInterface(TestEndpointBase):
    def setUp(self):
        super().setUp()
        self.retried_on_exception = None
        self._operation = mock.Mock(spec=OperationModel)
        self._operation.name = 'DescribeInstances'
        self._operation.metadata = {'protocol': 'query'}
        self._operation.service_model.service_id = ServiceId('EC2')
        self._operation.has_streaming_output = False
        self._operation.has_event_stream_output = False

    def assert_events_emitted(self, event_emitter, expected_events):
        self.assertEqual(
            self.get_events_emitted(event_emitter), expected_events
        )

    def test_retry_events_are_emitted(self):
        self.endpoint.make_request(self._operation, request_dict())
        call_args = self.event_emitter.emit.call_args
        self.assertEqual(call_args[0][0], 'needs-retry.ec2.DescribeInstances')

    def test_retry_events_can_alter_behavior(self):
        self.event_emitter.emit.side_effect = self.get_emitter_responses(
            num_retries=1
        )
        r = request_dict()
        r['context']['client_config'] = Config()
        self.endpoint.make_request(self._operation, r)
        self.assert_events_emitted(
            self.event_emitter,
            expected_events=[
                'request-created.ec2.DescribeInstances',
                'before-send.ec2.DescribeInstances',
                'before-parse.ec2.DescribeInstances',
                'response-received.ec2.DescribeInstances',
                'needs-retry.ec2.DescribeInstances',
            ]
            * 2,
        )

    def test_retry_on_socket_errors(self):
        self.event_emitter.emit.side_effect = self.get_emitter_responses(
            num_retries=1, num_events=3
        )
        self.http_session.send.side_effect = HTTPClientError(error='wrapped')
        with self.assertRaises(HTTPClientError):
            self.endpoint.make_request(self._operation, request_dict())
        self.assert_events_emitted(
            self.event_emitter,
            expected_events=[
                'request-created.ec2.DescribeInstances',
                'before-send.ec2.DescribeInstances',
                'response-received.ec2.DescribeInstances',
                'needs-retry.ec2.DescribeInstances',
            ]
            * 2,
        )

    def test_retry_attempts_added_to_response_metadata(self):
        self.event_emitter.emit.side_effect = self.get_emitter_responses(
            num_retries=1
        )
        parser = mock.Mock()
        parser.parse.return_value = {'ResponseMetadata': {}}
        self.factory.return_value.create_parser.return_value = parser
        r = request_dict()
        r['context']['client_config'] = Config()
        response = self.endpoint.make_request(self._operation, r)
        self.assertEqual(response[1]['ResponseMetadata']['RetryAttempts'], 1)

    def test_retry_attempts_is_zero_when_not_retried(self):
        self.event_emitter.emit.side_effect = self.get_emitter_responses(
            num_retries=0
        )
        parser = mock.Mock()
        parser.parse.return_value = {'ResponseMetadata': {}}
        self.factory.return_value.create_parser.return_value = parser
        response = self.endpoint.make_request(self._operation, request_dict())
        self.assertEqual(response[1]['ResponseMetadata']['RetryAttempts'], 0)


class TestS3ResetStreamOnRetry(TestEndpointBase):
    def setUp(self):
        super().setUp()

    def max_attempts_retry_handler(self, attempts, **kwargs):
        # Simulate a max requests of 3.
        self.total_calls += 1
        if attempts == 3:
            return None
        else:
            # Returning anything non-None will trigger a retry,
            # but 0 here is so that time.sleep(0) happens.
            return 0

    def test_reset_stream_on_retry(self):
        op = mock.Mock()
        body = RecordStreamResets('foobar')
        op.name = 'PutObject'
        op.has_streaming_output = True
        op.has_event_stream_output = False
        op.metadata = {'protocol': 'rest-xml'}
        request = request_dict()
        request['body'] = body
        request['context']['client_config'] = Config()
        self.event_emitter.emit.side_effect = self.get_emitter_responses(
            num_retries=2
        )
        self.endpoint.make_request(op, request)
        # 2 seeks for the resets and 6 (2 per creation) for content-length
        self.assertEqual(body.total_resets, 8)


class TestEventStreamBody(TestEndpointBase):
    def test_event_stream_body_is_streaming(self):
        self.op.has_event_stream_output = True
        request = request_dict()
        self.endpoint.make_request(self.op, request)
        sent_request = self.http_session.send.call_args[0][0]
        self.assertTrue(sent_request.stream_output)


class TestEndpointCreator(unittest.TestCase):
    def setUp(self):
        self.service_model = mock.Mock(
            endpoint_prefix='ec2', signature_version='v2', signing_name='ec2'
        )
        self.environ = {}
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()
        self.creator = EndpointCreator(mock.Mock())
        self.mock_session = mock.Mock(spec=URLLib3Session)

    def tearDown(self):
        self.environ_patch.stop()

    def test_creates_endpoint_with_configured_url(self):
        endpoint = self.creator.create_endpoint(
            self.service_model,
            region_name='us-east-1',
            endpoint_url='https://endpoint.url',
        )
        self.assertEqual(endpoint.host, 'https://endpoint.url')

    def test_creates_endpoint_with_ipv4_url(self):
        endpoint = self.creator.create_endpoint(
            self.service_model,
            region_name='us-east-1',
            endpoint_url='https://192.168.0.0',
        )
        self.assertEqual(endpoint.host, 'https://192.168.0.0')

    def test_creates_endpoint_with_ipv6_url(self):
        endpoint = self.creator.create_endpoint(
            self.service_model,
            region_name='us-east-1',
            endpoint_url='https://[100:0:2::61]:7480',
        )
        self.assertEqual(endpoint.host, 'https://[100:0:2::61]:7480')

    def test_raises_error_with_invalid_url(self):
        with pytest.raises(ValueError):
            self.creator.create_endpoint(
                self.service_model,
                region_name='us-east-1',
                endpoint_url='https://*.aws.amazon.com/',
            )

    def test_create_endpoint_with_default_timeout(self):
        self.creator.create_endpoint(
            self.service_model,
            region_name='us-west-2',
            endpoint_url='https://example.com',
            http_session_cls=self.mock_session,
        )
        session_args = self.mock_session.call_args[1]
        self.assertEqual(session_args.get('timeout'), DEFAULT_TIMEOUT)

    def test_create_endpoint_with_customized_timeout(self):
        self.creator.create_endpoint(
            self.service_model,
            region_name='us-west-2',
            endpoint_url='https://example.com',
            timeout=123,
            http_session_cls=self.mock_session,
        )
        session_args = self.mock_session.call_args[1]
        self.assertEqual(session_args.get('timeout'), 123)

    def test_get_endpoint_default_verify_ssl(self):
        self.creator.create_endpoint(
            self.service_model,
            region_name='us-west-2',
            endpoint_url='https://example.com',
            http_session_cls=self.mock_session,
        )
        session_args = self.mock_session.call_args[1]
        self.assertTrue(session_args.get('verify'))

    def test_verify_ssl_can_be_disabled(self):
        self.creator.create_endpoint(
            self.service_model,
            region_name='us-west-2',
            endpoint_url='https://example.com',
            verify=False,
            http_session_cls=self.mock_session,
        )
        session_args = self.mock_session.call_args[1]
        self.assertFalse(session_args.get('verify'))

    def test_verify_ssl_can_specify_cert_bundle(self):
        self.creator.create_endpoint(
            self.service_model,
            region_name='us-west-2',
            endpoint_url='https://example.com',
            verify='/path/cacerts.pem',
            http_session_cls=self.mock_session,
        )
        session_args = self.mock_session.call_args[1]
        self.assertEqual(session_args.get('verify'), '/path/cacerts.pem')

    def test_client_cert_can_specify_path(self):
        client_cert = '/some/path/cert'
        self.creator.create_endpoint(
            self.service_model,
            region_name='us-west-2',
            endpoint_url='https://example.com',
            client_cert=client_cert,
            http_session_cls=self.mock_session,
        )
        session_args = self.mock_session.call_args[1]
        self.assertEqual(session_args.get('client_cert'), '/some/path/cert')

    def test_honor_cert_bundle_env_var(self):
        self.environ['REQUESTS_CA_BUNDLE'] = '/env/cacerts.pem'
        self.creator.create_endpoint(
            self.service_model,
            region_name='us-west-2',
            endpoint_url='https://example.com',
            http_session_cls=self.mock_session,
        )
        session_args = self.mock_session.call_args[1]
        self.assertEqual(session_args.get('verify'), '/env/cacerts.pem')

    def test_env_ignored_if_explicitly_passed(self):
        self.environ['REQUESTS_CA_BUNDLE'] = '/env/cacerts.pem'
        self.creator.create_endpoint(
            self.service_model,
            region_name='us-west-2',
            endpoint_url='https://example.com',
            verify='/path/cacerts.pem',
            http_session_cls=self.mock_session,
        )
        session_args = self.mock_session.call_args[1]
        # /path/cacerts.pem wins over the value from the env var.
        self.assertEqual(session_args.get('verify'), '/path/cacerts.pem')

    def test_can_specify_max_pool_conns(self):
        self.creator.create_endpoint(
            self.service_model,
            region_name='us-west-2',
            endpoint_url='https://example.com',
            max_pool_connections=100,
            http_session_cls=self.mock_session,
        )
        session_args = self.mock_session.call_args[1]
        self.assertEqual(session_args.get('max_pool_connections'), 100)

    def test_socket_options(self):
        socket_options = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
        self.creator.create_endpoint(
            self.service_model,
            region_name='us-west-2',
            endpoint_url='https://example.com',
            http_session_cls=self.mock_session,
            socket_options=socket_options,
        )
        session_args = self.mock_session.call_args[1]
        self.assertEqual(session_args.get('socket_options'), socket_options)
