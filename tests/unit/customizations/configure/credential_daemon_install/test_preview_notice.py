# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""install says that credential daemon support is a developer preview once
the install starts, and not for a refusal or for uninstall."""

import shutil

import pytest

from awscli.customizations.credential_daemon.messages import PREVIEW_NOTICE
from awscli.customizations.exceptions import ConfigurationError
from tests.markers import skip_if_windows
from tests.unit.customizations.configure.credential_daemon_install.helpers import (
    RELEASE_URL,
    Runner,
    UninstallRunner,
    install,
    linux_http,
    macos_http,
    uninstall,
)

pytestmark = skip_if_windows

# The developer preview notice, as printed on its own line.
PREVIEW_LINE = f'{PREVIEW_NOTICE}\n'


def record_before_downloads(http, capsys, seen):
    """Record stderr when the first release file is downloaded."""
    for url, response in http.responses.items():
        if url == RELEASE_URL:
            continue

        def recorded(response=response):
            if not seen:
                seen.append(capsys.readouterr().err)
            return response

        http.responses[url] = recorded
    return http


class TestInstall:
    def test_linux_says_it_once_before_the_download(self, pinned_key, capsys):
        seen = []
        http = record_before_downloads(linux_http(), capsys, seen)
        assert install(http=http, runner=Runner()) == 0
        assert seen == [PREVIEW_LINE]
        captured = capsys.readouterr()
        assert PREVIEW_NOTICE not in captured.err
        assert PREVIEW_NOTICE not in captured.out

    def test_macos_says_it_once_before_the_download(self, capsys):
        seen = []
        http = record_before_downloads(macos_http(), capsys, seen)
        rc = install(
            system='darwin', is_root=False, http=http, runner=Runner()
        )
        assert rc == 0
        assert seen == [PREVIEW_LINE]
        captured = capsys.readouterr()
        assert PREVIEW_NOTICE not in captured.err
        assert PREVIEW_NOTICE not in captured.out

    @pytest.mark.parametrize(
        'options',
        [
            # Not a platform the credential daemon runs on.
            {'system': 'win32', 'is_root': False},
            # sudo on macOS.
            {'system': 'darwin', 'is_root': True},
            # Linux without root.
            {'system': 'linux', 'is_root': False},
            # No macOS release for Intel Macs.
            {'system': 'darwin', 'is_root': False, 'machine': 'x86_64'},
        ],
    )
    def test_a_refusal_says_nothing(self, options, capsys):
        with pytest.raises(ConfigurationError):
            install(http=macos_http(), runner=Runner(), **options)
        assert PREVIEW_NOTICE not in capsys.readouterr().err

    def test_no_gpg_on_linux_says_nothing(self, pinned_key, capsys):
        # Refused before the download, as the other missing prerequisites.
        shutil.which.return_value = None
        http = linux_http()
        with pytest.raises(ConfigurationError) as e:
            install(http=http, runner=Runner())
        assert 'Install gnupg' in str(e.value)
        assert http.urls == []
        assert PREVIEW_NOTICE not in capsys.readouterr().err

    def test_a_release_below_the_minimum_says_nothing(
        self, pinned_key, capsys
    ):
        runner = Runner(version='credsd 0.1.0\nstorage backends: tpm\n')
        with pytest.raises(ConfigurationError):
            install(http=linux_http(tag='v0.1.0'), runner=runner)
        assert PREVIEW_NOTICE not in capsys.readouterr().err


class TestUninstall:
    def test_says_nothing(self, tmp_path, linux_install, capsys):
        runner = UninstallRunner(
            removes=[linux_install.credential_daemon, *linux_install.units]
        )
        rc, _ = uninstall(tmp_path, runner=runner, is_tty=True)
        assert rc == 0
        assert PREVIEW_NOTICE not in capsys.readouterr().err
