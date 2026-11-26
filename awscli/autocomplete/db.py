import json
import logging
import os
import sqlite3

from awscli import __version__ as cli_version

LOG = logging.getLogger(__name__)

# We may eventually include a pre-generated version of this index as part
# of our shipped distributable, but for now we'll add this to our cache
# dir.
INDEX_DIR = os.path.expanduser(os.path.join('~', '.aws', 'cli', 'cache'))
INDEX_FILE = os.path.join(INDEX_DIR, f'{cli_version}.index')
# Where ``aws configure add-model`` installs models.  This mirrors
# botocore.loaders.Loader.CUSTOMER_DATA_PATH without importing botocore.
CUSTOMER_MODELS_DIR = os.path.expanduser(os.path.join('~', '.aws', 'models'))
BUILTIN_INDEX_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data',
    'ac.index',
)


# Key in the user index's metadata table that records which custom models
# the index was built from.
CUSTOM_MODELS_KEY = 'custom_models'


def list_custom_models(models_dir=None):
    """Return ``[service, api_version, size, mtime_ns]`` for each model.

    This only stats files, so it is cheap enough to run on every Tab press.
    """
    if models_dir is None:
        models_dir = CUSTOMER_MODELS_DIR
    models = []
    for service in _scandir(models_dir):
        if not service.is_dir():
            continue
        for version in _scandir(service.path):
            try:
                stat = os.stat(os.path.join(version.path, 'service-2.json'))
            except OSError:
                continue
            models.append(
                [service.name, version.name, stat.st_size, stat.st_mtime_ns]
            )
    return sorted(models)


def custom_models_fingerprint(models):
    """Return a string that changes whenever ``models`` change.

    An empty string means no models are installed.
    """
    return json.dumps(models) if models else ''


def get_index_custom_models_fingerprint(index_filename):
    """Return the fingerprint stored in an index, or None if unreadable.

    Indexes without the metadata table (such as the bundled index) were
    built without custom models, so they return an empty string.
    """
    if not os.path.isfile(index_filename):
        return ''
    try:
        conn = sqlite3.connect(index_filename)
        try:
            row = conn.execute(
                'SELECT value FROM index_metadata WHERE key = ?',
                (CUSTOM_MODELS_KEY,),
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.OperationalError as e:
        if 'no such table' in str(e):
            return ''
        return None
    except sqlite3.Error:
        return None
    return row[0] if row else ''


def _scandir(path):
    try:
        with os.scandir(path) as entries:
            return list(entries)
    except OSError:
        return []


# This is similar to DBConnection in awscli.customization.history.
# I'd like to reuse code, but we also have the contraint that we don't
# want to import anything outside of awscli.autocomplete to ensure
# our startup time is as minimal as possible.
class DatabaseConnection:
    _JOURNAL_MODE_OFF = 'PRAGMA journal_mode=OFF'

    def __init__(self, db_filename=None):
        self._db_conn = None
        self._db_filename = db_filename
        if self._db_filename is None:
            self._db_filename = self._get_index_filename()

    @property
    def _connection(self):
        if self._db_conn is None:
            kwargs = {'check_same_thread': False, 'isolation_level': None}
            if self._db_filename.startswith('file::memory:'):
                # This statement was added because old versions of sqlite
                # don't support 'uri' but we use it for tests and because
                # in the tests we use only in-memory database we're looking
                # for 'file::memory:' prefix if we decide to use 'uri' with
                # sqlite more widely we can ease restrictions to 'file:'
                kwargs['uri'] = True
            self._db_conn = sqlite3.connect(self._db_filename, **kwargs)
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

    def _get_index_filename(self):
        if os.path.isfile(INDEX_FILE):
            return INDEX_FILE
        return BUILTIN_INDEX_FILE
