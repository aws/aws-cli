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
import os
import shutil
import tempfile
import time
from io import BytesIO

from botocore.awsrequest import AWSRequest
from botocore.client import Config
from botocore.exceptions import ClientError
from botocore.stub import ANY

from s3transfer.manager import TransferConfig, TransferManager
from s3transfer.utils import ChunksizeAdjuster
from tests import (
    BaseGeneralInterfaceTest,
    NonSeekableReader,
    RecordingOSUtils,
    RecordingSubscriber,
    mock,
)


class BaseUploadTest(BaseGeneralInterfaceTest):
    def setUp(self):
        super().setUp()
        # TODO: We do not want to use the real MIN_UPLOAD_CHUNKSIZE
        # when we're adjusting parts.
        # This is really wasteful and fails CI builds because self.contents
        # would normally use 10MB+ of memory.
        # Until there's an API to configure this, we're patching this with
        # a min size of 1.  We can't patch MIN_UPLOAD_CHUNKSIZE directly
        # because it's already bound to a default value in the
        # chunksize adjuster.  Instead we need to patch out the
        # chunksize adjuster class.
        self.adjuster_patch = mock.patch(
            's3transfer.upload.ChunksizeAdjuster',
            lambda: ChunksizeAdjuster(min_size=1),
        )
        self.adjuster_patch.start()
        self.config = TransferConfig(max_request_concurrency=1)
        self._manager = TransferManager(self.client, self.config)

        # Create a temporary directory with files to read from
        self.tempdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tempdir, 'myfile')
        self.content = b'my content'

        with open(self.filename, 'wb') as f:
            f.write(self.content)

        # Initialize some default arguments
        self.bucket = 'mybucket'
        self.key = 'mykey'
        self.extra_args = {}
        self.subscribers = []

        # A list to keep track of all of the bodies sent over the wire
        # and their order.
        self.sent_bodies = []
        self.client.meta.events.register(
            'before-parameter-build.s3.*', self.collect_body
        )

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.tempdir)
        self.adjuster_patch.stop()

    def collect_body(self, params, model, **kwargs):
        # A handler to simulate the reading of the body including the
        # request-created event that signals to simulate the progress
        # callbacks
        if 'Body' in params:
            # TODO: This is not ideal. Need to figure out a better idea of
            # simulating reading of the request across the wire to trigger
            # progress callbacks
            request = AWSRequest(
                method='PUT',
                url='https://s3.amazonaws.com',
                data=params['Body'],
            )
            self.client.meta.events.emit(
                'request-created.s3.%s' % model.name,
                request=request,
                operation_name=model.name,
            )
            self.sent_bodies.append(self._stream_body(params['Body']))

    def _stream_body(self, body):
        read_amt = 8 * 1024
        data = body.read(read_amt)
        collected_body = data
        while data:
            data = body.read(read_amt)
            collected_body += data
        return collected_body

    @property
    def manager(self):
        return self._manager

    @property
    def method(self):
        return self.manager.upload

    def create_call_kwargs(self):
        return {
            'fileobj': self.filename,
            'bucket': self.bucket,
            'key': self.key,
        }

    def create_invalid_extra_args(self):
        return {'Foo': 'bar'}

    def create_stubbed_responses(self):
        return [{'method': 'put_object', 'service_response': {}}]

    def create_expected_progress_callback_info(self):
        return [{'bytes_transferred': 10}]

    def assert_expected_client_calls_were_correct(self):
        # We assert that expected client calls were made by ensuring that
        # there are no more pending responses. If there are no more pending
        # responses, then all stubbed responses were consumed.
        self.stubber.assert_no_pending_responses()


class TestNonMultipartUpload(BaseUploadTest):
    __test__ = True

    def add_put_object_response_with_default_expected_params(
        self, extra_expected_params=None, bucket=None
    ):
        if bucket is None:
            bucket = self.bucket

        expected_params = {'Body': ANY, 'Bucket': bucket, 'Key': self.key}
        if extra_expected_params:
            expected_params.update(extra_expected_params)
        upload_response = self.create_stubbed_responses()[0]
        upload_response['expected_params'] = expected_params
        self.stubber.add_response(**upload_response)

    def assert_put_object_body_was_correct(self):
        self.assertEqual(self.sent_bodies, [self.content])

    def test_upload(self):
        self.extra_args['RequestPayer'] = 'requester'
        self.add_put_object_response_with_default_expected_params(
            extra_expected_params={'RequestPayer': 'requester'}
        )
        future = self.manager.upload(
            self.filename, self.bucket, self.key, self.extra_args
        )
        future.result()
        self.assert_expected_client_calls_were_correct()
        self.assert_put_object_body_was_correct()

    def test_upload_with_checksum(self):
        self.extra_args['ChecksumAlgorithm'] = 'sha256'
        self.add_put_object_response_with_default_expected_params(
            extra_expected_params={'ChecksumAlgorithm': 'sha256'}
        )
        future = self.manager.upload(
            self.filename, self.bucket, self.key, self.extra_args
        )
        future.result()
        self.assert_expected_client_calls_were_correct()
        self.assert_put_object_body_was_correct()

    def test_upload_with_s3express_default_checksum(self):
        s3express_bucket = "mytestbucket--usw2-az6--x-s3"
        self.assertFalse("ChecksumAlgorithm" in self.extra_args)

        self.add_put_object_response_with_default_expected_params(
            extra_expected_params={'ChecksumAlgorithm': 'crc32'},
            bucket=s3express_bucket,
        )
        future = self.manager.upload(
            self.filename, s3express_bucket, self.key, self.extra_args
        )
        future.result()
        self.assert_expected_client_calls_were_correct()
        self.assert_put_object_body_was_correct()

    def test_upload_for_fileobj(self):
        self.add_put_object_response_with_default_expected_params()
        with open(self.filename, 'rb') as f:
            future = self.manager.upload(
                f, self.bucket, self.key, self.extra_args
            )
            future.result()
        self.assert_expected_client_calls_were_correct()
        self.assert_put_object_body_was_correct()

    def test_upload_for_seekable_filelike_obj(self):
        self.add_put_object_response_with_default_expected_params()
        bytes_io = BytesIO(self.content)
        future = self.manager.upload(
            bytes_io, self.bucket, self.key, self.extra_args
        )
        future.result()
        self.assert_expected_client_calls_were_correct()
        self.assert_put_object_body_was_correct()

    def test_upload_for_seekable_filelike_obj_that_has_been_seeked(self):
        self.add_put_object_response_with_default_expected_params()
        bytes_io = BytesIO(self.content)
        seek_pos = 5
        bytes_io.seek(seek_pos)
        future = self.manager.upload(
            bytes_io, self.bucket, self.key, self.extra_args
        )
        future.result()
        self.assert_expected_client_calls_were_correct()
        self.assertEqual(b''.join(self.sent_bodies), self.content[seek_pos:])

    def test_upload_for_non_seekable_filelike_obj(self):
        self.add_put_object_response_with_default_expected_params()
        body = NonSeekableReader(self.content)
        future = self.manager.upload(
            body, self.bucket, self.key, self.extra_args
        )
        future.result()
        self.assert_expected_client_calls_were_correct()
        self.assert_put_object_body_was_correct()

    def test_sigv4_progress_callbacks_invoked_once(self):
        # Reset the client and manager to use sigv4
        self.reset_stubber_with_new_client(
            {'config': Config(signature_version='s3v4')}
        )
        self.client.meta.events.register(
            'before-parameter-build.s3.*', self.collect_body
        )
        self._manager = TransferManager(self.client, self.config)

        # Add the stubbed response.
        self.add_put_object_response_with_default_expected_params()

        subscriber = RecordingSubscriber()
        future = self.manager.upload(
            self.filename, self.bucket, self.key, subscribers=[subscriber]
        )
        future.result()
        self.assert_expected_client_calls_were_correct()

        # The amount of bytes seen should be the same as the file size
        self.assertEqual(subscriber.calculate_bytes_seen(), len(self.content))

    def test_uses_provided_osutil(self):
        osutil = RecordingOSUtils()
        # Use the recording os utility for the transfer manager
        self._manager = TransferManager(self.client, self.config, osutil)

        self.add_put_object_response_with_default_expected_params()

        future = self.manager.upload(self.filename, self.bucket, self.key)
        future.result()

        # The upload should have used the os utility. We check this by making
        # sure that the recorded opens are as expected.
        expected_opens = [(self.filename, 'rb')]
        self.assertEqual(osutil.open_records, expected_opens)

    def test_allowed_upload_params_are_valid(self):
        op_model = self.client.meta.service_model.operation_model('PutObject')
        for allowed_upload_arg in self._manager.ALLOWED_UPLOAD_ARGS:
            self.assertIn(allowed_upload_arg, op_model.input_shape.members)

    def test_upload_with_bandwidth_limiter(self):
        self.content = b'a' * 1024 * 1024
        with open(self.filename, 'wb') as f:
            f.write(self.content)
        self.config = TransferConfig(
            max_request_concurrency=1, max_bandwidth=len(self.content) / 2
        )
        self._manager = TransferManager(self.client, self.config)

        self.add_put_object_response_with_default_expected_params()
        start = time.time()
        future = self.manager.upload(self.filename, self.bucket, self.key)
        future.result()
        # This is just a smoke test to make sure that the limiter is
        # being used and not necessary its exactness. So we set the maximum
        # bandwidth to len(content)/2 per sec and make sure that it is
        # noticeably slower. Ideally it will take more than two seconds, but
        # given tracking at the beginning of transfers are not entirely
        # accurate setting at the initial start of a transfer, we give us
        # some flexibility by setting the expected time to half of the
        # theoretical time to take.
        self.assertGreaterEqual(time.time() - start, 1)

        self.assert_expected_client_calls_were_correct()
        self.assert_put_object_body_was_correct()

    def test_raise_exception_on_s3_object_lambda_resource(self):
        s3_object_lambda_arn = (
            'arn:aws:s3-object-lambda:us-west-2:123456789012:'
            'accesspoint:my-accesspoint'
        )
        with self.assertRaisesRegex(ValueError, 'methods do not support'):
            self.manager.upload(self.filename, s3_object_lambda_arn, self.key)


class TestMultipartUpload(BaseUploadTest):
    __test__ = True

    def setUp(self):
        super().setUp()
        self.chunksize = 4
        self.config = TransferConfig(
            max_request_concurrency=1,
            multipart_threshold=1,
            multipart_chunksize=self.chunksize,
        )
        self._manager = TransferManager(self.client, self.config)
        self.multipart_id = 'my-upload-id'

    def create_stubbed_responses(self):
        return [
            {
                'method': 'create_multipart_upload',
                'service_response': {'UploadId': self.multipart_id},
            },
            {'method': 'upload_part', 'service_response': {'ETag': 'etag-1'}},
            {'method': 'upload_part', 'service_response': {'ETag': 'etag-2'}},
            {'method': 'upload_part', 'service_response': {'ETag': 'etag-3'}},
            {'method': 'complete_multipart_upload', 'service_response': {}},
        ]

    def create_expected_progress_callback_info(self):
        return [
            {'bytes_transferred': 4},
            {'bytes_transferred': 4},
            {'bytes_transferred': 2},
        ]

    def assert_upload_part_bodies_were_correct(self):
        expected_contents = []
        for i in range(0, len(self.content), self.chunksize):
            end_i = i + self.chunksize
            if end_i > len(self.content):
                expected_contents.append(self.content[i:])
            else:
                expected_contents.append(self.content[i:end_i])
        self.assertEqual(self.sent_bodies, expected_contents)

    def add_create_multipart_response_with_default_expected_params(
        self,
        extra_expected_params=None,
        bucket=None,
    ):
        if bucket is None:
            bucket = self.bucket

        expected_params = {'Bucket': bucket, 'Key': self.key}
        if extra_expected_params:
            expected_params.update(extra_expected_params)
        response = self.create_stubbed_responses()[0]
        response['expected_params'] = expected_params
        self.stubber.add_response(**response)

    def add_upload_part_responses_with_default_expected_params(
        self,
        extra_expected_params=None,
        bucket=None,
    ):
        if bucket is None:
            bucket = self.bucket

        num_parts = 3
        upload_part_responses = self.create_stubbed_responses()[1:-1]
        for i in range(num_parts):
            upload_part_response = upload_part_responses[i]
            expected_params = {
                'Bucket': bucket,
                'Key': self.key,
                'UploadId': self.multipart_id,
                'Body': ANY,
                'PartNumber': i + 1,
            }
            if extra_expected_params:
                expected_params.update(extra_expected_params)
                # If ChecksumAlgorithm is present stub the response checksums
                if 'ChecksumAlgorithm' in extra_expected_params:
                    name = extra_expected_params['ChecksumAlgorithm']
                    checksum_member = 'Checksum%s' % name.upper()
                    response = upload_part_response['service_response']
                    response[checksum_member] = 'sum%s==' % (i + 1)

            upload_part_response['expected_params'] = expected_params
            self.stubber.add_response(**upload_part_response)

    def add_complete_multipart_response_with_default_expected_params(
        self,
        extra_expected_params=None,
        bucket=None,
    ):
        if bucket is None:
            bucket = self.bucket

        expected_params = {
            'Bucket': bucket,
            'Key': self.key,
            'UploadId': self.multipart_id,
            'MultipartUpload': {
                'Parts': [
                    {'ETag': 'etag-1', 'PartNumber': 1},
                    {'ETag': 'etag-2', 'PartNumber': 2},
                    {'ETag': 'etag-3', 'PartNumber': 3},
                ]
            },
        }
        if extra_expected_params:
            expected_params.update(extra_expected_params)
        response = self.create_stubbed_responses()[-1]
        response['expected_params'] = expected_params
        self.stubber.add_response(**response)

    def test_upload(self):
        self.extra_args['RequestPayer'] = 'requester'

        # Add requester pays to the create multipart upload and upload parts.
        self.add_create_multipart_response_with_default_expected_params(
            extra_expected_params={'RequestPayer': 'requester'}
        )
        self.add_upload_part_responses_with_default_expected_params(
            extra_expected_params={'RequestPayer': 'requester'}
        )
        self.add_complete_multipart_response_with_default_expected_params(
            extra_expected_params={'RequestPayer': 'requester'}
        )

        future = self.manager.upload(
            self.filename, self.bucket, self.key, self.extra_args
        )
        future.result()
        self.assert_expected_client_calls_were_correct()

    def test_upload_for_fileobj(self):
        self.add_create_multipart_response_with_default_expected_params()
        self.add_upload_part_responses_with_default_expected_params()
        self.add_complete_multipart_response_with_default_expected_params()
        with open(self.filename, 'rb') as f:
            future = self.manager.upload(
                f, self.bucket, self.key, self.extra_args
            )
            future.result()
        self.assert_expected_client_calls_were_correct()
        self.assert_upload_part_bodies_were_correct()

    def test_upload_for_seekable_filelike_obj(self):
        self.add_create_multipart_response_with_default_expected_params()
        self.add_upload_part_responses_with_default_expected_params()
        self.add_complete_multipart_response_with_default_expected_params()
        bytes_io = BytesIO(self.content)
        future = self.manager.upload(
            bytes_io, self.bucket, self.key, self.extra_args
        )
        future.result()
        self.assert_expected_client_calls_were_correct()
        self.assert_upload_part_bodies_were_correct()

    def test_upload_for_seekable_filelike_obj_that_has_been_seeked(self):
        self.add_create_multipart_response_with_default_expected_params()
        self.add_upload_part_responses_with_default_expected_params()
        self.add_complete_multipart_response_with_default_expected_params()
        bytes_io = BytesIO(self.content)
        seek_pos = 1
        bytes_io.seek(seek_pos)
        future = self.manager.upload(
            bytes_io, self.bucket, self.key, self.extra_args
        )
        future.result()
        self.assert_expected_client_calls_were_correct()
        self.assertEqual(b''.join(self.sent_bodies), self.content[seek_pos:])

    def test_upload_for_non_seekable_filelike_obj(self):
        self.add_create_multipart_response_with_default_expected_params()
        self.add_upload_part_responses_with_default_expected_params()
        self.add_complete_multipart_response_with_default_expected_params()
        stream = NonSeekableReader(self.content)
        future = self.manager.upload(
            stream, self.bucket, self.key, self.extra_args
        )
        future.result()
        self.assert_expected_client_calls_were_correct()
        self.assert_upload_part_bodies_were_correct()

    def test_limits_in_memory_chunks_for_fileobj(self):
        # Limit the maximum in memory chunks to one but make number of
        # threads more than one. This means that the upload will have to
        # happen sequentially despite having many threads available because
        # data is sequentially partitioned into chunks in memory and since
        # there can only every be one in memory chunk, each upload part will
        # have to happen one at a time.
        self.config.max_request_concurrency = 10
        self.config.max_in_memory_upload_chunks = 1
        self._manager = TransferManager(self.client, self.config)

        # Add some default stubbed responses.
        # These responses are added in order of part number so if the
        # multipart upload is not done sequentially, which it should because
        # we limit the in memory upload chunks to one, the stubber will
        # raise exceptions for mismatching parameters for partNumber when
        # once the upload() method is called on the transfer manager.
        # If there is a mismatch, the stubber error will propagate on
        # the future.result()
        self.add_create_multipart_response_with_default_expected_params()
        self.add_upload_part_responses_with_default_expected_params()
        self.add_complete_multipart_response_with_default_expected_params()
        with open(self.filename, 'rb') as f:
            future = self.manager.upload(
                f, self.bucket, self.key, self.extra_args
            )
            future.result()

        # Make sure that the stubber had all of its stubbed responses consumed.
        self.assert_expected_client_calls_were_correct()
        # Ensure the contents were uploaded in sequentially order by checking
        # the sent contents were in order.
        self.assert_upload_part_bodies_were_correct()

    def test_upload_failure_invokes_abort(self):
        self.stubber.add_response(
            method='create_multipart_upload',
            service_response={'UploadId': self.multipart_id},
            expected_params={'Bucket': self.bucket, 'Key': self.key},
        )
        self.stubber.add_response(
            method='upload_part',
            service_response={'ETag': 'etag-1'},
            expected_params={
                'Bucket': self.bucket,
                'Body': ANY,
                'Key': self.key,
                'UploadId': self.multipart_id,
                'PartNumber': 1,
            },
        )
        # With the upload part failing this should immediately initiate
        # an abort multipart with no more upload parts called.
        self.stubber.add_client_error(method='upload_part')

        self.stubber.add_response(
            method='abort_multipart_upload',
            service_response={},
            expected_params={
                'Bucket': self.bucket,
                'Key': self.key,
                'UploadId': self.multipart_id,
            },
        )

        future = self.manager.upload(self.filename, self.bucket, self.key)
        # The exception should get propagated to the future and not be
        # a cancelled error or something.
        with self.assertRaises(ClientError):
            future.result()
        self.assert_expected_client_calls_were_correct()

    def test_upload_passes_select_extra_args(self):
        self.extra_args['Metadata'] = {'foo': 'bar'}

        # Add metadata to expected create multipart upload call
        self.add_create_multipart_response_with_default_expected_params(
            extra_expected_params={'Metadata': {'foo': 'bar'}}
        )
        self.add_upload_part_responses_with_default_expected_params()
        self.add_complete_multipart_response_with_default_expected_params()

        future = self.manager.upload(
            self.filename, self.bucket, self.key, self.extra_args
        )
        future.result()
        self.assert_expected_client_calls_were_correct()

    def test_multipart_upload_passes_checksums(self):
        self.extra_args['ChecksumAlgorithm'] = 'sha1'

        # ChecksumAlgorithm should be passed on the create_multipart call
        self.add_create_multipart_response_with_default_expected_params(
            extra_expected_params={'ChecksumAlgorithm': 'sha1'},
        )

        # ChecksumAlgorithm should be forwarded and a SHA1 will come back
        self.add_upload_part_responses_with_default_expected_params(
            extra_expected_params={'ChecksumAlgorithm': 'sha1'},
        )

        # The checksums should be used in the complete call like etags
        self.add_complete_multipart_response_with_default_expected_params(
            extra_expected_params={
                'MultipartUpload': {
                    'Parts': [
                        {
                            'ETag': 'etag-1',
                            'PartNumber': 1,
                            'ChecksumSHA1': 'sum1==',
                        },
                        {
                            'ETag': 'etag-2',
                            'PartNumber': 2,
                            'ChecksumSHA1': 'sum2==',
                        },
                        {
                            'ETag': 'etag-3',
                            'PartNumber': 3,
                            'ChecksumSHA1': 'sum3==',
                        },
                    ]
                }
            },
        )

        future = self.manager.upload(
            self.filename, self.bucket, self.key, self.extra_args
        )
        future.result()
        self.assert_expected_client_calls_were_correct()

    def test_multipart_upload_sets_s3express_default_checksum(self):
        s3express_bucket = "mytestbucket--usw2-az6--x-s3"
        self.assertFalse('ChecksumAlgorithm' in self.extra_args)

        # ChecksumAlgorithm should be passed on the create_multipart call
        self.add_create_multipart_response_with_default_expected_params(
            extra_expected_params={'ChecksumAlgorithm': 'crc32'},
            bucket=s3express_bucket,
        )

        # ChecksumAlgorithm should be forwarded and a SHA1 will come back
        self.add_upload_part_responses_with_default_expected_params(
            extra_expected_params={'ChecksumAlgorithm': 'crc32'},
            bucket=s3express_bucket,
        )

        # The checksums should be used in the complete call like etags
        self.add_complete_multipart_response_with_default_expected_params(
            extra_expected_params={
                'MultipartUpload': {
                    'Parts': [
                        {
                            'ETag': 'etag-1',
                            'PartNumber': 1,
                            'ChecksumCRC32': 'sum1==',
                        },
                        {
                            'ETag': 'etag-2',
                            'PartNumber': 2,
                            'ChecksumCRC32': 'sum2==',
                        },
                        {
                            'ETag': 'etag-3',
                            'PartNumber': 3,
                            'ChecksumCRC32': 'sum3==',
                        },
                    ]
                }
            },
            bucket=s3express_bucket,
        )

        future = self.manager.upload(
            self.filename, s3express_bucket, self.key, self.extra_args
        )
        future.result()
        self.assert_expected_client_calls_were_correct()

    def test_multipart_upload_with_ssec_args(self):
        params = {
            'RequestPayer': 'requester',
            'SSECustomerKey': 'key',
            'SSECustomerAlgorithm': 'AES256',
            'SSECustomerKeyMD5': 'key-hash',
        }
        self.extra_args.update(params)

        self.add_create_multipart_response_with_default_expected_params(
            extra_expected_params=params
        )

        self.add_upload_part_responses_with_default_expected_params(
            extra_expected_params=params
        )
        self.add_complete_multipart_response_with_default_expected_params(
            extra_expected_params=params
        )
        future = self.manager.upload(
            self.filename, self.bucket, self.key, self.extra_args
        )
        future.result()
        self.assert_expected_client_calls_were_correct()
