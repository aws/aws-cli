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
import sys

from awscli.customizations.agenttoolkit import atomic
from awscli.customizations.agenttoolkit.agents import (
    AGENT_CONFIGS,
    collapse_home,
    universal_first,
)
from awscli.customizations.agenttoolkit.utils import (
    AGENT_ARG,
    SCOPE_ARGS,
    SKILL_NAME_ARG,
    SYMLINK_ARGS,
    SYMLINK_SKIP_REASON,
    resolve_agents_for_args,
    skills_lock,
)
from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ParamValidationError
from awscli.customizations.utils import uni_print


class RemoveCommand(BasicCommand):
    NAME = 'remove-skill'
    DESCRIPTION = (
        'Remove a previously installed AWS skill from detected agents. '
        'By default the skill is removed from all detected agents, use '
        '``--agent`` to remove from a specific tool only.'
    )
    ARG_TABLE = [
        SKILL_NAME_ARG,
        AGENT_ARG,
        *SCOPE_ARGS,
        *SYMLINK_ARGS,
    ]

    def __init__(self, session, stream=None, agent_configs=None):
        super().__init__(session)
        if stream is None:
            stream = sys.stdout
        self._stream = stream
        if agent_configs is None:
            agent_configs = AGENT_CONFIGS
        self._agent_configs = agent_configs

    def _run_main(self, parsed_args, parsed_globals):
        skill_name = parsed_args.skill_name

        agents = resolve_agents_for_args(parsed_args, self._agent_configs)

        matches = []
        for agent in agents:
            for skill in agent.get_installed_skills():
                if skill.name == skill_name:
                    matches.append(skill)

        if not matches:
            raise ParamValidationError(
                f'Skill "{skill_name}" is not installed.'
            )

        removed_paths = set()
        ordered = universal_first(matches, get_id=lambda s: s.agent.config.id)
        targets = [(skill, _can_remove(skill)) for skill in ordered]
        # Writable paths first, so a skill that is also reached through a
        # path the CLI may not change is still removed.
        targets.sort(key=lambda t: not t[1])
        for skill, is_writable in targets:
            skill_dir = os.path.dirname(skill.path)
            # Resolve only the parent so a skills root shared by symlink is
            # removed once, but a symlinked skill dir is not followed.
            entry = os.path.join(
                os.path.realpath(os.path.dirname(skill_dir)),
                os.path.basename(skill_dir),
            )
            if entry in removed_paths:
                continue
            if not is_writable:
                removed_paths.add(entry)
                uni_print(
                    f'Skipped {skill.name} at {collapse_home(skill_dir)}: '
                    f'{SYMLINK_SKIP_REASON}.\n',
                    self._stream,
                )
                continue
            with skills_lock(os.path.dirname(entry)):
                # Delete any backup left by an interrupted update, or the
                # next recovery would restore the removed skill.
                atomic.recover(entry)
                if not os.path.lexists(entry):
                    # Another process removed it after it was listed.
                    removed_paths.add(entry)
                    continue
                if atomic.is_link(entry):
                    # The target may be shared with other agents, so only
                    # remove this agent's link to it.
                    os.unlink(entry)
                else:
                    atomic.remove_dir(entry)
            removed_paths.add(entry)
            uni_print(
                f'Removed {skill.name} from '
                f'{skill.agent.label_for(os.path.dirname(skill_dir))}.\n',
                self._stream,
            )
        return 0


def _can_remove(skill):
    """Whether the CLI may remove ``skill``.

    Only its skills directory is checked: a skill that is a symbolic link
    is removed by deleting the link, which never writes through it.
    """
    skills_root = os.path.dirname(os.path.dirname(skill.path))
    return skill.agent.can_write(skills_root)
