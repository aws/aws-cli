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
from multiprocessing.managers import BaseManager

import botocore.exceptions
import botocore.session
from botocore.stub import Stubber

from tests import mock
from tests import unittest
from tests import FileCreator
from s3transfer.compat import six
from s3transfer.exceptions import CancelledError
from s3transfer.processpool import ProcessTransferConfig
from s3transfer.processpool import ProcessPoolDownloader


class StubbedClient(object):
    def __init__(self):
        self._client = botocore.session.get_session().create_client(
            's3', 'us-west-2', aws_access_key_id='foo',
            aws_secret_access_key='bar')
        self._stubber = Stubber(self._client)
        self._stubber.activate()
        self._caught_stubber_errors = []

    def get_object(self, **kwargs):
        return self._client.get_object(**kwargs)

    def head_object(self, **kwargs):
        return self._client.head_object(**kwargs)

    def add_response(self, *args, **kwargs):
        self._stubber.add_response(*args, **kwargs)

    def add_client_error(self, *args, **kwargs):
        self._stubber.add_client_error(*args, **kwargs)


class StubbedClientManager(BaseManager):
    pass


StubbedClientManager.register('StubbedClient', StubbedClient)


# Ideally a Mock would be used here. However, they cannot be pickled
# for Windows. So instead we define a factory class at the module level that
# can return a stubbed client we initialized in the setUp.
class StubbedClientFactory(object):
    def __init__(self, stubbed_client):
        self._stubbed_client = stubbed_client

    def __call__(self, *args, **kwargs):
        # The __call__ is defined so we can provide an instance of the
        # StubbedClientFactory to mock.patch() and have the instance be
        # returned when the patched class is instantiated.
        return self

    def create_client(self):
        return self._stubbed_client


class TestProcessPoolDownloader(unittest.TestCase):
    def setUp(self):
        # The stubbed client needs to run in a manager to be shared across
        # processes and have it properly consume the stubbed response across
        # processes.
        self.manager = StubbedClientManager()
        self.manager.start()
        self.stubbed_client = self.manager.StubbedClient()
        self.stubbed_client_factory = StubbedClientFactory(self.stubbed_client)

        self.client_factory_patch = mock.patch(
            's3transfer.processpool.ClientFactory',
            self.stubbed_client_factory
        )
        self.client_factory_patch.start()
        self.files = FileCreator()

        self.config = ProcessTransferConfig(
            max_request_processes=1
        )
        self.downloader = ProcessPoolDownloader(config=self.config)
        self.bucket = 'mybucket'
        self.key = 'mykey'
        self.filename = self.files.full_path('filename')
        self.remote_contents = b'my content'
        self.stream = six.BytesIO(self.remote_contents)

    def tearDown(self):
        self.manager.shutdown()
        self.client_factory_patch.stop()
        self.files.remove_all()

    def assert_contents(self, filename, expected_contents):
        self.assertTrue(os.path.exists(filename))
        with open(filename, 'rb') as f:
            self.assertEqual(f.read(), expected_contents)

    def test_download_file(self):
        self.stubbed_client.add_response(
            'head_object', {'ContentLength': len(self.remote_contents)})
        self.stubbed_client.add_response(
            'get_object', {'Body': self.stream}
        )
        with self.downloader:
            self.downloader.download_file(self.bucket, self.key, self.filename)
        self.assert_contents(self.filename, self.remote_contents)

    def test_download_multiple_files(self):
        self.stubbed_client.add_response(
            'get_object', {'Body': self.stream}
        )
        self.stubbed_client.add_response(
            'get_object', {'Body': six.BytesIO(self.remote_contents)}
        )
        with self.downloader:
            self.downloader.download_file(
                self.bucket, self.key, self.filename,
                expected_size=len(self.remote_contents))
            other_file = self.files.full_path('filename2')
            self.downloader.download_file(
                self.bucket, self.key, other_file,
                expected_size=len(self.remote_contents))
        self.assert_contents(self.filename, self.remote_contents)
        self.assert_contents(other_file, self.remote_contents)

    def test_download_file_ranged_download(self):
        half_of_content_length = int(len(self.remote_contents)/2)
        self.stubbed_client.add_response(
            'head_object', {'ContentLength': len(self.remote_contents)})
        self.stubbed_client.add_response(
            'get_object', {
                'Body': six.BytesIO(
                    self.remote_contents[:half_of_content_length])}
        )
        self.stubbed_client.add_response(
            'get_object', {
                'Body': six.BytesIO(
                    self.remote_contents[half_of_content_length:])}
        )
        downloader = ProcessPoolDownloader(
            config=ProcessTransferConfig(
                multipart_chunksize=half_of_content_length,
                multipart_threshold=half_of_content_length,
                max_request_processes=1
            )
        )
        with downloader:
            downloader.download_file(self.bucket, self.key, self.filename)
        self.assert_contents(self.filename, self.remote_contents)

    def test_download_file_extra_args(self):
        self.stubbed_client.add_response(
            'head_object', {'ContentLength': len(self.remote_contents)},
            expected_params={
                'Bucket': self.bucket, 'Key': self.key,
                'VersionId': 'versionid'
            }
        )
        self.stubbed_client.add_response(
            'get_object', {'Body': self.stream},
            expected_params={
                'Bucket': self.bucket, 'Key': self.key,
                'VersionId': 'versionid'
            }
        )
        with self.downloader:
            self.downloader.download_file(
                self.bucket, self.key, self.filename,
                extra_args={'VersionId': 'versionid'}
            )
        self.assert_contents(self.filename, self.remote_contents)

    def test_download_file_expected_size(self):
        self.stubbed_client.add_response(
            'get_object', {'Body': self.stream}
        )
        with self.downloader:
            self.downloader.download_file(
                self.bucket, self.key, self.filename,
                expected_size=len(self.remote_contents))
        self.assert_contents(self.filename, self.remote_contents)

    def test_cleans_up_tempfile_on_failure(self):
        self.stubbed_client.add_client_error('get_object', 'NoSuchKey')
        with self.downloader:
            self.downloader.download_file(
                self.bucket, self.key, self.filename,
                expected_size=len(self.remote_contents))
        self.assertFalse(os.path.exists(self.filename))
        # Any tempfile should have been erased as well
        possible_matches = glob.glob('%s*' % self.filename + os.extsep)
        self.assertEqual(possible_matches, [])

    def test_validates_extra_args(self):
        with self.downloader:
            with self.assertRaises(ValueError):
                self.downloader.download_file(
                    self.bucket, self.key, self.filename,
                    extra_args={'NotSupported': 'NotSupported'}
                )

    def test_result_with_success(self):
        self.stubbed_client.add_response(
            'get_object', {'Body': self.stream}
        )
        with self.downloader:
            future = self.downloader.download_file(
                self.bucket, self.key, self.filename,
                expected_size=len(self.remote_contents))
            self.assertIsNone(future.result())

    def test_result_with_exception(self):
        self.stubbed_client.add_client_error('get_object', 'NoSuchKey')
        with self.downloader:
            future = self.downloader.download_file(
                self.bucket, self.key, self.filename,
                expected_size=len(self.remote_contents))
            with self.assertRaises(botocore.exceptions.ClientError):
                future.result()

    def test_result_with_cancel(self):
        self.stubbed_client.add_response(
            'get_object', {'Body': self.stream}
        )
        with self.downloader:
            future = self.downloader.download_file(
                self.bucket, self.key, self.filename,
                expected_size=len(self.remote_contents))
            future.cancel()
            with self.assertRaises(CancelledError):
                future.result()

    def test_shutdown_with_no_downloads(self):
        downloader = ProcessPoolDownloader()
        try:
            downloader.shutdown()
        except AttributeError:
            self.fail(
                'The downloader should be able to be shutdown even though '
                'the downloader was never started.'
            )

    def test_shutdown_with_no_downloads_and_ctrl_c(self):
        # Special shutdown logic happens if a KeyboardInterrupt is raised in
        # the context manager. However, this logic can not happen if the
        # downloader was never started. So a KeyboardInterrupt should be
        # the only exception propagated.
        with self.assertRaises(KeyboardInterrupt):
            with self.downloader:
                raise KeyboardInterrupt()
