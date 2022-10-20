# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import os
import json
from typing import List

import pytest

from build_system.utils import Utils
from build_system.utils import parse_requirements
from build_system.utils import ParseError
from build_system.utils import Requirement

from tests import skip_if_windows, if_windows


@pytest.fixture
def utils():
    return Utils()


@pytest.mark.parametrize(
    "lines,expected",
    [
        (
            "flit_core>=3.7.1,<3.7.2",
            Requirement("flit_core", ">=3.7.1", "<3.7.2"),
        ),
        (
            "colorama>=0.2.5,<0.4.4",
            Requirement("colorama", ">=0.2.5", "<0.4.4"),
        ),
        ("docutils>=0.10,<0.16", Requirement("docutils", ">=0.10", "<0.16")),
        (
            "cryptography>=3.3.2,<37.0.0",
            Requirement("cryptography", ">=3.3.2", "<37.0.0"),
        ),
        (
            "ruamel.yaml>=0.15.0,<=0.17.21",
            Requirement("ruamel.yaml", ">=0.15.0", "<=0.17.21"),
        ),
        ("wcwidth<0.2.0", Requirement("wcwidth", "<0.2.0")),
        (
            "prompt-toolkit>=3.0.24,<3.0.29",
            Requirement("prompt-toolkit", ">=3.0.24", "<3.0.29"),
        ),
        ("distro>=1.5.0,<1.6.0", Requirement("distro", ">=1.5.0", "<1.6.0")),
        (
            "awscrt>=0.12.4,<=0.14.0",
            Requirement("awscrt", ">=0.12.4", "<=0.14.0"),
        ),
        (
            "python-dateutil>=2.1,<3.0.0",
            Requirement("python-dateutil", ">=2.1", "<3.0.0"),
        ),
        (
            "jmespath>=0.7.1,<1.1.0",
            Requirement("jmespath", ">=0.7.1", "<1.1.0"),
        ),
        ("urllib3>=1.25.4,<1.27", Requirement("urllib3", ">=1.25.4", "<1.27")),
        (["urllib3>=1.\\\\", "25.4,<1.27"], Requirement("urllib3", ">=1.25.4", "<1.27")),
        ("#urllib3>=1.25.4,<1.27", None),
        ("urllib3>=1.25.4,<1.27 #foobarbaz", Requirement("urllib3", ">=1.25.4", "<1.27")),
        ("urllib3>=1.25.4,<1.27 ; python_version == 3.6", ParseError),
    ],
)
def test_parse_requirements(lines, expected):
    if isinstance(lines, str):
        lines = [lines]
    if isinstance(expected, Requirement):
        req = list(parse_requirements(lines))[0]
        assert req == expected
    elif expected is None:
        assert len(list(parse_requirements(lines))) == 0
    else:
        with pytest.raises(expected):
            list(parse_requirements(lines))


@pytest.mark.parametrize(
    "req,version,expected",
    [
        (Requirement("foo", "==1.0"), "1.0", True),
        (Requirement("foo", "==1.0"), "1.0.0", True),
        (Requirement("foo", "==1.0.0"), "1.0", True),
        (Requirement("foo", "==1.0"), "2.0", False),
        (Requirement("foo", ">=1.0", "<2.0"), "1.1", True),
        (Requirement("foo", ">=3.7.1", "<3.7.2"), "3.7.1", True),
        (Requirement("foo", ">=3.7.1", "<3.7.2"), "3.7.2", False),
        (Requirement("foo", ">=3.7.1", "<3.7.2"), "1.1.1", False),
        (Requirement("foo", ">=3.7.1", "<3.7.2"), "1.1.1", False),
        (Requirement("foo", ">=0.15.0", "<=0.17.21"), "0.14.0", False),
        (Requirement("foo", ">=0.15.0", "<=0.17.21"), "0.14.99999", False),
        (Requirement("foo", ">=0.15.0", "<=0.17.21"), "0.14.99999.123", False),
        (Requirement("foo", ">=0.15.0", "<=0.17.21"), "0.15.0", True),
        (Requirement("foo", ">=0.15.0", "<=0.17.21"), "0.16.0", True),
        (Requirement("foo", ">=0.15.0", "<=0.17.21"), "0.17.0", True),
        (Requirement("foo", ">=0.15.0", "<=0.17.21"), "0.17.21", True),
        (Requirement("foo", ">=0.15.0", "<=0.17.21"), "0.17.22", False),
        (Requirement("foo", ">=0.15.0", "<=0.17.21"), "0.18.0", False),
    ],
)
def test_requirement_ranges(req, version, expected):
    assert req.is_in_range(version) == expected


class TestUtils:
    def test_isdir(self, utils: Utils, tmp_path):
        file_path = tmp_path / "filename.txt"
        file_path.write_text("foo")

        assert utils.isdir(tmp_path) is True
        assert utils.isdir(file_path) is False

    def test_path_exists(self, utils: Utils, tmp_path):
        file_path = tmp_path / "filename.txt"
        file_path.write_text("foo")
        fake_path = tmp_path / "fake"

        assert utils.path_exists(file_path) is True
        assert utils.path_exists(fake_path) is False

    def test_rmtree(self, utils: Utils, tmp_path):
        file_path = tmp_path / "root.txt"
        file_path.write_text("foo")
        subdir_path = tmp_path / "dir"
        subdir_path.mkdir()
        subfile_path = subdir_path / "subfile.txt"
        subfile_path.write_text("bar")

        utils.rmtree(tmp_path)
        assert os.path.exists(tmp_path) is False

    @skip_if_windows
    def test_run(self, utils: Utils):
        assert utils.run(["test", "1", "==", "2"]).returncode == 1
        assert utils.run(["test", "1", "==", "1"]).returncode == 0

    @if_windows
    def test_run_windows(self, utils: Utils):
        assert utils.run(["exit", "1"], shell=True).returncode == 1
        assert utils.run(["exit"], shell=True).returncode == 0

    def test_copy_file(self, utils: Utils, tmp_path):
        src_path = tmp_path / "source.txt"
        src_path.write_text("foo")
        dst_path = tmp_path / "destination.txt"

        utils.copy_file(src_path, dst_path)
        with open(src_path, "r") as f:
            src = f.read()
        with open(dst_path, "r") as f:
            dst = f.read()

        assert src == dst

    def test_copy_directory_contents_into(self, utils: Utils, tmp_path):
        src_path = tmp_path / "src"
        src_path.mkdir()
        (src_path / "file").write_text("foo")
        dst_path = tmp_path / "dst"
        dst_path.mkdir()

        utils.copy_directory_contents_into(str(src_path), str(dst_path))

        assert open((dst_path / "file"), "r").read() == "foo"

    def test_copy_directory(self, utils: Utils, tmp_path):
        src_path = tmp_path / "src"
        src_path.mkdir()
        (src_path / "file").write_text("foo")
        dst_path = tmp_path / "dst"

        utils.copy_directory(src_path, dst_path)

        assert os.path.exists(dst_path)
        assert open((dst_path / "file"), "r").read() == "foo"

    def test_update_metadata(self, utils: Utils, tmp_path):
        data_dir = tmp_path / "awscli" / "data"
        data_dir.mkdir(parents=True)
        metadata_path = data_dir / "metadata.json"
        metadata_path.write_text("{}")

        utils.update_metadata(tmp_path, key="value")

        with open(metadata_path, "r") as f:
            data = json.load(f)
        assert data == {"key": "value"}

    @skip_if_windows
    def test_create_venv(self, utils: Utils, tmp_path):
        utils.create_venv(tmp_path)

        self.assert_dir_has_content(
            tmp_path,
            [
                "bin",
                "include",
                "lib",
            ],
        )
        self.assert_dir_has_content(
            tmp_path / "bin",
            [
                "python",
                "pip",
            ],
        )

    @if_windows
    def test_create_venv_windows(self, utils: Utils, tmp_path):
        utils.create_venv(tmp_path)

        self.assert_dir_has_content(
            tmp_path,
            [
                "Scripts",
                "Include",
                "Lib",
                "pyvenv.cfg",
            ],
        )
        self.assert_dir_has_content(
            tmp_path / "Scripts",
            [
                "python.exe",
                "pip.exe",
            ],
        )

    def assert_dir_has_content(self, path: str, expected_files: List[str]):
        assert set(expected_files).issubset(set(os.listdir(path)))
