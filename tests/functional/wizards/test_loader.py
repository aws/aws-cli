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
from awscli.testutils import unittest
from awscli.customizations.wizard import loader


class TestLoader(unittest.TestCase):
    def setUp(self):
        self.loader = loader.WizardLoader()

    def test_can_list_commands_with_wizards(self):
        # This list is going to change over time so we'll only pick a few
        # commands as a sanity check.
        commands = self.loader.list_commands_with_wizards()
        self.assertIn('configure', commands)
        self.assertIn('iam', commands)

    def test_can_list_wizards_for_service(self):
        wizard_names = self.loader.list_available_wizards('iam')
        self.assertIn('new-role', wizard_names)

    def test_can_load_wizard_file(self):
        loaded = self.loader.load_wizard('iam', 'new-role')
        self.assertIn('version', loaded)

    def test_exception_raised_when_wizard_does_not_exists(self):
        with self.assertRaises(loader.WizardNotExistError):
            self.loader.load_wizard('iam', 'wizard-foo-does-not-exist')

    def test_wizard_exists(self):
        self.assertTrue(self.loader.wizard_exists('iam', 'new-role'))
