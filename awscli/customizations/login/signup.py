# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from awscli.customizations.commands import BasicCommand
from awscli.customizations.credential_daemon.storage.chooser import (
    StorageChoice,
)
from awscli.customizations.credential_daemon.storage.policy import (
    DecisionSource,
    Storage,
)
from awscli.customizations.login.login import FilesSignIn, LoginCommand
from awscli.customizations.utils import uni_print

# Sign-In is allowed here for every new account, whatever its home region.
DEFAULT_SIGNUP_REGION = 'us-east-1'


class SignupCommand(LoginCommand):
    NAME = 'signup'
    DESCRIPTION = (
        'Create an AWS account and sign in to it. The ``signup`` command '
        'opens AWS account creation in your browser. When you finish, the '
        'CLI acquires temporary credentials and a refresh token that '
        'correspond to the console session for your new account, and sets '
        'the profile\'s region to the account\'s home region. The CLI '
        'refreshes the temporary credentials automatically as long as the '
        'refresh token is valid.\n\n'
        'You can override the directory where the CLI will store the '
        'temporary credentials with the ``AWS_LOGIN_CACHE_DIRECTORY`` '
        'environment variable.'
    )
    EXAMPLES = BasicCommand.FROM_FILE()

    def _files_sign_in(self):
        # The authorize request opens account creation, not sign-in.
        return SignupFilesSignIn(
            self._session,
            self._token_loader,
            authorize_prompt='create',
            chooser=self._chooser,
            config_writer=self._config_file_writer,
        )

    def _check_ready_before_prompts(
        self, profile_name, redirect_port, sign_in_type
    ):
        # Nothing to check: signup never uses the credential daemon.
        pass

    def ensure_profile_does_not_have_existing_credentials(self, profile_name):
        # Signup always signs in with files and refuses only what aws login
        # refuses on any profile, such as access keys in it. It never
        # refuses a profile set up for the credential daemon. For example,
        # on a profile with credential_storage = daemon, aws signup
        # --profile dev writes the session to files and prints nothing
        # about it. That keeps signup simple and the same as aws sso login,
        # which also ignores the setting.
        super().ensure_profile_does_not_have_existing_credentials(profile_name)
        return False

    def _leaving(self, profile_name, new):
        # Nothing moves out of the credential daemon. With
        # credential_daemon = login.111122223333-role-Admin, signup adds
        # login_session next to it, leaves that credential alone and sends
        # the credential daemon nothing; credential_daemon still takes
        # precedence when credentials are resolved, as after aws sso login
        # on such a profile.
        return None

    def _choose_storage(self, profile_name, redirect_port, sign_in_type):
        """Files, without asking: the credential daemon can't ask Sign-In to
        create an account."""
        return StorageChoice(
            Storage.FILE,
            DecisionSource.DEFAULT,
            profile_name=profile_name,
        )

    def _resolve_region(self, parsed_globals):
        # Signup takes place in us-east-1, which works for every new account
        # whatever its home region. A region from the profile or environment
        # is usually set for other work and could leave the browser stuck
        # after the account is created, so only --region overrides it.
        return parsed_globals.region or DEFAULT_SIGNUP_REGION

    def _resolve_profile_region(self, profile_name, region, access_token):
        home_region = self._get_home_region(access_token)
        existing_region = self._get_profile_region(profile_name)
        if not home_region:
            # Only point at setting a region if the profile doesn't have one.
            if not existing_region:
                uni_print(
                    '\nCould not determine the home region for this account. '
                    'To set the region for this profile, run "aws configure '
                    f'set region REGION --profile {profile_name}".\n'
                )
            return None

        if existing_region:
            if self._should_use_home_region(
                profile_name, existing_region, home_region
            ):
                return home_region
            return None

        # A new account has one region where regional services work, so
        # there's nothing to choose between.
        self._print_home_region_set(home_region)
        return home_region


class SignupFilesSignIn(FilesSignIn):
    def _print_install_hint(self, choice):
        # No hint: the daemon wouldn't protect a session signup keeps in
        # a file by design.
        pass
