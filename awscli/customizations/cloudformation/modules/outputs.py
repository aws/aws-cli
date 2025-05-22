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
Module output resolution.

These functions look at each key in the Outputs section of a module
to find and replace any references to those keys in the parent.
"""

import copy
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.modules.foreach import (
    getatt_foreach_list,
)
from awscli.customizations.cloudformation.modules.names import (
    RESOURCES,
    REF,
    SUB,
    GETATT,
    MODULES,
    OUTPUTS,
)
from awscli.customizations.cloudformation.modules.parse_sub import (
    WordType,
    is_sub_needed,
    parse_sub,
)
from awscli.customizations.cloudformation.modules.util import isdict
from awscli.customizations.cloudformation.modules.visitor import Visitor
from awscli.customizations.cloudformation.modules.resolve import (
    convert_resolved_sub_getatt,
    find_ref,
    resolve_getatt,
)


def process_module_outputs(module):
    """
    Fix parent template Ref, GetAtt, and Sub that point to module outputs.

    In the parent you can !GetAtt ModuleName.OutputName
    This will be converted so that it's correct in the packaged template.

    Recurse over all sections in the parent template looking for
    GetAtts and Subs that reference a module Outputs value.

    This function is running from the module, inspecting everything
    in the partially resolved parent template.
    """

    def vf(v):
        if not isdict(v.d) or v.p is None:
            return
        if SUB in v.d:
            resolve_output_sub(module, v.d[SUB], v.p, v.k)
        elif GETATT in v.d:
            resolve_output_getatt(module, v.d[GETATT], v.p, v.k)
        # Refs can't point to module outputs since we need Module.Output

    sections = [RESOURCES, MODULES, OUTPUTS]
    for section in sections:
        if section not in module.template:
            continue
        Visitor(module.template[section]).visit(vf)


def resolve_output_sub_getatt(module, w):
    """
    Resolve a reference to a module in a Sub GetAtt word.

    For example, the parent has

    Modules:
      A:
        Properties:
          Name: foo
    Outputs:
      B:
        Value: !Sub ${A.MyName}

    The module has:

      Parameters:
        Name:
          Type: String
      Resources:
        X:
          Properties:
            Y: !Ref Name
      Outputs:
        MyName: !GetAtt X.Name

    The resulting output:
      B: !Sub ${AX.Name}

    """

    tokens = w.split(".", 1)
    if len(tokens) < 2:
        msg = f"GetAtt {w} has unexpected number of tokens"
        raise exceptions.InvalidModuleError(msg=msg)

    # !Sub ${Content.BucketArn} -> !Sub ${ContentBucket.Arn}

    # Create a fake getatt and resolve it like normal
    n = "fake"
    d = {n: None}
    resolve_output_getatt(module, tokens, d, n)
    r = d[n]

    resolved = convert_resolved_sub_getatt(r)
    if not resolved:
        resolved = "${" + w + "}"
    return resolved


def resolve_output_sub(module, v, d, n):
    "Resolve a Sub that refers to a module reference or property"
    words = parse_sub(v, True)
    sub = ""
    for word in words:
        if word.t == WordType.STR:
            sub += word.w
        elif word.t == WordType.AWS:
            sub += "${AWS::" + word.w + "}"
        elif word.t == WordType.REF:
            # A ref to a module reference has to be a getatt
            resolved = "${" + word.w + "}"
            sub += resolved
        elif word.t == WordType.GETATT:
            resolved = resolve_output_sub_getatt(module, word.w)
            if not isinstance(resolved, str):
                msg = f"Sub expected a string in {module.name}, got {resolved}"
                raise exceptions.InvalidModuleError(msg=msg)
            sub += resolved

    if is_sub_needed(sub):
        d[n] = {SUB: sub}
    else:
        d[n] = sub


# pylint:disable=too-many-branches,too-many-locals,too-many-statements
# pylint:disable=too-many-return-statements
def resolve_output_getatt(module, v, d, n):
    """
    Resolve a GetAtt that refers to a module Output.

    This might be a simple reference to an Output Value like
    !Get ModuleName.OutputName.

    It might be a reference to a module that was in a ForEach loop,
    so we can !GetAtt ModuleName[0].OutputName or
    !GetAtt ModuleName[Identifier].OutputName.

    We can !GetAtt ModuleName[*].OutputName to get a list of all
    output values for a module that was in a foreach.

    These can also be references to Parameters that are maps.

    :param v The value
    :param d The dictionary
    :param n The name of the node

    This function sets d[n] and returns True if it resolved.
    """

    if not isinstance(v, list) or len(v) < 2:
        msg = f"GetAtt {v} invalid"
        raise exceptions.InvalidModuleError(msg=msg)

    # For example, Content.Arn or Content[0].Arn

    foreach_modules = None
    if module.parent_module:
        foreach_modules = module.parent_module.foreach_modules
    else:
        foreach_modules = module.foreach_modules

    name = v[0]
    prop_name = v[1]

    index = -1
    if "[]" in name:
        msg = f"Invalid GetAtt: {name}, did you mean [*]?"
        raise exceptions.InvalidModuleError(msg=msg)

    # Handle ModuleName.* the same as ModuleName[*]
    # This is passed in like [Storage, *.BucketArn]
    if "*." in prop_name:
        base_name = name
        prop_name = prop_name.replace("*.", "")

        if base_name in foreach_modules:
            resolve_output_getatt_foreach(
                module, foreach_modules, base_name, prop_name
            )
            return True
    elif "[*]" in name:
        # This is a reference to all of the foreach values
        # For example, Content[*].Arn
        base_name = name.split("[")[0]
        if base_name in foreach_modules:
            resolve_output_getatt_foreach(
                module, foreach_modules, base_name, prop_name
            )
            return True
    # Handle ModuleName.Identifier.OutputName the same as ModuleName[Identifier].OutputName
    elif (
        "." in prop_name
        and len(prop_name.split(".")) > 1
        and name in foreach_modules
    ):
        # This is the ModuleName.Identifier.OutputName format
        parts = prop_name.split(".", 2)
        identifier = parts[0]
        prop_name = parts[1]

        # If there's a third part, it's part of the property path
        if len(parts) > 2:
            prop_name = f"{parts[2]}.{prop_name}"

        # Directly resolve to the correct resource for dot notation
        if name in foreach_modules:
            # Find the array index for the identifier
            if isinstance(identifier, str):
                for i, k in enumerate(foreach_modules[name]):
                    if identifier == k:
                        d[n] = {GETATT: [f"{name}{i}", prop_name]}
                        return True

        # Continue with normal processing if we couldn't directly resolve
        index = identifier
    elif "[" in name:
        tokens = name.split("[")
        name = tokens[0]
        num = tokens[1].replace("]", "")
        if num.isdigit():
            index = int(num)
        else:
            # Support Content[A].Arn, Content['A'].Arn
            index = num.strip('"').strip("'")

    # index might be a number like 0: Content[0].Arn
    # or it might be a key like A: Content[A].Arn
    # The name of the foreach module might be Content0 or ContentA,
    # depending on if we used an Fn::ForEach identifier.

    # Handle ForEach module references
    if index != -1 and name in foreach_modules:
        if isinstance(index, int):
            name = f"{name}{index}"
        else:
            # Find the array index for the key
            if not module.foreach_name_is_i:
                # If Fn::ForEach was used with an identifier for
                # the logical id, we need to use that instead of the index
                name = f"{name}{index}"
            else:
                # The foreach name uses the array index
                for i, k in enumerate(foreach_modules[name]):
                    if index == k:
                        name = f"{name}{i}"

    reffed_prop = None
    if name == module.name:
        if prop_name in module.module_outputs:
            reffed_prop = module.module_outputs[prop_name]
        elif prop_name in module.props:
            reffed_prop = module.props[prop_name]

    if reffed_prop is None:
        return False

    # Handle the case where the output value is a GetAtt to a resource with ForEach
    if isinstance(reffed_prop, dict) and GETATT in reffed_prop:
        getatt_ref = reffed_prop[GETATT]
        if isinstance(getatt_ref, list) and len(getatt_ref) >= 2:
            resource_name = getatt_ref[0]
            property_path = getatt_ref[1]

            # Check if this is a reference to a resource with ForEach using [*] syntax
            if "[*]" in resource_name:
                base_name = resource_name.split("[")[0]
                # Check if we have resource identifiers from ForEach processing
                if (
                    hasattr(module, "resource_identifiers")
                    and base_name in module.resource_identifiers
                ):
                    # Create a list of GetAtt references to each copied resource
                    resource_list = []
                    for i, _ in enumerate(
                        module.resource_identifiers[base_name]
                    ):
                        resource_list.append(
                            {
                                GETATT: [
                                    f"{module.name}{base_name}{i}",
                                    property_path,
                                ]
                            }
                        )
                    d[n] = resource_list
                    return True

            # Check if this is a reference to a specific instance using [identifier] syntax
            elif "[" in resource_name and "]" in resource_name:
                base_name = resource_name.split("[")[0]
                identifier = resource_name.split("[")[1].split("]")[0]

                if (
                    hasattr(module, "resource_identifiers")
                    and base_name in module.resource_identifiers
                ):
                    keys = module.resource_identifiers[base_name]
                    if identifier in keys:
                        index = keys.index(identifier)
                        d[n] = {
                            GETATT: [
                                f"{module.name}{base_name}{index}",
                                property_path,
                            ]
                        }
                        return True

    if isinstance(reffed_prop, list):
        for i, r in enumerate(reffed_prop):
            replace_reffed_prop(module, r, reffed_prop, i)
            d[n] = reffed_prop
    else:
        replace_reffed_prop(module, reffed_prop, d, n)

    return True


def replace_reffed_prop(module, r, d, n):
    """
    Replace a reffed prop in an output getatt.

    param r: The Ref, Sub, or GetAtt

    Sets d[n].
    """

    if REF in r:
        ref = r[REF]
        found = find_ref(module, ref)
        if found:
            d[n] = found
        else:
            d[n] = {REF: module.name + ref}
    elif GETATT in r:
        getatt = r[GETATT]
        if len(getatt) < 2:
            msg = f"GetAtt {getatt} in {module.name} is invalid"
            raise exceptions.InvalidModuleError(msg=msg)
        s = getatt_foreach_list(getatt)
        if s is not None and s in module.foreach_modules:
            # Special handling for Overrides that GetAtt a module
            # property, when that module has a ForEach attribute
            if isinstance(module.foreach_modules[s], list):
                d[n] = copy.deepcopy(module.foreach_modules[s])
                for item in d[n]:
                    if GETATT in item and len(item[GETATT]) > 0:
                        item[GETATT][0] = module.name + item[GETATT][0]
        else:
            resolve_getatt(module, getatt, d, n)

    elif SUB in r:
        # Parse the Sub in the module reference
        words = parse_sub(r[SUB], True)
        sub = ""
        for word in words:
            if word.t == WordType.STR:
                sub += word.w
            elif word.t == WordType.AWS:
                sub += "${AWS::" + word.w + "}"
            elif word.t == WordType.REF:
                # This is a ref to a param or resource
                # If it's a resource, concatenante the name
                resolved = "${" + word.w + "}"
                if word.w in module.resources:
                    resolved = "${" + module.name + word.w + "}"
                elif word.w in module.module_parameters:
                    found = find_reffed_param(module, word.w)
                    if found:
                        resolved = found
                sub += resolved
            elif word.t == WordType.GETATT:
                resolved = "${" + word.w + "}"
                tokens = word.w.split(".", 1)
                if len(tokens) < 2:
                    msg = f"GetAtt {word.w} unexpected length"
                    raise exceptions.InvalidModuleError(msg=msg)
                if tokens[0] in module.resources:
                    resolved = "${" + module.name + word.w + "}"
                sub += resolved
        if is_sub_needed(sub):
            d[n] = {SUB: sub}
        else:
            d[n] = sub
    elif isdict(r):
        # An intrinsic like Join.. recurse
        for rk, rv in r.copy().items():
            replace_reffed_prop(module, rv, r, rk)
            d[n] = r
    elif isinstance(r, list):
        for ri, rv in enumerate(r):
            replace_reffed_prop(module, rv, r, ri)
            d[n] = r
    else:
        # Handle scalars in Properties
        d[n] = r


def find_reffed_param(module, w):
    "Find a reffed parameter in an output sub"
    resolved = None
    found = find_ref(module, w)
    if found:
        resolved = found
        if not isinstance(resolved, str):
            if SUB in resolved:
                resolved = resolved[SUB]
            else:
                msg = f"Expected str in {module.name}: {resolved}"
                raise exceptions.InvalidModuleError(msg=msg)
    return resolved


def resolve_output_getatt_foreach(module, foreach_modules, name, prop_name):
    "Resolve GetAtts that reference all Outputs from a foreach module"

    num_items = len(foreach_modules[name])
    dd = [None] * num_items

    # Create lists for the requested property
    bracket_key = name + "[*]." + prop_name
    dot_key = name + ".*." + prop_name

    if bracket_key not in foreach_modules:
        foreach_modules[bracket_key] = []
    if dot_key not in foreach_modules:
        foreach_modules[dot_key] = []

    for i in range(num_items):
        # Resolve the item as if it was a normal getatt
        vv = [f"{name}{i}", prop_name]
        resolved = resolve_output_getatt(module, vv, dd, i)
        if resolved:
            # Don't set anything here, just remember it so
            # we can go back and fix the entire getatt later
            item_val = dd[i]

            if item_val not in foreach_modules[bracket_key]:
                # Don't double add. We already replaced refs in
                # modules, so it shows up twice.
                foreach_modules[bracket_key].append(item_val)
                foreach_modules[dot_key].append(item_val)
