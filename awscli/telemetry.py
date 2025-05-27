# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import hashlib
import io
import os
import socket
import sqlite3
import sys
import threading
import time
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from botocore.useragent import UserAgentComponent

from awscli.compat import is_windows
from awscli.utils import add_component_to_user_agent_extra

_CACHE_DIR = Path.home() / '.aws' / 'cli' / 'cache'
_DATABASE_FILENAME = 'session.db'
_SESSION_LENGTH_SECONDS = 60 * 30

_CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class CLISessionData:
    key: str
    session_id: str
    timestamp: int


class CLISessionDatabaseConnection:
    _CREATE_TABLE = """
        CREATE TABLE IF NOT EXISTS session (
          key TEXT PRIMARY KEY,
          session_id TEXT NOT NULL,
          timestamp INTEGER NOT NULL
        )
    """
    _ENABLE_WAL = 'PRAGMA journal_mode=WAL'

    def __init__(self, connection=None):
        self._connection = connection or sqlite3.connect(
            _CACHE_DIR / _DATABASE_FILENAME,
            check_same_thread=False,
            isolation_level=None,
        )
        self._ensure_database_setup()

    def execute(self, query, *parameters):
        try:
            return self._connection.execute(query, *parameters)
        except sqlite3.OperationalError:
            # Process timed out waiting for database lock.
            # Return any empty `Cursor` object instead of
            # raising an exception.
            return sqlite3.Cursor(self._connection)

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
            pass


class CLISessionDatabaseWriter:
    _WRITE_RECORD = """
        INSERT OR REPLACE INTO session (
            key, session_id, timestamp
        ) VALUES (?, ?, ?)
    """

    def __init__(self, connection):
        self._connection = connection

    def write(self, data):
        self._connection.execute(
            self._WRITE_RECORD,
            (
                data.key,
                data.session_id,
                data.timestamp,
            ),
        )


class CLISessionDatabaseReader:
    _READ_RECORD = """
        SELECT *
        FROM session
        WHERE key = ?
    """

    def __init__(self, connection):
        self._connection = connection

    def read(self, key):
        cursor = self._connection.execute(self._READ_RECORD, (key,))
        result = cursor.fetchone()
        if result is None:
            return
        return CLISessionData(*result)


class CLISessionDatabaseSweeper:
    _DELETE_RECORDS = """
        DELETE FROM session
        WHERE timestamp < ?
    """

    def __init__(self, connection):
        self._connection = connection

    def sweep(self, timestamp):
        try:
            self._connection.execute(self._DELETE_RECORDS, (timestamp,))
        except Exception:
            # This is just a background cleanup task. No need to
            # handle it or direct to stderr.
            return


class CLISessionGenerator:
    def generate_session_id(self, hostname, tty, timestamp):
        return self._generate_md5_hash(hostname, tty, timestamp)

    def generate_cache_key(self, hostname, tty):
        return self._generate_md5_hash(hostname, tty)

    def _generate_md5_hash(self, *args):
        str_to_hash = ""
        for arg in args:
            if arg is not None:
                str_to_hash += str(arg)
        return hashlib.md5(str_to_hash.encode('utf-8')).hexdigest()


class CLISessionOrchestrator:
    def __init__(self, generator, writer, reader, sweeper):
        self._generator = generator
        self._writer = writer
        self._reader = reader
        self._sweeper = sweeper

        self._sweep_cache()

    @cached_property
    def cache_key(self):
        return self._generator.generate_cache_key(self._hostname, self._tty)

    @cached_property
    def _session_id(self):
        return self._generator.generate_session_id(
            self._hostname, self._tty, self._timestamp
        )

    @cached_property
    def session_id(self):
        if (cached_data := self._reader.read(self.cache_key)) is not None:
            # Cache hit, but session id is expired. Generate new id and update.
            if (
                cached_data.timestamp + _SESSION_LENGTH_SECONDS
                < self._timestamp
            ):
                cached_data.session_id = self._session_id
            # Always update the timestamp to last used.
            cached_data.timestamp = self._timestamp
            self._writer.write(cached_data)
            return cached_data.session_id
        # Cache miss, generate and write new record.
        session_id = self._session_id
        session_data = CLISessionData(
            self.cache_key, session_id, self._timestamp
        )
        self._writer.write(session_data)
        return session_id

    @cached_property
    def _tty(self):
        # os.ttyname is only available on Unix platforms.
        if is_windows:
            return
        try:
            return os.ttyname(sys.stdin.fileno())
        except (OSError, io.UnsupportedOperation):
            # Standard input was redirected to a pseudofile.
            # This can happen when running tests on IDEs or
            # running scripts with redirected input.
            return

    @cached_property
    def _hostname(self):
        return socket.gethostname()

    @cached_property
    def _timestamp(self):
        return int(time.time())

    def _sweep_cache(self):
        t = threading.Thread(
            target=self._sweeper.sweep,
            args=(self._timestamp - _SESSION_LENGTH_SECONDS,),
            daemon=True,
        )
        t.start()


def _get_cli_session_orchestrator():
    conn = CLISessionDatabaseConnection()
    return CLISessionOrchestrator(
        CLISessionGenerator(),
        CLISessionDatabaseWriter(conn),
        CLISessionDatabaseReader(conn),
        CLISessionDatabaseSweeper(conn),
    )


def add_session_id_component_to_user_agent_extra(session, orchestrator=None):
    cli_session_orchestrator = orchestrator or _get_cli_session_orchestrator()
    add_component_to_user_agent_extra(
        session, UserAgentComponent("sid", cli_session_orchestrator.session_id)
    )
