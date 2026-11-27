# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Helpers for running aws login against the fake credential daemon."""

import os
import socket
import textwrap
from argparse import Namespace

from botocore.credential_daemon import CredentialDaemonClient
from botocore.exceptions import CredentialDaemonTimeoutError
from botocore.session import Session

from awscli.customizations.credential_daemon.storage.chooser import (
    CredentialStorageChooser,
)
from awscli.customizations.login.login import LoginCommand
from awscli.testutils import CapturedRenderer, create_clidriver
from tests import mock
from tests.utils.credential_daemon import DEFAULT_PRINCIPAL

GLOBALS = Namespace(region='us-west-2', endpoint_url=None, verify_ssl=None)
HANDLER = 'awscli.customizations.login.credential_daemon'
MESSAGES = 'awscli.customizations.credential_daemon.messages'
# The sign-in reads the home region from the ID token.
SAMPLE_ID_TOKEN = (
    'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzM4NCJ9.eyJpc3MiOiJodHRwczovL3NpZ25pbi5hd'
    '3MuYW1hem9uLmNvbS9zaWduaW4iLCJpYXQiOjE3NjAxMTU3NjQsImV4cCI6MTc2MDExNjk'
    '2NSwiYXVkIjoiYXJuOmF3czpzaWduaW46OjpjbGkvc2FtZS1kZXZpY2UiLCJzdWIiOiJhc'
    'm46YXdzOmlhbTo6MDEyMzQ1Njc4OTAxMjp1c2VyL0FkbWluIiwic2Vzc2lvbl9hcm4iOiJ'
    'hcm46YXdzOmlhbTo6MDEyMzQ1Njc4OTAxMjp1c2VyL0FkbWluIn0.HcleGdakodn9ZbCsR'
    'nsF_F2n5TmQD-OW9zc9oMU7DtNrXQwxzg4jO40N2BMgiTyW'
)
FETCH_TOKEN = (
    'awscli.customizations.login.utils.SameDeviceLoginTokenFetcher.fetch_token'
)


def socket_checks_pass(path):
    """Let the socket checks pass for ``path`` in a test that mocks the
    socket itself, so there's no socket file or peer to check."""
    return mock.patch.multiple(
        'botocore.credential_daemon.transport',
        check_socket=mock.Mock(return_value=(path, os.geteuid())),
        check_peer=mock.Mock(),
        check_code_signature=mock.Mock(),
    )


def daemon_timeout(which, path):
    """The client's own timeout error for a credential daemon at ``path``.

    ``which`` is ``'connect'`` (connecting took too long) or ``'call'``
    (the credential daemon took the request but never answered). The
    client's default timeouts apply, as a command's do.
    """
    if which == 'connect':
        patches = {'connect': mock.Mock(side_effect=socket.timeout)}
    else:
        patches = {
            'connect': mock.Mock(),
            'sendall': mock.Mock(),
            'recv': mock.Mock(side_effect=socket.timeout),
        }
    with (
        mock.patch.multiple(socket.socket, **patches),
        socket_checks_pass(path),
    ):
        try:
            CredentialDaemonClient(socket_path=path).list_credentials()
        except CredentialDaemonTimeoutError as e:
            return e
    raise AssertionError(f'no {which} timeout')


def timeout_message(which, path):
    """What the client says when the ``which`` timeout fires on ``path``."""
    if which == 'connect':
        return (
            'The credential daemon didn\'t accept the connection on '
            f'{path} within the 1-second connect timeout.'
        )
    return (
        f'The credential daemon on {path} didn\'t respond within the '
        '5-second call timeout.'
    )


def rendered_help(*command):
    """The help text for ``aws <command> help``, with whitespace runs
    joined, so phrases can be found across line breaks."""
    renderer = CapturedRenderer()
    with mock.patch('awscli.help.get_renderer', return_value=renderer):
        create_clidriver().main([*command, 'help'])
    return ' '.join(renderer.rendered_contents.split())


def write_config(aws_dir, config):
    (aws_dir / 'config').write_text(textwrap.dedent(config))


def read_config(aws_dir):
    return (aws_dir / 'config').read_text()


def files_sign_in(session_id=DEFAULT_PRINCIPAL):
    """Patches for a sign-in with files that skips the browser."""
    return (
        mock.patch(
            FETCH_TOKEN,
            return_value=(
                {'accessToken': 'x', 'idToken': SAMPLE_ID_TOKEN},
                session_id,
            ),
        ),
        mock.patch('awscli.customizations.login.utils.get_base_sign_in_uri'),
        mock.patch('awscli.customizations.login.login.AuthCodeFetcher'),
    )


def login(
    fake,
    profile='dev',
    args=(),
    tty=True,
    storage_answer=None,
    replace=None,
    codes=(),
    read_input=None,
    environ=None,
    return_rc=False,
    command_class=LoginCommand,
    parsed_globals=GLOBALS,
    discover=False,
):
    """Run aws login against the fake, answering prompts as given.

    With return_rc, the command's return code is returned too. A
    read_input mock replaces codes, so a test can check the prompt.
    ``command_class`` runs another command the same way, such as
    ``SignupCommand``. With ``discover``, no client is given, so the socket
    is looked up as for a customer.
    """
    session = Session(profile=profile)
    client = None
    if not discover:
        client = CredentialDaemonClient(
            socket_path=fake.socket_path, timeout=5
        )
    ask_storage = mock.Mock(return_value=storage_answer)
    chooser = CredentialStorageChooser(
        session,
        credential_daemon_client=client,
        environ=environ if environ is not None else {},
        is_tty=lambda: tty,
        ask=ask_storage,
    )
    command = command_class(
        session, chooser=chooser, credential_daemon_client=client
    )
    ask_replace = mock.Mock(return_value=replace)
    with (
        mock.patch(f'{HANDLER}.is_stdin_a_tty', return_value=tty),
        mock.patch(f'{HANDLER}.yes_no_choice', ask_replace),
        mock.patch(f'{MESSAGES}.is_stdin_a_tty', return_value=tty),
        mock.patch(f'{MESSAGES}.yes_no_choice', ask_replace),
        mock.patch(
            f'{HANDLER}.compat_input',
            read_input or mock.Mock(side_effect=list(codes)),
        ),
    ):
        rc = command(list(args), parsed_globals)
    if return_rc:
        return ask_storage, ask_replace, rc
    return ask_storage, ask_replace
