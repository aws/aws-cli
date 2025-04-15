#!/usr/bin/env python3
"""
YAML Comparison Utility

This module provides functionality to compare two YAML strings for equivalent
content, ignoring sort order of keys and handling CloudFormation intrinsics.
"""

from awscli.customizations.cloudformation import yamlhelper


class YAMLParseError(Exception):
    """Exception raised for errors when parsing YAML content."""


def load_yaml_string(yaml_str):
    """
    Load YAML content from a string using CloudFormation's YAML helper.

    Args:
        yaml_str: String containing YAML content

    Returns:
        The parsed YAML content with proper handling of CloudFormation
        intrinsics

    Raises:
        YAMLParseError: If the string cannot be parsed as YAML
    """
    try:
        return yamlhelper.yaml_parse(yaml_str)
    except Exception as e:
        raise YAMLParseError(f"Error parsing YAML string: {str(e)}") from e


def are_yaml_equivalent(yaml1, yaml2):
    """
    Compare two YAML objects for equivalence, ignoring sort order of keys.

    Args:
        yaml1: First YAML object
        yaml2: Second YAML object

    Returns:
        True if the YAML objects are equivalent, False otherwise
    """
    # Handle different types, but treat dict and OrderedDict as equivalent
    if not isinstance(yaml1, type(yaml2)):
        # Special case: dict and OrderedDict should be considered equivalent
        if not (isinstance(yaml1, dict) and isinstance(yaml2, dict)):
            return False

    # Handle dictionaries (recursively compare values, ignoring key order)
    if isinstance(yaml1, dict):
        if set(yaml1.keys()) != set(yaml2.keys()):
            return False

        return all(
            are_yaml_equivalent(yaml1[key], yaml2[key]) for key in yaml1
        )

    # Handle lists
    if isinstance(yaml1, list):
        if len(yaml1) != len(yaml2):
            return False

        return _compare_lists(yaml1, yaml2)

    # Handle scalar values
    return yaml1 == yaml2


def _compare_lists(list1, list2):
    """
    Compare two lists for equivalence, handling different comparison
    strategies.

    Args:
        list1: First list
        list2: Second list

    Returns:
        True if the lists are equivalent, False otherwise
    """
    # Try to convert to sets if elements are hashable
    try:
        return set(list1) == set(list2)
    except TypeError:
        pass

    # Elements are not hashable, try sorting if comparable
    try:
        sorted1 = sorted(list1)
        sorted2 = sorted(list2)
        return all(
            are_yaml_equivalent(s1, s2) for s1, s2 in zip(sorted1, sorted2)
        )
    except TypeError:
        pass

    # Elements are not comparable, compare each element
    return all(
        any(are_yaml_equivalent(item1, item2) for item2 in list2)
        for item1 in list1
    )


def compare_yaml_strings(yaml_str1, yaml_str2):
    """
    Compare two YAML strings for equivalent content, ignoring sort order of
    keys and properly handling CloudFormation intrinsic functions.

    Args:
        yaml_str1: First YAML string
        yaml_str2: Second YAML string

    Returns:
        True if the strings contain equivalent YAML content, False otherwise
    """
    yaml1 = load_yaml_string(yaml_str1)
    yaml2 = load_yaml_string(yaml_str2)

    return are_yaml_equivalent(yaml1, yaml2)


def find_yaml_differences(yaml_str1, yaml_str2):
    """
    Compare two YAML strings and return a list of differences.

    Args:
        yaml_str1: First YAML string
        yaml_str2: Second YAML string

    Returns:
        A list of differences between the two YAML strings
    """
    yaml1 = load_yaml_string(yaml_str1)
    yaml2 = load_yaml_string(yaml_str2)

    differences = []
    _find_differences(yaml1, yaml2, [], differences)

    return differences


def _find_differences(yaml1, yaml2, path, differences):
    """
    Recursively find differences between two YAML objects.

    Args:
        yaml1: First YAML object
        yaml2: Second YAML object
        path: Current path in the YAML structure
        differences: List to collect differences
    """
    current_path = ".".join(str(p) for p in path) if path else "root"

    # Handle different types
    if not _are_compatible_types(yaml1, yaml2):
        differences.append(
            f"Type mismatch at {current_path}: "
            f"{type(yaml1).__name__} vs {type(yaml2).__name__}"
        )
        return

    # Handle dictionaries
    if isinstance(yaml1, dict):
        _compare_dicts(yaml1, yaml2, path, current_path, differences)
        return

    # Handle lists
    if isinstance(yaml1, list):
        _compare_lists_with_differences(
            yaml1, yaml2, path, current_path, differences
        )
        return

    # Handle scalar values
    if yaml1 != yaml2:
        differences.append(
            f"Value mismatch at {current_path}: '{yaml1}' vs '{yaml2}'"
        )


def _are_compatible_types(obj1, obj2):
    """
    Check if two objects have compatible types for comparison.

    Args:
        obj1: First object
        obj2: Second object

    Returns:
        True if types are compatible, False otherwise
    """
    if isinstance(obj1, type(obj2)):
        return True

    # Special case for dict types
    if isinstance(obj1, dict) and isinstance(obj2, dict):
        return True

    return False


def _compare_dicts(dict1, dict2, path, current_path, differences):
    """
    Compare two dictionaries and record differences.

    Args:
        dict1: First dictionary
        dict2: Second dictionary
        path: Current path in the YAML structure
        current_path: String representation of the current path
        differences: List to collect differences
    """
    # Check for missing keys
    keys1 = set(dict1.keys())
    keys2 = set(dict2.keys())

    for key in keys1 - keys2:
        differences.append(
            f"Key '{key}' at {current_path} exists in first YAML "
            f"but not in second"
        )

    for key in keys2 - keys1:
        differences.append(
            f"Key '{key}' at {current_path} exists in second YAML "
            f"but not in first"
        )

    # Check common keys
    for key in keys1 & keys2:
        new_path = path + [key]
        _find_differences(dict1[key], dict2[key], new_path, differences)


def _compare_lists_with_differences(
    list1, list2, path, current_path, differences
):
    """
    Compare two lists and record differences.

    Args:
        list1: First list
        list2: Second list
        path: Current path in the YAML structure
        current_path: String representation of the current path
        differences: List to collect differences
    """
    if len(list1) != len(list2):
        differences.append(
            f"List length mismatch at {current_path}: "
            f"{len(list1)} vs {len(list2)}"
        )
        return

    # Try to match items and find differences
    _find_list_item_differences(list1, list2, path, differences)


def _find_list_item_differences(list1, list2, path, differences):
    """
    Find differences between items in two lists.

    Args:
        list1: First list
        list2: Second list
        path: Current path in the YAML structure
        differences: List to collect differences
    """
    unmatched1 = list(list1)
    unmatched2 = list(list2)

    # First try to match items exactly
    for i, item1 in enumerate(list1):
        for j, item2 in enumerate(list2):
            if j < len(unmatched2) and i < len(unmatched1):
                if are_yaml_equivalent(item1, item2):
                    unmatched1[i] = None
                    unmatched2[j] = None
                    break

    # Process remaining unmatched items
    _process_unmatched_items(
        list1, list2, unmatched1, unmatched2, path, differences
    )


# pylint: disable=too-many-arguments, too-many-positional-arguments
def _process_unmatched_items(
    list1, list2, unmatched1, unmatched2, path, differences
):
    """
    Process unmatched items between two lists.

    Args:
        list1: First list
        list2: Second list
        unmatched1: List of unmatched items from first list
        unmatched2: List of unmatched items from second list
        path: Current path in the YAML structure
        differences: List to collect differences
    """
    for i, item1 in enumerate(list1):
        if i < len(unmatched1) and unmatched1[i] is not None:
            # Find best match to show differences
            best_match_idx = _find_best_match_index(unmatched2)

            if best_match_idx >= 0:
                new_path = path + [f"[{i}]"]
                _find_differences(
                    item1, list2[best_match_idx], new_path, differences
                )
                unmatched1[i] = None
                unmatched2[best_match_idx] = None


def _find_best_match_index(items):
    """
    Find the index of the first non-None item in a list.

    Args:
        items: List to search

    Returns:
        Index of first non-None item, or -1 if none found
    """
    for j, item in enumerate(items):
        if item is not None:
            return j
    return -1
