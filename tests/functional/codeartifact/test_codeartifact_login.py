import os
import platform
import subprocess
import time

from datetime import datetime
from dateutil.tz import tzlocal
from dateutil.relativedelta import relativedelta
from botocore.utils import parse_timestamp

from awscli.testutils import BaseAWSCommandParamsTest, FileCreator, mock
from awscli.compat import urlparse, StringIO, RawConfigParser
from awscli.customizations.codeartifact.login import CodeArtifactLogin


class TestCodeArtifactLogin(BaseAWSCommandParamsTest):

    prefix = 'codeartifact login'

    def setUp(self):
        super(TestCodeArtifactLogin, self).setUp()

        self.file_creator = FileCreator()
        self.test_pypi_rc_path = self.file_creator.full_path('pypirc')
        if not os.path.isdir(os.path.dirname(self.test_pypi_rc_path)):
            os.makedirs(os.path.dirname(self.test_pypi_rc_path))

        self.domain = 'domain'
        self.domain_owner = 'domain-owner'
        self.repository = 'repository'
        self.auth_token = 'auth-token'
        self.namespace = 'namespace'
        self.duration = 3600
        self.expiration = time.time() + self.duration
        self.expiration_as_datetime = parse_timestamp(self.expiration)

        self.pypi_rc_path_patch = mock.patch(
            'awscli.customizations.codeartifact.login.TwineLogin'
            '.get_pypi_rc_path'
        )
        self.pypi_rc_path_mock = self.pypi_rc_path_patch.start()
        self.pypi_rc_path_mock.return_value = self.test_pypi_rc_path

        self.subprocess_patch = mock.patch('subprocess.check_call')
        self.subprocess_mock = self.subprocess_patch.start()

    def tearDown(self):
        super(TestCodeArtifactLogin, self).tearDown()
        self.pypi_rc_path_patch.stop()
        self.subprocess_patch.stop()
        self.file_creator.remove_all()

    def _setup_cmd(self, tool,
                   include_domain_owner=False, dry_run=False,
                   include_duration_seconds=False,
                   include_namespace=False):
        package_format = CodeArtifactLogin.TOOL_MAP[tool]['package_format']
        self.endpoint = 'https://{domain}-{domainOwner}.codeartifact.aws.' \
            'a2z.com/{format}/{repository}/'.format(
                domain=self.domain,
                domainOwner=self.domain_owner,
                format=package_format,
                repository=self.repository
            )

        cmdline = self.prefix
        cmdline += ' --domain %s' % self.domain
        cmdline += ' --repository %s' % self.repository
        cmdline += ' --tool %s' % tool

        if include_domain_owner:
            cmdline += ' --domain-owner %s' % self.domain_owner

        if dry_run:
            cmdline += ' --dry-run'

        if include_duration_seconds:
            cmdline += ' --duration-seconds %s' % self.duration

        if include_namespace:
            cmdline += ' --namespace %s' % self.namespace

        # Responses from calls to services.
        self.parsed_responses = [
            {"authorizationToken": self.auth_token,
                "expiration": self.expiration},  # GetAuthorizationToken
            {"repositoryEndpoint": self.endpoint},  # GetRepositoryEndpoint
        ]

        return cmdline

    def _get_npm_commands(self, **kwargs):
        npm_cmd = 'npm.cmd' \
            if platform.system().lower() == 'windows' else 'npm'

        repo_uri = urlparse.urlsplit(self.endpoint)
        always_auth_config = '//{}{}:always-auth'.format(
            repo_uri.netloc, repo_uri.path
        )
        auth_token_config = '//{}{}:_authToken'.format(
            repo_uri.netloc, repo_uri.path
        )

        scope = kwargs.get('scope')
        registry = '{}:registry'.format(scope) if scope else 'registry'

        commands = []
        commands.append(
            [npm_cmd, 'config', 'set', registry, self.endpoint]
        )
        commands.append(
            [npm_cmd, 'config', 'set', always_auth_config, 'true']
        )
        commands.append(
            [npm_cmd, 'config', 'set', auth_token_config, self.auth_token]
        )

        return commands

    def _get_pip_commands(self):
        pip_index_url_fmt = '{scheme}://aws:{auth_token}@{netloc}{path}simple/'
        repo_uri = urlparse.urlsplit(self.endpoint)
        pip_index_url = pip_index_url_fmt.format(
            scheme=repo_uri.scheme,
            auth_token=self.auth_token,
            netloc=repo_uri.netloc,
            path=repo_uri.path
        )

        return [['pip', 'config', 'set', 'global.index-url', pip_index_url]]

    def _get_twine_commands(self):
        default_pypi_rc_fmt = '''\
[distutils]
index-servers=
    pypi
    codeartifact

[codeartifact]
repository: {repository_endpoint}
username: aws
password: {auth_token}'''
        default_pypi_rc = default_pypi_rc_fmt.format(
            repository_endpoint=self.endpoint,
            auth_token=self.auth_token
        )

        pypi_rc = RawConfigParser()
        if os.path.exists(self.test_pypi_rc_path):
            pypi_rc.read(self.test_pypi_rc_path)
            index_servers = pypi_rc.get('distutils', 'index-servers')
            servers = [
                server.strip()
                for server in index_servers.split('\n')
                if server.strip() != ''
            ]

            if 'codeartifact' not in servers:
                servers.append('codeartifact')
                pypi_rc.set(
                    'distutils', 'index-servers', '\n' + '\n'.join(servers)
                )

            if 'codeartifact' not in pypi_rc.sections():
                pypi_rc.add_section('codeartifact')

            pypi_rc.set('codeartifact', 'repository', self.endpoint)
            pypi_rc.set('codeartifact', 'username', 'aws')
            pypi_rc.set('codeartifact', 'password', self.auth_token)
        else:
            pypi_rc.readfp(StringIO(default_pypi_rc))

        pypi_rc_stream = StringIO()
        pypi_rc.write(pypi_rc_stream)
        pypi_rc_str = pypi_rc_stream.getvalue()
        pypi_rc_stream.close()

        return pypi_rc_str

    def _assert_expiration_printed_to_stdout(self, stdout):
        self.assertEqual(
            self.expiration_as_datetime.strftime(
                "%Y-%m-%d %H:%M:%S"), stdout.split("at ")[1][0:19]
        )

    def _assert_operations_called(
        self, package_format,
            include_domain_owner=False, include_duration_seconds=False
    ):
        self.assertEqual(len(self.operations_called), 2)

        get_auth_token_kwargs = {
            'domain': self.domain
        }
        get_repo_endpoint_kwargs = {
            'domain': self.domain,
            'repository': self.repository,
            'format': package_format
        }

        if include_domain_owner:
            get_auth_token_kwargs['domainOwner'] = self.domain_owner
            get_repo_endpoint_kwargs['domainOwner'] = self.domain_owner

        if include_duration_seconds:
            get_auth_token_kwargs['durationSeconds'] = self.duration

        self.assertEqual(
            self.operations_called[0][0].name, 'GetAuthorizationToken'
        )
        self.assertEqual(
            self.operations_called[0][1],
            get_auth_token_kwargs
        )

        self.assertEqual(
            self.operations_called[1][0].name, 'GetRepositoryEndpoint'
        )
        self.assertEqual(
            self.operations_called[1][1],
            get_repo_endpoint_kwargs
        )

    def _assert_subprocess_execution(self, commands):
        expected_calls = [
            mock.call(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ) for command in commands
        ]
        self.subprocess_mock.assert_has_calls(
            expected_calls, any_order=True
        )

    def _assert_dry_run_execution(self, commands, stdout):
        self.subprocess_mock.assert_not_called()
        for command in commands:
            self.assertIn(' '.join(command), stdout)

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

    def test_npm_login_without_domain_owner(self):
        cmdline = self._setup_cmd(tool='npm')
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(package_format='npm')
        self._assert_expiration_printed_to_stdout(stdout)
        self._assert_subprocess_execution(self._get_npm_commands())

    def test_npm_login_without_domain_owner_dry_run(self):
        cmdline = self._setup_cmd(tool='npm', dry_run=True)
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(package_format='npm')
        self._assert_dry_run_execution(self._get_npm_commands(), stdout)

    def test_npm_login_with_domain_owner(self):
        cmdline = self._setup_cmd(tool='npm', include_domain_owner=True)
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(
            package_format='npm',
            include_domain_owner=True, include_duration_seconds=False
        )
        self._assert_expiration_printed_to_stdout(stdout)
        self._assert_subprocess_execution(self._get_npm_commands())

    def test_npm_login_with_domain_owner_duration(self):
        cmdline = self._setup_cmd(tool='npm', include_domain_owner=True,
                                  include_duration_seconds=True)
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(
            package_format='npm',
            include_domain_owner=True, include_duration_seconds=True
        )
        self._assert_expiration_printed_to_stdout(stdout)
        self._assert_subprocess_execution(self._get_npm_commands())

    def test_npm_login_with_domain_owner_dry_run(self):
        cmdline = self._setup_cmd(
            tool='npm', include_domain_owner=True, dry_run=True
        )
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(
            package_format='npm', include_domain_owner=True
        )
        self._assert_dry_run_execution(self._get_npm_commands(), stdout)

    def test_npm_login_with_namespace(self):
        cmdline = self._setup_cmd(
            tool='npm', include_namespace=True
        )
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(package_format='npm')
        self._assert_expiration_printed_to_stdout(stdout)
        self._assert_subprocess_execution(
            self._get_npm_commands(scope='@{}'.format(self.namespace))
        )

    def test_npm_login_with_namespace_dry_run(self):
        cmdline = self._setup_cmd(
            tool='npm', include_namespace=True, dry_run=True
        )
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(package_format='npm')
        self._assert_dry_run_execution(self._get_npm_commands(
            scope='@{}'.format(self.namespace)), stdout)

    def test_pip_login_without_domain_owner(self):
        cmdline = self._setup_cmd(tool='pip')
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(
            package_format='pypi'
        )
        self._assert_expiration_printed_to_stdout(stdout)
        self._assert_subprocess_execution(self._get_pip_commands())

    def test_pip_login_without_domain_owner_dry_run(self):
        cmdline = self._setup_cmd(tool='pip', dry_run=True)
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(
            package_format='pypi'
        )
        self._assert_dry_run_execution(self._get_pip_commands(), stdout)

    def test_pip_login_with_domain_owner(self):
        cmdline = self._setup_cmd(tool='pip', include_domain_owner=True)
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(
            package_format='pypi', include_domain_owner=True
        )
        self._assert_expiration_printed_to_stdout(stdout)
        self._assert_subprocess_execution(self._get_pip_commands())

    def test_pip_login_with_domain_owner_duration(self):
        cmdline = self._setup_cmd(tool='pip', include_domain_owner=True,
                                  include_duration_seconds=True)
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(
            package_format='pypi', include_domain_owner=True,
            include_duration_seconds=True
        )
        self._assert_expiration_printed_to_stdout(stdout)
        self._assert_subprocess_execution(self._get_pip_commands())

    def test_pip_login_with_domain_owner_dry_run(self):
        cmdline = self._setup_cmd(
            tool='pip', include_domain_owner=True, dry_run=True
        )
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(
            package_format='pypi', include_domain_owner=True
        )
        self._assert_dry_run_execution(self._get_pip_commands(), stdout)

    def test_pip_login_with_namespace(self):
        cmdline = self._setup_cmd(tool='pip', include_namespace=True)
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=255)
        self._assert_operations_called(
            package_format='pypi'
        )
        self.assertIn('Argument --namespace is not supported for pip', stderr)

    def test_pip_login_with_namespace_dry_run(self):
        cmdline = self._setup_cmd(
            tool='pip', include_namespace=True, dry_run=True)
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=255)
        self._assert_operations_called(
            package_format='pypi'
        )
        self.assertIn('Argument --namespace is not supported for pip', stderr)

    def test_twine_login_without_domain_owner(self):
        cmdline = self._setup_cmd(tool='twine')
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(
            package_format='pypi'
        )
        self._assert_expiration_printed_to_stdout(stdout)
        with open(self.test_pypi_rc_path) as f:
            test_pypi_rc_str = f.read()

        self._assert_pypi_rc_has_expected_content(
            pypi_rc_str=test_pypi_rc_str,
            server='codeartifact',
            repo_url=self.endpoint,
            username='aws',
            password=self.auth_token
        )

    def test_twine_login_without_domain_owner_dry_run(self):
        cmdline = self._setup_cmd(tool='twine', dry_run=True)
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(
            package_format='pypi'
        )
        self.assertFalse(os.path.exists(self.test_pypi_rc_path))
        self._assert_pypi_rc_has_expected_content(
            pypi_rc_str=self._get_twine_commands(),
            server='codeartifact',
            repo_url=self.endpoint,
            username='aws',
            password=self.auth_token
        )

    def test_twine_login_with_domain_owner(self):
        cmdline = self._setup_cmd(tool='twine', include_domain_owner=True)
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(
            package_format='pypi', include_domain_owner=True
        )
        self._assert_expiration_printed_to_stdout(stdout)

        with open(self.test_pypi_rc_path) as f:
            test_pypi_rc_str = f.read()

        self._assert_pypi_rc_has_expected_content(
            pypi_rc_str=test_pypi_rc_str,
            server='codeartifact',
            repo_url=self.endpoint,
            username='aws',
            password=self.auth_token
        )

    def test_twine_login_with_domain_owner_duration(self):
        cmdline = self._setup_cmd(tool='twine', include_domain_owner=True,
                                  include_duration_seconds=True)
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(
            package_format='pypi', include_domain_owner=True,
            include_duration_seconds=True
        )
        self._assert_expiration_printed_to_stdout(stdout)

        with open(self.test_pypi_rc_path) as f:
            test_pypi_rc_str = f.read()

        self._assert_pypi_rc_has_expected_content(
            pypi_rc_str=test_pypi_rc_str,
            server='codeartifact',
            repo_url=self.endpoint,
            username='aws',
            password=self.auth_token
        )

    def test_twine_login_with_domain_owner_dry_run(self):
        cmdline = self._setup_cmd(
            tool='twine', include_domain_owner=True, dry_run=True
        )
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self._assert_operations_called(
            package_format='pypi', include_domain_owner=True
        )
        self.assertFalse(os.path.exists(self.test_pypi_rc_path))
        self._assert_pypi_rc_has_expected_content(
            pypi_rc_str=self._get_twine_commands(),
            server='codeartifact',
            repo_url=self.endpoint,
            username='aws',
            password=self.auth_token
        )

    def test_twine_login_with_namespace(self):
        cmdline = self._setup_cmd(
            tool='twine', include_namespace=True
        )
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=255)
        self._assert_operations_called(
            package_format='pypi'
        )
        self.assertIn(
            'Argument --namespace is not supported for twine', stderr)

    def test_twine_login_with_namespace_dry_run(self):
        cmdline = self._setup_cmd(
            tool='twine', include_namespace=True, dry_run=True
        )
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=255)
        self._assert_operations_called(
            package_format='pypi',
        )
        self.assertFalse(os.path.exists(self.test_pypi_rc_path))
        self.assertIn(
            'Argument --namespace is not supported for twine', stderr)
