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
import os
import zipfile

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
urlopen = six.moves.urllib.request.urlopen

# Most, but not all, python installations will have zlib. This is required to
# compress any files we send via a push. If we can't compress, we can still
# package the files in a zip container.
try:
    import zlib
    ZIP_COMPRESSION_MODE = zipfile.ZIP_DEFLATED
except ImportError:
    ZIP_COMPRESSION_MODE = zipfile.ZIP_STORED


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

    binary_stdin = sys.stdin.buffer

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

    binary_stdin = sys.stdin

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
