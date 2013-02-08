"""Translate the raw json files into python specific descriptions."""
import os
import sys
import json
from copy import deepcopy
try:
    from collections import OrderedDict
except ImportError:
    # OrderedDicts are used during the annotation process to preserve
    # the order of keys to create useful diffs.  Not doing this doesn't
    # break the behavior, it just creates less the useful diffs.
    # This only applies for python2.6, so we could include a backport
    # of ordered dict for python2.6 if we felt this was important.
    OrderedDict = dict


class ModelFiles(object):
    """Container object to hold all the various parsed json files.

    Includes:

        * The json service description.
        * The _services.json file.
        * The _regions.json file.
        * The <service>.extra.json enhancements file.
        * The name of the service.

    """
    def __init__(self, model, services, regions, enhancements, name=''):
        self.model = model
        self.services = services
        self.regions = regions
        self.enhancements = enhancements
        self.name = name


def load_model_files(args):
    model = json.load(open(args.modelfile),
                           object_pairs_hook=OrderedDict)
    services = json.load(open(args.services_file),
                        object_pairs_hook=OrderedDict)
    regions = json.load(open(args.regions_file),
                        object_pairs_hook=OrderedDict)
    enhancements = _load_enhancements_file(args.enhancements_file)
    service_name = os.path.splitext(os.path.basename(args.modelfile))[0]
    return ModelFiles(model, services, regions, enhancements,
                      name=service_name)


def _load_enhancements_file(file_path):
    if not os.path.isfile(file_path):
        return {}
    else:
        return json.load(open(file_path),
                         object_pairs_hook=OrderedDict)


def translate(model):
    new_model = deepcopy(model.model)
    transform_operations_list(new_model)
    new_model.update(model.enhancements.get('extra', {}))
    service_info = model.services.get(model.name, {})
    add_pagination_configs(
        new_model,
        model.enhancements.get('pagination', {}))
    new_model['metadata'] = service_info.copy()
    merge_dicts(new_model['operations'], model.enhancements.get('operations', {}))
    return new_model


def add_pagination_configs(new_model, pagination):
    # Adding in pagination configs means copying the config to a top level
    # 'pagination' key in the new model, and it also means adding the
    # pagination config to each individual operation.
    if pagination:
        new_model['pagination'] = pagination
    for name in pagination:
        config = pagination[name]
        operation = new_model['operations'].get(name)
        if operation is None:
            raise ValueError("Tried to add a pagination config for non "
                             "existent operation '%s'" % name)
        operation['pagination'] = config.copy()


def transform_operations_list(new_model):
    """Transforms list of operations into a dict.

    This mutates the passed in new_model.

    From:

        {'operations': [{'Name': 'Foo'}, {'Name': 'Bar'}]}

    To:

        {'operations': {'Foo': {}, 'Bar': {}}}

    The 'Name' key is extracted out of the per operation dict,
    but all the other fields are left in tact.

    """
    operations = new_model.get('operations', [])
    operations_map = OrderedDict()
    for operation in operations:
        name = operation.pop('name')
        operations_map[name] = operation
    new_model['operations'] = operations_map


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
