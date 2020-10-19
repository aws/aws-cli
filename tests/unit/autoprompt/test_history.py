# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import json

import mock
import os
import shutil
import tempfile

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import History
from prompt_toolkit.formatted_text import FormattedText

from awscli.autoprompt.history import (
    HistoryCompleter, HistoryDriver
)
from awscli.testutils import unittest


class TestHistoryCompleter(unittest.TestCase):
    def setUp(self):
        self.strings = [
            'chime associate-phone-number-with-user',
            'opsworks-cm associate-node',
            'deploy add-tags-to-on-premises-instances',
            's3 ls',
        ]
        self.buffer = mock.Mock(spec=Buffer)
        history = mock.Mock(spec=History)
        history.get_strings.return_value = self.strings
        self.buffer.history = history
        self.completer = HistoryCompleter(buffer=self.buffer)

    def test_get_completions_on_empty_document(self):
        document = Document('')
        strings = self.completer.get_completions(document)
        self.assertEqual(
            list(strings),
            [Completion(text='s3 ls', start_position=0,
                        display=FormattedText([('', 's3 ls')])),
             Completion(text='deploy add-tags-to-on-premises-instances',
                        start_position=0, display=FormattedText([('',
                        'deploy add-tags-to-on-premises-instances')])),
             Completion(text='opsworks-cm associate-node',
                        start_position=0, display=FormattedText(
                        [('', 'opsworks-cm associate-node')])),
             Completion(text='chime associate-phone-number-with-user',
                        start_position=0, display=FormattedText([('',
                        'chime associate-phone-number-with-user')]))
            ]
        )

    def test_get_completions_with_fuzzy_search(self):
        document = Document('omine')
        strings = self.completer.get_completions(document)
        self.assertEqual(
            list(strings),
            [Completion(text='opsworks-cm associate-node',
                        start_position=-5, display=FormattedText(
                        [('', 'opsworks-cm associate-node')])),
             Completion(text='deploy add-tags-to-on-premises-instances',
                        start_position=-5, display=FormattedText([('',
                        'deploy add-tags-to-on-premises-instances')]))
            ]
        )

    def test_show_newest_duplicated_command(self):
        strings = [
            'chime associate-phone-number-with-user',
            's3 ls',
            's3api list-buckets',
            's3 ls'
        ]
        history = mock.Mock(spec=History)
        history.get_strings.return_value = strings
        self.buffer.history = history
        self.completer = HistoryCompleter(buffer=self.buffer)
        document = Document('')
        response = self.completer.get_completions(document)
        self.assertEqual(
            list(response),
            [Completion(text='s3 ls',
                        start_position=0, display=FormattedText(
                        [('', 's3 ls')])),
             Completion(text='s3api list-buckets',
                        start_position=0, display=FormattedText([('',
                        's3api list-buckets')])),
             Completion(text='chime associate-phone-number-with-user',
                        start_position=0, display=FormattedText([('',
                        'chime associate-phone-number-with-user')]))
            ]
        )


class TestHistoryDriver(unittest.TestCase):
    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.filename = os.path.join(self.dirname, 'prompt_history.json')
        self.history_driver = HistoryDriver(self.filename)

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_store_string(self):
        self.history_driver.store_string('aws ec2 describe-instances')
        with open(self.filename, 'r') as f:
            history = json.load(f)
        self.assertEqual(
            history,
            {'version': 1, 'commands': ['aws ec2 describe-instances']}
        )

    def test_creates_folder_and_file(self):
        non_existing_path = os.path.join(self.dirname, 'foo', 'history.json')
        history_driver = HistoryDriver(non_existing_path)
        history_driver.store_string('aws ec2 describe-instances')
        self.assertTrue(os.path.exists(non_existing_path))

    def test_read_after_write_in_reversed_order(self):
        history_driver = HistoryDriver(self.filename)
        history_driver.store_string('aws ec2 describe-instances')
        history_driver.store_string('aws s3 ls')
        history_driver.store_string('aws dynamodb create-table')
        commands = history_driver.load_history_strings()
        self.assertEqual(
            list(commands),
            ['aws dynamodb create-table',
             'aws s3 ls',
             'aws ec2 describe-instances'
             ]
        )

    def test_keep_last_max_commands(self):
        history_driver = HistoryDriver(self.filename, max_commands=2)
        history_driver.store_string('aws ec2 describe-instances')
        history_driver.store_string('aws s3 ls')
        history_driver.store_string('aws dynamodb create-table')
        with open(self.filename, 'r') as f:
            commands = json.load(f)['commands']
        self.assertEqual(
            commands, ['aws s3 ls', 'aws dynamodb create-table']
        )

    @mock.patch('awscli.autoprompt.history.FileHistory')
    def test_handle_io_errors(self, file_history_mock):
        history_driver = HistoryDriver(self.filename)
        file_history_mock.store_string.side_effect = IOError
        history_driver.store_string('aws dynamodb create-table')
