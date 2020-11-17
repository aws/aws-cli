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
from prompt_toolkit.layout.containers import WindowAlign, HSplit, VSplit
from prompt_toolkit.widgets import Label, HorizontalLine

from awscli.customizations.wizard.ui.section import (
    WizardSectionTab, WizardSectionBody
)
from awscli.customizations.wizard.ui.utils import Spacer


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
                HSplit(section_bodies)
            ]
        )

    def _create_section_tab(self, section_name, section_definition):
        return WizardSectionTab(section_name, section_definition)

    def _create_section_body(self, section_name, section_definition):
        return WizardSectionBody(section_name, section_definition)
