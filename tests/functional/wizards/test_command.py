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
import os
import tempfile
import shutil

from awscli.testutils import BaseAWSCommandParamsTest, mock, cd
from awscli.testutils import BaseAWSHelpOutputTest


class TestRunWizard(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestRunWizard, self).setUp()
        self.tempdir = tempfile.mkdtemp()
        with cd(self.tempdir):
            os.mkdir('iam')
        self.parsed_responses = [{"Roles": []}]
        self.root_dir_patch = mock.patch(
            'awscli.customizations.wizard.loader.WIZARD_SPEC_DIR',
            self.tempdir
        )
        self.root_dir_patch.start()

    def tearDown(self):
        super(TestRunWizard, self).tearDown()
        shutil.rmtree(self.tempdir)
        self.root_dir_patch.stop()

    def test_can_run_wizard(self):
        wizard_path = os.path.join(self.tempdir, 'iam', 'test-wizard.yml')
        with open(wizard_path, 'w') as f:
            f.write(
                'version: "0.9"\n'
                'plan:\n'
                '  start:\n'
                '    values:\n'
                '      myprefix:\n'
                '        type: static\n'
                '        value: /foo/\n'
                'execute:\n'
                '  default:\n'
                '    - type: apicall\n'
                '      operation: iam.ListRoles\n'
                '      params:\n'
                '        PathPrefix: "{myprefix}"\n'
            )
        stdout, _, _ = self.assert_params_for_cmd(
            'iam wizard test-wizard',
            params={'PathPrefix': '/foo/'}
        )
        self.assertEqual(self.operations_called[0][0].name, 'ListRoles')

    def test_can_run_main_wizard(self):
        wizard_path = os.path.join(self.tempdir, 'iam', '_main.yml')
        with open(wizard_path, 'w') as f:
            f.write(
                'version: "0.9"\n'
                'plan:\n'
                '  start:\n'
                '    values:\n'
                '      myprefix:\n'
                '        type: static\n'
                '        value: /foo/\n'
                'execute:\n'
                '  default:\n'
                '    - type: apicall\n'
                '      operation: iam.ListRoles\n'
                '      params: {}\n'
            )
        stdout, _, _ = self.assert_params_for_cmd(
            'iam wizard',
            params={},
        )
        self.assertEqual(self.operations_called[0][0].name, 'ListRoles')


class TestWizardHelpCommand(BaseAWSHelpOutputTest):
    def test_wait_help_command(self):
        self.driver.main(['iam', 'wizard', 'help'])
        self.assert_contains('new-role')

    def test_wait_help_command(self):
        self.driver.main(['iam', 'wizard', 'new-role', 'help'])
        self.assert_contains('new-role')
