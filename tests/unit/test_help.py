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
from awscli.testutils import mock, unittest, skip_if_windows, FileCreator
import signal
import platform
import json
import sys
import os

from awscli.help import PosixHelpRenderer, ExecutableNotFoundError
from awscli.help import WindowsHelpRenderer, ProviderHelpCommand, HelpCommand
from awscli.help import TopicListerCommand, TopicHelpCommand
from awscli.argparser import HELP_BLURB
from awscli.compat import StringIO


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
    def __init__(self, output_stream=sys.stdout):
        HelpSpyMixin.__init__(self)
        PosixHelpRenderer.__init__(self, output_stream)


class FakeWindowsHelpRenderer(HelpSpyMixin, WindowsHelpRenderer):
    def __init__(self, output_stream=sys.stdout):
        HelpSpyMixin.__init__(self)
        WindowsHelpRenderer.__init__(self, output_stream)


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

    @skip_if_windows('Requires posix system.')
    def test_no_groff_or_mandoc_exists(self):
        renderer = FakePosixHelpRenderer()
        renderer.exists_on_path['groff'] = False
        renderer.exists_on_path['mandoc'] = False
        expected_error = 'Could not find executable named "groff or mandoc"'
        with self.assertRaisesRegex(ExecutableNotFoundError, expected_error):
            renderer.render('foo')

    @skip_if_windows('Requires POSIX system.')
    def test_renderer_falls_back_to_mandoc(self):
        stdout = StringIO()
        renderer = FakePosixHelpRenderer(output_stream=stdout)

        renderer.exists_on_path['groff'] = False
        renderer.exists_on_path['mandoc'] = True
        renderer.mock_popen.communicate.return_value = (b'foo', '')
        renderer.render('foo')
        self.assertEqual(stdout.getvalue(), 'foo\n')

    @skip_if_windows('Requires POSIX system.')
    def test_no_pager_exists(self):
        fake_pager = 'foobar'
        os.environ['MANPAGER'] = fake_pager
        stdout = StringIO()
        renderer = FakePosixHelpRenderer(output_stream=stdout)
        renderer.exists_on_path[fake_pager] = False

        renderer.exists_on_path['groff'] = True
        renderer.mock_popen.communicate.return_value = (b'foo', '')
        renderer.render('foo')
        self.assertEqual(stdout.getvalue(), 'foo\n')

    def test_shlex_split_for_pager_var(self):
        pager_cmd = '/bin/sh -c "col -bx | vim -c \'set ft=man\' -"'
        os.environ['PAGER'] = pager_cmd
        self.assertEqual(self.renderer.get_pager_cmdline(),
                         ['/bin/sh', '-c', "col -bx | vim -c 'set ft=man' -"])

    def test_can_render_contents(self):
        renderer = FakePosixHelpRenderer()
        renderer.exists_on_path['groff'] = True
        renderer.exists_on_path['less'] = True
        renderer.mock_popen.communicate.return_value = ('rendered', '')
        renderer.render('foo')
        self.assertEqual(renderer.popen_calls[-1][0], (['less', '-R'],))

    def test_can_page_output_on_windows(self):
        renderer = FakeWindowsHelpRenderer()
        renderer.mock_popen.communicate.return_value = ('rendered', '')
        renderer.render('foo')
        self.assertEqual(renderer.popen_calls[-1][0], (['more'],))

    @skip_if_windows("Ctrl-C not valid on windows.")
    def test_can_handle_ctrl_c(self):
        class CtrlCRenderer(FakePosixHelpRenderer):
            def _popen(self, *args, **kwargs):
                if self._is_pager_call(args):
                    os.kill(os.getpid(), signal.SIGINT)
                return self.mock_popen

            def _is_pager_call(self, args):
                return 'less' in args[0]

        renderer = CtrlCRenderer()
        renderer.mock_popen.communicate.return_value = ('send to pager', '')
        renderer.exists_on_path['groff'] = True
        renderer.exists_on_path['less'] = True
        renderer.render('foo')
        last_call = renderer.mock_popen.communicate.call_args_list[-1]
        self.assertEqual(last_call, mock.call(input='send to pager'))


class TestHelpCommandBase(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.file_creator = FileCreator()

    def tearDown(self):
        self.file_creator.remove_all()


class TestHelpCommand(TestHelpCommandBase):
    """Test some of the deeper functionality of the HelpCommand

    We do this by subclassing from HelpCommand and ensure it is behaving
    as expected.
    """
    def setUp(self):
        super(TestHelpCommand, self).setUp()
        self.doc_handler_mock = mock.Mock()
        self.subcommand_mock = mock.Mock()
        self.renderer = mock.Mock()

        class SampleHelpCommand(HelpCommand):
            EventHandlerClass = self.doc_handler_mock

            @property
            def subcommand_table(sample_help_cmd_self):
                return {'mycommand': self.subcommand_mock}

        self.cmd = SampleHelpCommand(self.session, None, None, None)
        self.cmd.renderer = self.renderer

    def test_subcommand_call(self):
        self.cmd(['mycommand'], None)
        self.subcommand_mock.assert_called_with([], None)
        self.assertFalse(self.doc_handler_mock.called)

    def test_regular_call(self):
        self.cmd([], None)
        self.assertFalse(self.subcommand_mock.called)
        self.doc_handler_mock.assert_called_with(self.cmd)
        self.assertTrue(self.renderer.render.called)

    def test_invalid_subcommand(self):
        with mock.patch('sys.stderr') as f:
            with self.assertRaises(SystemExit):
                self.cmd(['no-exist-command'], None)
        # We should see the pointer to "aws help" in the error message.
        error_message = ''.join(arg[0][0] for arg in f.write.call_args_list)
        self.assertIn(HELP_BLURB, error_message)


class TestProviderHelpCommand(TestHelpCommandBase):
    def setUp(self):
        super(TestProviderHelpCommand, self).setUp()
        self.session.provider = None
        self.command_table = {}
        self.arg_table = {}
        self.description = None
        self.synopsis = None
        self.usage = None

        # Create a temporary index file for ``aws help [command]`` to use.
        self.tags_dict = {
            'topic-name-1': {},
            'topic-name-2': {}
        }
        json_index = self.file_creator.create_file('index.json', '')
        with open(json_index, 'w') as f:
            json.dump(self.tags_dict, f, indent=4, sort_keys=True)
        self.json_patch = mock.patch(
            'awscli.topictags.TopicTagDB.index_file', json_index)
        self.json_patch.start()

        self.cmd = ProviderHelpCommand(self.session, self.command_table,
                                       self.arg_table, self.description,
                                       self.synopsis, self.usage)

    def tearDown(self):
        self.json_patch.stop()
        super(TestProviderHelpCommand, self).tearDown()

    def test_related_items(self):
        self.assertEqual(self.cmd.related_items, ['aws help topics'])

    def test_subcommand_table(self):
        subcommand_table = self.cmd.subcommand_table

        self.assertEqual(len(subcommand_table), 3)

        # Ensure there is a topics command
        self.assertIn('topics', subcommand_table)
        self.assertIsInstance(subcommand_table['topics'], TopicListerCommand)

        # Ensure the topics are there as well
        self.assertIn('topic-name-1', subcommand_table)
        self.assertIsInstance(subcommand_table['topic-name-1'],
                              TopicHelpCommand)
        self.assertEqual(subcommand_table['topic-name-1'].name, 'topic-name-1')

        self.assertIn('topic-name-2', subcommand_table)
        self.assertIsInstance(subcommand_table['topic-name-2'],
                              TopicHelpCommand)
        self.assertEqual(subcommand_table['topic-name-2'].name,
                         'topic-name-2')


class TestTopicListerCommand(TestHelpCommandBase):
    def setUp(self):
        super(TestTopicListerCommand, self).setUp()
        self.cmd = TopicListerCommand(self.session)

    def test_event_class(self):
        self.assertEqual(self.cmd.event_class, 'topics')

    def test_name(self):
        self.assertEqual(self.cmd.name, 'topics')


class TestTopicHelpCommand(TestHelpCommandBase):
    def setUp(self):
        super(TestTopicHelpCommand, self).setUp()
        self.name = 'topic-name-1'
        self.cmd = TopicHelpCommand(self.session, self.name)

    def test_event_class(self):
        self.assertEqual(self.cmd.event_class, 'topics.topic-name-1')

    def test_name(self):
        self.assertEqual(self.cmd.name, self.name)
