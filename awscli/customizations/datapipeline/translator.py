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


class PipelineDefinitionError(Exception):
    def __init__(self, msg, definition):
        full_msg = (
            "Error in pipeline definition: %s\n" % msg)
        super(PipelineDefinitionError, self).__init__(full_msg)
        self.msg = msg
        self.definition = definition


def definition_to_api(definition):
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
            if isinstance(value, list):
                for item in value:
                    fields.append(_convert_single_field(key, item))
            else:
                fields.append(_convert_single_field(key, value))
        api_object['fields'] = fields
        api_elements.append(api_object)
    return api_elements


def _convert_single_field(key, value):
    field = {'key': key}
    if isinstance(value, dict) and list(value.keys()) == ['ref']:
        field['refValue'] = value['ref']
    else:
        field['stringValue'] = value
    return field


def api_to_definition(api_response):
    # When we're translating from api_response -> definition
    # we have to be careful *not* to mutate the existing
    # response as other code might need to the original
    # api_response.
    pipeline_objs = []
    for element in api_response:
        current = {
            'id': element['id'],
            'name': element['name'],
        }
        for field in element['fields']:
            key = field['key']
            if 'stringValue' in field:
                value = field['stringValue']
            else:
                value = {'ref': field['refValue']}
            if key not in current:
                current[key] = value
            elif isinstance(current[key], list):
                # Dupe keys result in values aggregating
                # into a list.
                current[key].append(value)
            else:
                converted_list = [current[key], value]
                current[key] = converted_list
        pipeline_objs.append(current)
    return {'objects': pipeline_objs}
