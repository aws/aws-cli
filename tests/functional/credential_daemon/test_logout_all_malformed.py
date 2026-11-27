# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""aws logout --all must remove the plaintext session files even when
the credential daemon's reply is malformed.

A credential/list reply of an unexpected shape must not raise KeyError,
TypeError or AttributeError past _logout_all and stop the file sweep.
"""

import json
import socket
from argparse import Namespace

import pytest

if not hasattr(socket, 'AF_UNIX'):
    pytest.skip(
        'The credential daemon uses Unix sockets', allow_module_level=True
    )

from botocore.credential_daemon import CredentialDaemonClient

from awscli.customizations.login.logout import LogoutCommand
from tests import mock
from tests.utils.credential_daemon import FakeCredentialDaemon

SESSION_FILE = {
    'accessToken': {
        'accessKeyId': 'AKIDEXAMPLE',
        'secretAccessKey': 'secret',
        'sessionToken': 'token',
    },
    'refreshToken': 'refresh',
    'dpopKey': 'key',
}


class MalformedListCredentialDaemon(FakeCredentialDaemon):
    """Answers credential/list with a reply the CLI doesn't expect."""

    def __init__(self, reply, **kwargs):
        super().__init__(**kwargs)
        self.reply = reply

    def _list(self, params):
        return self.reply


@pytest.mark.parametrize(
    'reply',
    [
        {},
        {
            'credentials': [
                {
                    'kind': 'session_credentials',
                    'status': 'active',
                }
            ]
        },
        {'credentials': ['dev']},
        {'credentials': None},
    ],
    ids=['no-credentials', 'row-without-name', 'row-not-a-dict', 'null'],
)
@pytest.mark.parametrize(
    'profiles',
    [{'dev': {'login_session': 'x'}}, {'dev': {'credential_daemon': 'dev'}}],
    ids=['files-profiles', 'daemon-profile'],
)
def test_plaintext_is_removed(tmp_path, reply, profiles, capsys):
    session_file = tmp_path / 'cache' / 'session.json'
    session_file.parent.mkdir()
    session_file.write_text(json.dumps(SESSION_FILE))
    session = mock.Mock()
    session.profile = 'dev'
    session.full_config = {'profiles': profiles}
    session.get_config_variable.return_value = '/nonexistent/aws-file'
    with MalformedListCredentialDaemon(reply) as fake:
        command = LogoutCommand(
            session,
            cache_dir=str(session_file.parent),
            credential_daemon_client=CredentialDaemonClient(
                socket_path=fake.socket_path, timeout=5
            ),
        )
        rc = command._run_main(Namespace(all=True), mock.Mock())
    assert not session_file.exists()
    err = capsys.readouterr().err
    if isinstance(reply.get('credentials'), list):
        # Rows it can't read are skipped; a reply without a list is an
        # error.
        assert rc == 0
        assert err == ''
    elif 'credential_daemon' in profiles['dev']:
        # A profile uses the credential daemon: its sessions weren't
        # cleared.
        assert rc == 1
        assert "Sessions in the credential daemon weren't cleared" in err
    else:
        # No profile uses it: a warning, and the files decide the exit.
        assert rc == 0
        assert err.startswith(
            "warning: sessions in the credential daemon weren't checked: "
        )
