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
from awscli.testutils import unittest

from prompt_toolkit.keys import Keys

from tests import PromptToolkitApplicationStubber as ApplicationStubber
from awscli.customizations.wizard.app import create_wizard_app


class TestWizardApplication(unittest.TestCase):
    def setUp(self):
        self.definition = {
            'title': 'Wizard title',
            'plan': {
                'first_step': {
                    'values': {
                        'prompt1': {
                            'description': 'Description of first prompt',
                            'type': 'prompt'
                        },
                        'prompt2': {
                            'description': 'Description of second prompt',
                            'type': 'prompt'
                        },
                        'prompt3': {
                            'description': 'Description of third prompt',
                            'type': 'prompt'
                        }
                    }
                }
            }
        }
        self.app = create_wizard_app(self.definition)
        self.stubbed_app = ApplicationStubber(self.app)

    def add_app_values_assertion(self, **expected_values):
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertEqual(app.values, expected_values)
        )

    def test_can_answer_single_prompt(self):
        self.stubbed_app.add_text_to_current_buffer('val1')
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_app_values_assertion(prompt1='val1')
        self.stubbed_app.run()

    def test_can_answer_multiple_prompts(self):
        self.stubbed_app.add_text_to_current_buffer('val1')
        self.stubbed_app.add_keypress(Keys.Enter)
        self.stubbed_app.add_text_to_current_buffer('val2')
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_app_values_assertion(prompt1='val1', prompt2='val2')
        self.stubbed_app.run()

    def test_can_use_tab_to_submit_answer(self):
        self.stubbed_app.add_text_to_current_buffer('val1')
        self.stubbed_app.add_keypress(Keys.Tab)
        self.add_app_values_assertion(prompt1='val1')
        self.stubbed_app.run()

    def test_can_use_shift_tab_to_toggle_backwards_and_change_answer(self):
        self.stubbed_app.add_text_to_current_buffer('orig1')
        self.stubbed_app.add_keypress(Keys.Enter)
        self.stubbed_app.add_keypress(Keys.BackTab)
        self.stubbed_app.add_text_to_current_buffer('override1')
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_app_values_assertion(prompt1='override1', prompt2='')
        self.stubbed_app.run()


