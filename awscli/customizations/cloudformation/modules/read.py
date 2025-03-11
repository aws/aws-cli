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

import io
import os
import urllib
import zipfile

from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation import yamlhelper
from awscli.customizations.cloudformation.modules.names import (
    SOURCE,
    PACKAGES,
)


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

    content = ""
    dotzip = ".zip"
    is_remote_zip = False
    if is_url(source):
        zipslash = dotzip + "/"
        if zipslash in source:
            # This is a reference to a remote Package
            tokens = source.split(zipslash)
            source = tokens[0] + dotzip
            is_remote_zip = True
        try:
            with urllib.request.urlopen(source) as response:
                content = response.read()
        except Exception as e:
            print(e)
            raise exceptions.InvalidModulePathError(source=source)
        if is_remote_zip:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                content = zf.read(tokens[1])
    else:
        zipslash = dotzip + os.path.sep
        if zipslash in source:
            # This is a reference to a local Package
            tokens = source.split(zipslash)
            zip_path = tokens[0] + dotzip
            with zipfile.ZipFile(zip_path) as zf:
                content = zf.read(tokens[1])
        else:
            if not os.path.isfile(source):
                raise exceptions.InvalidModulePathError(source=source)

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


def get_packaged_module_path(template, p):
    """
    Get the path of the module including the package name

    The read_source function knows how to interpret the
    combined path that is returned.

    For example:

    p = $abc/module.yaml

    Assuming the template has:

    Packages:
      abc: package.zip

    Returns: package.zip/module.yaml

    Raises an error if the Package can't be found in the template.
    """
    if PACKAGES not in template:
        msg = f"Packages section not found for {p}"
        raise exceptions.InvalidModuleError(msg=msg)
    slash = "/"
    tokens = p.split(slash)
    if len(tokens) < 2:
        msg = f"Invalid Package/module name: {p}"
        raise exceptions.InvalidModuleError(msg=msg)
    package_name = tokens[0].replace("$", "")
    if package_name not in template[PACKAGES]:
        msg = f"Package name {package_name} not found: {p}"
        raise exceptions.InvalidModuleError(msg=msg)
    pkg = template[PACKAGES][package_name]
    if SOURCE not in pkg:
        msg = f"Package {pkg} doesn't have {SOURCE}: {p}"
        raise exceptions.InvalidModuleError(msg=msg)
    return pkg[SOURCE] + slash + os.path.sep.join(tokens[1:])
