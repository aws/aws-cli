#!/usr/bin/env python
# Copyright 2012-2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os

from awscli.compat import BytesIO
from awscli.testutils import (
    BaseAWSCommandParamsTest,
    FileCreator,
    skip_if_windows,
)


class TestStreamingOutput(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestStreamingOutput, self).setUp()
        self.files = FileCreator()

    def tearDown(self):
        super(TestStreamingOutput, self).tearDown()
        self.files.remove_all()

    def test_get_media_streaming_output(self):
        cmdline = (
            'kinesis-video-media get-media --stream-name test-stream '
            '--start-selector StartSelectorType=EARLIEST %s'
        )
        self.parsed_response = {
            'ContentType': 'video/webm',
            'Payload': BytesIO(b'testbody'),
        }
        outpath = self.files.full_path('outfile')
        params = {
            'StartSelector': {'StartSelectorType': 'EARLIEST'},
            'StreamName': 'test-stream',
        }
        self.assert_params_for_cmd(cmdline % outpath, params)
        with open(outpath, 'rb') as outfile:
            self.assertEqual(outfile.read(), b'testbody')

    @skip_if_windows('chmod is not supported on Windows')
    def test_streaming_output_file_permissions(self):
        cmdline = (
            'kinesis-video-media get-media --stream-name test-stream '
            '--start-selector StartSelectorType=EARLIEST %s'
        )
        self.parsed_response = {
            'ContentType': 'video/webm',
            'Payload': BytesIO(b'testbody'),
        }
        outpath = self.files.full_path('outfile')
        self.assert_params_for_cmd(cmdline % outpath, ignore_params=True)
        # Mask file type bits to isolate permission bits (rwxrwxrwx)
        self.assertEqual(os.stat(outpath).st_mode & 0o777, 0o600)

    @skip_if_windows('chmod is not supported on Windows')
    def test_streaming_output_does_not_chmod_non_regular_files(self):
        cmdline = (
            'kinesis-video-media get-media --stream-name test-stream '
            '--start-selector StartSelectorType=EARLIEST %s'
        )
        self.parsed_response = {
            'ContentType': 'video/webm',
            'Payload': BytesIO(b'testbody'),
        }
        original_mode = os.stat('/dev/null').st_mode & 0o777
        self.assert_params_for_cmd(cmdline % '/dev/null', ignore_params=True)
        self.assertEqual(os.stat('/dev/null').st_mode & 0o777, original_mode)
