#!/usr/bin/env python
# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.compat import six
from awscli.testutils import mock
from tests.functional.s3 import BaseS3TransferCommandTest


class TestMvCommand(BaseS3TransferCommandTest):

    prefix = 's3 mv '

    def test_cant_mv_object_onto_itself(self):
        cmdline = '%s s3://bucket/key s3://bucket/key' % self.prefix
        stderr = self.run_cmd(cmdline, expected_rc=252)[1]
        self.assertIn('Cannot mv a file onto itself', stderr)

    def test_cant_mv_object_with_implied_name(self):
        # The "key" key name is implied in the dst argument.
        cmdline = '%s s3://bucket/key s3://bucket/' % self.prefix
        stderr = self.run_cmd(cmdline, expected_rc=252)[1]
        self.assertIn('Cannot mv a file onto itself', stderr)

    def test_website_redirect_ignore_paramfile(self):
        full_path = self.files.create_file('foo.txt', 'mycontent')
        cmdline = '%s %s s3://bucket/key.txt --website-redirect %s' % \
            (self.prefix, full_path, 'http://someserver')
        self.parsed_responses = [{'ETag': '"c8afdb36c52cf4727836669019e69222"'}]
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(self.operations_called[0][0].name, 'PutObject')
        # Make sure that the specified web address is used as opposed to the
        # contents of the web address.
        self.assertEqual(
            self.operations_called[0][1]['WebsiteRedirectLocation'],
            'http://someserver'
        )

    def test_metadata_directive_copy(self):
        self.parsed_responses = [
            {"ContentLength": "100", "LastModified": "00:00:00Z"},
            {'ETag': '"foo-1"'},
            {'ETag': '"foo-2"'}
        ]
        cmdline = ('%s s3://bucket/key.txt s3://bucket/key2.txt'
                   ' --metadata-directive REPLACE' % self.prefix)
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 3,
                         self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'HeadObject')
        self.assertEqual(self.operations_called[1][0].name, 'CopyObject')
        self.assertEqual(self.operations_called[2][0].name, 'DeleteObject')
        self.assertEqual(self.operations_called[1][1]['MetadataDirective'],
                         'REPLACE')

    def test_no_metadata_directive_for_non_copy(self):
        full_path = self.files.create_file('foo.txt', 'mycontent')
        cmdline = '%s %s s3://bucket --metadata-directive REPLACE' % \
            (self.prefix, full_path)
        self.parsed_responses = \
            [{'ETag': '"c8afdb36c52cf4727836669019e69222"'}]
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 1,
                         self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'PutObject')
        self.assertNotIn('MetadataDirective', self.operations_called[0][1])

    def test_download_move_with_request_payer(self):
        cmdline = '%s s3://mybucket/mykey %s --request-payer' % (
            self.prefix, self.files.rootdir)

        self.parsed_responses = [
            # Response for HeadObject
            {"ContentLength": 100, "LastModified": "00:00:00Z"},
            # Response for GetObject
            {'ETag': '"foo-1"', 'Body': six.BytesIO(b'foo')},
            # Response for DeleteObject
            {}
        ]

        self.run_cmd(cmdline, expected_rc=0)
        self.assert_operations_called(
            [
                ('HeadObject', {
                    'Bucket': 'mybucket',
                    'Key': 'mykey',
                    'RequestPayer': 'requester',
                }),
                ('GetObject', {
                    'Bucket': 'mybucket',
                    'Key': 'mykey',
                    'RequestPayer': 'requester',
                }),
                ('DeleteObject', {
                    'Bucket': 'mybucket',
                    'Key': 'mykey',
                    'RequestPayer': 'requester',
                })
            ]
        )

    def test_copy_move_with_request_payer(self):
        cmdline = self.prefix
        cmdline += 's3://sourcebucket/sourcekey s3://mybucket/mykey'
        cmdline += ' --request-payer'

        self.parsed_responses = [
            self.head_object_response(),
            self.copy_object_response(),
            self.delete_object_response(),
        ]
        self.run_cmd(cmdline, expected_rc=0)
        self.assert_operations_called(
            [
                self.head_object_request(
                    'sourcebucket', 'sourcekey', RequestPayer='requester'),
                self.copy_object_request(
                    'sourcebucket', 'sourcekey', 'mybucket', 'mykey',
                    RequestPayer='requester'),
                self.delete_object_request(
                    'sourcebucket', 'sourcekey', RequestPayer='requester')
            ]
        )

    def test_with_copy_props(self):
        cmdline = self.prefix
        cmdline += 's3://sourcebucket/sourcekey s3://bucket/key'
        cmdline += ' --copy-props default'

        upload_id = 'upload_id'
        large_tag_set = {'tag-key': 'val' * 3000}
        metadata = {'tag-key': 'tag-value'}
        self.parsed_responses = [
            self.head_object_response(
                Metadata=metadata,
                ContentLength=8 * 1024 ** 2
            ),
            self.get_object_tagging_response(large_tag_set),
            self.create_mpu_response(upload_id),
            self.upload_part_copy_response(),
            self.complete_mpu_response(),
            self.put_object_tagging_response(),
            self.delete_object_response()
        ]
        self.run_cmd(cmdline, expected_rc=0)
        self.assert_operations_called(
            [
                self.head_object_request('sourcebucket', 'sourcekey'),
                self.get_object_tagging_request('sourcebucket', 'sourcekey'),
                self.create_mpu_request('bucket', 'key', Metadata=metadata),
                self.upload_part_copy_request(
                    'sourcebucket', 'sourcekey', 'bucket', 'key', upload_id,
                    CopySourceRange=mock.ANY, PartNumber=1,
                ),
                self.complete_mpu_request('bucket', 'key', upload_id, 1),
                self.put_object_tagging_request(
                    'bucket', 'key', large_tag_set
                ),
                self.delete_object_request('sourcebucket', 'sourcekey')
            ]
        )

    def test_mv_does_not_delete_source_on_failed_put_tagging(self):
        cmdline = self.prefix
        cmdline += 's3://sourcebucket/sourcekey s3://bucket/key'
        cmdline += ' --copy-props default'

        upload_id = 'upload_id'
        large_tag_set = {'tag-key': 'val' * 3000}
        metadata = {'tag-key': 'tag-value'}
        self.parsed_responses = [
            self.head_object_response(
                Metadata=metadata,
                ContentLength=8 * 1024 ** 2
            ),
            self.get_object_tagging_response(large_tag_set),
            self.create_mpu_response(upload_id),
            self.upload_part_copy_response(),
            self.complete_mpu_response(),
            self.access_denied_error_response(),  # PutObjectTagging error
            self.delete_object_response(),
        ]
        self.set_http_status_codes(
            [
                200,  # HeadObject
                200,  # GetObjectTagging
                200,  # CreateMultipartUpload
                200,  # UploadPartCopy
                200,  # CompleteMultipartUpload
                403,  # PutObjectTagging
                200,  # DeleteObject
            ]
        )
        self.run_cmd(cmdline, expected_rc=1)
        self.assert_operations_called(
            [
                self.head_object_request('sourcebucket', 'sourcekey'),
                self.get_object_tagging_request('sourcebucket', 'sourcekey'),
                self.create_mpu_request('bucket', 'key', Metadata=metadata),
                self.upload_part_copy_request(
                    'sourcebucket', 'sourcekey', 'bucket', 'key', upload_id,
                    CopySourceRange=mock.ANY, PartNumber=1,
                ),
                self.complete_mpu_request('bucket', 'key', upload_id, 1),
                self.put_object_tagging_request(
                    'bucket', 'key', large_tag_set
                ),
                self.delete_object_request('bucket', 'key')
            ]
        )
