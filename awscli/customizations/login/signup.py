# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from awscli.customizations.commands import BasicCommand
from awscli.customizations.login.login import LoginCommand
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
    AUTHORIZE_PROMPT = 'create'

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
