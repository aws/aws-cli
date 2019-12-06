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
"""Core planner and executor for wizards."""
import re
import jmespath
import os

from botocore import xform_name


class Runner(object):
    def __init__(self, planner, executor):
        self._planner = planner
        self._executor = executor

    def run(self, wizard_spec):
        params = self._planner.plan(wizard_spec['plan'])
        self._executor.execute(wizard_spec['execute'], params)


class Planner(object):
    _DONE_STEP = 'DONE'
    _STOP_RUNNING = object()

    def __init__(self, step_handlers):
        self._step_handlers = step_handlers
        # These will hold the values we store from
        # running through the plan steps.
        self._parameters = {}

    def plan(self, plan):
        self._parameters.clear()
        steps_iter = self._steps(plan)
        step = next(steps_iter)
        while step is not self._STOP_RUNNING:
            next_step_name = self._run_plan_step(step)
            step = steps_iter.send(next_step_name)
        return self._parameters

    def _steps(self, plan):
        step_names = list(plan)
        step_index = 0
        step_name = step_names[step_index]
        while True:
            next_step_name = yield plan[step_name]
            if next_step_name == self._DONE_STEP:
                yield self._STOP_RUNNING
            elif next_step_name is None:
                # If no explicit step is given, we go on to the next
                # sequential step.
                step_index += 1
                if step_index == len(step_names):
                    # If this is the last step, we're done with the
                    # plan phase.
                    yield self._STOP_RUNNING
                step_name = step_names[step_index]
            else:
                # If an explicit name is given we find the index
                # of the step name and update accordingly.
                step_index = step_names.index(next_step_name)
                step_name = next_step_name

    def _run_plan_step(self, step):
        # Running step consists of first fetching any values
        # based on what's defined in `values`.
        for key, value in step['values'].items():
            step_type = value['type']
            handler = self._step_handlers[step_type]
            response = handler.run_step(value, self._parameters)
            self._parameters[key] = response
        # And next we need to figure out if there's a next
        # step we need to resolve.  If the key is not defined
        # for this step we return None which results in moving
        # on to the next sequential step.
        if 'next_step' not in step:
            return
        return self._decide_next_step_name(step['next_step'])

    def _decide_next_step_name(self, next_step):
        if isinstance(next_step, str):
            # If an explicit step name is provided, we don't need to do
            # anything further.
            return next_step
        if 'switch' in next_step:
            varname = next_step['switch']
            value = self._parameters.get(varname)
            return next_step[value]


class BaseStep(object):
    # Subclasses must implement this.  This defines the name you'd
    # use for the `type` in a wizard definition.
    NAME = ''

    def run_step(self, step_definition, parameters):
        raise NotImplementedError("run_step")


class StaticStep(BaseStep):

    NAME = 'static'

    def run_step(self, step_definition, parameters):
        return step_definition['value']


class PromptStep(BaseStep):

    NAME = 'prompt'

    def __init__(self, prompter):
        self._prompter = prompter
        self._conversion_funcs = {
            'int': int,
            'float': float,
            'str': str,
            'bool': lambda x: True if x.lower() == 'true' else False
        }

    def run_step(self, step_definition, parameters):
        choices = self._get_choices(step_definition, parameters)
        response = self._prompter.prompt(step_definition['description'],
                                         choices=choices)
        return self._convert_data_type_if_needed(response, step_definition)

    def _get_choices(self, step_definition, parameters):
        choices = step_definition.get('choices')
        if choices is not None:
            if isinstance(choices, str):
                # If 'choices' is a string, we assume it's the name of
                # a variable.
                return parameters[choices]
            return choices

    def _convert_data_type_if_needed(self, response, step_definition):
        if 'datatype' not in step_definition:
            return response
        return self._conversion_funcs[step_definition['datatype']](response)


class YesNoPrompt(PromptStep):
    """Shorthand for a yes/no prompt.

    Asking yes/no questions is common enough in wizards that
    this class provides a shorthand for doing this instead of having
    to write out the long form version using the general ``prompt``
    step.

    """

    NAME = 'yesno-prompt'

    def run_step(self, step_definition, parameters):
        choices = [
            {'display': 'Yes', 'actual_value': 'yes'},
            {'display': 'No', 'actual_value': 'no'},
        ]
        if step_definition.get('start_value', 'yes') == 'no':
            # They want the "No" choice to be the starting value so we
            # need to reverse the choices.
            choices[:] = choices[::-1]
        response = self._prompter.prompt(step_definition['question'],
                                         choices=choices)
        return response


class FilePromptStep(BaseStep):

    NAME = 'fileprompt'

    def __init__(self, prompter):
        self._prompter = prompter

    def run_step(self, step_definition, parameters):
        response = self._prompter.prompt(step_definition['description'])
        return os.path.expanduser(os.path.abspath(response))


class TemplateStep(BaseStep):

    NAME = 'template'

    def run_step(self, step_definition, parameters):
        value = step_definition['value']
        return value.format(**parameters)


class APICallStep(BaseStep):

    NAME = 'apicall'

    def __init__(self, api_invoker):
        self._api_invoker = api_invoker

    def run_step(self, step_definition, parameters):
        service, op_name = step_definition['operation'].split('.', 1)
        return self._api_invoker.invoke(
            service=service, operation=op_name,
            api_params=step_definition['params'],
            plan_variables=parameters,
            optional_api_params=step_definition.get('optional_params'),
            query=step_definition.get('query'),
        )


class SharedConfigStep(BaseStep):

    NAME = 'sharedconfig'

    def __init__(self, config_api):
        self._config_api = config_api

    def run_step(self, step_definition, parameters):
        if step_definition['operation'] == 'ListProfiles':
            return self._config_api.list_profiles()
        elif step_definition['operation'] == 'GetValue':
            return self._config_api.get_value(
                profile=step_definition['params'].get('profile'),
                value=step_definition['params']['value'],
            )


class VariableResolver(object):

    _VAR_MATCH = re.compile(r'^{(.*?)}$')

    def resolve_variables(self, variables, params):
        """Replace references to variables with their values.

        Example::

            VariableResolver().resolve_variables(
              {'foo': 'bar'},
              {'MyValue': "{foo}"},
            ) == {'MyValue': 'bar'}

        """
        return self._resolve_vars(params, variables)

    def _resolve_vars(self, value, plan_vars):
        if isinstance(value, str):
            is_variable_ref = self._VAR_MATCH.search(value)
            if is_variable_ref:
                varname = is_variable_ref.group(1)
                return plan_vars[varname]
            return value
        elif isinstance(value, list):
            final = []
            for v in value:
                final.append(self._resolve_vars(v, plan_vars))
            return final
        elif isinstance(value, dict):
            final = {}
            for k, v in value.items():
                final[k] = self._resolve_vars(v, plan_vars)
            final = self._resolve_functions(final)
            return final
        else:
            return value

    def _resolve_functions(self, value):
        if len(value) != 1:
            return value
        only_key = list(value)[0]
        # The built in functions will likely move to another module
        # as we start to add more.
        if only_key == '__wizard__:File':
            filename = value[only_key]['path']
            with open(filename, 'rb') as f:
                return f.read()
        return value




class APIInvoker(object):
    """This class contains shared logic for the apicall step.

    The ``apicall`` in the planner and executor are slightly different
    but share a lot of similar logic.  This class is used share logic
    between the two steps.

    """
    def __init__(self, session):
        self._session = session

    def invoke(self, service, operation, api_params, plan_variables,
               optional_api_params=None, query=None):
        # TODO: All of the params that come from prompting the user
        # are strings.  We need a way to convert values to their
        # appropriate types.  We can either add typing into the wizard
        # spec or we possibly auto-convert based on the service
        # model (or both).
        client = self._session.create_client(service)
        resolved_params = self._resolve_params(
            api_params, optional_api_params, plan_variables)
        response = getattr(client, xform_name(operation))(**resolved_params)
        if query is not None:
            response = jmespath.search(query, response)
        return response

    def _resolve_params(self, api_params, optional_params, plan_vars):
        resolver = VariableResolver()
        api_params_resolved = resolver.resolve_variables(
            plan_vars, api_params)
        if optional_params is not None:
            optional_params_resolved = resolver.resolve_variables(
                plan_vars, optional_params)
            for key, value in optional_params_resolved.items():
                if key not in api_params_resolved and value is not None:
                    api_params_resolved[key] = value
        return api_params_resolved


class Executor(object):

    def __init__(self, step_handlers):
        self._step_handlers = step_handlers

    def execute(self, step, parameters):
        # We may eventually support jumping around to different step
        # names, but for now, we just iterate through the steps in order.
        for group in step.values():
            for step in group:
                self._execute_step(step, parameters)

    def _execute_step(self, step, parameters):
        if 'condition' in step:
            should_run = self._check_step_condition(step['condition'],
                                                    parameters)
            if not should_run:
                return
        step_type = step['type']
        handler = self._step_handlers[step_type]
        handler.run_step(step, parameters)

    def _check_step_condition(self, condition, parameters):
        statuses = []
        if not isinstance(condition, list):
            condition = [condition]
        for single in condition:
            statuses.append(self._check_single_condition(
                single, parameters))
        return all(statuses)

    def _check_single_condition(self, single, parameters):
        varname = single['variable']
        if 'equals' in single:
            expected = single['equals']
            return parameters.get(varname) == expected
        return False


class ExecutorStep(object):

    # Subclasses must implement this to specify what name to use
    # for the `type` in a wizard definition.
    NAME = ''

    def run_step(self, step_definition, parameters):
        raise NotImplementedError("run_step")


class APICallExecutorStep(ExecutorStep):

    NAME = 'apicall'

    def __init__(self, api_invoker):
        self._api_invoker = api_invoker

    def run_step(self, step_definition, parameters):
        service, op_name = step_definition['operation'].split('.', 1)
        response = self._api_invoker.invoke(
            service=service, operation=op_name,
            api_params=step_definition['params'],
            plan_variables=parameters,
            optional_api_params=step_definition.get('optional_params'),
            query=step_definition.get('query'),
        )
        if 'output_var' in step_definition:
            parameters[step_definition['output_var']] = response


class SharedConfigExecutorStep(ExecutorStep):

    NAME = 'sharedconfig'

    def __init__(self, config_api):
        self._config_api = config_api

    def run_step(self, step_definition, parameters):
        config_params = {}
        profile = None
        if 'profile' in step_definition:
            profile = self._resolve_params(step_definition['profile'],
                                           parameters)
        config_params = self._resolve_params(
            step_definition['params'], parameters
        )
        self._config_api.set_values(config_params, profile=profile)

    def _resolve_params(self, value, params):
        return VariableResolver().resolve_variables(params, value)


class SharedConfigAPI(object):
    """Simplified interface to reading/writing the ~/.aws/config file.

    This provides a simplified interface over the config file writer
    and the config operations provided by a botocore session.

    This allows similar logic to be shared by the planner and executor.

    """
    def __init__(self, session, config_writer):
        self._session = session
        self._config_writer = config_writer

    def list_profiles(self):
        return self._session.available_profiles

    def get_value(self, value, profile=None):
        # TODO: handle profile
        return self._session.get_config_variable(value)

    def set_values(self, values, profile=None):
        config_params = {}
        if profile is not None:
            section = profile
            if profile != 'default':
                section = 'profile %s' % section
            config_params['__section__'] = section
        config_params.update(values)
        config_filename = os.path.expanduser(
            self._session.get_config_variable('config_file'))
        self._config_writer.update_config(config_params, config_filename)


class DefineVariableStep(ExecutorStep):

    NAME = 'define-variable'

    def run_step(self, step_definition, parameters):
        value = step_definition['value']
        resolved_value = VariableResolver().resolve_variables(
            parameters, value)
        key = step_definition['varname']
        parameters[key] = resolved_value


class MergeDictStep(ExecutorStep):

    NAME = 'merge-dict'

    def run_step(self, step_definition, parameters):
        var_resolver = VariableResolver()
        result = {}
        for overlay in step_definition['overlays']:
            resolved_overlay = var_resolver.resolve_variables(
                parameters, overlay,
            )
            result = self._deep_merge(result, resolved_overlay)
        parameters[step_definition['output_var']] = result

    def _deep_merge(self, original, newvalue):
        if isinstance(newvalue, list) and isinstance(original, list):
            # We want to concat list together during a deep merge.
            return original + newvalue
        elif isinstance(newvalue, dict) and isinstance(original, dict):
            result = original.copy()
            for key, value in newvalue.items():
                if key not in result:
                    result[key] = value
                else:
                    result[key] = self._deep_merge(original[key], value)
            return result
        else:
            return newvalue
