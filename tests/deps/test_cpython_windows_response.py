import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(
    sys.platform != "win32" or platform.machine().lower() != "amd64",
    reason="requires a native x86-64 Windows toolchain",
)
def test_freeze_tool_links_beyond_windows_command_line_limit(
    tmp_path: Path,
) -> None:
    clang = shutil.which("clang")
    assert clang is not None, "native Clang and the MSVC SDK must be available"
    compiler_target = subprocess.run(
        [clang, "-print-target-triple"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert compiler_target.startswith("x86_64-")
    assert "-windows-msvc" in compiler_target
    root = Path(__file__).resolve().parents[2]
    shutil.copy2(root / "deps/scripts/build_cpython_windows.py", tmp_path)
    padding = "x" * max(0, 160 - len(str(tmp_path)))
    checkout = tmp_path / f"checkout with spaces {padding}"
    source_dir = checkout / "python source"
    project_dir = source_dir / "PCbuild"
    project_dir.mkdir(parents=True)
    build_dir = checkout / "build output"

    declarations = "".join(
        f"int unit_{index}(void);\n" for index in range(1, 170)
    )
    calls = " + ".join(f"unit_{index}()" for index in range(1, 170))
    (source_dir / "unit_0.c").write_text(
        f"{declarations}int main(void) {{ return {calls} - 14365; }}\n",
        encoding="utf-8",
    )
    for index in range(1, 170):
        (source_dir / f"unit_{index}.c").write_text(
            f"int unit_{index}(void) {{ return {index}; }}\n",
            encoding="utf-8",
        )
    sources = "".join(
        f'<ClCompile Include="../unit_{index}.c" />\n' for index in range(170)
    )
    (project_dir / "_freeze_module.vcxproj").write_text(
        '<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">'
        f"<ItemGroup>{sources}</ItemGroup></Project>",
        encoding="utf-8",
    )
    compiler = [
        clang,
        "--driver-mode=gcc",
        "-fuse-ld=lld",
        "-fms-runtime-lib=static",
        "-gcodeview",
    ]
    subprocess.run(
        [
            sys.executable,
            "-E",
            "-s",
            "-B",
            "-c",
            (
                "import os, subprocess\n"
                "from pathlib import Path\n"
                "import build_cpython_windows as builder\n"
                f"exe = builder.build_freeze_tool({compiler!r}, "
                f"Path({str(source_dir)!r}), Path({str(build_dir)!r}), "
                "dict(os.environ), 4, {})\n"
                "subprocess.run([str(exe)], check=True)\n"
            ),
        ],
        cwd=tmp_path,
        env=dict(os.environ),
        check=True,
        text=True,
    )
    objects = sorted((build_dir / "freeze-objects").glob("*.obj"))
    assert len(objects) == 170
    assert len(subprocess.list2cmdline([str(obj) for obj in objects])) > 32767


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows only")
def test_core_disables_remote_debugging(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    shutil.copy2(root / "deps/scripts/build_cpython_windows.py", tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "-E",
            "-s",
            "-B",
            "-c",
            "import build_cpython_windows as b; "
            "print('\\n'.join(b.core_defines('3.14.8')))",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Py_BUILD_CORE" in result.stdout.splitlines()
    assert "Py_REMOTE_DEBUG" not in result.stdout.splitlines()


def test_project_getpath_constants_never_contain_physical_source_paths(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    shutil.copy2(root / "deps/scripts/build_cpython_windows.py", tmp_path)
    source = tmp_path / "immutable source"
    project = source / "PCbuild"
    project.mkdir(parents=True)
    (project / "pythoncore.vcxproj").write_text(
        '<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">'
        '<ItemGroup><ClCompile Include="../Modules/getpath.c">'
        '<PreprocessorDefinitions>PREFIX="physical/install";'
        'EXEC_PREFIX="physical/install";VPATH="physical/source";'
        'VERSION=NULL;PLATLIBDIR="DLLs"</PreprocessorDefinitions>'
        '</ClCompile></ItemGroup></Project>'
    )
    result = subprocess.run(
        [
            sys.executable,
            "-E",
            "-s",
            "-B",
            "-c",
            (
                "import json; from pathlib import Path; "
                "import build_cpython_windows as b; "
                f"source = Path({str(source)!r}); "
                "sources = b.project_sources(source / 'PCbuild', source, "
                "'pythoncore', b.msbuild_properties('3.14.8')); "
                "print(json.dumps(sources[0].defines))"
            ),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == [
        "VERSION=NULL",
        'PLATLIBDIR="DLLs"',
        "PREFIX=NULL",
        "EXEC_PREFIX=NULL",
        'VPATH=""',
    ]
