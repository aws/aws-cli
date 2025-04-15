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

from collections import OrderedDict
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
)


def parse_conditions(d, find_ref):
    """Parse conditions and return a map of name:boolean"""
    retval = {}

    for k, v in d.items():
        retval[k] = istrue(v, find_ref, retval)

    print("conditions:", retval)

    return retval


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

            if val0 == eq[0] and val1 == eq[1]:
                if val0 is None or val1 is None:
                    # One of them is unresolved
                    retval = None
                else:
                    retval = val0 == val1
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


def process_conditions(name, conditions, sections, module_name):
    """
    Omit sections and nodes based on conditions.
    """

    # Check each Resource, Module, and Output
    # to see if a Condition omits it

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
                    section[k][CONDITION] = module_name + oldname

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
    # Otherwise replace the Fn::If with the correct value
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
                # return  # Assume this is a parent template condition?
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

            if not unresolved:
                newval = v.p[v.k]
                if isdict(newval) and REF in newval:
                    if newval[REF] == "AWS::NoValue":
                        del v.p[v.k]

    for section in sections:
        Visitor(section).visit(vf)


def isdict(v):
    "Returns True if the type is a dict or OrderedDict"
    return isinstance(v, (dict, OrderedDict))
