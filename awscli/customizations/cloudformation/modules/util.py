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
Helper functions for debugging.
"""

from collections import OrderedDict
from awscli.customizations.cloudformation import yamlhelper


def yamlstr(v):
    """
    Convert a dictionary to a yaml string.
    This is useful for debugging.
    """
    if not isdict(v):
        return v
    return yamlhelper.yaml_dump(v)


def isdict(v):
    """Returns True if the type is a dict or OrderedDict"""
    return isinstance(v, (dict, OrderedDict))
