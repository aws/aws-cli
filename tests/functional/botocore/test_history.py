from botocore.history import BaseHistoryHandler, get_global_history_recorder
from tests import BaseSessionTest, ClientHTTPStubber


class RecordingHandler(BaseHistoryHandler):
    def __init__(self):
        self.recorded_calls = []

    def emit(self, event_type, payload, source):
        self.recorded_calls.append((event_type, payload, source))


class TestRecordStatementsInjections(BaseSessionTest):
    def setUp(self):
        super().setUp()
        self.client = self.session.create_client('s3', 'us-west-2')
        self.http_stubber = ClientHTTPStubber(self.client)
        self.s3_response_body = (
            b'<ListAllMyBucketsResult '
            b'    xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
            b'  <Owner>'
            b'    <ID>d41d8cd98f00b204e9800998ecf8427e</ID>'
            b'    <DisplayName>foo</DisplayName>'
            b'  </Owner>'
            b'  <Buckets>'
            b'    <Bucket>'
            b'      <Name>bar</Name>'
            b'      <CreationDate>1912-06-23T22:57:02.000Z</CreationDate>'
            b'    </Bucket>'
            b'  </Buckets>'
            b'</ListAllMyBucketsResult>'
        )
        self.recording_handler = RecordingHandler()
        history_recorder = get_global_history_recorder()
        history_recorder.enable()
        history_recorder.add_handler(self.recording_handler)

    def _get_all_events_of_type(self, event_type):
        recorded_calls = self.recording_handler.recorded_calls
        matching = [call for call in recorded_calls if call[0] == event_type]
        return matching

    def test_does_record_api_call(self):
        self.http_stubber.add_response(body=self.s3_response_body)
        with self.http_stubber:
            self.client.list_buckets()

        api_call_events = self._get_all_events_of_type('API_CALL')
        self.assertEqual(len(api_call_events), 1)
        event = api_call_events[0]
        event_type, payload, source = event
        self.assertEqual(
            payload,
            {'operation': 'ListBuckets', 'params': {}, 'service': 's3'},
        )
        self.assertEqual(source, 'BOTOCORE')

    def test_does_record_http_request(self):
        self.http_stubber.add_response(body=self.s3_response_body)
        with self.http_stubber:
            self.client.list_buckets()

        http_request_events = self._get_all_events_of_type('HTTP_REQUEST')
        self.assertEqual(len(http_request_events), 1)
        event = http_request_events[0]
        event_type, payload, source = event

        method = payload['method']
        self.assertEqual(method, 'GET')

        # The header values vary too much per request to verify them here.
        # Instead just check the presense of each expected header.
        headers = payload['headers']
        for expected_header in [
            'Authorization',
            'User-Agent',
            'X-Amz-Date',
            'X-Amz-Content-SHA256',
        ]:
            self.assertIn(expected_header, headers)

        body = payload['body']
        self.assertIsNone(body)

        streaming = payload['streaming']
        self.assertEqual(streaming, False)

        url = payload['url']
        self.assertEqual(url, 'https://s3.us-west-2.amazonaws.com/')

        self.assertEqual(source, 'BOTOCORE')

    def test_does_record_http_response(self):
        self.http_stubber.add_response(body=self.s3_response_body)
        with self.http_stubber:
            self.client.list_buckets()

        http_response_events = self._get_all_events_of_type('HTTP_RESPONSE')
        self.assertEqual(len(http_response_events), 1)
        event = http_response_events[0]
        event_type, payload, source = event

        self.assertEqual(
            payload,
            {
                'status_code': 200,
                'headers': {},
                'streaming': False,
                'body': self.s3_response_body,
                'context': {'operation_name': 'ListBuckets'},
            },
        )
        self.assertEqual(source, 'BOTOCORE')

    def test_does_record_parsed_response(self):
        self.http_stubber.add_response(body=self.s3_response_body)
        with self.http_stubber:
            self.client.list_buckets()

        parsed_response_events = self._get_all_events_of_type(
            'PARSED_RESPONSE'
        )
        self.assertEqual(len(parsed_response_events), 1)
        event = parsed_response_events[0]
        event_type, payload, source = event

        # Given that the request contains headers with a user agent string
        # a date and a signature we need to disassemble the call and manually
        # assert the interesting bits since mock can only assert if the args
        # all match exactly.
        owner = payload['Owner']
        self.assertEqual(
            owner,
            {'DisplayName': 'foo', 'ID': 'd41d8cd98f00b204e9800998ecf8427e'},
        )

        buckets = payload['Buckets']
        self.assertEqual(len(buckets), 1)
        bucket = buckets[0]
        self.assertEqual(bucket['Name'], 'bar')

        metadata = payload['ResponseMetadata']
        self.assertEqual(
            metadata,
            {'HTTPHeaders': {}, 'HTTPStatusCode': 200, 'RetryAttempts': 0},
        )
