import os
import logging

from botocore.exceptions import ProfileNotFound
from botocore.credentials import JSONFileCache

LOG = logging.getLogger(__name__)
CACHE_DIR = os.path.expanduser(os.path.join('~', '.aws', 'cli', 'cache'))


def register_session_token_provider(event_handlers):
    event_handlers.register('session-initialized',
                            inject_session_token_provider_cache,
                            unique_id='inject_session_token_cred_provider_cache')


def inject_session_token_provider_cache(session, **kwargs):
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
                  "assume-role and shared-credentials-file cred provider cache. "
                  "Not configuring JSONFileCache for assume-role and shared-credentials-file.")
        return
    for provider_name in ['assume-role', 'shared-credentials-file']:
        provider = cred_chain.get_provider(provider_name)
        provider.cache = JSONFileCache(CACHE_DIR)
