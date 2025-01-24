"""
Provides configuration values from the environment variables.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from tox.config.loader.str_convert import StrConvert

CONVERT = StrConvert()


def get_env_var(key: str, of_type: type[Any]) -> tuple[Any, str] | None:
    """Get the environment variable option.

    :param key: the config key requested
    :param of_type: the type we would like to convert it to
    :return:
    """
    key_upper = key.upper()
    for environ_key in (f"TOX_{key_upper}", f"TOX{key_upper}"):
        if environ_key in os.environ:
            value = os.environ[environ_key]
            try:
                source = f"env var {environ_key}"
                result = CONVERT.to(raw=value, of_type=of_type, factory=None)
                return result, source
            except Exception as exception:
                logging.warning(
                    "env var %s=%r cannot be transformed to %r because %r",
                    environ_key,
                    value,
                    of_type,
                    exception,
                )
    return None


__all__ = ("get_env_var",)
