# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import collections.abc as collections_abc
import contextlib
import io
import locale
import os
import os.path
import queue
import re
import shlex
import signal
import urllib.parse as urlparse
from configparser import RawConfigParser
from urllib.error import URLError
from urllib.request import urlopen

from botocore.compat import six, OrderedDict

import sys
import zipfile
from functools import partial

# Backwards compatible definitions from six
PY3 = sys.version_info[0] == 3
advance_iterator = next
shlex_quote = shlex.quote
StringIO = io.StringIO
BytesIO = io.BytesIO
binary_type = bytes
raw_input = input


# Most, but not all, python installations will have zlib. This is required to
# compress any files we send via a push. If we can't compress, we can still
# package the files in a zip container.
try:
    import zlib

    ZIP_COMPRESSION_MODE = zipfile.ZIP_DEFLATED
except ImportError:
    ZIP_COMPRESSION_MODE = zipfile.ZIP_STORED


try:
    import sqlite3
except ImportError:
    sqlite3 = None


is_windows = sys.platform == 'win32'

is_macos = sys.platform == 'darwin'


if is_windows:
    default_pager = 'more'
else:
    default_pager = 'less -R'


class StdinMissingError(Exception):
    def __init__(self):
        message = 'stdin is required for this operation, but is not available.'
        super(StdinMissingError, self).__init__(message)


class NonTranslatedStdout:
    """This context manager sets the line-end translation mode for stdout.

    It is deliberately set to binary mode so that `\r` does not get added to
    the line ending. This can be useful when printing commands where a
    windows style line ending would cause errors.
    """

    def __enter__(self):
        if sys.platform == "win32":
            import msvcrt

            self.previous_mode = msvcrt.setmode(
                sys.stdout.fileno(), os.O_BINARY
            )
        return sys.stdout

    def __exit__(self, type, value, traceback):
        if sys.platform == "win32":
            import msvcrt

            msvcrt.setmode(sys.stdout.fileno(), self.previous_mode)


def ensure_text_type(s):
    if isinstance(s, str):
        return s
    if isinstance(s, bytes):
        return s.decode('utf-8')
    raise ValueError("Expected str, unicode or bytes, received %s." % type(s))


def get_binary_stdin():
    if sys.stdin is None:
        raise StdinMissingError()
    return sys.stdin.buffer


def get_binary_stdout():
    return sys.stdout.buffer


def _get_text_writer(stream, errors):
    return stream


def bytes_print(statement, stdout=None):
    """
    This function is used to write raw bytes to stdout.
    """
    if stdout is None:
        stdout = sys.stdout

    if getattr(stdout, 'buffer', None):
        stdout.buffer.write(statement)
    else:
        # If it is not possible to write to the standard out buffer.
        # The next best option is to decode and write to standard out.
        stdout.write(statement.decode('utf-8'))


def compat_open(filename, mode='r', encoding=None, access_permissions=None):
    """Back-port open() that accepts an encoding argument.

    In python3 this uses the built in open() and in python2 this
    uses the io.open() function.

    If the file is not being opened in binary mode, then we'll
    use locale.getpreferredencoding() to find the preferred
    encoding.

    """
    opener = os.open
    if access_permissions is not None:
        opener = partial(os.open, mode=access_permissions)
    if 'b' not in mode:
        encoding = locale.getpreferredencoding()
    return open(filename, mode, encoding=encoding, opener=opener)


def get_stdout_text_writer():
    return _get_text_writer(sys.stdout, errors="strict")


def get_stderr_text_writer():
    return _get_text_writer(sys.stderr, errors="replace")


def get_stderr_encoding():
    encoding = getattr(sys.__stderr__, 'encoding', None)
    if encoding is None:
        encoding = 'utf-8'
    return encoding


def compat_input(prompt):
    """
    Cygwin's pty's are based on pipes. Therefore, when it interacts with a Win32
    program (such as Win32 python), what that program sees is a pipe instead of
    a console. This is important because python buffers pipes, and so on a
    pty-based terminal, text will not necessarily appear immediately. In most
    cases, this isn't a big deal. But when we're doing an interactive prompt,
    the result is that the prompts won't display until we fill the buffer. Since
    raw_input does not flush the prompt, we need to manually write and flush it.

    See https://github.com/mintty/mintty/issues/56 for more details.
    """
    sys.stdout.write(prompt)
    sys.stdout.flush()
    return raw_input()


def compat_shell_quote(s, platform=None):
    """Return a shell-escaped version of the string *s*

    Unfortunately `shlex.quote` doesn't support Windows, so this method
    provides that functionality.
    """
    if platform is None:
        platform = sys.platform

    if platform == "win32":
        return _windows_shell_quote(s)
    else:
        return shlex.quote(s)


def _windows_shell_quote(s):
    """Return a Windows shell-escaped version of the string *s*

    Windows has potentially bizarre rules depending on where you look. When
    spawning a process via the Windows C runtime the rules are as follows:

    https://docs.microsoft.com/en-us/cpp/cpp/parsing-cpp-command-line-arguments

    To summarize the relevant bits:

    * Only space and tab are valid delimiters
    * Double quotes are the only valid quotes
    * Backslash is interpreted literally unless it is part of a chain that
      leads up to a double quote. Then the backslashes escape the backslashes,
      and if there is an odd number the final backslash escapes the quote.

    :param s: A string to escape
    :return: An escaped string
    """
    if not s:
        return '""'

    buff = []
    num_backspaces = 0
    for character in s:
        if character == '\\':
            # We can't simply append backslashes because we don't know if
            # they will need to be escaped. Instead we separately keep track
            # of how many we've seen.
            num_backspaces += 1
        elif character == '"':
            if num_backspaces > 0:
                # The backslashes are part of a chain that lead up to a
                # double quote, so they need to be escaped.
                buff.append('\\' * (num_backspaces * 2))
                num_backspaces = 0

            # The double quote also needs to be escaped. The fact that we're
            # seeing it at all means that it must have been escaped in the
            # original source.
            buff.append('\\"')
        else:
            if num_backspaces > 0:
                # The backslashes aren't part of a chain leading up to a
                # double quote, so they can be inserted directly without
                # being escaped.
                buff.append('\\' * num_backspaces)
                num_backspaces = 0
            buff.append(character)

    # There may be some leftover backspaces if they were on the trailing
    # end, so they're added back in here.
    if num_backspaces > 0:
        buff.append('\\' * num_backspaces)

    new_s = ''.join(buff)
    if ' ' in new_s or '\t' in new_s:
        # If there are any spaces or tabs then the string needs to be double
        # quoted.
        return '"%s"' % new_s
    return new_s


def get_popen_kwargs_for_pager_cmd(pager_cmd=None):
    """Returns the default pager to use dependent on platform

    :rtype: str
    :returns: A string represent the paging command to run based on the
        platform being used.
    """
    popen_kwargs = {}
    if pager_cmd is None:
        pager_cmd = default_pager
    # Similar to what we do with the help command, we need to specify
    # shell as True to make it work in the pager for Windows
    if is_windows:
        popen_kwargs = {'shell': True}
    else:
        pager_cmd = shlex.split(pager_cmd)
    popen_kwargs['args'] = pager_cmd
    return popen_kwargs


@contextlib.contextmanager
def ignore_user_entered_signals():
    """
    Ignores user entered signals to avoid process getting killed.
    """
    if is_windows:
        signal_list = [signal.SIGINT]
    else:
        signal_list = [signal.SIGINT, signal.SIGQUIT, signal.SIGTSTP]
    actual_signals = []
    for user_signal in signal_list:
        actual_signals.append(signal.signal(user_signal, signal.SIG_IGN))
    try:
        yield
    finally:
        for sig, user_signal in enumerate(signal_list):
            signal.signal(user_signal, actual_signals[sig])


# linux_distribution is used by the CodeDeploy customization. Python 3.8
# removed it from the stdlib, so it is vendored here in the case where the
# import fails.
try:
    from platform import linux_distribution
except ImportError:
    _UNIXCONFDIR = '/etc'

    def _dist_try_harder(distname, version, id):
        """Tries some special tricks to get the distribution
        information in case the default method fails.
        Currently supports older SuSE Linux, Caldera OpenLinux and
        Slackware Linux distributions.
        """
        if os.path.exists('/var/adm/inst-log/info'):
            # SuSE Linux stores distribution information in that file
            distname = 'SuSE'
            with open('/var/adm/inst-log/info') as f:
                for line in f:
                    tv = line.split()
                    if len(tv) == 2:
                        tag, value = tv
                    else:
                        continue
                    if tag == 'MIN_DIST_VERSION':
                        version = value.strip()
                    elif tag == 'DIST_IDENT':
                        values = value.split('-')
                        id = values[2]
            return distname, version, id

        if os.path.exists('/etc/.installed'):
            # Caldera OpenLinux has some infos in that file (thanks to Colin Kong)
            with open('/etc/.installed') as f:
                for line in f:
                    pkg = line.split('-')
                    if len(pkg) >= 2 and pkg[0] == 'OpenLinux':
                        # XXX does Caldera support non Intel platforms ? If yes,
                        #     where can we find the needed id ?
                        return 'OpenLinux', pkg[1], id

        if os.path.isdir('/usr/lib/setup'):
            # Check for slackware version tag file (thanks to Greg Andruk)
            verfiles = os.listdir('/usr/lib/setup')
            for n in range(len(verfiles) - 1, -1, -1):
                if verfiles[n][:14] != 'slack-version-':
                    del verfiles[n]
            if verfiles:
                verfiles.sort()
                distname = 'slackware'
                version = verfiles[-1][14:]
                return distname, version, id

        return distname, version, id

    _release_filename = re.compile(r'(\w+)[-_](release|version)', re.ASCII)
    _lsb_release_version = re.compile(
        r'(.+) release ([\d.]+)[^(]*(?:\((.+)\))?', re.ASCII
    )
    _release_version = re.compile(
        r'([^0-9]+)(?: release )?([\d.]+)[^(]*(?:\((.+)\))?',
        re.ASCII,
    )

    # See also http://www.novell.com/coolsolutions/feature/11251.html
    # and http://linuxmafia.com/faq/Admin/release-files.html
    # and http://data.linux-ntfs.org/rpm/whichrpm
    # and http://www.die.net/doc/linux/man/man1/lsb_release.1.html

    _supported_dists = (
        'SuSE',
        'debian',
        'fedora',
        'redhat',
        'centos',
        'mandrake',
        'mandriva',
        'rocks',
        'slackware',
        'yellowdog',
        'gentoo',
        'UnitedLinux',
        'turbolinux',
        'arch',
        'mageia',
    )

    def _parse_release_file(firstline):
        # Default to empty 'version' and 'id' strings.  Both defaults are used
        # when 'firstline' is empty.  'id' defaults to empty when an id can not
        # be deduced.
        version = ''
        id = ''

        # Parse the first line
        m = _lsb_release_version.match(firstline)
        if m is not None:
            # LSB format: "distro release x.x (codename)"
            return tuple(m.groups())

        # Pre-LSB format: "distro x.x (codename)"
        m = _release_version.match(firstline)
        if m is not None:
            return tuple(m.groups())

        # Unknown format... take the first two words
        l = firstline.strip().split()
        if l:
            version = l[0]
            if len(l) > 1:
                id = l[1]
        return '', version, id

    _distributor_id_file_re = re.compile("(?:DISTRIB_ID\s*=)\s*(.*)", re.I)
    _release_file_re = re.compile("(?:DISTRIB_RELEASE\s*=)\s*(.*)", re.I)
    _codename_file_re = re.compile("(?:DISTRIB_CODENAME\s*=)\s*(.*)", re.I)

    def linux_distribution(
        distname='',
        version='',
        id='',
        supported_dists=_supported_dists,
        full_distribution_name=1,
    ):
        return _linux_distribution(
            distname, version, id, supported_dists, full_distribution_name
        )

    def _linux_distribution(
        distname, version, id, supported_dists, full_distribution_name
    ):
        """Tries to determine the name of the Linux OS distribution name.
        The function first looks for a distribution release file in
        /etc and then reverts to _dist_try_harder() in case no
        suitable files are found.
        supported_dists may be given to define the set of Linux
        distributions to look for. It defaults to a list of currently
        supported Linux distributions identified by their release file
        name.
        If full_distribution_name is true (default), the full
        distribution read from the OS is returned. Otherwise the short
        name taken from supported_dists is used.
        Returns a tuple (distname, version, id) which default to the
        args given as parameters.
        """
        # check for the Debian/Ubuntu /etc/lsb-release file first, needed so
        # that the distribution doesn't get identified as Debian.
        # https://bugs.python.org/issue9514
        try:
            with open("/etc/lsb-release") as etclsbrel:
                for line in etclsbrel:
                    m = _distributor_id_file_re.search(line)
                    if m:
                        _u_distname = m.group(1).strip()
                    m = _release_file_re.search(line)
                    if m:
                        _u_version = m.group(1).strip()
                    m = _codename_file_re.search(line)
                    if m:
                        _u_id = m.group(1).strip()
                if _u_distname and _u_version:
                    return (_u_distname, _u_version, _u_id)
        except (OSError, UnboundLocalError):
            pass

        try:
            etc = os.listdir(_UNIXCONFDIR)
        except OSError:
            # Probably not a Unix system
            return distname, version, id
        etc.sort()
        for file in etc:
            m = _release_filename.match(file)
            if m is not None:
                _distname, dummy = m.groups()
                if _distname in supported_dists:
                    distname = _distname
                    break
        else:
            return _dist_try_harder(distname, version, id)

        # Read the first line
        with open(
            os.path.join(_UNIXCONFDIR, file),
            encoding='utf-8',
            errors='surrogateescape',
        ) as f:
            firstline = f.readline()
        _distname, _version, _id = _parse_release_file(firstline)

        if _distname and full_distribution_name:
            distname = _distname
        if _version:
            version = _version
        if _id:
            id = _id
        return distname, version, id
