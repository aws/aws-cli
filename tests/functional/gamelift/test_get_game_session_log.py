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
import os

from awscli.testutils import BaseAWSCommandParamsTest, FileCreator, mock
from awscli.compat import BytesIO


class TestGetGameSessionLog(BaseAWSCommandParamsTest):

    prefix = 'gamelift get-game-session-log'

    def setUp(self):
        super(TestGetGameSessionLog, self).setUp()
        self.files = FileCreator()
        self.filename = os.path.join(self.files.rootdir, 'myfile')
        self.urlopen_patch = mock.patch(
            'awscli.customizations.gamelift.getlog.urlopen')
        self.contents = b'My Contents'
        self.urlopen_mock = self.urlopen_patch.start()
        self.urlopen_mock.return_value = BytesIO(self.contents)

    def tearDown(self):
        super(TestGetGameSessionLog, self).tearDown()
        self.files.remove_all()
        self.urlopen_patch.stop()

    def test_get_game_session_log(self):
        cmdline = self.prefix
        cmdline += ' --game-session-id mysession'
        cmdline += ' --save-as %s' % self.filename

        self.parsed_responses = [{'PreSignedUrl': 'myurl'}]
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(
            self.operations_called[0][0].name, 'GetGameSessionLogUrl')
        self.assertEqual(
            self.operations_called[0][1],
            {'GameSessionId': 'mysession'}
        )

        # Ensure the contents were saved to the file
        self.assertTrue(os.path.exists(self.filename))
        with open(self.filename, 'rb') as f:
            self.assertEqual(f.read(), self.contents)

        # Ensure the output is as expected
        self.assertIn(
            'Successfully downloaded log archive for game session '
            'mysession to %s' % self.filename,
            stdout
        )
