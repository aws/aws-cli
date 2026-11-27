# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Reads and writes of a profile's settings in the config files."""

import os

from botocore.credential_daemon import profiles_with_config_file_keys
from botocore.credential_daemon.config import is_sso_profile_without_role

from awscli.customizations.credential_daemon.storage.policy import (
    CREDENTIAL_STORAGE,
    CREDENTIAL_STORAGE_ENV_VAR,
    DecisionSource,
    Storage,
    StorageDecision,
    decide_storage,
    sso_without_role_error,
)


def resolve_credential_storage(session, profile_name, environ=None):
    """Return ``daemon`` or ``file`` for the profile's own credentials
    (``resolve_own_storage``), or None if there's no answer yet.

    A ``profile_name`` of None is the default profile, as for the session
    with no profile selected.
    """
    storage = resolve_own_storage(
        session, profile_or_default(profile_name), environ
    ).storage
    return None if storage is None else storage.value


def resolve_own_storage(session, profile_name, environ=None):
    """``resolve_storage`` for the profile's own credentials, such as an
    aws login session or access keys.

    Raises ``ConfigurationError`` when ``AWS_CREDENTIAL_STORAGE=daemon``
    asks for the credential daemon for a profile it can't serve.
    """
    config = profile_config(session, profile_name)
    if not is_sso_profile_without_role(config):
        return resolve_storage(session, profile_name, environ)
    # An SSO profile with no account and no role, such as [profile ci]
    # with only sso_session = acme, keeps its own credentials in files.
    # Tools skip credential_daemon for it and use the keys in the files,
    # so keys stored in the daemon would never be used. So: files, never a
    # question, and AWS_CREDENTIAL_STORAGE=daemon is refused.
    if environ is None:
        environ = os.environ
    decision = decide_storage(
        environ.get(CREDENTIAL_STORAGE_ENV_VAR), None, None, False
    )
    if decision.storage is Storage.DAEMON:
        raise sso_without_role_error(profile_name, config)
    if decision.storage is Storage.FILE:
        return decision
    return StorageDecision(Storage.FILE, DecisionSource.SSO_WITHOUT_ROLE)


def resolve_storage(session, profile_name, environ=None):
    """The ``StorageDecision`` the profile's settings make, from
    ``AWS_CREDENTIAL_STORAGE`` or the profile's ``credential_storage``."""
    if environ is None:
        environ = os.environ
    env_value = environ.get(CREDENTIAL_STORAGE_ENV_VAR)
    # An empty or blank variable is unset, and a set one wins without the
    # profile being read.
    if env_value and env_value.strip():
        return decide_storage(env_value, None, None, False)
    section = profile_config(session, profile_name)
    where = f'profile "{profile_name}"'
    return decide_storage(None, section.get(CREDENTIAL_STORAGE), where, False)


def expanded_path(session, variable):
    """The path the session setting ``variable`` (``config_file`` or
    ``credentials_file``) names, with ``~`` expanded."""
    return os.path.expanduser(session.get_config_variable(variable))


def profile_or_default(profile_name):
    """The profile's name, or ``default`` for None.

    ``session.profile`` is None when no profile is selected, and the session
    then uses the default profile.
    """
    return 'default' if profile_name is None else profile_name


def profile_config(session, profile_name):
    # credential_storage and credential_daemon count only in the config
    # file, where aws configure set writes them.
    return profiles_with_config_file_keys(session).get(profile_name, {})
