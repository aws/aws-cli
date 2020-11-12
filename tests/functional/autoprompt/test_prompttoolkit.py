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
import json
import io
import os

from prompt_toolkit import Application
from prompt_toolkit.key_binding.key_processor import KeyPress
from prompt_toolkit.input import DummyInput

from prompt_toolkit.keys import Keys
from prompt_toolkit.utils import Event

from awscli.autocomplete.main import create_autocompleter
from awscli.autocomplete import generator, filters, parser
from awscli.autocomplete.local import indexer, model
from awscli.clidriver import create_clidriver
from awscli.autoprompt.factory import PromptToolkitFactory
from awscli.autoprompt.prompttoolkit import (
    PromptToolkitCompleter, PromptToolkitPrompter
)
from awscli.autoprompt.history import HistoryDriver
from awscli.testutils import unittest, random_chars, FileCreator, cd


def _ec2_only_command_table(command_table, **kwargs):
    for key in list(command_table):
        if key != 'ec2':
            del command_table[key]


def _generate_index(filename):
    # This will eventually be moved into some utility function.
    index_generator = generator.IndexGenerator(
        [indexer.create_model_indexer(filename)],
    )
    driver = create_clidriver()
    driver.session.register('building-command-table.main',
                            _ec2_only_command_table)
    index_generator.generate_index(driver)


class FakeApplication:
    debug = False

    def run(self, pre_run):
        pre_run()


class FakeInput(DummyInput):

    def fileno(self):
        return 0

    @property
    def closed(self):
        return False


class ApplicationStubber:
    _KEYPRESS = 'KEYPRESS'
    _ASSERTION = 'ASSERTION'

    def __init__(self, app):
        self._app = app
        self._app.input = FakeInput()
        self._queue = []

    def add_keypress_with_assertion(self, key, assertion):
        self.add_keypress_action(key)
        self.add_assertion_action(assertion, key)

    def add_keypress_action(self, key):
        self._queue.append((self._KEYPRESS, key))

    def add_assertion_action(self, assertion, key=None):
        self._queue.append((self._ASSERTION, assertion, key))

    def run(self, pre_run=None):
        key_processor = self._app.key_processor
        # After each rendering application will run this callback
        # it takes the next action from the queue and performs it
        # some key_presses can lead to rerender, after which this callback
        # will be run again before re-rendering app.invalidated property
        # set to True.
        # On exit this callback also run so we need to remove it before exit

        def callback(app):
            while self._queue and not app.invalidated:
                action = self._queue.pop(0)
                if action[0] == self._KEYPRESS:
                    key_processor.feed(KeyPress(action[1], ''))
                    key_processor.process_keys()
                if action[0] == self._ASSERTION:
                    if not action[1](app):
                        app.after_render = Event(app, None)
                        app.exit(
                            exception=AssertionError(f'Incorrect action on key '
                                                     f'press "{action[2]}"'))
                        return
            if not self._queue:
                app.after_render = Event(app, None)
                app.exit()

        self._app.after_render = Event(self._app, callback)

        _stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        self._app.output.stdout = _stdout
        self._app.run(pre_run=pre_run)


class BasicPromptToolkitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_file_creator = FileCreator()
        basename = 'tmpfile-%s' % str(random_chars(8))
        index_filename = cls.test_file_creator.full_path(basename)
        _generate_index(index_filename)
        cls.cli_parser = parser.CLIParser(model.ModelIndex(index_filename))
        cls.completion_source = create_autocompleter(
            index_filename, response_filter=filters.fuzzy_filter)

        history = {
            'version': 1,
            'commands': [
                'accessanalyzer update-findings',
                'ec2 describe-instances',
                's3 ls'
            ]
        }
        cls.history_filename = cls.test_file_creator.create_file(
            'prompt_history.json', json.dumps(history))

    @classmethod
    def tearDownClass(cls):
        cls.test_file_creator.remove_all()

    def setUp(self):
        self.completer = PromptToolkitCompleter(self.completion_source)
        self.history_driver = HistoryDriver(self.history_filename)
        self.driver = create_clidriver()
        self.factory = PromptToolkitFactory(
            self.completer,
            history_driver=self.history_driver
        )
        self.prompter = PromptToolkitPrompter(
            completion_source=self.completion_source,
            driver=self.driver,
            factory=self.factory,
            cli_parser=self.cli_parser
        )
        self.prompter.args = []
        self.prompter.input_buffer = self.factory.create_input_buffer()
        self.prompter.doc_buffer = self.factory.create_doc_buffer()
        self.prompter.output_buffer = self.factory.create_output_buffer()

    def create_application(self):
        layout = self.factory.create_layout()
        return Application(layout=layout)

    def get_current_buffer_assertion(self, buffer_name):
        return lambda app: app.current_buffer.name == buffer_name

    def get_buffer_is_visible_assertion(self, buffer_name):
        return lambda app: buffer_name in [window.content.buffer.name
                    for window in app.layout.get_visible_focusable_windows()]

    def get_buffer_not_visible_assertion(self, buffer_name):
        return lambda app: buffer_name not in [window.content.buffer.name
                    for window in app.layout.get_visible_focusable_windows()]


class TestPromptToolkitPrompterBuffer(BasicPromptToolkitTest):
    """This set of tests tests that we set the buffer (aka "construction zone")
    correctly. Some of these tests test against specific edge cases that have
    previously been known to produce unexpected behavior.

    """

    def get_updated_input_buffer_text(self, original_args):
        self.prompter.args = original_args
        self.prompter.pre_run()
        return self.prompter.input_buffer.document.text

    def test_preserve_buffer_text_if_invalid_command_entered(self):
        original_args = ['ec2', 'fake']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, 'ec2 fake')

    def test_dont_reset_buffer_text_if_complete_command_entered(self):
        original_args = ['ec2']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, 'ec2 ')

    def test_dont_reset_buffer_text_if_file_path_entered(self):
        original_args = ['s3', 'mv', '/path/to/file/1', 's3://path/to/file/2']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, 's3 mv /path/to/file/1 s3://path/to/file/2 ')

    def test_add_trailing_space_if_s3_ls_entered(self):
        original_args = ['s3', 'ls']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, 's3 ls ')

    def test_dont_add_trailing_space_if_incomplete_command(self):
        original_args = ['ec2', 'desc']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, 'ec2 desc')

    def test_dont_reset_buffer_text_if_s3_ls_space_entered(self):
        original_args = ['s3', 'ls ']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, 's3 ls ')

    def test_preserve_buffer_text_if_invalid_command_with_option_entered(self):
        original_args = ['ec2', 'fake', '--output']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, 'ec2 fake --output ')

    def test_add_trailing_space_if_valid_command_with_option_entered(self):
        original_args = ['ec2', 'describe-instances', '--output']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, 'ec2 describe-instances --output ')

    def test_reset_buffer_text_if_empty_aws_command_entered(self):
        original_args = [' ']
        buffer_text = self.get_updated_input_buffer_text(original_args)
        self.assertEqual(buffer_text, ' ')

    def test_handle_args_with_spaces(self):
        original_args = ['iam', 'create-role', '--description', 'With spaces']
        prompter = PromptToolkitPrompter(
            completion_source=self.completion_source, driver=self.driver,
            app=FakeApplication(), cli_parser=self.cli_parser)
        prompter.input_buffer = self.factory.create_input_buffer()
        prompter.doc_buffer = self.factory.create_doc_buffer()
        prompter.output_buffer = self.factory.create_output_buffer()
        args = prompter.prompt_for_args(original_args)
        self.assertEqual(prompter.input_buffer.document.text,
                         "iam create-role --description 'With spaces' ")
        self.assertEqual(args, original_args)


class TestPromptToolkitDocBuffer(BasicPromptToolkitTest):
    def get_updated_doc_buffer_text(self, original_args):
        self.prompter.args = original_args
        self.prompter.pre_run()
        return self.prompter.doc_buffer.document.text

    def test_doc_buffer_not_shown_on_start_and_not_focusable(self):
        stubber = ApplicationStubber(self.prompter.create_application())
        stubber.add_assertion_action(lambda app: app.show_doc is False)
        stubber.add_keypress_with_assertion(
            Keys.F1, self.get_current_buffer_assertion('input_buffer')
        )
        stubber.run(self.prompter.pre_run)

    def test_doc_buffer_shows_hides_on_F3(self):
        stubber = ApplicationStubber(self.prompter.create_application())
        stubber.add_keypress_with_assertion(Keys.F3, lambda app: app.show_doc is True)
        stubber.add_keypress_with_assertion(
            Keys.F3, self.get_current_buffer_assertion('input_buffer')
        )
        stubber.run(self.prompter.pre_run)

    def test_doc_buffer_gets_and_removes_focus(self):
        stubber = ApplicationStubber(self.prompter.create_application())
        stubber.add_keypress_with_assertion(Keys.F3, lambda app: app.show_doc is True)
        stubber.add_keypress_with_assertion(
            Keys.F2,
            lambda app: self.get_current_buffer_assertion('doc_buffer')
        )
        stubber.add_keypress_with_assertion(
            'q',
            lambda app: self.get_current_buffer_assertion('input_buffer')
        )
        stubber.run(self.prompter.pre_run)

    def test_doc_buffer_keeps_position_if_content_dont_change(self):
        original_args = ['ec2', 'describe-instances']
        self.prompter.args = original_args
        stubber = ApplicationStubber(self.prompter.create_application())
        stubber.add_keypress_action(Keys.F3)
        stubber.add_keypress_action(Keys.F2)
        # go to the top row
        stubber.add_keypress_with_assertion('g', lambda app: app.layout.get_buffer_by_name(
                    'doc_buffer').document.cursor_position_row == 0)
        # go three rows down
        stubber.add_keypress_action('j')
        stubber.add_keypress_action('j')
        stubber.add_keypress_with_assertion('j', lambda app: app.layout.get_buffer_by_name(
                    'doc_buffer').document.cursor_position_row == 3)
        # get back to input
        stubber.add_keypress_action('q')
        # go on enter the rest of the command and  check that cursor in doc
        # panel remains on the same place
        for k in ' --instances':
            stubber.add_keypress_with_assertion(k, lambda app:  app.layout.get_buffer_by_name(
                    'doc_buffer').document.cursor_position_row == 3)
        stubber.run(self.prompter.pre_run)

    def test_show_general_help_on_empty_input(self):
        original_args = [' ']
        buffer_text = self.get_updated_doc_buffer_text(original_args)
        self.assertIn('AWS Command Line Interface', buffer_text)

    def test_show_general_help_on_incorrect_command(self):
        original_args = ['fake']
        buffer_text = self.get_updated_doc_buffer_text(original_args)
        self.assertIn('AWS Command Line Interface', buffer_text)

    def test_show_command_help_on_command_without_subcommand(self):
        original_args = ['ec2']
        buffer_text = self.get_updated_doc_buffer_text(original_args)
        self.assertIn('Elastic Compute Cloud', buffer_text)

    def test_show_command_help_on_command_with_incorrect_subcommand(self):
        original_args = ['ec2', 'fake']
        buffer_text = self.get_updated_doc_buffer_text(original_args)
        self.assertIn('Elastic Compute Cloud', buffer_text)

    def test_show_subcommand_help_on_command_with_subcommand(self):
        original_args = ['ec2', 'describe-instances']
        buffer_text = self.get_updated_doc_buffer_text(original_args)
        self.assertIn('Describes the specified', buffer_text)

    def test_show_subcommand_help_on_command_with_subcommand_and_option(self):
        original_args = ['ec2', 'describe-instances', '--instance-ids']
        buffer_text = self.get_updated_doc_buffer_text(original_args)
        self.assertIn('Describes the specified', buffer_text)


class TestHistoryMode(BasicPromptToolkitTest):
    def test_history_mode_disabled_on_start_and_switched_by_control_R(self):
        stubber = ApplicationStubber(self.prompter.create_application())
        stubber.add_assertion_action(
            lambda app: not app.current_buffer.history_mode)
        stubber.add_keypress_with_assertion(
            Keys.ControlR, lambda app: app.current_buffer.history_mode)
        stubber.add_keypress_with_assertion(
            Keys.ControlR, lambda app: not app.current_buffer.history_mode
        )
        stubber.run(self.prompter.pre_run)

    def test_choose_and_disable_history_mode_with_enter(self):
        self.prompter.args = ['s']
        stubber = ApplicationStubber(self.prompter.create_application())
        stubber.add_assertion_action(
            lambda app: not app.current_buffer.history_mode)
        stubber.add_keypress_with_assertion(
            Keys.ControlR, lambda app: app.current_buffer.history_mode)
        # for some reason in this mode first click down chooses the original
        # input and only the second one gets to the completions
        stubber.add_keypress_action(Keys.Down)
        stubber.add_keypress_with_assertion(
            Keys.Down, lambda app:
            app.current_buffer.complete_state.current_completion.text == 's3 ls'
        )
        stubber.add_keypress_with_assertion(
            Keys.Enter, lambda app:
            not app.current_buffer.history_mode and
            app.current_buffer.name == 'input_buffer' and
            app.current_buffer.document.text == 's3 ls'
        )
        stubber.run(self.prompter.pre_run)

    def test_choose_and_disable_history_mode_with_space(self):
        self.prompter.args = ['s']
        stubber = ApplicationStubber(self.prompter.create_application())
        stubber.add_assertion_action(
            lambda app: not app.current_buffer.history_mode)
        stubber.add_keypress_with_assertion(
            Keys.ControlR, lambda app: app.current_buffer.history_mode)
        # for some reason in this mode first click down chooses the original
        # input and only the second one gets to the completions
        stubber.add_keypress_action(Keys.Down)
        stubber.add_keypress_with_assertion(
            Keys.Down, lambda app:
            app.current_buffer.complete_state.current_completion.text == 's3 ls'
        )
        stubber.add_keypress_with_assertion(
            ' ', lambda app:
            not app.current_buffer.history_mode and
            app.current_buffer.name == 'input_buffer' and
            app.current_buffer.document.text == 's3 ls '
        )
        stubber.run(self.prompter.pre_run)


class TestCompletions(BasicPromptToolkitTest):
    def test_service_full_name_shown(self):
        self.prompter.args = ['e']
        stubber = ApplicationStubber(self.prompter.create_application())
        stubber.add_assertion_action(
            lambda app: 'Elastic Compute' in
            app.current_buffer.complete_state.completions[0].display_meta_text)
        stubber.run(self.prompter.pre_run)

    def test_switch_to_multicolumn_mode(self):
        self.prompter.args = ['ec2 d']
        stubber = ApplicationStubber(self.prompter.create_application())
        stubber.add_keypress_with_assertion(Keys.F4, lambda app: app.multi_column)
        stubber.add_keypress_with_assertion(Keys.F4, lambda app: not app.multi_column)
        stubber.run(self.prompter.pre_run)


class TestHelpPanel(BasicPromptToolkitTest):
    def test_help_panel_disabled_on_start_and_appear_on_F1(self):
        stubber = ApplicationStubber(self.prompter.create_application())
        stubber.add_assertion_action(lambda app: app.show_help is False)
        stubber.add_keypress_with_assertion(Keys.F1, lambda app: app.show_help is True)
        stubber.add_keypress_with_assertion(Keys.F1, lambda app: app.show_help is False)
        stubber.run(self.prompter.pre_run)

    def test_show_correct_help_panel(self):
        stubber = ApplicationStubber(self.prompter.create_application())
        stubber.add_keypress_with_assertion(
            Keys.F1, self.get_buffer_is_visible_assertion('help_input'))
        stubber.add_assertion_action(
            self.get_buffer_not_visible_assertion('help_doc'))
        stubber.add_keypress_action(Keys.F3)
        stubber.add_keypress_with_assertion(
            Keys.F2, self.get_buffer_is_visible_assertion('help_doc'))
        stubber.add_assertion_action(
            self.get_buffer_not_visible_assertion('help_input'))
        stubber.run(self.prompter.pre_run)

    def test_toolbar_hides_when_help_panel_visible(self):
        stubber = ApplicationStubber(self.prompter.create_application())
        stubber.add_assertion_action(
            self.get_buffer_is_visible_assertion('toolbar_input'))
        stubber.add_keypress_with_assertion(
            Keys.F1, self.get_buffer_not_visible_assertion('toolbar_input'))
        stubber.add_assertion_action(
            self.get_buffer_not_visible_assertion('toolbar_doc'))
        stubber.run(self.prompter.pre_run)


class TestDebugPanel(BasicPromptToolkitTest):
    def test_debug_panel_not_visible_in_non_debug_mode(self):
        stubber = ApplicationStubber(self.prompter.create_application())
        stubber.add_assertion_action(
            self.get_buffer_not_visible_assertion('debug_buffer'))
        stubber.run(self.prompter.pre_run)

    def test_debug_panel_visible_in_debug_mode(self):
        app = self.prompter.create_application()
        app.debug = True
        stubber = ApplicationStubber(app)
        stubber.add_assertion_action(
            self.get_buffer_is_visible_assertion('debug_buffer'))
        stubber.run(self.prompter.pre_run)

    def test_open_save_dialog_on_control_s(self):
        app = self.prompter.create_application()
        app.debug = True
        stubber = ApplicationStubber(app)
        stubber.add_keypress_with_assertion(
            Keys.ControlS,
            lambda app: app.current_buffer.text == 'prompt_debug.log'
        )
        stubber.run(self.prompter.pre_run)

    def test_can_save_log_file(self):
        app = self.prompter.create_application()
        app.debug = True
        stubber = ApplicationStubber(app)
        stubber.add_keypress_action(Keys.ControlS)
        stubber.add_keypress_action(Keys.Enter)
        log_file_path = self.test_file_creator.full_path('prompt_debug.log')
        with cd(self.test_file_creator.rootdir):
            stubber.run(self.prompter.pre_run)
            self.assertTrue(os.path.exists(log_file_path))

    def test_can_switch_focus_between_panels(self):
        app = self.prompter.create_application()
        app.debug = True
        stubber = ApplicationStubber(app)
        stubber.add_assertion_action(
            self.get_current_buffer_assertion('input_buffer')
        )
        stubber.add_keypress_with_assertion(
            Keys.F2,
            self.get_current_buffer_assertion('debug_buffer')
        )
        stubber.add_keypress_with_assertion(
            Keys.F2,
            self.get_current_buffer_assertion('input_buffer')
        )
        stubber.run(self.prompter.pre_run)


class TestOutputPanel(BasicPromptToolkitTest):
    def test_output_panel_not_visible_on_start(self):
        stubber = ApplicationStubber(self.prompter.create_application())
        stubber.add_assertion_action(
            self.get_buffer_not_visible_assertion('output_buffer'))
        stubber.run(self.prompter.pre_run)

    def test_output_panel_switches_on_F5(self):
        app = self.prompter.create_application()
        stubber = ApplicationStubber(app)
        stubber.add_keypress_with_assertion(
            Keys.F5,
            self.get_buffer_is_visible_assertion('output_buffer'))
        stubber.add_keypress_with_assertion(
            Keys.F5,
            self.get_buffer_not_visible_assertion('output_buffer'))
        stubber.run(self.prompter.pre_run)

    def test_output_panel_and_doc_panel_can_be_visible_together(self):
        app = self.prompter.create_application()
        stubber = ApplicationStubber(app)
        stubber.add_keypress_with_assertion(
            Keys.F5,
            self.get_buffer_is_visible_assertion('output_buffer'))
        stubber.add_assertion_action(
            self.get_buffer_not_visible_assertion('doc_buffer')
        )
        stubber.add_keypress_with_assertion(
            Keys.F3,
            self.get_buffer_is_visible_assertion('doc_buffer'))
        stubber.add_assertion_action(
            self.get_buffer_is_visible_assertion('doc_buffer')
        )
        stubber.run(self.prompter.pre_run)

    def test_can_switch_focus_between_panels(self):
        app = self.prompter.create_application()
        stubber = ApplicationStubber(app)
        stubber.add_keypress_action(Keys.F5)
        stubber.add_keypress_action(Keys.F3)
        stubber.add_assertion_action(
            self.get_current_buffer_assertion('input_buffer')
        )
        stubber.add_keypress_with_assertion(
            Keys.F2,
            self.get_current_buffer_assertion('doc_buffer')
        )
        stubber.add_keypress_with_assertion(
            Keys.F2,
            self.get_current_buffer_assertion('output_buffer')
        )
        stubber.add_keypress_with_assertion(
            Keys.F2,
            self.get_current_buffer_assertion('input_buffer')
        )
        stubber.run(self.prompter.pre_run)

    def test_can_quit_output_panel(self):
        app = self.prompter.create_application()
        stubber = ApplicationStubber(app)
        stubber.add_keypress_action(Keys.F5)
        stubber.add_keypress_with_assertion(
            Keys.F2,
            self.get_current_buffer_assertion('output_buffer')
        )
        stubber.add_keypress_with_assertion(
            'q',
            self.get_current_buffer_assertion('input_buffer')
        )
        stubber.run(self.prompter.pre_run)

    def test_return_focus_on_input_buffer(self):
        app = self.prompter.create_application()
        stubber = ApplicationStubber(app)
        stubber.add_keypress_action(Keys.F5)
        stubber.add_keypress_with_assertion(
            Keys.F2,
            self.get_current_buffer_assertion('output_buffer')
        )
        stubber.add_keypress_with_assertion(
            Keys.F5,
            self.get_current_buffer_assertion('input_buffer')
        )
        stubber.run(self.prompter.pre_run)
