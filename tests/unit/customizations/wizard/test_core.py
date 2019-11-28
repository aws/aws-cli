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
import os
import ruamel.yaml as yaml

from botocore.session import Session

from awscli.customizations.configure.writer import ConfigFileWriter
from awscli.customizations.wizard import core
from awscli.customizations.wizard import ui
from awscli.testutils import unittest, mock, temporary_file


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
                'yesno-prompt': core.YesNoPrompt(self.prompter),
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
        parameters = self.planner.plan(loaded['plan'])
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

        parameters = self.planner.plan(loaded['plan'])
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

        parameters = self.planner.plan(loaded['plan'])
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

        parameters = self.planner.plan(loaded['plan'])
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

        parameters = self.planner.plan(loaded['plan'])
        self.assertEqual(parameters['name'], 'admin')
        self.assertEqual(
            self.prompter.recorded_prompts,
            [('Enter user name', 'admin', [{'display': 'Administrator',
                                             'actual_value': 'admin'},
                                            {'display': 'Developer',
                                             'actual_value': 'dev'}])],
        )

    def test_can_prompt_with_types(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              name:
                type: prompt
                description: Enter a string
                datatype: str
              age:
                type: prompt
                description: Enter an int
                datatype: int
              float:
                type: prompt
                description: Enter a float
                datatype: float
              trueval:
                type: prompt
                description: Enter a true value
                datatype: bool
              falseval:
                type: prompt
                description: Enter a false value
                datatype: bool
        """)
        # The responses will always return string values.
        self.responses['Enter a string'] = 'myname'
        self.responses['Enter an int'] = '100'
        self.responses['Enter a float'] = '2.0'
        self.responses['Enter a true value'] = 'true'
        self.responses['Enter a false value'] = 'false'

        parameters = self.planner.plan(loaded['plan'])
        self.assertEqual(parameters['name'], 'myname')
        self.assertEqual(parameters['age'], 100)
        self.assertEqual(parameters['float'], 2.0)
        self.assertEqual(parameters['trueval'], True)
        self.assertEqual(parameters['falseval'], False)

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

        parameters = self.planner.plan(loaded['plan'])
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

        parameters = self.planner.plan(loaded['plan'])
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
        api_step = core.APICallStep(
            api_invoker=core.APIInvoker(session=mock_session)
        )
        planner = core.Planner(
            step_handlers={
                'apicall': api_step,
            },
        )
        parameters = planner.plan(loaded['plan'])
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
        api_step = core.APICallStep(
            api_invoker=core.APIInvoker(session=mock_session)
        )
        planner = core.Planner(
            step_handlers={
                'apicall': api_step,
            },
        )
        parameters = planner.plan(loaded['plan'])
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
        parameters = self.planner.plan(loaded['plan'])
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
        parameters = self.planner.plan(loaded['plan'])
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

        parameters = self.planner.plan(loaded['plan'])
        self.assertEqual(parameters['name'], 'admin')
        self.assertEqual(
            self.prompter.recorded_prompts,
            [('Enter user name', 'admin', [{'display': 'Administrator',
                                             'actual_value': 'admin'},
                                            {'display': 'Developer',
                                             'actual_value': 'dev'}])],
        )

    def test_can_run_fileprompt_step(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              foo:
                type: fileprompt
                description: Select file
        """)
        prompter = mock.Mock(spec=ui.UIFilePrompter)
        prompter.prompt.return_value = 'myfile.txt'
        planner = core.Planner(
            step_handlers={
                'fileprompt': core.FilePromptStep(prompter=prompter),
            },
        )
        parameters = planner.plan(loaded['plan'])
        self.assertEqual(parameters['foo'],
                         os.path.abspath('myfile.txt'))

    def test_can_run_yes_no_prompt_step(self):
        loaded = load_wizard("""
        plan:
          test:
            values:
              wants_defaults:
                type: yesno-prompt
                question: "Do you want to use the defaults?"
        """)
        self.responses['Do you want to use the defaults?'] = 'yes'

        parameters = self.planner.plan(loaded['plan'])
        self.assertEqual(parameters['wants_defaults'], 'yes')
        self.assertEqual(
            self.prompter.recorded_prompts,
            [('Do you want to use the defaults?',
              'yes',
              [{'display': 'Yes', 'actual_value': 'yes'},
               {'display': 'No', 'actual_value': 'no'}])],
        )

    def test_can_set_default_yes_no_value(self):
        loaded = load_wizard("""
        plan:
          test:
            values:
              wants_defaults:
                type: yesno-prompt
                question: "Do you want to use the defaults?"
                start_value: no
        """)
        self.responses['Do you want to use the defaults?'] = 'no'

        parameters = self.planner.plan(loaded['plan'])
        self.assertEqual(
            self.prompter.recorded_prompts[0][2],
            # The default is No so it should be presented first.
            [{'display': 'No', 'actual_value': 'no'},
             {'display': 'Yes', 'actual_value': 'yes'}]
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

        parameters = self.planner.plan(loaded['plan'])
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
        parameters = custom_planner.plan(loaded['plan'])
        self.assertEqual(parameters['name'], 'myreturnvalue')

    def test_can_load_profiles(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              foo:
                type: sharedconfig
                operation: ListProfiles
        """)
        config_api = mock.Mock(spec=core.SharedConfigAPI)
        config_api.list_profiles.return_value = ['profile1', 'profile2']
        sharedconfig = core.SharedConfigStep(
            config_api=config_api,
        )
        planner = core.Planner(
            step_handlers={
                'sharedconfig': sharedconfig,
            },
        )
        parameters = planner.plan(loaded['plan'])
        self.assertEqual(parameters['foo'], ['profile1', 'profile2'])

    def test_can_read_config_profile_data(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              foo:
                type: sharedconfig
                operation: GetValue
                params:
                  profile: devprofile
                  value: region
        """)
        config_api = mock.Mock(spec=core.SharedConfigAPI)
        config_api.get_value.return_value = 'us-west-2'
        sharedconfig = core.SharedConfigStep(
            config_api=config_api,
        )
        planner = core.Planner(
            step_handlers={
                'sharedconfig': sharedconfig,
            },
        )
        parameters = planner.plan(loaded['plan'])
        self.assertEqual(parameters['foo'], 'us-west-2')
        config_api.get_value.assert_called_with(profile='devprofile',
                                                value='region')


class TestExecutor(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock(spec=Session)
        self.client = mock.Mock()
        self.session.create_client.return_value = self.client
        self.mock_config_writer = mock.Mock(spec=ConfigFileWriter)
        self.shared_config_file = 'shared-config-file'
        self.config_api = mock.Mock(spec=core.SharedConfigAPI)
        self.executor = core.Executor(
            step_handlers={
                'apicall': core.APICallExecutorStep(
                    core.APIInvoker(session=self.session),
                ),
                'sharedconfig': core.SharedConfigExecutorStep(
                    config_api=self.config_api,
                ),
                'define-variable': core.DefineVariableStep(),
                'merge-dict': core.MergeDictStep(),
            }
        )

    def test_can_make_api_call_with_params(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: apicall
              operation: iam.CreateUser
              params:
                UserName: admin
        """)
        self.executor.execute(loaded['execute'], {})
        self.session.create_client.assert_called_with('iam')
        self.client.create_user.assert_called_with(UserName='admin')

    def test_can_make_api_call_with_optional_params(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: apicall
              operation: iam.CreateUser
              params:
                UserName: admin
              optional_params:
                Path: "/foo"
        """)
        self.executor.execute(loaded['execute'], {})
        self.session.create_client.assert_called_with('iam')
        self.client.create_user.assert_called_with(
            UserName='admin', Path='/foo')

    def test_optional_params_not_passed_if_none(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: apicall
              operation: iam.CreateUser
              params:
                UserName: admin
              optional_params:
                # Omitted because the value is null.
                Path: null
        """)
        self.executor.execute(loaded['execute'], {})
        self.session.create_client.assert_called_with('iam')
        self.client.create_user.assert_called_with(UserName='admin')

    def test_can_make_conditional_api_call(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: apicall
              condition:
                variable: should_invoke
                equals: yes
              operation: iam.CreateUser
              params:
                UserName: admin
        """)
        self.executor.execute(loaded['execute'], {'should_invoke': 'no'})
        self.assertFalse(self.session.create_client.called)
        self.assertFalse(self.client.create_user.called)

    def test_can_make_conditional_on_env_var_not_exists(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: apicall
              condition:
                variable: does_not_exist
                equals: null
              operation: iam.CreateUser
              params:
                UserName: admin
        """)
        self.executor.execute(loaded['execute'], {})
        self.assertTrue(self.session.create_client.called)
        self.assertTrue(self.client.create_user.called)

    def test_can_have_multiple_conditions(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: apicall
              condition:
                - variable: foo
                  equals: one
                - variable: bar
                  equals: two
              operation: iam.CreateUser
              params:
                UserName: admin
        """)
        self.executor.execute(loaded['execute'], {'foo': 'one', 'bar': 'two'})
        self.assertTrue(self.session.create_client.called)
        self.assertTrue(self.client.create_user.called)

    def test_multiple_conditions_one_false(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: apicall
              condition:
                - variable: foo
                  equals: one
                - variable: bar
                  equals: two
              operation: iam.CreateUser
              params:
                UserName: admin
        """)
        self.executor.execute(loaded['execute'], {'foo': 'one', 'bar': 'NOTTWO'})
        self.assertFalse(self.session.create_client.called)

    def test_can_recursively_template_variables_in_params(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: apicall
              operation: iam.CreateUser
              params:
                UserName: "{foo}"
                Nested:
                  Variable: "{foo}"
                ListType:
                  - one
                  - "{foo}"
                ComboNest:
                  Foo:
                    - Bar: "{foo}"
                    - Baz: "{foo}"
        """)
        self.executor.execute(loaded['execute'], {'foo': 'FOOVALUE'})
        self.session.create_client.assert_called_with('iam')
        expected_params = {
            'UserName': 'FOOVALUE',
            'Nested': {
                'Variable': 'FOOVALUE',
            },
            'ListType': ['one', 'FOOVALUE'],
            'ComboNest': {
                'Foo': [
                    {'Bar': 'FOOVALUE'},
                    {'Baz': 'FOOVALUE'},
                ]
            }
        }
        self.client.create_user.assert_called_with(**expected_params)

    def test_can_store_output_vars(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: apicall
              operation: iam.CreateRole
              params:
                RoleName: admin
              output_var: role_arn
              query: Role.Arn
        """)
        params = {}
        self.client.create_role.return_value = {
            'Role': {'Arn': 'my-role-arn'},
        }
        self.executor.execute(loaded['execute'], params)
        self.client.create_role.assert_called_with(RoleName='admin')
        # We should have added 'role_arn' to the params dict and also
        # applied the jmespath query to the response before storing the
        # value.
        self.assertEqual(params['role_arn'], 'my-role-arn')

    def test_executes_multiple_groups(self):
        # We may introduce a 'next_step' similar to what you can do
        # in the planner, but for now, we just execute all steps sequentially
        # in the executor.
        loaded = load_wizard("""
        execute:
          default:
            - type: apicall
              operation: iam.CreateUser
              params:
                UserName: admin
          createrole:
            - type: apicall
              operation: iam.CreateRole
              params:
                RoleName: admin
        """)
        self.executor.execute(loaded['execute'], {})
        self.session.create_client.assert_called_with('iam')
        self.assertEqual(
            self.client.method_calls,
            [mock.call.create_user(UserName='admin'),
             mock.call.create_role(RoleName='admin')]
        )

    def test_can_write_to_config_file(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: sharedconfig
              operation: SetValues
              profile: mydevprofile
              params:
                region: us-west-2
                output: json
        """)
        self.executor.execute(loaded['execute'], {})
        self.config_api.set_values.assert_called_with(
             {'region': 'us-west-2', 'output': 'json'},
            profile='mydevprofile',
        )

    def test_writes_to_default_profile_if_omitted(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: sharedconfig
              operation: SetValues
              params:
                region: us-west-2
                output: json
        """)
        self.executor.execute(loaded['execute'], {})
        self.config_api.set_values.assert_called_with(
            {'region': 'us-west-2', 'output': 'json'}, profile=None
        )

    def test_can_expand_vars(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: sharedconfig
              operation: SetValues
              params:
                region: "{foo}"
        """)
        variables = {'foo': 'bar'}
        self.executor.execute(loaded['execute'], variables)
        self.config_api.set_values.assert_called_with(
            {'region': 'bar'}, profile=None)

    def test_can_define_variables(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: define-variable
              varname: myvar
              value:
                foo: bar
        """)
        variables = {}
        self.executor.execute(loaded['execute'], variables)
        self.assertEqual(variables, {'myvar': {'foo': 'bar'}})

    def test_can_reference_variables_in_definition(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: define-variable
              varname: myvar
              value:
                foo: "{bar}"
        """)
        variables = {"bar": "value-of-bar"}
        self.executor.execute(loaded['execute'], variables)
        self.assertEqual(variables, {'myvar': {'foo': 'value-of-bar'},
                                     'bar': 'value-of-bar'})

    def test_can_merge_dicts(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: define-variable
              varname: myvar
              value:
                foo: original-foo
                bar: original-bar
                baz: original-baz
            - type: merge-dict
              output_var: result
              overlays:
              - "{myvar}"
              - bar: FIRST-NEW-BAR
                baz: FIRST-NEW-BAZ
              - baz: SECOND-NEW-BAZ
                newkey: newvalue
        """)
        variables = {}
        self.executor.execute(loaded['execute'], variables)
        expected = {
            'foo': 'original-foo',
            'bar': 'FIRST-NEW-BAR',
            'baz': 'SECOND-NEW-BAZ',
            'newkey': 'newvalue',
        }
        self.assertEqual(variables['result'], expected)

    def test_can_merge_nested_dicts(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: define-variable
              varname: myvar
              value:
                foo:
                  bar:
                    baz: original-baz
                    baz2: original-baz2
                foo2: original-foo2
            - type: merge-dict
              output_var: result
              overlays:
              - "{myvar}"
              - foo:
                  bar:
                    baz: new-baz
                  bar2: new-bar2
        """)
        variables = {}
        self.executor.execute(loaded['execute'], variables)
        expected = {
            'foo': {'bar': {'baz': 'new-baz', 'baz2': 'original-baz2'},
                    'bar2': 'new-bar2'},
            'foo2': 'original-foo2',
        }
        self.assertEqual(variables['result'], expected)

    def test_can_merge_dicts_with_vars(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: define-variable
              varname: myvar
              value:
                foo:
                  bar:
                    baz: original-baz
                    baz2: original-baz2
                foo2: original-foo2
            - type: define-variable
              varname: myvar2
              value:
                foo:
                  bar:
                    baz: new-baz
                    baz2: original-baz2
                  bar2: new-bar2
            - type: merge-dict
              output_var: result
              overlays:
              - "{myvar}"
              - "{myvar2}"
        """)
        variables = {}
        self.executor.execute(loaded['execute'], variables)
        expected = {
            'foo': {'bar': {'baz': 'new-baz', 'baz2': 'original-baz2'},
                    'bar2': 'new-bar2'},
            'foo2': 'original-foo2',
        }
        self.assertEqual(variables['result'], expected)

    def test_can_replace_merged_bar(self):
        loaded = load_wizard("""
        execute:
          default:
            - type: define-variable
              varname: myvar
              value:
                foo: bar
            - type: merge-dict
              output_var: myvar
              overlays:
              - "{myvar}"
              - foo: new
        """)
        variables = {}
        self.executor.execute(loaded['execute'], variables)
        self.assertEqual(variables, {'myvar': {'foo': 'new'}})


class TestSharedConfigAPI(unittest.TestCase):
    def setUp(self):
        self.mock_session = mock.Mock(spec=Session)
        self.config_writer = mock.Mock(spec=ConfigFileWriter)
        self.config_filename = 'foo'
        self.mock_session.get_config_variable.return_value = \
            self.config_filename
        self.config_api = core.SharedConfigAPI(self.mock_session,
                                               self.config_writer)

    def test_delegates_to_config_writer(self):
        self.config_api.set_values({'foo': 'bar'}, profile='bar')
        self.config_writer.update_config.assert_called_with(
            {'foo': 'bar', '__section__': 'profile bar'},
             self.config_filename)

    def test_can_get_config_values(self):
        self.mock_session.get_config_variable.return_value = 'bar'
        self.assertEqual(self.config_api.get_value('foo'), 'bar')
        self.mock_session.get_config_variable.assert_called_with('foo')

    def test_can_list_profiles(self):
        self.mock_session.available_profiles = ['foo', 'bar']
        result = self.config_api.list_profiles()
        self.assertEqual(result, ['foo', 'bar'])


class TestRunner(unittest.TestCase):
    def setUp(self):
        self.planner = mock.Mock(spec=core.Planner)
        self.executor = mock.Mock(spec=core.Executor)
        self.runner = core.Runner(self.planner, self.executor)

    def test_can_delegate_to_obs(self):
        loaded = load_wizard("""
        plan:
          start:
            values:
              name:
                type: prompt
                description: Enter user name
        execute:
          default:
            - type: apicall
              operation: iam.CreateUser
              params:
                UserName: admin
        """)
        params = {'foo': 'bar'}
        self.planner.plan.return_value = params
        self.runner.run(wizard_spec=loaded)

        self.planner.plan.assert_called_with(loaded['plan'])
        self.executor.execute.assert_called_with(loaded['execute'], params)


class TestAPIInvoker(unittest.TestCase):
    def setUp(self):
        self.mock_session = mock.Mock(spec=Session)

    def get_call_args(self, session):
        return session.create_client.return_value.create_user.call_args

    def test_can_make_api_call(self):
        invoker = core.APIInvoker(self.mock_session)
        invoker.invoke(
            'iam',
            'CreateUser',
            api_params={'UserName': 'admin'},
            plan_variables={}
        )
        call_method_args = self.get_call_args(self.mock_session)
        self.assertEqual(call_method_args, mock.call(UserName='admin'))

    def test_can_invoke_with_plan_variables(self):
        invoker = core.APIInvoker(self.mock_session)
        invoker.invoke(
            'iam',
            'CreateUser',
            api_params={'UserName': '{username}'},
            plan_variables={'username': 'admin'}
        )
        call_method_args = self.get_call_args(self.mock_session)
        self.assertEqual(call_method_args, mock.call(UserName='admin'))

    def test_can_open_file_with_builtin_function(self):
        invoker = core.APIInvoker(self.mock_session)
        with temporary_file('r+') as f:
            f.write('admin')
            f.flush()
            invoker.invoke(
                'iam',
                'CreateUser',
                # There's two parts to this test.  First, we have the
                # filename stored as a variable.
                plan_variables={'myfile': f.name},
                api_params={
                    # Then we reference the file with the builtin File
                    # type.  We should replace this entire value with
                    # the contents of the temp file ('admin').
                    'UserName': {'__wizard__:File': {'path': '{myfile}'}},
                },
            )
        call_method_args = self.get_call_args(self.mock_session)
        self.assertEqual(call_method_args, mock.call(UserName=b'admin'))
