def _is_dot_notation_getatt(getatt_val, foreach_modules):
    """Check if this is a ModuleName.Identifier.OutputName format GetAtt"""
    return (
        isinstance(getatt_val, list)
        and len(getatt_val) == 2
        and isinstance(getatt_val[0], str)
        and isinstance(getatt_val[1], str)
        and "." in getatt_val[1]
        and getatt_val[0] in foreach_modules
    )


def _is_wildcard_notation_getatt(getatt_val, foreach_modules):
    """Check if this is a ModuleName.*.OutputName format GetAtt"""
    return (
        isinstance(getatt_val, list)
        and len(getatt_val) == 2
        and isinstance(getatt_val[0], str)
        and isinstance(getatt_val[1], str)
        and getatt_val[1].startswith("*.")
        and getatt_val[0] in foreach_modules
    )
