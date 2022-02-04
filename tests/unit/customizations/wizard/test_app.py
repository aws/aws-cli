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
from prompt_toolkit.application import Application
from prompt_toolkit.completion import PathCompleter, Completion
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import walk
import pytest

from tests import ThreadedAppRunner
from awscli.customizations.wizard.factory import create_wizard_app
from awscli.customizations.wizard.app import (
    WizardAppRunner, WizardTraverser, WizardValues, FileIO
)
from awscli.customizations.wizard.exceptions import (
    InvalidChoiceException, UnableToRunWizardError, UnexpectedWizardException,
    InvalidDataTypeConversionException
)
from awscli.customizations.wizard.core import BaseStep, Executor


@pytest.fixture
def mock_botocore_session():
    return mock.Mock(spec=Session)


@pytest.fixture
def mock_iam_client(mock_botocore_session):
    mock_client = mock.Mock()
    mock_botocore_session.create_client.return_value = mock_client
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
    mock_client.get_policy.return_value = {
        'Policy': {'DefaultVersionId': 'policy_id'}
    }
    mock_client.get_policy_version.return_value = {
        'PolicyVersion': {'Document': {'policy': 'policy_document'}}
    }
    mock_client.create_role.return_value = {
        'Role': {'Arn': 'returned-role-arn'}
    }
    return mock_client


@pytest.fixture
def make_stubbed_wizard_runner(ptk_app_session, mock_botocore_session):
    def _make_stubbed_wizard_runner(definition):
        app = create_wizard_app(
            definition=definition,
            session=mock_botocore_session,
            output=ptk_app_session.output,
            app_input=ptk_app_session.input,
        )
        ptk_app_session.app = app
        return ThreadedAppRunner(app=app)
    yield _make_stubbed_wizard_runner


@pytest.fixture
def patch_path_completer():
    with mock.patch(
            'awscli.customizations.wizard.ui.prompt.PathCompleter',
            FakePathCompleter) as completer:
        yield completer


class FakePathCompleter(PathCompleter):
    def get_completions(self, document, complete_event):
        prefix_len = len(document.text)
        yield from [
            Completion('file1'[prefix_len:], 0, display='file1'),
            Completion('file2'[prefix_len:], 0, display='file2'),
        ]


@pytest.fixture
def empty_definition():
    return {
        'title': 'Wizard title',
        'plan': {
            '__DONE__': {},
        },
        'execute': {}
    }


@pytest.fixture
def basic_definition():
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


@pytest.fixture
def conditional_definition():
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


@pytest.fixture
def choices_definition():
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


@pytest.fixture
def corrupted_choice_definition():
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


@pytest.fixture
def mixed_prompt_definition():
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


@pytest.fixture
def data_convert_definition():
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


@pytest.fixture
def api_call_definition():
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


@pytest.fixture
def details_definition():
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


@pytest.fixture
def preview_definition():
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


@pytest.fixture
def shared_config_definition():
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


@pytest.fixture
def run_wizard_definition():
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


@pytest.fixture
def file_prompt_definition():
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


class TestWizardAppRunner(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock(Session)
        self.app_factory = mock.Mock(create_wizard_app)
        self.app = mock.Mock(Application)
        self.app.traverser = mock.Mock(WizardTraverser)
        self.app_factory.return_value = self.app
        self.definition = {}
        self.runner = WizardAppRunner(
            session=self.session, app_factory=self.app_factory
        )

    def test_run_calls_expected_app_interfaces(self):
        self.runner.run(self.definition)
        self.app.run.assert_called_with()
        self.app.traverser.get_output.assert_called_with()

    def test_run_propagates_error_from_app_run(self):
        expected_exception = KeyboardInterrupt
        self.app.run.side_effect = KeyboardInterrupt
        with self.assertRaises(expected_exception):
            self.runner.run(self.definition)


class BaseWizardApplicationTest:
    def assert_app_values(self, app, **expected_values):
        assert dict(app.values) == expected_values

    def assert_buffer_text(self, app, buffer_name, expected_text):
        buffer = app.layout.get_buffer_by_name(buffer_name)
        assert buffer.document.text == expected_text

    def assert_current_buffer(self, app, buffer_name):
        assert app.layout.current_buffer.name, buffer_name

    def assert_expected_buffer_completions(
            self, app, buffer_name, expected_completions):
        buffer = app.layout.get_buffer_by_name(buffer_name)
        assert buffer.complete_state.completions == expected_completions

    def assert_prompt_is_visible(self, app, prompt_name):
        assert prompt_name in self.get_visible_buffers(app)

    def assert_prompt_is_not_visible(self, app, prompt_name):
        assert prompt_name not in self.get_visible_buffers(app)

    def assert_run_wizard_dialog_is_visible(self, app):
        dialog_container = app.layout.run_wizard_dialog.container
        assert dialog_container in self.get_visible_containers(app)

    def assert_run_wizard_dialog_is_not_visible(self, app):
        dialog_container = app.layout.run_wizard_dialog.container
        assert dialog_container not in self.get_visible_containers(app)

    def assert_toolbar_has_text(self, app, text):
        assert any(
            [text in tip[1]
             for tip in list(filter(
                lambda x: getattr(x, 'name', '') == 'toolbar_panel',
                app.layout.find_all_controls())
            )[0].text()()]
        )

    def assert_toolbar_does_not_have_text(self, app, text):
        assert not any(
            [text in tip[1]
             for tip in list(filter(
                lambda x: getattr(x, 'name', '') == 'toolbar_panel',
                app.layout.find_all_controls())
            )[0].text()()]
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
    def test_can_answer_single_prompt(
            self, make_stubbed_wizard_runner, basic_definition):
        app_runner = make_stubbed_wizard_runner(basic_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('val1\n')
            self.assert_app_values(app_runner.app, prompt1='val1')

    def test_can_answer_multiple_prompts(
            self, make_stubbed_wizard_runner, basic_definition):
        app_runner = make_stubbed_wizard_runner(basic_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('val1\n')
            # This is to remove the default answer of foo for prompt 2
            app_runner.feed_input(
                Keys.Backspace, Keys.Backspace, Keys.Backspace)
            app_runner.feed_input('val2\n')
            self.assert_app_values(
                app_runner.app, prompt1='val1', prompt2='val2')

    def test_can_use_tab_to_submit_answer(
            self, make_stubbed_wizard_runner, basic_definition):
        app_runner = make_stubbed_wizard_runner(basic_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('val1')
            app_runner.feed_input(Keys.Tab)
            self.assert_app_values(app_runner.app, prompt1='val1')

    def test_can_use_prompt_default_value(
            self, make_stubbed_wizard_runner, basic_definition):
        app_runner = make_stubbed_wizard_runner(basic_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.Tab)
            app_runner.feed_input(Keys.Tab)
            self.assert_app_values(app_runner.app, prompt1='', prompt2='foo')

    def test_can_use_shift_tab_to_toggle_backwards_and_change_answer(
            self, make_stubbed_wizard_runner, basic_definition):
        app_runner = make_stubbed_wizard_runner(basic_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('1\n')
            app_runner.feed_input(Keys.BackTab)
            app_runner.feed_input(Keys.Backspace)
            app_runner.feed_input('override1\n')
            self.assert_app_values(
                app_runner.app, prompt1='override1', prompt2='foo')

    def test_can_answer_prompts_across_sections(
            self, make_stubbed_wizard_runner, basic_definition):
        app_runner = make_stubbed_wizard_runner(basic_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('val1\n')
            app_runner.feed_input('\n')
            app_runner.feed_input('second_section_val1\n')
            self.assert_app_values(
                app_runner.app, prompt1='val1', prompt2='foo',
                second_section_prompt='second_section_val1'
            )

    def test_can_move_back_to_a_prompt_in_previous_section(
            self, make_stubbed_wizard_runner, basic_definition):
        app_runner = make_stubbed_wizard_runner(basic_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('val1\n')
            app_runner.feed_input('\n')
            app_runner.feed_input('second_section_val1\n')
            # At DONE step, hit back tab to select "Go back" button
            # and enter to select that button.
            app_runner.feed_input(Keys.BackTab, Keys.Enter)
            app_runner.feed_input(Keys.BackTab)
            # This is to remove the default answer of foo for prompt 2
            app_runner.feed_input(
                Keys.Backspace, Keys.Backspace, Keys.Backspace)
            app_runner.feed_input('override2\n')
            self.assert_app_values(
                app_runner.app, prompt1='val1', prompt2='override2',
                second_section_prompt='second_section_val1'
            )

    def test_prompts_are_not_visible_across_sections(
            self, make_stubbed_wizard_runner, basic_definition):
        app_runner = make_stubbed_wizard_runner(basic_definition)
        with app_runner.run_app_in_thread():
            self.assert_prompt_is_visible(app_runner.app, 'prompt1')
            self.assert_prompt_is_visible(app_runner.app, 'prompt2')
            self.assert_prompt_is_not_visible(
                app_runner.app, 'second_section_prompt')

            app_runner.feed_input('val1\n')
            app_runner.feed_input('val2\n')

            self.assert_prompt_is_not_visible(app_runner.app, 'prompt1')
            self.assert_prompt_is_not_visible(app_runner.app, 'prompt2')
            self.assert_prompt_is_visible(
                app_runner.app, 'second_section_prompt')

    def test_run_wizard_dialog_appears_only_at_end_of_wizard(
            self, make_stubbed_wizard_runner, basic_definition):
        app_runner = make_stubbed_wizard_runner(basic_definition)

        with app_runner.run_app_in_thread():
            self.assert_run_wizard_dialog_is_not_visible(app_runner.app)
            app_runner.feed_input('val1\n')
            self.assert_run_wizard_dialog_is_not_visible(app_runner.app)
            app_runner.feed_input('val2\n')
            self.assert_run_wizard_dialog_is_not_visible(app_runner.app)
            app_runner.feed_input('second_section_val1\n')
            self.assert_run_wizard_dialog_is_visible(app_runner.app)

    def test_enter_at_wizard_dialog_exits_app_with_zero_rc(
            self, make_stubbed_wizard_runner, basic_definition):
        app_runner = make_stubbed_wizard_runner(basic_definition)
        with app_runner.run_app_in_thread() as ctx:
            app_runner.feed_input('val1\n')
            app_runner.feed_input('val2\n')
            app_runner.feed_input('second_section_val1\n')
            self.assert_run_wizard_dialog_is_visible(app_runner.app)
            app_runner.feed_input(Keys.Enter)
        assert ctx.return_value == 0

    def test_can_go_back_from_run_wizard_dialog(
            self, make_stubbed_wizard_runner, basic_definition):
        app_runner = make_stubbed_wizard_runner(basic_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('val1\n')
            app_runner.feed_input('\n')
            app_runner.feed_input('second_section_val1\n')
            self.assert_run_wizard_dialog_is_visible(app_runner.app)
            app_runner.feed_input(Keys.Right, Keys.Enter)
            app_runner.feed_input('_override\n')
            self.assert_app_values(
                app_runner.app, prompt1='val1', prompt2='foo',
                second_section_prompt='second_section_val1_override'
            )

    def test_traverser_get_output(
            self, make_stubbed_wizard_runner, basic_definition):
        app_runner = make_stubbed_wizard_runner(basic_definition)
        assert app_runner.app.traverser.get_output() == 'output: some text'

    def test_can_exit_and_propagate_ctrl_c_from_wizard(
            self, make_stubbed_wizard_runner, basic_definition):
        app_runner = make_stubbed_wizard_runner(basic_definition)
        with app_runner.run_app_in_thread() as ctx:
            app_runner.feed_input(Keys.ControlC)
        assert isinstance(ctx.raised_exception, KeyboardInterrupt)

    def test_captures_unexpected_errors_when_processing_input(
            self, make_stubbed_wizard_runner, basic_definition):
        app_runner = make_stubbed_wizard_runner(basic_definition)
        unexpected_error = ValueError('Not expected')

        @app_runner.app.key_bindings.add('a')
        def trigger_unexpected_error(event):
            raise unexpected_error

        with app_runner.run_app_in_thread() as ctx:
            app_runner.feed_input('a')
        assert isinstance(ctx.raised_exception, UnexpectedWizardException)
        assert ctx.raised_exception.original_exception is unexpected_error

    def test_cant_open_save_panel_if_no_details_available(
            self, make_stubbed_wizard_runner, basic_definition):
        app_runner = make_stubbed_wizard_runner(basic_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.ControlS)
            assert 'save_details_dialogue' not in self.get_visible_buffers(
                app_runner.app)


class TestConditionalWizardApplication(BaseWizardApplicationTest):
    def test_conditional_prompt_is_skipped_when_condition_not_met(
            self, make_stubbed_wizard_runner, conditional_definition):
        app_runner = make_stubbed_wizard_runner(conditional_definition)
        with app_runner.run_app_in_thread():
            self.assert_prompt_is_not_visible(app_runner.app, 'conditional')
            app_runner.feed_input('condition-not-met\n')
            self.assert_prompt_is_not_visible(app_runner.app, 'conditional')
            app_runner.feed_input('after-conditional-val\n')
            self.assert_app_values(
                app_runner.app, before_conditional='condition-not-met',
                after_conditional='after-conditional-val',
            )

    def test_conditional_prompt_appears_when_condition_met(
            self, make_stubbed_wizard_runner, conditional_definition):
        app_runner = make_stubbed_wizard_runner(conditional_definition)
        with app_runner.run_app_in_thread():
            self.assert_prompt_is_not_visible(app_runner.app, 'conditional')
            app_runner.feed_input('condition-met\n')
            self.assert_prompt_is_visible(app_runner.app, 'conditional')
            app_runner.feed_input('val-at-conditional\n')
            self.assert_app_values(
                app_runner.app, before_conditional='condition-met',
                conditional='val-at-conditional',
            )


class TestChoicesWizardApplication(BaseWizardApplicationTest):
    def test_immediately_pressing_enter_selects_first_choice(
            self, make_stubbed_wizard_runner, choices_definition):
        app_runner = make_stubbed_wizard_runner(choices_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.Enter)
            self.assert_app_values(
                app_runner.app, choices_prompt='actual_option_1')

    def test_can_select_choice_in_prompt(
            self, make_stubbed_wizard_runner, choices_definition):
        app_runner = make_stubbed_wizard_runner(choices_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.Down, Keys.Enter)
            self.assert_app_values(
                app_runner.app, choices_prompt='actual_option_2')


class TestCorruptedChoicesWizardApplication(BaseWizardApplicationTest):
    def test_can_handle_corrupted_choices(
            self, make_stubbed_wizard_runner, corrupted_choice_definition):
        app_runner = make_stubbed_wizard_runner(corrupted_choice_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.Down, Keys.Enter)
            self.assert_app_values(
                app_runner.app, choices_prompt=None)

    def test_show_error_message_on_get_value_exception(
            self, make_stubbed_wizard_runner, corrupted_choice_definition):
        app_runner = make_stubbed_wizard_runner(corrupted_choice_definition)
        with app_runner.run_app_in_thread():
            self.assert_buffer_text(
                app_runner.app,
                'error_bar',
                'Encountered following error in wizard:\n\n\'operation\''
            )

    def test_toolbar_text_on_get_value_exception(
            self, make_stubbed_wizard_runner, corrupted_choice_definition):
        app_runner = make_stubbed_wizard_runner(corrupted_choice_definition)
        with app_runner.run_app_in_thread():
            self.assert_toolbar_has_text(app_runner.app, 'error message')


class TestMixedPromptTypeWizardApplication(BaseWizardApplicationTest):
    def test_can_answer_buffer_prompt_followed_by_select_prompt(
            self, make_stubbed_wizard_runner, mixed_prompt_definition):
        app_runner = make_stubbed_wizard_runner(mixed_prompt_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('buffer_answer\n')
            app_runner.feed_input(Keys.Enter)
            self.assert_app_values(
                app_runner.app, buffer_input_prompt='buffer_answer',
                select_prompt='select_answer_1'
            )


class TestPromptWithDataConvertWizardApplication(BaseWizardApplicationTest):
    def test_can_convert_integers(
            self, make_stubbed_wizard_runner, data_convert_definition):
        app_runner = make_stubbed_wizard_runner(data_convert_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('100\n')
            self.assert_app_values(app_runner.app, buffer_input_int=100)

    def test_can_convert_bool(
            self, make_stubbed_wizard_runner, data_convert_definition):
        app_runner = make_stubbed_wizard_runner(data_convert_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('0\n')
            app_runner.feed_input('true\n')
            self.assert_app_values(
                app_runner.app, buffer_input_int=0, buffer_input_bool=True
            )

    def test_show_error_and_stop_on_incorrect_input(
            self, make_stubbed_wizard_runner, data_convert_definition):
        app_runner = make_stubbed_wizard_runner(data_convert_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('foo\n')
            self.assert_buffer_text(
                app_runner.app,
                'error_bar',
                'Encountered following error in wizard:\n\n'
                'Invalid value foo for datatype int'
            )
            self.assert_current_buffer(app_runner.app, 'buffer_input_int')

    def test_clear_error_and_go_on_after_correction(
            self, make_stubbed_wizard_runner, data_convert_definition):
        app_runner = make_stubbed_wizard_runner(data_convert_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('foo\n')
            self.assert_buffer_text(
                app_runner.app,
                'error_bar',
                'Encountered following error in wizard:\n\n'
                'Invalid value foo for datatype int'
            )
            self.assert_current_buffer(app_runner.app, 'buffer_input_int')
            app_runner.feed_input(
                Keys.Backspace, Keys.Backspace, Keys.Backspace)
            app_runner.feed_input('100\n')
            self.assert_buffer_text(
                app_runner.app, 'error_bar', ''
            )
            self.assert_current_buffer(app_runner.app, 'buffer_input_bool')


class TestApiCallWizardApplication(BaseWizardApplicationTest):
    def test_uses_choices_from_api_call(
            self, make_stubbed_wizard_runner, api_call_definition,
            mock_iam_client):
        app_runner = make_stubbed_wizard_runner(api_call_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.Enter)
            self.assert_app_values(app_runner.app, choose_policy='policy1_arn')


class TestDetailsWizardApplication(BaseWizardApplicationTest):
    def test_get_details_for_choice(
            self, make_stubbed_wizard_runner, details_definition,
            mock_iam_client):
        app_runner = make_stubbed_wizard_runner(details_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.F3)
            self.assert_buffer_text(
                app_runner.app,
                'details_buffer',
                '{\n    "policy": "policy_document"\n}'
            )

    def test_details_disabled_for_choice_wo_details(
            self, make_stubbed_wizard_runner, details_definition,
            mock_iam_client):
        app_runner = make_stubbed_wizard_runner(details_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.Tab)
            self.assert_prompt_is_not_visible(
                app_runner.app, 'toolbar_details')
            app_runner.feed_input(Keys.F3)
            self.assert_prompt_is_not_visible(app_runner.app, 'details_buffer')

    def test_can_switch_focus_to_details_panel(
            self, make_stubbed_wizard_runner, details_definition,
            mock_iam_client):
        app_runner = make_stubbed_wizard_runner(details_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.F3)
            app_runner.feed_input(Keys.F2)
            self.assert_current_buffer(app_runner.app, 'details_buffer')
            app_runner.feed_input(Keys.F3)
            assert app_runner.app.layout.current_buffer is None

    def test_can_toggle_save_panel(
            self, make_stubbed_wizard_runner, details_definition,
            mock_iam_client):
        app_runner = make_stubbed_wizard_runner(details_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.ControlS)
            self.assert_current_buffer(app_runner.app, 'save_details_dialogue')
            self.assert_prompt_is_visible(
                app_runner.app, 'save_details_dialogue')
            assert app_runner.app.details_visible
            assert app_runner.app.save_details_visible

    def test_can_not_switch_focus_to_details_panel_if_it_not_visible(
            self, make_stubbed_wizard_runner, details_definition,
            mock_iam_client):
        app_runner = make_stubbed_wizard_runner(details_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.F2)
            assert app_runner.app.layout.current_buffer is None

    def test_can_set_details_panel_title(
            self, make_stubbed_wizard_runner, details_definition,
            mock_iam_client):
        app_runner = make_stubbed_wizard_runner(details_definition)
        with app_runner.run_app_in_thread():
            assert app_runner.app.details_title == 'Policy Document'
            app_runner.feed_input(Keys.F3)
            assert app_runner.app.details_title == 'Policy Document'

    def test_can_set_details_toolbar_text(
            self, make_stubbed_wizard_runner, details_definition,
            mock_iam_client):
        app_runner = make_stubbed_wizard_runner(details_definition)
        with app_runner.run_app_in_thread():
            self.assert_toolbar_has_text(app_runner.app, 'Policy Document')


class TestPreviewWizardApplication(BaseWizardApplicationTest):
    def test_details_panel_visible_by_default(
            self, make_stubbed_wizard_runner, preview_definition):
        app_runner = make_stubbed_wizard_runner(preview_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.Tab)
            self.assert_prompt_is_visible(app_runner.app, 'details_buffer')

    def test_get_details_for_choice(
            self, make_stubbed_wizard_runner, preview_definition):
        app_runner = make_stubbed_wizard_runner(preview_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.Tab)
            self.assert_buffer_text(
                app_runner.app,
                'details_buffer',
                'First option details'
            )

    def test_get_details_for_second_choice(
            self, make_stubbed_wizard_runner, preview_definition):
        app_runner = make_stubbed_wizard_runner(preview_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.Tab)
            app_runner.feed_input(Keys.Down)
            self.assert_buffer_text(
                app_runner.app,
                'details_buffer',
                'Second option details'
            )


class TestSharedConfigWizardApplication(BaseWizardApplicationTest):
    def test_uses_choices_from_api_call(
            self, make_stubbed_wizard_runner, shared_config_definition,
            mock_botocore_session):
        mock_botocore_session.available_profiles = ['profile1', 'profile2']
        app_runner = make_stubbed_wizard_runner(shared_config_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.Enter)
            self.assert_app_values(app_runner.app, choose_profile='profile1')


class TestRunWizardApplication(BaseWizardApplicationTest):
    def assert_error_bar_is_visible(self, app):
        assert 'error_bar' in self.get_visible_buffers(app)

    def assert_error_bar_is_not_visible(self, app):
        assert 'error_bar' not in self.get_visible_buffers(app)

    def test_run_wizard_execute(
            self, make_stubbed_wizard_runner, run_wizard_definition,
            mock_iam_client):
        app_runner = make_stubbed_wizard_runner(run_wizard_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('role-name\n')
            app_runner.feed_input(Keys.Enter)
        mock_iam_client.create_role.assert_called_with(RoleName='role-name')
        assert app_runner.app.values['role_arn'] == 'returned-role-arn'

    def test_run_wizard_captures_and_displays_errors(
            self, make_stubbed_wizard_runner, run_wizard_definition,
            mock_iam_client):
        app_runner = make_stubbed_wizard_runner(run_wizard_definition)
        mock_iam_client.create_role.side_effect = Exception(
            'Error creating role')
        with app_runner.run_app_in_thread():
            app_runner.feed_input('role-name\n')
            app_runner.feed_input(Keys.Enter)
            self.assert_buffer_text(
                app_runner.app,
                'error_bar',
                'Encountered following error in wizard:\n\nError creating role'
            )

    def test_can_change_answers_on_run_wizard_failure(
            self, make_stubbed_wizard_runner, run_wizard_definition,
            mock_iam_client):
        app_runner = make_stubbed_wizard_runner(run_wizard_definition)
        mock_iam_client.create_role.side_effect = [
            Exception('Initial error'),
            mock_iam_client.create_role.return_value,
        ]
        with app_runner.run_app_in_thread():
            app_runner.feed_input('role-name\n')
            self.assert_error_bar_is_not_visible(app_runner.app)
            self.assert_run_wizard_dialog_is_visible(app_runner.app)
            app_runner.feed_input(Keys.Enter)
            self.assert_buffer_text(
                app_runner.app,
                'error_bar',
                'Encountered following error in wizard:\n\nInitial error'
            )

            # Make sure dialog closed on error but error message is visible
            self.assert_run_wizard_dialog_is_not_visible(app_runner.app)
            self.assert_error_bar_is_visible(app_runner.app)
            app_runner.feed_input('-new\n')

            # Enter "Yes" to the done dialog again
            app_runner.feed_input(Keys.Enter)

        mock_iam_client.create_role.assert_called_with(
            RoleName='role-name-new')
        assert app_runner.app.values['role_arn'] == 'returned-role-arn'

    def test_can_switch_exception_panel(
            self, make_stubbed_wizard_runner, run_wizard_definition,
            mock_iam_client):
        app_runner = make_stubbed_wizard_runner(run_wizard_definition)
        mock_iam_client.create_role.side_effect = [
            Exception('Initial error'),
            mock_iam_client.create_role.return_value,
        ]
        with app_runner.run_app_in_thread():
            app_runner.feed_input('role-name\n')
            self.assert_error_bar_is_not_visible(app_runner.app)
            app_runner.feed_input(Keys.Enter)
            self.assert_error_bar_is_visible(app_runner.app)
            app_runner.feed_input(Keys.F4)
            self.assert_error_bar_is_not_visible(app_runner.app)

    def test_toolbar_has_exception_panel_hot_key(
            self, make_stubbed_wizard_runner, run_wizard_definition,
            mock_iam_client):
        app_runner = make_stubbed_wizard_runner(run_wizard_definition)
        mock_iam_client.create_role.side_effect = [
            Exception('Initial error'),
            mock_iam_client.create_role.return_value,
        ]
        with app_runner.run_app_in_thread():
            app_runner.feed_input('role-name\n')
            self.assert_error_bar_is_not_visible(app_runner.app)
            self.assert_toolbar_does_not_have_text(
                app_runner.app, 'error message')
            app_runner.feed_input(Keys.Enter)
            self.assert_error_bar_is_visible(app_runner.app)
            self.assert_toolbar_has_text(
                app_runner.app, 'error message')


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


class TestPromptCompletionWizardApplication(BaseWizardApplicationTest):
    def test_show_completions_for_buffer_text(
            self, make_stubbed_wizard_runner, file_prompt_definition,
            patch_path_completer):
        app_runner = make_stubbed_wizard_runner(file_prompt_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('fi')
            self.assert_expected_buffer_completions(
                app_runner.app,
                'choose_file',
                [
                    Completion('le1', 0, display='file1'),
                    Completion('le2', 0, display='file2'),
                ]
            )

    def test_choose_completion_on_Enter_and_stays_on_the_same_prompt(
            self, make_stubbed_wizard_runner, file_prompt_definition,
            patch_path_completer):
        app_runner = make_stubbed_wizard_runner(file_prompt_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('fi')
            app_runner.feed_input(Keys.Down, Keys.Enter)
            self.assert_buffer_text(app_runner.app, 'choose_file', 'file1')
            self.assert_current_buffer(app_runner.app, 'choose_file')

    def test_choose_completion_on_Enter_and_move_on_second_Enter(
            self, make_stubbed_wizard_runner, file_prompt_definition,
            patch_path_completer):
        app_runner = make_stubbed_wizard_runner(file_prompt_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('fi')
            app_runner.feed_input(Keys.Down, Keys.Enter)
            app_runner.feed_input(Keys.Enter)
            self.assert_current_buffer(app_runner.app, 'second_prompt')

    def test_switch_completions_on_tab(
            self, make_stubbed_wizard_runner, file_prompt_definition,
            patch_path_completer):
        app_runner = make_stubbed_wizard_runner(file_prompt_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('fi')
            app_runner.feed_input(Keys.Tab, Keys.Tab, Keys.Enter)
            self.assert_buffer_text(app_runner.app, 'choose_file', 'file2')
            self.assert_current_buffer(app_runner.app, 'choose_file')

    def test_switch_completions_on_back_tab(
            self, make_stubbed_wizard_runner, file_prompt_definition,
            patch_path_completer):
        app_runner = make_stubbed_wizard_runner(file_prompt_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('fi')
            app_runner.feed_input(Keys.Tab, Keys.Tab, Keys.BackTab, Keys.Enter)
            self.assert_buffer_text(app_runner.app, 'choose_file', 'file1')
            self.assert_current_buffer(app_runner.app, 'choose_file')

    def test_switch_prompt_on_tab_if_it_is_not_completing(
            self, make_stubbed_wizard_runner, file_prompt_definition,
            patch_path_completer):
        app_runner = make_stubbed_wizard_runner(file_prompt_definition)
        with app_runner.run_app_in_thread():
            app_runner.feed_input('rrrr')
            app_runner.feed_input(Keys.Tab)
            self.assert_current_buffer(app_runner.app, 'second_prompt')


class TestSaveDetailsWizard(BaseWizardApplicationTest):
    def test_file_saved_to_disk(self, make_stubbed_wizard_runner):
        definition = {
            'title': 'Show details in prompting stage',
            'plan': {
                'section': {
                    'shortname': 'Section',
                    'values': {
                        'policy_arn': {
                            'description': 'Choose policy',
                            'type': 'prompt',
                            'choices': ['a'],
                            'details': {
                                'value': 'test_value',
                                'description': 'Policy Document',
                                'output': 'json'
                            },
                        },
                    }
                },
                '__DONE__': {},
            },
            'execute': {}
        }
        app_runner = make_stubbed_wizard_runner(definition)
        mock_file_io = mock.Mock(spec=FileIO)
        app_runner.app.file_io = mock_file_io
        app_runner.app.values['test_value'] = {'foo': 'bar'}
        details_content = '{\n    "foo": "bar"\n}'
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.F3)
            self.assert_buffer_text(
                app_runner.app,
                'details_buffer',
                details_content
            )
            app_runner.feed_input(Keys.ControlS)
            app_runner.feed_input('/tmp/myfile.json\n')
            mock_file_io.write_file_contents.assert_called_with(
                '/tmp/myfile.json', details_content)
