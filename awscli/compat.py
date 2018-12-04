# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at

#     http://aws.amazon.com/apache2.0/

# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import sys
import shlex
import os
import os.path
import platform
import zipfile
import signal
import contextlib

from botocore.compat import six
#import botocore.compat

# If you ever want to import from the vendored six. Add it here and then
# import from awscli.compat. Also try to keep it in alphabetical order.
# This may get large.
advance_iterator = six.advance_iterator
PY3 = six.PY3
queue = six.moves.queue
shlex_quote = six.moves.shlex_quote
StringIO = six.StringIO
BytesIO = six.BytesIO
urlopen = six.moves.urllib.request.urlopen
binary_type = six.binary_type

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


if is_windows:
    default_pager = 'more'
else:
    default_pager = 'less -R'


class StdinMissingError(Exception):
    def __init__(self):
        message = (
            'stdin is required for this operation, but is not available.'
        )
        super(StdinMissingError, self).__init__(message)


class NonTranslatedStdout(object):
    """ This context manager sets the line-end translation mode for stdout.

    It is deliberately set to binary mode so that `\r` does not get added to
    the line ending. This can be useful when printing commands where a
    windows style line ending would casuse errors.
    """

    def __enter__(self):
        if sys.platform == "win32":
            import msvcrt
            self.previous_mode = msvcrt.setmode(sys.stdout.fileno(),
                                                os.O_BINARY)
        return sys.stdout

    def __exit__(self, type, value, traceback):
        if sys.platform == "win32":
            import msvcrt
            msvcrt.setmode(sys.stdout.fileno(), self.previous_mode)


def ensure_text_type(s):
    if isinstance(s, six.text_type):
        return s
    if isinstance(s, six.binary_type):
        return s.decode('utf-8')
    raise ValueError("Expected str, unicode or bytes, received %s." % type(s))


if six.PY3:
    import locale
    import urllib.parse as urlparse

    from urllib.error import URLError

    raw_input = input

    def get_binary_stdin():
        if sys.stdin is None:
            raise StdinMissingError()
        return sys.stdin.buffer

    def get_binary_stdout():
        return sys.stdout.buffer

    def _get_text_writer(stream, errors):
        return stream

    def compat_open(filename, mode='r', encoding=None):
        """Back-port open() that accepts an encoding argument.

        In python3 this uses the built in open() and in python2 this
        uses the io.open() function.

        If the file is not being opened in binary mode, then we'll
        use locale.getpreferredencoding() to find the preferred
        encoding.

        """
        if 'b' not in mode:
            encoding = locale.getpreferredencoding()
        return open(filename, mode, encoding=encoding)

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

else:
    import codecs
    import locale
    import io
    import urlparse

    from urllib2 import URLError

    raw_input = raw_input

    def get_binary_stdin():
        if sys.stdin is None:
            raise StdinMissingError()
        return sys.stdin

    def get_binary_stdout():
        return sys.stdout

    def _get_text_writer(stream, errors):
        # In python3, all the sys.stdout/sys.stderr streams are in text
        # mode.  This means they expect unicode, and will encode the
        # unicode automatically before actually writing to stdout/stderr.
        # In python2, that's not the case.  In order to provide a consistent
        # interface, we can create a wrapper around sys.stdout that will take
        # unicode, and automatically encode it to the preferred encoding.
        # That way consumers can just call get_text_writer(stream) and write
        # unicode to the returned stream.  Note that get_text_writer
        # just returns the stream in the PY3 section above because python3
        # handles this.

        # We're going to use the preferred encoding, but in cases that there is
        # no preferred encoding we're going to fall back to assuming ASCII is
        # what we should use. This will currently break the use of
        # PYTHONIOENCODING, which would require checking stream.encoding first,
        # however, the existing behavior is to only use
        # locale.getpreferredencoding() and so in the hope of not breaking what
        # is currently working, we will continue to only use that.
        encoding = locale.getpreferredencoding()
        if encoding is None:
            encoding = "ascii"

        return codecs.getwriter(encoding)(stream, errors)

    def compat_open(filename, mode='r', encoding=None):
        # See docstring for compat_open in the PY3 section above.
        if 'b' not in mode:
            encoding = locale.getpreferredencoding()
        return io.open(filename, mode, encoding=encoding)

    def bytes_print(statement, stdout=None):
        if stdout is None:
            stdout = sys.stdout

        stdout.write(statement)


def get_stdout_text_writer():
    return _get_text_writer(sys.stdout, errors="strict")


def get_stderr_text_writer():
    return _get_text_writer(sys.stderr, errors="replace")


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
        return shlex_quote(s)


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


def _backport_which(cmd, mode=os.F_OK | os.X_OK, path=None):
    """Given a command, mode, and a PATH string, return the path which
    conforms to the given mode on the PATH, or None if there is no such
    file.
    `mode` defaults to os.F_OK | os.X_OK. `path` defaults to the result
    of os.environ.get("PATH"), or can be overridden with a custom search
    path.
    """
    # Check that a given file can be accessed with the correct mode.
    # Additionally check that `file` is not a directory, as on Windows
    # directories pass the os.access check.
    def _access_check(fn, mode):
        return (os.path.exists(fn) and os.access(fn, mode)
                and not os.path.isdir(fn))

    # If we're given a path with a directory part, look it up directly rather
    # than referring to PATH directories. This includes checking relative to the
    # current directory, e.g. ./script
    if os.path.dirname(cmd):
        if _access_check(cmd, mode):
            return cmd
        return None

    if path is None:
        path = os.environ.get("PATH", os.defpath)
    if not path:
        return None
    path = path.split(os.pathsep)

    if sys.platform == "win32":
        # The current directory takes precedence on Windows.
        if not os.curdir in path:
            path.insert(0, os.curdir)

        # PATHEXT is necessary to check on Windows.
        pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
        # See if the given file matches any of the expected path extensions.
        # This will allow us to short circuit when given "python.exe".
        # If it does match, only test that one, otherwise we have to try
        # others.
        if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
            files = [cmd]
        else:
            files = [cmd + ext for ext in pathext]
    else:
        # On other platforms you don't have things like PATHEXT to tell you
        # what file suffixes are executable, so just pass on cmd as-is.
        files = [cmd]

    seen = set()
    for dir in path:
        normdir = os.path.normcase(dir)
        if not normdir in seen:
            seen.add(normdir)
            for thefile in files:
                name = os.path.join(dir, thefile)
                if _access_check(name, mode):
                    return name
    return None


try:
    from shutil import which
except ImportError:
    which = _backport_which
