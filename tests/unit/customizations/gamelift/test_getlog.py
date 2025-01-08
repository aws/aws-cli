# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from argparse import Namespace
import os

from botocore.session import get_session

from awscli.testutils import unittest, mock, FileCreator
from awscli.customizations.gamelift.getlog import GetGameSessionLogCommand
from awscli.compat import BytesIO


class TestGetGameSessionLogCommand(unittest.TestCase):
    def setUp(self):
        self.create_client_patch = mock.patch(
            'botocore.session.Session.create_client')
        self.mock_create_client = self.create_client_patch.start()
        self.session = get_session()

        self.client = mock.Mock()
        self.mock_create_client.return_value = self.client

        self.cmd = GetGameSessionLogCommand(self.session)

        self.contents = b'mycontents'
        self.file_creator = FileCreator()
        self.urlopen_patch = mock.patch(
            'awscli.customizations.gamelift.getlog.urlopen')
        self.urlopen_mock = self.urlopen_patch.start()
        self.urlopen_mock.return_value = BytesIO(self.contents)

    def tearDown(self):
        self.create_client_patch.stop()
        self.file_creator.remove_all()
        self.urlopen_patch.stop()

    def test_get_game_session_log(self):
        session_id = 'mysessionid'
        save_as = os.path.join(self.file_creator.rootdir, 'mylog')

        args = [
            '--game-session-id', session_id,
            '--save-as', save_as
        ]
        global_args = Namespace()
        global_args.region = 'us-west-2'
        global_args.endpoint_url = None
        global_args.verify_ssl = None

        presigned_url = 'mypresignedurl'
        self.client.get_game_session_log_url.return_value = {
            'PreSignedUrl': presigned_url
        }

        # Call the command
        self.cmd(args, global_args)

        # Ensure the client was created properly
        self.mock_create_client.assert_called_once_with(
            'gamelift', region_name='us-west-2', endpoint_url=None,
            verify=None
        )

        # Ensure the client was called correctly
        self.client.get_game_session_log_url.assert_called_once_with(
            GameSessionId=session_id)

        # Ensure the presigned url was used
        self.urlopen_mock.assert_called_once_with(presigned_url)

        # Ensure the contents were saved to the file
        with open(save_as, 'rb') as f:
            self.assertEqual(f.read(), self.contents)
