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
from awscli.customizations.agenttoolkit.utils import (
    SKILL_NAME_ARG,
    SKILL_VERSION_ARG,
    create_client,
)
from awscli.customizations.commands import BasicCommand
from awscli.utils import OutputStreamFactory


class GetSkillFileCommand(BasicCommand):
    NAME = 'get-skill-file'
    DESCRIPTION = (
        'Retrieve the contents of a single file from a skill. '
        'Use ``aws agent-toolkit get-skill-metadata`` to discover available '
        'file names for each skill. By default the latest version is '
        'retrieved, use ``--skill-version`` for a specific skill version.'
    )
    ARG_TABLE = [
        SKILL_NAME_ARG,
        {
            'name': 'file-path',
            'help_text': (
                'The file to fetch '
                '(such as SKILL.md, references/architecture.md).'
            ),
            'action': 'store',
            'cli_type_name': 'string',
            'required': True,
        },
        SKILL_VERSION_ARG,
    ]

    def __init__(self, session, client=None, output_stream_factory=None):
        super().__init__(session)
        self._client = client
        if output_stream_factory is None:
            output_stream_factory = OutputStreamFactory(session)
        self._output_stream_factory = output_stream_factory

    def _run_main(self, parsed_args, parsed_globals):
        client = self._client or create_client(self._session, parsed_globals)

        skill_name = parsed_args.skill_name
        file_path = parsed_args.file_path
        skill_version = getattr(parsed_args, 'skill_version', None) or 'latest'

        response = client.get_skill_file(
            name=skill_name,
            skillVersion=skill_version,
            filePath=file_path,
        )
        body = response['body'].read()
        with self._output_stream_factory.get_output_stream() as stream:
            stream.write(body.decode('utf-8'))
        return 0
