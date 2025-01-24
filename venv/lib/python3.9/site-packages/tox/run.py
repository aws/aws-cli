"""Main entry point for tox."""
from __future__ import annotations

import faulthandler
import logging
import os
import sys
import time
from typing import Sequence

from tox.config.cli.parse import get_options
from tox.report import HandledError, ToxHandler
from tox.session.state import State


def run(args: Sequence[str] | None = None) -> None:
    try:
        with ToxHandler.patch_thread():
            result = main(sys.argv[1:] if args is None else args)
    except Exception as exception:
        if isinstance(exception, HandledError):
            logging.error("%s| %s", type(exception).__name__, str(exception))
            result = -2
        else:
            raise
    except KeyboardInterrupt:
        result = -2
    finally:
        if "_TOX_SHOW_THREAD" in os.environ:  # pragma: no cover
            import threading  # pragma: no cover

            for thread in threading.enumerate():  # pragma: no cover
                print(thread)  # pragma: no cover
    raise SystemExit(result)


def main(args: Sequence[str]) -> int:
    state = setup_state(args)
    from tox.provision import provision

    result = provision(state)
    if result is not False:
        return result
    handler = state._options.cmd_handlers[state.conf.options.command]
    result = handler(state)
    return result


def setup_state(args: Sequence[str]) -> State:
    """Setup the state object of this run."""
    start = time.monotonic()
    # parse CLI arguments
    options = get_options(*args)
    options.parsed.start = start
    if options.parsed.exit_and_dump_after:
        faulthandler.dump_traceback_later(timeout=options.parsed.exit_and_dump_after, exit=True)  # pragma: no cover
    # build tox environment config objects
    state = State(options, args)
    return state
