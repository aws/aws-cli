# Copyright 2012-2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

See tests/unit/customizations/cloudformation/modules/map*.yaml
"""

import copy
from collections import OrderedDict
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.module_visitor import Visitor
from awscli.customizations.cloudformation.parse_sub import WordType
from awscli.customizations.cloudformation.parse_sub import parse_sub

MAP_PLACEHOLDER = "$MapValue"
INDEX_PLACEHOLDER = "$MapIndex"
SUB = "Fn::Sub"
MAP = "Map"
REF = "Ref"
PROPERTIES = "Properties"
MODULES = "Modules"
GETATT = "Fn::GetAtt"
RESOURCES = "Resources"


def replace_str(s, m, i):
    """
    Replace placeholders in a single string.

    s: The string to alter
    m: The map key
    i: The map index
    """
    s = s.replace(MAP_PLACEHOLDER, m)
    return s.replace(INDEX_PLACEHOLDER, f"{i}")


def map_placeholders(i, token, val):
    "Replace $MapValue and $MapIndex"

    if isinstance(val, (dict, OrderedDict)):
        if SUB in val:
            sub = val[SUB]
            if MAP_PLACEHOLDER in sub or INDEX_PLACEHOLDER in sub:
                r = replace_str(sub, token, i)
                words = parse_sub(r)
                need_sub = False
                for word in words:
                    if word.t != WordType.STR:
                        need_sub = True
                        break
                if need_sub:
                    return {SUB: r}
                return r
        elif GETATT in val:
            getatt = val[GETATT]
            # Handle expressions like !GetAtt Content[$MapIndex].Name
            # All we can do here is replace $MapIndex with a number.
            # Later, when we resolve outputs, we need to fix it
            new_getatt = []
            for item in getatt:
                new_getatt.append(replace_str(item, token, i))
            return {GETATT: new_getatt}

    elif isinstance(val, str):
        return replace_str(val, token, i)
    return val


def process_module_maps(template, parent_module):
    """
    Loop over Maps in modules.

    Returns a dictionary of mapped module names to map length,
    for later when we need to expand references that use an array index.

    For example:

    {"Content": 3}
    """
    retval = {}
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
            retval[k] = len(tokens)
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

    return retval


def resolve_mapped_lists(template, mapped):
    """
    Resolve GetAtts like !GetAtt Content[].Arn

    These are GetAtts that refer to each instance of
    a module's output. These are converted to lists.
    """

    # Visit the entire template
    if RESOURCES not in template:
        return

    def vf(v):
        if isdict(v.d) and GETATT in v.d and v.p is not None:
            getatt = v.d[GETATT]
            if isinstance(getatt, list) and len(getatt) > 1:
                if "[]" in getatt[0]:
                    s = ".".join(getatt)  # Content[0].Arn
                    if s in mapped:
                        v.p[v.k] = mapped[s]
            else:
                msg = f"Invalid GetAtt: {getatt}"
                raise exceptions.InvalidModuleError(msg=msg)

    v = Visitor(template[RESOURCES])
    v.visit(vf)


def isdict(v):
    "Returns True if the type is a dict or OrderedDict"
    return isinstance(v, (dict, OrderedDict))
