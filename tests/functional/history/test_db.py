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
import tempfile
import shutil
import json
import os

from awscli.compat import queue
from awscli.customizations.history.db import DatabaseConnection
from awscli.customizations.history.db import DatabaseRecordWriter
from awscli.customizations.history.db import DatabaseRecordReader
from awscli.testutils import unittest
from awscli.compat import sqlite3


class ThreadedRecordWriter(object):
    def __init__(self, writer, lock):
        self._read_q = queue.Queue()
        self._thread = threading.Thread(
            target=self._threaded_record_writer,
            args=(writer, lock))

    def _threaded_record_writer(self, writer, lock):
        while True:
            record = self._read_q.get()
            if record is False:
                return
            with lock:
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
        self.tempdir = tempfile.mkdtemp()
        self.db_filename = os.path.join(self.tempdir, 'history.db')
        self.connection = DatabaseConnection(db_filename=self.db_filename)
        self.connection.row_factory = sqlite3.Row

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def _get_cursor(self):
        return self.connection.cursor()


class BaseThreadedDatabaseWriter(BaseDatabaseTest):
    def setUp(self):
        super(BaseThreadedDatabaseWriter, self).setUp()
        self.threads = []
        self.writer = DatabaseRecordWriter(self.connection)

    def start_n_threads(self, n, lock):
        for _ in range(n):
            t = ThreadedRecordWriter(self.writer, lock)
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
        lock = threading.Lock()
        self.start_n_threads(thread_count, lock)
        for i in range(thread_count):
            self._write_records(i, [
                {
                    'event_type': 'API_CALL',
                    'payload': i,
                    'source': 'TEST',
                    'timestamp': 1234
                }, {
                    'event_type': 'HTTP_REQUEST',
                    'payload': i,
                    'source': 'TEST',
                    'timestamp': 1234
                }, {
                    'event_type': 'HTTP_RESPONSE',
                    'payload': i,
                    'source': 'TEST',
                    'timestamp': 1234
                }, {
                    'event_type': 'PARSED_RESPONSE',
                    'payload': i,
                    'source': 'TEST',
                    'timestamp': 1234
                }
            ])
        for t in self.threads:
            t.close()
        thread_id_to_request_id = {}
        cursor = self.connection.cursor()
        cursor.execute('select request_id, payload from records')
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
    def test_does_create_database(self):
        self.assertTrue(os.path.isfile(self.db_filename))

    def test_does_create_table(self):
        cursor = self._get_cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE "
                       "type='table' AND name='records';")
        result = cursor.fetchone()
        self.assertEqual(result[0], 1)

    def test_can_write_record(self):
        writer = DatabaseRecordWriter(connection=self.connection)
        known_record_fields = {
            'source': 'TEST',
            'event_type': 'foo',
            'payload': {"foo": "bar"},
            'timestamp': 1234
        }
        writer.write_record(known_record_fields)

        cursor = self._get_cursor()
        cursor.execute("SELECT COUNT(*) FROM records;")
        num_records = cursor.fetchone()
        self.assertEqual(num_records[0], 1)

        cursor.execute("SELECT * FROM records;")
        record = dict(cursor.fetchone())
        for col_name, row_value in known_record_fields.items():
            # Normally our reader would take care of parsing the JSON from
            # the payload.
            if col_name == 'payload':
                record[col_name] = json.loads(record[col_name])
                self.assertEqual(record[col_name], row_value)

        self.assertIn('id', record.keys())
        self.assertIn('request_id', record.keys())

    def test_can_write_many_records(self):
        writer = DatabaseRecordWriter(connection=self.connection)
        known_record_fields = {
            'source': 'TEST',
            'event_type': 'foo',
            'payload': '',
            'timestamp': 12334
        }
        records_to_write = 40
        for _ in range(records_to_write):
            writer.write_record(known_record_fields)

        cursor = self._get_cursor()
        cursor.execute("SELECT COUNT(*) FROM records;")
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
        records = [record for record in reader.yield_records('fake_id')]
        self.assertEqual(len(records), 0)

    def test_yields_nothing_no_recent_records(self):
        reader = DatabaseRecordReader(self.connection)
        records = [record for record in reader.yield_latest_records()]
        self.assertEqual(len(records), 0)

    def test_can_read_record(self):
        writer_a = DatabaseRecordWriter(self.connection)
        writer_b = DatabaseRecordWriter(self.connection)
        self._write_sequence_of_records(writer_a, [
            {
                'source': 'TEST',
                'event_type': 'foo',
                'payload': '',
                'timestamp': 3
            },
            {
                'source': 'TEST',
                'event_type': 'bar',
                'payload': '',
                'timestamp': 1
            },
            {
                'source': 'TEST',
                'event_type': 'baz',
                'payload': '',
                'timestamp': 4
            }
        ])
        self._write_sequence_of_records(writer_b, [
            {
                'source': 'TEST',
                'event_type': 'qux',
                'payload': '',
                'timestamp': 2
            },
            {
                'source': 'TEST',
                'event_type': 'zip',
                'payload': '',
                'timestamp': 6
            }
        ])
        reader = DatabaseRecordReader(self.connection)
        cursor = self._get_cursor()
        cursor.execute(
            'select id from records where event_type = "foo" limit 1')
        identifier = cursor.fetchone()['id']

        # This should select only the three records from writer_a since we
        # are explicitly looking for the records that match the id of the
        # foo event record.
        records = [record for record in reader.yield_records(identifier)]
        self.assertEqual(len(records), 3)
        for record in records:
            record_id = record['id']
            self.assertEqual(record_id, identifier)

    def test_can_read_most_recent_records(self):
        writer_a = DatabaseRecordWriter(self.connection)
        writer_b = DatabaseRecordWriter(self.connection)
        self._write_sequence_of_records(writer_a, [
            {
                'source': 'TEST',
                'event_type': 'foo',
                'payload': '',
                'timestamp': 3
            },
            {
                'source': 'TEST',
                'event_type': 'bar',
                'payload': '',
                'timestamp': 1
            }
        ])
        self._write_sequence_of_records(writer_b, [
            {
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
                       in reader.yield_latest_records()])
        self.assertEqual(set(['foo', 'bar']), records)
