"""
Regression test for six issue #98 (https://github.com/benjaminp/six/issues/98)
"""

import sys
import threading
import time

from botocore.vendored import six
from tests import mock

_original_setattr = six.moves.__class__.__setattr__


def _wrapped_setattr(key, value):
    # Monkey patch six.moves.__setattr__ to simulate
    # a poorly-timed thread context switch
    time.sleep(0.1)
    return _original_setattr(six.moves, key, value)


def _reload_six():
    # Issue #98 is caused by a race condition in six._LazyDescr.__get__
    # which is only called once per moved module. Reload six so all the
    # moved modules are reset.
    import importlib

    importlib.reload(six)


class _ExampleThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = False
        self.exc_info = None

    def run(self):
        try:
            # Simulate use of six by
            # botocore.configloader.raw_config_parse()
            # Should raise AttributeError if six < 1.9.0
            six.moves.configparser.RawConfigParser()
        except Exception:
            self.exc_info = sys.exc_info()


def test_six_thread_safety():
    _reload_six()
    with mock.patch(
        'botocore.vendored.six.moves.__class__.__setattr__',
        wraps=_wrapped_setattr,
    ):
        threads = []
        for i in range(2):
            t = _ExampleThread()
            threads.append(t)
            t.start()
        while threads:
            t = threads.pop()
            t.join()
            if t.exc_info:
                six.reraise(*t.exc_info)
