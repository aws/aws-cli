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
from botocore.history import HistoryRecorder

from awscli.customizations.agentregistry import cache, utils


@pytest.fixture(autouse=True)
def history_recorder():
    """A fresh history recorder in place of the process-wide one.

    Commands under test wrap the recorder they redact, which would otherwise
    leak into tests of other modules running in the same process.
    """
    recorder = HistoryRecorder()
    with patch.object(
        utils, 'get_global_history_recorder', return_value=recorder
    ):
        yield recorder


@pytest.fixture(autouse=True)
def signed_in_registry():
    """No registry remembered for the 401 hint from an earlier test."""
    with patch.dict(utils._SIGNED_IN, {'registry_id': None, 'hinted': False}):
        yield utils._SIGNED_IN


@pytest.fixture(autouse=True)
def isolated_token_cache(tmp_path, monkeypatch):
    """Never the real ~/.aws/agent-registry/cache."""
    directory = tmp_path / 'isolated-token-cache'
    monkeypatch.setattr(cache, 'CACHE_DIR', str(directory))
    return directory


@pytest.fixture(autouse=True)
def no_metadata_fetch_at_refresh():
    """The pre-refresh metadata check never reaches the network here.

    It cannot be read by default, so a refresh goes ahead; tests about the
    check patch it themselves.
    """
    with patch.object(
        cache,
        'discover_registry',
        side_effect=utils.AgentRegistryJWTError('not in unit tests'),
    ) as discover:
        yield discover


@pytest.fixture(autouse=True)
def no_session_database():
    """Never open the CLI's session database (~/.aws/cli/cache/session.db).

    These tests run the whole driver many times, and each run would open the
    shared SQLite database and start a sweeper thread on it. Across pytest
    workers that contends for the database, which crashed the interpreter on
    Python 3.9.
    """
    with patch('awscli.clidriver.register_session_id_event'):
        yield
