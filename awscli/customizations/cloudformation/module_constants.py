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

Refer to constants in Sub strings later in the template using ${Constant:name}

Constants can refer to other constants that were defined previously.

Adding constants to a template has side effects, since we have to
re-write all Subs in the template! Ideally nothing will change but
it's possible.

Example:

    Constants:
      foo: bar
      baz: abc-${AWS::AccountId}-${Constant::foo}

    Resources:
      Bucket:
        Type: AWS::S3::Bucket
        Metadata:
          Test: !Sub ${Constants:baz}
        Properties:
          BucketName: !Sub ${Constant::foo}

"""

from collections import OrderedDict
from awscli.customizations.cloudformation.parse_sub import WordType
from awscli.customizations.cloudformation.parse_sub import parse_sub
from awscli.customizations.cloudformation.module_visitor import Visitor
from awscli.customizations.cloudformation import exceptions

CONSTANTS = "Constants"
SUB = "Fn::Sub"


def process_constants(d):
    """
    Look for a Constants item in d and if it's found, replace all instances
    of those constants in Subs later in the dictionary.
    Returns a dict of constants.
    """
    if CONSTANTS not in d:
        return None

    constants = {}
    for k, v in d[CONSTANTS].items():
        s = replace_constants(constants, v)
        constants[k] = s

    del d[CONSTANTS]

    return constants


def replace_constants(constants, s):
    """
    Replace all constants in a string or in an entire dictionary.
    If s is a string, returns the modified string.
    If s is a dictionary, modifies the dictionary in place.
    """
    if isinstance(s, str):
        retval = ""
        words = parse_sub(s)
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

    if isdict(s):

        def vf(v):
            if isdict(v.d) and SUB in v.d and v.p is not None:
                s = v.d[SUB]
                if isinstance(s, str):
                    newval = replace_constants(constants, s)
                    if is_sub_needed(newval):
                        v.p[v.k] = {SUB: newval}
                    else:
                        v.p[v.k] = newval

        v = Visitor(s)
        v.visit(vf)

    return None


def isdict(d):
    "Returns true if d is a dict"
    return isinstance(d, (dict, OrderedDict))


def is_sub_needed(s):
    "Returns true if the string has any Sub variables"
    words = parse_sub(s)
    for w in words:
        if w.t != WordType.STR:
            return True
    return False
