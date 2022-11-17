# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import collections
import itertools
import json
import os
import logging
import re

import colorama
from botocore import UNSIGNED
from botocore.config import Config
from botocore.configprovider import ConstantProvider
from botocore.exceptions import ProfileNotFound
from botocore.utils import is_valid_endpoint_url

from prompt_toolkit import prompt as ptk_prompt
from prompt_toolkit.application import get_app
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import Validator
from prompt_toolkit.validation import ValidationError

from awscli.customizations.utils import uni_print
from awscli.customizations.configure import (
    profile_to_section, get_section_header,
)
from awscli.customizations.configure.writer import ConfigFileWriter
from awscli.customizations.wizard.ui.selectmenu import select_menu
from awscli.customizations.sso.utils import (
    do_sso_login, parse_sso_registration_scopes, PrintOnlyHandler, LOGIN_ARGS,
    BaseSSOCommand,
)
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
    '"Configuring the AWS CLI to use AWS Single Sign-On" section in the AWS '
    'CLI User Guide:'
    '\n\nhttps://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html'
)


class ValidatorWithDefault(Validator):
    def __init__(self, default=None):
        super(ValidatorWithDefault, self).__init__()
        self._default = default

    def _raise_validation_error(self, document, message):
        index = len(document.text)
        raise ValidationError(index, message)


class StartUrlValidator(ValidatorWithDefault):
    def validate(self, document):
        # If there's a default, allow an empty prompt
        if not document.text and self._default:
            return
        if not is_valid_endpoint_url(document.text):
            self._raise_validation_error(document, 'Not a valid Start URL')


class RequiredInputValidator(ValidatorWithDefault):
    def validate(self, document):
        if document.text or self._default:
            return
        self._raise_validation_error(document, 'A value is required')


class ScopesValidator(ValidatorWithDefault):
    def validate(self, document):
        # If there's a default, allow an empty prompt
        if not document.text and self._default:
            return
        if not self._is_comma_separated_list(document.text):
            self._raise_validation_error(
                document, 'Scope values must be separated by commas')

    def _is_comma_separated_list(self, value):
        scopes = value.split(',')
        for scope in scopes:
            if re.findall(r'\s', scope.strip()):
                return False
        return True


class PTKPrompt(object):
    _DEFAULT_PROMPT_FORMAT = '{prompt_text} [{current_value}]: '

    def __init__(self, prompter=None):
        if prompter is None:
            prompter = ptk_prompt
        self._prompter = prompter

    def _create_completer(self, completions):
        if completions is None:
            completions = []
        completer_kwargs = {
            'words': completions,
            'pattern': re.compile(r'\S+')
        }
        if isinstance(completions, dict):
            completer_kwargs['meta_dict'] = completions
            completer_kwargs['words'] = list(completions.keys())
        return WordCompleter(**completer_kwargs)

    def get_value(self, current_value, prompt_text='',
                  completions=None, validator=None, toolbar=None,
                  prompt_fmt=None):
        if prompt_fmt is None:
            prompt_fmt = self._DEFAULT_PROMPT_FORMAT
        prompt_string = prompt_fmt.format(
            prompt_text=prompt_text,
            current_value=current_value
        )
        prompter_kwargs = {
            'validator': validator,
            'validate_while_typing': False,
            'completer': self._create_completer(completions),
            'complete_while_typing': True,
            'style': self._get_prompt_style(),
        }
        if toolbar:
            prompter_kwargs['bottom_toolbar'] = toolbar
            prompter_kwargs['refresh_interval'] = 0.2
        response = self._prompter(prompt_string, **prompter_kwargs)
        # Strip any extra white space
        response = response.strip()
        if not response:
            # If the user hits enter, we return the current/default value
            response = current_value
        return response

    def _get_prompt_style(self):
        return Style.from_dict(
            {
                'bottom-toolbar': 'noreverse',
            }
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


class SSOSessionConfigurationPrompter:
    _DEFAULT_SSO_SCOPE = 'sso:account:access'
    _KNOWN_SSO_SCOPES = {
        'sso:account:access': (
            'Grants access to AWS IAM Identity Center accounts and permission '
            'sets'
        )
    }

    def __init__(self, botocore_session, prompter):
        self._botocore_session = botocore_session
        self._prompter = prompter
        self._sso_sessions = self._botocore_session.full_config.get(
            'sso_sessions', {})
        self._sso_session = None
        self.sso_session_config = {}

    @property
    def sso_session(self):
        return self._sso_session

    @sso_session.setter
    def sso_session(self, value):
        self._sso_session = value
        self.sso_session_config = self._sso_sessions.get(
            self._sso_session, {}).copy()

    def prompt_for_sso_session(self, required=True):
        prompt_text = 'SSO session name'
        prompt_fmt = None
        validator_cls = None
        if required:
            validator_cls = RequiredInputValidator
        if not self.sso_session:
            prompt_fmt = f'{prompt_text}: '
            if not required:
                prompt_fmt = f'{prompt_text} (Recommended): '
        sso_session = self._prompt_for(
            'sso_session', prompt_text,
            completions=sorted(self._sso_sessions),
            toolbar=self._get_sso_session_toolbar,
            validator_cls=validator_cls,
            prompt_fmt=prompt_fmt,
            current_value=self.sso_session,
        )
        self.sso_session = sso_session
        return sso_session

    def prompt_for_sso_start_url(self):
        return self._prompt_for(
            'sso_start_url', 'SSO start URL',
            completions=self._get_potential_start_urls(),
            validator_cls=StartUrlValidator,
        )

    def prompt_for_sso_region(self):
        return self._prompt_for(
            'sso_region', 'SSO region',
            completions=self._get_potential_sso_regions(),
            validator_cls=RequiredInputValidator,
        )

    def prompt_for_sso_registration_scopes(self):
        if 'sso_registration_scopes' not in self.sso_session_config:
            self.sso_session_config['sso_registration_scopes'] = \
                self._DEFAULT_SSO_SCOPE
        raw_scopes = self._prompt_for(
            'sso_registration_scopes', 'SSO registration scopes',
            completions=self._get_potential_sso_registrations_scopes(),
            validator_cls=ScopesValidator,
        )
        return parse_sso_registration_scopes(raw_scopes)

    def _prompt_for(self, config_name, text,
                    completions=None, validator_cls=None,
                    toolbar=None, prompt_fmt=None, current_value=None):
        if current_value is None:
            current_value = self.sso_session_config.get(config_name)
        validator = None
        if validator_cls:
            validator = validator_cls(current_value)
        value = self._prompter.get_value(
            current_value, text,
            completions=completions,
            validator=validator,
            toolbar=toolbar,
            prompt_fmt=prompt_fmt
        )
        if value:
            self.sso_session_config[config_name] = value
        return value

    def _get_sso_session_toolbar(self):
        current_input = get_app().current_buffer.document.text
        if current_input in self._sso_sessions:
            selected_sso_config = self._sso_sessions[current_input]
            return FormattedText([
                ('',  self._get_toolbar_border()),
                ('', '\n'),
                ('bold', f'Configuration for SSO session: {current_input}\n\n'),
                ('', json.dumps(selected_sso_config, indent=2)),
            ])

    def _get_toolbar_border(self):
        horizontal_line_char = '\u2500'
        return horizontal_line_char * get_app().output.get_size().columns

    def _get_potential_start_urls(self):
        profiles = self._botocore_session.full_config.get('profiles', {})
        configs_to_search = itertools.chain(
            profiles.values(),
            self._sso_sessions.values()
        )
        potential_start_urls = set()
        for config_to_search in configs_to_search:
            if 'sso_start_url' in config_to_search:
                start_url = config_to_search['sso_start_url']
                potential_start_urls.add(start_url)
        return list(potential_start_urls)

    def _get_potential_sso_regions(self):
        return self._botocore_session.get_available_regions('sso-oidc')

    def _get_potential_sso_registrations_scopes(self):
        potential_scopes = self._KNOWN_SSO_SCOPES.copy()
        scopes_to_sessions = self._get_previously_used_scopes_to_sso_sessions()
        for scope, sso_sessions in scopes_to_sessions.items():
            if scope not in potential_scopes:
                potential_scopes[scope] = (
                    f'Used in SSO sessions: {", ".join(sso_sessions)}'
                )
        return potential_scopes

    def _get_previously_used_scopes_to_sso_sessions(self):
        scopes_to_sessions = collections.defaultdict(list)
        for sso_session, sso_session_config in self._sso_sessions.items():
            if 'sso_registration_scopes' in sso_session_config:
                parsed_scopes = parse_sso_registration_scopes(
                    sso_session_config['sso_registration_scopes']
                )
                for parsed_scope in parsed_scopes:
                    scopes_to_sessions[parsed_scope].append(sso_session)
        return scopes_to_sessions


class BaseSSOConfigurationCommand(BaseSSOCommand):
    def __init__(self, session, prompter=None, config_writer=None):
        super(BaseSSOConfigurationCommand, self).__init__(session)
        if prompter is None:
            prompter = PTKPrompt()
        self._prompter = prompter
        if config_writer is None:
            config_writer = ConfigFileWriter()
        self._config_writer = config_writer
        self._sso_sessions = self._session.full_config.get('sso_sessions', {})
        self._sso_session_prompter = SSOSessionConfigurationPrompter(
            botocore_session=session, prompter=self._prompter,
        )

    def _write_sso_configuration(self):
        self._update_section(
            section_header=get_section_header(
                'sso-session', self._sso_session_prompter.sso_session),
            new_values=self._sso_session_prompter.sso_session_config
        )

    def _update_section(self, section_header, new_values):
        config_path = self._session.get_config_variable('config_file')
        config_path = os.path.expanduser(config_path)
        new_values['__section__'] = section_header
        self._config_writer.update_config(new_values, config_path)


class ConfigureSSOCommand(BaseSSOConfigurationCommand):
    NAME = 'sso'
    SYNOPSIS = ('aws configure sso [--profile profile-name]')
    DESCRIPTION = (
        'The ``aws configure sso`` command interactively prompts for the '
        'configuration values required to create a profile that sources '
        'temporary AWS credentials from AWS Single Sign-On.\n\n'
        f'{_CMD_PROMPT_USAGE}'
        'When providing the ``--profile`` parameter the named profile '
        'will be created or updated. When a profile is not explicitly set '
        'the profile name will be prompted for.\n\n'
        f'{_CONFIG_EXTRA_INFO}'
    )
    # TODO: Add CLI parameters to skip prompted values, --start-url, etc.
    ARG_TABLE = LOGIN_ARGS

    def __init__(self, session, prompter=None, selector=None,
                 config_writer=None, sso_token_cache=None, sso_login=None):
        super(ConfigureSSOCommand, self).__init__(
            session, prompter=prompter, config_writer=config_writer)
        if selector is None:
            selector = select_menu
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
        self._set_sso_session_if_configured_in_profile()

    def _set_sso_session_if_configured_in_profile(self):
        if 'sso_session' in self._profile_config:
            self._sso_session_prompter.sso_session = \
                self._profile_config['sso_session']

    def _handle_single_account(self, accounts):
        sso_account_id = accounts[0]['accountId']
        single_account_msg = (
            'The only AWS account available to you is: {}\n'
        )
        uni_print(single_account_msg.format(sso_account_id))
        return sso_account_id

    def _handle_multiple_accounts(self, accounts):
        available_accounts_msg = (
            'There are {} AWS accounts available to you.\n'
        )
        uni_print(available_accounts_msg.format(len(accounts)))
        selected_account = self._selector(
            accounts, display_format=display_account)
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
        uni_print('Using the account ID {}\n'.format(sso_account_id))
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
        role_names = [r['roleName'] for r in roles]
        sso_role_name = self._selector(role_names)
        return sso_role_name

    def _get_all_roles(self, sso, sso_token, sso_account_id):
        paginator = sso.get_paginator('list_account_roles')
        results = paginator.paginate(
            accountId=sso_account_id,
            accessToken=sso_token['accessToken']
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
        uni_print('Using the role name "{}"\n'.format(sso_role_name))
        self._new_profile_config_values['sso_role_name'] = sso_role_name
        return sso_role_name

    def _prompt_for_profile(self, sso_account_id=None, sso_role_name=None):
        if self._original_profile_name:
            profile_name = self._original_profile_name
        else:
            text = 'CLI profile name'
            default_profile = None
            if sso_account_id and sso_role_name:
                default_profile = f'{sso_role_name}-{sso_account_id}'
            validator = RequiredInputValidator(default_profile)
            profile_name = self._prompter.get_value(
                default_profile, text, validator=validator)
        return profile_name

    def _prompt_for_cli_default_region(self):
        # TODO: figure out a way to get a list of reasonable client regions
        return self._prompt_for_profile_config(
            'region', 'CLI default client Region')

    def _prompt_for_cli_output_format(self):
        return self._prompt_for_profile_config(
            'output', 'CLI default output format',
            completions=list(CLI_OUTPUT_FORMATS.keys()),
        )

    def _prompt_for_profile_config(self, config_name, text, completions=None):
        current_value = self._profile_config.get(config_name)
        new_value = self._prompter.get_value(
            current_value, text,
            completions=completions,
        )
        if new_value:
            self._new_profile_config_values[config_name] = new_value
        return new_value

    def _unset_session_profile(self):
        # The profile provided to the CLI as --profile may not exist.
        # This means we cannot use the session as is to create clients.
        # By overriding the profile provider we ensure that a non-existant
        # profile won't cause us to fail to create clients.
        # No configuration from the profile is needed for the SSO APIs.
        # It might be good to see if we can address this in a better way
        # in botocore.
        config_store = self._session.get_component('config_store')
        config_store.set_config_provider('profile', ConstantProvider(None))

    def _run_main(self, parsed_args, parsed_globals):
        self._unset_session_profile()
        on_pending_authorization = None
        if parsed_args.no_browser:
            on_pending_authorization = PrintOnlyHandler()
        sso_registration_args = self._prompt_for_sso_registration_args()
        sso_token = self._sso_login(
            self._session,
            token_cache=self._sso_token_cache,
            on_pending_authorization=on_pending_authorization,
            **sso_registration_args
        )

        # Construct an SSO client to explore the accounts / roles
        client_config = Config(
            signature_version=UNSIGNED,
            region_name=sso_registration_args['sso_region'],
        )
        sso = self._session.create_client('sso', config=client_config)

        sso_account_id, sso_role_name = self._prompt_for_sso_account_and_role(
            sso, sso_token
        )
        configured_for_aws_credentials = all((sso_account_id, sso_role_name))

        # General CLI configuration
        self._prompt_for_cli_default_region()
        self._prompt_for_cli_output_format()

        profile_name = self._prompt_for_profile(sso_account_id, sso_role_name)

        self._write_new_config(profile_name)
        self._print_conclusion(configured_for_aws_credentials, profile_name)
        return 0

    def _prompt_for_sso_registration_args(self):
        sso_session = self._sso_session_prompter.prompt_for_sso_session(
            required=False)
        if sso_session is None:
            self._warn_configuring_using_legacy_format()
            return self._prompt_for_registration_args_with_legacy_format()
        else:
            self._set_sso_session_in_profile_config(sso_session)
            if sso_session in self._sso_sessions:
                return self._get_sso_registration_args_from_sso_config(
                    sso_session)
            else:
                return self._prompt_for_registration_args_for_new_sso_session(
                    sso_session=sso_session
                )

    def _prompt_for_registration_args_with_legacy_format(self):
        self._store_sso_session_prompter_answers_to_profile_config()
        self._set_sso_session_defaults_from_profile_config()
        start_url, sso_region = self._prompt_for_sso_start_url_and_sso_region()
        return {
            'start_url': start_url,
            'sso_region': sso_region
        }

    def _get_sso_registration_args_from_sso_config(self, sso_session):
        sso_config = self._get_sso_session_config(sso_session)
        return {
            'session_name': sso_session,
            'start_url': sso_config['sso_start_url'],
            'sso_region': sso_config['sso_region'],
            'registration_scopes': sso_config.get('registration_scopes')
        }

    def _prompt_for_registration_args_for_new_sso_session(self, sso_session):
        self._set_sso_session_defaults_from_profile_config()
        start_url, sso_region = self._prompt_for_sso_start_url_and_sso_region()
        scopes = self._sso_session_prompter.prompt_for_sso_registration_scopes()
        return {
            'session_name': sso_session,
            'start_url': start_url,
            'sso_region': sso_region,
            'registration_scopes': scopes,
            # We force refresh for any new SSO sessions to ensure we are not
            # using any cached tokens from any previous of attempts to
            # create/authenticate a new SSO session as part of the configure
            # sso flow.
            'force_refresh': True
        }

    def _store_sso_session_prompter_answers_to_profile_config(self):
        # Wire the SSO session prompter to set config values to the
        # dictionary used for writing to the profile section
        self._sso_session_prompter.sso_session_config = \
            self._new_profile_config_values

    def _set_sso_session_in_profile_config(self, sso_session):
        self._new_profile_config_values['sso_session'] = sso_session

    def _set_sso_session_defaults_from_profile_config(self):
        # This is to ensure the SSO session prompter pulls in existing
        # SSO configuration as part of the prompt if a profile was explicitly
        # provided that already had SSO configuration
        if 'sso_start_url' in self._profile_config:
            self._sso_session_prompter.sso_session_config['sso_start_url'] = \
                self._profile_config['sso_start_url']
        if 'sso_region' in self._profile_config:
            self._sso_session_prompter.sso_session_config['sso_region'] = \
                self._profile_config['sso_region']

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
                sso, sso_token, sso_account_id)
        except sso.exceptions.UnauthorizedException as e:
            uni_print(
                'Unable to list AWS accounts and/or roles. '
                'Skipping configuring AWS credential provider for profile.\n'
            )
        return sso_account_id, sso_role_name

    def _write_new_config(self, profile):
        if self._new_profile_config_values:
            profile_section = profile_to_section(profile)
            self._update_section(
                profile_section, self._new_profile_config_values)
        if self._sso_session_prompter.sso_session:
            self._write_sso_configuration()

    def _print_conclusion(self, configured_for_aws_credentials, profile_name):
        if configured_for_aws_credentials:
            msg = (
                '\nTo use this profile, specify the profile name using '
                '--profile, as shown:\n\n'
                'aws s3 ls --profile {}\n'
            )
        else:
            msg = 'Successfully configured SSO for profile: {}\n'
        uni_print(msg.format(profile_name))


class ConfigureSSOSessionCommand(BaseSSOConfigurationCommand):
    NAME = 'sso-session'
    SYNOPSIS = ('aws configure sso-session')
    DESCRIPTION = (
        'The ``aws configure sso-session`` command interactively prompts for '
        'the configuration values required to create a SSO session. '
        'The SSO session can then be associated to a profile to retrieve '
        'SSO access tokens and AWS credentials.\n\n'
        f'{_CMD_PROMPT_USAGE}'
        f'{_CONFIG_EXTRA_INFO}'
    )

    def _run_main(self, parsed_args, parsed_globals):
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
