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

    if tag == "GetAtt" and isinstance(node.value, str):
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


def _add_yaml_1_1_boolean_resolvers(resolver_cls):
    # CloudFormation treats unquoted values that are YAML 1.1 native
    # booleans as booleans, rather than strings. In YAML 1.2, the only
    # boolean values are "true" and "false" so values such as "yes" and "no"
    # when loaded as strings are not quoted when dumped. This logic ensures
    # that we dump these values with quotes so that CloudFormation treats
    # these values as strings and not booleans.
    boolean_regex = re.compile(
        '^(?:yes|Yes|YES|no|No|NO'
        '|true|True|TRUE|false|False|FALSE'
        '|on|On|ON|off|Off|OFF)$'
    )
    boolean_first_chars = list(u'yYnNtTfFoO')
    resolver_cls.add_implicit_resolver(
        'tag:yaml.org,2002:bool', boolean_regex, boolean_first_chars)


def yaml_dump(dict_to_dump):
    """
    Dumps the dictionary as a YAML document
    :param dict_to_dump:
    :return:
    """

    yaml = ruamel.yaml.YAML(typ="safe", pure=True)
    yaml.default_flow_style = False
    yaml.Representer = FlattenAliasRepresenter
    _add_yaml_1_1_boolean_resolvers(yaml.Resolver)
    yaml.Representer.add_representer(OrderedDict, _dict_representer)

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
        yaml.Constructor.add_constructor(
            ruamel.yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            _dict_constructor)
        yaml.Constructor.add_multi_constructor(
            "!", intrinsics_multi_constructor)
        _add_yaml_1_1_boolean_resolvers(yaml.Resolver)

        return yaml.load(yamlstr)


class FlattenAliasRepresenter(ruamel.yaml.representer.SafeRepresenter):
    def ignore_aliases(self, data):
        return True
