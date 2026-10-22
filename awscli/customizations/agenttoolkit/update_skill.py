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
import collections
import contextlib
import datetime
import logging
import os
import sys

from botocore.config import Config
from botocore.exceptions import ClientError, HTTPClientError

from awscli.customizations.agenttoolkit.agents import (
    AGENT_CONFIGS,
    SKILL_METADATA_FILENAME,
)
from awscli.customizations.agenttoolkit.filelock import file_lock
from awscli.customizations.agenttoolkit.hooks import (
    HOOK_AGENT_IDS,
    HOOK_ERROR_MESSAGE,
    format_hook_message,
    format_hook_output,
    hook_config_path,
)
from awscli.customizations.agenttoolkit.state import (
    StateFileError,
    get_last_hook_run,
    is_auto_update_enabled,
    parse_timestamp,
    record_hook_run,
    toolkit_dir,
)
from awscli.customizations.agenttoolkit.utils import (
    AGENT_ARG,
    SKILL_NAME_ARG,
    AgentToolkitServiceError,
    agents_with_skill,
    collect_installed_skills,
    create_client,
    get_skill_download,
    install_skill,
    list_core_skills,
    read_installed_version,
    resolve_agents,
    resolve_latest_version,
)
from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ParamValidationError

LOG = logging.getLogger(__name__)

UPDATE_SKILL_NAME_ARG = {**SKILL_NAME_ARG, 'required': False}

ALL_SKILLS_ARG = {
    'name': 'all',
    'help_text': (
        'Update every installed AWS skill that is out of date. Cannot be '
        'combined with ``--skill-name``.'
    ),
    'action': 'store_true',
    'required': False,
}

HOOK_ARG = {
    'name': 'hook',
    'help_text': (
        'Run as the session start hook of the given agent. Implies '
        '``--all`` and '
        'also installs new skills in the ``aws-core`` category into agents '
        'that already have AWS skills. Does nothing unless automatic skill '
        'updates are turned on, prints only what the agent expects and '
        'always succeeds.'
    ),
    'action': 'store',
    'cli_type_name': 'string',
    'choices': list(HOOK_AGENT_IDS),
    'required': False,
}


class _UpdateResults(
    collections.namedtuple(
        '_UpdateResults',
        [
            'updated',
            'up_to_date',
            'skipped',
            'failed',
            'installed',
            'failed_installs',
        ],
    )
):
    """Outcome of updating every installed skill.

    ``skipped`` holds ``(skill_name, skill_dir, reason)``, ``failed`` and
    ``failed_installs`` hold ``(skill_name, error)`` for skills that could
    not be updated or newly installed, and ``installed`` the new core
    skills.
    """

    @classmethod
    def empty(cls):
        return cls([], [], [], [], [], [])

    @property
    def skipped_names(self):
        return sorted({name for name, _, _ in self.skipped})

    @property
    def failed_names(self):
        return [name for name, _ in self.failed]

    @property
    def failed_install_names(self):
        return [name for name, _ in self.failed_installs]

    def summary(self):
        installed = (
            f'{len(self.installed)} installed, ' if self.installed else ''
        )
        return (
            f'{installed}{len(self.updated)} updated, '
            f'{len(self.skipped_names)} skipped, '
            f'{len(self.failed) + len(self.failed_installs)} failed, '
            f'{len(self.up_to_date)} already up to date'
        )


# Agents stop a hook after 60 seconds and report it as an error. A failed
# check is tried again at the next session start, so fail fast instead of
# retrying.
HOOK_CLIENT_CONFIG = Config(
    connect_timeout=5, read_timeout=10, retries={'max_attempts': 1}
)

# Several sessions can start at once, and an agent may run more than one
# hook at session start. Hook runs take turns, and a run that starts right
# after another for the same agent finished does nothing, so the agent hears
# about an update once.
HOOK_LOCK_FILENAME = 'hook.lock'
HOOK_LOCK_TIMEOUT = 30
HOOK_RECENT_RUN_SECONDS = 10


class UpdateSkillCommand(BasicCommand):
    NAME = 'update-skill'
    DESCRIPTION = (
        'Update installed AWS skills to the latest version. '
        'Compares the locally installed version against the available skills '
        'and downloads the newer version if available. Pass ``--skill-name`` '
        'to update a single skill or ``--all`` to update every installed '
        'skill that is out of date. By default skills are '
        'updated for all detected agents, use ``--agent`` to update '
        'for only a specific tool.'
    )
    ARG_TABLE = [
        UPDATE_SKILL_NAME_ARG,
        ALL_SKILLS_ARG,
        AGENT_ARG,
        HOOK_ARG,
    ]

    def __init__(
        self,
        session,
        stream=None,
        client=None,
        agent_configs=None,
        error_stream=None,
    ):
        super().__init__(session)
        if stream is None:
            stream = sys.stdout
        self._stream = stream
        if error_stream is None:
            error_stream = sys.stderr
        self._error_stream = error_stream
        self._client = client
        if agent_configs is None:
            agent_configs = AGENT_CONFIGS
        self._agent_configs = agent_configs

    def _run_main(self, parsed_args, parsed_globals):
        skill_name = parsed_args.skill_name
        update_all = getattr(parsed_args, 'all', False)
        agent_filter = getattr(parsed_args, 'agent', None)
        hook = getattr(parsed_args, 'hook', None)

        if hook:
            if skill_name:
                raise ParamValidationError(
                    'Cannot use --skill-name together with --hook.'
                )
            if agent_filter:
                raise ParamValidationError(
                    'Cannot use --agent together with --hook.'
                )
            return self._run_hook(hook, parsed_globals)
        if update_all and skill_name:
            raise ParamValidationError(
                'Cannot use --skill-name together with --all.'
            )
        if not update_all and not skill_name:
            raise ParamValidationError(
                'Either --skill-name or --all is required.'
            )

        agents = resolve_agents(agent_filter, self._agent_configs)
        if not agents:
            raise ParamValidationError('No supported AI coding agents found.')

        if update_all:
            return self._update_all_skills(agents, parsed_globals)
        return self._update_one_skill(agents, parsed_globals, skill_name)

    def _create_client(self, parsed_globals, config=None):
        # Kept so a hook run uses one client for updates and new skills.
        if self._client is None:
            self._client = create_client(
                self._session, parsed_globals, config=config
            )
        return self._client

    def _update_one_skill(self, agents, parsed_globals, skill_name):
        installed_agents = agents_with_skill(agents, skill_name)
        if not installed_agents:
            raise ParamValidationError(
                f'Skill "{skill_name}" is not installed.'
            )

        # Build the client only once we know there is something to update, so
        # local failures are not masked by endpoint or credential errors.
        client = self._create_client(parsed_globals)
        remote_version, outdated = self._find_outdated(
            installed_agents, client, skill_name
        )
        if not outdated:
            self._stream.write(
                f'{skill_name} is already up to date ({remote_version}).\n'
            )
            return 0

        skipped = self._install_version(
            client, skill_name, remote_version, outdated, self._stream
        )
        self._write_skipped([(skill_name, *s) for s in skipped])
        return 0

    def _run_hook(self, agent_id, parsed_globals):
        # A hook left behind after automatic updates were turned off does
        # nothing.
        if not is_auto_update_enabled():
            return 0
        with contextlib.ExitStack() as stack:
            try:
                stack.enter_context(
                    file_lock(
                        os.path.join(toolkit_dir(), HOOK_LOCK_FILENAME),
                        timeout=HOOK_LOCK_TIMEOUT,
                    )
                )
            except TimeoutError:
                # Another run is still going and reports what it does.
                return 0
            except OSError as e:
                LOG.debug('Could not lock the hook run: %s', e)
            if self._hook_ran_recently(agent_id):
                return 0
            return self._run_hook_locked(agent_id, parsed_globals)

    def _hook_ran_recently(self, agent_id):
        run = get_last_hook_run(hook_config_path(self._hook_config(agent_id)))
        if run is None:
            return False
        age = datetime.datetime.now(datetime.timezone.utc) - parse_timestamp(
            run['timestamp']
        )
        return age.total_seconds() < HOOK_RECENT_RUN_SECONDS

    def _run_hook_locked(self, agent_id, parsed_globals):
        # The agent shows or acts on whatever is printed, and a failing hook
        # is reported as an error, so nothing escapes and it always succeeds.
        results = _UpdateResults.empty()
        error = None
        try:
            agents = resolve_agents(None, self._agent_configs)
            if self._collect_updates(
                agents, parsed_globals, None, results, HOOK_CLIENT_CONFIG
            ):
                self._install_new_core_skills(
                    agents, self._create_client(parsed_globals), results
                )
        except Exception as e:
            LOG.debug('Automatic skill update failed', exc_info=True)
            error = e
        # Skills updated before an error are still reported, so the agent
        # loads them again.
        message = format_hook_message(
            results.updated,
            results.installed,
            results.skipped_names,
            results.failed_names,
            results.failed_install_names,
        )
        if error is None:
            is_successful = not (results.failed or results.failed_installs)
            summary = results.summary()
        else:
            message = f'{message} {HOOK_ERROR_MESSAGE}'.lstrip()
            is_successful = False
            summary = f'Could not check for updates: {error}'
        self._stream.write(
            format_hook_output(
                agent_id,
                message,
                skills_updated=bool(results.updated or results.installed),
            )
        )
        self._record_hook_run(agent_id, is_successful, summary)
        return 0

    def _hook_config(self, agent_id):
        # The hook's agent may not be detected, or not in a custom config
        # list, but every hook id has a config in AGENT_CONFIGS.
        return next(
            c
            for c in [*self._agent_configs, *AGENT_CONFIGS]
            if c.id == agent_id
        )

    def _record_hook_run(self, agent_id, is_successful, summary):
        try:
            record_hook_run(
                hook_config_path(self._hook_config(agent_id)),
                is_successful=is_successful,
                summary=summary,
            )
        except StateFileError as e:
            LOG.debug('Could not record the hook run: %s', e)

    def _update_all_skills(self, agents, parsed_globals):
        results = _UpdateResults.empty()
        if not self._collect_updates(
            agents, parsed_globals, self._stream, results
        ):
            self._stream.write('No installed AWS skills found.\n')
            return 0
        if not (results.updated or results.skipped or results.failed):
            self._stream.write(
                'All installed AWS skills are already up to date.\n'
            )
            return 0
        self._stream.write(f'\n{results.summary()}.\n')
        self._write_skipped(results.skipped)
        self._write_failed(results.failed)
        return 1 if results.failed else 0

    def _collect_updates(
        self, agents, parsed_globals, stream, results, client_config=None
    ):
        """Update every installed skill that is out of date.

        Progress is written to ``stream`` if it is set. Each outcome is added
        to the ``_UpdateResults`` in ``results`` as soon as it is known, so
        it holds the skills already handled if an error is raised. Returns
        ``False`` if no skills are installed.
        """
        installed_skills = collect_installed_skills(agents)
        if not installed_skills:
            return False

        # Group by name from the scan above. Asking each agent which skills it
        # has once per skill name would rescan every skills directory for every
        # skill.
        agents_by_skill = {}
        for skill in installed_skills:
            agents_by_skill.setdefault(skill.name, []).append(skill.agent)

        client = self._create_client(parsed_globals, client_config)
        for skill_name in sorted(agents_by_skill):
            # One bad skill should not block updates to the remaining skills.
            try:
                remote_version, outdated = self._find_outdated(
                    agents_by_skill[skill_name], client, skill_name
                )
                if not outdated:
                    results.up_to_date.append(skill_name)
                    continue
                skill_skipped = self._install_version(
                    client, skill_name, remote_version, outdated, stream
                )
            except (AgentToolkitServiceError, ClientError) as e:
                results.failed.append((skill_name, e))
                continue
            if skill_skipped:
                results.skipped.extend(
                    (skill_name, *s) for s in skill_skipped
                )
            else:
                results.updated.append(skill_name)
        return True

    def _install_new_core_skills(self, agents, client, results):
        """Install core skills missing from agents that have AWS skills.

        Agents the customer never set up with the toolkit are left alone.
        A core skill removed with ``remove-skill`` is installed again.
        Outcomes are added to ``results`` like :meth:`_collect_updates`.
        """
        targets = [agent for agent in agents if agent.get_installed_skills()]
        if not targets:
            return
        core_skills = list_core_skills(client)
        for skill in sorted(core_skills, key=lambda s: s['name']):
            skill_name = skill['name']
            missing = self._agents_missing_skill(
                targets, skill_name, results.skipped
            )
            if not missing:
                continue
            try:
                zip_bytes, checksum, version = get_skill_download(
                    client, skill_name, version=skill.get('skillVersion')
                )
                skill_skipped = install_skill(
                    skill_name, version, zip_bytes, checksum, missing
                )
            except (
                AgentToolkitServiceError,
                ClientError,
                HTTPClientError,
            ) as e:
                results.failed_installs.append((skill_name, e))
                continue
            results.skipped.extend((skill_name, *s) for s in skill_skipped)
            if len(skill_skipped) < len(missing):
                results.installed.append(skill_name)

    def _agents_missing_skill(self, agents, skill_name, skipped):
        """Return the agents to install ``skill_name`` into.

        A directory of that name the toolkit did not install is added to
        ``skipped`` without downloading anything.
        """
        missing = []
        seen_roots = set()
        for agent in agents:
            root = os.path.realpath(agent.skills_path)
            if root in seen_roots:
                continue
            seen_roots.add(root)
            skill_dir = os.path.join(root, skill_name)
            if os.path.exists(
                os.path.join(skill_dir, SKILL_METADATA_FILENAME)
            ):
                continue
            if os.path.lexists(skill_dir):
                skipped.append(
                    (
                        skill_name,
                        skill_dir,
                        'a skill with this name exists that the AWS CLI '
                        'did not install',
                    )
                )
                continue
            missing.append(agent)
        return missing

    def _write_skipped(self, skipped):
        if not skipped:
            return
        self._stream.write('\nSkipped:\n')
        for skill_name, skill_dir, reason in skipped:
            self._stream.write(f'  {skill_name} at {skill_dir}: {reason}.\n')
        self._stream.write(
            'To install the AWS skill there, move the existing path aside and '
            'run "aws agent-toolkit add-skill --skill-name <name>".\n'
        )

    def _write_failed(self, failed):
        if not failed:
            return
        self._error_stream.write('\nFailed:\n')
        for skill_name, error in failed:
            self._error_stream.write(
                f'  Failed to update {skill_name}: {error}\n'
            )
        self._error_stream.write(
            'To retry, run "aws agent-toolkit update-skill --skill-name '
            '<name>".\n'
        )

    def _find_outdated(self, installed_agents, client, skill_name):
        remote_version = resolve_latest_version(client, skill_name)
        outdated = []
        for agent in installed_agents:
            skill_dir = os.path.join(agent.skills_path, skill_name)
            local_version = read_installed_version(skill_dir)
            if local_version != remote_version:
                outdated.append(agent)
        return remote_version, outdated

    def _install_version(
        self, client, skill_name, remote_version, agents, stream
    ):
        zip_bytes, checksum, version = get_skill_download(
            client, skill_name, version=remote_version
        )
        return install_skill(
            skill_name,
            version,
            zip_bytes,
            checksum,
            agents,
            stream,
            action='Updated',
            overwrite_existing=True,
        )
