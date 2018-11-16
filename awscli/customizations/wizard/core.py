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
    def __init__(self, session):
        self._session = session

    def run_step(self, step_definition, parameters):
        operation = step_definition['operation']
        service, op_name = operation.split('.', 1)
        method_name = xform_name(op_name)
        params = step_definition['params']
        response = self._invoke_apicall(service, method_name, params)
        if 'query' in step_definition:
            response = jmespath.search(step_definition['query'], response)
        return response

    def _invoke_apicall(self, service, method_name, params):
        client = self._session.create_client(service)
        return getattr(client, method_name)(**params)
