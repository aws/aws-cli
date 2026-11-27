# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""The latest aws-credential-daemon release: where it comes from, how it is
downloaded and how its signature is checked."""

import ipaddress
import os
import re
import shutil
import tarfile
import xml.etree.ElementTree as ElementTree
from urllib.parse import unquote, urljoin, urlsplit

from botocore import exceptions as botocore_exceptions
from urllib3.util.url import parse_url

from awscli import __version__ as awscli_version
from awscli.botocore.awsrequest import AWSRequest
from awscli.botocore.credential_daemon import (
    CREDENTIAL_DAEMON_PACKAGE_ID,
    CREDENTIAL_DAEMON_TEAM_ID,
    strip_control_characters,
)
from awscli.botocore.httpsession import URLLib3Session
from awscli.botocore.utils import get_environ_proxies
from awscli.customizations.exceptions import ConfigurationError
from awscli.customizations.gpg import gpg_keyring

RELEASE_REPO = 'aws/credential-daemon'


# The daemon's name in this command's messages; the help text spells it out.
CREDENTIAL_DAEMON_PRODUCT = 'aws-credential-daemon'


# github.com redirects this to the latest release's tag page. It's read
# instead of api.github.com's releases API, which allows only 60
# unauthenticated requests an hour per address, shared by everyone behind
# the same NAT or CI egress.
_LATEST_RELEASE_URL = f'https://github.com/{RELEASE_REPO}/releases/latest'


_RELEASE_TAG_URL = f'https://github.com/{RELEASE_REPO}/releases/tag/'


_RELEASE_DOWNLOAD_URL = f'https://github.com/{RELEASE_REPO}/releases/download/'


# The release's files are named by credsd's release workflow, so their URLs
# are built from the tag and these names, not read from the network.
MACOS_ASSET = 'credsd-macos-aarch64.pkg'


# The Linux archives' detached PGP signatures: the archive's name plus this.
LINUX_SIGNATURE_SUFFIX = '.sig'


# Every release must be at least this version. On Linux the version
# comes from the signed `credsd --version`, on macOS from the signed
# package's PackageInfo, and both must equal the tag.
MINIMUM_CREDENTIAL_DAEMON_VERSION = (0, 2, 0)


# Release downloads redirect from github.com to GitHub's storage hosts.
# Nothing is fetched from anywhere else, and only over HTTPS.
_STORAGE_HOSTS = (
    'objects.githubusercontent.com',
    'release-assets.githubusercontent.com',
)


_ALLOWED_HOSTS = ('github.com',) + _STORAGE_HOSTS


_MAX_REDIRECTS = 5


_REDIRECTS = (301, 302, 303, 307, 308)


# The CLI's User-Agent, sent on every request to GitHub, so it doesn't
# depend on urllib3 adding its own.
_USER_AGENT = f'aws-cli/{awscli_version}'


_MAX_DOWNLOAD_BYTES = 256 * 1024 * 1024


_DOWNLOAD_CHUNK_BYTES = 1024 * 1024


# The key aws-credential-daemon signs its Linux release archives with, and its
# fingerprint: the armored block in the repository's KEYS file at tag v0.1.0
# (commit 573f321d). It expires on 2030-10-08.
CREDENTIAL_DAEMON_PGP_KEY = """-----BEGIN PGP PUBLIC KEY BLOCK-----

mQINBGrJH2oBEADCwbGV0a0lkB7bwJZmXq7ZfBREtuMb18DRAwFe2eloh8UEdmFu
p09nFSHu74G8j61QiTQIRsu3BrOXS6a59TIDS0XFyPLYwqLow6JFDz+wqz6XoX46
pcMHXUoTnvIBI8K5IWq0wRqm+F3ndaZ1ofHzrIdggJPJyeG1sU9i6kAha215TOc+
lq8uBHw8qSDCnjjEzlmG0na7IZVDJUnERijhPomjJV36YMEsi0w0cWPiOgCIFtsw
n/amanSaH3WCz8WlJkwFjmqmdzqHUqM0V8MQ3OPuvLj9rtFkaQulIiMxxScoi85K
jlbluSJVpe+m+irQ70yQAqW8mbDHI/xILbvru/NhF2KdWzZzgQokMce9pDcU5Nkl
uV7zVZwD08wd/3Elc+ToSJYsnAsWlKffcKf2AohbIYjfV0TUsh9MM+rOZzfiHwvf
YX7NZA4LIzzUbrbkJq2sVZLut7v6v7p9uPAJQyNFcEdP5aaWniB9VFGSJpweUynz
bg25ck0jSqhouCDqEDwg/8jIrLkmkYSXkzqiDPLdeOHjuzsliVUfdyYBxE2+spX1
LkPWy8sJXZf5g/4jzIKmLXCBpeI3fFTQWn+48oL2GUT/88lWSELI8FKfF5HpuJig
jTqbeHfLRH/H0UqUdn/d+svjQgqNeh2AE9kF5oP26NFX87KO4DM0CMe55wARAQAB
tDhBV1MgQ3JlZGVudGlhbCBEYWVtb24gPGF3cy1jcmVkZW50aWFsLWRhZW1vbkBh
bWF6b24uY29tPokCcwQTAQgAXRYhBJGqU/6BW30Nwg0UZxiabrrktNKkBQJqyR9q
GxSAAAAAAAQADm1hbnUyLDIuNSsxLjEyLDAsMwIbAwUJB4TOAAULCQgHAgIiAgYV
CgkICwIEFgIDAQIeBwIXgAAKCRAYmm665LTSpNXGD/9AgV4Uo3eEbBU41cQf0e8B
k7mG4Ze6BlqCDOTIsHH1BUPpdsAT088+U8gn5rYsELReMD9ogfP/nDUlSEcGZG3l
PReuMwflKLhyOmWCDKDQ3rUdIOkWWMOQrL6YRZM7luWzfPXHXH3ffX2zdyXVVpuQ
2rCbc3q4TPXmJPYViaOfhytY4lmwUgk94i9n67xE9y9hMxk68o5pENOnsmzt+PCV
zS0rpowg+x2q0vCUQVMGaDPKrRs1n+bGne6h11wfSyLZKFoQTPoaM492P9SXXBgz
Qyv/0dcLSF3NNXRIWsp/x+cLCLjKzPgQ8HMeBv517ZIwntjF0hVw1fu1gNV8PzFl
Zd4E9l4igmFDECycdI4FxkdQhPMUcHzucGRjFcmLACa/7aL0BWuGsRh1KAp3gdl1
a/MjoChwKaAyczVR+8ii9D0VYXEgSPlWkQYnpWdmpiOh7qV9jth3RaoVfpaWx6vU
cJ8nqA1cJQGwlSh5KncnsptroK7Wg0FExSztWxa72hWJXLFA2xsrlVRNiZOuuosf
BUmQQh6sZ3GFAdnSa9qN39EMPOMXILEJ6VWiw8QkWbTl5XpdGAbknK/UMui5GR8E
KFjhfJl8VbfC1dgkX/urGiRO2c9O2S12/lLZLDuAP3j9G8DFPofztc/iCmBc39xY
feurlPhI6Vi9YskmgPW1uA==
=Rrae
-----END PGP PUBLIC KEY BLOCK-----
"""


CREDENTIAL_DAEMON_PGP_FINGERPRINT = '91AA53FE815B7D0DC20D1467189A6EBAE4B4D2A4'


# CREDENTIAL_DAEMON_TEAM_ID and CREDENTIAL_DAEMON_PACKAGE_ID, which the
# macOS package must be signed with, live in botocore.credential_daemon, next
# to the code requirement every command checks the running daemon against.
# A release's version is read from its tag, vMAJOR.MINOR.PATCH. Each part is
# ASCII digits and short enough for int(), which refuses more than 4300
# digits. Nothing signs the tag, so on macOS the version in the signed
# package's PackageInfo, MAJOR.MINOR.PATCH, must match it.
_RELEASE_TAG = re.compile(r'v?([0-9]{1,9})\.([0-9]{1,9})\.([0-9]{1,9})')


_PACKAGE_VERSION = re.compile(r'([0-9]{1,9})\.([0-9]{1,9})\.([0-9]{1,9})')


_SHOWN_TAG_LENGTH = 64


# `credsd --version`'s first line, "credsd 0.2.0", and its backends line,
# "storage backends: tpm, file".
_CREDENTIAL_DAEMON_VERSION_LINE = re.compile(r'(?:credsd )?(\S+)')


_STORAGE_BACKENDS_PREFIX = 'storage backends:'


# Control characters in a URL from the network. A URL with any is
# refused, and they're escaped before it's printed.
_URL_CONTROL_CHARACTERS = re.compile(r'[\x00-\x1f\x7f-\x9f]')


# A "?" or "#" right after a URL or path, up to the next space or quote:
# what _shown_error leaves out of an error's text.
_ERROR_URL_QUERY = re.compile(r'(?<=\S)([?#])[^\s\'"]+')


# The install can run as root, so its tools come from fixed system paths,
# not PATH, which under sudo can still be the user's.
_PKGUTIL = '/usr/sbin/pkgutil'


# A certificate in pkgutil --check-signature's chain: "1. Developer ID ...".
_PKGUTIL_CHAIN_ENTRY = re.compile(r'([0-9]{1,3})\. (.+)')


_GPG_SEARCH_PATH = os.pathsep.join(['/usr/bin', '/bin'])


def find_gpg():
    """The gpg that checks the Linux release's signature. Refuses when
    there's none, so Linux install checks for it before the download."""
    gpg = shutil.which('gpg', path=_GPG_SEARCH_PATH)
    if gpg is None:
        raise ConfigurationError(
            'gpg wasn\'t found in /usr/bin or /bin, so '
            f'{CREDENTIAL_DAEMON_PRODUCT} '
            f'download can\'t be checked. Install gnupg and try again.'
        )
    return gpg


# gpg --status-fd lines that mean the signature mustn't be trusted.
_GPG_BAD_STATUS = ('BADSIG', 'ERRSIG', 'EXPKEYSIG', 'REVKEYSIG', 'EXPSIG')


class _Release:
    def __init__(self, tag, version, assets):
        self.tag = tag
        self.version = version
        self.assets = assets


def linux_asset_name(arch):
    """The Linux TPM archive's name for ``arch`` (x64 or aarch64)."""
    return f'credsd-linux-{arch}-tpm.tar.gz'


def _release_assets(tag):
    """Each file of the release with this tag, name to download URL."""
    names = [MACOS_ASSET]
    for arch in ('x64', 'aarch64'):
        name = linux_asset_name(arch)
        names += [name, name + LINUX_SIGNATURE_SUFFIX]
    return {name: f'{_RELEASE_DOWNLOAD_URL}{tag}/{name}' for name in names}


def _release_version(tag):
    """The tag's version, refused if the tag isn't vMAJOR.MINOR.PATCH."""
    match = _RELEASE_TAG.fullmatch(tag) if isinstance(tag, str) else None
    if match is None:
        raise ConfigurationError(
            'Couldn\'t tell which version '
            f'{CREDENTIAL_DAEMON_PRODUCT}\'s latest release '
            f'is ({_shown_tag(tag)}), so it wasn\'t installed.'
        )
    return tuple(int(part) for part in match.groups())


def parse_version(text):
    """(MAJOR, MINOR, PATCH) for exactly ``MAJOR.MINOR.PATCH``, or None."""
    match = _PACKAGE_VERSION.fullmatch(text) if isinstance(text, str) else None
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def credential_daemon_version(output):
    """(version or None, storage backends) from ``credsd --version``.

    The output is ``credsd 0.2.0`` (or just ``0.2.0``), then a line
    ``storage backends: tpm, file``.
    """
    lines = (output or '').strip().splitlines()
    version = None
    if lines:
        match = _CREDENTIAL_DAEMON_VERSION_LINE.fullmatch(lines[0].strip())
        if match is not None:
            version = parse_version(match.group(1))
    backends = []
    for line in lines[1:]:
        line = line.strip()
        if line.startswith(_STORAGE_BACKENDS_PREFIX):
            backends = [
                name.strip()
                for name in line[len(_STORAGE_BACKENDS_PREFIX) :].split(',')
                if name.strip()
            ]
    return version, backends


def check_release_version(release_version, installed_version):
    """Refuse a release below the minimum, or older than what's
    installed (``installed_version``, None if unknown).

    Nothing signs GitHub's "latest", so it can point at any release the
    key or certificate ever signed. For example, with 0.2.0 installed and
    "latest" moved back to 0.1.0, install would otherwise replace 0.2.0
    with 0.1.0 and print "Installed". So a release older than
    MINIMUM_CREDENTIAL_DAEMON_VERSION is refused before the download, and
    one older than the installed version is refused before anything
    changes. The same version reinstalls. There's no override: raising the
    minimum takes a CLI release.
    """
    if release_version < MINIMUM_CREDENTIAL_DAEMON_VERSION:
        raise ConfigurationError(
            f'{CREDENTIAL_DAEMON_PRODUCT}\'s latest release is '
            f'{format_version(release_version)}, older than '
            f'{format_version(MINIMUM_CREDENTIAL_DAEMON_VERSION)}, the oldest '
            'this AWS CLI installs, so nothing was downloaded.'
        )
    if installed_version is not None and release_version < installed_version:
        raise ConfigurationError(
            f'{CREDENTIAL_DAEMON_PRODUCT}\'s latest release is '
            f'{format_version(release_version)}, older than the installed '
            f'{format_version(installed_version)}, so nothing was changed.'
        )


def check_package_version(components, release_version):
    """Check the signed package's own version, not just the tag's.

    The package's signature covers its PackageInfo, so a package
    re-uploaded under another tag is caught here. Every component must be the release's version.
    """
    for _, version in components:
        package_version = parse_version(version)
        if package_version is None:
            raise ConfigurationError(
                'Couldn\'t tell which version the '
                f'{CREDENTIAL_DAEMON_PRODUCT} package is, so '
                f'it wasn\'t installed.'
            )
        if package_version != release_version:
            raise ConfigurationError(
                f'The {CREDENTIAL_DAEMON_PRODUCT} package is version '
                f'{format_version(package_version)}, but its release says '
                f'{format_version(release_version)}, so it wasn\'t '
                f'installed.'
            )


def _shown_tag(tag):
    # The tag comes from the network, so it's cleaned before it's printed.
    if not isinstance(tag, str):
        tag = repr(tag)
    tag = strip_control_characters(tag)
    if len(tag) > _SHOWN_TAG_LENGTH:
        tag = tag[:_SHOWN_TAG_LENGTH] + '...'
    return tag


def format_version(version):
    return '.'.join(str(part) for part in version)


def printable_lines(text):
    """A command's output, line by line, without escape sequences."""
    return '\n'.join(
        strip_control_characters(line).strip()
        for line in (text or '').strip().splitlines()
    ).strip()


def _exit(result):
    return f'(exit {result.returncode})'


def _imported_pinned_key(status):
    """Whether gpg's --import --status-fd output has an IMPORT_OK line for
    the pinned key: "[GNUPG:] IMPORT_OK <reasons> <fingerprint>"."""
    pinned = CREDENTIAL_DAEMON_PGP_FINGERPRINT.replace(' ', '').upper()
    for line in (status or '').splitlines():
        fields = line.split()
        if (
            len(fields) >= 4
            and fields[0] == '[GNUPG:]'
            and fields[1] == 'IMPORT_OK'
            and fields[3].upper() == pinned
        ):
            return True
    return False


def _signed_by_pinned_key(status):
    """Whether gpg's --status-fd output shows a good pinned signature.

    VALIDSIG's first field is the signing key's fingerprint and its last
    the primary key's, so a release signed by a subkey also matches.
    """
    pinned = CREDENTIAL_DAEMON_PGP_FINGERPRINT.replace(' ', '').upper()
    valid = False
    for line in status.splitlines():
        fields = line.split()
        if len(fields) < 2 or fields[0] != '[GNUPG:]':
            continue
        if fields[1] in _GPG_BAD_STATUS:
            return False
        if fields[1] == 'VALIDSIG' and len(fields) > 2:
            valid = valid or pinned in (fields[2].upper(), fields[-1].upper())
    return valid


def _package_components(expanded):
    """The (identifier, version) of an expanded package's components.

    A component package has its PackageInfo at the top; a product archive
    has one in each component's directory. Empty if any PackageInfo
    isn't XML.
    """
    paths = [os.path.join(expanded, 'PackageInfo')]
    if os.path.isdir(expanded):
        paths += [
            os.path.join(expanded, name, 'PackageInfo')
            for name in sorted(os.listdir(expanded))
        ]
    components = []
    for path in paths:
        if not os.path.isfile(path):
            continue
        try:
            root = ElementTree.parse(path).getroot()
        except ElementTree.ParseError:
            return []
        components.append((root.get('identifier'), root.get('version')))
    return components


def _read_pkgutil_signature(output):
    """(status, notarization, certificate chain) from the output of
    ``pkgutil --check-signature``, or ('', '', []) if it isn't in the
    expected form.

    Read line by line, by position: the ``Package "<path>":`` line, then
    indented ``Name: value`` lines, then the numbered certificate chain,
    leaf first. The first line echoes the path, so nothing in it counts.
    Blank lines, such as the one pkgutil ends with, are skipped. Lines end
    only at a newline: str.splitlines() also ends one at characters such as
    U+2028, which a path can hold.
    """
    unreadable = ('', '', [])
    lines = output.split('\n')
    if not lines or not (
        lines[0].startswith('Package "') and lines[0].endswith('":')
    ):
        return unreadable
    fields = {}
    chain = None
    for line in lines[1:]:
        text = line.strip()
        if not text:
            continue
        if not line[:1].isspace():
            return unreadable
        if chain is not None:
            # Each entry's own lines (Expires, SHA256 Fingerprint, ...)
            # are indented further, and aren't numbered.
            entry = _PKGUTIL_CHAIN_ENTRY.match(text)
            if entry is not None:
                if int(entry.group(1)) != len(chain) + 1:
                    return unreadable
                chain.append(entry.group(2))
            continue
        if text == 'Certificate Chain:':
            chain = []
            continue
        name, sep, value = text.partition(': ')
        if sep:
            if name in fields:
                return unreadable
            fields[name] = value
    return (
        fields.get('Status', ''),
        fields.get('Notarization', ''),
        chain or [],
    )


def _check_url(url):
    _check_host(url, _ALLOWED_HOSTS)


def _check_host(url, hosts):
    """Check url is HTTPS to one of hosts, and return its urlsplit parts.

    urllib3 makes the connection, and it doesn't always split a URL the
    way urlsplit does: it ends the host at a backslash, so
    ``https://evil\\@github.com/`` connects to ``evil``. So a URL with a
    backslash or a control character is refused, and urlsplit and
    urllib3 must both find exactly an allowed host, with no user or port.
    """
    try:
        parts = urlsplit(url)
        connects_to = parse_url(url)
    except ValueError:
        raise _refused(url) from None
    if (
        '\\' in url
        or _URL_CONTROL_CHARACTERS.search(url)
        or parts.scheme != 'https'
        or parts.netloc not in hosts
        or connects_to.host != parts.netloc
        or connects_to.auth is not None
        or connects_to.port is not None
    ):
        raise _refused(url)
    return parts


def _check_asset_url(url, tag, name=None):
    """Check url is a file of aws-credential-daemon's GitHub release with this
    tag.

    With name, the file must be that asset.
    """
    parts = _check_host(url, ('github.com',))
    prefix = f'/{RELEASE_REPO}/releases/download/{tag}/'
    file_name = None
    if parts.path.startswith(prefix):
        file_name = unquote(parts.path[len(prefix) :])
    if (
        parts.query
        or parts.fragment
        or not file_name
        or '/' in file_name
        or _URL_CONTROL_CHARACTERS.search(file_name)
        or file_name in ('.', '..')
        or (name is not None and file_name != name)
    ):
        raise _refused(url)


def _check_asset_redirect(url, tag):
    # github.com sends release files on to GitHub's storage hosts. Any
    # other redirect must stay inside the same release.
    try:
        host = urlsplit(url).hostname
    except ValueError:
        raise _refused(url) from None
    if host in _STORAGE_HOSTS:
        _check_host(url, _STORAGE_HOSTS)
    else:
        _check_asset_url(url, tag)


def _refused(url):
    return ConfigurationError(
        f'Refusing to download {CREDENTIAL_DAEMON_PRODUCT} from {_shown_url(url)}.'
    )


def _check_bracketed_netloc(netloc):
    # A copy of CPython's urllib.parse._check_bracketed_netloc, which
    # urlsplit runs only from 3.11.4 and in later 3.9/3.10 security
    # releases, so every Python shows the same URL. Raises ValueError.
    if '[' not in netloc:
        return
    before, bracket, rest = netloc.rpartition('@')[2].partition('[')
    if bracket:
        host, _, port = rest.partition(']')
        if before or (port and not port.startswith(':')):
            raise ValueError(netloc)
    else:
        host = before.partition(':')[0]
    if host.startswith('v'):
        if not re.match(r'\Av[a-fA-F0-9]+\..+\Z', host):
            raise ValueError(netloc)
    elif isinstance(ipaddress.ip_address(host), ipaddress.IPv4Address):
        raise ValueError(netloc)


def _shown_url(url):
    """url as it's printed: its scheme, host, port and path.

    GitHub's storage redirects carry a temporary access token in the
    query string, and a user part can hold a password, so the query,
    the fragment and the user part are left out, and "..." marks where.
    The URL comes from the network, so its control characters are
    escaped. A URL that doesn't split prints as a placeholder.
    """
    # Escaped first: urlsplit drops tabs and newlines. The escapes are
    # only backslashes, x and hex digits, so they don't change the split.
    try:
        parts = urlsplit(_escape_control_characters(url))
        _check_bracketed_netloc(parts.netloc)
    except ValueError:
        return '<a URL that couldn\'t be read>'
    host = parts.netloc
    if '@' in host:
        host = '...@' + host.rpartition('@')[2]
    shown = f'{parts.scheme}://{host}{parts.path}'
    if parts.query:
        shown += '?...'
    if parts.fragment:
        shown += '#...'
    return shown


def _escape_control_characters(text):
    return _URL_CONTROL_CHARACTERS.sub(
        lambda m: f'\\x{ord(m.group()):02x}', text
    )


def _shown_error(error, url):
    """error's text, with any query string or fragment in it left out.

    botocore's and urllib3's errors repeat the URL, query string
    included, for example "Max retries exceeded with url: /x?sig=...".
    url's own query string and fragment go wherever they appear after
    their "?" or "#", and so does any other "?" or "#" part that follows
    a URL or path.
    """
    text = str(error)
    try:
        parts = urlsplit(url)
    except ValueError:
        parts = None
    if parts is not None:
        # With its "?" or "#", so a short one like "?1" doesn't turn
        # every "1" in the text into "...".
        for mark, secret in (('?', parts.query), ('#', parts.fragment)):
            if secret:
                text = text.replace(mark + secret, mark + '...')
    text = _ERROR_URL_QUERY.sub(r'\1...', text)
    return _escape_control_characters(text)


def extract_safely(archive, destination):
    """Extract only regular files and directories inside destination."""
    root = os.path.realpath(destination)
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        for member in members:
            path = os.path.realpath(os.path.join(root, member.name))
            if not (member.isfile() or member.isdir()) or not (
                path == root or path.startswith(root + os.sep)
            ):
                raise ConfigurationError(
                    f'The {CREDENTIAL_DAEMON_PRODUCT} archive has '
                    'an unexpected entry: '
                    f'{member.name}'
                )
        if hasattr(tarfile, 'data_filter'):
            tar.extractall(root, members=members, filter='data')
        else:
            tar.extractall(root, members=members)


def _read_capped(response, url):
    """The response's body, or an error once it passes the size limit.

    Reads at most one chunk past the limit, whatever Content-Length says.
    """
    too_large = ConfigurationError(
        f'{_shown_url(url)} is larger than expected.'
    )
    length = response.headers.get('Content-Length')
    if (
        isinstance(length, str)
        and length.isascii()
        and length.isdigit()
        # int() refuses more than 4300 digits.
        and (len(length) > 18 or int(length) > _MAX_DOWNLOAD_BYTES)
    ):
        raise too_large
    chunks = []
    size = 0
    try:
        for chunk in response.raw.stream(_DOWNLOAD_CHUNK_BYTES):
            size += len(chunk)
            if size > _MAX_DOWNLOAD_BYTES:
                raise too_large
            chunks.append(chunk)
    except ConfigurationError:
        raise
    except Exception as e:
        raise ConfigurationError(
            f'Couldn\'t download {_shown_url(url)}: {_shown_error(e, url)}'
        ) from None
    return b''.join(chunks)


class ReleaseSource:
    """Reads the latest release from GitHub, downloads its files, and checks
    their signatures. The host supplies the HTTP session and the checking
    tools' runner. ``verify`` is the CA bundle to check GitHub's
    certificates with (``AWS_CA_BUNDLE``, ``ca_bundle`` or ``--ca-bundle``),
    or None for the default."""

    def __init__(self, host, verify=None):
        self.host = host
        self.verify = verify

    def latest_release(self):
        """The latest release's tag, version and assets.

        The tag comes from where github.com's releases/latest redirects:
        exactly the release's tag page. ``assets`` maps each of the
        release's known file names to its download URL, built from the
        tag. Refuses a release whose tag isn't a version, before anything
        is downloaded.
        """
        response = self._send(_LATEST_RELEASE_URL)
        try:
            location = None
            if response.status_code in _REDIRECTS:
                location = response.headers.get('Location', '')
        finally:
            response.raw.close()
        unreadable = ConfigurationError(
            f'Couldn\'t read {CREDENTIAL_DAEMON_PRODUCT}\'s '
            'latest release from GitHub.'
        )
        if location is None:
            # A page instead of the redirect, such as from a repository
            # with no releases yet, or a proxy that answers for GitHub,
            # names no tag.
            if response.status_code == 200:
                raise unreadable
            raise ConfigurationError(
                f'Couldn\'t download {_shown_url(_LATEST_RELEASE_URL)}: '
                f'HTTP {response.status_code}'
            )
        try:
            url = urljoin(_LATEST_RELEASE_URL, location)
        except ValueError:
            raise _refused(location) from None
        if (
            not isinstance(url, str)
            or not url.startswith(_RELEASE_TAG_URL)
            or _URL_CONTROL_CHARACTERS.search(url)
        ):
            raise _refused(url)
        tag = url[len(_RELEASE_TAG_URL) :]
        # Only a tag that reads as a version gets into a URL.
        version = _release_version(tag)
        return _Release(tag, version, _release_assets(tag))

    def download(self, release, name, path):
        url = release.assets[name]
        # Only from the release the version came from: an asset pointing
        # at another release or repository isn't the release the tag
        # names.
        _check_asset_url(url, release.tag, name)
        missing = ConfigurationError(
            f'{CREDENTIAL_DAEMON_PRODUCT}\'s {_shown_tag(release.tag)} '
            f'release has no {strip_control_characters(name)}, so it '
            'wasn\'t installed.'
        )
        content = self.fetch(
            url,
            lambda location: _check_asset_redirect(location, release.tag),
            missing=missing,
        )
        with open(path, 'wb') as f:
            f.write(content)

    def fetch(self, url, check_url=None, missing=None):
        """GET url, following redirects that pass ``check_url``. With
        ``missing``, a 404 on url itself raises it."""
        check_url = check_url or _check_url
        first = url
        for _ in range(_MAX_REDIRECTS + 1):
            check_url(url)
            response = self._send(url)
            try:
                if response.status_code in _REDIRECTS:
                    location = response.headers.get('Location', '')
                    try:
                        url = urljoin(url, location)
                    except ValueError:
                        # A Location that doesn't split, such as
                        # https://[::1.
                        raise _refused(location) from None
                    continue
                # Only on the asset's own URL: a 404 from the storage host
                # after a good redirect is a broken download, not an asset
                # the release lacks.
                if (
                    missing is not None
                    and url == first
                    and response.status_code == 404
                ):
                    raise missing
                if response.status_code != 200:
                    raise ConfigurationError(
                        f'Couldn\'t download {_shown_url(url)}: '
                        f'HTTP {response.status_code}'
                    )
                return _read_capped(response, url)
            finally:
                # Drops the connection if the body wasn't read to its end.
                response.raw.close()
        raise ConfigurationError(
            f'Too many redirects downloading {_shown_url(url)}.'
        )

    def _send(self, url):
        """One GET of url, streamed so the body is read only up to the
        size limit. Not redirected: the caller checks each hop."""
        session = self.host.http_session or self._session(url)
        request = AWSRequest(
            method='GET',
            url=url,
            headers={'User-Agent': _USER_AGENT},
            stream_output=True,
        ).prepare()
        try:
            return session.send(request)
        except Exception as e:
            # from None: with --debug the CLI logs the traceback, and
            # the chained error has the whole URL.
            message = (
                f'Couldn\'t download {_shown_url(url)}: '
                f'{_shown_error(e, url)}'
            )
            if self.host.system == 'linux' and self._may_be_proxy(e):
                # Install runs under sudo there, which drops the proxy
                # settings unless they're kept.
                message += f'\n{self.host.proxy_hint()}'
            raise ConfigurationError(message) from None

    def _may_be_proxy(self, error):
        """Whether a failed request may have needed a proxy's settings:
        a connection that failed, or a TLS failure without a CA bundle
        (a proxy that inspects TLS). Not an HTTP error, which a server
        answered, nor a TLS failure with a bundle that sudo kept.

        The classes come from botocore.exceptions, as httpsession raises
        them: awscli.botocore.exceptions is the same file loaded as a
        second module, so a real EndpointConnectionError isn't an
        instance of its ConnectionError."""
        if isinstance(error, botocore_exceptions.SSLError):
            return self.verify is None
        return isinstance(
            error,
            (
                botocore_exceptions.ConnectionError,
                botocore_exceptions.ConnectionClosedError,
            ),
        )

    def _session(self, url):
        """A session for url, through the environment's proxies (unless
        NO_PROXY skips them for its host) and with the CLI's CA bundle."""
        verify = True if self.verify is None else self.verify
        return URLLib3Session(proxies=get_environ_proxies(url), verify=verify)

    def verify_pgp_signature(self, archive, signature, tmp):
        gpg = find_gpg()
        options, keyfile = gpg_keyring(
            gpg, tmp, CREDENTIAL_DAEMON_PGP_KEY, 'release-key.asc'
        )
        # Unlike aws update, which judges only --verify, a failed import is
        # an error here: install runs as root and installs a program that
        # gets secrets, so it stops on gpg's own import error rather than
        # going on to a verify that can only fail. The import is judged by
        # gpg's IMPORT_OK status line for the pinned key, not its exit
        # code, which can be non-zero for a warning about a key that
        # imported. --verify and the pinned VALIDSIG below stay the gate.
        imported = self.host.run_tool(
            options + ['--status-fd', '1', '--import', keyfile]
        )
        if not _imported_pinned_key(imported.stdout):
            raise ConfigurationError(
                f'Couldn\'t load {CREDENTIAL_DAEMON_PRODUCT}\'s '
                'signing key into gpg:\n'
                f'{printable_lines(imported.stderr) or _exit(imported)}'
            )
        # Besides gpg's exit code, require a good signature by the pinned
        # key's fingerprint, and no expired or revoked key.
        result = self.host.run_tool(
            options + ['--status-fd', '1', '--verify', signature, archive]
        )
        if result.returncode != 0 or not _signed_by_pinned_key(result.stdout):
            raise ConfigurationError(
                f'The {CREDENTIAL_DAEMON_PRODUCT} download\'s '
                'signature didn\'t verify:\n'
                f'{printable_lines(result.stderr) or _exit(result)}'
            )

    def verify_package_signature(self, package):
        result = self.host.run_tool([_PKGUTIL, '--check-signature', package])
        status, notarization, chain = _read_pkgutil_signature(result.stdout)
        signed = status.startswith(
            'signed by a developer certificate issued by Apple'
        )
        notarized = notarization == 'trusted by the Apple notary service'
        # The leaf certificate, the chain's first entry, is the signer's.
        ours = (
            bool(chain)
            and chain[0].startswith('Developer ID Installer: ')
            and chain[0].endswith(f'({CREDENTIAL_DAEMON_TEAM_ID})')
        )
        if result.returncode != 0 or not (signed and notarized and ours):
            # pkgutil's own words, such as "no signature" or a revoked
            # certificate, and its exit code.
            shown_status = strip_control_characters(status) or (
                'not in the expected form'
            )
            raise ConfigurationError(
                f'The {CREDENTIAL_DAEMON_PRODUCT} package isn\'t '
                'signed and notarized by '
                f'Amazon (Team ID {CREDENTIAL_DAEMON_TEAM_ID}), '
                'so it wasn\'t installed. pkgutil --check-signature '
                f'(exit {result.returncode}): Status: {shown_status}'
            )

    def verify_package_identifier(self, package, tmp):
        """Check every component of the package is aws-credential-daemon's.

        The signature check alone would accept any package signed with
        Amazon's Team ID. Returns the components' PackageInfo
        ``(identifier, version)`` pairs.
        """
        expanded = os.path.join(tmp, 'expanded')
        result = self.host.run_tool([_PKGUTIL, '--expand', package, expanded])
        components = []
        if result.returncode == 0:
            components = _package_components(expanded)
        if {identifier for identifier, _ in components} != {
            CREDENTIAL_DAEMON_PACKAGE_ID
        }:
            raise ConfigurationError(
                f'The {CREDENTIAL_DAEMON_PRODUCT} package isn\'t '
                f'{CREDENTIAL_DAEMON_PACKAGE_ID}, so it '
                f'wasn\'t installed.'
            )
        return components
