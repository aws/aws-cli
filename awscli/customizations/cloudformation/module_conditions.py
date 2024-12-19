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


def parse_conditions(d, find_ref):
    """Parse conditions and return a map of name:boolean"""
    retval = {}

    for k, v in d.items():
        retval[k] = istrue(v, find_ref)

    return retval


def istrue(v, find_ref):
    "Recursive function to evaluate a Condition"
    if EQUALS in v:
        eq = v[EQUALS]
        if len(eq) == 2:
            val0 = eq[0]
            val1 = eq[1]
            if REF in eq[0]:
                val0 = find_ref(eq[0][REF])
            if REF in eq[1]:
                val1 = find_ref(eq[1][REF])
            return val0 == val1
    elif NOT in v:
        if not isinstance(v[NOT], list):
            msg = "Not expression should be a list with 1 element: {v[NOT]}"
            raise exceptions.InvalidModuleError(msg=msg)
        return not istrue(v[NOT][0], find_ref)

    # TODO - Implement the other intrisics

    return False
