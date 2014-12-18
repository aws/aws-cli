import os
import time
import json
import logging
import getpass

from dateutil.parser import parse
from datetime import datetime
from dateutil.tz import tzlocal

from botocore import credentials
from botocore.compat import total_seconds
from botocore.exceptions import PartialCredentialsError


LOG = logging.getLogger(__name__)


class InvalidConfigError(Exception):
    pass


class RefreshWithMFAUnsupportedError(Exception):
    pass


def register_assume_role_provider(event_handlers):
    event_handlers.register('session-initialized',
                            inject_assume_role_provider,
                            unique_id='inject_assume_role_cred_provider')


def inject_assume_role_provider(session, **kwargs):
    provider = create_assume_role_provider(session, AssumeRoleProvider)
    try:
        # The final order will be:
        # * env
        # * assume-role
        # * shared-credentials-file
        # * ...
        cred_chain = session.get_component('credential_provider')
        cred_chain.insert_before('shared-credentials-file', provider)
    except Exception:
        # This is ok, it just means that we couldn't create the credential
        # provider object.
        LOG.debug("Not registering assume-role provider, credential "
                  "provider from session could not be created.")


def create_assume_role_provider(session, provider_cls):
    profile_name = session.get_config_variable('profile') or 'default'
    load_config = lambda: session.full_config
    return provider_cls(
        load_config=load_config,
        client_creator=session.create_client,
        cache=JSONFileCache(AssumeRoleProvider.CACHE_DIR),
        profile_name=profile_name,
    )


def create_refresher_function(client, params):
    def refresh():
        role_session_name = 'AWS-CLI-session-%s' % (int(time.time()))
        params['RoleSessionName'] = role_session_name
        response = client.assume_role(**params)
        credentials = response['Credentials']
        # We need to normalize the credential names to
        # the values expected by the refresh creds.
        return {
            'access_key': credentials['AccessKeyId'],
            'secret_key': credentials['SecretAccessKey'],
            'token': credentials['SessionToken'],
            'expiry_time': credentials['Expiration'],
        }
    return refresh


def create_mfa_serial_refresh():
    def _refresher():
        # We can explore an option in the future to support
        # reprompting for MFA, but for now we just error out
        # when the temp creds expire.
        raise RefreshWithMFAUnsupportedError(
            "Cannot refresh credentials: MFA token required.")
    return _refresher


class JSONFileCache(object):
    """JSON file cache.

    This provides a dict like interface that stores JSON serializable
    objects.

    The objects are serialized to JSON and stored in a file.  These
    values can be retrieved at a later time.

    """
    def __init__(self, working_dir):
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
            f.write(file_content)

    def _convert_cache_key(self, cache_key):
        full_path = os.path.join(self._working_dir, cache_key + '.json')
        return full_path


class AssumeRoleProvider(credentials.CredentialProvider):

    METHOD = 'assume-role'
    CACHE_DIR = os.path.expanduser(os.path.join('~', '.aws', 'cli', 'cache'))
    ROLE_CONFIG_VAR = 'role_arn'
    # Credentials are considered expired (and will be refreshed) once the total
    # remaining time left until the credentials expires is less than the
    # EXPIRY_WINDOW.
    EXPIRY_WINDOW_SECONDS = 60 * 15

    def __init__(self, load_config, client_creator, cache, profile_name,
                 prompter=getpass.getpass):
        """

        :type load_config: callable
        :param load_config: A function that accepts no arguments, and
            when called, will return the full configuration dictionary
            for the session (``session.full_config``).

        :type client_creator: callable
        :param client_creator: A factory function that will create
            a client when called.  Has the same interface as
            ``botocore.session.Session.create_client``.

        :type cache: JSONFileCache
        :param cache: An object that supports ``__getitem__``,
            ``__setitem__``, and ``__contains__``.  An example
            of this is the ``JSONFileCache`` class.

        :type profile_name: str
        :param profile_name: The name of the profile.

        :type prompter: callable
        :param prompter: A callable that returns input provided
            by the user (i.e raw_input, getpass.getpass, etc.).

        """
        self._load_config = load_config
        # client_creator is a callable that creates function.
        # It's basically session.create_client
        self._client_creator = client_creator
        self._profile_name = profile_name
        self._cache = cache
        self._prompter = prompter
        # The _loaded_config attribute will be populated from the
        # load_config() function once the configuration is actually
        # loaded.  The reason we go through all this instead of just
        # requiring that the loaded_config be passed to us is to that
        # we can defer configuration loaded until we actually try
        # to load credentials (as opposed to when the object is
        # instantiated).
        self._loaded_config = {}

    def load(self):
        self._loaded_config = self._load_config()
        if self._has_assume_role_config_vars():
            return self._load_creds_via_assume_role()

    def _has_assume_role_config_vars(self):
        profiles = self._loaded_config.get('profiles', {})
        return self.ROLE_CONFIG_VAR in profiles.get(self._profile_name, {})

    def _load_creds_via_assume_role(self):
        # We can get creds in one of two ways:
        # * It can either be cached on disk from an pre-existing session
        # * Cache doesn't have the creds (or is expired) so we need to make
        #   an assume role call to get temporary creds, which we then cache
        #   for subsequent requests.
        creds = self._load_creds_from_cache()
        if creds is not None:
            LOG.debug("Credentials for role retrieved from cache.")
            return creds
        else:
            # We get the Credential used by botocore as well
            # as the original parsed response from the server.
            creds, response = self._retrieve_temp_credentials()
            cache_key = self._create_cache_key()
            self._write_cached_credentials(response, cache_key)
            return creds

    def _load_creds_from_cache(self):
        cache_key = self._create_cache_key()
        try:
            from_cache = self._cache[cache_key]
            if self._is_expired(from_cache):
                # Don't need to delete the cache entry,
                # when we refresh via AssumeRole, we'll
                # update the cache with the new entry.
                LOG.debug("Credentials were found in cache, but they are expired.")
                return None
            else:
                return self._create_creds_from_response(from_cache)
        except KeyError:
            return None

    def _is_expired(self, credentials):
        end_time = parse(credentials['Credentials']['Expiration'])
        now = datetime.now(tzlocal())
        seconds = total_seconds(end_time - now)
        return seconds < self.EXPIRY_WINDOW_SECONDS

    def _create_cache_key(self):
        role_config = self._get_role_config_values()
        # On windows, ':' is not allowed in filenames, so we'll
        # replace them with '_' instead.
        role_arn = role_config['role_arn'].replace(':', '_')
        cache_key = '%s--%s' % (self._profile_name, role_arn)
        return cache_key.replace('/', '-')

    def _write_cached_credentials(self, creds, cache_key):
        self._cache[cache_key] = creds

    def _get_role_config_values(self):
        # This returns the role related configuration.
        profiles = self._loaded_config.get('profiles', {})
        try:
            source_profile = profiles[self._profile_name]['source_profile']
            role_arn = profiles[self._profile_name]['role_arn']
            mfa_serial = profiles[self._profile_name].get('mfa_serial')
        except KeyError as e:
            raise PartialCredentialsError(provider=self.METHOD,
                                          cred_var=str(e))
        external_id = profiles[self._profile_name].get('external_id')
        if source_profile not in profiles:
            raise InvalidConfigError(
                'The source_profile "%s" referenced in '
                'the profile "%s" does not exist.' % (
                    source_profile, self._profile_name))
        source_cred_values = profiles[source_profile]
        return {
            'role_arn': role_arn,
            'external_id': external_id,
            'source_profile': source_profile,
            'mfa_serial': mfa_serial,
            'source_cred_values': source_cred_values,
        }

    def _create_creds_from_response(self, response):
        config = self._get_role_config_values()
        if config.get('mfa_serial') is not None:
            # MFA would require getting a new TokenCode which would require
            # prompting the user for a new token, so we use a different
            # refresh_func.
            refresh_func = create_mfa_serial_refresh()
        else:
            refresh_func = create_refresher_function(
                self._create_client_from_config(config),
                self._assume_role_base_kwargs(config))
        return credentials.RefreshableCredentials(
            access_key=response['Credentials']['AccessKeyId'],
            secret_key=response['Credentials']['SecretAccessKey'],
            token=response['Credentials']['SessionToken'],
            method=self.METHOD,
            expiry_time=parse(response['Credentials']['Expiration']),
            refresh_using=refresh_func)

    def _create_client_from_config(self, config):
        source_cred_values = config['source_cred_values']
        client = self._client_creator(
            'sts', aws_access_key_id=source_cred_values['aws_access_key_id'],
            aws_secret_access_key=source_cred_values['aws_secret_access_key'],
            aws_session_token=source_cred_values.get('aws_session_token'),
        )
        return client

    def _retrieve_temp_credentials(self):
        LOG.debug("Retrieving credentials via AssumeRole.")
        config = self._get_role_config_values()
        client = self._create_client_from_config(config)

        assume_role_kwargs = self._assume_role_base_kwargs(config)
        role_session_name = 'AWS-CLI-session-%s' % (int(time.time()))
        assume_role_kwargs['RoleSessionName'] = role_session_name

        response = client.assume_role(**assume_role_kwargs)
        creds = self._create_creds_from_response(response)
        return creds, response

    def _assume_role_base_kwargs(self, config):
        assume_role_kwargs = {'RoleArn': config['role_arn']}
        if config['external_id'] is not None:
            assume_role_kwargs['ExternalId'] = config['external_id']
        if config['mfa_serial'] is not None:
            token_code = self._prompter("Enter MFA code: ")
            assume_role_kwargs['SerialNumber'] = config['mfa_serial']
            assume_role_kwargs['TokenCode'] = token_code
        return assume_role_kwargs
