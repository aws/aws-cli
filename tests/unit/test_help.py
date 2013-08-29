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
from tests import unittest
import os

import mock

from awscli.help import PosixHelpRenderer, ExecutableNotFoundError


class FakePosixHelpRenderer(PosixHelpRenderer):
    def __init__(self):
        self.exists_on_path = {}
        self.popen_calls = []

    def _exists_on_path(self, name):
        return self.exists_on_path.get(name)

    def _popen(self, *args, **kwargs):
        self.popen_calls.append((args, kwargs))
        return mock.Mock()


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

    @mock.patch('sys.exit', mock.Mock())
    def test_with_rst2man_py_exists(self):
        renderer = FakePosixHelpRenderer()
        renderer.exists_on_path['rst2man.py'] = True
        renderer.exists_on_path['rst2man'] = False
        renderer.exists_on_path['groff'] = True
        renderer.render('foo')
        # First call should be to rst2man.py not rst2man
        # List of tuples, so the first popen call's first position args
        # first element is the cmdlist ['rst2man.py']
        self.assertEqual(renderer.popen_calls[0][0][0], ['rst2man.py'])

    @mock.patch('sys.exit', mock.Mock())
    def test_with_rst2man_py_does_not_exist(self):
        renderer = FakePosixHelpRenderer()
        renderer.exists_on_path['rst2man.py'] = False
        renderer.exists_on_path['rst2man'] = True
        renderer.exists_on_path['groff'] = True
        renderer.render('foo')
        # First call should be to rst2man not rst2man.py
        self.assertEqual(renderer.popen_calls[0][0][0], ['rst2man'])

    @mock.patch('sys.exit', mock.Mock())
    def test_no_rst2man_exists(self):
        renderer = FakePosixHelpRenderer()
        # Simulate neither rst2man.py nor rst2man existing on the path.
        renderer.exists_on_path['rst2man.py'] = False
        renderer.exists_on_path['rst2man'] = False
        with self.assertRaisesRegexp(ExecutableNotFoundError,
                                     'Could not find executable named "rst2man.py"'):
            renderer.render('foo')
