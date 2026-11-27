# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for aws configure storing a new profile's access keys in the
credential daemon, run against the fake credential daemon."""

import socket
import textwrap
from argparse import Namespace

import pytest

if not hasattr(socket, 'AF_UNIX'):
    pytest.skip(
        'The credential daemon uses Unix sockets', allow_module_level=True
    )

from botocore.credential_daemon import CLI_TAGS, CredentialDaemonClient
from botocore.exceptions import (
    CredentialDaemonNotRunningError,
    CredentialDaemonTimeoutError,
)
from botocore.session import Session

from awscli.customizations.configure.configure import ConfigureCommand
from awscli.customizations.configure.credential_daemon_keys import (
    NewProfileKeys,
)
from awscli.customizations.configure.writer import ConfigFileWriter
from awscli.customizations.credential_daemon.messages import PREVIEW_NOTICE
from awscli.customizations.credential_daemon.storage.chooser import (
    CredentialStorageChooser,
)
from awscli.customizations.exceptions import ConfigurationError
from tests import mock
from tests.utils.credential_daemon import KIND_IAM_USER, KIND_LOGIN

ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE'
SECRET_KEY = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
GLOBALS = Namespace(region=None, endpoint_url=None, verify_ssl=None)
# The developer preview notice, as printed on its own line.
PREVIEW_LINE = f'{PREVIEW_NOTICE}\n'
NOT_STORED = (
    "The keys for profile 'ci' may not have been stored in the credential "
    'daemon, and nothing was saved to ~/.aws.'
)


@pytest.fixture
def home(home_aws_dir):
    # Not readable by others, so there's no permissions warning.
    (home_aws_dir / 'credentials').chmod(0o600)
    return home_aws_dir


def write(home, name, text):
    (home / name).write_text(textwrap.dedent(text))


def read(home, name):
    return (home / name).read_text()


class Prompter:
    def __init__(self, **values):
        self._values = values

    def get_value(self, current_value, config_name, prompt_text=''):
        return self._values.get(config_name)


def new_keys(**extra):
    return dict(
        aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, **extra
    )


def configure(
    fake, profile='ci', tty=True, answer=None, environ=None, **values
):
    """Run aws configure against the fake. Returns the storage question's
    mock."""
    session = Session(profile=profile)
    client = CredentialDaemonClient(socket_path=fake.socket_path, timeout=5)
    if isinstance(answer, BaseException):
        ask = mock.Mock(side_effect=answer)
    else:
        ask = mock.Mock(return_value=answer)
    chooser = CredentialStorageChooser(
        session,
        credential_daemon_client=client,
        environ=environ if environ is not None else {},
        is_tty=lambda: tty,
        ask=ask,
    )
    command = ConfigureCommand(
        session,
        prompter=Prompter(**values),
        keys=NewProfileKeys(session, chooser=chooser, client=client),
    )
    with mock.patch(
        'awscli.customizations.configure.configure.maybe_prompt_agent_toolkit'
    ):
        assert command([], GLOBALS) == 0
    return ask


def bootstraps(fake):
    return [p for m, p in fake.calls if m == 'credential/bootstrap']


def fail_config_write(error):
    """An update_config that fails the ~/.aws/config write with
    ``error``."""
    update_config = ConfigFileWriter.update_config

    def update(writer, new_values, config_filename, **kwargs):
        if config_filename.endswith('config'):
            raise error
        return update_config(writer, new_values, config_filename, **kwargs)

    return mock.patch.object(ConfigFileWriter, 'update_config', update)


def assert_nothing_written(home, config=''):
    assert read(home, 'config') == textwrap.dedent(config)
    assert read(home, 'credentials') == ''


class TestNewProfile:
    def test_yes_stores_the_keys_in_one_config_write(self, fake, home, capsys):
        ask = configure(fake, answer=True, **new_keys(region='us-west-2'))
        assert ask.call_args[0][0] == (
            'Store these keys in the credential daemon instead of '
            '~/.aws/credentials?\n'
            'Programs will get temporary credentials, so some things stop '
            'working (IAM calls without MFA, long presigned URLs).\n'
            'Older AWS SDKs can\'t use this profile (see docs for a '
            'workaround). [Y/n] '
        )
        credential = fake.credential('keys.ci')
        assert credential.kind == KIND_IAM_USER
        assert credential.secrets['secret_access_key'] == SECRET_KEY
        assert credential.tags == CLI_TAGS
        assert read(home, 'config') == (
            '[profile ci]\n'
            'region = us-west-2\n'
            'credential_storage = daemon\n'
            'credential_daemon = keys.ci\n'
        )
        assert read(home, 'credentials') == ''
        out = capsys.readouterr()
        assert out.out.endswith('Stored in the credential daemon.\n')
        assert out.err == PREVIEW_LINE

    def test_store_sends_the_keys_region_and_creator(self, fake, home):
        configure(fake, answer=True, **new_keys(region='eu-west-1'))
        (params,) = bootstraps(fake)
        assert params['credential'] == 'keys.ci'
        assert params['creator'] == 'aws-cli'
        assert params['provider']['type'] == 'aws_iam_user'
        assert fake.credential('keys.ci').secrets['access_key_id'] == (
            ACCESS_KEY
        )
        assert params['provider']['region'] == 'eu-west-1'

    def test_no_region_stores_with_us_east_1(self, fake, home):
        configure(fake, answer=True, **new_keys())
        (params,) = bootstraps(fake)
        assert params['provider']['region'] == 'us-east-1'
        assert read(home, 'config') == (
            '[profile ci]\n'
            'credential_storage = daemon\n'
            'credential_daemon = keys.ci\n'
        )

    def test_the_default_profile_is_named_keys_default(self, fake, home):
        configure(fake, profile=None, answer=True, **new_keys())
        assert fake.credential('keys.default').kind == KIND_IAM_USER
        assert read(home, 'config') == (
            '[default]\n'
            'credential_storage = daemon\n'
            'credential_daemon = keys.default\n'
        )

    def test_profile_name_is_cleaned_in_the_credential_name(self, fake, home):
        configure(fake, profile='me@corp', answer=True, **new_keys())
        (params,) = bootstraps(fake)
        assert params['credential'].startswith('keys.me-corp-')
        assert f"credential_daemon = {params['credential']}" in read(
            home, 'config'
        )

    def test_the_profile_then_gets_its_credentials_from_the_daemon(
        self, fake, home, daemon_env
    ):
        configure(fake, answer=True, **new_keys(region='us-west-2'))
        credentials = Session(profile='ci').get_credentials()
        assert credentials.method == 'credential-daemon'
        assert credentials.access_key != ACCESS_KEY

    def test_no_writes_the_files_and_saves_the_answer(
        self, fake, home, capsys
    ):
        configure(fake, answer=False, **new_keys(region='us-west-2'))
        assert read(home, 'credentials') == (
            '[ci]\n'
            f'aws_access_key_id = {ACCESS_KEY}\n'
            f'aws_secret_access_key = {SECRET_KEY}\n'
        )
        assert read(home, 'config') == (
            '[profile ci]\nregion = us-west-2\ncredential_storage = file\n'
        )
        assert bootstraps(fake) == []
        assert capsys.readouterr().out.endswith(
            "Saved credential_storage = file for 'ci'. The keys stay in "
            '~/.aws/credentials.\n'
        )

    def test_no_terminal_writes_the_files_without_asking(
        self, fake, home, capsys
    ):
        ask = configure(fake, tty=False, **new_keys())
        ask.assert_not_called()
        assert SECRET_KEY in read(home, 'credentials')
        assert 'credential_storage' not in read(home, 'config')
        assert fake.calls == []
        assert capsys.readouterr().err == ''

    def test_no_daemon_writes_the_files_without_asking(
        self, fake, home, capsys
    ):
        fake.stop()
        ask = configure(fake, **new_keys())
        ask.assert_not_called()
        assert SECRET_KEY in read(home, 'credentials')
        assert 'credential_storage' not in read(home, 'config')

    def test_ctrl_d_at_the_question_writes_nothing(self, fake, home):
        with pytest.raises(KeyboardInterrupt):
            configure(fake, answer=EOFError(), **new_keys())
        assert bootstraps(fake) == []
        assert_nothing_written(home)

    @pytest.mark.parametrize(
        'values',
        [
            # Temporary keys.
            dict(
                aws_access_key_id='ASIAIOSFODNN7EXAMPLE',
                aws_secret_access_key=SECRET_KEY,
                aws_session_token='token',
            ),
            # A lone key ID or secret.
            dict(aws_access_key_id=ACCESS_KEY),
            dict(aws_secret_access_key=SECRET_KEY),
            # No keys.
            dict(region='us-west-2'),
        ],
    )
    def test_anything_but_a_long_term_pair_is_as_before(
        self, fake, home, values
    ):
        ask = configure(fake, **values)
        ask.assert_not_called()
        assert fake.calls == []
        assert 'credential_' not in read(home, 'config')

    def test_storage_from_the_environment_stores_without_a_terminal(
        self, fake, home
    ):
        ask = configure(
            fake,
            tty=False,
            environ={'AWS_CREDENTIAL_STORAGE': 'daemon'},
            **new_keys(),
        )
        ask.assert_not_called()
        assert fake.credential('keys.ci').kind == KIND_IAM_USER
        # The variable decides, so no answer is saved.
        assert read(home, 'config') == (
            '[profile ci]\ncredential_daemon = keys.ci\n'
        )
        assert read(home, 'credentials') == ''


class TestStoreFails:
    def test_a_refused_store_saves_nothing(self, fake, home):
        fake.fail_next(
            'credential/bootstrap', 'CONFIG_DRIFTED', 'config drifted'
        )
        with pytest.raises(ConfigurationError) as e:
            configure(fake, answer=True, **new_keys(region='us-west-2'))
        assert str(e.value) == f'config drifted (CONFIG_DRIFTED). {NOT_STORED}'
        assert fake.credential('keys.ci') is None
        assert_nothing_written(home)

    def test_a_daemon_that_stops_before_the_store_saves_nothing(
        self, fake, home
    ):
        error = CredentialDaemonNotRunningError(
            error_msg='Nothing answers at the socket.'
        )
        with mock.patch.object(
            CredentialDaemonClient, 'store_keys', side_effect=error
        ):
            with pytest.raises(ConfigurationError) as e:
                configure(fake, answer=True, **new_keys())
        assert 'Then try again.' in str(e.value)
        assert str(e.value).endswith(NOT_STORED)
        assert_nothing_written(home)

    def test_a_name_already_there_is_refused_before_the_store(
        self, fake, home
    ):
        fake.seed('keys.ci', kind=KIND_IAM_USER)
        with pytest.raises(ConfigurationError) as e:
            configure(fake, answer=True, **new_keys())
        assert str(e.value) == (
            "The credential daemon already has a credential named "
            f"'keys.ci'. {NOT_STORED} Use another profile name."
        )
        assert bootstraps(fake) == []
        assert_nothing_written(home)

    def test_a_name_stored_since_the_list_is_refused_the_same_way(
        self, fake, home
    ):
        fake.need_approval_next('credential/bootstrap', 'replace keys.ci')
        with pytest.raises(ConfigurationError) as e:
            configure(fake, answer=True, **new_keys())
        assert 'already has a credential named' in str(e.value)
        assert_nothing_written(home)

    @pytest.mark.parametrize(
        'error', [OSError('disk full'), KeyboardInterrupt()]
    )
    def test_a_failed_config_write_leaves_the_stored_keys(
        self, fake, home, capsys, error
    ):
        with fail_config_write(error):
            with pytest.raises(type(error)):
                configure(fake, answer=True, **new_keys())
        assert fake.credential('keys.ci') is not None
        methods = [m for m, _ in fake.calls]
        assert 'credential/remove' not in methods
        assert 'credential/clear' not in methods
        assert_nothing_written(home)
        assert capsys.readouterr().err == PREVIEW_LINE
        # Trying again with the same profile name names the way out.
        with pytest.raises(ConfigurationError) as e:
            configure(fake, answer=True, **new_keys())
        assert str(e.value) == (
            "The credential daemon already has a credential named "
            f"'keys.ci'. {NOT_STORED} Use another profile name."
        )
        assert_nothing_written(home)


def store_then_fail(error):
    """A store_keys that stores the keys, then fails with ``error``, as
    when the reply is lost or Ctrl-C comes after the keys were sent."""
    store_keys = CredentialDaemonClient.store_keys

    def store(client, *args, **kwargs):
        store_keys(client, *args, **kwargs)
        raise error

    return mock.patch.object(CredentialDaemonClient, 'store_keys', store)


class TestStoreInterrupted:
    def assert_left_stored(self, fake, home):
        assert fake.credential('keys.ci') is not None
        assert 'credential/remove' not in [m for m, _ in fake.calls]
        assert_nothing_written(home)

    def test_ctrl_c_after_the_keys_were_sent_leaves_them(
        self, fake, home, capsys
    ):
        with store_then_fail(KeyboardInterrupt()):
            with pytest.raises(KeyboardInterrupt):
                configure(fake, answer=True, **new_keys())
        self.assert_left_stored(fake, home)
        assert capsys.readouterr().err == PREVIEW_LINE
        # Trying again with the same profile name names the way out.
        with pytest.raises(ConfigurationError) as e:
            configure(fake, answer=True, **new_keys())
        assert str(e.value) == (
            "The credential daemon already has a credential named "
            f"'keys.ci'. {NOT_STORED} Use another profile name."
        )

    def test_a_timeout_after_the_keys_were_sent_leaves_them(self, fake, home):
        error = CredentialDaemonTimeoutError(error_msg='No reply in 5s.')
        with store_then_fail(error):
            with pytest.raises(ConfigurationError) as e:
                configure(fake, answer=True, **new_keys())
        assert str(e.value).startswith('No reply in 5s. Start the ')
        assert str(e.value).endswith(NOT_STORED)
        self.assert_left_stored(fake, home)


class TestExistingProfile:
    @pytest.mark.parametrize(
        'name, kind', [('keys.ci', KIND_IAM_USER), ('login.ci', KIND_LOGIN)]
    )
    def test_a_daemon_profile_gets_the_keys_in_files_as_before(
        self, fake, home, name, kind
    ):
        # The keys aren't used while credential_daemon is set.
        fake.seed(name, kind=kind)
        profile = f"""\
            [profile ci]
            credential_daemon = {name}
            credential_storage = daemon
            """
        write(home, 'config', profile)
        ask = configure(fake, **new_keys(region='us-west-2'))
        ask.assert_not_called()
        assert fake.calls == []
        assert SECRET_KEY in read(home, 'credentials')
        assert read(home, 'config') == (
            textwrap.dedent(profile) + 'region = us-west-2\n'
        )

    def test_keys_in_files_are_replaced_as_before(self, fake, home):
        write(home, 'credentials', '[ci]\naws_access_key_id = AKIAOLD\n')
        ask = configure(fake, **new_keys())
        ask.assert_not_called()
        assert fake.calls == []
        assert ACCESS_KEY in read(home, 'credentials')
        assert 'credential_' not in read(home, 'config')


class TestPreviewNotice:
    def test_said_once_before_the_storage_question(self, fake, home, capsys):
        ask = configure(fake, answer=True, **new_keys())
        assert ask.call_count == 1
        captured = capsys.readouterr()
        assert captured.err == PREVIEW_LINE
        assert PREVIEW_NOTICE not in captured.out

    def test_no_terminal_says_nothing(self, fake, home, capsys):
        ask = configure(fake, tty=False, **new_keys())
        assert not ask.called
        assert PREVIEW_NOTICE not in capsys.readouterr().err

    def test_the_env_var_says_nothing(self, fake, home, capsys):
        ask = configure(
            fake,
            environ={'AWS_CREDENTIAL_STORAGE': 'file'},
            **new_keys(),
        )
        assert not ask.called
        assert PREVIEW_NOTICE not in capsys.readouterr().err

    def test_an_existing_profile_says_nothing(self, fake, home, capsys):
        write(home, 'credentials', '[ci]\naws_access_key_id = AKIAOLD\n')
        ask = configure(fake, **new_keys())
        assert not ask.called
        assert PREVIEW_NOTICE not in capsys.readouterr().err
