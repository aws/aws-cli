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
import os
from functools import partial

from prompt_toolkit.application import get_app
from prompt_toolkit.filters import has_focus
from prompt_toolkit.formatted_text import HTML, Template, to_formatted_text
from prompt_toolkit.formatted_text.utils import fragment_list_to_text
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.processors import Processor, Transformation
from prompt_toolkit.layout import (
    HSplit, Window, VSplit, FloatContainer, Float, ConditionalContainer
)
from prompt_toolkit.widgets import (
    Frame, HorizontalLine, Dialog, Button, TextArea, Label
)
from prompt_toolkit.widgets.base import Border

from awscli.autoprompt.filters import (
    help_section_visible, doc_window_has_focus, search_input_has_focus,
    input_buffer_has_focus, is_history_mode, is_debug_mode,
)


class FormatTextProcessor(Processor):
    """This Processor is used to transform formatted text into a useable
    format inside a ``prompt_toolkit.buffer.Buffer``.

    """
    def apply_transformation(self, text_input):
        # https://python-prompt-toolkit.readthedocs.io/en/master/pages/reference.html#module-prompt_toolkit.formatted_text
        fragments = to_formatted_text(
            HTML(fragment_list_to_text(text_input.fragments)))
        return Transformation(fragments)


class TitleLine:

    def __init__(self, title):
        fill = partial(Window, style='class:frame.border')
        self.container = VSplit([
            fill(char=Border.HORIZONTAL),
            fill(width=1, height=1, char='|'),
            Label(title, style='class:frame.label', dont_extend_width=True),
            fill(width=1, height=1, char='|'),
            fill(char=Border.HORIZONTAL),
        ], height=1)

    def __pt_container__(self):
        return self.container


class BaseHelpContainer(ConditionalContainer):
    STYLE = '<style fg="darkturquoise">'
    NAME = None
    CONDITION = None
    DIMENSIONS = {}
    FOCUSABLE = False

    def __init__(self):
        window = self.create_window(self.create_buffer())
        super().__init__(window, self.CONDITION)

    @property
    def help_text(self):
        pass

    def create_buffer(self):
        document = Document(text=self.help_text, cursor_position=0)
        help_buffer = Buffer(name=self.NAME, read_only=True)
        help_buffer.set_document(document, bypass_readonly=True)
        help_buffer.focusable = self.FOCUSABLE
        return help_buffer

    def create_window(self, help_buffer):
        return Window(
            content=BufferControl(
                buffer=help_buffer,
                input_processors=[FormatTextProcessor()]
            ),
            wrap_lines=True,
            **self.DIMENSIONS
        )


class BaseHelpView(BaseHelpContainer):
    TITLE = None
    DIMENSIONS = {'width': Dimension(max=35, preferred=25)}

    def create_window(self, help_buffer):
        return Frame(
            super(BaseHelpView, self).create_window(help_buffer),
            title=self.TITLE
        )


class InputHelpView(BaseHelpView):
    TITLE = 'Prompt panel help'
    NAME = 'help_input'
    CONDITION = has_focus('input_buffer')

    @property
    def help_text(self):
        return (
            f'{self.STYLE}[ENTER]</style> Autocomplete Choice/Execute Command\n'
            f'{self.STYLE}[F1]</style> Hide Shortkey Help\n'
            f'{self.STYLE}[F2]</style> Focus on next panel\n'
            f'{self.STYLE}[F3]</style> Hide/Show Docs\n'
            f'{self.STYLE}[F4]</style> One/Multi column prompt\n'
            f'{self.STYLE}[F5]</style> Hide/Show Output\n'
            f'{self.STYLE}[CONTROL+R]</style> On/Off bck-i-search'
        )


class OutputHelpView(BaseHelpView):
    TITLE = 'Output panel help'
    NAME = 'output_input'
    CONDITION = has_focus('output_buffer')

    @property
    def help_text(self):
        return (
            f'{self.STYLE}[/]</style> Search Forward\n'
            f'{self.STYLE}[?]</style> Search Backward\n'
            f'{self.STYLE}[n]</style> Find Next Match\n'
            f'{self.STYLE}[N]</style> Find Previous Match\n'
            f'{self.STYLE}[F1]</style> Hide Shortkey Help\n'
            f'{self.STYLE}[F2]</style> Focus on next panel\n'
            f'{self.STYLE}[F3]</style> Hide/Show Docs\n'
            f'{self.STYLE}[F5]</style> Hide/Show Output\n'
        )


class DocHelpView(BaseHelpView):
    TITLE = 'Doc panel help'
    NAME = 'help_doc'
    CONDITION = doc_window_has_focus | search_input_has_focus

    @property
    def help_text(self):
        return (
            f'{self.STYLE}[/]</style> Search Forward\n'
            f'{self.STYLE}[?]</style> Search Backward\n'
            f'{self.STYLE}[n]</style> Find Next Match\n'
            f'{self.STYLE}[N]</style> Find Previous Match\n'
            f'{self.STYLE}[w]</style> Go Up a Page\n'
            f'{self.STYLE}[z]</style> Go Down a Page\n'
            f'{self.STYLE}[j]</style> Go Up a Line\n'
            f'{self.STYLE}[k]</style> Go Down a Line\n'
            f'{self.STYLE}[g]</style> Go to Top\n'
            f'{self.STYLE}[G]</style> Go to Bottom\n'
            f'{self.STYLE}[F1]</style> Hide Shortkey Help\n'
            f'{self.STYLE}[F2]</style> Focus on next panel\n'
            f'{self.STYLE}[q]</style> Focus on Input\n'
            f'{self.STYLE}[F5]</style> Hide/Show Output'
        )


class BaseToolbarView(BaseHelpContainer):
    DIMENSIONS = {'height': Dimension(max=2)}
    SPACING = '    '


class DocToolbarView(BaseToolbarView):
    NAME = 'toolbar_doc'
    CONDITION = doc_window_has_focus | search_input_has_focus

    @property
    def help_text(self):
        return (
            f'{self.STYLE}[F1]</style> Show Shortkey Help{self.SPACING}'
            f'{self.STYLE}[F2]</style> Focus on next panel{self.SPACING}'
            f'{self.STYLE}[[q]</style> Focus on Input'
        )


class InputToolbarView(BaseToolbarView):
    NAME = 'toolbar_input'
    CONDITION = has_focus('input_buffer')

    @property
    def help_text(self):
        return (
            f'{self.STYLE}[ENTER]</style> Autocomplete '
            f'Choice/Execute Command{self.SPACING}'
            f'{self.STYLE}[F1]</style> Show Shortkey Help{self.SPACING}'
            f'{self.STYLE}[F2]</style> Focus on next panel{self.SPACING}'
            f'{self.STYLE}[F3]</style> Hide/Show Docs{self.SPACING}'
            f'{self.STYLE}[F5]</style> Hide/Show Output'
            )


class OutputToolbarView(BaseToolbarView):
    NAME = 'output_input'
    CONDITION = has_focus('output_buffer')

    @property
    def help_text(self):
        return (
            f'{self.STYLE}[F1]</style> Show Shortkey Help{self.SPACING}'
            f'{self.STYLE}[F2]</style> Focus on next panel{self.SPACING}'
            f'{self.STYLE}[F3]</style> Hide/Show Docs{self.SPACING}'
            f'{self.STYLE}[F5]</style> Hide/Show Output'
            )


class DebugToolbarView(BaseToolbarView):
    NAME = 'toolbar_input'
    CONDITION = is_debug_mode

    @property
    def help_text(self):
        return (
            f'{self.STYLE}[CONTROL+S]</style> Save log to file'
        )


class HistorySignToolbarView(BaseToolbarView):
    NAME = 'history_sign'
    STYLE = '<style fg="ansired" bg="#00ff44">'
    CONDITION = is_history_mode
    DIMENSIONS = {
        'height': Dimension(max=2),
        'width': Dimension(max=13),
    }

    @property
    def help_text(self):
        return f'{self.STYLE}bck-i-search</style>{self.SPACING}'


class ToolbarWidget:

    def __init__(self):
        self.container = HSplit([
            ConditionalContainer(HorizontalLine(), ~help_section_visible),
            VSplit([
                HistorySignToolbarView(),
                ConditionalContainer(
                    VSplit([InputToolbarView(),
                            DocToolbarView(),
                            OutputToolbarView()]),
                    ~help_section_visible
                )
            ])
        ])

    def __pt_container__(self):
        return self.container


class HelpPanelWidget:

    def __init__(self):
        self.container = ConditionalContainer(
            HSplit([DocHelpView(), InputHelpView(), OutputHelpView()]),
            help_section_visible
        )

    def __pt_container__(self):
        return self.container


class DebugPanelWidget:
    DIMENSIONS = {
        'width': Dimension(max=40, preferred=20),
    }

    def __init__(self):
        self._dialog_prev_focus = None

        self.dialog = self.create_save_file_dialog()

        _kb = KeyBindings()
        _kb.add(Keys.ControlS, filter=is_debug_mode, is_global=True)(
            self._activate_dialog)

        self.float_container = FloatContainer(
            Window(
                content=BufferControl(
                    buffer=Buffer(name='debug_buffer', read_only=True)
                ),
                wrap_lines=True,
            ),
            key_bindings=_kb,
            floats=[]
        )
        self.container = ConditionalContainer(
            Frame(
                HSplit([
                    self.float_container,
                    HorizontalLine(),
                    DebugToolbarView()
                ]),
                **self.DIMENSIONS,
                title='Debug panel'
            ),
            filter=is_debug_mode
        )

    def _activate_dialog(self, event):
        layout = event.app.layout
        self._dialog_prev_focus = event.app.current_buffer
        self.float_container.floats.append(Float(content=self.dialog))
        layout.focus(self.dialog)

    def create_save_file_dialog(self):
        default_filename = 'prompt_debug.log'

        def cancel_handler():
            app = get_app()
            textfield.text = default_filename
            app.layout.focus(textfield)
            self.float_container.floats.pop()
            app.layout.focus(self._dialog_prev_focus)

        def ok_handler(*args, **kwargs):
            app = get_app()
            buffer = app.layout.get_buffer_by_name('debug_buffer')
            with open(os.path.expanduser(textfield.text), 'w') as f:
                f.write(buffer.document.text)
            textfield.text = default_filename
            app.layout.focus(textfield)
            self.float_container.floats.pop()
            app.layout.focus(self._dialog_prev_focus)

        ok_button = Button(text='Save', handler=ok_handler)
        cancel_button = Button(text='Cancel', handler=cancel_handler)

        textfield = TextArea(text=default_filename, multiline=False)

        dialog = Dialog(
            title='Save logs to file',
            body=HSplit([
                Label(text='Log file name', dont_extend_height=True),
                textfield,
            ], padding=Dimension(preferred=1, max=1)),
            buttons=[ok_button, cancel_button],
            with_background=True)
        # add keybinding to save file on press Enter in textfield
        dialog.container.body.container.content.key_bindings.add(
            Keys.Enter, filter=has_focus(textfield))(ok_handler)

        return dialog

    def __pt_container__(self):
        return self.container
