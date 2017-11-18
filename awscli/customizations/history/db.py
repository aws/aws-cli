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
import uuid
import time
import json
import base64
import threading

from botocore.history import BaseHistoryHandler

from awscli.compat import sqlite3
from awscli.compat import ensure_text_type


class DatabaseConnection(object):
    _CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS records (
      id TEXT,
      request_id TEXT,
      source TEXT,
      event_type TEXT,
      timestamp INTEGER,
      payload TEXT
    )"""
    _ENABLE_WAL = """PRAGMA journal_mode=WAL"""
    _DATABASE_NAME = 'history.db'
    _DEFAULT_DATABASE_FILENAME = os.path.expanduser(
        os.path.join('~', '.aws', 'cli', 'history', _DATABASE_NAME))

    def __init__(self, db_filename=None):
        if db_filename:
            self._db_filename = db_filename
        elif os.environ.get('AWS_HISTORY_PATH'):
            self._db_filename = os.path.join(
                os.environ.get('AWS_HISTORY_PATH'), self._DATABASE_NAME)
        else:
            self._db_filename = self._DEFAULT_DATABASE_FILENAME

        if not os.path.isdir(os.path.dirname(self._db_filename)):
            os.makedirs(os.path.dirname(self._db_filename))
        self._connection = sqlite3.connect(
            self._db_filename, check_same_thread=False)
        self._ensure_database_setup()

    def _ensure_database_setup(self):
        self._create_record_table()
        self._try_to_enable_wal()

    def _create_record_table(self):
        cursor = self.cursor()
        cursor.execute(self._CREATE_TABLE)
        self._connection.commit()

    def _try_to_enable_wal(self):
        try:
            cursor = self.cursor()
            cursor.execute(self._ENABLE_WAL)
            self._connection.commit()
        except sqlite3.Error:
            # This is just a performance enhancement so it is optional. Not all
            # systems will have a sqlite compiled with the WAL enabled.
            pass

    def cursor(self):
        return self._connection.cursor()

    def commit(self):
        self._connection.commit()

    @property
    def row_factory(self):
        return self._connection.row_factory

    @row_factory.setter
    def row_factory(self, row_factory):
        self._connection.row_factory = row_factory


class PayloadSerializer(json.JSONEncoder):
    def _process_CaseInsensitiveDict(self, obj, type_name):
        return dict(obj)

    def _process_bytes(self, obj, type_name):
        encoded = base64.b64encode(obj)
        return ensure_text_type(encoded)

    def _process_datetime(self, obj, type_name):
        return obj.isoformat()

    def _unknown(self, obj, type_name):
        return type_name

    def encode(self, obj):
        # The default method is not called in PY2 where the JSONEncoder thinks
        # it can handle a bytes object becausae it can't tell it apart from a
        # str object. In PY3 this is handled by the _process_bytes method.
        # For PY2 we have to override the encode method where the encoding of
        # a bytes-like string will fail, catch the UnicodeDecodeError and
        # then call _process_bytes and retry the encoding.
        try:
            encoded = super(PayloadSerializer, self).encode(obj)
            return encoded
        except UnicodeDecodeError:
            b64encoded = self._process_bytes(obj, 'bytes')
            encoded = self.encode(b64encoded)
            return encoded

    def default(self, obj):
        type_name = type(obj).__name__
        return getattr(
            self, '_process_%s' % type_name, self._unknown
        )(obj, type_name)


class DatabaseRecordWriter(object):
    _WRITE_RECORD = """
    INSERT INTO records(id, request_id, source, event_type, timestamp, payload)
    VALUES (?,?,?,?,?,?)"""
    _REQUEST_LIFECYCLE_EVENTS = set(
        ['API_CALL', 'HTTP_REQUEST', 'HTTP_RESPONSE', 'PARSED_RESPONSE'])
    _START_OF_REQUEST_LIFECYCLE_EVENT = 'API_CALL'

    def __init__(self, connection=None):
        if connection is None:
            connection = DatabaseConnection()
        self._connection = connection
        self._request_ids = {}
        self._identifier = None

    def write_record(self, record):
        cursor = self._connection.cursor()
        db_record = self._create_db_record(record)
        cursor.execute(self._WRITE_RECORD, db_record)
        self._connection.commit()

    def _get_request_id(self, event_type):
        if event_type == self._START_OF_REQUEST_LIFECYCLE_EVENT:
            self._start_http_lifecycle()
        if event_type in self._REQUEST_LIFECYCLE_EVENTS:
            thread_id = threading.current_thread().ident
            request_id = self._request_ids.get(thread_id, '')
        else:
            request_id = ''
        return request_id

    def _start_http_lifecycle(self):
        thread_id = threading.current_thread().ident
        new_identifier = str(uuid.uuid4())
        self._request_ids[thread_id] = new_identifier

    def _get_identifier(self):
        if self._identifier is None:
            self._identifier = str(uuid.uuid4())
        return self._identifier

    def _create_db_record(self, record):
        uid = self._get_identifier()
        event_type = record['event_type']
        request_id = self._get_request_id(event_type)
        json_serialized_payload = json.dumps(record['payload'],
                                             cls=PayloadSerializer)
        db_record = (
            uid,
            request_id,
            record['source'],
            event_type,
            record['timestamp'],
            json_serialized_payload
        )
        return db_record


class DatabaseRecordReader(object):
    _ORDERING = 'ORDER BY timestamp'
    _GET_LAST_ID_RECORDS = """
    SELECT * FROM records
    WHERE id =
    (SELECT id FROM records WHERE timestamp =
    (SELECT max(timestamp) FROM records)) %s;""" % _ORDERING
    _GET_RECORDS_BY_ID = 'SELECT * from records where id = ? %s' % _ORDERING

    def __init__(self, connection=None):
        if connection is None:
            connection = DatabaseConnection()
        self._connection = connection
        self._connection.row_factory = self._row_factory

    def _row_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            val = row[idx]
            if col[0] == 'payload':
                val = json.loads(val)
            d[col[0]] = val
        return d

    def yield_latest_records(self):
        cursor = self._connection.cursor()
        cursor.execute(self._GET_LAST_ID_RECORDS)
        for row in cursor:
            yield row

    def yield_records(self, record_id):
        cursor = self._connection.cursor()
        cursor.execute(self._GET_RECORDS_BY_ID, [record_id])
        for row in cursor:
            yield row


class DatabaseHistoryHandler(BaseHistoryHandler):
    def __init__(self, writer=None):
        if writer is None:
            writer = DatabaseRecordWriter()
        self._writer = writer

    def emit(self, event_type, payload, source):
        record = {
            'event_type': event_type,
            'payload': payload,
            'source': source,
            'timestamp': int(time.time() * 1000)
        }
        self._writer.write_record(record)
