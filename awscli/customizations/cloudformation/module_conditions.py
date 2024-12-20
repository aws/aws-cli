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

from awscli.customizations.cloudformation import exceptions

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
    retval = False
    if EQUALS in v:
        eq = v[EQUALS]
        if len(eq) == 2:
            val0 = eq[0]
            val1 = eq[1]
            if IF in val0:
                val0 = resolve_if(val0[IF], find_ref, prior)
            if IF in val1:
                val1 = resolve_if(val1[IF], find_ref, prior)
            if REF in val0:
                val0 = find_ref(val0[REF])
            if REF in val1:
                val1 = find_ref(val1[REF])
            retval = val0 == val1
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
