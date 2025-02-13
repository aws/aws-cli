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
Read CloudFormation Module source files.
"""

import os
import urllib

from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation import yamlhelper


def is_url(p):
    "Returns true if the path looks like a URL instead of a local file"
    return p.startswith("https")


def read_source(source):
    """
    Read the source file and return the content as a string,
    plus a dictionary with line numbers.
    """

    if not isinstance(source, str):
        raise exceptions.InvalidModulePathError(source=source)

    if is_url(source):
        try:
            with urllib.request.urlopen(source) as response:
                return response.read()
        except Exception as e:
            print(e)
            raise exceptions.InvalidModulePathError(source=source)

    if not os.path.isfile(source):
        raise exceptions.InvalidModulePathError(source=source)

    content = ""
    with open(source, "r", encoding="utf-8") as s:
        content = s.read()

    node = yamlhelper.yaml_compose(content)
    lines = {}
    read_line_numbers(node, lines)

    return content, lines


def read_line_numbers(node, lines):
    """
    Read resource line numbers from a yaml node,
    using the logical id as the key.
    """
    for n in node.value:
        if n[0].value == "Resources":
            resource_map = n[1].value
            for r in resource_map:
                logical_id = r[0].value
                lines[logical_id] = r[1].start_mark.line
