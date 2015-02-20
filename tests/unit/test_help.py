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
from awscli.testutils import unittest, FileCreator
import json
import sys
import os

import mock

from awscli.help import PosixHelpRenderer, ExecutableNotFoundError
from awscli.help import WindowsHelpRenderer, ProviderHelpCommand,
from awscli.help import TopicListerCommand, TopicHelpCommand
from awscli.topictags import TopicTagDB


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


class TestHelpCommandBase(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.file_creator = FileCreator()

    def tearDown(self):
        self.file_creator.remove_all()


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

    def test_topic_table(self):
        topic_table = self.cmd.topic_table

        self.assertEqual(len(topic_table), 3)

        # Ensure there is a topics command
        self.assertIn('topics', topic_table)
        self.assertIsInstance(topic_table['topics'], TopicListerCommand)

        # Ensure the topics are there as well
        self.assertIn('topic-name-1', topic_table)
        self.assertIsInstance(topic_table['topic-name-1'], TopicHelpCommand)
        self.assertEqual(topic_table['topic-name-1'].name, 'topic-name-1')

        self.assertIn('topic-name-2', topic_table)
        self.assertIsInstance(topic_table['topic-name-2'], TopicHelpCommand)
        self.assertEqual(topic_table['topic-name-2'].name, 'topic-name-2')

    def test_topics_call(self):
        with mock.patch('awscli.help.TopicListerCommand.__call__') \
                as mock_call:
            self.cmd(['topics'], None)
            mock_call.assert_called()

    def test_topic_call(self):
        with mock.patch('awscli.help.TopicHelpCommand.__call__') as mock_call:
            self.cmd(['topic-name-1'], None)
            mock_call.assert_called()

    @mock.patch('awscli.help.TopicListerCommand.__call__')
    @mock.patch('awscli.help.TopicHelpCommand.__call__')
    @mock.patch('awscli.help.HelpCommand.__call__')
    def test_regular_call(self, help_command, topic_help_command,
                         topic_lister_command):
        self.cmd([], None)
        help_command.assert_called()
        self.assertFalse(topic_lister_command.called)
        self.assertFalse(topic_help_command.called)

    def test_invalid_topic_name(self):
        # This sole purpose of this patch is to remove errors from being
        # printed to screen even when the test passes when running the test
        # suite.
        with mock.patch('sys.stderr'):
            with self.assertRaises(SystemExit):
                self.cmd(['topic-foo'], None)


class TestTopicListerCommand(TestHelpCommandBase):
    def setUp(self):
        super(TestTopicListerCommand, self).setUp()
        self.descriptions = [
            'This describes the first topic',
            'This describes the second topic'
        ]
        self.tags_dict = {
            'topic-name-1': {
                'title': ['The first topic title'],
                'description': [self.descriptions[0]],
                'category': ['General Topics', 'Troubleshooting']
            },
            'topic-name-2': {
                'title': ['The second topic title'],
                'description': [self.descriptions[1]],
                'category': ['General Topics']
            }
        }
        self.topic_tag_db = TopicTagDB(self.tags_dict)
        self.cmd = TopicListerCommand(self.session, self.topic_tag_db)

    def test_event_class(self):
        self.assertEqual(self.cmd.event_class, 'topics')

    def test_name(self):
        self.assertEqual(self.cmd.name, 'topics')

    def test_title(self):
        self.assertEqual(self.cmd.title, 'AWS CLI Topic Guide')

    def test_description(self):
        self.assertIn('This is the AWS CLI Topic Guide', self.cmd.description)

    def test_topic_names(self):
        self.assertEqual(
            sorted(self.cmd.topic_names), ['topic-name-1', 'topic-name-2'])

    def test_categories(self):
        self.assertCountEqual(
            self.cmd.categories,
            {'General Topics':
                ['topic-name-1', 'topic-name-2'],
             'Troubleshooting':
                ['topic-name-1']}
        )

    def test_entries(self):
        ref_entries = {
            'topic-name-1': (
                '`topic-name-1 <topic-name-1.html>`_: %s' 
                % self.descriptions[0]),
            'topic-name-2': (
                '`topic-name-2 <topic-name-2.html>`_: %s'
                % self.descriptions[1])
        }
        self.assertCountEqual(self.cmd.entries, ref_entries)


class TestTopicHelpCommand(TestHelpCommandBase):
    def setUp(self):
        super(TestTopicHelpCommand, self).setUp()
        self.name = 'topic-name-1'
        self.title = 'The first topic title'
        self.description = 'This describes the first topic'
        self.category = 'General Topics'
        self.related_command = 's3'
        self.related_topic = 'foo'
        self.topic_body = 'Hello World!'

        self.tags_dict = {
            self.name: {
                'title': [self.title],
                'description': [self.description],
                'category': [self.category],
                'related command': [self.related_command],
                'related topic': [self.related_topic]
            }
        }
        self.topic_tag_db = TopicTagDB(self.tags_dict)
        self.cmd = TopicHelpCommand(self.session, self.name, self.topic_tag_db)
        self.dir_patch = mock.patch('awscli.topictags.TopicTagDB.topic_dir',
                                    self.file_creator.rootdir)
        self.dir_patch.start()

    def tearDown(self):
        self.dir_patch.stop()
        super(TestTopicHelpCommand, self).tearDown()

    def test_event_class(self):
        self.assertEqual(self.cmd.event_class, 'topics.topic-name-1')

    def test_name(self):
        self.assertEqual(self.cmd.name, self.name)

    def test_title(self):
        self.assertEqual(self.cmd.title, self.title)

    def test_contents(self):
        lines = [
            ':title: ' + self.title,
            ':description: ' + self.description,
            ':related command: ' + self.related_command,
            ':related topic: ' + self.related_topic,
            self.topic_body
        ]
        body = '\n'.join(lines)
        self.file_creator.create_file(self.name + '.rst', body)
        self.assertEqual(self.cmd.contents, self.topic_body)

    def test_contents_no_tags(self):
        lines = [
            self.topic_body
        ]
        body = '\n'.join(lines)
        self.file_creator.create_file(self.name + '.rst', body)
        self.assertEqual(self.cmd.contents, self.topic_body)

    def test_contents_tags_in_body(self):
        lines = [
            ':title: ' + self.title,
            ':description: ' + self.description,
            ':related command: ' + self.related_command
        ]
        body_lines = [
            ':related_topic: ' + self.related_topic,
            self.topic_body,
            ':foo: bar'
        ]
        body = '\n'.join(lines + body_lines)
        ref_body = '\n'.join(body_lines)
        self.file_creator.create_file(self.name + '.rst', body)
        self.assertEqual(self.cmd.contents, ref_body)
