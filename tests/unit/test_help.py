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

from awscli.help import PosixHelpRenderer


class TestHelpPager(unittest.TestCase):

    def setUp(self):
        self.renderer = PosixHelpRenderer()
        self.save_pager = os.environ.get('PAGER', None)
        self.save_manpager = os.environ.get('MANPAGER', None)

    def tearDown(self):
        if self.save_pager is not None:
            os.environ['PAGER'] = self.save_pager
        if self.save_manpager is not None:
            os.environ['MANPAGER'] = self.save_manpager

    def test_no_env_vars(self):
        if 'PAGER' in os.environ:
            del os.environ['PAGER']
        if 'MANPAGER' in os.environ:
            del os.environ['MANPAGER']
        self.assertEqual(self.renderer.get_pager_cmdline(),
                         self.renderer.PAGER.split())

    def test_manpager(self):
        pager_cmd = 'foobar'
        if 'PAGER' in os.environ:
            del os.environ['PAGER']
        os.environ['MANPAGER'] = pager_cmd
        self.assertEqual(self.renderer.get_pager_cmdline(),
                         pager_cmd.split())

    def test_pager(self):
        pager_cmd = 'fiebaz'
        if 'MANPAGER' in os.environ:
            del os.environ['MANPAGER']
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
        if 'PAGER' in os.environ:
            del os.environ['PAGER']
        os.environ['MANPAGER'] = pager_cmd
        self.assertEqual(self.renderer.get_pager_cmdline(),
                         pager_cmd.split())

    def test_pager_with_args(self):
        pager_cmd = 'less -X --clearscreen'
        if 'MANPAGER' in os.environ:
            del os.environ['MANPAGER']
        os.environ['PAGER'] = pager_cmd
        self.assertEqual(self.renderer.get_pager_cmdline(),
                         pager_cmd.split())
        
