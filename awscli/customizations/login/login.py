# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os
import webbrowser

import botocore
from awscrt.crypto import EC, ECType
from botocore.exceptions import ProfileNotFound
from botocore.loaders import Loader
from botocore.utils import (
    JSONFileCache,
    LoginCredentialsLoader,
    get_login_token_cache_directory,
)

from awscli.compat import compat_input
from awscli.customizations.commands import BasicCommand
from awscli.customizations.configure.sso import (
    PTKPrompt,
    RequiredInputValidator,
)
from awscli.customizations.configure.writer import ConfigFileWriter
from awscli.customizations.login.utils import (
    CrossDeviceLoginTokenFetcher,
    LoginType,
    SameDeviceLoginTokenFetcher,
)
from awscli.customizations.sso.utils import (
    AuthCodeFetcher,
    OpenBrowserHandler,
    PrintOnlyHandler,
    open_browser_with_original_ld_path,
)
from awscli.customizations.utils import uni_print

DEFAULT_REGION_FOR_PROMPT = 'us-east-1'


class LoginCommand(BasicCommand):
    NAME = 'login'
    DESCRIPTION = (
        'Login for local development using AWS Management Console '
        'credentials. Each time the ``login`` command is called, the '
        'CLI will acquire temporary credentials and a refresh token '
        'that correspond to your selected console session. '
        'The CLI will refresh the temporary credentials automatically '
        'as long as the refresh token is valid.\n\n'
        'You can override the directory where the CLI will store the '
        'temporary credentials with the ``AWS_LOGIN_CACHE_DIRECTORY`` '
        'environment variable.'
    )
    ARG_TABLE = [
        {
            'name': 'remote',
            'action': 'store_true',
            'default': False,
            'help_text': (
                'Disables the local callback server and redirect-based auth '
                'flow. Instead displays the URL and prompts you to paste the '
                'authorization code that is displayed after logging in. This is '
                'intended when running the CLI on remote hosts via SSH '
                'where a local browser is not available.'
            ),
        }
    ]

    def __init__(
        self,
        session,
        token_loader=None,
        config_file_writer=None,
    ):
        super().__init__(session)

        # Records if we had to prompt the user for a region,
        # which we'll save to the profile when we do
        self._prompted_for_region = False

        if token_loader is None:
            token_cache = JSONFileCache(get_login_token_cache_directory())
            token_loader = LoginCredentialsLoader(token_cache)
        self._token_loader = token_loader

        if config_file_writer is None:
            config_file_writer = ConfigFileWriter()
        self._config_file_writer = config_file_writer

    def _run_main(self, parsed_args, parsed_globals):
        region = self._resolve_region(parsed_globals)
        profile_name = self.resolve_profile_name()
        sign_in_type = self.resolve_sign_in_type(parsed_args)

        # If the profile specified via --profile doesn't already exist
        # add it to the session so the client creation still succeeds.
        # If the login is successful we'll save the profile at the end.
        if profile_name not in self._session.available_profiles:
            self._session._profile_map[profile_name] = {}

        config = botocore.config.Config(
            region_name=region,
            signature_version=botocore.UNSIGNED,
        )
        client = self._session.create_client(
            'signin',
            config=config,
            endpoint_url=parsed_globals.endpoint_url,
            verify=parsed_globals.verify_ssl,
        )

        private_key = EC.new_generate(ECType.P_256)

        if sign_in_type is LoginType.SAME_DEVICE:
            token_fetcher = SameDeviceLoginTokenFetcher(
                client=client,
                auth_code_fetcher=AuthCodeFetcher(),
                on_pending_authorization=OpenBrowserHandler(
                    open_browser=open_browser_with_original_ld_path
                ),
                private_key=private_key,
            )
        else:  # Cross-Device
            token_fetcher = CrossDeviceLoginTokenFetcher(
                client=client,
                on_pending_authorization=PrintOnlyHandler(),
                private_key=private_key,
            )

        # Execute the browser flow, and the initial call to the token endpoint
        access_token, session_id = token_fetcher.fetch_token()

        if not self.accept_change_to_existing_profile_if_needed(
            profile_name, session_id
        ):
            return

        # Cache the access token to disk
        self._token_loader.save_token(session_id, access_token)

        # Update the specified profile with the session (and region if not set)
        self._update_profile_with_login_session(
            profile_name, session_id, region
        )

        uni_print(
            f'\nUpdated profile {profile_name} to use {session_id} credentials.\n'
        )
        if profile_name != 'default':
            uni_print(
                f'Use "--profile {profile_name}" to use the new credentials, '
                f'such as "aws sts get-caller-identity --profile {profile_name}"\n'
            )

    def accept_change_to_existing_profile_if_needed(
        self, profile_name, new_session_id
    ):
        config = self._session.full_config['profiles'].get(profile_name, {})

        if 'login_session' not in config:
            return True

        existing_session_id = config['login_session']

        if existing_session_id == new_session_id:
            return True

        while True:
            response = compat_input(
                f'\nProfile {profile_name} is already configured to use session '
                f'{existing_session_id}. Do you want to overwrite it to use '
                f'{new_session_id} instead? (y/n): '
            )

            if response.lower() in ('y', 'yes'):
                return True
            elif response.lower() in ('n', 'no'):
                return False
            else:
                uni_print('Invalid response. Please enter "y" or "n"')

    @staticmethod
    def resolve_sign_in_type(parsed_args):
        if parsed_args.remote:
            return LoginType.CROSS_DEVICE

        return LoginType.SAME_DEVICE

    def resolve_profile_name(self):
        profile = self._session.profile
        return profile if profile is not None else 'default'

    def _resolve_region(self, parsed_globals):
        if parsed_globals.region:
            return parsed_globals.region
        try:
            if self._session.get_config_variable('region'):
                return self._session.get_config_variable('region')
        except ProfileNotFound:
            pass

        return self._prompt_for_region()

    def _prompt_for_region(self):
        prompter = PTKPrompt()
        self._prompted_for_region = True
        uni_print(
            'No AWS region has been configured. '
            'The AWS region is the geographic location of your AWS resources.\n\n'
            'If you have used AWS before and already have resources in your '
            'account, specify which region they were created in. '
            'If you have not created resources in your account before, you '
            'can pick the region closest to you: '
            'https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.html.\n\n'
            'You are able to change the region in the CLI at any time with '
            'the command "aws configure set region NEW_REGION".\n'
        )
        new_region = prompter.get_value(
            DEFAULT_REGION_FOR_PROMPT,
            'AWS Region',
            completions=list(self._load_all_regions()),
            validator=RequiredInputValidator(DEFAULT_REGION_FOR_PROMPT),
        )

        return new_region if new_region else DEFAULT_REGION_FOR_PROMPT

    @staticmethod
    def _load_all_regions():
        """Loads all regions from all partitions via partitions.json"""
        loader = Loader()
        for partition in loader.load_data('partitions')['partitions']:
            yield from partition['regions'].keys()

    def _update_profile_with_login_session(
        self, profile_name, session_id, region
    ):
        config_filename = os.path.expanduser(
            self._session.get_config_variable('config_file')
        )

        section_name = (
            'default'
            if profile_name == 'default'
            else f'profile {profile_name}'
        )

        new_values = {
            '__section__': section_name,
            'login_session': session_id,
        }

        if self._prompted_for_region:
            new_values['region'] = region

        self._config_file_writer.update_config(new_values, config_filename)
