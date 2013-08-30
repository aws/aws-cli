# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
"""Translate the raw json files into python specific descriptions."""
import os
import re
from copy import deepcopy

from botocore.compat import OrderedDict, json
from botocore import xform_name


class ModelFiles(object):
    """Container object to hold all the various parsed json files.

    Includes:

        * The json service description.
        * The _regions.json file.
        * The _retry.json file.
        * The <service>.extra.json enhancements file.
        * The name of the service.

    """
    def __init__(self, model, regions, retry, enhancements, name=''):
        self.model = model
        self.regions = regions
        self.retry = retry
        self.enhancements = enhancements
        self.name = name


def load_model_files(args):
    model = json.load(open(args.modelfile),
                      object_pairs_hook=OrderedDict)
    regions = json.load(open(args.regions_file),
                        object_pairs_hook=OrderedDict)
    retry = json.load(open(args.retry_file),
                      object_pairs_hook=OrderedDict)
    enhancements = _load_enhancements_file(args.enhancements_file)
    service_name = os.path.splitext(os.path.basename(args.modelfile))[0]
    return ModelFiles(model, regions, retry, enhancements,
                      name=service_name)


def _load_enhancements_file(file_path):
    if not os.path.isfile(file_path):
        return {}
    else:
        return json.load(open(file_path),
                         object_pairs_hook=OrderedDict)


def translate(model):
    new_model = deepcopy(model.model)
    new_model.update(model.enhancements.get('extra', {}))
    try:
        del new_model['pagination']
    except KeyError:
        pass
    add_pagination_configs(
        new_model,
        model.enhancements.get('pagination', {}))
    # Merge in any per operation overrides defined in the .extras.json file.
    merge_dicts(new_model['operations'], model.enhancements.get('operations', {}))
    add_retry_configs(
        new_model, model.retry.get('retry', {}), definitions=model.retry.get('definitions', {}))
    handle_op_renames(new_model, model.enhancements)
    handle_remove_deprecated_params(new_model, model.enhancements)
    handle_remove_deprecated_operations(new_model, model.enhancements)
    handle_filter_documentation(new_model, model.enhancements)
    return new_model


def handle_op_renames(new_model, enhancements):
    # This allows for operations to be renamed.  The only
    # implemented transformation is removing part of the operation name
    # (because that's all we currently need.)
    remove = enhancements.get('transformations', {}).get(
        'operation-name', {}).get('remove')
    if remove is not None:
        # We're going to recreate the dictionary because we want to preserve
        # the order.  This is the only option we have unless we have our own
        # custom OrderedDict.
        remove_regex = re.compile(remove)
        operations = new_model['operations']
        new_operation = OrderedDict()
        for key in operations:
            new_key = remove_regex.sub('', key)
            new_operation[new_key] = operations[key]
        new_model['operations'] = new_operation


def handle_remove_deprecated_operations(new_model, enhancements):
    # This removes any operation whose documentation string contains
    # the specified phrase that marks a deprecated parameter.
    keyword = enhancements.get('transformations', {}).get(
        'remove-deprecated-operations', {}).get('deprecated_keyword')
    remove = []
    if keyword is not None:
        operations = new_model['operations']
        for op_name in operations:
            operation = operations[op_name]
            if operation:
                docs = operation['documentation']
                if docs and docs.find(keyword) >= 0:
                    remove.append(op_name)
    for op in remove:
        del new_model['operations'][op]


def handle_remove_deprecated_params(new_model, enhancements):
    # This removes any parameter whose documentation string contains
    # the specified phrase that marks a deprecated parameter.
    keyword = enhancements.get('transformations', {}).get(
        'remove-deprecated-params', {}).get('deprecated_keyword')
    if keyword is not None:
        operations = new_model['operations']
        for op_name in operations:
            operation = operations[op_name]
            params = operation.get('input', {}).get('members')
            if params:
                new_params = OrderedDict()
                for param_name in params:
                    param = params[param_name]
                    docs = param['documentation']
                    if docs and docs.find(keyword) >= 0:
                        continue
                    new_params[param_name] = param
                operation['input']['members'] = new_params


def _filter_param_doc(param, replacement, regex):
    # Recurse into complex parameters looking for documentation.
    doc = param.get('documentation')
    if doc:
        param['documentation'] = regex.sub(replacement, doc)
    if param['type'] == 'structure':
        for member_name in param['members']:
            member = param['members'][member_name]
            _filter_param_doc(member, replacement, regex)
    if param['type'] == 'map':
        _filter_param_doc(param['keys'], replacement, regex)
        _filter_param_doc(param['members'], replacement, regex)
    elif param['type'] == 'list':
        _filter_param_doc(param['members'], replacement, regex)


def handle_filter_documentation(new_model, enhancements):
    #This provides a way to filter undesireable content (e.g. CDATA)
    #from documentation strings
    filter = enhancements.get('transformations', {}).get(
        'filter-documentation', {}).get('filter')
    if filter is not None:
        filter_regex = re.compile(filter.get('regex', ''), re.DOTALL)
        replacement = filter.get('replacement')
        operations = new_model['operations']
        for op_name in operations:
            operation = operations[op_name]
            doc = operation.get('documentation')
            if doc:
                new_doc = filter_regex.sub(replacement, doc)
                operation['documentation'] = new_doc
            params = operation.get('input', {}).get('members')
            if params:
                for param_name in params:
                    param = params[param_name]
                    _filter_param_doc(param, replacement, filter_regex)


def add_pagination_configs(new_model, pagination):
    # Adding in pagination configs means copying the config to a top level
    # 'pagination' key in the new model, and it also means adding the
    # pagination config to each individual operation.
    # Also, the input_token needs to be transformed to the python specific
    # name, so we're adding a py_input_token (e.g. NextToken -> next_token).
    if pagination:
        new_model['pagination'] = pagination
    for name in pagination:
        config = pagination[name]
        _check_known_pagination_keys(config)
        if 'py_input_token' not in config:
            input_token = config['input_token']
            if isinstance(input_token, list):
                py_input_token = []
                for token in input_token:
                    py_input_token.append(xform_name(token))
                config['py_input_token'] = py_input_token
            else:
                config['py_input_token'] = xform_name(input_token)
        # result_key must be defined
        if 'result_key' not in config:
            raise ValueError("Required key 'result_key' is missing from "
                             "from pagination config: %s" % config)
        operation = new_model['operations'].get(name)
        # result_key must match a key in the output.
        if not isinstance(config['result_key'], list):
            result_keys = [config['result_key']]
        else:
            result_keys = config['result_key']
        for result_key in result_keys:
            if result_key not in operation['output']['members']:
                raise ValueError("result_key %r is not an output member: %s" %
                                (result_key,
                                 operation['output']['members'].keys()))
        _check_input_keys_match(config, operation)
        if operation is None:
            raise ValueError("Tried to add a pagination config for non "
                             "existent operation '%s'" % name)
        operation['pagination'] = config.copy()


def _check_known_pagination_keys(config):
    # Verify that the pagination config only has keys we expect to see.
    expected = set(['input_token', 'py_input_token', 'output_token',
                    'result_key', 'limit_key', 'more_key'])
    for key in config:
        if key not in expected:
            raise ValueError("Unknown key in pagination config: %s" % key)


def _check_input_keys_match(config, operation):
    input_tokens = config['input_token']
    if not isinstance(input_tokens, list):
        input_tokens = [input_tokens]
    valid_input_names = operation['input']['members']
    for token in input_tokens:
        if token not in valid_input_names:
            raise ValueError("input_token refers to a non existent "
                             "input name for operation %s: %s.  "
                             "Must be one of: %s" % (operation['name'], token,
                                                     list(valid_input_names)))
    if 'limit_key' in config and config['limit_key'] not in valid_input_names:
        raise ValueError("limit_key refers to a non existent input name for "
                         "operation %s: %s.  Must be one of: %s" % (
                             operation['name'], config['limit_key'],
                             list(valid_input_names)))


def add_retry_configs(new_model, retry_model, definitions):
    if not retry_model:
        new_model['retry'] = {}
        return
    # The service specific retry config is keyed off of the endpoint
    # prefix as defined in the JSON model.
    endpoint_prefix = new_model.get('endpoint_prefix', '')
    service_config = retry_model.get(endpoint_prefix, {})
    resolve_references(service_config, definitions)
    # We want to merge the global defaults with the service specific
    # defaults, with the service specific defaults taking precedence.
    # So we use the global defaults as the base.
    final_retry_config = {'__default__': retry_model.get('__default__', {})}
    resolve_references(final_retry_config, definitions)
    # The merge the service specific config on top.
    merge_dicts(final_retry_config, service_config)
    new_model['retry'] = final_retry_config


def resolve_references(config, definitions):
    """Recursively replace $ref keys.

    To cut down on duplication, common definitions can be declared
    (and passed in via the ``definitions`` attribute) and then
    references as {"$ref": "name"}, when this happens the reference
    dict is placed with the value from the ``definition`` dict.

    This is recursively done.

    """
    for key, value in config.items():
        if isinstance(value, dict):
            if len(value) == 1 and list(value.keys())[0] == '$ref':
                # Then we need to resolve this reference.
                config[key] = definitions[list(value.values())[0]]
            else:
                resolve_references(value, definitions)


def merge_dicts(dict1, dict2):
    """Given two dict, merge the second dict into the first.

    The dicts can have arbitrary nesting.

    """
    for key in dict2:
        if is_sequence(dict2[key]):
            if key in dict1 and key in dict2:
                merge_dicts(dict1[key], dict2[key])
            else:
                dict1[key] = dict2[key]
        else:
            # At scalar types, we iterate and merge the
            # current dict that we're on.
            dict1[key] = dict2[key]


def is_sequence(x):
    return isinstance(x, (list, dict))
