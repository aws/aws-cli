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
import sys
import os
import tempfile
import shutil
from tests import unittest

import mock
from six import StringIO
from botocore.exceptions import ProfileNotFound

from awscli.customizations import configure



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


class FakeSession(object):
    def __init__(self, all_variables, profile_does_not_exist=False,
                 config_file_vars=None, environment_vars=None,
                 credentials=None):
        self.variables = all_variables
        self.profile_does_not_exist = profile_does_not_exist
        self.config = {}
        if config_file_vars is None:
            config_file_vars = {}
        self.config_file_vars = config_file_vars
        if environment_vars is None:
            environment_vars = {}
        self.environment_vars = environment_vars
        self._credentials = credentials
        self.profile = None

    def get_credentials(self):
        return self._credentials

    def get_config(self):
        if self.profile_does_not_exist:
            raise ProfileNotFound(profile='foo')
        return self.config

    def get_config_variable(self, name, methods=None):
        if self.profile_does_not_exist and not name == 'config_file':
            raise ProfileNotFound(profile='foo')
        if methods is not None:
            if 'env' in methods:
                return self.environment_vars.get(name)
            elif 'config' in methods:
                return self.config_file_vars.get(name)
        else:
            return self.variables.get(name)

    def emit(self, event_name, **kwargs):
        pass


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

    def test_configure_command_sends_values_to_writer(self):
        self.configure(args=[], parsed_globals=self.global_args)
        self.writer.update_config.assert_called_with(
            {'aws_access_key_id': 'new_value',
             'aws_secret_access_key': 'new_value',
             'region': 'new_value',
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
        # If the user specifies "--profile myname" we need to write
        # this out to the [profile myname] section.
        self.global_args.profile = 'myname'
        self.configure(args=[], parsed_globals=self.global_args)
        # Note the __section__ key name.
        self.writer.update_config.assert_called_with(
            {'__section__': 'profile myname',
             'aws_access_key_id': 'new_value',
             'aws_secret_access_key': 'new_value',
             'region': 'new_value',
             'output': 'new_value'}, 'myconfigfile')

    def test_session_says_profile_does_not_exist(self):
        # Whenever you try to get a config value from botocore,
        # it will raise an exception complaining about ProfileNotFound.
        # We should handle this case, and write out a new profile section
        # in the config file.
        session = FakeSession({'config_file': 'myconfigfile'},
                              profile_does_not_exist=True)
        self.configure = configure.ConfigureCommand(session,
                                                    prompter=self.precanned,
                                                    config_writer=self.writer)
        self.global_args.profile = 'profile-does-not-exist'
        self.configure(args=[], parsed_globals=self.global_args)
        self.writer.update_config.assert_called_with(
            {'__section__': 'profile profile-does-not-exist',
             'aws_access_key_id': 'new_value',
             'aws_secret_access_key': 'new_value',
             'region': 'new_value',
             'output': 'new_value'}, 'myconfigfile')


class TestInteractivePrompter(unittest.TestCase):
    @mock.patch('awscli.customizations.configure.raw_input')
    def test_access_key_is_masked(self, mock_raw_input):
        mock_raw_input.return_value = 'foo'
        prompter = configure.InteractivePrompter()
        response = prompter.get_value(
            current_value='myaccesskey', config_name='aws_access_key_id',
            prompt_text='Access key')
        # First we should return the value from raw_input.
        self.assertEqual(response, 'foo')
        # We should also not display the entire access key.
        prompt_text = mock_raw_input.call_args[0][0]
        self.assertNotIn('myaccesskey', prompt_text)
        self.assertRegexpMatches(prompt_text, r'\[\*\*\*\*.*\]')

    @mock.patch('awscli.customizations.configure.raw_input')
    def test_access_key_not_masked_when_none(self, mock_raw_input):
        mock_raw_input.return_value = 'foo'
        prompter = configure.InteractivePrompter()
        response = prompter.get_value(
            current_value=None, config_name='aws_access_key_id',
            prompt_text='Access key')
        # First we should return the value from raw_input.
        self.assertEqual(response, 'foo')
        prompt_text = mock_raw_input.call_args[0][0]
        self.assertIn('[None]', prompt_text)

    @mock.patch('awscli.customizations.configure.raw_input')
    def test_secret_key_is_masked(self, mock_raw_input):
        prompter = configure.InteractivePrompter()
        prompter.get_value(
            current_value='mysupersecretkey',
            config_name='aws_secret_access_key',
            prompt_text='Secret Key')
        # We should also not display the entire secret key.
        prompt_text = mock_raw_input.call_args[0][0]
        self.assertNotIn('mysupersecretkey', prompt_text)
        self.assertRegexpMatches(prompt_text, r'\[\*\*\*\*.*\]')

    @mock.patch('awscli.customizations.configure.raw_input')
    def test_non_secret_keys_are_not_masked(self, mock_raw_input):
        prompter = configure.InteractivePrompter()
        prompter.get_value(
            current_value='mycurrentvalue', config_name='not_a_secret_key',
            prompt_text='Enter value')
        # We should also not display the entire secret key.
        prompt_text = mock_raw_input.call_args[0][0]
        self.assertIn('mycurrentvalue', prompt_text)
        self.assertRegexpMatches(prompt_text, r'\[mycurrentvalue\]')


class TestConfigFileWriter(unittest.TestCase):
    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.config_filename = os.path.join(self.dirname, 'config')
        self.writer = configure.ConfigFileWriter()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def assert_update_config(self, original_config_contents, updated_data,
                             updated_config_contents):
        # Given the original_config, when it's updated with update_data,
        # it should produce updated_config_contents.
        with open(self.config_filename, 'w') as f:
            f.write(original_config_contents)
        self.writer.update_config(updated_data, self.config_filename)
        with open(self.config_filename, 'r') as f:
            new_contents = f.read()
        if new_contents != updated_config_contents:
            self.fail("Config file contents do not match.\n"
                      "Expected contents:\n"
                      "%s\n\n"
                      "Actual Contents:\n"
                      "%s\n" % (updated_config_contents, new_contents))

    def test_update_single_existing_value(self):
        original = '[default]\nfoo = 1\nbar = 1'
        updated = '[default]\nfoo = newvalue\nbar = 1'
        self.assert_update_config(
            original, {'foo': 'newvalue'}, updated)

    def test_update_single_existing_value_no_spaces(self):
        original = '[default]\nfoo=1\nbar=1'
        updated = '[default]\nfoo = newvalue\nbar=1'
        self.assert_update_config(
            original, {'foo': 'newvalue'}, updated)

    def test_update_single_new_values(self):
        expected = '[default]\nfoo = 1\nbar = 2\nbaz = newvalue\n'
        self.assert_update_config(
            '[default]\nfoo = 1\nbar = 2',
            {'baz': 'newvalue'}, expected)

    def test_handles_no_spaces(self):
        expected = '[default]\nfoo=1\nbar=2\nbaz = newvalue\n'
        self.assert_update_config(
            '[default]\nfoo=1\nbar=2',
            {'baz': 'newvalue'}, expected)

    def test_insert_values_in_middle_section(self):
        original_contents = (
            '[a]\n'
            'foo = bar\n'
            'baz = bar\n'
            '\n'
            '[b]\n'
            '\n'
            'foo = bar\n'
            '[c]\n'
            'foo = bar\n'
            'baz = bar\n'
        )
        expected_contents = (
            '[a]\n'
            'foo = bar\n'
            'baz = bar\n'
            '\n'
            '[b]\n'
            '\n'
            'foo = newvalue\n'
            '[c]\n'
            'foo = bar\n'
            'baz = bar\n'
        )
        self.assert_update_config(
            original_contents,
            {'foo': 'newvalue', '__section__': 'b'},
            expected_contents)

    def test_insert_new_value_in_middle_section(self):
        original_contents = (
            '[a]\n'
            'foo = bar\n'
            '\n'
            '[b]\n'
            '\n'
            'foo = bar\n'
            '\n'
            '[c]\n'
            'foo = bar\n'
        )
        expected_contents = (
            '[a]\n'
            'foo = bar\n'
            '\n'
            '[b]\n'
            '\n'
            'foo = bar\n'
            'newvalue = newvalue\n'
            '\n'
            '[c]\n'
            'foo = bar\n'
        )
        self.assert_update_config(
            original_contents,
            {'newvalue': 'newvalue', '__section__': 'b'},
            expected_contents)

    def test_new_config_file(self):
        self.assert_update_config(
            '\n',
            {'foo': 'value'},
            '\n[default]\nfoo = value\n')

    def test_section_does_not_exist(self):
        original_contents = (
            '[notdefault]\n'
            'foo = bar\n'
            'baz = bar\n'
            '\n'
            '\n'
            '\n'
            '[other "section"]\n'
            '\n'
            'foo = bar\n'
        )
        appended_contents = (
            '[default]\n'
            'foo = value\n'
        )
        self.assert_update_config(
            original_contents,
            {'foo': 'value'},
            original_contents + appended_contents)

    def test_config_file_does_not_exist(self):
        self.writer.update_config({'foo': 'value'}, self.config_filename)
        with open(self.config_filename, 'r') as f:
            new_contents = f.read()
        self.assertEqual(new_contents, '[default]\nfoo = value\n')

    @unittest.skipIf(sys.platform.lower().startswith('win'),
                     "Test not valid on windows.")
    def test_permissions_on_new_file(self):
        self.writer.update_config({'foo': 'value'}, self.config_filename)
        with open(self.config_filename, 'r') as f:
            f.read()
        self.assertEqual(os.stat(self.config_filename).st_mode & 0xFFF, 0o600)

    def test_update_config_with_comments(self):
        original = (
            '[default]\n'
            '#foo = 1\n'
            'bar = 1\n'
        )
        self.assert_update_config(
            original, {'foo': 'newvalue'},
            '[default]\n'
            '#foo = 1\n'
            'bar = 1\n'
            'foo = newvalue\n'
        )

    def test_spaces_around_key_names(self):
        original = (
            '[default]\n'
            'foo = 1\n'
            'bar = 1\n'
        )
        self.assert_update_config(
            original, {'foo': 'newvalue'},
            '[default]\n'
            'foo = newvalue\n'
            'bar = 1\n'
        )

    def test_unquoted_profile_name(self):
        original = (
            '[profile foobar]\n'
            'foo = 1\n'
            'bar = 1\n'
        )
        self.assert_update_config(
            original, {'foo': 'newvalue', '__section__': 'profile foobar'},
            '[profile foobar]\n'
            'foo = newvalue\n'
            'bar = 1\n'
        )

    def test_double_quoted_profile_name(self):
        original = (
            '[profile "foobar"]\n'
            'foo = 1\n'
            'bar = 1\n'
        )
        self.assert_update_config(
            original, {'foo': 'newvalue', '__section__': 'profile foobar'},
            '[profile "foobar"]\n'
            'foo = newvalue\n'
            'bar = 1\n'
        )

    def test_profile_with_multiple_spaces(self):
        original = (
            '[profile "two  spaces"]\n'
            'foo = 1\n'
            'bar = 1\n'
        )
        self.assert_update_config(
            original, {'foo': 'newvalue', '__section__': 'profile two  spaces'},
            '[profile "two  spaces"]\n'
            'foo = newvalue\n'
            'bar = 1\n'
        )


class TestConfigureListCommand(unittest.TestCase):

    def test_configure_list_command_nothing_set(self):
        # Test the case where the user only wants to change a single_value.
        session = FakeSession(all_variables={'config_file': '/config/location'})
        stream = StringIO()
        self.configure_list = configure.ConfigureListCommand(session, stream)
        self.configure_list(args=[], parsed_globals=None)
        rendered = stream.getvalue()
        self.assertRegexpMatches(rendered, 'profile\s+<not set>')
        self.assertRegexpMatches(rendered, 'access_key\s+<not set>')
        self.assertRegexpMatches(rendered, 'secret_key\s+<not set>')
        self.assertRegexpMatches(rendered, 'region\s+<not set>')

    def test_configure_from_env(self):
        env_vars = {
            'profile': 'myprofilename'
        }
        session = FakeSession(
            all_variables={'config_file': '/config/location'},
            environment_vars=env_vars)
        session.session_var_map = {'profile': (None, "PROFILE_ENV_VAR")}
        stream = StringIO()
        self.configure_list = configure.ConfigureListCommand(session, stream)
        self.configure_list(args=[], parsed_globals=None)
        rendered = stream.getvalue()
        self.assertRegexpMatches(
            rendered, 'profile\s+myprofilename\s+env\s+PROFILE_ENV_VAR')

    def test_configure_from_config_file(self):
        config_file_vars = {
            'region': 'us-west-2'
        }
        session = FakeSession(
            all_variables={'config_file': '/config/location'},
            config_file_vars=config_file_vars)
        session.session_var_map = {'region': ('region', "AWS_REGION")}
        stream = StringIO()
        self.configure_list = configure.ConfigureListCommand(session, stream)
        self.configure_list(args=[], parsed_globals=None)
        rendered = stream.getvalue()
        self.assertRegexpMatches(
            rendered, 'region\s+us-west-2\s+config_file\s+/config/location')

    def test_configure_from_multiple_sources(self):
        # Here the profile is from an env var, the
        # region is from the config file, and the credentials
        # are from an iam-role.
        env_vars = {
            'profile': 'myprofilename'
        }
        config_file_vars = {
            'region': 'us-west-2'
        }
        credentials = mock.Mock()
        credentials.access_key = 'access_key'
        credentials.secret_key = 'secret_key'
        credentials.method = 'iam-role'
        session = FakeSession(
            all_variables={'config_file': '/config/location'},
            environment_vars=env_vars,
            config_file_vars=config_file_vars,
            credentials=credentials)
        session.session_var_map = {
            'region': ('region', 'AWS_REGION'),
            'profile': ('profile', 'AWS_DEFAULT_PROFILE')}
        stream = StringIO()
        self.configure_list = configure.ConfigureListCommand(session, stream)
        self.configure_list(args=[], parsed_globals=None)
        rendered = stream.getvalue()
        # The profile came from an env var.
        self.assertRegexpMatches(
            rendered, 'profile\s+myprofilename\s+env\s+AWS_DEFAULT_PROFILE')
        # The region came from the config file.
        self.assertRegexpMatches(
            rendered, 'region\s+us-west-2\s+config_file\s+/config/location')
        # The credentials came from an IAM role.  Note how we're
        # also checking that the access_key/secret_key are masked
        # with '*' chars except for the last 4 chars.
        self.assertRegexpMatches(
            rendered, r'access_key\s+\*+_key\s+iam-role')
        self.assertRegexpMatches(
            rendered, r'secret_key\s+\*+_key\s+iam-role')


class TestConfigureGetSetCommand(unittest.TestCase):

    def test_configure_get_command(self):
        session = FakeSession({})
        session.config['region'] = 'us-west-2'
        stream = StringIO()
        config_get = configure.ConfigureGetCommand(session, stream)
        config_get(args=['region'], parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), 'us-west-2')

    def test_configure_get_command_no_exist(self):
        no_vars_defined = {}
        session = FakeSession(no_vars_defined)
        stream = StringIO()
        config_get = configure.ConfigureGetCommand(session, stream)
        rc = config_get(args=['region'], parsed_globals=None)
        rendered = stream.getvalue()
        # If a config value does not exist, we don't print any output.
        self.assertEqual(rendered, '')
        # And we exit with an rc of 1.
        self.assertEqual(rc, 1)

    def test_dotted_get(self):
        session = FakeSession({})
        session.full_config = {'preview': {'emr': 'true'}}
        stream = StringIO()
        config_get = configure.ConfigureGetCommand(session, stream)
        config_get(args=['preview.emr'], parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), 'true')

    def test_get_from_profile(self):
        session = FakeSession({})
        session.config = {'aws_access_key_id': 'access_key'}
        session.profile = None
        stream = StringIO()
        config_get = configure.ConfigureGetCommand(session, stream)
        config_get(args=['profile.testing.aws_access_key_id'],
                   parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), 'access_key')
        self.assertEqual(session.profile, 'testing')


class TestConfigureSetCommand(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession({'config_file': 'myconfigfile'})
        self.session.profile = None
        self.config_writer = mock.Mock()

    def test_configure_set_command(self):
        set_command = configure.ConfigureSetCommand(self.session, self.config_writer)
        set_command(args=['region', 'us-west-2'], parsed_globals=None)
        self.config_writer.update_config.assert_called_with(
            {'__section__': 'default', 'region': 'us-west-2'}, 'myconfigfile')

    def test_configure_set_command_dotted(self):
        set_command = configure.ConfigureSetCommand(self.session, self.config_writer)
        set_command(args=['preview.emr', 'true'], parsed_globals=None)
        self.config_writer.update_config.assert_called_with(
            {'__section__': 'preview', 'emr': 'true'}, 'myconfigfile')

    def test_configure_set_with_profile(self):
        self.session.profile = 'testing'
        set_command = configure.ConfigureSetCommand(self.session, self.config_writer)
        set_command(args=['region', 'us-west-2'], parsed_globals=None)
        self.config_writer.update_config.assert_called_with(
            {'__section__': 'profile testing', 'region': 'us-west-2'}, 'myconfigfile')
