"""
An implementation of JSON Schema for Python

The main functionality is provided by the validator classes for each of the
supported JSON Schema versions.

Most commonly, `validate` is the quickest way to simply validate a given
instance under a schema, and will create a validator for you.
"""
import warnings

from jsonschema._format import (
    FormatChecker,
    draft3_format_checker,
    draft4_format_checker,
    draft6_format_checker,
    draft7_format_checker,
    draft201909_format_checker,
    draft202012_format_checker,
)
from jsonschema._types import TypeChecker
from jsonschema.exceptions import (
    ErrorTree,
    FormatError,
    RefResolutionError,
    SchemaError,
    ValidationError,
)
from jsonschema.protocols import Validator
from jsonschema.validators import (
    Draft3Validator,
    Draft4Validator,
    Draft6Validator,
    Draft7Validator,
    Draft201909Validator,
    Draft202012Validator,
    RefResolver,
    validate,
)


def __getattr__(name):
    if name == "__version__":
        warnings.warn(
            "Accessing jsonschema.__version__ is deprecated and will be "
            "removed in a future release. Use importlib.metadata directly "
            "to query for jsonschema's version.",
            DeprecationWarning,
            stacklevel=2,
        )

        try:
            from importlib import metadata
        except ImportError:
            import importlib_metadata as metadata

        return metadata.version("jsonschema")
    raise AttributeError(f"module {__name__} has no attribute {name}")
