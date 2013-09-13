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
from tests import unittest
import random
import threading

from awscli.customizations.s3.tasks import MultipartUploadContext


class TestMultipartUploadContext(unittest.TestCase):

    def setUp(self):
        self.context = MultipartUploadContext(expected_parts=1)
        self.calls = []
        self.threads = []
        self.call_lock = threading.Lock()

    def tearDown(self):
        self.join_threads()

    def join_threads(self):
        for thread in self.threads:
            thread.join()

    def test_normal_non_threaded(self):
        # The context object is pretty straightforward.
        # This shows the non threaded usage of this object.
        context = MultipartUploadContext(expected_parts=3)
        # First you can announce an upload id.
        context.announce_upload_id('my_upload_id')
        # Then a thread that was waiting on the id would be notified.
        self.assertEqual(context.wait_for_upload_id(), 'my_upload_id')
        # Then thread would chug away at the parts.
        context.announce_finished_part(etag='etag1', part_number=1)
        context.announce_finished_part(etag='etag2', part_number=2)
        context.announce_finished_part(etag='etag3', part_number=3)
        # Then a thread that was waiting for all the parts to finish
        # would be notified.
        self.assertEqual(context.wait_for_parts_to_finish(), [
            {'ETag': 'etag1', 'PartNumber': 1},
            {'ETag': 'etag2', 'PartNumber': 2},
            {'ETag': 'etag3', 'PartNumber': 3}])

    def upload_part(self, part_number):
        # This simulates what a thread would do if it wanted to upload
        # a part.  First it would wait for the upload id.
        upload_id = self.context.wait_for_upload_id()
        with self.call_lock:
            self.calls.append(('upload_part', part_number, upload_id))
        # Then it would call UploadPart here.
        # Then it would announce that it's finished with a part.
        self.context.announce_finished_part(etag='etag%s' % part_number,
                                            part_number=part_number)

    def complete_upload(self):
        upload_id = self.context.wait_for_upload_id()
        parts = self.context.wait_for_parts_to_finish()
        with self.call_lock:
            self.calls.append(('complete_upload', upload_id, parts))

    def create_upload(self, upload_id):
        with self.call_lock:
            self.calls.append(('create_multipart_upload', 'my_upload_id'))
        self.context.announce_upload_id(upload_id)

    def start_thread(self, thread):
        thread.start()
        self.threads.append(thread)

    def test_basic_threaded_parts(self):
        # Now while test_normal_non_threaded showed the conceptual idea,
        # the real strength of MultipartUploadContext is that it works
        # when there are threads and when these threads operate out of
        # sequence.
        # For example, let's say a thread comes along that wants
        # to upload a part.  It needs to wait until the upload id
        # is announced.
        upload_part_thread = threading.Thread(target=self.upload_part,
                                              args=(1,))
        # Once this thread starts it will immediately block.
        self.start_thread(upload_part_thread)

        # Also, let's start the thread that will do the complete
        # multipart upload.  It will also block because it needs all
        # the parts so it's blocked up the upload_part_thread.  It also
        # needs the upload_id so it's blocked on that as well.
        complete_upload_thread = threading.Thread(target=self.complete_upload)
        self.start_thread(complete_upload_thread)

        # Then finally the CreateMultipartUpload completes and we
        # announce the upload id.
        self.create_upload('my_upload_id')
        # The upload_part thread can now proceed as well as the complete
        # multipart upload thread.
        self.join_threads()

        # We can verify that the invariants still hold.
        # First there should be three calls, create, upload, complete.
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(self.calls[0][0], 'create_multipart_upload')
        self.assertEqual(self.calls[1][0], 'upload_part')
        self.assertEqual(self.calls[2][0], 'complete_upload')

        # Verify the correct args were used.
        self.assertEqual(self.calls[0][1], 'my_upload_id')
        self.assertEqual(self.calls[1][1:], (1, 'my_upload_id'))
        self.assertEqual(
            self.calls[2][1:],
            ('my_upload_id', [{'ETag': 'etag1', 'PartNumber': 1}]))

    def test_randomized_stress_test(self):
        # Now given that we've verified the functionality from
        # the two tests above, we randomize the threading to ensure
        # that the order doesn't actually matter.  The invariant that
        # the CreateMultipartUpload is called first, then UploadPart
        # operations are called with the appropriate upload_id, then
        # CompleteMultipartUpload with the appropriate upload_id and
        # parts list should hold true regardless of how the threads
        # are ordered.

        # I've run this with much larger values, but 100 is a good
        # tradeoff with coverage vs. execution time.
        for i in range(100):
            if i % 100 == 0:
                print(i)
            expected_parts = random.randint(2, 50)
            self.context = MultipartUploadContext(expected_parts=expected_parts)
            self.threads = []
            self.calls = []
            all_threads = [
                threading.Thread(target=self.complete_upload),
                threading.Thread(target=self.create_upload,
                                args=('my_upload_id',)),
            ]
            for i in range(1, expected_parts + 1):
                all_threads.append(
                    threading.Thread(target=self.upload_part, args=(i,))
                )
            random.shuffle(all_threads)
            for thread in all_threads:
                self.start_thread(thread)
            self.join_threads()
            self.assertEqual(self.calls[0][0], 'create_multipart_upload')
            self.assertEqual(self.calls[-1][0], 'complete_upload')
            parts = set()
            for call in self.calls[1:-1]:
                self.assertEqual(call[0], 'upload_part')
                self.assertEqual(call[2], 'my_upload_id')
                parts.add(call[1])
            self.assertEqual(len(parts), expected_parts)
