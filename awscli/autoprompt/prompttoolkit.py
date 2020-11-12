# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import logging
import shlex
import sys
from contextlib import nullcontext, contextmanager

from prompt_toolkit.application import Application
from prompt_toolkit.completion import Completer, ThreadedCompleter
from prompt_toolkit.completion import Completion
from prompt_toolkit.document import Document

from awscli.logger import LOG_FORMAT
from awscli.autocomplete import parser
from awscli.autocomplete.local import model
from awscli.autoprompt.doc import DocsGetter
from awscli.autoprompt.factory import PromptToolkitFactory
from awscli.autoprompt.logger import PromptToolkitHandler


LOG = logging.getLogger(__name__)


@contextmanager
def loggers_handler_switcher():
    old_handlers = {}
    loggers = [name for name in logging.root.manager.loggerDict]

    handler = PromptToolkitHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        old_handlers[logger_name] = logger.handlers
        logger.handlers = []
        logger.addHandler(handler)
    yield None
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        for handler in old_handlers[logger_name]:
            logger.addHandler(handler)


class PromptToolkitPrompter:
    """Handles the actual prompting in the autoprompt workflow.

    """
    def __init__(self, completion_source, driver, completer=None,
                 factory=None, app=None, cli_parser=None):
        self._completion_source = completion_source
        if completer is None:
            completer = PromptToolkitCompleter(self._completion_source)
        # We wrap our completer with a ThreadedCompleter to make autocompletion
        # generation more responsive.
        self._completer = ThreadedCompleter(completer)
        if factory is None:
            factory = PromptToolkitFactory(completer=self._completer)
        self._parser = cli_parser
        if self._parser is None:
            self._parser = parser.CLIParser(model.ModelIndex())
        self._factory = factory
        self.input_buffer = None
        self.doc_buffer = None
        self.output_buffer = None
        if app is None:
            app = self.create_application()
        self._app = app
        self._args = []
        self._driver = driver
        self._docs_getter = DocsGetter(self._driver)

    def args(self, value):
        self._args = value

    args = property(None, args)

    def _create_buffers(self):
        self.input_buffer = self._factory.create_input_buffer(
            self.update_bottom_buffers_text)
        self.doc_buffer = self._factory.create_doc_buffer()
        self.output_buffer = self._factory.create_output_buffer()

    def _create_containers(self):
        input_buffer_container = self._factory.create_input_buffer_container(
            self.input_buffer)
        doc_window = self._factory.create_searchable_window(
            'Doc panel', self.doc_buffer)
        output_window = self._factory.create_searchable_window(
            'Output panel', self.output_buffer)
        return input_buffer_container, doc_window, output_window

    def create_application(self):
        self._create_buffers()
        input_buffer_container, \
                doc_window, output_window = self._create_containers()
        layout = self._factory.create_layout(
            on_input_buffer_text_changed=self.update_bottom_buffers_text,
            input_buffer_container=input_buffer_container,
            doc_window=doc_window, output_window=output_window
        )
        kb_manager = self._factory.create_key_bindings()
        kb = kb_manager.keybindings
        app = Application(layout=layout, key_bindings=kb, full_screen=False,
                          erase_when_done=True)
        self._set_app_defaults(app)
        return app

    def _set_app_defaults(self, app):
        app.show_doc = False
        app.multi_column = False
        app.show_help = False
        app.debug = False
        app.show_output = False
        return app

    def update_bottom_buffers_text(self, *args):
        parsed = self._parser.parse(
            'aws ' + self.input_buffer.document.text)
        self._update_doc_window_contents(parsed)

    def _update_doc_window_contents(self, parsed):
        content = self._docs_getter.get_docs(parsed)
        # The only way to "modify" a read-only buffer in prompt_toolkit is to
        # create a new `prompt_toolkit.document.Document`. A 'cursor_position'
        # of 0 allows us to start viewing the documentation from the beginning,
        # as opposed to the default of moving the cursor to the end.
        #
        # Note: `content` may be None if we are still in the middle of typing a
        # command (e.g. `aws ec2 descr`) or if the current command is invalid.
        # In these cases, we don't update the doc window.
        if content is not None and content != self.doc_buffer.document.text:
            self.doc_buffer.reset()
            new_document = Document(text=content, cursor_position=0)
            self.doc_buffer.set_document(new_document, bypass_readonly=True)

    def _set_debug_mode(self):
        if '--debug' in self._args:
            self._app.debug = True

    def pre_run(self):
        if '--cli-auto-prompt' in self._args:
            self._args.remove('--cli-auto-prompt')
        # Before prompting the user for a command, we copy what they entered
        # at the command line into the buffer (aka "construction zone"), set
        # the cursor position, and make sure to immediately provide a pop-up
        # menu with autocompletion options.
        #
        # If what the user entered at the command line already has no
        # completions, we just keep it as it is without showing
        # any suggestions.
        self.input_buffer.insert_text(' '.join(self._args))
        cmd_line_text = 'aws ' + self.input_buffer.document.text
        self._set_input_buffer_text(cmd_line_text)
        self.update_bottom_buffers_text()
        self.input_buffer.start_completion()

    def _set_input_buffer_text(self, cmd_line_text):
        """If entered command line does not have trailing space and can not
           be autocompleted we assume that it is a completed part of command
           and add trailing space to it"""
        if cmd_line_text[-1] == ' ':
            return
        if self._can_autocomplete(cmd_line_text):
            return
        if cmd_line_text.strip() != 'aws':
            self.input_buffer.insert_text(' ')

    def _can_autocomplete(self, cmd_line_text):
        return bool(self._completion_source.autocomplete(cmd_line_text))

    def _quote_args_with_spaces(self, args):
        return [shlex.quote(arg) for arg in args]

    def prompt_for_args(self, original_args):
        """Prompt for values for a given CLI command.

        :type original_args: list
        :param original_args: A list of the entered command at the program entry
            point, less the initial `aws` command.

        :rtype: list
        :return: A list of what was entered into the autoprompt buffer,
            delimited by whitespace characters.

        """
        self._args = self._quote_args_with_spaces(original_args)
        self._set_debug_mode()
        logging_manager = nullcontext
        if self._app.debug:
            logging_manager = loggers_handler_switcher
        with logging_manager():
            self._app.run(pre_run=self.pre_run)
        cmd_line_text = self.input_buffer.document.text
        # Once the application is finished running, the screen is cleared.
        # Here, we display the command to be run so that the user knows what
        # command caused the output that they're seeing.
        sys.stdout.write(f'> aws {cmd_line_text}\n')
        return shlex.split(cmd_line_text)


class PromptToolkitCompleter(Completer):
    """Handles conversion of autocompletion data from our completion source
    into `prompt_toolkit.Completion` objects that prompt_toolkit understands.

    Note: prompt_toolkit expects a method `get_completions()` to generate the
    `prompt_toolkit.Completion` objects.

    """
    def __init__(self, completion_source):
        self._completion_source = completion_source

    def _convert_to_prompt_completions(self, low_level_completions,
                                       text_before_cursor):
        # Converts the low-level completions from the model autocompleter
        # and converts them to Completion() objects that are used by
        # prompt_toolkit.
        word_before_cursor = self._strip_whitespace(text_before_cursor)
        completions = self._filter_completions(low_level_completions)
        ordered_completions = self._prioritize_required_args(completions)
        for completion in ordered_completions:
            display_text = self._get_display_text(completion)
            display_meta = self._get_display_meta(completion)
            location = self._get_starting_location_of_last_word(
                text_before_cursor, word_before_cursor)
            yield Completion(completion.name, location, display=display_text,
                             display_meta=display_meta)

    def get_completions(self, document, complete_event):
        try:
            text_before_cursor = document.text_before_cursor
            text_to_autocomplete = 'aws ' + text_before_cursor
            completions = self._completion_source.autocomplete(
                text_to_autocomplete, len(text_to_autocomplete))
            yield from self._convert_to_prompt_completions(
                completions, text_before_cursor)
        except Exception as e:
            LOG.debug('Exception caught in PromptToolkitCompleter: %s' % e,
                      exc_info=True)

    def _strip_whitespace(self, text):
        word_before_cursor = ''
        if text.strip():
            word_before_cursor = text.strip().split()[-1]
        return word_before_cursor

    def _prioritize_required_args(self, completions):
        required_args = self._get_required_args(completions)
        optional_args = self._get_optional_args(completions)
        return required_args + optional_args

    def _get_required_args(self, completions):
        results = [
            arg for arg in completions
            if arg.required
        ]
        return results

    def _get_optional_args(self, completions):
        results = [
            arg for arg in completions
            if not arg.required
        ]
        return results

    def _get_display_text(self, completion):
        if completion.display_text is not None:
            return completion.display_text
        display_text = completion.name
        if completion.name.startswith('--') and completion.required:
            display_text += ' (required)'
        return display_text

    def _get_display_meta(self, completion):
        display_meta = ''
        type_name = getattr(completion, 'cli_type_name', None)
        help_text = getattr(completion, 'help_text', None)
        if type_name:
            display_meta += f'[{type_name}] '
        if help_text:
            display_meta += f'{help_text}'
        return display_meta

    def _filter_completions(self, completions):
        completions = self._filter_out_autoprompt_overrides(completions)
        completions = self._remove_duplicate_completions(completions)
        return completions

    def _filter_out_autoprompt_overrides(self, completions):
        filtered_completions = [
            completion for completion in completions
            if completion.name not in ['--cli-auto-prompt',
                                       '--no-cli-auto-prompt']
        ]
        return filtered_completions

    def _remove_duplicate_completions(self, completions):
        unique_completion_names = []
        unique_completions = []
        for completion in completions:
            if completion.name not in unique_completion_names:
                unique_completion_names.append(completion.name)
                unique_completions.append(completion)
        return unique_completions

    def _get_starting_location_of_last_word(self, text_before_cursor,
                                            word_before_cursor):
        if text_before_cursor and text_before_cursor[-1] == ' ':
            location = 0
        else:
            location = -len(word_before_cursor)
        return location
