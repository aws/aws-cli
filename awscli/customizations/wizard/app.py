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
import json
from collections.abc import MutableMapping
from traceback import format_tb


from prompt_toolkit.application import Application
from prompt_toolkit.eventloop import get_event_loop, run_until_complete

from awscli.customizations.wizard import core
from awscli.customizations.wizard.ui.style import get_default_style
from awscli.customizations.wizard.ui.keybindings import get_default_keybindings
from awscli.utils import json_encoder


class UnexpectedWizardException(Exception):
    MSG_FORMAT = (
        'Encountered unexpected exception inside of wizard:\n\n'
        'Traceback:\n{original_tb}'
        '{original_exception_cls}: {original_exception}'
    )

    def __init__(self, original_exception):
        self.original_exception = original_exception
        message = self.MSG_FORMAT.format(
            original_tb=''.join(format_tb(original_exception.__traceback__)),
            original_exception_cls=self.original_exception.__class__.__name__,
            original_exception=self.original_exception
        )
        super().__init__(message)


class InvalidChoiceException(Exception):
    pass


class UnableToRunWizardError(Exception):
    pass


class WizardAppRunner(object):
    def __init__(self, session, app_factory):
        self._session = session
        self._app_factory = app_factory

    def run(self, loaded):
        """Run a single wizard given the contents as a string."""
        app = self._app_factory(loaded, self._session)
        app.run()
        # Propagates any exceptions that got set while in the app
        app.future.result()
        print(app.traverser.get_output())


class WizardApp(Application):
    def __init__(self, layout, values, traverser, executor, style=None,
                 key_bindings=None, full_screen=True):
        self.values = values
        self.traverser = traverser
        self.executor = executor
        if style is None:
            style = get_default_style()
        if key_bindings is None:
            key_bindings = get_default_keybindings()
        self.details_visible = False
        self.error_bar_visible = None
        super().__init__(
            layout=layout, style=style, key_bindings=key_bindings,
            full_screen=full_screen
        )

    def run(self, pre_run=None, **kwargs):
        loop = get_event_loop()
        previous_exc_handler = loop.get_exception_handler()
        loop.set_exception_handler(self._handle_exception)
        try:
            f = self.run_async(pre_run=pre_run)
            run_until_complete(f)
            return f.result()
        finally:
            loop.set_exception_handler(previous_exc_handler)

    def _handle_exception(self, context):
        self.exit(
            exception=UnexpectedWizardException(context['exception'])
        )


class WizardTraverser:
    DONE = core.DONE_SECTION_NAME
    OUTPUT = core.OUTPUT_SECTION_NAME

    def __init__(self, definition, values, executor):
        self._definition = definition
        self._values = values
        self._executor = executor
        self._prompt_definitions = self._collect_prompt_definitions()
        self._prompt_to_sections = self._map_prompts_to_sections()
        self._current_prompt = self._get_starting_prompt()
        self._previous_prompts = []
        self._visited_sections = [self.get_current_section()]

    def get_current_prompt(self):
        return self._current_prompt

    def get_current_section(self):
        if self.has_no_remaining_prompts():
            return self.DONE
        return self._prompt_to_sections[self._current_prompt]

    def get_current_prompt_choices(self):
        choices = self._get_choices(self._current_prompt)
        if choices:
            return [choice['display'] for choice in choices]
        return None

    def current_prompt_has_details(self):
        return 'details' in self._prompt_definitions.get(
            self._current_prompt, {})
    
    def submit_prompt_answer(self, answer):
        if 'choices' in self._prompt_definitions[self._current_prompt]:
            answer = self._convert_display_value_to_actual_value(
                self._get_choices(self._current_prompt),
                answer
            )
        self._values[self._current_prompt] = answer

    def next_prompt(self):
        if self._current_prompt == self.DONE:
            return self._current_prompt
        new_prompt = self._get_next_prompt()
        self._previous_prompts.append(self._current_prompt)
        section_of_new_prompt = self._prompt_to_sections.get(new_prompt)
        if section_of_new_prompt != self.get_current_section():
            self._visited_sections.append(self._prompt_to_sections[new_prompt])
        self._current_prompt = new_prompt
        return new_prompt

    def previous_prompt(self):
        if self._previous_prompts:
            previous = self._previous_prompts.pop()
            self._current_prompt = previous
        return self._current_prompt

    def run_wizard(self):
        if self.has_no_remaining_prompts():
            self._executor.execute(self._definition['execute'], self._values)
        else:
            raise UnableToRunWizardError(
                'Cannot run wizard. There are prompts remaining that must '
                'be answered.'
            )

    def is_prompt_visible(self, value_name):
        if self._prompt_to_sections[value_name] != self.get_current_section():
            return False
        return self._prompt_meets_condition(value_name)

    def is_prompt_details_visible_by_default(self, value_name):
        return self._prompt_definitions[value_name].get(
            'details', {}).get('visible', False)

    def has_visited_section(self, section_name):
        return section_name in self._visited_sections

    def has_no_remaining_prompts(self):
        return self.get_current_prompt() == self.DONE

    def _collect_prompt_definitions(self):
        value_prompt_definitions = {}
        plan = self._definition['plan']
        for section_name, section_definition in plan.items():
            if section_name == self.DONE:
                continue
            for name, value_definition in section_definition['values'].items():
                if value_definition['type'] == 'prompt':
                    value_prompt_definitions[name] = value_definition
        return value_prompt_definitions

    def _map_prompts_to_sections(self):
        prompts_to_sections = {}
        sections = self._definition['plan']
        for section_name, section_definition in sections.items():
            if section_name == self.DONE:
                prompts_to_sections[section_name] = self.DONE
                continue
            for name, value_definition in section_definition['values'].items():
                prompts_to_sections[name] = section_name
        return prompts_to_sections

    def _get_starting_prompt(self):
        return list(self._prompt_definitions)[0]

    def _get_choices(self, value_name):
        value_definition = self._prompt_definitions.get(value_name, {})
        if 'choices' in value_definition:
            choices = value_definition['choices']
            if not isinstance(value_definition['choices'], list):
                # When choices is declared as a variable, we want to use the
                # value from the variable.
                choices = self._values[value_definition['choices']]
            if choices:
                return self._get_normalized_choice_values(choices)
        return None

    def get_details_title(self):
        step_definition = self._prompt_definitions[self._current_prompt]
        if 'details' in step_definition:
            return step_definition['details'].get('description')
        return ''

    def get_details_for_choice(self, choice):
        if not choice:
            return ''
        step_definition = self._prompt_definitions[self._current_prompt]
        if 'details' in step_definition:
            value = self._convert_display_value_to_actual_value(
                self._get_choices(self._current_prompt), choice
            )
            format_type = step_definition['details'].get('output', 'text')
            temp_values = self._values.copy()
            if step_definition['details']['value'] == '__selected_choice__':
                output = temp_values[value]
            else:
                temp_values[self._current_prompt] = value
                output = temp_values[step_definition['details']['value']]

            return self._format_output(output, format_type)

    def _format_output(self, output, format_type):
        if format_type == 'json':
            return json.dumps(output, indent=4, default=json_encoder)
        return output

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
        if choices:
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
        return self.DONE

    def _prompt_meets_condition(self, value_name):
        value_definition = self._prompt_definitions[value_name]
        if 'condition' in value_definition:
            return core.ConditionEvaluator().evaluate(
                value_definition['condition'], self._values
            )
        return True

    def get_output(self):
        template_step = core.TemplateStep()
        return template_step.run_step(
            self._definition[self.OUTPUT], self._values)


class WizardValues(MutableMapping):
    def __init__(self, definition, value_retrieval_steps=None,
                 exception_handler=None):
        self._definition = definition
        if value_retrieval_steps is None:
            value_retrieval_steps = {}
        self._value_retrieval_steps = value_retrieval_steps
        self._values = {}
        self._value_definitions = self._collect_all_value_definitions()
        self._exception_handler = exception_handler

    def __getitem__(self, key):
        if key not in self._values and key in self._value_definitions:
            value_definition = self._value_definitions[key]
            if value_definition['type'] in self._value_retrieval_steps:
                retrieval_step = self._value_retrieval_steps[
                    value_definition['type']
                ]
                try:
                    return retrieval_step.run_step(value_definition, self)
                except Exception as e:
                    if self._exception_handler is not None:
                        return self._exception_handler(e)
                    raise
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
        plan = self._definition['plan']
        for section_name, section_definition in plan.items():
            if section_name == core.DONE_SECTION_NAME:
                continue
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
