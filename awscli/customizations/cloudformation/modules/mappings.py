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
Process the Mappings section in a module

If a Fn::FindInMap in a module cannot be fully resolved to a scalar value, the
mapping is emitted into the parent template with the module name as a prefix to
avoid naming conflicts. If a mapping can be fully resolved, it is replaced with
the resolved value directly.
"""

import logging
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.modules.resolve import resolve
from awscli.customizations.cloudformation.modules.visitor import Visitor
from awscli.customizations.cloudformation.modules.names import (
    RESOURCES,
    MODULES,
    OUTPUTS,
    MAPPINGS,
    FINDINMAP,
)
from awscli.customizations.cloudformation.modules.util import (
    isdict,
)

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


def parse_mappings(m, module_dict):
    """
    Parse mappings and store them in the module.

    :param m: The module
    :param module_dict: The raw module object
    """
    if MAPPINGS not in module_dict:
        m.mappings = {}
        return

    # Store the mappings in the module
    m.mappings = module_dict[MAPPINGS]


def process_mappings(m, module_dict):
    """
    Process mappings in the module.

    :param m: The module
    :param module_dict: The raw module object
    """
    # Parse and store mappings
    parse_mappings(m, module_dict)

    # If no mappings, nothing to do
    if not hasattr(m, "mappings") or not m.mappings:
        return

    # Track which mappings need to be emitted to the parent template
    mappings_to_emit = set()

    # Process all Fn::FindInMap expressions
    process_findmap_expressions(m, module_dict, mappings_to_emit)

    # Emit required mappings to parent template
    emit_mappings_to_parent(m, mappings_to_emit)


def process_findmap_expressions(m, module_dict, mappings_to_emit):
    """
    Process all Fn::FindInMap expressions in the module.

    :param m: The module
    :param module_dict: The raw module object
    :param mappings_to_emit: Set to track mappings that need to be emitted
    """

    def vf(v):
        if not isdict(v.d):
            return

        if FINDINMAP in v.d:

            # Try to resolve any Refs in the node
            resolve(m, v.d)

            if FINDINMAP not in v.d:
                # If the node is resolved, it's no longer a FindInMap
                return

            findmap_args = v.d[FINDINMAP]

            # Validate FindInMap structure
            if not isinstance(findmap_args, list) or len(findmap_args) != 3:
                msg = f"Invalid FindInMap structure: {findmap_args}"
                raise exceptions.InvalidModuleError(msg=msg)

            name, key, attr = findmap_args

            # Check if mapping exists
            if not isinstance(name, str) or name not in m.mappings:
                if name.startswith(m.name):
                    unprefixed = name.replace(m.name, "", 1)
                    if unprefixed in m.mappings:
                        # Special case for when we re-process
                        return
                msg = f"Mapping not found: {name}"
                raise exceptions.InvalidModuleError(msg=msg)

            # Check if key is a literal value (not a Ref or other intrinsic)
            if isdict(key) or isdict(attr):
                mappings_to_emit.add(name)
                findmap_args[0] = m.name + name
                return

            if key in m.mappings[name]:
                if attr in m.mappings[name][key]:
                    # Replace the FindInMap with the resolved value
                    v.p[v.k] = m.mappings[name][key][attr]
                    return

    # Process Fn::FindInMap in Resources, Modules, and Outputs
    sections = []
    if RESOURCES in module_dict:
        sections.append(module_dict[RESOURCES])
    if MODULES in module_dict:
        sections.append(module_dict[MODULES])
    if OUTPUTS in module_dict:
        sections.append(module_dict[OUTPUTS])

    for section in sections:
        Visitor(section).visit(vf)


def emit_mappings_to_parent(m, mappings_to_emit):
    """
    Emit required mappings to the parent template with prefixed names.

    :param m: The module
    :param mappings_to_emit: Set of mapping names that need to be emitted
    """
    if not mappings_to_emit:
        return

    if MAPPINGS not in m.template:
        m.template[MAPPINGS] = {}

    # Add required mappings to parent with prefixed names
    for mapping_name in mappings_to_emit:
        prefixed_name = m.name + mapping_name

        # Check for name conflicts
        if prefixed_name in m.template[MAPPINGS]:
            # If they are exactly the same, we don't need to add it again
            # Otherwise it's a name conflict
            if m.template[MAPPINGS][prefixed_name] != m.mappings[mapping_name]:
                msg = f"Mapping name conflict: {prefixed_name}"
                raise exceptions.InvalidModuleError(msg=msg)
        else:
            # Add the mapping to the parent template with the prefixed name
            m.template[MAPPINGS][prefixed_name] = m.mappings[mapping_name]
