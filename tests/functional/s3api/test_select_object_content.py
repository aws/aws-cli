#!/usr/bin/env python
# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import awscli.clidriver
from awscli.testutils import BaseAWSCommandParamsTest
from awscli.testutils import BaseAWSHelpOutputTest


class TestGetObject(BaseAWSCommandParamsTest):

    prefix = ['s3api', 'select-object-content']

    def setUp(self):
        super(TestGetObject, self).setUp()
        self.parsed_response = {'Payload': self.create_fake_payload()}

    def create_fake_payload(self):
        yield {'Records': {'Payload': 'a,b,c,d\n'}}
        # These next two events are ignored because they aren't
        # "Records".
        yield {'Progress': {'Details': {'BytesScanned': 1048576,
                                        'BytesProcessed': 37748736}}}
        yield {'Records': {'Payload': 'e,f,g,h\n'}}
        yield {'Stats': {'Details': {'BytesProcessed': 62605400,
                                     'BytesScanned': 1662276}}}
        yield {'End': {}}

    def remove_file_if_exists(self, filename):
        if os.path.isfile(filename):
            os.remove(filename)

    def test_can_stream_to_file(self):
        cmdline = self.prefix[::]
        cmdline.extend(['--bucket', 'mybucket'])
        cmdline.extend(['--key', 'mykey'])
        cmdline.extend(['--expression', 'SELECT * FROM S3Object'])
        cmdline.extend(['--expression-type', 'SQL'])
        cmdline.extend(['--request-progress', 'Enabled=True'])
        cmdline.extend(['--input-serialization', '{"CSV": {}, "CompressionType": "GZIP"}'])
        cmdline.extend(['--output-serialization', '{"CSV": {}}'])
        cmdline.extend(['outfile'])

        self.addCleanup(self.remove_file_if_exists, 'outfile')
        expected_params = {
            'Bucket': 'mybucket',
            'Key': u'mykey',
            'Expression': 'SELECT * FROM S3Object',
            'ExpressionType': 'SQL',
            'InputSerialization': {'CSV': {}, 'CompressionType': 'GZIP'},
            'OutputSerialization': {'CSV': {}},
            'RequestProgress': {'Enabled': True},
        }
        stdout = self.assert_params_for_cmd(cmdline, expected_params)[0]
        self.assertEqual(stdout, '')
        with open('outfile', 'r') as f:
            contents = f.read()
            self.assertEqual(contents, (
                'a,b,c,d\n'
                'e,f,g,h\n'
            ))

    def test_errors_are_propagated(self):
        self.http_response.status_code = 400
        self.parsed_response = {
            'Error': {
                'Code': 'CastFailed',
                'Message': 'Attempt to convert from one data type to another',
            }
        }
        cmdline = self.prefix + [
            '--bucket', 'mybucket',
            '--key', 'mykey',
            '--expression', 'SELECT * FROM S3Object',
            '--expression-type', 'SQL',
            '--request-progress', 'Enabled=True',
            '--input-serialization', '{"CSV": {}, "CompressionType": "GZIP"}',
            '--output-serialization', '{"CSV": {}}',
            'outfile',
        ]
        expected_params = {
            'Bucket': 'mybucket',
            'Key': u'mykey',
            'Expression': 'SELECT * FROM S3Object',
            'ExpressionType': 'SQL',
            'InputSerialization': {'CSV': {}, 'CompressionType': 'GZIP'},
            'OutputSerialization': {'CSV': {}},
            'RequestProgress': {'Enabled': True},
        }
        self.assert_params_for_cmd(
            cmd=cmdline, params=expected_params,
            expected_rc=255,
            stderr_contains=(
                'An error occurred (CastFailed) when '
                'calling the SelectObjectContent operation'),
        )


class TestHelpOutput(BaseAWSHelpOutputTest):
    def test_output(self):
        self.driver.main(['s3api', 'select-object-content', 'help'])
        # We don't want to be super picky because the wording may change
        # We just want to verify the Output section was customized.
        self.assert_contains(
            'Output\n======\n'
            'This command generates no output'
        )
