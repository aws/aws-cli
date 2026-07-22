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
from awscli.compat import compat_input
from awscli.customizations.exceptions import ConfigurationError
from awscli.customizations.utils import uni_print
from awscli.utils import is_stdin_a_tty


def yes_no_choice(prompt):
    """
    Prompts the user to answer a yes/no question.
    Continually re-prompts for invalid selections.

    :param prompt: Prompt text.
    :returns: True for yes, False for no.
    """
    while True:
        response = compat_input(prompt)

        if response.lower() in ('y', 'yes'):
            return True
        elif response.lower() in ('n', 'no'):
            return False
        else:
            uni_print('Invalid response. Please enter "y" or "n"\n')


def yes_no_never_choice(prompt):
    """
    Prompts the user with a yes/no/never question.
    Continually re-prompts for invalid selections.

    :param prompt: Prompt text.
    :returns: 'yes', 'no', or 'never'.
    """
    while True:
        response = compat_input(prompt)

        if response.lower() in ('y', 'yes') or response == '':
            return 'yes'
        elif response.lower() in ('n', 'no'):
            return 'no'
        elif response.lower() == 'never':
            return 'never'
        else:
            uni_print('Invalid response. Please enter "y", "n", or "never"\n')


def multiselect_choice(
    message,
    items,
    display_format=None,
    preselected=None,
    pt_input=None,
    pt_output=None,
):
    """
    Present a list of items with checkboxes for multi-selection.

    Arrow keys to navigate, space to toggle, enter to confirm.

    :param message: Prompt message displayed above the choices.
    :param items: List of items to select from.
    :param display_format: Optional callable to format items for display.
    :param preselected: Optional set of indices to pre-check.
    :param pt_input: Optional prompt_toolkit input (for testing).
    :param pt_output: Optional prompt_toolkit output (for testing).
    :returns: List of selected items.
    """
    if pt_input is None and not is_stdin_a_tty():
        raise ConfigurationError(
            "This command requires an interactive terminal (TTY)."
        )
    # Imported lazily so that loading this module does not pull in
    # prompt_toolkit for commands that only use yes_no_choice.
    from prompt_toolkit import Application
    from prompt_toolkit.key_binding.key_bindings import KeyBindings
    from prompt_toolkit.layout import HSplit, Layout, Window
    from prompt_toolkit.layout.controls import UIContent, UIControl
    from prompt_toolkit.layout.dimension import Dimension
    from prompt_toolkit.layout.screen import Point
    from prompt_toolkit.widgets import Label

    class MultiSelectControl(UIControl):
        def __init__(self, items, display_format=None, preselected=None):
            self._items = items
            self._cursor = 0
            self._selected = set(
                preselected if preselected is not None else range(len(items))
            )
            self._display_format = display_format

        def is_focusable(self):
            return True

        def preferred_width(self, max_width):
            return max_width

        def preferred_height(
            self, width, max_height, wrap_lines, get_line_prefix
        ):
            return len(self._items)

        def create_content(self, width, height):
            def get_line(i):
                check = 'x' if i in self._selected else ' '
                item = self._items[i]
                if self._display_format:
                    item = self._display_format(item)
                style = 'bold' if i == self._cursor else ''
                return [(style, f'  [{check}] {item}')]

            return UIContent(
                get_line=get_line,
                cursor_position=Point(x=0, y=self._cursor),
                line_count=len(self._items),
            )

        def get_key_bindings(self):
            kb = KeyBindings()

            @kb.add('up')
            def move_up(event):
                self._cursor = (self._cursor - 1) % len(self._items)

            @kb.add('down')
            def move_down(event):
                self._cursor = (self._cursor + 1) % len(self._items)

            @kb.add(' ')
            def toggle(event):
                if self._cursor in self._selected:
                    self._selected.discard(self._cursor)
                else:
                    self._selected.add(self._cursor)

            @kb.add('enter')
            def confirm(event):
                result = [self._items[i] for i in sorted(self._selected)]
                event.app.exit(result=result)

            return kb

    control = MultiSelectControl(
        items, display_format=display_format, preselected=preselected
    )
    body = Window(
        control,
        always_hide_cursor=False,
        height=Dimension(min=len(items), max=len(items)),
    )

    layout = Layout(
        HSplit(
            [
                Label(
                    f'{message} (space to toggle, up/down arrows to navigate, enter to confirm):'
                ),
                body,
            ]
        ),
        focused_element=body,
    )

    app_bindings = KeyBindings()

    @app_bindings.add('c-c')
    def exit_app(event):
        event.app.exit(exception=KeyboardInterrupt, style='class:aborting')

    app = Application(
        layout=layout,
        key_bindings=app_bindings,
        full_screen=False,
        erase_when_done=True,
        input=pt_input,
        output=pt_output,
    )
    return app.run()
