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
import os
import logging

from botocore import UNSIGNED
from botocore.config import Config
from botocore.configprovider import ConstantProvider
from botocore.exceptions import ProfileNotFound
from botocore.utils import is_valid_endpoint_url

from prompt_toolkit import prompt as ptk_prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.validation import Validator
from prompt_toolkit.validation import ValidationError

from awscli.customizations.utils import uni_print
from awscli.customizations.commands import BasicCommand
from awscli.customizations.configure import profile_to_section
from awscli.customizations.configure.writer import ConfigFileWriter
from awscli.customizations.wizard.selectmenu import select_menu
from awscli.customizations.sso.utils import do_sso_login
from awscli.formatter import CLI_OUTPUT_FORMATS


logger = logging.getLogger(__name__)


class StartUrlValidator(Validator):
    def __init__(self, default=None):
        super(StartUrlValidator, self).__init__()
        self._default = default

    def validate(self, document):
        # If there's a default, allow an empty prompt
        if not document.text and self._default:
            return
        if not is_valid_endpoint_url(document.text):
            index = len(document.text)
            raise ValidationError(index, 'Not a valid Start URL')


class PTKPrompt(object):
    def __init__(self, prompter=None):
        if prompter is None:
            prompter = ptk_prompt
        self._prompter = prompter

    def _create_completer(self, completions):
        if completions is None:
            completions = []
        if isinstance(completions, dict):
            meta_dict = completions
            completions = list(meta_dict.keys())
            completer = WordCompleter(
                completions,
                sentence=True,
                meta_dict=meta_dict,
            )
        else:
            completer = WordCompleter(completions, sentence=True)
        return completer

    def get_value(self, current_value, prompt_text='',
                  completions=None, validator=None):
        completer = self._create_completer(completions)
        prompt_string = u'{} [{}]: '.format(prompt_text, current_value)
        response = self._prompter(
            prompt_string,
            validator=validator,
            validate_while_typing=False,
            completer=completer,
            complete_while_typing=True,
        )
        # Strip any extra white space
        response = response.strip()
        if not response:
            # If the user hits enter, we return the current/default value
            response = current_value
        return response


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


class ConfigureSSOCommand(BasicCommand):
    NAME = 'sso'
    SYNOPSIS = ('aws configure sso [--profile profile-name]')
    DESCRIPTION = (
        'The ``aws configure sso`` command interactively prompts for the '
        'configuration values required to create a profile that sources '
        'temporary AWS credentials from AWS Single Sign-On. To keep an '
        'existing value, hit enter when prompted for the value.  When  you  '
        'are prompted for information, the current value will be displayed in '
        '[brackets].  If the config item has no value, it is displayed as '
        '[None]. When providing the ``--profile`` parameter the named profile '
        'will be created or updated. When a profile is not explicitly set '
        'the profile name will be prompted for.'
        '\n\nNote: The configuration is saved in the shared configuration '
        'file. By default, ``~/.aws/config``.'
    )
    # TODO: Add CLI parameters to skip prompted values, --start-url, etc.

    def __init__(self, session, prompter=None, selector=None,
                 config_writer=None, sso_token_cache=None):
        super(ConfigureSSOCommand, self).__init__(session)
        if prompter is None:
            prompter = PTKPrompt()
        self._prompter = prompter
        if selector is None:
            selector = select_menu
        self._selector = selector
        if config_writer is None:
            config_writer = ConfigFileWriter()
        self._config_writer = config_writer
        self._sso_token_cache = sso_token_cache

        self._new_values = {}
        self._original_profile_name = self._session.profile
        try:
            self._config = self._session.get_scoped_config()
        except ProfileNotFound:
            self._config = {}

    def _prompt_for(self, config_name, text,
                    completions=None, validator_cls=None):
        current_value = self._config.get(config_name)
        if validator_cls is None:
            validator = None
        else:
            validator = validator_cls(current_value)
        new_value = self._prompter.get_value(
            current_value, text,
            completions=completions,
            validator=validator,
        )
        if new_value:
            self._new_values[config_name] = new_value
        return new_value

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
        selected_account = self._selector(accounts, display_account)
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
        self._new_values['sso_account_id'] = sso_account_id
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
        self._new_values['sso_role_name'] = sso_role_name
        return sso_role_name

    def _prompt_for_profile(self, sso_account_id, sso_role_name):
        if self._original_profile_name:
            profile_name = self._original_profile_name
        else:
            default_profile = '{}-{}'.format(sso_role_name, sso_account_id)
            text = 'CLI profile name'
            profile_name = self._prompter.get_value(default_profile, text)
        return profile_name

    def _get_potential_start_urls(self):
        profiles = self._session.full_config.get('profiles', [])
        potential_start_urls = set()
        for profile, config in profiles.items():
            if 'sso_start_url' in config:
                start_url = config['sso_start_url']
                potential_start_urls.add(start_url)
        return list(potential_start_urls)

    def _prompt_for_start_url(self):
        potential_start_urls = self._get_potential_start_urls()
        start_url = self._prompt_for(
            'sso_start_url', 'SSO start URL',
            completions=potential_start_urls,
            validator_cls=StartUrlValidator,
        )
        return start_url

    def _get_potential_sso_regions(self):
        return self._session.get_available_regions('sso-oidc')

    def _prompt_for_sso_region(self):
        potential_sso_regions = self._get_potential_sso_regions()
        sso_region = self._prompt_for(
            'sso_region', 'SSO Region',
            completions=potential_sso_regions,
        )
        return sso_region

    def _prompt_for_cli_default_region(self):
        # TODO: figure out a way to get a list of reasonable client regions
        return self._prompt_for('region', 'CLI default client Region')

    def _prompt_for_cli_output_format(self):
        return self._prompt_for(
            'output', 'CLI default output format',
            completions=list(CLI_OUTPUT_FORMATS.keys()),
        )

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
        start_url = self._prompt_for_start_url()
        sso_region = self._prompt_for_sso_region()
        sso_token = do_sso_login(
            self._session,
            sso_region,
            start_url,
            token_cache=self._sso_token_cache,
        )

        # Construct an SSO client to explore the accounts / roles
        client_config = Config(
            signature_version=UNSIGNED,
            region_name=sso_region,
        )
        sso = self._session.create_client('sso', config=client_config)

        sso_account_id = self._prompt_for_account(sso, sso_token)
        sso_role_name = self._prompt_for_role(sso, sso_token, sso_account_id)

        # General CLI configuration
        self._prompt_for_cli_default_region()
        self._prompt_for_cli_output_format()

        profile_name = self._prompt_for_profile(sso_account_id, sso_role_name)

        usage_msg = (
            '\nTo use this profile, specify the profile name using '
            '--profile, as shown:\n\n'
            'aws s3 ls --profile {}\n'
        )
        uni_print(usage_msg.format(profile_name))

        self._write_new_config(profile_name)
        return 0

    def _write_new_config(self, profile):
        config_path = self._session.get_config_variable('config_file')
        config_path = os.path.expanduser(config_path)
        if self._new_values:
            section = profile_to_section(profile)
            self._new_values['__section__'] = section
            self._config_writer.update_config(self._new_values, config_path)
