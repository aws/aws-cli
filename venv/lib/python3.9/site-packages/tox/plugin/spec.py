from __future__ import annotations

from typing import Any, Callable, TypeVar, cast

import pluggy

from tox.config.sets import ConfigSet, EnvConfigSet
from tox.tox_env.register import ToxEnvRegister

from ..config.cli.parser import ToxParser
from ..execute import Outcome
from ..session.state import State
from ..tox_env.api import ToxEnv
from . import NAME

_F = TypeVar("_F", bound=Callable[..., Any])
_spec_marker = pluggy.HookspecMarker(NAME)


def _spec(func: _F) -> _F:
    return cast(_F, _spec_marker(func))


@_spec
def tox_register_tox_env(register: ToxEnvRegister) -> None:  # noqa: U100
    """
    Register new tox environment type. You can register:

    - **run environment**: by default this is a local subprocess backed virtualenv Python
    - **packaging environment**: by default this is a PEP-517 compliant local subprocess backed virtualenv Python

    :param register: a object that can be used to register new tox environment types
    """


@_spec
def tox_add_option(parser: ToxParser) -> None:  # noqa: U100
    """
    Add a command line argument. This is the first hook to be called, right after the logging setup and config source
    discovery.

    :param parser: the command line parser
    """


@_spec
def tox_add_core_config(core_conf: ConfigSet, state: State) -> None:  # noqa: U100
    """
    Called when the core configuration is built for a tox environment.

    :param core_conf: the core configuration object
    :param state: the global tox state object
    """


@_spec
def tox_add_env_config(env_conf: EnvConfigSet, state: State) -> None:  # noqa: U100
    """
    Called when configuration is built for a tox environment.

    :param env_conf: the core configuration object
    :param state: the global tox state object
    """


@_spec
def tox_before_run_commands(tox_env: ToxEnv) -> None:  # noqa: U100
    """
    Called before the commands set is executed.

    :param tox_env: the tox environment being executed
    """


@_spec
def tox_after_run_commands(tox_env: ToxEnv, exit_code: int, outcomes: list[Outcome]) -> None:  # noqa: U100
    """
    Called after the commands set is executed.

    :param tox_env: the tox environment being executed
    :param exit_code: exit code of the command
    :param outcomes: outcome of each command execution
    """


@_spec
def tox_on_install(tox_env: ToxEnv, arguments: Any, section: str, of_type: str) -> None:  # noqa: U100
    """
    Called before executing an installation command.

    :param tox_env: the tox environment where the command runs in
    :param arguments: installation arguments
    :param section: section of the installation
    :param of_type: type of the installation
    """


@_spec
def tox_env_teardown(tox_env: ToxEnv) -> None:  # noqa: U100
    """
    Called before executing an installation command.

    :param tox_env: the tox environment
    """


__all__ = [
    "NAME",
    "tox_register_tox_env",
    "tox_add_option",
    "tox_add_core_config",
    "tox_add_env_config",
    "tox_before_run_commands",
    "tox_after_run_commands",
    "tox_on_install",
    "tox_env_teardown",
]
