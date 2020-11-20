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
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings

from awscli.customizations.wizard.core import ConditionEvaluator
from awscli.customizations.wizard.ui.keybindings import get_default_keybindings
from awscli.customizations.wizard.ui.layout import WizardLayoutFactory
from awscli.customizations.wizard.ui.style import get_default_style


def create_wizard_app(definition):
    layout_factory = WizardLayoutFactory()
    app = Application(
        key_bindings=get_default_keybindings(),
        style=get_default_style(),
        layout=layout_factory.create_wizard_layout(definition),
        full_screen=True,
    )
    app.values = {}
    app.traverser = WizardTraverser(definition, app.values)
    return app


class WizardTraverser:
    def __init__(self, definition, values):
        self._definition = definition
        self._values = values
        self._prompt_definitions = self._collect_all_prompt_definitions()
        self._prompt_to_sections = self._map_prompts_to_sections()
        self._current_prompt = self._get_starting_prompt()
        self._previous_prompts = []
        self._visited_sections = [self.get_current_section()]

    def get_current_prompt(self):
        return self._current_prompt

    def get_current_section(self):
        return self._prompt_to_sections[self._current_prompt]

    def next_prompt(self):
        new_prompt = self._get_next_prompt()
        if new_prompt != self._current_prompt:
            self._previous_prompts.append(self._current_prompt)
        if self._prompt_to_sections[new_prompt] != self.get_current_section():
            self._visited_sections.append(self._prompt_to_sections[new_prompt])
        self._current_prompt = new_prompt
        return new_prompt

    def previous_prompt(self):
        if self._previous_prompts:
            previous = self._previous_prompts.pop()
            self._current_prompt = previous
        return self._current_prompt

    def is_prompt_visible(self, value_name):
        if self._prompt_to_sections[value_name] != self.get_current_section():
            return False
        return self._prompt_meets_condition(value_name)

    def has_visited_section(self, section_name):
        return section_name in self._visited_sections

    def _collect_all_prompt_definitions(self):
        value_prompt_definitions = {}
        for _, section_definition in self._definition['plan'].items():
            for name, value_definition in section_definition['values'].items():
                if value_definition['type'] == 'prompt':
                    value_prompt_definitions[name] = value_definition
        return value_prompt_definitions

    def _map_prompts_to_sections(self):
        prompts_to_sections = {}
        sections = self._definition['plan']
        for section_name, section_definition in sections.items():
            for name, value_definition in section_definition['values'].items():
                prompts_to_sections[name] = section_name
        return prompts_to_sections

    def _get_starting_prompt(self):
        return list(self._prompt_definitions)[0]

    def _get_next_prompt(self):
        prompts = list(self._prompt_definitions)
        current_pos = prompts.index(self._current_prompt)
        for prompt in prompts[current_pos+1:]:
            if self._prompt_meets_condition(prompt):
                return prompt
        return self._current_prompt

    def _prompt_meets_condition(self, value_name):
        value_definition = self._prompt_definitions[value_name]
        if 'condition' in value_definition:
            return ConditionEvaluator().evaluate(
                value_definition['condition'], self._values
            )
        return True
