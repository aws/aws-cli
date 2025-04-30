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
This file implements looping over module content with either the
ForEach attribute or the Fn::ForEach intrinsic function.

See tests/unit/customizations/cloudformation/modules/*foreach*.yaml
"""


import copy
from collections import OrderedDict
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.modules.visitor import Visitor
from awscli.customizations.cloudformation.modules.parse_sub import (
    is_sub_needed,
)
from awscli.customizations.cloudformation.yamlhelper import yaml_dump
from awscli.customizations.cloudformation.modules.flatten import (
    FLATTEN,
    fn_flatten,
)

IDENTIFIER_PLACEHOLDER = "$Identifier"
INDEX_PLACEHOLDER = "$Index"
VALUE_PLACEHOLDER = "$Value"
SUB = "Fn::Sub"
FOREACH = "ForEach"
REF = "Ref"
PROPERTIES = "Properties"
MODULES = "Modules"
GETATT = "Fn::GetAtt"
RESOURCES = "Resources"
OUTPUTS = "Outputs"
ORIGINAL_FOREACH_NAME = "OriginalForEachName"
VALUE = "Value"
FOREACH_PREFIX = "Fn::ForEach::"
FOREACH_NAME_IS_I = "foreach_name_is_i"
FOREACH_VALUE = "ForEachValue"


def replace_str(s, key, index):
    """
    Replace placeholders in a single string.

    s: The string to alter
    key: The foreach key
    index: The foreach index
    """
    s = s.replace(IDENTIFIER_PLACEHOLDER, key)
    return s.replace(INDEX_PLACEHOLDER, f"{index}")


def replace_identifier(s, identifier, value):
    """
    Replace ${identifier} or &{identifier} in a string with the value.

    s: The string to alter
    identifier: The identifier to replace
    value: The value to replace it with
    """
    # Replace ${identifier} with value
    s = s.replace(f"${{{identifier}}}", value)
    # Replace &{identifier} with value
    s = s.replace(f"&{{{identifier}}}", value)
    return s


def replace(i, token, val):
    "Replace $Identifier and $Index"

    if isinstance(val, (dict, OrderedDict)):
        if SUB in val:
            sub = val[SUB]
            if isinstance(sub, str):
                # Handle both $Identifier/$Index and ${Identifier} formats
                if IDENTIFIER_PLACEHOLDER in sub or INDEX_PLACEHOLDER in sub or "${Identifier}" in sub:
                    r = replace_str(sub, token, i)
                    if is_sub_needed(r):
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
def replace_values(identifier, replacement, original):
    """
    Replace ${identifier} and &{identifier} in values.

    identifier: The identifier name to replace
    replacement: The value to replace it with
    original: The value to process
    """
    if isinstance(original, (dict, OrderedDict)):
        if SUB in original:
            sub = original[SUB]
            if has_identifier(identifier, sub):
                r = replace_identifier(sub, identifier, replacement)
                if is_sub_needed(r):
                    return {SUB: r}
                return r
        elif GETATT in original:
            getatt = original[GETATT]
            new_getatt = []
            for x in getatt:
                if isinstance(x, str) and (has_identifier(identifier, x)):
                    s = replace_identifier(x, identifier, replacement)
                    new_getatt.append(s)
                else:
                    new_getatt.append(x)
            return {GETATT: new_getatt}
        else:
            # Process nested dictionaries
            result = {}
            for k, v in original.items():
                if isinstance(k, str) and has_identifier(identifier, k):
                    new_key = replace_identifier(k, identifier, replacement)
                    r = replace_values(identifier, replacement, v)
                    result[new_key] = r
                else:
                    result[k] = replace_values(identifier, replacement, v)
            return result
    elif isinstance(original, list):
        # Process lists
        return [
            replace_values(identifier, replacement, item) for item in original
        ]
    elif isinstance(original, str):
        return replace_identifier(original, identifier, replacement)
    return original


def has_identifier(identifier, s):
    """
    Check if a string contains an identifier.

    identifier: The identifier to check for
    x: The string to check
    """
    return f"${{{identifier}}}" in s or f"&{{{identifier}}}" in s


# pylint: disable=cell-var-from-loop
def process_module_foreach_item(name, config, retval, parent_module, template):
    """
    Process a single module that has a ForEach.

    ForEach can be:
    1. A comma-separated string
    2. A Ref to a parameter (typically CommaDelimitedList)
    3. A list of objects (typically from Fn::Flatten)
       - each must have an "Identifier" property
    4. A Map where keys serve as identifiers
    """

    modules = template[MODULES]

    # Handle Ref case and validate input
    _resolve_foreach_ref(config, name, parent_module)

    fe = config[FOREACH]

    # Parse the ForEach value into tokens and values
    tokens, values = _parse_foreach_value(fe, name)

    # Store tokens and values for later reference resolution
    _store_foreach_metadata(name, tokens, values, retval, parent_module)

    # Create modules for each token
    _create_foreach_modules(name, config, tokens, values, modules)


def _resolve_foreach_ref(config, k, parent_module):
    """Resolve and validate ForEach references."""

    fe = config[FOREACH]

    if isdict(fe):
        if REF in fe:
            resolved = parent_module.find_ref(fe[REF])
            if resolved is None:
                msg = f"{k} has an invalid ForEach Ref: {fe}"
                raise exceptions.InvalidModuleError(msg=msg)
            config[FOREACH] = resolved
            return

        if FLATTEN in fe:
            parent_module.resolve(fe)
            fn_flatten(config)
            return

        # Validate map keys
        for key in fe:
            if key.startswith("Fn::"):
                msg = f"{k} has invalid ForEach map key: {key}"
                raise exceptions.InvalidModuleError(msg=msg)


def _parse_foreach_value(m, k):
    """Parse ForEach value into tokens and values."""
    tokens = []
    values = {}

    # Handle empty list case
    if isinstance(m, list) and not m:
        print(f"Warning: ForEach for {k} is an empty list")
        return tokens, values

    # List of objects with Identifier property
    if isinstance(m, list) and all(isinstance(item, dict) for item in m):
        for i, item in enumerate(m):
            if "Identifier" not in item:
                msg = (
                    f"{k} ForEach list item at index {i} "
                    + "is missing required 'Identifier' property"
                )
                raise exceptions.InvalidModuleError(msg=msg)

            identifier = str(item["Identifier"])
            tokens.append(identifier)
            values[identifier] = item

    # Map where keys are identifiers
    elif isinstance(m, dict):
        tokens = list(m.keys())
        values = m

    # String (comma-separated list)
    elif isinstance(m, str):
        tokens = m.split(",")
        values = {token: token for token in tokens}

    # Invalid case
    else:
        msg = (
            f"{k} has an invalid ForEach value: must be a string, "
            "map, or list of objects with 'Identifier' property"
        )
        raise exceptions.InvalidModuleError(msg=msg)

    return tokens, values


def _store_foreach_metadata(k, tokens, values, retval, parent_module):
    """Store ForEach metadata for later reference resolution."""
    # Store tokens for later reference resolution
    retval[k] = tokens

    # Store values in parent module for $Value resolution
    if not hasattr(parent_module, "foreach_values"):
        parent_module.foreach_values = {}
    parent_module.foreach_values[k] = values


def _create_foreach_modules(name, config, tokens, values, modules):
    """
    Create modules for each token in the ForEach.

    At the end of this, the original module config is removed and
    replaced by copies with the index appended to the name,
    as if the template author had written them all out manually.

    After this, module processing happens as usual.
    """

    for i, token in enumerate(tokens):
        # The ForEach attribute always uses index-based suffixes.
        module_id = f"{name}{i}"

        copied_module = copy.deepcopy(config)

        # We need to remember the original name for later
        copied_module[ORIGINAL_FOREACH_NAME] = name

        # Store value for $Value resolution if it's a complex value
        value = values.get(token)
        if value is not None and value != token:
            copied_module[FOREACH_VALUE] = value

        del copied_module[FOREACH]

        # Process properties if they exist
        if PROPERTIES in copied_module:
            _process_module_properties(copied_module, i, token)

        modules[module_id] = copied_module

    # Remove the original module config
    del modules[name]


def _process_module_properties(module, i, token):
    """
    Process properties in a copied module, replacing placeholders.
    """

    # First replace $Identifier and $Index
    def vf(vis):
        if vis.p is not None:
            vis.p[vis.k] = replace(i, token, vis.d)

    Visitor(module[PROPERTIES]).visit(vf)

    # Then resolve any $Value references if we have a complex value
    if FOREACH_VALUE in module:
        resolve_foreach_value(module)
        
    # Add handling for ${Identifier} references in Fn::Sub expressions
    def resolve_identifier_refs(vis):
        if vis.p is not None:
            if isinstance(vis.d, dict) and SUB in vis.d:
                sub_val = vis.d[SUB]
                if isinstance(sub_val, str) and "${Identifier}" in sub_val:
                    # Replace ${Identifier} with the actual token
                    new_val = sub_val.replace("${Identifier}", token)
                    if is_sub_needed(new_val):
                        vis.d[SUB] = new_val
                    else:
                        vis.p[vis.k] = new_val
    
    # Process ${Identifier} references
    Visitor(module[PROPERTIES]).visit(resolve_identifier_refs)


def process_module_fnforeach_item(k, v, retval, parent_module, template):
    """
    Process a single module that has Fn::ForEach.

    This works like you would expect for Fn::ForEach, but cannot be
    nested. It is less capable than the simpler ForEach attribute,
    which can handle complex objects in addition to simple lists of strings.

    Fn::ForEach allows you to put the identifier in the logical ID, whereas
    the ForEach attribute always appends an incremented zero-based int.
    """

    modules = template[MODULES]
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
                new_key = replace_identifier(template_key, identifier, value)
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
            processed_value = replace_values(identifier, value, new_value)

            # Add the processed module to the modules dictionary
            modules[module_id] = processed_value

            # Remember the original name for GetAtt resolution
            modules[module_id][ORIGINAL_FOREACH_NAME] = loop_name
            modules[module_id][FOREACH_NAME_IS_I] = not identifier_in_key

    # Remove the ForEach entry
    del modules[k]


# pylint: disable=cell-var-from-loop
# pylint: disable=too-many-statements
def process_module_foreach(t, parent_module):
    """
    Loop over ForEach in modules. Also handles Fn::ForEach that wraps a module.

    Returns a dictionary of module name to [keys],
    for later when we need to expand references that use an array index.

    For example:

    {"Content": ["A", "B", "C"]}
    """
    retval = {}

    for k, v in t[MODULES].copy().items():

        # Process ForEach attribute
        if FOREACH in v:
            process_module_foreach_item(k, v, retval, parent_module, t)

        # Process Fn::ForEach
        if k.startswith(FOREACH_PREFIX):
            process_module_fnforeach_item(k, v, retval, parent_module, t)

    return retval


def resolve_foreach_value(copied_module):
    """
    Resolve foreach placeholders that are values.
    """
    value_obj = copied_module[FOREACH_VALUE]

    # Resolve $Value references in properties
    def resolve_value_refs(v):
        if v.p is None:
            return

        # Direct $Value replacement
        if isinstance(v.d, str) and VALUE_PLACEHOLDER in v.d:
            # Replace $Value with actual property values
            if v.d == VALUE_PLACEHOLDER:
                v.p[v.k] = value_obj
            elif v.d.startswith(f"{VALUE_PLACEHOLDER}."):
                # The prop name is the last part of the string
                prop_name = v.d.split(".")[-1]
                if isinstance(value_obj, dict) and prop_name in value_obj:
                    v.p[v.k] = value_obj[prop_name]
        
        # Handle Fn::Sub with ${Value.X} references
        elif isinstance(v.d, dict) and SUB in v.d:
            sub_val = v.d[SUB]
            if isinstance(sub_val, str):
                modified = False
                
                # Replace ${Value.X} with actual values
                for prop_name, prop_value in value_obj.items():
                    if isinstance(prop_value, (str, int, float, bool)):
                        placeholder = f"${{Value.{prop_name}}}"
                        if placeholder in sub_val:
                            sub_val = sub_val.replace(placeholder, str(prop_value))
                            modified = True
                
                # Update the value if modified
                if modified:
                    # If no more placeholders need substitution, convert to plain string
                    if not is_sub_needed(sub_val):
                        v.p[v.k] = sub_val
                    else:
                        v.d[SUB] = sub_val

    # First pass: process all properties
    Visitor(copied_module[PROPERTIES]).visit(resolve_value_refs)


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
