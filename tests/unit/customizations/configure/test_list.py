# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from argparse import Namespace

from awscli.testutils import unittest
from awscli.compat import six
from awscli.customizations.configure.list import ConfigureListCommand

from . import FakeSession


class TestConfigureListCommand(unittest.TestCase):

    def test_configure_list_command_nothing_set(self):
        # Test the case where the user only wants to change a single_value.
        session = FakeSession(
            all_variables={'config_file': '/config/location'})
        session.full_config = {
            'profiles': {'default': {'region': 'AWS_REGION'}}}
        stream = six.StringIO()
        self.configure_list = ConfigureListCommand(session, stream)
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
        session.full_config = {
            'profiles': {'default': {'region': 'AWS_REGION'}}}
        stream = six.StringIO()
        self.configure_list = ConfigureListCommand(session, stream)
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
        session.full_config = {
            'profiles': {'default': {'region': 'AWS_REGION'}}}
        stream = six.StringIO()
        self.configure_list = ConfigureListCommand(session, stream)
        self.configure_list(args=[], parsed_globals=None)
        rendered = stream.getvalue()
        self.assertRegexpMatches(
            rendered, 'region\s+us-west-2\s+config-file\s+/config/location')

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
        session.full_config = {
            'profiles': {'default': {'region': 'AWS_REGION'}}}
        stream = six.StringIO()
        self.configure_list = ConfigureListCommand(session, stream)
        self.configure_list(args=[], parsed_globals=None)
        rendered = stream.getvalue()
        # The profile came from an env var.
        self.assertRegexpMatches(
            rendered, 'profile\s+myprofilename\s+env\s+AWS_DEFAULT_PROFILE')
        # The region came from the config file.
        self.assertRegexpMatches(
            rendered, 'region\s+us-west-2\s+config-file\s+/config/location')
        # The credentials came from an IAM role.  Note how we're
        # also checking that the access_key/secret_key are masked
        # with '*' chars except for the last 4 chars.
        self.assertRegexpMatches(
            rendered, r'access_key\s+\*+_key\s+iam-role')
        self.assertRegexpMatches(
            rendered, r'secret_key\s+\*+_key\s+iam-role')

    def test_configure_from_args(self):
        parsed_globals = Namespace(profile='foo')
        env_vars = {
            'profile': 'myprofilename'
        }
        session = FakeSession(
            all_variables={'config_file': '/config/location'},
            profile='foo', environment_vars=env_vars)
        session.session_var_map = {'profile': (None, ['AWS_PROFILE'])}
        session.full_config = {
            'profiles': {'foo': {'region': 'AWS_REGION'}}}
        stream = six.StringIO()
        self.configure_list = ConfigureListCommand(session, stream)
        self.configure_list(args=[], parsed_globals=parsed_globals)
        rendered = stream.getvalue()
        self.assertRegexpMatches(
            rendered, 'profile\s+foo\s+manual\s+--profile')
