# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""aws configure's part for the credential daemon: a new profile's access
keys can go there instead of ~/.aws/credentials.

Only a profile that is in neither file, with a long-term key pair typed,
gets the storage question. Every other run of aws configure writes the
files as before.
"""

from botocore.credential_daemon import (
    CREDENTIAL_DAEMON_KEY,
    KEYS_TAG,
    end_sentence,
    find_credential_row,
    strip_control_characters,
    tagged_credential_name,
)
from botocore.exceptions import (
    CredentialDaemonApprovalRequiredError,
    CredentialDaemonError,
)

from awscli.customizations.credential_daemon.command import (
    CredentialDaemonCommandSupport,
)
from awscli.customizations.credential_daemon.messages import (
    CREDENTIAL_DAEMON,
    DAEMON_UNAVAILABLE_ERRORS,
    daemon_down_message,
    mark_created_by_cli,
)
from awscli.customizations.credential_daemon.storage.chooser import (
    CredentialStorageChooser,
)
from awscli.customizations.credential_daemon.storage.kinds import (
    CredentialKind,
)
from awscli.customizations.credential_daemon.storage.profiles import (
    profile_or_default,
)
from awscli.customizations.exceptions import ConfigurationError
from awscli.customizations.utils import uni_print

# Where the credential daemon makes its STS calls with the keys when no
# region is typed or configured: GetSessionToken's global endpoint.
DEFAULT_REGION = 'us-east-1'


class NewProfileKeys(CredentialDaemonCommandSupport):
    """Stores a new profile's access keys in the credential daemon, if the
    storage question (or ``AWS_CREDENTIAL_STORAGE``) chooses it."""

    def __init__(self, session, chooser=None, client=None, config_writer=None):
        super().__init__(session, client)
        self._chooser = chooser or CredentialStorageChooser(
            session, config_writer=config_writer
        )

    def save(self, profile_name, new_values, region):
        """Decide where the typed keys go, before any file is written.

        Returns None when aws configure writes the files as before: the
        profile exists, or no long-term pair was typed. Else a ``Saved``,
        whose ``values`` go into the profile's config write. When the
        keys went to the credential daemon, they're taken out of
        ``new_values``, so nothing goes to ~/.aws/credentials.
        """
        profile_name = profile_or_default(profile_name)
        if profile_name in self._session.available_profiles:
            # For example, keys typed for a profile with
            #   credential_daemon = keys.dev
            # go to ~/.aws/credentials as before, and aren't used while
            # credential_daemon is set.
            return None
        if not _long_term_pair(new_values):
            return None
        choice = self._chooser.choose(
            profile_name, kind=CredentialKind.STATIC_KEYS
        )
        saved = Saved(choice, self._chooser.unsaved_values(choice))
        if choice.uses_credential_daemon:
            name = tagged_credential_name(KEYS_TAG, profile_name)
            # The keys are stored before the config write, and stay stored
            # if the store is interrupted or that write fails. For example,
            # Ctrl-C while the keys are sent, or a full disk after the
            # store, can leave keys.dev in the credential daemon with no
            # profile naming it; if aws configure --profile dev stores in
            # the credential daemon again, it says the name is taken and
            # to use another profile name. Not undone: only the normal
            # path is handled in this release.
            self._store(
                profile_name,
                name,
                new_values['aws_access_key_id'],
                new_values['aws_secret_access_key'],
                region or DEFAULT_REGION,
            )
            del new_values['aws_access_key_id']
            del new_values['aws_secret_access_key']
            saved.name = name
            saved.values[CREDENTIAL_DAEMON_KEY] = name
        return saved

    def _store(self, profile_name, name, access_key_id, secret, region):
        client = self.client()
        try:
            # A name already there, such as one a deleted profile left, is
            # refused rather than replaced: replacing it needs the
            # customer's approval in the credential daemon.
            if find_credential_row(client.list_credentials(), name) is None:
                client.store_keys(name, access_key_id, secret, region)
                mark_created_by_cli(
                    client, name, done='Stored the keys', clears=None
                )
                return
        except CredentialDaemonApprovalRequiredError:
            # Stored by something else since the list.
            pass
        except DAEMON_UNAVAILABLE_ERRORS as e:
            raise ConfigurationError(
                f'{daemon_down_message(e)} {self._not_stored(profile_name)}'
            ) from e
        except CredentialDaemonError as e:
            # Such as a refused store; the message may quote the daemon.
            raise ConfigurationError(
                f'{end_sentence(_shown(str(e)))} '
                f'{self._not_stored(profile_name)}'
            ) from e
        raise ConfigurationError(
            f"The {CREDENTIAL_DAEMON} already has a credential named "
            f"'{_shown(name)}'. {self._not_stored(profile_name)} Use another "
            'profile name.'
        )

    def _not_stored(self, profile_name):
        return (
            f"The keys for profile '{_shown(profile_name)}' may not have "
            f'been stored in the {CREDENTIAL_DAEMON}, and nothing was saved '
            'to ~/.aws.'
        )

    def after_write(self, saved):
        """After the config write: what the customer is told."""
        if saved is None:
            return
        self._chooser.mark_saved(saved.choice)
        if saved.name is not None:
            uni_print(f'Stored in the {CREDENTIAL_DAEMON}.\n')
        self._chooser.print_saved_line(saved.choice)


class Saved:
    """Where a new profile's keys went: the storage ``choice``, the config
    ``values`` to write with the profile, and the credential's ``name`` in
    the credential daemon, or None for files."""

    def __init__(self, choice, values):
        self.choice = choice
        self.values = dict(values)
        self.name = None


def _long_term_pair(new_values):
    # Only both keys, typed together: a lone key ID or secret, or
    # temporary keys (an ASIA key ID, or a session token), go to the files
    # as before.
    key_id = new_values.get('aws_access_key_id')
    return (
        bool(key_id)
        and bool(new_values.get('aws_secret_access_key'))
        and not key_id.startswith('ASIA')
        and not new_values.get('aws_session_token')
    )


def _shown(name):
    return strip_control_characters(name)
