# Copyright 2012-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import re

import ruamel.yaml
from ruamel.yaml.resolver import ScalarNode, SequenceNode
from botocore.compat import json
from botocore.compat import OrderedDict


from awscli.compat import six
from awscli.utils import dump_yaml_to_str


def intrinsics_multi_constructor(loader, tag_prefix, node):
    """
    YAML constructor to parse CloudFormation intrinsics.
    This will return a dictionary with key being the intrinsic name
    """

    # Get the actual tag name excluding the first exclamation
    tag = node.tag[1:]

    # Some intrinsic functions doesn't support prefix "Fn::"
    prefix = "Fn::"
    if tag in ["Ref", "Condition"]:
        prefix = ""

    cfntag = prefix + tag

    if tag == "GetAtt" and isinstance(node.value, six.string_types):
        # ShortHand notation for !GetAtt accepts Resource.Attribute format
        # while the standard notation is to use an array
        # [Resource, Attribute]. Convert shorthand to standard format
        value = node.value.split(".", 1)

    elif isinstance(node, ScalarNode):
        # Value of this node is scalar
        value = loader.construct_scalar(node)

    elif isinstance(node, SequenceNode):
        # Value of this node is an array (Ex: [1,2])
        value = loader.construct_sequence(node)

    else:
        # Value of this node is an mapping (ex: {foo: bar})
        value = loader.construct_mapping(node)

    return {cfntag: value}


def _dict_representer(dumper, data):
    return dumper.represent_dict(data.items())


def _str_representer(dumper, data):
    # ruamel removes quotes from values that are unambiguously strings.
    # Values like 0888888 can only be a string because integers can't
    # have leading 0s and octals can't have the digits 8 and 9.
    # However, CloudFormation treats these nonoctal values as integers
    # and removes the leading 0s. This logic ensures that nonoctal
    # values are quoted when dumped.
    style = None
    if re.match('^0[0-9]*[89][0-9]*$', data):
        style = "'"
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style=style)


def yaml_dump(dict_to_dump):
    """
    Dumps the dictionary as a YAML document
    :param dict_to_dump:
    :return:
    """

    yaml = ruamel.yaml.YAML(typ="safe", pure=True)
    yaml.version = (1, 1)
    yaml.default_flow_style = False
    yaml.Representer = FlattenAliasRepresenter
    yaml.Representer.add_representer(OrderedDict, _dict_representer)
    yaml.Representer.add_representer(str, _str_representer)

    return dump_yaml_to_str(yaml, dict_to_dump)


def _dict_constructor(loader, node):
    # Necessary in order to make yaml merge tags work
    loader.flatten_mapping(node)
    return OrderedDict(loader.construct_pairs(node))


def yaml_parse(yamlstr):
    """Parse a yaml string"""
    try:
        # PyYAML doesn't support json as well as it should, so if the input
        # is actually just json it is better to parse it with the standard
        # json parser.
        return json.loads(yamlstr, object_pairs_hook=OrderedDict)
    except ValueError:
        yaml = ruamel.yaml.YAML(typ="safe", pure=True)
        yaml.version = (1, 1)
        yaml.Constructor.add_constructor(
            ruamel.yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            _dict_constructor)
        yaml.Constructor.add_multi_constructor(
            "!", intrinsics_multi_constructor)

        return yaml.load(yamlstr)


class FlattenAliasRepresenter(ruamel.yaml.representer.SafeRepresenter):
    def ignore_aliases(self, data):
        return True
