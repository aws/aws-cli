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
import mock
from datetime import datetime, timedelta
from dateutil.tz import tzlocal

from prompt_toolkit import prompt as ptk_prompt
from prompt_toolkit.document import Document
from prompt_toolkit.validation import DummyValidator
from prompt_toolkit.validation import ValidationError

from botocore.session import Session
from botocore.stub import Stubber
from botocore.exceptions import ProfileNotFound

from awscli.testutils import unittest
from awscli.customizations.configure.sso import display_account
from awscli.customizations.configure.sso import select_menu
from awscli.customizations.configure.sso import PTKPrompt
from awscli.customizations.configure.sso import ConfigureSSOCommand
from awscli.customizations.configure.sso import StartUrlValidator
from awscli.customizations.configure.writer import ConfigFileWriter
from awscli.formatter import CLI_OUTPUT_FORMATS


class TestPTKPrompt(unittest.TestCase):
    def setUp(self):
        self.mock_prompter = mock.Mock(spec=ptk_prompt)
        self.prompter = PTKPrompt(prompter=self.mock_prompter)

    def test_returns_input(self):
        self.mock_prompter.return_value = 'new_value'
        response = self.prompter.get_value('default_value', 'Prompt Text')
        self.assertEqual(response, 'new_value')

    def test_user_hits_enter_returns_current(self):
        self.mock_prompter.return_value = ''
        response = self.prompter.get_value('default_value', 'Prompt Text')
        # We convert the empty string to the default value
        self.assertEqual(response, 'default_value')

    def assert_expected_completions(self, completions):
        # The order of the completion list can vary becuase it comes from the
        # dict's keys. Asserting that each expected completion is in the list
        _, kwargs = self.mock_prompter.call_args_list[0]
        completer = kwargs['completer']
        self.assertEqual(len(completions), len(completer.words))
        for completion in completions:
            self.assertIn(completion, completer.words)

    def assert_expected_meta_dict(self, meta_dict):
        _, kwargs = self.mock_prompter.call_args_list[0]
        self.assertEqual(kwargs['completer'].meta_dict, meta_dict)

    def assert_expected_validator(self, validator):
        _, kwargs = self.mock_prompter.call_args_list[0]
        self.assertEqual(kwargs['validator'], validator)

    def test_handles_list_completions(self):
        completions = ['a', 'b']
        self.prompter.get_value('', '', completions=completions)
        self.assert_expected_completions(completions)

    def test_handles_dict_completions(self):
        descriptions = {
            'a': 'the letter a',
            'b': 'the letter b',
        }
        expected_completions = ['a', 'b']
        self.prompter.get_value('', '', completions=descriptions)
        self.assert_expected_completions(expected_completions)
        self.assert_expected_meta_dict(descriptions)

    def test_passes_validator(self):
        validator = DummyValidator()
        self.prompter.get_value('', '', validator=validator)
        self.assert_expected_validator(validator)

    def test_strips_extra_whitespace(self):
        self.mock_prompter.return_value = '  no_whitespace \t  '
        response = self.prompter.get_value('default_value', 'Prompt Text')
        self.assertEqual(response, 'no_whitespace')


class TestStartUrlValidator(unittest.TestCase):
    def setUp(self):
        self.document = mock.Mock(spec=Document)
        self.validator = StartUrlValidator()

    def _validate_text(self, text):
        self.document.text = text
        self.validator.validate(self.document)

    def assert_text_not_allowed(self, text):
        with self.assertRaises(ValidationError):
            self._validate_text(text)

    def test_disallowed_text(self):
        not_start_urls = [
            '',
            'd-abc123',
            'foo bar baz',
        ]
        for text in not_start_urls:
            self.assert_text_not_allowed(text)

    def test_allowed_text(self):
        valid_start_urls = [
            'https://d-abc123.awsapps.com/start',
            'https://d-abc123.awsapps.com/start#',
            'https://d-abc123.awsapps.com/start/',
            'https://d-abc123.awsapps.com/start-beta',
            'https://start.url',
        ]
        for text in valid_start_urls:
            self._validate_text(text)

    def test_allows_empty_string_if_default(self):
        default = 'https://some.default'
        self.validator = StartUrlValidator(default)
        self._validate_text('')


class TestConfigureSSOCommand(unittest.TestCase):
    def setUp(self):
        self.global_args = mock.Mock()
        self._session = Session()
        self.sso_client = self._session.create_client(
            'sso',
            region_name='us-west-2',
        )
        self.sso_stub = Stubber(self.sso_client)
        self.profile = 'a-profile'
        self.scoped_config = {}
        self.full_config = {
            'profiles': {
                self.profile: self.scoped_config
            }
        }
        self.mock_session = mock.Mock(spec=Session)
        self.mock_session.get_scoped_config.return_value = self.scoped_config
        self.mock_session.full_config = self.full_config
        self.mock_session.create_client.return_value = self.sso_client
        self.mock_session.profile = self.profile
        self.config_path = '/some/path'
        self.session_config = {
            'config_file': self.config_path,
        }
        self.mock_session.get_config_variable = self.session_config.get
        self.mock_session.get_available_regions.return_value = ['us-east-1']
        self.token_cache = {}
        self.writer = mock.Mock(spec=ConfigFileWriter)
        self.prompter = mock.Mock(spec=PTKPrompt)
        self.selector = mock.Mock(spec=select_menu)
        self.configure_sso = ConfigureSSOCommand(
            self.mock_session,
            prompter=self.prompter,
            selector=self.selector,
            config_writer=self.writer,
            sso_token_cache=self.token_cache,
        )
        self.region = 'us-west-2'
        self.output = 'json'
        self.sso_region = 'us-east-1'
        self.start_url = 'https://d-92671207e4.awsapps.com/start'
        self.account_id = '0123456789'
        self.role_name = 'roleA'
        self.cached_token_key = '13f9d35043871d073ab260e020f0ffde092cb14b'
        self.expires_at = datetime.now(tzlocal()) + timedelta(hours=24)
        self.access_token = {
            'accessToken': 'access.token.string',
            'expiresAt': self.expires_at,
        }
        self.token_cache[self.cached_token_key] = self.access_token

    def _add_list_accounts_response(self, accounts):
        params = {
            'accessToken': self.access_token['accessToken'],
        }
        response = {
            'accountList': accounts,
        }
        self.sso_stub.add_response('list_accounts', response, params)

    def _add_list_account_roles_response(self, roles):
        params = {
            'accountId': self.account_id,
            'accessToken': self.access_token['accessToken'],
        }
        response = {
            'roleList': roles,
        }
        self.sso_stub.add_response('list_account_roles', response, params)

    def _add_prompt_responses(self):
        self.prompter.get_value.side_effect = [
            self.start_url,
            self.sso_region,
            self.region,
            self.output,
        ]

    def _add_simple_single_item_responses(self):
        selected_account = {
            'accountId': self.account_id,
            'emailAddress': 'account@site.com',
        }
        self._add_list_accounts_response([selected_account])
        self._add_list_account_roles_response([{'roleName': self.role_name}])

    def assert_config_updates(self, config=None):
        if config is None:
            config = {
                '__section__': 'profile %s' % self.profile,
                'sso_start_url': self.start_url,
                'sso_region': self.sso_region,
                'sso_account_id': self.account_id,
                'sso_role_name': self.role_name,
                'region': self.region,
                'output': self.output,
            }
        self.writer.update_config.assert_called_with(config, self.config_path)

    def test_basic_configure_sso_flow(self):
        self._add_prompt_responses()
        selected_account = {
            'accountId': self.account_id,
            'emailAddress': 'account@site.com',
        }
        self.selector.side_effect = [
            selected_account,
            self.role_name,
        ]
        accounts = [
            selected_account,
            {'accountId': '1234567890', 'emailAddress': 'account2@site.com'},
        ]
        self._add_list_accounts_response(accounts)
        roles = [
            {'roleName': self.role_name},
            {'roleName': 'roleB'},
        ]
        self._add_list_account_roles_response(roles)
        with self.sso_stub:
            self.configure_sso(args=[], parsed_globals=self.global_args)
        self.sso_stub.assert_no_pending_responses()
        self.assert_config_updates()

    def test_single_account_single_role_flow(self):
        self._add_prompt_responses()
        self._add_simple_single_item_responses()
        with self.sso_stub:
            self.configure_sso(args=[], parsed_globals=self.global_args)
        self.sso_stub.assert_no_pending_responses()
        self.assert_config_updates()
        # Account / Role should be auto selected if only one is returned
        self.assertEqual(self.selector.call_count, 0)

    def test_no_accounts_flow_raises_error(self):
        self.prompter.get_value.side_effect = [self.start_url, self.sso_region]
        self._add_list_accounts_response([])
        with self.assertRaises(RuntimeError):
            with self.sso_stub:
                self.configure_sso(args=[], parsed_globals=self.global_args)
        self.sso_stub.assert_no_pending_responses()

    def test_no_roles_flow_raises_error(self):
        self._add_prompt_responses()
        selected_account = {
            'accountId': self.account_id,
            'emailAddress': 'account@site.com',
        }
        self._add_list_accounts_response([selected_account])
        self._add_list_account_roles_response([])
        with self.assertRaises(RuntimeError):
            with self.sso_stub:
                self.configure_sso(args=[], parsed_globals=self.global_args)
        self.sso_stub.assert_no_pending_responses()

    def assert_default_prompt_args(self, defaults):
        calls = self.prompter.get_value.call_args_list
        self.assertEqual(len(calls), len(defaults))
        for call, default in zip(calls, defaults):
            # The default to the prompt call is the first positional param
            self.assertEqual(call[0][0], default)

    def assert_prompt_completions(self, completions):
        calls = self.prompter.get_value.call_args_list
        self.assertEqual(len(calls), len(completions))
        for call, completions in zip(calls, completions):
            _, kwargs = call
            self.assertEqual(kwargs['completions'], completions)

    def test_defaults_to_scoped_config(self):
        self.scoped_config['sso_start_url'] = 'default-url'
        self.scoped_config['sso_region'] = 'default-sso-region'
        self.scoped_config['region'] = 'default-region'
        self.scoped_config['output'] = 'default-output'
        self._add_prompt_responses()
        self._add_simple_single_item_responses()
        with self.sso_stub:
            self.configure_sso(args=[], parsed_globals=self.global_args)
        self.sso_stub.assert_no_pending_responses()
        self.assert_config_updates()
        expected_defaults = [
            'default-url',
            'default-sso-region',
            'default-region',
            'default-output',
        ]
        self.assert_default_prompt_args(expected_defaults)

    def test_handles_no_profile(self):
        expected_profile = 'profile-a'
        self.profile = None
        self.mock_session.profile = None
        self.configure_sso = ConfigureSSOCommand(
            self.mock_session,
            prompter=self.prompter,
            selector=self.selector,
            config_writer=self.writer,
            sso_token_cache=self.token_cache,
        )
        # If there is no profile, it will be prompted for as the last value
        self.prompter.get_value.side_effect = [
            self.start_url,
            self.sso_region,
            self.region,
            self.output,
            expected_profile,
        ]
        self._add_simple_single_item_responses()
        with self.sso_stub:
            self.configure_sso(args=[], parsed_globals=self.global_args)
        self.sso_stub.assert_no_pending_responses()
        self.profile = expected_profile
        self.assert_config_updates()

    def test_handles_non_existant_profile(self):
        not_found_exception = ProfileNotFound(profile=self.profile)
        self.mock_session.get_scoped_config.side_effect = not_found_exception
        self.configure_sso = ConfigureSSOCommand(
            self.mock_session,
            prompter=self.prompter,
            selector=self.selector,
            config_writer=self.writer,
            sso_token_cache=self.token_cache,
        )
        self._add_prompt_responses()
        self._add_simple_single_item_responses()
        with self.sso_stub:
            self.configure_sso(args=[], parsed_globals=self.global_args)
        self.sso_stub.assert_no_pending_responses()
        self.assert_config_updates()

    def test_cli_config_is_none_not_written(self):
        self.prompter.get_value.side_effect = [
            self.start_url,
            self.sso_region,
            # The CLI region and output format shouldn't be written
            # to the config as they are None
            None,
            None
        ]
        self._add_simple_single_item_responses()
        with self.sso_stub:
            self.configure_sso(args=[], parsed_globals=self.global_args)
        self.sso_stub.assert_no_pending_responses()
        expected_config = {
            '__section__': 'profile %s' % self.profile,
            'sso_start_url': self.start_url,
            'sso_region': self.sso_region,
            'sso_account_id': self.account_id,
            'sso_role_name': self.role_name,
        }
        self.assert_config_updates(config=expected_config)

    def test_prompts_suggest_values(self):
        self.full_config['profiles']['another_profile'] = {
            'sso_start_url': self.start_url,
        }
        self._add_prompt_responses()
        self._add_simple_single_item_responses()
        with self.sso_stub:
            self.configure_sso(args=[], parsed_globals=self.global_args)
        self.sso_stub.assert_no_pending_responses()
        expected_start_urls = [self.start_url]
        expected_sso_regions = ['us-east-1']
        expected_cli_regions = None
        expected_cli_outputs = list(CLI_OUTPUT_FORMATS.keys())
        expected_completions = [
            expected_start_urls,
            expected_sso_regions,
            expected_cli_regions,
            expected_cli_outputs,
        ]
        self.assert_prompt_completions(expected_completions)


class TestDisplayAccount(unittest.TestCase):
    def setUp(self):
        self.account_id = '1234'
        self.email_address = 'test@test.com'
        self.account_name = 'FooBar'
        self.account = {
            'accountId': self.account_id,
            'emailAddress': self.email_address,
            'accountName': self.account_name,
        }

    def test_display_account_all_fields(self):
        account_str = display_account(self.account)
        self.assertIn(self.account_name, account_str)
        self.assertIn(self.email_address, account_str)
        self.assertIn(self.account_id, account_str)

    def test_display_account_missing_email(self):
        del self.account['emailAddress']
        account_str = display_account(self.account)
        self.assertIn(self.account_name, account_str)
        self.assertNotIn(self.email_address, account_str)
        self.assertIn(self.account_id, account_str)

    def test_display_account_missing_name(self):
        del self.account['accountName']
        account_str = display_account(self.account)
        self.assertNotIn(self.account_name, account_str)
        self.assertIn(self.email_address, account_str)
        self.assertIn(self.account_id, account_str)

    def test_display_account_missing_name_and_email(self):
        del self.account['accountName']
        del self.account['emailAddress']
        account_str = display_account(self.account)
        self.assertNotIn(self.account_name, account_str)
        self.assertNotIn(self.email_address, account_str)
        self.assertIn(self.account_id, account_str)
