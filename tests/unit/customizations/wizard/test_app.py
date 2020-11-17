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
from awscli.customizations.wizard.app import WizardTraverser


class BaseWizardApplicationTest(unittest.TestCase):
    def setUp(self):
        self.definition = self.get_definition()
        self.app = create_wizard_app(self.definition)
        self.stubbed_app = ApplicationStubber(self.app)

    def get_definition(self):
        return {
            'title': 'Wizard title',
            'plan': {}
        }

    def add_answer_submission(self, answer):
        self.stubbed_app.add_text_to_current_buffer(answer)
        self.stubbed_app.add_keypress(Keys.Enter)

    def add_app_values_assertion(self, **expected_values):
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertEqual(app.values, expected_values)
        )

    def add_prompt_is_visible_assertion(self, name):
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertIn(name, self.get_visible_buffers(app))
        )

    def add_prompt_is_not_visible_assertion(self, name):
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertNotIn(name, self.get_visible_buffers(app))
        )

    def get_visible_buffers(self, app):
        return [
            window.content.buffer.name
            for window in app.layout.visible_windows
            if hasattr(window.content, 'buffer')
        ]


class TestBasicWizardApplication(BaseWizardApplicationTest):
    def get_definition(self):
        return {
            'title': 'Basic Wizard',
            'plan': {
                'first_section': {
                    'shortname': 'First',
                    'values': {
                        'prompt1': {
                            'description': 'Description of first prompt',
                            'type': 'prompt'
                        },
                        'prompt2': {
                            'description': 'Description of second prompt',
                            'type': 'prompt'
                        },
                    }
                },
                'second_section': {
                    'shortname': 'Second',
                    'values': {
                        'second_section_prompt': {
                            'description': 'Description of prompt',
                            'type': 'prompt'
                        },
                    }
                }
            }
        }

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
        self.add_answer_submission('orig1')
        self.stubbed_app.add_keypress(Keys.BackTab)
        self.add_answer_submission('override1')
        self.add_app_values_assertion(prompt1='override1', prompt2='')
        self.stubbed_app.run()

    def test_can_answer_prompts_across_sections(self):
        self.add_answer_submission('val1')
        self.add_answer_submission('val2')
        self.add_answer_submission('second_section_val1')
        self.add_app_values_assertion(
            prompt1='val1', prompt2='val2',
            second_section_prompt='second_section_val1'
        )
        self.stubbed_app.run()

    def test_can_move_back_to_a_prompt_in_previous_section(self):
        self.add_answer_submission('val1')
        self.add_answer_submission('val2')
        self.add_answer_submission('second_section_val1')
        self.stubbed_app.add_keypress(Keys.BackTab)
        self.add_answer_submission('override2')
        self.add_app_values_assertion(
            prompt1='val1', prompt2='override2',
            second_section_prompt='second_section_val1'
        )
        self.stubbed_app.run()

    def test_prompts_are_not_visible_across_sections(self):
        self.add_prompt_is_visible_assertion('prompt1')
        self.add_prompt_is_visible_assertion('prompt2')
        self.add_prompt_is_not_visible_assertion('second_section_prompt')

        self.add_answer_submission('val1')
        self.add_answer_submission('val2')

        self.add_prompt_is_not_visible_assertion('prompt1')
        self.add_prompt_is_not_visible_assertion('prompt2')
        self.add_prompt_is_visible_assertion('second_section_prompt')
        self.stubbed_app.run()


class TestConditionalWizardApplication(BaseWizardApplicationTest):
    def get_definition(self):
        return {
            'title': 'Conditional wizard',
            'plan': {
                'section': {
                    'shortname': 'Section',
                    'values': {
                        'before_conditional': {
                            'description': 'Description of first prompt',
                            'type': 'prompt'
                        },
                        'conditional': {
                            'description': 'Description of second prompt',
                            'type': 'prompt',
                            'condition': {
                                'variable': 'before_conditional',
                                'equals': 'condition-met'
                            }
                        },
                        'after_conditional': {
                            'description': 'Description of second prompt',
                            'type': 'prompt',
                        },
                    }
                },
            }
        }

    def test_conditional_prompt_is_skipped_when_condition_not_met(self):
        self.add_prompt_is_not_visible_assertion('conditional')
        self.add_answer_submission('condition-not-met')
        self.add_prompt_is_not_visible_assertion('conditional')
        self.add_answer_submission('after-conditional-val')
        self.add_app_values_assertion(
            before_conditional='condition-not-met',
            after_conditional='after-conditional-val',
        )
        self.stubbed_app.run()

    def test_conditional_prompt_appears_when_condition_met(self):
        self.add_prompt_is_not_visible_assertion('conditional')
        self.add_answer_submission('condition-met')
        self.add_prompt_is_visible_assertion('conditional')
        self.add_answer_submission('val-at-conditional')
        self.add_app_values_assertion(
            before_conditional='condition-met',
            conditional='val-at-conditional',
        )
        self.stubbed_app.run()


class TestWizardTraverser(unittest.TestCase):
    def setUp(self):
        self.simple_definition = self.create_definition(
            sections={
                'first_section': {
                    'values': {
                        'first_prompt': self.create_prompt_definition(),
                        'second_prompt': self.create_prompt_definition(),
                    }
                }
            }
        )

    def create_traverser(self, definition, values=None):
        if values is None:
            values = {}
        return WizardTraverser(definition, values)

    def create_definition(self, sections):
        return {
            'plan': sections
        }

    def create_prompt_definition(self, description=None, condition=None):
        prompt = {
            'type': 'prompt'
        }
        if not description:
            description = 'A sample description'
        prompt['description'] = description
        if condition:
            prompt['condition'] = condition
        return prompt

    def test_get_current_prompt(self):
        traverser = self.create_traverser(self.simple_definition)
        self.assertEqual(traverser.get_current_prompt(), 'first_prompt')

    def test_get_current_section(self):
        traverser = self.create_traverser(self.simple_definition)
        self.assertEqual(traverser.get_current_section(), 'first_section')

    def test_next_prompt(self):
        traverser = self.create_traverser(self.simple_definition)
        next_prompt = traverser.next_prompt()
        self.assertEqual(next_prompt, 'second_prompt')
        self.assertEqual(traverser.get_current_section(), 'first_section')

    def test_next_prompt_condition_not_met(self):
        definition_with_condition = self.create_definition(
            sections={
                'first_section': {
                    'values': {
                        'first_prompt': self.create_prompt_definition(),
                        'conditional': self.create_prompt_definition(
                            condition={
                                'variable': 'first_prompt',
                                'equals': 'condition-met'
                            }
                        ),
                        'after_conditional': self.create_prompt_definition(),
                    }
                }
            }
        )
        traverser = self.create_traverser(
            definition_with_condition,
            values={
                'first_prompt': 'condition-not-met'
            }
        )
        next_prompt = traverser.next_prompt()
        self.assertEqual(next_prompt, 'after_conditional')

    def test_next_prompt_condition_met(self):
        definition_with_condition = self.create_definition(
            sections={
                'first_section': {
                    'values': {
                        'first_prompt': self.create_prompt_definition(),
                        'conditional': self.create_prompt_definition(
                            condition={
                                'variable': 'first_prompt',
                                'equals': 'condition-met'
                            }
                        ),
                        'after_conditional': self.create_prompt_definition(),
                    }
                }
            }
        )
        traverser = self.create_traverser(
            definition_with_condition,
            values={
                'first_prompt': 'condition-met'
            }
        )
        next_prompt = traverser.next_prompt()
        self.assertEqual(next_prompt, 'conditional')

    def test_next_prompt_moves_to_next_section_when_no_more_prompts(self):
        definition = self.create_definition(
            sections={
                'first_section': {
                    'values': {
                        'first_prompt': self.create_prompt_definition(),
                    }
                },
                'second_section': {
                    'values': {
                        'second_prompt': self.create_prompt_definition(),
                    }
                }
            }
        )
        traverser = self.create_traverser(definition)
        next_prompt = traverser.next_prompt()
        self.assertEqual(next_prompt, 'second_prompt')
        self.assertEqual(traverser.get_current_section(), 'second_section')

    def test_next_prompt_returns_same_prompt_at_end_of_wizard(self):
        definition = self.create_definition(
            sections={
                'only_section': {
                    'values': {
                        'only_prompt': self.create_prompt_definition(),
                    }
                }
            }
        )
        traverser = self.create_traverser(definition)
        next_prompt = traverser.next_prompt()
        self.assertEqual(next_prompt, 'only_prompt')

    def test_previous_prompt(self):
        traverser = self.create_traverser(self.simple_definition)
        next_prompt = traverser.next_prompt()
        self.assertEqual(next_prompt, 'second_prompt')
        self.assertEqual(traverser.get_current_section(), 'first_section')

        previous_prompt = traverser.previous_prompt()
        self.assertEqual(previous_prompt, 'first_prompt')
        self.assertEqual(traverser.get_current_section(), 'first_section')

    def test_previous_prompt_can_move_back_sections(self):
        definition = self.create_definition(
            sections={
                'first_section': {
                    'values': {
                        'first_prompt': self.create_prompt_definition(),
                    }
                },
                'second_section': {
                    'values': {
                        'second_prompt': self.create_prompt_definition(),
                    }
                }
            }
        )
        traverser = self.create_traverser(definition)
        next_prompt = traverser.next_prompt()
        self.assertEqual(next_prompt, 'second_prompt')
        self.assertEqual(traverser.get_current_section(), 'second_section')

        previous_prompt = traverser.previous_prompt()
        self.assertEqual(previous_prompt, 'first_prompt')
        self.assertEqual(traverser.get_current_section(), 'first_section')

    def test_previous_prompt_returns_same_prompt_at_start_of_wizard(self):
        traverser = self.create_traverser(self.simple_definition)
        previous_prompt = traverser.previous_prompt()
        self.assertEqual(previous_prompt, 'first_prompt')
        self.assertEqual(traverser.get_current_section(), 'first_section')

    def test_prompt_is_visible_when_no_condition(self):
        traverser = self.create_traverser(self.simple_definition)
        self.assertTrue(traverser.is_prompt_visible('second_prompt'))

    def test_prompt_is_visible_when_condition_met(self):
        definition_with_condition = self.create_definition(
            sections={
                'first_section': {
                    'values': {
                        'first_prompt': self.create_prompt_definition(),
                        'conditional': self.create_prompt_definition(
                            condition={
                                'variable': 'first_prompt',
                                'equals': 'condition-met'
                            }
                        ),
                    }
                }
            }
        )
        traverser = self.create_traverser(
            definition_with_condition,
            values={
                'first_prompt': 'condition-not-met'
            }
        )
        self.assertFalse(traverser.is_prompt_visible('conditional'))

    def test_prompt_is_not_visible_when_condition_not_met(self):
        definition_with_condition = self.create_definition(
            sections={
                'first_section': {
                    'values': {
                        'first_prompt': self.create_prompt_definition(),
                        'conditional': self.create_prompt_definition(
                            condition={
                                'variable': 'first_prompt',
                                'equals': 'condition-met'
                            }
                        ),
                    }
                }
            }
        )
        traverser = self.create_traverser(
            definition_with_condition,
            values={
                'first_prompt': 'condition-met'
            }
        )
        self.assertTrue(traverser.is_prompt_visible('conditional'))

    def test_prompt_is_not_visible_when_not_on_current_section(self):
        definition = self.create_definition(
            sections={
                'first_section': {
                    'values': {
                        'first_prompt': self.create_prompt_definition(),
                    }
                },
                'second_section': {
                    'values': {
                        'second_prompt': self.create_prompt_definition(),
                    }
                }
            }
        )
        traverser = self.create_traverser(definition)
        self.assertFalse(traverser.is_prompt_visible('second_prompt'))

    def test_has_visited_section(self):
        definition = self.create_definition(
            sections={
                'first_section': {
                    'values': {
                        'first_prompt': self.create_prompt_definition(),
                    }
                },
                'second_section': {
                    'values': {
                        'second_prompt': self.create_prompt_definition(),
                    }
                },
                'third_section': {
                    'values': {
                        'third_prompt': self.create_prompt_definition(),
                    }
                },
            }
        )
        # Start at the first section
        traverser = self.create_traverser(definition)
        self.assertTrue(traverser.has_visited_section('first_section'))
        self.assertFalse(traverser.has_visited_section('second_section'))
        self.assertFalse(traverser.has_visited_section('third_section'))

        # Move to the second section
        traverser.next_prompt()
        self.assertTrue(traverser.has_visited_section('first_section'))
        self.assertTrue(traverser.has_visited_section('second_section'))
        self.assertFalse(traverser.has_visited_section('third_section'))

        # Go back to the first section. Note the second section should still
        # count as visited.
        traverser.previous_prompt()
        self.assertTrue(traverser.has_visited_section('first_section'))
        self.assertTrue(traverser.has_visited_section('second_section'))
        self.assertFalse(traverser.has_visited_section('third_section'))
