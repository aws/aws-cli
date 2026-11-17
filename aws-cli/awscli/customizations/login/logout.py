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
from awscli.customizations.sso.logout import BaseCredentialSweeper
from awscli.customizations.utils import uni_print

LOG = logging.getLogger(__name__)


class LogoutCommand(BasicCommand):
    NAME = 'logout'
    DESCRIPTION = 'Clears cached login credentials for the specified profile.'
    ARG_TABLE = [
        {
            'name': 'all',
            'action': 'store_true',
            'help_text': (
                'Removes cached credentials for all profiles that use '
                '"aws login". Does not remove credentials from profiles '
                'configured to use other styles of credentials.'
            ),
        },
    ]

    def __init__(
        self,
        session,
        cache_dir=get_login_token_cache_directory(),
    ):
        super().__init__(session)
        self._cache_dir = cache_dir

    def _run_main(self, parsed_args, parsed_globals):
        if getattr(parsed_args, 'all', False):
            return self._logout_all()
        else:
            return self._logout_single_profile()

    def _logout_single_profile(self):
        profile = self._resolve_profile_name()
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

    def _logout_all(self):
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
        else:
            uni_print("No cached login session tokens found.\n")
        return 0

    def _resolve_profile_name(self):
        profile = self._session.profile
        return profile if profile is not None else 'default'

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
        return (
            isinstance(access_token, dict) and 'accessKeyId' in access_token
        )
