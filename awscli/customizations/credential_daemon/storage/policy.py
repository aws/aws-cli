# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""The credential_storage setting: its name, values and rules, and the
decision it makes. Nothing here reads files or the environment."""

from collections import namedtuple
from enum import Enum

from botocore.credential_daemon import strip_control_characters

from awscli.customizations.exceptions import ConfigurationError

CREDENTIAL_STORAGE = 'credential_storage'
CREDENTIAL_STORAGE_ENV_VAR = 'AWS_CREDENTIAL_STORAGE'
DAEMON = 'daemon'
FILE = 'file'


class Storage(Enum):
    """Where a profile's credentials go. Config files and messages use the
    setting's values, ``DAEMON`` and ``FILE`` (``.value``), never the
    member."""

    DAEMON = DAEMON
    FILE = FILE


class DecisionSource(Enum):
    """Where a storage decision came from."""

    ENV = 'env'
    SAVED = 'saved'
    NEW_ANSWER = 'answer'
    # No answer, but the profile is already in the credential daemon.
    PROFILE = 'profile'
    # No answer and no question: no terminal, or the credential daemon
    # isn't running.
    DEFAULT = 'default'
    # Files, because the profile is an SSO profile with no account and no
    # role, so the credential daemon is never used for it
    # (``sso_without_role_reason``).
    SSO_WITHOUT_ROLE = 'sso-without-role'


# A ``Storage`` and the ``DecisionSource`` that chose it, or both None when
# nothing has decided yet.
StorageDecision = namedtuple('StorageDecision', ['storage', 'source'])
UNDECIDED = StorageDecision(None, None)


def decide_storage(env_value, section_value, where, has_credential_daemon):
    """The decision from settings already read: ``AWS_CREDENTIAL_STORAGE``
    (``env_value``), then ``credential_storage`` (``section_value``) in
    ``where``, such as ``profile "dev"``, then ``credential_daemon`` in the
    profile (``has_credential_daemon``). ``UNDECIDED`` if none says.

    A bad value raises ``ConfigurationError``, the variable's before the
    setting is looked at.
    """
    # An empty or blank variable is unset.
    if env_value and env_value.strip():
        storage = _validate(env_value, CREDENTIAL_STORAGE_ENV_VAR)
        return StorageDecision(Storage(storage), DecisionSource.ENV)
    if section_value is not None:
        storage = _validate(section_value, f'{CREDENTIAL_STORAGE} in {where}')
        return StorageDecision(Storage(storage), DecisionSource.SAVED)
    # With nothing set, a profile that already names a credential stores
    # new credentials in the credential daemon without asking:
    #   [profile dev]
    #   credential_daemon = login.dev
    # aws login --profile dev signs in to the daemon, with no question.
    # credential_daemon wins over the profile's other settings, so new
    # credentials written to files would never be used.
    if has_credential_daemon:
        return StorageDecision(Storage.DAEMON, DecisionSource.PROFILE)
    return UNDECIDED


def sso_without_role_reason(profile_name, profile_config):
    """Why a profile with ``sso_session`` or ``sso_start_url`` and neither
    ``sso_account_id`` nor ``sso_role_name`` keeps its own credentials in
    files, as a sentence: tools skip ``credential_daemon`` for it."""
    key = 'sso_session' if 'sso_session' in profile_config else 'sso_start_url'
    return (
        f"Profile '{strip_control_characters(profile_name)}' has {key} "
        f'without an account or role, so the credential daemon can\'t '
        f'serve its credentials.'
    )


class SsoWithoutRoleError(ConfigurationError):
    """A request to store the own credentials of an SSO profile with no
    account and no role in the credential daemon (``sso_without_role_error``).
    aws configure import refuses only that row."""


def sso_without_role_error(
    profile_name,
    profile_config,
    remedy=f'run the command again with {CREDENTIAL_STORAGE_ENV_VAR}={FILE}',
):
    """The ``ConfigurationError`` for a request to store such a profile's
    own credentials in the credential daemon, such as
    ``AWS_CREDENTIAL_STORAGE=daemon``. ``remedy`` says how to store them in
    files instead, or is None when they're already there."""
    tail = f' To store them in files, {remedy}.' if remedy else ''
    return SsoWithoutRoleError(
        f'{sso_without_role_reason(profile_name, profile_config)} Nothing '
        f'was changed.{tail}'
    )


def _validate(value, source):
    if not isinstance(value, str):
        # An indented line after the key makes the value a dict.
        raise ConfigurationError(
            f'Invalid value for {strip_control_characters(source)}: it '
            f'isn\'t a single value. Use '
            f'"{DAEMON}" or "{FILE}", on the same line as the key.'
        )
    normalized = _normalize(value)
    if normalized not in (DAEMON, FILE):
        raise ConfigurationError(
            f'Invalid value "{strip_control_characters(value)}" for '
            f'{strip_control_characters(source)}. '
            f'Use "{DAEMON}" or "{FILE}".'
        )
    return normalized


def _normalize(value):
    return value.strip().lower()
