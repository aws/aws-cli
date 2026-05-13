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
"""``aws update`` — update the AWS CLI to the latest release in place.

Reads install.json to recover the install/bin directories, then runs
install.sh against the same paths. install.sh handles the actual
download, verification, and install.

Currently the install.sh location is supplied via the dev-only
``--dev-install-script`` flag. Network download will be added back
once install.sh is hosted at a stable URL.

Source-based installs are intentionally unsupported.
"""

import json
import os
import subprocess
import sys

from awscli.customizations.commands import BasicCommand


_SUPPORTED_SOURCES = ('exe', 'script-exe', 'update-exe')
_SYSTEM_INSTALL_DIR = '/usr/local/aws-cli'


class UpdateCommand(BasicCommand):
    NAME = 'update'
    DESCRIPTION = (
        'Update the AWS CLI to the latest version, preserving the current '
        'installation directory. Only supported for installations created '
        'by the official installers or the curl|bash install script.'
    )
    SYNOPSIS = 'aws update'
    ARG_TABLE = [
        {
            # TEMPORARY: required while install.sh has no public URL. Once
            # install.sh is hosted, the command will fetch it automatically
            # and this flag will be removed.
            'name': 'dev-install-script',
            'help_text': (
                '(Development only) Path to a local install.sh to run. '
                'Required until network download is implemented.'
            ),
            'cli_type_name': 'string',
            'required': True,
        },
    ]

    def _run_main(self, parsed_args, parsed_globals):
        install = _read_install_json()
        metadata = _read_metadata()
        source = install.get(
            'distribution_source',
            metadata.get('distribution_source', 'other'),
        )
        if source not in _SUPPORTED_SOURCES:
            raise UpdateError(
                f"'aws update' does not support installations with "
                f"distribution_source={source!r}. Supported sources are: "
                f"{', '.join(_SUPPORTED_SOURCES)}."
            )

        install_dir, bin_dir = _resolve_install_paths(install)
        is_system = install_dir == _SYSTEM_INSTALL_DIR

        if is_system and os.geteuid() != 0:
            raise UpdateError(
                'Updating a system-wide AWS CLI install requires root. '
                'Re-run with sudo.'
            )

        local_script = parsed_args.dev_install_script
        if not os.path.isfile(local_script):
            raise UpdateError(
                f"--dev-install-script: file not found: {local_script}"
            )

        sys.stdout.write(
            f"Updating AWS CLI at {install_dir} (source: {source})\n"
        )
        _run_install_script(local_script, install_dir, bin_dir, is_system)
        return 0


def register_update_command(event_handlers):
    event_handlers.register(
        'building-command-table.main', UpdateCommand.add_command
    )


def _read_install_json():
    return _read_data_file('install.json')


def _read_metadata():
    return _read_data_file('metadata.json')


def _read_data_file(filename):
    import awscli  # local import to avoid a top-level cycle
    path = os.path.join(
        os.path.dirname(os.path.abspath(awscli.__file__)), 'data', filename,
    )
    if not os.path.isfile(path):
        return {}
    with open(path) as f:
        return json.load(f)


def _resolve_install_paths(install):
    """Return (install_dir, bin_dir) from install.json.

    install.json is written by every supported installer. A missing file
    or missing fields means the CLI is in an unsupported state — either
    not installed via an official installer, or its install directory
    has been tampered with. We refuse to update rather than guess.
    """
    install_dir = install.get('install_dir')
    bin_dir = install.get('bin_dir')
    if not install_dir or not bin_dir:
        raise UpdateError(
            'install.json is missing or incomplete. This CLI install was '
            'either not produced by a supported installer or its install '
            'directory has been modified. Reinstall via the official '
            'installer or install.sh and try again.'
        )
    return install_dir, bin_dir


def _run_install_script(script_path, install_dir, bin_dir, is_system):
    env = os.environ.copy()
    env['AWS_CLI_DISTRIBUTION_SOURCE_OVERRIDE'] = 'update-exe'

    cmd = ['bash', script_path]
    if is_system:
        cmd.append('--system')
    else:
        # install.sh appends "/aws-cli" to XDG_DATA_HOME, so we hand it the
        # parent of the resolved install_dir.
        env['XDG_DATA_HOME'] = os.path.dirname(install_dir)
        env['XDG_BIN_HOME'] = bin_dir

    sys.stdout.write('Running install.sh...\n')
    subprocess.run(cmd, env=env, check=True)


class UpdateError(Exception):
    """Raised when the update flow cannot proceed."""
