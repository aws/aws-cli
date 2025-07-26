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
import sqlite3
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from awscli.botocore.exceptions import MD5UnavailableError
from awscli.botocore.session import Session
from awscli.telemetry import (
    CLISessionData,
    CLISessionDatabaseConnection,
    CLISessionDatabaseReader,
    CLISessionDatabaseSweeper,
    CLISessionDatabaseWriter,
    CLISessionGenerator,
    CLISessionOrchestrator,
    add_session_id_component_to_user_agent_extra,
)
from tests.markers import skip_if_windows


@pytest.fixture
def session_conn():
    conn = CLISessionDatabaseConnection(
        connection=sqlite3.connect(
            # Use an in-memory db for testing.
            ':memory:',
            check_same_thread=False,
            isolation_level=None,
        ),
    )
    # Write an initial record.
    conn.execute(
        """
            INSERT OR REPLACE INTO session (
                key, session_id, timestamp
            ) VALUES ('first_key', 'first_id', 5555555555)
        """
    )
    # Overwrite host id with deterministic value for testing.
    conn.execute(
        """
            INSERT OR REPLACE INTO host_id (
                key, id
            ) VALUES (0, 'my-hostname')
        """
    )
    return conn


@pytest.fixture
def session_writer(session_conn):
    return CLISessionDatabaseWriter(session_conn)


@pytest.fixture
def session_reader(session_conn):
    return CLISessionDatabaseReader(session_conn)


@pytest.fixture
def session_sweeper(session_conn):
    return CLISessionDatabaseSweeper(session_conn)


@pytest.fixture
def session_generator():
    return CLISessionGenerator()


@pytest.fixture
def expired_data(session_writer, session_reader, session_sweeper):
    # Write an expired record.
    session_writer.write(
        CLISessionData(
            key='expired_key',
            session_id='expired_id',
            timestamp=1000000000,
        )
    )
    # Ensure expired record exists.
    assert session_reader.read('expired_key') is not None
    yield
    # Ensure cleanup after test is run.
    session_sweeper.sweep(1000000001)


class TestCLISessionDatabaseConnection:
    def test_ensure_database_setup(self, session_conn):
        cursor = session_conn.execute(
            """
                SELECT name
                FROM sqlite_master
                WHERE type='table';
            """
        )
        assert cursor.fetchall() == [('session',), ('host_id',)]

    def test_timeout_does_not_raise_exception(self, session_conn):
        test_query = """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            AND name='session';
        """

        class FakeConnection(sqlite3.Connection):
            def execute(self, query, *parameters):
                # Simulate timeout by always raising.
                if query == test_query:
                    raise sqlite3.OperationalError()
                # Mock host id count query.
                cur = MagicMock()
                cur.fetchone.return_value = (1,)
                return cur

        fake_conn = CLISessionDatabaseConnection(FakeConnection(":memory:"))
        cursor = fake_conn.execute(test_query)
        assert cursor.fetchall() == []


class TestCLISessionDatabaseWriter:
    def test_write(self, session_writer, session_reader, session_sweeper):
        session_writer.write(
            CLISessionData(
                key='new-key',
                session_id='new-id',
                timestamp=1000000000,
            )
        )
        session_data = session_reader.read('new-key')
        assert session_data.key == 'new-key'
        assert session_data.session_id == 'new-id'
        assert session_data.timestamp == 1000000000
        session_sweeper.sweep(1000000001)


class TestCLISessionDatabaseReader:
    def test_read(self, session_reader):
        session_data = session_reader.read('first_key')
        assert session_data.key == 'first_key'
        assert session_data.session_id == 'first_id'
        assert session_data.timestamp == 5555555555

    def test_read_nonexistent_record(self, session_reader):
        session_data = session_reader.read('bad_key')
        assert session_data is None

    def test_read_host_id(self, session_reader):
        host_id = session_reader.read_host_id()
        assert host_id == 'my-hostname'


class TestCLISessionDatabaseSweeper:
    def test_sweep(self, expired_data, session_reader, session_sweeper):
        session_sweeper.sweep(1000000001)
        swept_data = session_reader.read('expired_key')
        assert swept_data is None

    def test_sweep_not_expired(
        self, expired_data, session_reader, session_sweeper
    ):
        session_sweeper.sweep(1000000000)
        swept_data = session_reader.read('expired_key')
        assert swept_data is not None

    def test_sweep_never_raises(self, session_sweeper):
        # Normally this would raise `sqlite3.ProgrammingError`,
        # but the `sweep` method catches bare exceptions.
        session_sweeper.sweep({'bad': 'input'})


class TestCLISessionGenerator:
    def test_generate_session_id(self, session_generator):
        session_id = session_generator.generate_session_id(
            'my-hostname',
            'my-tty',
            1000000000,
        )
        assert session_id == 'd949713b13ee'

    def test_generate_cache_key(self, session_generator):
        cache_key = session_generator.generate_cache_key(
            'my-hostname',
            'my-tty',
        )
        assert cache_key == 'b1ca2be0ffac'

    @patch('awscli.telemetry.get_md5')
    def test_checksum_fips_fallback(self, patched_get_md5, session_generator):
        patched_get_md5.side_effect = MD5UnavailableError()
        session_id = session_generator.generate_session_id(
            'my-hostname',
            'my-tty',
            1000000000,
        )
        assert session_id == '183b154db015'


@skip_if_windows
@patch('sys.stdin')
@patch('time.time', return_value=5555555555)
@patch('os.ttyname', return_value='my-tty')
class TestCLISessionOrchestrator:
    def test_session_id_gets_cached(
        self,
        patched_tty_name,
        patched_time,
        patched_stdin,
        session_sweeper,
        session_generator,
        session_reader,
        session_writer,
    ):
        patched_stdin.fileno.return_value = None
        orchestrator = CLISessionOrchestrator(
            session_generator, session_writer, session_reader, session_sweeper
        )
        assert orchestrator.session_id == '881cea8546fa'

        session_data = session_reader.read(orchestrator.cache_key)
        assert session_data.key == orchestrator.cache_key
        assert session_data.session_id == orchestrator.session_id
        assert session_data.timestamp == 5555555555

    def test_cached_session_id_updated_if_expired(
        self,
        patched_tty_name,
        patched_time,
        patched_stdin,
        session_sweeper,
        session_generator,
        session_reader,
        session_writer,
    ):
        patched_stdin.fileno.return_value = None

        # First, generate and cache a session id.
        orchestrator_1 = CLISessionOrchestrator(
            session_generator, session_writer, session_reader, session_sweeper
        )
        session_id_1 = orchestrator_1.session_id
        session_data_1 = session_reader.read(orchestrator_1.cache_key)
        assert session_data_1.session_id == session_id_1

        # Update the timestamp and get the new session id.
        patched_time.return_value = 7777777777
        orchestrator_2 = CLISessionOrchestrator(
            session_generator, session_writer, session_reader, session_sweeper
        )
        session_id_2 = orchestrator_2.session_id
        session_data_2 = session_reader.read(orchestrator_2.cache_key)

        # Cache key should be the same.
        assert session_data_2.key == session_data_1.key
        # Session id and timestamp should be updated.
        assert session_data_2.session_id == session_id_2
        assert session_data_2.session_id != session_data_1.session_id
        assert session_data_2.timestamp == 7777777777
        assert session_data_2.timestamp != session_data_1.timestamp

    def test_cached_session_id_not_updated_if_valid(
        self,
        patched_tty_name,
        patched_time,
        patched_stdin,
        session_sweeper,
        session_generator,
        session_reader,
        session_writer,
    ):
        patched_stdin.fileno.return_value = None

        # First, generate and cache a session id.
        orchestrator_1 = CLISessionOrchestrator(
            session_generator, session_writer, session_reader, session_sweeper
        )
        session_id_1 = orchestrator_1.session_id
        session_data_1 = session_reader.read(orchestrator_1.cache_key)
        assert session_data_1.session_id == session_id_1

        # Update the timestamp.
        patched_time.return_value = 5555555556
        orchestrator_2 = CLISessionOrchestrator(
            session_generator, session_writer, session_reader, session_sweeper
        )
        session_id_2 = orchestrator_2.session_id
        session_data_2 = session_reader.read(orchestrator_2.cache_key)

        # Cache key should be the same.
        assert session_data_2.key == session_data_1.key
        # Session id should not be updated.
        assert session_data_2.session_id == session_id_2
        assert session_data_2.session_id == session_data_1.session_id
        # Only timestamp should be updated.
        assert session_data_2.timestamp == 5555555556
        assert session_data_2.timestamp != session_data_1.timestamp


def test_add_session_id_component_to_user_agent_extra():
    session = MagicMock(Session)
    session.user_agent_extra = ''
    orchestrator = MagicMock(CLISessionOrchestrator)
    orchestrator.session_id = 'my-session-id'
    add_session_id_component_to_user_agent_extra(session, orchestrator)
    assert session.user_agent_extra == 'sid/my-session-id'


def test_entrypoint_catches_bare_exceptions():
    mock_orchestrator = MagicMock(CLISessionOrchestrator)
    type(mock_orchestrator).session_id = PropertyMock(side_effect=Exception)
    session = MagicMock(Session)
    add_session_id_component_to_user_agent_extra(session, mock_orchestrator)
