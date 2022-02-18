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
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from s3transfer.manager import TransferConfig, TransferManager
from s3transfer.utils import MIN_UPLOAD_CHUNKSIZE
from tests import BaseGeneralInterfaceTest, FileSizeProvider


class BaseCopyTest(BaseGeneralInterfaceTest):
    def setUp(self):
        super().setUp()
        self.config = TransferConfig(
            max_request_concurrency=1,
            multipart_chunksize=MIN_UPLOAD_CHUNKSIZE,
            multipart_threshold=MIN_UPLOAD_CHUNKSIZE * 4,
        )
        self._manager = TransferManager(self.client, self.config)

        # Initialize some default arguments
        self.bucket = 'mybucket'
        self.key = 'mykey'
        self.copy_source = {'Bucket': 'mysourcebucket', 'Key': 'mysourcekey'}
        self.extra_args = {}
        self.subscribers = []

        self.half_chunksize = int(MIN_UPLOAD_CHUNKSIZE / 2)
        self.content = b'0' * (2 * MIN_UPLOAD_CHUNKSIZE + self.half_chunksize)

    @property
    def manager(self):
        return self._manager

    @property
    def method(self):
        return self.manager.copy

    def create_call_kwargs(self):
        return {
            'copy_source': self.copy_source,
            'bucket': self.bucket,
            'key': self.key,
        }

    def create_invalid_extra_args(self):
        return {'Foo': 'bar'}

    def create_stubbed_responses(self):
        return [
            {
                'method': 'head_object',
                'service_response': {'ContentLength': len(self.content)},
            },
            {'method': 'copy_object', 'service_response': {}},
        ]

    def create_expected_progress_callback_info(self):
        return [
            {'bytes_transferred': len(self.content)},
        ]

    def add_head_object_response(self, expected_params=None, stubber=None):
        if not stubber:
            stubber = self.stubber
        head_response = self.create_stubbed_responses()[0]
        if expected_params:
            head_response['expected_params'] = expected_params
        stubber.add_response(**head_response)

    def add_successful_copy_responses(
        self,
        expected_copy_params=None,
        expected_create_mpu_params=None,
        expected_complete_mpu_params=None,
    ):

        # Add all responses needed to do the copy of the object.
        # Should account for both ranged and nonranged downloads.
        stubbed_responses = self.create_stubbed_responses()[1:]

        # If the length of copy responses is greater than one then it is
        # a multipart copy.
        copy_responses = stubbed_responses[0:1]
        if len(stubbed_responses) > 1:
            copy_responses = stubbed_responses[1:-1]

        # Add the expected create multipart upload params.
        if expected_create_mpu_params:
            stubbed_responses[0][
                'expected_params'
            ] = expected_create_mpu_params

        # Add any expected copy parameters.
        if expected_copy_params:
            for i, copy_response in enumerate(copy_responses):
                if isinstance(expected_copy_params, list):
                    copy_response['expected_params'] = expected_copy_params[i]
                else:
                    copy_response['expected_params'] = expected_copy_params

        # Add the expected complete multipart upload params.
        if expected_complete_mpu_params:
            stubbed_responses[-1][
                'expected_params'
            ] = expected_complete_mpu_params

        # Add the responses to the stubber.
        for stubbed_response in stubbed_responses:
            self.stubber.add_response(**stubbed_response)

    def test_can_provide_file_size(self):
        self.add_successful_copy_responses()

        call_kwargs = self.create_call_kwargs()
        call_kwargs['subscribers'] = [FileSizeProvider(len(self.content))]

        future = self.manager.copy(**call_kwargs)
        future.result()

        # The HeadObject should have not happened and should have been able
        # to successfully copy the file.
        self.stubber.assert_no_pending_responses()

    def test_provide_copy_source_as_dict(self):
        self.copy_source['VersionId'] = 'mysourceversionid'
        expected_params = {
            'Bucket': 'mysourcebucket',
            'Key': 'mysourcekey',
            'VersionId': 'mysourceversionid',
        }

        self.add_head_object_response(expected_params=expected_params)
        self.add_successful_copy_responses()

        future = self.manager.copy(**self.create_call_kwargs())
        future.result()
        self.stubber.assert_no_pending_responses()

    def test_invalid_copy_source(self):
        self.copy_source = ['bucket', 'key']
        future = self.manager.copy(**self.create_call_kwargs())
        with self.assertRaises(TypeError):
            future.result()

    def test_provide_copy_source_client(self):
        source_client = self.session.create_client(
            's3',
            'eu-central-1',
            aws_access_key_id='foo',
            aws_secret_access_key='bar',
        )
        source_stubber = Stubber(source_client)
        source_stubber.activate()
        self.addCleanup(source_stubber.deactivate)

        self.add_head_object_response(stubber=source_stubber)
        self.add_successful_copy_responses()

        call_kwargs = self.create_call_kwargs()
        call_kwargs['source_client'] = source_client
        future = self.manager.copy(**call_kwargs)
        future.result()

        # Make sure that all of the responses were properly
        # used for both clients.
        source_stubber.assert_no_pending_responses()
        self.stubber.assert_no_pending_responses()


class TestNonMultipartCopy(BaseCopyTest):
    __test__ = True

    def test_copy(self):
        expected_head_params = {
            'Bucket': 'mysourcebucket',
            'Key': 'mysourcekey',
        }
        expected_copy_object = {
            'Bucket': self.bucket,
            'Key': self.key,
            'CopySource': self.copy_source,
        }
        self.add_head_object_response(expected_params=expected_head_params)
        self.add_successful_copy_responses(
            expected_copy_params=expected_copy_object
        )

        future = self.manager.copy(**self.create_call_kwargs())
        future.result()
        self.stubber.assert_no_pending_responses()

    def test_copy_with_extra_args(self):
        self.extra_args['MetadataDirective'] = 'REPLACE'

        expected_head_params = {
            'Bucket': 'mysourcebucket',
            'Key': 'mysourcekey',
        }
        expected_copy_object = {
            'Bucket': self.bucket,
            'Key': self.key,
            'CopySource': self.copy_source,
            'MetadataDirective': 'REPLACE',
        }

        self.add_head_object_response(expected_params=expected_head_params)
        self.add_successful_copy_responses(
            expected_copy_params=expected_copy_object
        )

        call_kwargs = self.create_call_kwargs()
        call_kwargs['extra_args'] = self.extra_args
        future = self.manager.copy(**call_kwargs)
        future.result()
        self.stubber.assert_no_pending_responses()

    def test_copy_maps_extra_args_to_head_object(self):
        self.extra_args['CopySourceSSECustomerAlgorithm'] = 'AES256'

        expected_head_params = {
            'Bucket': 'mysourcebucket',
            'Key': 'mysourcekey',
            'SSECustomerAlgorithm': 'AES256',
        }
        expected_copy_object = {
            'Bucket': self.bucket,
            'Key': self.key,
            'CopySource': self.copy_source,
            'CopySourceSSECustomerAlgorithm': 'AES256',
        }

        self.add_head_object_response(expected_params=expected_head_params)
        self.add_successful_copy_responses(
            expected_copy_params=expected_copy_object
        )

        call_kwargs = self.create_call_kwargs()
        call_kwargs['extra_args'] = self.extra_args
        future = self.manager.copy(**call_kwargs)
        future.result()
        self.stubber.assert_no_pending_responses()

    def test_allowed_copy_params_are_valid(self):
        op_model = self.client.meta.service_model.operation_model('CopyObject')
        for allowed_upload_arg in self._manager.ALLOWED_COPY_ARGS:
            self.assertIn(allowed_upload_arg, op_model.input_shape.members)

    def test_copy_with_tagging(self):
        extra_args = {'Tagging': 'tag1=val1', 'TaggingDirective': 'REPLACE'}
        self.add_head_object_response()
        self.add_successful_copy_responses(
            expected_copy_params={
                'Bucket': self.bucket,
                'Key': self.key,
                'CopySource': self.copy_source,
                'Tagging': 'tag1=val1',
                'TaggingDirective': 'REPLACE',
            }
        )
        future = self.manager.copy(
            self.copy_source, self.bucket, self.key, extra_args
        )
        future.result()
        self.stubber.assert_no_pending_responses()

    def test_raise_exception_on_s3_object_lambda_resource(self):
        s3_object_lambda_arn = (
            'arn:aws:s3-object-lambda:us-west-2:123456789012:'
            'accesspoint:my-accesspoint'
        )
        with self.assertRaisesRegex(ValueError, 'methods do not support'):
            self.manager.copy(self.copy_source, s3_object_lambda_arn, self.key)

    def test_raise_exception_on_s3_object_lambda_resource_as_source(self):
        source = {
            'Bucket': 'arn:aws:s3-object-lambda:us-west-2:123456789012:'
            'accesspoint:my-accesspoint'
        }
        with self.assertRaisesRegex(ValueError, 'methods do not support'):
            self.manager.copy(source, self.bucket, self.key)


class TestMultipartCopy(BaseCopyTest):
    __test__ = True

    def setUp(self):
        super().setUp()
        self.config = TransferConfig(
            max_request_concurrency=1,
            multipart_threshold=1,
            multipart_chunksize=4,
        )
        self._manager = TransferManager(self.client, self.config)

    def create_stubbed_responses(self):
        return [
            {
                'method': 'head_object',
                'service_response': {'ContentLength': len(self.content)},
            },
            {
                'method': 'create_multipart_upload',
                'service_response': {'UploadId': 'my-upload-id'},
            },
            {
                'method': 'upload_part_copy',
                'service_response': {'CopyPartResult': {'ETag': 'etag-1'}},
            },
            {
                'method': 'upload_part_copy',
                'service_response': {'CopyPartResult': {'ETag': 'etag-2'}},
            },
            {
                'method': 'upload_part_copy',
                'service_response': {'CopyPartResult': {'ETag': 'etag-3'}},
            },
            {'method': 'complete_multipart_upload', 'service_response': {}},
        ]

    def create_expected_progress_callback_info(self):
        # Note that last read is from the empty sentinel indicating
        # that the stream is done.
        return [
            {'bytes_transferred': MIN_UPLOAD_CHUNKSIZE},
            {'bytes_transferred': MIN_UPLOAD_CHUNKSIZE},
            {'bytes_transferred': self.half_chunksize},
        ]

    def add_create_multipart_upload_response(self):
        self.stubber.add_response(**self.create_stubbed_responses()[1])

    def _get_expected_params(self):
        upload_id = 'my-upload-id'

        # Add expected parameters to the head object
        expected_head_params = {
            'Bucket': 'mysourcebucket',
            'Key': 'mysourcekey',
        }

        # Add expected parameters for the create multipart
        expected_create_mpu_params = {
            'Bucket': self.bucket,
            'Key': self.key,
        }

        expected_copy_params = []
        # Add expected parameters to the copy part
        ranges = [
            'bytes=0-5242879',
            'bytes=5242880-10485759',
            'bytes=10485760-13107199',
        ]
        for i, range_val in enumerate(ranges):
            expected_copy_params.append(
                {
                    'Bucket': self.bucket,
                    'Key': self.key,
                    'CopySource': self.copy_source,
                    'UploadId': upload_id,
                    'PartNumber': i + 1,
                    'CopySourceRange': range_val,
                }
            )

        # Add expected parameters for the complete multipart
        expected_complete_mpu_params = {
            'Bucket': self.bucket,
            'Key': self.key,
            'UploadId': upload_id,
            'MultipartUpload': {
                'Parts': [
                    {'ETag': 'etag-1', 'PartNumber': 1},
                    {'ETag': 'etag-2', 'PartNumber': 2},
                    {'ETag': 'etag-3', 'PartNumber': 3},
                ]
            },
        }

        return expected_head_params, {
            'expected_create_mpu_params': expected_create_mpu_params,
            'expected_copy_params': expected_copy_params,
            'expected_complete_mpu_params': expected_complete_mpu_params,
        }

    def _add_params_to_expected_params(
        self, add_copy_kwargs, operation_types, new_params
    ):

        expected_params_to_update = []
        for operation_type in operation_types:
            add_copy_kwargs_key = 'expected_' + operation_type + '_params'
            expected_params = add_copy_kwargs[add_copy_kwargs_key]
            if isinstance(expected_params, list):
                expected_params_to_update.extend(expected_params)
            else:
                expected_params_to_update.append(expected_params)

        for expected_params in expected_params_to_update:
            expected_params.update(new_params)

    def test_copy(self):
        head_params, add_copy_kwargs = self._get_expected_params()
        self.add_head_object_response(expected_params=head_params)
        self.add_successful_copy_responses(**add_copy_kwargs)

        future = self.manager.copy(**self.create_call_kwargs())
        future.result()
        self.stubber.assert_no_pending_responses()

    def test_copy_with_extra_args(self):
        # This extra argument should be added to the head object,
        # the create multipart upload, and upload part copy.
        self.extra_args['RequestPayer'] = 'requester'

        head_params, add_copy_kwargs = self._get_expected_params()
        head_params.update(self.extra_args)
        self.add_head_object_response(expected_params=head_params)

        self._add_params_to_expected_params(
            add_copy_kwargs,
            ['create_mpu', 'copy', 'complete_mpu'],
            self.extra_args,
        )
        self.add_successful_copy_responses(**add_copy_kwargs)

        call_kwargs = self.create_call_kwargs()
        call_kwargs['extra_args'] = self.extra_args
        future = self.manager.copy(**call_kwargs)
        future.result()
        self.stubber.assert_no_pending_responses()

    def test_copy_blacklists_args_to_create_multipart(self):
        # This argument can never be used for multipart uploads
        self.extra_args['MetadataDirective'] = 'COPY'

        head_params, add_copy_kwargs = self._get_expected_params()
        self.add_head_object_response(expected_params=head_params)
        self.add_successful_copy_responses(**add_copy_kwargs)

        call_kwargs = self.create_call_kwargs()
        call_kwargs['extra_args'] = self.extra_args
        future = self.manager.copy(**call_kwargs)
        future.result()
        self.stubber.assert_no_pending_responses()

    def test_copy_args_to_only_create_multipart(self):
        self.extra_args['ACL'] = 'private'

        head_params, add_copy_kwargs = self._get_expected_params()
        self.add_head_object_response(expected_params=head_params)

        self._add_params_to_expected_params(
            add_copy_kwargs, ['create_mpu'], self.extra_args
        )
        self.add_successful_copy_responses(**add_copy_kwargs)

        call_kwargs = self.create_call_kwargs()
        call_kwargs['extra_args'] = self.extra_args
        future = self.manager.copy(**call_kwargs)
        future.result()
        self.stubber.assert_no_pending_responses()

    def test_copy_passes_args_to_create_multipart_and_upload_part(self):
        # This will only be used for the complete multipart upload
        # and upload part.
        self.extra_args['SSECustomerAlgorithm'] = 'AES256'

        head_params, add_copy_kwargs = self._get_expected_params()
        self.add_head_object_response(expected_params=head_params)

        self._add_params_to_expected_params(
            add_copy_kwargs, ['create_mpu', 'copy'], self.extra_args
        )
        self.add_successful_copy_responses(**add_copy_kwargs)

        call_kwargs = self.create_call_kwargs()
        call_kwargs['extra_args'] = self.extra_args
        future = self.manager.copy(**call_kwargs)
        future.result()
        self.stubber.assert_no_pending_responses()

    def test_copy_maps_extra_args_to_head_object(self):
        self.extra_args['CopySourceSSECustomerAlgorithm'] = 'AES256'

        head_params, add_copy_kwargs = self._get_expected_params()

        # The CopySourceSSECustomerAlgorithm needs to get mapped to
        # SSECustomerAlgorithm for HeadObject
        head_params['SSECustomerAlgorithm'] = 'AES256'
        self.add_head_object_response(expected_params=head_params)

        # However, it needs to remain the same for UploadPartCopy.
        self._add_params_to_expected_params(
            add_copy_kwargs, ['copy'], self.extra_args
        )
        self.add_successful_copy_responses(**add_copy_kwargs)

        call_kwargs = self.create_call_kwargs()
        call_kwargs['extra_args'] = self.extra_args
        future = self.manager.copy(**call_kwargs)
        future.result()
        self.stubber.assert_no_pending_responses()

    def test_abort_on_failure(self):
        # First add the head object and create multipart upload
        self.add_head_object_response()
        self.add_create_multipart_upload_response()

        # Cause an error on upload_part_copy
        self.stubber.add_client_error('upload_part_copy', 'ArbitraryFailure')

        # Add the abort multipart to ensure it gets cleaned up on failure
        self.stubber.add_response(
            'abort_multipart_upload',
            service_response={},
            expected_params={
                'Bucket': self.bucket,
                'Key': self.key,
                'UploadId': 'my-upload-id',
            },
        )

        future = self.manager.copy(**self.create_call_kwargs())
        with self.assertRaisesRegex(ClientError, 'ArbitraryFailure'):
            future.result()
        self.stubber.assert_no_pending_responses()

    def test_mp_copy_with_tagging_directive(self):
        extra_args = {'Tagging': 'tag1=val1', 'TaggingDirective': 'REPLACE'}
        self.add_head_object_response()
        self.add_successful_copy_responses(
            expected_create_mpu_params={
                'Bucket': self.bucket,
                'Key': self.key,
                'Tagging': 'tag1=val1',
            }
        )
        future = self.manager.copy(
            self.copy_source, self.bucket, self.key, extra_args
        )
        future.result()
        self.stubber.assert_no_pending_responses()
