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

from awscli.compat import urlparse
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation import yamlhelper
from awscli.customizations.cloudformation.modules.names import (
    SOURCE,
    PACKAGES,
)

content_cache = {}


def is_url(p):
    "Returns true if the path looks like a URL instead of a local file"
    return p.startswith("https")


def is_s3_url(url):
    """
    Check if the URL provided is an S3 URL.

    :param url: URL to check
    :return: True if the URL is an S3 URL, False otherwise
    """
    try:
        parse_s3_url(url)
        return True
    except ValueError:
        return False


def parse_s3_url(
    url,
    bucket_name_property="Bucket",
    object_key_property="Key",
    version_property=None,
):
    """
    Parse an S3 URL and return a dict with the bucket name and object key

    :param url: S3 URL to parse
    :param bucket_name_property: Name of the prop to use for the bucket name
    :param object_key_property: Name of the prop to use for the object key
    :param version_property: Name of the prop to use for the version
    :return: Dictionary with the bucket name and object key
    """
    if isinstance(url, str) and url.startswith("s3://"):

        # Python < 2.7.10 don't parse query parameters from URI with custom
        # scheme such as s3://blah/blah. As a workaround, remove scheme
        # altogether to trigger the parser "s3://foo/bar?v=1" =>"//foo/bar?v=1"
        parsed = urlparse.urlparse(url[3:])
        query = urlparse.parse_qs(parsed.query)

        if parsed.netloc and parsed.path:
            result = {}
            result[bucket_name_property] = parsed.netloc
            result[object_key_property] = parsed.path.lstrip("/")

            # If there is a query string that has a single versionId field,
            # set the object version and return
            if (
                version_property is not None
                and "versionId" in query
                and len(query["versionId"]) == 1
            ):
                result[version_property] = query["versionId"][0]

            return result

    raise ValueError(
        f"URL given to the parse method is not a valid S3 url {url}"
    )


def _handle_s3_source(source, s3_client, dotzip):
    """
    Handle downloading files from S3.
    Returns the content and a flag indicating if this is part of a zip file.
    """
    content = ""
    is_remote_zip = False
    zipslash = dotzip + "/"
    tokens = None

    if zipslash in source:
        # This is a reference to a remote Package in S3
        tokens = source.split(zipslash)
        source = tokens[0] + dotzip
        is_remote_zip = True

    if s3_client is None:
        raise exceptions.InvalidModulePathError(
            source=source, msg="S3 client is required for S3 URLs"
        )

    try:
        s3_parts = parse_s3_url(source)
        response = s3_client.get_object(
            Bucket=s3_parts["Bucket"], Key=s3_parts["Key"]
        )
        content = response["Body"].read()
    except Exception as e:
        print(e)
        raise exceptions.InvalidModulePathError(source=source)

    if is_remote_zip and tokens:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            content = zf.read(tokens[1])

    return content


def _handle_http_source(source, dotzip):
    """
    Handle downloading files from HTTP URLs.
    Returns the content and a flag indicating if this is part of a zip file.
    """
    content = ""
    is_remote_zip = False
    zipslash = dotzip + "/"
    tokens = None

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

    if is_remote_zip and tokens:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            content = zf.read(tokens[1])

    return content


def _handle_local_source(source, dotzip):
    """
    Handle reading files from the local filesystem.
    Returns the content.
    """
    content = ""
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

    return content


def read_source(source, s3_client=None):
    """
    Read the source file and return the content as a string,
    plus a dictionary with line numbers.
    """
    if not isinstance(source, str):
        raise exceptions.InvalidModulePathError(
            msg=f"The value of {source} is not a valid path to a local file"
        )

    dotzip = ".zip"

    content = None

    if source in content_cache:
        content = content_cache[source]
    elif is_s3_url(source):
        # Handle S3 URLs
        content = _handle_s3_source(source, s3_client, dotzip)
    elif is_url(source):
        # Handle HTTPS URLs
        content = _handle_http_source(source, dotzip)
    else:
        # Handle local files
        content = _handle_local_source(source, dotzip)

    content_cache[source] = content

    node = yamlhelper.yaml_compose(content)
    lines = {}
    read_line_numbers(node, lines)

    return content, lines


def read_line_numbers(node, lines):
    """
    Read line numbers from a yaml node for all top-level sections.
    """
    for n in node.value:
        section_name = n[0].value
        lines[section_name] = n[0].start_mark.line + 1  # 1-based line numbers

        # For Resources section, also track individual resource line numbers
        if section_name == "Resources" and isinstance(n[1].value, list):
            resource_map = n[1].value
            for r in resource_map:
                logical_id = r[0].value
                lines[f"Resources.{logical_id}"] = r[1].start_mark.line + 1

        # For ParameterSchema section, track parameter schema line numbers
        if section_name == "ParameterSchema" and isinstance(n[1].value, list):
            schema_map = n[1].value
            for s in schema_map:
                param_name = s[0].value
                lines[f"ParameterSchema.{param_name}"] = (
                    s[1].start_mark.line + 1
                )

        # For Parameters section, track parameter line numbers
        if section_name == "Parameters" and isinstance(n[1].value, list):
            param_map = n[1].value
            for p in param_map:
                param_name = p[0].value
                lines[f"Parameters.{param_name}"] = p[1].start_mark.line + 1

        # For Modules section, track module properties
        if section_name == "Modules" and isinstance(n[1].value, list):
            modules_map = n[1].value
            _get_module_line_numbers(lines, modules_map)


# pylint: disable=too-many-nested-blocks
def _get_module_line_numbers(lines, modules_map):
    """Get line numbers for the Modules section"""

    for m in modules_map:
        # Skip if this is not a proper module entry (could be a scalar or other type)
        if not isinstance(m, list) or len(m) < 2:
            continue

        module_name = m[0].value
        lines[f"Modules.{module_name}"] = m[1].start_mark.line + 1

        # Track module properties
        if isinstance(m[1].value, list):
            for prop in m[1].value:
                # Skip if this is not a proper property entry
                if not isinstance(prop, list) or len(prop) < 2:
                    continue

                prop_name = prop[0].value
                lines[f"Modules.{module_name}.{prop_name}"] = (
                    prop[1].start_mark.line + 1
                )

                # Track Properties section within each module
                if prop_name == "Properties" and isinstance(
                    prop[1].value, list
                ):
                    for p in prop[1].value:
                        # Skip if this is not a proper property entry
                        if not isinstance(p, list) or len(p) < 2:
                            continue

                        prop_key = p[0].value
                        val = p[1].start_mark.line + 1
                        lines[
                            f"Modules.{module_name}.Properties.{prop_key}"
                        ] = val


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
