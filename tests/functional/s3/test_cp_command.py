#!/usr/bin/env python
# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import mock

from awscli.testutils import BaseAWSCommandParamsTest, FileCreator
from awscli.testutils import capture_input
from awscli.compat import six


class TestCPCommand(BaseAWSCommandParamsTest):

    prefix = 's3 cp '

    def setUp(self):
        super(TestCPCommand, self).setUp()
        self.files = FileCreator()

    def tearDown(self):
        super(TestCPCommand, self).tearDown()
        self.files.remove_all()

    def test_operations_used_in_upload(self):
        full_path = self.files.create_file('foo.txt', 'mycontent')
        cmdline = '%s %s s3://bucket/key.txt' % (self.prefix, full_path)
        self.parsed_responses = [{'ETag': '"c8afdb36c52cf4727836669019e69222"'}]
        self.run_cmd(cmdline, expected_rc=0)
        # The only operation we should have called is PutObject.
        self.assertEqual(len(self.operations_called), 1, self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'PutObject')

    def test_key_name_added_when_only_bucket_provided(self):
        full_path = self.files.create_file('foo.txt', 'mycontent')
        cmdline = '%s %s s3://bucket/' % (self.prefix, full_path)
        self.parsed_responses = [{'ETag': '"c8afdb36c52cf4727836669019e69222"'}]
        self.run_cmd(cmdline, expected_rc=0)
        # The only operation we should have called is PutObject.
        self.assertEqual(len(self.operations_called), 1, self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'PutObject')
        self.assertEqual(self.operations_called[0][1]['Key'], 'foo.txt')
        self.assertEqual(self.operations_called[0][1]['Bucket'], 'bucket')

    def test_trailing_slash_appended(self):
        full_path = self.files.create_file('foo.txt', 'mycontent')
        # Here we're saying s3://bucket instead of s3://bucket/
        # This should still work the same as if we added the trailing slash.
        cmdline = '%s %s s3://bucket' % (self.prefix, full_path)
        self.parsed_responses = [{'ETag': '"c8afdb36c52cf4727836669019e69222"'}]
        self.run_cmd(cmdline, expected_rc=0)
        # The only operation we should have called is PutObject.
        self.assertEqual(len(self.operations_called), 1, self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'PutObject')
        self.assertEqual(self.operations_called[0][1]['Key'], 'foo.txt')
        self.assertEqual(self.operations_called[0][1]['Bucket'], 'bucket')

    def test_upload_grants(self):
        full_path = self.files.create_file('foo.txt', 'mycontent')
        cmdline = ('%s %s s3://bucket/key.txt --grants read=id=foo '
                   'full=id=bar readacl=id=biz writeacl=id=baz' %
                   (self.prefix, full_path))
        self.parsed_responses = \
            [{'ETag': '"c8afdb36c52cf4727836669019e69222"'}]
        self.run_cmd(cmdline, expected_rc=0)
        # The only operation we should have called is PutObject.
        self.assertEqual(len(self.operations_called), 1,
                         self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'PutObject')
        self.assertDictEqual(
            self.operations_called[0][1],
            {'Key': u'key.txt', 'Bucket': u'bucket', 'GrantRead': u'id=foo',
             'GrantFullControl': u'id=bar', 'GrantReadACP': u'id=biz',
             'GrantWriteACP': u'id=baz', 'ContentType': u'text/plain',
             'Body': mock.ANY}
        )

    def test_upload_expires(self):
        full_path = self.files.create_file('foo.txt', 'mycontent')
        cmdline = ('%s %s s3://bucket/key.txt --expires 90' %
                   (self.prefix, full_path))
        self.parsed_responses = \
            [{'ETag': '"c8afdb36c52cf4727836669019e69222"'}]
        self.run_cmd(cmdline, expected_rc=0)
        # The only operation we should have called is PutObject.
        self.assertEqual(len(self.operations_called), 1,
                         self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'PutObject')
        self.assertEqual(self.operations_called[0][1]['Key'], 'key.txt')
        self.assertEqual(self.operations_called[0][1]['Bucket'], 'bucket')
        self.assertEqual(self.operations_called[0][1]['Expires'], '90')

    def test_operations_used_in_download_file(self):
        self.parsed_responses = [
            {"ContentLength": "100", "LastModified": "00:00:00Z"},
            {'ETag': '"foo-1"', 'Body': six.BytesIO(b'foo')},
        ]
        cmdline = '%s s3://bucket/key.txt %s' % (self.prefix,
                                                 self.files.rootdir)
        self.run_cmd(cmdline, expected_rc=0)
        # The only operations we should have called are HeadObject/GetObject.
        self.assertEqual(len(self.operations_called), 2, self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'HeadObject')
        self.assertEqual(self.operations_called[1][0].name, 'GetObject')

    def test_operations_used_in_recursive_download(self):
        self.parsed_responses = [
            {'ETag': '"foo-1"', 'Contents': [], 'CommonPrefixes': []},
        ]
        cmdline = '%s s3://bucket/key.txt %s --recursive' % (
            self.prefix, self.files.rootdir)
        self.run_cmd(cmdline, expected_rc=0)
        # We called ListObjects but had no objects to download, so
        # we only have a single ListObjects operation being called.
        self.assertEqual(len(self.operations_called), 1, self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'ListObjects')

    def test_website_redirect_ignore_paramfile(self):
        full_path = self.files.create_file('foo.txt', 'mycontent')
        cmdline = '%s %s s3://bucket/key.txt --website-redirect %s' % \
            (self.prefix, full_path, 'http://someserver')
        self.parsed_responses = [{'ETag': '"c8afdb36c52cf4727836669019e69222"'}]
        self.run_cmd(cmdline, expected_rc=0)
        # Make sure that the specified web address is used as opposed to the
        # contents of the web address.
        self.assertEqual(
            self.operations_called[0][1]['WebsiteRedirectLocation'],
            'http://someserver'
        )

    def test_metadata_copy(self):
        self.parsed_responses = [
            {"ContentLength": "100", "LastModified": "00:00:00Z"},
            {'ETag': '"foo-1"'},
        ]
        cmdline = ('%s s3://bucket/key.txt s3://bucket/key2.txt'
                   ' --metadata KeyName=Value' % self.prefix)
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 2,
                         self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'HeadObject')
        self.assertEqual(self.operations_called[1][0].name, 'CopyObject')
        self.assertEqual(self.operations_called[1][1]['Metadata'],
                         {'KeyName': 'Value'})

    def test_metadata_copy_with_put_object(self):
        full_path = self.files.create_file('foo.txt', 'mycontent')
        self.parsed_responses = [
            {"ContentLength": "100", "LastModified": "00:00:00Z"},
            {'ETag': '"foo-1"'},
        ]
        cmdline = ('%s %s s3://bucket/key2.txt'
                   ' --metadata KeyName=Value' % (self.prefix, full_path))
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 1,
                         self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'PutObject')
        self.assertEqual(self.operations_called[0][1]['Metadata'],
                         {'KeyName': 'Value'})

    def test_metadata_copy_with_multipart_upload(self):
        full_path = self.files.create_file('foo.txt', 'a' * 10 * (1024 ** 2))
        self.parsed_responses = [
            {'UploadId': 'foo'},
            {'ETag': '"foo-1"'},
            {'ETag': '"foo-2"'},
            {}
        ]
        cmdline = ('%s %s s3://bucket/key2.txt'
                   ' --metadata KeyName=Value' % (self.prefix, full_path))
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 4,
                         self.operations_called)
        self.assertEqual(self.operations_called[0][0].name,
                         'CreateMultipartUpload')
        self.assertEqual(self.operations_called[0][1]['Metadata'],
                         {'KeyName': 'Value'})

    def test_metadata_directive_copy(self):
        self.parsed_responses = [
            {"ContentLength": "100", "LastModified": "00:00:00Z"},
            {'ETag': '"foo-1"'},
        ]
        cmdline = ('%s s3://bucket/key.txt s3://bucket/key2.txt'
                   ' --metadata-directive REPLACE' % self.prefix)
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 2,
                         self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'HeadObject')
        self.assertEqual(self.operations_called[1][0].name, 'CopyObject')
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

    def test_cp_succeeds_with_mimetype_errors(self):
        full_path = self.files.create_file('foo.txt', 'mycontent')
        cmdline = '%s %s s3://bucket/key.txt' % (self.prefix, full_path)
        self.parsed_responses = [
            {'ETag': '"c8afdb36c52cf4727836669019e69222"'}]
        with mock.patch('mimetypes.guess_type') as mock_guess_type:
            # This should throw a UnicodeDecodeError.
            mock_guess_type.side_effect = lambda x: b'\xe2'.decode('ascii')
            self.run_cmd(cmdline, expected_rc=0)
        # Because of the decoding error the command should have succeeded
        # just that there was no content type added.
        self.assertNotIn('ContentType', self.last_kwargs)

    def test_cp_fails_with_utime_errors_but_continues(self):
        full_path = self.files.create_file('foo.txt', '')
        cmdline = '%s s3://bucket/key.txt %s' % (self.prefix, full_path)
        self.parsed_responses = [
            {"ContentLength": "100", "LastModified": "00:00:00Z"},
            {'ETag': '"foo-1"', 'Body': six.BytesIO(b'foo')}
        ]
        with mock.patch('os.utime') as mock_utime:
            mock_utime.side_effect = OSError(1, '')
            _, err, _ = self.run_cmd(cmdline, expected_rc=1)
            self.assertIn('attempting to modify the utime', err)

    def test_recursive_glacier_download_with_force_glacier(self):
        self.parsed_responses = [
            {
                'Contents': [
                    {'Key': 'foo/bar.txt', 'ContentLength': '100',
                     'LastModified': '00:00:00Z',
                     'StorageClass': 'GLACIER',
                     'Size': 100},
                ],
                'CommonPrefixes': []
            },
            {'ETag': '"foo-1"', 'Body': six.BytesIO(b'foo')},
        ]
        cmdline = '%s s3://bucket/foo %s --recursive --force-glacier-transfer'\
                  % (self.prefix, self.files.rootdir)
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 2, self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'ListObjects')
        self.assertEqual(self.operations_called[1][0].name, 'GetObject')

    def test_recursive_glacier_download_without_force_glacier(self):
        self.parsed_responses = [
            {
                'Contents': [
                    {'Key': 'foo/bar.txt', 'ContentLength': '100',
                     'LastModified': '00:00:00Z',
                     'StorageClass': 'GLACIER',
                     'Size': 100},
                ],
                'CommonPrefixes': []
            }
        ]
        cmdline = '%s s3://bucket/foo %s --recursive' % (
            self.prefix, self.files.rootdir)
        _, stderr, _ = self.run_cmd(cmdline, expected_rc=2)
        self.assertEqual(len(self.operations_called), 1, self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'ListObjects')
        self.assertIn('GLACIER', stderr)

    def test_warns_on_glacier_incompatible_operation(self):
        self.parsed_responses = [
            {'ContentLength': '100', 'LastModified': '00:00:00Z',
             'StorageClass': 'GLACIER'},
        ]
        cmdline = ('%s s3://bucket/key.txt .' % self.prefix)
        _, stderr, _ = self.run_cmd(cmdline, expected_rc=2)
        # There should not have been a download attempted because the
        # operation was skipped because it is glacier incompatible.
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(self.operations_called[0][0].name, 'HeadObject')
        self.assertIn('GLACIER', stderr)

    def test_warns_on_glacier_incompatible_operation_for_multipart_file(self):
        self.parsed_responses = [
            {'ContentLength': str(20 * (1024 ** 2)),
             'LastModified': '00:00:00Z',
             'StorageClass': 'GLACIER'},
        ]
        cmdline = ('%s s3://bucket/key.txt .' % self.prefix)
        _, stderr, _ = self.run_cmd(cmdline, expected_rc=2)
        # There should not have been a download attempted because the
        # operation was skipped because it is glacier incompatible.
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(self.operations_called[0][0].name, 'HeadObject')
        self.assertIn('GLACIER', stderr)

    def test_turn_off_glacier_warnings(self):
        self.parsed_responses = [
            {'ContentLength': str(20 * (1024 ** 2)),
             'LastModified': '00:00:00Z',
             'StorageClass': 'GLACIER'},
        ]
        cmdline = (
            '%s s3://bucket/key.txt . --ignore-glacier-warnings' % self.prefix)
        _, stderr, _ = self.run_cmd(cmdline, expected_rc=0)
        # There should not have been a download attempted because the
        # operation was skipped because it is glacier incompatible.
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(self.operations_called[0][0].name, 'HeadObject')
        self.assertEqual('', stderr)
    
    def test_cp_with_sse_flag(self):
        full_path = self.files.create_file('foo.txt', 'contents')
        cmdline = (
            '%s %s s3://bucket/key.txt --sse' % (
                self.prefix, full_path))
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(self.operations_called[0][0].name, 'PutObject')
        self.assertDictEqual(
            self.operations_called[0][1],
            {'Key': 'key.txt', 'Bucket': 'bucket',
             'ContentType': 'text/plain', 'Body': mock.ANY,
             'ServerSideEncryption': 'AES256'}
        )

    def test_cp_with_sse_c_flag(self):
        full_path = self.files.create_file('foo.txt', 'contents')
        cmdline = (
            '%s %s s3://bucket/key.txt --sse-c --sse-c-key foo' % (
                self.prefix, full_path))
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(self.operations_called[0][0].name, 'PutObject')
        self.assertDictEqual(
            self.operations_called[0][1],
            {'Key': 'key.txt', 'Bucket': 'bucket',
             'ContentType': 'text/plain', 'Body': mock.ANY,
             'SSECustomerAlgorithm': 'AES256', 'SSECustomerKey': 'Zm9v',
             'SSECustomerKeyMD5': 'rL0Y20zC+Fzt72VPzMSk2A=='}
        )

    # Note ideally the kms sse with a key id would be integration tests
    # However, you cannot delete kms keys so there would be no way to clean
    # up the tests
    def test_cp_upload_with_sse_kms_and_key_id(self):
        full_path = self.files.create_file('foo.txt', 'contents')
        cmdline = (
            '%s %s s3://bucket/key.txt --sse aws:kms --sse-kms-key-id foo' % (
                self.prefix, full_path))
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(self.operations_called[0][0].name, 'PutObject')
        self.assertDictEqual(
            self.operations_called[0][1],
            {'Key': 'key.txt', 'Bucket': 'bucket',
             'ContentType': 'text/plain', 'Body': mock.ANY,
             'SSEKMSKeyId': 'foo', 'ServerSideEncryption': 'aws:kms'}
        )

    def test_cp_upload_large_file_with_sse_kms_and_key_id(self):
        self.parsed_responses = [
            {'UploadId': 'foo'},  # CreateMultipartUpload
            {'ETag': '"foo"'},  # UploadPart
            {'ETag': '"foo"'},  # UploadPart
            {}  # CompleteMultipartUpload
        ]
        full_path = self.files.create_file('foo.txt', 'a' * 10 * (1024 ** 2))
        cmdline = (
            '%s %s s3://bucket/key.txt --sse aws:kms --sse-kms-key-id foo' % (
                self.prefix, full_path))
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 4)

        # We are only really concerned that the CreateMultipartUpload
        # used the KMS key id.
        self.assertEqual(
            self.operations_called[0][0].name, 'CreateMultipartUpload')
        self.assertDictEqual(
            self.operations_called[0][1],
            {'Key': 'key.txt', 'Bucket': 'bucket',
             'ContentType': 'text/plain',
             'SSEKMSKeyId': 'foo', 'ServerSideEncryption': 'aws:kms'}
        )

    def test_cp_copy_with_sse_kms_and_key_id(self):
        self.parsed_responses = [
            {'ContentLength': 5, 'LastModified': '00:00:00Z'},  # HeadObject
            {}  # CopyObject
        ]
        cmdline = (
            '%s s3://bucket/key1.txt s3://bucket/key2.txt '
            '--sse aws:kms --sse-kms-key-id foo' % self.prefix)
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 2)
        self.assertEqual(self.operations_called[1][0].name, 'CopyObject')
        self.assertDictEqual(
            self.operations_called[1][1],
            {'Key': 'key2.txt', 'Bucket': 'bucket',
             'ContentType': 'text/plain', 'CopySource': 'bucket/key1.txt',
             'SSEKMSKeyId': 'foo', 'ServerSideEncryption': 'aws:kms'}
        )

    def test_cp_copy_large_file_with_sse_kms_and_key_id(self):
        self.parsed_responses = [
            {'ContentLength': 10 * (1024 ** 2),
             'LastModified': '00:00:00Z'},  # HeadObject
            {'UploadId': 'foo'},  # CreateMultipartUpload
            {'CopyPartResult': {'ETag': '"foo"'}},  # UploadPartCopy
            {'CopyPartResult': {'ETag': '"foo"'}},  # UploadPartCopy
            {}  # CompleteMultipartUpload
        ]
        cmdline = (
            '%s s3://bucket/key1.txt s3://bucket/key2.txt '
            '--sse aws:kms --sse-kms-key-id foo' % self.prefix)
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 5)

        # We are only really concerned that the CreateMultipartUpload
        # used the KMS key id.
        self.assertEqual(
            self.operations_called[1][0].name, 'CreateMultipartUpload')
        self.assertDictEqual(
            self.operations_called[1][1],
            {'Key': 'key2.txt', 'Bucket': 'bucket',
             'ContentType': 'text/plain',
             'SSEKMSKeyId': 'foo', 'ServerSideEncryption': 'aws:kms'}
        )

    def test_cannot_use_recursive_with_stream(self):
        cmdline = '%s - s3://bucket/key.txt --recursive' % self.prefix
        _, stderr, _ = self.run_cmd(cmdline, expected_rc=255)
        self.assertIn(
            'Streaming currently is only compatible with non-recursive cp '
            'commands', stderr)


class TestStreamingCPCommand(BaseAWSCommandParamsTest):
    def test_streaming_upload(self):
        command = "s3 cp - s3://bucket/streaming.txt"
        self.parsed_responses = [{
            'ETag': '"c8afdb36c52cf4727836669019e69222"'
        }]

        binary_stdin = six.BytesIO(b'foo\n')
        location = "awscli.customizations.s3.s3handler.binary_stdin"
        with mock.patch(location, binary_stdin):
            self.run_cmd(command)

        self.assertEqual(len(self.operations_called), 1)
        model, args = self.operations_called[0]
        expected_args = {
            'Bucket': 'bucket',
            'Key': 'streaming.txt',
            'Body': mock.ANY
        }

        self.assertEqual(model.name, 'PutObject')
        self.assertEqual(args, expected_args)

    def test_streaming_upload_with_expected_size(self):
        command = "s3 cp - s3://bucket/streaming.txt --expected-size 4"
        self.parsed_responses = [{
            'ETag': '"c8afdb36c52cf4727836669019e69222"'
        }]

        binary_stdin = six.BytesIO(b'foo\n')
        location = "awscli.customizations.s3.s3handler.binary_stdin"
        with mock.patch(location, binary_stdin):
            self.run_cmd(command)

        self.assertEqual(len(self.operations_called), 1)
        model, args = self.operations_called[0]
        expected_args = {
            'Bucket': 'bucket',
            'Key': 'streaming.txt',
            'Body': mock.ANY
        }

        self.assertEqual(model.name, 'PutObject')
        self.assertEqual(args, expected_args)

    def test_streaming_upload_error(self):
        command = "s3 cp - s3://bucket/streaming.txt"
        self.parsed_responses = [{
            'Error': {
                'Code': 'NoSuchBucket',
                'Message': 'The specified bucket does not exist',
                'BucketName': 'bucket'
            }
        }]
        self.http_response.status_code = 404

        binary_stdin = six.BytesIO(b'foo\n')
        location = "awscli.customizations.s3.s3handler.binary_stdin"
        with mock.patch(location, binary_stdin):
            stdout, _, _ = self.run_cmd(command, expected_rc=1)

        error_message = (
            'Transfer failed: An error occurred (NoSuchBucket) when calling '
            'the PutObject operation: The specified bucket does not exist'
        )
        self.assertIn(error_message, stdout)

    def test_streaming_download(self):
        command = "s3 cp s3://bucket/streaming.txt -"
        self.parsed_responses = [
            {
                "AcceptRanges": "bytes",
                "LastModified": "Tue, 12 Jul 2016 21:26:07 GMT",
                "ContentLength": 4,
                "ETag": '"d3b07384d113edec49eaa6238ad5ff00"',
                "Metadata": {},
                "ContentType": "binary/octet-stream"
            },
            {
                "AcceptRanges": "bytes",
                "Metadata": {},
                "ContentType": "binary/octet-stream",
                "ContentLength": 4,
                "ETag": '"d3b07384d113edec49eaa6238ad5ff00"',
                "LastModified": "Tue, 12 Jul 2016 21:26:07 GMT",
                "Body": six.BytesIO(b'foo\n')
            }
        ]

        stdout, stderr, rc = self.run_cmd(command)
        self.assertEqual(stdout, 'foo\n')

        # Ensures no extra operations were called
        self.assertEqual(len(self.operations_called), 2)
        ops = [op[0].name for op in self.operations_called]
        expected_ops = ['HeadObject', 'GetObject']
        self.assertEqual(ops, expected_ops)

    def test_streaming_download_error(self):
        command = "s3 cp s3://bucket/streaming.txt -"
        self.parsed_responses = [{
            'Error': {
                'Code': 'NoSuchBucket',
                'Message': 'The specified bucket does not exist',
                'BucketName': 'bucket'
            }
        }]
        self.http_response.status_code = 404

        stdout, _, _ = self.run_cmd(command, expected_rc=1)
        error_message = (
            'Transfer failed: An error occurred (NoSuchBucket) when calling '
            'the HeadObject operation: The specified bucket does not exist'
        )
        self.assertIn(error_message, stdout)
