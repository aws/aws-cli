"""
Dev-only instrumentation utilities for measuring execution time (nanoseconds).

Usage:
    import awscli.perf_timer as T

    # Context manager
    with T.timer("section_name"):
        ...

    # Decorator
    @T.timed("section_name")
    def my_func(): ...

    # Import hook — call early, before imports you want to measure
    T.install_import_hook()          # all imports
    T.install_import_hook("boto")    # only modules matching prefix

    # Results are auto-saved to perf_timer_results.json at exit.
    # Manual dump:  T.dump("path.json")
"""

import atexit
import builtins
import functools
import json
import sys
import threading
import time
from contextlib import contextmanager

_lock = threading.Lock()
_stack = {}   # tid -> list of open entries
_roots = []   # completed top-level entries
_import_roots = []  # completed import entries (top-level only)
_OUT = "perf_timer_results.json"
_IMPORT_OUT = "perf_timer_imports.json"


def _tid():
    return threading.get_ident()


def _now():
    return time.time_ns()


def _current_stack():
    return _stack.setdefault(_tid(), [])


def _is_import(name):
    return name.startswith("import:")


def _begin(name):
    entry = {"name": name, "start_ns": _now(), "tid": _tid(), "children": []}
    with _lock:
        st = _current_stack()
        is_imp = _is_import(name)
        # Find nearest same-category ancestor (not just immediate parent)
        for i in range(len(st) - 1, -1, -1):
            if _is_import(st[i]["name"]) == is_imp:
                st[i]["children"].append(entry)
                break
        st.append(entry)
    return entry


def _end(entry):
    entry["end_ns"] = _now()
    entry["dur_ns"] = entry["end_ns"] - entry["start_ns"]
    is_imp = _is_import(entry["name"])
    with _lock:
        st = _current_stack()
        assert st[-1] is entry, f"Stack mismatch: expected {entry['name']}, got {st[-1]['name']}"
        st.pop()
        # It's a root if nothing on the stack shares its category
        has_same_category_parent = any(
            _is_import(e["name"]) == is_imp for e in st
        )
        if not has_same_category_parent:
            if is_imp:
                _import_roots.append(entry)
            else:
                _roots.append(entry)


@contextmanager
def timer(name):
    e = _begin(name)
    try:
        yield e
    finally:
        _end(e)


def timed(name):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            with timer(name):
                return fn(*a, **kw)
        return wrapper
    return deco


# --- Import hook ---

_original_import = builtins.__import__
_import_prefix = None


def _hooked_import(name, *args, **kwargs):
    if _import_prefix and not name.startswith(_import_prefix):
        return _original_import(name, *args, **kwargs)
    if name in sys.modules:
        return _original_import(name, *args, **kwargs)
    with timer(f"import:{name}"):
        return _original_import(name, *args, **kwargs)


def install_import_hook(prefix=None):
    global _import_prefix
    _import_prefix = prefix
    builtins.__import__ = _hooked_import


def remove_import_hook():
    builtins.__import__ = _original_import


# --- Output ---

def _serialize(entries):
    out = []
    for e in entries:
        node = {
            "name": e["name"],
            "start_ns": e["start_ns"],
            "end_ns": e.get("end_ns"),
            "dur_ns": e.get("dur_ns"),
            "tid": e["tid"],
        }
        if e["children"]:
            node["children"] = _serialize(e["children"])
        out.append(node)
    return out


def dump(path=None):
    try:
        with _lock:
            data = _serialize(_roots)
            import_data = _serialize(_import_roots)
        with open(path or _OUT, "w") as f:
            json.dump(data, f, indent=2)
        with open(_IMPORT_OUT, "w") as f:
            json.dump(import_data, f, indent=2)
    except Exception:
        pass


atexit.register(dump)
