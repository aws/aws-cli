# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from tests import mock, unittest
import json
import re
import socket
import time

from botocore.awsrequest import AWSRequest
from botocore.compat import six
from botocore.exceptions import ConnectionError
from botocore.hooks import HierarchicalEmitter
from botocore.model import OperationModel
from botocore.model import ServiceModel
from botocore.monitoring import Monitor
from botocore.monitoring import MonitorEventAdapter
from botocore.monitoring import CSMSerializer
from botocore.monitoring import SocketPublisher
from botocore.monitoring import BaseMonitorEvent
from botocore.monitoring import APICallEvent
from botocore.monitoring import APICallAttemptEvent


class PublishingException(Exception):
    pass


class TestMonitor(unittest.TestCase):
    def setUp(self):
        self.adapter = mock.Mock(MonitorEventAdapter)
        self.publisher = mock.Mock(SocketPublisher)
        self.handler = Monitor(self.adapter, self.publisher)

    def test_register(self):
        event_emitter = mock.Mock(HierarchicalEmitter)
        self.handler.register(event_emitter)
        self.assertEqual(
            event_emitter.register_last.call_args_list,
            [
                mock.call('before-parameter-build', self.handler.capture),
                mock.call('request-created', self.handler.capture),
                mock.call('response-received', self.handler.capture),
                mock.call('after-call', self.handler.capture),
                mock.call('after-call-error', self.handler.capture),
            ]
        )

    def test_handle(self):
        event = object()
        self.adapter.feed.return_value = event
        self.handler.capture('event-name', event_parameter='event-value')
        self.adapter.feed.assert_called_with(
            'event-name', {'event_parameter': 'event-value'})
        self.publisher.publish.assert_called_with(event)

    def test_handle_no_publish(self):
        self.adapter.feed.return_value = None
        self.handler.capture('event-name', event_parameter='event-value')
        self.publisher.publish.assert_not_called()

    def test_handle_catches_exceptions(self):
        self.publisher.publish.side_effect = PublishingException()
        try:
            self.handler.capture('event-name', event_parameter='event-value')
        except PublishingException:
            self.fail('The publishing exception should have been caught '
                      'in the handler')


class TestMonitorEventAdapter(unittest.TestCase):
    def setUp(self):
        self.mock_time = mock.Mock(time.time)
        self.mock_time.return_value = 0
        self.adapter = MonitorEventAdapter(self.mock_time)

        self.context = {}
        self.wire_name = 'MyOperation'
        self.operation_model = mock.Mock(OperationModel)
        self.operation_model.wire_name = self.wire_name
        self.service_id = 'MyService'
        self.service_model = mock.Mock(ServiceModel)
        self.service_model.service_id = self.service_id
        self.operation_model.service_model = self.service_model

        self.url = 'https://us-east-1.myservice.amazonaws.com'
        self.request_headers = {}
        self.request = mock.Mock(AWSRequest)
        self.request.url = self.url
        self.request.headers = self.request_headers
        self.request.context = self.context

        self.http_status_code = 200
        self.response_headers = {}

    def feed_before_parameter_build_event(self, current_time=0):
        self.mock_time.return_value = current_time
        self.adapter.feed('before-parameter-build', {
            'model': self.operation_model,
            'context': self.context
        })

    def feed_request_created_event(self, current_time=0):
        self.mock_time.return_value = current_time
        self.adapter.feed('request-created', {
            'request': self.request,
        })

    def test_feed_before_parameter_build_returns_no_event(self):
        self.assertIsNone(
            self.adapter.feed('before-parameter-build', {
                'model': self.operation_model,
                'context': self.context
            })
        )

    def test_feed_request_created_returns_no_event(self):
        self.adapter.feed('before-parameter-build', {
            'model': self.operation_model,
            'context': self.context
        })
        self.assertIsNone(
            self.adapter.feed('request-created', {
                'request': self.request,
            })
        )

    def test_feed_with_successful_response(self):
        self.feed_before_parameter_build_event(current_time=1)
        self.feed_request_created_event(current_time=2)

        self.mock_time.return_value = 3
        attempt_event = self.adapter.feed('response-received', {
            'parsed_response': {
                'ResponseMetadata': {
                    'HTTPStatusCode': self.http_status_code,
                    'HTTPHeaders': self.response_headers
                }
            },
            'context': self.context,
            'exception': None
        })
        self.assertEqual(
            attempt_event,
            APICallAttemptEvent(
                service=self.service_id,
                operation=self.wire_name,
                timestamp=2000,
                latency=1000,
                url=self.url,
                request_headers=self.request_headers,
                http_status_code=self.http_status_code,
                response_headers=self.response_headers,
            )
        )

        self.mock_time.return_value = 4
        call_event = self.adapter.feed('after-call', {
            'parsed': {
                'ResponseMetadata': {
                    'HTTPStatusCode': self.http_status_code,
                    'HTTPHeaders': self.response_headers
                }
            },
            'context': self.context
        })
        self.assertEqual(
            call_event,
            APICallEvent(
                service=self.service_id,
                operation=self.wire_name,
                timestamp=1000,
                latency=3000,
                attempts=[attempt_event]
            )
        )

    def test_feed_with_retries(self):
        self.feed_before_parameter_build_event(current_time=1)
        self.feed_request_created_event(current_time=2)

        self.mock_time.return_value = 3
        first_attempt_event = self.adapter.feed('response-received', {
            'parsed_response': {
                'ResponseMetadata': {
                    'HTTPStatusCode': 500,
                    'HTTPHeaders': self.response_headers
                }
            },
            'context': self.context,
            'exception': None
        })
        self.assertEqual(
            first_attempt_event,
            APICallAttemptEvent(
                service=self.service_id,
                operation=self.wire_name,
                timestamp=2000,
                latency=1000,
                url=self.url,
                request_headers=self.request_headers,
                http_status_code=500,
                response_headers=self.response_headers,
            )
        )

        self.feed_request_created_event(current_time=5)
        self.mock_time.return_value = 6
        second_attempt_event = self.adapter.feed('response-received', {
            'parsed_response': {
                'ResponseMetadata': {
                    'HTTPStatusCode': 200,
                    'HTTPHeaders': self.response_headers
                }
            },
            'context': self.context,
            'exception': None
        })
        self.assertEqual(
            second_attempt_event,
            APICallAttemptEvent(
                service=self.service_id,
                operation=self.wire_name,
                timestamp=5000,
                latency=1000,
                url=self.url,
                request_headers=self.request_headers,
                http_status_code=200,
                response_headers=self.response_headers,
            )
        )

        self.mock_time.return_value = 7
        call_event = self.adapter.feed('after-call', {
            'parsed': {
                'ResponseMetadata': {
                    'HTTPStatusCode': 200,
                    'HTTPHeaders': self.response_headers
                }
            },
            'context': self.context
        })
        self.assertEqual(
            call_event,
            APICallEvent(
                service=self.service_id,
                operation=self.wire_name,
                timestamp=1000,
                latency=6000,
                attempts=[first_attempt_event, second_attempt_event]
            )
        )

    def test_feed_with_retries_exceeded(self):
        self.feed_before_parameter_build_event(current_time=1)
        self.feed_request_created_event(current_time=2)

        self.mock_time.return_value = 3
        first_attempt_event = self.adapter.feed('response-received', {
            'parsed_response': {
                'ResponseMetadata': {
                    'HTTPStatusCode': 500,
                    'HTTPHeaders': self.response_headers
                }
            },
            'context': self.context,
            'exception': None
        })
        self.feed_request_created_event(current_time=5)
        self.mock_time.return_value = 6
        second_attempt_event = self.adapter.feed('response-received', {
            'parsed_response': {
                'ResponseMetadata': {
                    'HTTPStatusCode': 200,
                    'HTTPHeaders': self.response_headers,
                    'MaxAttemptsReached': True
                }
            },
            'context': self.context,
            'exception': None
        })
        self.mock_time.return_value = 7
        call_event = self.adapter.feed('after-call', {
            'parsed': {
                'ResponseMetadata': {
                    'HTTPStatusCode': 200,
                    'HTTPHeaders': self.response_headers,
                    'MaxAttemptsReached': True
                }
            },
            'context': self.context
        })
        self.assertEqual(
            call_event,
            APICallEvent(
                service=self.service_id,
                operation=self.wire_name,
                timestamp=1000,
                latency=6000,
                attempts=[first_attempt_event, second_attempt_event],
                retries_exceeded=True
            )
        )

    def test_feed_with_parsed_error(self):
        self.feed_before_parameter_build_event(current_time=1)
        self.feed_request_created_event(current_time=2)

        self.mock_time.return_value = 3
        parsed_error = {'Code': 'MyErrorCode', 'Message': 'MyMessage'}
        parsed_response = {
            'Error': parsed_error,
            'ResponseMetadata': {
                'HTTPStatusCode': 400,
                'HTTPHeaders': self.response_headers
            }
        }
        attempt_event = self.adapter.feed('response-received', {
            'parsed_response': parsed_response,
            'context': self.context,
            'exception': None
        })
        self.assertEqual(
            attempt_event,
            APICallAttemptEvent(
                service=self.service_id,
                operation=self.wire_name,
                timestamp=2000,
                latency=1000,
                url=self.url,
                request_headers=self.request_headers,
                http_status_code=400,
                response_headers=self.response_headers,
                parsed_error=parsed_error
            )
        )

        self.mock_time.return_value = 4
        call_event = self.adapter.feed('after-call', {
            'parsed': parsed_response,
            'context': self.context
        })
        self.assertEqual(
            call_event,
            APICallEvent(
                service=self.service_id,
                operation=self.wire_name,
                timestamp=1000,
                latency=3000,
                attempts=[attempt_event]
            )
        )

    def test_feed_with_wire_exception(self):
        self.feed_before_parameter_build_event(current_time=1)
        self.feed_request_created_event(current_time=2)

        self.mock_time.return_value = 3
        wire_exception = Exception('Some wire exception')
        attempt_event = self.adapter.feed('response-received', {
            'parsed_response': None,
            'context': self.context,
            'exception': wire_exception
        })
        self.assertEqual(
            attempt_event,
            APICallAttemptEvent(
                service=self.service_id,
                operation=self.wire_name,
                timestamp=2000,
                latency=1000,
                url=self.url,
                request_headers=self.request_headers,
                wire_exception=wire_exception,
            )
        )

        self.mock_time.return_value = 4
        call_event = self.adapter.feed(
            'after-call-error', {
                'exception': wire_exception,
                'context': self.context
            }
        )
        self.assertEqual(
            call_event,
            APICallEvent(
                service=self.service_id,
                operation=self.wire_name,
                timestamp=1000,
                latency=3000,
                attempts=[attempt_event]
            )
        )

    def test_feed_with_wire_exception_retries_exceeded(self):
        self.feed_before_parameter_build_event(current_time=1)
        self.feed_request_created_event(current_time=2)

        self.mock_time.return_value = 3
        # Connection errors are retryable
        wire_exception = ConnectionError(error='connection issue')
        attempt_event = self.adapter.feed('response-received', {
            'parsed_response': None,
            'context': self.context,
            'exception': wire_exception
        })
        self.mock_time.return_value = 4
        call_event = self.adapter.feed(
            'after-call-error', {
                'exception': wire_exception,
                'context': self.context
            }
        )
        self.assertEqual(
            call_event,
            APICallEvent(
                service=self.service_id,
                operation=self.wire_name,
                timestamp=1000,
                latency=3000,
                attempts=[attempt_event],
                retries_exceeded=True
            )
        )


class TestBaseMonitorEvent(unittest.TestCase):
    def test_init_self(self):
        event = BaseMonitorEvent(
            service='MyService', operation='MyOperation', timestamp=1000
        )
        self.assertEqual(event.service, 'MyService')
        self.assertEqual(event.operation, 'MyOperation')
        self.assertEqual(event.timestamp, 1000)

    def test_eq(self):
        self.assertEqual(
            BaseMonitorEvent(
                service='MyService', operation='MyOperation', timestamp=1000
            ),
            BaseMonitorEvent(
                service='MyService', operation='MyOperation', timestamp=1000
            )
        )

    def test_not_eq_different_classes(self):
        self.assertNotEqual(
            BaseMonitorEvent(
                service='MyService', operation='MyOperation', timestamp=1000
            ), object()
        )

    def test_not_eq_different_attrs(self):
        self.assertNotEqual(
            BaseMonitorEvent(
                service='MyService', operation='MyOperation', timestamp=1000
            ),
            BaseMonitorEvent(
                service='DifferentService', operation='DifferentOperation',
                timestamp=0
            )
        )


class TestAPICallEvent(unittest.TestCase):
    def test_init(self):
        event = APICallEvent(
            service='MyService', operation='MyOperation', timestamp=1000,
            latency=2000, attempts=[]
        )
        self.assertEqual(event.service, 'MyService')
        self.assertEqual(event.operation, 'MyOperation')
        self.assertEqual(event.timestamp, 1000)
        self.assertEqual(event.latency, 2000)
        self.assertEqual(event.attempts, [])

    def test_new_api_call_attempt_event(self):
        event = APICallEvent(
            service='MyService', operation='MyOperation', timestamp=1000,
            latency=2000, attempts=[]
        )
        attempt_event = event.new_api_call_attempt(timestamp=2000)
        self.assertEqual(
            attempt_event,
            APICallAttemptEvent(
                service='MyService', operation='MyOperation', timestamp=2000
            )
        )
        self.assertEqual(event.attempts, [attempt_event])


class TestAPICallAttemptEvent(unittest.TestCase):
    def test_init(self):
        url = 'https://us-east-1.myservice.amazonaws.com'
        parsed_error = {'Code': 'ErrorCode', 'Message': 'ErrorMessage'}
        wire_exception = Exception('Some wire exception')
        event = APICallAttemptEvent(
            service='MyService', operation='MyOperation', timestamp=1000,
            latency=2000, url=url, http_status_code=200, request_headers={},
            response_headers={}, parsed_error=parsed_error,
            wire_exception=wire_exception
        )
        self.assertEqual(event.service, 'MyService')
        self.assertEqual(event.operation, 'MyOperation')
        self.assertEqual(event.timestamp, 1000)
        self.assertEqual(event.latency, 2000)
        self.assertEqual(event.url, url)
        self.assertEqual(event.http_status_code, 200)
        self.assertEqual(event.request_headers, {})
        self.assertEqual(event.response_headers, {})
        self.assertEqual(event.parsed_error, parsed_error)
        self.assertEqual(event.wire_exception, wire_exception)


class TestCSMSerializer(unittest.TestCase):
    def setUp(self):
        self.csm_client_id = 'MyId'
        self.serializer = CSMSerializer(self.csm_client_id)
        self.service = 'MyService'
        self.operation = 'MyOperation'
        self.user_agent = 'my-user-agent'
        self.fqdn = 'us-east-1.myservice.amazonaws.com'
        self.url = 'https://' + self.fqdn
        self.timestamp = 1000
        self.latency = 2000
        self.request_headers = {
            'User-Agent': self.user_agent
        }

    def get_serialized_event_dict(self, event):
        serialized_event = self.serializer.serialize(event)
        return json.loads(serialized_event.decode('utf-8'))

    def test_validates_csm_client_id(self):
        max_client_id_len = 255
        with self.assertRaises(ValueError):
            CSMSerializer('a' * (max_client_id_len + 1))

    def test_serialize_produces_bytes(self):
        event = APICallEvent(
            service=self.service, operation=self.operation, timestamp=1000)
        serialized_event = self.serializer.serialize(event)
        self.assertIsInstance(serialized_event, six.binary_type)

    def test_serialize_does_not_add_whitespace(self):
        event = APICallEvent(
            service=self.service, operation=self.operation, timestamp=1000)
        serialized_event = self.serializer.serialize(event)
        self.assertIsNone(re.match(r'\s', serialized_event.decode('utf-8')))

    def test_serialize_api_call_event(self):
        event = APICallEvent(
            service=self.service, operation=self.operation, timestamp=1000)
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(
            serialized_event_dict, {
                'Version': 1,
                'Type': 'ApiCall',
                'Service': self.service,
                'Api': self.operation,
                'ClientId': self.csm_client_id,
                'MaxRetriesExceeded': 0,
                'Timestamp': 1000,
                'AttemptCount': 0,
            }
        )

    def test_serialize_api_call_event_with_latency(self):
        event = APICallEvent(
            service=self.service, operation=self.operation,
            timestamp=1000, latency=2000)
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(serialized_event_dict['Latency'], self.latency)

    def test_serialize_api_call_event_with_attempts(self):
        event = APICallEvent(
            service=self.service, operation=self.operation, timestamp=1000)
        event.new_api_call_attempt(2000)
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(serialized_event_dict['AttemptCount'], 1)

    def test_serialize_api_call_event_region(self):
        event = APICallEvent(
            service=self.service, operation=self.operation, timestamp=1000)
        attempt = event.new_api_call_attempt(2000)
        auth_value = (
            'AWS4-HMAC-SHA256 '
            'Credential=myaccesskey/20180523/my-region-1/ec2/aws4_request,'
            'SignedHeaders=content-type;host;x-amz-date, '
            'Signature=somesignature'

        )
        self.request_headers['Authorization'] = auth_value
        attempt.request_headers = self.request_headers
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(serialized_event_dict['Region'], 'my-region-1')

    def test_serialize_api_call_event_user_agent(self):
        event = APICallEvent(
            service=self.service, operation=self.operation, timestamp=1000)
        attempt = event.new_api_call_attempt(2000)
        attempt.request_headers = {'User-Agent': self.user_agent}
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(serialized_event_dict['UserAgent'], self.user_agent)

    def test_serialize_api_call_event_http_status_code(self):
        event = APICallEvent(
            service=self.service, operation=self.operation, timestamp=1000)
        attempt = event.new_api_call_attempt(2000)
        attempt.http_status_code = 200
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(serialized_event_dict['FinalHttpStatusCode'], 200)

    def test_serialize_api_call_event_parsed_error(self):
        event = APICallEvent(
            service=self.service, operation=self.operation, timestamp=1000)
        attempt = event.new_api_call_attempt(2000)
        attempt.parsed_error = {
            'Code': 'MyErrorCode',
            'Message': 'My error message'
        }
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(
            serialized_event_dict['FinalAwsException'], 'MyErrorCode')
        self.assertEqual(
            serialized_event_dict['FinalAwsExceptionMessage'],
            'My error message'
        )

    def test_serialize_api_call_event_wire_exception(self):
        event = APICallEvent(
            service=self.service, operation=self.operation, timestamp=1000)
        attempt = event.new_api_call_attempt(2000)
        attempt.wire_exception = Exception('Error on the wire')
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(
            serialized_event_dict['FinalSdkException'], 'Exception')
        self.assertEqual(
            serialized_event_dict['FinalSdkExceptionMessage'],
            'Error on the wire'
        )

    def test_serialize_api_call_event_with_retries_exceeded(self):
        event = APICallEvent(
            service=self.service, operation=self.operation, timestamp=1000,
            retries_exceeded=True)
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(serialized_event_dict['MaxRetriesExceeded'], 1)

    def test_serialize_api_call_attempt_event(self):
        event = APICallAttemptEvent(
            service=self.service, operation=self.operation,
            timestamp=self.timestamp)
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(
            serialized_event_dict, {
                'Version': 1,
                'Type': 'ApiCallAttempt',
                'Service': self.service,
                'Api': self.operation,
                'ClientId': self.csm_client_id,
                'Timestamp': self.timestamp,
            }
        )

    def test_serialize_api_call_attempt_event_with_latency(self):
        event = APICallAttemptEvent(
            service=self.service, operation=self.operation,
            timestamp=self.timestamp, latency=self.latency)
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(serialized_event_dict['AttemptLatency'], self.latency)

    def test_serialize_with_user_agent(self):
        event = APICallAttemptEvent(
            service=self.service, operation=self.operation,
            timestamp=self.timestamp,
            request_headers={'User-Agent': self.user_agent}
        )
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(serialized_event_dict['UserAgent'], self.user_agent)

    def test_serialize_with_url(self):
        event = APICallAttemptEvent(
            service=self.service, operation=self.operation,
            timestamp=self.timestamp, url=self.url)
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(serialized_event_dict['Fqdn'], self.fqdn)

    def test_serialize_with_s3_signing(self):
        auth_value = 'AWS myaccesskey:somesignature'
        self.request_headers['Authorization'] = auth_value
        event = APICallAttemptEvent(
            service=self.service, operation=self.operation,
            timestamp=self.timestamp, request_headers=self.request_headers)
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(serialized_event_dict['AccessKey'], 'myaccesskey')

    def test_serialize_with_sigv4_sigining(self):
        auth_value = (
            'AWS4-HMAC-SHA256 '
            'Credential=myaccesskey/20180523/my-region-1/ec2/aws4_request,'
            'SignedHeaders=content-type;host;x-amz-date, '
            'Signature=somesignature'

        )
        self.request_headers['Authorization'] = auth_value
        event = APICallAttemptEvent(
            service=self.service, operation=self.operation,
            timestamp=self.timestamp, request_headers=self.request_headers)
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(serialized_event_dict['AccessKey'], 'myaccesskey')

    def test_serialize_with_session_token(self):
        self.request_headers['X-Amz-Security-Token'] = 'my-security-token'
        event = APICallAttemptEvent(
            service=self.service, operation=self.operation,
            timestamp=self.timestamp, request_headers=self.request_headers)
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(
            serialized_event_dict['SessionToken'], 'my-security-token')

    def test_serialize_with_path_parameters_in_url(self):
        self.url = 'https://' + self.fqdn + '/resource'
        event = APICallAttemptEvent(
            service=self.service, operation=self.operation,
            timestamp=self.timestamp, url=self.url)
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(serialized_event_dict['Fqdn'], self.fqdn)

    def test_serialize_with_request_id_headers(self):
        response_headers = {
            'x-amzn-requestid': 'id1',
            'x-amz-request-id': 'id2',
            'x-amz-id-2': 'id3',
        }
        event = APICallAttemptEvent(
            service=self.service, operation=self.operation,
            timestamp=self.timestamp, response_headers=response_headers)
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(serialized_event_dict['XAmznRequestId'], 'id1')
        self.assertEqual(serialized_event_dict['XAmzRequestId'], 'id2')
        self.assertEqual(serialized_event_dict['XAmzId2'], 'id3')

    def test_serialize_filters_unwanted_response_headers(self):
        response_headers = {'filter-out': 'do-not-include-this'}
        event = APICallAttemptEvent(
            service=self.service, operation=self.operation,
            timestamp=self.timestamp, response_headers=response_headers)
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(
            serialized_event_dict, {
                'Version': 1,
                'Type': 'ApiCallAttempt',
                'Service': self.service,
                'Api': self.operation,
                'ClientId': self.csm_client_id,
                'Timestamp': self.timestamp,
            }
        )

    def test_serialize_with_status_code(self):
        event = APICallAttemptEvent(
            service=self.service, operation=self.operation,
            timestamp=self.timestamp, http_status_code=200)
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(serialized_event_dict['HttpStatusCode'], 200)

    def test_serialize_with_service_error(self):
        event = APICallAttemptEvent(
            service=self.service, operation=self.operation,
            timestamp=self.timestamp, parsed_error={
                'Code': 'MyErrorCode',
                'Message': 'My error message'
            }
        )
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(serialized_event_dict['AwsException'], 'MyErrorCode')
        self.assertEqual(
            serialized_event_dict['AwsExceptionMessage'], 'My error message')

    def test_serialize_with_wire_exception(self):
        event = APICallAttemptEvent(
            service=self.service, operation=self.operation,
            timestamp=self.timestamp,
            wire_exception=Exception('Error on the wire')
        )
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(serialized_event_dict['SdkException'], 'Exception')
        self.assertEqual(
            serialized_event_dict['SdkExceptionMessage'], 'Error on the wire')

    def test_serialize_truncates_long_user_agent(self):
        max_user_agent_length = 256
        user_agent = 'a' * (max_user_agent_length + 1)
        event = APICallAttemptEvent(
            service=self.service, operation=self.operation,
            timestamp=self.timestamp,
            request_headers={'User-Agent': user_agent}
        )
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(
            serialized_event_dict['UserAgent'],
            user_agent[:max_user_agent_length]
        )

    def test_serialize_truncates_long_service_error(self):
        max_error_code_length = 128
        max_error_message_length = 512
        long_error_code = 'c' * (max_error_code_length + 1)
        long_error_message = 'm' * (max_error_message_length + 1)
        event = APICallAttemptEvent(
            service=self.service, operation=self.operation,
            timestamp=self.timestamp, parsed_error={
                'Code': long_error_code,
                'Message': long_error_message
            }
        )
        serialized_event_dict = self.get_serialized_event_dict(event)
        self.assertEqual(
            serialized_event_dict['AwsException'],
            long_error_code[:max_error_code_length]
        )
        self.assertEqual(
            serialized_event_dict['AwsExceptionMessage'],
            long_error_message[:max_error_message_length]
        )

    def test_serialize_truncates_long_wire_exception(self):
        max_class_name_length = 128
        max_error_message_length = 512
        long_class_name = 'W' * (max_class_name_length + 1)
        wire_class = type(long_class_name, (Exception,), {})
        long_error_message = 'm' * (max_error_message_length + 1)
        event = APICallAttemptEvent(
            service=self.service, operation=self.operation,
            timestamp=self.timestamp,
            wire_exception=wire_class(long_error_message)
        )
        serialized_event_dict = self.get_serialized_event_dict(event)

        self.assertEqual(
            serialized_event_dict['SdkException'],
            long_class_name[:max_class_name_length]
        )
        self.assertEqual(
            serialized_event_dict['SdkExceptionMessage'],
            long_error_message[:max_error_message_length]
        )


class TestSocketPublisher(unittest.TestCase):
    def setUp(self):
        self.socket = mock.Mock(socket.socket)
        self.host = '127.0.0.1'
        self.port = 31000
        self.serializer = mock.Mock(CSMSerializer)
        self.publisher = SocketPublisher(
            self.socket, self.host, self.port, self.serializer)

    def test_publish(self):
        event = object()
        self.serializer.serialize.return_value = b'serialized event'
        self.publisher.publish(event)
        self.serializer.serialize.assert_called_with(event)
        self.socket.sendto.assert_called_with(
            b'serialized event', (self.host, self.port))

    def test_skips_publishing_over_max_size(self):
        event = mock.Mock(APICallAttemptEvent)
        max_event_size = 8 * 1024
        self.serializer.serialize.return_value = b'a' * (max_event_size + 1)
        self.publisher.publish(event)
        self.socket.sendto.assert_not_called()
