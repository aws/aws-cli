import os
import sys
from contextlib import contextmanager

from mock import Mock, patch

from awscli.testutils import unittest, skip_if_windows
from awscli.testutils import capture_output
from awscli.compat import StringIO

import colorama
from colorama import Fore
from colorama import Back
from colorama.winterm import WinTerm, WinStyle, WinColor


@skip_if_windows('Posix color code tests')
class TestPosix(unittest.TestCase):
    _COLORAMA_KWARGS = {
        'autoreset': True,
        'strip': False,
    }
    _ANSI_RESET_ALL = '\033[0m'
    _ANSI_FORE_RED = '\033[31m'
    _ANSI_FORE_BLUE = '\033[34m'

    def test_fore_attributes(self):
        self.assertEqual(Fore.BLACK, '\033[30m')
        self.assertEqual(Fore.RED, '\033[31m')
        self.assertEqual(Fore.GREEN, '\033[32m')
        self.assertEqual(Fore.YELLOW, '\033[33m')
        self.assertEqual(Fore.BLUE, '\033[34m')
        self.assertEqual(Fore.MAGENTA, '\033[35m')
        self.assertEqual(Fore.CYAN, '\033[36m')
        self.assertEqual(Fore.WHITE, '\033[37m')
        self.assertEqual(Fore.RESET, '\033[39m')

        # Check the light, extended versions.
        self.assertEqual(Fore.LIGHTBLACK_EX, '\033[90m')
        self.assertEqual(Fore.LIGHTRED_EX, '\033[91m')
        self.assertEqual(Fore.LIGHTGREEN_EX, '\033[92m')
        self.assertEqual(Fore.LIGHTYELLOW_EX, '\033[93m')
        self.assertEqual(Fore.LIGHTBLUE_EX, '\033[94m')
        self.assertEqual(Fore.LIGHTMAGENTA_EX, '\033[95m')
        self.assertEqual(Fore.LIGHTCYAN_EX, '\033[96m')
        self.assertEqual(Fore.LIGHTWHITE_EX, '\033[97m')

    def test_back_attributes(self):
        self.assertEqual(Back.BLACK, '\033[40m')
        self.assertEqual(Back.RED, '\033[41m')
        self.assertEqual(Back.GREEN, '\033[42m')
        self.assertEqual(Back.YELLOW, '\033[43m')
        self.assertEqual(Back.BLUE, '\033[44m')
        self.assertEqual(Back.MAGENTA, '\033[45m')
        self.assertEqual(Back.CYAN, '\033[46m')
        self.assertEqual(Back.WHITE, '\033[47m')
        self.assertEqual(Back.RESET, '\033[49m')

        # Check the light, extended versions.
        self.assertEqual(Back.LIGHTBLACK_EX, '\033[100m')
        self.assertEqual(Back.LIGHTRED_EX, '\033[101m')
        self.assertEqual(Back.LIGHTGREEN_EX, '\033[102m')
        self.assertEqual(Back.LIGHTYELLOW_EX, '\033[103m')
        self.assertEqual(Back.LIGHTBLUE_EX, '\033[104m')
        self.assertEqual(Back.LIGHTMAGENTA_EX, '\033[105m')
        self.assertEqual(Back.LIGHTCYAN_EX, '\033[106m')
        self.assertEqual(Back.LIGHTWHITE_EX, '\033[107m')

    @contextmanager
    def colorama_text(self, tty=True):
        with capture_output() as captured:
            captured.stdout.isatty = lambda: tty
            with colorama.colorama_text(**self._COLORAMA_KWARGS):
                yield captured

    def test_colorama_auto_resets(self):
        with self.colorama_text() as captured:
             content = Fore.RED + 'foo'
             sys.stdout.write(content)
             sys.stdout.write('bar')
        # Since auto-reset is enabled each call to write should end with the
        # reset code. And foo should start with the red foreground code. This
        # also depends on the strip=False behavior to pass on windows.
        self.assertEqual(captured.stdout.getvalue(),
                         '%sfoo%sbar%s' % (self._ANSI_FORE_RED,
                                           self._ANSI_RESET_ALL,
                                           self._ANSI_RESET_ALL))

    def test_colorama_does_not_strip(self):
        # Strip is set to False which means that it doesn't remove ansi codes
        # from the output if its a pipe.
        with self.colorama_text() as captured:
            content = Fore.BLUE + 'foo'
            sys.stdout.write(content)
            self.assertEqual(captured.stdout.getvalue(),
                             '%sfoo%s' % (self._ANSI_FORE_BLUE,
                                          self._ANSI_RESET_ALL))

    def test_colorama_does_not_strip_non_tty(self):
        with self.colorama_text(tty=False) as captured:
            content = Fore.BLUE + 'foo'
            sys.stdout.write(content)
            self.assertEqual(captured.stdout.getvalue(),
                             '%sfoo%s' % (self._ANSI_FORE_BLUE,
                                          self._ANSI_RESET_ALL))



@unittest.skipUnless(sys.platform.startswith("win"), "requires Windows")
class WinTermTest(unittest.TestCase):
    @patch('colorama.winterm.win32')
    def test_init(self, mockWin32):
        mockAttr = Mock()
        mockAttr.wAttributes = 7 + 6 * 16 + 8
        mockWin32.GetConsoleScreenBufferInfo.return_value = mockAttr
        term = WinTerm()
        self.assertEqual(term._fore, 7)
        self.assertEqual(term._back, 6)
        self.assertEqual(term._style, 8)

    def test_get_attrs(self):
        term = WinTerm()

        term._fore = 0
        term._back = 0
        term._style = 0
        self.assertEqual(term.get_attrs(), 0)

        term._fore = WinColor.YELLOW
        self.assertEqual(term.get_attrs(), WinColor.YELLOW)

        term._back = WinColor.MAGENTA
        self.assertEqual(
            term.get_attrs(),
            WinColor.YELLOW + WinColor.MAGENTA * 16)

        term._style = WinStyle.BRIGHT
        self.assertEqual(
            term.get_attrs(),
            WinColor.YELLOW + WinColor.MAGENTA * 16 + WinStyle.BRIGHT)

    @patch('colorama.winterm.win32')
    def test_reset_all(self, mockWin32):
        mockAttr = Mock()
        mockAttr.wAttributes = 1 + 2 * 16 + 8
        mockWin32.GetConsoleScreenBufferInfo.return_value = mockAttr
        term = WinTerm()

        term.set_console = Mock()
        term._fore = -1
        term._back = -1
        term._style = -1

        term.reset_all()

        self.assertEqual(term._fore, 1)
        self.assertEqual(term._back, 2)
        self.assertEqual(term._style, 8)
        self.assertEqual(term.set_console.called, True)

    @unittest.skipUnless(sys.platform.startswith("win"), "requires Windows")
    def test_fore(self):
        term = WinTerm()
        term.set_console = Mock()
        term._fore = 0

        term.fore(5)

        self.assertEqual(term._fore, 5)
        self.assertEqual(term.set_console.called, True)

    @unittest.skipUnless(sys.platform.startswith("win"), "requires Windows")
    def test_back(self):
        term = WinTerm()
        term.set_console = Mock()
        term._back = 0

        term.back(5)

        self.assertEqual(term._back, 5)
        self.assertEqual(term.set_console.called, True)

    @unittest.skipUnless(sys.platform.startswith("win"), "requires Windows")
    def test_style(self):
        term = WinTerm()
        term.set_console = Mock()
        term._style = 0

        term.style(22)

        self.assertEqual(term._style, 22)
        self.assertEqual(term.set_console.called, True)

    @patch('colorama.winterm.win32')
    def test_set_console(self, mockWin32):
        mockAttr = Mock()
        mockAttr.wAttributes = 0
        mockWin32.GetConsoleScreenBufferInfo.return_value = mockAttr
        term = WinTerm()
        term.windll = Mock()

        term.set_console()

        self.assertEqual(
            mockWin32.SetConsoleTextAttribute.call_args,
            ((mockWin32.STDOUT, term.get_attrs()), {})
        )

    @patch('colorama.winterm.win32')
    def test_set_console_on_stderr(self, mockWin32):
        mockAttr = Mock()
        mockAttr.wAttributes = 0
        mockWin32.GetConsoleScreenBufferInfo.return_value = mockAttr
        term = WinTerm()
        term.windll = Mock()

        term.set_console(on_stderr=True)

        self.assertEqual(
            mockWin32.SetConsoleTextAttribute.call_args,
            ((mockWin32.STDERR, term.get_attrs()), {})
        )
