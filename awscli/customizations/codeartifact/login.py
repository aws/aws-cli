import errno
import os
import platform
import sys
import subprocess
import re

from datetime import datetime
from dateutil.tz import tzutc
from dateutil.relativedelta import relativedelta
from botocore.utils import parse_timestamp

from awscli.compat import (
    is_windows, urlparse, RawConfigParser, StringIO,
    get_stderr_encoding, is_macos
)
from awscli.customizations import utils as cli_utils
from awscli.customizations.commands import BasicCommand
from awscli.customizations.utils import uni_print


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


class CommandFailedError(Exception):
    def __init__(self, called_process_error, auth_token):
        msg = str(called_process_error).replace(auth_token, '******')
        if called_process_error.stderr is not None:
            msg +=(
                f' Stderr from command:\n'
                f'{called_process_error.stderr.decode(get_stderr_encoding())}'
            )
        Exception.__init__(self, msg)


class BaseLogin(object):
    _TOOL_NOT_FOUND_MESSAGE = '%s was not found. Please verify installation.'

    def __init__(self, auth_token, expiration, repository_endpoint,
                 domain, repository, subprocess_utils, namespace=None):
        self.auth_token = auth_token
        self.expiration = expiration
        self.repository_endpoint = repository_endpoint
        self.domain = domain
        self.repository = repository
        self.subprocess_utils = subprocess_utils
        self.namespace = namespace

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
            self._run_command(tool, command)

        self._write_success_message(tool)

    def _run_command(self, tool, command, *, ignore_errors=False):
        try:
            self.subprocess_utils.run(
                command,
                capture_output=True,
                check=True
            )
        except subprocess.CalledProcessError as ex:
            if not ignore_errors:
                raise CommandFailedError(ex, self.auth_token)
        except OSError as ex:
            if ex.errno == errno.ENOENT:
                raise ValueError(
                    self._TOOL_NOT_FOUND_MESSAGE % tool
                )
            raise ex

    @classmethod
    def get_commands(cls, endpoint, auth_token, **kwargs):
        raise NotImplementedError('get_commands()')


class SwiftLogin(BaseLogin):

    DEFAULT_NETRC_FMT = \
        u'machine {hostname} login token password {auth_token}'

    NETRC_REGEX_FMT = \
        r'(?P<entry_start>\bmachine\s+{escaped_hostname}\s+login\s+\S+\s+password\s+)' \
        r'(?P<token>\S+)'

    def login(self, dry_run=False):
        scope = self.get_scope(
            self.namespace
        )
        commands = self.get_commands(
            self.repository_endpoint, self.auth_token, scope=scope
        )

        if not is_macos:
            hostname = urlparse.urlparse(self.repository_endpoint).hostname
            new_entry = self.DEFAULT_NETRC_FMT.format(
                hostname=hostname,
                auth_token=self.auth_token
            )
            if dry_run:
                self._display_new_netrc_entry(new_entry, self.get_netrc_path())
            else:
                self._update_netrc_entry(hostname, new_entry, self.get_netrc_path())

        self._run_commands('swift', commands, dry_run)

    def _display_new_netrc_entry(self, new_entry, netrc_path):
        sys.stdout.write('Dryrun mode is enabled, not writing to netrc.')
        sys.stdout.write(os.linesep)
        sys.stdout.write(
            f'The following line would have been written to {netrc_path}:'
        )
        sys.stdout.write(os.linesep)
        sys.stdout.write(os.linesep)
        sys.stdout.write(new_entry)
        sys.stdout.write(os.linesep)
        sys.stdout.write(os.linesep)
        sys.stdout.write('And would have run the following commands:')
        sys.stdout.write(os.linesep)
        sys.stdout.write(os.linesep)

    def _update_netrc_entry(self, hostname, new_entry, netrc_path):
        pattern = re.compile(
            self.NETRC_REGEX_FMT.format(escaped_hostname=re.escape(hostname)),
            re.M
        )
        if not os.path.isfile(netrc_path):
            self._create_netrc_file(netrc_path, new_entry)
        else:
            with open(netrc_path, 'r') as f:
                contents = f.read()
            escaped_auth_token = self.auth_token.replace('\\', r'\\')
            new_contents = re.sub(
                pattern,
                rf"\g<entry_start>{escaped_auth_token}",
                contents
            )

            if new_contents == contents:
                new_contents = self._append_netrc_entry(new_contents, new_entry)

            with open(netrc_path, 'w') as f:
                f.write(new_contents)

    def _create_netrc_file(self, netrc_path, new_entry):
        dirname = os.path.split(netrc_path)[0]
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        with os.fdopen(os.open(netrc_path,
                               os.O_WRONLY | os.O_CREAT, 0o600), 'w') as f:
            f.write(new_entry + '\n')

    def _append_netrc_entry(self, contents, new_entry):
        if contents.endswith('\n'):
            return contents + new_entry + '\n'
        else:
            return contents + '\n' + new_entry + '\n'

    @classmethod
    def get_netrc_path(cls):
        return os.path.join(os.path.expanduser("~"), ".netrc")

    @classmethod
    def get_scope(cls, namespace):
        # Regex for valid scope name
        valid_scope_name = re.compile(
            r'\A[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}\Z'
        )

        if namespace is None:
            return namespace

        if not valid_scope_name.match(namespace):
            raise ValueError(
                'Invalid scope name, scope must contain URL-safe '
                'characters, no leading dots or underscores and no '
                'more than 39 characters'
            )

        return namespace

    @classmethod
    def get_commands(cls, endpoint, auth_token, **kwargs):
        commands = []
        scope = kwargs.get('scope')

        # Set up the codeartifact repository as the swift registry.
        set_registry_command = [
            'swift', 'package-registry', 'set', endpoint
        ]
        if scope is not None:
            set_registry_command.extend(['--scope', scope])
        commands.append(set_registry_command)

        # Authenticate against the repository.
        # We will write token to .netrc for Linux and Windows
        # MacOS will store the token from command line option to Keychain
        login_registry_command = [
            'swift', 'package-registry', 'login', f'{endpoint}login'
        ]
        if is_macos:
            login_registry_command.extend(['--token', auth_token])
        commands.append(login_registry_command)

        return commands


class NuGetBaseLogin(BaseLogin):
    _NUGET_INDEX_URL_FMT = '{endpoint}v3/index.json'

    # When adding new sources we can specify that we added the source to the
    # user level NuGet.Config file. However, when updating an existing source
    # we cannot be specific about which level NuGet.Config file was updated
    # because it is possible that the existing source was not in the user
    # level NuGet.Config. The source listing command returns all configured
    # sources from all NuGet.Config levels. The update command updates the
    # source in whichever NuGet.Config file the source was found.
    _SOURCE_ADDED_MESSAGE = 'Added source %s to the user level NuGet.Config\n'
    _SOURCE_UPDATED_MESSAGE = 'Updated source %s in the NuGet.Config\n'
    # Example line the below regex should match:
    # 1.  nuget.org [Enabled]
    _SOURCE_REGEX = re.compile(r'^\d+\.\s(?P<source_name>.+)\s\[.*\]')

    def login(self, dry_run=False):
        try:
            source_to_url_dict = self._get_source_to_url_dict()
        except OSError as ex:
            if ex.errno == errno.ENOENT:
                raise ValueError(
                    self._TOOL_NOT_FOUND_MESSAGE % self._get_tool_name()
                )
            raise ex

        nuget_index_url = self._NUGET_INDEX_URL_FMT.format(
            endpoint=self.repository_endpoint
        )
        source_name, already_exists = self._get_source_name(
            nuget_index_url, source_to_url_dict
        )

        if already_exists:
            command = self._get_configure_command(
                'update', nuget_index_url, source_name
            )
            source_configured_message = self._SOURCE_UPDATED_MESSAGE
        else:
            command = self._get_configure_command('add', nuget_index_url, source_name)
            source_configured_message = self._SOURCE_ADDED_MESSAGE

        if dry_run:
            dry_run_command = ' '.join([str(cd) for cd in command])
            uni_print(dry_run_command)
            uni_print('\n')
            return

        try:
            self.subprocess_utils.run(
                command,
                capture_output=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            uni_print('Failed to update the NuGet.Config\n')
            raise CommandFailedError(e, self.auth_token)

        uni_print(source_configured_message % source_name)
        self._write_success_message('nuget')

    def _get_source_to_url_dict(self):
        """
        Parses the output of the nuget sources list command.

        A dict is created where the keys are the source names
        and the values the corresponding URL.

        The output of the command can contain header and footer information
        around the 'Registered Sources' section, which is ignored.

        Example output that is parsed:

        Registered Sources:

        1. Source Name 1 [Enabled]
           https://source1.com/index.json
        2. Source Name 2 [Disabled]
           https://source2.com/index.json
        100. Source Name 100 [Activé]
             https://source100.com/index.json
        """
        response = self.subprocess_utils.check_output(
            self._get_list_command(),
            stderr=self.subprocess_utils.PIPE
        )

        lines = response.decode(os.device_encoding(1) or "utf-8").splitlines()
        lines = [line for line in lines if line.strip() != '']

        source_to_url_dict = {}
        for i in range(len(lines)):
            result = self._SOURCE_REGEX.match(lines[i].strip())
            if result:
                source_to_url_dict[result["source_name"].strip()] = \
                    lines[i + 1].strip()

        return source_to_url_dict

    def _get_source_name(self, codeartifact_url, source_dict):
        default_name = '{}/{}'.format(self.domain, self.repository)

        # Check if the CodeArtifact URL is already present in the
        # NuGet.Config file. If the URL already exists, use the source name
        # already assigned to the CodeArtifact URL.
        for source_name, source_url in source_dict.items():
            if source_url == codeartifact_url:
                return source_name, True

        # If the CodeArtifact URL is not present in the NuGet.Config file,
        # check if the default source name already exists so we can know
        # whether we need to add a new entry or update the existing entry.
        for source_name in source_dict.keys():
            if source_name == default_name:
                return source_name, True

        # If neither the source url nor the source name already exist in the
        # NuGet.Config file, use the default source name.
        return default_name, False

    def _get_tool_name(self):
        raise NotImplementedError('_get_tool_name()')

    def _get_list_command(self):
        raise NotImplementedError('_get_list_command()')

    def _get_configure_command(self, operation, nuget_index_url, source_name):
        raise NotImplementedError('_get_configure_command()')


class NuGetLogin(NuGetBaseLogin):

    def _get_tool_name(self):
        return 'nuget'

    def _get_list_command(self):
        return ['nuget', 'sources', 'list', '-format', 'detailed']

    def _get_configure_command(self, operation, nuget_index_url, source_name):
        return [
            'nuget', 'sources', operation,
            '-name', source_name,
            '-source', nuget_index_url,
            '-username', 'aws',
            '-password', self.auth_token
        ]


class DotNetLogin(NuGetBaseLogin):

    def _get_tool_name(self):
        return 'dotnet'

    def _get_list_command(self):
        return ['dotnet', 'nuget', 'list', 'source', '--format', 'detailed']

    def _get_configure_command(self, operation, nuget_index_url, source_name):
        command = ['dotnet', 'nuget', operation, 'source']

        if operation == 'add':
            command.append(nuget_index_url)
            command += ['--name', source_name]
        else:
            command.append(source_name)
            command += ['--source', nuget_index_url]

        command += [
            '--username', 'aws',
            '--password', self.auth_token
        ]

        # Encryption is not supported on non-Windows platforms.
        if not is_windows:
            command.append('--store-password-in-clear-text')

        return command


class NpmLogin(BaseLogin):

    # On Windows we need to be explicit about the .cmd file to execute
    # (unless we execute through the shell, i.e. with shell=True).
    NPM_CMD = 'npm.cmd' if platform.system().lower() == 'windows' else 'npm'

    def login(self, dry_run=False):
        scope = self.get_scope(
            self.namespace
        )
        commands = self.get_commands(
            self.repository_endpoint, self.auth_token, scope=scope
        )
        self._run_commands('npm', commands, dry_run)

    def _run_command(self, tool, command):
        ignore_errors = any('always-auth' in arg for arg in command)
        super()._run_command(tool, command, ignore_errors=ignore_errors)

    @classmethod
    def get_scope(cls, namespace):
        # Regex for valid scope name
        valid_scope_name = re.compile('^(@[a-z0-9-~][a-z0-9-._~]*)')

        if namespace is None:
            return namespace

        # Add @ prefix to scope if it doesn't exist
        if namespace.startswith('@'):
            scope = namespace
        else:
            scope = '@{}'.format(namespace)

        if not valid_scope_name.match(scope):
            raise ValueError(
                'Invalid scope name, scope must contain URL-safe '
                'characters, no leading dots or underscores'
            )

        return scope

    @classmethod
    def get_commands(cls, endpoint, auth_token, **kwargs):
        commands = []
        scope = kwargs.get('scope')

        # prepend scope if it exists
        registry = '{}:registry'.format(scope) if scope else 'registry'

        # set up the codeartifact repository as the npm registry.
        commands.append(
            [cls.NPM_CMD, 'config', 'set', registry, endpoint]
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
        domain,
        repository,
        subprocess_utils,
        pypi_rc_path=None
    ):
        if pypi_rc_path is None:
            pypi_rc_path = self.get_pypi_rc_path()
        self.pypi_rc_path = pypi_rc_path
        super(TwineLogin, self).__init__(
            auth_token, expiration, repository_endpoint,
            domain, repository, subprocess_utils)

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
            pypi_rc.read_string(default_pypi_rc)

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
        'swift': {
            'package_format': 'swift',
            'login_cls': SwiftLogin,
            'namespace_support': True,
        },
        'nuget': {
            'package_format': 'nuget',
            'login_cls': NuGetLogin,
            'namespace_support': False,
        },
        'dotnet': {
            'package_format': 'nuget',
            'login_cls': DotNetLogin,
            'namespace_support': False,
        },
        'npm': {
            'package_format': 'npm',
            'login_cls': NpmLogin,
            'namespace_support': True,
        },
        'pip': {
            'package_format': 'pypi',
            'login_cls': PipLogin,
            'namespace_support': False,
        },
        'twine': {
            'package_format': 'pypi',
            'login_cls': TwineLogin,
            'namespace_support': False,
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
            'name': 'namespace',
            'help_text': 'Associates a namespace with your repository tool',
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
            'name': 'endpoint-type',
            'help_text': 'The type of endpoint you want the tool to interact with',
            'required': False
        },
        {
            'name': 'dry-run',
            'action': 'store_true',
            'help_text': 'Only print the commands that would be executed '
                         'to connect your tool with your repository without '
                         'making any changes to your configuration. Note that '
                         'this prints the unredacted auth token as part of the output',
            'required': False,
            'default': False
        },
    ]

    def _get_namespace(self, tool, parsed_args):
        namespace_compatible = self.TOOL_MAP[tool]['namespace_support']

        if not namespace_compatible and parsed_args.namespace:
            raise ValueError(
                'Argument --namespace is not supported for {}'.format(tool)
            )
        else:
            return parsed_args.namespace

    def _get_repository_endpoint(
        self, codeartifact_client, parsed_args, package_format
    ):
        kwargs = {
            'domain': parsed_args.domain,
            'repository': parsed_args.repository,
            'format': package_format
        }
        if parsed_args.endpoint_type:
            kwargs['endpointType'] = parsed_args.endpoint_type
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

        domain = parsed_args.domain
        repository = parsed_args.repository
        namespace = self._get_namespace(tool, parsed_args)

        auth_token = auth_token_res['authorizationToken']
        expiration = parse_timestamp(auth_token_res['expiration'])
        login = self.TOOL_MAP[tool]['login_cls'](
            auth_token, expiration, repository_endpoint,
            domain, repository, subprocess, namespace
        )

        login.login(parsed_args.dry_run)

        return 0
