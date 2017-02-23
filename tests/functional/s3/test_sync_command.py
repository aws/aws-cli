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
from awscli.testutils import set_invalid_utime
from awscli.testutils import BaseAWSCommandParamsTest, FileCreator
from mock import patch
import os

from awscli.compat import six


class TestSyncCommand(BaseAWSCommandParamsTest):

    prefix = 's3 sync '

    def setUp(self):
        super(TestSyncCommand, self).setUp()
        self.files = FileCreator()

    def tearDown(self):
        super(TestSyncCommand, self).tearDown()
        self.files.remove_all()

    def test_website_redirect_ignore_paramfile(self):
        full_path = self.files.create_file('foo.txt', 'mycontent')
        cmdline = '%s %s s3://bucket/key.txt --website-redirect %s' % \
            (self.prefix, self.files.rootdir, 'http://someserver')
        self.parsed_responses = [
            {"CommonPrefixes": [], "Contents": []},
            {'ETag': '"c8afdb36c52cf4727836669019e69222"'}
        ]
        self.run_cmd(cmdline, expected_rc=0)

        # The only operations we should have called are ListObjects/PutObject.
        self.assertEqual(len(self.operations_called), 2, self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'ListObjects')
        self.assertEqual(self.operations_called[1][0].name, 'PutObject')
        # Make sure that the specified web address is used as opposed to the
        # contents of the web address when uploading the object
        self.assertEqual(
            self.operations_called[1][1]['WebsiteRedirectLocation'],
            'http://someserver'
        )

    def test_no_recursive_option(self):
        cmdline = '. s3://mybucket --recursive'
        # Return code will be 2 for invalid parameter ``--recursive``
        self.run_cmd(cmdline, expected_rc=2)

    def test_sync_from_non_existant_directory(self):
        non_existant_directory = os.path.join(self.files.rootdir, 'fakedir')
        cmdline = '%s %s s3://bucket/' % (self.prefix, non_existant_directory)
        self.parsed_responses = [
            {"CommonPrefixes": [], "Contents": []}
        ]
        _, stderr, _ = self.run_cmd(cmdline, expected_rc=255)
        self.assertIn('does not exist', stderr)

    def test_sync_to_non_existant_directory(self):
        key = 'foo.txt'
        non_existant_directory = os.path.join(self.files.rootdir, 'fakedir')
        cmdline = '%s s3://bucket/ %s' % (self.prefix, non_existant_directory)
        self.parsed_responses = [
            {"CommonPrefixes": [], "Contents": [
                {"Key": key, "Size": 3,
                 "LastModified": "2014-01-09T20:45:49.000Z"}]},
            {'ETag': '"c8afdb36c52cf4727836669019e69222-"',
             'Body': six.BytesIO(b'foo')}
        ]
        self.run_cmd(cmdline, expected_rc=0)
        # Make sure the file now exists.
        self.assertTrue(
            os.path.exists(os.path.join(non_existant_directory, key)))

    def test_glacier_sync_with_force_glacier(self):
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
        cmdline = '%s s3://bucket/foo %s --force-glacier-transfer' % (
            self.prefix, self.files.rootdir)
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(len(self.operations_called), 2, self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'ListObjects')
        self.assertEqual(self.operations_called[1][0].name, 'GetObject')

    def test_handles_glacier_incompatible_operations(self):
        self.parsed_responses = [
            {'Contents': [
                {'Key': 'foo', 'Size': 100,
                 'LastModified': '00:00:00Z', 'StorageClass': 'GLACIER'}]}
        ]
        cmdline = '%s s3://bucket/ %s' % (
            self.prefix, self.files.rootdir)
        _, stderr, _ = self.run_cmd(cmdline, expected_rc=2)
        # There should not have been a download attempted because the
        # operation was skipped because it is glacier incompatible.
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(self.operations_called[0][0].name, 'ListObjects')
        self.assertIn('GLACIER', stderr)

    def test_turn_off_glacier_warnings(self):
        self.parsed_responses = [
            {'Contents': [
                {'Key': 'foo', 'Size': 100,
                 'LastModified': '00:00:00Z', 'StorageClass': 'GLACIER'}]}
        ]
        cmdline = '%s s3://bucket/ %s --ignore-glacier-warnings' % (
            self.prefix, self.files.rootdir)
        _, stderr, _ = self.run_cmd(cmdline, expected_rc=0)
        # There should not have been a download attempted because the
        # operation was skipped because it is glacier incompatible.
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(self.operations_called[0][0].name, 'ListObjects')
        self.assertEqual('', stderr)

    def test_warning_on_invalid_timestamp(self):
        full_path = self.files.create_file('foo.txt', 'mycontent')

        # Set the update time to a value that will raise a ValueError when
        # converting to datetime
        set_invalid_utime(full_path)
        cmdline = '%s %s s3://bucket/key.txt' % \
                  (self.prefix, self.files.rootdir)
        self.parsed_responses = [
            {"CommonPrefixes": [], "Contents": []},
            {'ETag': '"c8afdb36c52cf4727836669019e69222"'}
        ]
        self.run_cmd(cmdline, expected_rc=2)

        # We should still have put the object
        self.assertEqual(len(self.operations_called), 2, self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'ListObjects')
        self.assertEqual(self.operations_called[1][0].name, 'PutObject')

    def test_sync_with_delete_on_downloads(self):
        full_path = self.files.create_file('foo.txt', 'mycontent')
        cmdline = '%s s3://bucket %s --delete' % (
            self.prefix, self.files.rootdir)
        self.parsed_responses = [
            {"CommonPrefixes": [], "Contents": []},
            {'ETag': '"c8afdb36c52cf4727836669019e69222"'}
        ]
        self.run_cmd(cmdline, expected_rc=0)

        # The only operations we should have called are ListObjects.
        self.assertEqual(len(self.operations_called), 1, self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'ListObjects')

        self.assertFalse(os.path.exists(full_path))

    def test_sync_skips_over_files_deleted_between_listing_and_transfer(self):
        full_path = self.files.create_file('foo.txt', 'mycontent')
        cmdline = '%s %s s3://bucket/' % (
            self.prefix, self.files.rootdir)

        # FileGenerator.list_files should skip over files that cause an
        # OSError to be raised because they are missing when we try to
        # get their stats.
        def side_effect(_):
            os.remove(full_path)
            raise OSError()
        with patch(
                'awscli.customizations.s3.filegenerator.get_file_stat',
                side_effect=side_effect
                ):
            self.run_cmd(cmdline, expected_rc=2)

        # We should not call PutObject because the file was deleted
        # before we could transfer it
        self.assertEqual(len(self.operations_called), 1, self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'ListObjects')
