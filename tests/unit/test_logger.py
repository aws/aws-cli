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
import logging

import awscrt.io

from awscli.logger import (
    disable_crt_logging,
    enable_crt_logging,
    remove_stream_logger,
    set_stream_logger,
)
from awscli.testutils import mock, unittest


class TestLogger(unittest.TestCase):
    def test_can_set_stream_handler(self):
        set_stream_logger('test_stream_logger', logging.DEBUG)
        log = logging.getLogger('test_stream_logger')
        self.assertEqual(
            log.handlers[0].name, 'test_stream_logger_stream_handler'
        )

    def test_keeps_only_one_stream_handler(self):
        set_stream_logger('test_stream_logger', logging.DEBUG)
        set_stream_logger('test_stream_logger', logging.ERROR)
        log = logging.getLogger('test_stream_logger')
        self.assertEqual(len(log.handlers), 1)
        self.assertEqual(
            log.handlers[0].name, 'test_stream_logger_stream_handler'
        )
        self.assertEqual(log.handlers[0].level, logging.ERROR)

    def test_can_remove_stream_handler(self):
        set_stream_logger('test_stream_logger', logging.DEBUG)
        remove_stream_logger('test_stream_logger')
        log = logging.getLogger('test_stream_logger')
        self.assertEqual(len(log.handlers), 0)

    @mock.patch('awscrt.io.set_log_level')
    def test_can_enable_crt_logging(self, mock_init_logging):
        enable_crt_logging()
        mock_init_logging.assert_called_with(
            awscrt.io.LogLevel.Debug,
        )

    @mock.patch('awscrt.io.set_log_level')
    def test_can_disable_crt_logging(self, mock_init_logging):
        disable_crt_logging()
        mock_init_logging.assert_called_with(
            awscrt.io.LogLevel.NoLogs,
        )
