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
from prompt_toolkit.layout.containers import Window, Dimension
from prompt_toolkit.layout.controls import BufferControl


class Spacer:
    """Fills empty space in a layout

    It is helpful for extending a particular container with a visual
    element such as expanding tab column in the wizard app with the
    color gray.
    """
    def __init__(self):
        self.container = self._get_container()

    def _get_container(self):
        buffer = Buffer(
            document=Document(''),
            read_only=True
        )
        return Window(
            content=BufferControl(
                buffer=buffer, focusable=False
            )
        )

    def __pt_container__(self):
        return self.container

