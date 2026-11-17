# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from io import StringIO
from unittest.mock import patch

import pytest

from awscli.customizations.configure import (
    is_overly_permissive,
    warn_if_permissive,
)
from awscli.testutils import skip_if_windows


@pytest.mark.parametrize("mode", [0o700, 0o600, 0o400, 0o200, 0o000])
def test_acceptable_modes_are_not_overly_permissive(mode):
    assert is_overly_permissive(mode) is False


@pytest.mark.parametrize("mode", [0o644, 0o666, 0o777, 0o610, 0o601])
def test_overly_permissive_modes_are_detected(mode):
    assert is_overly_permissive(mode) is True


def _create_creds_file(tmp_path, mode):
    path = tmp_path / "credentials"
    path.write_text("[default]\naws_access_key_id=testing\n")
    os.chmod(path, mode)
    return str(path)


@skip_if_windows("Permissions test not valid on Windows.")
def test_prints_warning_for_permissive_file(tmp_path):
    path = _create_creds_file(tmp_path, 0o644)
    err = StringIO()
    warn_if_permissive(path, err_stream=err)
    output = err.getvalue()
    assert "aws: [WARNING]" in output
    assert path in output
    assert "accessible by other users" in output


@skip_if_windows("Permissions test not valid on Windows.")
def test_no_warning_for_0o600_file(tmp_path):
    path = _create_creds_file(tmp_path, 0o600)
    err = StringIO()
    warn_if_permissive(path, err_stream=err)
    assert err.getvalue() == ""


@skip_if_windows("Permissions test not valid on Windows.")
def test_no_warning_for_0o700_file(tmp_path):
    path = _create_creds_file(tmp_path, 0o700)
    err = StringIO()
    warn_if_permissive(path, err_stream=err)
    assert err.getvalue() == ""


@skip_if_windows("Permissions test not valid on Windows.")
def test_skips_when_file_does_not_exist(tmp_path):
    err = StringIO()
    warn_if_permissive(str(tmp_path / "nonexistent"), err_stream=err)
    assert err.getvalue() == ""


@patch("awscli.customizations.configure.is_windows", True)
def test_skips_on_windows(tmp_path):
    path = _create_creds_file(tmp_path, 0o777)
    err = StringIO()
    warn_if_permissive(path, err_stream=err)
    assert err.getvalue() == ""
