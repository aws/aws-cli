#!/usr/bin/env python3
"""Pack the embedded AWS CLI v2 fallback artifacts.

This step deliberately does not build CPython. It consumes an interpreter
prefix (--python-root), such as the one deps/scripts/build_cpython.py
installs, so a payload or runtime bootstrap change reuses the interpreter.
Separate archive, payload, and runtime commands let xtask cache their outputs
independently.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from build_environ import network_environ, tool_environ
from build_guard import guard
from native_target import require_native_target

VENV_DEPS_REVISION = "3"
AWSCRT_SOURCE_FILES_MAX = 1024


def awscrt_c_sources(
    source_dir: Path,
    *,
    entry_limit: int = AWSCRT_SOURCE_FILES_MAX,
) -> list[Path]:
    """Every C source of the pinned aws-crt-python checkout.

    Upstream's setup.py compiles glob('source/*.c') with no platform
    subdirectories, so the checkout itself is the source list; sorting
    keeps compile order deterministic.
    """
    sources = []
    for count, path in enumerate(source_dir.iterdir(), 1):
        if count >= entry_limit:
            raise SystemExit(
                f"more than {entry_limit} entries in {source_dir}"
            )
        if path.suffix == ".c" and path.is_file() and not path.is_symlink():
            sources.append(path)
    sources.sort()
    if source_dir / "module.c" not in sources:
        raise SystemExit(
            f"{source_dir} does not look like aws-crt-python's source/ "
            f"directory: module.c is missing from its "
            f"{len(sources)} .c files"
        )
    return sources


def run(
    args: list[str],
    *,
    env: dict[str, str],
    cwd: Path | None = None,
    stdout: int | None = None,
) -> subprocess.CompletedProcess[bytes]:
    stdout_target = subprocess.PIPE if stdout is None else stdout
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            env=env,
            stdout=stdout_target,
            stderr=subprocess.PIPE,
            check=True,
        )
    except subprocess.CalledProcessError as err:
        if err.stdout:
            sys.stdout.buffer.write(err.stdout)
        if err.stderr:
            sys.stderr.buffer.write(err.stderr)
        raise


def output(args: list[str], env: dict[str, str]) -> str:
    result = run(args, env=env, stdout=subprocess.PIPE)
    return result.stdout.decode("utf-8").strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def is_macos_target(target_triple: str) -> bool:
    return target_triple.startswith(("aarch64-macos", "x86_64-macos"))


def is_linux_musl_target(target_triple: str) -> bool:
    return target_triple.startswith(
        (
            "x86_64-linux",
            "x86_64-unknown-linux",
            "aarch64-linux",
            "aarch64-unknown-linux",
        )
    ) and target_triple.endswith("-musl")


def require_supported_target(target_triple: str) -> None:
    require_native_target(target_triple)
    if (
        is_linux_musl_target(target_triple)
        or is_macos_target(target_triple)
        or target_triple in ("x86_64-windows-msvc", "x86_64-pc-windows-msvc")
    ):
        return
    raise SystemExit(
        "Python fallback generation supports x86_64-linux-musl and native macOS"
    )


def can_run_python(python: Path, env: dict[str, str]) -> bool:
    try:
        run([str(python), "-c", "import sys; sys.exit(0)"], env=env)
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def ensure_host_python(
    python_root: Path,
    python_abi: str,
    env: dict[str, str],
) -> Path:
    target_python = (
        python_root
        / "bin"
        / f"{python_abi}{'.exe' if sys.platform == 'win32' else ''}"
    )
    if can_run_python(target_python, env):
        return target_python

    host = f"{platform.system()} {platform.machine()}"
    raise SystemExit(
        "target python interpreter is not runnable on this "
        f"host ({host}); add a host-python build for this platform"
    )


def validate_aws_cli_source(source: Path, expected_version: str) -> Path:
    init_py = source / "awscli" / "__init__.py"
    text = init_py.read_text()
    if f"__version__ = '{expected_version}'" not in text:
        raise SystemExit(f"{source} is not AWS CLI v2 {expected_version}")
    return source


def filter_runtime_requirements(source: Path, destination: Path) -> Path:
    """Retain upstream pins and hashes, excluding our built/stubbed modules.

    pip-compile writes one unindented requirement followed by its hashes
    and comments. Drop the entire stanza so no orphan hashes survive.
    The source digest makes any lock update invalidate the venv marker.
    """
    excluded = {"awscrt", "ruamel-yaml-clib"}
    found: set[str] = set()
    retained = [f"# Source lock SHA256: {sha256(source)}\n"]
    skip = False
    for line in source.read_text(encoding="utf-8").splitlines(keepends=True):
        if line and not line[0].isspace() and not line.startswith("#"):
            match = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)==", line)
            if match is None:
                raise SystemExit(f"unsupported runtime lock entry: {line!r}")
            name = re.sub(r"[-_.]+", "-", match[1]).lower()
            skip = name in excluded
            if skip:
                found.add(name)
        if not skip:
            retained.append(line)
    missing = excluded - found
    if missing:
        raise SystemExit(
            f"{source} is missing excluded requirements: {sorted(missing)}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("".join(retained), encoding="utf-8")
    return destination


def validate_awscrt_source(source: Path, expected_version: str) -> Path:
    """Check the checkout is aws-crt-python at the pinned version.

    Upstream stamps the real version into awscrt/__init__.py only when
    releasing; a git checkout carries a ".dev0" placeholder. When the
    placeholder is present the version is guaranteed by the commit pin
    instead: the source manifest pins the commit and archive SHA256.
    """
    init_py = source / "awscrt" / "__init__.py"
    module_c = source / "source" / "module.c"
    missing = [path for path in (init_py, module_c) if not path.is_file()]
    if missing:
        raise SystemExit(
            f"{source} is not an aws-crt-python checkout: missing {missing}"
        )
    match = re.search(
        r"^__version__ = '([^']+)'", init_py.read_text(), re.MULTILINE
    )
    if match is None:
        raise SystemExit(f"{init_py} has no __version__ line")
    found = match.group(1)
    if not found.endswith(".dev0") and found != expected_version:
        raise SystemExit(
            f"{source} is aws-crt-python {found}, expected {expected_version}"
        )
    return source


def site_packages(python: Path, env: dict[str, str]) -> Path:
    purelib = output(
        [
            str(python),
            "-c",
            "import sysconfig; print(sysconfig.get_paths()['purelib'])",
        ],
        env,
    )
    return Path(purelib)


def python_version_id(python: Path, env: dict[str, str]) -> str:
    return output(
        [
            str(python),
            "-c",
            (
                "import sys; print(f'{sys.implementation.name} "
                "{sys.version_info.major}.{sys.version_info.minor}."
                "{sys.version_info.micro}')"
            ),
        ],
        env,
    )


def pythonpath_env(env: dict[str, str], path: Path) -> dict[str, str]:
    """`env` with `path` ahead of any PYTHONPATH it already carries."""
    pip_env = dict(env)
    existing = env.get("PYTHONPATH")
    pip_env["PYTHONPATH"] = (
        f"{path}{os.pathsep}{existing}" if existing else str(path)
    )
    return pip_env


def ensure_venv(
    host_python: Path,
    cache_dir: Path,
    requirements: Path,
    stubs_dir: Path,
    env: dict[str, str],
) -> Path:
    venv_dir = cache_dir / "venv"
    marker = venv_dir / ".zippy-deps-version"
    python = (
        venv_dir / "Scripts" / "python.exe"
        if sys.platform == "win32"
        else venv_dir / "bin" / "python"
    )
    marker_text = (
        f"{VENV_DEPS_REVISION}\n"
        f"{sha256(requirements)}\n"
        f"{python_version_id(host_python, env)}\n"
        # The venv's home is this interpreter; a reused cache directory must
        # not keep packing against a previous interpreter build.
        f"{host_python.resolve()}\n"
    )
    if (
        python.exists()
        and marker.exists()
        and marker.read_text() == marker_text
    ):
        return python
    if venv_dir.exists():
        shutil.rmtree(venv_dir)

    run(
        [str(host_python), "-m", "venv", "--without-pip", str(venv_dir)],
        env=env,
    )
    # pip alone reaches the network, so it alone sees the proxy and index
    # settings; the stubs shadow the extensions the static interpreter
    # cannot load while it runs.
    pip_env = pythonpath_env(env | network_environ(), stubs_dir)
    run(
        [
            str(python),
            "-m",
            "ensurepip",
            "--upgrade",
            "--default-pip",
        ],
        env=pip_env,
    )
    command = [
        str(python),
        "-m",
        "pip",
        "install",
        "--quiet",
        "--disable-pip-version-check",
        "--no-cache-dir",
        "--only-binary=:all:",
        "--require-hashes",
        "--requirement",
        str(requirements),
    ]
    run(command, env=pip_env)
    marker.write_text(marker_text)
    return python


def create_stubs(stubs_dir: Path, target_triple: str) -> None:
    if stubs_dir.exists():
        shutil.rmtree(stubs_dir)

    ruamel_dir = stubs_dir / "ruamel"
    ruamel_dir.mkdir(parents=True, exist_ok=True)
    (ruamel_dir / "__init__.py").write_text("")
    (stubs_dir / "_ruamel_yaml.py").write_text(
        '"""Stub for the optional ruamel.yaml C extension."""\n\n'
        "def __getattr__(name):\n"
        '    if name.startswith("__") and name.endswith("__"):\n'
        "        raise AttributeError(name)\n"
        "    raise ModuleNotFoundError(\n"
        '        f"_ruamel_yaml.{name} not available in this static build"\n'
        "    )\n"
    )
    if not is_linux_musl_target(target_triple):
        return

    ctypes_dir = stubs_dir / "ctypes"
    ctypes_dir.mkdir(parents=True, exist_ok=True)
    (ctypes_dir / "__init__.py").write_text(
        '"""Static-musl stub for stdlib ctypes dynamic loading."""\n\n'
        "class CDLL:\n"
        "    def __init__(self, name: object) -> None:\n"
        "        raise OSError('ctypes dynamic loading is not available')\n\n"
        "class _Shell32:\n"
        "    def IsUserAnAdmin(self):\n"
        "        return False\n\n"
        "class _Windll:\n"
        "    shell32 = _Shell32()\n\n"
        "windll = _Windll()\n\n"
        "def __getattr__(name):\n"
        '    if name.startswith("__") and name.endswith("__"):\n'
        "        raise AttributeError(name)\n"
        "    raise ImportError(\n"
        "        f'ctypes.{name} is not available in this static build'\n"
        "    )\n"
    )
    colorama_dir = stubs_dir / "colorama"
    colorama_dir.mkdir(parents=True, exist_ok=True)
    (colorama_dir / "win32.py").write_text(
        '"""Linux static-build stub for colorama.win32."""\n\n'
        "STDOUT = -11\n"
        "STDERR = -12\n"
        "ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004\n"
        "windll = None\n\n"
        "class COORD:\n"
        "    def __init__(self, x=0, y=0):\n"
        "        self.X = x\n"
        "        self.Y = y\n\n"
        "class _ScreenBufferInfo:\n"
        "    def __init__(self):\n"
        "        self.wAttributes = 0\n"
        "        self.dwSize = COORD()\n"
        "        self.dwCursorPosition = COORD()\n\n"
        "def winapi_test():\n"
        "    return False\n\n"
        "def GetConsoleScreenBufferInfo(_stream_id=STDOUT):\n"
        "    return _ScreenBufferInfo()\n\n"
        "def SetConsoleTextAttribute(*_args):\n"
        "    return None\n\n"
        "def SetConsoleCursorPosition(*_args, **_kwargs):\n"
        "    return None\n\n"
        "def FillConsoleOutputCharacter(*_args):\n"
        "    return 0\n\n"
        "def FillConsoleOutputAttribute(*_args):\n"
        "    return None\n\n"
        "def SetConsoleTitle(_title):\n"
        "    return None\n\n"
        "def GetConsoleMode(_handle):\n"
        "    return 0\n\n"
        "def SetConsoleMode(_handle, _mode):\n"
        "    return None\n"
    )


def generate_python_sources(
    host_python: Path,
    gen_inittab: Path,
    gen_frozen_bootstrap: Path,
    python_root: Path,
    inittab_c: Path,
    frozen_bootstrap_c: Path,
    objects_txt: Path,
    libs_txt: Path,
    env: dict[str, str],
) -> None:
    inittab_c.parent.mkdir(parents=True, exist_ok=True)
    frozen_bootstrap_c.parent.mkdir(parents=True, exist_ok=True)
    objects_txt.parent.mkdir(parents=True, exist_ok=True)
    libs_txt.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            str(host_python),
            str(gen_inittab),
            str(python_root),
            str(inittab_c),
            str(objects_txt),
            str(libs_txt),
        ],
        env=env,
    )
    run(
        [
            str(host_python),
            str(gen_frozen_bootstrap),
            str(python_root),
            str(frozen_bootstrap_c),
        ],
        env=env,
    )


def generate_autocomplete_index(
    venv_python: Path,
    gen_ac_index: Path,
    aws_cli_src: Path,
    awscrt_python: Path,
    output_root: Path,
    env: dict[str, str],
) -> None:
    """Write the autocomplete index entries the payload packs.

    `awscrt_python` is the directory holding the `awscrt` package. The
    generator runs under the venv, whose site-packages hold the remaining
    dependencies.
    """
    run(
        [
            str(venv_python),
            str(gen_ac_index),
            "--output-root",
            str(output_root),
            "--python-path",
            str(aws_cli_src),
            "--python-path",
            str(awscrt_python),
        ],
        env=env,
    )


def pack_blob(
    host_python: Path,
    pack_tool: Path,
    python_root: Path,
    python_abi: str,
    aws_cli_src: Path,
    awscrt_src: Path,
    venv_python: Path,
    stubs_dir: Path,
    autocomplete_index: Path,
    blob: Path,
    env: dict[str, str],
) -> None:
    blob.parent.mkdir(parents=True, exist_ok=True)
    stdlib = (
        python_root / "bin" / "Lib"
        if sys.platform == "win32"
        else python_root / "lib" / python_abi
    )
    # Only the producer knows the source/cache/dependency/tool roots in
    # sysconfig. Its payload-only copies must win over the real metadata
    # that the packing interpreter and its venv/pip still use unchanged.
    sysconfig = python_root / "lib" / "payload-sysconfig"
    if not sysconfig.is_dir():
        raise SystemExit(f"missing CPython payload sysconfig: {sysconfig}")
    run(
        [
            str(host_python),
            str(pack_tool),
            str(blob),
            f"{stubs_dir}:",
            f"{sysconfig}:",
            f"{stdlib}:",
            f"{aws_cli_src / 'awscli'}:awscli",
            f"{autocomplete_index}:",
            f"{awscrt_src / 'awscrt'}:awscrt",
            f"{site_packages(venv_python, env)}:",
        ],
        env=env,
    )


def compile_runtime_bytecode(
    host_python: Path,
    runtime_source: Path,
    runtime_bytecode: Path,
    env: dict[str, str],
) -> None:
    runtime_bytecode.parent.mkdir(parents=True, exist_ok=True)
    script = (
        "import marshal, pathlib, sys\n"
        "source = pathlib.Path(sys.argv[1])\n"
        "output = pathlib.Path(sys.argv[2])\n"
        "code = compile(source.read_bytes(), 'src/' + source.name, 'exec', "
        "dont_inherit=True, optimize=2)\n"
        "output.write_bytes(marshal.dumps(code))\n"
    )
    run(
        [
            str(host_python),
            "-c",
            script,
            str(runtime_source),
            str(runtime_bytecode),
        ],
        env=env,
    )


def write_bytecode_metadata(
    host_python: Path,
    blob: Path,
    runtime_bytecode: Path,
    metadata: Path,
    python_config: Path,
    env: dict[str, str],
) -> None:
    script = (
        "import hashlib, importlib.util, json, pathlib, sys\n"
        "blob, runtime, metadata, config = map(pathlib.Path, sys.argv[1:])\n"
        "digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()\n"
        "values = {\n"
        "    'implementation': sys.implementation.name,\n"
        "    'cache_tag': sys.implementation.cache_tag,\n"
        "    'magic_number': importlib.util.MAGIC_NUMBER.hex(),\n"
        "    'payload_sha256': digest(blob),\n"
        "    'runtime_sha256': digest(runtime),\n"
        "}\n"
        "metadata.write_text(json.dumps(values, indent=2, sort_keys=True) + '\\n')\n"
        "magic = int.from_bytes(importlib.util.MAGIC_NUMBER, 'little')\n"
        "config.write_text(\n"
        "    '// Generated by '\n"
        "    'deps/scripts/prepare_python_fallback.py; do not edit.\\n'\n"
        "    'pub const DYNAMIC: bool = false;\\n'\n"
        "    'pub const EMBEDDED_PAYLOAD: bool = true;\\n'\n"
        "    'pub const EXECUTABLE: &str = \\\"\\\";\\n'\n"
        "    'pub const PLATLIB: &str = \\\"\\\";\\n'\n"
        "    f'pub const BYTECODE_MAGIC: u32 = {magic};\\n'\n"
        ")\n"
    )
    metadata.parent.mkdir(parents=True, exist_ok=True)
    python_config.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            str(host_python),
            "-c",
            script,
            str(blob),
            str(runtime_bytecode),
            str(metadata),
            str(python_config),
        ],
        env=env,
    )


def compile_awscrt_sources(
    cc: str,
    target_triple: str,
    python_include: Path,
    crt_include: Path,
    awscrt_src: Path,
    object_dir: Path,
    sdk_path: str | None,
    env: dict[str, str],
) -> list[Path]:
    source_dir = awscrt_src / "source"
    object_dir.mkdir(parents=True, exist_ok=True)
    objects: list[Path] = []
    target_args: list[str] = []
    for root, logical in (
        (awscrt_src, "aws-crt-python"),
        (object_dir, "aws-crt-python-build"),
        (python_include, "cpython/include"),
        (crt_include, "crt/include"),
    ):
        # Clang can encounter either separator spelling on Windows.
        for prefix in dict.fromkeys(
            (f"{root}{os.sep}", f"{root.as_posix()}/")
        ):
            target_args.append(f"-ffile-prefix-map={prefix}={logical}/")
    if target_triple.endswith("linux-gnu"):
        # Distro GCC need not enable PIE by default; these objects are linked
        # into the system-mode PIE executable alongside shared libpython.
        target_args.append("-fPIC")
    if target_triple in ("x86_64-windows-msvc", "x86_64-pc-windows-msvc"):
        target_args.extend(
            [
                "--driver-mode=gcc",
                "-fms-runtime-lib=static",
                "-DPy_NO_ENABLE_SHARED",
            ]
        )
    if is_macos_target(target_triple):
        if sdk_path is None:
            raise SystemExit("--sdk-path is required for macOS awscrt builds")
        target_args.extend(
            [
                "-isysroot",
                sdk_path,
                "-isystem",
                str(Path(sdk_path) / "usr" / "include"),
                "-iframework",
                str(Path(sdk_path) / "System" / "Library" / "Frameworks"),
            ]
        )
    for source in awscrt_c_sources(source_dir):
        obj = object_dir / f"{source.name}.o"
        run(
            [
                cc,
                *target_args,
                "-O2",
                "-I",
                str(python_include),
                "-I",
                str(crt_include),
                # The checkout's own headers stay on the quoted-include path
                # only: it ships a source/io.h, and Windows' pyconfig.h
                # includes the C runtime's <io.h>.
                "-iquote",
                str(source_dir),
                "-Wno-strict-aliasing",
                "-std=gnu99",
                "-DAWS_USE_DEFAULT_HASHTABLE_HASH",
                "-DNDEBUG",
                "-fno-sanitize=undefined",
                "-ffunction-sections",
                "-fdata-sections",
                "-c",
                str(source),
                "-o",
                str(obj),
            ],
            env=env,
        )
        objects.append(obj)
    return objects


def read_lines(path: Path) -> list[str]:
    return [
        line.strip() for line in path.read_text().splitlines() if line.strip()
    ]


def combine_archive(
    ar: str,
    ranlib: str,
    objects: list[str],
    libraries: list[str],
    output_file: Path,
    env: dict[str, str],
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":
        run(
            [
                "/usr/bin/xcrun",
                "libtool",
                "-static",
                "-o",
                str(output_file),
                *objects,
                *libraries,
            ],
            env=env,
        )
        return
    script_lines = [f"CREATE {output_file}"]
    script_lines.extend(f"ADDMOD {obj}" for obj in objects)
    script_lines.extend(f"ADDLIB {lib}" for lib in libraries)
    script_lines.extend(["SAVE", "END", ""])
    subprocess.run(
        [ar, "-M"],
        input="\n".join(script_lines).encode("utf-8"),
        env=env,
        check=True,
    )
    run([ranlib, str(output_file)], env=env)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    for tool in ("cc", "ar", "ranlib"):
        parser.add_argument(f"--{tool}", required=True)
    parser.add_argument("--target-triple", required=True)
    parser.add_argument("--sdk-path")
    parser.add_argument("--msvc-environ", type=Path)
    parser.add_argument(
        "--python-root",
        required=True,
        help="install prefix of the project-built CPython interpreter",
    )
    parser.add_argument(
        "--python-abi",
        required=True,
        help="ABI name of the packed CPython (e.g. python3.14)",
    )
    phases = parser.add_subparsers(dest="phase", required=True)
    archive = phases.add_parser("archive")
    payload = phases.add_parser("payload")
    runtime = phases.add_parser("runtime")
    for phase in (archive, payload):
        phase.add_argument("--cache-dir", required=True)
        phase.add_argument("--awscrt-version", required=True)
        phase.add_argument("--awscrt-source", required=True)
    archive.add_argument("--crt-include-dir", required=True)
    archive.add_argument("--gen-inittab", required=True)
    archive.add_argument("--gen-frozen-bootstrap", required=True)
    archive.add_argument("--inittab", required=True)
    archive.add_argument("--frozen-bootstrap", required=True)
    archive.add_argument("--object-file", required=True)
    payload.add_argument("--aws-cli-version", required=True)
    payload.add_argument("--aws-cli-source", required=True)
    payload.add_argument("--pack-tool", required=True)
    payload.add_argument("--requirements", required=True)
    payload.add_argument("--gen-ac-index", required=True)
    payload.add_argument("--blob", required=True)
    runtime.add_argument("--blob", required=True)
    runtime.add_argument("--runtime-source", required=True)
    runtime.add_argument("--runtime-bytecode", required=True)
    runtime.add_argument("--metadata", required=True)
    runtime.add_argument("--python-config", required=True)
    return parser.parse_args()


def prepare_payload(
    args: argparse.Namespace, host_python: Path, env: dict[str, str]
) -> None:
    guard("python-fallback-pack")
    cache_dir = Path(args.cache_dir)
    aws_cli_src = validate_aws_cli_source(
        Path(args.aws_cli_source), args.aws_cli_version
    )
    awscrt_src = validate_awscrt_source(
        Path(args.awscrt_source), args.awscrt_version
    )
    stubs_dir = cache_dir / "stubs"
    create_stubs(stubs_dir, args.target_triple)
    venv_python = ensure_venv(
        host_python,
        cache_dir,
        filter_runtime_requirements(
            Path(args.requirements), cache_dir / "runtime-requirements.txt"
        ),
        stubs_dir,
        env,
    )
    autocomplete_index = cache_dir / "generated" / "autocomplete-index"
    generate_autocomplete_index(
        venv_python,
        Path(args.gen_ac_index),
        aws_cli_src,
        awscrt_src,
        autocomplete_index,
        env,
    )
    pack_blob(
        host_python,
        Path(args.pack_tool),
        Path(args.python_root),
        args.python_abi,
        aws_cli_src,
        awscrt_src,
        venv_python,
        stubs_dir,
        autocomplete_index,
        Path(args.blob),
        env,
    )


def prepare_archive(
    args: argparse.Namespace, host_python: Path, env: dict[str, str]
) -> None:
    guard("python-fallback-archive")
    cache_dir = Path(args.cache_dir)
    generated_dir = cache_dir / "generated"
    python_root = Path(args.python_root)
    awscrt_src = validate_awscrt_source(
        Path(args.awscrt_source), args.awscrt_version
    )
    objects_txt = generated_dir / "objects.txt"
    libs_txt = generated_dir / "libs.txt"
    generate_python_sources(
        host_python,
        Path(args.gen_inittab),
        Path(args.gen_frozen_bootstrap),
        python_root,
        Path(args.inittab),
        Path(args.frozen_bootstrap),
        objects_txt,
        libs_txt,
        env,
    )
    awscrt_objects = compile_awscrt_sources(
        args.cc,
        args.target_triple,
        python_root / "include" / args.python_abi,
        Path(args.crt_include_dir),
        awscrt_src,
        generated_dir / "awscrt-objects",
        args.sdk_path,
        env,
    )
    combine_archive(
        args.ar,
        args.ranlib,
        read_lines(objects_txt) + [str(path) for path in awscrt_objects],
        read_lines(libs_txt),
        Path(args.object_file),
        env,
    )


def main() -> None:
    args = parse_args()
    require_supported_target(args.target_triple)
    # Compilers and SDK paths are explicit inputs to the cached stages.
    env = tool_environ(msvc_environ=args.msvc_environ)
    if args.sdk_path:
        env["SDKROOT"] = args.sdk_path
    host_python = ensure_host_python(
        Path(args.python_root), args.python_abi, env
    )
    if args.phase == "archive":
        prepare_archive(args, host_python, env)
    elif args.phase == "payload":
        prepare_payload(args, host_python, env)
    else:
        compile_runtime_bytecode(
            host_python,
            Path(args.runtime_source),
            Path(args.runtime_bytecode),
            env,
        )
        write_bytecode_metadata(
            host_python,
            Path(args.blob),
            Path(args.runtime_bytecode),
            Path(args.metadata),
            Path(args.python_config),
            env,
        )


if __name__ == "__main__":
    main()
