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
from prompt_toolkit.formatted_text import HTML, to_formatted_text
from prompt_toolkit.formatted_text.utils import fragment_list_to_text
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.layout import HSplit, Window, VSplit
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import ConditionalContainer
from prompt_toolkit.layout.processors import Processor, Transformation
from prompt_toolkit.widgets import Frame, HorizontalLine

from awscli.autoprompt.filters import (
    help_section_visible, doc_window_has_focus, search_input_has_focus,
    input_buffer_has_focus, is_history_mode
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


class BaseHelpContainer(ConditionalContainer):
    STYLE = '<style fg="darkturquoise">'
    NAME = None
    CONDITION = None
    DIMENSIONS = {}

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
    CONDITION = input_buffer_has_focus

    @property
    def help_text(self):
        return (
            f'{self.STYLE}[ENTER]</style> Autocomplete Choice/Execute Command\n'
            f'{self.STYLE}[F1]</style> Hide/Show Shortkey Help\n'
            f'{self.STYLE}[F2]</style> Focus on Docs\n'
            f'{self.STYLE}[F3]</style> Hide/Show Docs\n'
            f'{self.STYLE}[F4]</style> One/Multi column prompt\n'
            f'{self.STYLE}[CONTROL+R]</style> On/Off bck-i-search'
        )


class DocHelpView(BaseHelpView):
    TITLE = 'Don panel help'
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
            f'{self.STYLE}[F1]</style> Hide/Show Shortkey Help\n'
            f'{self.STYLE}[F2] or [q]</style> Focus on Input'
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
            f'{self.STYLE}[F1]</style> Hide/Show Shortkey Help{self.SPACING}'
            f'{self.STYLE}[F2] or [q]</style> Focus on Input'
        )


class InputToolbarView(BaseToolbarView):
    NAME = 'toolbar_input'
    CONDITION = input_buffer_has_focus

    @property
    def help_text(self):
        return (
            f'{self.STYLE}[ENTER]</style> Autocomplete '
            f'Choice/Execute Command{self.SPACING}'
            f'{self.STYLE}[F1]</style> Hide/Show Shortkey Help{self.SPACING}'
            f'{self.STYLE}[F2]</style> Focus on Docs{self.SPACING}'
            f'{self.STYLE}[F3]</style> Hide/Show Docs'
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
                    VSplit([InputToolbarView(), DocToolbarView()]),
                    ~help_section_visible
                )
            ])
        ])

    def __pt_container__(self):
        return self.container


class HelpPanelWidget:

    def __init__(self):
        self.container = ConditionalContainer(
            HSplit([DocHelpView(), InputHelpView()]),
            help_section_visible
        )

    def __pt_container__(self):
        return self.container
