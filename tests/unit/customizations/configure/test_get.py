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

from awscli.customizations.configure.get import ConfigureGetCommand
from awscli.compat import six

from . import FakeSession


class TestConfigureGetCommand(unittest.TestCase):

    def test_configure_get_command(self):
        session = FakeSession({})
        session.config['region'] = 'us-west-2'
        stream = six.StringIO()
        config_get = ConfigureGetCommand(session, stream)
        config_get(args=['region'], parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), 'us-west-2')

    def test_configure_get_command_no_exist(self):
        no_vars_defined = {}
        session = FakeSession(no_vars_defined)
        stream = six.StringIO()
        config_get = ConfigureGetCommand(session, stream)
        rc = config_get(args=['region'], parsed_globals=None)
        rendered = stream.getvalue()
        # If a config value does not exist, we don't print any output.
        self.assertEqual(rendered, '')
        # And we exit with an rc of 1.
        self.assertEqual(rc, 1)

    def test_dotted_get(self):
        session = FakeSession({})
        session.full_config = {'preview': {'emr': 'true'}}
        stream = six.StringIO()
        config_get = ConfigureGetCommand(session, stream)
        config_get(args=['preview.emr'], parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), 'true')

    def test_dotted_get_with_profile(self):
        session = FakeSession({})
        session.full_config = {'profiles': {'emr-dev': {
            'emr': {'instance_profile': 'my_ip'}}}}
        session.config = {'emr': {'instance_profile': 'my_ip'}}
        stream = six.StringIO()
        config_get = ConfigureGetCommand(session, stream)
        config_get(args=['emr-dev.emr.instance_profile'], parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), 'my_ip')

    def test_get_from_profile(self):
        session = FakeSession({})
        session.full_config = {'profiles': {'testing': {'aws_access_key_id': 'access_key'}}}
        stream = six.StringIO()
        config_get = ConfigureGetCommand(session, stream)
        config_get(args=['profile.testing.aws_access_key_id'],
                   parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), 'access_key')

    def test_get_nested_attribute(self):
        session = FakeSession({})
        session.full_config = {
            'profiles': {'testing': {'s3': {'signature_version': 's3v4'}}}}
        stream = six.StringIO()
        config_get = ConfigureGetCommand(session, stream)
        config_get(args=['profile.testing.s3.signature_version'],
                   parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), 's3v4')

    def test_get_nested_attribute_from_default(self):
        session = FakeSession({})
        session.full_config = {
            'profiles': {'default': {'s3': {'signature_version': 's3v4'}}}}
        stream = six.StringIO()
        config_get = ConfigureGetCommand(session, stream)
        config_get(args=['default.s3.signature_version'],
                   parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), 's3v4')

    def test_get_nested_attribute_from_default_does_not_exist(self):
        session = FakeSession({})
        session.full_config = {'profiles': {}}
        stream = six.StringIO()
        config_get = ConfigureGetCommand(session, stream)
        config_get(args=['default.s3.signature_version'],
                   parsed_globals=None)
        rendered = stream.getvalue()
        self.assertEqual(rendered.strip(), '')