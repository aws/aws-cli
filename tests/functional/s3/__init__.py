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
import mock
import os

from awscrt.s3 import S3Request
from botocore.awsrequest import AWSResponse

from tests import CLIRunner, SessionStubber, HTTPResponse
from awscli.clidriver import AWSCLIEntryPoint
from awscli.testutils import unittest, create_clidriver, temporary_file
from awscli.testutils import BaseAWSCommandParamsTest, FileCreator
from awscli.compat import six


class BaseS3TransferCommandTest(BaseAWSCommandParamsTest):
    def setUp(self):
        super(BaseS3TransferCommandTest, self).setUp()
        self.files = FileCreator()
        self.init_clidriver()

    def init_clidriver(self):
        with temporary_file('w') as f:
            f.write(
                '[default]\n'
                's3 =\n'
                '  max_concurrent_requests = 1\n'
            )
            f.flush()
            self.environ['AWS_CONFIG_FILE'] = f.name
            self.driver = create_clidriver()
            self.entry_point = AWSCLIEntryPoint(self.driver)

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

    def assert_in_operations_called(self, expected_operation_with_params):
        actual_operations_with_params = [
            (operation_called[0].name, operation_called[1])
            for operation_called in self.operations_called
        ]
        for actual_operation_with_params in actual_operations_with_params:
            if expected_operation_with_params == actual_operation_with_params:
                return
        self.fail(
            'Expected request: %s does not match any of the actual requests '
            'made: %s' % (
                expected_operation_with_params, actual_operations_with_params
            )
        )

    def head_object_response(self, **override_kwargs):
        response = {
            'ContentLength': 100,
            'LastModified': '00:00:00Z'
        }
        response.update(override_kwargs)
        return response

    def list_objects_response(self, keys, **override_kwargs):
        contents = []
        for key in keys:
            content = {
                'Key': key,
                'LastModified': '00:00:00Z',
                'Size': 100
            }
            if override_kwargs:
                content.update(override_kwargs)
            contents.append(content)
        return {
            'Contents': contents,
            'CommonPrefixes': []
        }

    def get_object_response(self):
        return {
            'ETag': '"foo-1"',
            'Body': six.BytesIO(b'foo')
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

    def get_object_tagging_response(self, tags):
        return {
            'TagSet': [{'Key': k, 'Value': v} for k, v in tags.items()]
        }

    def put_object_tagging_response(self):
        return 'PutObjectTagging', self.empty_response()

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

    def get_object_tagging_request(self, bucket, key):
        return 'GetObjectTagging', {
            'Bucket': bucket,
            'Key': key,
        }

    def put_object_tagging_request(self, bucket, key, tags):
        return 'PutObjectTagging', {
            'Bucket': bucket,
            'Key': key,
            'Tagging': {
                'TagSet': [
                    {'Key': k, 'Value': v} for k, v in tags.items()
                ],
            }
        }

    def no_such_key_error_response(self):
        return {
            'Error': {
                'Code': 'NoSuchKey',
                'Message': 'The specified key does not exist',
            }
        }

    def access_denied_error_response(self):
        return {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'Operation not allowed',
            }
        }

    def set_http_status_codes(self, status_codes):
        self.http_responses = [
            AWSResponse(None, code, {}, None) for code in status_codes
        ]

    def mp_copy_responses(self):
        return [
            self.create_mpu_response('upload_id'),
            self.upload_part_copy_response(),
            self.complete_mpu_response(),
        ]


class BaseCRTTransferClientTest(unittest.TestCase):
    def setUp(self):
        self.crt_client_patch = mock.patch('s3transfer.crt.S3Client')
        self.mock_crt_client = self.crt_client_patch.start()
        self.mock_crt_client.return_value.make_request.side_effect = \
            self.simulate_make_request_side_effect
        self.captured_on_done_callbacks = []
        self.config_files = FileCreator()
        self.config_filename = os.path.join(
            self.config_files.rootdir, 'config')
        self.files = FileCreator()
        self.session_stubber = IgnoreCRTRequestsSessionStubber()
        self.cli_runner = CLIRunner(session_stubber=self.session_stubber)
        self.set_config_file_contents(
            self.cli_runner.env, self.config_filename)
        self.region = 'us-west-2'
        self.cli_runner.env['AWS_DEFAULT_REGION'] = self.region

    def tearDown(self):
        self.crt_client_patch.stop()
        self.config_files.remove_all()
        self.files.remove_all()

    def set_config_file_contents(self, env, config_filename):
        with open(config_filename, 'w') as f:
            f.write(
                '[default]\n'
                's3 =\n'
                '  preferred_transfer_client = crt\n'
                '  max_concurrent_requests = 1\n'
            )
            f.flush()
        env['AWS_CONFIG_FILE'] = config_filename

    def simulate_make_request_side_effect(self, *args, **kwargs):
        if kwargs.get('recv_filepath'):
            parent_dir = os.path.dirname(kwargs['recv_filepath'])
            if not os.path.isdir(parent_dir):
                os.makedirs(parent_dir)
            with open(kwargs['recv_filepath'], 'w') as f:
                f.write('content')
        if kwargs.get('on_done'):
            # Ideally we just run the on_done callbacks here. The
            # on_done callbacks often call the transfer future's result()
            # method. However, the transfer future relies on an underlying
            # CRT future from the returned S3Request object when calling
            # result(). If we call on_done here, the underlying future is
            # not available as it has not been returned yet which makes the
            # the on_done callback fail. So instead, we collect the on_done
            # callbacks and invoke them at a later part to fully simulate
            # the transfer.
            self.captured_on_done_callbacks.append(kwargs.get('on_done'))
        return mock.Mock(S3Request)

    def run_command(self, cmdline):
        result = self.cli_runner.run(cmdline)
        self.assertEqual(result.rc, 0)
        self.run_on_done_callbacks()

    def run_on_done_callbacks(self):
        for done_callback in self.captured_on_done_callbacks:
            done_callback(error=None)

    def get_virtual_s3_host(self, bucket):
        return f'{bucket}.s3.{self.region}.amazonaws.com'

    def get_crt_make_request_calls(self):
        return self.mock_crt_client.return_value.make_request.call_args_list

    def add_botocore_head_object_response(self):
        self.cli_runner.add_response(
            HTTPResponse(
                headers={
                    'Content-Length': '100',
                    'Last-Modified': 'Thu, 11 Feb 2021 04:24:23 GMT',
                }
            )
        )

    def add_botocore_list_objects_response(self, keys):
        xml_body = (
            '<?xml version="1.0" ?>'
            '<ListBucketResult xmlns='
            '"http://s3.amazonaws.com/doc/2006-03-01/">'
            '<Prefix/>'
        )
        for key in keys:
            xml_body += (
                '<Contents>'
                '<LastModified>2015-12-08T18:26:43.000Z</LastModified>'
                f'<Key>{key}</Key>'
                '<Size>100</Size>'
                '</Contents>'
            )
        xml_body += '</ListBucketResult>'
        self.cli_runner.add_response(HTTPResponse(body=xml_body))

    def add_botocore_put_object_response(self):
        self.cli_runner.add_response(HTTPResponse())

    def add_botocore_get_object_response(self):
        self.cli_runner.add_response(
            HTTPResponse(headers={'ETag': '"foo-1"'}, body=six.BytesIO(b'foo'))
        )

    def add_botocore_copy_object_response(self):
        self.cli_runner.add_response(
            HTTPResponse(body='<CopyObjectResult></CopyObjectResult>')
        )

    def add_botocore_delete_object_response(self):
        self.cli_runner.add_response(HTTPResponse())

    def assert_crt_make_request_call(
            self, make_request_call, expected_type, expected_host,
            expected_path, expected_http_method=None,
            expected_send_filepath=None,
            expected_recv_startswith=None):
        make_request_kwargs = make_request_call[1]
        self.assertEqual(
            make_request_kwargs['type'], expected_type)
        self.assertEqual(
            make_request_kwargs['request'].headers.get('host'),
            expected_host
        )
        self.assertEqual(
            make_request_kwargs['request'].path, expected_path)
        if expected_http_method:
            self.assertEqual(
                make_request_kwargs['request'].method, expected_http_method)
        if expected_send_filepath:
            self.assertEqual(
                make_request_kwargs['send_filepath'], expected_send_filepath)
        if expected_recv_startswith:
            # The s3transfer/crt implementation has the CRT client download
            # to a temporary file before moving it to the correct location.
            # This temporary file is just the normal file name with some
            # characters appended to the end. So we are just asserting that
            # the temporary filename being used seems appropriate by seeing if
            # it starts with the final filename as we are not really able to
            # mock out and assert any part of the HTTP layer
            # of the CRT client.
            self.assertTrue(
                make_request_kwargs['recv_filepath'].startswith(
                    expected_recv_startswith
                ), (
                    f"{make_request_kwargs['recv_filepath']} does not "
                    f"start with {expected_recv_startswith}"
                )
            )

    def assert_no_remaining_botocore_responses(self):
        self.session_stubber.assert_no_remaining_responses()


# The CRT integrations use botocore clients to serialize the request.
# This affects the normal stubber because even though no HTTP requests
# get sent when the client is used to serialize HTTP requests, the stubber
# will still try to provide an HTTP response even though its not needed.
# So this class detects if a call is being made just for the serialization of
# an HTTP request for the CRT client by checking if the request is
# signed as these requests get signed by the CRT client. And if the
# request is intended for the CRT client, it does not send a response back.
class IgnoreCRTRequestsSessionStubber(SessionStubber):
    def _return_queued_http_response(self, request, **kwargs):
        if 'Authorization' not in request.headers:
            return
        response = self._responses.popleft()
        return response.on_http_request_sent(request)
