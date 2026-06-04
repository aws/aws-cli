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
import pytest
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from awscli.customizations.prompts import multiselect_choice

# ANSI escape sequences for simulating input
UP = '\x1b[A'
DOWN = '\x1b[B'
SPACE = ' '
ENTER = '\r'
CTRL_C = '\x03'


@pytest.fixture
def pipe_input():
    with create_pipe_input() as inp:
        yield inp


def _run(pipe_input, items, **kwargs):
    return multiselect_choice(
        '', items, pt_input=pipe_input, pt_output=DummyOutput(), **kwargs
    )


def test_enter_returns_all_preselected_by_default(pipe_input):
    pipe_input.send_text(ENTER)
    assert _run(pipe_input, ['a', 'b', 'c']) == ['a', 'b', 'c']


def test_space_deselects_current_item(pipe_input):
    pipe_input.send_text(SPACE + ENTER)
    assert _run(pipe_input, ['a', 'b', 'c']) == ['b', 'c']


def test_navigate_down_and_deselect(pipe_input):
    pipe_input.send_text(DOWN + SPACE + ENTER)
    assert _run(pipe_input, ['a', 'b', 'c']) == ['a', 'c']


def test_navigate_up_wraps_around(pipe_input):
    pipe_input.send_text(UP + SPACE + ENTER)
    assert _run(pipe_input, ['a', 'b', 'c']) == ['a', 'b']


def test_toggle_on_and_off(pipe_input):
    pipe_input.send_text(SPACE + SPACE + ENTER)
    assert _run(pipe_input, ['a', 'b', 'c']) == ['a', 'b', 'c']


def test_deselect_all(pipe_input):
    pipe_input.send_text(SPACE + DOWN + SPACE + DOWN + SPACE + ENTER)
    assert _run(pipe_input, ['a', 'b', 'c']) == []


def test_preselected_none_starts_all_selected(pipe_input):
    pipe_input.send_text(ENTER)
    assert _run(pipe_input, ['x', 'y'], preselected=None) == ['x', 'y']


def test_preselected_subset(pipe_input):
    pipe_input.send_text(ENTER)
    assert _run(pipe_input, ['a', 'b', 'c'], preselected={1}) == ['b']


def test_preselected_empty(pipe_input):
    pipe_input.send_text(ENTER)
    assert _run(pipe_input, ['a', 'b', 'c'], preselected=set()) == []


def test_display_format_does_not_affect_return_value(pipe_input):
    pipe_input.send_text(ENTER)
    assert _run(
        pipe_input, [1, 2, 3], display_format=lambda x: f'item-{x}'
    ) == [1, 2, 3]


def test_single_item(pipe_input):
    pipe_input.send_text(ENTER)
    assert _run(pipe_input, ['only']) == ['only']


def test_ctrl_c_raises_keyboard_interrupt(pipe_input):
    pipe_input.send_text(CTRL_C)
    with pytest.raises(KeyboardInterrupt):
        _run(pipe_input, ['a', 'b'])
