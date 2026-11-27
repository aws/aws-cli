# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Profile rules for the credential daemon: the key, credential names and
the config-file overlay."""

import hashlib
import re

from botocore.configloader import load_config, raw_config_parse
from botocore.credential_daemon.text import strip_control_characters
from botocore.exceptions import ConfigNotFound, InvalidConfigError
from botocore.utils import SSO_ROLE_CONFIG_VARS

CREDENTIAL_DAEMON_KEY = 'credential_daemon'
# Keys read from the config file alone. session.full_config adds each
# profile's keys from the credentials file over the config file's, but these
# say where a profile's credentials are and where new ones go, and the CLI
# writes them to the config file. SSOProvider's check that a profile agrees
# with its sso-session also skips these keys, so adding one here changes both.
CONFIG_FILE_ONLY_KEYS = (CREDENTIAL_DAEMON_KEY, 'credential_storage')


CREDENTIAL_NAME_MAX_LENGTH = 64


# The credential daemon has one name space for every type of credential, so
# the names the CLI makes start with a tag for what's stored. Today each type
# has its own place on disk, and [profile acme] and [sso-session acme] don't
# clash.
LOGIN_TAG = 'login.'
KEYS_TAG = 'keys.'
SSO_TAG = 'sso.'

_HASH_LENGTH = 8
_VALID_NAME = re.compile(
    rf'(?!\.)[A-Za-z0-9._-]{{1,{CREDENTIAL_NAME_MAX_LENGTH}}}'
)
_DISALLOWED_CHARACTER = re.compile(r'[^A-Za-z0-9._-]')


def is_valid_credential_name(name):
    """Whether the credential daemon accepts ``name`` as a credential name.

    A valid name has 1 to ``CREDENTIAL_NAME_MAX_LENGTH`` (64) of
    ``A-Z a-z 0-9 . _ -`` and doesn't start with ``.``. ``name`` can be
    any value, since it may come from the credential daemon's JSON or
    from a config value, and anything that isn't a string isn't valid.
    """
    return isinstance(name, str) and bool(_VALID_NAME.fullmatch(name))


def full_config_with_config_file_keys(session):
    """Return ``session.full_config`` with ``CONFIG_FILE_ONLY_KEYS`` read
    from the config file alone.

    Where the credentials file sets one of them for a profile, the config
    file's value replaces it, or it's removed if the config file has none.
    The session's own config isn't changed.
    """
    config = session.full_config
    profiles = config.get('profiles', {})
    if not any(
        key in profile
        for profile in profiles.values()
        for key in CONFIG_FILE_ONLY_KEYS
    ):
        return config
    try:
        credentials_file = raw_config_parse(
            session.get_config_variable('credentials_file')
        )
    except ConfigNotFound:
        return config
    from_credentials_file = {
        name: [key for key in CONFIG_FILE_ONLY_KEYS if key in keys]
        for name, keys in credentials_file.items()
        if name in profiles
    }
    from_credentials_file = {
        name: keys for name, keys in from_credentials_file.items() if keys
    }
    if not from_credentials_file:
        return config
    try:
        config_file = load_config(
            session.get_config_variable('config_file')
        ).get('profiles', {})
    except ConfigNotFound:
        config_file = {}
    profiles = dict(profiles)
    for name, keys in from_credentials_file.items():
        profile = dict(profiles[name])
        own = config_file.get(name, {})
        for key in keys:
            if key in own:
                profile[key] = own[key]
            else:
                profile.pop(key, None)
        profiles[name] = profile
    return dict(config, profiles=profiles)


def profiles_with_config_file_keys(session):
    """The ``profiles`` of ``full_config_with_config_file_keys()``."""
    return full_config_with_config_file_keys(session).get('profiles', {})


def credential_daemon_value(profile_name, profile_config):
    """Return the profile's ``credential_daemon``, or None.

    Raises ``InvalidConfigError`` if it isn't a valid credential name. An
    indented line after the key makes the value a dict, not a string.
    """
    name = profile_config.get(CREDENTIAL_DAEMON_KEY)
    if name is None:
        return None
    # A bad value is a config error, as for any other bad profile key. For
    # example, `credential_daemon = my keys` makes every credential lookup
    # for the profile fail with this error. Ignoring the value would
    # quietly fall through to other credentials, which the profile asked
    # not to use.
    if not isinstance(name, str):
        raise InvalidConfigError(
            error_msg=(
                f'The {CREDENTIAL_DAEMON_KEY} in profile '
                f'"{strip_control_characters(profile_name)}" is '
                f'not a single value. Put the name on the same line, with '
                f'no indented lines after it.'
            )
        )
    if not is_valid_credential_name(name):
        raise InvalidConfigError(
            error_msg=(
                f'The {CREDENTIAL_DAEMON_KEY} '
                f'"{strip_control_characters(name)}" in profile '
                f'"{strip_control_characters(profile_name)}" is not valid. '
                f'Use 1 to {CREDENTIAL_NAME_MAX_LENGTH} letters, '
                f'digits, ".", "_" or "-", not starting with ".".'
            )
        )
    return name


def tagged_credential_name(tag, name):
    """The credential name the CLI makes for ``name`` under ``tag``.

    ``name`` is a profile or sso-session name, so it's always a string.
    ``tag`` (``login.``, ``keys.`` or ``sso.``) goes in front of it, and a
    valid result is returned unchanged: ``login.`` and ``dev`` give
    ``login.dev``. Otherwise each disallowed character becomes ``-``, and
    the name is cut to its first 55 characters.
    Then ``-`` and the first 8 hex digits of the SHA-256 of the tagged
    name are added, so names that convert to the same text (``me@corp``
    and ``me-corp``) stay different: ``login.`` and ``me@corp`` give
    ``login.me-corp-`` and 8 hex digits.

    Two profiles can still get the same name, though it's unlikely: a
    profile named ``me-corp-`` plus those 8 hex digits gives the same
    name as ``me@corp``. Nothing prevents this, and both profiles then
    share one daemon credential.
    """
    _check_name(name)
    tagged = tag + name
    if is_valid_credential_name(tagged):
        return tagged
    converted = _DISALLOWED_CHARACTER.sub('-', tagged)
    digest = hashlib.sha256(tagged.encode('utf-8')).hexdigest()
    kept = CREDENTIAL_NAME_MAX_LENGTH - _HASH_LENGTH - 1
    return f'{converted[:kept]}-{digest[:_HASH_LENGTH]}'


def _check_name(name):
    # Callers pass profile and sso-session names, which are always strings.
    if not isinstance(name, str):
        raise TypeError(
            f'A credential name must be a string, not {type(name).__name__}'
        )
    if not name:
        raise ValueError('A credential name can\'t be empty')


def is_sso_profile(profile_config):
    """Whether a profile signs in with SSO (``sso_session`` or
    ``sso_start_url``)."""
    return 'sso_session' in profile_config or 'sso_start_url' in profile_config


def is_sso_profile_without_role(profile_config):
    """Whether a profile is an SSO profile with no account and no role.

    That's ``sso_session`` or ``sso_start_url`` with neither ``sso_account_id``
    nor ``sso_role_name``. For such a daemon profile, the credential daemon
    isn't called and the profile resolves as if it had no ``credential_daemon``
    (SEP rule 3).
    """
    return is_sso_profile(profile_config) and not any(
        key in profile_config for key in SSO_ROLE_CONFIG_VARS
    )


def get_credential_daemon_name(profile_name, profile_config):
    """Return the daemon credential a profile uses, or None.

    Raises ``InvalidConfigError`` if the name isn't valid, or if the profile
    also sets a key that gets credentials some other way. An SSO profile with
    no account and no role may set those keys, since the credential daemon
    isn't used for it.
    """
    name = credential_daemon_value(profile_name, profile_config)
    if name is None:
        return None
    if is_sso_profile_without_role(profile_config):
        return name
    shown = strip_control_characters(profile_name)
    # SEP rule 2. web_identity_token_file is checked first: it's a second
    # credential source, even next to role_arn.
    if 'web_identity_token_file' in profile_config:
        raise InvalidConfigError(
            error_msg=(
                f'The profile "{shown}" has two credential sources, '
                f'{CREDENTIAL_DAEMON_KEY} and web_identity_token_file. Remove '
                f'one.'
            )
        )
    if 'role_arn' in profile_config:
        raise InvalidConfigError(
            error_msg=(
                f'The profile "{shown}" contains both '
                f'{CREDENTIAL_DAEMON_KEY} and role_arn. To assume a role with '
                f'daemon credentials, set source_profile = '
                f'{shown} in a separate profile.'
            )
        )
    return name


DAEMON_SOCKET_ENV_VAR = 'AWS_CREDENTIAL_DAEMON_SOCKET'


# The tags the CLI adds with credential/tag to each credential it creates
# or signs in, after the bootstrap. aws logout --all and aws sso logout
# clear only credentials that carry them.
CREATED_BY_TAG = 'created-by'
CLI_TAGS = {CREATED_BY_TAG: 'aws-cli'}
