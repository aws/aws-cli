use python_fallback::helpers::HostExitStatus;
use std::ffi::CStr;

pub struct Case {
    pub source: &'static CStr,
    pub status: HostExitStatus,
    pub stderr_contains: &'static str,
}

const fn silent(source: &'static CStr, status: i64) -> Case {
    Case {
        source,
        status: status as HostExitStatus,
        stderr_contains: "",
    }
}

pub const CASES: &[Case] = &[
    silent(c"raise SystemExit()", 0),
    silent(c"raise SystemExit(None)", 0),
    silent(c"raise SystemExit(0)", 0),
    silent(c"raise SystemExit(1)", 1),
    silent(c"raise SystemExit(2)", 2),
    silent(c"raise SystemExit(255)", 255),
    silent(c"raise SystemExit(-1)", -1),
    silent(c"raise SystemExit(-9)", -9),
    silent(c"raise SystemExit(-100)", -100),
    silent(c"raise SystemExit(-255)", -255),
    silent(c"raise SystemExit(-256)", -256),
    silent(c"raise SystemExit(256)", 256),
    silent(c"raise SystemExit(300)", 300),
    silent(c"raise SystemExit(2 ** 31)", 1 << 31),
    silent(c"raise SystemExit(2 ** 31 - 1)", (1 << 31) - 1),
    silent(c"raise SystemExit(2 ** 33 + 300)", (1 << 33) + 300),
    silent(c"raise SystemExit(2 ** 63 - 1)", i64::MAX),
    silent(c"raise SystemExit(-(2 ** 63))", i64::MIN),
    silent(c"raise SystemExit(2 ** 64)", -1),
    silent(c"raise SystemExit(-(2 ** 64))", -1),
    silent(c"raise SystemExit(True)", 1),
    silent(c"raise SystemExit(False)", 0),
    silent(
        c"class Status(int): pass\nraise SystemExit(Status(300))",
        300,
    ),
    Case {
        source:
            c"class Indexable:\n    def __index__(self): return 5\nraise SystemExit(Indexable())",
        status: 1,
        stderr_contains: "Indexable object at",
    },
    Case {
        source: c"raise SystemExit('boom')",
        status: 1,
        stderr_contains: "boom\n",
    },
    Case {
        source: c"raise SystemExit([1, 2])",
        status: 1,
        stderr_contains: "[1, 2]\n",
    },
    Case {
        source: c"raise SystemExit(1.5)",
        status: 1,
        stderr_contains: "1.5\n",
    },
];

pub const ERROR_CASES: &[Case] = &[
    silent(
        c"class NoCode(SystemExit):
    def __getattribute__(self, name):
        if name == 'code': raise RuntimeError('missing code')
        return super().__getattribute__(name)
raise NoCode(7)",
        1,
    ),
    silent(
        c"class BadString:
    def __str__(self): raise RuntimeError('cannot stringify')
raise SystemExit(BadString())",
        1,
    ),
    silent(
        c"class SurrogateString:
    def __str__(self): return '\\ud800'
raise SystemExit(SurrogateString())",
        1,
    ),
    Case {
        source: c"_alive = [True]
class TrackedCode:
    def __str__(self): return 'alive' if _alive[0] else 'released'
class TrackedExit(SystemExit):
    def __del__(self): _alive[0] = False
raise TrackedExit(TrackedCode())",
        status: 1,
        stderr_contains: "alive\n",
    },
];

pub const CAPTURE_STDERR: &CStr = c"
import sys
assert sys.flags.isolated == 1
assert sys.flags.ignore_environment == 1
assert sys.flags.no_user_site == 1
assert sys.flags.no_site == 1
assert sys.flags.dont_write_bytecode == 1
assert getattr(sys.flags, 'safe_path', True)
assert sys.argv == ['aws-python-exit-harness']

class _Capture:
    def __init__(self):
        self.chunks = []

    def write(self, text):
        self.chunks.append(text)
        return len(text)

    def flush(self):
        pass

    def take(self):
        text = ''.join(self.chunks)
        self.chunks.clear()
        return text

sys.stderr = _Capture()
";
