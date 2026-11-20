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
import glob
import keyword
import os
import re
import shutil

from awscli.customizations.lambdaweb import constants, output
from awscli.customizations.lambdaweb.exceptions import (
    EntryPointNotFoundError,
    InvalidSourceError,
)
from awscli.customizations.lambdaweb.runtimes.base import (
    HIDDEN_FILES_BULLET,
    EntrySelection,
    Runtime,
    ScaffoldDocs,
    validate_relative_entry,
)
from awscli.customizations.lambdaweb.utils import posix_relpath

RUNTIMES = ('python3.15',)
ENTRYPOINT_ENV_VAR = 'AWS_LAMBDA_PYTHON_ENTRYPOINT'
DEFAULT_ENTRY = 'main:app'
SCAFFOLD_ENTRY = 'main.py'
INTERFACES = ('asgi', 'wsgi')
# The runtime OS runs glibc 2.34, so wheels tagged up to manylinux_2_34 are
# compatible. pip matches --platform values against wheel tags literally
# (no glibc ceiling), so each tag family in common use needs its own flag.
WHEEL_PLATFORMS = (
    'manylinux2014_aarch64',
    'manylinux_2_28_aarch64',
    'manylinux_2_34_aarch64',
)
PIP_PLATFORM_FLAGS = ' '.join(
    f'--platform {platform}' for platform in WHEEL_PLATFORMS
)
# uv applies a real glibc ceiling, so one value accepts every older tag.
UV_PLATFORM = 'aarch64-manylinux_2_34'

# Files that identify a Python project when --runtime is omitted.
MARKER_FILES = (
    'requirements.txt',
    'pyproject.toml',
    'Pipfile',
    'uv.lock',
    'poetry.lock',
    'setup.py',
    'manage.py',
)

# Checked in order when --entry-point is omitted; each maps to module:app.
ENTRY_CANDIDATES = (
    'main.py',
    'app.py',
    'application.py',
    'asgi.py',
    'wsgi.py',
    'server.py',
    'src/main.py',
    'app/main.py',
)

# The generated AGENTS.md paraphrases this list in its packaging
# section; update both together.
EXCLUDE_PATTERNS = (
    'venv/',
    '.venv/',
    '*.egg-info/',
    '.pytest_cache/',
    '.mypy_cache/',
    '.ruff_cache/',
    '.tox/',
    '.nox/',
    '.hypothesis/',
    'htmlcov/',
    '.coverage',
    '*.pyo',
)

# A top-level ``app = ...`` or ``application = ...``, type hint allowed.
_OBJECT_ASSIGNMENT = re.compile(
    r'^(app|application)\s*(?::[^=\n]+)?=', re.MULTILINE
)
# A top-level ``def app(...)``, ``async def app``, or ``class application``.
_OBJECT_DEF = re.compile(
    r'^(?:async\s+def|def|class)\s+(app|application)\b', re.MULTILINE
)
# An import line that binds the name ``app`` or ``application``.
_OBJECT_IMPORT = re.compile(
    r'^(?:from\s+\S+\s+)?import\s+[^\n]*\b(app|application)\b',
    re.MULTILINE,
)
# Pulls the value out of ``os.environ.setdefault('DJANGO_SETTINGS_MODULE',
# ...)`` in manage.py. The first segment names the project package, for
# both ``mysite.settings`` and split layouts like ``config.settings.local``.
_DJANGO_SETTINGS = re.compile(
    r"""DJANGO_SETTINGS_MODULE['"]\s*,\s*['"](\w+)[\w.]*['"]"""
)
# A ``Tag: cp315-cp315-manylinux_2_28_aarch64`` line in a wheel's
# WHEEL metadata file.
_WHEEL_TAG = re.compile(r'^Tag:\s*(\S+)', re.MULTILINE)
# Pure-Python wheels say ``Root-Is-Purelib: true`` and run anywhere.
_PURELIB = re.compile(r'^Root-Is-Purelib:\s*true', re.MULTILINE | re.I)
# Any arm64 Linux platform tag: bare ``linux_aarch64`` or any
# ``manylinux*`` flavor.
_LINUX_ARM64 = re.compile(r'^(?:manylinux[\w.]*|linux)_aarch64$')


def _platform_runs_on_runtime(platform):
    """Return True when a wheel platform tag targets arm64 Linux."""
    return _LINUX_ARM64.match(platform) is not None


def _invalid_entry(value):
    return InvalidSourceError(
        f"--entry-point '{value}' isn't a valid Python entry point. Use "
        'module:object as you would with uvicorn or gunicorn (for example, '
        'main:app or app.main:app), optionally prefixed with asgi: or wsgi:, '
        'or the path to a .py file.'
    )


def _check_dotted(value, original):
    parts = value.split('.')
    if not value or any(
        not part.isidentifier() or keyword.iskeyword(part) for part in parts
    ):
        raise _invalid_entry(original)


def parse_entry(value):
    """Return ``(interface, module, obj)`` for a ``module:object`` string."""
    parts = value.rsplit(':', 2)
    if len(parts) < 2:
        raise _invalid_entry(value)
    obj = parts.pop()
    module = parts.pop()
    interface = parts.pop() if parts else None
    if interface is not None and interface not in INTERFACES:
        raise _invalid_entry(value)
    _check_dotted(module, value)
    _check_dotted(obj, value)
    return interface, module, obj


def format_entry(interface, module, obj):
    address = f'{module}:{obj}'
    return address if interface is None else f'{interface}:{address}'


def module_file(source_dir, module):
    """Return the module's file relative to ``source_dir``.

    A module that does not exist raises ``EntryPointNotFoundError``. A
    namespace package (a directory without ``__init__.py``) is importable
    but cannot define an application object, so it is rejected.
    """
    base = os.path.join(source_dir, *module.split('.'))
    for candidate in (f'{base}.py', os.path.join(base, '__init__.py')):
        if os.path.isfile(candidate):
            return posix_relpath(os.path.relpath(candidate, source_dir))
    if os.path.isdir(base):
        raise InvalidSourceError(
            f"Python module '{module}' is a directory without __init__.py "
            f"under '{source_dir}', so it cannot define an application "
            'object. Add an __init__.py that defines it, or use a module '
            'file.'
        )
    raise EntryPointNotFoundError(
        f"Python module '{module}' was not found under '{source_dir}'. The "
        f"command looked for {posix_relpath(os.path.relpath(base, source_dir))}"
        '.py and a package directory with that name. Check --entry-point, or '
        'include the module in --code.'
    )


def _entry_from_path(source_dir, value):
    """Translate ``pkg/module.py[:object]`` into ``(module, obj)``."""
    path, obj = value, None
    if not value.endswith('.py'):
        path, sep, obj = value.rpartition(':')
        if not sep or not path.endswith('.py'):
            raise _invalid_entry(value)
    normalized = validate_relative_entry(source_dir, path)
    if not os.path.isfile(os.path.join(source_dir, normalized)):
        head = path.split(':', 1)[0]
        if ':' in path and head in INTERFACES:
            raise InvalidSourceError(
                f"--entry-point '{value}' combines an interface prefix "
                'with a file path. Use the prefix with module:object '
                f'(for example, {head}:main:app), or the file path '
                'without a prefix.'
            ) from None
        raise EntryPointNotFoundError(
            f"--entry-point '{path}' was not found under '{source_dir}'."
        )
    parts = posix_relpath(normalized)[: -len('.py')].split('/')
    if parts[-1] == '__init__':
        parts.pop()
    if not parts or any(
        not part.isidentifier() or keyword.iskeyword(part) for part in parts
    ):
        raise InvalidSourceError(
            f"entry point '{path}' can't be imported as a Python module "
            'because a directory or file name is not a valid identifier. '
            'Rename the path, or pass --entry-point module:object for an '
            'importable module.'
        )
    if obj is None:
        # Match auto-detection: pick ``app`` or ``application`` from the
        # module's assignments when the path names no object.
        obj = _object_name(source_dir, normalized)
    _check_dotted(obj, value)
    return '.'.join(parts), obj


def _object_name(source_dir, relpath):
    """Pick ``app`` or ``application`` from the module's definitions."""
    try:
        with open(os.path.join(source_dir, relpath), encoding='utf-8') as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        return 'app'
    names = set()
    for pattern in (_OBJECT_ASSIGNMENT, _OBJECT_DEF, _OBJECT_IMPORT):
        names.update(pattern.findall(text))
    if not names:
        # A factory layout (``def create_app():``) defines neither name;
        # the runtime would import the module and fail to resolve the
        # object, so say so now instead of deploying a broken revision.
        output.progress(
            f"Warning: {posix_relpath(relpath)} does not define 'app' or "
            "'application' at the top level, so the entry point may not "
            'resolve. Define the application object at module level (for '
            'example app = create_app()), or pass --entry-point '
            'module:object.'
        )
        return 'app'
    if 'app' not in names:
        return 'application'
    return 'app'


def _django_entry(source_dir):
    """Return ``project.asgi:application`` or the WSGI form for Django."""
    manage = os.path.join(source_dir, 'manage.py')
    if not os.path.isfile(manage):
        return None
    try:
        with open(manage, encoding='utf-8') as f:
            match = _DJANGO_SETTINGS.search(f.read())
    except (OSError, UnicodeDecodeError):
        match = None
    projects = []
    if match and match.group(1).isidentifier():
        projects.append(match.group(1))
    # Dependencies installed with ``--target .`` sit next to the project and
    # can contain asgi.py or wsgi.py (asgiref does), so only directories that
    # carry Django settings qualify as fallback projects.
    for entry in sorted(os.listdir(source_dir)):
        if entry in projects or not entry.isidentifier():
            continue
        base = os.path.join(source_dir, entry)
        if os.path.isfile(os.path.join(base, 'settings.py')) or os.path.isdir(
            os.path.join(base, 'settings')
        ):
            projects.append(entry)
    for project in projects:
        for name in ('asgi', 'wsgi'):
            if os.path.isfile(os.path.join(source_dir, project, f'{name}.py')):
                return f'{project}.{name}:application'
    return None


def resolve_entry_point(source_dir, explicit=None):
    """Return the ``module:object`` entry for ``source_dir``."""
    if explicit is not None:
        head = explicit.split(':', 1)[0]
        if (
            explicit.endswith('.py')
            or head.endswith('.py')
            or '/' in explicit
            or os.sep in explicit
        ):
            module, obj = _entry_from_path(source_dir, explicit)
            return format_entry(None, module, obj)
        interface, module, obj = parse_entry(explicit)
        if module.endswith('.py'):
            example = (
                f"{interface or 'asgi'}:"
                f"{module[: -len('.py')].replace('/', '.')}:{obj}"
            )
            raise InvalidSourceError(
                f"--entry-point '{explicit}' names module '{module}', "
                'which looks like a file path. Use module:object '
                f'without the .py suffix (for example, {example}), or '
                'the file form without an interface prefix.'
            )
        module_file(source_dir, module)
        return format_entry(interface, module, obj)

    for candidate in ENTRY_CANDIDATES:
        if os.path.isfile(os.path.join(source_dir, candidate)):
            module = candidate[: -len('.py')].replace('/', '.')
            return f'{module}:{_object_name(source_dir, candidate)}'
    django = _django_entry(source_dir)
    if django is not None:
        return django
    candidates = ', '.join(ENTRY_CANDIDATES)
    raise EntryPointNotFoundError(
        f"No Python entry point was found under '{source_dir}'. The command "
        f'checked: {candidates}, and a Django project with manage.py. Use '
        '--entry-point module:object to specify one (for example, '
        '--entry-point src.server:app).'
    )


def select(source_dir, entry):
    """Return the :class:`EntrySelection` for a ``module:object`` entry.

    The runtime imports ``main:app`` unless ``AWS_LAMBDA_PYTHON_ENTRYPOINT``
    names another module or object, so any other entry is applied through
    that variable.
    """
    _, module, _ = parse_entry(entry)
    env = None if entry == DEFAULT_ENTRY else {ENTRYPOINT_ENV_VAR: entry}
    return EntrySelection(
        display=entry, bundle_path=module_file(source_dir, module), env=env
    )


def python_version(runtime_id):
    return runtime_id[len('python') :]


def _dist_info_dirs(source_dir):
    return sorted(
        glob.glob(os.path.join(glob.escape(source_dir), '*.dist-info'))
    )


def _poetry_declares(text):
    """Return True when [tool.poetry.dependencies] lists a package.

    The ``python`` entry is the interpreter constraint that ``poetry``
    always writes, not a package, so it alone does not count.
    """
    in_section = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('['):
            in_section = stripped == '[tool.poetry.dependencies]'
            continue
        if not in_section or not stripped or stripped.startswith('#'):
            continue
        key = stripped.split('=', 1)[0].strip().strip('"').strip("'")
        if key != 'python':
            return True
    return False


def _declared_dependencies(source_dir):
    """Return the manifest that declares dependencies, or ``None``."""
    requirements = os.path.join(source_dir, 'requirements.txt')
    if os.path.isfile(requirements):
        try:
            with open(requirements, encoding='utf-8') as f:
                lines = [line.strip() for line in f]
        except (OSError, UnicodeDecodeError):
            lines = []
        for line in lines:
            if not line or line.startswith('#'):
                continue
            if line.startswith('-'):
                # Option lines such as --index-url configure pip without
                # declaring a package. Lines that pull in requirements
                # (-r/-c) or an editable install (-e) still count.
                head = line.split('=', 1)[0].split()[0]
                if head not in (
                    '-r',
                    '--requirement',
                    '-c',
                    '--constraint',
                    '-e',
                    '--editable',
                ):
                    continue
            return 'requirements.txt'
    for name in ('uv.lock', 'poetry.lock', 'Pipfile.lock', 'Pipfile'):
        if os.path.isfile(os.path.join(source_dir, name)):
            return name
    pyproject = os.path.join(source_dir, 'pyproject.toml')
    if os.path.isfile(pyproject):
        try:
            with open(pyproject, encoding='utf-8') as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            text = ''
        if re.search(r'^\s*dependencies\s*=\s*\[\s*["\']', text, re.M):
            return 'pyproject.toml'
        if _poetry_declares(text):
            return 'pyproject.toml'
    return None


def install_command(source_dir, runtime_id):
    """Return the arm64 install command that matches the project's tooling."""
    version = python_version(runtime_id)
    has_requirements = os.path.isfile(
        os.path.join(source_dir, 'requirements.txt')
    )
    use_uv = os.path.isfile(os.path.join(source_dir, 'uv.lock')) or bool(
        shutil.which('uv')
    )
    if use_uv:
        has_pyproject = os.path.isfile(
            os.path.join(source_dir, 'pyproject.toml')
        )
        source = 'requirements.txt' if has_requirements else 'pyproject.toml'
        command = (
            f'uv pip install -r {source} --target . --python-platform '
            f'{UV_PLATFORM} --python-version {version}'
        )
        if not has_requirements and not has_pyproject:
            # A lock file alone (for example Pipfile.lock) names no file
            # that uv can install from directly.
            command = (
                'export the dependencies to requirements.txt, then '
                'uv pip install -r requirements.txt --target . '
                f'--python-platform {UV_PLATFORM} --python-version {version}'
            )
        return command
    command = (
        'pip install -r requirements.txt --target . --only-binary=:all: '
        f'{PIP_PLATFORM_FLAGS} --implementation cp '
        f'--python-version {version}'
    )
    if not has_requirements:
        command = (
            f'export the dependencies to requirements.txt, then {command}'
        )
    return command


def _tag_runs_on_runtime(tag, version):
    """Return True when a full wheel tag can load on the runtime."""
    parts = tag.split('-')
    if len(parts) != 3:
        return True
    interpreter, abi, platform = parts
    # A runtime id without a usable version (for example a bare
    # 'python3' sent through for the service to validate) gives no
    # interpreter to compare against, so only the platform is checked.
    if re.fullmatch(r'\d+\.\d+', version):
        if abi == 'abi3':
            # Stable-ABI wheels load on every version at or above
            # their floor.
            floor = re.match(r'^cp3(\d+)$', interpreter)
            if floor is not None and int(floor.group(1)) > int(
                version.split('.')[1]
            ):
                return False
        elif abi not in ('none', 'cp' + version.replace('.', '')):
            # Covers wheels built for another version (cp313) and for
            # a free-threaded interpreter (cp315t).
            return False
    return platform == 'any' or _platform_runs_on_runtime(platform)


def _foreign_wheels(dist_info_dirs, version):
    """Return package names whose wheels cannot load on the runtime."""
    foreign = []
    for path in dist_info_dirs:
        try:
            with open(os.path.join(path, 'WHEEL'), encoding='utf-8') as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        if _PURELIB.search(text):
            continue
        tags = _WHEEL_TAG.findall(text)
        if not tags:
            continue
        if any(_tag_runs_on_runtime(tag, version) for tag in tags):
            continue
        reasons = set()
        for tag in tags:
            parts = tag.split('-')
            if len(parts) != 3:
                continue
            interpreter, abi, platform = parts
            if platform != 'any' and not _platform_runs_on_runtime(platform):
                reasons.add(platform)
            else:
                reasons.add(f'{interpreter}-{abi}')
        name = os.path.basename(path)[: -len('.dist-info')]
        foreign.append((name, sorted(reasons)[0]))
    return foreign


def inspect_dependencies(source_dir, runtime_id):
    """Warn when dependencies are missing or cannot load on the runtime."""
    installed = _dist_info_dirs(source_dir)
    if not installed:
        manifest = _declared_dependencies(source_dir)
        if manifest is None:
            return
        command = install_command(source_dir, runtime_id)
        output.progress(
            f'Warning: {manifest} declares dependencies, but no installed '
            f"packages were found under --code '{source_dir}'. The "
            'deployment package must include them. To install them for the '
            f'{runtime_id} runtime, run: {command}'
        )
        return
    foreign = _foreign_wheels(installed, python_version(runtime_id))
    if not foreign:
        return
    command = install_command(source_dir, runtime_id)
    sample = ', '.join(
        f'{name} ({platform})' for name, platform in foreign[:5]
    )
    if len(foreign) > 5:
        sample += f', and {len(foreign) - 5} more'
    output.progress(
        f'Warning: {len(foreign)} installed package(s) were built for '
        f'another platform or Python version: {sample}. Web Functions run on '
        f'{constants.RUNTIME_ARCHITECTURE} Linux, so these imports will fail. '
        f'Reinstall them for the {runtime_id} runtime with: {command}'
    )


def _main_py():
    runtime_port = constants.RUNTIME_HTTP_PORT
    local_port_env_var = constants.LOCAL_PORT_ENV_VAR
    return f'''\
# Minimal AWS Lambda Web Function. Replace ``app`` with any WSGI or ASGI
# application object, such as a FastAPI, Flask, or Django application.
import json


def app(environ, start_response):
    start_response("200 OK", [("content-type", "application/json")])
    body = {{"message": "Hello from Lambda Web!", "path": environ["PATH_INFO"]}}
    return [json.dumps(body).encode()]


if __name__ == "__main__":
    # Lambda runs ``app`` behind a managed server; this block is for
    # local development only. {local_port_env_var} changes the local port.
    import os
    from wsgiref.simple_server import make_server

    port = int(os.environ.get("{local_port_env_var}", {runtime_port}))
    print(f"listening on port {{port}}")
    make_server("", port, app).serve_forever()
'''


def _install_commands_markdown():
    version = python_version(RUNTIMES[0])
    return f"""\
  ```bash
  uv pip install -r requirements.txt --target . \\
      --python-platform {UV_PLATFORM} --python-version {version}
  # or
  pip install -r requirements.txt --target . --only-binary=:all: \\
      {PIP_PLATFORM_FLAGS} \\
      --implementation cp --python-version {version}
  ```"""


_DOCS = ScaffoldDocs(
    language='Python',
    project_summary=(
        'a Python web application that AWS Lambda serves behind an HTTPS '
        'endpoint'
    ),
    why_bullet=(
        '- Deploy a standard Python application that exposes a WSGI or ASGI\n'
        '  application object. There is no server to configure and no\n'
        '  Lambda-specific handler or adapter.'
    ),
    entry_file=SCAFFOLD_ENTRY,
    start_command=f'python {SCAFFOLD_ENTRY}',
    deploy_alias=None,
    how_it_works=f"""\
`{SCAFFOLD_ENTRY}` exposes a WSGI application object named `app`. AWS Lambda \
imports
`{DEFAULT_ENTRY}` and serves it with a managed HTTP server, so there is
no server to run, port to bind, handler to export, or adapter to
install. FastAPI,
Starlette, Flask, and Django applications expose the same kind of object:
`app = FastAPI()`, `app = Flask(__name__)`, or Django's
`mysite.asgi:application`.""",
    runtime_contract=f"""\
- Expose a WSGI or ASGI application object. The runtime imports \
`{DEFAULT_ENTRY}`
  by default and serves it with a managed server; the application
  never binds a port. The runtime selects ASGI for a coroutine
  callable and WSGI otherwise.
- Do not start a server at import time. Keep `uvicorn.run(...)`,
  `app.run(...)`, and `serve_forever()` under `if __name__ == "__main__":`
  for local runs only. `{constants.LOCAL_PORT_ENV_VAR}` changes the local \
port only. Do not set
  it with `--env`.
- Responses stream as the application produces them. Return an iterable from
  a WSGI application, or send ASGI `http.response.body` messages with
  `more_body`.""",
    layout=f"""\
- `{SCAFFOLD_ENTRY}`: The entry module. It defines `app`, the object that
  `{DEFAULT_ENTRY}` names. If you rename the module or the object, deploy with
  `--entry-point module:object`.
- The runtime is `{RUNTIMES[0]}`. There is no build step. The runtime imports
  the module directly.""",
    dependencies=f"""\
- Web Functions use the `{constants.RUNTIME_ARCHITECTURE}` architecture. \
The architecture
  is not configurable. Compiled packages need `aarch64` manylinux wheels.
- Install dependencies into the project root so they deploy with the code,
  and target the runtime platform so wheels match it:
{_install_commands_markdown()}
- Keep `.venv` for local development only. `deploy` excludes it.
- Keep secrets out of the source tree. Pass nonsecret configuration with
  `--env`.""",
    packaging=f"""\
- `deploy` packages the `--code` directory. It does not run `pip` or `uv`, so
  install dependencies into the directory first. It warns when a manifest
  declares dependencies that are not installed, or when installed wheels
  target another platform or Python version.
{HIDDEN_FILES_BULLET}
- `deploy` excludes `__pycache__`, `*.pyc`, `venv`, `.venv`, and test caches.
- The runtime imports `{DEFAULT_ENTRY}` by default. For another module or \
object,
  pass `--entry-point module:object`, the same string you would pass to
  uvicorn or gunicorn. `deploy` sets `{ENTRYPOINT_ENV_VAR}` on the
  revision. To force an interface, set `--env
  {ENTRYPOINT_ENV_VAR}=asgi:module:object` or `wsgi:module:object`
  instead. Do not use that environment variable with `--entry-point`.""",
)


class PythonRuntime(Runtime):
    family = 'python'
    display_name = 'Python'
    aliases = ('python',)
    versions = RUNTIMES
    entry_env_var = ENTRYPOINT_ENV_VAR
    default_entry = DEFAULT_ENTRY
    entry_point_uses_env = True
    exclude_patterns = EXCLUDE_PATTERNS
    docs = _DOCS
    symlink_hint = (
        'If these are dependencies, the bundle may be missing modules; '
        'reinstall them into the --code directory with pip or uv, which '
        'write real files, before deploying.'
    )

    def detect(self, source_dir):
        return any(
            os.path.isfile(os.path.join(source_dir, name))
            for name in MARKER_FILES + ENTRY_CANDIDATES
        )

    def resolve_entry(self, source_dir, explicit=None):
        return select(source_dir, resolve_entry_point(source_dir, explicit))

    def customer_entry(self, value, source_dir):
        try:
            _, module, _ = parse_entry(value)
        except InvalidSourceError:
            raise InvalidSourceError(
                f"{ENTRYPOINT_ENV_VAR} is set to '{value}', which isn't a "
                'valid entry point. Use module:object, optionally prefixed '
                'with asgi: or wsgi:.'
            ) from None
        try:
            bundle_path = module_file(source_dir, module)
        except EntryPointNotFoundError:
            raise EntryPointNotFoundError(
                f"{ENTRYPOINT_ENV_VAR} names Python module '{module}', "
                f"which was not found under '{source_dir}'. Check the "
                'variable, or include the module in --code.'
            ) from None
        return EntrySelection(
            display=value,
            bundle_path=bundle_path,
            env={ENTRYPOINT_ENV_VAR: value},
        )

    def inspect_dependencies(self, source_dir, runtime_id):
        inspect_dependencies(source_dir, runtime_id)

    def scaffold_files(self, function_name):
        return {SCAFFOLD_ENTRY: _main_py()}

    def scaffold_entry(self):
        return DEFAULT_ENTRY


RUNTIME = PythonRuntime()
