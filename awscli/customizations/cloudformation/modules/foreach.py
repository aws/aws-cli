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

We originally called the attribute "Map" and renamed it to "ForEach" for
consistency with Fn::ForEach.

See tests/unit/customizations/cloudformation/modules/foreach*.yaml
"""

import copy
from collections import OrderedDict
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.modules.visitor import Visitor
from awscli.customizations.cloudformation.modules.parse_sub import WordType
from awscli.customizations.cloudformation.modules.parse_sub import parse_sub

IDENTIFIER_PLACEHOLDER = "$Identifier"
INDEX_PLACEHOLDER = "$Index"
VALUE_PLACEHOLDER = "$Value"
VALUE_PLACEHOLDER = "$Value"
SUB = "Fn::Sub"
FOREACH = "ForEach"  # Renamed from MAP
REF = "Ref"
PROPERTIES = "Properties"
MODULES = "Modules"
GETATT = "Fn::GetAtt"
RESOURCES = "Resources"
OUTPUTS = "Outputs"
ORIGINAL_FOREACH_NAME = "OriginalForEachName"  # Renamed from ORIGINAL_MAP_NAME
VALUE = "Value"
FOREACH_PREFIX = "Fn::ForEach::"
FOREACH_NAME_IS_I = "foreach_name_is_i"  # Renamed from MAP_NAME_IS_I


def replace_str(s, m, i):
    """
    Replace placeholders in a single string.

    s: The string to alter
    m: The foreach key
    i: The foreach index
    """
    s = s.replace(IDENTIFIER_PLACEHOLDER, m)
    return s.replace(INDEX_PLACEHOLDER, f"{i}")


def replace_identifier(s, identifier, value):
    """
    Replace ${identifier} or &{identifier} in a string with the value.

    s: The string to alter
    identifier: The identifier to replace
    value: The value to replace it with
    """
    # Replace ${identifier} with value
    s = s.replace(f"${{{identifier}}}", value)
    # Replace &{identifier} with value (for non-alphanumeric characters)
    s = s.replace(f"&{{{identifier}}}", value)
    return s


def foreach_placeholders(i, token, val):
    "Replace $Identifier and $Index"

    if isinstance(val, (dict, OrderedDict)):
        if SUB in val:
            sub = val[SUB]
            if IDENTIFIER_PLACEHOLDER in sub or INDEX_PLACEHOLDER in sub:
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
            # Handle expressions like !GetAtt Content[$Index].Name
            # All we can do here is replace $Index with a number.
            # Later, when we resolve outputs, we need to fix it
            new_getatt = []
            for item in getatt:
                new_getatt.append(replace_str(item, token, i))
            return {GETATT: new_getatt}
    elif isinstance(val, str):
        return replace_str(val, token, i)
    return val


# pylint: disable=too-many-return-statements
# pylint: disable=too-many-branches
# pylint: disable=too-many-locals
def foreach_identifier_placeholders(identifier, value, val):
    """
    Replace ${identifier} and &{identifier} in values.

    identifier: The identifier to replace
    value: The value to replace it with
    val: The value to process
    """
    if isinstance(val, (dict, OrderedDict)):
        if SUB in val:
            sub = val[SUB]
            if f"${{{identifier}}}" in sub or f"&{{{identifier}}}" in sub:
                r = replace_identifier(sub, identifier, value)
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
            new_getatt = []
            for item in getatt:
                if isinstance(item, str) and (
                    f"${{{identifier}}}" in item
                    or f"&{{{identifier}}}" in item
                ):
                    new_getatt.append(
                        replace_identifier(item, identifier, value)
                    )
                else:
                    new_getatt.append(item)
            return {GETATT: new_getatt}
        else:
            # Process nested dictionaries
            result = {}
            for k, v in val.items():
                if isinstance(k, str) and (
                    f"${{{identifier}}}" in k or f"&{{{identifier}}}" in k
                ):
                    new_key = replace_identifier(k, identifier, value)
                    result[new_key] = foreach_identifier_placeholders(
                        identifier, value, v
                    )
                else:
                    result[k] = foreach_identifier_placeholders(
                        identifier, value, v
                    )
            return result
    elif isinstance(val, list):
        # Process lists
        return [
            foreach_identifier_placeholders(identifier, value, item)
            for item in val
        ]
    elif isinstance(val, str):
        return replace_identifier(val, identifier, value)
    return val


# pylint: disable=cell-var-from-loop
# pylint: disable=too-many-statements
def process_module_foreach(template, parent_module):
    """
    Loop over ForEach in modules.

    Returns a dictionary of foreach module names to [keys],
    for later when we need to expand references that use an array index.

    For example:

    {"Content": ["A", "B", "C"]}
    """
    retval = {}
    modules = template[MODULES]

    # Process ForEach attribute
    for k, v in modules.copy().items():
        if FOREACH in v:
            # Expect ForEach to be a CSV or ref to a CSV
            m = v[FOREACH]
            if isdict(m) and REF in m:
                m = parent_module.find_ref(m[REF])
                if m is None:
                    msg = f"{k} has an invalid ForEach Ref"
                    raise exceptions.InvalidModuleError(msg=msg)
            tokens = m.split(",")
            retval[k] = tokens
            for i, token in enumerate(tokens):
                # Make a new module
                module_id = f"{k}{i}"
                copied_module = copy.deepcopy(v)
                copied_module[ORIGINAL_FOREACH_NAME] = k
                del copied_module[FOREACH]
                # Replace $Identifier and $Index placeholders
                if PROPERTIES in copied_module:

                    def vf(vis):
                        if vis.p is not None:
                            vis.p[vis.k] = foreach_placeholders(
                                i, token, vis.d
                            )

                    Visitor(copied_module[PROPERTIES]).visit(vf)

                modules[module_id] = copied_module

            del modules[k]

    # Process Fn::ForEach
    for k, v in modules.copy().items():
        if k.startswith(FOREACH_PREFIX):
            prefix_len = len(FOREACH_PREFIX)
            loop_name = k[prefix_len:]

            # Validate ForEach structure
            if not isinstance(v, list) or len(v) != 3:
                msg = (
                    f"Fn::ForEach::{loop_name} must be a list "
                    + "with 3 elements: [identifier, collection, template]"
                )
                raise exceptions.InvalidModuleError(msg=msg)

            identifier = v[0]
            collection = v[1]
            template_fragment = v[2]

            # Handle collection that might be a Ref to a CommaDelimitedList
            if isdict(collection) and REF in collection:
                collection = parent_module.find_ref(collection[REF])
                if collection is None:
                    msg = f"Fn::ForEach::{loop_name} invalid collection Ref"
                    raise exceptions.InvalidModuleError(msg=msg)

            # Convert string to list if it's a comma-delimited string
            if isinstance(collection, str):
                collection = collection.split(",")

            # Ensure collection is a list
            if not isinstance(collection, list):
                msg = (
                    f"Fn::ForEach::{loop_name} collection must be a "
                    + "list or a reference to a CommaDelimitedList"
                )
                raise exceptions.InvalidModuleError(msg=msg)

            # Track the mapping for GetAtt resolution
            retval[loop_name] = []

            # Process each item in the collection
            for i, value in enumerate(collection):
                # Add to the mapping list
                retval[loop_name].append(value)

                # Process each key in the template fragment
                for template_key, template_value in template_fragment.items():
                    # Replace ${identifier} in the key
                    if isinstance(template_key, str):
                        new_key = replace_identifier(
                            template_key, identifier, value
                        )
                    else:
                        new_key = template_key

                    # Check if the identifier is part of the object key
                    identifier_in_key = isinstance(template_key, str) and (
                        f"${{{identifier}}}" in template_key
                        or f"&{{{identifier}}}" in template_key
                    )

                    # If identifier is in the key, use the key value itself
                    # Otherwise, add an index to ensure unique module names
                    if identifier_in_key:
                        module_id = new_key
                    else:
                        module_id = f"{new_key}{i}"

                    # Create a deep copy of the template value
                    new_value = copy.deepcopy(template_value)

                    # Replace ${identifier} in the value recursively
                    processed_value = foreach_identifier_placeholders(
                        identifier, value, new_value
                    )

                    # Add the processed module to the modules dictionary
                    modules[module_id] = processed_value

                    # Remember the original name for GetAtt resolution
                    modules[module_id][ORIGINAL_FOREACH_NAME] = loop_name
                    modules[module_id][
                        FOREACH_NAME_IS_I
                    ] = not identifier_in_key

            # Remove the ForEach entry
            del modules[k]

    return retval


def resolve_foreach_lists(template, foreach_modules):
    """
    Resolve GetAtts like !GetAtt Content[*].Arn

    These are GetAtts that refer to each instance of
    a module's output. These are converted to lists.
    """

    def vf(v):
        if isdict(v.d) and GETATT in v.d and v.p is not None:
            getatt = v.d[GETATT]
            s = getatt_foreach_list(getatt)
            if s is not None:
                if s in foreach_modules:
                    v.p[v.k] = copy.deepcopy(foreach_modules[s])

    if RESOURCES in template:
        v = Visitor(template[RESOURCES])
        v.visit(vf)

    if OUTPUTS in template:
        for _, val in template[OUTPUTS].items():
            output_val = val.get(VALUE, None)
            if output_val is not None and GETATT in output_val:
                s = getatt_foreach_list(output_val[GETATT])
                if s is not None and s in foreach_modules:
                    # Handling for Override GetAtts to module Outputs
                    # that reference a module with a ForEach
                    val[VALUE] = copy.deepcopy(foreach_modules[s])


def getatt_foreach_list(getatt):
    """
    Converts a getatt array like ['Content[*]', 'Arn'] to a string,
    joining with a dot. 'Content[*].Arn'
    Returns None if the getatt is not a list at least 2 elements long,
    and if the first element does not contain '[*]'
    """
    if isinstance(getatt, list) and len(getatt) > 1:
        if "[*]" in getatt[0]:
            result = ".".join(getatt)  # Content[*].Arn
            return result
    return None


def isdict(v):
    "Returns True if the type is a dict or OrderedDict"
    return isinstance(v, (dict, OrderedDict))
