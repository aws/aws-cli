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
import datetime
import threading
import logging
from collections import MutableMapping

from botocore.history import BaseHistoryHandler

from awscli.compat import sqlite3
from awscli.compat import ensure_text_type


LOG = logging.getLogger(__name__)


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
    _ENABLE_WAL = 'PRAGMA journal_mode=WAL'
    _DEFAULT_DATABASE_NAME = 'history.db'

    def __init__(self, db_filename):
        self._connection = sqlite3.connect(
            db_filename, check_same_thread=False, isolation_level=None)
        self._ensure_database_setup()

    def execute(self, query, *parameters):
        self._connection.execute(query, *parameters)

    def cursor(self):
        return self._connection.cursor()

    def _ensure_database_setup(self):
        self._create_record_table()
        self._try_to_enable_wal()

    def _create_record_table(self):
        self.execute(self._CREATE_TABLE)

    def _try_to_enable_wal(self):
        try:
            self.execute(self._ENABLE_WAL)
        except sqlite3.Error:
            # This is just a performance enhancement so it is optional. Not all
            # systems will have a sqlite compiled with the WAL enabled.
            LOG.debug('Failed to enable sqlite WAL.')

    @property
    def row_factory(self):
        return self._connection.row_factory

    @row_factory.setter
    def row_factory(self, row_factory):
        self._connection.row_factory = row_factory


class PayloadSerializer(json.JSONEncoder):
    def _encode_mutable_mapping(self, obj):
        return dict(obj)

    def _encode_datetime(self, obj):
        return obj.isoformat()

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return self._encode_datetime(obj)
        elif isinstance(obj, MutableMapping):
            return self._encode_mutable_mapping(obj)
        else:
            return repr(obj)


class DatabaseRecordWriter(object):
    _WRITE_RECORD = """
        INSERT INTO records(
            id, request_id, source, event_type, timestamp, payload)
        VALUES (?,?,?,?,?,?) """

    def __init__(self, connection=None):
        if connection is None:
            connection = DatabaseConnection()
        self._connection = connection

    def write_record(self, record):
        # This method is not threadsafe by itself, it is only threadsafe when
        # used inside a handler bound to the HistoryRecorder in botocore which
        # is protected by a lock.
        db_record = self._create_db_record(record)
        self._connection.execute(self._WRITE_RECORD, db_record)

    def _create_db_record(self, record):
        event_type = record['event_type']
        json_serialized_payload = json.dumps(record['payload'],
                                             cls=PayloadSerializer)
        db_record = (
            record['command_id'],
            record.get('request_id'),
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

    def iter_latest_records(self):
        cursor = self._connection.cursor()
        cursor.execute(self._GET_LAST_ID_RECORDS)
        for row in cursor:
            yield row

    def iter_records(self, record_id):
        cursor = self._connection.cursor()
        cursor.execute(self._GET_RECORDS_BY_ID, [record_id])
        for row in cursor:
            yield row


class RecordBuilder(object):
    _REQUEST_LIFECYCLE_EVENTS = set(
        ['API_CALL', 'HTTP_REQUEST', 'HTTP_RESPONSE', 'PARSED_RESPONSE'])
    _START_OF_REQUEST_LIFECYCLE_EVENT = 'API_CALL'
    _BYTES_BODY_PAYLOADS = set(['HTTP_REQUEST', 'HTTP_RESPONSE'])

    def __init__(self):
        self._identifier = None
        self._locals = threading.local()

    def _get_current_thread_request_id(self):
        request_id = getattr(self._locals, 'request_id', None)
        return request_id

    def _start_http_lifecycle(self):
        setattr(self._locals, 'request_id', str(uuid.uuid4()))

    def _get_request_id(self, event_type):
        if event_type == self._START_OF_REQUEST_LIFECYCLE_EVENT:
            self._start_http_lifecycle()
        if event_type in self._REQUEST_LIFECYCLE_EVENTS:
            request_id = self._get_current_thread_request_id()
            return request_id
        return None

    def _format_payload(self, event_type, payload):
        # If the payload has a body key it can be in bytes, so it needs to be
        # converted to utf-8 if possible so it can be serialized as JSON later.
        if event_type in self._BYTES_BODY_PAYLOADS:
            body = payload['body']
            if body is not None:
                payload['body'] = ensure_text_type(body)
        return payload

    def _get_identifier(self):
        if self._identifier is None:
            self._identifier = str(uuid.uuid4())
        return self._identifier

    def build_record(self, event_type, payload, source):
        uid = self._get_identifier()
        payload = self._format_payload(event_type, payload)
        record = {
            'command_id': uid,
            'event_type': event_type,
            'payload': payload,
            'source': source,
            'timestamp': int(time.time() * 1000)
        }
        request_id = self._get_request_id(event_type)
        if request_id:
            record['request_id'] = request_id
        return record


class DatabaseHistoryHandler(BaseHistoryHandler):
    def __init__(self, writer=None, record_builder=None):
        if writer is None:
            writer = DatabaseRecordWriter()
        self._writer = writer
        if record_builder is None:
            record_builder = RecordBuilder()
        self._record_builder = record_builder

    def emit(self, event_type, payload, source):
        record = self._record_builder.build_record(event_type, payload, source)
        self._writer.write_record(record)
