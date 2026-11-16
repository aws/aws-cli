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
"""Runtime families supported by ``aws lambda-web deploy``.

Each module defines one :class:`~.base.Runtime` instance that owns the
behavior specific to its language: ``--runtime`` aliases, project detection,
entry-point resolution, packaging rules, and the starter application.
"""

from awscli.customizations.lambdaweb.exceptions import InvalidSourceError
from awscli.customizations.lambdaweb.runtimes import nodejs, python

ALL = (nodejs.RUNTIME, python.RUNTIME)
DEFAULT = nodejs.RUNTIME


def resolve_requested(value):
    """Return ``(runtime_id, runtime)`` for a ``--runtime`` value.

    Returns ``None`` when the option was omitted. An alias selects the newest
    version of its family; any other identifier is sent to the service as
    given, so a runtime newer than this CLI still deploys.
    """
    if not value:
        return None
    for runtime in ALL:
        if value in runtime.aliases:
            return runtime.latest, runtime
    return value, for_identifier(value)


def for_identifier(runtime_id):
    """Return the runtime family for a runtime identifier.

    Falls back to the default family so an unrecognized identifier keeps the
    packaging behavior the command had before runtime families existed. The
    service validates the identifier itself.
    """
    for runtime in ALL:
        if runtime.matches(runtime_id):
            return runtime
    return DEFAULT


def hello_world_values():
    """Return the ``--runtime`` values ``--hello-world`` accepts."""
    return [
        value
        for runtime in ALL
        for value in (runtime.latest,) + runtime.aliases
    ]


def entry_env_vars():
    return tuple(runtime.entry_env_var for runtime in ALL)


def detect(source_dir):
    """Return the runtimes whose project markers appear in ``source_dir``."""
    return tuple(runtime for runtime in ALL if runtime.detect(source_dir))


def detect_single(source_dir):
    """Return the one detected runtime, ``None``, or raise when ambiguous."""
    matches = detect(source_dir)
    if len(matches) <= 1:
        return matches[0] if matches else None
    names = ' and '.join(runtime.display_name for runtime in matches)
    options = ' or '.join(
        f'--runtime {runtime.aliases[0]}' for runtime in matches
    )
    raise InvalidSourceError(
        f"--code '{source_dir}' contains both {names} project files, so the "
        f'command cannot choose a runtime. Run it again with {options}.'
    )
