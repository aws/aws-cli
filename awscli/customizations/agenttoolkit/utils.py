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
import zlib

from awscli.customizations.agenttoolkit import atomic
from awscli.customizations.agenttoolkit.agents import (
    AGENT_CONFIGS,
    SKILL_FILENAME,
    SKILL_METADATA_FILENAME,
    get_detected_agents,
    universal_first,
)
from awscli.customizations.agenttoolkit.filelock import file_lock
from awscli.customizations.agenttoolkit.state import toolkit_dir
from awscli.customizations.exceptions import ParamValidationError
from awscli.customizations.utils import create_client_from_parsed_globals

LOG = logging.getLogger(__name__)
MAX_UNCOMPRESSED_SIZE = 10 * 1024 * 1024  # 10 MB

# Serializes changes to skill directories across processes. Lives in the
# agent toolkit state directory.
SKILLS_LOCK_FILENAME = 'skills.lock'

# Errors zipfile can raise while extracting a member.
_ZIP_READ_ERRORS = (
    zipfile.BadZipFile,
    zlib.error,
    EOFError,
    RuntimeError,  # encrypted member
    NotImplementedError,  # unsupported compression method
)

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


# The Agent Toolkit API is served from a single region today,
# Default there unless the caller passes an explicit ``--region``,
# otherwise a user whose configured region is elsewhere would hit
# an endpoint that does not exist.
AGENT_TOOLKIT_REGION = 'us-east-1'


def create_client(session, parsed_globals):
    overrides = {}
    if not getattr(parsed_globals, 'region', None):
        overrides['region_name'] = AGENT_TOOLKIT_REGION
    return create_client_from_parsed_globals(
        session,
        'agenttoolkit',
        parsed_globals,
        overrides=overrides,
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


def collect_installed_skills(agents):
    seen_paths = set()
    skills = []
    for agent in universal_first(agents):
        for skill in agent.get_installed_skills():
            real_path = os.path.realpath(skill.path)
            if real_path in seen_paths:
                continue
            seen_paths.add(real_path)
            skills.append(skill)
    return skills


def agents_with_skill(agents, skill_name):
    return [
        agent
        for agent in agents
        if any(
            skill.name == skill_name for skill in agent.get_installed_skills()
        )
    ]


def read_installed_version(skill_dir):
    metadata = read_skill_metadata(skill_dir)
    if metadata is None:
        return None
    return metadata.get('version')


def read_skill_metadata(skill_dir):
    path = os.path.join(skill_dir, SKILL_METADATA_FILENAME)
    try:
        with open(path, encoding='utf-8') as f:
            metadata = json.load(f)
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
    if not isinstance(metadata, dict):
        # Valid JSON, but not an object, so there are no fields to read.
        LOG.debug(
            'Ignoring skill metadata at %s: expected a JSON object, got %s.',
            path,
            type(metadata).__name__,
        )
        return None
    return metadata


def write_skill_metadata(skill_dir, version):
    path = os.path.join(skill_dir, SKILL_METADATA_FILENAME)
    with open(path, 'w', encoding='utf-8') as f:
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
    """Install a skill into each agent's skills directory."""
    expected = checksum.strip().lower().split()[0]
    actual = hashlib.sha256(zip_bytes).hexdigest()
    if len(expected) != 64 or actual != expected:
        raise AgentToolkitServiceError(
            f'Checksum verification failed for {skill_name} '
            f'(expected {expected!r}, got {actual!r}).'
        )

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as e:
        raise AgentToolkitServiceError(
            f'Could not read the archive for {skill_name}: {e}'
        ) from e
    with zf:
        _verify_skill_archive(skill_name, zf)
        extracted_paths = set()
        for agent in universal_first(agents):
            skill_dir = os.path.join(agent.skills_path, skill_name)
            real_dir = os.path.realpath(skill_dir)
            if real_dir in extracted_paths:
                continue
            extracted_paths.add(real_dir)
            try:
                with skills_lock():
                    installed = _install_skill_dir(
                        skill_name,
                        version,
                        zf,
                        real_dir,
                        stream,
                        overwrite_existing,
                    )
            except OSError as e:
                raise AgentToolkitServiceError(
                    f'Could not install {skill_name} at {real_dir}: {e}'
                ) from e
            if installed and stream:
                stream.write(
                    f'  {action} {skill_name} ({version})'
                    f' to {agent.display_label}.\n'
                )


def _verify_skill_archive(skill_name, zf):
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
    if not any(
        os.path.normpath(info.filename) == SKILL_FILENAME and not info.is_dir()
        for info in zf.infolist()
    ):
        raise AgentToolkitServiceError(
            f'Refusing to install {skill_name}: the archive has no '
            f'{SKILL_FILENAME}.'
        )


def _install_skill_dir(
    skill_name, version, zf, real_dir, stream, overwrite_existing
):
    """Install into ``real_dir``. Returns whether anything was written."""
    atomic.recover(real_dir)
    if os.path.lexists(real_dir) and not os.path.isdir(real_dir):
        if stream:
            stream.write(
                f'  Skipped {skill_name} at {real_dir}: '
                f'a file that is not a skill directory is in the way.\n'
            )
        return False
    if os.path.isdir(real_dir):
        marker = os.path.join(real_dir, SKILL_METADATA_FILENAME)
        if not os.path.exists(marker):
            if stream:
                stream.write(
                    f'  Skipped {skill_name} at {real_dir}: '
                    f'directory was not installed by the AWS CLI.\n'
                )
            return False
        # Marker is present, but if SKILL.md is missing the previous install
        # is corrupted (e.g. user deleted files by hand).
        skill_file = os.path.join(real_dir, SKILL_FILENAME)
        is_corrupted = not os.path.exists(skill_file)
        if not overwrite_existing and not is_corrupted:
            if stream:
                installed = read_installed_version(real_dir)
                version_note = f' ({installed})' if installed else ''
                stream.write(
                    f'  {skill_name} is already installed'
                    f'{version_note} at {real_dir}. Run '
                    f'"aws agent-toolkit update-skill '
                    f'--skill-name {skill_name}" to update, '
                    f'or remove it first to reinstall.\n'
                )
            return False
        if is_corrupted and not overwrite_existing and stream:
            stream.write(
                f'  Reinstalling {skill_name} at {real_dir}: '
                f'previous install appears incomplete.\n'
            )

    os.makedirs(os.path.dirname(real_dir), exist_ok=True)
    staging_dir = atomic.make_staging_dir(real_dir)
    try:
        # Extraction reads and checks every member, so a corrupt archive
        # fails here, before anything is swapped.
        try:
            zf.extractall(staging_dir)
        except _ZIP_READ_ERRORS as e:
            raise AgentToolkitServiceError(
                f'Refusing to install {skill_name}: the archive is corrupt '
                f'or unsupported ({e}).'
            ) from e
        write_skill_metadata(staging_dir, version)
        atomic.swap_into_place(staging_dir, real_dir)
    except BaseException:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise
    return True


def skills_lock():
    """Lock held while changing skill directories."""
    return file_lock(os.path.join(toolkit_dir(), SKILLS_LOCK_FILENAME))


def _recover_interrupted_changes(agents):
    """Restore or clean up skill directories left by an interrupted change.

    A skill that was mid-swap is hidden from :meth:`get_installed_skills`
    until it is recovered, so this runs whenever agents are resolved.
    """
    roots = {os.path.realpath(agent.skills_path) for agent in agents}
    try:
        with skills_lock():
            for root in sorted(roots):
                atomic.recover_all(root)
    except OSError as e:
        # Best effort: installing a skill recovers its directory again.
        LOG.debug('Could not recover interrupted skill changes: %s', e)


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
        agents = [agent] if agent is not None else []
    else:
        agents = get_detected_agents(agent_configs=agent_configs)
    _recover_interrupted_changes(agents)
    return agents
