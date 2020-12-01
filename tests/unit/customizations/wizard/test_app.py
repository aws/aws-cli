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

from botocore.session import Session
from prompt_toolkit.keys import Keys

from tests import PromptToolkitApplicationStubber as ApplicationStubber
from awscli.customizations.wizard.app import (
    create_wizard_app, InvalidChoiceException, WizardTraverser,
    WizardValues
)
from awscli.customizations.wizard.core import BaseStep


class BaseWizardApplicationTest(unittest.TestCase):
    def setUp(self):
        self.definition = self.get_definition()
        self.session = mock.Mock(spec=Session)
        self.app = create_wizard_app(self.definition, self.session)
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
            lambda app: self.assertEqual(dict(app.values), expected_values)
        )

    def add_buffer_text_assertion(self, buffer_name, text):
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertEqual(
                app.layout.get_buffer_by_name(buffer_name).document.text,
                text)
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


class TestChoicesWizardApplication(BaseWizardApplicationTest):
    def get_definition(self):
        return {
            'title': 'Conditional wizard',
            'plan': {
                'section': {
                    'shortname': 'Section',
                    'values': {
                        'choices_prompt': {
                            'description': 'Description of first prompt',
                            'type': 'prompt',
                            'choices': [
                                {
                                    'display': 'Option 1',
                                    'actual_value': 'actual_option_1'
                                },
                                {
                                    'display': 'Option 2',
                                    'actual_value': 'actual_option_2'
                                }
                            ]
                        }
                    }
                }
            }
        }

    def test_immediately_pressing_enter_selects_first_choice(self):
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_app_values_assertion(choices_prompt='actual_option_1')
        self.stubbed_app.run()

    def test_can_select_choice_in_prompt(self):
        self.stubbed_app.add_keypress(Keys.Down)
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_app_values_assertion(choices_prompt='actual_option_2')
        self.stubbed_app.run()


class TestMixedPromptTypeWizardApplication(BaseWizardApplicationTest):
    def get_definition(self):
        return {
            'title': 'Wizard with both buffer inputs and select inputs',
            'plan': {
                'section': {
                    'shortname': 'Section',
                    'values': {
                        'buffer_input_prompt': {
                            'description': 'Type answer',
                            'type': 'prompt',
                        },
                        'select_prompt': {
                            'description': 'Select answer',
                            'type': 'prompt',
                            'choices': [
                                'select_answer_1',
                                'select_answer_2'
                            ]
                        }
                    }
                }
            }
        }

    def test_can_answer_buffer_prompt_followed_by_select_prompt(self):
        self.add_answer_submission('buffer_answer')
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_app_values_assertion(
            buffer_input_prompt='buffer_answer',
            select_prompt='select_answer_1'
        )
        self.stubbed_app.run()


class TestApiCallWizardApplication(BaseWizardApplicationTest):
    def get_definition(self):
        return {
            'title': 'Uses API call in prompting stage',
            'plan': {
                'section': {
                    'shortname': 'Section',
                    'values': {
                        'existing_policies': {
                            'type': 'apicall',
                            'operation': 'iam.ListPolicies',
                            'params': {},
                            'query': (
                                'sort_by(Policies[].{display: PolicyName, '
                                'actual_value: Arn}, &display)'
                            )
                        },
                        'choose_policy': {
                            'description': 'Choose policy',
                            'type': 'prompt',
                            'choices': 'existing_policies'
                        }
                    }
                }
            }
        }

    def test_uses_choices_from_api_call(self):
        mock_client = mock.Mock()
        self.session.create_client.return_value = mock_client
        mock_client.list_policies.return_value = {
            'Policies': [
                {
                    'PolicyName': 'policy1',
                    'Arn': 'policy1_arn'
                },
                {
                    'PolicyName': 'policy2',
                    'Arn': 'policy2_arn'
                }
            ]
        }
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_app_values_assertion(choose_policy='policy1_arn')
        self.stubbed_app.run()


class TestDetailsWizardApplication(BaseWizardApplicationTest):
    def get_definition(self):
        return {
            'title': 'Show details in prompting stage',
            'plan': {
                'section': {
                    'shortname': 'Section',
                    'values': {
                        'version_id': {
                            'type': 'apicall',
                            'operation': 'iam.GetPolicy',
                            'params': {
                                'PolicyArn': '{policy_arn}'
                            },
                            'query': 'Policy.DefaultVersionId',
                            'cache': True
                        },
                        'policy_document': {
                            'type': 'apicall',
                            'operation': 'iam.GetPolicyVersion',
                            'params': {
                                'PolicyArn': '{policy_arn}',
                                'VersionId': '{version_id}'
                            },
                            'query': 'PolicyVersion.Document',
                            'cache': True
                        },
                        'existing_policies': {
                            'type': 'apicall',
                            'operation': 'iam.ListPolicies',
                            'params': {},
                            'query': (
                                'sort_by(Policies[].{display: PolicyName, '
                                'actual_value: Arn}, &display)'
                            )
                        },
                        'policy_arn': {
                            'description': 'Choose policy',
                            'type': 'prompt',
                            'choices': 'existing_policies',
                            'details': {'value': 'policy_document'},
                        },
                        'some_prompt': {
                            'description': 'Choose something',
                            'type': 'prompt',
                            'choices': [1, 2, 3],
                        }
                    }
                }
            }
        }

    def setUp(self):
        super(TestDetailsWizardApplication, self).setUp()
        self.mock_client = mock.Mock()
        self.session.create_client.return_value = self.mock_client
        self.mock_client.list_policies.return_value = {
            'Policies': [
                {
                    'PolicyName': 'policy1',
                    'Arn': 'policy1_arn'
                },
                {
                    'PolicyName': 'policy2',
                    'Arn': 'policy2_arn'
                }
            ]
        }
        self.mock_client.get_policy.return_value = {
            'Policy': {'DefaultVersionId': 'policy_id'}
        }
        self.mock_client.get_policy_version.return_value = {
            'PolicyVersion': {'Document': {'policy': 'policy_document'}}
        }

    def test_get_details_for_choice(self):
        self.stubbed_app.add_keypress(Keys.F3)
        self.add_buffer_text_assertion(
            'details_buffer',
            '{\n  "policy": "policy_document"\n}'
        )
        self.add_prompt_is_visible_assertion('toolbar_details')
        self.stubbed_app.run()

    def test_details_disabled_for_choice_wo_details(self):
        self.add_prompt_is_visible_assertion('toolbar_details')
        self.stubbed_app.add_keypress(Keys.Tab)
        self.add_prompt_is_not_visible_assertion('toolbar_details')
        self.stubbed_app.add_keypress(Keys.F3)
        self.add_prompt_is_not_visible_assertion('details_buffer')

    def test_can_switch_focus_to_details_panel(self):
        self.stubbed_app.add_keypress(Keys.F3)
        self.stubbed_app.add_keypress(
            Keys.F2,
            lambda app: self.assertEqual(
                app.layout.current_buffer.name, 'details_buffer')
        )
        self.stubbed_app.add_keypress(
            Keys.F3,
            lambda app: self.assertIsNone(app.layout.current_buffer)
        )
        self.stubbed_app.run()

    def test_can_not_switch_focus_to_details_panel_if_it_not_visible(self):
        self.stubbed_app.add_keypress(
            Keys.F2,
            lambda app: self.assertIsNone(app.layout.current_buffer)
        )
        self.stubbed_app.run()


class TestSharedConfigWizardApplication(BaseWizardApplicationTest):
    def get_definition(self):
        return {
            'title': 'Uses shared config API in prompting stage',
            'plan': {
                'section': {
                    'shortname': 'Section',
                    'values': {
                        'existing_profiles': {
                            'type': 'sharedconfig',
                            'operation': 'ListProfiles',
                        },
                        'choose_profile': {
                            'description': 'Choose profile',
                            'type': 'prompt',
                            'choices': 'existing_profiles'
                        }
                    }
                }
            }
        }

    def test_uses_choices_from_api_call(self):
        self.session.available_profiles = ['profile1', 'profile2']
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_app_values_assertion(choose_profile='profile1')
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
        self.simple_choice_definition = self.create_definition(
            sections={
                'first_section': {
                    'values': {
                        'choice_prompt': self.create_prompt_definition(
                            choices=[
                                {
                                    'display': 'Option 1',
                                    'actual_value': 'actual_option_1'
                                },
                                {
                                    'display': 'Option 2',
                                    'actual_value': 'actual_option_2'
                                }
                            ]
                        ),
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

    def create_prompt_definition(self, description=None, condition=None,
                                 choices=None):
        prompt = {
            'type': 'prompt'
        }
        if not description:
            description = 'A sample description'
        prompt['description'] = description
        if condition:
            prompt['condition'] = condition
        if choices:
            prompt['choices'] = choices
        return prompt

    def test_get_current_prompt(self):
        traverser = self.create_traverser(self.simple_definition)
        self.assertEqual(traverser.get_current_prompt(), 'first_prompt')

    def test_get_current_section(self):
        traverser = self.create_traverser(self.simple_definition)
        self.assertEqual(traverser.get_current_section(), 'first_section')

    def test_get_current_prompt_choices(self):
        traverser = self.create_traverser(self.simple_choice_definition)
        self.assertEqual(
            traverser.get_current_prompt_choices(),
            ['Option 1', 'Option 2']
        )

    def test_get_current_prompt_choices_as_list_of_strings(self):
        choice_wizard = self.create_definition(
            sections={
                'first_section': {
                    'values': {
                        'choice_prompt': self.create_prompt_definition(
                            choices=[
                                'from_list_1',
                                'from_list_2',
                            ]
                        ),
                    }
                }
            }
        )
        traverser = self.create_traverser(choice_wizard)
        self.assertEqual(
            traverser.get_current_prompt_choices(),
            ['from_list_1', 'from_list_2']
        )

    def test_get_current_prompt_choices_from_variable(self):
        values = {'choices_var': ['from_var_1', 'from_var_2']}
        choice_wizard = self.create_definition(
            sections={
                'first_section': {
                    'values': {
                        'choice_prompt': self.create_prompt_definition(
                            choices='choices_var'
                        ),
                    }
                }
            }
        )
        traverser = self.create_traverser(choice_wizard, values)
        self.assertEqual(
            traverser.get_current_prompt_choices(),
            ['from_var_1', 'from_var_2']
        )

    def test_get_current_prompt_choices_returns_none_when_no_choices(self):
        traverser = self.create_traverser(self.simple_definition)
        self.assertEqual(traverser.get_current_prompt_choices(), None)

    def test_submit_prompt_answer(self):
        values = {}
        traverser = self.create_traverser(self.simple_definition, values)
        traverser.submit_prompt_answer('answer1')
        self.assertEqual(values, {'first_prompt': 'answer1'})

    def test_submit_prompt_answer_converts_display_value(self):
        values = {}
        traverser = self.create_traverser(
            self.simple_choice_definition, values
        )
        traverser.submit_prompt_answer('Option 1')
        self.assertEqual(values, {'choice_prompt': 'actual_option_1'})

    def test_submit_prompt_answer_throw_error_for_invalid_option(self):
        traverser = self.create_traverser(self.simple_choice_definition)
        with self.assertRaises(InvalidChoiceException):
            traverser.submit_prompt_answer('Not an option')

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


class TestWizardValues(unittest.TestCase):
    def setUp(self):
        self.definition = {
            'title': 'Wizard',
            'plan': {
                'section': {
                    'shortname': 'Section',
                    'values': {
                        'no_handler_value': {
                            'type': 'prompt'
                        },
                        'handler_value': {
                            'type': 'use_handler'
                        }
                    }
                }
            }
        }
        self.handler = mock.Mock(BaseStep)

    def get_wizard_values(self, retrieval_steps=None):
        return WizardValues(self.definition, retrieval_steps)

    def test_manual_get_and_set(self):
        values = self.get_wizard_values()
        values['no_handler_value'] = 'manual'
        self.assertEqual(values['no_handler_value'], 'manual')

    def test_get_with_handler(self):
        self.handler.run_step.return_value = 'from_handler'
        values = self.get_wizard_values({'use_handler': self.handler})
        self.assertEqual(values['handler_value'], 'from_handler')

    def test_manual_set_overrides_delegation_handler(self):
        self.handler.run_step.return_value = 'from_handler'
        values = self.get_wizard_values({'use_handler': self.handler})
        values['handler_value'] = 'manual'
        self.assertEqual(values['handler_value'], 'manual')
        self.handler.run_step.assert_not_called()

    def test_delete(self):
        values = self.get_wizard_values()
        values['no_handler_value'] = 'manual'
        self.assertEqual(values['no_handler_value'], 'manual')
        del values['no_handler_value']
        self.assertNotIn('no_handler_value', values)

    def test_iterates_over_value_names(self):
        values = self.get_wizard_values()
        values['no_handler_value'] = 'manual'
        value_names = list(values)
        self.assertEqual(value_names, ['no_handler_value'])

    def test_length(self):
        values = self.get_wizard_values()
        values['no_handler_value'] = 'manual'
        self.assertEqual(len(values), 1)

    def test_copy(self):
        values = self.get_wizard_values()
        values['foo'] = 'bar'
        values['bar'] = 'foo'
        values_copy = values.copy()
        for key in values.keys():
            self.assertEqual(values[key], values_copy[key])
        self.assertEqual(len(values), len(values_copy))
        self.assertNotEqual(id(values), id(values_copy))
