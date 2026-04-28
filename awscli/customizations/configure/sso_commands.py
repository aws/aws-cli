# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""
Defines SSO-specific configure commands, to be used with the `aws configure`
command.

The main reason it lives in its own separate module instead of in
`awscli/customizations/configure/sso.py` is so that these commands can be
referenced without importing `awscli/customizations/configure/sso.py`,
which imports from `prompt_toolkit`. Importing from `prompt_toolkit` has
historically increased command execution times.

This separation helps us limit our imports from `prompt_toolkit` to when it
is actually needed, improving execution time across most commands.
"""
import logging
import os

import colorama
from botocore import UNSIGNED
from botocore.config import Config
from botocore.configprovider import ConstantProvider
from botocore.exceptions import ProfileNotFound

from awscli.customizations.configure import (
    get_section_header,
    profile_to_section,
)
from awscli.customizations.configure.writer import ConfigFileWriter
from awscli.customizations.sso.utils import (
    LOGIN_ARGS,
    BaseSSOCommand,
    PrintOnlyHandler,
    do_sso_login,
)
from awscli.customizations.utils import uni_print
from awscli.formatter import CLI_OUTPUT_FORMATS

logger = logging.getLogger(__name__)

_CMD_PROMPT_USAGE = (
    'To keep an existing value, hit enter when prompted for the value. When '
    'you are prompted for information, the current value will be displayed in '
    '[brackets]. If the config item has no value, it is displayed as '
    '[None] or omitted entirely.\n\n'
)
_CONFIG_EXTRA_INFO = (
    'Note: The configuration is saved in the shared configuration file. '
    'By default, ``~/.aws/config``. For more information, see the '
    '"Configuring the AWS CLI to use AWS IAM Identity Center" section in the '
    'AWS CLI User Guide:'
    '\n\nhttps://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html'
)


def display_account(account):
    """Converts an SSO account response into a display string.

    All fields should be present in the API response but we've seen some
    cases where the account name or email address is not set. Considering
    we only need the account name and email address for display purposes
    we should be defensive just in case they don't come back.
    """
    if 'accountName' not in account and 'emailAddress' not in account:
        account_template = '{accountId}'
    elif 'emailAddress' not in account:
        account_template = '{accountName} ({accountId})'
    elif 'accountName' not in account:
        account_template = '{emailAddress} ({accountId})'
    else:
        account_template = '{accountName}, {emailAddress} ({accountId})'
    return account_template.format(**account)


def get_account_sorting_key(account):
    only_account_id = ('accountName' not in account and 'emailAddress' not in account)
    for key in ('accountName', 'emailAddress', 'accountId'):
        value = account.get(key, None)
        if value is not None:
            return (only_account_id, value.lower())
    return (only_account_id, None)


class BaseSSOConfigurationCommand(BaseSSOCommand):
    def __init__(self, session, prompter=None, config_writer=None):
        super(BaseSSOConfigurationCommand, self).__init__(session)
        self._prompter = prompter
        if config_writer is None:
            config_writer = ConfigFileWriter()
        self._config_writer = config_writer
        self._sso_sessions = self._session.full_config.get('sso_sessions', {})
        # Initialize self._sso_session_prompter to None. It will be
        # initialized lazily during command execution.
        self._sso_session_prompter = None

    def _init_prompt_toolkit(self):
        from awscli.customizations.configure.sso import (
            PTKPrompt,
            SSOSessionConfigurationPrompter,
        )
        if self._prompter is None:
            self._prompter = PTKPrompt()

        self._sso_session_prompter = SSOSessionConfigurationPrompter(
            botocore_session=self._session,
            prompter=self._prompter,
        )

    def _write_sso_configuration(self):
        self._update_section(
            section_header=get_section_header(
                'sso-session', self._sso_session_prompter.sso_session
            ),
            new_values=self._sso_session_prompter.sso_session_config,
        )

    def _update_section(self, section_header, new_values):
        config_path = self._session.get_config_variable('config_file')
        config_path = os.path.expanduser(config_path)
        new_values['__section__'] = section_header
        self._config_writer.update_config(new_values, config_path)

    def _run_main(self, parsed_args, parsed_globals):
        self._init_prompt_toolkit()


class ConfigureSSOCommand(BaseSSOConfigurationCommand):
    NAME = 'sso'
    SYNOPSIS = 'aws configure sso [--profile profile-name]'
    DESCRIPTION = (
        'The ``aws configure sso`` command interactively prompts for the '
        'configuration values required to create a profile that sources '
        'temporary AWS credentials from AWS IAM Identity Center.\n\n'
        f'{_CMD_PROMPT_USAGE}'
        'When providing the ``--profile`` parameter the named profile '
        'will be created or updated. When a profile is not explicitly set '
        'the profile name will be prompted for.\n\n'
        f'{_CONFIG_EXTRA_INFO}'
    )
    # TODO: Add CLI parameters to skip prompted values, --start-url, etc.
    ARG_TABLE = LOGIN_ARGS

    def __init__(
        self,
        session,
        prompter=None,
        selector=None,
        config_writer=None,
        sso_token_cache=None,
        sso_login=None,
    ):
        super(ConfigureSSOCommand, self).__init__(
            session, prompter=prompter, config_writer=config_writer
        )
        self._selector = selector
        if sso_login is None:
            sso_login = do_sso_login
        self._sso_login = sso_login
        self._sso_token_cache = sso_token_cache

        self._new_profile_config_values = {}
        self._original_profile_name = self._session.profile
        try:
            self._profile_config = self._session.get_scoped_config()
        except ProfileNotFound:
            self._profile_config = {}

    def _init_prompt_toolkit(self):
        super()._init_prompt_toolkit()
        if self._selector is None:
            from awscli.customizations.wizard.ui.selectmenu import select_menu
            self._selector = select_menu
        self._set_sso_session_if_configured_in_profile()

    def _set_sso_session_if_configured_in_profile(self):
        if 'sso_session' in self._profile_config:
            self._sso_session_prompter.sso_session = self._profile_config[
                'sso_session'
            ]

    def _handle_single_account(self, accounts):
        sso_account_id = accounts[0]['accountId']
        single_account_msg = 'The only AWS account available to you is: {}\n'
        uni_print(single_account_msg.format(sso_account_id))
        return sso_account_id

    def _handle_multiple_accounts(self, accounts):
        available_accounts_msg = (
            'There are {} AWS accounts available to you.\n'
        )
        uni_print(available_accounts_msg.format(len(accounts)))
        sorted_accounts = sorted(accounts, key=get_account_sorting_key)
        selected_account = self._selector(
            sorted_accounts, display_format=display_account
        )
        sso_account_id = selected_account['accountId']
        return sso_account_id

    def _get_all_accounts(self, sso, sso_token):
        paginator = sso.get_paginator('list_accounts')
        results = paginator.paginate(accessToken=sso_token['accessToken'])
        return results.build_full_result()

    def _prompt_for_account(self, sso, sso_token):
        accounts = self._get_all_accounts(sso, sso_token)['accountList']
        if not accounts:
            raise RuntimeError('No AWS accounts are available to you.')
        if len(accounts) == 1:
            sso_account_id = self._handle_single_account(accounts)
        else:
            sso_account_id = self._handle_multiple_accounts(accounts)
        uni_print(f'Using the account ID {sso_account_id}\n')
        self._new_profile_config_values['sso_account_id'] = sso_account_id
        return sso_account_id

    def _handle_single_role(self, roles):
        sso_role_name = roles[0]['roleName']
        available_roles_msg = 'The only role available to you is: {}\n'
        uni_print(available_roles_msg.format(sso_role_name))
        return sso_role_name

    def _handle_multiple_roles(self, roles):
        available_roles_msg = 'There are {} roles available to you.\n'
        uni_print(available_roles_msg.format(len(roles)))
        sorted_roles = sorted(roles, key=lambda x: x['roleName'].lower())
        role_names = [r['roleName'] for r in sorted_roles]
        sso_role_name = self._selector(role_names)
        return sso_role_name

    def _get_all_roles(self, sso, sso_token, sso_account_id):
        paginator = sso.get_paginator('list_account_roles')
        results = paginator.paginate(
            accountId=sso_account_id, accessToken=sso_token['accessToken']
        )
        return results.build_full_result()

    def _prompt_for_role(self, sso, sso_token, sso_account_id):
        roles = self._get_all_roles(sso, sso_token, sso_account_id)['roleList']
        if not roles:
            error_msg = 'No roles are available for the account {}'
            raise RuntimeError(error_msg.format(sso_account_id))
        if len(roles) == 1:
            sso_role_name = self._handle_single_role(roles)
        else:
            sso_role_name = self._handle_multiple_roles(roles)
        uni_print(f'Using the role name "{sso_role_name}"\n')
        self._new_profile_config_values['sso_role_name'] = sso_role_name
        return sso_role_name

    def _prompt_for_profile(self, sso_account_id=None, sso_role_name=None):
        from awscli.customizations.configure.sso import RequiredInputValidator
        if self._original_profile_name:
            profile_name = self._original_profile_name
        else:
            text = 'Profile name'
            default_profile = None
            if sso_account_id and sso_role_name:
                default_profile = f'{sso_role_name}-{sso_account_id}'
            validator = RequiredInputValidator(default_profile)
            profile_name = self._prompter.get_value(
                default_profile, text, validator=validator
            )
        return profile_name

    def _prompt_for_cli_default_region(self):
        # TODO: figure out a way to get a list of reasonable client regions
        return self._prompt_for_profile_config(
            'region', 'Default client Region'
        )

    def _prompt_for_cli_output_format(self):
        return self._prompt_for_profile_config(
            'output',
            'CLI default output format (json if not specified)',
            completions=list(CLI_OUTPUT_FORMATS.keys()),
        )

    def _prompt_for_profile_config(self, config_name, text, completions=None):
        current_value = self._profile_config.get(config_name)

        new_value = self._prompter.get_value(
            current_value,
            text,
            completions=completions,
        )
        if new_value:
            self._new_profile_config_values[config_name] = new_value
        return new_value

    def _unset_session_profile(self):
        config_store = self._session.get_component('config_store')
        config_store.set_config_provider('profile', ConstantProvider(None))

    def _run_main(self, parsed_args, parsed_globals):
        super()._run_main(parsed_args, parsed_globals)
        self._unset_session_profile()
        on_pending_authorization = None
        if parsed_args.no_browser:
            on_pending_authorization = PrintOnlyHandler()
        sso_registration_args = self._prompt_for_sso_registration_args()
        sso_token = self._sso_login(
            self._session,
            parsed_globals=parsed_globals,
            token_cache=self._sso_token_cache,
            on_pending_authorization=on_pending_authorization,
            use_device_code=parsed_args.use_device_code,
            **sso_registration_args,
        )

        client_config = Config(
            signature_version=UNSIGNED,
            region_name=sso_registration_args['sso_region'],
        )
        sso = self._session.create_client('sso', config=client_config)

        sso_account_id, sso_role_name = self._prompt_for_sso_account_and_role(
            sso, sso_token
        )
        configured_for_aws_credentials = all((sso_account_id, sso_role_name))

        self._prompt_for_cli_default_region()
        self._prompt_for_cli_output_format()

        profile_name = self._prompt_for_profile(sso_account_id, sso_role_name)

        self._write_new_config(profile_name)
        self._print_conclusion(configured_for_aws_credentials, profile_name)
        return 0

    def _prompt_for_sso_registration_args(self):
        sso_session = self._sso_session_prompter.prompt_for_sso_session(
            required=False
        )
        if sso_session is None:
            self._warn_configuring_using_legacy_format()
            return self._prompt_for_registration_args_with_legacy_format()
        else:
            self._set_sso_session_in_profile_config(sso_session)
            if sso_session in self._sso_sessions:
                return self._get_sso_registration_args_from_sso_config(
                    sso_session
                )
            else:
                return self._prompt_for_registration_args_for_new_sso_session(
                    sso_session=sso_session
                )

    def _prompt_for_registration_args_with_legacy_format(self):
        self._store_sso_session_prompter_answers_to_profile_config()
        self._set_sso_session_defaults_from_profile_config()
        start_url, sso_region = self._prompt_for_sso_start_url_and_sso_region()
        return {'start_url': start_url, 'sso_region': sso_region}

    def _get_sso_registration_args_from_sso_config(self, sso_session):
        sso_config = self._get_sso_session_config(sso_session)
        return {
            'session_name': sso_session,
            'start_url': sso_config['sso_start_url'],
            'sso_region': sso_config['sso_region'],
            'registration_scopes': sso_config.get('registration_scopes'),
        }

    def _prompt_for_registration_args_for_new_sso_session(self, sso_session):
        self._set_sso_session_defaults_from_profile_config()
        start_url, sso_region = self._prompt_for_sso_start_url_and_sso_region()
        scopes = (
            self._sso_session_prompter.prompt_for_sso_registration_scopes()
        )
        return {
            'session_name': sso_session,
            'start_url': start_url,
            'sso_region': sso_region,
            'registration_scopes': scopes,
            'force_refresh': True,
        }

    def _store_sso_session_prompter_answers_to_profile_config(self):
        self._sso_session_prompter.sso_session_config = (
            self._new_profile_config_values
        )

    def _set_sso_session_in_profile_config(self, sso_session):
        self._new_profile_config_values['sso_session'] = sso_session

    def _set_sso_session_defaults_from_profile_config(self):
        if 'sso_start_url' in self._profile_config:
            self._sso_session_prompter.sso_session_config['sso_start_url'] = (
                self._profile_config['sso_start_url']
            )
        if 'sso_region' in self._profile_config:
            self._sso_session_prompter.sso_session_config['sso_region'] = (
                self._profile_config['sso_region']
            )

    def _prompt_for_sso_start_url_and_sso_region(self):
        start_url = self._sso_session_prompter.prompt_for_sso_start_url()
        sso_region = self._sso_session_prompter.prompt_for_sso_region()
        return start_url, sso_region

    def _warn_configuring_using_legacy_format(self):
        uni_print(
            f'{colorama.Style.BRIGHT}WARNING: Configuring using legacy format '
            f'(e.g. without an SSO session).\n'
            f'Consider re-running "configure sso" command and providing '
            f'a session name.\n{colorama.Style.RESET_ALL}'
        )

    def _prompt_for_sso_account_and_role(self, sso, sso_token):
        sso_account_id = None
        sso_role_name = None
        try:
            sso_account_id = self._prompt_for_account(sso, sso_token)
            sso_role_name = self._prompt_for_role(
                sso, sso_token, sso_account_id
            )
        except sso.exceptions.UnauthorizedException:
            uni_print(
                'Unable to list AWS accounts and/or roles. '
                'Skipping configuring AWS credential provider for profile.\n'
            )
        return sso_account_id, sso_role_name

    def _write_new_config(self, profile):
        if self._new_profile_config_values:
            profile_section = profile_to_section(profile)
            self._update_section(
                profile_section, self._new_profile_config_values
            )
        if self._sso_session_prompter.sso_session:
            self._write_sso_configuration()

    def _print_conclusion(self, configured_for_aws_credentials, profile_name):
        if configured_for_aws_credentials:
            if profile_name.lower() == 'default':
                msg = (
                    'The AWS CLI is now configured to use the default profile.\n'
                    'Run the following command to verify your configuration:\n\n'
                    'aws sts get-caller-identity\n'
                )
            else:
                msg = (
                    'To use this profile, specify the profile name using '
                    '--profile, as shown:\n\n'
                    'aws sts get-caller-identity --profile {}\n'
                )
        else:
            msg = 'Successfully configured SSO for profile: {}\n'
        uni_print(msg.format(profile_name))


class ConfigureSSOSessionCommand(BaseSSOConfigurationCommand):
    NAME = 'sso-session'
    SYNOPSIS = 'aws configure sso-session'
    DESCRIPTION = (
        'The ``aws configure sso-session`` command interactively prompts for '
        'the configuration values required to create a SSO session. '
        'The SSO session can then be associated to a profile to retrieve '
        'SSO access tokens and AWS credentials.\n\n'
        f'{_CMD_PROMPT_USAGE}'
        f'{_CONFIG_EXTRA_INFO}'
    )

    def _run_main(self, parsed_args, parsed_globals):
        super()._run_main(parsed_args, parsed_globals)
        self._sso_session_prompter.prompt_for_sso_session()
        self._sso_session_prompter.prompt_for_sso_start_url()
        self._sso_session_prompter.prompt_for_sso_region()
        self._sso_session_prompter.prompt_for_sso_registration_scopes()
        self._write_sso_configuration()
        self._print_configuration_success()
        return 0

    def _print_configuration_success(self):
        sso_session = self._sso_session_prompter.sso_session
        uni_print(
            f'\nCompleted configuring SSO session: {sso_session}\n'
            f'Run the following to login and refresh access token for '
            f'this session:\n\n'
            f'aws sso login --sso-session {sso_session}\n'
        )
