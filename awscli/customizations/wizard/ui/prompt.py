# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from prompt_toolkit.application import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.layout.containers import Window, VSplit, Dimension
from prompt_toolkit.layout.controls import BufferControl


class WizardPrompt:
    def __init__(self, value_name, value_definition):
        self._value_name = value_name
        self._value_definition = value_definition
        self.container = self._get_container()

    def _get_container(self):
        return VSplit(
            [
                WizardPromptDescription(
                    self._value_name,
                    self._value_definition['description']
                ),
                WizardPromptAnswer(self._value_name)
            ]
        )

    def __pt_container__(self):
        return self.container


class WizardPromptDescription:
    def __init__(self, value_name, value_description):
        self._value_name = value_name
        self._value_description = value_description
        self.container = self._get_container()

    def _get_container(self):
        content = f'{self._value_description}:'
        buffer = Buffer(
            document=Document(content),
            read_only=True
        )
        return Window(
            content=BufferControl(
                buffer=buffer, focusable=False
            ),
            style=self._get_style,
            width=Dimension.exact(len(content) + 1),
            dont_extend_height=True,
        )

    def _get_style(self):
        if get_app().layout.has_focus(self._value_name):
            return 'class:wizard.prompt.description.current'
        else:
            return 'class:wizard.prompt.description'

    def __pt_container__(self):
        return self.container


class WizardPromptAnswer:
    def __init__(self, value_name):
        self._value_name = value_name
        self.container = self._get_answer_container()

    def _get_answer_container(self):
        return Window(
            content=BufferControl(
                buffer=Buffer(name=self._value_name)
            ),
            style=self._get_style,
            dont_extend_height=True,
        )

    def _get_style(self):
        if get_app().layout.has_focus(self._value_name):
            return 'class:wizard.prompt.answer.current'
        else:
            return 'class:wizard.prompt.answer'

    def __pt_container__(self):
        return self.container
