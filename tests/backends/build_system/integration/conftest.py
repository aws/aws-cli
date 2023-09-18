import pytest

from tests.backends.build_system.integration import VEnvWorkspace


@pytest.fixture
def workspace(tmp_path) -> VEnvWorkspace:
    return VEnvWorkspace(tmp_path)


@pytest.fixture(scope='module')
def exe_deps(tmpdir_factory):
    workspace = VEnvWorkspace(tmpdir_factory.mktemp('build_exe'))
    workspace.call_build_system("portable-exe", download_deps=True)
    return workspace


@pytest.fixture(scope='module')
def exe_no_deps(tmpdir_factory):
    workspace = VEnvWorkspace(tmpdir_factory.mktemp('build_exe'))
    workspace.install_dependencies()
    workspace.install_pyinstaller()
    workspace.call_build_system("portable-exe", download_deps=False)
    return workspace


@pytest.fixture(scope='module')
def sdist_deps(tmpdir_factory):
    workspace = VEnvWorkspace(tmpdir_factory.mktemp('system-sandbox'))
    workspace.call_build_system("system-sandbox", download_deps=True)
    return workspace


@pytest.fixture(scope='module')
def sdist_no_deps(tmpdir_factory):
    workspace = VEnvWorkspace(tmpdir_factory.mktemp('system-sandbox'))
    workspace.install_dependencies()
    workspace.call_build_system("system-sandbox", download_deps=False)
    return workspace
