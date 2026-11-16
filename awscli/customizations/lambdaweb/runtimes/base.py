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
import dataclasses
import os

from awscli.customizations.lambdaweb.exceptions import InvalidSourceError


@dataclasses.dataclass(frozen=True)
class EntrySelection:
    """How the runtime locates the application in the deployment package.

    ``bundle_path`` names a file that must be present in the package, or is
    ``None`` when the entry cannot be mapped to one file. ``wrapper`` is an
    ``(arcname, content)`` file to add to the package. ``env`` holds
    environment variables to set on the revision.
    """

    display: str
    bundle_path: str = None
    wrapper: tuple = None
    env: dict = None


@dataclasses.dataclass(frozen=True)
class ScaffoldDocs:
    """Runtime-specific fragments for the starter README and AGENTS.md."""

    language: str
    project_summary: str
    why_bullet: str
    entry_file: str
    start_command: str
    deploy_alias: str
    how_it_works: str
    runtime_contract: str
    layout: str
    dependencies: str
    packaging: str


# Shared by every runtime's packaging section.
HIDDEN_FILES_BULLET = """\
- Hidden files and directories are excluded by default, except for known
  framework build paths. Use `--include-hidden-files` when the application
  needs another hidden path. Exact excluded files, such as `.env` or `*.pem`,
  require `--force-include`. Excluded directories, such as `.ssh`, remain
  excluded."""


class Runtime:
    """Behavior that differs between Web Function runtime families.

    One instance exists per family. ``versions`` lists runtime identifiers
    newest first, and ``aliases`` are the short names ``--runtime`` accepts
    for the newest one.
    """

    family = ''
    display_name = ''
    aliases = ()
    versions = ()
    entry_env_var = ''
    default_entry = ''
    # True when ``--entry-point`` is applied through ``entry_env_var``, so an
    # explicit ``--entry-point`` replaces an inherited value instead of
    # conflicting with it.
    entry_point_uses_env = False
    exclude_patterns = ()
    docs = None

    @property
    def latest(self):
        return self.versions[0]

    def matches(self, runtime_id):
        return runtime_id.startswith(self.family)

    def accepts_hello_world(self, runtime_id):
        return runtime_id == self.latest

    def detect(self, source_dir):
        """Return True when ``source_dir`` looks like this runtime's app."""
        raise NotImplementedError

    def resolve_entry(self, source_dir, explicit=None):
        """Return the :class:`EntrySelection` for the source tree."""
        raise NotImplementedError

    def customer_entry(self, value, source_dir):
        """Return the selection for a customer-set ``entry_env_var`` value."""
        raise NotImplementedError

    def inspect_dependencies(self, source_dir, runtime_id):
        """Warn about dependency problems the service would not report."""

    def scaffold_files(self, function_name):
        """Return ``{relative_path: content}`` for the starter application."""
        raise NotImplementedError

    def scaffold_entry(self):
        """Return the display form of the starter's entry point."""
        raise NotImplementedError


def validate_relative_entry(source_dir, explicit):
    """Reject an explicit entry path that is absolute or escapes the tree."""
    if os.path.isabs(explicit):
        raise InvalidSourceError(
            f"entry point '{explicit}' must be relative to source dir"
        )
    normalized = os.path.normpath(explicit)
    if '..' in normalized.split(os.sep):
        raise InvalidSourceError(
            f"entry point '{explicit}' escapes source dir"
        )
    return normalized
