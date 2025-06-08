# Copyright 2012-2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
Module constants.

Add a Constants section to the module or the parent template for
string constants, to help reduce copy-paste within the template.

Refer to constants in Sub strings later in the template using ${Const::name}

You can also create constants that are objects, which can be referred to
with Ref.

Constants can refer to other constants that were defined previously.

Adding constants to a template has side effects, since we have to
re-write all Subs in the template! Ideally nothing will change but
it's possible.

Example:

    Constants:
      foo: bar
      baz: abc-${AWS::AccountId}-${Const::foo}
      obj:
        AnObject:
            Foo: bar

    Resources:
      Bucket:
        Type: AWS::S3::Bucket
        Metadata:
          Test: !Sub ${Const::baz}
          TestObj: !Ref Const::obj
        Properties:
          BucketName: !Sub ${Const::foo}

"""

from collections import OrderedDict
from awscli.customizations.cloudformation.modules.parse_sub import WordType
from awscli.customizations.cloudformation.modules.parse_sub import parse_sub
from awscli.customizations.cloudformation.modules.parse_sub import (
    is_sub_needed,
)
from awscli.customizations.cloudformation.modules.visitor import Visitor
from awscli.customizations.cloudformation import exceptions

CONSTANTS = "Constants"
SUB = "Fn::Sub"
REF = "Ref"
CONSTANT_REF = "Const::"


def process_constants(d):
    """
    Look for a Constants item in d and if it's found, return it
    as a dict. Looks for references to previously defined constants
    and substitutes them.
    Deletes the Constants item from d.
    Returns a dict of the constants.
    """
    if CONSTANTS not in d:
        return None

    constants = {}
    for k, v in d[CONSTANTS].items():
        s = replace_constants(constants, v)
        if s is not None:
            constants[k] = s
        else:
            # Add an object constant
            constants[k] = v

    del d[CONSTANTS]

    return constants


def replace_constants(constants, item):
    """
    Replace all constants in a string or in an entire dictionary.
    If item is a string, returns the modified string.
    If item is a dictionary, modifies the dictionary in place.
    """
    if isinstance(item, str):
        retval = ""
        words = parse_sub(item)
        for w in words:
            if w.t == WordType.STR:
                retval += w.w
            if w.t == WordType.REF:
                retval += f"${{{w.w}}}"
            if w.t == WordType.AWS:
                retval += f"${{AWS::{w.w}}}"
            if w.t == WordType.GETATT:
                retval += f"${{{w.w}}}"
            if w.t == WordType.CONSTANT:
                if w.w in constants:
                    retval += constants[w.w]
                else:
                    msg = f"Unknown constant: {w.w}"
                    raise exceptions.InvalidModuleError(msg=msg)
        return retval

    if isdict(item):

        # Recursively dive into d and replace all string constants
        # that are found in Subs.
        # Also replace Refs to objects

        def vf(v):
            if isdict(v.d) and SUB in v.d and v.p is not None:
                s = v.d[SUB]
                if isinstance(s, str):
                    newval = replace_constants(constants, s)
                    if is_sub_needed(newval):
                        v.p[v.k] = {SUB: newval}
                    else:
                        v.p[v.k] = newval
            if isdict(v.d) and REF in v.d and v.p is not None:
                r = v.d[REF]
                # If this has the form Const::name, replace it
                if r.startswith(CONSTANT_REF):
                    r = r.replace(CONSTANT_REF, "")
                    if r in constants:
                        v.p[v.k] = constants[r]

        v = Visitor(item)
        v.visit(vf)

    return None


def isdict(d):
    "Returns true if d is a dict"
    return isinstance(d, (dict, OrderedDict))
