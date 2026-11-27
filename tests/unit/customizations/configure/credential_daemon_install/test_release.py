# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os
import shutil
import socket
import subprocess
import sys
from urllib.parse import quote, urlsplit

import pytest
from botocore import exceptions as botocore_exceptions
from urllib3.connectionpool import HTTPSConnectionPool
from urllib3.exceptions import MaxRetryError, ProtocolError
from urllib3.exceptions import ReadTimeoutError as URLLib3ReadTimeoutError
from urllib3.util.url import parse_url

from awscli import __version__ as awscli_version
from awscli.botocore.awsrequest import AWSRequest
from awscli.customizations.configure.credential_daemon_install import (
    release as install_release,
)
from awscli.customizations.configure.credential_daemon_install.host import (
    InstallHost,
)
from awscli.customizations.configure.credential_daemon_install.release import (
    ReleaseSource,
)
from awscli.customizations.configure.credentialdaemon import (
    InstallCredentialDaemonCommand,
)
from awscli.customizations.exceptions import (
    ConfigurationError,
)
from tests import mock
from tests.markers import skip_if_windows
from tests.unit.customizations.configure.credential_daemon_install.helpers import (
    DOWNLOAD,
    MACOS_ASSET,
    RELEASE_URL,
    FakeHttp,
    Response,
    Runner,
    credential_daemon_package,
    download,
    install,
    linux_http,
    macos_http,
    package_info,
    release,
    tag_page,
)

# How much RawBody hands out per read when built from content.
_CHUNK = install_release._DOWNLOAD_CHUNK_BYTES


class TestPinnedRelease:
    def test_the_release_repository(self):
        assert install_release.RELEASE_REPO == 'aws/credential-daemon'

    # Windows runners' gpg (from Git for Windows) can't read Windows paths.
    @skip_if_windows
    @pytest.mark.skipif(shutil.which('gpg') is None, reason='needs gpg')
    def test_the_pinned_key_has_the_pinned_fingerprint(self, tmp_path):
        key = tmp_path / 'key.asc'
        key.write_text(install_release.CREDENTIAL_DAEMON_PGP_KEY)
        result = subprocess.run(
            [
                'gpg',
                '--homedir',
                str(tmp_path),
                '--batch',
                '--with-colons',
                '--show-keys',
                str(key),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        records = [line.split(':') for line in result.stdout.splitlines()]
        primary = [r for r in records if r[0] == 'pub']
        assert len(primary) == 1
        fingerprints = [r[9] for r in records if r[0] == 'fpr']
        assert fingerprints[0] == (
            install_release.CREDENTIAL_DAEMON_PGP_FINGERPRINT
        )
        assert fingerprints[0] == '91AA53FE815B7D0DC20D1467189A6EBAE4B4D2A4'


NAME = 'credsd-linux-x64-tpm.tar.gz'


class TestLinuxSignatures:
    def test_a_missing_signature_says_so(self, pinned_key):
        http = linux_http()
        http.responses[f'{DOWNLOAD}/{NAME}.sig'] = Response(404)
        with pytest.raises(ConfigurationError) as e:
            install(http=http)
        assert str(e.value) == (
            f'aws-credential-daemon\'s v1.0.0 release has no {NAME}.sig, so '
            f'it wasn\'t installed.'
        )

    def test_a_sig_signature_is_used(self, pinned_key):
        http = linux_http()
        runner = Runner()
        assert install(http=http, runner=runner) == 0
        assert f'{DOWNLOAD}/{NAME}.sig' in http.urls
        assert f'{DOWNLOAD}/{NAME}.asc' not in http.urls
        assert os.path.basename(runner.commands[1][-2]) == (
            'aws-credential-daemon.tar.gz.sig'
        )


class TestLatestRelease:
    """The tag comes from where github.com's releases/latest redirects,
    not from api.github.com, which allows 60 requests an hour per address
    without a token."""

    def test_reads_the_tag_from_the_redirect_and_nothing_else(self):
        http = macos_http('v1.2.3')
        release_ = ReleaseSource(
            InstallHost(http_session=http)
        ).latest_release()
        assert (release_.tag, release_.version) == ('v1.2.3', (1, 2, 3))
        # One request, not followed to the tag's page.
        assert http.urls == [RELEASE_URL]

    def test_never_asks_api_github_com(self, pinned_key):
        assert 'api.github.com' not in install_release._ALLOWED_HOSTS
        http = linux_http()
        assert install(http=http) == 0
        assert not [url for url in http.urls if 'api.github.com' in url]

    def test_the_assets_are_built_from_the_tag(self):
        http = macos_http('v1.2.3')
        release_ = ReleaseSource(
            InstallHost(http_session=http)
        ).latest_release()
        base = download('v1.2.3')
        assert release_.assets == {
            'credsd-macos-aarch64.pkg': f'{base}/credsd-macos-aarch64.pkg',
            'credsd-linux-x64-tpm.tar.gz': (
                f'{base}/credsd-linux-x64-tpm.tar.gz'
            ),
            'credsd-linux-x64-tpm.tar.gz.sig': (
                f'{base}/credsd-linux-x64-tpm.tar.gz.sig'
            ),
            'credsd-linux-aarch64-tpm.tar.gz': (
                f'{base}/credsd-linux-aarch64-tpm.tar.gz'
            ),
            'credsd-linux-aarch64-tpm.tar.gz.sig': (
                f'{base}/credsd-linux-aarch64-tpm.tar.gz.sig'
            ),
        }
        assert install_release.linux_asset_name('aarch64') == (
            'credsd-linux-aarch64-tpm.tar.gz'
        )
        assert install_release.MACOS_ASSET == 'credsd-macos-aarch64.pkg'

    @pytest.mark.parametrize('status', [301, 302, 303, 307, 308])
    def test_any_redirect_status(self, status):
        http = FakeHttp({RELEASE_URL: release('v1.2.3', status=status)})
        release_ = ReleaseSource(
            InstallHost(http_session=http)
        ).latest_release()
        assert release_.tag == 'v1.2.3'

    def test_a_relative_location_to_the_tag_page(self):
        http = FakeHttp(
            {
                RELEASE_URL: Response(
                    302,
                    headers={
                        'Location': '/aws/credential-daemon/releases/tag/v1.2.3'
                    },
                )
            }
        )
        release_ = ReleaseSource(
            InstallHost(http_session=http)
        ).latest_release()
        assert release_.tag == 'v1.2.3'

    @pytest.mark.parametrize(
        'location',
        [
            'https://github.com/evil/credential-daemon/releases/tag/v1.0.0',
            'https://github.com/aws/credential-daemon-evil/releases/tag/v1.0.0',
            'https://evil.example.com/aws/credential-daemon/releases/tag/'
            'v1.0.0',
            'http://github.com/aws/credential-daemon/releases/tag/v1.0.0',
            'https://x@github.com/aws/credential-daemon/releases/tag/v1.0.0',
            'https://github.com:8443/aws/credential-daemon/releases/tag/'
            'v1.0.0',
            'https://github.com/aws/credential-daemon/releases/download/'
            'v1.0.0/credsd-macos-aarch64.pkg',
            'https://github.com/aws/credential-daemon/releases',
            '',
        ],
    )
    def test_a_location_other_than_the_tag_page_is_refused(self, location):
        http = FakeHttp(
            {RELEASE_URL: Response(302, headers={'Location': location})}
        )
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=http)
        assert str(e.value).startswith(
            'Refusing to download aws-credential-daemon from '
        )
        assert http.urls == [RELEASE_URL]

    def test_a_location_with_control_characters_is_refused(self):
        location = f'{tag_page("v1.0.0")}\x1b[2K'
        http = FakeHttp(
            {RELEASE_URL: Response(302, headers={'Location': location})}
        )
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=http)
        assert str(e.value) == (
            'Refusing to download aws-credential-daemon from '
            f'{tag_page("v1.0.0")}\\x1b[2K.'
        )

    def test_a_page_instead_of_a_redirect_is_unreadable(self):
        http = FakeHttp({RELEASE_URL: Response(content=b'<html>')})
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=http)
        assert str(e.value) == (
            "Couldn't read aws-credential-daemon's latest release from GitHub."
        )
        # The page isn't read.
        assert http.responses[RELEASE_URL].raw.read == 0
        assert http.responses[RELEASE_URL].raw.closed

    def test_an_http_error(self):
        http = FakeHttp({RELEASE_URL: Response(403)})
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=http)
        assert str(e.value) == (f"Couldn't download {RELEASE_URL}: HTTP 403")


class TestMissingAssets:
    def test_a_missing_package_says_so(self):
        http = macos_http()
        http.responses[f'{DOWNLOAD}/credsd-macos-aarch64.pkg'] = Response(404)
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=http)
        assert str(e.value) == (
            'aws-credential-daemon\'s v1.0.0 release has no '
            'credsd-macos-aarch64.pkg, so it wasn\'t installed.'
        )

    def test_a_missing_archive_says_so(self, pinned_key):
        http = linux_http()
        http.responses[f'{DOWNLOAD}/{NAME}'] = Response(404)
        with pytest.raises(ConfigurationError) as e:
            install(http=http)
        assert str(e.value) == (
            f'aws-credential-daemon\'s v1.0.0 release has no {NAME}, so it '
            'wasn\'t installed.'
        )

    def test_a_404_after_a_redirect_is_an_http_error(self):
        # Only the release's own URL means the file isn't in the release.
        http = macos_http()
        storage = 'https://objects.githubusercontent.com/x'
        http.responses[f'{DOWNLOAD}/credsd-macos-aarch64.pkg'] = Response(
            302, headers={'Location': storage}
        )
        http.responses[storage] = Response(404)
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=http)
        assert str(e.value) == f"Couldn't download {storage}: HTTP 404"


class TestProxiesAndCaBundle:
    """Without a test session, each request gets a URLLib3Session with the
    environment's proxies for its URL and the CLI's CA bundle."""

    def fetch(self, verify=None, environ=None):
        sessions = []

        def session(**kwargs):
            sessions.append(kwargs)
            fake = mock.Mock()
            fake.send.return_value = Response(content=b'ok')
            return fake

        with (
            mock.patch.object(install_release, 'URLLib3Session', session),
            mock.patch.dict(os.environ, environ or {}, clear=True),
        ):
            source = ReleaseSource(InstallHost(), verify=verify)
            assert source.fetch(f'{DOWNLOAD}/{NAME}') == b'ok'
        return sessions

    def test_uses_the_environments_proxy(self):
        sessions = self.fetch(environ={'HTTPS_PROXY': 'http://proxy:3128'})
        assert sessions == [
            {'proxies': {'https': 'http://proxy:3128'}, 'verify': True}
        ]

    def test_no_proxy_skips_it(self):
        sessions = self.fetch(
            environ={
                'HTTPS_PROXY': 'http://proxy:3128',
                'NO_PROXY': 'github.com',
            }
        )
        assert sessions == [{'proxies': {}, 'verify': True}]

    def test_uses_the_ca_bundle(self):
        sessions = self.fetch(verify='/etc/corp-ca.pem')
        assert sessions == [{'proxies': {}, 'verify': '/etc/corp-ca.pem'}]

    PROXY_HINT = (
        'Behind a proxy, keep its settings under sudo:\n'
        '  sudo --preserve-env=HTTPS_PROXY,https_proxy,NO_PROXY,no_proxy,'
        'AWS_CA_BUNDLE aws configure credential-daemon install\n'
        'If the proxy inspects TLS, also pass --ca-bundle with its CA file.'
    )

    def fail(self, error, system='linux', verify=None, **host_options):
        http = mock.Mock()
        http.send.side_effect = error
        source = ReleaseSource(
            InstallHost(system=system, http_session=http, **host_options),
            verify=verify,
        )
        with pytest.raises(ConfigurationError) as e:
            source.latest_release()
        assert str(e.value).startswith(f"Couldn't download {RELEASE_URL}: ")
        return str(e.value)

    def refused(self):
        return botocore_exceptions.EndpointConnectionError(
            endpoint_url=RELEASE_URL, error=OSError('refused')
        )

    @pytest.mark.parametrize(
        'system, hint', [('linux', True), ('darwin', False)]
    )
    def test_a_connection_error_says_how_to_keep_the_proxy(self, system, hint):
        # Lowercase names too: many images set only https_proxy.
        message = self.fail(self.refused(), system=system)
        assert message.endswith(f'\n{self.PROXY_HINT}') is hint

    @pytest.mark.parametrize(
        'error',
        [
            botocore_exceptions.ProxyConnectionError(
                proxy_url='http://proxy:3128', error='refused'
            ),
            botocore_exceptions.ConnectTimeoutError(endpoint_url=RELEASE_URL),
            botocore_exceptions.ConnectionClosedError(
                endpoint_url=RELEASE_URL
            ),
        ],
    )
    def test_other_connection_errors_give_the_hint(self, error):
        assert self.fail(error).endswith(self.PROXY_HINT)

    def test_a_tls_failure_without_a_ca_bundle_gives_the_hint(self):
        error = botocore_exceptions.SSLError(
            endpoint_url=RELEASE_URL, error='certificate verify failed'
        )
        assert self.fail(error).endswith(self.PROXY_HINT)

    def test_a_tls_failure_with_a_ca_bundle_gives_no_hint(self):
        # The bundle was already passed; keeping the proxy won't help.
        error = botocore_exceptions.SSLError(
            endpoint_url=RELEASE_URL, error='certificate verify failed'
        )
        assert 'Behind a proxy' not in self.fail(error, verify='/etc/ca.pem')

    def test_an_error_that_isnt_a_connection_gives_no_hint(self):
        error = botocore_exceptions.ReadTimeoutError(endpoint_url=RELEASE_URL)
        assert 'Behind a proxy' not in self.fail(error)

    def test_the_hint_is_the_plain_command_wherever_this_aws_is(
        self, tmp_path
    ):
        # An aws in a folder of the user's, such as a venv: the hint still
        # says plain aws, with no path, so it reads the same on every OS.
        aws = tmp_path / 'venv' / 'bin' / 'aws'
        aws.parent.mkdir(parents=True)
        aws.write_text('#!/bin/sh\n')
        aws.chmod(0o755)
        http = mock.Mock()
        http.send.side_effect = self.refused()
        with mock.patch.object(sys, 'argv', [str(aws)]):
            with pytest.raises(ConfigurationError) as e:
                ReleaseSource(
                    InstallHost(system='linux', http_session=http)
                ).latest_release()
        assert str(e.value).endswith(f'\n{self.PROXY_HINT}')
        assert str(tmp_path) not in str(e.value)


@skip_if_windows
class TestProxyHintFromTheRealSession:
    """The hint for what the CLI's own HTTP stack raises, not a fake.
    httpsession raises botocore.exceptions classes, and
    awscli.botocore.exceptions is the same file loaded as another
    module, so its classes don't match them."""

    def closed_port(self):
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]

    def test_a_proxy_that_refuses_gives_the_hint(self, monkeypatch):
        # HTTPS_PROXY names a port nothing listens on: the real
        # URLLib3Session that _session builds raises ProxyConnectionError.
        for name in ('https_proxy', 'NO_PROXY', 'no_proxy', 'ALL_PROXY'):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv(
            'HTTPS_PROXY', f'http://127.0.0.1:{self.closed_port()}'
        )
        host = InstallHost(system='linux')
        with pytest.raises(ConfigurationError) as e:
            ReleaseSource(host).latest_release()
        assert str(e.value).endswith(TestProxiesAndCaBundle.PROXY_HINT)

    def test_the_exceptions_are_the_ones_the_session_raises(self):
        session_module = sys.modules[install_release.URLLib3Session.__module__]
        for name in (
            'EndpointConnectionError',
            'ConnectionClosedError',
            'SSLError',
        ):
            assert getattr(session_module, name) is getattr(
                install_release.botocore_exceptions, name
            ), name


class TestVersionChecks:
    def test_the_minimum(self):
        assert install_release.MINIMUM_CREDENTIAL_DAEMON_VERSION == (0, 2, 0)

    @pytest.mark.parametrize(
        'release_version, installed',
        [
            ((0, 2, 0), None),
            ((0, 2, 0), (0, 2, 0)),
            ((0, 3, 0), (0, 2, 9)),
            ((1, 0, 0), (0, 9, 0)),
        ],
    )
    def test_the_same_or_a_newer_version_installs(
        self, release_version, installed
    ):
        install_release.check_release_version(release_version, installed)

    @pytest.mark.parametrize('installed', [None, (0, 1, 0)])
    def test_a_release_below_the_minimum_is_refused(self, installed):
        with pytest.raises(ConfigurationError) as e:
            install_release.check_release_version((0, 1, 9), installed)
        assert str(e.value) == (
            'aws-credential-daemon\'s latest release is 0.1.9, older than '
            '0.2.0, the oldest this AWS CLI installs, so nothing was '
            'downloaded.'
        )

    def test_a_downgrade_is_refused(self):
        with pytest.raises(ConfigurationError) as e:
            install_release.check_release_version((0, 2, 0), (0, 10, 0))
        assert str(e.value) == (
            'aws-credential-daemon\'s latest release is 0.2.0, older than '
            'the installed 0.10.0, so nothing was changed.'
        )

    @pytest.mark.parametrize(
        'text, version',
        [
            ('0.2.0', (0, 2, 0)),
            ('10.20.30', (10, 20, 30)),
            ('v0.2.0', None),
            ('0.2', None),
            ('0.2.0-rc1', None),
            ('\u0660.2.0', None),
            ('', None),
            (None, None),
            (5, None),
        ],
    )
    def test_parse_version(self, text, version):
        assert install_release.parse_version(text) == version

    @pytest.mark.parametrize(
        'output, expected',
        [
            (
                'credsd 0.2.0\nstorage backends: tpm, file\n',
                ((0, 2, 0), ['tpm', 'file']),
            ),
            ('0.2.0\nstorage backends: file', ((0, 2, 0), ['file'])),
            ('credsd 0.2.0\n', ((0, 2, 0), [])),
            ('credsd 0.2.0-dev\nstorage backends: tpm', (None, ['tpm'])),
            ('creds 0.2.0\n', (None, [])),
            ('', (None, [])),
            (None, (None, [])),
        ],
    )
    def test_reads_credsd_version_output(self, output, expected):
        assert install_release.credential_daemon_version(output) == expected


class TestDownloads:
    def test_follows_redirects_to_githubs_storage(self, pinned_key):
        http = linux_http()
        storage = f'https://objects.githubusercontent.com/{NAME}'
        http.responses[storage] = http.responses[f'{DOWNLOAD}/{NAME}']
        http.responses[f'{DOWNLOAD}/{NAME}'] = Response(
            302, headers={'Location': storage}
        )
        install(
            http=http,
        )
        assert storage in http.urls

    def test_sends_the_clis_user_agent_on_every_request(self, pinned_key):
        http = linux_http()
        storage = f'https://objects.githubusercontent.com/{NAME}'
        http.responses[storage] = http.responses[f'{DOWNLOAD}/{NAME}']
        http.responses[f'{DOWNLOAD}/{NAME}'] = Response(
            302, headers={'Location': storage}
        )
        install(
            http=http,
        )
        assert RELEASE_URL in http.urls
        assert storage in http.urls
        assert http.user_agents == [f'aws-cli/{awscli_version}'] * len(
            http.urls
        )

    @pytest.mark.parametrize(
        'location',
        ['https://evil.example.com/credsd', 'http://github.com/credsd'],
    )
    def test_refuses_other_hosts_and_plain_http(self, pinned_key, location):
        http = FakeHttp(
            {RELEASE_URL: Response(302, headers={'Location': location})}
        )
        with pytest.raises(ConfigurationError) as e:
            install(http=http)
        assert 'Refusing to download' in str(e.value)

    def test_http_errors(self, pinned_key):
        http = FakeHttp({RELEASE_URL: Response(404)})
        with pytest.raises(ConfigurationError) as e:
            install(http=http)
        assert 'HTTP 404' in str(e.value)


class TestDownloadSizeLimit:
    """The body is streamed and reading stops at the size limit."""

    LIMIT = 10

    @pytest.fixture(autouse=True)
    def small_limit(self):
        with mock.patch.object(
            install_release, '_MAX_DOWNLOAD_BYTES', self.LIMIT
        ):
            yield

    def fetch(self, *responses):
        http = FakeHttp({})
        requests = []
        replies = iter(responses)

        def send(request):
            requests.append(request)
            return next(replies)

        http.send = send
        command = InstallCredentialDaemonCommand(
            mock.Mock(), InstallHost(http_session=http)
        )
        return ReleaseSource(command.host).fetch(RELEASE_URL), requests

    def test_requests_a_streamed_body(self):
        body, requests = self.fetch(Response(content=b'0123456789'))
        assert body == b'0123456789'
        assert all(request.stream_output for request in requests)

    def test_stops_reading_past_the_limit(self):
        # An endless body: reading it all would never end.
        def endless():
            while True:
                yield b'xxxx'

        response = Response(chunks=endless())
        with pytest.raises(ConfigurationError) as e:
            self.fetch(response)
        assert str(e.value) == f'{RELEASE_URL} is larger than expected.'
        assert response.raw.read <= self.LIMIT + 4
        assert response.raw.closed

    def test_a_content_length_over_the_limit_reads_nothing(self):
        response = Response(
            content=b'x' * 100, headers={'Content-Length': '100'}
        )
        with pytest.raises(ConfigurationError, match='larger than expected'):
            self.fetch(response)
        assert response.raw.read == 0
        assert response.raw.closed

    def test_a_huge_content_length_reads_nothing(self):
        response = Response(
            content=b'x', headers={'Content-Length': '9' * 5000}
        )
        with pytest.raises(ConfigurationError, match='larger than expected'):
            self.fetch(response)
        assert response.raw.read == 0

    def test_a_short_content_length_doesnt_lift_the_limit(self):
        response = Response(
            content=b'x' * 100, headers={'Content-Length': '5'}
        )
        with pytest.raises(ConfigurationError, match='larger than expected'):
            self.fetch(response)
        assert response.raw.read <= self.LIMIT + _CHUNK

    def test_redirect_and_error_bodies_arent_read(self):
        location = f'{DOWNLOAD}/credsd'
        redirect = Response(302, headers={'Location': location})
        error = Response(500, content=b'x' * 100)
        with pytest.raises(ConfigurationError, match='HTTP 500'):
            self.fetch(redirect, error)
        assert redirect.raw.read == 0 and redirect.raw.closed
        assert error.raw.read == 0 and error.raw.closed

    def test_a_broken_stream_is_a_download_error(self):
        def broken():
            yield b'x'
            raise OSError('connection reset')

        with pytest.raises(ConfigurationError) as e:
            self.fetch(Response(chunks=broken()))
        assert str(e.value) == (
            f'Couldn\'t download {RELEASE_URL}: connection reset'
        )


# credsd releases are compatible with each other, so any release installs.
class TestReleaseVersion:
    @pytest.mark.parametrize('tag', ['v0.2.0', 'v1.2.0', 'v1.10.0', '2.0.0'])
    def test_any_release_installs_on_macos(self, tag):
        http = macos_http(tag)
        runner = Runner(package=credential_daemon_package(tag.lstrip('v')))
        assert install(system='darwin', http=http, runner=runner) == 0
        assert runner.commands[-1][0] == '/usr/sbin/installer'

    @skip_if_windows
    @pytest.mark.parametrize('tag', ['v0.2.0', 'v1.2.0', 'v1.10.0', '2.0.0'])
    def test_any_release_installs_on_linux(self, pinned_key, tag):
        http = linux_http(tag=tag)
        runner = Runner(
            version=f'credsd {tag.lstrip("v")}\nstorage backends: tpm\n'
        )
        assert install(http=http, runner=runner) == 0
        assert runner.commands[-2][0].endswith('/credsd')
        assert runner.commands[-2][1:] == ['install']

    @pytest.mark.parametrize(
        'tag',
        [
            'latest',
            'v1.2',
            'v1.2.0-rc1',
            '',
            'v1.0.0/x',
            'v1.0.0?x=1',
            'v1.0.0%2Fx',
            # Non-ASCII digits, which \d would accept.
            'v\u0661.\u0662.\u0660',
            # More digits than int() reads.
            pytest.param('v' + '9' * 5000 + '.0.0', id='5000-digits'),
            'v1234567890.0.0',
        ],
    )
    def test_an_unreadable_version_is_refused(self, pinned_key, tag):
        http = FakeHttp({RELEASE_URL: release(tag)})
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=http)
        assert 'Couldn\'t tell which version' in str(e.value)
        assert http.urls == [RELEASE_URL]

    def test_the_shown_tag_is_shortened(self):
        tag = 'v1.2' + 'x' * 100
        http = FakeHttp({RELEASE_URL: release(tag)})
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=http)
        shown = 'v1.2' + 'x' * 60 + '...'
        assert str(e.value) == (
            f'Couldn\'t tell which version aws-credential-daemon\'s '
            f'latest release is ({shown}), so it wasn\'t installed.'
        )

    def test_the_largest_version_part_is_read(self):
        http = macos_http('v1.999999999.0')
        runner = Runner(package=credential_daemon_package('1.999999999.0'))
        assert install(system='darwin', http=http, runner=runner) == 0


# Nothing signs the release tag, so a release must not get in under another
# release's tag.
class TestRelabelledReleases:
    def test_an_old_package_under_a_new_tag_is_refused(self):
        # The old, properly signed 1.0.0 package re-uploaded as v9.9.9.
        http = macos_http('v9.9.9')
        runner = Runner(package=credential_daemon_package('1.0.0'))
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=http, runner=runner)
        assert str(e.value) == (
            'The aws-credential-daemon package is version 1.0.0, but its '
            'release says 9.9.9, so it wasn\'t installed.'
        )
        assert not any(c[0] == '/usr/sbin/installer' for c in runner.commands)

    @pytest.mark.parametrize('system', ['darwin', 'linux'])
    def test_files_come_only_from_the_tags_release(self, pinned_key, system):
        # The asset URLs are built from the tag, so a release can't point
        # at another release's files.
        http = (
            macos_http('v9.9.9')
            if system == 'darwin'
            else linux_http(tag='v9.9.9')
        )
        runner = Runner(
            package=credential_daemon_package('9.9.9'),
            version='credsd 9.9.9\nstorage backends: tpm, file\n',
        )
        assert install(system=system, http=http, runner=runner) == 0
        assert http.urls[0] == RELEASE_URL
        assert all(
            url.startswith(f'{download("v9.9.9")}/') for url in http.urls[1:]
        )

    @pytest.mark.parametrize(
        'package',
        [
            # Older and newer than the tag's version.
            credential_daemon_package('0.1.0'),
            credential_daemon_package('1.2.5'),
            credential_daemon_package('1.3.1'),
            # A product archive with one component of another version.
            {
                'Distribution': '<installer-gui-script/>',
                'a.pkg/PackageInfo': credential_daemon_package('1.3.0')[
                    'PackageInfo'
                ],
                'b.pkg/PackageInfo': credential_daemon_package('1.2.0')[
                    'PackageInfo'
                ],
            },
        ],
    )
    def test_a_package_version_other_than_the_tags_is_refused(self, package):
        runner = Runner(package=package)
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=macos_http('v1.3.0'), runner=runner)
        assert 'but its release says 1.3.0' in str(e.value)
        assert not any(c[0] == '/usr/sbin/installer' for c in runner.commands)

    @pytest.mark.parametrize(
        'info',
        [
            '<pkg-info identifier="com.amazon.aws.credsd.daemon"/>',
            package_info('com.amazon.aws.credsd.daemon', 'v1.3.0'),
            package_info('com.amazon.aws.credsd.daemon', '1.3'),
            package_info('com.amazon.aws.credsd.daemon', '\u0661.3.0'),
        ],
    )
    def test_an_unreadable_package_version_is_refused(self, info):
        runner = Runner(package={'PackageInfo': info})
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=macos_http('v1.3.0'), runner=runner)
        assert str(e.value) == (
            'Couldn\'t tell which version the aws-credential-daemon package '
            'is, so it wasn\'t installed.'
        )
        assert not any(c[0] == '/usr/sbin/installer' for c in runner.commands)

    def test_the_version_is_checked_after_the_signature(self):
        runner = Runner(
            pkgutil='Status: no signature\n',
            package=credential_daemon_package('1.0.0'),
        )
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=macos_http('v1.3.0'), runner=runner)
        assert 'isn\'t signed and notarized' in str(e.value)

    def test_a_signature_failure_shows_pkgutils_status_and_exit_code(self):
        # pkgutil exits 1 for an unsigned package.
        runner = Runner(
            pkgutil='Package "x.pkg":\n   Status: no signature\n',
            pkgutil_rc=1,
        )
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=macos_http(), runner=runner)
        assert str(e.value) == (
            'The aws-credential-daemon package isn\'t signed and notarized by '
            'Amazon (Team ID 94KV3E626L), so it wasn\'t installed. pkgutil '
            '--check-signature (exit 1): Status: no signature'
        )

    def test_a_failed_pkgutil_run_is_refused_even_with_good_output(self):
        runner = Runner(pkgutil_rc=1)
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=macos_http(), runner=runner)
        assert str(e.value).endswith(
            '(exit 1): Status: signed by a developer certificate issued by '
            'Apple for distribution'
        )
        assert not any(c[0] == '/usr/sbin/installer' for c in runner.commands)

    def test_unreadable_pkgutil_output_says_so(self):
        runner = Runner(pkgutil='garbage\n')
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=macos_http(), runner=runner)
        assert str(e.value).endswith(
            '(exit 0): Status: not in the expected form'
        )

    def test_a_matching_version_installs(self):
        runner = Runner(package=credential_daemon_package('1.3.0'))
        assert (
            install(system='darwin', http=macos_http('v1.3.0'), runner=runner)
            == 0
        )
        assert runner.commands[-1][0] == '/usr/sbin/installer'


class TestReleaseDownloadPath:
    NAME = MACOS_ASSET

    @staticmethod
    def refused(url, shown=None, name=MACOS_ASSET):
        with pytest.raises(ConfigurationError) as e:
            install_release._check_asset_url(url, 'v1.0.0', name)
        assert str(e.value) == (
            f'Refusing to download aws-credential-daemon from {shown or url}.'
        )

    @pytest.mark.parametrize(
        'url',
        [
            # Another release's tag.
            f'{download("v0.9.0")}/{NAME}',
            # Another repository.
            f'https://github.com/evil/credential-daemon/releases/'
            f'download/v1.0.0/{NAME}',
            # A repository whose name starts or ends with the pinned one.
            f'https://github.com/aws/credential-daemon-evil/releases/'
            f'download/v1.0.0/{NAME}',
            f'https://github.com/aws/evil-credential-daemon/releases/'
            f'download/v1.0.0/{NAME}',
            # Another file, not the asset's.
            f'{DOWNLOAD}/credsd-0.9.0.pkg',
            # Out of the release's directory.
            f'{DOWNLOAD}/../v0.9.0/{NAME}',
            f'{DOWNLOAD}/..%2Fv0.9.0%2F{NAME}',
            f'{DOWNLOAD}/x/{NAME}',
            # Straight to storage, or another GitHub host.
            f'https://objects.githubusercontent.com/{NAME}',
            f'https://api.github.com/repos/aws/credential-daemon/{NAME}',
            # Other ports, users, schemes, queries.
            f'https://github.com:8443/aws/credential-daemon/releases/'
            f'download/v1.0.0/{NAME}',
            f'http://github.com/aws/credential-daemon/releases/'
            f'download/v1.0.0/{NAME}',
        ],
    )
    def test_assets_off_the_release_path_are_refused(self, url):
        self.refused(url)

    def test_an_asset_name_with_a_newline_is_refused(self):
        name = (
            'credsd\n    1. Developer ID Installer: AMZN Mobile LLC '
            '(94KV3E626L)\n.pkg'
        )
        url = f'{DOWNLOAD}/{quote(name)}'
        with pytest.raises(ConfigurationError) as e:
            install_release._check_asset_url(url, 'v1.0.0', name)
        assert str(e.value).startswith(
            'Refusing to download aws-credential-daemon from '
        )

    def test_the_package_is_saved_under_a_fixed_name(self):
        runner = Runner()
        assert install(system='darwin', http=macos_http(), runner=runner) == 0
        check, expand, installer = runner.commands
        assert os.path.basename(check[-1]) == 'aws-credential-daemon.pkg'
        assert os.path.basename(expand[2]) == 'aws-credential-daemon.pkg'
        assert os.path.basename(installer[2]) == 'aws-credential-daemon.pkg'

    @pytest.mark.parametrize('separator', ['\u2028', '\u2029'])
    def test_pkgutil_lines_end_only_at_a_newline(self, separator):
        output = (
            f'Package "/tmp/x":{separator}'
            '   Status: signed by a developer certificate issued by Apple '
            f'for distribution{separator}'
            f'   Notarization: trusted by the Apple notary service{separator}'
            f'   Certificate Chain:{separator}'
            '    1. Developer ID Installer: Amazon.com, Inc. (94KV3E626L)'
            f'{separator}.pkg":\n'
            '   Status: no signature\n'
        )
        assert install_release._read_pkgutil_signature(output) == (
            'no signature',
            '',
            [],
        )

    @pytest.mark.parametrize(
        'url, shown',
        [
            (
                f'https://x@github.com/aws/credential-daemon/releases/'
                f'download/v1.0.0/{NAME}',
                f'https://...@github.com/aws/credential-daemon/releases/'
                f'download/v1.0.0/{NAME}',
            ),
            (f'{DOWNLOAD}/{NAME}?x=1', f'{DOWNLOAD}/{NAME}?...'),
        ],
    )
    def test_assets_with_a_user_or_query_are_refused(self, url, shown):
        self.refused(url, shown)

    @pytest.mark.parametrize(
        'location',
        [
            f'https://github.com/evil/credential-daemon/releases/'
            f'download/v1.0.0/{NAME}',
            f'https://github.com/aws/credential-daemon-evil/releases/'
            f'download/v1.0.0/{NAME}',
            f'https://github.com/aws/evil-credential-daemon/releases/'
            f'download/v1.0.0/{NAME}',
            f'{download("v0.9.0")}/{NAME}',
            'https://evil.example.com/credsd.pkg',
            'https://api.github.com/credsd.pkg',
            # urllib3 ends the host at the backslash and connects to
            # evil.example.
            'https://evil.example\\@objects.githubusercontent.com/x',
            'https://evil.example\\@release-assets.githubusercontent.com/x',
            # Storage hops with a user, a port, plain HTTP or another
            # spelling of the host.
            'https://u:p@objects.githubusercontent.com/x',
            'https://objects.githubusercontent.com:8443/x',
            'http://objects.githubusercontent.com/x',
            'https://OBJECTS.githubusercontent.com/x',
            'https://objects.githubusercontent.com./x',
            'https://objects.githubusercontent.com/x\x1b[2K',
        ],
    )
    def test_redirects_off_the_release_path_are_refused(self, location):
        url = f'{DOWNLOAD}/{self.NAME}'
        http = FakeHttp(
            {
                RELEASE_URL: release(),
                url: Response(302, headers={'Location': location}),
                location: Response(content=b'pkg'),
            }
        )
        runner = Runner()
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=http, runner=runner)
        assert 'Refusing to download' in str(e.value)
        assert location not in http.urls
        assert runner.commands == []

    @pytest.mark.parametrize(
        'location',
        [
            'https://release-assets.githubusercontent.com/x?sig=1',
            f'{DOWNLOAD}/{NAME}-moved',
        ],
    )
    def test_redirects_to_storage_or_within_the_release_are_followed(
        self, location
    ):
        url = f'{DOWNLOAD}/{self.NAME}'
        http = FakeHttp(
            {
                RELEASE_URL: release(),
                url: Response(302, headers={'Location': location}),
                location: Response(content=b'pkg'),
            }
        )
        assert install(system='darwin', http=http) == 0
        assert http.urls[-1] == location

    @pytest.mark.parametrize(
        'location',
        [
            'https://evil.example\\@objects.githubusercontent.com/x',
            'https://evil.example\\@release-assets.githubusercontent.com/x',
        ],
    )
    def test_backslash_redirect_is_not_followed_where_urllib3_connects(
        self, location
    ):
        # urlsplit sees a storage host, but urllib3, which makes the
        # connection, sees evil.example.
        prepared = AWSRequest(method='GET', url=location).prepare().url
        assert urlsplit(location).hostname.endswith('.githubusercontent.com')
        assert parse_url(prepared).host == 'evil.example'
        url = f'{DOWNLOAD}/{self.NAME}'
        http = FakeHttp(
            {
                RELEASE_URL: release(),
                url: Response(302, headers={'Location': location}),
                prepared: Response(content=b'pkg'),
                location: Response(content=b'pkg'),
            }
        )
        runner = Runner()
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=http, runner=runner)
        assert 'Refusing to download' in str(e.value)
        assert http.urls == [RELEASE_URL, url]
        assert runner.commands == []

    @pytest.mark.parametrize(
        'url, shown',
        [
            (
                f'{DOWNLOAD}/\x1b]0;pwned\x07\x1b[2K',
                f'{DOWNLOAD}/\\x1b]0;pwned\\x07\\x1b[2K',
            ),
            (
                f'{download("v0.9.0")}/\x1b[2Kx',
                f'{download("v0.9.0")}/\\x1b[2Kx',
            ),
            (
                f'https://github.com\x9b2K/{NAME}',
                f'https://github.com\\x9b2K/{NAME}',
            ),
        ],
    )
    def test_refused_urls_are_printed_with_control_characters_escaped(
        self, url, shown
    ):
        self.refused(url, shown)

    def test_redirect_errors_escape_control_characters(self):
        url = f'{DOWNLOAD}/{self.NAME}'
        http = FakeHttp(
            {
                RELEASE_URL: release(),
                url: Response(302, headers={'Location': f'{url}\x1b[2K'}),
            }
        )
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=http)
        assert '\x1b' not in str(e.value)
        assert f'{url}\\x1b[2K' in str(e.value)

    @pytest.mark.parametrize(
        'location',
        [
            'https://[::1',
            'https://[::1/x?sig=SECRET1',
            'https://[SECRET1]/x',
            'http://[bad]/',
        ],
    )
    def test_a_redirect_that_doesnt_split_is_refused(self, location):
        url = f'{DOWNLOAD}/{self.NAME}'
        http = FakeHttp(
            {
                RELEASE_URL: release(),
                url: Response(302, headers={'Location': location}),
            }
        )
        runner = Runner()
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=http, runner=runner)
        # Printed through _shown_url, so never the URL itself.
        assert str(e.value) == (
            'Refusing to download aws-credential-daemon from '
            "<a URL that couldn't be read>."
        )
        assert http.urls == [RELEASE_URL, url]
        assert runner.commands == []

    def test_an_asset_url_that_doesnt_split_is_refused(self):
        self.refused(
            f'https://[::1/x?{TOKEN}', "<a URL that couldn't be read>"
        )

    @pytest.mark.parametrize(
        'check',
        [
            lambda url: install_release._check_host(url, ('github.com',)),
            lambda url: install_release._check_asset_redirect(url, 'v1.0.0'),
        ],
        ids=['check_host', 'check_asset_redirect'],
    )
    def test_url_checks_refuse_a_url_that_doesnt_split(self, check):
        with pytest.raises(ConfigurationError) as e:
            check(f'https://[::1/x?{TOKEN}')
        assert str(e.value) == (
            'Refusing to download aws-credential-daemon from '
            "<a URL that couldn't be read>."
        )


TOKEN = 'TOKENa1b2c3'

# What github.com redirects a release download to: a storage URL signed
# with a temporary token in its query string.
SIGNED = (
    'https://release-assets.githubusercontent.com/'
    'github-production-release-asset/123/abc'
    '?X-Amz-Algorithm=AWS4-HMAC-SHA256'
    f'&X-Amz-Credential={TOKEN}%2F20261114%2Fus-east-1%2Fs3%2Faws4_request'
    f'&X-Amz-Signature={TOKEN}&jwt={TOKEN}'
    '&response-content-disposition=attachment%3B%20filename%3Dcredsd.pkg'
)

SIGNED_SHOWN = (
    'https://release-assets.githubusercontent.com/'
    'github-production-release-asset/123/abc?...'
)


class TestShownUrls:
    """A printed URL never has its query string, fragment or user part."""

    @pytest.mark.parametrize(
        'url, shown',
        [
            (SIGNED, SIGNED_SHOWN),
            (f'{SIGNED}#{TOKEN}', f'{SIGNED_SHOWN}#...'),
            (f'{DOWNLOAD}/credsd.pkg#{TOKEN}', f'{DOWNLOAD}/credsd.pkg#...'),
            (
                f'https://u:{TOKEN}@objects.githubusercontent.com:8443/x',
                'https://...@objects.githubusercontent.com:8443/x',
            ),
            (
                'https://evil.example\\@objects.githubusercontent.com/x',
                'https://...@objects.githubusercontent.com/x',
            ),
            (f'{DOWNLOAD}/credsd.pkg', f'{DOWNLOAD}/credsd.pkg'),
            (f'{DOWNLOAD}/credsd.pkg?', f'{DOWNLOAD}/credsd.pkg'),
            # Control characters are still escaped, newlines included,
            # which urlsplit would otherwise drop.
            (
                f'{DOWNLOAD}/\x1b]0;pwned\x07?sig={TOKEN}\x1b[2K',
                f'{DOWNLOAD}/\\x1b]0;pwned\\x07?...',
            ),
            (f'{DOWNLOAD}/a\nb\x9b', f'{DOWNLOAD}/a\\x0ab\\x9b'),
            (
                f'https://github.com\x9b2K/credsd.pkg?{TOKEN}',
                'https://github.com\\x9b2K/credsd.pkg?...',
            ),
            # Doesn't split: a placeholder, never the URL.
            (f'https://[::1/x?sig={TOKEN}', "<a URL that couldn't be read>"),
            (
                f'https://[{TOKEN}]/x?sig={TOKEN}',
                "<a URL that couldn't be read>",
            ),
        ],
    )
    def test_shown_url(self, url, shown):
        assert install_release._shown_url(url) == shown

    # The check urlsplit does only from CPython 3.11.4, so it's tested
    # without urlsplit.
    @pytest.mark.parametrize(
        'netloc',
        [
            'github.com',
            '[::1]',
            '[::1]:8443',
            'u:p@[fe80::1%eth0]',
            '[v1.x]',
        ],
    )
    def test_a_good_bracketed_host_is_kept(self, netloc):
        install_release._check_bracketed_netloc(netloc)

    @pytest.mark.parametrize(
        'netloc',
        [f'[{TOKEN}]', '[1.2.3.4]', 'a[::1]', '[::1]x', '[vZ.x]'],
    )
    def test_a_bad_bracketed_host_is_refused(self, netloc):
        with pytest.raises(ValueError):
            install_release._check_bracketed_netloc(netloc)

    def fetch_error(self, response):
        """The error from downloading a release file that github.com
        redirects to SIGNED, which then gives response."""
        name = MACOS_ASSET
        http = FakeHttp(
            {
                RELEASE_URL: release(),
                f'{DOWNLOAD}/{name}': Response(
                    302, headers={'Location': SIGNED}
                ),
                SIGNED: response,
            }
        )
        with pytest.raises(ConfigurationError) as e:
            install(system='darwin', http=http)
        assert SIGNED in http.urls
        message = str(e.value)
        assert TOKEN not in message
        assert 'X-Amz' not in message
        return e.value

    def test_http_errors(self):
        error = self.fetch_error(Response(403))
        assert str(error) == f"Couldn't download {SIGNED_SHOWN}: HTTP 403"

    def test_too_many_redirects(self):
        error = self.fetch_error(Response(302, headers={'Location': SIGNED}))
        assert str(error) == f'Too many redirects downloading {SIGNED_SHOWN}.'

    def test_too_large(self):
        error = self.fetch_error(
            Response(headers={'Content-Length': '9' * 30})
        )
        assert str(error) == f'{SIGNED_SHOWN} is larger than expected.'

    def test_refused_redirect(self):
        location = f'https://u:{TOKEN}@objects.githubusercontent.com/x?{TOKEN}'
        error = self.fetch_error(Response(302, headers={'Location': location}))
        assert str(error) == (
            'Refusing to download aws-credential-daemon from '
            'https://...@objects.githubusercontent.com/x?....'
        )

    @staticmethod
    def errors():
        """Real botocore and urllib3 errors for SIGNED, as
        URLLib3Session.send raises them."""
        pool = HTTPSConnectionPool('release-assets.githubusercontent.com', 443)
        target = SIGNED.split('.com', 1)[1]
        reason = OSError('[Errno 111] Connection refused')
        return [
            botocore_exceptions.EndpointConnectionError(
                endpoint_url=SIGNED, error=reason
            ),
            botocore_exceptions.ConnectTimeoutError(
                endpoint_url=SIGNED, error=reason
            ),
            botocore_exceptions.ReadTimeoutError(
                endpoint_url=SIGNED,
                error=URLLib3ReadTimeoutError(pool, target, 'Read timed out'),
            ),
            botocore_exceptions.SSLError(endpoint_url=SIGNED, error=reason),
            botocore_exceptions.ConnectionClosedError(
                endpoint_url=SIGNED,
                request=None,
                error=ProtocolError('Connection aborted.', reason),
            ),
            botocore_exceptions.HTTPClientError(
                error=MaxRetryError(pool, target, reason)
            ),
            MaxRetryError(pool, target, reason),
            # A reason quoting the URL, repr-style.
            ValueError(f"bad URL '{SIGNED}'"),
        ]

    def test_the_errors_used_here_have_the_token(self):
        for error in self.errors():
            assert TOKEN in str(error), error

    @pytest.mark.parametrize('index', range(8))
    def test_send_errors(self, index):
        raised = self.errors()[index]

        def send():
            raise raised

        error = self.fetch_error(send)
        assert str(error).startswith(f"Couldn't download {SIGNED_SHOWN}: ")
        # With --debug the CLI logs the traceback, chained errors and all.
        assert error.__cause__ is None and error.__suppress_context__

    def test_send_error_keeps_the_reason(self):
        raised = self.errors()[-3]  # HTTPClientError around MaxRetryError

        def send():
            raise raised

        error = self.fetch_error(send)
        assert str(error) == (
            f"Couldn't download {SIGNED_SHOWN}: An HTTP Client raised an "
            'unhandled exception: HTTPSConnectionPool(host='
            "'release-assets.githubusercontent.com', port=443): Max retries "
            'exceeded with url: /github-production-release-asset/123/abc?... '
            "(Caused by OSError('[Errno 111] Connection refused'))"
        )

    @pytest.mark.parametrize('index', range(8))
    def test_read_errors(self, index):
        raised = self.errors()[index]

        def chunks():
            yield b'x'
            raise raised

        error = self.fetch_error(Response(chunks=chunks()))
        assert str(error).startswith(f"Couldn't download {SIGNED_SHOWN}: ")
        assert error.__cause__ is None and error.__suppress_context__

    @pytest.mark.parametrize(
        'text, shown',
        [
            # Only a "?" or "#" right after a URL or path goes.
            ('Is it there? No.', 'Is it there? No.'),
            ('error #5', 'error #5'),
            ('url: /x?a=1&b=2 (Caused by x)', 'url: /x?... (Caused by x)'),
            ('"https://h/x?a=1"', '"https://h/x?..."'),
            ("'https://h/x#frag'", "'https://h/x#...'"),
            ('bad\x1b[2K', 'bad\\x1b[2K'),
        ],
    )
    def test_shown_error(self, text, shown):
        assert install_release._shown_error(ValueError(text), '') == shown

    def test_shown_error_drops_the_urls_own_query_anywhere(self):
        # Even where the pattern wouldn't find it: after a quote.
        url = f'https://h/x?a\'{TOKEN}'
        text = f"bad URL: '/x?a'{TOKEN}'"
        shown = install_release._shown_error(ValueError(text), url)
        assert shown == "bad URL: '/x?...'"

    def test_shown_error_leaves_the_rest_of_the_text_alone(self):
        url = 'https://h/x?1'
        text = '[Errno 111] url: /x?1 (1 try)'
        shown = install_release._shown_error(ValueError(text), url)
        assert shown == '[Errno 111] url: /x?... (1 try)'
