# Copyright 2012-2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

"""
This file implements looping over module content.

Example:

Parameters:
  List:
    Type: CommaDelimitedList
    Default: A,B,C

Modules:
  Content:
    Source: ./map-module.yaml
    Map: !Ref List
    Properties:
      Name: !Sub my-bucket-$MapValue
      Idx: !Sub $MapIndex
"""

import copy
from collections import OrderedDict
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.parse_sub import WordType
from awscli.customizations.cloudformation.parse_sub import parse_sub

MAP_PLACEHOLDER = "$MapValue"
INDEX_PLACEHOLDER = "$MapIndex"
SUB = "Fn::Sub"
MAP = "Map"
REF = "Ref"
PROPERTIES = "Properties"
MODULES = "Modules"


def map_placeholders(i, token, val):
    "Replace $MapValue and $MapIndex"
    if isinstance(val, (dict, OrderedDict)) and SUB in val:
        sub = val[SUB]
        if MAP_PLACEHOLDER in sub or INDEX_PLACEHOLDER in sub:
            r = sub.replace(MAP_PLACEHOLDER, token)
            r = r.replace(INDEX_PLACEHOLDER, f"{i}")
            words = parse_sub(r)
            need_sub = False
            for word in words:
                if word.t != WordType.STR:
                    need_sub = True
                    break
            if need_sub:
                return {SUB: r}
            return r
    elif isinstance(val, str):
        r = val.replace(MAP_PLACEHOLDER, token)
        r = r.replace(INDEX_PLACEHOLDER, f"{i}")
        return r
    return val


def process_module_maps(template, parent_module):
    "Loop over Maps in modules"
    modules = template[MODULES]
    for k, v in modules.copy().items():
        if MAP in v:
            # Expect Map to be a CSV or ref to a CSV
            m = v[MAP]
            if isdict(m) and REF in m:
                m = parent_module.find_ref(m[REF])
                if m is None:
                    msg = f"{k} has an invalid Map Ref"
                    raise exceptions.InvalidModuleError(msg=msg)
            tokens = m.split(",")
            for i, token in enumerate(tokens):
                # Make a new module
                module_id = f"{k}{i}"
                copied_module = copy.deepcopy(v)
                del copied_module[MAP]
                # Replace $Map and $Index placeholders
                if PROPERTIES in copied_module:
                    for prop, val in copied_module[PROPERTIES].copy().items():
                        copied_module[PROPERTIES][prop] = map_placeholders(
                            i, token, val
                        )
                modules[module_id] = copied_module

            del modules[k]


def isdict(v):
    "Returns True if the type is a dict or OrderedDict"
    return isinstance(v, (dict, OrderedDict))
