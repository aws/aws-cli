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
from botocore.session import Session

from awscli.customizations.wizard.devcommands import WizardDev
from awscli.customizations.wizard.devcommands import WizardDevRunner
from awscli.testutils import mock, unittest


class TestWizardDevCommand(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock(spec=Session)
        self.session.emit_first_non_none_response.return_value = None
        self.dev_runner = mock.Mock(spec=WizardDevRunner)

    def test_will_delegate_to_runner(self):
        cmd = WizardDev(self.session, dev_runner=self.dev_runner)
        cmd(['--run-wizard', 'mywizard.yml'], parsed_globals=None)
        self.dev_runner.run_wizard.assert_called_with('mywizard.yml')
