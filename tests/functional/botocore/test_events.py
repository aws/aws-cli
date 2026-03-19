# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests import BaseSessionTest, mock


class RecordingHandler:
    def __init__(self):
        self.recorded_events = []

    def record(self, event_name, **kwargs):
        self.recorded_events.append((event_name, kwargs))


class TestClientEvents(BaseSessionTest):
    def setUp(self):
        super().setUp()
        self.region = 'us-west-2'
        self.client = self.session.create_client('ec2', self.region)

    def test_emit_response_received(self):
        recording_handler = RecordingHandler()
        self.client.meta.events.register(
            'response-received.ec2.DescribeRegions', recording_handler.record
        )
        with mock.patch(
            'botocore.httpsession.URLLib3Session.send'
        ) as mock_send:
            response_body = (
                b'<?xml version="1.0" ?>'
                b'<DescribeRegionsResponse xmlns="">'
                b'</DescribeRegionsResponse>'
            )
            mock_send.return_value = mock.Mock(
                status_code=200, headers={}, content=response_body
            )
            self.client.describe_regions()
        self.assertEqual(
            recording_handler.recorded_events,
            [
                (
                    'response-received.ec2.DescribeRegions',
                    {
                        'exception': None,
                        'response_dict': {
                            'body': response_body,
                            'headers': {},
                            'context': mock.ANY,
                            'status_code': 200,
                        },
                        'parsed_response': {'ResponseMetadata': mock.ANY},
                        'context': mock.ANY,
                    },
                )
            ],
        )

    def test_emit_response_received_for_exception(self):
        recording_handler = RecordingHandler()
        self.client.meta.events.register(
            'response-received.ec2.DescribeRegions', recording_handler.record
        )
        with mock.patch(
            'botocore.httpsession.URLLib3Session.send'
        ) as mock_send:
            raised_exception = RuntimeError('Unexpected exception')
            mock_send.side_effect = raised_exception
            with self.assertRaises(RuntimeError):
                self.client.describe_regions()
        self.assertEqual(
            recording_handler.recorded_events,
            [
                (
                    'response-received.ec2.DescribeRegions',
                    {
                        'exception': raised_exception,
                        'response_dict': None,
                        'parsed_response': None,
                        'context': mock.ANY,
                    },
                )
            ],
        )
