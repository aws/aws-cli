# ruff: noqa: F811 (pytest fixtures imported from test_identity_change_on_move)
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Every combination of the identity check when aws login signs a
profile in as someone else.

prod starts on files as Admin (``login_session = PROD_ADMIN``), or in the
credential daemon on Admin's credential, whose row may not say who it holds.
The credential daemon names aws login credentials after who signs in, so the
sign-in lands on the credential named for the new identity. The matrix varies
that credential's row before the sign-in, whether alias names it, who signs
in, the customer's answer, and whether the clear after a "no" works. Each
case checks that a no or a failure changes nothing, that anything left behind
is reported, at most one question (the one asked for session files), that the
"Kept" line names prod's identity (with no terminal, that aws login fails
instead, as it does for session files), that alias never changes, and that Admin's
credential is never touched by a sign-in as someone else. Only a credential
signed in as the new identity before is in use, so a no never signs a
signed-out one back in for alias. Admin signing in again to an Admin
credential with no record of who signed in needs the credential daemon's
approval, so it fails and nothing changes.
"""

import contextlib
import itertools

import pytest
from botocore.credential_daemon import CredentialDaemonClient
from botocore.exceptions import CredentialDaemonNotRunningError

from awscli.customizations.exceptions import ConfigurationError
from tests import mock
from tests.functional.credential_daemon.test_identity_change_on_move import (  # noqa: F401
    OTHER_DEV,
    OTHER_NAME,
    PROD_ADMIN,
    PROD_NAME,
    browser,
    login,
    read_config,
    write_config,
    write_session_file,
)

NAMES = {PROD_ADMIN: PROD_NAME, OTHER_DEV: OTHER_NAME}
ROWS = [None, 'active', 'no_session', 'expired']  # the new identity's
ALIAS = [False, True]  # alias names the new identity's credential
ANSWERS = [True, False, 'notty']
CLEAR_FAILS = [False, True]  # credential/logout fails
# prod on files, or in the credential daemon on Admin's credential (with or
# without an identity the credential daemon recorded for it).
STARTS = ['files', 'daemon', 'daemon-no-principal']
CASES = [
    case
    for case in itertools.product(
        STARTS,
        ROWS,
        ALIAS,
        [OTHER_DEV, PROD_ADMIN],  # who signs in
        ANSWERS,
        CLEAR_FAILS,
    )
    # In the credential daemon, Admin's row is prod's own; the same identity
    # refreshes it.
    if case[0] == 'files'
    or case[3] != PROD_ADMIN
    or case[1:3] == (None, False)
]


def _question(own):
    return (
        f'\nProfile prod is already configured to use session {own}. '
        f'Do you want to overwrite it to use {OTHER_DEV} instead? (y/n): '
    )


def _role(principal):
    return principal.split('/')[1]


def _id(case):
    start, row, alias, new, answer, clear_fails = case
    return (
        f'{start}-{row or "missing"}-alias{int(alias)}-new:{_role(new)}-'
        f'ans:{answer}-clearfail{int(clear_fails)}'
    )


def _state(fake, name):
    cred = fake.credential(name)
    return None if cred is None else (cred.status, cred.principal)


def _setup(fake, aws_dir, start, row, alias, new):
    name = NAMES[new]
    if start == 'files':
        prod = f'login_session = {PROD_ADMIN}'
    else:
        prod = f'credential_storage = daemon\n        credential_daemon = {PROD_NAME}'
    config = f'''
        [profile prod]
        {prod}
        region = us-west-2
        '''
    if alias:
        config += f'''
        [profile alias]
        credential_storage = daemon
        credential_daemon = {name}
        '''
    write_config(aws_dir, config)
    session_file = None
    if start == 'files':
        session_file = write_session_file(aws_dir, PROD_ADMIN)
    else:
        fake.seed(PROD_NAME, principal=PROD_ADMIN)
        if start == 'daemon-no-principal':
            fake.credential(PROD_NAME).principal = None
    if row == 'expired':
        fake.seed(name, principal=new)
        fake.expire(name)
    elif row is not None:
        fake.seed(name, principal=new, status=row)
    return session_file


def _clear_fails(fails):
    if not fails:
        return contextlib.nullcontext()
    return mock.patch.object(
        CredentialDaemonClient,
        'logout',
        side_effect=CredentialDaemonNotRunningError(
            error_msg='The credential daemon stopped.'
        ),
    )


@pytest.mark.parametrize('case', CASES, ids=[_id(c) for c in CASES])
def test_sign_in(fake, aws_dir, browser, capsys, case):
    start, row, alias, new, answer, clear_fails = case
    name = NAMES[new]
    session_file = _setup(fake, aws_dir, start, row, alias, new)
    admin_before = _state(fake, PROD_NAME)
    config_before = read_config(aws_dir)
    alias_config = config_before.partition('[profile alias]')[2]
    fake.next_principal = new
    if answer == 'notty':
        kwargs = {'tty': False}
        if start == 'files':
            kwargs['environ'] = {'AWS_CREDENTIAL_STORAGE': 'daemon'}
    else:
        kwargs = {'replace': answer}
        if start == 'files':
            kwargs['storage_answer'] = True
    # With no terminal a different identity is an error, as for session
    # files.
    refused = answer == 'notty' and new != PROD_ADMIN
    # The credential daemon can't tell it's the same person.
    needs_approval = start == 'daemon-no-principal' and new == PROD_ADMIN
    with _clear_fails(clear_fails):
        if needs_approval:
            with pytest.raises(ConfigurationError) as error:
                login(fake, **kwargs)
            [request_id] = fake.approval_requests()
            assert str(error.value).startswith(
                f'Replacing {PROD_NAME} needs approval.\n  '
            )
            assert f'sudo creds request approve {request_id}' in str(
                error.value
            )
            assert read_config(aws_dir) == config_before
            assert _state(fake, PROD_NAME) == admin_before
            return
        if refused:
            with pytest.raises(ConfigurationError) as error:
                login(fake, **kwargs)
            ask = None
        else:
            ask = login(fake, **kwargs)
    out = capsys.readouterr()
    config = read_config(aws_dir)
    prod_config = config.split('[profile alias]')[0]
    after = _state(fake, name)
    # Who prod was: its session or, since the credential daemon's rows
    # don't say who, its credential's name.
    own = PROD_ADMIN if start == 'files' else PROD_NAME

    # Only a different identity is asked about, with the question asked for
    # session files.
    asks = new != PROD_ADMIN and answer != 'notty'
    if not refused:
        assert ask.call_args_list == (
            [mock.call(_question(own))] if asks else []
        )
    # alias never changes, and Admin's credential isn't touched.
    assert config.partition('[profile alias]')[2] == alias_config
    if new != PROD_ADMIN:
        assert _state(fake, PROD_NAME) == admin_before
    if new == PROD_ADMIN or answer is True:
        # Signed in as the new identity.
        assert f'credential_daemon = {name}' in prod_config
        assert 'login_session' not in prod_config
        if session_file is not None:
            assert not session_file.exists()
        assert after == ('active', new)
        assert ask.exit_code in (0, None)
        return
    # Not changed: the profile and its file are as they were.
    if start == 'files':
        assert f'login_session = {PROD_ADMIN}' in prod_config
        assert 'credential_daemon' not in prod_config
        assert session_file.exists()
    else:
        assert f'credential_daemon = {PROD_NAME}' in prod_config
        assert 'login_session' not in prod_config
    kept = [
        line
        for line in out.out.splitlines()
        if line.startswith('Kept \'prod\' signed in as')
    ]
    if refused:
        assert kept == []
        assert str(error.value) == (
            f'Profile prod is already configured to use session {own}. '
            f'Run \'aws login\' in a terminal to overwrite it to use '
            f'{OTHER_DEV}. Profile \'prod\' wasn\'t changed.'
        )
    else:
        assert kept == [f'Kept \'prod\' signed in as {own}.']
    if row == 'active':
        # In use: never signed out.
        assert after == ('active', new)
        assert refused or ask.exit_code in (0, None)
    elif clear_fails:
        # What was left behind, who uses it, and how to sign it out.
        assert after == ('active', new)
        assert refused or ask.exit_code == 1
        assert 'logout --all' in out.err
        assert (', and \'alias\' uses it' in out.err) == alias
    else:
        # A signed-out, expired or new credential is signed out again,
        # even when alias names it.
        assert after == ('no_session', new)
        assert refused or ask.exit_code in (0, None)
