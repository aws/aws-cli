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
"""List the skills a registry offers, and the agents each is installed for.

The skills are the registry's ``SKILL`` records, read with
``ListDiscoverableRegistryRecords``, and the name in each one's SKILL.md
with ``BatchGetDiscoverableRegistryRecord``. Whether one is installed is
decided locally, from the provenance marker ``install-skill`` writes, so
nothing is downloaded.
"""

from botocore.exceptions import BotoCoreError, ClientError

from awscli.customizations.agentregistry.dataplane import (
    SIGN_IN_ARGUMENTS,
    SIGN_IN_DESCRIPTION,
    create_data_plane_client,
    skill_record_pages,
)
from awscli.customizations.agentregistry.install_skill import (
    PROVENANCE_MARKER,
    installed_skills,
    resolve_skill_folders,
    skill_md_name,
    source_key,
)
from awscli.customizations.agentregistry.utils import (
    AgentRegistryJWTError,
    bare_registry_id,
    printable,
    write_status,
)
from awscli.customizations.agenttoolkit.agents import AGENT_CONFIGS
from awscli.customizations.agenttoolkit.utils import AGENT_ARG
from awscli.customizations.commands import BasicCommand
from awscli.formatter import get_formatter
from awscli.utils import OutputStreamFactory

# The record fields listed, as the registry returns them.
_RECORD_FIELDS = ('name', 'recordId', 'description', 'recordVersion')

# The most record ids one BatchGetDiscoverableRegistryRecord call takes.
_BATCH_GET_LIMIT = 100

# The text and table formatters write values as they are, so a control
# character in a field the publisher chose, such as the description, would
# reach the terminal: an escape sequence could rewrite what is shown, and a
# tab or newline would add columns or rows to text output that scripts split.
# They are replaced there. JSON and YAML output keep the values exactly as
# the registry returned them, for the programs that parse it: JSON escapes
# C0 control characters, the escape character among them, and YAML quotes
# and escapes non-printable characters. JSONFormatter uses ensure_ascii=False,
# though, so DEL, C1 controls and bidirectional overrides pass through in
# JSON and YAML output, as they do for the generated commands.
_DISPLAYED_OUTPUTS = ('text', 'table')

# --agent is agent-toolkit's own argument, as for install-skill, but this
# command has no --target-directory to exclude.
_AGENT_ARGUMENT = dict(
    AGENT_ARG,
    help_text=(
        AGENT_ARG['help_text']
        + ' Only that agent\'s skills folder is checked for installed skills.'
    ),
)


def _displayed(skill):
    """``skill`` with control characters replaced, for text and table output.

    ``printable`` also strips leading and trailing whitespace. Nothing is cut
    off, because the limit is each value's own length.
    """
    return {
        key: printable(value, limit=len(value))
        if isinstance(value, str)
        else value
        for key, value in skill.items()
    }


class ListSkillsCommand(BasicCommand):
    """List a registry's skills and where each is installed."""

    NAME = 'list-skills'
    DESCRIPTION = (
        'Lists the skills a registry offers: the name, record id, '
        'description and version of each of its ``SKILL`` records, read '
        'with ``ListDiscoverableRegistryRecords``, and in ``installedFor`` '
        'the AI coding agents it is installed for. Every page of records is '
        'read, so ``--no-paginate`` and ``--max-items`` do not apply.\n\n'
        '``skillName`` is the ``name`` in the frontmatter of the '
        "record's ``SKILL.md``, which ``install-skill`` names the skill's "
        'folder after; ``name`` is the record\'s own name, which can '
        'differ. The command reads it with '
        '``BatchGetDiscoverableRegistryRecord``, up to 100 records a call, '
        'with the same credentials or sign-in as the listing. ``skillName`` '
        'is left out for a record whose ``SKILL.md`` text is missing or '
        "can't be read, and for every record, with a warning, if those "
        'calls fail. Nothing else they return is shown.\n\n'
        'Each agent in ``installedFor`` has an ``id``, the value to pass as '
        '``--agent``, and a display ``name``. A skills folder that several '
        'agents share is listed once: ``~/.agents/skills`` as ``universal``, '
        'unless ``--agent`` names one of the agents that share it. A skill is '
        'installed for an agent when the agent\'s skills folder holds a copy '
        'that ``install-skill`` installed from this registry, record and '
        f'endpoint, as recorded in its ``{PROVENANCE_MARKER}``, whatever its '
        'version. The copy is found by that marker, whatever the name of its '
        'folder. A copy installed by anything else, or from another '
        'registry, record or endpoint, does not count. The folders of every '
        'detected agent are checked, or only those of the agent named by '
        '``--agent``; with none detected, ``installedFor`` is empty. Nothing '
        'is downloaded. Install or update a skill with ``install-skill``.\n\n'
        + SIGN_IN_DESCRIPTION
    )
    ARG_TABLE = [
        {
            'name': 'registry-id',
            'required': True,
            'help_text': (
                'The registry to list the skills of, given as an id or an '
                'ARN.'
            ),
        },
        _AGENT_ARGUMENT,
        *SIGN_IN_ARGUMENTS,
    ]

    def __init__(
        self, session, agent_configs=None, output_stream_factory=None
    ):
        super().__init__(session)
        if agent_configs is None:
            agent_configs = AGENT_CONFIGS
        self._agent_configs = agent_configs
        if output_stream_factory is None:
            output_stream_factory = OutputStreamFactory(session)
        self._output_stream_factory = output_stream_factory

    def _run_main(self, parsed_args, parsed_globals):
        # Before any network call, so a bad --agent or registry id fails
        # fast.
        folders = resolve_skill_folders(parsed_args, self._agent_configs)
        registry_id = bare_registry_id(parsed_args.registry_id)
        data_plane = create_data_plane_client(
            self._session, parsed_args, parsed_globals
        )

        # Each folder is read once, whatever the number of records.
        installed = _installed_index(folders)
        skills = []
        record_ids = []
        for page in skill_record_pages(
            data_plane.client, parsed_args.registry_id
        ):
            for record in page:
                skill = {
                    field: record[field]
                    for field in _RECORD_FIELDS
                    if field in record
                }
                source = {
                    'registryId': registry_id,
                    'recordId': record.get('recordId'),
                    'endpoint': data_plane.endpoint,
                }
                skill['installedFor'] = _installed_for(source, installed)
                skills.append(skill)
                record_ids.append(record.get('recordId'))

        # The listing has no descriptors, so the SKILL.md names are read
        # with BatchGet, with the same client and sign-in.
        names = _skill_names(
            data_plane.client, parsed_args.registry_id, record_ids
        )
        skills = [
            _with_skill_name(skill, names.get(record_id))
            for skill, record_id in zip(skills, record_ids)
        ]

        output = parsed_globals.output
        if output is None:
            output = self._session.get_config_variable('output')
        if output in _DISPLAYED_OUTPUTS:
            skills = [_displayed(skill) for skill in skills]
        formatter = get_formatter(output, parsed_globals)
        with self._output_stream_factory.get_output_stream() as stream:
            formatter(self.NAME, {'skills': skills}, stream=stream)
        return 0


def _installed_index(folders):
    """For each folder, the sources of the skills install-skill put there.

    Each is ``(agent name, agent id, set of source keys)``, read from the
    provenance markers of the skills in the folder, whatever their folders'
    names, so each marker is read once however many records are listed.
    """
    return [
        (
            agent,
            agent_id,
            {source_key(marker) for _, _, marker in installed_skills(folder)},
        )
        for agent, folder, agent_id in folders
    ]


def _installed_for(source, installed):
    """The agents whose skills folder holds a skill from ``source``.

    Each is ``{'id': <--agent value>, 'name': <display name>}``. A folder
    counts if it holds a skill whose provenance marker names the same
    registry, record and endpoint, whatever the folder's name or the
    record's; the SHA-256 is not compared, so an outdated copy counts too.
    ``installed`` is what :func:`_installed_index` read.
    """
    key = source_key(source)
    return [
        {'id': agent_id, 'name': agent}
        for agent, agent_id, sources in installed
        if key in sources
    ]


def _skill_names(client, registry_id, record_ids):
    """The SKILL.md name of each record that has one, by record id.

    Read with BatchGetDiscoverableRegistryRecord, at most
    :data:`_BATCH_GET_LIMIT` records a call. If a call fails, a warning is
    printed and no names are returned, so the listing still goes out.
    Nothing else of the response is used: not the SKILL.md text, and not
    the package's download URL.
    """
    wanted = list(
        dict.fromkeys(
            record_id
            for record_id in record_ids
            if isinstance(record_id, str) and record_id
        )
    )
    # For the lookups; the list keeps the order.
    asked = set(wanted)
    names = {}
    try:
        for start in range(0, len(wanted), _BATCH_GET_LIMIT):
            response = client.batch_get_discoverable_registry_record(
                entries=[
                    {
                        'registryId': registry_id,
                        'recordIds': wanted[start : start + _BATCH_GET_LIMIT],
                    }
                ]
            )
            records = (
                response.get('registryRecords')
                if isinstance(response, dict)
                else None
            )
            for record in records if isinstance(records, list) else []:
                if not isinstance(record, dict):
                    continue
                name = skill_md_name(record)
                record_id = record.get('recordId')
                if name and record_id in asked:
                    names[record_id] = name
    except (ClientError, BotoCoreError, AgentRegistryJWTError) as e:
        # The error code or kind only: messages can repeat URLs.
        if isinstance(e, ClientError):
            reason = e.response.get('Error', {}).get('Code') or 'ClientError'
        else:
            reason = type(e).__name__
        write_status(
            f'Warning: could not read the SKILL.md names of the skills '
            f'({printable(reason)}), so skillName is left out.'
        )
        return {}
    return names


def _with_skill_name(skill, name):
    """``skill`` with ``skillName`` right after ``name``, if there is one."""
    if name is None:
        return skill
    if 'name' not in skill:
        return {'skillName': name, **skill}
    result = {}
    for key, value in skill.items():
        result[key] = value
        if key == 'name':
            result['skillName'] = name
    return result
