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
    Window, HSplit, Dimension, ConditionalContainer
)
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.widgets import Box

from awscli.customizations.wizard.ui.prompt import WizardPrompt


class WizardSectionTab:
    def __init__(self, section_name, section_definition):
        self._name = section_name
        self._definition = section_definition
        self.container = self._get_container()

    def _get_container(self):
        content = f"{self._definition['shortname']}"
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
        traverser = get_app().traverser
        if traverser.get_current_section() == self._name:
            return 'class:wizard.section.tab.current'
        elif traverser.has_visited_section(self._name):
            return 'class:wizard.section.tab.visited'
        return 'class:wizard.section.tab.unvisited'

    def __pt_container__(self):
        return self.container


class WizardSectionBody:
    def __init__(self, section_name, section_definition):
        self._name = section_name
        self._definition = section_definition
        self.container = self._get_container()

    def _get_container(self):
        return ConditionalContainer(
            Box(
                HSplit(
                    self._create_prompts_from_section_definition(),
                    padding=1
                ),
                padding_left=2, padding_top=1
            ),
            Condition(self._is_current_section)
        )

    def _is_current_section(self):
        return get_app().traverser.get_current_section() == self._name

    def _create_prompts_from_section_definition(self):
        prompts = []
        for value_name, value_definition in self._definition['values'].items():
            if value_definition['type'] == 'prompt':
                prompts.append(WizardPrompt(value_name, value_definition))
        return prompts

    def __pt_container__(self):
        return self.container
