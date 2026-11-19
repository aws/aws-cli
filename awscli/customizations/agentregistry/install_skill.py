# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Download, verify and install a skill from a registry.

One command replaces the sequence a customer would otherwise run by hand:
fetch the record, read its ``artifact`` (a SHA-256 digest and a short-lived
download URL), fetch the archive, verify it against that digest, and extract it
into the skills folder of each detected agent, or into a target directory. A
record without a package that holds its SKILL.md text is installed from that
text alone.

The digest check is not optional. Skills carry executable content, so an archive
whose bytes do not match the digest recorded at publish time is rejected rather
than installed with a warning.
"""

import hashlib
import hmac
import http.client
import json
import logging
import os
import posixpath
import re
import secrets
import shlex
import shutil
import stat
import tempfile
import unicodedata
import urllib.error
import urllib.parse
import zipfile
import zlib

import ruamel.yaml

from awscli.customizations.agentregistry.constants import HTTP_TIMEOUT
from awscli.customizations.agentregistry.dataplane import (
    SIGN_IN_ARGUMENTS,
    SIGN_IN_DESCRIPTION,
    create_data_plane_client,
    skill_record_pages,
)
from awscli.customizations.agentregistry.utils import (
    AgentRegistryJWTError,
    bare_registry_id,
    comparable_endpoint,
    printable,
    redact_secrets,
    require_https,
    url_origin,
    urlopen,
    write_status,
)
from awscli.customizations.agenttoolkit.agents import (
    AGENT_CONFIGS,
    SKILL_METADATA_FILENAME,
    universal_first,
)
from awscli.customizations.agenttoolkit.utils import AGENT_ARG, resolve_agents
from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ParamValidationError

logger = logging.getLogger(__name__)

# Defensive ceilings. A registry we control should never exceed these, but the
# archive is attacker-controlled input from the extractor's point of view. The
# record publishes no size, so these are the only bound on the download.
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_EXTRACTED_BYTES = 512 * 1024 * 1024
MAX_ENTRIES = 10_000

# The most entries of a skills folder looked at when finding the skills this
# command installed there by their provenance markers.
MAX_SCANNED_ENTRIES = 10_000

_CHUNK_BYTES = 64 * 1024

# The SKILL.md name becomes a directory name; the record name never does. The
# service allows '/' and '.' in record names, so 'a/../../x' is a valid record
# name. The Agent Skills specification
# (https://agentskills.io/specification) requires a skill's name to equal its
# folder's and to be lowercase letters, digits and single hyphens, neither
# first nor last, at most 64 characters. The pattern is the service's
# (VestryCommon SkillMdFrontmatterRules.NAME_FORM). Patterns here are used
# with fullmatch(), because '$' would also accept a trailing newline.
SKILL_NAME = re.compile(r'[a-z0-9](?:[a-z0-9]*(?:-[a-z0-9]+)*)?')
MAX_SKILL_NAME_LENGTH = 64
SKILL_NAME_RULE = (
    'at most 64 lowercase letters, digits and hyphens, with no hyphen at the '
    'start or end and no two hyphens in a row'
)

# A skill's folder may also have an older name outside the specification,
# such as pdf_tool or PDF-Tool, which agents load as well. Such a name is
# still a single, portable folder name: it cannot be '.' or '..', start with
# a dot (as the staging and backup folders do) or hold a separator.
_LEGACY_FOLDER_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*')
FOLDER_NAME_RULE = (
    'at most 64 letters, digits, dots, underscores and hyphens, beginning '
    'with a letter or digit'
)

# The names Windows reads as a device or as another name are refused only
# there; other systems, like the service, take them as they are.
_ON_WINDOWS = os.name == 'nt'

# Windows device names, which name a device rather than a file whatever the
# extension (CON and con.txt alike, and CON .txt, whose spaces Windows drops).
# Windows also counts the superscript digits 1, 2 and 3 as COM and LPT ports.
_WINDOWS_DEVICE_NAME = re.compile(
    r'(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9\u00b9\u00b2\u00b3]'
    r'|LPT[1-9\u00b9\u00b2\u00b3]) *(?:\..*)?',
    re.IGNORECASE,
)

# Characters Windows does not allow in a file name. ZipFile.extractall
# replaces them there; this extractor refuses them on every system instead.
_UNPORTABLE_CHARACTERS = re.compile(r'[\x00-\x1f<>:"|?*]')

# The hex SHA-256 digest published in a record's ``artifact``.
SHA256_HEX = re.compile(r'[0-9a-f]{64}')

# A skill package has this file at its root.
SKILL_MARKER = 'SKILL.md'

# The spellings of SKILL.md the service accepts, in its order of preference.
# A skill.md is installed as SKILL.md, so agents on case-sensitive file
# systems find it.
_SKILL_MD_NAMES = ('SKILL.md', 'skill.md')

# The most of SKILL.md read for its frontmatter, as much as the service reads
# (VestryCommon SkillZipLimits.MAX_SKILL_MD_BYTES). The frontmatter opens and
# closes with a line of just this.
_MAX_SKILL_MD_BYTES = 100 * 1024
_FRONTMATTER_FENCE = b'---'

# Written at the root of every skill this command installs, so every later
# run can tell whether a folder came from the same registry, endpoint and
# record, and whether it is up to date. An archive cannot contain it. It holds
# no secrets.
PROVENANCE_MARKER = '.agent-registry-skill.json'
_PROVENANCE_FIELDS = ('registryId', 'recordId', 'endpoint', 'sha256')

# What an install holds, recorded in the marker as ``content``: the record's
# package, or only the SKILL.md text the record publishes when it has no
# package. A marker without the field predates it, so holds a package. Its
# sha256 is the package's, or that of the SKILL.md bytes written.
CONTENT_PACKAGE = 'package'
CONTENT_SKILL_MD = 'skillMd'
_CONTENT_LABELS = {CONTENT_PACKAGE: 'package', CONTENT_SKILL_MD: 'SKILL.md'}

# The most text a record's SKILL.md can hold (the service's DescriptorData).
MAX_SKILL_MD_CHARACTERS = 102_400
_MAX_PROVENANCE_BYTES = 64 * 1024

# Names an archive cannot contain, and what each is reserved for. agent-toolkit
# takes a folder holding its metadata file for a skill it installed, and
# would update or replace it as one.
_RESERVED_NAMES = {
    PROVENANCE_MARKER: (
        'the file in which install-skill notes where a skill came from'
    ),
    SKILL_METADATA_FILENAME: "agent-toolkit's install metadata",
}

# Zip errors from a damaged archive, an unsupported compression method or a
# corrupt compressed stream.
_ZIP_ERRORS = (zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError)

# --agent is agent-toolkit's own argument, so the agent ids and their skills
# folders are the same in both commands.
AGENT_ARGUMENT = dict(
    AGENT_ARG,
    help_text=(
        AGENT_ARG['help_text']
        + ' Cannot be combined with <code>--target-directory</code>.'
    ),
)


def _windows_unsafe(segment):
    """True on Windows for a name it reads as a device or as another name.

    Windows drops a trailing dot or space, so ``pdf-extract.`` is the same
    folder as ``pdf-extract``. Other systems keep such names as they are, so
    there they are not refused.
    """
    return _ON_WINDOWS and bool(
        _WINDOWS_DEVICE_NAME.fullmatch(segment) or segment.endswith(('.', ' '))
    )


def is_spec_skill_name(name):
    """True if ``name`` is in the Agent Skills specification's form here.

    On Windows, a device name such as ``con`` is not.
    """
    return (
        isinstance(name, str)
        and len(name) <= MAX_SKILL_NAME_LENGTH
        and bool(SKILL_NAME.fullmatch(name))
        and not _windows_unsafe(name)
    )


def folder_name_problem(name):
    """Why ``name`` cannot name a skill's folder here, or None if it can.

    A name in the Agent Skills specification's form can, and so can an older
    one of :data:`FOLDER_NAME_RULE`. On Windows, a device name such as
    ``con``, or a name ending in a dot, is refused too.
    """
    if is_spec_skill_name(name):
        return None
    if (
        isinstance(name, str)
        and len(name) <= MAX_SKILL_NAME_LENGTH
        and _LEGACY_FOLDER_NAME.fullmatch(name)
        and not _windows_unsafe(name)
    ):
        return None
    windows_rule = (
        ', and must not be a Windows device name such as CON or NUL or end '
        'in a dot'
        if _ON_WINDOWS
        else ''
    )
    return (
        f"a skill's folder name must be a skill name under the Agent Skills "
        f'specification ({SKILL_NAME_RULE}) or, for an older skill, '
        f'{FOLDER_NAME_RULE}{windows_rule}'
    )


def safe_folder_name(name):
    """``name``, if it can name a skill's folder on this system.

    Either a name in the Agent Skills specification's form or an older one
    of :data:`FOLDER_NAME_RULE`, as :func:`folder_name_problem` decides.
    """
    problem = folder_name_problem(name)
    if problem:
        raise AgentRegistryJWTError(
            f'Refusing a skill named {printable(repr(name))}: {problem}.'
        )
    return name


def skill_path(target_root, name):
    """Resolve ``target_root/name``, guaranteeing a direct child of the root."""
    root = os.path.realpath(target_root)
    path = os.path.join(root, safe_folder_name(name))
    if os.path.dirname(os.path.realpath(path)) != root:
        raise AgentRegistryJWTError(
            f'Refusing {path}: it resolves outside {root}.'
        )
    return path


def is_installed_skill(path):
    """True for a real directory with a ``SKILL.md`` at its root."""
    return (
        not os.path.islink(path)
        and os.path.isdir(path)
        and os.path.isfile(os.path.join(path, SKILL_MARKER))
    )


def read_provenance(skill_dir):
    """Where the skill in ``skill_dir`` came from, or None if unknown.

    The marker must be a regular file of at most 64 KiB holding a JSON object
    whose fields are all strings, ``content`` included if it is there.
    Anything else, including a symlink, counts as unknown, and nothing here
    raises. A ``content`` this version doesn't know, from a newer AWS CLI, is
    kept as it is: such a skill is listed and can be uninstalled, but
    install-skill never replaces it.
    """
    path = os.path.join(skill_dir, PROVENANCE_MARKER)
    try:
        info = os.lstat(path)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_size > _MAX_PROVENANCE_BYTES
        ):
            return None
        # No following links, and no blocking if the file was just swapped
        # for a FIFO; fstat checks what was actually opened.
        flags = (
            os.O_RDONLY
            | getattr(os, 'O_NOFOLLOW', 0)
            | getattr(os, 'O_NONBLOCK', 0)
            | getattr(os, 'O_BINARY', 0)
        )
        fd = os.open(path, flags)
        with os.fdopen(fd, 'rb') as f:
            if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
                return None
            data = f.read(_MAX_PROVENANCE_BYTES + 1)
        if len(data) > _MAX_PROVENANCE_BYTES:
            return None
        marker = json.loads(data)
    except (OSError, ValueError, RecursionError):
        return None
    if not isinstance(marker, dict) or not all(
        isinstance(marker.get(field), str) for field in _PROVENANCE_FIELDS
    ):
        return None
    content = marker.get('content', CONTENT_PACKAGE)
    if not isinstance(content, str):
        return None
    installed = {field: marker[field] for field in _PROVENANCE_FIELDS}
    installed['content'] = content
    return installed


def source_key(source):
    """What tells one source apart: its registry, record and endpoint."""
    return (
        source['registryId'],
        source['recordId'],
        comparable_endpoint(source['endpoint']),
    )


def same_source(installed, source):
    """True if both came from the same registry and record at one endpoint."""
    return source_key(installed) == source_key(source)


def is_known_content(installed):
    """True unless ``installed`` holds content only a newer AWS CLI knows."""
    return installed['content'] in _CONTENT_LABELS


def keeps_package(installed, source):
    """True if ``installed`` is the package and ``source`` only SKILL.md.

    A package record always carries its SKILL.md text as well, and the
    registry may leave out the package's download URL, so a record that
    offers only the text may still have the package. The package installed
    is then kept unless ``--force`` asks for the text alone.
    """
    return (
        installed['content'] == CONTENT_PACKAGE
        and source['content'] == CONTENT_SKILL_MD
    )


def same_content(installed, source):
    """True if both hold the same kind of content with the same SHA-256."""
    return (
        installed['content'] == source['content']
        and installed['sha256'] == source['sha256']
    )


def installed_skills(folder):
    """Every skill install-skill installed in ``folder``, whatever its name.

    Each is ``(name, path, marker)``, sorted by name, for a direct child of
    ``folder`` that is a real directory (not a symbolic link) with a valid
    folder name, a ``SKILL.md`` and a readable provenance marker. The
    staging and backup folders start with a dot, so they are skipped. At most
    :data:`MAX_SCANNED_ENTRIES` entries are looked at, and each marker is read
    once. An entry that cannot be read is skipped, and a folder that is
    missing or cannot be listed holds none.
    """
    root = os.path.realpath(folder)
    found = []
    try:
        with os.scandir(root) as entries:
            for count, entry in enumerate(entries):
                if count >= MAX_SCANNED_ENTRIES:
                    logger.debug(
                        'Looked at the first %d entries of %s only.',
                        MAX_SCANNED_ENTRIES,
                        root,
                    )
                    break
                try:
                    skill = _installed_skill(entry)
                except OSError as e:
                    logger.debug('Skipping %s: %r', entry.path, e)
                    continue
                if skill is not None:
                    found.append(skill)
    except OSError as e:
        # Also an error while listing, after which the skills already found
        # are kept.
        logger.debug('Could not read the skills folder %s: %r', root, e)
    return sorted(found, key=lambda item: item[0])


def _installed_skill(entry):
    """``(name, path, marker)`` for a skill install-skill installed, or None.

    ``entry`` is a :func:`os.scandir` entry of a skills folder.
    """
    if (
        entry.name.startswith('.')
        or entry.is_symlink()
        or folder_name_problem(entry.name)
        or not is_installed_skill(entry.path)
    ):
        return None
    marker = read_provenance(entry.path)
    if marker is None:
        return None
    try:
        source_key(marker)
    except ValueError:
        # An endpoint urllib cannot parse matches no source.
        return None
    return entry.name, entry.path, marker


def installed_copies(folder, source):
    """The skills in ``folder`` that install-skill installed from ``source``.

    Found by their provenance markers, whatever their folders' names, as
    :func:`installed_skills` finds them.
    """
    return [
        (name, path, marker)
        for name, path, marker in installed_skills(folder)
        if same_source(marker, source)
    ]


def source_detail(marker, with_endpoint=False):
    """``registry A, record R``, and `` at E`` with the endpoint."""
    detail = (
        f'registry {printable(marker["registryId"])}, record '
        f'{printable(marker["recordId"])}'
    )
    if with_endpoint:
        detail += f' at {printable(marker["endpoint"])}'
    return detail


def describe_source(marker):
    """``from registry A, record R``."""
    return f'from {source_detail(marker)}'


def resolve_skill_folders(parsed_args, agent_configs=None):
    """The skills folders a command acts on.

    Each is ``(agent name, folder, agent id)``. ``--target-directory`` names
    one folder, with no agent. Otherwise the
    folders are those of the agent named by ``--agent``, or of every detected
    agent, resolved the same way ``aws agent-toolkit`` resolves them. Several
    agents share ``~/.agents/skills``, so a folder is listed once, for the
    first agent that uses it.
    """
    agent_filter = getattr(parsed_args, 'agent', None)
    target_directory = getattr(parsed_args, 'target_directory', None)
    if agent_filter and target_directory:
        raise ParamValidationError(
            '--agent and --target-directory cannot be used together.'
        )
    if target_directory:
        return [(None, os.path.expanduser(target_directory), None)]
    folders = []
    seen = set()
    agents = resolve_agents(agent_filter, agent_configs)
    for agent in universal_first(agents):
        real_path = os.path.realpath(agent.skills_path)
        if real_path in seen:
            continue
        seen.add(real_path)
        folders.append(
            (agent.display_name, agent.skills_path, agent.config.id)
        )
    return folders


def report(agent, message):
    """One result line, naming the agent when there is one."""
    write_status(f'{agent}: {message}' if agent else message)


def is_s3_host(host, region):
    """True for an Amazon S3 endpoint in ``region``.

    Covers virtual-hosted and path-style URLs, dual-stack, FIPS and access-point
    endpoints, the legacy dash-region form, and the us-east-1 global endpoint.
    """
    host = (host or '').lower()
    r = re.escape(region)
    bucket = r'(?:[a-z0-9][a-z0-9.-]*\.)?'
    patterns = [
        rf'^{bucket}(?:s3|s3-fips|s3-accesspoint|s3-accesspoint-fips)'
        rf'(?:\.dualstack)?\.{r}\.amazonaws\.com(?:\.cn)?$',
        rf'^{bucket}s3-{r}\.amazonaws\.com$',
    ]
    if region == 'us-east-1':
        patterns.append(rf'^{bucket}s3\.amazonaws\.com$')
    return any(re.match(pattern, host) for pattern in patterns)


def validate_download_url(url, region):
    require_https(url, 'download URL')
    host = urllib.parse.urlsplit(url).hostname
    if not is_s3_host(host, region):
        # The origin only: a presigned URL's query string is a credential.
        raise AgentRegistryJWTError(
            f'Refusing to download from {url_origin(url)}: the download URL '
            f'must point at Amazon S3 in {region}.'
        )
    return url


class InstallSkillCommand(BasicCommand):
    """Install a single skill by registry id and record id or name."""

    NAME = 'install-skill'
    DESCRIPTION = (
        'Downloads a skill from a registry, verifies it against the SHA-256 '
        'digest published on the record, and extracts it into the skills '
        'folder of every detected AI coding agent, the agent named by '
        '``--agent``, or ``--target-directory``.\n\n'
        'Name the record with ``--record-id``, or with ``--record-name``: '
        "the record's own name, as ``list-skills`` shows it in ``name``, "
        'not the name in its ``SKILL.md`` (``skillName`` in '
        '``list-skills``). That name is looked up among every page of the '
        "registry's ``SKILL`` records with "
        '``ListDiscoverableRegistryRecords``, with the same credentials or '
        'sign-in as the rest of the command, so it also needs the '
        '``agent-registry:ListDiscoverableRegistryRecords`` permission. It '
        "is compared exactly, case included, with each record's ``name``. "
        'The command says which record id the name resolved to. It refuses '
        'a name no skill record has, and a name more than one skill record '
        'has, listing their record ids so that you can choose one with '
        '``--record-id``.\n\n'
        'The archive is fetched directly from storage using the short-lived '
        'download URL in the record\'s ``artifact``, so the bytes do '
        'not pass through the service fleet. Installation is refused if the '
        'digest does not match, because skills carry executable content. The '
        'archive is downloaded and verified once, then installed into each '
        'folder in turn; a failure in one folder does not stop the '
        'others.\n\n'
        'A record with no downloadable package that holds the text of its '
        '``SKILL.md`` is installed from that text, as it is: only '
        '``SKILL.md`` is installed, nothing is downloaded, and the command '
        'says so. A ``SKILL.md`` the record only links to is never fetched, '
        'so such a record is refused, as is a record with neither. A skill '
        "installed from the record's package is kept, though, when the "
        'record offers only its ``SKILL.md`` text, because the registry can '
        'leave the package out; pass ``--force`` to replace it with the text '
        'alone.\n\n'
        'The Agent Skills specification requires a skill\'s folder to have '
        "the skill's name, so the command installs the skill in a folder "
        "named after the ``name`` in the frontmatter of the package's "
        '``SKILL.md``, whatever the record is named, and says so when the '
        'two names differ. The ``SKILL.md`` name is checked before anything '
        'is written. A valid skill name '
        f'({SKILL_NAME_RULE}) is installed as it is. A name outside the '
        f'specification, but still {FOLDER_NAME_RULE}, is installed with a '
        'warning, because some agents may not load it; any other name is '
        'refused. If the package wraps its files in a single top-level '
        'folder, the command installs them without that folder, whatever its '
        'name.\n\n'
        'Each install records its registry, endpoint, record, SHA-256 and '
        'whether it holds the package or only ``SKILL.md`` in '
        f'``{PROVENANCE_MARKER}`` at the root of the skill. Rerunning '
        'install-skill updates a skill it installed to the package now '
        'published on the record, and leaves an up-to-date one as it is, '
        'finding it by that marker whatever its folder is named. If the '
        "skill's ``SKILL.md`` name has changed, the skill is installed under "
        'the new name, and the earlier install is reported, not removed. A '
        'folder holding a skill from another registry, endpoint or record, '
        'one this command did not install, or one a newer version of the AWS '
        'CLI installed, is never replaced. The '
        'command exits non-zero if any folder was refused or could not be '
        'installed. Find the skills a registry offers with '
        '``list-skills``, and uninstall a skill with '
        '``uninstall-skill``.\n\n' + SIGN_IN_DESCRIPTION
    )
    ARG_TABLE = [
        {
            'name': 'registry-id',
            'required': True,
            'help_text': 'The registry holding the skill.',
        },
        {
            'name': 'record-id',
            'help_text': (
                'The record to install, given as an id or an ARN. Specify '
                'either this or <code>--record-name</code>.'
            ),
        },
        {
            'name': 'record-name',
            'help_text': (
                "The record's own name, as <code>list-skills</code> shows "
                'it in <code>name</code>, matched exactly, case included. '
                "The name in the record's <code>SKILL.md</code>, "
                '<code>skillName</code> in <code>list-skills</code>, is not '
                'matched. A name more than one skill record has is refused, '
                'with their record ids. Looking the name up also needs the '
                '<code>agent-registry:ListDiscoverableRegistryRecords</code> '
                'permission. Specify either this or <code>--record-id</code>.'
            ),
        },
        AGENT_ARGUMENT,
        {
            'name': 'target-directory',
            'help_text': (
                'Directory to install into instead of the skills folders of '
                'the detected agents. The command places the skill in a '
                "subdirectory named after the skill's name in its "
                '<code>SKILL.md</code>. Cannot be combined with '
                '<code>--agent</code>.'
            ),
        },
        *SIGN_IN_ARGUMENTS,
        {
            'name': 'force',
            'action': 'store_true',
            'help_text': (
                'Reinstall even if the installed copy is already up to date, '
                "and replace a copy of the record's package with its "
                '<code>SKILL.md</code> text when the record offers only the '
                'text. A skill installed from another registry, endpoint or '
                'record, or by anything other than this command, is never '
                'replaced.'
            ),
        },
    ]

    def __init__(self, session, agent_configs=None):
        super().__init__(session)
        if agent_configs is None:
            agent_configs = AGENT_CONFIGS
        self._agent_configs = agent_configs

    def _run_main(self, parsed_args, parsed_globals):
        # Before any network call, so a bad combination or a machine with no
        # agent fails fast.
        wanted_name = parsed_args.record_name
        if bool(parsed_args.record_id) == bool(wanted_name):
            raise ParamValidationError(
                'Specify exactly one of --record-id and --record-name.'
            )
        folders = resolve_skill_folders(parsed_args, self._agent_configs)
        if not folders:
            raise ParamValidationError(
                'No supported AI coding agents found. Pass --target-directory '
                '<dir> to install into a folder of your choice, or --agent '
                '<id> once that agent is set up on this machine.'
            )
        data_plane = create_data_plane_client(
            self._session, parsed_args, parsed_globals
        )

        requested = parsed_args.record_id
        if wanted_name:
            # The same listing, client and sign-in as list-skills.
            requested = _resolve_record_name(
                data_plane.client, parsed_args.registry_id, wanted_name
            )
            write_status(
                f'Record {printable(repr(wanted_name))} is '
                f'{printable(requested)}.'
            )
        record = self._get_record(
            data_plane.client, parsed_args.registry_id, requested
        )
        record_id = _record_id(record, requested)
        record_name = record.get('name')
        shown = _record_display_name(record, record_id)
        kind, payload, digest = _read_content(record, requested)
        source = {
            'registryId': bare_registry_id(parsed_args.registry_id),
            'recordId': record_id,
            # Recorded with each install, so every later run can tell where
            # it came from.
            'endpoint': data_plane.endpoint,
            'sha256': digest,
            'content': kind,
        }

        pending = []
        failed = False
        for agent, folder, agent_id in folders:
            # Found by their markers, whatever their folders are named, so
            # this needs no download to learn the SKILL.md name.
            copies = installed_copies(folder, source)
            newer = [
                path
                for _, path, marker in copies
                if not is_known_content(marker)
            ]
            if newer:
                report(agent, _newer_install(newer[0]))
                failed = True
                continue
            if not parsed_args.force:
                left = [
                    (_UP_TO_DATE, name, path, marker)
                    for name, path, marker in copies
                    if same_content(marker, source)
                ] + [
                    (_KEPT, name, path, marker)
                    for name, path, marker in copies
                    if keeps_package(marker, source)
                ]
                if left:
                    action, name, path, marker = left[0]
                    report(agent, _outcome(action, name, path, marker, source))
                    _report_earlier_copies(
                        agent, copies, path, folder, agent_id
                    )
                    continue
            pending.append((agent, folder, agent_id, copies))
        if not pending:
            # Nothing to install or update anywhere, so nothing is
            # downloaded.
            return 1 if failed else 0

        if kind == CONTENT_SKILL_MD:
            # Nothing is downloaded: the text came with the record. Its name
            # is checked before saying what is installed.
            declared, unreadable = _frontmatter_name_from_bytes(
                payload, "the record's SKILL.md"
            )
            name = _named(declared, unreadable, shown)
            write_status(
                f'Installing the SKILL.md text published on record '
                f'{printable(record_id)}; the record has no package, so only '
                f'SKILL.md is installed.'
            )
            _note_record_name(record_name, name)
            return self._install_all(
                pending,
                name,
                lambda staged: _write_skill_md(staged, payload),
                source,
                parsed_args.force,
                failed,
            )

        url = validate_download_url(payload, data_plane.region)
        with tempfile.TemporaryDirectory(prefix='agent-registry-') as scratch:
            archive = os.path.join(scratch, 'package.zip')
            write_status(f'Downloading {shown} from {url_origin(url)}...')
            self._download(url, archive, data_plane.ca_bundle)

            actual = _sha256(archive)
            if not hmac.compare_digest(actual, digest):
                raise AgentRegistryJWTError(
                    f'Refusing to install {shown}: the archive does not match '
                    f'the SHA-256 digest published on the record.\n'
                    f'  expected {digest}\n'
                    f'  actual   {actual}'
                )
            write_status(f'Verified SHA-256 {digest}')
            # Once, so a bad archive is reported once rather than per folder.
            # The skill is installed under the name in its SKILL.md, whatever
            # the record's name.
            name = _check_archive(archive, shown)
            _note_record_name(record_name, name)
            return self._install_all(
                pending,
                name,
                lambda staged: _safe_extract(archive, staged),
                source,
                parsed_args.force,
                failed,
            )

    def _install_all(self, pending, name, populate, source, force, failed):
        """Install into each pending folder in turn; 1 if any failed.

        ``failed`` says whether a folder already failed before.
        """
        for agent, folder, agent_id, copies in pending:
            if not self._install_into(
                populate, name, agent, folder, agent_id, copies, source, force
            ):
                failed = True
        return 1 if failed else 0

    def _install_into(
        self, populate, name, agent, folder, agent_id, copies, source, force
    ):
        """Install the skill into one skills folder; False if that failed.

        ``copies`` are the skills install-skill installed there from
        ``source`` before this run. One under another name, from a SKILL.md
        name the record no longer has, is reported, not removed.
        """
        uninstall = _uninstall_command(name, folder, agent_id)
        try:
            destination = skill_path(folder, name)
            action, installed = _plan_destination(
                destination, name, force, source, uninstall
            )
        except AgentRegistryJWTError as e:
            report(agent, str(e))
            return False
        if action not in _LEFT_AS_IT_IS:
            try:
                action, installed = _install(
                    populate, name, destination, source, force, uninstall
                )
            except _Refused as e:
                # Another run changed the folder since the first check.
                report(agent, str(e))
                return False
            except (AgentRegistryJWTError, OSError) as e:
                report(
                    agent,
                    f'Could not install {name} to {destination}: '
                    f'{printable(e)}',
                )
                return False
        report(agent, _outcome(action, name, destination, installed, source))
        _report_earlier_copies(agent, copies, destination, folder, agent_id)
        return True

    def _get_record(self, client, registry_id, record_id):
        response = client.batch_get_discoverable_registry_record(
            entries=[{'registryId': registry_id, 'recordIds': [record_id]}]
        )
        records = response.get('registryRecords') or []
        for record in records:
            if isinstance(record, dict) and _is_record(record, record_id):
                return record
        errors = [
            error
            for error in response.get('errors') or []
            if isinstance(error, dict)
        ]
        if errors:
            # The service chooses this text.
            details = '; '.join(
                f'{printable(error.get("errorCode")) or "error"}: '
                f'{printable(error.get("message"))}'
                for error in errors
            )
            raise AgentRegistryJWTError(
                f'Could not get record {record_id} from registry '
                f'{registry_id}: {details}'
            )
        if records:
            raise AgentRegistryJWTError(
                f'The registry returned a record other than {record_id}, so '
                f'nothing was installed.'
            )
        raise AgentRegistryJWTError(
            f'Record {record_id} was not found in registry {registry_id}, '
            f'or you are not entitled to it.'
        )

    def _download(self, url, destination, ca_bundle=None):
        # Messages name the origin only: the query string is a credential.
        origin = url_origin(url)
        try:
            with urlopen(
                url,
                timeout=HTTP_TIMEOUT,
                purpose='download URL',
                ca_bundle=ca_bundle,
            ) as response:
                written = 0
                with open(destination, 'wb') as f:
                    while True:
                        chunk = response.read(_CHUNK_BYTES)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > MAX_ARCHIVE_BYTES:
                            raise AgentRegistryJWTError(
                                f'Archive exceeds {MAX_ARCHIVE_BYTES} bytes; '
                                f'refusing to continue.'
                            )
                        f.write(chunk)
        except urllib.error.HTTPError as e:
            # A presigned URL that has expired reports 403, which is worth
            # distinguishing from an authorization problem with the registry.
            hint = (
                ' The download URL may have expired; run the command again.'
                if e.code == 403
                else ''
            )
            raise AgentRegistryJWTError(
                f'Download from {origin} failed with HTTP {e.code}.{hint}'
            )
        except urllib.error.URLError as e:
            reason = redact_secrets(printable(e.reason))
            raise AgentRegistryJWTError(
                f'Download from {origin} failed: {reason}'
            )
        except (OSError, http.client.HTTPException) as e:
            # A read that times out or stops short, after the connection was
            # made.
            raise AgentRegistryJWTError(
                f'Download from {origin} failed: '
                f'{redact_secrets(printable(e)) or type(e).__name__}'
            )


class _Refused(AgentRegistryJWTError):
    """The destination must not be written to."""


# What to do with a destination folder.
_INSTALL = 'install'
_UPDATE = 'update'
_REINSTALL = 'reinstall'
_UP_TO_DATE = 'up to date'
# The package is kept: the record now offers only its SKILL.md text.
_KEPT = 'kept'
_LEFT_AS_IT_IS = (_UP_TO_DATE, _KEPT)


def _outcome(action, name, destination, installed, source):
    """The result line for a folder that was not refused."""
    if action == _UP_TO_DATE:
        return f'{name} is already up to date at {destination}.'
    if action == _KEPT:
        return (
            f"{name} at {destination} holds the record's package; the record "
            f'now publishes no downloadable package, so it was left as it '
            f'is. Pass --force to replace it with the SKILL.md text only.'
        )
    if action == _UPDATE:
        old = f'{printable(installed["sha256"])[:12]}\u2026'
        new = f'{source["sha256"][:12]}\u2026'
        if installed['content'] != source['content']:
            old = f'{_content_label(installed)} {old}'
            new = f'{_content_label(source)} {new}'
        return f'Updated {name} at {destination} ({old} \u2192 {new}).'
    if action == _REINSTALL:
        return f'Reinstalled {name} at {destination}.'
    return f'Installed {name} to {destination}'


def _content_label(marker):
    """How a result line names what ``marker`` says an install holds."""
    content = marker['content']
    return _CONTENT_LABELS.get(content) or printable(repr(content))


def _newer_install(destination):
    """The refusal for a skill a newer AWS CLI installed."""
    return (
        f'Refusing to replace {destination}: it was installed by a newer '
        f'version of the AWS CLI, which this one does not understand. Update '
        f'the AWS CLI to install or update the skill here.'
    )


def _same_file(first, second):
    """True if both paths are one file, False also if either is missing."""
    try:
        return os.path.samefile(first, second)
    except OSError:
        return False


def _report_earlier_copies(agent, copies, destination, folder, agent_id):
    """Report each of ``copies`` other than ``destination``; none is removed.

    ``copies`` are the skills install-skill installed in ``folder`` from the
    same source before this run, as :func:`installed_copies` returns them.
    """
    for earlier, path, _ in copies:
        if os.path.lexists(path) and not _same_file(path, destination):
            report(
                agent,
                f'An earlier install of this record is at {path}; '
                f'uninstall it with '
                f'{_uninstall_command(earlier, folder, agent_id)} if you '
                f'no longer need it.',
            )


def _uninstall_command(name, folder, agent_id):
    """The uninstall-skill command for the skill in ``folder``, to run."""
    command = ['aws', 'agent-registry', 'uninstall-skill', '--name', name]
    if agent_id:
        command += ['--agent', agent_id]
    else:
        command += ['--target-directory', folder]
    return ' '.join(shlex.quote(part) for part in command)


def _plan_destination(destination, name, force, source, uninstall):
    """What to do with ``destination``, as ``(action, installed marker)``.

    A missing folder is installed. A skill this command installed from the
    same ``source`` is updated if its SHA-256 or kind of content differs,
    and is otherwise up to date, or reinstalled with ``force``; but the
    package is kept (:func:`keeps_package`) unless ``force``. Anything else,
    also a skill a newer AWS CLI installed, raises ``_Refused``.
    ``uninstall`` is the command that would uninstall the folder's skill,
    for the advice in a refusal.
    """
    if os.path.islink(destination):
        raise _Refused(
            f'Refusing to replace {destination}: it is a symbolic link.'
        )
    if not os.path.lexists(destination):
        return _INSTALL, None
    if not is_installed_skill(destination):
        raise _Refused(
            f'Refusing to replace {destination}: it has no {SKILL_MARKER} at '
            f'its root, so it is not an installed skill.'
        )
    installed = read_provenance(destination)
    if installed is not None and not is_known_content(installed):
        # Even with --force: an older CLI never overwrites a newer one's.
        raise _Refused(_newer_install(destination))
    if installed is not None and same_source(installed, source):
        if keeps_package(installed, source) and not force:
            return _KEPT, installed
        if not same_content(installed, source):
            return _UPDATE, installed
        return (_REINSTALL if force else _UP_TO_DATE), installed
    # Another source or an unknown one: --force does not replace it either,
    # so say what would.
    elsewhere = (
        'install into another folder with --agent or --target-directory'
    )
    if installed is None:
        # Also a damaged, oversized or symlinked marker, so this does not
        # claim the skill came from another tool. uninstall-skill skips such a
        # folder too, so it is not offered.
        raise _Refused(
            f'Refusing to replace {destination}: it has no readable '
            f"{PROVENANCE_MARKER}, so this command can't tell where it came "
            f'from. Move or delete the folder yourself, or {elsewhere}.'
        )
    with_endpoint = comparable_endpoint(
        installed['endpoint']
    ) != comparable_endpoint(source['endpoint'])
    raise _Refused(
        f'Refusing to replace {destination}: it was installed from '
        f'{source_detail(installed, with_endpoint)}, not '
        f'{source_detail(source, with_endpoint)}. Uninstall it first with '
        f'{uninstall}, or {elsewhere}.'
    )


def _resolve_record_name(client, registry_id, name):
    """The id of the registry's one skill record named ``name``.

    The record's own name is matched, exactly; never the name in its
    SKILL.md. The model says record names are unique within a registry, but
    registries hold same-named records, so every page is read and more than
    one record with the name is refused, listing each. A record listed more
    than once is one match. A record without an id cannot be installed, so
    it never matches.
    """
    matches = {}
    for page in skill_record_pages(client, registry_id):
        for record in page:
            record_id = record.get('recordId')
            if (
                record.get('name') == name
                and isinstance(record_id, str)
                and record_id
            ):
                matches.setdefault(record_id, record.get('recordVersion'))
    if len(matches) == 1:
        return next(iter(matches))
    if matches:
        found = ', '.join(
            _match_detail(record_id, version)
            for record_id, version in matches.items()
        )
        raise AgentRegistryJWTError(
            f'Registry {printable(registry_id)} has more than one skill '
            f'record named {printable(repr(name))}: {found}. Pass '
            f'--record-id to choose one.'
        )
    raise AgentRegistryJWTError(
        f'Registry {printable(registry_id)} has no skill record named '
        f"{printable(repr(name))}; --record-name matches the record's name "
        f'(name in list-skills), not its SKILL.md name (skillName). Run aws '
        f'agent-registry list-skills --registry-id {printable(registry_id)} '
        f'to see the names.'
    )


def _match_detail(record_id, version):
    """A record named in a refusal: its id, and its version if it has one."""
    if isinstance(version, str) and version:
        return f'{printable(record_id)} ({printable(version)})'
    return printable(record_id)


def _record_display_name(record, record_id):
    """What messages call the record: its name, or its id if it has none.

    The record's name is not checked: the skill is installed under the name
    in its SKILL.md. The registry chooses both, so the result is printable.
    """
    name = record.get('name')
    return printable(name if isinstance(name, str) and name else record_id)


def _note_record_name(record_name, name):
    """Say so if the record's name is not the skill's, ``name``."""
    if isinstance(record_name, str) and record_name not in ('', name):
        write_status(
            f'Record {printable(repr(record_name))} installs as skill '
            f'{printable(repr(name))}.'
        )


def _record_id(record, record_id):
    """The bare id of the record, also when it was requested by ARN."""
    found = record.get('recordId')
    if isinstance(found, str) and found:
        return found
    return record_id.rpartition('/record/')[2]


def _is_record(record, record_id):
    """True if ``record`` is the one requested by id or ARN."""
    if record_id in (record.get('recordId'), record.get('recordArn')):
        return True
    # A record ARN ends in /record/<record id>.
    prefix, marker, bare_id = record_id.rpartition('/record/')
    return bool(marker) and bare_id == record.get('recordId')


def _read_content(record, record_id):
    """What the record publishes to install, as ``(kind, payload, sha256)``.

    The record's package, if it has a downloadable one: ``(CONTENT_PACKAGE,
    downloadUrl, sha256)``. The digest is checked for shape here so that a
    malformed one fails clearly instead of as a mismatch after the download,
    and a package with one is refused rather than replaced by the text.
    Otherwise the SKILL.md text the record holds: ``(CONTENT_SKILL_MD,
    bytes, sha256 of those bytes)``. A SKILL.md the record only links to is
    never fetched.
    """
    shown = printable(record_id)
    artifact = record.get('artifact')
    if not isinstance(artifact, dict):
        artifact = {}
    url = artifact.get('downloadUrl')
    if url:
        digest = artifact.get('sha256')
        if not isinstance(digest, str) or not SHA256_HEX.fullmatch(digest):
            raise AgentRegistryJWTError(
                f'Record {shown} does not publish a valid SHA-256 digest '
                f'for its package (64 lowercase hexadecimal characters), so '
                f'the download cannot be verified.'
            )
        return CONTENT_PACKAGE, url, digest
    skill_md = _skill_md_descriptor(record)
    data = skill_md.get('data')
    if isinstance(data, str) and data.strip():
        data = _skill_md_bytes(data, shown)
        return CONTENT_SKILL_MD, data, hashlib.sha256(data).hexdigest()
    source = skill_md.get('source')
    from_url = source.get('fromUrl') if isinstance(source, dict) else None
    link = from_url.get('url') if isinstance(from_url, dict) else None
    if isinstance(link, str) and link:
        # The origin only, as for any URL a message shows.
        raise AgentRegistryJWTError(
            f'Record {shown} publishes its SKILL.md only as a link to '
            f'{printable(url_origin(link))}. install-skill does not fetch '
            f'from hosts a publisher chooses; the publisher must upload a '
            f'package or put the SKILL.md text in the record.'
        )
    raise AgentRegistryJWTError(
        f'Record {shown} has no downloadable package and no SKILL.md '
        f'text, so there is nothing to install.'
    )


def _skill_md_descriptor(record):
    """The record's ``descriptors.agentSkillsDefinition.additionalData
    .skillMd``, or ``{}`` if any level is missing or not a mapping."""
    found = record
    for key in ('descriptors', 'agentSkillsDefinition', 'additionalData'):
        found = found.get(key)
        if not isinstance(found, dict):
            return {}
    found = found.get('skillMd')
    return found if isinstance(found, dict) else {}


def skill_md_name(record):
    """The name in the SKILL.md text a record holds, or None.

    None also if the record holds no text, or text install-skill would
    refuse: too long, not valid text, without a readable frontmatter name,
    or with a name that cannot name a skill's folder. Nothing is printed.
    """
    data = _skill_md_descriptor(record).get('data')
    if not isinstance(data, str) or not data.strip():
        return None
    encoded, problem = _encoded_skill_md(data)
    if problem:
        return None
    name, _ = _frontmatter_name_from_bytes(encoded, "the record's SKILL.md")
    return name if folder_name_problem(name) is None else None


def _encoded_skill_md(data):
    """``data`` as the bytes of a SKILL.md file, as ``(bytes, None)``.

    Or ``(None, why)``. The text is written as it is, line endings included,
    so it must fit in a record (:data:`MAX_SKILL_MD_CHARACTERS`), hold no
    NUL and be valid Unicode text.
    """
    if len(data) > MAX_SKILL_MD_CHARACTERS:
        return None, (
            f'its SKILL.md text has more than the '
            f"{MAX_SKILL_MD_CHARACTERS:,} characters a record's SKILL.md can "
            f'hold'
        )
    if '\x00' in data:
        return None, 'its SKILL.md text contains a NUL character'
    try:
        return data.encode('utf-8'), None
    except UnicodeEncodeError:
        # A lone surrogate, which no file can hold as UTF-8.
        return None, 'its SKILL.md text is not valid Unicode text'


def _skill_md_bytes(data, shown):
    encoded, problem = _encoded_skill_md(data)
    if problem:
        raise AgentRegistryJWTError(
            f'Refusing to install record {shown}: {problem}.'
        )
    return encoded


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(_CHUNK_BYTES), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _collision_key(name):
    """The path an entry lands on, as a case-insensitive filesystem sees it.

    macOS and Windows filesystems ignore case, and macOS also ignores Unicode
    normalization, so two names that differ only in those ways are one file.
    """
    normalized = posixpath.normpath(name.replace('\\', '/'))
    return unicodedata.normalize('NFC', normalized).casefold()


def _damaged(error):
    # The message can repeat an entry name, which the archive chose.
    return AgentRegistryJWTError(
        f'The archive is damaged or uses an unsupported zip feature: '
        f'{printable(error)}'
    )


def _checked_entries(zf):
    """The archive's entries, after refusing any that are unsafe to extract.

    ``ZipFile.extractall`` is not safe on untrusted input: an entry named
    ``../../x`` or an absolute path writes outside the target, and a symlink
    entry can redirect later writes. Entries whose names repeat, or differ only
    in case, overwrite one another, so what is installed would depend on
    extraction order and filesystem. Skills contain executable content, so
    each entry is validated before anything is written. The sizes checked here
    are the ones the archive declares; extraction counts the real ones.
    """
    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES:
        raise AgentRegistryJWTError(
            f'Archive contains {len(infos)} entries, more than the '
            f'{MAX_ENTRIES} allowed.'
        )
    total = sum(info.file_size for info in infos)
    if total > MAX_EXTRACTED_BYTES:
        raise AgentRegistryJWTError(
            f'Archive expands to {total} bytes, more than the '
            f'{MAX_EXTRACTED_BYTES} allowed.'
        )

    names = set()
    for info in infos:
        # Entry names are attacker-controlled, so they are printed with
        # repr() to neutralise control characters.
        name = info.filename
        if name.startswith('/') or os.path.isabs(name):
            raise AgentRegistryJWTError(
                f'Refusing absolute path in archive: {name!r}'
            )
        segments = name.replace('\\', '/').split('/')
        if '..' in segments:
            raise AgentRegistryJWTError(
                f'Refusing path traversal in archive: {name!r}'
            )
        if _UNPORTABLE_CHARACTERS.search(name) or any(
            _windows_unsafe(segment)
            for segment in segments
            if segment not in ('', '.')
        ):
            raise AgentRegistryJWTError(
                f'Refusing entry whose name is not a portable file name: '
                f'{name!r}'
            )
        reserved = _reserved_name(segments)
        if reserved:
            # Otherwise an archive could claim to come from another registry,
            # or to be installed by agent-toolkit, and be replaced, or
            # replace, as if it did.
            raise AgentRegistryJWTError(
                f'Refusing entry {name!r}: the name {reserved} is reserved '
                f'for {_RESERVED_NAMES[reserved]}.'
            )
        # Mode bits 0xA000 mark a symlink; following one during extraction
        # would let a later entry write outside the destination.
        if (info.external_attr >> 16) & 0xF000 == 0xA000:
            raise AgentRegistryJWTError(
                f'Refusing symlink in archive: {name!r}'
            )
        if info.flag_bits & 0x1:
            raise AgentRegistryJWTError(
                f'Refusing encrypted entry in archive: {name!r}'
            )
        if name in names:
            raise AgentRegistryJWTError(
                f'Refusing duplicate entry in archive: {name!r}'
            )
        names.add(name)
    _check_skill_md_casing(infos)
    _check_collisions(info.filename for info in infos)
    return infos


def _check_collisions(names):
    collision_keys = set()
    for name in names:
        key = _collision_key(name)
        if key in collision_keys:
            raise AgentRegistryJWTError(
                f'Refusing entry whose path collides with another entry: '
                f'{name!r}'
            )
        collision_keys.add(key)


def _normalised(name):
    """An entry name as a path: ``/``-separated, no empty or ``.`` parts.

    A directory entry keeps its trailing ``/``, as the service's
    CanonicalPath does, so a directory named SKILL.md is never taken for the
    file.
    """
    name = name.replace('\\', '/')
    path = '/'.join(
        segment for segment in name.split('/') if segment not in ('', '.')
    )
    return f'{path}/' if path and name.endswith('/') else path


def _not_a_skill_package(message):
    # The service's wording, so the same package fails the same way.
    return AgentRegistryJWTError(f'Not a valid skill package: {message}')


def _check_skill_md_casing(infos):
    """Refuse SKILL.md spelled other than SKILL.md or skill.md, or both.

    As the service checks every folder of a package.
    """
    casings = {}
    for info in infos:
        directory, _, basename = _normalised(info.filename).rpartition('/')
        if basename.casefold() == SKILL_MARKER.casefold():
            casings.setdefault(directory, set()).add(basename)
    for spellings in casings.values():
        if len(spellings) > 1:
            raise _not_a_skill_package(
                'The package spells SKILL.md in more than one casing in one '
                'directory.'
            )
        if not spellings <= set(_SKILL_MD_NAMES):
            raise _not_a_skill_package(
                'The package spells SKILL.md in a casing other than SKILL.md '
                'or skill.md.'
            )


def _install_plan(infos):
    """Each entry with the name it is installed under, or None to skip it.

    The package layouts the service accepts: SKILL.md at the root, or, with
    none there, at the top of the package's only top-level folder, whose
    contents are installed without the folder itself. Either way a skill.md
    is installed as SKILL.md.
    """
    top_levels = set()
    candidates = set()
    enclosed = False
    for info in infos:
        path = _normalised(info.filename)
        if not path:
            continue
        segments = path.rstrip('/').split('/')
        top_levels.add(segments[0])
        if path.endswith('/'):
            # A directory, whatever its name.
            continue
        if len(segments) == 1 and path in _SKILL_MD_NAMES:
            candidates.add(path)
        elif len(segments) == 2 and segments[1] in _SKILL_MD_NAMES:
            candidates.add(path)
            enclosed = True

    def preferred(folder):
        for skill_md in _SKILL_MD_NAMES:
            if folder + skill_md in candidates:
                return folder + skill_md
        return None

    skill_md = preferred('')
    if skill_md and enclosed:
        raise _not_a_skill_package(
            'The package has a SKILL.md at its root and another at the top '
            'of a directory.'
        )
    if not skill_md and len(top_levels) > 1:
        raise _not_a_skill_package(
            'The package has more than one top-level entry and no SKILL.md '
            'at its root.'
        )
    if not skill_md and top_levels:
        skill_md = preferred(next(iter(top_levels)) + '/')
    if not skill_md:
        raise _not_a_skill_package(
            'The package has no SKILL.md at its root or at the top of a '
            'single top-level directory.'
        )

    folder = skill_md.rpartition('/')[0]
    prefix = f'{folder}/' if folder else ''
    plan = []
    for info in infos:
        path = _normalised(info.filename)
        if path == skill_md:
            installed = SKILL_MARKER
        elif prefix and path.rstrip('/') == folder:
            # The wrapper folder itself, which is not installed.
            installed = None
        else:
            # With a wrapper, every other entry is inside it.
            installed = path[len(prefix) :]
        plan.append((info, installed or None))
    _check_installed_names([name for _, name in plan if name])
    return plan


def _check_installed_names(names):
    """The entry checks again, on the names entries are installed under."""
    for name in names:
        segments = name.split('/')
        if (
            '..' in segments
            or _UNPORTABLE_CHARACTERS.search(name)
            or any(_windows_unsafe(segment) for segment in segments)
            or _reserved_name(segments)
        ):
            raise AgentRegistryJWTError(
                f'Refusing entry installed as {name!r}: it is not a safe '
                f'file name.'
            )
    if len(set(names)) != len(names):
        raise AgentRegistryJWTError(
            'Refusing an archive in which two entries install to the same '
            'path.'
        )
    _check_collisions(names)


def _reserved_name(segments):
    """The reserved name one of ``segments`` is, or None.

    Compared as a case-insensitive filesystem sees names.
    """
    for segment in segments:
        folded = unicodedata.normalize('NFC', segment).casefold()
        for reserved in _RESERVED_NAMES:
            if folded == reserved.casefold():
                return reserved
    return None


def _frontmatter_name(zf, info):
    """``(name, None)`` from a package's SKILL.md, or ``(None, why)``.

    As :func:`_frontmatter_name_from_bytes` reads it.
    """
    with zf.open(info) as f:
        data = f.read(_MAX_SKILL_MD_BYTES + 1)
    return _frontmatter_name_from_bytes(data, "the package's SKILL.md")


def _no_frontmatter(lines, what):
    """Why the SKILL.md split into ``lines`` does not begin with frontmatter.

    The service refuses a byte order mark and carriage returns alone as line
    breaks too, and frontmatter that does not start on the first line.
    """
    first = lines[0] if lines else b''
    if first.startswith(b'\xef\xbb\xbf'):
        return f'{what} begins with a byte order mark, not frontmatter'
    if b'\r' in first.rstrip():
        return (
            f'{what} breaks lines with carriage returns alone, so it does not '
            f'begin with a frontmatter line'
        )
    first_text = next(
        (index for index, line in enumerate(lines) if line.strip()), None
    )
    if first_text and lines[first_text].rstrip() == _FRONTMATTER_FENCE:
        return f'{what} has blank lines before its frontmatter'
    return f'{what} does not begin with frontmatter'


def _frontmatter_name_from_bytes(data, what):
    """``(name, None)`` from SKILL.md's frontmatter, or ``(None, why)``.

    ``data`` is the start of SKILL.md, at least :data:`_MAX_SKILL_MD_BYTES`
    plus one byte of it if it is that long, and ``what`` names it in the
    reason. The frontmatter is the YAML between a ``---`` line at the very
    start of the file and the next ``---`` line, which must come within the
    first :data:`_MAX_SKILL_MD_BYTES`. It is parsed with ruamel.yaml's base
    loader, which builds nothing but strings, lists and mappings: no tag
    constructs an object, and a scalar stays text, as the service reads it.
    An alias is composed by reference, so it cannot expand the document, and
    nesting too deep to parse is a parse failure.
    """
    lines = data[:_MAX_SKILL_MD_BYTES].split(b'\n')
    if len(data) > _MAX_SKILL_MD_BYTES:
        # Cut short at the limit, so not a whole line.
        lines.pop()
    if not lines or lines[0].rstrip() != _FRONTMATTER_FENCE:
        return None, _no_frontmatter(lines, what)
    end = next(
        (
            index
            for index, line in enumerate(lines[1:], 1)
            if line.rstrip() == _FRONTMATTER_FENCE
        ),
        None,
    )
    if end is None:
        return None, (
            f'the frontmatter of {what} does not end within its first '
            f'{_MAX_SKILL_MD_BYTES} bytes'
        )
    try:
        document = ruamel.yaml.YAML(typ='base', pure=True).load(
            b'\n'.join(lines[1:end]).decode('utf-8')
        )
    except Exception as e:
        # Also RecursionError, for nesting too deep to parse. The type
        # only: the parser's message quotes the text, which a record holds
        # as sensitive.
        logger.debug(
            'Could not parse the SKILL.md frontmatter: %s', type(e).__name__
        )
        return None, f'the frontmatter of {what} is not valid UTF-8 YAML'
    name = document.get('name') if isinstance(document, dict) else None
    if not isinstance(name, str) or not name:
        return None, f'the frontmatter of {what} has no name'
    return name, None


def _check_archive(archive, shown):
    """Refuse an archive that is unsafe or not a skill package, up front.

    Returns the name in the package's ``SKILL.md``, which the skill is
    installed under, once :func:`_check_declared_name` has checked it.
    ``shown`` is what messages call the record. A wrapper folder that the
    package's files are installed without does not count.
    """
    try:
        with zipfile.ZipFile(archive) as zf:
            plan = _install_plan(_checked_entries(zf))
            skill_md = next(
                info for info, installed in plan if installed == SKILL_MARKER
            )
            declared, unreadable = _frontmatter_name(zf, skill_md)
    except _ZIP_ERRORS as e:
        raise _damaged(e)
    return _named(declared, unreadable, shown)


def _named(declared, unreadable, shown):
    """The SKILL.md name, checked, from what a frontmatter reader returned."""
    if unreadable:
        raise AgentRegistryJWTError(
            f"Refusing to install {shown}: {unreadable}, so the skill's name, "
            f"which its folder is named after, can't be read."
        )
    return _check_declared_name(declared, shown)


def _check_declared_name(declared, shown):
    """``declared``, the SKILL.md name, if the skill can be installed under it.

    It must be able to name a folder here (:func:`folder_name_problem`). A
    name outside the Agent Skills specification's form is installed with one
    warning. SKILL.md is never rewritten.
    """
    problem = folder_name_problem(declared)
    if problem:
        # The package chooses the name.
        raise AgentRegistryJWTError(
            f'Refusing to install {shown}: its SKILL.md names the skill '
            f'{printable(repr(declared))}, which cannot name its folder: '
            f'{problem}. The publisher must rename the skill in its SKILL.md.'
        )
    if not is_spec_skill_name(declared):
        write_status(
            f'Warning: {declared} is not an Agent Skills name '
            f'({SKILL_NAME_RULE}); some agents may not load it.'
        )
    return declared


def _file_mode(info):
    """The entry's permissions, never more than ``0o755``.

    Keeps a script's executable bit, but never setuid, setgid, sticky or
    write access for anyone but the owner, who can always read and write.
    An archive made on Windows records no permissions, and gets ``0o644``.
    """
    mode = (info.external_attr >> 16) & 0o777
    if not mode:
        mode = 0o644
    return (mode & 0o755) | 0o600


def _extract_file(zf, info, target, budget):
    """Write one entry to ``target`` and return the bytes it produced.

    The bytes are counted as they are written, so an archive whose headers
    understate the sizes cannot write more than the entry declares or more
    than ``budget`` in total.
    """
    written = 0
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0)
    fd = os.open(target, flags, 0o600)
    with os.fdopen(fd, 'wb') as out, zf.open(info) as source:
        while True:
            chunk = source.read(_CHUNK_BYTES)
            if not chunk:
                break
            written += len(chunk)
            if written > info.file_size:
                raise AgentRegistryJWTError(
                    f'Refusing entry {info.filename!r}: it expands beyond '
                    f'the {info.file_size} bytes its header declares.'
                )
            if written > budget:
                raise AgentRegistryJWTError(
                    f'Archive expands beyond the {MAX_EXTRACTED_BYTES} bytes '
                    f'allowed.'
                )
            out.write(chunk)
    os.chmod(target, _file_mode(info))
    return written


def _safe_extract(archive, destination):
    """Extract a skill package into ``destination``, refusing anything unsafe.

    Every entry is checked, and must resolve inside ``destination``, before
    anything is written. Entries are written under the names of the install
    plan. Directories get ``0o755`` and files keep their mode from the
    archive within ``0o755``.
    """
    os.makedirs(destination, exist_ok=True)
    real_destination = os.path.realpath(destination)
    try:
        with zipfile.ZipFile(archive) as zf:
            targets = []
            for info, installed in _install_plan(_checked_entries(zf)):
                if installed is None:
                    # The single top-level folder the skill is wrapped in.
                    continue
                target = os.path.realpath(os.path.join(destination, installed))
                if target != real_destination and not target.startswith(
                    real_destination + os.sep
                ):
                    raise AgentRegistryJWTError(
                        f'Refusing entry that escapes the target directory: '
                        f'{info.filename!r}'
                    )
                targets.append((info, target))
            budget = MAX_EXTRACTED_BYTES
            for info, target in targets:
                if info.is_dir():
                    os.makedirs(target, exist_ok=True)
                    continue
                os.makedirs(os.path.dirname(target), exist_ok=True)
                budget -= _extract_file(zf, info, target, budget)
    except _ZIP_ERRORS as e:
        raise _damaged(e)
    for directory, _, _ in os.walk(destination):
        os.chmod(directory, 0o755)


def remove_leftover(path):
    """Delete a staging or backup folder, warning if it cannot be removed."""
    try:
        shutil.rmtree(path)
    except OSError as e:
        write_status(
            f'Warning: could not remove {path} ({printable(e)}). Remove it '
            f'by hand.'
        )


def _write_skill_md(staged, data):
    """Write the record's SKILL.md text, ``data``, as the staged skill.

    The bytes are written as they are, so the SHA-256 in the marker is
    theirs.
    """
    path = os.path.join(staged, SKILL_MARKER)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0)
    fd = os.open(path, flags, 0o644)
    with os.fdopen(fd, 'wb') as f:
        f.write(data)
    # The umask may have narrowed the modes: as an extracted package's.
    os.chmod(path, 0o644)
    os.chmod(staged, 0o755)


def _write_provenance(skill_dir, source):
    """Record where the skill came from, as part of the staged folder."""
    path = os.path.join(skill_dir, PROVENANCE_MARKER)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0)
    fd = os.open(path, flags, 0o644)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(
            {
                **{field: source[field] for field in _PROVENANCE_FIELDS},
                'content': source['content'],
            },
            f,
        )
        f.write('\n')
    # The umask may have narrowed the mode os.open was given.
    os.chmod(path, 0o644)


def _install(populate, name, destination, source, force, uninstall):
    """Stage the skill next to ``destination`` and swap it into place.

    ``populate`` writes the skill into the staged folder it is given: the
    package extracted, or the record's SKILL.md text. The provenance marker
    is written into the staged folder, so it lands with the install in the
    same rename. The destination is planned again just before the swap, by
    the same rules, in case another run changed it while this one was
    writing; if it is up to date by then, it is left as it is. Returns
    ``(action, installed marker)`` from that second plan.
    """
    # Stage next to the destination, on the same filesystem, so the final
    # swap is a rename rather than a copy.
    parent = os.path.dirname(destination)
    os.makedirs(parent, exist_ok=True)
    staged = tempfile.mkdtemp(prefix=f'.{name}.staging-', dir=parent)
    try:
        populate(staged)
        if not os.path.isfile(os.path.join(staged, SKILL_MARKER)):
            raise AgentRegistryJWTError(
                f'The archive for {name} has no {SKILL_MARKER} at its root, '
                f'so it is not a valid skill package.'
            )
        _write_provenance(staged, source)
        action, installed = _plan_destination(
            destination, name, force, source, uninstall
        )
        if action not in _LEFT_AS_IT_IS:
            _replace(staged, destination)
        return action, installed
    finally:
        if os.path.lexists(staged):
            remove_leftover(staged)


def _replace(staged, destination):
    """Swap the staged tree into place by rename.

    ``staged`` sits in the same directory as ``destination``, so every step is
    an atomic rename. If the swap fails, the previous install is restored.
    """
    backup = None
    if os.path.lexists(destination):
        backup = os.path.join(
            os.path.dirname(destination),
            f'.{os.path.basename(destination)}.old-{secrets.token_hex(4)}',
        )
        os.rename(destination, backup)
    try:
        os.rename(staged, destination)
    except Exception:
        if backup:
            try:
                os.rename(backup, destination)
            except OSError as e:
                # The original error is what is raised; say where the
                # previous install is, so it can be moved back by hand.
                write_status(
                    f'Warning: could not restore the previous install to '
                    f'{destination} ({printable(e)}). It is in {backup}.'
                )
        raise
    if backup:
        remove_leftover(backup)
