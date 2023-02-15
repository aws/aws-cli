import os
import platform
from typing import List, Any

import pytest


from build_system.install import Installer
from build_system.install import Uninstaller
from backends.build_system.utils import Utils
from tests.backends.build_system.markers import skip_if_windows, if_windows


class FakeUtils(Utils):
    def __init__(self, is_exe: bool, responses: bool = False):
        self._is_exe = is_exe
        self._responses = responses
        self.calls: List[Any] = []

    def isdir(self, path: str) -> bool:
        self.calls.append(("isdir", path))
        if path == os.path.join("build_dir", "exe"):
            return self._is_exe
        else:
            return self._responses

    def run(self, command, **kwargs):
        self.calls.append(("run", command, kwargs))

    def copy_directory(self, src, dst):
        self.calls.append(("copy_directory", src, dst))

    def copy_directory_contents_into(self, src, dst):
        self.calls.append(("copy_directory_contents_into", src, dst))

    def update_metadata(self, dirname, **kwargs):
        self.calls.append(("update_metadata", dirname, kwargs))

    def rmtree(self, path):
        self.calls.append(("rmtree", path))

    def read_file_lines(self, path: str) -> List[str]:
        self.calls.append(("read_file_lines", path))
        return ["file"]

    def write_file(self, path: str, content: str):
        self.calls.append(("write_file", path, content))

    def path_exists(self, path: str):
        self.calls.append(("path_exists", path))
        return self._responses

    def makedirs(self, path: str):
        self.calls.append(("makedirs", path))

    def islink(self, path: str) -> bool:
        self.calls.append(("islink", path))
        return self._responses

    def symlink(self, src: str, dst: str):
        self.calls.append(("symlink", src, dst))

    def remove(self, path: str):
        self.calls.append(("remove", path))


class TestInstaller:
    @skip_if_windows
    def test_install_exe(self):
        utils = FakeUtils(is_exe=True)
        installer = Installer("build_dir", utils=utils)
        installer.install("lib_dir", "bin_dir")

        assert utils.calls == [
            ("isdir", os.path.join("build_dir", "exe")),
            ("isdir", "lib_dir"),
            (
                "copy_directory",
                os.path.join("build_dir", "exe", "aws", "dist"),
                "lib_dir",
            ),
            ("path_exists", "bin_dir"),
            ("makedirs", "bin_dir"),
            ("islink", os.path.join("bin_dir", "aws")),
            (
                "symlink",
                os.path.join("lib_dir", "aws"),
                os.path.join("bin_dir", "aws"),
            ),
            ("islink", os.path.join("bin_dir", "aws_completer")),
            (
                "symlink",
                os.path.join("lib_dir", "aws_completer"),
                os.path.join("bin_dir", "aws_completer"),
            ),
        ]

    @if_windows
    def test_install_exe_windows(self):
        utils = FakeUtils(is_exe=True)
        installer = Installer("build_dir", utils=utils)
        installer.install("lib_dir", "bin_dir")

        assert utils.calls == [
            ("isdir", os.path.join("build_dir", "exe")),
            ("isdir", "lib_dir"),
            (
                "copy_directory",
                os.path.join("build_dir", "exe", "aws", "dist"),
                "lib_dir",
            ),
            ("write_file", "bin_dir\\aws.cmd", "@echo off\nlib_dir\\aws.exe %*\n"),
        ]

    @skip_if_windows
    def test_install_venv(self):
        utils = FakeUtils(is_exe=False)
        installer = Installer("build_dir", utils=utils)
        installer.install("lib_dir", "bin_dir")

        assert utils.calls == [
            ("isdir", "build_dir/exe"),
            ("isdir", "lib_dir"),
            ("copy_directory", "build_dir/venv", "lib_dir"),
            ("read_file_lines", "lib_dir/bin/aws"),
            ("write_file", "lib_dir/bin/aws", "#!lib_dir/bin/python\n"),
            ("read_file_lines", "lib_dir/bin/aws_completer"),
            (
                "write_file",
                "lib_dir/bin/aws_completer",
                "#!lib_dir/bin/python\n",
            ),
            ("path_exists", "bin_dir"),
            ("makedirs", "bin_dir"),
            ("islink", "bin_dir/aws"),
            ("symlink", "lib_dir/bin/aws", "bin_dir/aws"),
            ("islink", "bin_dir/aws_completer"),
            ("symlink", "lib_dir/bin/aws_completer", "bin_dir/aws_completer"),
        ]

    @if_windows
    def test_install_venv_windows(self):
        utils = FakeUtils(is_exe=False)
        installer = Installer("build_dir", utils=utils)
        installer.install("lib_dir", "bin_dir")

        assert utils.calls == [
            ("isdir", "build_dir\\exe"),
            ("isdir", "lib_dir"),
            ("copy_directory", "build_dir\\venv", "lib_dir"),
            ("read_file_lines", "lib_dir\\Scripts\\aws.cmd"),
            (
                "write_file",
                "lib_dir\\Scripts\\aws.cmd",
                '@echo off & "lib_dir\\Scripts\\python.exe" -x "%~f0" %* & goto :eof\n',
            ),
            ("path_exists", "bin_dir"),
            ("makedirs", "bin_dir"),
            ("islink", "bin_dir\\aws.cmd"),
            ("symlink", "lib_dir\\Scripts\\aws.cmd", "bin_dir\\aws.cmd"),
        ]


class TestUninstaller:
    @skip_if_windows
    def test_uninstall(self):
        utils = FakeUtils(is_exe=True, responses=True)
        uninstaller = Uninstaller(utils=utils)
        uninstaller.uninstall("lib_dir", "bin_dir")

        assert utils.calls == [
            ("isdir", "lib_dir"),
            ("rmtree", "lib_dir"),
            ("islink", "bin_dir/aws"),
            ("remove", "bin_dir/aws"),
            ("islink", "bin_dir/aws_completer"),
            ("remove", "bin_dir/aws_completer"),
        ]

    @if_windows
    def test_uninstall_windows(self):
        utils = FakeUtils(is_exe=True, responses=True)
        uninstaller = Uninstaller(utils=utils)
        uninstaller.uninstall("lib_dir", "bin_dir")

        assert utils.calls == [
            ("isdir", "lib_dir"),
            ("rmtree", "lib_dir"),
            ("islink", "bin_dir\\aws.cmd"),
            ("remove", "bin_dir\\aws.cmd"),
        ]
