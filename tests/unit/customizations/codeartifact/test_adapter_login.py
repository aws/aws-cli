import errno
import os
import re
import signal
import stat
import subprocess
from configparser import RawConfigParser
from datetime import datetime
from urllib.parse import urlsplit

from dateutil.relativedelta import relativedelta
from dateutil.tz import tzlocal, tzutc

from awscli.compat import urlparse
from awscli.customizations.codeartifact.login import (
    BaseLogin,
    CommandFailedError,
    DotNetLogin,
    NpmLogin,
    NuGetLogin,
    PipLogin,
    SwiftLogin,
    TwineLogin,
    get_relative_expiration_time,
)
from awscli.testutils import FileCreator, mock, skip_if_windows, unittest


class TestBaseLogin(unittest.TestCase):
    def setUp(self):
        self.domain = 'domain'
        self.domain_owner = 'domain-owner'
        self.package_format = 'npm'
        self.repository = 'repository'
        self.auth_token = 'auth-token'
        self.expiration = (
            datetime.now(tzlocal())
            + relativedelta(hours=10)
            + relativedelta(minutes=9)
        ).replace(microsecond=0)
        self.endpoint = (
            f'https://{self.domain}-{self.domain_owner}.codeartifact.aws.'
            f'a2z.com/{self.package_format}/{self.repository}/'
        )

        self.subprocess_utils = mock.Mock()

        self.test_subject = BaseLogin(
            self.auth_token,
            self.expiration,
            self.endpoint,
            self.domain,
            self.repository,
            self.subprocess_utils,
        )

    def test_login(self):
        with self.assertRaises(NotImplementedError):
            self.test_subject.login()

    def test_get_commands(self):
        with self.assertRaises(NotImplementedError):
            self.test_subject.get_commands(self.endpoint, self.auth_token)

    def test_run_commands_command_failed(self):
        error_to_be_caught = subprocess.CalledProcessError(
            returncode=1,
            cmd=['cmd'],
            output=None,
            stderr=b'Command error message.',
        )
        self.subprocess_utils.run.side_effect = error_to_be_caught
        with self.assertRaisesRegex(
            CommandFailedError,
            rf"{re.escape(str(error_to_be_caught))}"
            rf" Stderr from command:\nCommand error message.",
        ):
            self.test_subject._run_commands('tool', ['cmd'])

    def test_run_commands_command_failed_redact_auth_token(self):
        error_to_be_caught = subprocess.CalledProcessError(
            returncode=1,
            cmd=['cmd', 'with', 'auth-token', 'present'],
            output=None,
            stderr=b'Command error message.',
        )
        self.subprocess_utils.run.side_effect = error_to_be_caught
        with self.assertRaisesRegex(
            CommandFailedError,
            (
                r"(?=.*cmd)(?=.*with)(?!.*auth-token)(?=.*present)"
                r"(?=.*Stderr from command:\nCommand error message.)"
            ),
        ):
            self.test_subject._run_commands('tool', ['cmd'])

    def test_run_commands_nonexistent_command(self):
        self.subprocess_utils.run.side_effect = OSError(
            errno.ENOENT, 'not found error'
        )
        tool = 'NotSupported'
        with self.assertRaisesRegex(ValueError, f'{tool} was not found.'):
            self.test_subject._run_commands(tool, ['echo', tool])

    def test_run_commands_unhandled_error(self):
        self.subprocess_utils.run.side_effect = OSError(
            errno.ENOSYS, 'unhandled error'
        )
        tool = 'NotSupported'
        with self.assertRaisesRegex(OSError, 'unhandled error'):
            self.test_subject._run_commands(tool, ['echo', tool])


def handle_timeout(signum, frame, test_name):
    raise TimeoutError(f"{test_name} timed out!!")


class TestSwiftLogin(unittest.TestCase):
    def setUp(self):
        self.domain = 'domain'
        self.domain_owner = 'domain-owner'
        self.package_format = 'swift'
        self.repository = 'repository'
        self.auth_token = 'auth-token'
        self.namespace = 'namespace'
        self.expiration = (
            datetime.now(tzlocal())
            + relativedelta(hours=10)
            + relativedelta(minutes=9)
        ).replace(microsecond=0)
        self.endpoint = (
            f'https://{self.domain}-{self.domain_owner}.codeartifact'
            f'.aws.a2z.com/{self.package_format}/{self.repository}/'
        )
        self.hostname = urlparse.urlparse(self.endpoint).hostname
        self.new_entry = SwiftLogin.DEFAULT_NETRC_FMT.format(
            hostname=self.hostname, auth_token=self.auth_token
        )

        self.file_creator = FileCreator()
        self.test_netrc_path = self.file_creator.full_path('netrc')
        self.get_netrc_path_patch = mock.patch(
            'awscli.customizations.codeartifact.login.SwiftLogin'
            '.get_netrc_path'
        )
        self.get_netrc_path_mock = self.get_netrc_path_patch.start()
        self.get_netrc_path_mock.return_value = self.test_netrc_path

        self.base_command = ['swift', 'package-registry', 'set', self.endpoint]
        self.macos_commands = [
            self.base_command[:],
            [
                'swift',
                'package-registry',
                'login',
                self.endpoint + 'login',
                '--token',
                self.auth_token,
            ],
        ]
        self.non_macos_commands = [
            self.base_command[:],
            ['swift', 'package-registry', 'login', self.endpoint + 'login'],
        ]

        self.subprocess_utils = mock.Mock()

        self.test_subject = SwiftLogin(
            self.auth_token,
            self.expiration,
            self.endpoint,
            self.domain,
            self.repository,
            self.subprocess_utils,
        )

    def tearDown(self):
        self.get_netrc_path_patch.stop()
        self.file_creator.remove_all()

    def _assert_netrc_has_expected_content(self, expected_contents):
        with open(self.test_netrc_path) as file:
            actual_contents = file.read()
            self.assertEqual(expected_contents, actual_contents)

    def _assert_netrc_has_expected_permissions(self):
        file_stat = os.stat(self.test_netrc_path)
        file_mode = file_stat.st_mode
        self.assertTrue(stat.S_IRUSR & file_mode)
        self.assertTrue(stat.S_IWUSR & file_mode)

    def test_get_netrc_path(self):
        self.assertEqual(SwiftLogin.get_netrc_path(), self.test_netrc_path)

    def test_regex_only_match_escaped_hostname(self):
        pattern = re.compile(
            SwiftLogin.NETRC_REGEX_FMT.format(
                escaped_hostname=re.escape(self.hostname)
            ),
            re.M,
        )
        bad_endpoint = (
            f'https://{self.domain}-{self.domain_owner}-codeartifact'
            f'-aws-a2z-com/{self.package_format}/{self.repository}/'
        )
        bad_hostname = urlparse.urlparse(bad_endpoint).hostname
        bad_entry = SwiftLogin.DEFAULT_NETRC_FMT.format(
            hostname=bad_hostname, auth_token=self.auth_token
        )
        self.assertTrue(pattern.match(self.new_entry))
        self.assertFalse(pattern.match(bad_entry))

    def test_create_netrc_if_not_exist(self):
        self.assertFalse(os.path.exists(self.test_netrc_path))
        self.test_subject._update_netrc_entry(
            self.hostname, 'a new entry', self.test_netrc_path
        )
        self.assertTrue(os.path.exists(self.test_netrc_path))
        self._assert_netrc_has_expected_permissions()
        self._assert_netrc_has_expected_content('a new entry\n')

    def test_replacement_token_has_backslash(self):
        existing_content = f'machine {self.hostname} login token password expired-auth-token\n'
        with open(self.test_netrc_path, 'w+') as f:
            f.write(existing_content)
        self.test_subject.auth_token = r'new-token_.\1\g<entry_start>\n\w'
        # make sure it uses re.sub() to replace the token
        self.test_subject._update_netrc_entry(
            self.hostname, '', self.test_netrc_path
        )
        self.assertTrue(os.path.exists(self.test_netrc_path))
        self._assert_netrc_has_expected_content(
            f'machine {self.hostname} login token password {self.test_subject.auth_token}\n'
        )

    def test_update_netrc_with_existing_entry(self):
        existing_content = f'machine {self.hostname} login token password expired-auth-token\n'

        expected_content = f'{self.new_entry}\n'
        with open(self.test_netrc_path, 'w+') as f:
            f.write(existing_content)

        self.test_subject._update_netrc_entry(
            self.hostname, self.new_entry, self.test_netrc_path
        )
        self._assert_netrc_has_expected_content(expected_content)

    def test_update_netrc_with_existing_entry_in_between(self):
        existing_content = (
            f'some random line above\n'
            f'machine {self.hostname} login token password expired-auth-token\n'
            f'some random line below\n'
        )

        expected_content = (
            f'some random line above\n'
            f'{self.new_entry}\n'
            f'some random line below\n'
        )
        with open(self.test_netrc_path, 'w+') as f:
            f.write(existing_content)

        self.test_subject._update_netrc_entry(
            self.hostname, self.new_entry, self.test_netrc_path
        )
        self._assert_netrc_has_expected_content(expected_content)

    def test_append_netrc_without_ending_newline(self):
        existing_content = 'machine host login user password 1234'

        expected_content = (
            f'machine host login user password 1234\n' f'{self.new_entry}\n'
        )
        with open(self.test_netrc_path, 'w+') as f:
            f.write(existing_content)

        self.test_subject._update_netrc_entry(
            self.hostname, self.new_entry, self.test_netrc_path
        )
        self._assert_netrc_has_expected_content(expected_content)

    def test_append_netrc_with_ending_newline(self):
        existing_content = 'machine host login user password 1234\n'

        expected_content = (
            f'machine host login user password 1234\n' f'{self.new_entry}\n'
        )
        with open(self.test_netrc_path, 'w+') as f:
            f.write(existing_content)

        self.test_subject._update_netrc_entry(
            self.hostname, self.new_entry, self.test_netrc_path
        )
        self._assert_netrc_has_expected_content(expected_content)

    def test_update_netrc_with_multiple_spaces_and_newlines(self):
        existing_content = (
            f' machine   {self.hostname}\n'
            f'   login token \n'
            f'password expired-auth-token  \n'
            f'\n'
            f'machine example1.com\n'
            f' login user1 \n'
            f'password  1234\n'
        )
        expected_content = (
            f' machine   {self.hostname}\n'
            f'   login token \n'
            f'password auth-token  \n'
            f'\n'
            f'machine example1.com\n'
            f' login user1 \n'
            f'password  1234\n'
        )
        with open(self.test_netrc_path, 'w+') as f:
            f.write(existing_content)

        self.test_subject._update_netrc_entry(
            self.hostname, self.new_entry, self.test_netrc_path
        )
        self._assert_netrc_has_expected_content(expected_content)

    def test_update_netrc_with_multiple_existing_entries(self):
        existing_content = (
            f'machine {self.hostname} login token password expired-auth-token-1\n'
            f'machine {self.hostname} login token password expired-auth-token-2\n'
        )
        expected_content = f'{self.new_entry}\n' f'{self.new_entry}\n'
        with open(self.test_netrc_path, 'w+') as f:
            f.write(existing_content)

        self.test_subject._update_netrc_entry(
            self.hostname, self.new_entry, self.test_netrc_path
        )
        self._assert_netrc_has_expected_content(expected_content)

    @mock.patch('awscli.customizations.codeartifact.login.is_macos', True)
    def test_login_macos(self):
        self.test_subject.login()
        expected_calls = [
            mock.call(command, capture_output=True, check=True)
            for command in self.macos_commands
        ]
        self.subprocess_utils.run.assert_has_calls(
            expected_calls, any_order=True
        )

    @mock.patch('awscli.customizations.codeartifact.login.is_macos', False)
    def test_login_non_macos(self):
        self.test_subject.login()
        expected_calls = [
            mock.call(command, capture_output=True, check=True)
            for command in self.non_macos_commands
        ]
        self.subprocess_utils.run.assert_has_calls(
            expected_calls, any_order=True
        )

    def test_login_swift_tooling_error(self):
        self.subprocess_utils.run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd='swift command', stderr=b''
        )
        with self.assertRaises(CommandFailedError):
            self.test_subject.login()

    def test_login_swift_not_installed(self):
        self.subprocess_utils.run.side_effect = OSError(
            errno.ENOENT, 'not found error'
        )
        with self.assertRaisesRegex(
            ValueError, 'swift was not found. Please verify installation.'
        ):
            self.test_subject.login()

    def test_get_scope(self):
        expected_value = 'namespace'
        scope = self.test_subject.get_scope(self.namespace)
        self.assertEqual(scope, expected_value)

    def test_get_scope_none_namespace(self):
        expected_value = None
        scope = self.test_subject.get_scope(None)
        self.assertEqual(scope, expected_value)

    def test_get_scope_invalid_leading_character(self):
        with self.assertRaises(ValueError):
            self.test_subject.get_scope(f'.{self.namespace}')

    def test_get_scope_invalid_length(self):
        with self.assertRaises(ValueError):
            self.test_subject.get_scope("a" * 40)

    @mock.patch('awscli.customizations.codeartifact.login.is_macos', True)
    def test_get_commands_macos(self):
        commands = self.test_subject.get_commands(
            self.endpoint, self.auth_token
        )
        self.assertCountEqual(commands, self.macos_commands)

    @mock.patch('awscli.customizations.codeartifact.login.is_macos', False)
    def test_get_commands_non_macos(self):
        commands = self.test_subject.get_commands(
            self.endpoint, self.auth_token
        )
        self.assertCountEqual(commands, self.non_macos_commands)

    @mock.patch('awscli.customizations.codeartifact.login.is_macos', True)
    def test_get_commands_with_scope_macos(self):
        commands = self.test_subject.get_commands(
            self.endpoint, self.auth_token, scope=self.namespace
        )
        self.macos_commands[0] += ['--scope', self.namespace]
        self.assertCountEqual(commands, self.macos_commands)

    @mock.patch('awscli.customizations.codeartifact.login.is_macos', False)
    def test_get_commands_with_scope_non_macos(self):
        commands = self.test_subject.get_commands(
            self.endpoint, self.auth_token, scope=self.namespace
        )
        self.non_macos_commands[0] += ['--scope', self.namespace]
        self.assertCountEqual(commands, self.non_macos_commands)

    def test_login_dry_run(self):
        self.test_subject.login(dry_run=True)
        self.subprocess_utils.check_output.assert_not_called()
        self.assertFalse(os.path.exists(self.test_netrc_path))

    @skip_if_windows("Unix file permissions are not supported on Windows.")
    @mock.patch('awscli.customizations.codeartifact.login.is_macos', False)
    def test_login_adjusts_permissions_on_preexisting_file(self):
        existing_content = (
            f'machine {self.hostname} login token password old-token\n'
        )
        with open(self.test_netrc_path, 'w') as f:
            f.write(existing_content)
        os.chmod(self.test_netrc_path, 0o644)
        self.test_subject.login()
        file_mode = os.stat(self.test_netrc_path).st_mode
        self.assertEqual(stat.S_IMODE(file_mode), 0o600)

    @skip_if_windows("Unix file permissions are not supported on Windows.")
    @mock.patch('awscli.customizations.codeartifact.login.is_macos', False)
    @mock.patch('sys.stderr')
    @mock.patch('os.chmod', side_effect=OSError(
        errno.EPERM, 'Operation not permitted'
    ))
    def test_login_writes_error_when_chmod_fails(
        self, mock_chmod, mock_stderr
    ):
        existing_content = (
            f'machine {self.hostname} login token password old-token\n'
        )
        with open(self.test_netrc_path, 'w') as f:
            f.write(existing_content)
        self.test_subject.login()
        mock_stderr.write.assert_any_call(
            'Unable to set file permissions for %s: '
            '[Errno 1] Operation not permitted%s'
            % (self.test_netrc_path, os.linesep)
        )

class TestNuGetLogin(unittest.TestCase):
    _NUGET_INDEX_URL_FMT = NuGetLogin._NUGET_INDEX_URL_FMT
    _NUGET_SOURCES_LIST_RESPONSE = b"""\
Registered Sources:
  1. Source Name 1 [Enabled]
     https://source1.com/index.json
  2. Ab[.d7  $#!],   [Disabled]
     https://source2.com/index.json"""

    _NUGET_SOURCES_LIST_RESPONSE_BACKTRACKING = b'1.' + b' ' * 10000 + b'a'

    _NUGET_SOURCES_LIST_RESPONSE_WITH_SPACE = b"""\
                Registered Sources:

                  1. Source Name 1 [Enabled]
                     https://source1.com/index.json
                  2. Ab[.d7  $#!],   [Disabled]
                     https://source2.com/index.json"""

    def setUp(self):
        self.domain = 'domain'
        self.domain_owner = 'domain-owner'
        self.package_format = 'nuget'
        self.repository = 'repository'
        self.auth_token = 'auth-token'
        self.expiration = (
            datetime.now(tzlocal())
            + relativedelta(hours=10)
            + relativedelta(minutes=9)
        ).replace(microsecond=0)
        self.endpoint = (
            f'https://{self.domain}-{self.domain_owner}.codeartifact.aws.'
            f'a2z.com/{self.package_format}/{self.repository}/'
        )

        self.nuget_index_url = self._NUGET_INDEX_URL_FMT.format(
            endpoint=self.endpoint,
        )
        self.source_name = self.domain + '/' + self.repository
        self.list_operation_command = [
            'nuget',
            'sources',
            'list',
            '-format',
            'detailed',
        ]
        self.add_operation_command = [
            'nuget',
            'sources',
            'add',
            '-name',
            self.source_name,
            '-source',
            self.nuget_index_url,
            '-username',
            'aws',
            '-password',
            self.auth_token,
        ]
        self.update_operation_command = [
            'nuget',
            'sources',
            'update',
            '-name',
            self.source_name,
            '-source',
            self.nuget_index_url,
            '-username',
            'aws',
            '-password',
            self.auth_token,
        ]

        self.subprocess_utils = mock.Mock()

        self.test_subject = NuGetLogin(
            self.auth_token,
            self.expiration,
            self.endpoint,
            self.domain,
            self.repository,
            self.subprocess_utils,
        )

    def test_login(self):
        self.subprocess_utils.check_output.return_value = (
            self._NUGET_SOURCES_LIST_RESPONSE
        )
        self.test_subject.login()
        self.subprocess_utils.check_output.assert_any_call(
            self.list_operation_command, stderr=self.subprocess_utils.PIPE
        )
        self.subprocess_utils.run.assert_called_with(
            self.add_operation_command, capture_output=True, check=True
        )

    def test_login_dry_run(self):
        self.subprocess_utils.check_output.return_value = (
            self._NUGET_SOURCES_LIST_RESPONSE
        )
        self.test_subject.login(dry_run=True)
        self.subprocess_utils.check_output.assert_called_once_with(
            ['nuget', 'sources', 'list', '-format', 'detailed'],
            stderr=self.subprocess_utils.PIPE,
        )

    def test_login_old_nuget(self):
        self.subprocess_utils.check_output.return_value = (
            self._NUGET_SOURCES_LIST_RESPONSE_WITH_SPACE
        )
        self.test_subject.login()
        self.subprocess_utils.check_output.assert_any_call(
            self.list_operation_command, stderr=self.subprocess_utils.PIPE
        )
        self.subprocess_utils.run.assert_called_with(
            self.add_operation_command, capture_output=True, check=True
        )

    def test_login_dry_run_old_nuget(self):
        self.subprocess_utils.check_output.return_value = (
            self._NUGET_SOURCES_LIST_RESPONSE_WITH_SPACE
        )
        self.test_subject.login(dry_run=True)
        self.subprocess_utils.check_output.assert_called_once_with(
            ['nuget', 'sources', 'list', '-format', 'detailed'],
            stderr=self.subprocess_utils.PIPE,
        )

    def test_login_source_name_already_exists(self):
        list_response = (
            'Registered Sources:\n'
            '  1.  ' + self.source_name + ' [ENABLED]\n'
            '      https://source.com/index.json'
        )
        self.subprocess_utils.check_output.return_value = list_response.encode(
            'utf-8'
        )
        self.test_subject.login()
        self.subprocess_utils.run.assert_called_with(
            self.update_operation_command, capture_output=True, check=True
        )

    def test_login_source_url_already_exists_old_nuget(self):
        non_default_source_name = 'Source Name'
        list_response = (
            'Registered Sources:\n'
            '\n'
            '  1. ' + non_default_source_name + ' [ENABLED]\n'
            '      ' + self.nuget_index_url
        )
        self.subprocess_utils.check_output.return_value = list_response.encode(
            'utf-8'
        )
        self.test_subject.login()
        self.subprocess_utils.run.assert_called_with(
            [
                'nuget',
                'sources',
                'update',
                '-name',
                non_default_source_name,
                '-source',
                self.nuget_index_url,
                '-username',
                'aws',
                '-password',
                self.auth_token,
            ],
            capture_output=True,
            check=True,
        )

    def test_login_source_url_already_exists(self):
        non_default_source_name = 'Source Name'
        list_response = (
            'Registered Sources:\n'
            '  1. ' + non_default_source_name + ' [ENABLED]\n'
            '      ' + self.nuget_index_url
        )
        self.subprocess_utils.check_output.return_value = list_response.encode(
            'utf-8'
        )
        self.test_subject.login()
        self.subprocess_utils.run.assert_called_with(
            [
                'nuget',
                'sources',
                'update',
                '-name',
                non_default_source_name,
                '-source',
                self.nuget_index_url,
                '-username',
                'aws',
                '-password',
                self.auth_token,
            ],
            capture_output=True,
            check=True,
        )

    def test_login_nuget_not_installed(self):
        self.subprocess_utils.check_output.side_effect = OSError(
            errno.ENOENT, 'not found error'
        )
        with self.assertRaisesRegex(
            ValueError, 'nuget was not found. Please verify installation.'
        ):
            self.test_subject.login()

    @skip_if_windows("Windows does not support signal.SIGALRM.")
    def test_login_nuget_sources_listed_with_backtracking(self):
        self.subprocess_utils.check_output.return_value = (
            self._NUGET_SOURCES_LIST_RESPONSE_BACKTRACKING
        )
        signal.signal(
            signal.SIGALRM,
            lambda signum, frame: handle_timeout(signum, frame, self.id()),
        )
        signal.alarm(10)
        self.test_subject.login()
        signal.alarm(0)
        self.subprocess_utils.check_output.assert_any_call(
            self.list_operation_command, stderr=self.subprocess_utils.PIPE
        )


class TestDotNetLogin(unittest.TestCase):
    _NUGET_INDEX_URL_FMT = NuGetLogin._NUGET_INDEX_URL_FMT
    _NUGET_SOURCES_LIST_RESPONSE = b"""\
Registered Sources:
  1. Source Name 1 [Enabled]
     https://source1.com/index.json
  2. Ab[.d7  $#!],   [Disabled]
     https://source2.com/index.json"""

    _NUGET_SOURCES_LIST_RESPONSE_BACKTRACKING = b'1.' + b' ' * 10000 + b'a'

    _NUGET_SOURCES_LIST_RESPONSE_WITH_EXTRA_NON_LIST_TEXT = b"""\
Welcome to dotnet 2.0!

Registered Sources:
  1. Source Name 1 [Enabled]
     https://source1.com/index.json
  2. ati-nugetserver [Disabled]
     http://atinugetserver-env.elasticbeanstalk.com/nuget
warn : You are running the 'list source' operation with an 'HTTP' source,
'ati-nugetserver' [http://atinugetserver-env..elasticbeanstalk.com/nuget]'.
Non-HTTPS access will be removed in a future version. Consider migrating
to an 'HTTPS' source."""

    def setUp(self):
        self.domain = 'domain'
        self.domain_owner = 'domain-owner'
        self.package_format = 'nuget'
        self.repository = 'repository'
        self.auth_token = 'auth-token'
        self.expiration = (
            datetime.now(tzlocal())
            + relativedelta(hours=10)
            + relativedelta(minutes=9)
        ).replace(microsecond=0)
        self.endpoint = (
            f'https://{self.domain}-{self.domain_owner}.codeartifact.aws.'
            f'a2z.com/{self.package_format}/{self.repository}/'
        )

        self.nuget_index_url = self._NUGET_INDEX_URL_FMT.format(
            endpoint=self.endpoint,
        )
        self.source_name = self.domain + '/' + self.repository
        self.list_operation_command = [
            'dotnet',
            'nuget',
            'list',
            'source',
            '--format',
            'detailed',
        ]
        self.add_operation_command_windows = [
            'dotnet',
            'nuget',
            'add',
            'source',
            self.nuget_index_url,
            '--name',
            self.source_name,
            '--username',
            'aws',
            '--password',
            self.auth_token,
        ]
        self.add_operation_command_non_windows = [
            'dotnet',
            'nuget',
            'add',
            'source',
            self.nuget_index_url,
            '--name',
            self.source_name,
            '--username',
            'aws',
            '--password',
            self.auth_token,
            '--store-password-in-clear-text',
        ]
        self.update_operation_command_windows = [
            'dotnet',
            'nuget',
            'update',
            'source',
            self.source_name,
            '--source',
            self.nuget_index_url,
            '--username',
            'aws',
            '--password',
            self.auth_token,
        ]
        self.update_operation_command_non_windows = [
            'dotnet',
            'nuget',
            'update',
            'source',
            self.source_name,
            '--source',
            self.nuget_index_url,
            '--username',
            'aws',
            '--password',
            self.auth_token,
            '--store-password-in-clear-text',
        ]

        self.subprocess_utils = mock.Mock()

        self.test_subject = DotNetLogin(
            self.auth_token,
            self.expiration,
            self.endpoint,
            self.domain,
            self.repository,
            self.subprocess_utils,
        )

    @mock.patch('awscli.customizations.codeartifact.login.is_windows', False)
    def test_login(self):
        self.subprocess_utils.check_output.return_value = (
            self._NUGET_SOURCES_LIST_RESPONSE
        )
        self.test_subject.login()
        self.subprocess_utils.check_output.assert_any_call(
            self.list_operation_command, stderr=self.subprocess_utils.PIPE
        )
        self.subprocess_utils.run.assert_called_with(
            self.add_operation_command_non_windows,
            capture_output=True,
            check=True,
        )

    @mock.patch('awscli.customizations.codeartifact.login.is_windows', True)
    def test_login_on_windows(self):
        self.subprocess_utils.check_output.return_value = (
            self._NUGET_SOURCES_LIST_RESPONSE
        )
        self.test_subject.login()
        self.subprocess_utils.check_output.assert_any_call(
            self.list_operation_command, stderr=self.subprocess_utils.PIPE
        )
        self.subprocess_utils.run.assert_called_with(
            self.add_operation_command_windows, capture_output=True, check=True
        )

    def test_login_dry_run(self):
        self.subprocess_utils.check_output.return_value = (
            self._NUGET_SOURCES_LIST_RESPONSE
        )
        self.test_subject.login(dry_run=True)
        self.subprocess_utils.check_output.assert_called_once_with(
            self.list_operation_command, stderr=self.subprocess_utils.PIPE
        )

    @mock.patch('awscli.customizations.codeartifact.login.is_windows', False)
    def test_login_sources_listed_with_extra_non_list_text(self):
        self.subprocess_utils.check_output.return_value = (
            self._NUGET_SOURCES_LIST_RESPONSE_WITH_EXTRA_NON_LIST_TEXT
        )
        self.test_subject.login()
        self.subprocess_utils.check_output.assert_any_call(
            self.list_operation_command, stderr=self.subprocess_utils.PIPE
        )
        self.subprocess_utils.run.assert_called_with(
            self.add_operation_command_non_windows,
            capture_output=True,
            check=True,
        )

    @mock.patch('awscli.customizations.codeartifact.login.is_windows', True)
    def test_login_sources_listed_with_extra_non_list_text_on_windows(self):
        self.subprocess_utils.check_output.return_value = (
            self._NUGET_SOURCES_LIST_RESPONSE_WITH_EXTRA_NON_LIST_TEXT
        )
        self.test_subject.login()
        self.subprocess_utils.check_output.assert_any_call(
            self.list_operation_command, stderr=self.subprocess_utils.PIPE
        )
        self.subprocess_utils.run.assert_called_with(
            self.add_operation_command_windows, capture_output=True, check=True
        )

    def test_login_sources_listed_with_extra_non_list_text_dry_run(self):
        self.subprocess_utils.check_output.return_value = (
            self._NUGET_SOURCES_LIST_RESPONSE_WITH_EXTRA_NON_LIST_TEXT
        )
        self.test_subject.login(dry_run=True)
        self.subprocess_utils.check_output.assert_called_once_with(
            self.list_operation_command, stderr=self.subprocess_utils.PIPE
        )

    @skip_if_windows("Windows does not support signal.SIGALRM.")
    @mock.patch('awscli.customizations.codeartifact.login.is_windows', False)
    def test_login_dotnet_sources_listed_with_backtracking(self):
        self.subprocess_utils.check_output.return_value = (
            self._NUGET_SOURCES_LIST_RESPONSE_BACKTRACKING
        )
        signal.signal(
            signal.SIGALRM,
            lambda signum, frame: handle_timeout(signum, frame, self.id()),
        )
        signal.alarm(10)
        self.test_subject.login()
        signal.alarm(0)

    @skip_if_windows("Windows does not support signal.SIGALRM.")
    @mock.patch('awscli.customizations.codeartifact.login.is_windows', True)
    def test_login_dotnet_sources_listed_with_backtracking_windows(self):
        self.subprocess_utils.check_output.return_value = (
            self._NUGET_SOURCES_LIST_RESPONSE_BACKTRACKING
        )
        signal.signal(
            signal.SIGALRM,
            lambda signum, frame: handle_timeout(signum, frame, self.id()),
        )
        signal.alarm(10)
        self.test_subject.login()
        signal.alarm(0)

    @mock.patch('awscli.customizations.codeartifact.login.is_windows', False)
    def test_login_source_name_already_exists(self):
        list_response = (
            'Registered Sources:\n'
            '  1.  ' + self.source_name + ' [ENABLED]\n'
            '      https://source.com/index.json'
        )
        self.subprocess_utils.check_output.return_value = list_response.encode(
            'utf-8'
        )
        self.test_subject.login()
        self.subprocess_utils.run.assert_called_with(
            self.update_operation_command_non_windows,
            capture_output=True,
            check=True,
        )

    @mock.patch('awscli.customizations.codeartifact.login.is_windows', True)
    def test_login_source_name_already_exists_on_windows(self):
        list_response = (
            'Registered Sources:\n'
            '  1.  ' + self.source_name + ' [ENABLED]\n'
            '      https://source.com/index.json'
        )
        self.subprocess_utils.check_output.return_value = list_response.encode(
            'utf-8'
        )
        self.test_subject.login()
        self.subprocess_utils.run.assert_called_with(
            self.update_operation_command_windows,
            capture_output=True,
            check=True,
        )

    @mock.patch('awscli.customizations.codeartifact.login.is_windows', True)
    def test_login_source_url_already_exists(self):
        non_default_source_name = 'Source Name'
        list_response = (
            'Registered Sources:\n'
            '  1. ' + non_default_source_name + ' [ENABLED]\n'
            '      ' + self.nuget_index_url
        )
        self.subprocess_utils.check_output.return_value = list_response.encode(
            'utf-8'
        )
        self.test_subject.login()
        self.subprocess_utils.run.assert_called_with(
            [
                'dotnet',
                'nuget',
                'update',
                'source',
                non_default_source_name,
                '--source',
                self.nuget_index_url,
                '--username',
                'aws',
                '--password',
                self.auth_token,
            ],
            capture_output=True,
            check=True,
        )

    def test_login_dotnet_not_installed(self):
        self.subprocess_utils.check_output.side_effect = OSError(
            errno.ENOENT, 'not found error'
        )
        with self.assertRaisesRegex(
            ValueError, 'dotnet was not found. Please verify installation.'
        ):
            self.test_subject.login()


class TestNpmLogin(unittest.TestCase):
    NPM_CMD = NpmLogin.NPM_CMD

    def setUp(self):
        self.domain = 'domain'
        self.domain_owner = 'domain-owner'
        self.package_format = 'npm'
        self.repository = 'repository'
        self.auth_token = 'auth-token'
        self.namespace = 'namespace'
        self.expiration = (
            datetime.now(tzlocal())
            + relativedelta(hours=10)
            + relativedelta(minutes=9)
        ).replace(microsecond=0)
        self.endpoint = (
            f'https://{self.domain}-{self.domain_owner}.codeartifact.aws.'
            f'a2z.com/{self.package_format}/{self.repository}/'
        )

        repo_uri = urlsplit(self.endpoint)
        always_auth_config = f'//{repo_uri.netloc}{repo_uri.path}:always-auth'
        auth_token_config = f'//{repo_uri.netloc}{repo_uri.path}:_authToken'
        self.commands = []
        self.commands.append(
            [self.NPM_CMD, 'config', 'set', 'registry', self.endpoint]
        )
        self.commands.append(
            [self.NPM_CMD, 'config', 'set', always_auth_config, 'true']
        )
        self.auth_token_key = auth_token_config

        self.subprocess_utils = mock.Mock()

        self.test_subject = NpmLogin(
            self.auth_token,
            self.expiration,
            self.endpoint,
            self.domain,
            self.repository,
            self.subprocess_utils,
        )

    @mock.patch('awscli.customizations.codeartifact.login.NpmLogin._write_npmrc_value')
    def test_login(self, mock_write_npmrc):
        self.test_subject.login()
        expected_calls = [
            mock.call(command, capture_output=True, check=True)
            for command in self.commands
        ]
        self.subprocess_utils.run.assert_has_calls(
            expected_calls, any_order=True
        )
        mock_write_npmrc.assert_called_once_with(
            self.auth_token_key, self.auth_token, mock.ANY
        )

    @mock.patch('awscli.customizations.codeartifact.login.NpmLogin._write_npmrc_value')
    def test_login_always_auth_error_ignored(self, mock_write_npmrc):
        """Test login ignores error for always-auth.

        This test is for NPM version >= 9 where the support of 'always-auth'
        has been dropped. Running the command to set config gives a non-zero
        exit code. This is to make sure that login ignores that error and all
        other commands executes successfully.
        """

        def side_effect(command, capture_output, check):
            """Set side_effect for always-auth config setting command"""
            if any('always-auth' in arg for arg in command):
                raise subprocess.CalledProcessError(returncode=1, cmd=command)

            return mock.DEFAULT

        self.subprocess_utils.run.side_effect = side_effect
        self.test_subject.login()
        expected_calls = [
            mock.call(command, capture_output=True, check=True)
            for command in self.commands
        ]
        self.subprocess_utils.run.assert_has_calls(
            expected_calls, any_order=True
        )
        mock_write_npmrc.assert_called_once_with(
            self.auth_token_key, self.auth_token, mock.ANY
        )

    def test_get_scope(self):
        expected_value = f'@{self.namespace}'
        scope = self.test_subject.get_scope(self.namespace)
        self.assertEqual(scope, expected_value)

    def test_get_scope_none_namespace(self):
        expected_value = None
        scope = self.test_subject.get_scope(None)
        self.assertEqual(scope, expected_value)

    def test_get_scope_invalid_name(self):
        with self.assertRaises(ValueError):
            self.test_subject.get_scope(f'.{self.namespace}')

    def test_get_scope_invalid_trailing_characters(self):
        # The namespace has to be valid in its entirety and not just at
        # its start, otherwise invalid scope names are handed off to
        # ``npm config set``.
        invalid_namespaces = [
            f'{self.namespace} with spaces',
            f'{self.namespace}!!!',
            f'{self.namespace}/../..',
            f'{self.namespace}\nregistry=http://example.com',
        ]
        for namespace in invalid_namespaces:
            with self.subTest(namespace=namespace):
                with self.assertRaises(ValueError):
                    self.test_subject.get_scope(namespace)

    def test_get_scope_without_prefix(self):
        expected_value = f'@{self.namespace}'
        scope = self.test_subject.get_scope(f'@{self.namespace}')
        self.assertEqual(scope, expected_value)

    def test_get_commands(self):
        commands = self.test_subject.get_commands(
            self.endpoint, self.auth_token
        )
        self.assertCountEqual(commands, self.commands)
        for cmd in commands:
            self.assertNotIn(self.auth_token, cmd)

    def test_get_commands_with_scope(self):
        commands = self.test_subject.get_commands(
            self.endpoint, self.auth_token, scope=self.namespace
        )
        expected = list(self.commands)
        expected[0][3] = f'{self.namespace}:registry'
        self.assertCountEqual(commands, expected)

    def test_login_dry_run(self):
        self.test_subject.login(dry_run=True)
        self.subprocess_utils.assert_not_called()



class TestNpmWriteNpmrcValue(unittest.TestCase):

    def setUp(self):
        self.domain = 'domain'
        self.domain_owner = 'domain-owner'
        self.package_format = 'npm'
        self.repository = 'repository'
        self.auth_token = 'auth-token'
        self.expiration = (datetime.now(tzlocal()) + relativedelta(hours=10)
                           + relativedelta(minutes=9)).replace(microsecond=0)
        self.endpoint = 'https://{domain}-{domainOwner}.codeartifact.aws.' \
            'a2z.com/{format}/{repository}/'.format(
                domain=self.domain,
                domainOwner=self.domain_owner,
                format=self.package_format,
                repository=self.repository
            )

        repo_uri = urlparse.urlsplit(self.endpoint)
        self.auth_token_key = '//{}{}:_authToken'.format(
            repo_uri.netloc, repo_uri.path
        )

        self.file_creator = FileCreator()
        self.test_npmrc_path = self.file_creator.full_path('.npmrc')

        self.subprocess_utils = mock.Mock()

        self.test_subject = NpmLogin(
            self.auth_token, self.expiration, self.endpoint,
            self.domain, self.repository, self.subprocess_utils
        )

    def tearDown(self):
        self.file_creator.remove_all()

    def test_creates_new_file_when_not_exists(self):
        npmrc_path = os.path.join(self.file_creator.rootdir, 'subdir', '.npmrc')
        self.test_subject._write_npmrc_value(
            self.auth_token_key, self.auth_token, npmrc_path)
        self.assertTrue(os.path.isfile(npmrc_path))
        with open(npmrc_path, 'r') as f:
            contents = f.read()
        self.assertEqual(
            contents, '{}={}\n'.format(self.auth_token_key, self.auth_token))

    @skip_if_windows("Unix file permissions are not supported on Windows.")
    @mock.patch.object(NpmLogin, 'get_npmrc_path')
    def test_login_sets_secure_permissions_on_new_file(self, mock_path):
        npmrc_path = os.path.join(self.file_creator.rootdir, 'newdir', '.npmrc')
        mock_path.return_value = npmrc_path
        self.test_subject.login()
        file_mode = os.stat(npmrc_path).st_mode
        self.assertEqual(stat.S_IMODE(file_mode), 0o600)

    def test_appends_to_existing_file_without_key(self):
        self.file_creator.create_file(
            '.npmrc', 'registry=https://example.com/\n')
        self.test_subject._write_npmrc_value(self.auth_token_key, self.auth_token, self.test_npmrc_path)
        with open(self.test_npmrc_path, 'r') as f:
            contents = f.read()
        self.assertIn('registry=https://example.com/', contents)
        self.assertIn('{}={}'.format(self.auth_token_key, self.auth_token),
                      contents)

    def test_replaces_existing_key(self):
        self.file_creator.create_file(
            '.npmrc',
            'registry=https://example.com/\n'
            '{}=old-token\n'.format(self.auth_token_key) +
            '//host/path/:always-auth=true\n'
        )
        self.test_subject._write_npmrc_value(self.auth_token_key, 'new-token', self.test_npmrc_path)
        with open(self.test_npmrc_path, 'r') as f:
            contents = f.read()
        self.assertIn('{}=new-token'.format(self.auth_token_key), contents)
        self.assertNotIn('old-token', contents)
        self.assertIn('registry=https://example.com/', contents)
        self.assertIn('//host/path/:always-auth=true', contents)

    def test_preserves_other_entries(self):
        self.file_creator.create_file(
            '.npmrc',
            '//other-host/path/:_authToken=other-token\n'
            '{}=old-token\n'.format(self.auth_token_key)
        )
        self.test_subject._write_npmrc_value(self.auth_token_key, 'new-token', self.test_npmrc_path)
        with open(self.test_npmrc_path, 'r') as f:
            contents = f.read()
        self.assertIn('//other-host/path/:_authToken=other-token', contents)
        self.assertIn('{}=new-token'.format(self.auth_token_key), contents)
        self.assertNotIn('old-token', contents)

    @skip_if_windows("Unix file permissions are not supported on Windows.")
    @mock.patch.object(NpmLogin, 'get_npmrc_path')
    def test_login_adjusts_permissions_on_preexisting_file(self, mock_path):
        mock_path.return_value = self.test_npmrc_path
        self.file_creator.create_file('.npmrc', 'registry=https://example.com/\n')
        os.chmod(self.test_npmrc_path, 0o644)
        self.test_subject.login()
        file_mode = os.stat(self.test_npmrc_path).st_mode
        self.assertEqual(stat.S_IMODE(file_mode), 0o600)

    def test_handles_file_without_trailing_newline(self):
        self.file_creator.create_file('.npmrc', 'registry=https://example.com/')
        self.test_subject._write_npmrc_value(self.auth_token_key, self.auth_token, self.test_npmrc_path)
        with open(self.test_npmrc_path, 'r') as f:
            contents = f.read()
        lines = contents.strip().split('\n')
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], 'registry=https://example.com/')
        self.assertEqual(
            lines[1], '{}={}'.format(self.auth_token_key, self.auth_token))

    @mock.patch.object(NpmLogin, 'get_npmrc_path')
    def test_token_not_passed_to_subprocess(self, mock_path):
        mock_path.return_value = self.test_npmrc_path
        self.file_creator.create_file('.npmrc', '')
        self.test_subject.login()
        for call in self.subprocess_utils.run.call_args_list:
            command = call[0][0] if call[0] else call[1].get('command', [])
            self.assertNotIn(self.auth_token, ' '.join(command))

    @mock.patch.object(NpmLogin, 'get_npmrc_path')
    def test_dry_run_does_not_write_file(self, mock_path):
        npmrc_path = os.path.join(self.file_creator.rootdir, 'noexist', '.npmrc')
        mock_path.return_value = npmrc_path
        self.test_subject.login(dry_run=True)
        self.assertFalse(os.path.exists(npmrc_path))

    def test_special_chars_in_key_escaped(self):
        npmrc_path = os.path.join(self.file_creator.rootdir, 'esctest', '.npmrc')
        self.test_subject._write_npmrc_value(
            self.auth_token_key, self.auth_token, npmrc_path)
        with open(npmrc_path, 'r') as f:
            contents = f.read()
        self.assertEqual(
            contents, '{}={}\n'.format(self.auth_token_key, self.auth_token))

    def test_get_npmrc_path_respects_env_var(self):
        custom_path = '/tmp/custom/.npmrc'
        with mock.patch.dict(os.environ, {'NPM_CONFIG_USERCONFIG': custom_path}):
            result = NpmLogin.get_npmrc_path()
        self.assertEqual(result, custom_path)

    def test_get_npmrc_path_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('NPM_CONFIG_USERCONFIG', None)
            result = NpmLogin.get_npmrc_path()
        expected = os.path.join(os.path.expanduser('~'), '.npmrc')
        self.assertEqual(result, expected)

    def test_atomic_write_preserves_original_on_replace_failure(self):
        self.file_creator.create_file(
            '.npmrc', 'registry=https://example.com/\n')
        original_content = 'registry=https://example.com/\n'
        with mock.patch('os.replace', side_effect=OSError('replace failed')):
            with self.assertRaises(OSError):
                self.test_subject._write_npmrc_value(
                    self.auth_token_key, self.auth_token, self.test_npmrc_path)
        with open(self.test_npmrc_path, 'r') as f:
            contents = f.read()
        self.assertEqual(contents, original_content)

    @mock.patch('os.unlink')
    def test_atomic_write_cleans_up_tmp_on_replace_failure(self, mock_unlink):
        self.file_creator.create_file(
            '.npmrc', 'registry=https://example.com/\n')
        with mock.patch('os.replace', side_effect=OSError('replace failed')):
            with self.assertRaises(OSError):
                self.test_subject._write_npmrc_value(
                    self.auth_token_key, self.auth_token, self.test_npmrc_path)
        mock_unlink.assert_called_once()
        unlinked_path = mock_unlink.call_args[0][0]
        self.assertIn('.npmrc.tmp.', unlinked_path)

    def test_atomic_write_no_tmp_file_left_after_success(self):
        self.file_creator.create_file(
            '.npmrc', 'registry=https://example.com/\n')
        dirname = os.path.dirname(self.test_npmrc_path)
        self.test_subject._write_npmrc_value(
            self.auth_token_key, self.auth_token, self.test_npmrc_path)
        tmp_files = [f for f in os.listdir(dirname)
                     if '.npmrc.tmp.' in f]
        self.assertEqual(tmp_files, [])

    @skip_if_windows("Unix file permissions are not supported on Windows.")
    def test_create_tmp_file_returns_fd_and_path(self):
        dirname = self.file_creator.rootdir
        fd, tmp_path = self.test_subject._create_tmp_file(dirname)
        try:
            self.assertTrue(tmp_path.startswith(dirname))
            self.assertIn('.npmrc.tmp.', tmp_path)
            file_mode = os.stat(tmp_path).st_mode
            self.assertEqual(stat.S_IMODE(file_mode), 0o600)
        finally:
            os.close(fd)
            os.unlink(tmp_path)

    def test_create_tmp_file_retries_on_collision(self):
        dirname = self.file_creator.rootdir
        fd1, path1 = self.test_subject._create_tmp_file(dirname)
        fd2, path2 = self.test_subject._create_tmp_file(dirname)
        try:
            self.assertNotEqual(path1, path2)
        finally:
            os.close(fd1)
            os.close(fd2)
            os.unlink(path1)
            os.unlink(path2)

    def test_create_tmp_file_raises_after_max_retries(self):
        with mock.patch('os.open', side_effect=FileExistsError('exists')):
            with self.assertRaises(RuntimeError):
                self.test_subject._create_tmp_file(self.file_creator.rootdir)


class TestPipLogin(unittest.TestCase):
    PIP_INDEX_URL_FMT = PipLogin.PIP_INDEX_URL_FMT

    def setUp(self):
        self.domain = 'domain'
        self.domain_owner = 'domain-owner'
        self.package_format = 'pip'
        self.repository = 'repository'
        self.auth_token = 'auth-token'
        self.expiration = (
            datetime.now(tzlocal())
            + relativedelta(years=1)
            + relativedelta(months=9)
        ).replace(microsecond=0)
        self.endpoint = (
            f'https://{self.domain}-{self.domain_owner}.codeartifact.aws.'
            f'a2z.com/{self.package_format}/{self.repository}/'
        )

        repo_uri = urlsplit(self.endpoint)
        self.pip_index_url = self.PIP_INDEX_URL_FMT.format(
            scheme=repo_uri.scheme,
            auth_token=self.auth_token,
            netloc=repo_uri.netloc,
            path=repo_uri.path,
        )

        self.subprocess_utils = mock.Mock()

        self.test_subject = PipLogin(
            self.auth_token,
            self.expiration,
            self.endpoint,
            self.domain,
            self.repository,
            self.subprocess_utils,
        )

    def test_get_commands(self):
        expected_commands = [
            ['pip', 'config', 'set', 'global.index-url', self.pip_index_url]
        ]
        commands = self.test_subject.get_commands(
            self.endpoint, self.auth_token
        )
        self.assertCountEqual(commands, expected_commands)

    def test_login(self):
        self.test_subject.login()
        self.subprocess_utils.run.assert_called_once_with(
            ['pip', 'config', 'set', 'global.index-url', self.pip_index_url],
            capture_output=True,
            check=True,
        )

    def test_login_dry_run(self):
        self.test_subject.login(dry_run=True)
        self.subprocess_utils.run.assert_not_called()


class TestTwineLogin(unittest.TestCase):
    DEFAULT_PYPI_RC_FMT = TwineLogin.DEFAULT_PYPI_RC_FMT

    def setUp(self):
        self.file_creator = FileCreator()
        self.domain = 'domain'
        self.domain_owner = 'domain-owner'
        self.package_format = 'pip'
        self.repository = 'repository'
        self.auth_token = 'auth-token'
        self.expiration = (
            datetime.now(tzlocal())
            + relativedelta(years=1)
            + relativedelta(months=9)
        ).replace(microsecond=0)
        self.endpoint = (
            f'https://{self.domain}-{self.domain_owner}.codeartifact.aws.'
            f'a2z.com/{self.package_format}/{self.repository}/'
        )
        self.default_pypi_rc = self.DEFAULT_PYPI_RC_FMT.format(
            repository_endpoint=self.endpoint, auth_token=self.auth_token
        )
        self.subprocess_utils = mock.Mock()
        self.test_pypi_rc_path = self.file_creator.full_path('pypirc')
        if not os.path.isdir(os.path.dirname(self.test_pypi_rc_path)):
            os.makedirs(os.path.dirname(self.test_pypi_rc_path))

        self.test_subject = TwineLogin(
            self.auth_token,
            self.expiration,
            self.endpoint,
            self.domain,
            self.repository,
            self.subprocess_utils,
            self.test_pypi_rc_path,
        )

    def tearDown(self):
        self.file_creator.remove_all()

    def _assert_pypi_rc_has_expected_content(
        self, pypi_rc_str, server, repo_url=None, username=None, password=None
    ):
        pypi_rc = RawConfigParser()
        pypi_rc.read_string(pypi_rc_str)

        self.assertIn('distutils', pypi_rc.sections())
        self.assertIn('index-servers', pypi_rc.options('distutils'))
        index_servers = pypi_rc.get('distutils', 'index-servers')
        index_servers = [
            index_server.strip()
            for index_server in index_servers.split('\n')
            if index_server.strip() != ''
        ]
        self.assertIn(server, index_servers)

        if repo_url or username or password:
            self.assertIn(server, pypi_rc.sections())

        if repo_url:
            self.assertIn('repository', pypi_rc.options(server))
            self.assertEqual(pypi_rc.get(server, 'repository'), repo_url)

        if username:
            self.assertIn('username', pypi_rc.options(server))
            self.assertEqual(pypi_rc.get(server, 'username'), username)

        if password:
            self.assertIn('password', pypi_rc.options(server))
            self.assertEqual(pypi_rc.get(server, 'password'), password)

    def test_get_pypi_rc_path(self):
        self.assertEqual(
            TwineLogin.get_pypi_rc_path(),
            os.path.join(os.path.expanduser("~"), ".pypirc"),
        )

    def test_login_pypi_rc_not_found_defaults_set(self):
        self.test_subject.login()

        with open(self.test_pypi_rc_path) as f:
            test_pypi_rc_str = f.read()

        self._assert_pypi_rc_has_expected_content(
            pypi_rc_str=test_pypi_rc_str,
            server='codeartifact',
            repo_url=self.endpoint,
            username='aws',
            password=self.auth_token,
        )

    def test_login_dry_run(self):
        self.test_subject.login(dry_run=True)
        self.subprocess_utils.run.assert_not_called()
        self.assertFalse(os.path.exists(self.test_pypi_rc_path))

    def test_login_existing_pypi_rc_not_clobbered(self):
        existing_pypi_rc = '''\
[distutils]
index-servers=
    pypi
    test

[pypi]
repository: http://www.python.org/pypi/
username: monty
password: JgCXIr5xGG

[test]
repository: http://example.com/test/
username: testusername
password: testpassword
'''

        with open(self.test_pypi_rc_path, 'w+') as f:
            f.write(existing_pypi_rc)

        self.test_subject.login()

        with open(self.test_pypi_rc_path) as f:
            test_pypi_rc_str = f.read()

        self._assert_pypi_rc_has_expected_content(
            pypi_rc_str=test_pypi_rc_str,
            server='codeartifact',
            repo_url=self.endpoint,
            username='aws',
            password=self.auth_token,
        )

        self._assert_pypi_rc_has_expected_content(
            pypi_rc_str=test_pypi_rc_str,
            server='pypi',
            repo_url='http://www.python.org/pypi/',
            username='monty',
            password='JgCXIr5xGG',
        )

        self._assert_pypi_rc_has_expected_content(
            pypi_rc_str=test_pypi_rc_str,
            server='test',
            repo_url='http://example.com/test/',
            username='testusername',
            password='testpassword',
        )

    def test_login_existing_pypi_rc_with_codeartifact_not_clobbered(self):
        existing_pypi_rc = '''\
[distutils]
index-servers=
    pypi
    codeartifact

[pypi]
repository: http://www.python.org/pypi/
username: monty
password: JgCXIr5xGG

[codeartifact]
repository: https://test-testOwner.codeartifact.aws.a2z.com/pypi/testRepo/
username: aws
password: expired_token
'''

        with open(self.test_pypi_rc_path, 'w+') as f:
            f.write(existing_pypi_rc)

        self.test_subject.login()

        with open(self.test_pypi_rc_path) as f:
            test_pypi_rc_str = f.read()

        self._assert_pypi_rc_has_expected_content(
            pypi_rc_str=test_pypi_rc_str,
            server='codeartifact',
            repo_url=self.endpoint,
            username='aws',
            password=self.auth_token,
        )

        self._assert_pypi_rc_has_expected_content(
            pypi_rc_str=test_pypi_rc_str,
            server='pypi',
            repo_url='http://www.python.org/pypi/',
            username='monty',
            password='JgCXIr5xGG',
        )

    @skip_if_windows("Unix file permissions are not supported on Windows.")
    def test_login_sets_secure_permissions_on_new_file(self):
        self.assertFalse(os.path.exists(self.test_pypi_rc_path))
        self.test_subject.login()
        file_mode = os.stat(self.test_pypi_rc_path).st_mode
        self.assertEqual(stat.S_IMODE(file_mode), 0o600)

    @skip_if_windows("Unix file permissions are not supported on Windows.")
    def test_login_adjusts_permissions_on_preexisting_file(self):
        existing_pypi_rc = '''\
[distutils]
index-servers=
    pypi

[pypi]
repository: http://www.python.org/pypi/
username: test
password: JgCXIr5xGG
'''
        with open(self.test_pypi_rc_path, 'w') as f:
            f.write(existing_pypi_rc)
        os.chmod(self.test_pypi_rc_path, 0o644)
        self.test_subject.login()
        file_mode = os.stat(self.test_pypi_rc_path).st_mode
        self.assertEqual(stat.S_IMODE(file_mode), 0o600)

    @skip_if_windows("Unix file permissions are not supported on Windows.")
    @mock.patch('sys.stderr')
    @mock.patch('os.chmod', side_effect=OSError(
        errno.EPERM, 'Operation not permitted'
    ))
    def test_login_writes_error_when_chmod_fails(self, mock_chmod, mock_stderr):
        self.test_subject.login()
        mock_stderr.write.assert_any_call(
            'Unable to set file permissions for %s: '
            '[Errno 1] Operation not permitted%s'
            % (self.test_pypi_rc_path, os.linesep)
        )

    def test_login_existing_invalid_pypi_rc_error(self):
        # This is an invalid pypirc as the list of servers are expected under
        # an 'index-servers' option instead of 'servers'.
        existing_pypi_rc = '''\
[distutils]
servers=
    pypi

[pypi]
repository: http://www.python.org/pypi/
username: monty
password: JgCXIr5xGG
'''

        with open(self.test_pypi_rc_path, 'w+') as f:
            f.write(existing_pypi_rc)

        with open(self.test_pypi_rc_path) as f:
            original_content = f.read()

        with self.assertRaises(Exception):
            self.test_subject.login()

        # We should just leave the pypirc untouched when it's invalid.
        with open(self.test_pypi_rc_path) as f:
            self.assertEqual(f.read(), original_content)


class TestRelativeExpirationTime(unittest.TestCase):
    def test_with_years_months_days(self):
        remaining = relativedelta(years=1, months=9)
        message = get_relative_expiration_time(remaining)
        self.assertEqual(message, '1 year and 9 months')

    def test_with_years_months(self):
        remaining = relativedelta(
            years=1, months=8, days=30, hours=23, minutes=59, seconds=30
        )
        message = get_relative_expiration_time(remaining)
        self.assertEqual(message, '1 year and 8 months')

    def test_with_years_month(self):
        remaining = relativedelta(
            years=3, days=30, hours=23, minutes=59, seconds=30
        )
        message = get_relative_expiration_time(remaining)
        self.assertEqual(message, '3 years')

    def test_with_years_days(self):
        remaining = relativedelta(years=1, days=9)
        message = get_relative_expiration_time(remaining)
        self.assertEqual(message, '1 year')

    def test_with_year(self):
        remaining = relativedelta(months=11, days=30)
        message = get_relative_expiration_time(remaining)
        self.assertEqual(message, '11 months and 30 days')

    def test_with_years(self):
        remaining = relativedelta(years=1, months=11)
        message = get_relative_expiration_time(remaining)
        self.assertEqual(message, '1 year and 11 months')

    def test_with_years_days_hours_minutes(self):
        remaining = relativedelta(years=2, days=7, hours=11, minutes=44)
        message = get_relative_expiration_time(remaining)
        self.assertEqual(message, '2 years')

    def test_with_days_minutes(self):
        remaining = relativedelta(days=1, minutes=44)
        message = get_relative_expiration_time(remaining)
        self.assertEqual(message, '1 day')

    def test_with_day(self):
        remaining = relativedelta(days=1)
        message = get_relative_expiration_time(remaining)
        self.assertEqual(message, '1 day')

    def test_with_hour(self):
        self.expiration = (
            datetime.now(tzlocal()) + relativedelta(hours=1)
        ).replace(microsecond=0)
        remaining = relativedelta(
            self.expiration, datetime.now(tzutc())
        ) + relativedelta(seconds=30)
        message = get_relative_expiration_time(remaining)
        self.assertEqual(message, '1 hour')

    def test_with_minutes_seconds(self):
        remaining = relativedelta(hours=1)
        message = get_relative_expiration_time(remaining)
        self.assertEqual(message, '1 hour')

    def test_with_full_time(self):
        remaining = relativedelta(
            years=2, months=3, days=7, hours=11, minutes=44
        )
        message = get_relative_expiration_time(remaining)
        self.assertEqual(message, '2 years and 3 months')
