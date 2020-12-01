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
from prompt_toolkit.application import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.containers import (
    Window, VSplit, Dimension, ConditionalContainer
)
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.layout.containers import ScrollOffsets

from awscli.customizations.wizard.ui.selectmenu import (
    CollapsableSelectionMenuControl
)
from awscli.customizations.wizard.ui.utils import FullyExtendedWidthWindow


class WizardPrompt:
    def __init__(self, value_name, value_definition):
        self._value_name = value_name
        self._value_definition = value_definition
        self.container = self._get_container()

    def _get_container(self):
        uses_choices = 'choices' in self._value_definition
        if uses_choices:
            answer = WizardPromptSelectionAnswer(self._value_name)
        else:
            answer = WizardPromptAnswer(self._value_name)
        return ConditionalContainer(
            VSplit(
                [
                    WizardPromptDescription(
                        self._value_name,
                        self._value_definition['description']
                    ),
                    answer
                ],
            ),
            Condition(self._is_visible)
        )

    def _is_visible(self):
        return get_app().traverser.is_prompt_visible(self._value_name)

    def __pt_container__(self):
        return self.container


class WizardPromptDescription:
    def __init__(self, value_name, value_description):
        self._value_name = value_name
        self._value_description = value_description
        self.container = self._get_container()

    def _get_container(self):
        content = f'{self._value_description}:'
        buffer = Buffer(
            document=Document(content),
            read_only=True
        )
        return Window(
            content=BufferControl(
                buffer=buffer, focusable=False
            ),
            style=self._get_style,
            width=Dimension.exact(len(content) + 1),
            dont_extend_height=True,
        )

    def _get_style(self):
        if get_app().traverser.get_current_prompt() == self._value_name:
            return 'class:wizard.prompt.description.current'
        else:
            return 'class:wizard.prompt.description'

    def __pt_container__(self):
        return self.container


class WizardPromptAnswer:
    def __init__(self, value_name):
        self._value_name = value_name
        self._buffer = self._get_answer_buffer()
        self.container = self._get_answer_container()

    def _get_answer_buffer(self):
        return Buffer(name=self._value_name)

    def _get_answer_container(self):
        return FullyExtendedWidthWindow(
            content=BufferControl(
                buffer=self._buffer
            ),
            style=self._get_style,
            dont_extend_height=True,
        )

    def _get_style(self):
        if get_app().traverser.get_current_prompt() == self._value_name:
            return 'class:wizard.prompt.answer.current'
        else:
            return 'class:wizard.prompt.answer'

    def __pt_container__(self):
        return self.container


class WizardPromptSelectionAnswer(WizardPromptAnswer):
    def _get_answer_container(self):
        return FullyExtendedWidthWindow(
            content=CollapsableSelectionMenuControl(
                items=self._get_choices,
                selection_capture_buffer=self._buffer,
                on_toggle=self._show_details
            ),
            style=self._get_style,
            always_hide_cursor=True,
            scroll_offsets=ScrollOffsets(),
            right_margins=[ScrollbarMargin()],
        )

    def _get_choices(self):
        return get_app().traverser.get_current_prompt_choices()

    def _show_details(self, choice):
        if get_app().details_visible:
            details_buffer = get_app().layout.get_buffer_by_name(
                'details_buffer')
            details = self._get_details(choice)
            details_buffer.reset()
            new_document = Document(text=details, cursor_position=0)
            details_buffer.set_document(new_document, bypass_readonly=True)

    def _get_details(self, choice):
        return get_app().traverser.get_details_for_choice(choice)
