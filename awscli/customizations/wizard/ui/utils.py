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
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.layout.containers import Window, Dimension
from prompt_toolkit.layout.controls import BufferControl


def get_ui_control_by_buffer_name(layout, buffer_name):
    """Retrieves any UI control based on it's buffer name

    Prompt toolkit has a variety of methods on its layout to retrieve the
    a buffer by name but most of them require the control to be a
    BufferControl object. This function allows for better duck typing in that
    it includes UI control objects that have buffer properties.
    """
    for control in layout.find_all_controls():
        if hasattr(control, 'buffer') and control.buffer.name == buffer_name:
            return control
    raise ValueError(
        f"Couldn't find buffer in the current layout: {buffer_name}")


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


class FullyExtendedWidthWindow(Window):
    """Window that fully extends its available width"""
    def preferred_width(self, max_available_width):
        return Dimension(preferred=max_available_width)
