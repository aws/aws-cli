# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.clidriver import CLIOperationCaller


class PipelineDefinitionError(Exception):
    def __init__(self, msg, definition):
        full_msg = (
            "Error in pipeline definition: %s\n" % msg)
        super(PipelineDefinitionError, self).__init__(full_msg)
        self.msg = msg
        self.definition = definition


# Method to convert the dictionary input to a string
# This is required for escaping
def dict_to_string(dictionary, indent=2):
    return json.dumps(dictionary, indent=indent)


# Method to parse the arguments to get the region value
def get_region(session, parsed_globals):
    region = parsed_globals.region
    if region is None:
        region = session.get_config_variable('region')
    return region


def remove_cli_error_event(client):
    """This unregister call will go away once the client switchover
    is done, but for now we're relying on S3 catching a ClientError
    when we check if a bucket exists, so we need to ensure the
    botocore ClientError is raised instead of the CLI's error handler.
    """
    client.meta.events.unregister(
        'after-call', unique_id='awscli-error-handler')


# Method to display the response for a particular CLI operation
def display_response(session, operation_name, result, parsed_globals):
    cli_operation_caller = CLIOperationCaller(session)
    # Calling a private method. Should be changed after the functionality
    # is moved outside CliOperationCaller.
    cli_operation_caller._display_response(
        operation_name, result, parsed_globals)


def api_to_definition(definition):
    # When we're translating from api_response -> definition
    # we have to be careful *not* to mutate the existing
    # response as other code might need to the original
    # api_response.
    if 'pipelineObjects' in definition:
        definition['objects'] = _api_to_objects_definition(
            definition.pop('pipelineObjects'))
    if 'parameterObjects' in definition:
        definition['parameters'] = _api_to_parameters_definition(
            definition.pop('parameterObjects'))
    if 'parameterValues' in definition:
        definition['values'] = _api_to_values_definition(
            definition.pop('parameterValues'))
    return definition


def definition_to_api_objects(definition):
    if 'objects' not in definition:
        raise PipelineDefinitionError('Missing "objects" key', definition)
    api_elements = []
    # To convert to the structure expected by the service,
    # we convert the existing structure to a list of dictionaries.
    # Each dictionary has a 'fields', 'id', and 'name' key.
    for element in definition['objects']:
        try:
            element_id = element.pop('id')
        except KeyError:
            raise PipelineDefinitionError('Missing "id" key of element: %s' %
                                          json.dumps(element), definition)
        api_object = {'id': element_id}
        # If a name is provided, then we use that for the name,
        # otherwise the id is used for the name.
        name = element.pop('name', element_id)
        api_object['name'] = name
        # Now we need the field list.  Each element in the field list is a dict
        # with a 'key', 'stringValue'|'refValue'
        fields = []
        for key, value in sorted(element.items()):
            fields.extend(_parse_each_field(key, value))
        api_object['fields'] = fields
        api_elements.append(api_object)
    return api_elements


def definition_to_api_parameters(definition):
    if 'parameters' not in definition:
        return None
    parameter_objects = []
    for element in definition['parameters']:
        try:
            parameter_id = element.pop('id')
        except KeyError:
            raise PipelineDefinitionError('Missing "id" key of parameter: %s' %
                                          json.dumps(element), definition)
        parameter_object = {'id': parameter_id}
        # Now we need the attribute list.  Each element in the attribute list
        # is a dict with a 'key', 'stringValue'
        attributes = []
        for key, value in sorted(element.items()):
            attributes.extend(_parse_each_field(key, value))
        parameter_object['attributes'] = attributes
        parameter_objects.append(parameter_object)
    return parameter_objects


def definition_to_parameter_values(definition):
    if 'values' not in definition:
        return None
    parameter_values = []
    for key in definition['values']:
        parameter_values.extend(
            _convert_single_parameter_value(key, definition['values'][key]))

    return parameter_values


def _parse_each_field(key, value):
    values = []
    if isinstance(value, list):
        for item in value:
            values.append(_convert_single_field(key, item))
    else:
        values.append(_convert_single_field(key, value))
    return values


def _convert_single_field(key, value):
    field = {'key': key}
    if isinstance(value, dict) and list(value.keys()) == ['ref']:
        field['refValue'] = value['ref']
    else:
        field['stringValue'] = value
    return field


def _convert_single_parameter_value(key, values):
    parameter_values = []
    if isinstance(values, list):
        for each_value in values:
            parameter_value = {'id': key, 'stringValue': each_value}
            parameter_values.append(parameter_value)
    else:
        parameter_value = {'id': key, 'stringValue': values}
        parameter_values.append(parameter_value)
    return parameter_values


def _api_to_objects_definition(api_response):
    pipeline_objects = []
    for element in api_response:
        current = {
            'id': element['id'],
            'name': element['name']
        }
        for field in element['fields']:
            key = field['key']
            if 'stringValue' in field:
                value = field['stringValue']
            else:
                value = {'ref': field['refValue']}
            _add_value(key, value, current)
        pipeline_objects.append(current)
    return pipeline_objects


def _api_to_parameters_definition(api_response):
    parameter_objects = []
    for element in api_response:
        current = {
            'id': element['id']
        }
        for attribute in element['attributes']:
            _add_value(attribute['key'], attribute['stringValue'], current)
        parameter_objects.append(current)
    return parameter_objects


def _api_to_values_definition(api_response):
    pipeline_values = {}
    for element in api_response:
        _add_value(element['id'], element['stringValue'], pipeline_values)
    return pipeline_values


def _add_value(key, value, current_map):
    if key not in current_map:
        current_map[key] = value
    elif isinstance(current_map[key], list):
        # Dupe keys result in values aggregating
        # into a list.
        current_map[key].append(value)
    else:
        converted_list = [current_map[key], value]
        current_map[key] = converted_list
