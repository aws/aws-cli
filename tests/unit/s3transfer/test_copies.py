# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests import BaseTaskTest
from tests import RecordingSubscriber
from s3transfer.copies import CopyObjectTask
from s3transfer.copies import CopyPartTask


class BaseCopyTaskTest(BaseTaskTest):
    def setUp(self):
        super(BaseCopyTaskTest, self).setUp()
        self.bucket = 'mybucket'
        self.key = 'mykey'
        self.copy_source = {
            'Bucket': 'mysourcebucket',
            'Key': 'mysourcekey'
        }
        self.extra_args = {}
        self.callbacks = []
        self.size = 5


class TestCopyObjectTask(BaseCopyTaskTest):
    def get_copy_task(self, **kwargs):
        default_kwargs = {
            'client': self.client, 'copy_source': self.copy_source,
            'bucket': self.bucket, 'key': self.key,
            'extra_args': self.extra_args, 'callbacks': self.callbacks,
            'size': self.size
        }
        default_kwargs.update(kwargs)
        return self.get_task(CopyObjectTask, main_kwargs=default_kwargs)

    def test_main(self):
        self.stubber.add_response(
            'copy_object', service_response={},
            expected_params={
                'Bucket': self.bucket, 'Key': self.key,
                'CopySource': self.copy_source
            }
        )
        task = self.get_copy_task()
        task()

        self.stubber.assert_no_pending_responses()

    def test_extra_args(self):
        self.extra_args['ACL'] = 'private'
        self.stubber.add_response(
            'copy_object', service_response={},
            expected_params={
                'Bucket': self.bucket, 'Key': self.key,
                'CopySource': self.copy_source, 'ACL': 'private'
            }
        )
        task = self.get_copy_task()
        task()

        self.stubber.assert_no_pending_responses()

    def test_callbacks_invoked(self):
        subscriber = RecordingSubscriber()
        self.callbacks.append(subscriber.on_progress)
        self.stubber.add_response(
            'copy_object', service_response={},
            expected_params={
                'Bucket': self.bucket, 'Key': self.key,
                'CopySource': self.copy_source
            }
        )
        task = self.get_copy_task()
        task()

        self.stubber.assert_no_pending_responses()
        self.assertEqual(subscriber.calculate_bytes_seen(), self.size)


class TestCopyPartTask(BaseCopyTaskTest):
    def setUp(self):
        super(TestCopyPartTask, self).setUp()
        self.copy_source_range = 'bytes=5-9'
        self.extra_args['CopySourceRange'] = self.copy_source_range
        self.upload_id = 'myuploadid'
        self.part_number = 1
        self.result_etag = 'my-etag'

    def get_copy_task(self, **kwargs):
        default_kwargs = {
            'client': self.client, 'copy_source': self.copy_source,
            'bucket': self.bucket, 'key': self.key,
            'upload_id': self.upload_id, 'part_number': self.part_number,
            'extra_args': self.extra_args, 'callbacks': self.callbacks,
            'size': self.size
        }
        default_kwargs.update(kwargs)
        return self.get_task(CopyPartTask, main_kwargs=default_kwargs)

    def test_main(self):
        self.stubber.add_response(
            'upload_part_copy', service_response={
                'CopyPartResult': {
                    'ETag': self.result_etag
                }
            },
            expected_params={
                'Bucket': self.bucket, 'Key': self.key,
                'CopySource': self.copy_source, 'UploadId': self.upload_id,
                'PartNumber': self.part_number,
                'CopySourceRange': self.copy_source_range
            }
        )
        task = self.get_copy_task()
        self.assertEqual(
            task(), {'PartNumber': self.part_number, 'ETag': self.result_etag})
        self.stubber.assert_no_pending_responses()

    def test_extra_args(self):
        self.extra_args['RequestPayer'] = 'requester'
        self.stubber.add_response(
            'upload_part_copy', service_response={
                'CopyPartResult': {
                    'ETag': self.result_etag
                }
            },
            expected_params={
                'Bucket': self.bucket, 'Key': self.key,
                'CopySource': self.copy_source, 'UploadId': self.upload_id,
                'PartNumber': self.part_number,
                'CopySourceRange': self.copy_source_range,
                'RequestPayer': 'requester'
            }
        )
        task = self.get_copy_task()
        self.assertEqual(
            task(), {'PartNumber': self.part_number, 'ETag': self.result_etag})
        self.stubber.assert_no_pending_responses()

    def test_callbacks_invoked(self):
        subscriber = RecordingSubscriber()
        self.callbacks.append(subscriber.on_progress)
        self.stubber.add_response(
            'upload_part_copy', service_response={
                'CopyPartResult': {
                    'ETag': self.result_etag
                }
            },
            expected_params={
                'Bucket': self.bucket, 'Key': self.key,
                'CopySource': self.copy_source, 'UploadId': self.upload_id,
                'PartNumber': self.part_number,
                'CopySourceRange': self.copy_source_range
            }
        )
        task = self.get_copy_task()
        self.assertEqual(
            task(), {'PartNumber': self.part_number, 'ETag': self.result_etag})
        self.stubber.assert_no_pending_responses()
        self.assertEqual(subscriber.calculate_bytes_seen(), self.size)
