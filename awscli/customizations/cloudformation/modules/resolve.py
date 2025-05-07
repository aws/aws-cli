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
Module reference resolution.
"""

from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.modules.names import (
    DEFAULT,
    GETATT,
    REF,
    SUB,
)
from awscli.customizations.cloudformation.modules.parse_sub import (
    WordType,
    is_sub_needed,
    parse_sub,
)
from awscli.customizations.cloudformation.modules.util import isdict
from awscli.customizations.cloudformation.modules.visitor import Visitor

# pylint: disable=fixme


def resolve(module, resource):
    "Resolve references in the resource"

    # TODO: If we just called this at a high level at some
    # point during processing, we probably wouldn't need to
    # pass around the find_ref function. Nodes would already
    # be resolved before processing.

    def vf(v):
        if not isdict(v.d) or v.p is None:
            return
        if REF in v.d:
            resolve_ref(module, v.d[REF], v.p, v.k)
        elif SUB in v.d:
            resolve_sub(module, v.d[SUB], v.p, v.k)
        elif GETATT in v.d:
            resolve_getatt(module, v.d[GETATT], v.p, v.k)

    Visitor(resource).visit(vf)


def resolve_ref(module, v, d, n):
    """
    Look for the Ref in the parent template Properties if it matches
    a module Parameter name. If it's not there, use the default if
    there is one. If not, raise an error.

    If there is no matching Parameter, look for a resource with that
    name in this module and fix the logical id so it has the prefix.

    Otherwise raise an exception.
    """
    if not isinstance(v, str):
        msg = f"Ref should be a string: {v}"
        raise exceptions.InvalidModuleError(msg=msg)

    found = find_ref(module, v)
    if found is not None:
        d[n] = found
    else:
        if isinstance(v, str) and v.startswith("AWS::"):
            pass  # return
        # msg = (
        #    f"Not found in {module.source}: {n}: {v}"
        # )
        # raise exceptions.InvalidModuleError(msg=msg)
        #
        # Ideally we would raise an exception here. But in the case
        # of a sub-module referring to another sub-module in
        # the Overrides section, the name has already been fixed,
        # so we won't find it in this template or in parameters.
        # This is identical to the possiblity that a module author
        # might refer to something directly in the parent, without
        # an input. The tradeoff is that we can't detect legit typos.
        # We have to depend on cfn-lint on the final template.


def resolve_sub_ref(module, w):
    "Resolve a ref inside of a Sub string"
    resolved = "${" + w + "}"
    found = find_ref(module, w)
    if found is not None:
        if isinstance(found, str):
            resolved = found
        else:
            if REF in found:
                resolved = "${" + found[REF] + "}"
            elif SUB in found:
                resolved = found[SUB]
            elif GETATT in found:
                tokens = found[GETATT]
                if len(tokens) < 2:
                    msg = (
                        "Invalid Sub referencing a GetAtt. " + f"{w}: {found}"
                    )
                    raise exceptions.InvalidModuleError(msg=msg)

                resolved = "${" + ".".join(tokens) + "}"
    return resolved


def resolve_sub_getatt(module, w):
    "Resolve a GetAtt ('A.B') inside a Sub string"
    tokens = w.split(".", 1)
    if len(tokens) < 2:
        msg = f"GetAtt {w} has unexpected number of tokens"
        raise exceptions.InvalidModuleError(msg=msg)

    # Create a fake getatt
    n = "fake"
    d = {n: None}
    resolve_getatt(module, tokens, d, n)

    resolved = convert_resolved_sub_getatt(d[n])
    if not resolved:
        resolved = "${" + w + "}"
    return resolved


def convert_resolved_sub_getatt(r):
    """
    Convert a part of a Sub that has a GetAtt.
    """
    resolved = ""
    if r is not None:
        if GETATT in r:
            getatt = r[GETATT]
            resolved = "${" + ".".join(getatt) + "}"
        elif SUB in r:
            resolved = r[SUB]
        elif REF in r:
            resolved = "${" + r[REF] + "}"
        else:
            # Handle scalar properties
            resolved = r

    return resolved


# pylint: disable=too-many-branches,unused-argument
def resolve_sub(module, v, d, n):
    """
    Parse the Sub string and break it into tokens.

    If we can fully resolve it, we can replace it with a string.

    Use the same logic as with resolve_ref.
    """

    words = parse_sub(v, True)
    sub = ""
    for word in words:
        if word.t == WordType.STR:
            sub += word.w
        elif word.t == WordType.AWS:
            sub += "${AWS::" + word.w + "}"
        elif word.t == WordType.REF:
            sub += resolve_sub_ref(module, word.w)
        elif word.t == WordType.GETATT:
            sub += resolve_sub_getatt(module, word.w)

    need_sub = is_sub_needed(sub)
    if need_sub:
        d[n] = {SUB: sub}
    else:
        d[n] = sub


def resolve_getatt(module, v, d, n):
    """
    Resolve a GetAtt. All we do here is add the prefix.

    !GetAtt Foo.Bar becomes !GetAtt ModuleNameFoo.Bar

    Also handles GetAtts that reference Parameters that are maps:
    !GetAtt Name[*] - Get the keys in the map
    !GetAtt Name[Key] - Get the entire object for Key
    !GetAtt Name[Key].Attribute - Get an attribute
    """
    if not isinstance(v, list):
        msg = f"GetAtt {v} is not a list"
        raise exceptions.InvalidModuleError(msg=msg)

    if resolve_getatt_map_param(module, v, d, n):
        return

    # Standard resource GetAtt handling
    # Make sure the logical id exists
    exists = False
    for resource in module.resources:
        if resource == v[0]:
            exists = True
            break
    if exists:
        logical_id = module.name + v[0]
        d[n] = {GETATT: [logical_id, v[1]]}


def resolve_getatt_map_param(module, v, d, n):
    """
    Try to resolve a GetAtt that refers to a Parameter that is a map.
    """
    name = v[0]

    if not isinstance(name, str):
        msg = f"name is not a string: {name}"
        raise exceptions.InvalidModuleError(msg=msg)

    prop_name = v[1] if len(v) > 1 else ""

    # Check for map parameter access with [*] syntax
    index = -1
    if "[]" in name:
        msg = f"Invalid GetAtt: {name}, did you mean [*]?"
        raise exceptions.InvalidModuleError(msg=msg)
    if "[*]" in name:

        name = name.replace("[*]", "")

        if name not in module.parent_module.foreach_modules:
            # This is a reference to all values: Name[*]
            # Check if it's a Map parameter
            if name in module.props and isinstance(module.props[name], dict):
                map_value = module.props[name]

                # Handle !GetAtt MapName[*] - return list of keys
                if prop_name == "":
                    d[n] = list(map_value.keys())
                    return True

                # Handle !GetAtt MapName[*].AttributeName -
                # return a list of all values for that attribute
                result = []
                for key in map_value:
                    if (
                        isinstance(map_value[key], dict)
                        and prop_name in map_value[key]
                    ):
                        result.append(map_value[key][prop_name])
                if result:
                    d[n] = result
                    # Also store in foreach_modules to make
                    # it accessible to parent
                    key_name = f"{name}[*].{prop_name}"
                    module.parent_module.foreach_modules[key_name] = result

                    # Also store with the module name for output references
                    # This is needed for Map parameters accessed
                    # via module outputs
                    if module.name:
                        module_output_key = f"{module.name}.{key_name}"
                        module.parent_module.foreach_modules[
                            module_output_key
                        ] = result
                    return True
    elif "[" in name:
        tokens = name.split("[")
        name = tokens[0]
        if tokens[1] != "]":
            num = tokens[1].replace("]", "")
            if num.isdigit():
                index = int(num)
            else:
                # Support Name[A], Name['A']
                index = num.strip('"').strip("'")

    # Check if this is a Map parameter access with a specific key
    if name not in module.parent_module.foreach_modules:
        if name in module.props and isinstance(module.props[name], dict):
            map_value = module.props[name]

            # Handle !GetAtt MapName[Key] -
            # return entire object at that key
            if index != -1 and isinstance(index, str) and index in map_value:

                if prop_name == "":
                    d[n] = map_value[index]
                    return True

                # Handle !GetAtt MapName[Key].Attribute -
                # return specific attribute
                if (
                    isinstance(map_value[index], dict)
                    and prop_name in map_value[index]
                ):
                    d[n] = map_value[index][prop_name]
                    return True

    return False


def find_ref(module, name):
    """
    Find a Ref.

    A Ref might be to a module Parameter with a matching parent
    template Property, or a Parameter Default. It could also
    be a reference to another resource in this module.

    :param name The name to search for
    :return The referenced element or None
    """
    if name in module.props:
        if name not in module.module_parameters:
            # The parent tried to set a property that doesn't exist
            # in the Parameters section of this module
            msg = f"{name} not found in module Parameters: {module.source}"
            raise exceptions.InvalidModuleError(msg=msg)

        p = module.props[name]
        if isdict(p):
            if module.parent_module.name != "" and REF in p:
                p = find_ref(module.parent_module, p[REF])
        return p

    if name in module.module_parameters:
        param = module.module_parameters[name]
        if DEFAULT in param:
            # Use the default value of the Parameter
            return param[DEFAULT]
        msg = f"{name} does not have a Default and is not a Property"
        raise exceptions.InvalidModuleError(msg=msg)

    for logical_id in module.resources:
        if name == logical_id:
            # Simply rename local references to include the module name
            return {REF: module.name + logical_id}

    return None
