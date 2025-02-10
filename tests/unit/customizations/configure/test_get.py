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
from awscli.testutils import unittest
from awscli.compat import StringIO

from awscli.customizations.configure.get import ConfigureGetCommand

from . import FakeSession


class TestConfigureGetCommand(unittest.TestCase):

    def create_command(self, session):
        stdout = StringIO()
        stderr = StringIO()
        command = ConfigureGetCommand(session, stdout, stderr)
        return stdout, stderr, command

    def test_configure_get_command(self):
        session = FakeSession({})
        session.config['region'] = 'us-west-2'
        stream, error_stream, config_get = self.create_command(session)
        config_get(args=['region'], parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), 'us-west-2')

    def test_configure_get_command_no_exist(self):
        no_vars_defined = {}
        session = FakeSession(no_vars_defined)
        stream, error_stream, config_get = self.create_command(session)
        rc = config_get(args=['region'], parsed_globals=None)
        rendered = stream.getvalue()
        # If a config value does not exist, we don't print any output.
        self.assertEqual(rendered, '')
        # And we exit with an rc of 1.
        self.assertEqual(rc, 1)

    def test_dotted_get(self):
        session = FakeSession({})
        session.full_config = {'preview': {'emr': 'true'}}
        stream, error_stream, config_get = self.create_command(session)
        config_get(args=['preview.emr'], parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), 'true')

    def test_dotted_get_with_profile(self):
        session = FakeSession({})
        session.full_config = {'profiles': {'emr-dev': {
            'emr': {'instance_profile': 'my_ip'}}}}
        session.config = {'emr': {'instance_profile': 'my_ip'}}
        stream, error_stream, config_get = self.create_command(session)
        config_get(args=['emr-dev.emr.instance_profile'], parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), 'my_ip')

    def test_get_from_profile(self):
        session = FakeSession({})
        session.full_config = {
            'profiles': {'testing': {'aws_access_key_id': 'access_key'}}}
        stream, error_stream, config_get = self.create_command(session)
        config_get = ConfigureGetCommand(session, stream)
        config_get(args=['profile.testing.aws_access_key_id'],
                   parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), 'access_key')

    def test_get_nested_attribute(self):
        session = FakeSession({})
        session.full_config = {
            'profiles': {'testing': {'s3': {'signature_version': 's3v4'}}}}
        stream, error_stream, config_get = self.create_command(session)
        config_get(args=['profile.testing.s3.signature_version'],
                   parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), 's3v4')

    def test_get_nested_attribute_from_default(self):
        session = FakeSession({})
        session.full_config = {
            'profiles': {'default': {'s3': {'signature_version': 's3v4'}}}}
        stream, error_stream, config_get = self.create_command(session)
        config_get(args=['default.s3.signature_version'],
                   parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), 's3v4')

    def test_get_nested_attribute_from_default_does_not_exist(self):
        session = FakeSession({})
        session.full_config = {'profiles': {}}
        stream, error_stream, config_get = self.create_command(session)
        config_get(args=['default.s3.signature_version'],
                   parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), '')

    def test_get_nested_attribute_from_implicit_default(self):
        session = FakeSession({})
        session.full_config = {
            'profiles': {'default': {'s3': {'signature_version': 's3v4'}}}}
        stream, error_stream, config_get = self.create_command(session)
        config_get(args=['s3.signature_version'],
                   parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), 's3v4')

    def test_get_section_returns_error(self):
        session = FakeSession({})
        session.full_config = {
            'profiles': {'default': {'s3': {'signature_version': 's3v4'}}}}
        session.config = {'s3': {'signature_version': 's3v4'}}
        stream, error_stream, config_get = self.create_command(session)
        rc = config_get(args=['s3'], parsed_globals=None)
        self.assertEqual(rc, 1)

        error_message = error_stream.getvalue()
        expected_message = (
            'varname (s3) must reference a value, not a section or '
            'sub-section.')
        self.assertEqual(error_message, expected_message)
        self.assertEqual(stream.getvalue(), '')

    def test_get_non_string_returns_error(self):
        # This should never happen, but we handle this case so we should
        # test it.
        session = FakeSession({})
        session.full_config = {
            'profiles': {'default': {'foo': object()}}}
        stream, error_stream, config_get = self.create_command(session)
        rc = config_get(args=['foo'], parsed_globals=None)
        self.assertEqual(rc, 1)
        self.assertEqual(stream.getvalue(), '')
        self.assertEqual(error_stream.getvalue(), '')
