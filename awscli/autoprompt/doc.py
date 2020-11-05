# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import io
from docutils.core import publish_string

from awscli.bcdoc import docevents, textwriter


class DocsGetter:
    """The main documentation getter for the auto-prompt workflow.

    This class calls out to helper classes to help grab the specific docs for
    service commands and service operations.

    """
    def __init__(self, driver):
        self._driver = driver
        self._cache = {}

    def _render_docs(self, help_command):
        renderer = FileRenderer()
        help_command.renderer = renderer
        help_command(None, None)
        # The report_level override is so that we don't print anything
        # to stdout/stderr on rendering issues.
        original_cli_help = renderer.contents.decode('utf-8')
        text_content = self._convert_rst_to_basic_text(original_cli_help)
        index = text_content.find('DESCRIPTION')
        if index > 0:
            text_content = text_content[index + len('DESCRIPTION'):]
        return text_content

    def _convert_rst_to_basic_text(self, contents):
        """Convert restructured text to basic text output.

        This function removes most of the decorations added
        in restructured text.

        This function is used to generate documentation we
        can show to users in a cross platform manner.

        Basic indentation and list formatting are kept,
        but many RST features are removed (such as
        section underlines).

        """
        # The report_level override is so that we don't print anything
        # to stdout/stderr on rendering issues.
        converted = publish_string(
            contents, writer=BasicTextWriter(),
            settings_overrides={'report_level': 5, 'halt_level': 5}
        )
        return converted.decode('utf-8').replace('\r', '')

    def get_doc_content(self, help_command):
        """Does the heavy lifting of retrieving the actual documentation
        content.

        """
        instance = help_command.EventHandlerClass(help_command)
        docevents.generate_events(help_command.session, help_command)
        content = self._render_docs(help_command)
        instance.unregister()
        return content

    def get_docs(self, parsed):
        lineage = parsed.lineage
        current_command = parsed.current_command
        if (tuple(lineage), current_command) not in self._cache:
            if current_command == 'aws':
                help_command = self._driver.create_help_command()
            else:
                subcommand_table = self._driver.subcommand_table
                for arg in lineage[1:]:
                    subcommand = subcommand_table[arg]
                    subcommand_table = subcommand.subcommand_table
                command = subcommand_table.get(current_command)
                help_command = command.create_help_command()
            docs = self.get_doc_content(help_command)
            self._cache[(tuple(lineage), current_command)] = docs
        return self._cache[(tuple(lineage), current_command)]


class FileRenderer:

    def __init__(self):
        self._io = io.BytesIO()

    def render(self, contents):
        self._io.write(contents)

    @property
    def contents(self):
        return self._io.getvalue()


class BasicTextWriter(textwriter.TextWriter):
    def translate(self):
        visitor = BasicTextTranslator(self.document)
        self.document.walkabout(visitor)
        self.output = visitor.body


class BasicTextTranslator(textwriter.TextTranslator):
    def depart_title(self, node):
        # Make the section titles upper cased, similar to
        # the man page output.
        text = ''.join(x[1] for x in self.states.pop() if x[0] == -1)
        self.stateindent.pop()
        self.states[-1].append((0, ['', text.upper(), '']))

    # The botocore TextWriter has additional formatting
    # for literals, for the aws-shell docs we don't want any
    # special processing so these nodes are noops.

    def visit_literal(self, node):
        pass

    def depart_literal(self, node):
        pass
