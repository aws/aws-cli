# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""The credential daemon's part of ``aws logout``: signing sessions out of
the credential daemon."""

import logging
import os
import sys

from botocore.credential_daemon import (
    Source,
    credential_daemon_value,
    is_logout_unsupported,
    is_sso_profile_without_role,
)
from botocore.exceptions import (
    CredentialDaemonCredentialNotFoundError,
    CredentialDaemonError,
)

from awscli.customizations.credential_daemon.command import (
    CredentialDaemonCommandSupport,
)
from awscli.customizations.credential_daemon.messages import (
    quoted_names,
    uses_phrase,
    warn_unsupported_platform,
)
from awscli.customizations.credential_daemon.sessions import (
    profiles_naming,
    profiles_using_credential_daemon,
    profiles_using_session_file,
)
from awscli.customizations.credential_daemon.storage.chooser import (
    CREDENTIAL_DAEMON,
)
from awscli.customizations.login.backends import (
    ALL_SESSIONS,
    SignOutBackend,
    SignOutResult,
)
from awscli.customizations.login.utils import (
    delete_session_file,
    report_undeleted_file,
    session_file_path,
)
from awscli.customizations.utils import uni_print

LOG = logging.getLogger(__name__)


class DaemonSignOut(CredentialDaemonCommandSupport, SignOutBackend):
    """Signs profiles and sessions out of the credential daemon, with any
    session file an older CLI left beside a profile in it.
    ``FilesSignOut`` (logout.py) has the other session files.
    """

    def __init__(self, session, cache_dir, client=None):
        super().__init__(session, client=client)
        self._cache_dir = cache_dir

    def sessions(self, profile):
        if profile is ALL_SESSIONS:
            return [ALL_SESSIONS]
        name = self.credential_name(profile)
        if name is None:
            return []
        session_id = self.profile_config(profile).get('login_session')
        return [(profile, name, session_id)]

    def sign_out(self, target):
        if target is ALL_SESSIONS:
            sweep = self._logout_all_from_credential_daemon()
            # cleared is None when the credential daemon couldn't be
            # checked: it may hold sessions, so it isn't empty.
            return SignOutResult(
                ok=sweep.ok, empty=sweep.ok and sweep.cleared == 0
            )
        return SignOutResult(
            ok=self._logout_from_credential_daemon(*target) == 0, empty=None
        )

    def _logout_from_credential_daemon(self, profile, name, session_id):
        # An older CLI may have written a plaintext session beside it.
        # Delete it first: it's local and doesn't need the credential daemon.
        file_ok = self._delete_leftover_session_file(profile, session_id)
        credential_daemon_ok = self.logout_profile(profile, name)
        return 0 if file_ok and credential_daemon_ok else 1

    def _delete_leftover_session_file(self, profile, session_id):
        if session_id is None:
            return True
        path = session_file_path(session_id, self._cache_dir)
        users = profiles_using_session_file(self._session, session_id, profile)
        if users and os.path.lexists(path):
            # The CLI deletes only what no other profile uses. For example,
            # [profile a] and [profile b] both with login_session =
            # arn:aws:iam::111122223333:user/dev share one session file:
            # aws logout --profile a keeps it, since an older CLI signed in
            # as b still reads it.
            uni_print(
                f"Kept the cached login session file for profile "
                f"'{profile}', because {uses_phrase(users)}.\n",
                sys.stderr,
            )
            return True
        if users:
            # Nothing to delete or keep.
            return True
        try:
            deleted = delete_session_file(path)
        except OSError as e:
            report_undeleted_file(path, e)
            return False
        if deleted:
            uni_print(
                f"Removed the cached login session file for profile "
                f"'{profile}'.\n"
            )
        return True

    def credential_name(self, profile):
        """The credential the profile names in the credential daemon, or
        None.

        None for an SSO profile with no account and no role: tools skip
        its credential_daemon, such as sso.acme that aws sso login wrote on
        [profile ci] with only sso_session = acme, and use its aws login
        session in files, so that session is what aws logout signs out.
        """
        config = self.profile_config(profile)
        if is_sso_profile_without_role(config):
            return None
        return credential_daemon_value(profile, config)

    def logout_profile(self, profile, name):
        """Sign the profile out of credential ``name``. Returns whether
        nothing was left signed in."""
        if not self.runs_here():
            # As for aws logout --all: signing out can't succeed here, so
            # it's a warning, not an error, whatever
            # AWS_CREDENTIAL_DAEMON_SOCKET says.
            warn_unsupported_platform([profile])
            return True
        client = self.client()
        try:
            # The credential daemon decides what it holds: it
            # signs out a session and refuses access keys, which have no
            # sign-in.
            result = client.logout(name)
        except CredentialDaemonCredentialNotFoundError:
            uni_print(
                f"warning: the {CREDENTIAL_DAEMON} has no "
                f"credential named '{name}' "
                f"for profile '{profile}'\n",
                sys.stderr,
            )
            return True
        except CredentialDaemonError as e:
            if is_logout_unsupported(e):
                # The credential daemon says it has no sign-in, as for
                # access keys.
                _print_no_session_to_clear(profile)
                return True
            self.report_uncleared(
                f"The session for profile '{profile}'",
                e,
                "wasn't",
                'aws logout',
            )
            return False
        if not result.signed_out:
            # As for a profile with no session file.
            uni_print(
                f"warning: no login session found for profile '{profile}' "
                f"in the {CREDENTIAL_DAEMON}\n",
                sys.stderr,
            )
            return True
        # Profiles that name the same credential share its session.
        others = profiles_naming(self._session, name, profile)
        also = ''
        if others:
            also = f' (also signed out: {quoted_names(others)})'
        uni_print(
            f"Signed out of profile '{profile}' in the "
            f"{CREDENTIAL_DAEMON}{also}. Note, any "
            "local developer tools that have already loaded its credentials "
            "may continue to use them until they expire, in at most 15 "
            "minutes.\n"
        )
        return True

    def _logout_all_from_credential_daemon(self):
        """Sign out of every session the CLI made in the credential daemon,
        except SSO sessions, which aws sso logout signs out. credsd always
        sends a row's source, so a row without one isn't an SSO session
        here."""
        return self.sign_out_tagged(
            select=lambda row: row.source != Source.SSO,
            what='session',
            command='aws logout --all',
            profiles_using=lambda: profiles_using_credential_daemon(
                self._session
            ),
            log=LOG,
            log_message='Not clearing credential daemon sessions: %s',
        )


def _print_no_session_to_clear(profile):
    # No advice on the keys: in this release aws configure can't change or
    # remove keys the credential daemon holds. For example, 'aws configure
    # --profile ci' on a profile with credential_daemon = keys.ci writes
    # ~/.aws/credentials and leaves keys.ci in use.
    uni_print(
        f"warning: profile '{profile}' has no sign-in session to clear in "
        f"the {CREDENTIAL_DAEMON}.\n",
        sys.stderr,
    )
