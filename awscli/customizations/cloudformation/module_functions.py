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
import os
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.module_merge import (
    isdict,
    merge_props,
)
from awscli.customizations.cloudformation.module_visitor import Visitor

MERGE = "Fn::Merge"
SELECT = "Fn::Select"
REF = "Ref"
GETATT = "Fn::GetAtt"
INSERT_FILE = "Fn::InsertFile"


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
            if not isinstance(arr, list):
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
    """

    def vf(v):
        if isdict(v.d) and MERGE in v.d and v.p is not None:
            mrg = v.d[MERGE]
            if not isinstance(mrg, list):
                msg = f"Fn::Merge requires a list: {v.k}: {v.d}"
                raise exceptions.InvalidModuleError(msg=msg)
            if len(mrg) < 2:
                msg = f"Fn::Merge requires at least 2 args: {v.k}: {v.d}"
                raise exceptions.InvalidModuleError(msg=msg)
            result = None
            is_list = True
            if isinstance(mrg[0], list):
                result = []
            else:
                result = {}
                is_list = False
            for _, m in enumerate(mrg):
                # If there are any unresolved Refs, leave these alone
                # so that the parent can resolve them
                if REF in m:
                    return
                if GETATT in m:
                    return
                msg = f"Fn::Merge items types mismatch: {v.k}: {v.d}"
                if is_list and not isinstance(m, list):
                    raise exceptions.InvalidModuleError(msg=msg)
                if not is_list and isinstance(m, list):
                    raise exceptions.InvalidModuleError(msg=msg)
                result = merge_props(result, m)
            v.p[v.k] = result

    Visitor(d).visit(vf)


def fn_insertfile(d, base_path):
    "Insert file contents into the template"

    def vf(v):
        if isdict(v.d) and INSERT_FILE in v.d and v.p is not None:
            content = ""
            relative_path = v.d[INSERT_FILE]
            abs_path = os.path.join(base_path, relative_path)
            norm_path = os.path.normpath(abs_path)
            with open(norm_path, "r", encoding="utf-8") as s:
                content = s.read()
            v.p[v.k] = content

    Visitor(d).visit(vf)
