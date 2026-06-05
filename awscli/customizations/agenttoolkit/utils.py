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
import logging
import os
import shutil
import zipfile

from awscli.customizations.agenttoolkit.agents import (
    AGENT_CONFIGS,
    SKILL_METADATA_FILENAME,
    get_detected_agents,
    universal_first,
)
from awscli.customizations.exceptions import ParamValidationError
from awscli.customizations.utils import create_client_from_parsed_globals

LOG = logging.getLogger(__name__)
MAX_UNCOMPRESSED_SIZE = 10 * 1024 * 1024  # 10 MB

NONPROD_ACCESS_TOKEN_HEADER = 'x-nonprod-access-token'
NONPROD_ACCESS_TOKEN_ENV_VAR = 'NONPROD_ACCESS_TOKEN_HEADER'

SKILL_NAME_ARG = {
    'name': 'skill-name',
    'help_text': 'The name of the skill.',
    'action': 'store',
    'cli_type_name': 'string',
    'required': True,
}

SKILL_VERSION_ARG = {
    'name': 'skill-version',
    'help_text': (
        'Skill version to retrieve (such as ``v1``). Defaults to latest.'
    ),
    'action': 'store',
    'cli_type_name': 'string',
    'required': False,
}

AGENT_ARG = {
    'name': 'agent',
    'help_text': (
        'The agentic tool to target. If not set, the operation applies '
        'to all detected tools. Valid values: '
        f'{", ".join(c.id for c in AGENT_CONFIGS)}.'
    ),
    'action': 'store',
    'cli_type_name': 'string',
    'required': False,
}


def create_client(session, parsed_globals):
    return create_client_from_parsed_globals(
        session,
        'agenttoolkit',
        parsed_globals,
    )


def resolve_latest_version(client, skill_name):
    response = client.get_latest_skill_version(name=skill_name)
    return response['body'].strip()


def get_skill_download(client, skill_name, version=None):
    """
    Download a skill zip and its checksum via the modeled API.

    Returns (zip_bytes, checksum_hex, resolved_version).
    """

    # Actually look up the latest version instead of just passing 'latest',
    # this lets us write out the new version to the metadata file without
    # inspecting the zip contents
    if version is None:
        version = resolve_latest_version(client, skill_name)

    response = client.get_skill_file(
        name=skill_name, skillVersion=version, filePath='download'
    )
    zip_bytes = response['body'].read()

    response = client.get_skill_file_checksum(
        name=skill_name, skillVersion=version, filePath='download'
    )
    checksum = response['body'].strip().lower().split()[0]
    return zip_bytes, checksum, version


def read_installed_version(skill_dir):
    metadata = read_skill_metadata(skill_dir)
    if metadata is None:
        return None
    return metadata.get('version')


def read_skill_metadata(skill_dir):
    path = os.path.join(skill_dir, SKILL_METADATA_FILENAME)
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        LOG.debug(
            'Could not parse skill metadata at %s: %s. '
            'The file may be corrupted; remove or re-install the skill '
            'to recover.',
            path,
            e,
        )
        return None


def write_skill_metadata(skill_dir, version):
    path = os.path.join(skill_dir, SKILL_METADATA_FILENAME)
    with open(path, 'w') as f:
        json.dump({'version': version}, f)
        f.write('\n')


def install_skill(
    skill_name,
    version,
    zip_bytes,
    checksum,
    agents,
    stream=None,
    action='Installed',
    overwrite_existing=False,
):
    expected = checksum.strip().lower().split()[0]
    actual = hashlib.sha256(zip_bytes).hexdigest()
    if len(expected) != 64 or actual != expected:
        raise AgentToolkitServiceError(
            f'Checksum verification failed for {skill_name} '
            f'(expected {expected!r}, got {actual!r}).'
        )

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        total_size = sum(i.file_size for i in zf.infolist())
        if total_size > MAX_UNCOMPRESSED_SIZE:
            raise AgentToolkitServiceError(
                f'Refusing to extract: uncompressed size '
                f'({total_size} bytes) exceeds limit.'
            )
        for member in zf.namelist():
            normalized = os.path.normpath(member)
            if normalized.startswith('..') or os.path.isabs(normalized):
                raise AgentToolkitServiceError(
                    f'Refusing to extract {member!r}'
                    ' (path escapes skill directory).'
                )

        extracted_paths = set()
        for agent in universal_first(agents):
            skill_dir = os.path.join(agent.skills_path, skill_name)
            real_dir = os.path.realpath(skill_dir)
            if real_dir in extracted_paths:
                continue
            extracted_paths.add(real_dir)
            if os.path.isdir(real_dir):
                marker = os.path.join(real_dir, SKILL_METADATA_FILENAME)
                if not os.path.exists(marker):
                    if stream:
                        stream.write(
                            f'  Skipped {skill_name} at {real_dir}: '
                            f'directory was not installed by the AWS CLI.\n'
                        )
                    continue
                if not overwrite_existing:
                    if stream:
                        installed = read_installed_version(real_dir)
                        version_note = f' ({installed})' if installed else ''
                        stream.write(
                            f'  {skill_name} is already installed'
                            f'{version_note}. Run "aws agent-toolkit '
                            f'update-skill --skill-name {skill_name}" to '
                            f'update, or remove it first to reinstall.\n'
                        )
                    continue
                shutil.rmtree(real_dir)
            os.makedirs(real_dir, exist_ok=True)
            zf.extractall(real_dir)
            write_skill_metadata(real_dir, version)
            if stream:
                stream.write(
                    f'  {action} {skill_name} ({version})'
                    f' to {agent.display_label}.\n'
                )


class AgentToolkitServiceError(Exception):
    pass


def resolve_agents(agent_filter, agent_configs=None):
    """Resolve agents, optionally filtered by agent id."""
    if agent_configs is None:
        agent_configs = AGENT_CONFIGS
    if agent_filter:
        by_id = {c.id.lower(): c for c in agent_configs}
        config = by_id.get(agent_filter.lower())
        if config is None:
            raise ParamValidationError(
                f'Invalid agent "{agent_filter}". Valid values: '
                f'{", ".join(sorted(c.id for c in agent_configs))}.'
            )
        agent = config.detect()
        return [agent] if agent is not None else []
    return get_detected_agents(agent_configs=agent_configs)
