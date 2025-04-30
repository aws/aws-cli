# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


from unittest.mock import patch

from awscli.customizations.q.uninstall import UninstallCommand
from awscli.customizations.q.utils import Q_EXTENSION_DIR
from awscli.testutils import mock


class TestUninstallCommand:
    def setup_method(self):
        self.session = mock.Mock()
        self.mock_shutil_rmtree = patch('shutil.rmtree').start()
        self.uninstall_command = UninstallCommand(self.session)

    @patch('pathlib.Path.is_file', return_value=False)
    def test_uninstall_not_installed(self, mock_is_file):
        self.uninstall_command._run_main([], None)

        # Verify Q extension was called with correct argument
        self.mock_shutil_rmtree.assert_not_called()

    @patch('pathlib.Path.is_file', return_value=True)
    def test_uninstall_removes(self, mock_is_file):
        self.uninstall_command._run_main([], None)

        # Verify Q extension was called with correct argument
        self.mock_shutil_rmtree.assert_called_once_with(
            Q_EXTENSION_DIR, ignore_errors=True
        )
