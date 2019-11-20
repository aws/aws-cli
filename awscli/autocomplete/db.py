import logging

from awscli.compat import sqlite3


LOG = logging.getLogger(__name__)


# This is similar to DBConnection in awscli.customization.history.
# I'd like to reuse code, but we also have the contraint that we don't
# want to import anything outside of awscli.autocomplete to ensure
# our startup time is as minimal as possible.
class DatabaseConnection(object):
    _JOURNAL_MODE_OFF = 'PRAGMA journal_mode=OFF'

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
        # We are setting journal mode to off because there is no guarantee
        # the user has permissions to write temporary files to where the
        # CLI is installed and in-practice, the index is only ever read from
        # (except when we need to generate it).
        self.execute(self._JOURNAL_MODE_OFF)
