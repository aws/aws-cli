import errno
import os
import platform
import sys
import subprocess

from datetime import datetime
from dateutil.tz import tzutc
from dateutil.relativedelta import relativedelta
from botocore.utils import parse_timestamp

from awscli.compat import urlparse, RawConfigParser, StringIO
from awscli.customizations import utils as cli_utils
from awscli.customizations.commands import BasicCommand


def get_relative_expiration_time(remaining):
    values = []
    prev_non_zero_attr = False
    for attr in ["years", "months", "days", "hours", "minutes"]:
        value = getattr(remaining, attr)
        if value > 0:
            if prev_non_zero_attr:
                values.append("and")
            values.append(str(value))
            values.append(attr[:-1] if value == 1 else attr)
        if prev_non_zero_attr:
            break
        prev_non_zero_attr = value > 0

    message = " ".join(values)
    return message


class BaseLogin(object):

    def __init__(self, auth_token,
                 expiration, repository_endpoint, subprocess_utils):
        self.auth_token = auth_token
        self.expiration = expiration
        self.repository_endpoint = repository_endpoint
        self.subprocess_utils = subprocess_utils

    def login(self, dry_run=False):
        raise NotImplementedError('login()')

    def _dry_run_commands(self, tool, commands):
        for command in commands:
            sys.stdout.write(' '.join(command))
            sys.stdout.write(os.linesep)
            sys.stdout.write(os.linesep)

    def _write_success_message(self, tool):
        # add extra 30 seconds make expiration more reasonable
        # for some corner case
        # e.g. 11 hours 59 minutes 31 seconds should output --> 12 hours.
        remaining = relativedelta(
            self.expiration, datetime.now(tzutc())) + relativedelta(seconds=30)
        expiration_message = get_relative_expiration_time(remaining)

        sys.stdout.write('Successfully configured {} to use '
                         'AWS CodeArtifact repository {} '
                         .format(tool, self.repository_endpoint))
        sys.stdout.write(os.linesep)
        sys.stdout.write('Login expires in {} at {}'.format(
            expiration_message, self.expiration))
        sys.stdout.write(os.linesep)

    def _run_commands(self, tool, commands, dry_run=False):
        if dry_run:
            self._dry_run_commands(tool, commands)
            return

        for command in commands:
            try:
                self.subprocess_utils.check_call(
                    command,
                    stdout=self.subprocess_utils.PIPE,
                    stderr=self.subprocess_utils.PIPE,
                )
            except OSError as ex:
                if ex.errno == errno.ENOENT:
                    raise ValueError(
                        '%s was not found. Please verify installation.' % tool
                    )
                raise ex

        self._write_success_message(tool)

    @classmethod
    def get_commands(cls, endpoint, auth_token, **kwargs):
        raise NotImplementedError('get_commands()')


class NpmLogin(BaseLogin):

    # On Windows we need to be explicit about the .cmd file to execute
    # (unless we execute through the shell, i.e. with shell=True).
    NPM_CMD = 'npm.cmd' if platform.system().lower() == 'windows' else 'npm'

    def login(self, dry_run=False):
        commands = self.get_commands(
            self.repository_endpoint, self.auth_token
        )
        self._run_commands('npm', commands, dry_run)

    @classmethod
    def get_commands(cls, endpoint, auth_token, **kwargs):
        commands = []

        # set up the codeartifact repository as the npm registry.
        commands.append(
            [cls.NPM_CMD, 'config', 'set', 'registry', endpoint]
        )

        repo_uri = urlparse.urlsplit(endpoint)

        # configure npm to always require auth for the repository.
        always_auth_config = '//{}{}:always-auth'.format(
            repo_uri.netloc, repo_uri.path
        )
        commands.append(
            [cls.NPM_CMD, 'config', 'set', always_auth_config, 'true']
        )

        # set auth info for the repository.
        auth_token_config = '//{}{}:_authToken'.format(
            repo_uri.netloc, repo_uri.path
        )
        commands.append(
            [cls.NPM_CMD, 'config', 'set', auth_token_config, auth_token]
        )

        return commands


class PipLogin(BaseLogin):

    PIP_INDEX_URL_FMT = '{scheme}://aws:{auth_token}@{netloc}{path}simple/'

    def login(self, dry_run=False):
        commands = self.get_commands(
            self.repository_endpoint, self.auth_token
        )
        self._run_commands('pip', commands, dry_run)

    @classmethod
    def get_commands(cls, endpoint, auth_token, **kwargs):
        repo_uri = urlparse.urlsplit(endpoint)
        pip_index_url = cls.PIP_INDEX_URL_FMT.format(
            scheme=repo_uri.scheme,
            auth_token=auth_token,
            netloc=repo_uri.netloc,
            path=repo_uri.path
        )

        return [['pip', 'config', 'set', 'global.index-url', pip_index_url]]


class TwineLogin(BaseLogin):

    DEFAULT_PYPI_RC_FMT = u'''\
[distutils]
index-servers=
    pypi
    codeartifact

[codeartifact]
repository: {repository_endpoint}
username: aws
password: {auth_token}'''

    def __init__(
        self,
        auth_token,
        expiration,
        repository_endpoint,
        subprocess_utils,
        pypi_rc_path=None
    ):
        if pypi_rc_path is None:
            pypi_rc_path = self.get_pypi_rc_path()
        self.pypi_rc_path = pypi_rc_path
        super(TwineLogin, self).__init__(
            auth_token, expiration, repository_endpoint, subprocess_utils)

    @classmethod
    def get_commands(cls, endpoint, auth_token, **kwargs):
        # TODO(ujjwalpa@): We don't really have a command to execute for Twine
        # as we directly write to the pypirc file (or to stdout for dryrun)
        # with python itself instead. Nevertheless, we're using this method for
        # testing so we'll keep the interface for now but return a string with
        # the expected pypirc content instead of a list of commands to
        # execute. This definitely reeks of code smell and there is probably
        # room for rethinking and refactoring the interfaces of these adapter
        # helper classes in the future.

        assert 'pypi_rc_path' in kwargs, 'pypi_rc_path must be provided.'
        pypi_rc_path = kwargs['pypi_rc_path']

        default_pypi_rc = cls.DEFAULT_PYPI_RC_FMT.format(
            repository_endpoint=endpoint,
            auth_token=auth_token
        )

        pypi_rc = RawConfigParser()
        if os.path.exists(pypi_rc_path):
            try:
                pypi_rc.read(pypi_rc_path)
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

                pypi_rc.set('codeartifact', 'repository', endpoint)
                pypi_rc.set('codeartifact', 'username', 'aws')
                pypi_rc.set('codeartifact', 'password', auth_token)
            except Exception as e:  # invalid .pypirc file
                sys.stdout.write('%s is in an invalid state.' % pypi_rc_path)
                sys.stdout.write(os.linesep)
                raise e
        else:
            pypi_rc.readfp(StringIO(default_pypi_rc))

        pypi_rc_stream = StringIO()
        pypi_rc.write(pypi_rc_stream)
        pypi_rc_str = pypi_rc_stream.getvalue()
        pypi_rc_stream.close()

        return pypi_rc_str

    def login(self, dry_run=False):
        # No command to execute for Twine, we get the expected pypirc content
        # instead.
        pypi_rc_str = self.get_commands(
            self.repository_endpoint,
            self.auth_token,
            pypi_rc_path=self.pypi_rc_path
        )

        if dry_run:
            sys.stdout.write('Dryrun mode is enabled, not writing to pypirc.')
            sys.stdout.write(os.linesep)
            sys.stdout.write(
                '%s would have been set to the following:' % self.pypi_rc_path
            )
            sys.stdout.write(os.linesep)
            sys.stdout.write(os.linesep)
            sys.stdout.write(pypi_rc_str)
            sys.stdout.write(os.linesep)
        else:
            with open(self.pypi_rc_path, 'w+') as fp:
                fp.write(pypi_rc_str)

            self._write_success_message('twine')

    @classmethod
    def get_pypi_rc_path(cls):
        return os.path.join(os.path.expanduser("~"), ".pypirc")


class CodeArtifactLogin(BasicCommand):
    '''Log in to the idiomatic tool for the requested package format.'''

    TOOL_MAP = {
        'npm': {
            'package_format': 'npm',
            'login_cls': NpmLogin
        },
        'pip': {
            'package_format': 'pypi',
            'login_cls': PipLogin
        },
        'twine': {
            'package_format': 'pypi',
            'login_cls': TwineLogin
        }
    }

    NAME = 'login'

    DESCRIPTION = (
        'Sets up the idiomatic tool for your package format to use your '
        'CodeArtifact repository. Your login information is valid for up '
        'to 12 hours after which you must login again.'
    )

    ARG_TABLE = [
        {
            'name': 'tool',
            'help_text': 'The tool you want to connect with your repository',
            'choices': list(TOOL_MAP.keys()),
            'required': True,
        },
        {
            'name': 'domain',
            'help_text': 'Your CodeArtifact domain name',
            'required': True,
        },
        {
            'name': 'domain-owner',
            'help_text': 'The AWS account ID that owns your CodeArtifact '
                         'domain',
            'required': False,
        },
        {
            'name': 'duration-seconds',
            'cli_type_name': 'integer',
            'help_text': 'The time, in seconds, that the login information '
                         'is valid',
            'required': False,
        },
        {
            'name': 'repository',
            'help_text': 'Your CodeArtifact repository name',
            'required': True,
        },
        {
            'name': 'dry-run',
            'action': 'store_true',
            'help_text': 'Only print the commands that would be executed '
                         'to connect your tool with your repository without '
                         'making any changes to your configuration',
            'required': False,
            'default': False
        },
    ]

    def _get_repository_endpoint(
        self, codeartifact_client, parsed_args, package_format
    ):
        kwargs = {
            'domain': parsed_args.domain,
            'repository': parsed_args.repository,
            'format': package_format
        }
        if parsed_args.domain_owner:
            kwargs['domainOwner'] = parsed_args.domain_owner

        get_repository_endpoint_response = \
            codeartifact_client.get_repository_endpoint(**kwargs)

        return get_repository_endpoint_response['repositoryEndpoint']

    def _get_authorization_token(self, codeartifact_client, parsed_args):
        kwargs = {
            'domain': parsed_args.domain
        }
        if parsed_args.domain_owner:
            kwargs['domainOwner'] = parsed_args.domain_owner

        if parsed_args.duration_seconds:
            kwargs['durationSeconds'] = parsed_args.duration_seconds

        get_authorization_token_response = \
            codeartifact_client.get_authorization_token(**kwargs)

        return get_authorization_token_response

    def _run_main(self, parsed_args, parsed_globals):
        tool = parsed_args.tool.lower()

        package_format = self.TOOL_MAP[tool]['package_format']

        codeartifact_client = cli_utils.create_client_from_parsed_globals(
            self._session, 'codeartifact', parsed_globals
        )

        auth_token_res = self._get_authorization_token(
            codeartifact_client, parsed_args
        )

        repository_endpoint = self._get_repository_endpoint(
            codeartifact_client, parsed_args, package_format
        )

        auth_token = auth_token_res['authorizationToken']
        expiration = parse_timestamp(auth_token_res['expiration'])
        login = self.TOOL_MAP[tool]['login_cls'](
            auth_token, expiration, repository_endpoint, subprocess
        )

        login.login(parsed_args.dry_run)

        return 0
