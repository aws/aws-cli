"""Check the Cargo dependency drivers without compiling dependencies."""

import json
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


def evaluate(directory: Path, expression: str) -> object:
    result = subprocess.run(
        [
            sys.executable,
            "-E",
            "-s",
            "-B",
            "-c",
            (
                "from pathlib import Path; import json; "
                "import build_cpython as c; "
                "import prepare_python_fallback as f; "
                f"print(json.dumps({expression}))"
            ),
        ],
        cwd=directory,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_pgo_trains_on_quoted_source_without_bytecode(
    staged_driver: Path,
) -> None:
    source = staged_driver / "upstream tree's source"
    args = evaluate(
        staged_driver,
        "c.configure_args(Path('/install'), Path('/openssl'), "
        "Path('/zlib-xz'), Path('/deps'), "
        f"'x86_64-unknown-linux-musl', True, Path({str(source)!r}))",
    )
    assert isinstance(args, list)
    task = next(arg for arg in args if arg.startswith("PROFILE_TASK="))
    assert shlex.split(task.removeprefix("PROFILE_TASK=")) == [
        "-B",
        str(staged_driver / "profile_aws.py"),
        str(source),
    ]
    assert "--without-remote-debug" in args


def test_no_pgo_retains_lto_and_omits_training(staged_driver: Path) -> None:
    args = evaluate(
        staged_driver,
        "c.configure_args(Path('/install'), Path('/openssl'), "
        "Path('/zlib-xz'), Path('/deps'), "
        "'x86_64-unknown-linux-musl', False, Path('/missing'))",
    )
    assert isinstance(args, list)
    assert "--with-lto=thin" in args
    assert "--without-remote-debug" in args
    assert "--enable-optimizations" not in args
    assert not any(arg.startswith("PROFILE_TASK=") for arg in args)


def test_training_stamp_hashes_contents_and_ignores_bytecode(
    staged_driver: Path,
) -> None:
    source = staged_driver / "upstream"
    package = source / "awscli"
    package.mkdir(parents=True)
    module = package / "argparser.py"
    module.write_text("original\n")
    expression = (
        "c.stamp_text(Path('/python'), 'x86_64-unknown-linux-musl', "
        f"'clang', True, None, None, Path({str(source)!r}))"
    )
    initial = evaluate(staged_driver, expression)
    (package / "cache.pyc").write_bytes(b"ignored")
    assert evaluate(staged_driver, expression) == initial
    module.write_text("modified\n")
    assert evaluate(staged_driver, expression) != initial


def test_runtime_lock_retains_hashes_and_removes_entire_stanzas(
    staged_driver: Path,
) -> None:
    source = staged_driver / "lock.txt"
    source.write_text(
        "awscrt==0.37.0 \\\n    --hash=sha256:exclude-crt\n"
        "colorama==0.4.6 \\\n    --hash=sha256:keep\n"
        "Ruamel_Yaml.Clib==0.2.15 \\\n    --hash=sha256:exclude-clib\n"
    )
    output = staged_driver / "filtered.txt"
    evaluate(
        staged_driver,
        "str(f.filter_runtime_requirements("
        f"Path({str(source)!r}), Path({str(output)!r})))",
    )
    text = output.read_text()
    assert "sha256:keep" in text
    assert "exclude-crt" not in text
    assert "exclude-clib" not in text
    assert "Source lock SHA256:" in text


@pytest.mark.parametrize(
    ("target_triple", "emulation"),
    [
        ("x86_64-unknown-linux-musl", "elf_x86_64"),
        ("aarch64-unknown-linux-musl", "aarch64linux"),
    ],
)
def test_linux_materialization_uses_o3_and_preserves_native_archive_contract(
    staged_driver: Path,
    target_triple: str,
    emulation: str,
) -> None:
    result = evaluate(
        staged_driver,
        f"[str(arg) for arg in c.materialize_command('ld.lld', "
        f"{target_triple!r}, Path('/input.a'), Path('/output.o'), "
        "[Path('/support.a')], None)]",
    )
    assert result == [
        "ld.lld",
        "-m",
        emulation,
        "-r",
        "--lto-O3",
        "-o",
        str(Path("/output.o")),
        "--whole-archive",
        str(Path("/input.a")),
        "--no-whole-archive",
        str(Path("/support.a")),
    ]


def test_linux_config_accepts_reviewed_micro_release_features(
    staged_driver: Path,
) -> None:
    old = '#define PY_SUPPORT_TIER 2\n#define HAVE_ZLIB 1\n'
    new = (
        '#define PY_SUPPORT_TIER 0\n#define HAVE_ZLIB 1\n'
        '#define HAVE_DL_ITERATE_PHDR 1\n'
        '#define _Py_LINKER_THREAD_STACK_SIZE 1048576\n'
    )
    assert (
        evaluate(
            staged_driver, f'c.linux_configuration_changes({old!r}, {new!r})'
        )
        == {}
    )
    changed = new.replace('HAVE_ZLIB 1', 'HAVE_ZLIB 0')
    assert evaluate(
        staged_driver, f'c.linux_configuration_changes({old!r}, {changed!r})'
    ) == {'HAVE_ZLIB': ['1', '0']}


def test_linux_config_accepts_reviewed_arm_differences(
    staged_driver: Path,
) -> None:
    old = (
        '#define HAVE_ZLIB 1\n#define HAVE_GCC_ASM_FOR_X64 1\n'
        '#define _Py_HACL_CAN_COMPILE_VEC128 1\n'
        '#define _Py_HACL_CAN_COMPILE_VEC256 1\n'
    )
    new = (
        '#define PY_SUPPORT_TIER 0\n#define HAVE_ZLIB 1\n'
        '#define HAVE_DL_ITERATE_PHDR 1\n'
        '#define _Py_LINKER_THREAD_STACK_SIZE 1048576\n'
        '#define HAVE_USABLE_WCHAR_T 1\n'
    )
    arm = "'aarch64-unknown-linux-musl'"
    assert (
        evaluate(
            staged_driver,
            f'c.linux_configuration_changes({old!r}, {new!r}, {arm})',
        )
        == {}
    )
    assert evaluate(
        staged_driver, f'c.linux_configuration_changes({old!r}, {new!r})'
    ) == {
        'HAVE_GCC_ASM_FOR_X64': ['1', None],
        'HAVE_USABLE_WCHAR_T': [None, '1'],
        '_Py_HACL_CAN_COMPILE_VEC128': ['1', None],
        '_Py_HACL_CAN_COMPILE_VEC256': ['1', None],
    }


def test_linux_config_requires_remote_debugging_disabled(
    staged_driver: Path,
) -> None:
    old = '#define HAVE_ZLIB 1\n#define Py_REMOTE_DEBUG 1\n'
    reviewed = (
        '#define PY_SUPPORT_TIER 0\n#define HAVE_DL_ITERATE_PHDR 1\n'
        '#define _Py_LINKER_THREAD_STACK_SIZE 1048576\n'
    )
    disabled = reviewed + '#define HAVE_ZLIB 1\n'
    enabled = disabled + '#define Py_REMOTE_DEBUG 1\n'
    assert (
        evaluate(
            staged_driver,
            f'c.linux_configuration_changes({old!r}, {disabled!r})',
        )
        == {}
    )
    assert evaluate(
        staged_driver, f'c.linux_configuration_changes({old!r}, {enabled!r})'
    ) == {'Py_REMOTE_DEBUG': [None, '1']}


def test_awscrt_sources_are_sorted_regular_c_files(
    staged_driver: Path,
) -> None:
    source = staged_driver / "source"
    source.mkdir()
    for name in ["zeta.c", "module.c", "alpha.c", "header.h"]:
        (source / name).write_text("")
    (source / "directory.c").mkdir()
    (source / "directory.c" / "nested.c").write_text("")
    assert evaluate(
        staged_driver,
        f"[path.name for path in f.awscrt_c_sources(Path({str(source)!r}))]",
    ) == ["alpha.c", "module.c", "zeta.c"]


def test_awscrt_source_limit_counts_non_c_directory_entries(
    staged_driver: Path,
) -> None:
    source = staged_driver / "source"
    source.mkdir()
    (source / "module.c").write_text("")
    (source / "header.h").write_text("")
    assert (
        evaluate(
            staged_driver,
            f"len(f.awscrt_c_sources(Path({str(source)!r}), entry_limit=3))",
        )
        == 1
    )
    (source / "non-source-directory").mkdir()
    with pytest.raises(subprocess.CalledProcessError) as failure:
        evaluate(
            staged_driver,
            f"len(f.awscrt_c_sources(Path({str(source)!r}), entry_limit=3))",
        )
    assert "more than 3 entries" in failure.value.stderr


def test_empty_awscrt_source_set_is_rejected(staged_driver: Path) -> None:
    source = staged_driver / "source"
    source.mkdir()
    (source / "header.h").write_text("")
    with pytest.raises(subprocess.CalledProcessError) as failure:
        evaluate(
            staged_driver,
            f"len(f.awscrt_c_sources(Path({str(source)!r})))",
        )
    assert "module.c is missing from its 0 .c files" in failure.value.stderr


def test_msvc_capture_is_explicit_and_preserves_inherited_home(
    staged_driver: Path,
) -> None:
    capture = staged_driver / "msvc.json"
    capture.write_text(
        json.dumps(
            {
                "Path": "captured SDK tools",
                "INCLUDE": "C:/café/include",
                "LIB": "C:/sdk/lib",
                "LIBPATH": "C:/sdk/metadata",
                "HOME": "must not replace inherited home",
            }
        )
    )
    source = {
        "PATH": "tools",
        "HOME": "original home",
        "INCLUDE": "untrusted headers",
        "LIB": "untrusted libraries",
        "LIBPATH": "untrusted metadata",
        "CL": "untrusted flags",
    }
    expression = "__import__('build_environ').tool_environ"
    assert evaluate(staged_driver, f"{expression}({source!r})") == {
        "PATH": "tools",
        "HOME": "original home",
        "LC_ALL": "C",
    }
    assert evaluate(
        staged_driver,
        f"{expression}({source!r}, msvc_environ=Path({str(capture)!r}))",
    ) == {
        "PATH": "captured SDK tools",
        "HOME": "original home",
        "LC_ALL": "C",
        "INCLUDE": "C:/café/include",
        "LIB": "C:/sdk/lib",
        "LIBPATH": "C:/sdk/metadata",
    }


@pytest.mark.parametrize("capture", [["INCLUDE", "headers"], {"INCLUDE": 123}])
def test_invalid_msvc_capture_is_rejected(
    staged_driver: Path,
    capture: object,
) -> None:
    path = staged_driver / "msvc.json"
    path.write_text(json.dumps(capture))
    with pytest.raises(subprocess.CalledProcessError) as failure:
        evaluate(
            staged_driver,
            "__import__('build_environ').tool_environ("
            f"msvc_environ=Path({str(path)!r}))",
        )
    assert "must map names to strings" in failure.value.stderr
