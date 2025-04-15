#!/usr/bin/env python3
"""
YAML Comparison Utility

This module provides functionality to compare two YAML strings for equivalent content,
ignoring the sort order of keys and properly handling CloudFormation intrinsic functions.
"""

from awscli.customizations.cloudformation import yamlhelper


def load_yaml_string(yaml_str):
    """
    Load YAML content from a string using CloudFormation's YAML helper.
    
    Args:
        yaml_str: String containing YAML content
        
    Returns:
        The parsed YAML content with proper handling of CloudFormation intrinsics
        
    Raises:
        Exception: If the string cannot be parsed as YAML
    """
    try:
        return yamlhelper.yaml_parse(yaml_str)
    except Exception as e:
        raise Exception(f"Error parsing YAML string: {str(e)}")


def are_yaml_equivalent(yaml1, yaml2):
    """
    Compare two YAML objects for equivalence, ignoring sort order of keys.
    
    Args:
        yaml1: First YAML object
        yaml2: Second YAML object
        
    Returns:
        True if the YAML objects are equivalent, False otherwise
    """
    # Handle different types
    if type(yaml1) != type(yaml2):
        return False
    
    # Handle dictionaries (recursively compare values, ignoring key order)
    if isinstance(yaml1, dict):
        if set(yaml1.keys()) != set(yaml2.keys()):
            return False
        
        return all(are_yaml_equivalent(yaml1[key], yaml2[key]) for key in yaml1)
    
    # Handle lists (compare as sets if elements are hashable, otherwise sort and compare)
    elif isinstance(yaml1, list):
        if len(yaml1) != len(yaml2):
            return False
        
        # Try to convert to sets if elements are hashable
        try:
            return set(yaml1) == set(yaml2)
        except TypeError:
            # Elements are not hashable, try sorting if comparable
            try:
                sorted1 = sorted(yaml1)
                sorted2 = sorted(yaml2)
                return all(are_yaml_equivalent(s1, s2) for s1, s2 in zip(sorted1, sorted2))
            except TypeError:
                # Elements are not comparable, compare each element
                # This is a simplification and might not work for all cases
                return all(any(are_yaml_equivalent(item1, item2) for item2 in yaml2) 
                          for item1 in yaml1)
    
    # Handle scalar values
    else:
        return yaml1 == yaml2


def compare_yaml_strings(yaml_str1, yaml_str2):
    """
    Compare two YAML strings for equivalent content, ignoring sort order of keys
    and properly handling CloudFormation intrinsic functions.
    
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
    current_path = '.'.join(str(p) for p in path) if path else 'root'
    
    # Handle different types
    if type(yaml1) != type(yaml2):
        differences.append(f"Type mismatch at {current_path}: {type(yaml1).__name__} vs {type(yaml2).__name__}")
        return
    
    # Handle dictionaries
    if isinstance(yaml1, dict):
        # Check for missing keys
        keys1 = set(yaml1.keys())
        keys2 = set(yaml2.keys())
        
        for key in keys1 - keys2:
            differences.append(f"Key '{key}' at {current_path} exists in first YAML but not in second")
        
        for key in keys2 - keys1:
            differences.append(f"Key '{key}' at {current_path} exists in second YAML but not in first")
        
        # Check common keys
        for key in keys1 & keys2:
            new_path = path + [key]
            _find_differences(yaml1[key], yaml2[key], new_path, differences)
    
    # Handle lists
    elif isinstance(yaml1, list):
        if len(yaml1) != len(yaml2):
            differences.append(f"List length mismatch at {current_path}: {len(yaml1)} vs {len(yaml2)}")
            return
        
        # Try to match items and find differences
        # This is a simplified approach and might not catch all differences optimally
        unmatched1 = list(yaml1)
        unmatched2 = list(yaml2)
        
        # First try to match items exactly
        for i, item1 in enumerate(yaml1):
            for j, item2 in enumerate(yaml2):
                if j < len(unmatched2) and i < len(unmatched1):
                    if are_yaml_equivalent(item1, item2):
                        unmatched1[i] = None
                        unmatched2[j] = None
                        break
        
        # Process remaining unmatched items
        for i, item1 in enumerate(yaml1):
            if i < len(unmatched1) and unmatched1[i] is not None:
                # Find best match to show differences
                best_match_idx = -1
                for j, item2 in enumerate(yaml2):
                    if j < len(unmatched2) and unmatched2[j] is not None:
                        best_match_idx = j
                        break
                
                if best_match_idx >= 0:
                    new_path = path + [f"[{i}]"]
                    _find_differences(item1, yaml2[best_match_idx], new_path, differences)
                    unmatched1[i] = None
                    unmatched2[best_match_idx] = None
    
    # Handle scalar values
    elif yaml1 != yaml2:
        differences.append(f"Value mismatch at {current_path}: '{yaml1}' vs '{yaml2}'")
