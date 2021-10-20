# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import glob
import os
import time

from tests import assert_files_equal
from tests.integration import BaseTransferManagerIntegTest
from s3transfer.processpool import ProcessTransferConfig
from s3transfer.processpool import ProcessPoolDownloader


class TestProcessPoolDownloader(BaseTransferManagerIntegTest):
    def setUp(self):
        super(TestProcessPoolDownloader, self).setUp()
        self.multipart_threshold = 5 * 1024 * 1024
        self.config = ProcessTransferConfig(
            multipart_threshold=self.multipart_threshold
        )
        self.client_kwargs = {'region_name': self.region}

    def create_process_pool_downloader(self, client_kwargs=None, config=None):
        if client_kwargs is None:
            client_kwargs = self.client_kwargs
        if config is None:
            config = self.config
        return ProcessPoolDownloader(
            client_kwargs=client_kwargs, config=config)

    def test_below_threshold(self):
        downloader = self.create_process_pool_downloader()
        filename = self.files.create_file_with_size(
            'foo.txt', filesize=1024 * 1024)
        self.upload_file(filename, '1mb.txt')

        download_path = os.path.join(self.files.rootdir, '1mb.txt')
        with downloader:
            downloader.download_file(
                self.bucket_name, '1mb.txt', download_path)
        assert_files_equal(filename, download_path)

    def test_above_threshold(self):
        downloader = self.create_process_pool_downloader()
        filename = self.files.create_file_with_size(
            'foo.txt', filesize=20 * 1024 * 1024)
        self.upload_file(filename, '20mb.txt')

        download_path = os.path.join(self.files.rootdir, '20mb.txt')
        with downloader:
            downloader.download_file(
                self.bucket_name, '20mb.txt', download_path)
        assert_files_equal(filename, download_path)

    def test_large_download_exits_quickly_on_exception(self):
        downloader = self.create_process_pool_downloader()

        filename = self.files.create_file_with_size(
            'foo.txt', filesize=60 * 1024 * 1024)
        self.upload_file(filename, '60mb.txt')

        download_path = os.path.join(self.files.rootdir, '60mb.txt')
        sleep_time = 0.2
        try:
            with downloader:
                downloader.download_file(
                    self.bucket_name, '60mb.txt', download_path)
                # Sleep for a little to get the transfer process going
                time.sleep(sleep_time)
                # Raise an exception which should cause the preceding
                # download to cancel and exit quickly
                start_time = time.time()
                raise KeyboardInterrupt()
        except KeyboardInterrupt:
            pass
        end_time = time.time()
        # The maximum time allowed for the transfer manager to exit.
        # This means that it should take less than a couple second after
        # sleeping to exit.
        max_allowed_exit_time = 5
        self.assertLess(
            end_time - start_time, max_allowed_exit_time,
            "Failed to exit under %s. Instead exited in %s." % (
                max_allowed_exit_time, end_time - start_time)
        )

        # Make sure the actual file and the temporary do not exist
        # by globbing for the file and any of its extensions
        possible_matches = glob.glob('%s*' % download_path)
        self.assertEqual(possible_matches, [])

    def test_many_files_exits_quickly_on_exception(self):
        downloader = self.create_process_pool_downloader()

        filename = self.files.create_file_with_size(
            '1mb.txt', filesize=1024 * 1024)
        self.upload_file(filename, '1mb.txt')

        filenames = []
        base_filename = os.path.join(self.files.rootdir, 'file')
        for i in range(10):
            filenames.append(base_filename + str(i))

        try:
            with downloader:
                start_time = time.time()
                for filename in filenames:
                    downloader.download_file(
                        self.bucket_name, '1mb.txt', filename)
                # Raise an exception which should cause the preceding
                # transfer to cancel and exit quickly
                raise KeyboardInterrupt()
        except KeyboardInterrupt:
            pass
        end_time = time.time()
        # The maximum time allowed for the transfer manager to exit.
        # This means that it should take less than a couple seconds to exit.
        max_allowed_exit_time = 5
        self.assertLess(
            end_time - start_time, max_allowed_exit_time,
            "Failed to exit under %s. Instead exited in %s." % (
                max_allowed_exit_time, end_time - start_time)
        )

        # For the transfer that did get cancelled, make sure the temporary
        # file got removed.
        possible_matches = glob.glob('%s*' % base_filename)
        self.assertEqual(possible_matches, [])
