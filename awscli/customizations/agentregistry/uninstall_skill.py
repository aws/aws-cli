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
"""Uninstall a skill that ``install-skill`` put in place.

Purely local: no network call, no credentials and no AWS client. The command
deletes directory trees, so it only acts on a path that looks like an
installed skill and asks before deleting unless told not to.
"""

import os
import shutil

from awscli.customizations.agentregistry.install_skill import (
    AGENT_ARGUMENT,
    FOLDER_NAME_RULE,
    MAX_SCANNED_ENTRIES,
    PROVENANCE_MARKER,
    SKILL_MARKER,
    SKILL_NAME_RULE,
    describe_source,
    read_provenance,
    report,
    resolve_skill_folders,
    safe_folder_name,
    skill_path,
)
from awscli.customizations.agentregistry.utils import (
    AgentRegistryJWTError,
    printable,
    prompt,
    stdin_is_terminal,
    write_status,
)
from awscli.customizations.agenttoolkit.agents import AGENT_CONFIGS
from awscli.customizations.commands import BasicCommand


def _require_installed_skill(path, name):
    """Refuse anything that is not a real skill directory."""
    if os.path.islink(path):
        raise AgentRegistryJWTError(
            f'Refusing to remove {path}: it is a symbolic link.'
        )
    if not os.path.exists(path):
        raise AgentRegistryJWTError(
            f'No skill named {name} is installed at {path}.'
        )
    if not os.path.isdir(path):
        raise AgentRegistryJWTError(
            f'Refusing to remove {path}: it is not a directory.'
        )
    if not os.path.isfile(os.path.join(path, SKILL_MARKER)):
        raise AgentRegistryJWTError(
            f'Refusing to remove {path}: it has no {SKILL_MARKER} at its '
            f'root, so it does not look like an installed skill.'
        )


def _on_disk_path(path):
    """``path``, with its last part spelled as the file system has it.

    On a file system that ignores case, ``--name PDF-Extract`` finds the
    folder ``pdf-extract``, which is what the result line should name. The
    folder is the entry of its parent that is the same file. If it cannot
    be found, ``path`` is returned as it is.
    """
    parent, name = os.path.split(path)
    try:
        info = os.lstat(path)
        if not info.st_ino:
            # No file id to tell two folders apart by, as on some network
            # shares: keep the name as typed.
            return path
        with os.scandir(parent) as entries:
            match = None
            for count, entry in enumerate(entries):
                if count >= MAX_SCANNED_ENTRIES:
                    break
                if entry.name == name:
                    return path
                if (
                    match is None
                    and entry.name.casefold() == name.casefold()
                    # os.lstat, not entry.stat: on Windows a directory
                    # entry's stat has no file id, so it never matches
                    and os.path.samestat(os.lstat(entry.path), info)
                ):
                    match = entry.path
    except OSError:
        return path
    return match or path


class UninstallSkillCommand(BasicCommand):
    """Uninstall a skill by name."""

    NAME = 'uninstall-skill'
    DESCRIPTION = (
        'Uninstalls a skill installed with ``install-skill`` from the skills '
        'folder of every detected AI coding agent, the agent named by '
        '``--agent``, or ``--target-directory``.\n\n'
        'Only a skill that ``install-skill`` installed is uninstalled, from '
        'any registry: the folder must be a direct child of the skills '
        'folder, must not be a symbolic link, and must have a '
        f'``{SKILL_MARKER}`` and a readable ``{PROVENANCE_MARKER}`` at its '
        'root. Any other folder is skipped. Symbolic links inside it are '
        'removed, never followed. The command asks once, listing every '
        'folder it will remove and where each came from, and exits non-zero '
        'if any folder was skipped, refused or could not be removed.\n\n'
        'This command works on the local file system only. It makes no '
        'network calls and needs no credentials.'
    )
    ARG_TABLE = [
        {
            'name': 'name',
            'required': True,
            'help_text': (
                'The skill to uninstall: the name of its directory in the '
                'skills folder, as printed by <code>install-skill</code>. The '
                'name must be a valid skill name under the Agent Skills '
                f'specification ({SKILL_NAME_RULE}) or, for an older skill, '
                f'{FOLDER_NAME_RULE}. The command refuses any other name '
                'before it looks at the file system.'
            ),
        },
        AGENT_ARGUMENT,
        {
            'name': 'target-directory',
            'help_text': (
                'Directory the skill was installed into with '
                '<code>install-skill --target-directory</code>, instead of '
                'the skills folders of the detected agents. Cannot be '
                'combined with <code>--agent</code>.'
            ),
        },
        {
            'name': 'yes',
            'action': 'store_true',
            'help_text': (
                'Uninstall without prompting for confirmation. Required when '
                'standard input is not a terminal.'
            ),
        },
    ]

    def __init__(self, session, agent_configs=None):
        super().__init__(session)
        if agent_configs is None:
            agent_configs = AGENT_CONFIGS
        self._agent_configs = agent_configs

    def _run_main(self, parsed_args, parsed_globals):
        # Any name a skill's folder can have, including an older one.
        name = safe_folder_name(parsed_args.name)
        folders = resolve_skill_folders(parsed_args, self._agent_configs)

        found = []
        failed = False
        for agent, folder, _ in folders:
            try:
                # Guaranteed a direct child of the skills folder.
                path = skill_path(folder, name)
                if not os.path.lexists(path):
                    continue
                _require_installed_skill(path, name)
                path = _on_disk_path(path)
            except AgentRegistryJWTError as e:
                report(agent, str(e))
                failed = True
                continue
            # Read now: it goes with the folder.
            marker = read_provenance(path)
            if marker is None:
                # Never delete a folder this command's install-skill did not
                # put in place.
                report(
                    agent,
                    f'Skipping {path}: it has no readable '
                    f"{PROVENANCE_MARKER}, so it wasn't installed by aws "
                    f'agent-registry install-skill. Delete it yourself if you '
                    f'no longer need it.',
                )
                failed = True
                continue
            found.append((agent, path, marker))
        if not found:
            if failed:
                return 1
            where = ', '.join(folder for _, folder, _ in folders)
            raise AgentRegistryJWTError(
                f'No skill named {name} is installed in {where}.'
                if folders
                else f'No skill named {name} is installed: no supported AI '
                f'coding agents were found.'
            )

        if not parsed_args.yes and not self._confirmed(found):
            return 1

        for agent, path, marker in found:
            # Checked again just before deleting: the directory could have
            # been replaced by a link while the prompt was open. rmtree
            # removes links inside the tree without following them.
            if os.path.islink(path):
                report(
                    agent, f'Refusing to remove {path}: it is a symbolic link.'
                )
                failed = True
                continue
            try:
                shutil.rmtree(path)
            except OSError as e:
                report(agent, f'Could not remove {path}: {printable(e)}')
                failed = True
                continue
            # The folder's own name, which may differ in case from --name.
            report(
                agent,
                f'Uninstalled {os.path.basename(path)} from '
                f'{os.path.dirname(path)} (installed '
                f'{describe_source(marker)})',
            )
        return 1 if failed else 0

    def _confirmed(self, found):
        paths = [path for _, path, _ in found]
        if not stdin_is_terminal():
            raise AgentRegistryJWTError(
                f'Refusing to remove {", ".join(paths)} without confirmation: '
                f'standard input is not a terminal. Pass --yes to remove '
                f'{"it" if len(paths) == 1 else "them"}.'
            )
        if len(found) == 1:
            _, path, marker = found[0]
            question = f'Remove {path} ({describe_source(marker)})? [y/N]: '
        else:
            listing = ''.join(
                f'  {path} ({describe_source(marker)})\n'
                for _, path, marker in found
            )
            question = f'Remove these {len(found)} folders?\n{listing}[y/N]: '
        if prompt(question).lower() in ('y', 'yes'):
            return True
        write_status('Aborted, nothing was removed.')
        return False
