#!/usr/bin/env python3
"""Build a static CPython for x86_64-windows-msvc with native Clang.

CPython has no autoconf build on Windows: the Windows build is an MSBuild
solution under `PCbuild`, and it produces `python3xx.dll`, never a static
interpreter. This module compiles the source set that solution describes,
with native Clang, into one static archive plus a runnable `python.exe`.

The source lists come from the `.vcxproj` files instead of being duplicated
here, so a CPython upgrade brings its own file list along. Three projects
matter:

- `pythoncore.vcxproj` is the interpreter core and its builtin modules.
- `_freeze_module.vcxproj` is that core minus those modules, plus the freeze
  tool. It already builds as a static console program with
  `Py_NO_ENABLE_SHARED`, which is the switch `PC/pyconfig.h` reads to select
  a non-DLL interpreter.
- One project per stdlib extension module.

`Python/frozen_modules/*.h` is generated rather than shipped, so the freeze
tool is built first and run over the module list its own project carries.

Every stdlib extension is compiled into the archive and registered in a
generated `config.c`. That is what the embedding pipeline expects from this
interpreter on every target: a static libpython with no `lib-dynload` and no
`.pyd` files. The third-party libraries those extensions need come from the
CRT and python-deps install prefixes, never from `PCbuild`'s `externals`
tree.

`build_cpython.py` imports this module by bare name and dispatches to
`build_static_cpython` for the Windows target, so the staging helper copies
both drivers into one generated directory. `build_static_cpython` returns the
generated `config.c` because its caller exports the archive's own extension
table from it, the way the autoconf targets export CPython's.
"""

from __future__ import annotations

import concurrent.futures
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ElementTree

MSBUILD_NS = "{http://schemas.microsoft.com/developer/msbuild/2003}"

TARGET_TRIPLE = "x86_64-windows-msvc"

# Windows import libraries the interpreter and its modules need: the four
# from pythoncore.vcxproj plus the ones the extension projects below name.
SYSTEM_LIBRARIES = [
    "advapi32",
    "bcrypt",
    "crypt32",
    "iphlpapi",
    "ole32",
    "oleaut32",
    # CPython calls the POSIX spellings of the C runtime functions (open,
    # read, isatty); the Microsoft C runtime exports them from oldnames.
    "oldnames",
    "pathcch",
    "rpcrt4",
    "shlwapi",
    "user32",
    "version",
    "ws2_32",
]


class Extension:
    """A stdlib extension module compiled into the static interpreter.

    `project` names the PCbuild project whose source list is used. Sources
    outside the CPython tree are dropped: those are the bundled copies of
    third-party libraries that PCbuild builds from its `externals` tree and
    this build takes from its own dependency prefixes instead.
    """

    def __init__(
        self,
        name: str,
        *,
        project: str | None = None,
        defines: tuple[str, ...] = (),
        include_dirs: tuple[str, ...] = (),
    ) -> None:
        self.name = name
        self.project = project or name
        self.defines = defines
        self.include_dirs = include_dirs


# `pcbuild.proj` names the full extension set. Left out here: `_tkinter`
# (no Tcl/Tk), `_wmi` (C++, and only feeds platform.win32_edition()), the
# test modules, and `_decimal`, whose project takes libmpdec from PCbuild's
# `externals` tree, so `project_sources()` drops those files.
#
# `_multiprocessing` is here even though the autoconf targets disable it.
# `Lib/multiprocessing/connection.py` imports it inside a `try` that
# re-raises when `sys.platform == "win32"` and swallows the ImportError
# everywhere else, so the package is importable without the extension on
# POSIX and unimportable without it here. The AWS CLI's vendored
# `s3transfer/compat.py` imports `multiprocessing.managers` at module
# scope, which every high-level `aws s3` command reaches.
EXTENSIONS = [
    Extension("_asyncio"),
    Extension("_bz2"),
    Extension(
        "_ctypes",
        defines=("USING_MALLOC_CLOSURE_DOT_C=1", "FFI_STATIC_BUILD"),
    ),
    Extension(
        "_elementtree",
        defines=("XML_STATIC", "USE_PYEXPAT_CAPI"),
        include_dirs=("Modules/expat",),
    ),
    Extension("_hashlib"),
    Extension("_lzma", defines=("LZMA_API_STATIC",)),
    Extension("_multiprocessing"),
    Extension("_overlapped"),
    Extension("_queue"),
    Extension("_socket"),
    Extension(
        "_sqlite3",
        defines=("PY_SQLITE_HAVE_SERIALIZE", "PY_SQLITE_ENABLE_LOAD_EXTENSION"),
    ),
    Extension("_ssl"),
    Extension("_uuid"),
    Extension("_zoneinfo"),
    Extension("_zstd"),
    Extension(
        "pyexpat",
        defines=("XML_STATIC", "HAVE_EXPAT_CONFIG_H"),
        include_dirs=("Modules/expat",),
    ),
    Extension("select"),
    Extension("unicodedata"),
]


# Extension modules linked into the core are "builtin" modules, so they use
# Py_BUILD_CORE_BUILTIN where PCbuild's DLL projects use
# Py_BUILD_CORE_MODULE.
EXTENSION_DEFINES = [
    "WIN32",
    "Py_BUILD_CORE_BUILTIN",
    "Py_NO_ENABLE_SHARED",
]

FREEZE_DEFINES = ["WIN32", "Py_BUILD_CORE", "Py_NO_ENABLE_SHARED", "_CONSOLE"]

# MSVC compiler options in the project files, mapped to their Clang
# equivalents. Options with no effect on this build are dropped.
MSVC_OPTION_MAP = {
    "/arch:AVX": "-mavx",
    "/arch:AVX2": "-mavx2",
    "/arch:AVX512": "-mavx512f",
}


def file_prefix_map_flags(
    source_dir: Path,
    cache_dir: Path,
    openssl_prefix: Path,
    zlib_xz_prefix: Path,
    deps_prefix: Path | None,
) -> list[str]:
    """Keep C filenames useful without embedding build-machine roots.

    Both drivers know these roots at their build callsites. Map only those
    trees, including headers read from dependency installations, rather
    than stripping an arbitrary checkout or home directory. More specific
    roots come last because Clang uses the last matching prefix; a source
    package or dependency prefix can itself live inside the cache tree.
    """
    roots = [
        (cache_dir, "cpython-cache"),
        (cache_dir / "build", "cpython-build"),
        (source_dir, "cpython"),
        (openssl_prefix, "openssl"),
        (zlib_xz_prefix, "zlib-xz"),
    ]
    if deps_prefix is not None:
        roots.append((deps_prefix, "python-deps"))
    mappings = sorted(
        ((str(root.resolve()), stable) for root, stable in roots),
        key=lambda mapping: len(mapping[0]),
    )
    # The separator prevents a root from also matching a sibling whose
    # name merely starts with that root's name.
    return [
        f"-ffile-prefix-map={prefix}={stable}/"
        for root, stable in mappings
        for prefix in dict.fromkeys(
            (f"{root}{os.sep}", f"{Path(root).as_posix()}/")
        )
    ]


def core_defines(python_version: str) -> list[str]:
    """Defines every core translation unit gets.

    `Py_NO_ENABLE_SHARED` replaces pythoncore.vcxproj's
    `_USRDLL;Py_ENABLE_SHARED` pair and `_Py_HAVE_ZLIB` enables the zlib
    module against the archive from the CRT prefix.

    `MS_COREDLL` is what makes `sysmodule.c` publish `sys.winver` from
    `MS_DLL_ID`, and the stdlib's `site` module reads `sys.winver`
    unconditionally on Windows to build the per-user site-packages path.
    Its only other effect is an auto-link pragma that `Py_BUILD_CORE`
    already suppresses; `Py_ENABLE_SHARED`, not `MS_COREDLL`, is what would
    turn the API declarations into DLL exports.
    """
    major_minor = ".".join(python_version.split(".")[:2])
    return [
        "WIN32",
        "Py_BUILD_CORE",
        "Py_BUILD_CORE_BUILTIN",
        "Py_NO_ENABLE_SHARED",
        "MS_COREDLL",
        f'MS_DLL_ID="{major_minor}"',
        "_Py_HAVE_ZLIB",
    ]


def msbuild_properties(python_version: str) -> dict[str, str]:
    """MSBuild properties the per-file settings in pythoncore.vcxproj expand.

    `SysWinVer` reaches sys.winver; the VPATH and debug-extension values only
    matter to a build-tree layout this build never produces.
    """
    major_minor = ".".join(python_version.split(".")[:2])
    return {
        "SysWinVer": major_minor,
        "PyVPath": "",
        "PyDebugExt": "",
    }


def run(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
            errors="replace",
        )
    except subprocess.CalledProcessError as err:
        if err.stdout:
            sys.stdout.write(err.stdout)
        if err.stderr:
            sys.stderr.write(err.stderr)
        raise
    return result.stdout or ""


class Source:
    """One translation unit with the per-file settings its project gave it."""

    def __init__(
        self,
        path: Path,
        defines: tuple[str, ...] = (),
        options: tuple[str, ...] = (),
        include_dirs: tuple[str, ...] = (),
    ) -> None:
        self.path = path
        self.defines = defines
        self.options = options
        self.include_dirs = include_dirs


def expand_properties(value: str, properties: dict[str, str]) -> str:
    for name, replacement in properties.items():
        value = value.replace(f"$({name})", replacement)
    if "$(" in value:
        raise SystemExit(f"unresolved MSBuild property in project value: {value}")
    return value


def split_list(value: str | None) -> list[str]:
    if not value:
        return []
    items = []
    for item in value.replace("\n", "").split(";"):
        item = item.strip()
        if not item or item.startswith("%("):
            continue
        items.append(item)
    return items


def project_sources(
    pcbuild_dir: Path,
    source_dir: Path,
    project: str,
    properties: dict[str, str],
) -> list[Source]:
    """C sources a project compiles for x64, with their per-file settings.

    Sources that resolve outside the CPython tree are the bundled
    third-party libraries from PCbuild's `externals` tree; this build links
    its own archives instead, so they are skipped.
    """
    tree = ElementTree.parse(pcbuild_dir / f"{project}.vcxproj")
    sources: list[Source] = []
    for element in tree.iter(f"{MSBUILD_NS}ClCompile"):
        include = element.get("Include")
        if not include:
            continue
        condition = element.get("Condition")
        if condition and "x64" not in condition:
            continue
        # A property in the path names PCbuild's `externals` tree: the
        # bundled copy of a third-party library this build already has as its
        # own archive.
        if "$(" in include:
            continue
        path = Path(os.path.normpath(pcbuild_dir / include.replace("\\", "/")))
        if not path.is_relative_to(source_dir):
            continue
        defines: list[str] = []
        options: list[str] = []
        for definition in element.findall(f"{MSBUILD_NS}PreprocessorDefinitions"):
            entry_condition = definition.get("Condition")
            if entry_condition and "x64" not in entry_condition:
                continue
            defines.extend(
                expand_properties(item, properties)
                for item in split_list(definition.text)
            )
        for option in element.findall(f"{MSBUILD_NS}AdditionalOptions"):
            for item in expand_properties(option.text or "", properties).split():
                if item.startswith("%("):
                    continue
                mapped = MSVC_OPTION_MAP.get(item)
                if mapped:
                    options.append(mapped)
        if path == source_dir / "Modules" / "getpath.c":
            # Unlike POSIX, this build never runs a build-tree interpreter.
            # NULL prefixes and empty VPATH use Windows' executable/Lib
            # landmarks without embedding any physical package directory.
            defines = [
                item
                for item in defines
                if item.partition("=")[0]
                not in {"PREFIX", "EXEC_PREFIX", "VPATH"}
            ]
            defines.extend(["PREFIX=NULL", "EXEC_PREFIX=NULL", 'VPATH=""'])
        sources.append(Source(path, tuple(defines), tuple(options)))
    return sources


def frozen_modules(
    pcbuild_dir: Path,
    source_dir: Path,
) -> list[tuple[str, Path, str]]:
    """(module name, source .py, header file name) for each frozen module.

    The stdlib modules are `None` items; `Modules/getpath.py` gets its own
    `GetPath` item because the project freezes it outside the generated
    mapping.
    """
    tree = ElementTree.parse(pcbuild_dir / "_freeze_module.vcxproj")
    elements = [
        element
        for tag in ("None", "GetPath")
        for element in tree.iter(f"{MSBUILD_NS}{tag}")
    ]
    modules: list[tuple[str, Path, str]] = []
    for element in elements:
        include = element.get("Include")
        mod_name = element.findtext(f"{MSBUILD_NS}ModName")
        out_file = element.findtext(f"{MSBUILD_NS}OutFile")
        if not include or not mod_name or not out_file:
            continue
        source = Path(os.path.normpath(pcbuild_dir / include.replace("\\", "/")))
        if not source.is_relative_to(source_dir):
            continue
        header = Path(out_file.replace("\\", "/")).name
        modules.append((mod_name, source, header))
    if not modules:
        raise SystemExit("no frozen modules found in _freeze_module.vcxproj")
    return modules


def core_include_dirs(source_dir: Path) -> list[Path]:
    """Include path pyproject.props and pythoncore.vcxproj set up.

    `Python` covers the generated `frozen_modules` headers, which both
    `frozen.c` and `getpath.c` include through that directory.
    """
    return [
        source_dir / "Include",
        source_dir / "Include" / "internal",
        source_dir / "Include" / "internal" / "mimalloc",
        source_dir / "PC",
        source_dir / "Modules" / "_hacl",
        source_dir / "Modules" / "_hacl" / "include",
        source_dir / "Python",
    ]


def compile_source(
    cc: list[str],
    source: Source,
    object_path: Path,
    include_dirs: list[Path],
    defines: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> Path:
    object_path.parent.mkdir(parents=True, exist_ok=True)
    # Keep __DATE__/__TIME__ warnings from rejecting upstream metadata;
    # Modules/getbuildinfo.c puts both into sys.version on every target.
    command = [*cc, "-O2", "-fno-strict-aliasing", "-Wno-date-time"]
    for define in [*defines, *source.defines]:
        command.append(f"-D{define}")
    for directory in [*include_dirs, *source.include_dirs]:
        command.append(f"-I{directory}")
    command.extend(source.options)
    command.extend(["-c", str(source.path), "-o", str(object_path)])
    run(command, cwd=cwd, env=env)
    return object_path


def compile_all(
    cc: list[str],
    jobs: list[tuple[Source, Path, list[Path], list[str]]],
    *,
    cwd: Path,
    env: dict[str, str],
    parallelism: int,
) -> list[Path]:
    objects: list[Path] = []
    with concurrent.futures.ThreadPoolExecutor(parallelism) as pool:
        futures = [
            pool.submit(
                compile_source,
                cc,
                source,
                object_path,
                include_dirs,
                defines,
                cwd=cwd,
                env=env,
            )
            for source, object_path, include_dirs, defines in jobs
        ]
        for future in concurrent.futures.as_completed(futures):
            objects.append(future.result())
    return objects


def object_paths(objects_dir: Path, sources: list[Source]) -> list[Path]:
    """One object file per source, named so same-named sources never collide."""
    return [
        objects_dir / f"{index:04d}-{source.path.stem}.obj"
        for index, source in enumerate(sources)
    ]


def build_freeze_tool(
    cc: list[str],
    source_dir: Path,
    build_dir: Path,
    env: dict[str, str],
    parallelism: int,
    properties: dict[str, str],
) -> Path:
    """Build `_freeze_module.exe`, which generates the frozen module headers."""
    pcbuild_dir = source_dir / "PCbuild"
    objects_dir = build_dir / "freeze-objects"
    sources = project_sources(
        pcbuild_dir,
        source_dir,
        "_freeze_module",
        properties,
    )
    include_dirs = core_include_dirs(source_dir)
    compile_jobs = [
        (source, object_path, include_dirs, FREEZE_DEFINES)
        for source, object_path in zip(
            sources,
            object_paths(objects_dir, sources),
        )
    ]
    objects = compile_all(
        cc,
        compile_jobs,
        cwd=source_dir,
        env=env,
        parallelism=parallelism,
    )
    executable = build_dir / "_freeze_module.exe"
    # Deep checkouts can exceed the Windows command-line limit even with
    # the freeze tool's smaller object list.
    response = executable.with_suffix(".objects.rsp")
    response.write_text(
        "".join(f'"{obj.as_posix()}"\n' for obj in sorted(objects)),
        encoding="utf-8",
    )
    run(
        [
            *cc,
            f"@{response}",
            "-o",
            str(executable),
            *[f"-l{library}" for library in SYSTEM_LIBRARIES],
        ],
        cwd=source_dir,
        env=env,
    )
    return executable


def freeze_all(
    freeze_tool: Path,
    source_dir: Path,
    build_dir: Path,
    env: dict[str, str],
) -> None:
    """Generate the frozen module headers into the build directory.

    They land under `Python/frozen_modules` because the two consumers spell
    the include differently: `Python/frozen.c` asks for
    `frozen_modules/<name>.h` and `Modules/getpath.c` for
    `Python/frozen_modules/getpath.h`.
    """
    output_dir = build_dir / "Python" / "frozen_modules"
    output_dir.mkdir(parents=True, exist_ok=True)
    for mod_name, module_source, header in frozen_modules(
        source_dir / "PCbuild",
        source_dir,
    ):
        run(
            [
                str(freeze_tool),
                mod_name,
                str(module_source),
                str(output_dir / header),
            ],
            cwd=source_dir,
            env=env,
        )


def generate_config_c(
    source_dir: Path,
    build_dir: Path,
    extensions: list[Extension],
) -> Path:
    """`PC/config.c` with every compiled-in extension module added.

    Editing the upstream table keeps the builtin list exactly as CPython
    declares it for Windows and adds the modules this build compiles in,
    which is what an inittab for a static interpreter has to contain.
    """
    original = (source_dir / "PC" / "config.c").read_text(encoding="utf-8")
    sentinel = "    /* Sentinel */"
    if sentinel not in original:
        raise SystemExit("PC/config.c has no sentinel comment to extend")
    declarations = "".join(
        f"extern PyObject* PyInit_{extension.name}(void);\n" for extension in extensions
    )
    entries = "".join(
        f'    {{"{extension.name}", PyInit_{extension.name}}},\n'
        for extension in extensions
    )
    generated = original.replace(
        '#include "Python.h"\n',
        '#include "Python.h"\n\n'
        "/* Stdlib extension modules compiled into this static build. */\n"
        + declarations,
        1,
    ).replace(sentinel, entries + sentinel, 1)
    config_c = build_dir / "config.c"
    config_c.write_text(generated, encoding="utf-8")
    return config_c


def generate_dll_globals_c(build_dir: Path) -> Path:
    """Define the two Python-DLL globals a static interpreter still needs.

    `PC/dl_nt.c` declares `PyWin_DLLhModule` and `PyWin_DLLVersionString`
    inside `#ifdef Py_ENABLE_SHARED`, so a static build compiles that file to
    nothing. `sysmodule.c` reads both for `sys.dllhandle` and `sys.winver`.
    There is no module handle to report here, and the version string is the
    same `MS_DLL_ID` the DLL build uses.
    """
    source = build_dir / "dll_globals.c"
    source.write_text(
        '#include "Python.h"\n'
        "#include <windows.h>\n"
        "\n"
        "HMODULE PyWin_DLLhModule = NULL;\n"
        "const char *PyWin_DLLVersionString = MS_DLL_ID;\n",
        encoding="utf-8",
    )
    return source


def core_sources(
    source_dir: Path,
    config_c: Path,
    dll_globals_c: Path,
    properties: dict[str, str],
) -> list[Source]:
    """pythoncore's sources with the DLL-only and fixed-table ones replaced.

    `PC/dl_nt.c` is the DLL entry point, and `PC/config.c` carries the fixed
    builtin table that the generated one supersedes.
    """
    replaced = {
        source_dir / "PC" / "config.c",
        source_dir / "PC" / "dl_nt.c",
    }
    sources = [
        source
        for source in project_sources(
            source_dir / "PCbuild",
            source_dir,
            "pythoncore",
            properties,
        )
        if source.path not in replaced
    ]
    sources.append(Source(config_c))
    sources.append(Source(dll_globals_c))
    return sources


def extension_sources(
    source_dir: Path,
    extensions: list[Extension],
    properties: dict[str, str],
) -> list[Source]:
    """Extension sources, with each file compiled once.

    `pyexpat` and `_elementtree` both list the bundled expat sources, and one
    copy in the archive is enough.
    """
    seen: set[Path] = set()
    sources: list[Source] = []
    for extension in extensions:
        for source in project_sources(
            source_dir / "PCbuild",
            source_dir,
            extension.project,
            properties,
        ):
            if source.path in seen:
                continue
            seen.add(source.path)
            sources.append(
                Source(
                    source.path,
                    source.defines + extension.defines,
                    source.options,
                    tuple(
                        str(source_dir / directory)
                        for directory in extension.include_dirs
                    ),
                )
            )
    return sources


def create_archive(
    ar: str,
    objects: list[Path],
    archive: Path,
    *,
    cwd: Path,
    env: dict[str, str],
) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        archive.unlink()
    # The response file keeps the command line under the Windows limit: a
    # static CPython is well over three hundred objects.
    response = archive.with_suffix(".objects.rsp")
    response.write_text(
        "".join(f'"{obj.as_posix()}"\n' for obj in sorted(objects)),
        encoding="utf-8",
    )
    run(
        [ar, "rcs", str(archive), f"@{response}"],
        cwd=cwd,
        env=env,
    )


def link_interpreter(
    cc: list[str],
    source_dir: Path,
    build_dir: Path,
    archive: Path,
    include_dirs: list[Path],
    library_dirs: list[Path],
    libraries: list[str],
    defines: list[str],
    *,
    env: dict[str, str],
) -> Path:
    """Link `python.exe` from `Programs/python.c` and the static archive."""
    executable = build_dir / "python.exe"
    command = [*cc, "-O2"]
    for define in defines:
        command.append(f"-D{define}")
    for directory in include_dirs:
        command.append(f"-I{directory}")
    command.append(str(source_dir / "Programs" / "python.c"))
    command.extend(["-o", str(executable), str(archive)])
    for directory in library_dirs:
        command.append(f"-L{directory}")
    command.extend(f"-l{library}" for library in libraries)
    # Upstream's python.exe embeds `PC/python.manifest`, whose
    # `longPathAware` lets it reach paths past MAX_PATH where the host
    # enables them, as pip needs inside a venv under a deep stage prefix.
    # That manifest carries its own execution level, so the linker adds none.
    command.extend(
        [
            "-Xlinker",
            "/manifest:embed",
            "-Xlinker",
            "/manifestuac:no",
            "-Xlinker",
            f"/manifestinput:{source_dir / 'PC' / 'python.manifest'}",
        ]
    )
    run(command, cwd=source_dir, env=env)
    return executable


def build_venv_launchers(
    cc: list[str],
    source_dir: Path,
    build_dir: Path,
    python_abi: str,
    *,
    env: dict[str, str],
) -> list[tuple[Path, str]]:
    """Build the redirectors `venv` copies into a new environment's Scripts.

    `PC/venvlauncher.c` reads `pyvenv.cfg` and runs the base interpreter it
    names. `venv` fails to create a usable environment without these, and
    packing the fallback payload installs its dependencies into one.
    `EXENAME` has to name this build's interpreter rather than upstream's
    `python.exe`.
    """
    launchers: list[tuple[Path, str]] = []
    for name, subsystem in (
        ("venvlauncher", "console"),
        ("venvwlauncher", "windows"),
    ):
        executable = build_dir / f"{name}.exe"
        command = [
            *cc,
            "-O2",
            f'-DEXENAME=L"{python_abi}.exe"',
            "-DPY_ICON",
            f"-I{source_dir / 'Include'}",
            f"-I{source_dir / 'PC'}",
            str(source_dir / "PC" / "venvlauncher.c"),
            "-o",
            str(executable),
            "-Xlinker",
            f"/subsystem:{subsystem}",
            "-lpathcch",
            "-loldnames",
        ]
        if subsystem == "windows":
            # The source defines wmain, not WinMain, so name the wide
            # console startup routine the windowed variant has to use.
            # lld-link takes it as its own option, as it takes the
            # subsystem; it has no GNU `-e`.
            command.extend(["-Xlinker", "/entry:wmainCRTStartup"])
        run(command, cwd=source_dir, env=env)
        launchers.append((executable, f"{name}.exe"))
    return launchers


def install_tree(
    source_dir: Path,
    prefix: Path,
    python_abi: str,
    python_version: str,
    executable: Path,
    archive: Path,
    config_c: Path,
    venv_launchers: list[tuple[Path, str]],
) -> None:
    """Lay the build out the way the embedding pipeline reads a CPython root.

    `bin/<abi>.exe` beside `bin/Lib` is what CPython's own path resolution
    needs on Windows: it looks for `Lib\\os.py` next to the executable. The
    rest of the tree matches what deps/scripts/gen_inittab.py and
    deps/scripts/prepare_python_fallback.py read: the static archive,
    the generated inittab source under a `config-<version>` directory, an
    empty support archive directory, and the headers under `include/<abi>`.
    """
    major_minor = ".".join(python_version.split(".")[:2])
    bin_dir = prefix / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(executable, bin_dir / f"{python_abi}.exe")

    stdlib = bin_dir / "Lib"
    if stdlib.exists():
        shutil.rmtree(stdlib)
    shutil.copytree(source_dir / "Lib", stdlib)
    launcher_dir = stdlib / "venv" / "scripts" / "nt"
    launcher_dir.mkdir(parents=True, exist_ok=True)
    for launcher, name in venv_launchers:
        shutil.copy2(launcher, launcher_dir / name)

    lib_dir = prefix / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(archive, lib_dir / f"lib{python_abi}.a")
    config_dir = lib_dir / python_abi / f"config-{major_minor}"
    config_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config_c, config_dir / "config.c")
    (lib_dir / "python-support").mkdir(exist_ok=True)

    include_dir = prefix / "include" / python_abi
    if include_dir.exists():
        shutil.rmtree(include_dir)
    shutil.copytree(source_dir / "Include", include_dir)
    shutil.copy2(source_dir / "PC" / "pyconfig.h", include_dir / "pyconfig.h")


def verify_install(
    prefix: Path,
    python_abi: str,
    env: dict[str, str],
) -> None:
    """Check the installed interpreter registered every extension above.

    `verify_static_build()` in build_cpython.py runs only on the autoconf
    targets, so this is the one post-build check this target gets.
    Without it, a module missing from `EXTENSIONS` is missing from the
    generated inittab, and the interpreter still builds, links, and runs:
    the omission only surfaces as an ImportError in a user's hands.

    `multiprocessing` is imported as well because it is the package whose
    importability, not just its behavior, depends on an extension being
    registered (see the `EXTENSIONS` comment).

    `-I` keeps the caller's PYTHON* variables out of the check, including
    the PYTHONOPTIMIZE that would drop the assert, and `-B` keeps it from
    writing bytecode caches into the install prefix.
    """
    python = prefix / "bin" / f"{python_abi}.exe"
    required = ", ".join(repr(extension.name) for extension in EXTENSIONS)
    check = (
        "import sys\n"
        f"required = [{required}]\n"
        "missing = [name for name in required "
        "if name not in sys.builtin_module_names]\n"
        "assert not missing, f'not registered in the inittab: {missing}'\n"
        "import multiprocessing.managers\n"
    )
    run([str(python), "-I", "-B", "-c", check], cwd=prefix, env=env)


def build_static_cpython(
    compiler: str,
    ar: str,
    python_version: str,
    prefix: Path,
    openssl_prefix: Path,
    zlib_xz_prefix: Path,
    deps_prefix: Path,
    cache_dir: Path,
    source_dir: Path,
    env: dict[str, str],
    jobs: int,
) -> Path:
    """Build and install the static interpreter; return its `config.c`.

    The returned file is the generated extension table of the archive this
    installs, which the caller turns into the prefix's exported inittab
    source.
    """
    if sys.platform != "win32":
        raise SystemExit("the Windows CPython build only runs on Windows")
    python_abi = "python" + ".".join(python_version.split(".")[:2])
    properties = msbuild_properties(python_version)
    build_dir = cache_dir / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)

    cc = [
        compiler,
        "--driver-mode=gcc",
        "-fuse-ld=lld",
        "-fms-runtime-lib=static",
        "-gcodeview",
        *file_prefix_map_flags(
            source_dir, cache_dir, openssl_prefix, zlib_xz_prefix, deps_prefix
        ),
    ]
    # The generated frozen headers live in the build directory, so the source
    # package stays read-only: frozen.c and getpath.c reach them through
    # `frozen_modules/...` on the include path.
    include_dirs = [
        *core_include_dirs(source_dir),
        build_dir,
        build_dir / "Python",
        openssl_prefix / "include",
        zlib_xz_prefix / "include",
        deps_prefix / "include",
    ]

    freeze_tool = build_freeze_tool(
        cc,
        source_dir,
        build_dir,
        env,
        jobs,
        properties,
    )
    freeze_all(freeze_tool, source_dir, build_dir, env)

    config_c = generate_config_c(source_dir, build_dir, EXTENSIONS)
    dll_globals_c = generate_dll_globals_c(build_dir)
    objects_dir = build_dir / "objects"
    core = core_sources(source_dir, config_c, dll_globals_c, properties)
    extensions = extension_sources(source_dir, EXTENSIONS, properties)
    defines = core_defines(python_version)
    compile_jobs: list[tuple[Source, Path, list[Path], list[str]]] = [
        (source, object_path, include_dirs, defines)
        for source, object_path in zip(
            core,
            object_paths(objects_dir / "core", core),
        )
    ]
    compile_jobs.extend(
        (source, object_path, include_dirs, EXTENSION_DEFINES)
        for source, object_path in zip(
            extensions,
            object_paths(objects_dir / "extensions", extensions),
        )
    )
    objects = compile_all(
        cc,
        compile_jobs,
        cwd=source_dir,
        env=env,
        parallelism=jobs,
    )

    archive = build_dir / f"lib{python_abi}.a"
    create_archive(ar, objects, archive, cwd=source_dir, env=env)

    executable = link_interpreter(
        cc,
        source_dir,
        build_dir,
        archive,
        include_dirs,
        [openssl_prefix / "lib", zlib_xz_prefix / "lib", deps_prefix / "lib"],
        [
            "ssl",
            "crypto",
            "z",
            "lzma",
            "sqlite3",
            "bz2",
            "ffi",
            "zstd",
            *SYSTEM_LIBRARIES,
        ],
        defines,
        env=env,
    )
    venv_launchers = build_venv_launchers(
        cc,
        source_dir,
        build_dir,
        python_abi,
        env=env,
    )
    install_tree(
        source_dir,
        prefix,
        python_abi,
        python_version,
        executable,
        archive,
        config_c,
        venv_launchers,
    )
    verify_install(prefix, python_abi, env)
    return config_c
