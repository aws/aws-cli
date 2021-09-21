# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os
import re
import json
import threading
import datetime
import numbers

import mock

from awscli.compat import queue
from awscli.customizations.history.db import DatabaseConnection
from awscli.customizations.history.db import DatabaseHistoryHandler
from awscli.customizations.history.db import DatabaseRecordWriter
from awscli.customizations.history.db import DatabaseRecordReader
from awscli.customizations.history.db import PayloadSerializer
from awscli.customizations.history.db import RecordBuilder
from awscli.testutils import unittest, FileCreator
from tests import CaseInsensitiveDict


class FakeDatabaseConnection(object):
    def __init__(self):
        self.execute = mock.MagicMock()
        self.closed = False

    def close(self):
        self.closed = True


class TestGetHistoryDBFilename(unittest.TestCase):
    def setUp(self):
        self.files = FileCreator()

    def tearDown(self):
        self.files.remove_all()


class TestDatabaseConnection(unittest.TestCase):
    @mock.patch('awscli.compat.sqlite3.connect')
    def test_can_connect_to_argument_file(self, mock_connect):
        expected_location = os.path.expanduser(os.path.join(
            '~', 'foo', 'bar', 'baz.db'))
        DatabaseConnection(expected_location)
        mock_connect.assert_called_with(
            expected_location, check_same_thread=False, isolation_level=None)

    @mock.patch('awscli.compat.sqlite3.connect')
    def test_does_try_to_enable_wal(self, mock_connect):
        conn = DatabaseConnection(':memory:')
        conn._connection.execute.assert_any_call('PRAGMA journal_mode=WAL')

    def test_does_ensure_table_created_first(self):
        db = DatabaseConnection(":memory:")
        cursor = db.execute('PRAGMA table_info(records)')
        schema = [col[:3] for col in cursor.fetchall()]
        expected_schema = [
            (0, 'id', 'TEXT'),
            (1, 'request_id', 'TEXT'),
            (2, 'source', 'TEXT'),
            (3, 'event_type', 'TEXT'),
            (4, 'timestamp', 'INTEGER'),
            (5, 'payload', 'TEXT'),
        ]
        self.assertEqual(expected_schema, schema)

    @mock.patch('awscli.compat.sqlite3.connect')
    def test_can_close(self, mock_connect):
        connection = mock.Mock()
        mock_connect.return_value = connection
        conn = DatabaseConnection(':memory:')
        conn.close()
        self.assertTrue(connection.close.called)


class TestDatabaseHistoryHandler(unittest.TestCase):
    UUID_PATTERN = re.compile(
        '^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$',
        re.I
    )

    def test_emit_does_write_cli_rc_record(self):
        writer = mock.Mock(DatabaseRecordWriter)
        record_builder = RecordBuilder()
        handler = DatabaseHistoryHandler(writer, record_builder)
        handler.emit('CLI_RC', 0, 'CLI')
        call = writer.write_record.call_args[0][0]
        self.assertEqual(call, {
                    'command_id': mock.ANY,
                    'event_type': 'CLI_RC',
                    'payload': 0,
                    'source': 'CLI',
                    'timestamp': mock.ANY
        })
        self.assertTrue(self.UUID_PATTERN.match(call['command_id']))
        self.assertIsInstance(call['timestamp'], numbers.Number)

    def test_emit_does_write_cli_version_record(self):
        writer = mock.Mock(DatabaseRecordWriter)
        record_builder = RecordBuilder()
        handler = DatabaseHistoryHandler(writer, record_builder)
        handler.emit('CLI_VERSION', 'Version Info', 'CLI')
        call = writer.write_record.call_args[0][0]
        self.assertEqual(call, {
                    'command_id': mock.ANY,
                    'event_type': 'CLI_VERSION',
                    'payload': 'Version Info',
                    'source': 'CLI',
                    'timestamp': mock.ANY
        })
        self.assertTrue(self.UUID_PATTERN.match(call['command_id']))
        self.assertIsInstance(call['timestamp'], numbers.Number)

    def test_emit_does_write_api_call_record(self):
        writer = mock.Mock(DatabaseRecordWriter)
        record_builder = RecordBuilder()
        handler = DatabaseHistoryHandler(writer, record_builder)
        payload = {'foo': 'bar'}
        handler.emit('API_CALL', payload, 'BOTOCORE')
        call = writer.write_record.call_args[0][0]
        self.assertEqual(call, {
                    'command_id': mock.ANY,
                    'request_id': mock.ANY,
                    'event_type': 'API_CALL',
                    'payload': payload,
                    'source': 'BOTOCORE',
                    'timestamp': mock.ANY
        })
        self.assertTrue(self.UUID_PATTERN.match(call['command_id']))
        self.assertTrue(self.UUID_PATTERN.match(call['request_id']))

    def test_emit_does_write_http_request_record(self):
        writer = mock.Mock(DatabaseRecordWriter)
        record_builder = RecordBuilder()
        handler = DatabaseHistoryHandler(writer, record_builder)
        payload = {'body': b'data'}
        # In order for an http_request to have a request_id it must have been
        # preceeded by an api_call record.
        handler.emit('API_CALL', '', 'BOTOCORE')
        handler.emit('HTTP_REQUEST', payload, 'BOTOCORE')
        call = writer.write_record.call_args[0][0]
        self.assertEqual(call, {
                    'command_id': mock.ANY,
                    'request_id': mock.ANY,
                    'event_type': 'HTTP_REQUEST',
                    'payload': payload,
                    'source': 'BOTOCORE',
                    'timestamp': mock.ANY
        })
        self.assertTrue(self.UUID_PATTERN.match(call['command_id']))
        self.assertTrue(self.UUID_PATTERN.match(call['request_id']))

    def test_emit_does_write_http_response_record(self):
        writer = mock.Mock(DatabaseRecordWriter)
        record_builder = RecordBuilder()
        handler = DatabaseHistoryHandler(writer, record_builder)
        payload = {'body': b'data'}
        # In order for an http_response to have a request_id it must have been
        # preceeded by an api_call record.
        handler.emit('API_CALL', '', 'BOTOCORE')
        handler.emit('HTTP_RESPONSE', payload, 'BOTOCORE')
        call = writer.write_record.call_args[0][0]
        self.assertEqual(call, {
                    'command_id': mock.ANY,
                    'request_id': mock.ANY,
                    'event_type': 'HTTP_RESPONSE',
                    'payload': payload,
                    'source': 'BOTOCORE',
                    'timestamp': mock.ANY
        })
        self.assertTrue(self.UUID_PATTERN.match(call['command_id']))
        self.assertTrue(self.UUID_PATTERN.match(call['request_id']))

    def test_emit_does_write_parsed_response_record(self):
        writer = mock.Mock(DatabaseRecordWriter)
        record_builder = RecordBuilder()
        handler = DatabaseHistoryHandler(writer, record_builder)
        payload = {'metadata': {'data': 'foobar'}}
        # In order for an http_response to have a request_id it must have been
        # preceeded by an api_call record.
        handler.emit('API_CALL', '', 'BOTOCORE')
        handler.emit('PARSED_RESPONSE', payload, 'BOTOCORE')
        call = writer.write_record.call_args[0][0]
        self.assertEqual(call, {
                    'command_id': mock.ANY,
                    'request_id': mock.ANY,
                    'event_type': 'PARSED_RESPONSE',
                    'payload': payload,
                    'source': 'BOTOCORE',
                    'timestamp': mock.ANY
        })
        self.assertTrue(self.UUID_PATTERN.match(call['command_id']))
        self.assertTrue(self.UUID_PATTERN.match(call['request_id']))


class BaseDatabaseRecordTester(unittest.TestCase):
    def assert_contains_lines_in_order(self, lines, contents):
        for line in lines:
            self.assertIn(line, contents)
            beginning = contents.find(line)
            contents = contents[(beginning + len(line)):]


class BaseDatabaseRecordWriterTester(BaseDatabaseRecordTester):
    UUID_PATTERN = re.compile(
        '^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$',
        re.I
    )

    def setUp(self):
        self.db = DatabaseConnection(':memory:')
        self.writer = DatabaseRecordWriter(self.db)


class TestDatabaseRecordWriter(BaseDatabaseRecordWriterTester):
    def setUp(self):
        super(TestDatabaseRecordWriter, self).setUp()

    def _read_last_record(self):
        cursor = self.db.execute('SELECT * FROM records')
        written_record = cursor.fetchone()
        return written_record

    def test_can_close(self):
        connection = mock.Mock()
        writer = DatabaseRecordWriter(connection)
        writer.close()
        self.assertTrue(connection.close.called)

    def test_can_write_record(self):
        self.writer.write_record({
            'command_id': 'command',
            'event_type': 'FOO',
            'payload': 'bar',
            'source': 'TEST',
            'timestamp': 1234
        })

        # Now that we have verified the order of the fields in the insert
        # statement we can verify that the record values are in the correct
        # order in the tuple.
        # (command_id, request_id, source, event_type, timestamp, payload)
        written_record = self._read_last_record()
        self.assertEqual(written_record,
                         ('command', None, 'TEST', 'FOO', 1234, '"bar"'))

    def test_commit_count_matches_write_count(self):
        records_to_write = 10
        for _ in range(records_to_write):
            self.writer.write_record({
                'command_id': 'command',
                'event_type': 'foo',
                'payload': '',
                'source': 'TEST',
                'timestamp': 1234
            })
        cursor = self.db.execute('SELECT COUNT(*) FROM records')
        record_count = cursor.fetchone()[0]

        self.assertEqual(record_count, records_to_write)

    def test_can_write_cli_version_record(self):
        self.writer.write_record({
            'command_id': 'command',
            'event_type': 'CLI_VERSION',
            'payload': ('aws-cli/1.11.184 Python/3.6.2 Darwin/15.6.0 '
                        'botocore/1.7.42'),
            'source': 'TEST',
            'timestamp': 1234
        })
        written_record = self._read_last_record()

        self.assertEqual(
            written_record,
            ('command', None, 'TEST', 'CLI_VERSION', 1234,
             '"aws-cli/1.11.184 Python/3.6.2 Darwin/15.6.0 botocore/1.7.42"')
        )

    def test_can_write_cli_arguments_record(self):
        self.writer.write_record({
            'command_id': 'command',
            'event_type': 'CLI_ARGUMENTS',
            'payload': ['s3', 'ls'],
            'source': 'TEST',
            'timestamp': 1234
        })

        written_record = self._read_last_record()
        self.assertEqual(
            written_record,
            ('command', None, 'TEST', 'CLI_ARGUMENTS', 1234, '["s3", "ls"]')
        )

    def test_can_write_api_call_record(self):
        self.writer.write_record({
            'command_id': 'command',
            'event_type': 'API_CALL',
            'payload': {
                'service': 's3',
                'operation': 'ListBuckets',
                'params': {},
            },
            'source': 'TEST',
            'timestamp': 1234
        })

        written_record = self._read_last_record()
        self.assertEqual(
            written_record,
            ('command', None, 'TEST', 'API_CALL', 1234, json.dumps({
                'service': 's3',
                'operation': 'ListBuckets',
                'params': {},
            }))
        )

    def test_can_write_http_request_record(self):
        self.writer.write_record({
            'command_id': 'command',
            'event_type': 'HTTP_REQUEST',
            'payload': {
                'method': 'GET',
                'headers': CaseInsensitiveDict({}),
                'body': '...',
            },
            'source': 'TEST',
            'timestamp': 1234
        })

        written_record = self._read_last_record()
        self.assertEqual(
            written_record,
            ('command', None, 'TEST', 'HTTP_REQUEST', 1234, json.dumps({
                'method': 'GET',
                'headers': {},
                'body': '...',
            }))
        )

    def test_can_write_http_response_record(self):
        self.writer.write_record({
            'command_id': 'command',
            'event_type': 'HTTP_RESPONSE',
            'payload': {
                'streaming': False,
                'headers': {},
                'body': '...',
                'status_code': 200,
                'request_id': '1234abcd'
            },
            'source': 'TEST',
            'timestamp': 1234
        })

        written_record = self._read_last_record()
        self.assertEqual(
            written_record,
            ('command', None, 'TEST', 'HTTP_RESPONSE', 1234, json.dumps({
                'streaming': False,
                'headers': {},
                'body': '...',
                'status_code': 200,
                'request_id': '1234abcd'
            }))
        )

    def test_can_write_parsed_response_record(self):
        self.writer.write_record({
            'command_id': 'command',
            'event_type': 'PARSED_RESPONSE',
            'payload': {},
            'source': 'TEST',
            'timestamp': 1234
        })

        written_record = self._read_last_record()
        self.assertEqual(
            written_record,
            ('command', None, 'TEST', 'PARSED_RESPONSE', 1234, '{}')
        )

    def test_can_write_cli_rc_record(self):
        self.writer.write_record({
            'command_id': 'command',
            'event_type': 'CLI_RC',
            'payload': 0,
            'source': 'TEST',
            'timestamp': 1234
        })

        written_record = self._read_last_record()
        self.assertEqual(
            written_record,
            ('command', None, 'TEST', 'CLI_RC', 1234, '0')
        )


class ThreadedRecordBuilder(object):
    def __init__(self, tracker):
        self._read_q = queue.Queue()
        self._write_q = queue.Queue()
        self._thread = threading.Thread(
            target=self._threaded_request_tracker,
            args=(tracker,))

    def _threaded_request_tracker(self, builder):
        while True:
            event_type = self._read_q.get()
            if event_type is False:
                return
            payload = {'body': b''}
            request_id = builder.build_record(event_type, payload, '')
            self._write_q.put_nowait(request_id)

    def read_n_results(self, n):
        records = [self._write_q.get() for _ in range(n)]
        return records

    def request_id_for_event(self, event_type):
        self._read_q.put_nowait(event_type)

    def start(self):
        self._thread.start()

    def close(self):
        self._read_q.put_nowait(False)
        self._thread.join()


class TestMultithreadRequestId(unittest.TestCase):
    def setUp(self):
        self.builder = RecordBuilder()
        self.threads = []

    def tearDown(self):
        for t in self.threads:
            t.close()

    def start_n_threads(self, n):
        for _ in range(n):
            t = ThreadedRecordBuilder(self.builder)
            t.start()
            self.threads.append(t)

    def test_each_thread_has_separate_request_id(self):
        self.start_n_threads(2)
        self.threads[0].request_id_for_event('API_CALL')
        self.threads[0].request_id_for_event('HTTP_REQUEST')
        self.threads[1].request_id_for_event('API_CALL')
        self.threads[1].request_id_for_event('HTTP_REQUEST')

        a_records = self.threads[0].read_n_results(2)
        b_records = self.threads[1].read_n_results(2)

        # Each thread should have its own set of request_ids so the request
        # ids in each set of records should match, but should not match the
        # request_ids from the other thread.
        a_request_ids = [record['request_id'] for record in a_records]
        self.assertEqual(len(a_request_ids), 2)
        self.assertEqual(a_request_ids[0], a_request_ids[1])
        thread_a_request_id = a_request_ids[0]

        b_request_ids = [record['request_id'] for record in b_records]
        self.assertEqual(len(b_request_ids), 2)
        self.assertEqual(b_request_ids[0], b_request_ids[1])
        thread_b_request_id = b_request_ids[0]

        # Since the request_id is reset by the API_CALL record being written
        # and thread b has now written an API_CALL record the request id has
        # been reset once. To ensure this doesnt bleed over to other threads
        # we will write another record in thread a and ensure that it's
        # request_id matches the previous ones from thread a rather than then
        # thread b request_id
        self.threads[0].request_id_for_event('HTTP_RESPONSE')
        self.threads[1].request_id_for_event('HTTP_RESPONSE')
        a_record = self.threads[0].read_n_results(1)[0]
        b_record = self.threads[1].read_n_results(1)[0]
        self.assertEqual(a_record['request_id'], thread_a_request_id)
        self.assertEqual(b_record['request_id'], thread_b_request_id)


class TestDatabaseRecordReader(BaseDatabaseRecordTester):
    def setUp(self):
        self.fake_connection = FakeDatabaseConnection()
        self.reader = DatabaseRecordReader(self.fake_connection)

    def test_can_close(self):
        self.reader.close()
        self.assertTrue(self.fake_connection.closed)

    def test_row_factory_set(self):
        self.assertEqual(self.fake_connection.row_factory,
                         self.reader._row_factory)

    def test_iter_latest_records_performs_correct_query(self):
        expected_query = (
            '    SELECT * FROM records\n'
            '        WHERE id =\n'
            '        (SELECT id FROM records WHERE timestamp =\n'
            '        (SELECT max(timestamp) FROM records)) ORDER BY timestamp;'
        )
        [_ for _ in self.reader.iter_latest_records()]
        self.assertEqual(
            self.fake_connection.execute.call_args[0][0].strip(),
            expected_query.strip())

    def test_iter_latest_records_does_iter_records(self):
        records_to_get = [1, 2, 3]
        self.fake_connection.execute.return_value.__iter__.return_value = iter(
            records_to_get)
        records = [r for r in self.reader.iter_latest_records()]
        self.assertEqual(records, records_to_get)

    def test_iter_records_performs_correct_query(self):
        expected_query = ('SELECT * from records where id = ? '
                          'ORDER BY timestamp')
        [_ for _ in self.reader.iter_records('fake_id')]
        self.assertEqual(
            self.fake_connection.execute.call_args[0][0].strip(),
            expected_query.strip())

    def test_iter_records_does_iter_records(self):
        records_to_get = [1, 2, 3]
        self.fake_connection.execute.return_value.__iter__.return_value = iter(
            records_to_get)
        records = [r for r in self.reader.iter_records('fake_id')]
        self.assertEqual(records, records_to_get)


class TestPayloadSerialzier(unittest.TestCase):
    def test_can_serialize_basic_types(self):
        original = {
            'string': 'foo',
            'int': 4,
            'list': [1, 2, 'bar'],
            'dict': {
                'sun': 'moon'
            },
            'float': 1.2
        }
        string_value = json.dumps(original, cls=PayloadSerializer)
        reloaded = json.loads(string_value)
        self.assertEqual(original, reloaded)

    def test_can_serialize_datetime(self):
        now = datetime.datetime.now()
        iso_now = now.isoformat()
        string_value = json.dumps(now, cls=PayloadSerializer)
        reloaded = json.loads(string_value)
        self.assertEqual(iso_now, reloaded)

    def test_can_serialize_case_insensitive_dict(self):
        original = CaseInsensitiveDict({
            'fOo': 'bar'
        })
        string_value = json.dumps(original, cls=PayloadSerializer)
        reloaded = json.loads(string_value)
        self.assertEqual(original, reloaded)

    def test_can_serialize_unknown_type(self):
        original = queue.Queue()
        encoded = repr(original)
        string_value = json.dumps(original, cls=PayloadSerializer)
        reloaded = json.loads(string_value)
        self.assertEqual(encoded, reloaded)

    def test_can_serialize_non_utf_8_bytes_type(self):
        original = b'\xfe\xed'  # Non utf-8 byte squence
        encoded = '<Byte sequence>'
        string_value = json.dumps(original, cls=PayloadSerializer)
        reloaded = json.loads(string_value)
        self.assertEqual(encoded, reloaded)

    def test_does_preserve_utf_8_bytes_type(self):
        original = b'foobar'  # utf-8 byte squence
        encoded = 'foobar'
        string_value = json.dumps(original, cls=PayloadSerializer)
        reloaded = json.loads(string_value)
        self.assertEqual(encoded, reloaded)

    def test_can_serialize_non_utf_8_bytes_type_in_dict(self):
        original = {'foo': 'bar', 'bytes': b'\xfe\xed'}
        encoded = {'foo': 'bar', 'bytes': '<Byte sequence>'}
        string_value = json.dumps(original, cls=PayloadSerializer)
        reloaded = json.loads(string_value)
        self.assertEqual(encoded, reloaded)

    def test_can_serialize_non_utf_8_bytes_type_in_list(self):
        original = ['foo', b'\xfe\xed']
        encoded = ['foo', '<Byte sequence>']
        string_value = json.dumps(original, cls=PayloadSerializer)
        reloaded = json.loads(string_value)
        self.assertEqual(encoded, reloaded)

    def test_can_serialize_non_utf_8_bytes_type_in_tuple(self):
        original = ('foo', b'\xfe\xed')
        encoded = ['foo', '<Byte sequence>']
        string_value = json.dumps(original, cls=PayloadSerializer)
        reloaded = json.loads(string_value)
        self.assertEqual(encoded, reloaded)

    def test_can_serialize_non_utf_8_bytes_nested(self):
        original = {
            'foo': 'bar',
            'bytes': b'\xfe\xed',
            'list': ['foo', b'\xfe\xed'],
            'more_nesting': {
                'bytes': b'\xfe\xed',
                'tuple': ('bar', 'baz', b'\xfe\ed')
            }
        }
        encoded = {
            'foo': 'bar',
            'bytes': '<Byte sequence>',
            'list': ['foo', '<Byte sequence>'],
            'more_nesting': {
                'bytes': '<Byte sequence>',
                'tuple': ['bar', 'baz', '<Byte sequence>']
            }
        }
        string_value = json.dumps(original, cls=PayloadSerializer)
        reloaded = json.loads(string_value)
        self.assertEqual(encoded, reloaded)


class TestRecordBuilder(unittest.TestCase):
    UUID_PATTERN = re.compile(
        '^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$',
        re.I
    )

    def setUp(self):
        self.builder = RecordBuilder()

    def _get_request_id_for_event_type(self, event_type):
        record = self.builder.build_record(event_type, {'body': b''}, '')
        return record.get('request_id')

    def test_does_inject_timestamp(self):
        record = self.builder.build_record('TEST', '', '')
        self.assertTrue('timestamp' in record)
        self.assertTrue(isinstance(record['timestamp'], numbers.Number))

    def test_does_inject_command_id(self):
        record = self.builder.build_record('TEST', '', '')
        self.assertTrue('timestamp' in record)
        self.assertTrue(isinstance(record['timestamp'], numbers.Number))
        self.assertTrue('command_id' in record)
        self.assertTrue(self.UUID_PATTERN.match(record['command_id']))

    def test_does_create_record_with_correct_fields(self):
        record = self.builder.build_record('type', 'payload', 'source')
        self.assertEqual(record['event_type'], 'type')
        self.assertEqual(record['payload'], 'payload')
        self.assertEqual(record['source'], 'source')
        self.assertTrue('command_id' in record)
        self.assertTrue('timestamp' in record)

    def test_can_process_http_request_with_none_body(self):
        try:
            self.builder.build_record('HTTP_REQUEST', {'body': None}, '')
        except ValueError:
            self.fail("Should not raise value error")

    def test_can_process_http_response_with_nono_body(self):
        try:
            self.builder.build_record('HTTP_RESPONSE', {'body': None}, '')
        except ValueError:
            self.fail("Should not raise value error")

    def test_can_get_request_id_from_api_call(self):
        identifier = self._get_request_id_for_event_type('API_CALL')
        self.assertTrue(self.UUID_PATTERN.match(identifier))

    def test_does_get_id_for_http_request_with_api_call(self):
        call_identifier = self._get_request_id_for_event_type('API_CALL')
        request_identifier = self._get_request_id_for_event_type(
            'HTTP_REQUEST')

        self.assertEqual(call_identifier, request_identifier)
        self.assertTrue(self.UUID_PATTERN.match(call_identifier))

    def test_does_get_id_for_http_response_with_api_call(self):
        call_identifier = self._get_request_id_for_event_type('API_CALL')
        response_identifier = self._get_request_id_for_event_type(
            'HTTP_RESPONSE')

        self.assertEqual(call_identifier, response_identifier)
        self.assertTrue(self.UUID_PATTERN.match(call_identifier))

    def test_does_get_id_for_parsed_response_with_api_call(self):
        call_identifier = self._get_request_id_for_event_type('API_CALL')
        response_identifier = self._get_request_id_for_event_type(
            'PARSED_RESPONSE')

        self.assertEqual(call_identifier, response_identifier)
        self.assertTrue(self.UUID_PATTERN.match(call_identifier))

    def test_does_not_get_id_for_http_request_without_api_call(self):
        identifier = self._get_request_id_for_event_type('HTTP_REQUEST')
        self.assertIsNone(identifier)

    def test_does_not_get_id_for_http_response_without_api_call(self):
        identifier = self._get_request_id_for_event_type('HTTP_RESPONSE')
        self.assertIsNone(identifier)

    def test_does_not_get_id_for_parsed_response_without_api_call(self):
        identifier = self._get_request_id_for_event_type('PARSED_RESPONSE')
        self.assertIsNone(identifier)


class TestIdentifierLifecycles(unittest.TestCase):
    def setUp(self):
        self.builder = RecordBuilder()

    def _get_multiple_request_ids(self, events):
        fake_payload = {'body': b''}
        request_ids = [
            self.builder.build_record(
                event,
                fake_payload.copy(),
                ''
            )['request_id']
            for event in events
        ]
        return request_ids

    def test_multiple_http_lifecycle_writes_have_same_request_id(self):
        request_ids = self._get_multiple_request_ids(
             ['API_CALL', 'HTTP_REQUEST', 'HTTP_RESPONSE', 'PARSED_RESPONSE']
         )
        # All request_ids should match since this is one request lifecycle
        unique_request_ids = set(request_ids)
        self.assertEqual(len(unique_request_ids), 1)

    def test_request_id_reset_on_api_call(self):
        request_ids = self._get_multiple_request_ids(
             ['API_CALL', 'HTTP_REQUEST', 'HTTP_RESPONSE', 'PARSED_RESPONSE',
              'API_CALL', 'HTTP_REQUEST', 'HTTP_RESPONSE', 'PARSED_RESPONSE',
              'API_CALL', 'HTTP_REQUEST', 'HTTP_RESPONSE', 'PARSED_RESPONSE']
         )

        # There should be three distinct requet_ids since there are three
        # distinct calls that end with a parsed response.
        unique_request_ids = set(request_ids)
        self.assertEqual(len(unique_request_ids), 3)

        # Check that the request ids match the correct events.
        first_request_ids = request_ids[:4]
        unique_first_request_ids = set(first_request_ids)
        self.assertEqual(len(unique_first_request_ids), 1)

        second_request_ids = request_ids[4:8]
        unique_second_request_ids = set(second_request_ids)
        self.assertEqual(len(unique_second_request_ids), 1)

        third_request_ids = request_ids[8:]
        unique_third_request_ids = set(third_request_ids)
        self.assertEqual(len(unique_third_request_ids), 1)
