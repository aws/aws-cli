"""
A reader that drain a stream via its file no on a background thread.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from threading import Event, Thread
from types import TracebackType
from typing import Callable

WAIT_GENERAL = 0.05  # stop thread join every so often (give chance to a signal interrupt)


class ReadViaThread(ABC):
    def __init__(self, file_no: int, handler: Callable[[bytes], None], name: str, drain: bool) -> None:
        self.file_no = file_no
        self.stop = Event()
        self.thread = Thread(target=self._read_stream, name=f"tox-r-{name}-{file_no}")
        self.handler = handler
        self._on_exit_drain = drain

    def __enter__(self) -> ReadViaThread:
        self.thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,  # noqa: U100
        exc_val: BaseException | None,  # noqa: U100
        exc_tb: TracebackType | None,  # noqa: U100
    ) -> None:
        self.stop.set()  # signal thread to stop
        while self.thread.is_alive():  # wait until it stops
            self.thread.join(WAIT_GENERAL)
        self._drain_stream()  # read anything left

    @abstractmethod
    def _read_stream(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def _drain_stream(self) -> None:
        raise NotImplementedError
