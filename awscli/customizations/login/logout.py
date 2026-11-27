# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import logging
import os
import sys

from botocore.utils import (
    generate_login_cache_key,
    get_login_token_cache_directory,
)

from awscli.customizations.commands import BasicCommand
from awscli.customizations.login.backends import (
    ALL_SESSIONS,
    SignOutBackend,
    SignOutResult,
)
from awscli.customizations.login.credential_daemon_logout import (
    DaemonSignOut,
)
from awscli.customizations.sso.logout import BaseCredentialSweeper
from awscli.customizations.utils import uni_print

LOG = logging.getLogger(__name__)


class LogoutCommand(BasicCommand):
    NAME = 'logout'
    DESCRIPTION = (
        'Clears cached login credentials for the specified profile. If the '
        'profile uses the credential daemon (``credential_daemon``), it '
        'signs the profile\'s session out of the credential daemon '
        'instead. Every profile that names the same credential is signed '
        'out with it. With ``--all``, it also signs out every session in '
        'the credential daemon that the CLI created or signed in. Other '
        'tools\' sessions are left alone.'
    )
    ARG_TABLE = [
        {
            'name': 'all',
            'action': 'store_true',
            'help_text': (
                'Removes cached credentials for all profiles that use '
                '"aws login", and signs out every session the CLI created in '
                'the credential daemon. Does not remove access keys or '
                'credentials from profiles configured to use other styles '
                'of credentials.'
            ),
        },
    ]

    def __init__(
        self,
        session,
        cache_dir=get_login_token_cache_directory(),
        credential_daemon_client=None,
    ):
        super().__init__(session)
        self._credential_daemon = DaemonSignOut(
            session, cache_dir, client=credential_daemon_client
        )
        # Files first: they need no daemon. Then the credential daemon,
        # whatever happened to the files.
        self._backends = [
            FilesSignOut(session, cache_dir, self._credential_daemon),
            self._credential_daemon,
        ]

    def _run_main(self, parsed_args, parsed_globals):
        # One profile, or every session with --all.
        profile = ALL_SESSIONS
        if not getattr(parsed_args, 'all', False):
            profile = self._resolve_profile_name()
        results = []
        for backend in self._backends:
            for target in backend.sessions(profile):
                results.append(backend.sign_out(target))
        return self._report(profile, results)

    def _report(self, profile, results):
        """Exit 1 if any backend left something behind."""
        # Say nothing was found only when no backend had a session, so it
        # never contradicts a daemon sign-out or a daemon that couldn't be
        # checked.
        if profile is ALL_SESSIONS and all(r.empty for r in results):
            uni_print("No cached login session tokens found.\n")
        return 0 if all(r.ok for r in results) else 1

    def _resolve_profile_name(self):
        profile = self._session.profile
        return profile if profile is not None else 'default'


class FilesSignOut(SignOutBackend):
    """Signs out of the login token cache: deletes the session files.

    The deletes are unchanged on purpose: a profile that doesn't use the
    credential daemon sees the same output and exit codes as before.
    """

    def __init__(self, session, cache_dir, credential_daemon):
        self._session = session
        self._cache_dir = cache_dir
        self._credential_daemon = credential_daemon

    def sessions(self, profile):
        # A profile in the credential daemon is the credential daemon's,
        # with any session file an older CLI left beside it.
        if (
            profile is not ALL_SESSIONS
            and self._credential_daemon.credential_name(profile) is not None
        ):
            return []
        return [profile]

    def sign_out(self, target):
        if target is ALL_SESSIONS:
            return SignOutResult(
                ok=True, empty=self._delete_all_session_files()
            )
        return SignOutResult(
            ok=self._sign_out_profile(target) == 0, empty=None
        )

    def _sign_out_profile(self, profile):
        session_id = self._get_login_session_id(profile)
        if session_id is None:
            msg = f"warning: no login session found for profile '{profile}'\n"
            uni_print(msg, sys.stderr)
            return 0

        cache_key = generate_login_cache_key(session_id)
        file_to_delete = os.path.join(self._cache_dir, f"{cache_key}.json")

        if os.path.exists(file_to_delete):
            os.remove(file_to_delete)
        uni_print(
            f"Removed cached login credentials for profile '{profile}'. "
            "Note, any local developer tools that have already loaded the "
            "access token may continue to use it until its expiration. "
            "Access tokens expire in 15 minutes.\n"
        )
        return 0

    def _delete_all_session_files(self):
        """Delete every cached login session file. Returns whether there
        was nothing to delete."""
        sweeper = LoginTokenSweeper()
        deleted_count = sweeper.delete_credentials(self._cache_dir)
        if deleted_count > 0:
            plural = "s" if deleted_count != 1 else ""
            uni_print(
                f"Removed {deleted_count} cached login credential{plural}. "
                "Note, any local developer tools that have already loaded "
                "access tokens may continue to use them until their "
                "expiration. Access tokens expire in 15 minutes.\n"
            )
        return deleted_count == 0

    def _get_login_session_id(self, profile):
        loaded_config = self._session.full_config
        profiles = loaded_config.get('profiles', {})
        profile_config = profiles.get(profile, {})
        return profile_config.get('login_session')


class LoginTokenSweeper(BaseCredentialSweeper):
    def delete_credentials(self, creds_dir):
        """Override to return count of deleted credentials."""
        if not os.path.isdir(creds_dir):
            return 0

        deleted_count = 0
        filenames = os.listdir(creds_dir)
        for filename in filenames:
            filepath = os.path.join(creds_dir, filename)
            contents = self._get_json_contents(filepath)
            if contents is None:
                continue
            if self._should_delete(contents):
                self._before_deletion(contents)
                os.remove(filepath)
                deleted_count += 1

        return deleted_count

    def _should_delete(self, contents):
        access_token = contents.get('accessToken')
        return isinstance(access_token, dict) and 'accessKeyId' in access_token
