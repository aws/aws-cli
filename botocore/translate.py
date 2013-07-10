"""Translate the raw json files into python specific descriptions."""
import os
import sys
import json
from copy import deepcopy
from .compat import OrderedDict
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
    return new_model


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
        if operation is None:
            raise ValueError("Tried to add a pagination config for non "
                             "existent operation '%s'" % name)
        operation['pagination'] = config.copy()


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
