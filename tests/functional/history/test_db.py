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
import threading
import json
import re

from awscli.compat import queue
from awscli.customizations.history.db import DatabaseConnection
from awscli.customizations.history.db import RecordBuilder
from awscli.customizations.history.db import DatabaseRecordWriter
from awscli.customizations.history.db import DatabaseRecordReader
from awscli.customizations.history.db import DatabaseHistoryHandler
from awscli.testutils import unittest
from awscli.compat import sqlite3
from tests import CaseInsensitiveDict


class ThreadedRecordWriter(object):
    def __init__(self, writer):
        self._read_q = queue.Queue()
        self._thread = threading.Thread(
            target=self._threaded_record_writer,
            args=(writer,))

    def _threaded_record_writer(self, writer):
        while True:
            record = self._read_q.get()
            if record is False:
                return
            writer.write_record(record)

    def write_record(self, record):
        self._read_q.put_nowait(record)

    def start(self):
        self._thread.start()

    def close(self):
        self._read_q.put_nowait(False)
        self._thread.join()


class BaseDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.connection = DatabaseConnection(':memory:')
        self.connection.row_factory = sqlite3.Row


class BaseThreadedDatabaseWriter(BaseDatabaseTest):
    def setUp(self):
        super(BaseThreadedDatabaseWriter, self).setUp()
        self.threads = []
        self.writer = DatabaseRecordWriter(self.connection)

    def start_n_threads(self, n):
        for _ in range(n):
            t = ThreadedRecordWriter(self.writer)
            t.start()
            self.threads.append(t)

    def tearDown(self):
        for t in self.threads:
            t.close()
        super(BaseThreadedDatabaseWriter, self).tearDown()


@unittest.skipIf(sqlite3 is None,
                 "sqlite3 not supported in this python")
class TestMultithreadedDatabaseWriter(BaseThreadedDatabaseWriter):
    def _write_records(self, thread_number, records):
        t = self.threads[thread_number]
        for record in records:
            t.write_record(record)

    def test_bulk_writes_all_succeed(self):
        thread_count = 10
        self.start_n_threads(thread_count)
        for i in range(thread_count):
            self._write_records(i, [
                {
                    'command_id': 'command',
                    'event_type': 'API_CALL',
                    'payload': i,
                    'source': 'TEST',
                    'timestamp': 1234
                }, {
                    'command_id': 'command',
                    'event_type': 'HTTP_REQUEST',
                    'payload': i,
                    'source': 'TEST',
                    'timestamp': 1234
                }, {
                    'command_id': 'command',
                    'event_type': 'HTTP_RESPONSE',
                    'payload': i,
                    'source': 'TEST',
                    'timestamp': 1234
                }, {
                    'command_id': 'command',
                    'event_type': 'PARSED_RESPONSE',
                    'payload': i,
                    'source': 'TEST',
                    'timestamp': 1234
                }
            ])
        for t in self.threads:
            t.close()
        thread_id_to_request_id = {}
        cursor = self.connection.execute(
            'SELECT request_id, payload FROM records'
        )
        records = 0
        for record in cursor:
            records += 1
            request_id = record['request_id']
            thread_id = record['payload']
            if thread_id not in thread_id_to_request_id:
                thread_id_to_request_id[thread_id] = request_id
            else:
                prior_request_id = thread_id_to_request_id[thread_id]
                self.assertEqual(request_id, prior_request_id)
        self.assertEqual(records, 4 * thread_count)


@unittest.skipIf(sqlite3 is None,
                 "sqlite3 not supported in this python")
class TestDatabaseRecordWriter(BaseDatabaseTest):
    def test_does_create_table(self):
        cursor = self.connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE "
            "type='table' AND name='records'"
        )
        result = cursor.fetchone()
        self.assertEqual(result[0], 1)

    def test_can_write_record(self):
        writer = DatabaseRecordWriter(connection=self.connection)
        known_record_fields = {
            'command_id': 'command',
            'source': 'TEST',
            'event_type': 'foo',
            'payload': {"foo": "bar"},
            'timestamp': 1234
        }
        writer.write_record(known_record_fields)

        cursor = self.connection.execute("SELECT COUNT(*) FROM records")
        num_records = cursor.fetchone()
        self.assertEqual(num_records[0], 1)

        cursor.execute("SELECT * FROM records")
        record = dict(cursor.fetchone())
        for col_name, row_value in known_record_fields.items():
            # Normally our reader would take care of parsing the JSON from
            # the payload.
            if col_name == 'payload':
                record[col_name] = json.loads(record[col_name])
                self.assertEqual(record[col_name], row_value)

        self.assertTrue('id' in record.keys())
        self.assertTrue('request_id' in record.keys())

    def test_can_write_many_records(self):
        writer = DatabaseRecordWriter(connection=self.connection)
        known_record_fields = {
            'command_id': 'command',
            'source': 'TEST',
            'event_type': 'foo',
            'payload': '',
            'timestamp': 1234
        }
        records_to_write = 40
        for _ in range(records_to_write):
            writer.write_record(known_record_fields)

        cursor = self.connection.execute("SELECT COUNT(*) FROM records")
        num_records = cursor.fetchone()
        self.assertEqual(num_records[0], records_to_write)


@unittest.skipIf(sqlite3 is None,
                 "sqlite3 not supported in this python")
class TestDatabaseRecordReader(BaseDatabaseTest):
    def _write_sequence_of_records(self, writer, records):
        for record in records:
            writer.write_record(record)

    def test_yields_nothing_if_no_matching_record_id(self):
        reader = DatabaseRecordReader(self.connection)
        records = [record for record in reader.iter_records('fake_id')]
        self.assertEqual(len(records), 0)

    def test_yields_nothing_no_recent_records(self):
        reader = DatabaseRecordReader(self.connection)
        records = [record for record in reader.iter_latest_records()]
        self.assertEqual(len(records), 0)

    def test_can_read_record(self):
        writer = DatabaseRecordWriter(self.connection)
        self._write_sequence_of_records(writer, [
            {
                'command_id': 'command a',
                'source': 'TEST',
                'event_type': 'foo',
                'payload': '',
                'timestamp': 3
            },
            {
                'command_id': 'command a',
                'source': 'TEST',
                'event_type': 'bar',
                'payload': '',
                'timestamp': 1
            },
            {
                'command_id': 'command a',
                'source': 'TEST',
                'event_type': 'baz',
                'payload': '',
                'timestamp': 4
            }
        ])
        self._write_sequence_of_records(writer, [
            {
                'command_id': 'command b',
                'source': 'TEST',
                'event_type': 'qux',
                'payload': '',
                'timestamp': 2
            },
            {
                'command_id': 'command b',
                'source': 'TEST',
                'event_type': 'zip',
                'payload': '',
                'timestamp': 6
            }
        ])
        reader = DatabaseRecordReader(self.connection)
        cursor = self.connection.execute(
            'select id from records where event_type = "foo" limit 1')
        identifier = cursor.fetchone()['id']

        # This should select only the three records from writer_a since we
        # are explicitly looking for the records that match the id of the
        # foo event record.
        records = [record for record in reader.iter_records(identifier)]
        self.assertEqual(len(records), 3)
        for record in records:
            record_id = record['id']
            self.assertEqual(record_id, identifier)

    def test_can_read_most_recent_records(self):
        writer = DatabaseRecordWriter(self.connection)
        self._write_sequence_of_records(writer, [
            {
                'command_id': 'command a',
                'source': 'TEST',
                'event_type': 'foo',
                'payload': '',
                'timestamp': 3
            },
            {
                'command_id': 'command a',
                'source': 'TEST',
                'event_type': 'bar',
                'payload': '',
                'timestamp': 1
            }
        ])
        self._write_sequence_of_records(writer, [
            {
                'command_id': 'command b',
                'source': 'TEST',
                'event_type': 'baz',
                'payload': '',
                'timestamp': 2
            }
        ])

        # Since the foo and bar events were written by the writer_a they all
        # share an id. foo was written at time 3 which makes it the most
        # recent, so when we call get_latest_records we should get the
        # foo and bar records only.
        reader = DatabaseRecordReader(self.connection)
        records = set([record['event_type'] for record
                       in reader.iter_latest_records()])
        self.assertEqual(set(['foo', 'bar']), records)


class TestDatabaseHistoryHandler(unittest.TestCase):
    UUID_PATTERN = re.compile(
        '^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$',
        re.I
    )

    def setUp(self):
        self.db = DatabaseConnection(':memory:')
        self.writer = DatabaseRecordWriter(connection=self.db)
        self.record_builder = RecordBuilder()
        self.handler = DatabaseHistoryHandler(
            writer=self.writer, record_builder=self.record_builder)

    def _get_last_record(self):
        record = self.db.execute('SELECT * FROM records').fetchone()
        return record

    def _assert_expected_event_type(self, source, record):
        self.assertEqual(source, record[3])

    def _assert_expected_payload(self, source, record):
        loaded_payload = json.loads(record[-1])
        self.assertEqual(source, loaded_payload)

    def _assert_expected_source(self, source, record):
        self.assertEqual(source, record[2])

    def _assert_has_request_id(self, record):
        identifier = record[1]
        self.assertTrue(self.UUID_PATTERN.match(identifier))

    def _assert_record_has_command_id(self, record):
        identifier = record[0]
        self.assertTrue(self.UUID_PATTERN.match(identifier))

    def test_does_emit_write_record(self):
        self.handler.emit('event_type', 'payload', 'source')
        record = self._get_last_record()
        self._assert_record_has_command_id(record)
        self._assert_expected_event_type('event_type', record)
        self._assert_expected_payload('payload', record)
        self._assert_expected_source('source', record)

    def test_can_emit_write_record_with_structure(self):
        payload = {'foo': 'bar'}
        self.handler.emit('event_type', payload, 'source')
        record = self._get_last_record()
        self._assert_record_has_command_id(record)
        self._assert_expected_event_type('event_type', record)
        self._assert_expected_payload(payload, record)
        self._assert_expected_source('source', record)

    def test_can_emit_cli_version_record(self):
        # CLI_VERSION records have a list of strings payload
        payload = 'foobarbaz'
        self.handler.emit('CLI_VERSION', payload, 'CLI')
        record = self._get_last_record()
        self._assert_record_has_command_id(record)
        self._assert_expected_event_type('CLI_VERSION', record)
        self._assert_expected_payload(payload, record)
        self._assert_expected_source('CLI', record)

    def test_can_emit_cli_arguments_record(self):
        # CLI_ARGUMENTS records have a list of strings payload
        payload = ['foo', 'bar', 'baz']
        self.handler.emit('CLI_ARGUMENTS', payload, 'CLI')
        record = self._get_last_record()
        self._assert_record_has_command_id(record)
        self._assert_expected_event_type('CLI_ARGUMENTS', record)
        self._assert_expected_payload(payload, record)
        self._assert_expected_source('CLI', record)

    def test_can_emit_api_call_record(self):
        # API_CALL records have a dictionary based payload
        payload = {
            'service': 's3',
            'operation': 'ListBuckets',
            'params': {}
        }
        self.handler.emit('API_CALL', payload, 'BOTOCORE')
        record = self._get_last_record()
        self._assert_record_has_command_id(record)
        self._assert_has_request_id(record)
        self._assert_expected_event_type('API_CALL', record)
        self._assert_expected_payload(payload, record)
        self._assert_expected_source('BOTOCORE', record)

    def test_can_emit_api_call_record_with_binary_param(self):
        # API_CALL records have a dictionary based payload
        payload = {
            'service': 'lambda',
            'operation': 'CreateFunction',
            'params': {
                "FunctionName": "Name",
                "Handler": "mod.fn",
                "Role": "foobar",
                "Runtime": "python3",
                "Code": {
                    "ZipFile": b'zipfile binary content \xfe\xed'
                }
            }
        }
        self.handler.emit('API_CALL', payload, 'BOTOCORE')
        record = self._get_last_record()
        parsed_payload = payload.copy()
        parsed_payload['params']['Code']['ZipFile'] = \
            '<Byte sequence>'
        self._assert_record_has_command_id(record)
        self._assert_has_request_id(record)
        self._assert_expected_event_type('API_CALL', record)
        self._assert_expected_payload(parsed_payload, record)
        self._assert_expected_source('BOTOCORE', record)

    def test_can_emit_http_request_record(self):
        # HTTP_REQUEST records have have their entire body field as a binary
        # blob, howver it will all be utf-8 valid since the binary fields
        # from the api call will have been b64 encoded.
        payload = {
            'url': ('https://lambda.us-west-2.amazonaws.com/2015-03-31/'
                    'functions'),
            'method': 'POST',
            'headers': CaseInsensitiveDict({
                'foo': 'bar'
            }),
            'body': b'body with no invalid utf-8 bytes in it',
            'streaming': False
        }
        self.handler.emit('HTTP_REQUEST', payload, 'BOTOCORE')
        record = self._get_last_record()
        parsed_payload = payload.copy()
        parsed_payload['headers'] = dict(parsed_payload['headers'])
        parsed_payload['body'] = 'body with no invalid utf-8 bytes in it'
        self._assert_record_has_command_id(record)
        self._assert_expected_event_type('HTTP_REQUEST', record)
        self._assert_expected_payload(parsed_payload, record)
        self._assert_expected_source('BOTOCORE', record)

    def test_can_emit_http_response_record(self):
        # HTTP_RESPONSE also contains a binary response in its body, but it
        # will not contain any non-unicode characters
        payload = {
            'status_code': 200,
            'headers': CaseInsensitiveDict({
                'foo': 'bar'
            }),
            'body': b'body with no invalid utf-8 bytes in it',
            'streaming': False
        }
        self.handler.emit('HTTP_RESPONSE', payload, 'BOTOCORE')
        record = self._get_last_record()
        parsed_payload = payload.copy()
        parsed_payload['headers'] = dict(parsed_payload['headers'])
        parsed_payload['body'] = 'body with no invalid utf-8 bytes in it'
        self._assert_record_has_command_id(record)
        self._assert_expected_event_type('HTTP_RESPONSE', record)
        self._assert_expected_payload(parsed_payload, record)
        self._assert_expected_source('BOTOCORE', record)

    def test_can_emit_parsed_response_record(self):
        payload = {
            "Count": 1,
            "Items": [
                {
                    "strkey": {
                        "S": "string"
                    }
                }
            ],
            "ScannedCount": 1,
            "ConsumedCapacity": None
        }
        self.handler.emit('PARSED_RESPONSE', payload, 'BOTOCORE')
        record = self._get_last_record()
        self._assert_record_has_command_id(record)
        self._assert_expected_event_type('PARSED_RESPONSE', record)
        self._assert_expected_payload(payload, record)
        self._assert_expected_source('BOTOCORE', record)

    def test_can_emit_parsed_response_record_with_binary(self):
        # PARSED_RESPONSE can also contain raw bytes
        payload = {
            "Count": 1,
            "Items": [
                {
                    "bitkey": {
                        "B": b"binary data \xfe\xed"
                    }
                }
            ],
            "ScannedCount": 1,
            "ConsumedCapacity": None
        }
        self.handler.emit('PARSED_RESPONSE', payload, 'BOTOCORE')
        record = self._get_last_record()
        parsed_payload = payload.copy()
        parsed_payload['Items'][0]['bitkey']['B'] = "<Byte sequence>"
        self._assert_record_has_command_id(record)
        self._assert_expected_event_type('PARSED_RESPONSE', record)
        self._assert_expected_payload(payload, record)
        self._assert_expected_source('BOTOCORE', record)

    def test_does_not_mutate_dict(self):
        payload = {
            "bitkey": b"binary data \xfe\xed"
        }
        copy_payload = payload.copy()
        self.handler.emit('test', payload, 'BOTOCORE')
        self.assertEqual(payload, copy_payload)

    def test_does_not_mutate_list(self):
        payload = ['non binary data', b"binary data \xfe\xed"]
        copy_payload = list(payload)
        self.handler.emit('test', payload, 'BOTOCORE')
        self.assertEqual(payload, copy_payload)
