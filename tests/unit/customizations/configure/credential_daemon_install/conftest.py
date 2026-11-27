# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import shutil
from argparse import Namespace

import pytest

from awscli.customizations.configure.credential_daemon_install import (
    release as install_release,
)
from tests import mock
from tests.unit.customizations.configure.credential_daemon_install.helpers import (
    FINGERPRINT,
    write,
)


@pytest.fixture
def pinned_key():
    with (
        mock.patch.object(install_release, 'CREDENTIAL_DAEMON_PGP_KEY', 'KEY'),
        mock.patch.object(
            install_release, 'CREDENTIAL_DAEMON_PGP_FINGERPRINT', FINGERPRINT
        ),
        mock.patch.object(shutil, 'which', return_value='/usr/bin/gpg'),
    ):
        yield


@pytest.fixture
def linux_install(tmp_path):
    root = tmp_path / 'root'
    credential_daemon = write(root / 'usr/local/libexec/credsd/credsd')
    units = [
        write(root / 'etc/systemd/system/credsd.service'),
        write(root / 'etc/systemd/system/credsd.socket'),
    ]
    # Not the install's: these must be left alone.
    data = write(root / 'var/lib/credsd/credentials')
    other = write(root / 'usr/local/libexec/other/tool')
    return Namespace(
        credential_daemon=credential_daemon,
        units=units,
        data=data,
        other=other,
    )
