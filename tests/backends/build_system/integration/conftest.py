import pytest

from tests.backends.build_system.integration import VEnvWorkspace


@pytest.fixture
def workspace(tmp_path) -> VEnvWorkspace:
    return VEnvWorkspace(tmp_path)
