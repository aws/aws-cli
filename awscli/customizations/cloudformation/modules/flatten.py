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

# pylint: disable=too-many-branches,too-many-locals

"""
Implementation of the enhanced Fn::Flatten function for CloudFormation modules.
"""

import logging

from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.modules.visitor import Visitor
from awscli.customizations.cloudformation.modules.merge import isdict

LOG = logging.getLogger(__name__)

# Define the intrinsic function name
FLATTEN = "Fn::Flatten"


def _normalize_pattern(pattern):
    """
    Normalize a JSONPath-like pattern by removing leading $ and dot if present.

    Args:
        pattern: The pattern to normalize

    Returns:
        Normalized pattern
    """
    if not pattern or pattern == "$":
        return ""

    # Remove leading $ if present
    if pattern.startswith("$"):
        pattern = pattern[1:]
        if pattern.startswith("."):
            pattern = pattern[1:]

    return pattern


def _split_pattern_into_segments(pattern):
    """
    Split a JSONPath-like pattern into segments.

    Args:
        pattern: A JSONPath-like pattern string

    Returns:
        List of pattern segments
    """
    segments = []
    current_segment = ""
    in_brackets = False

    for char in pattern:
        if char == "[" and not in_brackets:
            if current_segment:
                segments.append(current_segment)
                current_segment = ""
            in_brackets = True
            current_segment += char
        elif char == "]" and in_brackets:
            current_segment += char
            in_brackets = False
            segments.append(current_segment)
            current_segment = ""
        elif char == "." and not in_brackets:
            if current_segment:
                segments.append(current_segment)
                current_segment = ""
        else:
            current_segment += char

    if current_segment:
        segments.append(current_segment)

    return segments


def _process_segment(value, segment, next_values):
    """
    Process a single segment against a value and add results to next_values.

    Args:
        value: The current value being processed
        segment: The segment to apply
        next_values: List to collect results

    Returns:
        True if the segment was processed, False otherwise
    """
    # Handle wildcard for dictionaries
    if segment == "*" and isinstance(value, dict):
        next_values.extend(list(value.values()))
        return True

    # Handle wildcard for lists
    if segment == "[*]" and isinstance(value, list):
        next_values.extend(value)
        return True

    # Handle specific list index
    if (
        segment.startswith("[")
        and segment.endswith("]")
        and segment[1:-1].isdigit()
    ):
        index = int(segment[1:-1])
        if isinstance(value, list) and 0 <= index < len(value):
            next_values.append(value[index])
            return True

    # Handle dictionary key access
    if isinstance(value, dict) and segment in value:
        next_values.append(value[segment])
        return True

    # Handle array property access with wildcard
    if segment.endswith("[*]"):
        prop = segment[:-3]
        if (
            isinstance(value, dict)
            and prop in value
            and isinstance(value[prop], list)
        ):
            next_values.extend(value[prop])
            return True

    return False


def _extract_by_pattern(source, pattern):
    """
    Extract values from a nested structure using a JSONPath-like pattern.

    Args:
        source: The source data structure (dict, list, or scalar)
        pattern: A JSONPath-like pattern string (e.g., "$.*.items[*]")

    Returns:
        A list of extracted values
    """
    # Handle empty or root pattern
    if not pattern or pattern == "$":
        return [source]

    # Normalize the pattern
    pattern = _normalize_pattern(pattern)
    if not pattern:
        return [source]

    # Split the pattern into segments
    segments = _split_pattern_into_segments(pattern)

    # Process segments recursively
    current_values = [source]

    for segment in segments:
        next_values = []

        for value in current_values:
            _process_segment(value, segment, next_values)

        current_values = next_values

        # If we have no values at this point, we can stop processing
        if not current_values:
            break

    return current_values


def _process_item_for_transform(item):
    """
    Process an item to extract nested structures if needed.

    Args:
        item: The item to process

    Returns:
        List of items to process
    """
    result = [item]  # Always include the original item

    if not isdict(item):
        return result

    # If the item is a dictionary with a single key and that value is a
    # list or dict, we might need to process its contents
    if len(item) == 1:
        key = next(iter(item.keys()))
        value = item[key]

        # For dictionaries with nested structure, consider its nested content
        if isinstance(value, list):
            # Add list items individually
            result.extend(value)
        elif isdict(value):
            # For nested dictionaries, include any list properties
            for _, prop_value in value.items():
                if isinstance(prop_value, list):
                    result.extend(prop_value)

    return result


def _extract_variable_values(actual_item, variables):
    """
    Extract variable values from an item based on variable patterns.

    Args:
        actual_item: The item to extract values from
        variables: Dictionary of variable names to patterns

    Returns:
        Dictionary of variable names to extracted values

    Raises:
        InvalidModuleError: If a variable pattern is invalid
    """
    var_values = {}
    for var_name, var_pattern in variables.items():
        if not isinstance(var_pattern, str):
            err_msg = (
                f"Fn::Flatten Transform variable pattern for "
                f"'{var_name}' must be a string"
            )
            raise exceptions.InvalidModuleError(msg=err_msg)

        # Handle special case for direct property access with [*]
        if var_pattern.startswith("$item.") and var_pattern.endswith("[*]"):
            prop_name = var_pattern[
                6:-3
            ]  # Extract property name between $item. and [*]
            if prop_name in actual_item and isinstance(
                actual_item[prop_name], list
            ):
                var_values[var_name] = actual_item[prop_name]
                continue

        # Regular extraction
        var_values[var_name] = _extract_by_pattern(actual_item, var_pattern)

    return var_values


def _apply_transform(items, transform):
    """
    Apply transformation to each item in the list.

    Args:
        items: List of items to transform
        transform: Transform configuration with template and variables

    Returns:
        List of transformed items

    Raises:
        InvalidModuleError: If the transform configuration is invalid
    """
    if not transform or "Template" not in transform:
        err_msg = "Fn::Flatten Transform requires a Template parameter"
        raise exceptions.InvalidModuleError(msg=err_msg)

    template = transform.get("Template")
    variables = transform.get("Variables", {})

    if variables and not isdict(variables):
        err_msg = "Fn::Flatten Transform Variables must be an object"
        raise exceptions.InvalidModuleError(msg=err_msg)

    result = []

    # Process each item and extract nested structures if needed
    processed_items = []
    for item in items:
        processed_items.extend(_process_item_for_transform(item))

    # Process each item with the transform
    for item in processed_items:
        # Determine the actual item to use for variable extraction
        if (
            isdict(item)
            and len(item) == 1
            and isinstance(next(iter(item.values())), dict)
        ):
            actual_item = next(iter(item.values()))
        else:
            actual_item = item

        # If no variables, just apply the template directly
        if not variables:
            transformed = _apply_template(
                actual_item, template, {"item": actual_item}
            )
            result.append(transformed)
            continue

        # Extract variable values
        var_values = _extract_variable_values(actual_item, variables)

        # Generate cross product of all variable combinations
        combinations = _generate_combinations(var_values)

        # Apply template for each combination
        for combo in combinations:
            context = {"item": actual_item}
            context.update(combo)
            transformed = _apply_template(actual_item, template, context)
            result.append(transformed)

    return result


def _generate_combinations(var_values):
    """
    Generate all combinations of variable values.

    Args:
        var_values: Dictionary mapping var names to lists of possible values

    Returns:
        List of dictionaries, each representing one combination of var values
    """
    if not var_values:
        return [{}]

    # Start with first variable
    var_name, values = next(iter(var_values.items()))
    remaining_vars = {k: v for k, v in var_values.items() if k != var_name}

    # Get combinations for remaining variables
    sub_combinations = _generate_combinations(remaining_vars)

    # Combine with values of the current variable
    result = []
    for value in values:
        for sub_combo in sub_combinations:
            combo = {var_name: value}
            combo.update(sub_combo)
            result.append(combo)

    return result


def _process_variable_reference(template_str, context):
    """
    Process variable references in a string template.

    Args:
        template_str: The string template with variable references
        context: Dictionary of variables available for substitution

    Returns:
        The processed string with variables replaced
    """
    result = template_str
    i = 0

    while i < len(result):
        if result[i] == "$" and i + 1 < len(result) and result[i + 1] != "$":
            # Found a variable reference
            var_start = i

            # Check if it's a simple reference or a path expression
            if i + 1 < len(result) and result[i + 1] == "{":
                # Path expression with braces ${var.path}
                i += 2  # Skip past ${
                var_end = result.find("}", i)
                if var_end == -1:
                    # No closing brace, treat as literal
                    i += 1
                    continue
                var_path = result[i:var_end].strip()
                i = var_end + 1
                full_var = result[var_start:i]
            else:
                # Simple reference $var or path expression $var.path
                i += 1  # Skip past $
                var_end = i
                while var_end < len(result) and (
                    result[var_end].isalnum()
                    or result[var_end] == "_"
                    or result[var_end] == "."
                ):
                    var_end += 1
                var_path = result[i:var_end].strip()
                full_var = result[var_start:var_end]
                i = var_end

            # Resolve the variable
            replacement = _resolve_variable_path(var_path, context)

            # Replace the variable reference with its value
            if replacement is not None:
                if not isinstance(replacement, str):
                    replacement = str(replacement)
                result = result.replace(full_var, replacement)
                # Reset i to continue from the start of the replacement
                i = var_start + len(replacement)
            else:
                # Variable not found, continue
                i = var_start + 1
        else:
            i += 1

    return result


def _resolve_variable_path(var_path, context):
    """
    Resolve a variable path expression against a context.

    Args:
        var_path: The variable path (e.g., "item.name")
        context: Dictionary of variables

    Returns:
        The resolved value or None if not found
    """
    if "." in var_path:
        # Handle path expressions like item.name
        parts = var_path.split(".")
        if parts[0] in context:
            current = context[parts[0]]
            valid_path = True
            for part in parts[1:]:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    valid_path = False
                    break
            if valid_path:
                return current
    else:
        # Simple variable reference
        if var_path in context:
            return context[var_path]

    return None


def _convert_string_to_number(value_str):
    """
    Convert a string to a number if possible.

    Args:
        value_str: The string to convert

    Returns:
        The converted number or the original string
    """
    if value_str.isdigit():
        return int(value_str)
    try:
        return float(value_str)
    except ValueError:
        return value_str


def _apply_template(item, template, context):
    """
    Apply a template to an item using the provided context.

    Args:
        item: The source item
        template: The template to apply (can be dict, list, or scalar)
        context: Dictionary of variables available for substitution

    Returns:
        The transformed item
    """
    if isinstance(template, dict):
        result = {}
        for key, value in template.items():
            result[key] = _apply_template(item, value, context)
        return result

    if isinstance(template, list):
        return [_apply_template(item, value, context) for value in template]

    if isinstance(template, str) and "$" in template:
        # Process string with variable references
        result = _process_variable_reference(template, context)

        # Convert to number if appropriate
        return _convert_string_to_number(result)

    # Return as is for non-template values
    return template


def _group_by_attribute(items, attribute):
    """
    Group items by a specific attribute.

    Args:
        items: List of items to group
        attribute: The attribute to group by

    Returns:
        Dictionary mapping attribute values to lists of items
    """
    result = {}
    for item in items:
        if not isinstance(item, dict) or attribute not in item:
            continue

        key = str(item[attribute])
        if key not in result:
            result[key] = []
        result[key].append(item)

    return result


def _extract_items_from_source(source):
    """
    Extract items from a non-list source without a pattern.

    Args:
        source: The source to extract items from

    Returns:
        List of extracted items
    """
    if not isdict(source):
        return [source]

    # Convert the dict to a list of dicts
    result = []
    for key, value in source.items():
        if isinstance(value, list):
            for item in value:
                result.append({key: item})
        else:
            result.append({key: value})

    return result


def _process_flatten(flatten_config):
    """
    Process a single Fn::Flatten configuration.

    Args:
        flatten_config: The Fn::Flatten configuration object or simple source

    Returns:
        The flattened result

    Raises:
        InvalidModuleError: If the configuration is invalid
    """

    # Handle simple source case (just a list or scalar)
    if not isdict(flatten_config):
        if isinstance(flatten_config, list):
            return flatten_config
        return [flatten_config]

    # Extract parameters from the configuration
    if "Source" not in flatten_config:
        err_msg = "Fn::Flatten requires a Source parameter"
        raise exceptions.InvalidModuleError(msg=err_msg)

    source = flatten_config.get("Source")
    pattern = flatten_config.get("Pattern")
    transform = flatten_config.get("Transform")
    group_by = flatten_config.get("GroupBy")

    # Handle empty or invalid source
    if source is None:
        msg = "Fn::Flatten Source must be specified"
        raise exceptions.InvalidModuleError(msg=msg)

    # Extract values using pattern if provided
    items = []
    if pattern:
        if not isinstance(pattern, str):
            err_msg = "Fn::Flatten Pattern must be a string"
            raise exceptions.InvalidModuleError(msg=err_msg)
        items = _extract_by_pattern(source, pattern)
    elif isinstance(source, list):
        items = source
    else:
        # For non-list sources without a pattern, extract items
        items = _extract_items_from_source(source)

    # Apply transformation if provided
    if transform:
        if not isdict(transform):
            err_msg = "Fn::Flatten Transform must be an object"
            raise exceptions.InvalidModuleError(msg=err_msg)
        if "Template" not in transform:
            err_msg = "Fn::Flatten Transform requires a Template parameter"
            raise exceptions.InvalidModuleError(msg=err_msg)
        items = _apply_transform(items, transform)

    # Group by attribute if provided
    if group_by:
        if not isinstance(group_by, str):
            err_msg = "Fn::Flatten GroupBy must be a string"
            raise exceptions.InvalidModuleError(msg=err_msg)
        return _group_by_attribute(items, group_by)

    return items


def fn_flatten(d):
    """
    Find all instances of Fn::Flatten in the dictionary and process them.

    This function uses the visitor pattern to recursively find and process
    all Fn::Flatten intrinsic functions in the template.

    Args:
        d: The template dictionary to process

    Raises:
        InvalidModuleError: If there's an error processing Fn::Flatten
    """

    def vf(v):
        # Skip if not a dictionary or doesn't contain Fn::Flatten
        if not isdict(v.d) or FLATTEN not in v.d or v.p is None:
            return

        try:
            # Process the Fn::Flatten configuration
            flatten_config = v.d[FLATTEN]
            result = _process_flatten(flatten_config)

            # Replace the Fn::Flatten with its result
            v.p[v.k] = result
        except Exception as e:
            error_msg = f"Error processing Fn::Flatten: {str(e)}"
            LOG.error(error_msg)
            raise exceptions.InvalidModuleError(msg=error_msg)

    # Visit all nodes in the template
    Visitor(d).visit(vf)
