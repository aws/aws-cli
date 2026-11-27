# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os

import botocore
from awscrt.crypto import EC, ECType
from botocore.configprovider import ConfiguredEndpointProvider
from botocore.credential_daemon import (
    CREDENTIAL_DAEMON_KEY,
    profiles_with_config_file_keys,
)
from botocore.exceptions import ProfileNotFound
from botocore.utils import (
    JSONFileCache,
    LoginCredentialsLoader,
    get_login_token_cache_directory,
)

from awscli.customizations.agenttoolkit.hint import (
    maybe_prompt_agent_toolkit,
)
from awscli.customizations.commands import BasicCommand
from awscli.customizations.configure.writer import ConfigFileWriter
from awscli.customizations.credential_daemon.hint import (
    print_session_install_hint,
)
from awscli.customizations.credential_daemon.storage.chooser import (
    CredentialStorageChooser,
)
from awscli.customizations.login.backends import (
    SignInBackend,
    SignInRequest,
    SignInResult,
)
from awscli.customizations.login.credential_daemon import (
    DaemonSignIn,
    SessionMove,
    redirect_port_refused_error,
    refuses_redirect_port,
)
from awscli.customizations.login.utils import (
    CrossDeviceLoginTokenFetcher,
    LoginType,
    SameDeviceLoginTokenFetcher,
    decode_id_token_payload,
    existing_credentials_error,
)
from awscli.customizations.prompts import yes_no_choice
from awscli.customizations.sso.utils import (
    REDIRECT_PORT_ARG,
    AuthCodeFetcher,
    OpenBrowserHandler,
    PrintOnlyHandler,
    open_browser_with_original_ld_path,
    validate_redirect_port,
)
from awscli.customizations.utils import load_all_regions, uni_print
from awscli.utils import is_stdin_a_tty

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
        'environment variable.\n\n'
        'If the profile uses the credential daemon '
        '(``credential_storage = daemon``), the credential daemon keeps the '
        'session and refreshes its credentials instead, and nothing is '
        'cached on disk. The profile gets ``credential_daemon``, not '
        '``login_session``, and ``AWS_LOGIN_CACHE_DIRECTORY`` doesn\'t '
        'apply.'
    )
    EXAMPLES = BasicCommand.FROM_FILE()
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
        },
        REDIRECT_PORT_ARG,
    ]

    def __init__(
        self,
        session,
        token_loader=None,
        config_file_writer=None,
        chooser=None,
        credential_daemon_client=None,
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
        self._chooser = chooser or CredentialStorageChooser(
            session, config_writer=config_file_writer
        )
        self._credential_daemon = DaemonSignIn(
            session, self._chooser, client=credential_daemon_client
        )
        self._files = self._files_sign_in()

    def _run_main(self, parsed_args, parsed_globals):
        request = self._resolve(parsed_args, parsed_globals)
        backend = self._sign_in_backend(request)
        result = backend.sign_in(request)
        if not result.ok:
            return result.exit_code

        # What the profile leaves where its session was goes in the same
        # write.
        values = dict(result.profile_values)
        if request.leaving is not None:
            values.update(request.leaving.values_to_clear())
        # Update the specified profile with the session (and region if not
        # set). A new profile's answer goes in the same write, so a failed
        # write leaves no profile behind.
        try:
            profile_region = self._resolve_profile_region(
                request.profile_name, request.region, result.access_token
            )
            self._write_profile(request.profile_name, values, profile_region)
        except BaseException:
            backend.write_failed(request)
            raise

        # Also clears what the profile left, at its place in the output.
        backend.after_write(request, result)
        self._print_next_steps(
            request.profile_name,
            request.region,
            request.is_new_profile,
            parsed_globals,
        )
        if result.exit_code is None and request.leaving is not None:
            # The sign-in worked, but the old session is still in the
            # credential daemon, or a session file couldn't be deleted.
            return request.leaving.exit_code
        return result.exit_code

    def _resolve(self, parsed_args, parsed_globals):
        """What the sign-in needs, as a ``SignInRequest``. Everything that
        can fail before the browser opens fails here."""
        validate_redirect_port(parsed_args.redirect_port)
        profile_name = self.resolve_profile_name()
        sign_in_type = self.resolve_sign_in_type(parsed_args)
        redirect_port = parsed_args.redirect_port
        self._check_ready_before_prompts(
            profile_name, redirect_port, sign_in_type
        )
        region = self._resolve_region(parsed_globals)

        # If the profile specified via --profile doesn't already exist
        # add it to the session so the client creation still succeeds.
        # If the login is successful we'll save the profile at the end.
        is_new_profile = profile_name not in self._session.available_profiles
        if is_new_profile:
            self._session._profile_map[profile_name] = {}

        # Abort if the profile is already configured with a different style
        # of credentials, since they'd still have precedence over login
        self.ensure_profile_does_not_have_existing_credentials(profile_name)

        choice = self._choose_storage(
            profile_name, redirect_port, sign_in_type
        )
        request = SignInRequest(
            profile_name=profile_name,
            region=region,
            sign_in_type=sign_in_type,
            is_new_profile=is_new_profile,
            parsed_args=parsed_args,
            parsed_globals=parsed_globals,
            choice=choice,
        )
        backend = self._sign_in_backend(request)
        backend.check(profile_name, self.NAME)
        return request._replace(leaving=self._leaving(profile_name, backend))

    def _sign_in_backend(self, request):
        """The backend that signs in and keeps the session: the credential
        daemon or files, as the storage choice says."""
        if request.choice.uses_credential_daemon:
            return self._credential_daemon
        return self._files

    def _files_sign_in(self):
        """The backend that keeps the session in the login token cache."""
        return FilesSignIn(
            self._session,
            self._token_loader,
            chooser=self._chooser,
            config_writer=self._config_file_writer,
        )

    def _leaving(self, profile_name, new):
        """What the profile leaves in the other backend, if its session is
        there now, or None."""
        before = self._credential_daemon.profile_config(profile_name)
        for backend in (self._credential_daemon, self._files):
            if backend is not new and backend.holds(profile_name, before):
                return backend.leave(profile_name, before)
        return None

    def _check_ready_before_prompts(
        self, profile_name, redirect_port, sign_in_type
    ):
        """Fail before any prompt if the profile's credential daemon
        isn't ready, or if its credential there holds access keys."""
        # A refused port gets its own error first.
        daemon_path = not refuses_redirect_port(redirect_port, sign_in_type)
        if not daemon_path and self._chooser.stores_in_credential_daemon(
            profile_name
        ):
            # The sign-in goes to the credential daemon without asking, so
            # the port is refused before the region prompt too.
            raise redirect_port_refused_error()
        if daemon_path:
            # Before the region prompt and the browser, so a credential
            # daemon that isn't there fails the command before it asks
            # anything.
            self._credential_daemon.check_ready_if_stored(profile_name)
        # Before the region prompt too: access keys in the credential
        # daemon are refused, whether the sign-in goes there or back to
        # files.
        self._credential_daemon.refuse_access_keys(
            profile_name, self.NAME, daemon_path=daemon_path
        )

    def _choose_storage(self, profile_name, redirect_port, sign_in_type):
        """Where the sign-in goes: the credential daemon or files."""
        if refuses_redirect_port(redirect_port, sign_in_type):
            # Don't ask about the credential daemon for a sign-in it can't do.
            # A profile already in the credential daemon gets the port error
            # before anything is saved or sent to the credential daemon.
            choice = self._chooser.choose_without_asking(profile_name)
        else:
            # A new storage answer is saved only once the sign-in succeeds,
            # with the profile, so a cancelled or failed sign-in saves
            # nothing.
            choice = self._chooser.choose(profile_name)
        return choice

    def _print_next_steps(
        self, profile_name, region, is_new_profile, parsed_globals
    ):
        if profile_name != 'default':
            uni_print(
                f'Use "--profile {profile_name}" to use the new credentials, '
                f'such as "aws sts get-caller-identity --profile {profile_name}"\n'
            )

        # Only nudge on first-time setup (a newly created profile), not on
        # routine re-auth of an existing profile.
        if is_new_profile:
            maybe_prompt_agent_toolkit(
                self._session, parsed_globals, region=region
            )

    def ensure_profile_does_not_have_existing_credentials(self, profile_name):
        """
        Raises an error if the specified profile is already
        configured with a different style of credentials.
        """
        config = self._config_for_credentials_check(profile_name)
        existing_credentials_style = self._existing_credentials_style(config)

        if existing_credentials_style:
            raise existing_credentials_error(
                self.NAME, profile_name, existing_credentials_style
            )

        return False

    def _config_for_credentials_check(self, profile_name):
        """The profile's settings that the credentials check reads, with
        credential_daemon and credential_storage from the config file."""
        config = self._credential_daemon.profile_config(profile_name)
        if CREDENTIAL_DAEMON_KEY in config:
            # Next to credential_daemon, the credential daemon wins: the
            # keys are ignored on the credential daemon path, with a
            # warning, and credential_process is the documented line for
            # older SDKs, which a newer CLI ignores.
            config = {
                key: value
                for key, value in config.items()
                if key not in ('aws_access_key_id', 'credential_process')
            }
        # A credential_daemon's type comes from the credential daemon, not
        # from its name. Access keys there are refused before any prompt,
        # whatever credential_storage says (_check_ready_before_prompts).
        return config

    def _existing_credentials_style(self, config):
        """The style of credentials ``config`` already has, or None."""
        existing_credentials_style = None

        if 'web_identity_token_file' in config:
            existing_credentials_style = 'Web Identity'
        elif 'sso_role_name' in config or 'sso_account_id' in config:
            existing_credentials_style = 'SSO'
        elif 'aws_access_key_id' in config:
            existing_credentials_style = 'Access Key'
        elif 'role_arn' in config:
            existing_credentials_style = 'Assume Role'
        elif 'credential_process' in config:
            existing_credentials_style = 'Credential Process'

        return existing_credentials_style

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
        from awscli.customizations.configure.sso import (
            PTKPrompt,
            RequiredInputValidator,
        )

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
            completions=list(load_all_regions()),
            validator=RequiredInputValidator(DEFAULT_REGION_FOR_PROMPT),
        )

        return new_region if new_region else DEFAULT_REGION_FOR_PROMPT

    def _resolve_profile_region(self, profile_name, region, access_token):
        home_region = self._get_home_region(access_token)
        if self._prompted_for_region:
            # The customer picked this before we knew the home region.
            if self._should_use_home_region(profile_name, region, home_region):
                return home_region
            return region

        existing_region = self._get_profile_region(profile_name)
        if existing_region:
            if self._should_use_home_region(
                profile_name, existing_region, home_region
            ):
                return home_region
            return None

        # The region came from --region or the environment. Ask instead of
        # saving it, since the region used to sign in isn't necessarily the
        # one the customer wants as the profile's default. The home region
        # is the better default, as regional services only work there.
        if not is_stdin_a_tty():
            # Passing --region is how a login runs without a terminal, so
            # leave the region unset rather than prompting where no one can
            # answer. The sign-in has already succeeded either way.
            return None
        try:
            return self._prompt_for_profile_region(
                profile_name, home_region or region
            )
        except (KeyboardInterrupt, EOFError):
            return None

    def _get_profile_region(self, profile_name):
        profile = self._session.full_config['profiles'].get(profile_name, {})
        return profile.get('region')

    @staticmethod
    def _get_home_region(access_token):
        if access_token is None:
            # The credential daemon keeps the ID token, so there's no home
            # region to read.
            return None
        # Sign-In only includes this for accounts that have a home region.
        return decode_id_token_payload(access_token['idToken']).get(
            'aws_home_region'
        )

    def _should_use_home_region(self, profile_name, region, home_region):
        if not home_region or home_region == region:
            return False
        if not is_stdin_a_tty():
            return False
        try:
            if not yes_no_choice(
                f'\nProfile {profile_name} is configured for region '
                f'{region}, but the home region for this account is '
                f'{home_region}. Regional services outside the home region '
                f'are denied. Do you want to set the region to '
                f'{home_region}? (y/n): '
            ):
                return False
        except (KeyboardInterrupt, EOFError):
            return False
        self._print_home_region_set(home_region)
        return True

    @staticmethod
    def _print_home_region_set(home_region):
        uni_print(
            f'\nSet region to {home_region}, '
            'the home region for this account.\n'
        )

    def _prompt_for_profile_region(self, profile_name, default_region):
        from awscli.customizations.configure.sso import (
            PTKPrompt,
            RequiredInputValidator,
        )

        uni_print(f'\nNo region is set for profile {profile_name}.\n')
        new_region = PTKPrompt().get_value(
            default_region,
            'AWS Region',
            completions=list(load_all_regions()),
            validator=RequiredInputValidator(default_region),
        )
        return new_region if new_region else default_region

    def _write_profile(self, profile_name, values, region):
        """The one config write for a sign-in: the backend's values, and the
        region if there is one to save."""
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
            **values,
        }

        if region:
            new_values['region'] = region

        self._config_file_writer.update_config(new_values, config_filename)


class FilesSignIn(SignInBackend):
    """Signs in with the sign-in client and keeps the session in the login
    token cache. The profile gets its ``login_session``."""

    def __init__(
        self,
        session,
        token_loader,
        authorize_prompt=None,
        chooser=None,
        config_writer=None,
    ):
        self._session = session
        self._token_loader = token_loader
        # Sent as the OIDC prompt parameter on the authorize request.
        self._authorize_prompt = authorize_prompt
        self._config_writer = config_writer or ConfigFileWriter()
        self._chooser = chooser or CredentialStorageChooser(
            session, config_writer=self._config_writer
        )

    def check(self, profile_name, command):
        """Refuse files for a profile whose access keys would win over
        login_session."""
        # Moving back to files: the keys would win over login_session, so
        # they're refused as for any other profile.
        config = profiles_with_config_file_keys(self._session).get(
            profile_name, {}
        )
        if 'aws_access_key_id' in config:
            raise existing_credentials_error(
                command, profile_name, 'Access Key'
            )

    def holds(self, profile_name, before):
        """Whether the profile names a session file."""
        return before.get('login_session') is not None

    def leave(self, profile_name, before):
        """What a sign-in into the credential daemon does with the session
        file the profile had, as a ``SessionMove``."""
        return SessionMove(
            self._session, self._config_writer, profile_name, before
        )

    def sign_in(self, request):
        profile_name = request.profile_name
        region = request.region
        sign_in_type = request.sign_in_type
        parsed_args = request.parsed_args
        parsed_globals = request.parsed_globals

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
                auth_code_fetcher=AuthCodeFetcher(
                    redirect_port=parsed_args.redirect_port,
                ),
                on_pending_authorization=OpenBrowserHandler(
                    open_browser=open_browser_with_original_ld_path
                ),
                private_key=private_key,
                prompt=self._authorize_prompt,
            )
        else:  # Cross-Device
            token_fetcher = CrossDeviceLoginTokenFetcher(
                client=client,
                on_pending_authorization=PrintOnlyHandler(),
                private_key=private_key,
                prompt=self._authorize_prompt,
            )

        # Execute the browser flow, and the initial call to the token endpoint
        access_token, session_id = token_fetcher.fetch_token()

        if not self.accept_change_to_existing_profile_if_needed(
            profile_name, session_id
        ):
            return SignInResult(ok=False, exit_code=None)

        # Record where we signed in. Refresh tokens are regional, so the
        # refresh has to go back to the same region rather than whatever
        # region is configured when it runs. An endpoint override supplies
        # the host instead, so the region no longer says where the request
        # went and we leave it out for the refresh to resolve itself.
        if not self._resolve_endpoint_override(parsed_globals):
            access_token['signInRegion'] = region

        # Cache the access token to disk
        self._token_loader.save_token(session_id, access_token)

        values = dict(self._chooser.unsaved_values(request.choice))
        values['login_session'] = session_id
        return SignInResult(
            ok=True,
            exit_code=None,
            profile_values=values,
            access_token=access_token,
        )

    def after_write(self, request, result):
        profile_name = request.profile_name
        session_id = result.profile_values['login_session']
        uni_print(
            f'\nUpdated profile {profile_name} to use {session_id} credentials.\n'
        )
        choice = request.choice
        leaving = request.leaving
        self._chooser.mark_saved(choice)
        if leaving is not None:
            leaving.note()
        storage_line = self._chooser.storage_line(choice)
        if storage_line is not None:
            uni_print(f'{storage_line}\n')
        if leaving is not None:
            # Clears the credential the profile left.
            for line in leaving.release():
                uni_print(f'{line}\n')
            leaving.after_summary()
        self._chooser.print_saved_line(choice)
        self._print_install_hint(choice)

    def _print_install_hint(self, choice):
        """After the file write: the note to install the credential daemon,
        when the session went to a file before it's installed."""
        print_session_install_hint(choice, get_login_token_cache_directory())

    def accept_change_to_existing_profile_if_needed(
        self, profile_name, new_session_id
    ):
        config = self._session.full_config['profiles'].get(profile_name, {})

        if 'login_session' not in config:
            return True

        existing_session_id = config['login_session']

        if existing_session_id == new_session_id:
            return True

        return yes_no_choice(
            f'\nProfile {profile_name} is already configured to use session '
            f'{existing_session_id}. Do you want to overwrite it to use '
            f'{new_session_id} instead? (y/n): '
        )

    def _resolve_endpoint_override(self, parsed_globals):
        if parsed_globals.endpoint_url:
            return parsed_globals.endpoint_url
        if self._session.get_config_variable(
            'ignore_configured_endpoint_urls'
        ):
            return None
        return ConfiguredEndpointProvider(
            full_config=self._session.full_config,
            scoped_config=self._session.get_scoped_config(),
            client_name='signin',
        ).provide()
