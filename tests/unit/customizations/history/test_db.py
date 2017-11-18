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
import re
import json
import threading
import base64
import datetime
from collections import MutableMapping
from collections import Mapping

import mock

from awscli.compat import queue
from awscli.customizations.history.db import DatabaseHistoryHandler
from awscli.customizations.history.db import DatabaseRecordWriter
from awscli.customizations.history.db import DatabaseRecordReader
from awscli.customizations.history.db import PayloadSerializer
from awscli.testutils import unittest


# CaseInsensitiveDict from requests that must be serializble.
class CaseInsensitiveDict(MutableMapping):
    def __init__(self, data=None, **kwargs):
        self._store = dict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key, value):
        # Use the lowercased key for lookups, but store the actual
        # key alongside the value.
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key):
        return self._store[key.lower()][1]

    def __delitem__(self, key):
        del self._store[key.lower()]

    def __iter__(self):
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self):
        return len(self._store)

    def lower_items(self):
        """Like iteritems(), but with all lowercase keys."""
        return (
            (lowerkey, keyval[1])
            for (lowerkey, keyval)
            in self._store.items()
        )

    def __eq__(self, other):
        if isinstance(other, Mapping):
            other = CaseInsensitiveDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.lower_items()) == dict(other.lower_items())

    # Copy is required
    def copy(self):
        return CaseInsensitiveDict(self._store.values())

    def __repr__(self):
        return str(dict(self.items()))


class FakeDatabaseConnection(object):
    def __init__(self):
        self.mock_cursor = mock.Mock()
        self.commits = 0

    def cursor(self):
        return self.mock_cursor

    def commit(self):
        self.commits += 1


class TestDatabaseHistoryHandler(unittest.TestCase):
    def test_history_creates_record_for_writer(self):
        writer = mock.Mock(DatabaseRecordWriter)
        handler = DatabaseHistoryHandler(writer)
        handler.emit('CLI_RC', 0, 'CLI')
        self.assertEqual(
            writer.write_record.call_args_list,
            [
                mock.call({
                    'event_type': 'CLI_RC',
                    'payload': 0,
                    'source': 'CLI',
                    'timestamp': mock.ANY
                })
            ]
        )
        # Also make sure the timestamp is of the correct type
        self.assertIsInstance(
            writer.write_record.call_args[0][0]['timestamp'], int)


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
        self.fake_connection = FakeDatabaseConnection()
        self.writer = DatabaseRecordWriter(connection=self.fake_connection)

    def _write_record(self, record):
        self.writer.write_record(record)
        write_call = self.fake_connection.mock_cursor.execute.call_args[0]
        insert_stmt, written_record = write_call
        return insert_stmt, written_record

    def assert_insert_statement_structure_correct(self, stmt):
        # Make sure the columns are in the expected order.
        self.assert_contains_lines_in_order(['insert into records',
                                            '(',
                                             'id',
                                             'request_id',
                                             'source',
                                             'event_type',
                                             'timestamp',
                                             'payload',
                                             ')',
                                             'values'], stmt.lower())


class TestDatabaseRecordWriter(BaseDatabaseRecordWriterTester):
    def setUp(self):
        super(TestDatabaseRecordWriter, self).setUp()

    def test_can_write_record(self):
        insert_stmt, written_record = self._write_record({
            'event_type': 'FOO',
            'payload': 'bar',
            'source': 'TEST',
            'timestamp': 1234
        })

        self.assert_insert_statement_structure_correct(insert_stmt)

        # Now that we have verified the order of the fields in the insert
        # statement we can verify that the record values are in the correct
        # order in the tuple.
        # The written records first two fields are an id and the request_id
        # which are generated uuid4s. The rest of the fields should be the
        # ones from the above record in the order:
        # (source, event_type, timestamp, payload)
        self.assertEqual(written_record[2:], ('TEST', 'FOO', 1234, '"bar"'))

        # The id will always be present and will be a uuid4 and the request_id
        # will either be blank or a valid uuid4. In this case since the
        # event_type TEST is not a known http lifecycle event it will not have
        # a request_id.
        identifier, request_id = written_record[:2]
        self.assertTrue(self.UUID_PATTERN.match(identifier))
        self.assertEqual(request_id, '')

    def test_commit_count_matches_write_count(self):
        records_to_write = 10
        for _ in range(records_to_write):
            self._write_record({
                'event_type': 'foo',
                'payload': '',
                'source': 'TEST',
                'timestamp': 1234
            })
        self.assertEqual(self.fake_connection.commits, records_to_write)

    def test_can_write_cli_version_record(self):
        insert_stmt, written_record = self._write_record({
            'event_type': 'CLI_VERSION',
            'payload': ('aws-cli/1.11.184 Python/3.6.2 Darwin/15.6.0 '
                        'botocore/1.7.42'),
            'source': 'TEST',
            'timestamp': 1234
        })

        self.assert_insert_statement_structure_correct(insert_stmt)
        self.assertEqual(
            written_record[2:],
            ('TEST', 'CLI_VERSION', 1234,
             '"aws-cli/1.11.184 Python/3.6.2 Darwin/15.6.0 botocore/1.7.42"')
        )
        identifier, request_id = written_record[:2]
        self.assertTrue(self.UUID_PATTERN.match(identifier))
        self.assertEqual(request_id, '')

    def test_can_write_cli_arguments_record(self):
        insert_stmt, written_record = self._write_record({
            'event_type': 'CLI_ARGUMENTS',
            'payload': ['s3', 'ls'],
            'source': 'TEST',
            'timestamp': 1234
        })

        self.assert_insert_statement_structure_correct(insert_stmt)
        self.assertEqual(
            written_record[2:],
            ('TEST', 'CLI_ARGUMENTS', 1234, '["s3", "ls"]')
        )
        identifier, request_id = written_record[:2]
        self.assertTrue(self.UUID_PATTERN.match(identifier))
        self.assertEqual(request_id, '')

    def test_can_write_api_call_record(self):
        insert_stmt, written_record = self._write_record({
            'event_type': 'API_CALL',
            'payload': {
                'service': 's3',
                'operation': 'ListBuckets',
                'params': {},
            },
            'source': 'TEST',
            'timestamp': 1234
        })

        self.assert_insert_statement_structure_correct(insert_stmt)
        self.assertEqual(
            written_record[2:],
            ('TEST', 'API_CALL', 1234, json.dumps({
                'service': 's3',
                'operation': 'ListBuckets',
                'params': {},
            }))
        )
        identifier, request_id = written_record[:2]
        self.assertTrue(self.UUID_PATTERN.match(identifier))
        self.assertTrue(self.UUID_PATTERN.match(request_id))

    def test_can_write_http_request_record(self):
        insert_stmt, written_record = self._write_record({
            'event_type': 'HTTP_REQUEST',
            'payload': {
                'method': 'GET',
                'headers': {},
                'body': '...',
            },
            'source': 'TEST',
            'timestamp': 1234
        })

        self.assert_insert_statement_structure_correct(insert_stmt)
        self.assertEqual(
            written_record[2:],
            ('TEST', 'HTTP_REQUEST', 1234, json.dumps({
                'method': 'GET',
                'headers': {},
                'body': '...',
            }))
        )
        identifier, request_id = written_record[:2]
        self.assertTrue(self.UUID_PATTERN.match(identifier))

    def test_can_write_http_response_record(self):
        insert_stmt, written_record = self._write_record({
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

        self.assert_insert_statement_structure_correct(insert_stmt)
        self.assertEqual(
            written_record[2:],
            ('TEST', 'HTTP_RESPONSE', 1234, json.dumps({
                'streaming': False,
                'headers': {},
                'body': '...',
                'status_code': 200,
                'request_id': '1234abcd'
            }))
        )
        identifier, request_id = written_record[:2]
        self.assertTrue(self.UUID_PATTERN.match(identifier))

    def test_can_write_parsed_response_record(self):
        insert_stmt, written_record = self._write_record({
            'event_type': 'PARSED_RESPONSE',
            'payload': {},
            'source': 'TEST',
            'timestamp': 1234
        })

        self.assert_insert_statement_structure_correct(insert_stmt)
        self.assertEqual(
            written_record[2:],
            ('TEST', 'PARSED_RESPONSE', 1234, '{}')
        )
        identifier, request_id = written_record[:2]
        self.assertTrue(self.UUID_PATTERN.match(identifier))

    def test_can_write_cli_rc_record(self):
        insert_stmt, written_record = self._write_record({
            'event_type': 'CLI_RC',
            'payload': 0,
            'source': 'TEST',
            'timestamp': 1234
        })

        self.assert_insert_statement_structure_correct(insert_stmt)
        self.assertEqual(
            written_record[2:],
            ('TEST', 'CLI_RC', 1234, '0')
        )
        identifier, request_id = written_record[:2]
        self.assertTrue(self.UUID_PATTERN.match(identifier))
        self.assertEqual(request_id, '')


class TestIdentifierLifecycles(BaseDatabaseRecordWriterTester):
    def _write_sequence_of_records(self, records):
        written_records = [
            written_record for _, written_record in
            [self._write_record(record) for record in records]]
        return written_records

    def test_multiple_http_lifecycle_writes_have_same_request_id(self):
        written_records = self._write_sequence_of_records([
                {
                    'event_type': 'API_CALL',
                    'payload': '',
                    'source': 'TEST',
                    'timestamp': 1234
                },
                {
                    'event_type': 'HTTP_REQUEST',
                    'payload': '',
                    'source': 'TEST',
                    'timestamp': 1234
                },
                {
                    'event_type': 'HTTP_RESPONSE',
                    'payload': '',
                    'source': 'TEST',
                    'timestamp': 1234
                },
                {
                    'event_type': 'PARSED_RESPONSE',
                    'payload': '',
                    'source': 'TEST',
                    'timestamp': 1234
                }
        ])
        # Exctract just the request_ids from the written records which is
        # the second field.
        written_record_request_ids = [record[1] for record in written_records]

        # All request_ids should match since this is one request lifecycle
        unique_request_ids = set(written_record_request_ids)
        self.assertEqual(len(unique_request_ids), 1)

    def test_request_id_reset_on_api_call(self):
        written_records = self._write_sequence_of_records([
                {
                    'event_type': 'API_CALL',
                    'payload': '',
                    'source': 'TEST',
                    'timestamp': 1234
                },
                {
                    'event_type': 'PARSED_RESPONSE',
                    'payload': '',
                    'source': 'TEST',
                    'timestamp': 1234
                },
                {
                    'event_type': 'API_CALL',
                    'payload': '',
                    'source': 'TEST',
                    'timestamp': 1234
                },
                {
                    'event_type': 'PARSED_RESPONSE',
                    'payload': '',
                    'source': 'TEST',
                    'timestamp': 1234
                },
                {
                    'event_type': 'API_CALL',
                    'payload': '',
                    'source': 'TEST',
                    'timestamp': 1234
                },
                {
                    'event_type': 'PARSED_RESPONSE',
                    'payload': '',
                    'source': 'TEST',
                    'timestamp': 1234
                }
        ])
        written_record_request_ids = [record[1] for record in written_records]

        # There should be three distinct requet_ids since there are three
        # distinct calls that end with a parsed response.
        unique_request_ids = set(written_record_request_ids)
        self.assertEqual(len(unique_request_ids), 3)

        # Check that the request ids match the correct events.
        first_request_ids = written_record_request_ids[:2]
        unique_first_request_ids = set(first_request_ids)
        self.assertEqual(len(unique_first_request_ids), 1)

        second_request_ids = written_record_request_ids[2:4]
        unique_second_request_ids = set(second_request_ids)
        self.assertEqual(len(unique_second_request_ids), 1)

        third_request_ids = written_record_request_ids[4:]
        unique_third_request_ids = set(third_request_ids)
        self.assertEqual(len(unique_third_request_ids), 1)

    def test_identifier_is_always_the_same(self):
        # Three http lifecycles are written here, the overall identifier for
        # the records should remain the same regardless.
        written_records = self._write_sequence_of_records([
                {
                    'event_type': 'api_call',
                    'payload': '',
                    'source': 'test',
                    'timestamp': 1234
                },
                {
                    'event_type': 'parsed_response',
                    'payload': '',
                    'source': 'test',
                    'timestamp': 1234
                },
                {
                    'event_type': 'api_call',
                    'payload': '',
                    'source': 'test',
                    'timestamp': 1234
                },
                {
                    'event_type': 'parsed_response',
                    'payload': '',
                    'source': 'test',
                    'timestamp': 1234
                },
                {
                    'event_type': 'api_call',
                    'payload': '',
                    'source': 'test',
                    'timestamp': 1234
                },
                {
                    'event_type': 'parsed_response',
                    'payload': '',
                    'source': 'test',
                    'timestamp': 1234
                }
        ])
        # The record id is the first field in the record.
        written_record_ids = [record[0] for record in written_records]
        # Even though the request lifecycle was reset multpile times the
        # overall id should be the same.
        unique_ids = set(written_record_ids)
        self.assertEqual(len(unique_ids), 1)


class ThreadedRecordWriter(object):
    def __init__(self, writer, fake_connection):
        self._read_q = queue.Queue()
        self._write_q = queue.Queue()
        self._thread = threading.Thread(
            target=self._threaded_record_writer,
            args=(writer, fake_connection))
        self._thread.start()

    def _threaded_record_writer(self, writer, fake_connection):
        while True:
            record = self._read_q.get()
            if record is False:
                return
            writer.write_record(record)
            write_call = fake_connection.mock_cursor.execute.call_args[0]
            _, written_record = write_call
            self._write_q.put_nowait(written_record)

    def read_n_records(self, n):
        records = [self._write_q.get() for _ in range(n)]
        return records

    def write_record(self, record):
        self._read_q.put_nowait(record)

    def close(self):
        self._read_q.put_nowait(False)
        self._thread.join()


class TestMultithreadRequestId(TestIdentifierLifecycles):
    def setUp(self):
        super(TestMultithreadRequestId, self).setUp()
        self.thread_a = ThreadedRecordWriter(
            self.writer, self.fake_connection)
        self.thread_b = ThreadedRecordWriter(
            self.writer, self.fake_connection)

    def tearDown(self):
        self.thread_a.close()
        self.thread_b.close()

    def test_each_thread_has_separate_request_id(self):
        self.thread_a.write_record({
            'event_type': 'API_CALL',
            'payload': '',
            'source': 'TEST_a',
            'timestamp': 1234
        })
        self.thread_a.write_record({
            'event_type': 'HTTP_REQUEST',
            'payload': '',
            'source': 'TEST_a',
            'timestamp': 1234
        })

        self.thread_b.write_record({
            'event_type': 'API_CALL',
            'payload': '',
            'source': 'TEST_b',
            'timestamp': 1234
        })
        self.thread_b.write_record({
            'event_type': 'HTTP_REQUEST',
            'payload': '',
            'source': 'TEST_b',
            'timestamp': 1234
        })

        a_records = self.thread_a.read_n_records(2)
        b_records = self.thread_b.read_n_records(2)

        # Each thread should have its own set of request_ids so the request
        # ids in each set of records should match, but should not match the
        # request_ids from the other thread.
        a_request_ids = [record[1] for record in a_records]
        self.assertEqual(len(a_request_ids), 2)
        self.assertEqual(a_request_ids[0], a_request_ids[1])
        thread_a_request_id = a_request_ids[0]

        b_request_ids = [record[1] for record in b_records]
        self.assertEqual(len(b_request_ids), 2)
        self.assertEqual(b_request_ids[0], b_request_ids[1])
        thread_b_request_id = b_request_ids[0]

        self.assertNotEqual(thread_a_request_id, thread_b_request_id)

        # Since the request_id is reset by the API_CALL record being written
        # and thread b has now written an API_CALL record the request id has
        # been reset once. To ensure this doesnt bleed over to other threads
        # we will write another record in thread a and ensure that it's
        # request_id matches the previous ones from thread a rather than then
        # thread b request_id
        self.thread_a.write_record({
            'event_type': 'HTTP_RESPONSE',
            'payload': '',
            'source': 'TEST_a',
            'timestamp': 1234
        })
        self.thread_b.write_record({
            'event_type': 'HTTP_RESPONSE',
            'payload': '',
            'source': 'TEST_b',
            'timestamp': 1234
        })
        a_record = self.thread_a.read_n_records(1)[0]
        b_record = self.thread_b.read_n_records(1)[0]
        self.assertEqual(a_record[1], thread_a_request_id)
        self.assertEqual(b_record[1], thread_b_request_id)


class TestDatabaseRecordReader(BaseDatabaseRecordTester):
    def setUp(self):
        self.fake_connection = FakeDatabaseConnection()
        self.reader = DatabaseRecordReader(self.fake_connection)

    def test_row_factory_set(self):
        self.assertEqual(self.fake_connection.row_factory,
                         self.reader._row_factory)

    def test_yield_latest_records(self):
        pass

    def test_yield_records(self):
        pass


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

    def test_can_serialize_case_bytes(self):
        original = b'\xfe\xed'
        encoded = base64.b64encode(original).decode('utf-8')
        string_value = json.dumps(original, cls=PayloadSerializer)
        reloaded = json.loads(string_value)
        self.assertEqual(encoded, reloaded)
