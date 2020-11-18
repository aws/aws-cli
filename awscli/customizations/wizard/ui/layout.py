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
from prompt_toolkit.layout.containers import WindowAlign, HSplit
from prompt_toolkit.widgets import Label

from awscli.customizations.wizard.ui.prompt import WizardPrompt


class WizardLayoutFactory:
    def create_wizard_layout(self, defintion):
        return Layout(
            container=HSplit(
                [
                    self._create_title(defintion),
                    self._create_all_prompts(defintion)
                ],
                padding=1,
            )
        )

    def _create_title(self, definition):
        title = Label(f'{definition["title"]}', style='class:wizard.title')
        title.window.align = WindowAlign.CENTER
        return title

    def _create_all_prompts(self, definition):
        prompts = []
        for step_definition in definition['plan'].values():
            prompts.extend(
                self._create_prompts_from_step_definition(step_definition)
            )
        return HSplit(prompts, padding=0)

    def _create_prompts_from_step_definition(self, step_definition):
        prompts = []
        for value_name, value_definition in step_definition['values'].items():
            if value_definition['type'] == 'prompt':
                prompts.append(WizardPrompt(value_name, value_definition))
        return prompts
