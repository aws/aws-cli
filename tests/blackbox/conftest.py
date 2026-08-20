"""Shared fixtures for blackbox tests."""

from __future__ import annotations

import os
import shutil

import pytest


@pytest.fixture
def aws_cli() -> str:
    command = os.environ.get("AWS_TEST_COMMAND") or shutil.which("aws")
    if command is None:
        pytest.fail(
            "No AWS CLI binary found: set AWS_TEST_COMMAND to its path or "
            "make `aws` available on PATH."
        )
    return command


@pytest.fixture
def aws_config(tmp_path):
    """Factory fixture that writes an AWS config file and returns its path."""

    def _make(config_dict: dict[str, dict[str, str]]) -> str:
        lines = []
        for section, values in config_dict.items():
            lines.append(f"[{section}]")
            for key, val in values.items():
                lines.append(f"{key} = {val}")
            lines.append("")
        path = tmp_path / "config"
        path.write_text("\n".join(lines))
        return str(path)

    return _make
