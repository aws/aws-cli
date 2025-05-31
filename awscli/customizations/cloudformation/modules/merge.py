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
This file implements module override merges.
"""

from awscli.customizations.cloudformation.modules.util import isdict


def merge_props(original, overrides):
    """
    This function merges dicts, replacing values in the original with
    overrides.  This function is recursive and can act on lists and scalars.
    See the unit tests for example merges.
    See tests/unit/customizations/cloudformation/modules/policy-*.yaml

    :return A new value with the overridden properties
    """
    original_type = type(original)
    override_type = type(overrides)
    if not isdict(overrides) and override_type is not list:
        return overrides

    if original_type is not override_type:
        return overrides

    if isdict(original):
        retval = original.copy()
        for k in original:
            if k in overrides:
                retval[k] = merge_props(retval[k], overrides[k])
        for k in overrides:
            if k not in original:
                retval[k] = overrides[k]
        return retval

    # original and overrides are lists
    new_list = []
    for item in original:
        new_list.append(item)
    for item in overrides:
        new_list.append(item)
    return new_list
