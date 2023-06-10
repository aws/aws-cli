# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import ruamel.yaml
from botocore.compat import OrderedDict

from awscli.utils import dump_yaml_to_str

def _ordered_constructor(loader, node):
    loader.flatten_mapping(node)
    return OrderedDict(loader.construct_pairs(node))

def _ordered_representer(dumper, data):
    return dumper.represent_mapping(
        str(ruamel.yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG),
        data.items())

def ordered_yaml_load(stream):
    """ Load an OrderedDict object from a yaml stream."""
    yaml = ruamel.yaml.YAML(typ="safe", pure=True)
    yaml.Constructor.add_constructor(
        str(ruamel.yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG),
        _ordered_constructor)

    return yaml.load(stream)


def ordered_yaml_dump(to_dump, stream=None):
    """
    Dump an OrderedDict object to yaml.

    :param to_dump: The OrderedDict to dump
    :type to_dump: OrderedDict

    :param stream: The file to dump to
    If not given or if None, only return the value
    :type stream: file
    """
    yaml = ruamel.yaml.YAML(typ="safe", pure=True)
    yaml.default_flow_style = False
    yaml.Representer.add_representer(OrderedDict, _ordered_representer)

    if stream is None:
        return dump_yaml_to_str(yaml, to_dump)

    yaml.dump(to_dump, stream)
