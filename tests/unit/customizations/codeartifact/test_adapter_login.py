import errno
import os

from datetime import datetime
from dateutil.tz import tzlocal, tzutc
from dateutil.relativedelta import relativedelta

from awscli.testutils import unittest, mock, FileCreator
from awscli.compat import urlparse, RawConfigParser, StringIO
from awscli.customizations.codeartifact.login import (
    BaseLogin, NpmLogin, PipLogin, TwineLogin,
    get_relative_expiration_time
)


class TestBaseLogin(unittest.TestCase):
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

        self.subprocess_utils = mock.Mock()

        self.test_subject = BaseLogin(
            self.auth_token, self.expiration,
            self.endpoint, self.subprocess_utils
        )

    def test_login(self):
        with self.assertRaises(NotImplementedError):
            self.test_subject.login()

    def test_get_commands(self):
        with self.assertRaises(NotImplementedError):
            self.test_subject.get_commands(
                self.endpoint, self.auth_token
            )

    def test_run_commands_nonexistent_command(self):
        self.subprocess_utils.check_call.side_effect = OSError(
            errno.ENOENT, 'not found error'
        )
        tool = 'NotSupported'
        with self.assertRaisesRegexp(ValueError, '%s was not found.' % tool):
            self.test_subject._run_commands(tool, ['echo', tool])

    def test_run_commands_unhandled_error(self):
        self.subprocess_utils.check_call.side_effect = OSError(
            errno.ENOSYS, 'unhandled error'
        )
        tool = 'NotSupported'
        with self.assertRaisesRegexp(OSError, 'unhandled error'):
            self.test_subject._run_commands(tool, ['echo', tool])


class TestNpmLogin(unittest.TestCase):

    NPM_CMD = NpmLogin.NPM_CMD

    def setUp(self):
        self.domain = 'domain'
        self.domain_owner = 'domain-owner'
        self.package_format = 'npm'
        self.repository = 'repository'
        self.auth_token = 'auth-token'
        self.namespace = 'namespace'
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
        always_auth_config = '//{}{}:always-auth'.format(
            repo_uri.netloc, repo_uri.path
        )
        auth_token_config = '//{}{}:_authToken'.format(
            repo_uri.netloc, repo_uri.path
        )
        self.commands = []
        self.commands.append([
            self.NPM_CMD, 'config', 'set', 'registry', self.endpoint
        ])
        self.commands.append(
            [self.NPM_CMD, 'config', 'set', always_auth_config, 'true']
        )
        self.commands.append(
            [self.NPM_CMD, 'config', 'set', auth_token_config, self.auth_token]
        )

        self.subprocess_utils = mock.Mock()

        self.test_subject = NpmLogin(
            self.auth_token, self.expiration,
            self.endpoint, self.subprocess_utils
        )

    def test_login(self):
        self.test_subject.login()
        expected_calls = [
            mock.call(
                command,
                stdout=self.subprocess_utils.PIPE,
                stderr=self.subprocess_utils.PIPE,
            ) for command in self.commands
        ]
        self.subprocess_utils.check_call.assert_has_calls(
            expected_calls, any_order=True
        )

    def test_get_scope(self):
        expected_value = '@{}'.format(self.namespace)
        scope = self.test_subject.get_scope(self.namespace)
        self.assertEqual(scope, expected_value)

    def test_get_scope_none_namespace(self):
        expected_value = None
        scope = self.test_subject.get_scope(None)
        self.assertEqual(scope, expected_value)

    def test_get_scope_invalid_name(self):
        with self.assertRaises(ValueError):
            self.test_subject.get_scope('.{}'.format(self.namespace))

    def test_get_scope_without_prefix(self):
        expected_value = '@{}'.format(self.namespace)
        scope = self.test_subject.get_scope('@{}'.format(self.namespace))
        self.assertEqual(scope, expected_value)

    def test_get_commands(self):
        commands = self.test_subject.get_commands(
            self.endpoint, self.auth_token
        )
        self.assertCountEqual(commands, self.commands)

    def test_get_commands_with_scope(self):
        commands = self.test_subject.get_commands(
            self.endpoint, self.auth_token, scope=self.namespace
        )
        self.commands[0][3] = '{}:registry'.format(self.namespace)
        self.assertCountEqual(commands, self.commands)

    def test_login_dry_run(self):
        self.test_subject.login(dry_run=True)
        self.subprocess_utils.check_call.assert_not_called()


class TestPipLogin(unittest.TestCase):

    PIP_INDEX_URL_FMT = PipLogin.PIP_INDEX_URL_FMT

    def setUp(self):
        self.domain = 'domain'
        self.domain_owner = 'domain-owner'
        self.package_format = 'pip'
        self.repository = 'repository'
        self.auth_token = 'auth-token'
        self.expiration = (datetime.now(tzlocal()) + relativedelta(years=1)
                           + relativedelta(months=9)).replace(microsecond=0)
        self.endpoint = 'https://{domain}-{domainOwner}.codeartifact.aws.' \
            'a2z.com/{format}/{repository}/'.format(
                domain=self.domain,
                domainOwner=self.domain_owner,
                format=self.package_format,
                repository=self.repository
            )

        repo_uri = urlparse.urlsplit(self.endpoint)
        self.pip_index_url = self.PIP_INDEX_URL_FMT.format(
            scheme=repo_uri.scheme,
            auth_token=self.auth_token,
            netloc=repo_uri.netloc,
            path=repo_uri.path
        )

        self.subprocess_utils = mock.Mock()

        self.test_subject = PipLogin(
            self.auth_token, self.expiration,
            self.endpoint, self.subprocess_utils
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
        self.subprocess_utils.check_call.assert_called_once_with(
            ['pip', 'config', 'set', 'global.index-url', self.pip_index_url],
            stdout=self.subprocess_utils.PIPE,
            stderr=self.subprocess_utils.PIPE,
        )

    def test_login_dry_run(self):
        self.test_subject.login(dry_run=True)
        self.subprocess_utils.check_call.assert_not_called()


class TestTwineLogin(unittest.TestCase):

    DEFAULT_PYPI_RC_FMT = TwineLogin.DEFAULT_PYPI_RC_FMT

    def setUp(self):
        self.file_creator = FileCreator()
        self.domain = 'domain'
        self.domain_owner = 'domain-owner'
        self.package_format = 'pip'
        self.repository = 'repository'
        self.auth_token = 'auth-token'
        self.expiration = (datetime.now(tzlocal()) + relativedelta(years=1)
                           + relativedelta(months=9)).replace(microsecond=0)
        self.endpoint = 'https://{domain}-{domainOwner}.codeartifact.aws.' \
            'a2z.com/{format}/{repository}/'.format(
                domain=self.domain,
                domainOwner=self.domain_owner,
                format=self.package_format,
                repository=self.repository
            )
        self.default_pypi_rc = self.DEFAULT_PYPI_RC_FMT.format(
            repository_endpoint=self.endpoint,
            auth_token=self.auth_token
        )
        self.subprocess_utils = mock.Mock()
        self.test_pypi_rc_path = self.file_creator.full_path('pypirc')
        if not os.path.isdir(os.path.dirname(self.test_pypi_rc_path)):
            os.makedirs(os.path.dirname(self.test_pypi_rc_path))

        self.test_subject = TwineLogin(
            self.auth_token,
            self.expiration,
            self.endpoint,
            self.subprocess_utils,
            self.test_pypi_rc_path
        )

    def tearDown(self):
        self.file_creator.remove_all()

    def _assert_pypi_rc_has_expected_content(
        self, pypi_rc_str, server, repo_url=None, username=None, password=None
    ):
        pypi_rc = RawConfigParser()
        pypi_rc.readfp(StringIO(pypi_rc_str))

        self.assertIn('distutils', pypi_rc.sections())
        self.assertIn('index-servers', pypi_rc.options('distutils'))
        index_servers = pypi_rc.get('distutils', 'index-servers')
        index_servers = [
            index_server.strip()
            for index_server
            in index_servers.split('\n')
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
            os.path.join(os.path.expanduser("~"), ".pypirc")
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
            password=self.auth_token
        )

    def test_login_dry_run(self):
        self.test_subject.login(dry_run=True)
        self.subprocess_utils.check_call.assert_not_called()
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
            password=self.auth_token
        )

        self._assert_pypi_rc_has_expected_content(
            pypi_rc_str=test_pypi_rc_str,
            server='pypi',
            repo_url='http://www.python.org/pypi/',
            username='monty',
            password='JgCXIr5xGG'
        )

        self._assert_pypi_rc_has_expected_content(
            pypi_rc_str=test_pypi_rc_str,
            server='test',
            repo_url='http://example.com/test/',
            username='testusername',
            password='testpassword'
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
            password=self.auth_token
        )

        self._assert_pypi_rc_has_expected_content(
            pypi_rc_str=test_pypi_rc_str,
            server='pypi',
            repo_url='http://www.python.org/pypi/',
            username='monty',
            password='JgCXIr5xGG'
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
        remaining = relativedelta(years=1, months=8, days=30, hours=23,
                                  minutes=59, seconds=30)
        message = get_relative_expiration_time(remaining)
        self.assertEqual(message, '1 year and 8 months')

    def test_with_years_month(self):
        remaining = relativedelta(years=3, days=30, hours=23,
                                  minutes=59, seconds=30)
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
        self.expiration = (datetime.now(tzlocal())
                           + relativedelta(hours=1)).replace(microsecond=0)
        remaining = relativedelta(
            self.expiration, datetime.now(tzutc())) + relativedelta(seconds=30)
        message = get_relative_expiration_time(remaining)
        self.assertEqual(message, '1 hour')

    def test_with_minutes_seconds(self):
        remaining = relativedelta(hours=1)
        message = get_relative_expiration_time(remaining)
        self.assertEqual(message, '1 hour')

    def test_with_full_time(self):
        remaining = relativedelta(
            years=2, months=3, days=7, hours=11, minutes=44)
        message = get_relative_expiration_time(remaining)
        self.assertEqual(message, '2 years and 3 months')
