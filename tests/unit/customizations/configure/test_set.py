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
import os

from awscli.customizations.configure.set import ConfigureSetCommand
from awscli.testutils import unittest
from . import FakeSession


class TestConfigureSetCommand(unittest.TestCase):

    def setUp(self):
        self.session = FakeSession({'config_file': 'myconfigfile'})
        self.fake_credentials_filename = os.path.expanduser(
            '~/fake_credentials_filename')
        self.session.profile = None
        self.config_writer = mock.Mock()

    def test_configure_set_command(self):
        set_command = ConfigureSetCommand(
            self.session, self.config_writer)
        set_command(args=['region', 'us-west-2'], parsed_globals=None)
        self.config_writer.update_config.assert_called_with(
            {'__section__': 'default', 'region': 'us-west-2'}, 'myconfigfile')

    def test_configure_set_command_dotted(self):
        set_command = ConfigureSetCommand(
            self.session, self.config_writer)
        set_command(args=['plugins.foo', 'true'], parsed_globals=None)
        self.config_writer.update_config.assert_called_with(
            {'__section__': 'plugins', 'foo': 'true'}, 'myconfigfile')

    def test_configure_set_command_dotted_with_default_profile(self):
        self.session.variables['profile'] = 'default'
        set_command = ConfigureSetCommand(
            self.session, self.config_writer)
        set_command(
            args=['emr.instance_profile', 'my_ip_emr'], parsed_globals=None)
        self.config_writer.update_config.assert_called_with(
            {'__section__': 'default',
             'emr': {'instance_profile': 'my_ip_emr'}}, 'myconfigfile')

    def test_configure_set_handles_predefined_plugins_section(self):
        self.session.variables['profile'] = 'default'
        set_command = ConfigureSetCommand(
            self.session, self.config_writer)
        set_command(
            args=['plugins.foo', 'mypackage'], parsed_globals=None)
        self.config_writer.update_config.assert_called_with(
            {'__section__': 'plugins',
             'foo': 'mypackage'}, 'myconfigfile')

    def test_configure_set_command_dotted_with_profile(self):
        self.session.profile = 'emr-dev'
        set_command = ConfigureSetCommand(
            self.session, self.config_writer)
        set_command(
            args=['emr.instance_profile', 'my_ip_emr'], parsed_globals=None)
        self.config_writer.update_config.assert_called_with(
            {'__section__': 'profile emr-dev', 'emr':
                {'instance_profile': 'my_ip_emr'}}, 'myconfigfile')

    def test_configure_set_with_profile(self):
        self.session.profile = 'testing'
        set_command = ConfigureSetCommand(
            self.session, self.config_writer)
        set_command(args=['region', 'us-west-2'], parsed_globals=None)
        self.config_writer.update_config.assert_called_with(
            {'__section__': 'profile testing', 'region': 'us-west-2'},
            'myconfigfile')

    def test_configure_set_triple_dotted(self):
        # aws configure set default.s3.signature_version s3v4
        set_command = ConfigureSetCommand(
            self.session, self.config_writer)
        set_command(args=['default.s3.signature_version', 's3v4'],
                    parsed_globals=None)
        self.config_writer.update_config.assert_called_with(
            {'__section__': 'default', 's3': {'signature_version': 's3v4'}},
            'myconfigfile')

    def test_configure_set_with_profile_nested(self):
        # aws configure set default.s3.signature_version s3v4
        set_command = ConfigureSetCommand(
            self.session, self.config_writer)
        set_command(args=['profile.foo.s3.signature_version', 's3v4'],
                    parsed_globals=None)
        self.config_writer.update_config.assert_called_with(
            {'__section__': 'profile foo',
             's3': {'signature_version': 's3v4'}}, 'myconfigfile')

    def test_access_key_written_to_shared_credentials_file(self):
        set_command = ConfigureSetCommand(
            self.session, self.config_writer)
        set_command(args=['aws_access_key_id', 'foo'],
                    parsed_globals=None)
        self.config_writer.update_config.assert_called_with(
            {'__section__': 'default',
             'aws_access_key_id': 'foo'}, self.fake_credentials_filename)

    def test_secret_key_written_to_shared_credentials_file(self):
        set_command = ConfigureSetCommand(
            self.session, self.config_writer)
        set_command(args=['aws_secret_access_key', 'foo'],
                    parsed_globals=None)
        self.config_writer.update_config.assert_called_with(
            {'__section__': 'default',
             'aws_secret_access_key': 'foo'}, self.fake_credentials_filename)

    def test_session_token_written_to_shared_credentials_file(self):
        set_command = ConfigureSetCommand(
            self.session, self.config_writer)
        set_command(args=['aws_session_token', 'foo'],
                    parsed_globals=None)
        self.config_writer.update_config.assert_called_with(
            {'__section__': 'default',
             'aws_session_token': 'foo'}, self.fake_credentials_filename)

    def test_access_key_written_to_shared_credentials_file_profile(self):
        set_command = ConfigureSetCommand(
            self.session, self.config_writer)
        set_command(args=['profile.foo.aws_access_key_id', 'bar'],
                    parsed_globals=None)
        self.config_writer.update_config.assert_called_with(
            {'__section__': 'foo',
             'aws_access_key_id': 'bar'}, self.fake_credentials_filename)
