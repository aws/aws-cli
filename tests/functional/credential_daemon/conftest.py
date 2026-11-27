# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Fixtures shared by the credential daemon functional tests."""

import pytest

from awscli.compat import is_windows
from tests import mock
from tests.functional.credential_daemon.login_helpers import HANDLER
from tests.utils.credential_daemon import FakeCredentialDaemon

# What a developer's own shell or ~/.aws could otherwise feed into a test.
CLEARED_ENV_VARS = (
    'AWS_PROFILE',
    'AWS_DEFAULT_PROFILE',
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY',
    'AWS_SESSION_TOKEN',
    'AWS_CREDENTIAL_STORAGE',
    'AWS_CREDENTIAL_DAEMON_SOCKET',
    'AWS_ROLE_ARN',
    'AWS_WEB_IDENTITY_TOKEN_FILE',
    'AWS_CONTAINER_CREDENTIALS_RELATIVE_URI',
    'AWS_CONTAINER_CREDENTIALS_FULL_URI',
    'AWS_REGION',
    'AWS_DEFAULT_REGION',
    'AWS_CONFIG_FILE',
    'AWS_SHARED_CREDENTIALS_FILE',
    'AWS_LOGIN_CACHE_DIRECTORY',
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path_factory):
    """No developer environment, and no real ~/.aws, in any test."""
    for name in CLEARED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('HOME', str(tmp_path_factory.mktemp('home')))


@pytest.fixture
def fake(request):
    """A fake credential daemon. Parametrize it indirectly to pass
    FakeCredentialDaemon's options, or override it as ``fake(fake)`` to seed
    it.

    Windows has no Unix sockets, so every test that uses the fake skips
    there; the tests that don't need it still run.
    """
    if is_windows:
        pytest.skip('The fake credential daemon needs Unix sockets')
    with FakeCredentialDaemon(**getattr(request, 'param', {})) as fake:
        yield fake


@pytest.fixture
def aws_dir(tmp_path, monkeypatch):
    # No real ~/.aws. HOME is a folder of its own, so the paths the
    # messages show are the full ones.
    (tmp_path / 'home').mkdir()
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    monkeypatch.setenv('AWS_CONFIG_FILE', str(tmp_path / 'config'))
    monkeypatch.setenv(
        'AWS_SHARED_CREDENTIALS_FILE', str(tmp_path / 'credentials')
    )
    monkeypatch.setenv('AWS_LOGIN_CACHE_DIRECTORY', str(tmp_path / 'cache'))
    (tmp_path / 'config').write_text('')
    return tmp_path


@pytest.fixture
def home_aws_dir(tmp_path, monkeypatch):
    """~/.aws, with the files named the way a customer writes them, so the
    messages show them with ~."""
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('AWS_CONFIG_FILE', '~/.aws/config')
    monkeypatch.setenv('AWS_SHARED_CREDENTIALS_FILE', '~/.aws/credentials')
    home_aws_dir = tmp_path / '.aws'
    home_aws_dir.mkdir()
    (home_aws_dir / 'config').write_text('')
    (home_aws_dir / 'credentials').write_text('')
    return home_aws_dir


@pytest.fixture
def daemon_env(fake, monkeypatch):
    """Point AWS_CREDENTIAL_DAEMON_SOCKET at the fake."""
    monkeypatch.setenv('AWS_CREDENTIAL_DAEMON_SOCKET', fake.socket_path)


@pytest.fixture
def browser():
    with mock.patch(f'{HANDLER}.open_browser_with_original_ld_path') as open_:
        yield open_
