# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore.session import Session

from awscli.customizations.exceptions import ParamValidationError
from awscli.customizations.wizard.commands import TopLevelWizardCommand
from awscli.customizations.wizard.core import Runner
from awscli.customizations.wizard.loader import WizardLoader
from awscli.customizations.wizard.app import WizardAppRunner
from awscli.testutils import mock, unittest


class TestWizardCommand(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock(spec=Session)
        self.session.emit_first_non_none_response.return_value = None
        self.loader = mock.Mock(spec=WizardLoader)
        self.loader.list_available_wizards.return_value = ['mywizard']
        self.wizard_v2_runner = mock.Mock(spec=WizardAppRunner)
        self.wizard_v1_runner = mock.Mock(spec=Runner)
        self.runner = {
            '0.1': self.wizard_v1_runner,
            '0.2': self.wizard_v2_runner
        }

    def test_will_delegate_v1_definition_to_v1_runner(self):
        loaded = {
            'version': '0.1'
        }
        self.loader.load_wizard.return_value = loaded
        cmd = TopLevelWizardCommand(
            self.session, loader=self.loader,
            parent_command='', runner=self.runner
        )
        cmd(['mywizard'], parsed_globals=None)
        self.wizard_v1_runner.run.assert_called_with(loaded)

    def test_will_delegate_v2_definition_to_v2_runner(self):
        loaded = {
            'version': '0.2'
        }
        self.loader.load_wizard.return_value = loaded
        cmd = TopLevelWizardCommand(
            self.session, loader=self.loader,
            parent_command='', runner=self.runner
        )
        cmd(['mywizard'], parsed_globals=None)
        self.wizard_v2_runner.run.assert_called_with(loaded)

    def test_will_raise_exception_for_unsupported_version(self):
        loaded = {
            'version': '100'
        }
        self.loader.load_wizard.return_value = loaded
        cmd = TopLevelWizardCommand(
            self.session, loader=self.loader,
            parent_command='', runner=self.runner
        )
        with self.assertRaises(ParamValidationError) as e:
            cmd(['mywizard'], parsed_globals=None)
        self.assertIn('file has unsupported version', str(e.exception))
