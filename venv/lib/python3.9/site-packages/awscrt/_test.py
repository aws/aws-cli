"""
Private utilities for testing
"""
import _awscrt
from awscrt import NativeResource
import gc
import inspect
import os
import sys
import time
import types

from awscrt.io import ClientBootstrap, DefaultHostResolver, EventLoopGroup


def native_memory_usage() -> int:
    """
    Returns number of bytes currently allocated by awscrt's native code.

    `AWS_CRT_MEMORY_TRACING `environment variable must be set before module
    is loaded, or 0 will always be returned. Legal values are:

    *   `AWS_CRT_MEMORY_TRACING=0`: No tracing

    *   `AWS_CRT_MEMORY_TRACING=1`: Only track allocation sizes and total allocated

    *   `AWS_CRT_MEMORY_TRACING=2`: Capture callstacks for each allocation
    """
    return _awscrt.native_memory_usage()


def dump_native_memory():
    """
    If there are outstanding allocations from awscrt's native code, dump them
    to log, along with any information gathered based on the tracing level.

    In order to see the dump, logging must initialized at `LogLevel.Trace`
    and the `AWS_CRT_MEMORY_TRACING` environment variable must be non-zero
    when module is loaded. Legal values are:

    *   `AWS_CRT_MEMORY_TRACING=0`: No tracing

    *   `AWS_CRT_MEMORY_TRACING=1`: Only track allocation sizes and total allocated

    *   `AWS_CRT_MEMORY_TRACING=2`: Capture callstacks for each allocation
    """
    return _awscrt.native_memory_dump()


def join_all_native_threads(*, timeout_sec: float = -1.0) -> bool:
    """
    Waits for all native threads to complete their join call.

    This can only be safely called from the main thread.
    This call may be required for native memory usage to reach zero.

    Args:
        timeout_sec (float): Number of seconds to wait before a timeout exception is raised.
            By default the wait is unbounded.

    Returns:
        bool: Returns whether threads could be joined before the timeout.
    """
    return _awscrt.thread_join_all_managed(timeout_sec)


def check_for_leaks(*, timeout_sec=10.0):
    """
    Checks that all awscrt resources have been freed after a test.

    If any resources still exist, debugging info is printed and an exception is raised.

    Requirements:
        * `awscrt.NativeResource._track_lifetime = True`: must be set before test begins
            to ensure accurate tracking.

        * `AWS_CRT_MEMORY_TRACING=2`: environment variable that must be set before
            any awscrt modules are imported, to ensure accurate native leak checks.

        * `AWS_CRT_MEMORY_PRINT_SECRETS_OK=1`: optional environment variable that
            will print the full contents of leaked python objects. DO NOT SET THIS
            if the test results will be made public as it may result in secrets
            being leaked.
    """
    ClientBootstrap.release_static_default()
    EventLoopGroup.release_static_default()
    DefaultHostResolver.release_static_default()

    if os.getenv('AWS_CRT_MEMORY_TRACING') != '2':
        raise RuntimeError("environment variable AWS_CRT_MEMORY_TRACING=2 must be set for accurate leak checks")

    if not NativeResource._track_lifetime:
        raise RuntimeError("awscrt.NativeResource._track_lifetime=True must be set for accurate leak checks")

    # Native resources might need a few more ticks to finish cleaning themselves up.
    wait_until = time.time() + timeout_sec
    while time.time() < wait_until:
        if not NativeResource._living and not native_memory_usage() > 0:
            return
        gc.collect()
        # join_all_native_threads() is sometimes required to get mem usage to 0
        join_all_native_threads(timeout_sec=0.1)
        time.sleep(0.1)

    # Print out debugging info on leaking resources
    num_living_resources = len(NativeResource._living)
    if num_living_resources:

        leak_secrets_ok = os.getenv('AWS_CRT_MEMORY_PRINT_SECRETS_OK') == '1'
        if leak_secrets_ok:
            print("Leaking NativeResources:")
        else:
            print("Leaking NativeResources (set AWS_CRT_MEMORY_PRINT_SECRETS_OK=1 env var for more detailed report):")

        def _printobj(prefix, obj):
            # be sure not to accidentally print a dictionary with a password in it
            if leak_secrets_ok:
                s = str(obj)
                if len(s) > 1000:
                    s = s[:1000] + '...TRUNCATED PRINT'
                print(prefix, s)
            else:
                print(prefix, type(obj))

        for i in NativeResource._living:
            _printobj('-', i)

            # getrefcount(i) returns 4+ here, but 2 of those are due to debugging.
            # Don't show:
            # - 1 for WeakSet iterator due to this for-loop.
            # - 1 for getrefcount(i)'s reference.
            # But do show:
            # - 1 for item's self-reference.
            # - the rest are what's causing this leak.
            refcount = sys.getrefcount(i) - 2

            # Gather list of referrers, but don't show those created by the act of iterating the WeakSet
            referrers = []
            for r in gc.get_referrers(i):
                if isinstance(r, types.FrameType):
                    frameinfo = inspect.getframeinfo(r)
                    our_fault = (frameinfo.filename.endswith('_weakrefset.py') or
                                 frameinfo.filename.endswith('awscrt/_test.py'))
                    if our_fault:
                        continue

                referrers.append(r)

            print('  sys.getrefcount():', refcount)
            print('  gc.referrers():', len(referrers))
            for r in referrers:
                if isinstance(r, types.FrameType):
                    _printobj('  -', inspect.getframeinfo(r))
                else:
                    _printobj('  -', r)

    mem_bytes = native_memory_usage()
    if mem_bytes > 0:
        print('Leaking {} bytes native memory (enable Trace logging to see more)'.format(mem_bytes))
        dump_native_memory()

    raise RuntimeError("awscrt leak check failed. {} NativeResource objects. {} bytes native memory".format(
        num_living_resources, mem_bytes))
