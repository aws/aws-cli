import os

from utils import cd, bin_path, run, virtualenv_enabled

INSTALL_ARGS = "--no-binary :all: --no-build-isolation --no-cache-dir --no-index "
PINNED_PIP_VERSION = '20.0.2'
SETUP_DEPS = ("setuptools-", "setuptools_scm", "wheel")


class InstallationError(Exception):
    pass


def get_package_tarball(package_dir, package_prefix):
    package_filenames = sorted(
        [p for p in os.listdir(package_dir) if p.startswith(package_prefix)]
    )
    if len(package_filenames) == 0:
        raise InstallationError(
            "Unable to find local package starting with %s prefix." % package_prefix
        )
    # We only expect a single package from the downloader
    return package_filenames[0]


def install_local_package(package_dir, package, pip_script="pip"):
    with cd(package_dir):
        run(
            "%s install %s --find-links file://%s %s"
            % (pip_script, INSTALL_ARGS, package_dir, package)
        )


def find_and_install_tarball(package_dir, package_prefix, pip_script="pip"):
    tarball = get_package_tarball(package_dir, package_prefix)
    install_local_package(package_dir, tarball, pip_script)


def pip_install_packages(package_dir):
    package_dir = os.path.abspath(package_dir)

    # Setup pip to support modern setuptools calls
    pip_script = os.path.join(os.environ["VIRTUAL_ENV"], bin_path(), "pip")
    local_python = os.path.join(os.environ["VIRTUAL_ENV"], bin_path(), "python")

    # Windows can't replace a running pip.exe, so we need to work around
    run("%s -m pip install pip==%s" % (local_python, PINNED_PIP_VERSION))

    # Install or update prerequisite build packages
    setup_requires_dir = os.path.join(package_dir, "setup")
    install_setup_deps(pip_script, setup_requires_dir)

    find_and_install_tarball(package_dir, "awscli", pip_script)


def install_setup_deps(pip_script, setup_package_dir):
    # These packages need to be installed in this order before we
    # attempt anything else in order to support PEP517 setup_requires
    # specifications.

    # We need setuptools >= 37.0.0 for setuptools_scm to work properly
    for setup_dep in SETUP_DEPS:
        find_and_install_tarball(setup_package_dir, setup_dep, pip_script)


def install_packages(package_dir):
    """Builds setup environment and installs copies of local packages for CLI"""

    if not virtualenv_enabled():
        raise InstallationError(
            "Installation being performed outside of a virtualenv. Please enable before running."
        )
    else:
        pip_install_packages(package_dir)
