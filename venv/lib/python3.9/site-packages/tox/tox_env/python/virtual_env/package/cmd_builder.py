from __future__ import annotations

import glob
import shutil
import sys
import tarfile
from functools import partial
from io import TextIOWrapper
from os import PathLike
from pathlib import Path
from typing import Generator, Iterator, List, cast
from zipfile import ZipFile

from packaging.requirements import Requirement

from tox.config.sets import EnvConfigSet
from tox.config.types import Command
from tox.execute import Outcome
from tox.plugin import impl
from tox.session.cmd.run.single import run_command_set
from tox.tox_env.api import ToxEnvCreateArgs
from tox.tox_env.errors import Fail
from tox.tox_env.package import Package, PackageToxEnv
from tox.tox_env.python.package import PythonPackageToxEnv, SdistPackage, WheelPackage
from tox.tox_env.python.pip.req_file import PythonDeps
from tox.tox_env.python.virtual_env.api import VirtualEnv
from tox.tox_env.register import ToxEnvRegister
from tox.tox_env.runner import RunToxEnv
from tox.tox_env.util import add_change_dir_conf

from .pyproject import Pep517VirtualEnvPackager
from .util import dependencies_with_extras

if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    from importlib.metadata import Distribution
else:  # pragma: no cover (py38+)
    from importlib_metadata import Distribution


class VirtualEnvCmdBuilder(PythonPackageToxEnv, VirtualEnv):
    def __init__(self, create_args: ToxEnvCreateArgs) -> None:
        super().__init__(create_args)
        self._sdist_meta_tox_env: Pep517VirtualEnvPackager | None = None

    @staticmethod
    def id() -> str:
        return "virtualenv-cmd-builder"

    def register_config(self) -> None:
        super().register_config()
        root = self.core["toxinidir"]
        self.conf.add_config(
            keys="deps",
            of_type=PythonDeps,
            factory=partial(PythonDeps.factory, root),
            default=PythonDeps("", root),
            desc="Name of the python dependencies as specified by PEP-440",
        )
        self.conf.add_config(
            keys=["commands"],
            of_type=List[Command],
            default=[],
            desc="the commands to be called for testing",
        )
        add_change_dir_conf(self.conf, self.core)
        self.conf.add_config(
            keys=["ignore_errors"],
            of_type=bool,
            default=False,
            desc="when executing the commands keep going even if a sub-command exits with non-zero exit code",
        )
        self.conf.add_config(
            keys=["package_glob"],
            of_type=str,
            default=str(self.conf["env_tmp_dir"] / "dist" / "*"),
            desc="when executing the commands keep going even if a sub-command exits with non-zero exit code",
        )

    def requires(self) -> PythonDeps:
        return cast(PythonDeps, self.conf["deps"])

    def perform_packaging(self, for_env: EnvConfigSet) -> list[Package]:
        self.setup()
        path: Path | None = getattr(self.options, "install_pkg", None)
        if path is None:  # use install_pkg if specified, otherwise build via commands
            chdir: Path = self.conf["change_dir"]
            ignore_errors: bool = self.conf["ignore_errors"]
            status = run_command_set(self, "commands", chdir, ignore_errors, [])
            if status != Outcome.OK:
                raise Fail("stopping as failed to build package")
            package_glob = self.conf["package_glob"]
            found = glob.glob(package_glob)
            if not found:
                raise Fail(f"no package found in {package_glob}")
            elif len(found) != 1:
                raise Fail(f"found more than one package {', '.join(sorted(found))}")
            path = Path(found[0])
        return self.extract_install_info(for_env, path)

    def extract_install_info(self, for_env: EnvConfigSet, path: Path) -> list[Package]:
        extras: set[str] = for_env["extras"]
        if path.suffix == ".whl":
            wheel_dist = WheelDistribution(path)
            requires: list[str] = wheel_dist.requires or []
            deps = dependencies_with_extras([Requirement(i) for i in requires], extras, wheel_dist.metadata["Name"])
            package: Package = WheelPackage(path, deps)
        else:  # must be source distribution
            work_dir = self.env_tmp_dir / "sdist-extract"
            if work_dir.exists():  # pragma: no branch
                shutil.rmtree(work_dir)  # pragma: no cover
            work_dir.mkdir()
            with tarfile.open(str(path), "r:gz") as tar:
                tar.extractall(path=str(work_dir))
            assert self._sdist_meta_tox_env is not None  # the register run env is guaranteed to be called before this
            with self._sdist_meta_tox_env.display_context(self._has_display_suspended):
                self._sdist_meta_tox_env.root = next(work_dir.iterdir())  # contains a single egg info folder
                deps = self._sdist_meta_tox_env.get_package_dependencies(for_env)
                name = self._sdist_meta_tox_env.get_package_name(for_env)
            package = SdistPackage(path, dependencies_with_extras(deps, extras, name))
        return [package]

    def register_run_env(self, run_env: RunToxEnv) -> Generator[tuple[str, str], PackageToxEnv, None]:
        yield from super().register_run_env(run_env)
        # in case the outcome is a sdist we'll use this to find out its metadata
        result = yield f"{self.conf.name}_sdist_meta", Pep517VirtualEnvPackager.id()
        self._sdist_meta_tox_env = cast(Pep517VirtualEnvPackager, result)

    def child_pkg_envs(self, run_conf: EnvConfigSet) -> Iterator[PackageToxEnv]:  # noqa: U100
        if self._sdist_meta_tox_env is not None:  # pragma: no branch
            yield self._sdist_meta_tox_env


class WheelDistribution(Distribution):  # cannot subclass has type Any
    def __init__(self, wheel: Path) -> None:
        self._wheel = wheel
        self._dist_name: str | None = None

    @property
    def dist_name(self) -> str:
        if self._dist_name is None:
            with ZipFile(self._wheel) as zip_file:
                for name in zip_file.namelist():
                    root = name.split("/")[0]
                    if root.endswith(".dist-info"):
                        self._dist_name = root
                        break
                else:
                    raise Fail(f"no .dist-info inside {self._wheel}")
        return self._dist_name

    def read_text(self, filename: str) -> str | None:
        with ZipFile(self._wheel) as zip_file:
            try:
                with TextIOWrapper(zip_file.open(f"{self.dist_name}/{filename}"), encoding="utf-8") as file_handler:
                    return file_handler.read()
            except KeyError:
                return None

    def locate_file(self, path: str | PathLike[str]) -> PathLike[str]:
        return self._wheel / path  # pragma: no cover # not used by us, but part of the ABC


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_package_env(VirtualEnvCmdBuilder)
