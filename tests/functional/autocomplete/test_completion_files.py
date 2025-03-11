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
import pytest
from jsonschema import Draft4Validator

from awscli import clidriver

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
                            },
                        }
                    },
                    "required": ["completions"],
                    "additionalProperties": False,
                },
            },
        },
    },
    "additionalProperties": False,
}


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
        models.append((service_model, completions))
    return models


@pytest.mark.parametrize(
    "service_model, completions", get_models_with_completions()
)
def test_verify_generated_completions_are_valid(service_model, completions):
    _validate_schema(completions)
    # Validate that every operation named in the completions
    # file references a known operation.
    _lint_model_references(completions, service_model)
    _lint_resource_references(completions, service_model)


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
        input_shape = service_model['operations'][op_name]['input']['shape']
        input_members = service_model['shapes'][input_shape]['members']
        for param in completions['operations'][op_name]:
            assert param in input_members


def _lint_resource_references(completions, service_model):
    # Verify resourceIdentifier keys in the operations map to
    # resourceIdentifier keys in the resources map.
    resources = completions['resources']
    for completions in completions['operations'].values():
        for param_data in completions.values():
            for comp_data in param_data['completions']:
                resource_name = comp_data['resourceName']
                resource_id = comp_data['resourceIdentifier']
                assert resource_name in resources
                identifiers = resources[resource_name]['resourceIdentifier']
                assert resource_id in identifiers
    # We also want to lint the 'resources' key as well.
    for resource_data in resources.values():
        assert resource_data['operation'] in service_model['operations']
