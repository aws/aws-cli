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
import base64
import io
import json
import os
import time
import warnings
import zipfile

from awscli.customizations.agenttoolkit.agents import AgentConfig


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def make_jwt(exp=None, **claims):
    """An unsigned three-part JWT; only its shape and claims matter here."""
    claims.setdefault('exp', exp or int(time.time()) + 3600)
    header = _b64(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode())
    payload = _b64(json.dumps(claims).encode())
    return f'{header}.{payload}.signature'


def make_jwe():
    """A five-part encrypted token, as Auth0 issues without an audience."""
    header = _b64(json.dumps({'alg': 'dir', 'enc': 'A256GCM'}).encode())
    return f'{header}..iv.ciphertext.tag'


def make_skill_md(name='pdf-extract', body='skill'):
    """SKILL.md text whose frontmatter names the skill ``name``."""
    return f'---\nname: {name}\ndescription: A skill.\n---\n{body}'


def make_zip(entries):
    """Build a zip from ``{name: bytes_or_str}`` or a list of pairs.

    A name may be a ZipInfo. A list can repeat a name, which zipfile allows
    with a warning.
    """
    pairs = entries.items() if isinstance(entries, dict) else entries
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zf, warnings.catch_warnings():
        warnings.filterwarnings('ignore', 'Duplicate name', UserWarning)
        for name, data in pairs:
            zf.writestr(name, data)
    return buffer.getvalue()


def make_agents(home, detected=('claude-code', 'codex', 'gemini-cli')):
    """Agent definitions rooted at ``home``; only ``detected`` ones exist.

    Codex and Gemini CLI share ``<home>/.agents/skills``, as they do for real.
    Returns the definitions and each agent's skills folder by id.
    """
    shared = os.path.join(home, '.agents', 'skills')
    configs = [
        AgentConfig(
            id='claude-code',
            display_name='Claude Code',
            detection_path=os.path.join(home, '.claude'),
        ),
        AgentConfig(
            id='codex',
            display_name='Codex',
            detection_path=os.path.join(home, '.codex'),
            skills_path_override=shared,
        ),
        AgentConfig(
            id='gemini-cli',
            display_name='Gemini CLI',
            detection_path=os.path.join(home, '.gemini'),
            skills_path_override=shared,
        ),
        AgentConfig(
            id='cursor',
            display_name='Cursor',
            detection_path=os.path.join(home, '.cursor'),
        ),
    ]
    folders = {}
    for config in configs:
        if config.id in detected:
            os.makedirs(config.detection_path, exist_ok=True)
        folders[config.id] = config.skills_path_override or os.path.join(
            config.detection_path, 'skills'
        )
    return configs, folders
