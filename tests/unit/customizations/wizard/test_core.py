# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import ruamel.yaml as yaml

from botocore.session import Session

from awscli.customizations.wizard import core
from awscli.testutils import unittest, mock


def load_wizard(yaml_str):
    data = yaml.load(yaml_str, Loader=yaml.RoundTripLoader)
    return data


class FakePrompter(object):
    def __init__(self, responses):
        self.responses = responses
        self.recorded_prompts = []

    def prompt(self, text, choices=None):
        response = self.responses.get(text)
        if choices is not None:
            entry = text, response, choices
        else:
            entry = text, response
        self.recorded_prompts.append(entry)
        return response


class TestPlanner(unittest.TestCase):
    def setUp(self):
        self.responses = {}
        self.prompter = FakePrompter(self.responses)
        self.planner = core.Planner(
            step_handlers={
                'static': core.StaticStep(),
                'prompt': core.PromptStep(self.prompter),
                'template': core.TemplateStep(),
            }
        )

    def test_can_prompt_for_single_value(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              name:
                type: prompt
                description: Enter user name
        """)

        self.responses['Enter user name'] = 'admin'
        parameters = self.planner.run(loaded['plan'])
        self.assertEqual(parameters['name'], 'admin')

    def test_can_prompt_for_multiple_values_in_order(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              name:
                type: prompt
                description: Enter user name
              group:
                type: prompt
                description: Enter group name
        """)
        self.responses['Enter user name'] = 'myname'
        self.responses['Enter group name'] = 'wheel'

        parameters = self.planner.run(loaded['plan'])
        self.assertEqual(parameters['name'], 'myname')
        self.assertEqual(parameters['group'], 'wheel')
        # We should also have prompted in the order that the keys
        # were defined.
        self.assertEqual(
            self.prompter.recorded_prompts,
            [('Enter user name', 'myname'),
             ('Enter group name', 'wheel')],
        )

    def test_can_prompt_for_conditional_values_true(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              should_stop:
                type: prompt
                description: Should we stop
            next_step:
              switch: should_stop
              yes: DONE
              no: ask_name
          ask_name:
            values:
              name:
                type: prompt
                description: Enter user name
        """)
        self.responses['Should we stop'] = 'no'
        self.responses['Enter user name'] = 'admin'

        parameters = self.planner.run(loaded['plan'])
        self.assertEqual(parameters['should_stop'], 'no')
        self.assertEqual(parameters['name'], 'admin')
        self.assertEqual(
            self.prompter.recorded_prompts,
            [('Should we stop', 'no'),
             ('Enter user name', 'admin')],
        )

    def test_can_prompt_for_conditional_values_false(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              should_stop:
                type: prompt
                description: Should we stop
            next_step:
              switch: should_stop
              yes: DONE
              no: ask_name
          ask_name:
            values:
              name:
                type: prompt
                description: Enter user name
        """)
        self.responses['Should we stop'] = 'yes'

        parameters = self.planner.run(loaded['plan'])
        self.assertEqual(parameters['should_stop'], 'yes')
        self.assertNotIn('name', parameters)
        self.assertEqual(
            self.prompter.recorded_prompts,
            [('Should we stop', 'yes')],
        )

    def test_can_prompt_with_choices_for_prompt(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              name:
                type: prompt
                description: Enter user name
                choices:
                    - display: Administrator
                      actual_value: admin
                    - display: Developer
                      actual_value: dev
        """)
        self.responses['Enter user name'] = 'admin'

        parameters = self.planner.run(loaded['plan'])
        self.assertEqual(parameters['name'], 'admin')
        self.assertEqual(
            self.prompter.recorded_prompts,
            [('Enter user name', 'admin', [{'display': 'Administrator',
                                             'actual_value': 'admin'},
                                            {'display': 'Developer',
                                             'actual_value': 'dev'}])],
        )

    def test_special_step_done_stops_run(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              foo:
                type: prompt
                description: Foo
            next_step: DONE
          # This step will never be executed.
          never_used:
            values:
              bar:
                type: prompt
                description: Bar
        """)
        self.responses['Foo'] = 'foo-value'

        parameters = self.planner.run(loaded['plan'])
        self.assertEqual(parameters['foo'], 'foo-value')
        self.assertNotIn('bar', parameters)
        self.assertEqual(
            self.prompter.recorded_prompts,
            # We never prompt for the 'bar' value.
            [('Foo', 'foo-value'),]
        )

    def test_can_run_template_step(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              foo:
                type: prompt
                description: Foo
              bar:
                type: template
                value: "template-{foo}"
        """)
        self.responses['Foo'] = 'foo-value'

        parameters = self.planner.run(loaded['plan'])
        self.assertEqual(parameters['foo'], 'foo-value')
        self.assertEqual(parameters['bar'], 'template-foo-value')
        self.assertEqual(
            self.prompter.recorded_prompts,
            [('Foo', 'foo-value'),]
        )

    def test_can_run_apicall_step(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              foo:
                type: apicall
                operation: iam.ListPolicies
                params:
                  Scope: AWS
        """)
        mock_session = mock.Mock(spec=Session)
        mock_client = mock.Mock()
        mock_session.create_client.return_value = mock_client
        mock_client.list_policies.return_value = {
            'Policies': ['foo'],
        }
        api_step = core.APICallStep(session=mock_session)
        planner = core.Planner(
            step_handlers={
                'apicall': api_step,
            },
        )
        parameters = planner.run(loaded['plan'])
        self.assertEqual(parameters['foo'], {'Policies': ['foo']})

    def test_can_run_apicall_step_with_query(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              foo:
                type: apicall
                operation: iam.ListPolicies
                params:
                  Scope: AWS
                query: Policies[].Name
        """)
        mock_session = mock.Mock(spec=Session)
        mock_client = mock.Mock()
        mock_session.create_client.return_value = mock_client
        mock_client.list_policies.return_value = {
            'Policies': [{'Name': 'one'}, {'Name': 'two'}],
        }
        api_step = core.APICallStep(session=mock_session)
        planner = core.Planner(
            step_handlers={
                'apicall': api_step,
            },
        )
        parameters = planner.run(loaded['plan'])
        # Note this value is the result is applying the
        # Polices[].Name jmespath query to the response.
        self.assertEqual(parameters['foo'], ['one', 'two'])

    def test_can_use_static_value(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              foo:
                type: static
                value: myvalue
        """)
        parameters = self.planner.run(loaded['plan'])
        self.assertEqual(parameters['foo'], 'myvalue')

    def test_can_use_static_value_as_non_string_type(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              foo:
                type: static
                value: [1, 2, 3]
        """)
        parameters = self.planner.run(loaded['plan'])
        self.assertEqual(parameters['foo'], [1, 2, 3])

    def test_choices_can_be_variable_reference(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              choices_var:
                type: static
                value:
                  - display: Administrator
                    actual_value: admin
                  - display: Developer
                    actual_value: dev
              name:
                type: prompt
                description: Enter user name
                choices: choices_var
        """)
        self.responses['Enter user name'] = 'admin'

        parameters = self.planner.run(loaded['plan'])
        self.assertEqual(parameters['name'], 'admin')
        self.assertEqual(
            self.prompter.recorded_prompts,
            [('Enter user name', 'admin', [{'display': 'Administrator',
                                             'actual_value': 'admin'},
                                            {'display': 'Developer',
                                             'actual_value': 'dev'}])],
        )

    def test_can_jump_around_to_next_steps(self):
        # This test shows that you can specify an explicit
        # next step name to jump to.
        loaded = load_wizard("""
        plan:
          step_a:
            values:
              first:
                type: prompt
                description: step_a
            next_step: step_d
          step_b:
            values:
              fourth:
                type: prompt
                description: step_b
            next_step: DONE
          step_c:
            values:
              third:
                type: prompt
                description: step_c
            next_step: step_b
          step_d:
            values:
              second:
                type: prompt
                description: step_d
            next_step: step_c
        """)
        # Note the order here, we should run the steps
        # in this order: step_a, step_d, step_c, step_b
        self.responses['step_a'] = 'one'
        self.responses['step_d'] = 'two'
        self.responses['step_c'] = 'three'
        self.responses['step_b'] = 'four'

        parameters = self.planner.run(loaded['plan'])
        self.assertEqual(parameters['first'], 'one')
        self.assertEqual(parameters['second'], 'two')
        self.assertEqual(parameters['third'], 'three')
        self.assertEqual(parameters['fourth'], 'four')
        self.assertEqual(
            self.prompter.recorded_prompts,
            [('step_a', 'one'),
             ('step_d', 'two'),
             ('step_c', 'three'),
             ('step_b', 'four')],
        )

    def test_can_delegate_to_arbitrary_type(self):

        class CustomStep(core.BaseStep):
            def run_step(self, step_definition, parameters):
                # Just return whatever the value of 'foo' is in the
                # step definition.
                return step_definition['foo']

        custom_step = CustomStep()
        custom_planner = core.Planner(
            step_handlers={
                'customstep': custom_step,
            },
        )
        loaded = load_wizard("""
        plan:
          start:
            values:
              name:
                type: customstep
                foo: myreturnvalue
        """)
        parameters = custom_planner.run(loaded['plan'])
        self.assertEqual(parameters['name'], 'myreturnvalue')
