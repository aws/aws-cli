# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2]
NEXT_RELEASE_DIR = REPO_ROOT / '.changes' / 'next-release'


def _next_release_json_files():
    if not NEXT_RELEASE_DIR.is_dir():
        return []
    return [
        p for p in sorted(NEXT_RELEASE_DIR.iterdir()) if p.suffix == '.json'
    ]


@pytest.mark.parametrize(
    "json_path",
    _next_release_json_files(),
    ids=lambda p: p.name,
)
def test_next_release_json_is_well_formed(json_path):
    raw = json_path.read_text('utf-8')
    try:
        entry = json.loads(raw)
    except json.JSONDecodeError as e:
        pytest.fail(f"{json_path.name} is not valid JSON: {e}")
    assert isinstance(entry, dict), (
        f"{json_path.name} should be a JSON object, got {type(entry).__name__}"
    )
    VALID_TYPES = {'feature', 'bugfix', 'enhancement', 'api-change'}
    for key in ('category', 'description', 'type'):
        assert key in entry, f"{json_path.name} missing required key '{key}'"
        assert isinstance(entry[key], str) and entry[key].strip(), (
            f"{json_path.name} key '{key}' must be a non-empty string"
        )
    assert entry['type'] in VALID_TYPES, (
        f"{json_path.name} has invalid type '{entry['type']}', "
        f"must be one of {sorted(VALID_TYPES)}"
    )
