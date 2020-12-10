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
from awscli.testutils import unittest, mock

from awscli.customizations.wizard.ui.style import get_default_style


class TestStyles(unittest.TestCase):

    @mock.patch('awscli.customizations.wizard.ui.style.is_windows')
    def test_get_styles_for_windows(self, is_windows):
        is_windows.return_value = True
        style = get_default_style()
        self.assertIn(('shadow', 'bg:#eeeeee'), style.style_rules)
        self.assertNotIn(('shadow', 'bg:#222222'), style.style_rules)

    @mock.patch('awscli.customizations.wizard.ui.style.is_windows')
    def test_get_styles_for_non_windows(self, is_windows):
        is_windows.return_value = False
        style = get_default_style()
        self.assertIn(('shadow', 'bg:#222222'), style.style_rules)
        self.assertNotIn(('shadow', 'bg:#eeeeee'), style.style_rules)
