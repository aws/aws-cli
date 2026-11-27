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
import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import zipfile
from unittest.mock import Mock, patch

import pytest

from awscli.customizations.agenttoolkit import state, utils
from awscli.customizations.agenttoolkit.agents import (
    SKILL_METADATA_FILENAME,
    AgentConfig,
)


def _can_create_symlinks():
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            os.symlink(
                tmpdir, os.path.join(tmpdir, 'link'), target_is_directory=True
            )
        except (OSError, NotImplementedError):
            return False
    return True


# Creating symlinks on Windows needs admin rights or Developer Mode.
requires_symlinks = pytest.mark.skipif(
    not _can_create_symlinks(),
    reason='Creating symlinks is not permitted for this user.',
)


# Directory junctions are Windows only, and need no special rights.
requires_junctions = pytest.mark.skipif(
    sys.platform != 'win32', reason='Directory junctions are Windows only.'
)


def make_junction(link, target):
    """Create a Windows directory junction at ``link`` pointing at
    ``target``, like ``mklink /J``."""
    import _winapi

    _winapi.CreateJunction(str(target), str(link))


def make_parsed_globals(output='json'):
    pg = Mock()
    pg.output = output
    pg.query = None
    pg.color = 'off'
    pg.no_paginate = False
    return pg


def make_session():
    session = Mock()
    session.user_agent_extra = ''
    session.get_config_variable.return_value = 'json'
    session.emit_first_non_none_response.return_value = None
    return session


def make_skill_zip(files=None):
    """Create a skill zip and returns (bytes, checksum)."""
    if files is None:
        files = {'SKILL.md': '# Test Skill\n'}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    zip_bytes = buf.getvalue()
    checksum = hashlib.sha256(zip_bytes).hexdigest()
    return zip_bytes, checksum


def make_skill(tmp_path, agent_name, skill_name, with_marker=True):
    skill_dir = tmp_path / agent_name / 'skills' / skill_name
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('test')
    if with_marker:
        (skill_dir / SKILL_METADATA_FILENAME).write_text(
            json.dumps({'version': 'v1'})
        )


def home_relative(home, *parts):
    """Return the path joined from ``parts`` relative to ``home``."""
    return os.path.relpath(os.path.join(str(home), *map(str, parts)), home)


def make_config(tmp_path, **overrides):
    defaults = {
        'id': 'test-agent',
        'display_name': 'Test Agent',
        'detection_path': str(tmp_path / '.test-agent'),
    }
    defaults.update(overrides)
    detection_path = defaults['detection_path']
    if detection_path.startswith('~/'):
        default_skills_path = os.path.join(detection_path[2:], 'skills')
    else:
        default_skills_path = home_relative(tmp_path, detection_path, 'skills')
    defaults.setdefault('skills_paths', [default_skills_path])
    return AgentConfig(**defaults)


def skills_dir_entries(path):
    """Names in ``path``, without the skills lock file."""
    return sorted(
        p.name for p in path.iterdir() if p.name != utils.SKILLS_LOCK_FILENAME
    )


@contextlib.contextmanager
def unwritable_aws_cli_dir(tmp_path):
    """Make the agent toolkit directory impossible to create.

    A file where ``~/.aws`` should be blocks it on every platform, even as
    root, unlike removing write permission.
    """
    aws_path = tmp_path / 'blocked-home' / '.aws'
    aws_path.parent.mkdir(parents=True)
    aws_path.write_text('')
    state_path = aws_path / 'cli' / 'agent-toolkit' / 'state.json'
    with patch.object(state, 'STATE_PATH', str(state_path)):
        yield
