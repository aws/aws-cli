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

This section is not emitted into the output.
We have to be able to fully resolve it locally.
"""

from collections import OrderedDict
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.module_visitor import Visitor

AND = "Fn::And"
EQUALS = "Fn::Equals"
IF = "Fn::If"
NOT = "Fn::Not"
OR = "Fn::Or"
REF = "Ref"
CONDITION = "Condition"


def parse_conditions(d, find_ref):
    """Parse conditions and return a map of name:boolean"""
    retval = {}

    for k, v in d.items():
        retval[k] = istrue(v, find_ref, retval)

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
    "Recursive function to evaluate a Condition"
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
            # Recurse for nested IFs
            if val0 == eq[0] and val1 == eq[1]:
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
        retval = not istrue(v[NOT][0], find_ref, prior)
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


def process_conditions(name, conditions, modules, resources, outputs):
    """
    Visit all modules, resources, and outputs
    to look for Fn::If conditions
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
            if conditions[condition_name]:
                v.p[v.k] = trueval
            else:
                v.p[v.k] = falseval
            newval = v.p[v.k]
            if isdict(newval) and REF in newval:
                if newval[REF] == "AWS::NoValue":
                    del v.p[v.k]

    Visitor(modules).visit(vf)
    Visitor(resources).visit(vf)
    Visitor(outputs).visit(vf)


def isdict(v):
    "Returns True if the type is a dict or OrderedDict"
    return isinstance(v, (dict, OrderedDict))
