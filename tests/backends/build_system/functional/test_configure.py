import shutil
import os
import subprocess
from pathlib import Path
from typing import List, Optional

from tests import skip_if_windows


ROOT_DIR = Path(__file__).parents[4]
EXPECTED_AUTORECONF_VERSION = "2.71"
WINDOWS_SKIP_MESSAGE = "autoreconf not supported on windows"


def _autoreconf(args: Optional[List[str]] = None, directory=None):
    if args is None:
        args = []
    command = ['autoreconf'] + args
    result = subprocess.run(
        command,
        capture_output=True,
        cwd=directory,
    )
    assert result.returncode == 0
    output = result.stdout.decode()
    return output


def _read_configure(root):
    with open(root / "configure", "r") as f:
        return f.read()


@skip_if_windows(WINDOWS_SKIP_MESSAGE)
def test_local_autoreconf_version_correct():
    output = _autoreconf(['--version'])
    assert EXPECTED_AUTORECONF_VERSION in output


@skip_if_windows(WINDOWS_SKIP_MESSAGE)
def test_ensure_configure_is_active(tmpdir):
    test_dir = tmpdir / "testbuild"
    test_dir.mkdir()
    files_required_for_configure_generation = [
        "configure.ac",
        "Makefile.in",
        "m4",
    ]
    for filename in files_required_for_configure_generation:
        source = ROOT_DIR / filename
        dest = test_dir / filename
        if os.path.isfile(source):
            shutil.copyfile(source, dest)
        else:
            shutil.copytree(source, dest)

    _autoreconf(directory=test_dir)
    regenerated_configure = _read_configure(test_dir)
    original_configure = _read_configure(ROOT_DIR)

    assert original_configure == regenerated_configure
