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
from collections.abc import MutableMapping
import json

from prompt_toolkit.application import Application

from awscli.customizations.configure.writer import ConfigFileWriter
from awscli.customizations.wizard import core
from awscli.customizations.wizard.ui.keybindings import get_default_keybindings
from awscli.customizations.wizard.ui.layout import WizardLayoutFactory
from awscli.customizations.wizard.ui.style import get_default_style
from awscli.utils import json_encoder


def create_wizard_app(definition, session):
    api_invoker = core.APIInvoker(session=session)
    shared_config = core.SharedConfigAPI(session=session,
                                         config_writer=ConfigFileWriter())
    layout_factory = WizardLayoutFactory()
    app = Application(
        key_bindings=get_default_keybindings(),
        style=get_default_style(),
        layout=layout_factory.create_wizard_layout(definition),
        full_screen=True,
    )
    app.values = WizardValues(
        definition,
        value_retrieval_steps={
            core.APICallStep.NAME: core.APICallStep(api_invoker=api_invoker),
            core.SharedConfigStep.NAME: core.SharedConfigStep(
                config_api=shared_config),
        }
    )
    app.traverser = WizardTraverser(definition, app.values)
    app.details_visible = False
    return app


class InvalidChoiceException(Exception):
    pass


class WizardTraverser:
    def __init__(self, definition, values):
        self._definition = definition
        self._values = values
        self._prompt_definitions = self._collect_prompt_definitions()
        self._prompt_to_sections = self._map_prompts_to_sections()
        self._current_prompt = self._get_starting_prompt()
        self._previous_prompts = []
        self._visited_sections = [self.get_current_section()]

    def get_current_prompt(self):
        return self._current_prompt

    def get_current_section(self):
        return self._prompt_to_sections[self._current_prompt]

    def get_current_prompt_choices(self):
        choices = self._get_choices(self._current_prompt)
        if choices:
            return [choice['display'] for choice in choices]
        return None

    def current_prompt_has_details(self):
        return 'details' in self._prompt_definitions[self._current_prompt]
    
    def submit_prompt_answer(self, answer):
        if 'choices' in self._prompt_definitions[self._current_prompt]:
            answer = self._convert_display_value_to_actual_value(
                self._get_choices(self._current_prompt),
                answer
            )
        self._values[self._current_prompt] = answer

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

    def _collect_prompt_definitions(self):
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

    def _get_choices(self, value_name):
        value_definition = self._prompt_definitions[value_name]
        if 'choices' in value_definition:
            choices = value_definition['choices']
            if not isinstance(value_definition['choices'], list):
                # When choices is declared as a variable, we want to use the
                # value from the variable.
                choices = self._values[value_definition['choices']]
            return self._get_normalized_choice_values(choices)
        return None

    def get_details_for_choice(self, choice):
        step_definition = self._prompt_definitions[self._current_prompt]
        if 'details' in step_definition:
            value = self._convert_display_value_to_actual_value(
                self._get_choices(self._current_prompt), choice
            )
            temp_values = self._values.copy()
            temp_values[self._current_prompt] = value
            details = temp_values[step_definition['details']['value']]
            return json.dumps(details, indent=2,
                              default=json_encoder)

    def _get_normalized_choice_values(self, choices):
        normalized_choices = []
        for choice in choices:
            if isinstance(choice, str):
                normalized_choices.append(
                    {
                        'display': choice,
                        'actual_value': choice
                    }
                )
            else:
                normalized_choices.append(choice)
        return normalized_choices

    def _convert_display_value_to_actual_value(self, choices, display_value):
        for choice in choices:
            if choice['display'] == display_value:
                return choice['actual_value']
        raise InvalidChoiceException(
            f"'{display_value}' is not a valid choice. Valid choices are: "
            f"{[choice['display'] for choice in choices]}"
        )

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
            return core.ConditionEvaluator().evaluate(
                value_definition['condition'], self._values
            )
        return True


class WizardValues(MutableMapping):
    def __init__(self, definition, value_retrieval_steps=None):
        self._definition = definition
        if value_retrieval_steps is None:
            value_retrieval_steps = {}
        self._value_retrieval_steps = value_retrieval_steps
        self._values = {}
        self._value_definitions = self._collect_all_value_definitions()

    def __getitem__(self, key):
        if key not in self._values and key in self._value_definitions:
            value_definition = self._value_definitions[key]
            if value_definition['type'] in self._value_retrieval_steps:
                retrieval_step = self._value_retrieval_steps[
                    value_definition['type']
                ]
                return retrieval_step.run_step(value_definition, self)
        return self._values[key]

    def __setitem__(self, key, value):
        self._values[key] = value

    def __delitem__(self, key):
        del self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def __str__(self):
        return str(self._values)

    def _collect_all_value_definitions(self):
        value_definitions = {}
        for _, section_definition in self._definition['plan'].items():
            for name, value_definition in section_definition['values'].items():
                value_definitions[name] = value_definition
        return value_definitions

    def __copy__(self):
        new_vars = type(self)(
            self._definition,
            self._value_retrieval_steps,
        )
        for varname, value in self.items():
            new_vars[varname] = value
        return new_vars

    copy = __copy__
