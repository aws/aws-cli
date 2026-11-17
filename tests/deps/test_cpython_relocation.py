"""Relocation independence of the CPython builder's shipped metadata."""

import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def staged_driver(tmp_path: Path) -> Path:
    source = Path(__file__).resolve().parents[2] / "deps/scripts"
    for path in source.iterdir():
        if path.is_file():
            shutil.copy2(path, tmp_path / path.name)
    return tmp_path


def driver_eval(directory: Path, expression: str) -> object:
    result = subprocess.run(
        [
            sys.executable,
            "-E",
            "-s",
            "-B",
            "-c",
            (
                "from pathlib import Path; import json; "
                "import build_cpython as b; "
                f"print(json.dumps({expression}))"
            ),
        ],
        cwd=directory,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX configure layout")
def test_getpath_uses_stable_prefixes_and_a_real_relative_source_tree(
    staged_driver: Path,
) -> None:
    source = staged_driver / "immutable package"
    source.mkdir()
    (source / "configure").write_text("source landmark")
    cache = staged_driver / "scratch"
    build = cache / "build"
    build.mkdir(parents=True)
    driver_eval(
        staged_driver,
        f"b.prepare_source_link(Path({str(source)!r}), Path({str(cache)!r}))",
    )
    args = driver_eval(
        staged_driver,
        "b.configure_args(Path('/physical/install'), Path('/openssl'), "
        "Path('/zlib-xz'), Path('/deps'), 'x86_64-unknown-linux-musl', False)",
    )
    assert isinstance(args, list)
    assert "--prefix=/physical/install" in args
    assert "host_prefix=/aws-cli-python" in args
    assert "host_exec_prefix=/aws-cli-python" in args
    assert "--srcdir=../source" in args
    assert (build / "../source/configure").read_text() == "source landmark"
    assert (cache / "source").resolve() == source


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX build metadata")
def test_payload_root_inventory_covers_tools_and_training_outside_cache(
    staged_driver: Path,
) -> None:
    roots = driver_eval(
        staged_driver,
        "[[str(path), logical] for path, logical in "
        "b.payload_sysconfig_roots(('/toolchain/bin/cc', '/toolchain/bin/ar'), "
        "Path('/install'), Path('/package'), Path('/cache'), Path('/openssl'), "
        "Path('/zlib-xz'), Path('/deps'), Path('/tools/llvm-profdata'), "
        "Path('/runtime/profile.a'), '/SDK', Path('/training/aws-cli'), {})]",
    )
    assert isinstance(roots, list)
    mapped = dict(roots)
    assert mapped["/install"] == "/aws-cli-python"
    assert (
        mapped["/package"]
        == mapped["/cache/source"]
        == ("/aws-cli-build/cpython")
    )
    assert mapped["/cache/build"] == "/aws-cli-build/cpython-build"
    assert mapped["/openssl"] == "/aws-cli-build/openssl"
    assert mapped["/zlib-xz"] == "/aws-cli-build/zlib-xz"
    assert mapped["/deps"] == "/aws-cli-build/python-deps"
    assert mapped["/toolchain/bin"] == "/aws-cli-build/toolchain"
    assert mapped["/tools/llvm-profdata"] == (
        "/aws-cli-build/pgo/llvm-profdata"
    )
    assert mapped["/runtime/profile.a"] == (
        "/aws-cli-build/pgo/libclang_rt.profile.a"
    )
    assert mapped["/SDK"] == "/aws-cli-build/sdk"
    assert mapped["/training/aws-cli"] == "/aws-cli-build/aws-cli"
    assert mapped[str(staged_driver)] == "/aws-cli-build/cpython-driver"


@pytest.mark.parametrize("flags_api", ["build_env", "direct"])
def test_file_prefix_maps_make_native_objects_relocation_invariant(
    staged_driver: Path,
    flags_api: str,
) -> None:
    if sys.platform != "linux":
        pytest.skip("native Linux compiler check")
    clang = os.environ.get("AWS_NATIVE_TEST_CC") or shutil.which("clang")
    if clang is None:
        pytest.skip("a native compiler is required to compile the filename probe")
    compiler = staged_driver / "toolchain's bin" / "cc"
    compiler.parent.mkdir()
    compiler.write_text(f'#!/bin/sh\nexec {shlex.quote(clang)} "$@"\n')
    compiler.chmod(0o755)
    unrelated = staged_driver / "unrelated include" / "probe.h"
    unrelated.parent.mkdir()
    unrelated.write_text("const char *unrelated_file = __FILE__;\n")
    objects: list[bytes] = []
    for checkout in ("checkout-a", "checkout-b"):
        cache = staged_driver / checkout / "cache root's tree"
        source = cache / "packages" / "cpython"
        openssl = cache / "outputs" / "openssl"
        zlib_xz = cache / "outputs" / "zlib-xz"
        deps = cache / "outputs" / "python deps"
        build = cache / "build"
        headers = {
            "source_header": source / "Include" / "probe.h",
            "generated": build / "Modules" / "config.c",
            "cache": cache / "scratch" / "probe.h",
            "openssl": openssl / "include" / "probe.h",
            "zlib_xz": zlib_xz / "include" / "probe.h",
            "deps": deps / "include" / "probe.h",
            "sibling": source.with_name("cpython-other") / "probe.h",
        }
        for name, header in headers.items():
            header.parent.mkdir(parents=True, exist_ok=True)
            header.write_text(f"const char *{name}_file = __FILE__;\n")
        translation_unit = source / "Python" / "probe.c"
        translation_unit.parent.mkdir()
        translation_unit.write_text(
            "".join(
                f'#include "{header}"\n'
                for header in [*headers.values(), unrelated]
            )
            + "const char *source_file = __FILE__;\n"
            + "const char *base_file = __BASE_FILE__;\n"
            + 'const char *build_date = __DATE__ " " __TIME__;\n'
        )
        roots = (
            f"Path({str(source)!r}), Path({str(cache)!r}), "
            f"Path({str(openssl)!r}), Path({str(zlib_xz)!r}), "
            f"Path({str(deps)!r})"
        )
        env = driver_eval(
            staged_driver,
            f"b.build_env({str(compiler)!r}, 'ar', 'ranlib', 'ld', "
            f"'{platform.machine()}-unknown-linux-musl', "
            f"Path({str(openssl)!r}), Path({str(zlib_xz)!r}), "
            f"Path({str(deps)!r}), None, "
            f"source_dir=Path({str(source)!r}), "
            f"cache_dir=Path({str(cache)!r}))",
        )
        assert isinstance(env, dict)
        object_path = build / "probe.o"
        # DWARF 5 line tables checksum file contents, and this probe's
        # contents name its absolute include paths; real sources do not.
        compile_args = [
            "-gdwarf-4",
            "-Wno-error=date-time",
            "-c",
            str(translation_unit),
            "-o",
            str(object_path),
        ]
        if flags_api == "build_env":
            assert "-Wno-error=date-time" in shlex.split(env["CFLAGS"])
            command = [
                "/bin/sh",
                "-c",
                f"{env['CC']} {env['CFLAGS']} {shlex.join(compile_args)}",
            ]
        else:
            flags = driver_eval(
                staged_driver,
                f"b.build_cpython_windows.file_prefix_map_flags({roots})",
            )
            assert isinstance(flags, list)
            command = [str(compiler), *flags, *compile_args]
        subprocess.run(command, cwd=build, env=env, check=True)
        data = object_path.read_bytes()
        assert b"Jan  1 2000 00:00:00\0" in data
        for filename in (
            "cpython/Python/probe.c",
            "cpython/Include/probe.h",
            "cpython-build/Modules/config.c",
            "cpython-cache/scratch/probe.h",
            "openssl/include/probe.h",
            "zlib-xz/include/probe.h",
            "python-deps/include/probe.h",
            "cpython-cache/packages/cpython-other/probe.h",
        ):
            assert filename.encode() + b"\0" in data
        assert str(unrelated).encode() + b"\0" in data
        assert str(cache).encode() not in data
        objects.append(data)
    assert objects[0] == objects[1]


def test_is_built_requires_payload_sysconfig_and_current_revision(
    staged_driver: Path,
) -> None:
    prefix = staged_driver / "install"
    (prefix / "lib").mkdir(parents=True)
    (prefix / "bin").mkdir()
    suffix = ".exe" if sys.platform == "win32" else ""
    for filename in (
        "lib/libpython3.14.a",
        "lib/python3.14-inittab.c",
        f"bin/python3.14{suffix}",
    ):
        (prefix / filename).touch()
    target = "x86_64-pc-windows-msvc" if sys.platform == "win32" else (
        "x86_64-unknown-linux-musl"
    )
    arguments = f"Path('/python'), {target!r}, 'clang 21', False, None, None"
    stamp = driver_eval(staged_driver, f"b.stamp_text({arguments})")
    assert isinstance(stamp, str)
    stamp_path = prefix / ".cpython-build-version"
    (prefix / "lib/payload-sysconfig").mkdir()
    stamp_path.write_text("35\n" + stamp.partition("\n")[2])
    expression = (
        f"b.is_built(Path({str(prefix)!r}), 'python3.14', {arguments})"
    )
    assert not driver_eval(staged_driver, expression)
    stamp_path.write_text(stamp)
    assert driver_eval(staged_driver, expression)
    (prefix / "lib/payload-sysconfig").rmdir()
    assert not driver_eval(staged_driver, expression)
