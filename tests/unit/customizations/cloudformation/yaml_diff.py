#!/usr/bin/env python3
"""
YAML Diff Utility

This module provides functionality to generate traditional diff output
between two YAML strings, focusing on the specific parts that differ.
"""

from awscli.customizations.cloudformation import yamlhelper
from tests.unit.customizations.cloudformation.yaml_compare import load_yaml_string


def _format_yaml_for_diff(yaml_obj, path=None):
    """
    Format a specific part of a YAML object for diff display.
    
    Args:
        yaml_obj: The YAML object to format
        path: Path to the specific part to extract (list of keys/indices)
        
    Returns:
        A string representation of the YAML object or subpart
    """
    if path:
        # Navigate to the specific part of the YAML
        current = yaml_obj
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list) and isinstance(key, int) and key < len(current):
                current = current[key]
            else:
                return f"<Path {'.'.join(str(p) for p in path)} not found>"
        yaml_obj = current
    
    # Format the YAML object
    return yamlhelper.yaml_dump(yaml_obj)


def show_yaml_diff(yaml_str1, yaml_str2, path=None):
    """
    Generate a traditional diff output between two YAML strings.
    
    Args:
        yaml_str1: First YAML string
        yaml_str2: Second YAML string
        path: Optional path to focus the diff on a specific part
        
    Returns:
        A string containing the diff output
    """
    import difflib
    
    yaml1 = load_yaml_string(yaml_str1)
    yaml2 = load_yaml_string(yaml_str2)
    
    # If path is provided, extract just that part
    yaml1_str = _format_yaml_for_diff(yaml1, path)
    yaml2_str = _format_yaml_for_diff(yaml2, path)
    
    # Generate unified diff
    yaml1_lines = yaml1_str.splitlines(True)
    yaml2_lines = yaml2_str.splitlines(True)
    
    diff = difflib.unified_diff(
        yaml1_lines, 
        yaml2_lines,
        fromfile='expected',
        tofile='actual',
        n=3  # Context lines
    )
    
    return ''.join(diff)
