# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import json
import os

import pytest
from botocore.utils import generate_login_cache_key

from awscli.customizations.login.logout import LogoutCommand
from tests import mock


@pytest.fixture
def login_session_id():
    return "arn:aws:sts::012345678901:assumed-role/Login/foo"


@pytest.fixture
def config(login_session_id):
    return {
        'profiles': {
            'default': {
                'region': 'us-east-1',
            },
            'login-profile': {
                'region': 'us-east-1',
                'login_session': login_session_id,
            },
        }
    }


@pytest.fixture
def session(config):
    session = mock.Mock()
    session.full_config = config
    return session


@pytest.fixture
def login_cache_dir(tmpdir, login_session_id):
    cache_key = generate_login_cache_key(login_session_id)
    tmpdir.join(f"{cache_key}.json").write(b'')
    return tmpdir


@pytest.fixture
def valid_token_structure():
    return {
        "accessToken": {
            "accessKeyId": "ASIATESTACCESSKEY123",
            "secretAccessKey": "test-secret-key",
            "sessionToken": "test-session-token",
            "accountId": "012345678901",
            "expiresAt": "2025-11-10T12:00:00Z"
        },
        "tokenType": "Bearer",
        "clientId": "arn:aws:signin:::devtools/test",
        "refreshToken": "test-refresh-token",
        "idToken": "test-id-token",
        "dpopKey": (
            "-----BEGIN EC PRIVATE KEY-----\n"
            "test-key\n"
            "-----END EC PRIVATE KEY-----"
        )
    }


@pytest.fixture
def logout_cmd(session, login_cache_dir):
    logout = LogoutCommand(
        session=session,
        cache_dir=login_cache_dir,
    )
    return logout


class TestLogoutCommand:
    @mock.patch('awscli.customizations.login.logout.os.remove')
    def test_logout_deletes_cache_files(
        self,
        mock_remove,
        logout_cmd,
        session,
        login_cache_dir,
        login_session_id,
        capsys,
    ):
        session.profile = 'login-profile'
        cache_key = generate_login_cache_key(login_session_id)

        parsed_args = mock.Mock()
        parsed_args.all = False
        logout_cmd._run_main(parsed_args, mock.Mock())

        expected_calls = [
            mock.call(os.path.join(login_cache_dir, f"{cache_key}.json")),
        ]
        mock_remove.assert_has_calls(expected_calls)

        captured = capsys.readouterr()
        assert (
            "Removed cached login credentials for profile 'login-profile'"
            in captured.out
        )

    @mock.patch('awscli.customizations.login.logout.os.remove')
    def test_logout_no_login_session(
        self, mock_remove, logout_cmd, session, capsys
    ):
        session.profile = 'default'

        parsed_args = mock.Mock()
        parsed_args.all = False
        logout_cmd._run_main(parsed_args, mock.Mock())
        mock_remove.assert_not_called()

        captured = capsys.readouterr()
        assert (
            captured.err
            == "warning: no login session found for profile 'default'\n"
        )

    def test_logout_all_deletes_multiple_tokens(
        self, logout_cmd, login_cache_dir, valid_token_structure, capsys
    ):
        token_files = []
        for i in range(3):
            token_file = login_cache_dir.join(f"token_{i}.json")
            token_file.write(json.dumps(valid_token_structure))
            token_files.append(token_file)

        for token_file in token_files:
            assert token_file.exists()

        parsed_args = mock.Mock()
        parsed_args.all = True
        logout_cmd._run_main(parsed_args, mock.Mock())

        for token_file in token_files:
            assert not token_file.exists()

        captured = capsys.readouterr()
        assert "Removed 3 cached login credentials" in captured.out

    def test_logout_all_ignores_invalid_json(
        self, logout_cmd, login_cache_dir, valid_token_structure, capsys
    ):
        valid_token_file = login_cache_dir.join("valid_token.json")
        valid_token_file.write(json.dumps(valid_token_structure))

        invalid_json_file = login_cache_dir.join("invalid.json")
        invalid_json_file.write("{ this is not valid json }")

        assert valid_token_file.exists()
        assert invalid_json_file.exists()

        parsed_args = mock.Mock()
        parsed_args.all = True
        logout_cmd._run_main(parsed_args, mock.Mock())

        assert not valid_token_file.exists()

        assert invalid_json_file.exists()

        captured = capsys.readouterr()
        assert "Removed 1 cached login credential" in captured.out

    def test_logout_all_ignores_non_token_files(
        self, logout_cmd, login_cache_dir, valid_token_structure, capsys
    ):
        valid_token_file = login_cache_dir.join("valid_token.json")
        valid_token_file.write(json.dumps(valid_token_structure))

        non_token_json = {
            "someOtherKey": "value",
            "anotherKey": {
                "nestedData": "test"
            }
        }
        non_token_file = login_cache_dir.join("non_token.json")
        non_token_file.write(json.dumps(non_token_json))

        assert valid_token_file.exists()
        assert non_token_file.exists()

        parsed_args = mock.Mock()
        parsed_args.all = True
        logout_cmd._run_main(parsed_args, mock.Mock())

        assert not valid_token_file.exists()

        assert non_token_file.exists()

        captured = capsys.readouterr()
        assert "Removed 1 cached login credential" in captured.out

    def test_logout_all_with_no_tokens(
        self, logout_cmd, tmpdir, session, capsys
    ):
        empty_cache_dir = tmpdir.mkdir("empty_cache")

        logout_cmd_empty = LogoutCommand(
            session=session,
            cache_dir=empty_cache_dir,
        )

        parsed_args = mock.Mock()
        parsed_args.all = True
        logout_cmd_empty._run_main(parsed_args, mock.Mock())

        captured = capsys.readouterr()
        assert "No cached login session tokens found" in captured.out

    def test_logout_all_when_cache_dir_missing(
        self, session, tmpdir, capsys
    ):
        non_existent_cache_dir = tmpdir.join("non_existent_cache")

        assert not non_existent_cache_dir.exists()

        logout_cmd_missing = LogoutCommand(
            session=session,
            cache_dir=non_existent_cache_dir,
        )

        parsed_args = mock.Mock()
        parsed_args.all = True
        logout_cmd_missing._run_main(parsed_args, mock.Mock())

        captured = capsys.readouterr()
        assert "No cached login session tokens found" in captured.out

    def test_logout_all_validates_token_structure(
        self, logout_cmd, login_cache_dir, valid_token_structure, capsys
    ):
        valid_token_file = login_cache_dir.join("valid_token.json")
        valid_token_file.write(json.dumps(valid_token_structure))

        malformed_token_structure = {
            "accessToken": {
                "secretAccessKey": "test-secret-key",
                "sessionToken": "test-session-token",
                "accountId": "012345678901",
                "expiresAt": "2025-11-10T12:00:00Z"
            },
            "tokenType": "Bearer",
            "clientId": "arn:aws:signin:::devtools/test",
            "refreshToken": "test-refresh-token",
            "idToken": "test-id-token"
        }

        malformed_token_file = login_cache_dir.join("malformed_token.json")
        malformed_token_file.write(json.dumps(malformed_token_structure))

        assert valid_token_file.exists()
        assert malformed_token_file.exists()

        parsed_args = mock.Mock()
        parsed_args.all = True
        logout_cmd._run_main(parsed_args, mock.Mock())

        assert not valid_token_file.exists()

        assert malformed_token_file.exists()

        captured = capsys.readouterr()
        assert "Removed 1 cached login credential" in captured.out
