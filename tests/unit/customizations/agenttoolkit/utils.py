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
import hashlib
import io
import json
import zipfile
from unittest.mock import Mock

from awscli.customizations.agenttoolkit.agents import (
    SKILL_METADATA_FILENAME,
    AgentConfig,
)


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


def make_config(tmp_path, **overrides):
    defaults = {
        'id': 'test-agent',
        'display_name': 'Test Agent',
        'detection_path': str(tmp_path / '.test-agent'),
    }
    defaults.update(overrides)
    return AgentConfig(**defaults)
