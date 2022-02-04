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
import os

import awscrt.io
import pytest
from prompt_toolkit.keys import Keys

from awscli.autocomplete.main import create_autocompleter
from awscli.autocomplete import generator, filters, parser, db
from awscli.autocomplete.local import indexer, model
from awscli.clidriver import create_clidriver
from awscli.autoprompt.factory import PromptToolkitFactory
from awscli.autoprompt.prompttoolkit import (
    PromptToolkitCompleter, PromptToolkitPrompter
)
from awscli.autoprompt.history import HistoryDriver
from awscli.testutils import mock, FileCreator, cd
from tests import ThreadedAppRunner


def _ec2_only_command_table(command_table, **kwargs):
    for key in list(command_table):
        if key != 'ec2':
            del command_table[key]


def _generate_index_if_needed(db_connection):
    if not _index_has_been_generated(db_connection):
        # This will eventually be moved into some utility function.
        index_generator = generator.IndexGenerator(
            [indexer.ModelIndexer(db_connection)],
        )
        driver = create_clidriver()
        driver.session.register('building-command-table.main',
                                _ec2_only_command_table)
        index_generator.generate_index(driver)


def _index_has_been_generated(db_connection):
    result = db_connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='command_table';"
    )
    return any(result.fetchall())


@pytest.fixture()
def files():
    files = FileCreator()
    yield files
    files.remove_all()


@pytest.fixture(scope='module')
def model_index():
    index_filename = 'file::memory:?cache=shared'
    db_connection = db.DatabaseConnection(index_filename)
    _generate_index_if_needed(db_connection)
    yield index_filename
    db_connection.close()


@pytest.fixture
def history_file(files):
    history = {
        'version': 1,
        'commands': [
            'accessanalyzer update-findings',
            'ec2 describe-instances',
            's3 ls'
        ]
    }
    return files.create_file(
        'prompt_history.json', json.dumps(history))


@pytest.fixture
def prompter(model_index, history_file, ptk_app_session):
    cli_parser = parser.CLIParser(model.ModelIndex(model_index))
    completion_source = create_autocompleter(
        model_index, response_filter=filters.fuzzy_filter)
    completer = PromptToolkitCompleter(completion_source)
    history_driver = HistoryDriver(history_file)
    driver = create_clidriver()
    factory = PromptToolkitFactory(completer, history_driver=history_driver)
    return PromptToolkitPrompter(
        completion_source=completion_source,
        driver=driver,
        factory=factory,
        cli_parser=cli_parser,
        output=ptk_app_session.output,
        app_input=ptk_app_session.input,
    )


@pytest.fixture
def app_runner(prompter):
    return ThreadedAppRunner(
        app=prompter.app, pre_run=prompter.pre_run)


class BasicPromptToolkitTest:
    def assert_current_buffer(self, app, expected_current_buffer_name):
        assert app.current_buffer.name == expected_current_buffer_name

    def assert_current_buffer_text(self, app, expected):
        assert app.current_buffer.text == expected

    def assert_buffer_is_visible(self, app, buffer_name):
        assert buffer_name in self.get_all_visible_buffers(app)

    def assert_buffer_is_not_visible(self, app, buffer_name):
        assert buffer_name not in self.get_all_visible_buffers(app)

    def get_all_visible_buffers(self, app):
        return [
            window.content.buffer.name
            for window in app.layout.visible_windows
            if hasattr(window.content, 'buffer')
        ]


class TestPromptToolkitPrompterBuffer:
    """This set of tests tests that we set the buffer (aka "construction zone")
    correctly. Some of these tests test against specific edge cases that have
    previously been known to produce unexpected behavior.

    """
    @pytest.mark.parametrize(
        'args,expected_input_buffer_text',
        [
            (['ec2', 'fake'], 'ec2 fake'),
            (['ec2'], 'ec2 '),
            (['s3', 'mv', '/path/to/file/1', 's3://path/to/file/2'],
             's3 mv /path/to/file/1 s3://path/to/file/2 '),
            (['s3', 'ls'], 's3 ls '),
            (['ec2', 'desc'], 'ec2 desc'),
            (['s3', 'ls '], 's3 ls '),
            (['ec2', 'fake', '--output'],
             'ec2 fake --output '),
            (['ec2', 'describe-instances', '--output'],
             'ec2 describe-instances --output '),
            ([' '], ' '),
        ]
    )
    def test_input_buffer_initialization(
            self, prompter, args, expected_input_buffer_text):
        prompter.args = args
        prompter.pre_run()
        actual_input_text = prompter.input_buffer.document.text
        assert actual_input_text == expected_input_buffer_text

    def test_handle_args_with_spaces(self, app_runner, prompter):
        original_args = ['iam', 'create-role', '--description', 'With spaces']
        prompter.args = original_args
        with app_runner.run_app_in_thread(
                target=prompter.prompt_for_args, args=(original_args,)) as ctx:
            assert prompter.input_buffer.document.text == (
                "iam create-role --description 'With spaces' "
            )
        assert ctx.return_value == original_args


class TestPromptToolkitDocBuffer(BasicPromptToolkitTest):
    def assert_doc_panel_is_visible(self, app):
        assert app.show_doc

    def assert_doc_panel_is_not_visible(self, app):
        assert not app.show_doc

    def assert_doc_panel_cursor_position(self, app, expected_row):
        assert app.layout.get_buffer_by_name(
            'doc_buffer').document.cursor_position_row == expected_row

    def test_doc_buffer_not_shown_on_start_and_not_focusable(self, app_runner):
        with app_runner.run_app_in_thread():
            self.assert_doc_panel_is_not_visible(app_runner.app)
            app_runner.feed_input(Keys.F1)
            self.assert_current_buffer(app_runner.app, 'input_buffer')

    def test_doc_buffer_shows_hides_on_F3(self, app_runner):
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.F3)
            self.assert_doc_panel_is_visible(app_runner.app)
            app_runner.feed_input(Keys.F3)
            self.assert_doc_panel_is_not_visible(app_runner.app)
            self.assert_current_buffer(app_runner.app, 'input_buffer')

    def test_doc_buffer_gets_and_removes_focus(self, app_runner):
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.F3)
            self.assert_doc_panel_is_visible(app_runner.app)
            app_runner.feed_input(Keys.F2)
            self.assert_current_buffer(app_runner.app, 'doc_buffer')
            app_runner.feed_input('q')
            self.assert_current_buffer(app_runner.app, 'input_buffer')

    def test_doc_buffer_keeps_position_if_content_dont_change(
            self, prompter, app_runner):
        prompter.args = ['ec2', 'describe-instances']
        with app_runner.run_app_in_thread():
            # Open the doc panel, focus on it, and go to its top
            app_runner.feed_input(Keys.F3, Keys.F2, 'g')
            self.assert_doc_panel_cursor_position(
                app_runner.app, expected_row=0)
            # Move three rows down
            app_runner.feed_input('j', 'j', 'j')
            self.assert_doc_panel_cursor_position(
                app_runner.app, expected_row=3)
            # Focus on the input buffer
            app_runner.feed_input('q')
            # Add parameters to the currently inputted command
            app_runner.feed_input('--instances')
            # The doc position should not have moved
            self.assert_doc_panel_cursor_position(
                app_runner.app, expected_row=3)

    @pytest.mark.parametrize(
        'args,expected_docs',
        [
            ([' '], 'AWS Command Line Interface'),
            (['fake'], 'AWS Command Line Interface'),
            (['ec2'], 'Elastic Compute Cloud'),
            (['ec2', 'fake'], 'Elastic Compute Cloud'),
            (['ec2', 'describe-instances'], 'Describes the specified'),
            (['ec2', 'describe-instances', '--instance-ids'],
             'Describes the specified'),
        ]
    )
    def test_doc_panel_content(self, prompter, args, expected_docs):
        prompter.args = args
        prompter.pre_run()
        assert expected_docs in prompter.doc_buffer.document.text


class TestHistoryMode(BasicPromptToolkitTest):
    def assert_history_mode_is_enabled(self, app):
        assert app.current_buffer.history_mode

    def assert_history_mode_is_disabled(self, app):
        assert not app.current_buffer.history_mode

    def assert_selected_history_completion(self, app, expected):
        actual = app.current_buffer.complete_state.current_completion.text
        assert actual == expected

    def test_history_mode_disabled_on_start_and_switched_by_control_R(
            self, app_runner):
        with app_runner.run_app_in_thread():
            self.assert_history_mode_is_disabled(app_runner.app)
            app_runner.feed_input(Keys.ControlR)
            self.assert_history_mode_is_enabled(app_runner.app)
            app_runner.feed_input(Keys.ControlR)
            self.assert_history_mode_is_disabled(app_runner.app)

    def test_choose_and_disable_history_mode_with_enter(
            self, app_runner, prompter):
        prompter.args = ['s3']
        with app_runner.run_app_in_thread():
            self.assert_history_mode_is_disabled(app_runner.app)
            app_runner.feed_input(Keys.ControlR)
            self.assert_history_mode_is_enabled(app_runner.app)
            app_runner.feed_input(Keys.Down)
            self.assert_selected_history_completion(
                app_runner.app, 's3 ls')
            app_runner.feed_input(Keys.Enter)
            self.assert_current_buffer(app_runner.app, 'input_buffer')
            self.assert_current_buffer_text(app_runner.app, 's3 ls')

    def test_choose_and_disable_history_mode_with_space(
            self, app_runner, prompter):
        prompter.args = ['s3']
        with app_runner.run_app_in_thread():
            self.assert_history_mode_is_disabled(app_runner.app)
            app_runner.feed_input(Keys.ControlR)
            self.assert_history_mode_is_enabled(app_runner.app)
            app_runner.feed_input(Keys.Down)
            self.assert_selected_history_completion(
                app_runner.app, 's3 ls')
            app_runner.feed_input(' ')
            self.assert_history_mode_is_disabled(app_runner.app)
            self.assert_current_buffer(app_runner.app, 'input_buffer')
            self.assert_current_buffer_text(app_runner.app, 's3 ls ')


class TestCompletions(BasicPromptToolkitTest):
    def test_service_full_name_shown(self, app_runner, prompter):
        prompter.args = ['e']
        with app_runner.run_app_in_thread():
            first_completion = app_runner.app.current_buffer.\
                complete_state.completions[0]
            assert 'Elastic Compute' in first_completion.display_meta_text

    def test_switch_to_multicolumn_mode(self, app_runner, prompter):
        prompter.args = ['ec2']
        with app_runner.run_app_in_thread():
            assert not app_runner.app.multi_column
            app_runner.feed_input(Keys.F4)
            assert app_runner.app.multi_column
            app_runner.feed_input(Keys.F4)
            assert not app_runner.app.multi_column


class TestHelpPanel(BasicPromptToolkitTest):
    def test_help_panel_disabled_on_start_and_appear_on_F1(
            self, app_runner, prompter):
        with app_runner.run_app_in_thread():
            assert not app_runner.app.show_help
            app_runner.feed_input(Keys.F1)
            assert app_runner.app.show_help
            app_runner.feed_input(Keys.F1)
            assert not app_runner.app.show_help

    def test_show_correct_help_panel(
            self, app_runner, prompter):
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.F1)
            self.assert_buffer_is_visible(app_runner.app, 'help_input')
            self.assert_buffer_is_not_visible(app_runner.app, 'help_doc')
            # Open doc panel and focus on it
            app_runner.feed_input(Keys.F3, Keys.F2)
            # The help for the doc panel should now be visible instead of
            # the help for the main input buffer
            self.assert_buffer_is_visible(app_runner.app, 'help_doc')
            self.assert_buffer_is_not_visible(app_runner.app, 'help_input')

    def test_toolbar_hides_when_help_panel_visible(
            self, app_runner, prompter):
        with app_runner.run_app_in_thread():
            self.assert_buffer_is_visible(app_runner.app, 'toolbar_input')
            app_runner.feed_input(Keys.F1)
            self.assert_buffer_is_not_visible(app_runner.app, 'toolbar_input')
            self.assert_buffer_is_not_visible(app_runner.app, 'toolbar_doc')


class TestDebugPanel(BasicPromptToolkitTest):
    def test_debug_panel_not_visible_in_non_debug_mode(
            self, app_runner, prompter):
        with app_runner.run_app_in_thread():
            self.assert_buffer_is_not_visible(app_runner.app, 'debug_buffer')

    def test_debug_panel_visible_in_debug_mode(
            self, app_runner, prompter):
        prompter.app.debug = True
        with app_runner.run_app_in_thread():
            self.assert_buffer_is_visible(app_runner.app, 'debug_buffer')

    def test_open_save_dialog_on_control_s(
            self, app_runner, prompter):
        prompter.app.debug = True
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.ControlS)
            self.assert_current_buffer_text(app_runner.app, 'prompt_debug.log')

    def test_can_save_log_file(
            self, app_runner, prompter, files):
        prompter.app.debug = True
        log_file_path = files.full_path('prompt_debug.log')
        with cd(files.rootdir):
            with app_runner.run_app_in_thread():
                app_runner.feed_input(Keys.ControlS)
                app_runner.feed_input(Keys.Enter)
        assert os.path.exists(log_file_path)

    def test_can_switch_focus_between_panels(
            self, app_runner, prompter):
        prompter.app.debug = True
        with app_runner.run_app_in_thread():
            self.assert_current_buffer(app_runner.app, 'input_buffer')
            app_runner.feed_input(Keys.F2)
            self.assert_current_buffer(app_runner.app, 'debug_buffer')
            app_runner.feed_input(Keys.F2)
            self.assert_current_buffer(app_runner.app, 'input_buffer')

    @mock.patch('awscrt.io.init_logging')
    def test_debug_mode_does_not_allow_crt_logging(
            self, mock_init_logging, app_runner, prompter):
        args = ['ec2', 'describe-instances', '--debug']
        with app_runner.run_app_in_thread(
                target=prompter.prompt_for_args, args=(args,)):
            assert app_runner.app.debug
        mock_init_logging.assert_called_with(
            awscrt.io.LogLevel.NoLogs, 'stderr'
        )


class TestOutputPanel(BasicPromptToolkitTest):
    def test_output_panel_not_visible_on_start(self, app_runner):
        with app_runner.run_app_in_thread():
            self.assert_buffer_is_not_visible(app_runner.app, 'output_buffer')

    def test_output_panel_switches_on_F5(self, app_runner):
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.F5)
            self.assert_buffer_is_visible(app_runner.app, 'output_buffer')
            app_runner.feed_input(Keys.F5)
            self.assert_buffer_is_not_visible(app_runner.app, 'output_buffer')

    def test_output_panel_and_doc_panel_can_be_visible_together(
            self, app_runner):
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.F5)
            self.assert_buffer_is_visible(app_runner.app, 'output_buffer')
            self.assert_buffer_is_not_visible(app_runner.app, 'doc_buffer')
            app_runner.feed_input(Keys.F3)
            self.assert_buffer_is_visible(app_runner.app, 'doc_buffer')
            self.assert_buffer_is_visible(app_runner.app, 'output_buffer')

    def test_can_switch_focus_between_panels(self, app_runner):
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.F5, Keys.F3)
            self.assert_current_buffer(app_runner.app, 'input_buffer')
            app_runner.feed_input(Keys.F2)
            self.assert_current_buffer(app_runner.app, 'doc_buffer')
            app_runner.feed_input(Keys.F2)
            self.assert_current_buffer(app_runner.app, 'output_buffer')
            app_runner.feed_input(Keys.F2)
            self.assert_current_buffer(app_runner.app, 'input_buffer')

    def test_can_quit_output_panel(self, app_runner):
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.F5, Keys.F2)
            self.assert_current_buffer(app_runner.app, 'output_buffer')
            app_runner.feed_input('q')
            self.assert_current_buffer(app_runner.app, 'input_buffer')

    def test_return_focus_on_input_buffer(self, app_runner):
        with app_runner.run_app_in_thread():
            app_runner.feed_input(Keys.F5, Keys.F2)
            self.assert_current_buffer(app_runner.app, 'output_buffer')
            app_runner.feed_input(Keys.F5)
            self.assert_current_buffer(app_runner.app, 'input_buffer')
