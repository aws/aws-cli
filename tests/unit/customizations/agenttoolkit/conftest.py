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
from unittest.mock import patch

import pytest

from awscli.customizations.agenttoolkit import state


@pytest.fixture(autouse=True)
def _isolate_agent_toolkit_home(tmp_path_factory):
    # Keep tests from writing state or lock files under the real ~/.aws.
    home = tmp_path_factory.mktemp('agent-toolkit-home')
    with patch.object(state, 'STATE_PATH', str(home / 'state.json')):
        yield home


@pytest.fixture(autouse=True)
def _home_is_tmp_path(tmp_path, monkeypatch):
    # Skills paths are relative to the home directory, so point it at the
    # test's directory. Tests that need another home or directory set it
    # themselves.
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    # Start in the home directory, so commands that also act on the current
    # directory's project-level skills never reach the real checkout.
    monkeypatch.chdir(tmp_path)
