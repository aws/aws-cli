import os
import json
import logging

from botocore.exceptions import ProfileNotFound

LOG = logging.getLogger(__name__)


def register_assume_role_provider(event_handlers):
    event_handlers.register('session-initialized',
                            inject_assume_role_provider_cache,
                            unique_id='inject_assume_role_cred_provider_cache')


def inject_assume_role_provider_cache(session, **kwargs):
    try:
        cred_chain = session.get_component('credential_provider')
    except ProfileNotFound:
        # If a user has provided a profile that does not exist,
        # trying to retrieve components/config on the session
        # will raise ProfileNotFound.  Sometimes this is invalid:
        #
        # "ec2 describe-instances --profile unknown"
        #
        # and sometimes this is perfectly valid:
        #
        # "configure set region us-west-2 --profile brand-new-profile"
        #
        # Because we can't know (and don't want to know) whether
        # the customer is trying to do something valid, we just
        # immediately return.  If it's invalid something else
        # up the stack will raise ProfileNotFound, otherwise
        # the configure (and other) commands will work as expected.
        LOG.debug("ProfileNotFound caught when trying to inject "
                  "assume-role cred provider cache.  Not configuring "
                  "JSONFileCache for assume-role.")
        return
    provider = cred_chain.get_provider('assume-role')
    provider.cache = JSONFileCache()


class JSONFileCache(object):
    """JSON file cache.

    This provides a dict like interface that stores JSON serializable
    objects.

    The objects are serialized to JSON and stored in a file.  These
    values can be retrieved at a later time.

    """

    CACHE_DIR = os.path.expanduser(os.path.join('~', '.aws', 'cli', 'cache'))

    def __init__(self, working_dir=CACHE_DIR):
        self._working_dir = working_dir

    def __contains__(self, cache_key):
        actual_key = self._convert_cache_key(cache_key)
        return os.path.isfile(actual_key)

    def __getitem__(self, cache_key):
        """Retrieve value from a cache key."""
        actual_key = self._convert_cache_key(cache_key)
        try:
            with open(actual_key) as f:
                return json.load(f)
        except (OSError, ValueError, IOError):
            raise KeyError(cache_key)

    def __setitem__(self, cache_key, value):
        full_key = self._convert_cache_key(cache_key)
        try:
            file_content = json.dumps(value)
        except (TypeError, ValueError):
            raise ValueError("Value cannot be cached, must be "
                             "JSON serializable: %s" % value)
        if not os.path.isdir(self._working_dir):
            os.makedirs(self._working_dir)
        with os.fdopen(os.open(full_key,
                               os.O_WRONLY | os.O_CREAT, 0o600), 'w') as f:
            f.truncate()
            f.write(file_content)

    def _convert_cache_key(self, cache_key):
        full_path = os.path.join(self._working_dir, cache_key + '.json')
        return full_path
