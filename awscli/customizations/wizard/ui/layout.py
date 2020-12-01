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
from prompt_toolkit.layout import Layout
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.widgets import Label, HorizontalLine
from prompt_toolkit.layout.containers import (
    Window, HSplit, Dimension, ConditionalContainer, WindowAlign, VSplit
)
from prompt_toolkit.layout.controls import BufferControl
from awscli.autoprompt.widgets import BaseToolbarView, TitleLine
from awscli.customizations.wizard.ui.section import (
    WizardSectionTab, WizardSectionBody
)
from awscli.customizations.wizard.ui.utils import Spacer
from awscli.customizations.wizard.ui.keybindings import (
    details_visible, prompt_has_details
)


class WizardLayoutFactory:
    def create_wizard_layout(self, definition):
        return Layout(
            container=HSplit(
                [
                    self._create_title(definition),
                    self._create_sections(definition),
                    HorizontalLine()
                ],
            )
        )

    def _create_title(self, definition):
        title = Label(f'{definition["title"]}', style='class:wizard.title')
        title.window.align = WindowAlign.CENTER
        return title

    def _create_sections(self, definition):
        section_tabs = []
        section_bodies = []
        for section_name, section_definition in definition['plan'].items():
            section_tabs.append(
                self._create_section_tab(section_name, section_definition)
            )
            section_bodies.append(
                self._create_section_body(section_name, section_definition)
            )
        section_tabs.append(Spacer())
        return VSplit(
            [
                HSplit(
                    section_tabs,
                    padding=1,
                    style='class:wizard.section.tab'
                ),
                HSplit([*section_bodies,
                        WizardDetailsPanel(),
                        DetailPanelToolbarView()])
            ]
        )

    def _create_section_tab(self, section_name, section_definition):
        return WizardSectionTab(section_name, section_definition)

    def _create_section_body(self, section_name, section_definition):
        return WizardSectionBody(section_name, section_definition)


class WizardDetailsPanel:
    DIMENSIONS = {
        'details_window_height_max': 40,
        'details_window_height_pref': 30,
    }

    def __init__(self):
        self.container = self._get_container()

    def _get_container(self):
        return ConditionalContainer(
            HSplit([
                TitleLine('Details panel'),
                Window(
                    content=BufferControl(
                        buffer=Buffer(name='details_buffer', read_only=True),
                    ),
                    height=Dimension(
                        max=self.DIMENSIONS['details_window_height_max'],
                        preferred=self.DIMENSIONS['details_window_height_pref']
                    ),
                    wrap_lines=True
                )
            ]),
            details_visible
        )

    def __pt_container__(self):
        return self.container


class DetailPanelToolbarView(BaseToolbarView):
    NAME = 'toolbar_details'
    CONDITION = prompt_has_details

    def create_window(self, help_buffer):
        return HSplit([
            HorizontalLine(),
            super(DetailPanelToolbarView, self).create_window(help_buffer)
        ])

    @property
    def help_text(self):
        return (
            f'{self.STYLE}[F2]</style> Switch to details panel{self.SPACING}'
            f'{self.STYLE}[F3]</style> Show/Hide details panel'
        )
