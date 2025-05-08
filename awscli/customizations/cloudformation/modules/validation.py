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
Parameter schema validation for CloudFormation modules.
"""

import re
import logging
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.modules.util import isdict
from awscli.customizations.cloudformation.modules.names import (
    REF
)



LOG = logging.getLogger(__name__)

# Schema section name
PARAMETER_SCHEMA = "ParameterSchema"

# Schema keywords
TYPE = "Type"
REQUIRED = "Required"
PROPERTIES = "Properties"
ITEMS = "Items"
DEFAULT = "Default"
ENUM = "Enum"
MIN_LENGTH = "MinLength"
MAX_LENGTH = "MaxLength"
PATTERN = "Pattern"
MIN_ITEMS = "MinItems"
MAX_ITEMS = "MaxItems"
MINIMUM = "Minimum"
MAXIMUM = "Maximum"
EXCLUSIVE_MINIMUM = "ExclusiveMinimum"
EXCLUSIVE_MAXIMUM = "ExclusiveMaximum"

# Schema types
STRING = "String"
NUMBER = "Number"
BOOLEAN = "Boolean"
OBJECT = "Object"
ARRAY = "Array"
NULL = "Null"

class ParameterValidationError(exceptions.CloudFormationCommandError):
    """Exception raised when parameter validation fails."""
    def __init__(self, module_name, param_name, expected, received):
        self.module_name = module_name
        self.param_name = param_name
        self.expected = expected
        self.received = received
        message = (
            f"Parameter validation failed for module '{module_name}': "
            f"Parameter '{param_name}' expected {expected}, received {received}"
        )
        super().__init__(message=message)


def validate_parameters(module_name, module_template, properties):
    """
    Validate module parameters against their schema definitions.
    
    Args:
        module_name: Name of the module being validated
        module_template: The module template containing schema definitions
        properties: The properties provided to the module
        
    Raises:
        ParameterValidationError: If validation fails
    """
    if PARAMETER_SCHEMA not in module_template:
        # No schema defined, skip validation
        return
    
    schema = module_template[PARAMETER_SCHEMA]
    
    # If no properties provided but schema exists, use empty dict
    if properties is None:
        properties = {}
    
    for param_name, param_schema in schema.items():
        # Skip validation if parameter not provided and no default
        if param_name not in properties and DEFAULT not in param_schema:
            # Check if this parameter is required by any schema
            for schema_name, schema_def in schema.items():
                if (TYPE in schema_def and 
                    schema_def[TYPE] == OBJECT and 
                    REQUIRED in schema_def and 
                    param_name in schema_def[REQUIRED]):
                    raise ParameterValidationError(
                        module_name,
                        param_name,
                        f"Required parameter",
                        "Not provided"
                    )
            continue
            
        # Get parameter value or default
        param_value = properties.get(param_name)
        
        # Validate the parameter
        validate_parameter(module_name, param_name, param_schema, param_value)


def validate_parameter(module_name, param_path, schema, value):
    """
    Validate a single parameter against its schema.
    
    Args:
        module_name: Name of the module being validated
        param_path: Path to the parameter (for nested validation)
        schema: Schema definition for the parameter
        value: Value to validate
        
    Raises:
        ParameterValidationError: If validation fails
    """
    # Apply default if value is None and default exists
    if value is None and DEFAULT in schema:
        value = schema[DEFAULT]
    
    # Handle CloudFormation/YAML boolean values for BOOLEAN type
    if schema.get(TYPE) == BOOLEAN and isinstance(value, str):
        lower_value = value.lower()
        if lower_value in ("true", "yes", "on"):
            value = True
        elif lower_value in ("false", "no", "off"):
            value = False
    
    # Check type
    if TYPE in schema:
        expected_type = schema[TYPE]
        validate_type(module_name, param_path, expected_type, schema, value)
    
    # Additional validations based on type
    if schema.get(TYPE) == STRING:
        validate_string(module_name, param_path, schema, value)
    elif schema.get(TYPE) == NUMBER:
        validate_number(module_name, param_path, schema, value)
    elif schema.get(TYPE) == ARRAY:
        validate_array(module_name, param_path, schema, value)
    elif schema.get(TYPE) == OBJECT:
        validate_object(module_name, param_path, schema, value)
    
    # Check enum for any type
    if ENUM in schema and value is not None and value not in schema[ENUM]:
        raise ParameterValidationError(
            module_name,
            param_path,
            f"One of {schema[ENUM]}",
            value
        )


def validate_type(module_name, param_path, expected_type, schema, value):
    """Validate that the value matches the expected type."""
    if value is None:
        return

    # Ignore unresolved intrinsic functions
    if isdict(value):
        if REF in value:
            return
        for key in value:
            if key.startswith("Fn::"):
                return
    
    if expected_type == STRING:
        if not isinstance(value, str):
            raise ParameterValidationError(
                module_name,
                param_path,
                "String",
                f"{type(value).__name__}: {value}"
            )
    elif expected_type == NUMBER:
        if not isinstance(value, (int, float)):
            raise ParameterValidationError(
                module_name,
                param_path,
                "Number",
                f"{type(value).__name__}: {value}"
            )
    elif expected_type == BOOLEAN:
        if not isinstance(value, bool):
            raise ParameterValidationError(
                module_name,
                param_path,
                "Boolean",
                f"{type(value).__name__}: {value}"
            )
    elif expected_type == ARRAY:
        if not isinstance(value, list):
            raise ParameterValidationError(
                module_name,
                param_path,
                "Array",
                f"{type(value).__name__}: {value}"
            )
    elif expected_type == OBJECT:
        if not isinstance(value, dict):
            raise ParameterValidationError(
                module_name,
                param_path,
                "Object",
                f"{type(value).__name__}: {value}"
            )
    elif expected_type == NULL:
        if value is not None:
            raise ParameterValidationError(
                module_name,
                param_path,
                "Null",
                f"{type(value).__name__}: {value}"
            )


def validate_string(module_name, param_path, schema, value):
    """Validate string constraints."""
    if value is None:
        return
    
    if MIN_LENGTH in schema and len(value) < schema[MIN_LENGTH]:
        raise ParameterValidationError(
            module_name,
            param_path,
            f"String with minimum length {schema[MIN_LENGTH]}",
            f"Length {len(value)}: {value}"
        )
    
    if MAX_LENGTH in schema and len(value) > schema[MAX_LENGTH]:
        raise ParameterValidationError(
            module_name,
            param_path,
            f"String with maximum length {schema[MAX_LENGTH]}",
            f"Length {len(value)}: {value}"
        )
    
    if PATTERN in schema and not re.match(schema[PATTERN], value):
        raise ParameterValidationError(
            module_name,
            param_path,
            f"String matching pattern '{schema[PATTERN]}'",
            value
        )


def validate_number(module_name, param_path, schema, value):
    """Validate number constraints."""
    if value is None:
        return
    
    if MINIMUM in schema and value < schema[MINIMUM]:
        raise ParameterValidationError(
            module_name,
            param_path,
            f"Number >= {schema[MINIMUM]}",
            value
        )
    
    if MAXIMUM in schema and value > schema[MAXIMUM]:
        raise ParameterValidationError(
            module_name,
            param_path,
            f"Number <= {schema[MAXIMUM]}",
            value
        )
    
    if EXCLUSIVE_MINIMUM in schema and value <= schema[EXCLUSIVE_MINIMUM]:
        raise ParameterValidationError(
            module_name,
            param_path,
            f"Number > {schema[EXCLUSIVE_MINIMUM]}",
            value
        )
    
    if EXCLUSIVE_MAXIMUM in schema and value >= schema[EXCLUSIVE_MAXIMUM]:
        raise ParameterValidationError(
            module_name,
            param_path,
            f"Number < {schema[EXCLUSIVE_MAXIMUM]}",
            value
        )


def validate_array(module_name, param_path, schema, value):
    """Validate array constraints and items."""
    if value is None:
        return
    
    if MIN_ITEMS in schema and len(value) < schema[MIN_ITEMS]:
        raise ParameterValidationError(
            module_name,
            param_path,
            f"Array with minimum {schema[MIN_ITEMS]} items",
            f"Array with {len(value)} items"
        )
    
    if MAX_ITEMS in schema and len(value) > schema[MAX_ITEMS]:
        raise ParameterValidationError(
            module_name,
            param_path,
            f"Array with maximum {schema[MAX_ITEMS]} items",
            f"Array with {len(value)} items"
        )
    
    # Validate each item if items schema is provided
    if ITEMS in schema and value:
        item_schema = schema[ITEMS]
        for i, item in enumerate(value):
            item_path = f"{param_path}[{i}]"
            validate_parameter(module_name, item_path, item_schema, item)


def validate_object(module_name, param_path, schema, value):
    """Validate object properties and required fields."""
    if value is None:
        return
    
    # Check required properties
    if REQUIRED in schema:
        for req_prop in schema[REQUIRED]:
            if req_prop not in value:
                raise ParameterValidationError(
                    module_name,
                    param_path,
                    f"Object with required property '{req_prop}'",
                    f"Missing required property"
                )
    
    # Validate each property if properties schema is provided
    if PROPERTIES in schema and value:
        for prop_name, prop_schema in schema[PROPERTIES].items():
            if prop_name in value:
                prop_path = f"{param_path}.{prop_name}"
                prop_value = value[prop_name]
                validate_parameter(module_name, prop_path, prop_schema, prop_value)
            elif DEFAULT in prop_schema:
                # Apply default value if property is missing
                value[prop_name] = prop_schema[DEFAULT]


def apply_defaults(schema, properties):
    """
    Apply default values from schema to properties.
    
    Args:
        schema: Schema definition
        properties: Properties to update with defaults
        
    Returns:
        Updated properties with defaults applied
    """
    if properties is None:
        properties = {}
    else:
        properties = properties.copy()
    
    for param_name, param_schema in schema.items():
        if param_name not in properties and DEFAULT in param_schema:
            properties[param_name] = param_schema[DEFAULT]
        
        # Apply defaults to nested objects
        if (param_name in properties and 
            properties[param_name] is not None and
            param_schema.get(TYPE) == OBJECT and 
            PROPERTIES in param_schema):
            
            for prop_name, prop_schema in param_schema[PROPERTIES].items():
                if (prop_name not in properties[param_name] and 
                    DEFAULT in prop_schema):
                    if properties[param_name] is None:
                        properties[param_name] = {}
                    properties[param_name][prop_name] = prop_schema[DEFAULT]
    
    return properties
