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
from botocore.compat import json
from botocore.compat import OrderedDict

import yaml
from yaml.resolver import ScalarNode, SequenceNode


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


def _needs_quoting(value):
    """
    Check if a string value needs to be quoted to prevent YAML from
    interpreting it as a non-string type (number, boolean, null, etc.).
    
    This addresses issue #3991 where strings like '1e10' were being
    output without quotes, causing them to be interpreted as numbers
    when the YAML is re-parsed.
    """
    if not isinstance(value, str) or not value:
        return False
    
    # Check for scientific notation (e.g., 1e10, 1E-5, 2.5e+3)
    # These are valid floats but should remain as strings if originally strings
    import re
    scientific_pattern = r'^[+-]?(\d+\.?\d*|\d*\.?\d+)[eE][+-]?\d+$'
    if re.match(scientific_pattern, value):
        return True
    
    # Check for octal notation (e.g., 0o755, 0O644)
    if re.match(r'^0[oO][0-7]+$', value):
        return True
    
    # Check for hex notation (e.g., 0x1A, 0X2B)
    if re.match(r'^0[xX][0-9a-fA-F]+$', value):
        return True
    
    # Check for binary notation (e.g., 0b1010)
    if re.match(r'^0[bB][01]+$', value):
        return True
    
    # Check for special YAML float values
    if value.lower() in ('.inf', '-.inf', '.nan', '+.inf'):
        return True
    
    # Check for YAML 1.1 legacy octals (e.g., 0755) - numbers starting with 0
    # but not just "0" and containing only digits
    if re.match(r'^0\d+$', value):
        return True
    
    # Check for sexagesimal (base 60) numbers like 1:30:00
    if re.match(r'^\d+:\d+(:\d+)*$', value):
        return True
    
    return False


def _string_representer(dumper, data):
    """
    Custom string representer that quotes strings which could be 
    misinterpreted as numbers or other YAML types.
    """
    if _needs_quoting(data):
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style="'")
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


def yaml_dump(dict_to_dump):
    """
    Dumps the dictionary as a YAML document
    :param dict_to_dump:
    :return:
    """
    FlattenAliasDumper.add_representer(OrderedDict, _dict_representer)
    FlattenAliasDumper.add_representer(str, _string_representer)
    return yaml.dump(
        dict_to_dump,
        default_flow_style=False,
        Dumper=FlattenAliasDumper,
    )


def _dict_constructor(loader, node):
    # Necessary in order to make yaml merge tags work
    loader.flatten_mapping(node)
    return OrderedDict(loader.construct_pairs(node))


class SafeLoaderWrapper(yaml.SafeLoader):
    """Isolated safe loader to allow for customizations without global changes.
    """

    pass

def yaml_parse(yamlstr):
    """Parse a yaml string"""
    try:
        # PyYAML doesn't support json as well as it should, so if the input
        # is actually just json it is better to parse it with the standard
        # json parser.
        return json.loads(yamlstr, object_pairs_hook=OrderedDict)
    except ValueError:
        loader = SafeLoaderWrapper
        loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, 
                               _dict_constructor)
        loader.add_multi_constructor("!", intrinsics_multi_constructor)
        return yaml.load(yamlstr, loader)


class FlattenAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True
