"""
Run tox environments in parallel.
"""
from __future__ import annotations

import logging
from argparse import ArgumentParser, ArgumentTypeError

from tox.config.cli.parser import ToxParser
from tox.plugin import impl
from tox.session.state import State
from tox.util.cpu import auto_detect_cpus

from ...env_select import CliEnv, register_env_select_flags
from .common import env_run_create_flags, execute

logger = logging.getLogger(__name__)

ENV_VAR_KEY = "TOX_PARALLEL_ENV"
OFF_VALUE = 0
DEFAULT_PARALLEL = OFF_VALUE


@impl
def tox_add_option(parser: ToxParser) -> None:
    our = parser.add_command("run-parallel", ["p"], "run environments in parallel", run_parallel)
    register_env_select_flags(our, default=CliEnv())
    env_run_create_flags(our, mode="run-parallel")
    parallel_flags(our, default_parallel=auto_detect_cpus())


def parse_num_processes(str_value: str) -> int | None:
    if str_value == "all":
        return None
    if str_value == "auto":
        return auto_detect_cpus()
    try:
        value = int(str_value)
    except ValueError as exc:
        raise ArgumentTypeError(f"value must be a positive number, is {str_value!r}") from exc
    if value < 0:
        raise ArgumentTypeError(f"value must be positive, is {value!r}")
    return value


def parallel_flags(our: ArgumentParser, default_parallel: int, no_args: bool = False) -> None:
    our.add_argument(
        "-p",
        "--parallel",
        dest="parallel",
        help="run tox environments in parallel, the argument controls limit: all,"
        " auto - cpu count, some positive number, zero is turn off",
        action="store",
        type=parse_num_processes,  # type: ignore # nargs confuses it
        default=default_parallel,
        metavar="VAL",
        **({"nargs": "?"} if no_args else {}),  # type: ignore # type checker can't unroll it
    )
    our.add_argument(
        "-o",
        "--parallel-live",
        action="store_true",
        dest="parallel_live",
        help="connect to stdout while running environments",
    )
    our.add_argument(
        "--parallel-no-spinner",
        action="store_true",
        dest="parallel_no_spinner",
        help="do not show the spinner",
    )


def run_parallel(state: State) -> int:
    """here we'll just start parallel sub-processes"""
    option = state.conf.options
    return execute(
        state,
        max_workers=option.parallel,
        has_spinner=option.parallel_no_spinner is False and option.parallel_live is False,
        live=option.parallel_live,
    )
