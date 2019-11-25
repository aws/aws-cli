# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import uuid

from botocore.history import HistoryRecorder

from awscli.testutils import mock, create_clidriver, FileCreator
from awscli.testutils import BaseAWSCommandParamsTest


class BaseHistoryCommandParamsTest(BaseAWSCommandParamsTest):
    def setUp(self):
        history_recorder = self._make_clean_history_recorder()
        super(BaseHistoryCommandParamsTest, self).setUp()
        self.history_recorder = history_recorder
        self.files = FileCreator()
        config_contents = (
            '[default]\n'
            'cli_history = enabled'
        )
        self.environ['AWS_CONFIG_FILE'] = self.files.create_file(
            'config', config_contents)
        self.environ['AWS_CLI_HISTORY_FILE'] = self.files.create_file(
            'history.db', '')
        self.driver = create_clidriver()

    def _make_clean_history_recorder(self):
        # This is to ensure that for each new test run the CLI is using
        # a brand new HistoryRecorder as this is global so previous test
        # runs could have injected handlers onto it as all of the tests
        # are ran in the same process.
        history_recorder = HistoryRecorder()

        # The HISTORY_RECORDER is instantiated on module import before we
        # doing any patching which means we cannot simply patch
        # botocore.get_global_history_recorder as the objects are already
        # instantiated as so we have to individually patch each one of these...
        self._apply_history_recorder_patch(
            'awscli.clidriver', history_recorder)
        self._apply_history_recorder_patch(
            'awscli.customizations.history', history_recorder)
        return history_recorder

    def _apply_history_recorder_patch(self, module, history_recorder):
        patch_history_recorder = mock.patch(
            module + '.HISTORY_RECORDER', history_recorder)
        patch_history_recorder.start()
        self.addCleanup(patch_history_recorder.stop)

    def _cleanup_db_connections(self):
        # Reaching into private data to close out the database connection.
        # Windows won't let us delete the tempdir until these connections are
        # closed in the tearDown step and we have no other way of forcing
        # them to close.
        handlers = self.history_recorder._handlers
        for handler in handlers:
            handler._writer.close()

    def tearDown(self):
        super(BaseHistoryCommandParamsTest, self).tearDown()
        self._cleanup_db_connections()
        self.files.remove_all()
