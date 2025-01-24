from __future__ import annotations

import logging
import os
import sys
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Generator, Iterator, NoReturn, Optional, Sequence, cast

from cachetools import cached
from packaging.requirements import Requirement
from pyproject_api import BackendFailed, CmdStatus, Frontend

from tox.config.sets import EnvConfigSet
from tox.execute.api import ExecuteStatus
from tox.execute.pep517_backend import LocalSubProcessPep517Executor
from tox.execute.request import StdinSource
from tox.plugin import impl
from tox.tox_env.api import ToxEnvCreateArgs
from tox.tox_env.errors import Fail
from tox.tox_env.package import Package, PackageToxEnv
from tox.tox_env.python.package import (
    EditableLegacyPackage,
    EditablePackage,
    PythonPackageToxEnv,
    SdistPackage,
    WheelPackage,
)
from tox.tox_env.register import ToxEnvRegister
from tox.tox_env.runner import RunToxEnv
from tox.util.file_view import create_session_view

from ..api import VirtualEnv
from .util import dependencies_with_extras, dependencies_with_extras_from_markers

if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    from importlib.metadata import Distribution, PathDistribution
else:  # pragma: no cover (<py38)
    from importlib_metadata import Distribution, PathDistribution

if sys.version_info >= (3, 11):  # pragma: no cover (py311+)
    import tomllib
else:  # pragma: no cover (py311+)
    import tomli as tomllib

ConfigSettings = Optional[Dict[str, Any]]


class ToxBackendFailed(Fail, BackendFailed):
    def __init__(self, backend_failed: BackendFailed) -> None:
        Fail.__init__(self)
        result: dict[str, Any] = {
            "code": backend_failed.code,
            "exc_type": backend_failed.exc_type,
            "exc_msg": backend_failed.exc_msg,
        }
        BackendFailed.__init__(
            self,
            result,
            backend_failed.out,
            backend_failed.err,
        )


class BuildEditableNotSupported(RuntimeError):
    """raised when build editable is not supported"""


class ToxCmdStatus(CmdStatus):
    def __init__(self, execute_status: ExecuteStatus) -> None:
        self._execute_status = execute_status

    @property
    def done(self) -> bool:
        # 1. process died
        status = self._execute_status
        if status.exit_code is not None:  # pragma: no branch
            return True  # pragma: no cover
        # 2. the backend output reported back that our command is done
        return b"\n" in status.out.rpartition(b"Backend: Wrote response ")[0]

    def out_err(self) -> tuple[str, str]:
        status = self._execute_status
        if status is None or status.outcome is None:  # interrupt before status create # pragma: no branch
            return "", ""  # pragma: no cover
        return status.outcome.out_err()


class Pep517VirtualEnvPackager(PythonPackageToxEnv, VirtualEnv):
    """local file system python virtual environment via the virtualenv package"""

    def __init__(self, create_args: ToxEnvCreateArgs) -> None:
        super().__init__(create_args)
        self._frontend_: Pep517VirtualEnvFrontend | None = None
        self.builds: defaultdict[str, list[EnvConfigSet]] = defaultdict(list)
        self._distribution_meta: PathDistribution | None = None
        self._package_dependencies: list[Requirement] | None = None
        self._package_name: str | None = None
        self._pkg_lock = RLock()  # can build only one package at a time
        self.root = self.conf["package_root"]
        self._package_paths: set[Path] = set()

    @staticmethod
    def id() -> str:
        return "virtualenv-pep-517"

    @property
    def _frontend(self) -> Pep517VirtualEnvFrontend:
        if self._frontend_ is None:
            self._frontend_ = Pep517VirtualEnvFrontend(self.root, self)
        return self._frontend_

    def register_config(self) -> None:
        super().register_config()
        self.conf.add_config(
            keys=["meta_dir"],
            of_type=Path,
            default=lambda conf, name: self.env_dir / ".meta",  # noqa: U100
            desc="directory where to put the project metadata files",
        )
        self.conf.add_config(
            keys=["pkg_dir"],
            of_type=Path,
            default=lambda conf, name: self.env_dir / "dist",  # noqa: U100
            desc="directory where to put project packages",
        )

    @property
    def pkg_dir(self) -> Path:
        return cast(Path, self.conf["pkg_dir"])

    @property
    def meta_folder(self) -> Path:
        meta_folder: Path = self.conf["meta_dir"]
        meta_folder.mkdir(exist_ok=True)
        return meta_folder

    @property
    def meta_folder_if_populated(self) -> Path | None:
        """Return the metadata directory if it contains any files, otherwise None."""
        meta_folder = self.meta_folder
        if meta_folder.exists() and tuple(meta_folder.iterdir()):
            return meta_folder
        return None

    def register_run_env(self, run_env: RunToxEnv) -> Generator[tuple[str, str], PackageToxEnv, None]:
        yield from super().register_run_env(run_env)
        build_type = run_env.conf["package"]
        self.builds[build_type].append(run_env.conf)

    def _setup_env(self) -> None:
        super()._setup_env()
        if "editable" in self.builds:
            if not self._frontend.optional_hooks["build_editable"]:
                raise BuildEditableNotSupported
            build_requires = self._frontend.get_requires_for_build_editable().requires
            self._install(build_requires, PythonPackageToxEnv.__name__, "requires_for_build_editable")
        if "wheel" in self.builds:
            build_requires = self._frontend.get_requires_for_build_wheel().requires
            self._install(build_requires, PythonPackageToxEnv.__name__, "requires_for_build_wheel")
        if "sdist" in self.builds or "external" in self.builds:
            build_requires = self._frontend.get_requires_for_build_sdist().requires
            self._install(build_requires, PythonPackageToxEnv.__name__, "requires_for_build_sdist")

    def _teardown(self) -> None:
        executor = self._frontend.backend_executor
        if executor is not None:  # pragma: no branch
            try:
                if executor.is_alive:
                    self._frontend._send("_exit")  # try first on amicable shutdown
            except SystemExit:  # pragma: no cover  # if already has been interrupted ignore
                pass
            finally:
                executor.close()
        for path in self._package_paths:
            if path.exists():
                logging.debug("delete package %s", path)
                path.unlink()
        super()._teardown()

    def perform_packaging(self, for_env: EnvConfigSet) -> list[Package]:
        """build the package to install"""
        try:
            deps = self._load_deps(for_env)
        except BuildEditableNotSupported:
            targets = [e for e in self.builds.pop("editable") if e["package"] == "editable"]
            names = ", ".join(sorted({t.env_name for t in targets if t.env_name}))
            logging.error(
                f"package config for {names} is editable, however the build backend {self._frontend.backend}"
                f" does not support PEP-660, falling back to editable-legacy - change your configuration to it",
            )
            for env in targets:
                env._defined["package"].value = "editable-legacy"  # type: ignore
                self.builds["editable-legacy"].append(env)
            deps = self._load_deps(for_env)
        of_type: str = for_env["package"]
        if of_type == "editable-legacy":
            self.setup()
            deps = [*self.requires(), *self._frontend.get_requires_for_build_sdist().requires] + deps
            package: Package = EditableLegacyPackage(self.core["tox_root"], deps)  # the folder itself is the package
        elif of_type == "sdist":
            self.setup()
            with self._pkg_lock:
                sdist = self._frontend.build_sdist(sdist_directory=self.pkg_dir).sdist
                sdist = create_session_view(sdist, self._package_temp_path)
                self._package_paths.add(sdist)
                package = SdistPackage(sdist, deps)
        elif of_type in {"wheel", "editable"}:
            w_env = self._wheel_build_envs.get(for_env["wheel_build_env"])
            if w_env is not None and w_env is not self:
                with w_env.display_context(self._has_display_suspended):
                    return w_env.perform_packaging(for_env)
            else:
                self.setup()
                method = "build_editable" if of_type == "editable" else "build_wheel"
                with self._pkg_lock:
                    wheel = getattr(self._frontend, method)(
                        wheel_directory=self.pkg_dir,
                        metadata_directory=self.meta_folder_if_populated,
                        config_settings=self._wheel_config_settings,
                    ).wheel
                    wheel = create_session_view(wheel, self._package_temp_path)
                    self._package_paths.add(wheel)
                package = (EditablePackage if of_type == "editable" else WheelPackage)(wheel, deps)
        else:  # pragma: no cover # for when we introduce new packaging types and don't implement
            raise TypeError(f"cannot handle package type {of_type}")  # pragma: no cover
        return [package]

    @property
    def _package_temp_path(self) -> Path:
        return cast(Path, self.core["temp_dir"]) / "package"

    def _load_deps(self, for_env: EnvConfigSet) -> list[Requirement]:
        # first check if this is statically available via PEP-621
        deps = self._load_deps_from_static(for_env)
        if deps is None:
            deps = self._load_deps_from_built_metadata(for_env)
        return deps

    def _load_deps_from_static(self, for_env: EnvConfigSet) -> list[Requirement] | None:
        pyproject_file = self.core["package_root"] / "pyproject.toml"
        if not pyproject_file.exists():  # check if it's static PEP-621 metadata
            return None
        with pyproject_file.open("rb") as file_handler:
            pyproject = tomllib.load(file_handler)
        if "project" not in pyproject:
            return None  # is not a PEP-621 pyproject
        project = pyproject["project"]
        extras: set[str] = for_env["extras"]
        for dynamic in project.get("dynamic", []):
            if dynamic == "dependencies" or (extras and dynamic == "optional-dependencies"):
                return None  # if any dependencies are dynamic we can just calculate all dynamically

        deps_with_markers: list[tuple[Requirement, set[str | None]]] = [
            (Requirement(i), {None}) for i in project.get("dependencies", [])
        ]
        optional_deps = project.get("optional-dependencies", {})
        for extra, reqs in optional_deps.items():
            deps_with_markers.extend((Requirement(req), {extra}) for req in (reqs or []))
        return dependencies_with_extras_from_markers(
            deps_with_markers=deps_with_markers,
            extras=extras,
            package_name=project.get("name", "."),
        )

    def _load_deps_from_built_metadata(self, for_env: EnvConfigSet) -> list[Requirement]:
        # dependencies might depend on the python environment we're running in => if we build a wheel use that env
        # to calculate the package metadata, otherwise ourselves
        of_type: str = for_env["package"]
        reqs: list[Requirement] | None = None
        name = ""
        if of_type in ("wheel", "editable"):  # wheel packages
            w_env = self._wheel_build_envs.get(for_env["wheel_build_env"])
            if w_env is not None and w_env is not self:
                with w_env.display_context(self._has_display_suspended):
                    if isinstance(w_env, Pep517VirtualEnvPackager):
                        reqs, name = w_env.get_package_dependencies(for_env), w_env.get_package_name(for_env)
                    else:
                        reqs = []
        if reqs is None:
            reqs = self.get_package_dependencies(for_env)
            name = self.get_package_name(for_env)
        extras: set[str] = for_env["extras"]
        deps = dependencies_with_extras(reqs, extras, name)
        return deps

    def get_package_dependencies(self, for_env: EnvConfigSet) -> list[Requirement]:
        with self._pkg_lock:
            if self._package_dependencies is None:  # pragma: no branch
                self._ensure_meta_present(for_env)
                requires: list[str] = cast(PathDistribution, self._distribution_meta).requires or []
                self._package_dependencies = [Requirement(i) for i in requires]  # pragma: no branch
        return self._package_dependencies

    def get_package_name(self, for_env: EnvConfigSet) -> str:
        with self._pkg_lock:
            if self._package_name is None:  # pragma: no branch
                self._ensure_meta_present(for_env)
                self._package_name = cast(PathDistribution, self._distribution_meta).metadata["Name"]
        return self._package_name

    def _ensure_meta_present(self, for_env: EnvConfigSet) -> None:
        if self._distribution_meta is not None:  # pragma: no branch
            return  # pragma: no cover
        self.setup()
        end = self._frontend
        if for_env["package"] == "editable":
            dist_info = end.prepare_metadata_for_build_editable(self.meta_folder, self._wheel_config_settings).metadata
        else:
            dist_info = end.prepare_metadata_for_build_wheel(self.meta_folder, self._wheel_config_settings).metadata
        self._distribution_meta = Distribution.at(str(dist_info))

    @property
    def _wheel_config_settings(self) -> ConfigSettings | None:
        return {"--build-option": []}

    def requires(self) -> tuple[Requirement, ...]:
        return self._frontend.requires


class Pep517VirtualEnvFrontend(Frontend):
    def __init__(self, root: Path, env: Pep517VirtualEnvPackager) -> None:
        super().__init__(*Frontend.create_args_from_folder(root))
        self._tox_env = env
        self._backend_executor_: LocalSubProcessPep517Executor | None = None
        into: dict[str, Any] = {}
        pkg_cache = cached(
            into,
            key=lambda *args, **kwargs: "wheel" if "wheel_directory" in kwargs else "sdist",  # noqa: U100
        )
        self.build_wheel = pkg_cache(self.build_wheel)  # type: ignore
        self.build_sdist = pkg_cache(self.build_sdist)  # type: ignore
        self.build_editable = pkg_cache(self.build_editable)  # type: ignore

    @property
    def backend_cmd(self) -> Sequence[str]:
        return ["python"] + self.backend_args

    def _send(self, cmd: str, **kwargs: Any) -> tuple[Any, str, str]:
        try:
            if cmd in ("prepare_metadata_for_build_wheel", "prepare_metadata_for_build_editable"):
                # given we'll build a wheel we might skip the prepare step
                if "wheel" in self._tox_env.builds or "editable" in self._tox_env.builds:
                    return None, "", ""  # will need to build wheel either way, avoid prepare
            return super()._send(cmd, **kwargs)
        except BackendFailed as exception:
            raise exception if isinstance(exception, ToxBackendFailed) else ToxBackendFailed(exception) from exception

    @contextmanager
    def _send_msg(
        self,
        cmd: str,
        result_file: Path,  # noqa: U100
        msg: str,
    ) -> Iterator[ToxCmdStatus]:
        with self._tox_env.execute_async(
            cmd=self.backend_cmd,
            cwd=self._root,
            stdin=StdinSource.API,
            show=None,
            run_id=cmd,
            executor=self.backend_executor,
        ) as execute_status:
            execute_status.write_stdin(f"{msg}{os.linesep}")
            yield ToxCmdStatus(execute_status)
        outcome = execute_status.outcome
        if outcome is not None:  # pragma: no branch
            outcome.assert_success()

    def _unexpected_response(self, cmd: str, got: Any, expected_type: Any, out: str, err: str) -> NoReturn:
        try:
            super()._unexpected_response(cmd, got, expected_type, out, err)
        except BackendFailed as exception:
            raise exception if isinstance(exception, ToxBackendFailed) else ToxBackendFailed(exception) from exception

    @property
    def backend_executor(self) -> LocalSubProcessPep517Executor:
        if self._backend_executor_ is None:
            environment_variables = self._tox_env.environment_variables.copy()
            backend = os.pathsep.join(str(i) for i in self._backend_paths).strip()
            if backend:
                environment_variables["PYTHONPATH"] = backend
            self._backend_executor_ = LocalSubProcessPep517Executor(
                colored=self._tox_env.options.is_colored,
                cmd=self.backend_cmd,
                env=environment_variables,
                cwd=self._root,
            )

        return self._backend_executor_

    @contextmanager
    def _wheel_directory(self) -> Iterator[Path]:
        yield self._tox_env.pkg_dir  # use our local wheel directory for building wheel


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_package_env(Pep517VirtualEnvPackager)
