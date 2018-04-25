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
import uuid
import time
import json
import datetime
import threading
import logging
from collections import MutableMapping

from botocore.history import BaseHistoryHandler

from awscli.compat import sqlite3
from awscli.compat import binary_type


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

    def __init__(self, db_filename):
        self._connection = sqlite3.connect(
            db_filename, check_same_thread=False, isolation_level=None)
        self._ensure_database_setup()

    def close(self):
        self._connection.close()

    def execute(self, query, *parameters):
        return self._connection.execute(query, *parameters)

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

    def _try_decode_bytes(self, obj):
        try:
            obj = obj.decode('utf-8')
        except UnicodeDecodeError:
            obj = '<Byte sequence>'
        return obj

    def _remove_non_unicode_stings(self, obj):
        if isinstance(obj, str):
            obj = self._try_decode_bytes(obj)
        elif isinstance(obj, dict):
            obj = dict((k, self._remove_non_unicode_stings(v)) for k, v
                       in obj.items())
        elif isinstance(obj, (list, tuple)):
            obj = [self._remove_non_unicode_stings(o) for o in obj]
        return obj

    def encode(self, obj):
        try:
            return super(PayloadSerializer, self).encode(obj)
        except UnicodeDecodeError:
            # This happens in PY2 in the case where a record payload has some
            # binary data in it that is not utf-8 encodable. PY2 will not call
            # the default method on the individual field with bytes in it since
            # it thinks it can handle it with the normal string serialization
            # method. Since it cannot tell the difference between a utf-8 str
            # and a str with raw bytes in it we will get a UnicodeDecodeError
            # here at the top level. There are no hooks into the serialization
            # process in PY2 that allow us to fix this behavior, so instead
            # when we encounter the unicode error we climb the structure
            # ourselves and replace all strings that are not utf-8 decodable
            # and try to encode again.
            scrubbed_obj = self._remove_non_unicode_stings(obj)
            return super(PayloadSerializer, self).encode(scrubbed_obj)

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return self._encode_datetime(obj)
        elif isinstance(obj, MutableMapping):
            return self._encode_mutable_mapping(obj)
        elif isinstance(obj, binary_type):
            # In PY3 the bytes type differs from the str type so the default
            # method will be called when a bytes object is encountered.
            # We call the same _try_decode_bytes method that either decodes it
            # to a utf-8 string and continues serialization, or removes the
            # value if it is not valid utf-8 string.
            return self._try_decode_bytes(obj)
        else:
            return repr(obj)


class DatabaseRecordWriter(object):
    _WRITE_RECORD = """
        INSERT INTO records(
            id, request_id, source, event_type, timestamp, payload)
        VALUES (?,?,?,?,?,?) """

    def __init__(self, connection):
        self._connection = connection
        self._lock = threading.Lock()

    def close(self):
        self._connection.close()

    def write_record(self, record):
        db_record = self._create_db_record(record)
        with self._lock:
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
    _GET_ALL_RECORDS = (
        'SELECT a.id AS id_a, '
        '    b.id AS id_b, '
        '    a.timestamp as timestamp, '
        '    a.payload AS args, '
        '    b.payload AS rc '
        'FROM records a, records b '
        'where a.event_type == "CLI_ARGUMENTS" AND '
        '    b.event_type = "CLI_RC" AND '
        '    id_a == id_b '
        '%s DESC' % _ORDERING
    )

    def __init__(self, connection):
        self._connection = connection
        self._connection.row_factory = self._row_factory

    def close(self):
        self._connection.close()

    def _row_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            val = row[idx]
            if col[0] == 'payload':
                val = json.loads(val)
            d[col[0]] = val
        return d

    def iter_latest_records(self):
        cursor = self._connection.execute(self._GET_LAST_ID_RECORDS)
        for row in cursor:
            yield row

    def iter_records(self, record_id):
        cursor = self._connection.execute(self._GET_RECORDS_BY_ID, [record_id])
        for row in cursor:
            yield row

    def iter_all_records(self):
        cursor = self._connection.execute(self._GET_ALL_RECORDS)
        for row in cursor:
            yield row


class RecordBuilder(object):
    _REQUEST_LIFECYCLE_EVENTS = set(
        ['API_CALL', 'HTTP_REQUEST', 'HTTP_RESPONSE', 'PARSED_RESPONSE'])
    _START_OF_REQUEST_LIFECYCLE_EVENT = 'API_CALL'

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

    def _get_identifier(self):
        if self._identifier is None:
            self._identifier = str(uuid.uuid4())
        return self._identifier

    def build_record(self, event_type, payload, source):
        uid = self._get_identifier()
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
    def __init__(self, writer, record_builder):
        self._writer = writer
        self._record_builder = record_builder

    def emit(self, event_type, payload, source):
        record = self._record_builder.build_record(event_type, payload, source)
        self._writer.write_record(record)
