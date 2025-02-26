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
This file implements local module support for intrinsics
that are only available on the client.

Fn::Select
Fn::Merge

"""

from collections import OrderedDict
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.module_merge import (
    isdict,
    merge_props,
)
from awscli.customizations.cloudformation.module_visitor import Visitor

MERGE = "Fn::Merge"
SELECT = "Fn::Select"


def fn_select(d):
    """
    Resolve Fn::Select where all items are scalars.
    """

    def vf(v):
        if isdict(v.d) and SELECT in v.d and v.p is not None:
            sel = v.d[SELECT]
            if not isinstance(sel, list) or len(sel) != 2:
                return
            arr = sel[0]
            idx = sel[1]
            if isinstance(idx, (dict, OrderedDict, list)):
                return
            for item in arr:
                if isinstance(item, (dict, OrderedDict, list)):
                    return
            v.p[v.k] = arr[int(idx)]

    Visitor(d).visit(vf)


def fn_merge(d):
    """
    Find all instances of Fn::Merge in the dictionary and merge
    them into a single object.

    Raises an error if any argument to Fn::Merge is not a dictionary,
    or if any of the keys are themselves intrinsic functions that
    cannot be resolved on the client.
    """

    def vf(v):
        if isdict(v.d) and MERGE in v.d and v.p is not None:
            mrg = v.d[MERGE]
            if len(mrg) != 2:
                msg = f"Fn::Merge requires 2 args: {v.k}: {v.d}"
                raise exceptions.InvalidModuleError(msg=msg)
            v.p[v.k] = merge_props(mrg[0], mrg[1])

    Visitor(d).visit(vf)
