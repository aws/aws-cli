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

# pylint: disable=fixme

"""
Parse the Conditions section in a module

If we can fully resolve a condition in a module, it is not emitted into
the parent. Otherwise, it is prefixed with the module name and emitted,
checking to see if there are any duplicate conditions.
"""

import logging
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.modules.visitor import Visitor
from awscli.customizations.cloudformation.modules.names import (
    AND,
    EQUALS,
    IF,
    NOT,
    OR,
    REF,
    CONDITION,
    CONDITIONS,
    MODULES,
    OUTPUTS,
    RESOURCES,
)
from awscli.customizations.cloudformation.modules.util import (
    isdict,
)
from awscli.customizations.cloudformation.modules import resolve


LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


def parse_conditions(m, module_dict):
    """
    Parse conditions and store a map of name:True|False|None.

    None means the condition is unresolved.
    """

    if CONDITIONS not in module_dict:
        return

    def find_ref(v):
        return resolve.find_ref(m, v)

    for k, v in module_dict[CONDITIONS].items():
        m.conditions[k] = istrue(v, find_ref, m.conditions)


def resolve_if(v, find_ref, prior):
    "Resolve Fn::If"
    msg = f"If expression should be a list with 3 elements: {v}"
    if not isinstance(v, list):
        raise exceptions.InvalidModuleError(msg=msg)
    if len(v) != 3:
        raise exceptions.InvalidModuleError(msg=msg)
    if istrue(v[0], find_ref, prior):
        return v[1]
    return v[2]


def is_scalar(val):
    "Returns true if the value is int, str, float, bool"
    return isinstance(val, (int, str, float, bool))


# pylint: disable=too-many-branches,too-many-statements
def istrue(v, find_ref, prior):
    """
    Recursive function to evaluate a Condition.

    Returns True or False if a condition can be fully resolved.
    Otherwise it returns None, which means we have to emit
    the condition into the parent and prefix the name.
    """

    if not isdict(v):
        return False

    retval = False

    if EQUALS in v:
        eq = v[EQUALS]
        if len(eq) == 2:
            val0 = eq[0]
            val1 = eq[1]

            if isdict(val0) and IF in val0:
                val0 = resolve_if(val0[IF], find_ref, prior)
            if isdict(val1) and IF in val1:
                val1 = resolve_if(val1[IF], find_ref, prior)

            if isdict(val0) and REF in val0:
                val0 = find_ref(val0[REF])
            if isdict(val1) and REF in val1:
                val1 = find_ref(val1[REF])

            if is_scalar(val0) and is_scalar(val1):
                retval = val0 == val1
            elif val0 is None or val1 is None:
                # One of them is unresolved
                retval = None
            elif val0 == eq[0] and val1 == eq[1]:
                # Nothing changed.. This avoids infinite recursion,
                # but when would this happen and how would they be equal?
                if val0 == val1:
                    # Identical objects
                    retval = True
                else:
                    # Since at least one is not scalar, it must be unresolved
                    retval = None
            else:
                retval = istrue({EQUALS: [val0, val1]}, find_ref, prior)

        else:
            msg = f"Equals expression should be a list with 2 elements: {eq}"
            raise exceptions.InvalidModuleError(msg=msg)
    if NOT in v:
        if not isinstance(v[NOT], list):
            msg = f"Not expression should be a list with 1 element: {v[NOT]}"
            raise exceptions.InvalidModuleError(msg=msg)
        r = istrue(v[NOT][0], find_ref, prior)
        if r is True or r is False:
            retval = not r
        elif r is None:
            retval = None
        else:
            msg = f"Unexpected NOT: {v}"
            raise exceptions.InvalidModuleError(msg=msg)
    if AND in v:
        vand = v[AND]
        msg = f"And expression should be a list with 2 elements: {vand}"
        if not isinstance(vand, list):
            raise exceptions.InvalidModuleError(msg=msg)
        if len(vand) != 2:
            raise exceptions.InvalidModuleError(msg=msg)
        retval = istrue(vand[0], find_ref, prior) and istrue(
            vand[1], find_ref, prior
        )
    if OR in v:
        vor = v[OR]
        msg = f"Or expression should be a list with 2 elements: {vor}"
        if not isinstance(vor, list):
            raise exceptions.InvalidModuleError(msg=msg)
        if len(vor) != 2:
            raise exceptions.InvalidModuleError(msg=msg)
        retval = istrue(vor[0], find_ref, prior) or istrue(
            vor[1], find_ref, prior
        )
    if IF in v:
        # Shouldn't ever see an IF here
        msg = f"Unexpected If: {v[IF]}"
        raise exceptions.InvalidModuleError(msg=msg)
    if CONDITION in v:
        condition_name = v[CONDITION]
        if condition_name in prior:
            retval = prior[condition_name]
        else:
            msg = f"Condition {condition_name} was not evaluated yet"
            raise exceptions.InvalidModuleError(msg=msg)
            # TODO: Should we re-order the conditions?
            # We are depending on the author putting them in order

    return retval


def process_conditions(m, module_dict):
    """
    Omit sections and nodes based on conditions.

    :param m: The module
    :param module_dict: The raw module object
    """

    name = m.name

    parse_conditions(m, module_dict)

    conditions = m.conditions

    if conditions is None:
        return

    sections = []
    if RESOURCES in module_dict:
        sections.append(module_dict[RESOURCES])
    if MODULES in module_dict:
        sections.append(module_dict[MODULES])
    if OUTPUTS in module_dict:
        sections.append(module_dict[OUTPUTS])

    omit_section_items(sections, conditions, name)

    omit_fn_ifs(sections, conditions, name)

    emit_unresolved_conditions(m, module_dict)


def emit_unresolved_conditions(m, module_dict):
    """
    Emit unresolved Conditions into the parent.
    """

    if CONDITIONS not in module_dict:
        return

    cs = module_dict[CONDITIONS]

    for k, v in m.conditions.items():
        if v is None:
            if CONDITIONS not in m.template:
                m.template[CONDITIONS] = {}
            newname = m.name + k
            if newname in m.template[CONDITIONS]:
                # If they are exactly the same, we don't need it,
                # Otherwise it's a name conflict.
                if m.template[CONDITIONS][newname] != cs[k]:

                    msg = f"Condition name conflict: {newname}"
                    raise exceptions.InvalidModuleError(msg=msg)
            else:
                orig = cs[k].copy()
                m.template[CONDITIONS][newname] = orig


def omit_fn_ifs(sections, conditions, name):
    """
    Omit any properties than have a false Fn::If.
    If the condition is unresolved, leave it and prefix it with the name
    """

    # Example
    #
    # Resources
    #   Foo:
    #     Properties:
    #       Something:
    #         Fn::If:
    #         - ConditionName
    #         - AnObject
    #         - !Ref AWS::NoValue
    #
    # In this case, delete the 'Something' node entirely
    # Otherwise replace the Fn::If with the correct value.
    # If it's unresolved, prepend the module name
    def vf(v):
        if isdict(v.d) and IF in v.d and v.p is not None:
            conditional = v.d[IF]
            if len(conditional) != 3:
                msg = f"Invalid conditional in {name}: {conditional}"
                raise exceptions.InvalidModuleError(msg=msg)
            condition_name = conditional[0]
            trueval = conditional[1]
            falseval = conditional[2]
            if condition_name not in conditions:
                if condition_name.startswith(name):
                    unprefixed = condition_name.replace(name, "", 1)
                    if unprefixed in conditions:
                        # Special case when we re-evaluate conditions
                        return
                    msg = f"{name} Condition not found: {condition_name}"
                    raise exceptions.InvalidModuleError(msg=msg)
            unresolved = False
            if conditions[condition_name] is True:
                v.p[v.k] = trueval
            elif conditions[condition_name] is False:
                v.p[v.k] = falseval
            else:
                # Unresolved, leave it alone
                unresolved = True
                conditional[0] = name + condition_name

            if not unresolved:
                newval = v.p[v.k]
                if isdict(newval) and REF in newval:
                    if newval[REF] == "AWS::NoValue":
                        del v.p[v.k]

    for section in sections:
        Visitor(section).visit(vf)


def omit_section_items(sections, conditions, name):
    """
    Omit sections items like resources that have false conditions.
    If the condition is unresolved, leave it and prefix with the module name
    """
    for section in sections:
        for k, v in section.copy().items():
            if CONDITION not in v:
                continue

            if v[CONDITION] in conditions:
                cval = conditions[v[CONDITION]]
                if cval is False:
                    del section[k]
                elif cval is True:
                    del section[k][CONDITION]
                else:
                    # It's unresolved, leave it and prefix it
                    oldname = section[k][CONDITION]
                    del section[k][CONDITION]
                    section[k][CONDITION] = name + oldname
