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
from dataclasses import dataclass

import jmespath
import pytest
from jsonschema import Draft4Validator

from awscli import clidriver
from awscli.botocore.model import ServiceModel
from awscli.botocore.utils import ArgumentGenerator

COMPLETIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "resources": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string"},
                    "resourceIdentifier": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                        "minProperties": 1,
                    },
                    "inputParameters": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["operation", "resourceIdentifier"],
                "additionalProperties": False,
            },
        },
        "operations": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "completions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "parameters": {
                                        "type": "object",
                                        "additionalProperties": {
                                            "type": "string"
                                        },
                                    },
                                    "resourceName": {"type": "string"},
                                    "resourceIdentifier": {"type": "string"},
                                },
                                "required": [
                                    "resourceName",
                                    "resourceIdentifier",
                                ],
                            },
                        }
                    },
                    "required": ["completions"],
                    "additionalProperties": False,
                },
            },
        },
    },
    "required": ["version", "resources", "operations"],
    "additionalProperties": False,
}


@dataclass
class ServiceTestData:
    service_model: dict
    completions: dict
    service_name: str


def get_models_with_completions():
    session = clidriver.create_clidriver().session
    loader = session.get_component('data_loader')
    services_with_completions = loader.list_available_services('completions-1')
    models = []
    for service_name in services_with_completions:
        service_model = loader.load_service_model(service_name, 'service-2')
        api_version = service_model['metadata']['apiVersion']
        completions = loader.load_service_model(
            service_name, 'completions-1', api_version
        )
        models.append(
            ServiceTestData(service_model, completions, service_name)
        )
    return models


@pytest.mark.parametrize(
    "test_data",
    get_models_with_completions(),
    ids=lambda test_data: test_data.service_name,
)
def test_verify_generated_completions_are_valid(test_data):
    completions = test_data.completions
    service_model = test_data.service_model
    _validate_schema(completions)
    # Validate that every operation named in the completions
    # file references a known operation.
    _lint_model_references(completions, service_model)
    _lint_resource_references(completions, service_model)
    _lint_completions(completions, service_model)
    _validate_jmespaths(completions, service_model)


def _get_input_members(service_model, operation_name):
    operation = service_model['operations'][operation_name]
    if 'input' not in operation:
        return {}
    input_shape = operation['input']['shape']
    return service_model['shapes'][input_shape]['members']


def _validate_schema(completions):
    # Ensure completions-1.json file adheres to a JSON schema.
    validator = Draft4Validator(COMPLETIONS_SCHEMA)
    errors = list(e.message for e in validator.iter_errors(completions))
    if errors:
        raise AssertionError('\n'.join(errors))


def _lint_model_references(completions, service_model):
    known_operations = set(service_model['operations'])
    for op_name in completions['operations']:
        assert op_name in known_operations
        # We also want to ensure that all parameters in completions-1.json
        # map to an input member in the service model.
        input_members = _get_input_members(service_model, op_name)
        for param in completions['operations'][op_name]:
            assert param in input_members


def _lint_resource_references(completions, service_model):
    resources = completions['resources']
    for resource_data in resources.values():
        operation_name = resource_data['operation']
        assert operation_name in service_model['operations']

        if 'inputParameters' in resource_data:
            input_members = _get_input_members(service_model, operation_name)
            for param in resource_data['inputParameters']:
                assert param in input_members


def _lint_completions(completions, service_model):
    resources = completions['resources']
    for op_name, completions_data in completions['operations'].items():
        completion_input_members = _get_input_members(service_model, op_name)

        for param_data in completions_data.values():
            for completer_config in param_data['completions']:
                resource_name = completer_config['resourceName']
                resource_id = completer_config['resourceIdentifier']
                assert resource_name in resources
                resource_identifiers = resources[resource_name][
                    'resourceIdentifier'
                ]
                assert resource_id in resource_identifiers

                _validate_completion_parameters(
                    completer_config, resources, completion_input_members
                )


def _validate_completion_parameters(
    completer_config, resources, completion_input_members
):
    resource_name = completer_config['resourceName']
    resource_config = resources[resource_name]
    required_params = resource_config.get('inputParameters', [])
    completion_params = completer_config.get('parameters', {})

    # All required parameters must be provided
    assert set(completion_params.keys()) == set(required_params)

    # Parameter values must be valid in completion operation
    for param_value in completion_params.values():
        assert param_value in completion_input_members


def _validate_jmespaths(completions, service_model):
    service_model_obj = ServiceModel(service_model)
    resources = completions['resources']
    for rconfig in resources.values():
        op_model = service_model_obj.operation_model(rconfig['operation'])
        output_shape = op_model.output_shape
        assert output_shape is not None

        for jmespath_expr in rconfig['resourceIdentifier'].values():
            _validate_jmespath_expression(
                jmespath_expr,
                op_model.output_shape,
            )


def _validate_jmespath_expression(
    jmespath_expr,
    output_shape,
):
    # Test if the JMESPath expression can resolve to a non-empty value
    arg_gen = ArgumentGenerator(use_member_names=True)
    sample_output = arg_gen.generate_skeleton(output_shape)
    search_result = jmespath.search(jmespath_expr, sample_output)
    assert (
        search_result is not None
    ), "Expression is blob or another unsupported type"
    assert search_result, f"Expression is broken: {jmespath_expr}"
    sample_arg = search_result[0]
    assert isinstance(
        sample_arg, str
    ), f"Expression not a string: {jmespath_expr}"
