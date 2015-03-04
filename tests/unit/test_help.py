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
from awscli.testutils import unittest
import sys
import os

import mock

from awscli.help import PosixHelpRenderer, ExecutableNotFoundError
from awscli.help import WindowsHelpRenderer


class HelpSpyMixin(object):
    def __init__(self):
        self.exists_on_path = {}
        self.popen_calls = []
        self.mock_popen = mock.Mock()

    def _exists_on_path(self, name):
        return self.exists_on_path.get(name)

    def _popen(self, *args, **kwargs):
        self.popen_calls.append((args, kwargs))
        return self.mock_popen


class FakePosixHelpRenderer(HelpSpyMixin, PosixHelpRenderer):
    pass


class FakeWindowsHelpRenderer(HelpSpyMixin, WindowsHelpRenderer):
    pass


class TestHelpPager(unittest.TestCase):

    def setUp(self):
        self.environ = {}
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()
        self.renderer = PosixHelpRenderer()

    def tearDown(self):
        self.environ_patch.stop()

    def test_no_env_vars(self):
        self.assertEqual(self.renderer.get_pager_cmdline(),
                         self.renderer.PAGER.split())

    def test_manpager(self):
        pager_cmd = 'foobar'
        os.environ['MANPAGER'] = pager_cmd
        self.assertEqual(self.renderer.get_pager_cmdline(),
                         pager_cmd.split())

    def test_pager(self):
        pager_cmd = 'fiebaz'
        os.environ['PAGER'] = pager_cmd
        self.assertEqual(self.renderer.get_pager_cmdline(),
                         pager_cmd.split())

    def test_both(self):
        os.environ['MANPAGER'] = 'foobar'
        os.environ['PAGER'] = 'fiebaz'
        self.assertEqual(self.renderer.get_pager_cmdline(),
                         'foobar'.split())

    def test_manpager_with_args(self):
        pager_cmd = 'less -X'
        os.environ['MANPAGER'] = pager_cmd
        self.assertEqual(self.renderer.get_pager_cmdline(),
                         pager_cmd.split())

    def test_pager_with_args(self):
        pager_cmd = 'less -X --clearscreen'
        os.environ['PAGER'] = pager_cmd
        self.assertEqual(self.renderer.get_pager_cmdline(),
                         pager_cmd.split())

    @unittest.skipIf(sys.platform.startswith('win'), "requires posix system")
    def test_no_groff_exists(self):
        renderer = FakePosixHelpRenderer()
        renderer.exists_on_path['groff'] = False
        with self.assertRaisesRegexp(ExecutableNotFoundError,
                                     'Could not find executable named "groff"'):
            renderer.render('foo')

    def test_shlex_split_for_pager_var(self):
        pager_cmd = '/bin/sh -c "col -bx | vim -c \'set ft=man\' -"'
        os.environ['PAGER'] = pager_cmd
        self.assertEqual(self.renderer.get_pager_cmdline(),
                         ['/bin/sh', '-c', "col -bx | vim -c 'set ft=man' -"])

    def test_can_render_contents(self):
        renderer = FakePosixHelpRenderer()
        renderer.exists_on_path['groff'] = True
        renderer.mock_popen.communicate.return_value = ('rendered', '')
        renderer.render('foo')
        self.assertEqual(renderer.popen_calls[-1][0], (['less', '-R'],))

    def test_can_page_output_on_windows(self):
        renderer = FakeWindowsHelpRenderer()
        renderer.mock_popen.communicate.return_value = ('rendered', '')
        renderer.render('foo')
        self.assertEqual(renderer.popen_calls[-1][0], (['more'],))
