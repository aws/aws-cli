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
from awscli.testutils import BaseAWSCommandParamsTest, FileCreator
import re

import mock
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


if __name__ == "__main__":
    unittest.main()
