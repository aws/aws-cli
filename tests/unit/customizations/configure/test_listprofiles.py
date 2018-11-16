# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from . import FakeSession
from awscli.compat import six
from awscli.testutils import unittest
from awscli.customizations.configure.listprofiles import ListProfilesCommand


class TestListProfilesCommand(unittest.TestCase):
    def _create_command(self, profiles=None):
        session = FakeSession({}, available_profiles=profiles)
        stdout = six.StringIO()
        command = ListProfilesCommand(session, out_stream=stdout)
        return stdout, command

    def test_lists_profile_default(self):
        stdout, list_profiles = self._create_command()
        list_profiles(args=[], parsed_globals=None)
        self.assertEqual('default\n', stdout.getvalue())

    def test_lists_profile_multiple(self):
        profiles = [
            'default',
            'profile-foo',
            'profile-baz',
            'some profile',
        ]
        stdout, list_profiles = self._create_command(profiles=profiles)
        list_profiles(args=[], parsed_globals=None)
        self.assertEqual('\n'.join(profiles) + '\n', stdout.getvalue())
