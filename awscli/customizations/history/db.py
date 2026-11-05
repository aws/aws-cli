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
import datetime
import json
import logging
import os
import threading
import time
import uuid

from botocore.history import BaseHistoryHandler

from awscli.compat import binary_type, collections_abc, sqlite3

LOG = logging.getLogger(__name__)

REDACTED_VALUE = '***REDACTED***'

# Exact key names (case-insensitive) whose values are credential/secret
# material and must never be persisted to the CLI history database. This is
# intentionally an exact-match set, not a substring match: a substring match
# on something like "token" would also catch harmless, non-secret fields
# that are extremely common across AWS APIs (NextToken, ContinuationToken,
# PaginationToken, ClientToken, JobToken, ...), silently degrading the
# usefulness of `aws history show` for routine debugging while adding no
# real protection.
#
# This list is deliberately broader than what service models mark
# `"sensitive": true` in botocore's shape metadata: for example STS's
# AssumeRole response marks `Credentials.SecretAccessKey` as sensitive but
# NOT `Credentials.SessionToken`, even though a session token is just as
# usable as a live credential as the secret key it's paired with. Rather
# than depend on every service team's model annotations being complete
# (and rather than requiring shape/operation-model context, which callers
# of this module do not have -- CLI history records are already-serialized
# dicts by the time they reach here), we redact by field name directly, as
# a deliberately conservative backstop.
_SENSITIVE_KEY_NAMES = frozenset(
    name.lower()
    for name in (
        'SecretAccessKey',
        'SessionToken',
        'SecretString',
        'SecretKey',
        'Password',
        'MasterUserPassword',
        'PrivateKey',
        'ClientSecret',
        'RefreshToken',
        'AccessToken',
        'IdToken',
        'ApiKey',
        'Authorization',
        'X-Amz-Security-Token',
    )
)


def _redact_sensitive_values(obj):
    """Recursively replace values of well-known credential/secret-bearing
    keys with a redaction marker, leaving everything else untouched.

    Dict keys are matched case-insensitively by exact name (see
    _SENSITIVE_KEY_NAMES). HTTP header dicts and parsed API request/response
    payloads both flow through this same function, since both can carry
    the fields listed above (headers carry Authorization/X-Amz-Security-
    Token; payloads carry the rest).
    """
    if isinstance(obj, collections_abc.Mapping):
        redacted = {}
        for key, value in obj.items():
            if isinstance(key, str) and key.lower() in _SENSITIVE_KEY_NAMES:
                redacted[key] = REDACTED_VALUE
            else:
                redacted[key] = _redact_sensitive_values(value)
        return redacted
    elif isinstance(obj, (list, tuple)):
        return [_redact_sensitive_values(item) for item in obj]
    else:
        return obj


# Event types whose payload is a structured dict that may directly or
# transitively contain credential material: API_CALL params (what the user
# is sending, e.g. a new IAM password or secret value being set) and
# PARSED_RESPONSE (what the service returned, e.g. STS temporary
# credentials or a decrypted secret).
_STRUCTURED_PAYLOAD_EVENTS = frozenset(('API_CALL', 'PARSED_RESPONSE'))


def _redact_payload(event_type, payload):
    if event_type in _STRUCTURED_PAYLOAD_EVENTS:
        return _redact_sensitive_values(payload)
    if event_type == 'HTTP_REQUEST' and isinstance(
        payload, collections_abc.Mapping
    ):
        payload = dict(payload)
        if 'headers' in payload:
            payload['headers'] = _redact_sensitive_values(payload['headers'])
        return payload
    if event_type == 'HTTP_RESPONSE' and isinstance(
        payload, collections_abc.Mapping
    ):
        # The raw response body at this point is still an unparsed byte/XML/
        # JSON blob (PARSED_RESPONSE, handled above, is the structured
        # equivalent of the same data). We can't safely redact specific
        # fields inside an arbitrary, not-yet-parsed wire format without
        # risking either missing a secret embedded in it (an incomplete
        # regex over arbitrary XML/JSON) or corrupting it, so the safe
        # default is to not persist the raw body at all for this event type.
        payload = dict(payload)
        if 'body' in payload:
            payload['body'] = REDACTED_VALUE
        return payload
    return payload


class DatabaseConnection:
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
        self._db_filename = db_filename
        self._connection = sqlite3.connect(
            db_filename, check_same_thread=False, isolation_level=None
        )
        self._set_file_permissions()
        self._ensure_database_setup()

    def close(self):
        self._connection.close()

    def _set_file_permissions(self):
        for suffix in ('', '-wal', '-shm'):
            path = self._db_filename + suffix
            if not os.path.exists(path):
                continue
            try:
                os.chmod(path, 0o600)
            except OSError as e:
                LOG.debug('Unable to set file permissions for %s: %s', path, e)

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
            obj = dict(
                (k, self._remove_non_unicode_stings(v)) for k, v in obj.items()
            )
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
        elif isinstance(obj, collections_abc.MutableMapping):
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


class DatabaseRecordWriter:
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
        json_serialized_payload = json.dumps(
            record['payload'], cls=PayloadSerializer
        )
        db_record = (
            record['command_id'],
            record.get('request_id'),
            record['source'],
            event_type,
            record['timestamp'],
            json_serialized_payload,
        )
        return db_record


class DatabaseRecordReader:
    _ORDERING = 'ORDER BY timestamp'
    _GET_LAST_ID_RECORDS = (
        """
        SELECT * FROM records
        WHERE id =
        (SELECT id FROM records WHERE timestamp =
        (SELECT max(timestamp) FROM records)) %s;"""
        % _ORDERING
    )
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


class RecordBuilder:
    _REQUEST_LIFECYCLE_EVENTS = set(
        ['API_CALL', 'HTTP_REQUEST', 'HTTP_RESPONSE', 'PARSED_RESPONSE']
    )
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
            'payload': _redact_payload(event_type, payload),
            'source': source,
            'timestamp': int(time.time() * 1000),
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
