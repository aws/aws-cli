pub const ASSERTIONS: &str = r#"
import _zippy_finder as z
import sys

assert sys.stdin.encoding.lower() == "utf-8"
assert sys.stdout.encoding.lower() == "utf-8"
assert sys.stderr.encoding.lower() == "utf-8"
assert sys.stdin.errors == "surrogateescape"
assert sys.stdout.errors == "surrogateescape"
assert sys.stderr.errors == "backslashreplace"
assert sys.path == EXPECTED_SYS_PATH
assert sum(type(item) is z.Finder for item in sys.meta_path) == 1

assert z.exists("plain") is True
assert z.exists("missing") is False
try:
    z.exists(1)
except TypeError:
    pass
else:
    raise AssertionError("exists accepted a non-string")
assert z.is_package("pkg") is True
assert z.is_package("plain") is False
try:
    z.is_package("missing")
except FileNotFoundError:
    pass
else:
    raise AssertionError("is_package did not report a missing entry")
assert z.is_bytecode("plain") is True
assert z.is_bytecode("resources/raw.txt") is False
assert z.is_bytecode("missing") is False
assert z.has_prefix("dir/") is True
assert z.has_prefix("dir/sub/") is True
assert z.has_prefix("zzzz") is False
assert z.list_prefix("dir/") == [
    "dir/a.txt", "dir/sub/b.txt", "dir/sub/c.txt", "dir/z.txt"
]
assert z.list_prefix("missing/") == []
assert z.list_dir("dir/") == ["a.txt", "sub", "z.txt"]
assert z.list_dir("dir/sub/") == ["b.txt", "c.txt"]
assert z.list_services("models/", "service-2") == ["ec2", "s3"]
assert z.list_services("models/", "waiters-2") == ["s3"]
assert z.list_api_versions("models/", "ec2", "service-2") == [
    "2015-01-01", "2016-11-15"
]
assert z.list_api_versions("models/", "s3", "waiters-2") == ["2006-03-01"]
assert z.list_api_versions("models/", "missing", "service-2") == []

assert z.get_data("resources/raw.txt") == b"raw resource bytes"
assert z.get_data("resources/compressed.txt") == b"compressed resource bytes"
try:
    z.get_data("missing")
except FileNotFoundError:
    pass
else:
    raise AssertionError("get_data did not report a missing entry")
try:
    z.get_data("bad_compressed_mod")
except OSError:
    pass
else:
    raise AssertionError("get_data accepted malformed compressed data")

# Every compressed read reserves the zstd scratch, pyload::decompress::ZSTD_BUFFER_LEN
# (the default window plus the largest block), through PyMem_Malloc and frees it
# before returning; raw entries need no scratch.
import _tracemalloc
ZSTD_BUFFER_LEN = 8 * 1024 * 1024 + 128 * 1024

def traced_growth(function, *args):
    _tracemalloc.start()
    try:
        before = _tracemalloc.get_traced_memory()[0]
        _tracemalloc.reset_peak()
        function(*args)
        current, peak = _tracemalloc.get_traced_memory()
        return current - before, peak - before
    finally:
        _tracemalloc.stop()

for function, name in [(z.get_data, "resources/compressed.txt"),
                       (z.load_code, "compressed_mod")]:
    retained, peak = traced_growth(function, name)
    assert peak >= ZSTD_BUFFER_LEN, (name, peak)
    assert retained < 64 * 1024, (name, retained)
for function, name in [(z.get_data, "resources/raw.txt"), (z.load_code, "plain")]:
    _, peak = traced_growth(function, name)
    assert peak < 64 * 1024, (name, peak)

plain_ns = {}
exec(z.load_code("plain"), plain_ns)
assert plain_ns["VALUE"] == 11
compressed_ns = {}
exec(z.load_code("compressed_mod"), compressed_ns)
assert compressed_ns["VALUE"] == 33
try:
    z.load_code("resources/raw.txt")
except ImportError:
    pass
else:
    raise AssertionError("load_code accepted a resource")
try:
    z.load_code("malformed_mod")
except ValueError:
    pass
else:
    raise AssertionError("load_code accepted malformed marshal data")
try:
    z.load_code("noncode_mod")
except ImportError:
    pass
else:
    raise AssertionError("load_code accepted a marshalled non-code object")
try:
    z.load_code("bad_compressed_mod")
except OSError:
    pass
else:
    raise AssertionError("load_code accepted malformed compressed data")

stats = z.stats()
assert stats == {
    "entry_count": EXPECTED_ENTRY_COUNT,
    "blob_length": EXPECTED_BLOB_LENGTH,
}

finder = z.Finder()
plain_spec = finder.find_spec("plain")
assert plain_spec.name == "plain"
assert plain_spec.loader is finder
assert plain_spec.origin == "/<zippy>/plain.py"
assert plain_spec.submodule_search_locations is None
pkg_spec = finder.find_spec("pkg")
assert pkg_spec.origin == "/<zippy>/pkg/__init__.py"
assert pkg_spec.submodule_search_locations == []
assert finder.find_spec("missing") is None
assert finder.find_spec("resources/raw.txt") is None

alias_spec = finder.find_spec("botocore", [])
assert alias_spec._zippy_lookup_name == "awscli.botocore"
assert alias_spec.submodule_search_locations == [
    "/<zippy>/__ZIPPY_VENDORED__/awscli.botocore"
]
alias_module = type(sys)("botocore")
alias_module.__spec__ = alias_spec
finder.exec_module(alias_module)
assert alias_module.ALIAS_VALUE == "botocore"
assert alias_module.__file__ == "/<zippy>/awscli/botocore/__init__.py"
vendored_spec = finder.find_spec(
    "public.child", ["/<zippy>/__ZIPPY_VENDORED__/vendor.root"]
)
assert vendored_spec._zippy_lookup_name == "vendor.root.child"
vendored_module = type(sys)("public.child")
vendored_module.__spec__ = vendored_spec
finder.exec_module(vendored_module)
assert vendored_module.VENDORED_VALUE == 44
assert vendored_module.__file__ == "/<zippy>/vendor/root/child.py"
# Relative to the working directory, the marker names no vendored package.
assert finder.find_spec(
    "public.child", ["__ZIPPY_VENDORED__/vendor.root"]
) is None
malformed_spec = finder.find_spec("malformed_mod")
malformed_module = type(sys)("malformed_mod")
malformed_module.__spec__ = malformed_spec
try:
    finder.exec_module(malformed_module)
except ValueError:
    pass
else:
    raise AssertionError("manual malformed exec unexpectedly succeeded")

import plain
assert plain.VALUE == 11
assert plain.__file__ == "/<zippy>/plain.py"
import pkg
assert pkg.PACKAGE_VALUE == 22
import pkg.child
assert pkg.child.CHILD_VALUE == 23
assert pkg.child.__file__ == "/<zippy>/pkg/child.py"
import compressed_mod
assert compressed_mod.VALUE == 33
try:
    import definitely_missing
except ModuleNotFoundError:
    pass
else:
    raise AssertionError("missing import unexpectedly succeeded")
try:
    import malformed_mod
except ValueError:
    pass
else:
    raise AssertionError("malformed marshal import unexpectedly succeeded")
assert "malformed_mod" not in sys.modules
try:
    import noncode_mod
except ImportError:
    pass
else:
    raise AssertionError("marshalled non-code import unexpectedly succeeded")
assert "noncode_mod" not in sys.modules
try:
    import bad_compressed_mod
except OSError:
    pass
else:
    raise AssertionError("malformed compressed import unexpectedly succeeded")
assert "bad_compressed_mod" not in sys.modules

none_refs = sys.getrefcount(None)
finder_refs = sys.getrefcount(finder)
for _ in range(128):
    assert finder.find_spec("repeated-miss") is None
    assert finder.create_module(None) is None
    repeated_alias = finder.find_spec("botocore", [])
    assert repeated_alias._zippy_lookup_name == "awscli.botocore"
    del repeated_alias
assert sys.getrefcount(None) == none_refs
assert sys.getrefcount(finder) == finder_refs

installed = next(item for item in sys.meta_path if type(item) is z.Finder)
sys.meta_path.remove(installed)
del installed
assert sum(type(item) is z.Finder for item in sys.meta_path) == 0
"#;

pub const REPLACEMENT_ASSERTIONS: &str = r#"
import _zippy_finder as z
import sys
assert sum(type(item) is z.Finder for item in sys.meta_path) == 1
assert z.exists("plain") is False
assert z.exists("replacement.txt") is True
assert z.get_data("replacement.txt") == b"replacement"
assert z.stats() == {
    "entry_count": EXPECTED_ENTRY_COUNT,
    "blob_length": EXPECTED_BLOB_LENGTH,
}
"#;

pub const REJECTED_REINSTALL_ASSERTIONS: &str = r#"
import _zippy_finder as z
assert z.exists("replacement.txt") is True
assert z.get_data("replacement.txt") == b"replacement"
"#;

pub const ATEXIT_IMPORT_REGISTRATION: &str = r#"
import atexit
import sys

def _import_during_finalize():
    sys.modules.pop("gc", None)
    __import__("gc")
    with open(FINALIZE_MARKER_PATH, "w") as marker:
        marker.write("imported")

atexit.register(_import_during_finalize)
"#;
pub const MISSING_PAYLOAD: &str = r#"
import _zippy_finder as z
import sys

def expect_error(exception, function, *args, message=None):
    try:
        function(*args)
    except exception as error:
        assert message is None or str(error) == message, error
        return
    raise AssertionError(f'{function} did not raise {exception}')

expect_error(RuntimeError, z.stats, message='zippy: payload not loaded')
# Arguments are converted before the payload view is checked, and lookup names
# are bounded only after it.
for function in [z.exists, z.is_package, z.is_bytecode, z.get_data, z.load_code]:
    expect_error(TypeError, function, 1)
expect_error(RuntimeError, z.exists, 'x', message='zippy: payload not loaded')
expect_error(
    RuntimeError, z.list_api_versions, 'x' * 4096, 's', 'service-2',
    message='zippy: payload not loaded',
)
module = type(sys)('unnamed')
module.__name__ = 1
expect_error(TypeError, z.Finder().exec_module, module)
"#;

pub const EDGES: &str = r#"
def expect_error(exception, function, *args):
    try:
        function(*args)
    except exception:
        return
    raise AssertionError(f'{function} did not raise {exception}')

assert z.get_data('empty') == b''
assert z.get_data('compressed-empty') == b''
assert finder.get_data('empty') == b''
assert finder.get_data('compressed-empty') == b''
expect_error(FileNotFoundError, finder.get_data, 'missing')
expect_error(FileNotFoundError, z.load_code, 'missing')
expect_error(TypeError, z.stats, 1)
for function in [z.exists, z.is_package, z.is_bytecode, z.has_prefix,
                 z.list_prefix, z.list_dir, z.get_data, z.load_code]:
    expect_error(TypeError, function)
    expect_error(TypeError, function, 1)
    expect_error(TypeError, function, 'name', 'extra')
expect_error(TypeError, z.list_services, 'prefix')
expect_error(TypeError, z.list_services, 'prefix', 1)
expect_error(TypeError, z.list_api_versions, 'prefix', 'service')
expect_error(TypeError, z.list_api_versions, 'prefix', 'service', 1)
expect_error(OverflowError, z.list_api_versions, 'x' * 4096, 's', 'service-2')
expect_error(TypeError, z.list_api_versions, 'x' * 4096, 's', 1)
expect_error(TypeError, finder.find_spec)
expect_error(TypeError, finder.find_spec, 1)
expect_error(TypeError, finder.find_spec, 'name', None, None, None)
expect_error(OverflowError, finder.find_spec, 'm' * 1024)
expect_error(
    OverflowError, finder.find_spec, 'child', ['/<zippy>/__ZIPPY_VENDORED__/' + 'x' * 4096]
)
assert finder.find_spec('s3transfer') is None
for path in [[], (), 1, [1], ['/<zippy>/__ZIPPY_VENDORED__/'], ['__ZIPPY_VENDORED__/x']]:
    alias = finder.find_spec('s3transfer', path)
    assert alias._zippy_lookup_name == 'awscli.s3transfer'
    assert alias.origin == '/<zippy>/s3transfer/__init__.py'
    assert alias.submodule_search_locations == [
        '/<zippy>/__ZIPPY_VENDORED__/awscli.s3transfer'
    ]
vendored = finder.find_spec('public.pkg', ['/<zippy>/__ZIPPY_VENDORED__/vendor.root'])
assert vendored._zippy_lookup_name == 'vendor.root.pkg'
assert vendored.submodule_search_locations == [
    '/<zippy>/__ZIPPY_VENDORED__/vendor.root.pkg'
]
module = type(sys)('public.pkg')
module.__spec__ = vendored
finder.exec_module(module)
assert module.VALUE == 55
assert module.__file__ == '/<zippy>/vendor/root/pkg/__init__.py'
assert '__builtins__' in module.__dict__
for spec in [None, type('Spec', (), {'_zippy_lookup_name': None})()]:
    module = type(sys)('awscli.s3transfer')
    module.__spec__ = spec
    finder.exec_module(module)
    assert module.VALUE == 55
# A synthetic file past the 1024-byte buffer fails the import before the body runs.
module = type(sys)('m' * 1024)
expect_error(OverflowError, finder.exec_module, module)
assert not hasattr(module, 'VALUE')
assert '__file__' not in module.__dict__
module = type(sys)('missing')
expect_error(ImportError, finder.exec_module, module)
module = type(sys)('empty')
expect_error(ImportError, finder.exec_module, module)
installed = next(item for item in sys.meta_path if type(item) is z.Finder)
sys.meta_path.remove(installed)
del installed
"#;

pub const FILE_ALLOCATION_SETUP: &str = r#"
import _zippy_finder as z
import sys
file_allocation_module = type(sys)('n' * 512)
file_allocation_exec = z.Finder().exec_module
file_allocation_args = (file_allocation_module,)
file_allocation_size = sys.getsizeof('/<zippy>/' + 'n' * 512 + '.py')
"#;

pub const FILE_ALLOCATION_ASSERTIONS: &str = r#"
assert not hasattr(file_allocation_module, 'FILE_ALLOCATION_VALUE')
assert not hasattr(file_allocation_module, '__file__')
del file_allocation_module, file_allocation_exec, file_allocation_args
del file_allocation_size
"#;

pub const INIT_FAILURE_ASSERTIONS: &str = r#"
import gc
gc.collect()
assert not [
    module for module in gc.get_objects()
    if type(module) is type(gc) and module.__name__ == '_zippy_finder'
], 'a failed initialization leaked its module'
"#;

pub const UNSORTED_ASSERTIONS: &str = r#"
import _zippy_finder as z
try:
    z.list_services('models/', 'service-2')
except RuntimeError as error:
    assert str(error) == 'zippy: invalid payload', error
else:
    raise AssertionError('list_services accepted an unsorted payload')
try:
    z.list_api_versions('models/', 'a', 'service-2')
except RuntimeError as error:
    assert str(error) == 'zippy: invalid payload', error
else:
    raise AssertionError('list_api_versions accepted an unsorted payload')
"#;

pub const SUBINTERPRETER: &str = r#"
import _zippy_finder as z
finder = z.Finder()
calls = [
    (z.exists, ('replacement.txt',)),
    (z.has_prefix, ('replacement',)),
    (z.list_prefix, ('replacement',)),
    (z.list_dir, ('replacement',)),
    (z.list_services, ('models/', 'service-2')),
    (z.list_api_versions, ('models/', 's3', 'service-2')),
    (z.get_data, ('replacement.txt',)),
    (z.load_code, ('replacement.txt',)),
    (z.is_package, ('replacement.txt',)),
    (z.is_bytecode, ('replacement.txt',)),
    (z.stats, ()),
    (finder.find_spec, ('replacement.txt',)),
    (finder.create_module, (None,)),
    (finder.exec_module, (None,)),
    (finder.get_data, ('replacement.txt',)),
]
assert len(calls) == 15
for function, args in calls:
    try:
        function(*args)
    except ImportError as error:
        assert str(error) == 'zippy: finder is only available in the main interpreter'
    else:
        raise AssertionError(f'{function} accessed the main interpreter finder')
"#;

pub const AFTER_SUBINTERPRETER: &str = r#"
assert z.get_data('replacement.txt') == b'replacement'
assert z.Finder().get_data('replacement.txt') == b'replacement'
assert z.stats()['entry_count'] == 1
"#;
