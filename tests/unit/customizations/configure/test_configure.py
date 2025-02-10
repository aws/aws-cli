# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.customizations.configure import configure, ConfigValue, NOT_SET
from awscli.customizations.configure import profile_to_section
from awscli.testutils import mock, unittest
from awscli.compat import StringIO

from . import FakeSession


class TestConfigureCommand(unittest.TestCase):

    def setUp(self):
        self.writer = mock.Mock()
        self.global_args = mock.Mock()
        self.global_args.profile = None
        self.precanned = PrecannedPrompter(value='new_value')
        self.session = FakeSession({'config_file': 'myconfigfile'})
        self.configure = configure.ConfigureCommand(self.session,
                                                    prompter=self.precanned,
                                                    config_writer=self.writer)

    def assert_credentials_file_updated_with(self, new_values):
        called_args = self.writer.update_config.call_args_list
        credentials_file_call = called_args[0]
        expected_creds_file = os.path.expanduser('~/fake_credentials_filename')
        self.assertEqual(credentials_file_call,
                         mock.call(new_values, expected_creds_file))

    def test_configure_command_sends_values_to_writer(self):
        self.configure(args=[], parsed_globals=self.global_args)
        # Credentials are always written to the shared credentials file.
        self.assert_credentials_file_updated_with(
            {'aws_access_key_id': 'new_value',
             'aws_secret_access_key': 'new_value'})

        # Non-credentials config is written to the config file.
        self.writer.update_config.assert_called_with(
            {'region': 'new_value',
             'output': 'new_value'}, 'myconfigfile')

    def test_same_values_are_not_changed(self):
        # If the user enters the same value as the current value, we don't need
        # to write anything to the config.
        self.configure = configure.ConfigureCommand(self.session,
                                                    prompter=EchoPrompter(),
                                                    config_writer=self.writer)
        self.configure(args=[], parsed_globals=self.global_args)
        self.assertFalse(self.writer.update_config.called)

    def test_none_values_are_not_changed(self):
        # If a user hits enter, this will result in a None value which means
        # don't change the existing values.  In this case, we don't need
        # to write anything out to the config.
        user_presses_enter = None
        precanned = PrecannedPrompter(value=user_presses_enter)
        self.configure = configure.ConfigureCommand(self.session,
                                                    prompter=precanned,
                                                    config_writer=self.writer)
        self.configure(args=[], parsed_globals=self.global_args)
        self.assertFalse(self.writer.update_config.called)

    def test_create_configure_cmd_session_only(self):
        self.configure = configure.ConfigureCommand(self.session)
        self.assertIsInstance(self.configure, configure.ConfigureCommand)

    def test_some_values_changed(self):
        # Test the case where the user only wants to change a single_value.
        responses = {
            "AWS Access Key ID": None,
            "AWS Secert Access Key": None,
            "Default region name": None,
            "Default output format": "NEW OUTPUT FORMAT",
        }
        prompter = KeyValuePrompter(responses)
        self.configure = configure.ConfigureCommand(self.session, prompter=prompter,
                                                    config_writer=self.writer)
        self.configure(args=[], parsed_globals=self.global_args)

        # We only need to write out the default output format.
        self.writer.update_config.assert_called_with(
            {'output': 'NEW OUTPUT FORMAT'}, 'myconfigfile')

    def test_section_name_can_be_changed_for_profiles(self):
        # If the user specifies a profile we need to write this out to
        # the [profile myname] section.
        self.session.profile = 'myname'
        self.configure(args=[], parsed_globals=self.global_args)
        # Note the __section__ key name.
        self.assert_credentials_file_updated_with(
            {'aws_access_key_id': 'new_value',
             'aws_secret_access_key': 'new_value',
             '__section__': 'myname'})
        self.writer.update_config.assert_called_with(
            {'__section__': 'profile myname',
             'region': 'new_value',
             'output': 'new_value'}, 'myconfigfile')

    def test_session_says_profile_does_not_exist(self):
        # Whenever you try to get a config value from botocore,
        # it will raise an exception complaining about ProfileNotFound.
        # We should handle this case, and write out a new profile section
        # in the config file.
        session = FakeSession({'config_file': 'myconfigfile'},
                              profile_does_not_exist=True,
                              profile='profile-does-not-exist')
        self.configure = configure.ConfigureCommand(session,
                                                    prompter=self.precanned,
                                                    config_writer=self.writer)
        self.configure(args=[], parsed_globals=self.global_args)
        self.assert_credentials_file_updated_with(
            {'aws_access_key_id': 'new_value',
             'aws_secret_access_key': 'new_value',
             '__section__': 'profile-does-not-exist'})
        self.writer.update_config.assert_called_with(
            {'__section__': 'profile profile-does-not-exist',
             'region': 'new_value',
             'output': 'new_value'}, 'myconfigfile')


class TestInteractivePrompter(unittest.TestCase):

    def setUp(self):
        self.input_patch = mock.patch('awscli.compat.raw_input')
        self.mock_raw_input = self.input_patch.start()
        self.stdout = StringIO()
        self.stdout_patch = mock.patch('sys.stdout', self.stdout)
        self.stdout_patch.start()

    def tearDown(self):
        self.input_patch.stop()
        self.stdout_patch.stop()

    def test_access_key_is_masked(self):
        self.mock_raw_input.return_value = 'foo'
        prompter = configure.InteractivePrompter()
        response = prompter.get_value(
            current_value='myaccesskey', config_name='aws_access_key_id',
            prompt_text='Access key')
        # First we should return the value from raw_input.
        self.assertEqual(response, 'foo')
        # We should also not display the entire access key.
        prompt_text = self.stdout.getvalue()
        self.assertNotIn('myaccesskey', prompt_text)
        self.assertRegex(prompt_text, r'\[\*\*\*\*.*\]')

    def test_access_key_not_masked_when_none(self):
        self.mock_raw_input.return_value = 'foo'
        prompter = configure.InteractivePrompter()
        response = prompter.get_value(
            current_value=None, config_name='aws_access_key_id',
            prompt_text='Access key')
        # First we should return the value from raw_input.
        self.assertEqual(response, 'foo')
        prompt_text = self.stdout.getvalue()
        self.assertIn('[None]', prompt_text)

    def test_secret_key_is_masked(self):
        prompter = configure.InteractivePrompter()
        prompter.get_value(
            current_value='mysupersecretkey',
            config_name='aws_secret_access_key',
            prompt_text='Secret Key')
        # We should also not display the entire secret key.
        prompt_text = self.stdout.getvalue()
        self.assertNotIn('mysupersecretkey', prompt_text)
        self.assertRegex(prompt_text, r'\[\*\*\*\*.*\]')

    def test_non_secret_keys_are_not_masked(self):
        prompter = configure.InteractivePrompter()
        prompter.get_value(
            current_value='mycurrentvalue', config_name='not_a_secret_key',
            prompt_text='Enter value')
        # We should also not display the entire secret key.
        prompt_text = self.stdout.getvalue()
        self.assertIn('mycurrentvalue', prompt_text)
        self.assertRegex(prompt_text, r'\[mycurrentvalue\]')

    def test_user_hits_enter_returns_none(self):
        # If a user hits enter, then raw_input returns the empty string.
        self.mock_raw_input.return_value = ''

        prompter = configure.InteractivePrompter()
        response = prompter.get_value(
            current_value=None, config_name='aws_access_key_id',
            prompt_text='Access key')
        # We convert the empty string to None to indicate that there
        # was no input.
        self.assertIsNone(response)

    def test_compat_input_flushes_after_each_prompt(self):
        # Clear out the default patch
        self.stdout_patch.stop()

        # Create a mock stdout to record flush calls and replace stdout_patch
        self.stdout = mock.Mock()
        self.stdout_patch = mock.patch('sys.stdout', self.stdout)
        self.stdout_patch.start()

        # Make sure flush called at least once
        prompter = configure.InteractivePrompter()
        prompter.get_value(current_value='foo', config_name='bar',
                           prompt_text='baz')
        self.assertTrue(self.stdout.flush.called)

        # Make sure flush is called after *every* prompt
        self.stdout.reset_mock()
        prompter.get_value(current_value='foo2', config_name='bar2',
                           prompt_text='baz2')
        self.assertTrue(self.stdout.flush.called)


class TestConfigValueMasking(unittest.TestCase):

    def test_config_value_is_masked(self):
        config_value = ConfigValue(
            'fake_access_key', 'config_file', 'aws_access_key_id')
        self.assertEqual(config_value.value, 'fake_access_key')
        config_value.mask_value()
        self.assertEqual(config_value.value, '****************_key')

    def test_dont_mask_unset_value(self):
        no_config = ConfigValue(NOT_SET, None, None)
        self.assertEqual(no_config.value, NOT_SET)
        no_config.mask_value()
        self.assertEqual(no_config.value, NOT_SET)


class TestProfileToSection(unittest.TestCase):

    def test_normal_profile(self):
        profile = 'my-profile'
        section = profile_to_section(profile)
        self.assertEqual('profile my-profile', section)

    def test_profile_with_spaces(self):
        profile = 'my spaced profile'
        section = profile_to_section(profile)
        self.assertEqual('profile \'my spaced profile\'', section)

    def test_profile_with_tab(self):
        profile = 'tab\ts'
        section = profile_to_section(profile)
        self.assertEqual('profile \'tab\ts\'', section)

    def test_profile_with_consecutive_spaces(self):
        profile = '    '
        section = profile_to_section(profile)
        self.assertEqual('profile \'    \'', section)


class PrecannedPrompter(object):

    def __init__(self, value):
        self._value = value

    def get_value(self, current_value, logical_name, prompt_text=''):
        return self._value


class EchoPrompter(object):

    def get_value(self, current_value, logical_name, prompt_text=''):
        return current_value


class KeyValuePrompter(object):

    def __init__(self, mapping):
        self.mapping = mapping

    def get_value(self, current_value, config_name, prompt_text=''):
        return self.mapping.get(prompt_text)
