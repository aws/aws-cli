# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import mock, BaseAWSCommandParamsTest, FileCreator
from awscli.compat import BytesIO

class BaseS3TransferCommandTest(BaseAWSCommandParamsTest):
    def setUp(self):
        super(BaseS3TransferCommandTest, self).setUp()
        self.files = FileCreator()

    def tearDown(self):
        super(BaseS3TransferCommandTest, self).tearDown()
        self.files.remove_all()

    def assert_operations_called(self, expected_operations_with_params):
        actual_operations_with_params = [
            (operation_called[0].name, operation_called[1])
            for operation_called in self.operations_called
        ]
        self.assertEqual(
            actual_operations_with_params, expected_operations_with_params)

    def head_object_response(self, **override_kwargs):
        response = {
            'ContentLength': 100,
            'LastModified': '00:00:00Z'
        }
        response.update(override_kwargs)
        return response

    def list_objects_response(self, keys):
        contents = []
        for key in keys:
            contents.append(
                {
                    'Key': key,
                    'LastModified': '00:00:00Z',
                    'Size': 100
                }
            )

        return {
            'Contents': contents,
            'CommonPrefixes': []
        }

    def get_object_response(self):
        return {
            'ETag': '"foo-1"',
            'Body': BytesIO(b'foo')
        }

    def copy_object_response(self):
        return self.empty_response()

    def delete_object_response(self):
        return self.empty_response()

    def create_mpu_response(self, upload_id):
        return {
            'UploadId': upload_id
        }

    def upload_part_copy_response(self):
        return {
            'CopyPartResult': {
                'ETag': '"etag"'
            }
        }

    def complete_mpu_response(self):
        return self.empty_response()

    def empty_response(self):
        return {}

    def head_object_request(self, bucket, key, **override_kwargs):
        params = {
            'Bucket': bucket,
            'Key': key,
        }
        params.update(override_kwargs)
        return 'HeadObject', params

    def list_objects_request(self, bucket, prefix=None, **override_kwargs):
        params = {
            'Bucket': bucket,
        }
        if prefix is None:
            params['Prefix'] = ''
        params.update(override_kwargs)
        return 'ListObjectsV2', params

    def put_object_request(self, bucket, key, **override_kwargs):
        params = {
            'Bucket': bucket,
            'Key': key,
            'ChecksumAlgorithm': 'CRC32',
            'Body': mock.ANY,
        }
        params.update(override_kwargs)
        return 'PutObject', params

    def get_object_request(self, bucket, key, **override_kwargs):
        params = {
            'Bucket': bucket,
            'Key': key,
        }
        params.update(override_kwargs)
        return 'GetObject', params

    def copy_object_request(self, source_bucket, source_key, bucket, key,
                            **override_kwargs):
        params = {
            'Bucket': bucket,
            'Key': key,
            'CopySource': {
                'Bucket': source_bucket,
                'Key': source_key
            }
        }
        params.update(override_kwargs)
        return 'CopyObject', params

    def delete_object_request(self, bucket, key, **override_kwargs):
        params = {
            'Bucket': bucket,
            'Key': key,
        }
        params.update(override_kwargs)
        return 'DeleteObject', params

    def create_mpu_request(self, bucket, key, **override_kwargs):
        params = {
            'Bucket': bucket,
            'Key': key,
        }
        params.update(override_kwargs)
        return 'CreateMultipartUpload', params

    def upload_part_copy_request(self, source_bucket, source_key, bucket, key,
                                 upload_id, **override_kwargs):
        params = {
            'Bucket': bucket,
            'Key': key,
            'CopySource': {
                'Bucket': source_bucket,
                'Key': source_key
            },
            'UploadId': upload_id,

        }
        params.update(override_kwargs)
        return 'UploadPartCopy', params

    def complete_mpu_request(self, bucket, key, upload_id, num_parts,
                             **override_kwargs):
        parts = []
        for i in range(num_parts):
            parts.append(
                {
                    'ETag': '"etag"', 'PartNumber': i + 1
                }
            )
        params = {
            'Bucket': bucket,
            'Key': key,
            'UploadId': upload_id,
            'MultipartUpload': {'Parts': parts}
        }
        params.update(override_kwargs)
        return 'CompleteMultipartUpload', params
