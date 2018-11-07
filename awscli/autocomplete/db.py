import sqlite3
import logging


LOG = logging.getLogger(__name__)


# This is similar to DBConnection in awscli.customization.history.
# I'd like to reuse code, but we also have the contraint that we don't
# want to import anything outside of awscli.autocomplete to ensure
# our startup time is as minimal as possible.
class DatabaseConnection(object):
    _ENABLE_WAL = 'PRAGMA journal_mode=WAL'

    def __init__(self, db_filename):
        self._db_conn = None
        self._db_filename = db_filename

    @property
    def _connection(self):
        if self._db_conn is None:
            self._db_conn = sqlite3.connect(
                self._db_filename, check_same_thread=False,
                isolation_level=None)
            self._ensure_database_setup()
        return self._db_conn

    def close(self):
        self._connection.close()

    def execute(self, query, **kwargs):
        return self._connection.execute(query, kwargs)

    def _ensure_database_setup(self):
        self._try_to_enable_wal()

    def _try_to_enable_wal(self):
        try:
            self.execute(self._ENABLE_WAL)
        except sqlite3.Error:
            # This is just a performance enhancement so it is optional. Not all
            # systems will have a sqlite compiled with the WAL enabled.
            LOG.debug('Failed to enable sqlite WAL.')
