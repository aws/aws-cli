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
from io import BytesIO, TextIOWrapper
from awscli.testutils import unittest, mock

from botocore.session import Session
from prompt_toolkit.application import Application
from prompt_toolkit.completion import PathCompleter, Completion
from prompt_toolkit.eventloop import Future
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import walk

from tests import (
    PromptToolkitApplicationStubber as ApplicationStubber,
    FakeApplicationOutput
)
from awscli.customizations.wizard.factory import create_wizard_app
from awscli.customizations.wizard.app import (
    WizardAppRunner, WizardTraverser, WizardValues
)
from awscli.customizations.wizard.exceptions import (
    InvalidChoiceException, UnableToRunWizardError, UnexpectedWizardException,
    InvalidDataTypeConversionException
)
from awscli.customizations.wizard.core import BaseStep, Executor


class TestWizardAppRunner(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock(Session)
        self.app_factory = mock.Mock(create_wizard_app)
        self.app = mock.Mock(Application)
        self.app.future = mock.Mock(Future)
        self.app.traverser = mock.Mock(WizardTraverser)
        self.app_factory.return_value = self.app
        self.definition = {}
        self.runner = WizardAppRunner(
            session=self.session, app_factory=self.app_factory
        )

    def test_run_calls_expected_app_interfaces(self):
        self.runner.run(self.definition)
        self.app.run.assert_called_with()
        self.app.future.result.assert_called_with()
        self.app.traverser.get_output.assert_called_with()

    def test_run_propagates_error_from_app_future(self):
        expected_exception = KeyboardInterrupt
        self.app.future.result.side_effect = KeyboardInterrupt
        with self.assertRaises(expected_exception):
            self.runner.run(self.definition)


class BaseWizardApplicationTest(unittest.TestCase):
    def setUp(self):
        self.definition = self.get_definition()
        self.session = mock.Mock(spec=Session)
        self.app = create_wizard_app(
            self.definition, self.session, FakeApplicationOutput())
        self.stubbed_app = ApplicationStubber(self.app)

    def get_definition(self):
        return {
            'title': 'Wizard title',
            'plan': {
                '__DONE__': {},
            },
            'execute': {}
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

    def add_current_buffer_assertion(self, buffer_name):
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertEqual(
                app.layout.current_buffer.name, buffer_name)
        )

    def add_buffer_completions_assertion(self, buffer_name, completions):
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertEqual(
                app.layout.get_buffer_by_name(
                    buffer_name).complete_state.completions,
                completions)
        )

    def add_prompt_is_visible_assertion(self, name):
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertIn(name, self.get_visible_buffers(app))
        )

    def add_prompt_is_not_visible_assertion(self, name):
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertNotIn(name, self.get_visible_buffers(app))
        )

    def add_run_wizard_dialog_is_visible(self):
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertIn(
                app.layout.run_wizard_dialog.container,
                self.get_visible_containers(app)
            )
        )

    def add_run_wizard_dialog_is_not_visible(self):
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertNotIn(
                app.layout.run_wizard_dialog.container,
                self.get_visible_containers(app)
            )
        )

    def add_toolbar_has_text_assertion(self, text):
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertTrue(any(
                [text in tip[1]
                 for tip in list(filter(
                    lambda x: getattr(x, 'name', '') == 'toolbar_panel',
                    app.layout.find_all_controls())
                 )[0].text()()]
            ))
        )

    def add_toolbar_has_not_text_assertion(self, text):
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertFalse(any(
                [text in tip[1]
                 for tip in list(filter(
                    lambda x: getattr(x, 'name', '') == 'toolbar_panel',
                    app.layout.find_all_controls())
                 )[0].text()()]
            ))
        )

    def get_visible_buffers(self, app):
        return [
            window.content.buffer.name
            for window in app.layout.visible_windows
            if hasattr(window.content, 'buffer')
        ]

    def get_visible_containers(self, app):
        return list(walk(app.layout.container, skip_hidden=True))


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
                            'type': 'prompt',
                            'default_value': 'foo'
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
                        'template_section': {
                            'type': 'template',
                            'value': 'some text',
                        }
                    }
                },
                '__DONE__': {},
            },
            'execute': {},
            '__OUTPUT__': {'value': 'output: {template_section}'}
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

    def test_can_use_prompt_default_value(self):
        self.stubbed_app.add_keypress(Keys.Tab)
        self.stubbed_app.add_keypress(Keys.Tab)
        self.add_app_values_assertion(prompt1='', prompt2='foo')
        self.stubbed_app.run()

    def test_can_use_shift_tab_to_toggle_backwards_and_change_answer(self):
        self.add_answer_submission('orig1')
        self.stubbed_app.add_keypress(Keys.BackTab)
        self.add_answer_submission('override1')
        self.add_app_values_assertion(prompt1='override1', prompt2='foo')
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
        self.stubbed_app.add_keypress(Keys.BackTab)  # At DONE step
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

    def test_run_wizard_dialog_appears_only_at_end_of_wizard(self):
        self.add_run_wizard_dialog_is_not_visible()
        self.add_answer_submission('val1')
        self.add_run_wizard_dialog_is_not_visible()
        self.add_answer_submission('val2')
        self.add_run_wizard_dialog_is_not_visible()
        self.add_answer_submission('second_section_val1')
        self.add_run_wizard_dialog_is_visible()
        self.stubbed_app.run()

    def test_enter_at_wizard_dialog_exits_app_with_zero_rc(self):
        self.add_answer_submission('val1')
        self.add_answer_submission('val2')
        self.add_answer_submission('second_section_val1')
        self.add_run_wizard_dialog_is_visible()
        self.stubbed_app.add_keypress(Keys.Enter)
        self.stubbed_app.run()
        self.assertEqual(self.app.future.result(), 0)

    def test_can_go_back_from_run_wizard_dialog(self):
        self.add_answer_submission('val1')
        self.add_answer_submission('val2')
        self.add_answer_submission('second_section_val1')
        self.add_run_wizard_dialog_is_visible()
        self.stubbed_app.add_keypress(Keys.Right)
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_answer_submission('override_second_section_val1')
        self.add_app_values_assertion(
            prompt1='val1', prompt2='val2',
            second_section_prompt='override_second_section_val1'
        )
        self.stubbed_app.run()

    def test_traverser_get_output(self):
        self.assertEqual('output: some text',
                         self.app.traverser.get_output())

    def test_can_exit_and_propagate_ctrl_c_from_wizard(self):
        self.stubbed_app.add_keypress(Keys.ControlC)
        with self.assertRaises(KeyboardInterrupt):
            self.stubbed_app.run()
            self.app.future.result()

    def test_captures_unexpected_errors_when_processing_input(self):
        unexpected_error = ValueError('Not expected')

        @self.app.key_bindings.add('a')
        def trigger_unexpected_error(event):
            raise unexpected_error

        self.app.output.stdout = TextIOWrapper(BytesIO(), encoding="utf-8")

        pipe_input = create_pipe_input()
        captured_exception = None
        try:
            pipe_input.send_text('a')
            self.app.input = pipe_input
            self.app.run()
        except UnexpectedWizardException as e:
            captured_exception = e
        finally:
            pipe_input.close()
        self.assertIsInstance(captured_exception, UnexpectedWizardException)
        self.assertIs(captured_exception.original_exception, unexpected_error)


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
                '__DONE__': {},
            },
            'execute': {}
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
                },
                '__DONE__': {},
            },
            'execute': {}
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


class TestCorruptedChoicesWizardApplication(BaseWizardApplicationTest):
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
                            'choices': 'corrupted_choice'
                        },
                        'corrupted_choice': {
                            'description': 'Description of first prompt',
                            'type': 'apicall',
                        }
                    }
                },
                '__DONE__': {},
            },
            'execute': {}
        }

    def test_can_handle_corrupted_choices(self):
        self.stubbed_app.add_keypress(Keys.Down)
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_app_values_assertion(choices_prompt=None)
        self.stubbed_app.run()

    def test_show_error_message_on_get_value_exception(self):
        self.add_buffer_text_assertion(
            'error_bar',
            'Encountered following error in wizard:\n\n\'operation\''
        )
        self.stubbed_app.run()

    def test_toolbar_text_on_get_value_exception(self):
        self.add_toolbar_has_text_assertion('error message')
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
                },
                '__DONE__': {},
            },
            'execute': {}
        }

    def test_can_answer_buffer_prompt_followed_by_select_prompt(self):
        self.add_answer_submission('buffer_answer')
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_app_values_assertion(
            buffer_input_prompt='buffer_answer',
            select_prompt='select_answer_1'
        )
        self.stubbed_app.run()


class TestPromptWithDataConvertWizardApplication(BaseWizardApplicationTest):
    def get_definition(self):
        return {
            'title': 'Wizard with both buffer inputs and select inputs',
            'plan': {
                'section': {
                    'shortname': 'Section',
                    'values': {
                        'buffer_input_int': {
                            'description': 'Type answer',
                            'type': 'prompt',
                            'datatype': 'int'
                        },
                        'buffer_input_bool': {
                            'description': 'Type answer',
                            'type': 'prompt',
                            'datatype': 'bool'
                        },
                    }
                },
                '__DONE__': {},
            },
            'execute': {}
        }

    def test_can_convert_integers(self):
        self.add_answer_submission('100')
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_app_values_assertion(
            buffer_input_int=100,
            buffer_input_bool=False
        )
        self.stubbed_app.run()

    def test_can_convert_bool(self):
        self.add_answer_submission('0')
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_answer_submission('true')
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_app_values_assertion(
            buffer_input_int=100,
            buffer_input_bool=True
        )
        self.stubbed_app.run()

    def test_show_error_and_stop_on_incorrect_input(self):
        self.add_answer_submission('foo')
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_buffer_text_assertion(
            'error_bar',
            'Encountered following error in wizard:\n\n'
            'Invalid value foo for datatype int'
        )
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertEqual(
                app.layout.current_buffer.name, 'buffer_input_int')
        )
        self.stubbed_app.run()

    def test_clear_error_and_go_on_after_correction(self):
        self.add_answer_submission('foo')
        self.add_buffer_text_assertion(
            'error_bar',
            'Encountered following error in wizard:\n\n'
            'Invalid value foo for datatype int'
        )
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertEqual(
                app.layout.current_buffer.name, 'buffer_input_int')
        )
        self.add_answer_submission('100')
        self.add_buffer_text_assertion('error_bar', '')
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertEqual(
                app.layout.current_buffer.name, 'buffer_input_bool')
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
                },
                '__DONE__': {},
            },
            'execute': {}
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
                            'details': {
                                'value': 'policy_document',
                                'description': 'Policy Document',
                                'output': 'json'
                            },
                        },
                        'some_prompt': {
                            'description': 'Choose something',
                            'type': 'prompt',
                            'choices': [1, 2, 3],
                        }
                    }
                },
                '__DONE__': {},
            },
            'execute': {}
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
            '{\n    "policy": "policy_document"\n}'
        )
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

    def test_can_set_details_panel_title(self):
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertEqual(app.details_title, 'Policy Document')
        )
        self.stubbed_app.add_keypress(
            Keys.F3,
            lambda app: self.assertEqual(app.details_title, 'Policy Document')
        )
        self.stubbed_app.run()

    def test_can_set_details_toolbar_text(self):
        self.add_toolbar_has_text_assertion('Policy Document')
        self.stubbed_app.run()


class TestPreviewWizardApplication(BaseWizardApplicationTest):
    def get_definition(self):
        return {
            'title': 'Show details in prompting stage',
            'plan': {
                'section': {
                    'shortname': 'Section',
                    'values': {
                        'option1': {
                            'type': 'template',
                            'value': "First option details"
                        },
                        'option2': {
                            'type': 'template',
                            'value': "Second option details"
                        },
                        'some_prompt': {
                            'description': 'Choose something',
                            'type': 'prompt',
                            'choices': [{
                                'display': '1', 'actual_value': '2'
                            }],
                        },
                        'choose_option': {
                            'description': 'Choose option',
                            'type': 'prompt',
                            'choices': [
                                {'display': 'Option 1',
                                 'actual_value': 'option1'},
                                {'display': 'Option 2',
                                 'actual_value': 'option2'},
                            ],
                            'details': {
                                'visible': True,
                                'value': '__selected_choice__',
                                'description': 'Option details',
                            },
                        },
                    }
                },
                '__DONE__': {},
            }
        }

    def test_details_panel_visible_by_default(self):
        self.stubbed_app.add_keypress(Keys.Tab)
        self.add_prompt_is_visible_assertion('details_buffer')
        self.stubbed_app.run()

    def test_get_details_for_choice(self):
        self.stubbed_app.add_keypress(Keys.Tab)
        self.add_buffer_text_assertion(
            'details_buffer',
            'First option details'
        )
        self.stubbed_app.run()

    def test_get_details_for_second_choice(self):
        self.stubbed_app.add_keypress(Keys.Tab)
        self.stubbed_app.add_keypress(Keys.Down)
        self.add_buffer_text_assertion(
            'details_buffer',
            'Second option details'
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
                },
                '__DONE__': {},
            }
        }

    def test_uses_choices_from_api_call(self):
        self.session.available_profiles = ['profile1', 'profile2']
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_app_values_assertion(choose_profile='profile1')
        self.stubbed_app.run()


class TestRunWizardApplication(BaseWizardApplicationTest):
    def setUp(self):
        super().setUp()
        self.client = mock.Mock()
        self.session.create_client.return_value = self.client
        self.role_arn = 'returned-role-arn'
        self.create_role_response = {
            'Role': {
                'Arn': self.role_arn
            }
        }

    def get_definition(self):
        return {
            'title': 'For running execute step',
            'plan': {
                'section': {
                    'shortname': 'Section',
                    'values': {
                        'role_name': {
                            'type': 'prompt',
                            'description': 'Enter role name'
                        }
                    }
                },
                '__DONE__': {},
            },
            'execute': {
                'default': [
                    {
                        'type': 'apicall',
                        'operation': 'iam.CreateRole',
                        'params': {
                            'RoleName': "{role_name}"
                        },
                        'output_var': 'role_arn',
                        'query': 'Role.Arn',
                    }

                ]
            }
        }

    def add_error_bar_is_not_visible_assertion(self):
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertNotIn(
                'error_bar', self.get_visible_buffers(app))
        )

    def add_error_bar_is_visible_assertion(self):
        self.stubbed_app.add_app_assertion(
            lambda app: self.assertIn(
                'error_bar', self.get_visible_buffers(app))
        )

    def test_run_wizard_execute(self):
        self.client.create_role.return_value = self.create_role_response
        self.add_answer_submission('role-name')
        self.stubbed_app.add_keypress(Keys.Enter)
        self.stubbed_app.run()
        self.client.create_role.assert_called_with(RoleName='role-name')
        self.assertEqual(self.app.values['role_arn'], self.role_arn)

    def test_run_wizard_captures_and_displays_errors(self):
        self.client.create_role.side_effect = Exception('Error creating role')
        self.add_answer_submission('role-name')
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_buffer_text_assertion(
            'error_bar',
            'Encountered following error in wizard:\n\nError creating role'
        )
        self.stubbed_app.run()

    def test_can_change_answers_on_run_wizard_failure(self):
        self.client.create_role.side_effect = [
            Exception('Initial error'),
            self.create_role_response
        ]
        self.add_answer_submission('role-name')
        self.add_error_bar_is_not_visible_assertion()
        self.add_run_wizard_dialog_is_visible()
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_buffer_text_assertion(
            'error_bar',
            'Encountered following error in wizard:\n\nInitial error'
        )

        # Make sure dialog closed on error but error message is still visible
        self.add_run_wizard_dialog_is_not_visible()
        self.add_error_bar_is_visible_assertion()
        self.add_answer_submission('new-role-name')

        # Make sure we select "Yes" button in dialog
        self.stubbed_app.add_keypress(Keys.Left)
        self.stubbed_app.add_keypress(Keys.Enter)
        self.stubbed_app.run()
        self.client.create_role.assert_called_with(RoleName='new-role-name')
        self.assertEqual(self.app.values['role_arn'], self.role_arn)

    def test_can_switch_exception_panel(self):
        self.client.create_role.side_effect = [
            Exception('Initial error'),
            self.create_role_response
        ]
        self.add_answer_submission('role-name')
        self.add_error_bar_is_not_visible_assertion()
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_error_bar_is_visible_assertion()
        self.stubbed_app.add_keypress(Keys.F2)
        self.add_error_bar_is_not_visible_assertion()

    def test_toolbar_has_exception_panel_hot_key(self):
        self.client.create_role.side_effect = [
            Exception('Initial error'),
            self.create_role_response
        ]
        self.add_answer_submission('role-name')
        self.add_error_bar_is_not_visible_assertion()
        self.add_toolbar_has_not_text_assertion('error message')
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_error_bar_is_visible_assertion()
        self.add_toolbar_has_text_assertion('error message')


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

        self.single_prompt_definition = self.create_definition(
            sections={
                'only_section': {
                    'values': {
                        'only_prompt': self.create_prompt_definition(),
                    }
                }
            }
        )

        self.single_prompt_definition_with_datatype = self.create_definition(
            sections={
                'only_section': {
                    'values': {
                        'only_prompt': self.create_prompt_definition(
                                                            datatype='int'),
                    }
                }
            }
        )

    def create_traverser(self, definition, values=None, executor=None,):
        if values is None:
            values = {}
        if executor is None:
            executor = mock.Mock(Executor)
        return WizardTraverser(definition, values, executor)

    def create_definition(self, sections, execute=None):
        sections = sections.copy()
        sections['__DONE__'] = {}
        if execute is None:
            execute = {}
        return {
            'plan': sections,
            'execute': execute
        }

    def create_prompt_definition(self, description=None, condition=None,
                                 choices=None, datatype=None):
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
        if datatype:
            prompt['datatype'] = datatype
        return prompt

    def test_get_current_prompt(self):
        traverser = self.create_traverser(self.simple_definition)
        self.assertEqual(traverser.get_current_prompt(), 'first_prompt')

    def test_get_current_prompt_returns_done_when_no_more_prompts(self):
        traverser = self.create_traverser(self.single_prompt_definition)
        traverser.next_prompt()
        self.assertEqual(traverser.get_current_prompt(), traverser.DONE)

    def test_get_current_section(self):
        traverser = self.create_traverser(self.simple_definition)
        self.assertEqual(traverser.get_current_section(), 'first_section')

    def test_get_current_section_returns_done_when_no_more_prompts(self):
        traverser = self.create_traverser(self.single_prompt_definition)
        traverser.next_prompt()
        self.assertEqual(traverser.get_current_section(), traverser.DONE)

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

    def test_submit_prompt_answer_converts_datatype(self):
        values = {}
        traverser = self.create_traverser(
            self.single_prompt_definition_with_datatype, values
        )
        traverser.submit_prompt_answer('100')
        self.assertEqual(values, {'only_prompt': 100})

    def test_submit_prompt_raise_correct_exception_on_datatype_convert(self):
        values = {}
        traverser = self.create_traverser(
            self.single_prompt_definition_with_datatype, values,
        )
        with self.assertRaises(InvalidDataTypeConversionException) as e:
            traverser.submit_prompt_answer('foo')
        self.assertEqual(
            str(e.exception), 'Invalid value foo for datatype int')

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

    def test_next_prompt_returns_done_at_end_of_wizard(self):
        traverser = self.create_traverser(self.single_prompt_definition)
        next_prompt = traverser.next_prompt()
        self.assertEqual(next_prompt, traverser.DONE)

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

    def test_previous_prompt_returns_last_prompt_from_done(self):
        traverser = self.create_traverser(self.single_prompt_definition)
        traverser.next_prompt()
        self.assertTrue(traverser.has_no_remaining_prompts())
        self.assertEqual(traverser.previous_prompt(), 'only_prompt')

    def test_run_wizard_calls_executor(self):
        executor = mock.Mock(Executor)
        values = {}
        execute_definition = {
            'step': []
        }
        traverser = self.create_traverser(
            definition=self.create_definition(
                sections={
                    'only_section': {
                        'values': {
                            'only_prompt': self.create_prompt_definition(),
                        }
                    },
                },
                execute=execute_definition
            ),
            values=values,
            executor=executor,
        )
        traverser.submit_prompt_answer('only_answer')
        traverser.next_prompt()
        traverser.run_wizard()
        executor.execute.assert_called_with(execute_definition, values)

    def test_run_wizard_throws_error_when_not_at_done_step(self):
        traverser = self.create_traverser(self.simple_definition)
        with self.assertRaises(UnableToRunWizardError):
            traverser.run_wizard()

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

    def test_has_no_remaining_prompts(self):
        traverser = self.create_traverser(self.single_prompt_definition)
        self.assertFalse(traverser.has_no_remaining_prompts())
        traverser.next_prompt()
        self.assertTrue(traverser.has_no_remaining_prompts())


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
        self.exception_handler = mock.Mock()

    def get_wizard_values(self, retrieval_steps=None, exception_handler=None):
        if exception_handler is None:
            exception_handler = self.exception_handler
        return WizardValues(
            self.definition, retrieval_steps, exception_handler
        )

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

    def test_exception_handler(self):
        e = Exception()
        self.handler.run_step.side_effect = e
        values = self.get_wizard_values({'use_handler': self.handler})
        value = values['handler_value']
        self.exception_handler.assert_called_with(e)


class FakePathCompleter(PathCompleter):
    def get_completions(self, document, complete_event):
        prefix_len = len(document.text)

        yield from [
            Completion('file1'[prefix_len:], 0, display='file1'),
            Completion('file2'[prefix_len:], 0, display='file2'),
        ]


class TestPromptCompletionWizardApplication(BaseWizardApplicationTest):
    def setUp(self):
        self.patch = mock.patch(
            'awscli.customizations.wizard.ui.prompt.PathCompleter',
            FakePathCompleter)
        self.patch.start()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        self.patch.stop()

    def get_definition(self):
        return {
            'title': 'Uses API call in prompting stage',
            'plan': {
                'section': {
                    'shortname': 'Section',
                    'values': {
                        'choose_file': {
                            'description': 'Choose file',
                            'type': 'prompt',
                            'completer': 'file_completer'
                        },
                        'second_prompt': {
                            'description': 'Second prompt',
                            'type': 'prompt',
                        }
                    }
                },
                '__DONE__': {},
            },
            'execute': {}
        }

    def test_show_completions_for_buffer_text(self):
        self.stubbed_app.add_text_to_current_buffer('fi')
        self.stubbed_app.start_completion_for_current_buffer()
        self.add_buffer_completions_assertion('choose_file',
            [
                Completion('le1', 0, display='file1'),
                Completion('le2', 0, display='file2'),
            ]
        )
        self.stubbed_app.run()

    def test_choose_completion_on_Enter_and_stays_on_the_same_prompt(self):
        self.stubbed_app.add_text_to_current_buffer('fi')
        self.stubbed_app.start_completion_for_current_buffer()
        self.stubbed_app.add_keypress(Keys.Down)
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_buffer_text_assertion('choose_file', 'file1')
        self.add_current_buffer_assertion('choose_file')
        self.stubbed_app.run()

    def test_choose_completion_on_Enter_and_move_on_second_Enter(self):
        self.stubbed_app.add_text_to_current_buffer('fi')
        self.stubbed_app.start_completion_for_current_buffer()
        self.stubbed_app.add_keypress(Keys.Down)
        self.stubbed_app.add_keypress(Keys.Enter)
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_current_buffer_assertion('second_prompt')
        self.stubbed_app.run()

    def test_switch_completions_on_tab(self):
        self.stubbed_app.add_text_to_current_buffer('fi')
        self.stubbed_app.start_completion_for_current_buffer()
        self.stubbed_app.add_keypress(Keys.Tab)
        self.stubbed_app.add_keypress(Keys.Tab)
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_buffer_text_assertion('choose_file', 'file2')
        self.add_current_buffer_assertion('choose_file')
        self.stubbed_app.run()

    def test_switch_completions_on_back_tab(self):
        self.stubbed_app.add_text_to_current_buffer('fi')
        self.stubbed_app.start_completion_for_current_buffer()
        self.stubbed_app.add_keypress(Keys.Tab)
        self.stubbed_app.add_keypress(Keys.Tab)
        self.stubbed_app.add_keypress(Keys.BackTab)
        self.stubbed_app.add_keypress(Keys.Enter)
        self.add_buffer_text_assertion('choose_file', 'file1')
        self.add_current_buffer_assertion('choose_file')
        self.stubbed_app.run()

    def test_switch_prompt_on_tab_if_it_is_not_completing(self):
        self.stubbed_app.add_text_to_current_buffer('rrrr')
        self.stubbed_app.add_keypress(Keys.Tab)
        self.add_current_buffer_assertion('second_prompt')
        self.stubbed_app.run()
