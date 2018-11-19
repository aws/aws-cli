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
import jmespath
import os

from botocore import xform_name


class Planner(object):
    _DONE_STEP = 'DONE'
    _STOP_RUNNING = object()

    def __init__(self, step_handlers):
        self._step_handlers = step_handlers
        # These will hold the values we store from
        # running through the plan steps.
        self._parameters = {}

    def run(self, plan):
        self._parameters.clear()
        steps_iter = self._steps(plan)
        step = next(steps_iter)
        while step is not self._STOP_RUNNING:
            next_step_name = self._run_step(step)
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

    def _run_step(self, step):
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
    def run_step(self, step_definition, parameters):
        raise NotImplementedError("run_step")


class StaticStep(BaseStep):
    def run_step(self, step_definition, parameters):
        return step_definition['value']


class PromptStep(BaseStep):
    def __init__(self, prompter):
        self._prompter = prompter

    def run_step(self, step_definition, parameters):
        choices = self._get_choices(step_definition, parameters)
        response = self._prompter.prompt(step_definition['description'],
                                         choices=choices)
        return response

    def _get_choices(self, step_definition, parameters):
        choices = step_definition.get('choices')
        if choices is not None:
            if isinstance(choices, str):
                # If 'choices' is a string, we assume it's the name of
                # a variable.
                return parameters[choices]
            return choices


class TemplateStep(BaseStep):

    def run_step(self, step_definition, parameters):
        value = step_definition['value']
        return value.format(**parameters)


class APICallStep(BaseStep):
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
        api_params_resolved = self._resolve_vars(api_params, plan_vars)
        if optional_params is not None:
            optional_params_resolved = self._resolve_vars(optional_params,
                                                          plan_vars)
            for key, value in optional_params_resolved.items():
                if key not in api_params_resolved and value is not None:
                    api_params_resolved[key] = value
        return api_params_resolved

    def _resolve_vars(self, value, plan_vars):
        if isinstance(value, str):
            value = value.format(**plan_vars)
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
            return final
        else:
            return value


class Executor(object):

    def __init__(self, step_handlers):
        self._step_handlers = step_handlers

    def run(self, step, parameters):
        # We may eventually support jumping around to different step
        # names, but for now, we just iterate through the steps in order.
        for group in step.values():
            for step in group:
                self._run_step(step, parameters)

    def _run_step(self, step, parameters):
        if 'condition' in step:
            should_run = self._check_step_condition(step['condition'],
                                                    parameters)
            if not should_run:
                return
        step_type = step['type']
        handler = self._step_handlers[step_type]
        handler.run_step(step, parameters)

    def _check_step_condition(self, condition, parameters):
        varname = condition['variable']
        if 'equals' in condition:
            expected = condition['equals']
            return parameters.get(varname) == expected
        return False


class ExecutorStep(object):
    def run_step(self, step_definition, parameters):
        raise NotImplementedError("run_step")


class APICallExecutorStep(ExecutorStep):
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
        # TODO: remove duplication with APICallExecutorStep
        if isinstance(value, str):
            value = value.format(**params)
            return value
        elif isinstance(value, list):
            final = []
            for v in value:
                final.append(self._resolve_params(v, params))
            return final
        elif isinstance(value, dict):
            final = {}
            for k, v in value.items():
                final[k] = self._resolve_params(v, params)
            return final
        else:
            return value


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
