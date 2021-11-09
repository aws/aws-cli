# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import base64
import re

import pytest

from tests import (
    create_session, mock, temporary_file, unittest,
    BaseSessionTest, ClientHTTPStubber, FreezeTime
)

import botocore.session
from botocore.config import Config
from botocore.compat import datetime, urlsplit, parse_qs, get_md5
from botocore.exceptions import (
    ParamValidationError, ClientError,
    UnsupportedS3ConfigurationError,
    UnsupportedS3AccesspointConfigurationError,
)
from botocore.parsers import ResponseParserError
from botocore.loaders import Loader
from botocore import UNSIGNED


DATE = datetime.datetime(2021, 8, 27, 0, 0, 0)


class TestS3BucketValidation(unittest.TestCase):
    def test_invalid_bucket_name_raises_error(self):
        session = botocore.session.get_session()
        s3 = session.create_client('s3')
        with self.assertRaises(ParamValidationError):
            s3.put_object(Bucket='adfgasdfadfs/bucket/name',
                          Key='foo', Body=b'asdf')


class BaseS3OperationTest(BaseSessionTest):
    def setUp(self):
        super(BaseS3OperationTest, self).setUp()
        self.region = 'us-west-2'
        self.client = self.session.create_client(
            's3', self.region)
        self.http_stubber = ClientHTTPStubber(self.client)


class BaseS3ClientConfigurationTest(BaseSessionTest):
    _V4_AUTH_REGEX = re.compile(
        r'AWS4-HMAC-SHA256 '
        r'Credential=\w+/\d+/'
        r'(?P<signing_region>[a-z0-9-]+)/'
        r'(?P<signing_name>[a-z0-9-]+)/'
    )

    def setUp(self):
        super(BaseS3ClientConfigurationTest, self).setUp()
        self.region = 'us-west-2'

    def assert_signing_region(self, request, expected_region):
        auth_header = request.headers['Authorization'].decode('utf-8')
        actual_region = None
        match = self._V4_AUTH_REGEX.match(auth_header)
        if match:
            actual_region = match.group('signing_region')
        self.assertEqual(expected_region, actual_region)

    def assert_signing_name(self, request, expected_name):
        auth_header = request.headers['Authorization'].decode('utf-8')
        actual_name = None
        match = self._V4_AUTH_REGEX.match(auth_header)
        if match:
            actual_name = match.group('signing_name')
        self.assertEqual(expected_name, actual_name)

    def assert_signing_region_in_url(self, url, expected_region):
        qs_components = parse_qs(urlsplit(url).query)
        self.assertIn(expected_region, qs_components['X-Amz-Credential'][0])

    def assert_endpoint(self, request, expected_endpoint):
        actual_endpoint = urlsplit(request.url).netloc
        self.assertEqual(actual_endpoint, expected_endpoint)

    def create_s3_client(self, **kwargs):
        client_kwargs = {
            'region_name': self.region
        }
        client_kwargs.update(kwargs)
        return self.session.create_client('s3', **client_kwargs)

    def set_config_file(self, fileobj, contents):
        fileobj.write(contents)
        fileobj.flush()
        self.environ['AWS_CONFIG_FILE'] = fileobj.name


class TestS3ClientConfigResolution(BaseS3ClientConfigurationTest):
    def test_no_s3_config(self):
        client = self.create_s3_client()
        self.assertIsNone(client.meta.config.s3)

    def test_client_s3_dualstack_handles_uppercase_true(self):
        with temporary_file('w') as f:
            self.set_config_file(
                f,
                '[default]\n'
                's3 = \n'
                '    use_dualstack_endpoint = True'
            )
            client = self.create_s3_client()
            self.assertEqual(
                client.meta.config.s3['use_dualstack_endpoint'], True)

    def test_client_s3_dualstack_handles_lowercase_true(self):
        with temporary_file('w') as f:
            self.set_config_file(
                f,
                '[default]\n'
                's3 = \n'
                '    use_dualstack_endpoint = true'
            )
            client = self.create_s3_client()
            self.assertEqual(
                client.meta.config.s3['use_dualstack_endpoint'], True)

    def test_client_s3_accelerate_handles_uppercase_true(self):
        with temporary_file('w') as f:
            self.set_config_file(
                f,
                '[default]\n'
                's3 = \n'
                '    use_accelerate_endpoint = True'
            )
            client = self.create_s3_client()
            self.assertEqual(
                client.meta.config.s3['use_accelerate_endpoint'], True)

    def test_client_s3_accelerate_handles_lowercase_true(self):
        with temporary_file('w') as f:
            self.set_config_file(
                f,
                '[default]\n'
                's3 = \n'
                '    use_accelerate_endpoint = true'
            )
            client = self.create_s3_client()
            self.assertEqual(
                client.meta.config.s3['use_accelerate_endpoint'], True)

    def test_client_payload_signing_enabled_handles_uppercase_true(self):
        with temporary_file('w') as f:
            self.set_config_file(
                f,
                '[default]\n'
                's3 = \n'
                '    payload_signing_enabled = True'
            )
            client = self.create_s3_client()
            self.assertEqual(
                client.meta.config.s3['payload_signing_enabled'], True)

    def test_client_payload_signing_enabled_handles_lowercase_true(self):
        with temporary_file('w') as f:
            self.set_config_file(
                f,
                '[default]\n'
                's3 = \n'
                '    payload_signing_enabled = true'
            )
            client = self.create_s3_client()
            self.assertEqual(
                client.meta.config.s3['payload_signing_enabled'], True)

    def test_includes_unmodeled_s3_config_vars(self):
        with temporary_file('w') as f:
            self.set_config_file(
                f,
                '[default]\n'
                's3 = \n'
                '    unmodeled = unmodeled_val'
            )
            client = self.create_s3_client()
            self.assertEqual(
                client.meta.config.s3['unmodeled'], 'unmodeled_val')

    def test_mixed_modeled_and_unmodeled_config_vars(self):
        with temporary_file('w') as f:
            self.set_config_file(
                f,
                '[default]\n'
                's3 = \n'
                '    payload_signing_enabled = true\n'
                '    unmodeled = unmodeled_val'
            )
            client = self.create_s3_client()
            self.assertEqual(
                client.meta.config.s3,
                {
                    'payload_signing_enabled': True,
                    'unmodeled': 'unmodeled_val'
                }
            )

    def test_use_arn_region(self):
        self.environ['AWS_S3_USE_ARN_REGION'] = 'true'
        client = self.create_s3_client()
        self.assertEqual(
            client.meta.config.s3,
            {
                'use_arn_region': True,
            }
        )

    def test_use_arn_region_config_var(self):
        with temporary_file('w') as f:
            self.set_config_file(
                f,
                '[default]\n'
                's3_use_arn_region = true'
            )
            client = self.create_s3_client()
            self.assertEqual(
                client.meta.config.s3,
                {
                    'use_arn_region': True,
                }
            )

    def test_use_arn_region_nested_config_var(self):
        with temporary_file('w') as f:
            self.set_config_file(
                f,
                '[default]\n'
                's3 = \n'
                '    use_arn_region = true'
            )
            client = self.create_s3_client()
            self.assertEqual(
                client.meta.config.s3,
                {
                    'use_arn_region': True,
                }
            )

    def test_use_arn_region_is_case_insensitive(self):
        self.environ['AWS_S3_USE_ARN_REGION'] = 'True'
        client = self.create_s3_client()
        self.assertEqual(
            client.meta.config.s3,
            {
                'use_arn_region': True,
            }
        )

    def test_use_arn_region_env_var_overrides_config_var(self):
        self.environ['AWS_S3_USE_ARN_REGION'] = 'false'
        with temporary_file('w') as f:
            self.set_config_file(
                f,
                '[default]\n'
                's3 = \n'
                '    use_arn_region = true'
            )
            client = self.create_s3_client()
        self.assertEqual(
            client.meta.config.s3,
            {
                'use_arn_region': False,
            }
        )

    def test_client_config_use_arn_region_overrides_env_var(self):
        self.environ['AWS_S3_USE_ARN_REGION'] = 'true'
        client = self.create_s3_client(
            config=Config(
                s3={'use_arn_region': False}
            )
        )
        self.assertEqual(
            client.meta.config.s3,
            {
                'use_arn_region': False,
            }
        )

    def test_client_config_use_arn_region_overrides_config_var(self):
        with temporary_file('w') as f:
            self.set_config_file(
                f,
                '[default]\n'
                's3 = \n'
                '    use_arn_region = true'
            )
            client = self.create_s3_client(
                config=Config(
                    s3={'use_arn_region': False}
                )
            )
        self.assertEqual(
            client.meta.config.s3,
            {
                'use_arn_region': False,
            }
        )

    def test_use_arn_region_is_case_insensitive(self):
        self.environ['AWS_S3_USE_ARN_REGION'] = 'True'
        client = self.create_s3_client()
        self.assertEqual(
            client.meta.config.s3,
            {
                'use_arn_region': True,
            }
        )

    def test_client_region_defaults_to_aws_global(self):
        client = self.create_s3_client(region_name=None)
        self.assertEqual(client.meta.region_name, 'aws-global')

    def test_client_region_remains_us_east_1(self):
        client = self.create_s3_client(region_name='us-east-1')
        self.assertEqual(client.meta.region_name, 'us-east-1')

    def test_client_region_remains_aws_global(self):
        client = self.create_s3_client(region_name='aws-global')
        self.assertEqual(client.meta.region_name, 'aws-global')


class TestS3Copy(BaseS3OperationTest):

    def create_s3_client(self, **kwargs):
        client_kwargs = {
            'region_name': self.region
        }
        client_kwargs.update(kwargs)
        return self.session.create_client('s3', **client_kwargs)

    def create_stubbed_s3_client(self, **kwargs):
        client = self.create_s3_client(**kwargs)
        http_stubber = ClientHTTPStubber(client)
        http_stubber.start()
        return client, http_stubber

    def test_s3_copy_object_with_empty_response(self):
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            region_name='us-east-1'
        )

        empty_body = b''
        complete_body = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n\n'
            b'<CopyObjectResult '
            b'xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
            b'<LastModified>2020-04-21T21:03:31.000Z</LastModified>'
            b'<ETag>&quot;s0mEcH3cK5uM&quot;</ETag></CopyObjectResult>'
        )

        self.http_stubber.add_response(status=200, body=empty_body)
        self.http_stubber.add_response(status=200, body=complete_body)
        response = self.client.copy_object(
            Bucket='bucket',
            CopySource='other-bucket/test.txt',
            Key='test.txt',
        )

        # Validate we retried and got second body
        self.assertEqual(len(self.http_stubber.requests), 2)
        self.assertEqual(response['ResponseMetadata']['HTTPStatusCode'], 200)
        self.assertTrue('CopyObjectResult' in response)

    def test_s3_copy_object_with_incomplete_response(self):
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            region_name='us-east-1'
        )

        incomplete_body = b'<?xml version="1.0" encoding="UTF-8"?>\n\n\n'
        self.http_stubber.add_response(status=200, body=incomplete_body)
        with self.assertRaises(ResponseParserError):
            self.client.copy_object(
                Bucket='bucket',
                CopySource='other-bucket/test.txt',
                Key='test.txt',
            )


class TestAccesspointArn(BaseS3ClientConfigurationTest):
    def setUp(self):
        super(TestAccesspointArn, self).setUp()
        self.client, self.http_stubber = self.create_stubbed_s3_client()

    def create_stubbed_s3_client(self, **kwargs):
        client = self.create_s3_client(**kwargs)
        http_stubber = ClientHTTPStubber(client)
        http_stubber.start()
        return client, http_stubber

    def assert_expected_copy_source_header(self,
                                           http_stubber, expected_copy_source):
        request = self.http_stubber.requests[0]
        self.assertIn('x-amz-copy-source', request.headers)
        self.assertEqual(
            request.headers['x-amz-copy-source'], expected_copy_source)

    def add_copy_object_response(self, http_stubber):
        http_stubber.add_response(
            body=b'<CopyObjectResult></CopyObjectResult>'
        )

    def assert_endpoint(self, request, expected_endpoint):
        actual_endpoint = urlsplit(request.url).netloc
        self.assertEqual(actual_endpoint, expected_endpoint)

    def assert_header_matches(self, request, header_key, expected_value):
        self.assertEqual(request.headers.get(header_key), expected_value)

    def test_missing_account_id_in_arn(self):
        accesspoint_arn = (
            'arn:aws:s3:us-west-2::accesspoint:myendpoint'
        )
        with self.assertRaises(botocore.exceptions.ParamValidationError):
            self.client.list_objects(Bucket=accesspoint_arn)

    def test_missing_accesspoint_name_in_arn(self):
        accesspoint_arn = (
            'arn:aws:s3:us-west-2:123456789012:accesspoint'
        )
        with self.assertRaises(botocore.exceptions.ParamValidationError):
            self.client.list_objects(Bucket=accesspoint_arn)

    def test_accesspoint_includes_asterisk(self):
        accesspoint_arn = (
            'arn:aws:s3:us-west-2:123456789012:accesspoint:*'
        )
        with self.assertRaises(botocore.exceptions.ParamValidationError):
            self.client.list_objects(Bucket=accesspoint_arn)

    def test_accesspoint_arn_contains_subresources(self):
        accesspoint_arn = (
            'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint:object'
        )
        with self.assertRaises(botocore.exceptions.ParamValidationError):
            self.client.list_objects(Bucket=accesspoint_arn)

    def test_accesspoint_arn_with_custom_endpoint(self):
        accesspoint_arn = (
            'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint'
        )
        self.client, http_stubber = self.create_stubbed_s3_client(
            endpoint_url='https://custom.com')
        http_stubber.add_response()
        self.client.list_objects(Bucket=accesspoint_arn)
        expected_endpoint = 'myendpoint-123456789012.custom.com'
        self.assert_endpoint(http_stubber.requests[0], expected_endpoint)

    def test_accesspoint_arn_with_custom_endpoint_and_dualstack(self):
        accesspoint_arn = (
            'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint'
        )
        self.client, http_stubber = self.create_stubbed_s3_client(
            endpoint_url='https://custom.com',
            config=Config(s3={'use_dualstack_endpoint': True}))
        http_stubber.add_response()
        self.client.list_objects(Bucket=accesspoint_arn)
        expected_endpoint = 'myendpoint-123456789012.custom.com'
        self.assert_endpoint(http_stubber.requests[0], expected_endpoint)

    def test_accesspoint_arn_with_s3_accelerate(self):
        accesspoint_arn = (
            'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint'
        )
        self.client, _ = self.create_stubbed_s3_client(
            config=Config(s3={'use_accelerate_endpoint': True}))
        with self.assertRaises(
                botocore.exceptions.
                UnsupportedS3AccesspointConfigurationError):
            self.client.list_objects(Bucket=accesspoint_arn)

    def test_accesspoint_arn_cross_partition(self):
        accesspoint_arn = (
            'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint'
        )
        self.client, _ = self.create_stubbed_s3_client(
            region_name='cn-north-1')
        with self.assertRaises(
                botocore.exceptions.
                UnsupportedS3AccesspointConfigurationError):
            self.client.list_objects(Bucket=accesspoint_arn)

    def test_accesspoint_arn_cross_partition_use_client_region(self):
        accesspoint_arn = (
            'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint'
        )
        self.client, _ = self.create_stubbed_s3_client(
            region_name='cn-north-1',
            config=Config(s3={'use_accelerate_endpoint': True})
        )
        with self.assertRaises(
                botocore.exceptions.
                UnsupportedS3AccesspointConfigurationError):
            self.client.list_objects(Bucket=accesspoint_arn)

    def test_signs_with_arn_region(self):
        accesspoint_arn = (
            'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint'
        )
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            region_name='us-east-1')
        self.http_stubber.add_response()
        self.client.list_objects(Bucket=accesspoint_arn)
        self.assert_signing_region(self.http_stubber.requests[0], 'us-west-2')

    def test_signs_with_client_region_when_use_arn_region_false(self):
        accesspoint_arn = (
            'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint'
        )
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            region_name='us-east-1',
            config=Config(s3={'use_arn_region': False})
        )
        self.http_stubber.add_response()
        self.client.list_objects(Bucket=accesspoint_arn)
        self.assert_signing_region(self.http_stubber.requests[0], 'us-east-1')

    def test_presign_signs_with_arn_region(self):
        accesspoint_arn = (
            'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint'
        )
        self.client, _ = self.create_stubbed_s3_client(
            region_name='us-east-1',
            config=Config(signature_version='s3v4')
        )
        url = self.client.generate_presigned_url(
            'get_object', {'Bucket': accesspoint_arn, 'Key': 'mykey'})
        self.assert_signing_region_in_url(url, 'us-west-2')

    def test_presign_signs_with_client_region_when_use_arn_region_false(self):
        accesspoint_arn = (
            'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint'
        )
        self.client, _ = self.create_stubbed_s3_client(
            region_name='us-east-1',
            config=Config(
                signature_version='s3v4', s3={'use_arn_region': False}
            )
        )
        url = self.client.generate_presigned_url(
            'get_object', {'Bucket': accesspoint_arn, 'Key': 'mykey'})
        self.assert_signing_region_in_url(url, 'us-east-1')

    def test_copy_source_str_with_accesspoint_arn(self):
        copy_source = (
            'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint/'
            'object/myprefix/myobject'
        )
        self.client, self.http_stubber = self.create_stubbed_s3_client()
        self.add_copy_object_response(self.http_stubber)
        self.client.copy_object(
            Bucket='mybucket', Key='mykey', CopySource=copy_source
        )
        self.assert_expected_copy_source_header(
            self.http_stubber,
            expected_copy_source=(
                b'arn%3Aaws%3As3%3Aus-west-2%3A123456789012%3Aaccesspoint%3A'
                b'myendpoint/object/myprefix/myobject'
            )
        )

    def test_copy_source_str_with_accesspoint_arn_and_version_id(self):
        copy_source = (
            'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint/'
            'object/myprefix/myobject?versionId=myversionid'
        )
        self.client, self.http_stubber = self.create_stubbed_s3_client()
        self.add_copy_object_response(self.http_stubber)
        self.client.copy_object(
            Bucket='mybucket', Key='mykey', CopySource=copy_source
        )
        self.assert_expected_copy_source_header(
            self.http_stubber,
            expected_copy_source=(
                b'arn%3Aaws%3As3%3Aus-west-2%3A123456789012%3Aaccesspoint%3A'
                b'myendpoint/object/myprefix/myobject?versionId=myversionid'
            )
        )

    def test_copy_source_dict_with_accesspoint_arn(self):
        copy_source = {
            'Bucket':
                'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint',
            'Key': 'myprefix/myobject',
        }
        self.client, self.http_stubber = self.create_stubbed_s3_client()
        self.add_copy_object_response(self.http_stubber)
        self.client.copy_object(
            Bucket='mybucket', Key='mykey', CopySource=copy_source
        )
        self.assert_expected_copy_source_header(
            self.http_stubber,
            expected_copy_source=(
                b'arn%3Aaws%3As3%3Aus-west-2%3A123456789012%3Aaccesspoint%3A'
                b'myendpoint/object/myprefix/myobject'
            )
        )

    def test_copy_source_dict_with_accesspoint_arn_and_version_id(self):
        copy_source = {
            'Bucket':
                'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint',
            'Key': 'myprefix/myobject',
            'VersionId': 'myversionid'
        }
        self.client, self.http_stubber = self.create_stubbed_s3_client()
        self.add_copy_object_response(self.http_stubber)
        self.client.copy_object(
            Bucket='mybucket', Key='mykey', CopySource=copy_source
        )
        self.assert_expected_copy_source_header(
            self.http_stubber,
            expected_copy_source=(
                b'arn%3Aaws%3As3%3Aus-west-2%3A123456789012%3Aaccesspoint%3A'
                b'myendpoint/object/myprefix/myobject?versionId=myversionid'
            )
        )

    def test_basic_outpost_arn(self):
        outpost_arn = (
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost:'
            'op-01234567890123456:accesspoint:myaccesspoint'
        )
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            region_name='us-east-1')
        self.http_stubber.add_response()
        self.client.list_objects(Bucket=outpost_arn)
        request = self.http_stubber.requests[0]
        self.assert_signing_name(request, 's3-outposts')
        self.assert_signing_region(request, 'us-west-2')
        expected_endpoint = (
            'myaccesspoint-123456789012.op-01234567890123456.'
            's3-outposts.us-west-2.amazonaws.com'
        )
        self.assert_endpoint(request, expected_endpoint)

    def test_basic_outpost_arn(self):
        outpost_arn = (
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost:'
            'op-01234567890123456:accesspoint:myaccesspoint'
        )
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            endpoint_url='https://custom.com',
            region_name='us-east-1')
        self.http_stubber.add_response()
        self.client.list_objects(Bucket=outpost_arn)
        request = self.http_stubber.requests[0]
        self.assert_signing_name(request, 's3-outposts')
        self.assert_signing_region(request, 'us-west-2')
        expected_endpoint = (
            'myaccesspoint-123456789012.op-01234567890123456.custom.com'
        )
        self.assert_endpoint(request, expected_endpoint)

    def test_outpost_arn_presigned_url(self):
        outpost_arn = (
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost/'
            'op-01234567890123456/accesspoint/myaccesspoint'
        )
        expected_url = (
            'myaccesspoint-123456789012.op-01234567890123456.'
            's3-outposts.us-west-2.amazonaws.com'
        )
        expected_credentials = '20210827%2Fus-west-2%2Fs3-outposts%2Faws4_request'
        expected_signature = (
            'a944fbe2bfbae429f922746546d1c6f890649c88ba7826bd1d258ac13f327e09'
        )
        config = Config(signature_version='s3v4')
        presigned_url = self._get_presigned_url(
            outpost_arn, 'us-west-2', config=config
        )
        self._assert_presigned_url(
            presigned_url, expected_url,
            expected_signature, expected_credentials
        )

    def test_outpost_arn_presigned_url_with_use_arn_region(self):
        outpost_arn = (
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost/'
            'op-01234567890123456/accesspoint/myaccesspoint'
        )
        expected_url = (
            'myaccesspoint-123456789012.op-01234567890123456.'
            's3-outposts.us-west-2.amazonaws.com'
        )
        expected_credentials = '20210827%2Fus-west-2%2Fs3-outposts%2Faws4_request'
        expected_signature = (
            'a944fbe2bfbae429f922746546d1c6f890649c88ba7826bd1d258ac13f327e09'
        )
        config = Config(
            signature_version='s3v4',
            s3={
                'use_arn_region': True,
            }
        )
        presigned_url = self._get_presigned_url(
            outpost_arn, 'us-west-2', config=config
        )
        self._assert_presigned_url(
            presigned_url, expected_url,
            expected_signature, expected_credentials
        )

    def test_outpost_arn_presigned_url_cross_region_arn(self):
        outpost_arn = (
            'arn:aws:s3-outposts:us-east-1:123456789012:outpost/'
            'op-01234567890123456/accesspoint/myaccesspoint'
        )
        expected_url = (
            'myaccesspoint-123456789012.op-01234567890123456.'
            's3-outposts.us-east-1.amazonaws.com'
        )
        expected_credentials = '20210827%2Fus-east-1%2Fs3-outposts%2Faws4_request'
        expected_signature = (
            '7f93df0b81f80e590d95442d579bd6cf749a35ff4bbdc6373fa669b89c7fce4e'
        )
        config = Config(
            signature_version='s3v4',
            s3={
                'use_arn_region': True,
            }
        )
        presigned_url = self._get_presigned_url(
            outpost_arn, 'us-west-2', config=config
        )
        self._assert_presigned_url(
            presigned_url, expected_url,
            expected_signature, expected_credentials
        )

    def test_outpost_arn_with_s3_accelerate(self):
        outpost_arn = (
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost:'
            'op-01234567890123456:accesspoint:myaccesspoint'
        )
        self.client, _ = self.create_stubbed_s3_client(
            config=Config(s3={'use_accelerate_endpoint': True}))
        with self.assertRaises(UnsupportedS3AccesspointConfigurationError):
            self.client.list_objects(Bucket=outpost_arn)

    def test_outpost_arn_with_s3_dualstack(self):
        outpost_arn = (
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost:'
            'op-01234567890123456:accesspoint:myaccesspoint'
        )
        self.client, _ = self.create_stubbed_s3_client(
            config=Config(s3={'use_dualstack_endpoint': True}))
        with self.assertRaises(UnsupportedS3AccesspointConfigurationError):
            self.client.list_objects(Bucket=outpost_arn)

    def test_incorrect_outpost_format(self):
        outpost_arn = (
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost'
        )
        with self.assertRaises(botocore.exceptions.ParamValidationError):
            self.client.list_objects(Bucket=outpost_arn)

    def test_incorrect_outpost_no_accesspoint(self):
        outpost_arn = (
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost:'
            'op-01234567890123456'
        )
        with self.assertRaises(botocore.exceptions.ParamValidationError):
            self.client.list_objects(Bucket=outpost_arn)

    def test_incorrect_outpost_resource_format(self):
        outpost_arn = (
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost:myaccesspoint'
        )
        with self.assertRaises(botocore.exceptions.ParamValidationError):
            self.client.list_objects(Bucket=outpost_arn)

    def test_incorrect_outpost_sub_resources(self):
        outpost_arn = (
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost:'
            'op-01234567890123456:accesspoint:mybucket:object:foo'
        )
        with self.assertRaises(botocore.exceptions.ParamValidationError):
            self.client.list_objects(Bucket=outpost_arn)

    def test_incorrect_outpost_invalid_character(self):
        outpost_arn = (
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost:'
            'op-0123456.890123456:accesspoint:myaccesspoint'
        )
        with self.assertRaises(botocore.exceptions.ParamValidationError):
            self.client.list_objects(Bucket=outpost_arn)

    def test_s3_object_lambda_arn_with_s3_dualstack(self):
        s3_object_lambda_arn = (
            'arn:aws:s3-object-lambda:us-west-2:123456789012:'
            'accesspoint/myBanner'
        )
        self.client, _ = self.create_stubbed_s3_client(
            config=Config(s3={'use_dualstack_endpoint': True}))
        with self.assertRaises(UnsupportedS3AccesspointConfigurationError):
            self.client.list_objects(Bucket=s3_object_lambda_arn)

    def test_s3_object_lambda_fips_raise_for_cross_region(self):
        s3_object_lambda_arn = (
            'arn:aws-us-gov:s3-object-lambda:us-gov-east-1:123456789012:'
            'accesspoint/mybanner'
        )
        self.client, _ = self.create_stubbed_s3_client(
            region_name='fips-us-gov-west-1',
            config=Config(s3={'use_arn_region': False})
        )
        expected_exception = UnsupportedS3AccesspointConfigurationError
        with self.assertRaisesRegex(expected_exception,
                                     'ARNs in another region are not allowed'):
            self.client.list_objects(Bucket=s3_object_lambda_arn)

    def test_s3_object_lambda_with_global_regions(self):
        s3_object_lambda_arn = (
            'arn:aws:s3-object-lambda:us-east-1:123456789012:'
            'accesspoint/mybanner'
        )
        expected_exception = UnsupportedS3AccesspointConfigurationError
        expected_msg = 'a regional endpoint must be specified'
        for region in ('aws-global', 's3-external-1'):
            self.client, _ = self.create_stubbed_s3_client(
                region_name=region, config=Config(s3={'use_arn_region': False})
            )
            with self.assertRaisesRegex(expected_exception, expected_msg):
                self.client.list_objects(Bucket=s3_object_lambda_arn)

    def test_s3_object_lambda_arn_with_us_east_1(self):
        # test that us-east-1 region is not resolved
        # into s3 global endpoint
        s3_object_lambda_arn = (
            'arn:aws:s3-object-lambda:us-east-1:123456789012:'
            'accesspoint/myBanner'
        )
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            region_name='us-east-1',
            config=Config(s3={'use_arn_region': False})
        )
        self.http_stubber.add_response()
        self.client.list_objects(Bucket=s3_object_lambda_arn)
        request = self.http_stubber.requests[0]
        self.assert_signing_name(request, 's3-object-lambda')
        self.assert_signing_region(request, 'us-east-1')
        expected_endpoint = (
            'myBanner-123456789012.s3-object-lambda.us-east-1.amazonaws.com'
        )
        self.assert_endpoint(request, expected_endpoint)

    def test_basic_s3_object_lambda_arn(self):
        s3_object_lambda_arn = (
            'arn:aws:s3-object-lambda:us-west-2:123456789012:'
            'accesspoint/myBanner'
        )
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            region_name='us-east-1')
        self.http_stubber.add_response()
        self.client.list_objects(Bucket=s3_object_lambda_arn)
        request = self.http_stubber.requests[0]
        self.assert_signing_name(request, 's3-object-lambda')
        self.assert_signing_region(request, 'us-west-2')
        expected_endpoint = (
            'myBanner-123456789012.s3-object-lambda.us-west-2.amazonaws.com'
        )
        self.assert_endpoint(request, expected_endpoint)

    def test_outposts_raise_exception_if_fips_region(self):
        outpost_arn = (
            'arn:aws:s3-outposts:us-gov-east-1:123456789012:outpost:'
            'op-01234567890123456:accesspoint:myaccesspoint'
        )
        self.client, _ = self.create_stubbed_s3_client(region_name="fips-east-1")
        expected_exception = UnsupportedS3AccesspointConfigurationError
        with self.assertRaisesRegex(expected_exception,
                                    'outpost ARNs do not support FIPS'):
            self.client.list_objects(Bucket=outpost_arn)

    def test_accesspoint_fips_raise_for_cross_region(self):
        s3_accesspoint_arn = (
            'arn:aws-us-gov:s3:us-gov-east-1:123456789012:'
            'accesspoint:myendpoint'
        )
        self.client, _ = self.create_stubbed_s3_client(
            region_name='fips-us-gov-west-1',
            config=Config(s3={'use_arn_region': False})
        )
        expected_exception = UnsupportedS3AccesspointConfigurationError
        with self.assertRaisesRegex(expected_exception,
                                    'ARNs in another region are not allowed'):
            self.client.list_objects(Bucket=s3_accesspoint_arn)

    def test_accesspoint_fips_raise_if_fips_in_arn(self):
        s3_accesspoint_arn = (
            "arn:aws-us-gov:s3:fips-us-gov-west-1:123456789012:" "accesspoint:myendpoint"
        )
        self.client, _ = self.create_stubbed_s3_client(
            region_name="fips-us-gov-west-1",
        )
        expected_exception = UnsupportedS3AccesspointConfigurationError
        with self.assertRaisesRegex(
            expected_exception, "Invalid ARN, FIPS region not allowed in ARN."
        ):
            self.client.list_objects(Bucket=s3_accesspoint_arn)

    def test_accesspoint_with_global_regions(self):
        s3_accesspoint_arn = (
            'arn:aws:s3:us-east-1:123456789012:accesspoint:myendpoint'
        )
        self.client, _ = self.create_stubbed_s3_client(
            region_name='aws-global',
            config=Config(s3={'use_arn_region': False})
        )
        expected_exception = UnsupportedS3AccesspointConfigurationError
        with self.assertRaisesRegex(expected_exception,
                                    'regional endpoint must be specified'):
            self.client.list_objects(Bucket=s3_accesspoint_arn)

        # It shouldn't raise if use_arn_region is True
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            region_name='s3-external-1',
            config=Config(s3={'use_arn_region': True})
        )

        self.http_stubber.add_response()
        self.client.list_objects(Bucket=s3_accesspoint_arn)
        request = self.http_stubber.requests[0]
        expected_endpoint = (
            'myendpoint-123456789012.s3-accesspoint.'
            'us-east-1.amazonaws.com'
        )
        self.assert_endpoint(request, expected_endpoint)

        # It shouldn't raise if no use_arn_region is specified since
        # use_arn_region defaults to True
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            region_name='s3-external-1',
        )

        self.http_stubber.add_response()
        self.client.list_objects(Bucket=s3_accesspoint_arn)
        request = self.http_stubber.requests[0]
        expected_endpoint = (
            'myendpoint-123456789012.s3-accesspoint.'
            'us-east-1.amazonaws.com'
        )
        self.assert_endpoint(request, expected_endpoint)

    def test_mrap_arn_with_client_regions(self):
        mrap_arn = 'arn:aws:s3::123456789012:accesspoint:mfzwi23gnjvgw.mrap'
        region_tests = [
            ('us-east-1', 'mfzwi23gnjvgw.mrap.accesspoint.s3-global.amazonaws.com'),
            ('us-west-2', 'mfzwi23gnjvgw.mrap.accesspoint.s3-global.amazonaws.com'),
            ('aws-global', 'mfzwi23gnjvgw.mrap.accesspoint.s3-global.amazonaws.com'),
        ]
        for region, expected in region_tests:
            self._assert_mrap_endpoint(mrap_arn, region, expected)

    def test_mrap_arn_with_other_partition(self):
        mrap_arn = 'arn:aws-cn:s3::123456789012:accesspoint:mfzwi23gnjvgw.mrap'
        expected = 'mfzwi23gnjvgw.mrap.accesspoint.s3-global.amazonaws.com.cn'
        self._assert_mrap_endpoint(mrap_arn, 'cn-north-1', expected)

    def test_mrap_arn_with_invalid_s3_configs(self):
        mrap_arn = 'arn:aws:s3::123456789012:accesspoint:mfzwi23gnjvgw.mrap'
        config_tests = [
            (
              'us-west-2',
              Config(s3={'use_dualstack_endpoint': True})
            ),
            (
              'us-west-2',
              Config(s3={'use_accelerate_endpoint': True})
            )
        ]
        for region, config in config_tests:
            self._assert_mrap_config_failure(mrap_arn, region, config=config)

    def test_mrap_arn_with_custom_endpoint(self):
        mrap_arn = 'arn:aws:s3::123456789012:accesspoint:mfzwi23gnjvgw.mrap'
        endpoint_url = 'https://test.endpoint.amazonaws.com'
        expected = 'mfzwi23gnjvgw.mrap.test.endpoint.amazonaws.com'
        self._assert_mrap_endpoint(
            mrap_arn, 'us-east-1', expected, endpoint_url=endpoint_url
        )

    def test_mrap_arn_with_vpc_endpoint(self):
        mrap_arn = 'arn:aws:s3::123456789012:accesspoint:mfzwi23gnjvgw.mrap'
        endpoint_url = 'https://vpce-123-abc.vpce.s3-global.amazonaws.com'
        expected = 'mfzwi23gnjvgw.mrap.vpce-123-abc.vpce.s3-global.amazonaws.com'
        self._assert_mrap_endpoint(
            mrap_arn, 'us-west-2', expected, endpoint_url=endpoint_url
        )

    def test_mrap_arn_with_disable_config_enabled(self):
        mrap_arn = 'arn:aws:s3::123456789012:accesspoint:mfzwi23gnjvgw.mrap'
        config = Config(s3={'s3_disable_multiregion_access_points': True})
        for region in ('us-west-2', 'aws-global'):
            self._assert_mrap_config_failure(mrap_arn, region, config)

    def test_mrap_arn_with_disable_config_enabled_custom_endpoint(self):
        mrap_arn = 'arn:aws:s3::123456789012:accesspoint:myendpoint'
        config = Config(s3={'s3_disable_multiregion_access_points': True})
        self._assert_mrap_config_failure(mrap_arn, 'us-west-2', config)

    def test_mrap_arn_with_disable_config_disabled(self):
        mrap_arn = 'arn:aws:s3::123456789012:accesspoint:mfzwi23gnjvgw.mrap'
        config = Config(s3={'s3_disable_multiregion_access_points': False})
        expected = 'mfzwi23gnjvgw.mrap.accesspoint.s3-global.amazonaws.com'
        self._assert_mrap_endpoint(mrap_arn, 'us-west-2', expected, config=config)

    def test_global_arn_without_mrap_suffix(self):
        global_arn_tests = [
            (
                'arn:aws:s3::123456789012:accesspoint:myendpoint',
                'myendpoint.accesspoint.s3-global.amazonaws.com',
            ),
            (
                'arn:aws:s3::123456789012:accesspoint:my.bucket',
                'my.bucket.accesspoint.s3-global.amazonaws.com',
            ),
        ]
        for arn, expected in global_arn_tests:
            self._assert_mrap_endpoint(arn, 'us-west-2', expected)

    def test_mrap_signing_algorithm_is_sigv4a(self):
        s3_accesspoint_arn = (
            'arn:aws:s3::123456789012:accesspoint:mfzwi23gnjvgw.mrap'
        )
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            region_name='us-west-2'
        )
        self.http_stubber.add_response()
        self.client.list_objects(Bucket=s3_accesspoint_arn)
        request = self.http_stubber.requests[0]
        self._assert_sigv4a_used(request.headers)

    def test_mrap_presigned_url(self):
        mrap_arn = 'arn:aws:s3::123456789012:accesspoint:mfzwi23gnjvgw.mrap'
        config = Config(s3={'s3_disable_multiregion_access_points': False})
        expected_url = 'mfzwi23gnjvgw.mrap.accesspoint.s3-global.amazonaws.com'
        self._assert_mrap_presigned_url(mrap_arn, 'us-west-2', expected_url, config=config)

    def test_mrap_presigned_url_disabled(self):
        mrap_arn = 'arn:aws:s3::123456789012:accesspoint:mfzwi23gnjvgw.mrap'
        config = Config(s3={'s3_disable_multiregion_access_points': True})
        self._assert_mrap_config_presigned_failure(mrap_arn, 'us-west-2', config)

    def _assert_mrap_config_failure(self, arn, region, config):
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            region_name=region, config=config)
        with self.assertRaises(botocore.exceptions.
                UnsupportedS3AccesspointConfigurationError):
            self.client.list_objects(Bucket=arn)

    @FreezeTime(botocore.auth.datetime, date=DATE)
    def _get_presigned_url(self, arn, region, config=None, endpoint_url=None):
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            region_name=region,
            endpoint_url=endpoint_url,
            config=config,
            aws_access_key_id='ACCESS_KEY_ID',
            aws_secret_access_key='SECRET_ACCESS_KEY'
        )
        presigned_url = self.client.generate_presigned_url(
            'get_object',
            Params={'Bucket': arn, 'Key': 'obj'},
            ExpiresIn=900
        )
        return presigned_url

    def _assert_presigned_url(
        self,
        presigned_url,
        expected_url,
        expected_signature,
        expected_credentials
    ):
        url_parts = urlsplit(presigned_url)
        assert url_parts.netloc == expected_url
        query_strs = url_parts.query.split('&')
        query_parts = dict(part.split('=') for part in query_strs)
        assert expected_signature == query_parts['X-Amz-Signature']
        assert expected_credentials in query_parts['X-Amz-Credential']


    def _assert_mrap_presigned_url(
        self, arn, region, expected, endpoint_url=None, config=None
    ):
        presigned_url = self._get_presigned_url(
            arn, region, endpoint_url=None, config=None
        )
        url_parts = urlsplit(presigned_url)
        self.assertEqual(expected, url_parts.hostname)
        # X-Amz-Region-Set header MUST be * (percent-encoded as %2A) for MRAPs
        self.assertIn('X-Amz-Region-Set=%2A', url_parts.query)

    def _assert_mrap_config_presigned_failure(self, arn, region, config):
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            region_name=region, config=config)
        with self.assertRaises(botocore.exceptions.
                UnsupportedS3AccesspointConfigurationError):
            self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': arn, 'Key': 'test_object'}
            )

    def _assert_mrap_endpoint(
        self, arn, region, expected, endpoint_url=None, config=None
    ):
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            region_name=region, endpoint_url=endpoint_url, config=config)
        self.http_stubber.add_response()
        self.client.list_objects(Bucket=arn)
        request = self.http_stubber.requests[0]
        self.assert_endpoint(request, expected)
        # MRAP requests MUST include a global signing region stored in the
        # X-Amz-Region-Set header as *.
        self.assert_header_matches(request, 'X-Amz-Region-Set', b'*')

    def _assert_sigv4a_used(self, headers):
        self.assertIn(
            b'AWS4-ECDSA-P256-SHA256', headers.get('Authorization', '')
        )



class TestOnlyAsciiCharsAllowed(BaseS3OperationTest):
    def test_validates_non_ascii_chars_trigger_validation_error(self):
        self.http_stubber.add_response()
        with self.http_stubber:
            with self.assertRaises(ParamValidationError):
                self.client.put_object(
                    Bucket='foo', Key='bar', Metadata={
                        'goodkey': 'good', 'non-ascii': u'\u2713'})


class TestS3GetBucketLifecycle(BaseS3OperationTest):
    def test_multiple_transitions_returns_one(self):
        response_body = (
            '<?xml version="1.0" ?>'
            '<LifecycleConfiguration xmlns="http://s3.amazonaws.'
            'com/doc/2006-03-01/">'
            '	<Rule>'
            '		<ID>transitionRule</ID>'
            '		<Prefix>foo</Prefix>'
            '		<Status>Enabled</Status>'
            '		<Transition>'
            '			<Days>40</Days>'
            '			<StorageClass>STANDARD_IA</StorageClass>'
            '		</Transition>'
            '		<Transition>'
            '			<Days>70</Days>'
            '			<StorageClass>GLACIER</StorageClass>'
            '		</Transition>'
            '	</Rule>'
            '	<Rule>'
            '		<ID>noncurrentVersionRule</ID>'
            '		<Prefix>bar</Prefix>'
            '		<Status>Enabled</Status>'
            '		<NoncurrentVersionTransition>'
            '			<NoncurrentDays>40</NoncurrentDays>'
            '			<StorageClass>STANDARD_IA</StorageClass>'
            '		</NoncurrentVersionTransition>'
            '		<NoncurrentVersionTransition>'
            '			<NoncurrentDays>70</NoncurrentDays>'
            '			<StorageClass>GLACIER</StorageClass>'
            '		</NoncurrentVersionTransition>'
            '	</Rule>'
            '</LifecycleConfiguration>'
        ).encode('utf-8')
        s3 = self.session.create_client('s3')
        with ClientHTTPStubber(s3) as http_stubber:
            http_stubber.add_response(body=response_body)
            response = s3.get_bucket_lifecycle(Bucket='mybucket')
        # Each Transition member should have at least one of the
        # transitions provided.
        self.assertEqual(
            response['Rules'][0]['Transition'],
            {'Days': 40, 'StorageClass': 'STANDARD_IA'}
        )
        self.assertEqual(
            response['Rules'][1]['NoncurrentVersionTransition'],
            {'NoncurrentDays': 40, 'StorageClass': 'STANDARD_IA'}
        )


class TestS3PutObject(BaseS3OperationTest):
    def test_500_error_with_non_xml_body(self):
        # Note: This exact tesdict may not be applicable from
        # an integration standpoint if the issue is fixed in the future.
        #
        # The issue is that:
        # S3 returns a 200 response but the received response from urllib3 has
        # a 500 status code and the headers are in the body of the
        # the response. Botocore will try to parse out the error body as xml,
        # but the body is invalid xml because it is full of headers.
        # So instead of blowing up on an XML parsing error, we
        # should at least use the 500 status code because that can be
        # retried.
        #
        # We are unsure of what exactly causes the response to be mangled
        # but we expect it to be how 100 continues are handled.
        non_xml_content = (
            'x-amz-id-2: foo\r\n'
            'x-amz-request-id: bar\n'
            'Date: Tue, 06 Oct 2015 03:20:38 GMT\r\n'
            'ETag: "a6d856bc171fc6aa1b236680856094e2"\r\n'
            'Content-Length: 0\r\n'
            'Server: AmazonS3\r\n'
        ).encode('utf-8')
        s3 = self.session.create_client('s3')
        with ClientHTTPStubber(s3) as http_stubber:
            http_stubber.add_response(status=500, body=non_xml_content)
            http_stubber.add_response()
            response = s3.put_object(Bucket='mybucket', Key='mykey', Body=b'foo')
            # The first response should have been retried even though the xml is
            # invalid and eventually return the 200 response.
            self.assertEqual(response['ResponseMetadata']['HTTPStatusCode'], 200)
            self.assertEqual(len(http_stubber.requests), 2)


class TestWriteGetObjectResponse(BaseS3ClientConfigurationTest):
    def create_stubbed_s3_client(self, **kwargs):
        client = self.create_s3_client(**kwargs)
        http_stubber = ClientHTTPStubber(client)
        http_stubber.start()
        return client, http_stubber

    def test_endpoint_redirection(self):
        regions = ['us-west-2', 'us-east-1']
        for region in regions:
            self.client, self.http_stubber = self.create_stubbed_s3_client(
                region_name=region)
            self.http_stubber.add_response()
            self.client.write_get_object_response(
                RequestRoute='endpoint-io.a1c1d5c7',
                RequestToken='SecretToken',
            )
            request = self.http_stubber.requests[0]
            self.assert_signing_name(request, 's3-object-lambda')
            self.assert_signing_region(request, region)
            expected_endpoint = (
                'endpoint-io.a1c1d5c7.s3-object-lambda.'
                '%s.amazonaws.com' % region
            )
            self.assert_endpoint(request, expected_endpoint)

    def test_endpoint_redirection_fails_with_custom_endpoint(self):
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            region_name='us-west-2', endpoint_url="https://example.com")
        self.http_stubber.add_response()
        self.client.write_get_object_response(
            RequestRoute='endpoint-io.a1c1d5c7',
            RequestToken='SecretToken',
        )
        request = self.http_stubber.requests[0]
        self.assert_signing_name(request, 's3-object-lambda')
        self.assert_signing_region(request, 'us-west-2')
        self.assert_endpoint(request, 'endpoint-io.a1c1d5c7.example.com')

    def test_endpoint_redirection_fails_with_accelerate_endpoint(self):
        config = Config(s3={'use_accelerate_endpoint': True})
        self.client, self.http_stubber = self.create_stubbed_s3_client(
            region_name='us-west-2',
            config=config,
        )
        self.http_stubber.add_response()
        with self.assertRaises(UnsupportedS3ConfigurationError):
            self.client.write_get_object_response(
                RequestRoute='endpoint-io.a1c1d5c7',
                RequestToken='SecretToken',
            )


class TestS3SigV4(BaseS3OperationTest):
    def setUp(self):
        super(TestS3SigV4, self).setUp()
        self.client = self.session.create_client(
            's3', self.region, config=Config(signature_version='s3v4'))
        self.http_stubber = ClientHTTPStubber(self.client)
        self.http_stubber.add_response()

    def get_sent_headers(self):
        return self.http_stubber.requests[0].headers

    def test_content_md5_set(self):
        with self.http_stubber:
            self.client.put_object(Bucket='foo', Key='bar', Body='baz')
        self.assertIn('content-md5', self.get_sent_headers())

    def test_content_md5_set_empty_body(self):
        with self.http_stubber:
            self.client.put_object(Bucket='foo', Key='bar', Body='')
        self.assertIn('content-md5', self.get_sent_headers())

    def test_content_md5_set_empty_file(self):
        with self.http_stubber:
            with temporary_file('rb') as f:
                assert f.read() == b''
                self.client.put_object(Bucket='foo', Key='bar', Body=f)
        self.assertIn('content-md5', self.get_sent_headers())

    def test_content_sha256_set_if_config_value_is_true(self):
        config = Config(signature_version='s3v4', s3={
            'payload_signing_enabled': True
        })
        self.client = self.session.create_client(
            's3', self.region, config=config)
        self.http_stubber = ClientHTTPStubber(self.client)
        self.http_stubber.add_response()
        with self.http_stubber:
            self.client.put_object(Bucket='foo', Key='bar', Body='baz')
        sent_headers = self.get_sent_headers()
        sha_header = sent_headers.get('x-amz-content-sha256')
        self.assertNotEqual(sha_header, b'UNSIGNED-PAYLOAD')

    def test_content_sha256_not_set_if_config_value_is_false(self):
        config = Config(signature_version='s3v4', s3={
            'payload_signing_enabled': False
        })
        self.client = self.session.create_client(
            's3', self.region, config=config)
        self.http_stubber = ClientHTTPStubber(self.client)
        self.http_stubber.add_response()
        with self.http_stubber:
            self.client.put_object(Bucket='foo', Key='bar', Body='baz')
        sent_headers = self.get_sent_headers()
        sha_header = sent_headers.get('x-amz-content-sha256')
        self.assertEqual(sha_header, b'UNSIGNED-PAYLOAD')

    def test_content_sha256_set_if_md5_is_unavailable(self):
        with mock.patch('botocore.auth.MD5_AVAILABLE', False):
            with mock.patch('botocore.utils.MD5_AVAILABLE', False):
                with self.http_stubber:
                    self.client.put_object(Bucket='foo', Key='bar', Body='baz')
        sent_headers = self.get_sent_headers()
        unsigned = 'UNSIGNED-PAYLOAD'
        self.assertNotEqual(sent_headers['x-amz-content-sha256'], unsigned)
        self.assertNotIn('content-md5', sent_headers)


class TestCanSendIntegerHeaders(BaseSessionTest):

    def test_int_values_with_sigv4(self):
        s3 = self.session.create_client(
            's3', config=Config(signature_version='s3v4'))
        with ClientHTTPStubber(s3) as http_stubber:
            http_stubber.add_response()
            s3.upload_part(Bucket='foo', Key='bar', Body=b'foo',
                           UploadId='bar', PartNumber=1, ContentLength=3)
            headers = http_stubber.requests[0].headers
            # Verify that the request integer value of 3 has been converted to
            # string '3'.  This also means we've made it pass the signer which
            # expects string values in order to sign properly.
            self.assertEqual(headers['Content-Length'], b'3')


class TestRegionRedirect(BaseS3OperationTest):
    def setUp(self):
        super(TestRegionRedirect, self).setUp()
        self.client = self.session.create_client(
            's3', 'us-west-2', config=Config(
                signature_version='s3v4',
                s3={'addressing_style': 'path'},
            ))
        self.http_stubber = ClientHTTPStubber(self.client)

        self.redirect_response = {
            'status': 301,
            'headers': {'x-amz-bucket-region': 'eu-central-1'},
            'body': (
                b'<?xml version="1.0" encoding="UTF-8"?>\n'
                b'<Error>'
                b'    <Code>PermanentRedirect</Code>'
                b'    <Message>The bucket you are attempting to access must be'
                b'        addressed using the specified endpoint. Please send '
                b'        all future requests to this endpoint.'
                b'    </Message>'
                b'    <Bucket>foo</Bucket>'
                b'    <Endpoint>foo.s3.eu-central-1.amazonaws.com</Endpoint>'
                b'</Error>'
            )
        }
        self.bad_signing_region_response = {
            'status': 400,
            'headers': {'x-amz-bucket-region': 'eu-central-1'},
            'body': (
                b'<?xml version="1.0" encoding="UTF-8"?>'
                b'<Error>'
                b'  <Code>AuthorizationHeaderMalformed</Code>'
                b'  <Message>the region us-west-2 is wrong; '
                b'expecting eu-central-1</Message>'
                b'  <Region>eu-central-1</Region>'
                b'  <RequestId>BD9AA1730D454E39</RequestId>'
                b'  <HostId></HostId>'
                b'</Error>'
            )
        }
        self.success_response = {
            'status': 200,
            'headers': {},
            'body': (
                b'<?xml version="1.0" encoding="UTF-8"?>\n'
                b'<ListBucketResult>'
                b'    <Name>foo</Name>'
                b'    <Prefix></Prefix>'
                b'    <Marker></Marker>'
                b'    <MaxKeys>1000</MaxKeys>'
                b'    <EncodingType>url</EncodingType>'
                b'    <IsTruncated>false</IsTruncated>'
                b'</ListBucketResult>'
            )
        }

    def test_region_redirect(self):
        self.http_stubber.add_response(**self.redirect_response)
        self.http_stubber.add_response(**self.success_response)
        with self.http_stubber:
            response = self.client.list_objects(Bucket='foo')
        self.assertEqual(response['ResponseMetadata']['HTTPStatusCode'], 200)
        self.assertEqual(len(self.http_stubber.requests), 2)

        initial_url = ('https://s3.us-west-2.amazonaws.com/foo'
                       '?encoding-type=url')
        self.assertEqual(self.http_stubber.requests[0].url, initial_url)

        fixed_url = ('https://s3.eu-central-1.amazonaws.com/foo'
                     '?encoding-type=url')
        self.assertEqual(self.http_stubber.requests[1].url, fixed_url)

    def test_region_redirect_cache(self):
        self.http_stubber.add_response(**self.redirect_response)
        self.http_stubber.add_response(**self.success_response)
        self.http_stubber.add_response(**self.success_response)

        with self.http_stubber:
            first_response = self.client.list_objects(Bucket='foo')
            second_response = self.client.list_objects(Bucket='foo')

        self.assertEqual(
            first_response['ResponseMetadata']['HTTPStatusCode'], 200)
        self.assertEqual(
            second_response['ResponseMetadata']['HTTPStatusCode'], 200)

        self.assertEqual(len(self.http_stubber.requests), 3)
        initial_url = ('https://s3.us-west-2.amazonaws.com/foo'
                       '?encoding-type=url')
        self.assertEqual(self.http_stubber.requests[0].url, initial_url)

        fixed_url = ('https://s3.eu-central-1.amazonaws.com/foo'
                     '?encoding-type=url')
        self.assertEqual(self.http_stubber.requests[1].url, fixed_url)
        self.assertEqual(self.http_stubber.requests[2].url, fixed_url)

    def test_resign_request_with_region_when_needed(self):

        # Create a client with no explicit configuration so we can
        # verify the default behavior.
        client = self.session.create_client('s3', 'us-west-2')
        with ClientHTTPStubber(client) as http_stubber:
            http_stubber.add_response(**self.bad_signing_region_response)
            http_stubber.add_response(**self.success_response)
            first_response = client.list_objects(Bucket='foo')
            self.assertEqual(
                first_response['ResponseMetadata']['HTTPStatusCode'], 200)

            self.assertEqual(len(http_stubber.requests), 2)
            initial_url = ('https://foo.s3.us-west-2.amazonaws.com/'
                           '?encoding-type=url')
            self.assertEqual(http_stubber.requests[0].url, initial_url)

            fixed_url = ('https://foo.s3.eu-central-1.amazonaws.com/'
                         '?encoding-type=url')
            self.assertEqual(http_stubber.requests[1].url, fixed_url)

    def test_resign_request_in_us_east_1(self):
        region_headers = {'x-amz-bucket-region': 'eu-central-1'}

        # Verify that the default behavior in us-east-1 will redirect
        client = self.session.create_client('s3', 'us-east-1')
        with ClientHTTPStubber(client) as http_stubber:
            http_stubber.add_response(status=400)
            http_stubber.add_response(status=400, headers=region_headers)
            http_stubber.add_response(headers=region_headers)
            http_stubber.add_response()
            response = client.head_object(Bucket='foo', Key='bar')
            self.assertEqual(response['ResponseMetadata']['HTTPStatusCode'], 200)

            self.assertEqual(len(http_stubber.requests), 4)
            initial_url = ('https://foo.s3.us-east-1.amazonaws.com/bar')
            self.assertEqual(http_stubber.requests[0].url, initial_url)

            fixed_url = ('https://foo.s3.eu-central-1.amazonaws.com/bar')
            self.assertEqual(http_stubber.requests[-1].url, fixed_url)

    def test_resign_request_in_us_east_1_fails(self):
        region_headers = {'x-amz-bucket-region': 'eu-central-1'}

        # Verify that the final 400 response is propagated
        # back to the user.
        client = self.session.create_client('s3', 'us-east-1')
        with ClientHTTPStubber(client) as http_stubber:
            http_stubber.add_response(status=400)
            http_stubber.add_response(status=400, headers=region_headers)
            http_stubber.add_response(headers=region_headers)
            # The final request still fails with a 400.
            http_stubber.add_response(status=400)
            with self.assertRaises(ClientError) as e:
                client.head_object(Bucket='foo', Key='bar')
            self.assertEqual(len(http_stubber.requests), 4)

    def test_no_region_redirect_for_accesspoint(self):
        self.http_stubber.add_response(**self.redirect_response)
        accesspoint_arn = (
            'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint'
        )
        with self.http_stubber:
            try:
                self.client.list_objects(Bucket=accesspoint_arn)
            except self.client.exceptions.ClientError as e:
                self.assertEqual(
                    e.response['Error']['Code'], 'PermanentRedirect')
            else:
                self.fail('PermanentRedirect error should have been raised')


class TestFipsRegionRedirect(BaseS3OperationTest):
    def setUp(self):
        super(TestFipsRegionRedirect, self).setUp()
        self.client = self.session.create_client(
            "s3",
            "fips-us-west-2",
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )
        self.http_stubber = ClientHTTPStubber(self.client)

        self.redirect_response = {
            "status": 301,
            "headers": {"x-amz-bucket-region": "us-west-1"},
            "body": (
                b'<?xml version="1.0" encoding="UTF-8"?>\n'
                b"<Error>"
                b"    <Code>PermanentRedirect</Code>"
                b"    <Message>The bucket you are attempting to access must be"
                b"        addressed using the specified endpoint. Please send "
                b"        all future requests to this endpoint."
                b"    </Message>"
                b"    <Bucket>foo</Bucket>"
                b"    <Endpoint>foo.s3-fips.us-west-1.amazonaws.com</Endpoint>"
                b"</Error>"
            ),
        }
        self.success_response = {
            "status": 200,
            "headers": {},
            "body": (
                b'<?xml version="1.0" encoding="UTF-8"?>\n'
                b"<ListBucketResult>"
                b"    <Name>foo</Name>"
                b"    <Prefix></Prefix>"
                b"    <Marker></Marker>"
                b"    <MaxKeys>1000</MaxKeys>"
                b"    <EncodingType>url</EncodingType>"
                b"    <IsTruncated>false</IsTruncated>"
                b"</ListBucketResult>"
            ),
        }
        self.bad_signing_region_response = {
            "status": 400,
            "headers": {"x-amz-bucket-region": "us-west-1"},
            "body": (
                b'<?xml version="1.0" encoding="UTF-8"?>'
                b"<Error>"
                b"  <Code>AuthorizationHeaderMalformed</Code>"
                b"  <Message>the region us-west-2 is wrong; "
                b"expecting us-west-1</Message>"
                b"  <Region>us-west-1</Region>"
                b"  <RequestId>BD9AA1730D454E39</RequestId>"
                b"  <HostId></HostId>"
                b"</Error>"
            ),
        }

    def test_fips_region_redirect(self):
        self.http_stubber.add_response(**self.redirect_response)
        self.http_stubber.add_response(**self.success_response)
        with self.http_stubber:
            response = self.client.list_objects(Bucket="foo")
        self.assertEqual(response["ResponseMetadata"]["HTTPStatusCode"], 200)
        self.assertEqual(len(self.http_stubber.requests), 2)

        initial_url = "https://s3-fips.us-west-2.amazonaws.com/foo" "?encoding-type=url"
        self.assertEqual(self.http_stubber.requests[0].url, initial_url)

        fixed_url = "https://s3-fips.us-west-1.amazonaws.com/foo" "?encoding-type=url"
        self.assertEqual(self.http_stubber.requests[1].url, fixed_url)

    def test_fips_region_redirect_cache(self):
        self.http_stubber.add_response(**self.redirect_response)
        self.http_stubber.add_response(**self.success_response)
        self.http_stubber.add_response(**self.success_response)

        with self.http_stubber:
            first_response = self.client.list_objects(Bucket="foo")
            second_response = self.client.list_objects(Bucket="foo")

        self.assertEqual(first_response["ResponseMetadata"]["HTTPStatusCode"], 200)
        self.assertEqual(second_response["ResponseMetadata"]["HTTPStatusCode"], 200)

        self.assertEqual(len(self.http_stubber.requests), 3)
        initial_url = "https://s3-fips.us-west-2.amazonaws.com/foo" "?encoding-type=url"
        self.assertEqual(self.http_stubber.requests[0].url, initial_url)

        fixed_url = "https://s3-fips.us-west-1.amazonaws.com/foo" "?encoding-type=url"
        self.assertEqual(self.http_stubber.requests[1].url, fixed_url)
        self.assertEqual(self.http_stubber.requests[2].url, fixed_url)

    def test_fips_resign_request_with_region_when_needed(self):

        # Create a client with no explicit configuration so we can
        # verify the default behavior.
        client = self.session.create_client("s3", "fips-us-west-2")
        with ClientHTTPStubber(client) as http_stubber:
            http_stubber.add_response(**self.bad_signing_region_response)
            http_stubber.add_response(**self.success_response)
            first_response = client.list_objects(Bucket="foo")
            self.assertEqual(first_response["ResponseMetadata"]["HTTPStatusCode"], 200)

            self.assertEqual(len(http_stubber.requests), 2)
            initial_url = "https://foo.s3-fips.us-west-2.amazonaws.com/" "?encoding-type=url"
            self.assertEqual(http_stubber.requests[0].url, initial_url)

            fixed_url = (
                "https://foo.s3-fips.us-west-1.amazonaws.com/" "?encoding-type=url"
            )
            self.assertEqual(http_stubber.requests[1].url, fixed_url)

    def test_fips_resign_request_in_us_east_1(self):
        region_headers = {"x-amz-bucket-region": "us-east-2"}

        # Verify that the default behavior in us-east-1 will redirect
        client = self.session.create_client("s3", "fips-us-east-1")
        with ClientHTTPStubber(client) as http_stubber:
            http_stubber.add_response(status=400)
            http_stubber.add_response(status=400, headers=region_headers)
            http_stubber.add_response(headers=region_headers)
            http_stubber.add_response()
            response = client.head_object(Bucket="foo", Key="bar")
            self.assertEqual(response["ResponseMetadata"]["HTTPStatusCode"], 200)

            self.assertEqual(len(http_stubber.requests), 4)
            initial_url = "https://foo.s3-fips.aws-global.amazonaws.com/bar"
            self.assertEqual(http_stubber.requests[0].url, initial_url)

            fixed_url = "https://foo.s3-fips.us-east-2.amazonaws.com/bar"
            self.assertEqual(http_stubber.requests[-1].url, fixed_url)

    def test_fips_resign_request_in_us_east_1_fails(self):
        region_headers = {"x-amz-bucket-region": "us-east-2"}

        # Verify that the final 400 response is propagated
        # back to the user.
        client = self.session.create_client("s3", "fips-us-east-1")
        with ClientHTTPStubber(client) as http_stubber:
            http_stubber.add_response(status=400)
            http_stubber.add_response(status=400, headers=region_headers)
            http_stubber.add_response(headers=region_headers)
            # The final request still fails with a 400.
            http_stubber.add_response(status=400)
            with self.assertRaises(ClientError):
                client.head_object(Bucket="foo", Key="bar")
            self.assertEqual(len(http_stubber.requests), 4)

    def test_fips_no_region_redirect_for_accesspoint(self):
        self.http_stubber.add_response(**self.redirect_response)
        accesspoint_arn = "arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint"
        with self.http_stubber:
            try:
                self.client.list_objects(Bucket=accesspoint_arn)
            except self.client.exceptions.ClientError as e:
                self.assertEqual(e.response["Error"]["Code"], "PermanentRedirect")
            else:
                self.fail("PermanentRedirect error should have been raised")


class TestGeneratePresigned(BaseS3OperationTest):
    def assert_is_v2_presigned_url(self, url):
        qs_components = parse_qs(urlsplit(url).query)
        # Assert that it looks like a v2 presigned url by asserting it does
        # not have a couple of the v4 qs components and assert that it has the
        # v2 Signature component.
        self.assertNotIn('X-Amz-Credential', qs_components)
        self.assertNotIn('X-Amz-Algorithm', qs_components)
        self.assertIn('Signature', qs_components)

    def test_generate_unauthed_url(self):
        config = Config(signature_version=botocore.UNSIGNED)
        client = self.session.create_client('s3', self.region, config=config)
        url = client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': 'foo',
                'Key': 'bar'
            })
        self.assertEqual(url, 'https://foo.s3.us-west-2.amazonaws.com/bar')

    def test_generate_unauthed_post(self):
        config = Config(signature_version=botocore.UNSIGNED)
        client = self.session.create_client('s3', self.region, config=config)
        parts = client.generate_presigned_post(Bucket='foo', Key='bar')
        expected = {
            'fields': {'key': 'bar'},
            'url': 'https://foo.s3.us-west-2.amazonaws.com/'
        }
        self.assertEqual(parts, expected)

    def test_default_presign_uses_sigv4(self):
        url = self.client.generate_presigned_url(ClientMethod='list_buckets')
        self.assertIn('Algorithm=AWS4-HMAC-SHA256', url)

    def test_sigv4_presign(self):
        config = Config(signature_version='s3v4')
        client = self.session.create_client('s3', self.region, config=config)
        url = client.generate_presigned_url(ClientMethod='list_buckets')
        self.assertIn('Algorithm=AWS4-HMAC-SHA256', url)

    def test_uses_sigv4_for_unknown_region(self):
        client = self.session.create_client('s3', 'us-west-88')
        url = client.generate_presigned_url(ClientMethod='list_buckets')
        self.assertIn('Algorithm=AWS4-HMAC-SHA256', url)

    def test_default_presign_sigv4_in_sigv4_only_region(self):
        client = self.session.create_client('s3', 'us-east-2')
        url = client.generate_presigned_url(ClientMethod='list_buckets')
        self.assertIn('Algorithm=AWS4-HMAC-SHA256', url)

    def test_presign_unsigned(self):
        config = Config(signature_version=botocore.UNSIGNED)
        client = self.session.create_client('s3', 'us-east-2', config=config)
        url = client.generate_presigned_url(ClientMethod='list_buckets')
        self.assertEqual(
            'https://s3.us-east-2.amazonaws.com/', url)

    def test_presign_url_with_ssec(self):
        config = Config(signature_version='s3v4')
        client = self.session.create_client('s3', 'us-east-1', config=config)
        url = client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': 'mybucket',
                'Key': 'mykey',
                'SSECustomerKey': 'a' * 32,
                'SSECustomerAlgorithm': 'AES256'
            }
        )
        # The md5 of the sse-c key will be injected when parameters are
        # built so it should show up in the presigned url as well.
        self.assertIn(
            'x-amz-server-side-encryption-customer-key-md5&', url
        )

    def test_presign_s3_accelerate(self):
        config = Config(signature_version=botocore.UNSIGNED,
                        s3={'use_accelerate_endpoint': True})
        client = self.session.create_client('s3', 'us-east-1', config=config)
        url = client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': 'mybucket', 'Key': 'mykey'}
        )
        # The url should be the accelerate endpoint
        self.assertEqual(
            'https://mybucket.s3-accelerate.amazonaws.com/mykey', url)

    def test_presign_s3_accelerate_fails_with_fips(self):
        config = Config(
            signature_version=botocore.UNSIGNED, s3={"use_accelerate_endpoint": True}
        )
        client = self.session.create_client("s3", "fips-us-east-1", config=config)
        expected_exception = UnsupportedS3ConfigurationError
        with self.assertRaisesRegex(
            expected_exception, "S3 Accelerate does not have any FIPS"
        ):
            client.generate_presigned_url(
                ClientMethod="get_object", Params={"Bucket": "mybucket", "Key": "mykey"}
            )

    def test_presign_post_s3_accelerate(self):
        config = Config(signature_version=botocore.UNSIGNED,
                        s3={'use_accelerate_endpoint': True})
        client = self.session.create_client('s3', 'us-east-1', config=config)
        parts = client.generate_presigned_post(
            Bucket='mybucket', Key='mykey')
        # The url should be the accelerate endpoint
        expected = {
            'fields': {'key': 'mykey'},
            'url': 'https://mybucket.s3-accelerate.amazonaws.com/'
        }
        self.assertEqual(parts, expected)



def _checksum_test_cases():
    yield ('put_bucket_tagging',
            {"Bucket": "foo", "Tagging":{"TagSet":[]}})
    yield ('put_bucket_lifecycle',
            {"Bucket": "foo", "LifecycleConfiguration":{"Rules":[]}})
    yield ('put_bucket_lifecycle_configuration',
            {"Bucket": "foo", "LifecycleConfiguration":{"Rules":[]}})
    yield ('put_bucket_cors',
            {"Bucket": "foo", "CORSConfiguration":{"CORSRules": []}})
    yield ('delete_objects',
            {"Bucket": "foo", "Delete": {"Objects": [{"Key": "bar"}]}})
    yield ('put_bucket_replication',
            {"Bucket": "foo",
             "ReplicationConfiguration": {"Role":"", "Rules": []}})
    yield ('put_bucket_acl',
            {"Bucket": "foo", "AccessControlPolicy":{}})
    yield ('put_bucket_logging',
            {"Bucket": "foo",
             "BucketLoggingStatus":{}})
    yield ('put_bucket_notification',
            {"Bucket": "foo", "NotificationConfiguration":{}})
    yield ('put_bucket_policy',
            {"Bucket": "foo", "Policy": "<bucket-policy>"})
    yield ('put_bucket_request_payment',
            {"Bucket": "foo", "RequestPaymentConfiguration":{"Payer": ""}})
    yield ('put_bucket_versioning',
            {"Bucket": "foo", "VersioningConfiguration":{}})
    yield ('put_bucket_website',
            {"Bucket": "foo",
             "WebsiteConfiguration":{}})
    yield ('put_object_acl',
            {"Bucket": "foo", "Key": "bar", "AccessControlPolicy":{}})
    yield ('put_object_legal_hold',
            {"Bucket": "foo", "Key": "bar", "LegalHold":{"Status": "ON"}})
    yield ('put_object_retention',
            {"Bucket": "foo", "Key": "bar",
             "Retention":{"RetainUntilDate":"2020-11-05"}})
    yield ('put_object_lock_configuration',
            {"Bucket": "foo", "ObjectLockConfiguration":{}})


@pytest.mark.parametrize("operation, operation_kwargs", _checksum_test_cases())
def test_checksums_included_in_expected_operations(operation, operation_kwargs):
    """Validate expected calls include Content-MD5 header"""
    environ = {}
    with mock.patch('os.environ', environ):
        environ['AWS_ACCESS_KEY_ID'] = 'access_key'
        environ['AWS_SECRET_ACCESS_KEY'] = 'secret_key'
        environ['AWS_CONFIG_FILE'] = 'no-exist-foo'
        session = create_session()
        session.config_filename = 'no-exist-foo'
        client = session.create_client('s3')
        with ClientHTTPStubber(client) as stub:
            stub.add_response()
            call = getattr(client, operation)
            call(**operation_kwargs)
            assert 'Content-MD5' in stub.requests[-1].headers


def _s3_addressing_test_cases():
    # The default behavior for DNS compatible buckets
    yield dict(region='us-west-2', bucket='bucket', key='key',
                 expected_url='https://bucket.s3.us-west-2.amazonaws.com/key')
    yield dict(region='us-east-1', bucket='bucket', key='key',
                 expected_url='https://bucket.s3.us-east-1.amazonaws.com/key')
    yield dict(region='us-west-1', bucket='bucket', key='key',
                 expected_url='https://bucket.s3.us-west-1.amazonaws.com/key')
    yield dict(region='us-west-1', bucket='bucket', key='key',
                 is_secure=False,
                 expected_url='http://bucket.s3.us-west-1.amazonaws.com/key')

    # Virtual host addressing is independent of signature version.
    yield dict(region='aws-global', bucket='bucket', key='key',
                 signature_version='s3v4',
                 expected_url='https://bucket.s3.amazonaws.com/key')
    yield dict(region='us-west-2', bucket='bucket', key='key',
                 signature_version='s3v4',
                 expected_url=(
                     'https://bucket.s3.us-west-2.amazonaws.com/key'))
    yield dict(region='us-east-1', bucket='bucket', key='key',
                 signature_version='s3v4',
                 expected_url='https://bucket.s3.us-east-1.amazonaws.com/key')
    yield dict(region='us-west-1', bucket='bucket', key='key',
                 signature_version='s3v4',
                 expected_url=(
                     'https://bucket.s3.us-west-1.amazonaws.com/key'))
    yield dict(region='us-west-1', bucket='bucket', key='key',
                 signature_version='s3v4', is_secure=False,
                 expected_url=(
                     'http://bucket.s3.us-west-1.amazonaws.com/key'))
    yield dict(
        region='us-west-1', bucket='bucket-with-num-1', key='key',
        signature_version='s3v4', is_secure=False,
        expected_url='http://bucket-with-num-1.s3.us-west-1.amazonaws.com/key')

    # Regions outside of the 'aws' partition.
    # These should still default to virtual hosted addressing
    # unless explicitly configured otherwise.
    yield dict(region='cn-north-1', bucket='bucket', key='key',
                 signature_version='s3v4',
                 expected_url=(
                     'https://bucket.s3.cn-north-1.amazonaws.com.cn/key'))
    # If the request is unsigned, we should have the default
    # fix_s3_host behavior which is to use virtual hosting where
    # possible but fall back to path style when needed.
    yield dict(region='cn-north-1', bucket='bucket', key='key',
                 signature_version=UNSIGNED,
                 expected_url=(
                     'https://bucket.s3.cn-north-1.amazonaws.com.cn/key'))
    yield dict(region='cn-north-1', bucket='bucket.dot', key='key',
                 signature_version=UNSIGNED,
                 expected_url=(
                     'https://s3.cn-north-1.amazonaws.com.cn/bucket.dot/key'))

    # And of course you can explicitly specify which style to use.
    virtual_hosting = {'addressing_style': 'virtual'}
    yield dict(region='cn-north-1', bucket='bucket', key='key',
                 signature_version=UNSIGNED,
                 s3_config=virtual_hosting,
                 expected_url=(
                     'https://bucket.s3.cn-north-1.amazonaws.com.cn/key'))
    path_style = {'addressing_style': 'path'}
    yield dict(region='cn-north-1', bucket='bucket', key='key',
                 signature_version=UNSIGNED,
                 s3_config=path_style,
                 expected_url=(
                     'https://s3.cn-north-1.amazonaws.com.cn/bucket/key'))

    # If you don't have a DNS compatible bucket, we use path style.
    yield dict(
        region='aws-global', bucket='bucket.dot', key='key',
        expected_url='https://s3.amazonaws.com/bucket.dot/key')
    yield dict(
        region='us-west-2', bucket='bucket.dot', key='key',
        expected_url='https://s3.us-west-2.amazonaws.com/bucket.dot/key')
    yield dict(
        region='us-east-1', bucket='bucket.dot', key='key',
        expected_url='https://s3.us-east-1.amazonaws.com/bucket.dot/key')
    yield dict(
        region='us-east-1', bucket='BucketName', key='key',
        expected_url='https://s3.us-east-1.amazonaws.com/BucketName/key')
    yield dict(
        region='us-west-1', bucket='bucket_name', key='key',
        expected_url='https://s3.us-west-1.amazonaws.com/bucket_name/key')
    yield dict(
        region='us-west-1', bucket='-bucket-name', key='key',
        expected_url='https://s3.us-west-1.amazonaws.com/-bucket-name/key')
    yield dict(
        region='us-west-1', bucket='bucket-name-', key='key',
        expected_url='https://s3.us-west-1.amazonaws.com/bucket-name-/key')
    yield dict(
        region='us-west-1', bucket='aa', key='key',
        expected_url='https://s3.us-west-1.amazonaws.com/aa/key')
    yield dict(
        region='us-west-1', bucket='a'*64, key='key',
        expected_url=('https://s3.us-west-1.amazonaws.com/%s/key' % ('a' * 64))
    )

    # Custom endpoint url should always be used.
    yield dict(
        customer_provided_endpoint='https://my-custom-s3/',
        bucket='foo', key='bar',
        expected_url='https://my-custom-s3/foo/bar')
    yield dict(
        customer_provided_endpoint='https://my-custom-s3/',
        bucket='bucket.dots', key='bar',
        expected_url='https://my-custom-s3/bucket.dots/bar')
    # Doesn't matter what region you specify, a custom endpoint url always
    # wins.
    yield dict(
        customer_provided_endpoint='https://my-custom-s3/',
        region='us-west-2', bucket='foo', key='bar',
        expected_url='https://my-custom-s3/foo/bar')

    # Explicitly configuring "virtual" addressing_style.
    virtual_hosting = {'addressing_style': 'virtual'}
    yield dict(
        region='aws-global', bucket='bucket', key='key',
        s3_config=virtual_hosting,
        expected_url='https://bucket.s3.amazonaws.com/key')
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        s3_config=virtual_hosting,
        expected_url='https://bucket.s3.us-east-1.amazonaws.com/key')
    yield dict(
        region='us-west-2', bucket='bucket', key='key',
        s3_config=virtual_hosting,
        expected_url='https://bucket.s3.us-west-2.amazonaws.com/key')
    yield dict(
        region='eu-central-1', bucket='bucket', key='key',
        s3_config=virtual_hosting,
        expected_url='https://bucket.s3.eu-central-1.amazonaws.com/key')
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        s3_config=virtual_hosting,
        customer_provided_endpoint='https://foo.amazonaws.com',
        expected_url='https://bucket.foo.amazonaws.com/key')
    yield dict(
        region='unknown', bucket='bucket', key='key',
        s3_config=virtual_hosting,
        expected_url='https://bucket.s3.unknown.amazonaws.com/key')

    # Test us-gov with virtual addressing.
    yield dict(
        region='us-gov-west-1', bucket='bucket', key='key',
        s3_config=virtual_hosting,
        expected_url='https://bucket.s3.us-gov-west-1.amazonaws.com/key')

    # Test path style addressing.
    path_style = {'addressing_style': 'path'}
    yield dict(
        region='aws-global', bucket='bucket', key='key',
        s3_config=path_style,
        expected_url='https://s3.amazonaws.com/bucket/key')
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        s3_config=path_style,
        expected_url='https://s3.us-east-1.amazonaws.com/bucket/key')
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        s3_config=path_style,
        customer_provided_endpoint='https://foo.amazonaws.com/',
        expected_url='https://foo.amazonaws.com/bucket/key')
    yield dict(
        region='unknown', bucket='bucket', key='key',
        s3_config=path_style,
        expected_url='https://s3.unknown.amazonaws.com/bucket/key')

    # S3 accelerate
    use_accelerate = {'use_accelerate_endpoint': True}
    yield dict(
        region='aws-global', bucket='bucket', key='key',
        s3_config=use_accelerate,
        expected_url='https://bucket.s3-accelerate.amazonaws.com/key')
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        s3_config=use_accelerate,
        expected_url='https://bucket.s3-accelerate.amazonaws.com/key')
    yield dict(
        # region is ignored with S3 accelerate.
        region='us-west-2', bucket='bucket', key='key',
        s3_config=use_accelerate,
        expected_url='https://bucket.s3-accelerate.amazonaws.com/key')
    # Provided endpoints still get recognized as accelerate endpoints.
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        customer_provided_endpoint='https://s3-accelerate.amazonaws.com',
        expected_url='https://bucket.s3-accelerate.amazonaws.com/key')
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        customer_provided_endpoint='http://s3-accelerate.amazonaws.com',
        expected_url='http://bucket.s3-accelerate.amazonaws.com/key')
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        s3_config=use_accelerate, is_secure=False,
        # Note we're using http://  because is_secure=False.
        expected_url='http://bucket.s3-accelerate.amazonaws.com/key')
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        # s3-accelerate must be the first part of the url.
        customer_provided_endpoint='https://foo.s3-accelerate.amazonaws.com',
        expected_url='https://foo.s3-accelerate.amazonaws.com/bucket/key')
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        # The endpoint must be an Amazon endpoint.
        customer_provided_endpoint='https://s3-accelerate.notamazon.com',
        expected_url='https://s3-accelerate.notamazon.com/bucket/key')
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        # Extra components must be whitelisted.
        customer_provided_endpoint='https://s3-accelerate.foo.amazonaws.com',
        expected_url='https://s3-accelerate.foo.amazonaws.com/bucket/key')
    yield dict(
        region='unknown', bucket='bucket', key='key',
        s3_config=use_accelerate,
        expected_url='https://bucket.s3-accelerate.amazonaws.com/key')
    # Use virtual even if path is specified for s3 accelerate because
    # path style will not work with S3 accelerate.
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        s3_config={'use_accelerate_endpoint': True,
                   'addressing_style': 'path'},
        expected_url='https://bucket.s3-accelerate.amazonaws.com/key')

    # S3 dual stack endpoints.
    use_dualstack = {'use_dualstack_endpoint': True}
    yield dict(
        region=None, bucket='bucket', key='key',
        s3_config=use_dualstack,
        # Uses us-east-1 for no region set.
        expected_url='https://bucket.s3.dualstack.us-east-1.amazonaws.com/key')
    yield dict(
        region='aws-global', bucket='bucket', key='key',
        s3_config=use_dualstack,
        # Pseudo-regions should not have any special resolving logic even when
        # the endpoint won't work as we do not have the metadata to know that
        # a region does not support dualstack. So just format it based on the
        # region name.
        expected_url=(
            'https://bucket.s3.dualstack.aws-global.amazonaws.com/key'))
    yield dict(
        region=None, bucket='bucket', key='key',
        s3_config=use_dualstack, signature_version='s3v4',
        expected_url='https://bucket.s3.dualstack.us-east-1.amazonaws.com/key')
    yield dict(
        region='aws-global', bucket='bucket', key='key',
        s3_config=use_dualstack, signature_version='s3v4',
        expected_url='https://bucket.s3.dualstack.aws-global.amazonaws.com/key')
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        s3_config=use_dualstack, signature_version='s3v4',
        expected_url='https://bucket.s3.dualstack.us-east-1.amazonaws.com/key')
    yield dict(
        region='us-west-2', bucket='bucket', key='key',
        s3_config=use_dualstack, signature_version='s3v4',
        expected_url='https://bucket.s3.dualstack.us-west-2.amazonaws.com/key')
    yield dict(
        region='unknown', bucket='bucket', key='key',
        s3_config=use_dualstack, signature_version='s3v4',
        expected_url='https://bucket.s3.dualstack.unknown.amazonaws.com/key')
    # Non DNS compatible buckets use path style for dual stack.
    yield dict(
        region='us-west-2', bucket='bucket.dot', key='key',
        s3_config=use_dualstack,
        # Still default to virtual hosted when possible.
        expected_url=(
            'https://s3.dualstack.us-west-2.amazonaws.com/bucket.dot/key'))
    # Supports is_secure (use_ssl=False in create_client()).
    yield dict(
        region='us-west-2', bucket='bucket.dot', key='key', is_secure=False,
        s3_config=use_dualstack,
        # Still default to virtual hosted when possible.
        expected_url=(
            'http://s3.dualstack.us-west-2.amazonaws.com/bucket.dot/key'))

    # Is path style is requested, we should use it, even if the bucket is
    # DNS compatible.
    force_path_style = {
        'use_dualstack_endpoint': True,
        'addressing_style': 'path',
    }
    yield dict(
        region='us-west-2', bucket='bucket', key='key',
        s3_config=force_path_style,
        # Still default to virtual hosted when possible.
        expected_url='https://s3.dualstack.us-west-2.amazonaws.com/bucket/key')

    # Accelerate + dual stack
    use_accelerate_dualstack = {
        'use_accelerate_endpoint': True,
        'use_dualstack_endpoint': True,
    }
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        s3_config=use_accelerate_dualstack,
        expected_url=(
            'https://bucket.s3-accelerate.dualstack.amazonaws.com/key'))
    yield dict(
        # Region is ignored with S3 accelerate.
        region='us-west-2', bucket='bucket', key='key',
        s3_config=use_accelerate_dualstack,
        expected_url=(
            'https://bucket.s3-accelerate.dualstack.amazonaws.com/key'))
    # Only s3-accelerate overrides a customer endpoint.
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        s3_config=use_dualstack,
        customer_provided_endpoint='https://s3-accelerate.amazonaws.com',
        expected_url=(
            'https://bucket.s3-accelerate.amazonaws.com/key'))
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        # Dualstack is whitelisted.
        customer_provided_endpoint=(
            'https://s3-accelerate.dualstack.amazonaws.com'),
        expected_url=(
            'https://bucket.s3-accelerate.dualstack.amazonaws.com/key'))
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        # Even whitelisted parts cannot be duplicated.
        customer_provided_endpoint=(
            'https://s3-accelerate.dualstack.dualstack.amazonaws.com'),
        expected_url=(
            'https://s3-accelerate.dualstack.dualstack'
            '.amazonaws.com/bucket/key'))
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        # More than two extra parts is not allowed.
        customer_provided_endpoint=(
            'https://s3-accelerate.dualstack.dualstack.dualstack'
            '.amazonaws.com'),
        expected_url=(
            'https://s3-accelerate.dualstack.dualstack.dualstack.amazonaws.com'
            '/bucket/key'))
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        # Extra components must be whitelisted.
        customer_provided_endpoint='https://s3-accelerate.foo.amazonaws.com',
        expected_url='https://s3-accelerate.foo.amazonaws.com/bucket/key')
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        s3_config=use_accelerate_dualstack, is_secure=False,
        # Note we're using http://  because is_secure=False.
        expected_url=(
            'http://bucket.s3-accelerate.dualstack.amazonaws.com/key'))
    # Use virtual even if path is specified for s3 accelerate because
    # path style will not work with S3 accelerate.
    use_accelerate_dualstack['addressing_style'] = 'path'
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        s3_config=use_accelerate_dualstack,
        expected_url=(
            'https://bucket.s3-accelerate.dualstack.amazonaws.com/key'))

    # Access-point arn cases
    accesspoint_arn = (
        'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint'
    )
    yield dict(
        region='us-west-2', bucket=accesspoint_arn, key='key',
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'us-west-2.amazonaws.com/key'
        )
    )
    yield dict(
        region='us-west-2', bucket=accesspoint_arn, key='key',
        s3_config={'use_arn_region': True},
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'us-west-2.amazonaws.com/key'
        )
    )
    yield dict(
        region='us-west-2', bucket=accesspoint_arn, key='myendpoint/key',
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'us-west-2.amazonaws.com/myendpoint/key'
        )
    )
    yield dict(
        region='us-west-2', bucket=accesspoint_arn, key='foo/myendpoint/key',
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'us-west-2.amazonaws.com/foo/myendpoint/key'
        )
    )
    yield dict(
        # Note: The access-point arn has us-west-2 and the client's region is
        # us-east-1, for the defauldict the access-point arn region is used.
        region='us-east-1', bucket=accesspoint_arn, key='key',
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'us-west-2.amazonaws.com/key'
        )
    )
    yield dict(
        region='us-east-1', bucket=accesspoint_arn, key='key',
        s3_config={'use_arn_region': False},
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'us-east-1.amazonaws.com/key'
        )
    )
    yield dict(
        region='s3-external-1', bucket=accesspoint_arn, key='key',
        s3_config={'use_arn_region': True},
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'us-west-2.amazonaws.com/key'
        )
    )

    yield dict(
        region='aws-global', bucket=accesspoint_arn, key='key',
        s3_config={'use_arn_region': True},
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'us-west-2.amazonaws.com/key'
        )
    )
    yield dict(
        region='unknown', bucket=accesspoint_arn, key='key',
        s3_config={'use_arn_region': False},
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'unknown.amazonaws.com/key'
        )
    )
    yield dict(
        region='unknown', bucket=accesspoint_arn, key='key',
        s3_config={'use_arn_region': True},
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'us-west-2.amazonaws.com/key'
        )
    )
    accesspoint_arn_cn = (
        'arn:aws-cn:s3:cn-north-1:123456789012:accesspoint:myendpoint'
    )
    yield dict(
        region='cn-north-1', bucket=accesspoint_arn_cn, key='key',
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'cn-north-1.amazonaws.com.cn/key'
        )
    )
    yield dict(
        region='cn-northwest-1', bucket=accesspoint_arn_cn, key='key',
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'cn-north-1.amazonaws.com.cn/key'
        )
    )
    yield dict(
        region='cn-northwest-1', bucket=accesspoint_arn_cn, key='key',
        s3_config={'use_arn_region': False},
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'cn-northwest-1.amazonaws.com.cn/key'
        )
    )
    accesspoint_arn_gov = (
        'arn:aws-us-gov:s3:us-gov-west-1:123456789012:accesspoint:myendpoint'
    )
    accesspoint_cross_region_arn_gov = (
        "arn:aws-us-gov:s3:us-gov-east-1:123456789012:accesspoint:myendpoint"
    )
    yield dict(
        region='us-gov-west-1', bucket=accesspoint_arn_gov, key='key',
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'us-gov-west-1.amazonaws.com/key'
        )
    )
    yield dict(
        region='fips-us-gov-west-1', bucket=accesspoint_arn_gov, key='key',
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint-fips.'
            'us-gov-west-1.amazonaws.com/key'
        )
    )
    yield dict(
        region='fips-us-gov-west-1', bucket=accesspoint_arn_gov, key='key',
        s3_config={'use_arn_region': False},
        expected_url=(
            "https://myendpoint-123456789012.s3-accesspoint-fips."
            "us-gov-west-1.amazonaws.com/key"
        ),
    )
    yield dict(
        region="fips-us-gov-west-1",
        bucket=accesspoint_cross_region_arn_gov,
        s3_config={"use_arn_region": True},
        key="key",
        expected_url=(
            "https://myendpoint-123456789012.s3-accesspoint-fips."
            "us-gov-east-1.amazonaws.com/key"
        ),
    )
    yield dict(
        region="us-gov-west-1",
        bucket=accesspoint_arn_gov,
        key="key",
        s3_config={"use_arn_region": False},
        expected_url=(
            "https://myendpoint-123456789012.s3-accesspoint-fips."
            "us-gov-west-1.amazonaws.com/key"
        ),
        use_fips_endpoint=True,
    )
    yield dict(
        region="us-gov-west-1",
        bucket=accesspoint_cross_region_arn_gov,
        key="key",
        s3_config={"use_arn_region": True},
        expected_url=(
            "https://myendpoint-123456789012.s3-accesspoint-fips."
            "us-gov-east-1.amazonaws.com/key"
        ),
        use_fips_endpoint=True,
    )

    yield dict(
        region='us-west-2', bucket=accesspoint_arn, key='key', is_secure=False,
        expected_url=(
            'http://myendpoint-123456789012.s3-accesspoint.'
            'us-west-2.amazonaws.com/key'
        )
    )
    # Dual-stack with access-point arn
    yield dict(
        # Note: The access-point arn has us-west-2 and the client's region is
        # us-east-1, for the defauldict the access-point arn region is used.
        region='us-east-1', bucket=accesspoint_arn, key='key',
        s3_config={
            'use_dualstack_endpoint': True,
        },
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.dualstack.'
            'us-west-2.amazonaws.com/key'
        )
    )
    yield dict(
        region='us-east-1', bucket=accesspoint_arn, key='key',
        s3_config={
            'use_dualstack_endpoint': True,
            'use_arn_region': False
        },
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.dualstack.'
            'us-east-1.amazonaws.com/key'
        )
    )
    yield dict(
        region='us-gov-west-1', bucket=accesspoint_arn_gov, key='key',
        s3_config={
            'use_dualstack_endpoint': True,
        },
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.dualstack.'
            'us-gov-west-1.amazonaws.com/key'
        )
    )
    yield dict(
        region='fips-us-gov-west-1', bucket=accesspoint_arn_gov, key='key',
        s3_config={
            'use_arn_region': True,
            'use_dualstack_endpoint': True,
        },
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint-fips.dualstack.'
            'us-gov-west-1.amazonaws.com/key'
        )
    )
    # None of the various s3 settings related to paths should affect what
    # endpoint to use when an access-point is provided.
    yield dict(
        region='us-west-2', bucket=accesspoint_arn, key='key',
        s3_config={'addressing_style': 'auto'},
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'us-west-2.amazonaws.com/key'
        )
    )
    yield dict(
        region='us-west-2', bucket=accesspoint_arn, key='key',
        s3_config={'addressing_style': 'virtual'},
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'us-west-2.amazonaws.com/key'
        )
    )
    yield dict(
        region='us-west-2', bucket=accesspoint_arn, key='key',
        s3_config={'addressing_style': 'path'},
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'us-west-2.amazonaws.com/key'
        )
    )

    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        expected_url=(
            'https://bucket.s3.us-east-1.amazonaws.com/key'))
    yield dict(
        region='us-west-2', bucket='bucket', key='key',
        expected_url=(
            'https://bucket.s3.us-west-2.amazonaws.com/key'))
    yield dict(
        region=None, bucket='bucket', key='key',
        expected_url=(
            'https://bucket.s3.amazonaws.com/key'))
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        s3_config={
            'use_dualstack_endpoint': True,
        },
        expected_url=(
            'https://bucket.s3.dualstack.us-east-1.amazonaws.com/key'))
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        s3_config={
            'use_accelerate_endpoint': True,
        },
        expected_url=(
            'https://bucket.s3-accelerate.amazonaws.com/key'))
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        s3_config={
            'use_accelerate_endpoint': True,
            'use_dualstack_endpoint': True,
        },
        expected_url=(
            'https://bucket.s3-accelerate.dualstack.amazonaws.com/key'))

    s3_object_lambda_arn_gov = (
        'arn:aws-us-gov:s3-object-lambda:us-gov-west-1:'
        '123456789012:accesspoint:mybanner'
    )
    yield dict(
        region='fips-us-gov-west-1', bucket=s3_object_lambda_arn_gov, key='key',
        expected_url=(
            'https://mybanner-123456789012.s3-object-lambda-fips.'
            'us-gov-west-1.amazonaws.com/key'
        )
    )
    yield dict(
        region="us-gov-west-1",
        bucket=s3_object_lambda_arn_gov,
        key="key",
        expected_url=(
            "https://mybanner-123456789012.s3-object-lambda-fips."
            "us-gov-west-1.amazonaws.com/key"
        ),
        use_fips_endpoint=True,
    )
    s3_object_lambda_cross_region_arn_gov = (
        "arn:aws-us-gov:s3-object-lambda:us-gov-east-1:"
        "123456789012:accesspoint:mybanner"
    )
    yield dict(
        region="fips-us-gov-west-1",
        bucket=s3_object_lambda_cross_region_arn_gov,
        key="key",
        s3_config={"use_arn_region": True},
        expected_url=(
            "https://mybanner-123456789012.s3-object-lambda-fips."
            "us-gov-east-1.amazonaws.com/key"
        ),
    )
    yield dict(
        region="us-gov-west-1",
        bucket=s3_object_lambda_cross_region_arn_gov,
        key="key",
        s3_config={"use_arn_region": True},
        expected_url=(
            "https://mybanner-123456789012.s3-object-lambda-fips."
            "us-gov-east-1.amazonaws.com/key"
        ),
        use_fips_endpoint=True,
    )

    s3_object_lambda_arn = (
        "arn:aws:s3-object-lambda:us-east-1:"
        "123456789012:accesspoint:mybanner"
    )
    yield dict(
        region='aws-global', bucket=s3_object_lambda_arn, key='key',
        s3_config={'use_arn_region': True},
        expected_url=(
            'https://mybanner-123456789012.s3-object-lambda.'
            'us-east-1.amazonaws.com/key'
        )
    )


@pytest.mark.parametrize("test_case", _s3_addressing_test_cases())
def test_correct_url_used_for_s3(test_case):
    # Test that given various sets of config options and bucket names,
    # we construct the expect endpoint url.
    _verify_expected_endpoint_url(**test_case)


def _verify_expected_endpoint_url(
    region=None,
    bucket="bucket",
    key="key",
    s3_config=None,
    is_secure=True,
    customer_provided_endpoint=None,
    expected_url=None,
    signature_version=None,
    use_fips_endpoint=None
):
    environ = {}
    with mock.patch('os.environ', environ):
        environ['AWS_ACCESS_KEY_ID'] = 'access_key'
        environ['AWS_SECRET_ACCESS_KEY'] = 'secret_key'
        environ['AWS_CONFIG_FILE'] = 'no-exist-foo'
        environ['AWS_SHARED_CREDENTIALS_FILE'] = 'no-exist-foo'
        session = create_session()
        session.config_filename = "no-exist-foo"
        config = Config(signature_version=signature_version, s3=s3_config,
                        use_fips_endpoint=use_fips_endpoint)
        s3 = session.create_client('s3', region_name=region, use_ssl=is_secure,
                                   config=config,
                                   endpoint_url=customer_provided_endpoint)
        with ClientHTTPStubber(s3) as http_stubber:
            http_stubber.add_response()
            s3.put_object(Bucket=bucket, Key=key, Body=b'bar')
            assert http_stubber.requests[0].url == expected_url


def _create_s3_client(region, is_secure, endpoint_url, s3_config,
                      signature_version):
    environ = {}
    with mock.patch('os.environ', environ):
        environ['AWS_ACCESS_KEY_ID'] = 'access_key'
        environ['AWS_SECRET_ACCESS_KEY'] = 'secret_key'
        environ['AWS_CONFIG_FILE'] = 'no-exist-foo'
        environ['AWS_SHARED_CREDENTIALS_FILE'] = 'no-exist-foo'
        session = create_session()
        session.config_filename = 'no-exist-foo'
        config = Config(
            signature_version=signature_version,
            s3=s3_config
        )
        s3 = session.create_client('s3', region_name=region, use_ssl=is_secure,
                                   config=config,
                                   endpoint_url=endpoint_url)
        return s3



def _addressing_for_presigned_url_test_cases():

    yield dict(region=None, bucket='bucket', key='key',
                 signature_version=None,
                 expected_url='https://bucket.s3.amazonaws.com/key')
    yield dict(region='aws-global', bucket='bucket', key='key',
                 signature_version=None,
                 expected_url='https://bucket.s3.amazonaws.com/key')
    yield dict(region='us-east-1', bucket='bucket', key='key',
                 signature_version=None,
                 expected_url='https://bucket.s3.us-east-1.amazonaws.com/key')
    yield dict(region='us-east-1', bucket='bucket', key='key',
                 signature_version='s3v4',
                 expected_url='https://bucket.s3.us-east-1.amazonaws.com/key')
    yield dict(region='us-east-1', bucket='bucket', key='key',
                 signature_version='s3v4',
                 s3_config={'addressing_style': 'path'},
                 expected_url='https://s3.us-east-1.amazonaws.com/bucket/key')

    yield dict(region='us-west-2', bucket='bucket', key='key',
                 signature_version=None,
                 expected_url='https://bucket.s3.us-west-2.amazonaws.com/key')
    yield dict(region='us-west-2', bucket='bucket', key='key',
                 signature_version='s3v4',
                 expected_url='https://bucket.s3.us-west-2.amazonaws.com/key')
    yield dict(region='us-west-2', bucket='bucket', key='key',
                 signature_version='s3v4',
                 s3_config={'addressing_style': 'path'},
                 expected_url='https://s3.us-west-2.amazonaws.com/bucket/key')

    # An 's3v4' only region.
    yield dict(region='us-east-2', bucket='bucket', key='key',
                 signature_version=None,
                 expected_url='https://bucket.s3.us-east-2.amazonaws.com/key')
    yield dict(region='us-east-2', bucket='bucket', key='key',
                 signature_version='s3v4',
                 expected_url='https://bucket.s3.us-east-2.amazonaws.com/key')
    yield dict(region='us-east-2', bucket='bucket', key='key',
                 signature_version='s3v4',
                 s3_config={'addressing_style': 'path'},
                 expected_url='https://s3.us-east-2.amazonaws.com/bucket/key')

    # Dualstack endpoints
    yield dict(
        region='us-west-2', bucket='bucket', key='key',
        signature_version=None,
        s3_config={'use_dualstack_endpoint': True},
        expected_url='https://bucket.s3.dualstack.us-west-2.amazonaws.com/key')
    yield dict(
        region='us-west-2', bucket='bucket', key='key',
        signature_version='s3v4',
        s3_config={'use_dualstack_endpoint': True},
        expected_url='https://bucket.s3.dualstack.us-west-2.amazonaws.com/key')

    # Accelerate
    yield dict(region='us-west-2', bucket='bucket', key='key',
                 signature_version=None,
                 s3_config={'use_accelerate_endpoint': True},
                 expected_url='https://bucket.s3-accelerate.amazonaws.com/key')

    # A region that we don't know about.
    yield dict(region='us-west-50', bucket='bucket', key='key',
                 signature_version=None,
                 expected_url='https://bucket.s3.us-west-50.amazonaws.com/key')

    # Customer provided URL results in us leaving the host untouched.
    yield dict(region='us-west-2', bucket='bucket', key='key',
                 signature_version=None,
                 customer_provided_endpoint='https://foo.com/',
                 expected_url='https://foo.com/bucket/key')

    # Access-point
    accesspoint_arn = (
        'arn:aws:s3:us-west-2:123456789012:accesspoint:myendpoint'
    )
    yield dict(
        region='us-west-2', bucket=accesspoint_arn, key='key',
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'us-west-2.amazonaws.com/key'
        )
    )
    yield dict(
        region='us-east-1', bucket=accesspoint_arn, key='key',
        s3_config={'use_arn_region': False},
        expected_url=(
            'https://myendpoint-123456789012.s3-accesspoint.'
            'us-east-1.amazonaws.com/key'
        )
    )

    # Use us-east-1 regional endpoint configuration cases
    us_east_1_regional_endpoint = {
        'us_east_1_regional_endpoint': 'regional'
    }
    yield dict(
        region='us-east-1', bucket='bucket', key='key',
        s3_config=us_east_1_regional_endpoint, signature_version='s3v4',
        expected_url=(
            'https://bucket.s3.us-east-1.amazonaws.com/key'))


@pytest.mark.parametrize("test_case", _addressing_for_presigned_url_test_cases())
def test_addressing_for_presigned_urls(test_case):
    # Here's we're just focusing on the addressing mode used for presigned URLs.
    # We special case presigned URLs due to backward compatibility.
    _verify_presigned_url_addressing(**test_case)


def _verify_presigned_url_addressing(
    region=None, bucket='bucket', key='key', s3_config=None, is_secure=True,
    customer_provided_endpoint=None, expected_url=None, signature_version=None
):
    s3 = _create_s3_client(region=region, is_secure=is_secure,
                           endpoint_url=customer_provided_endpoint,
                           s3_config=s3_config,
                           signature_version=signature_version)
    url = s3.generate_presigned_url(
        'get_object', {'Bucket': bucket, 'Key': key})
    # We're not trying to verify the params for URL presigning,
    # those are tested elsewhere.  We just care about the hostname/path.
    parts = urlsplit(url)
    actual = '%s://%s%s' % parts[:3]
    assert actual == expected_url


class TestRequestPayerObjectTagging(BaseS3OperationTest):
    def _assert_request_payer_header(self, op_name, **kwargs):
        self.http_stubber.add_response()
        with self.http_stubber:
            getattr(self.client, op_name)(**kwargs)
        request = self.http_stubber.requests[0]
        self.assertIn('x-amz-request-payer', request.headers)

    def test_can_provide_request_payer_put_tagging(self):
        self._assert_request_payer_header('put_object_tagging',
            Bucket='bucket',
            Key='key',
            RequestPayer='requester',
            Tagging={'TagSet': []},
        )

    def test_can_provide_request_payer_get_tagging(self):
        self._assert_request_payer_header('get_object_tagging',
            Bucket='bucket',
            Key='key',
            RequestPayer='requester',
        )


class TestS3XMLPayloadEscape(BaseS3OperationTest):
    def assert_correct_content_md5(self, request):
        content_md5_bytes = get_md5(request.body).digest()
        content_md5 = base64.b64encode(content_md5_bytes)
        self.assertEqual(content_md5, request.headers['Content-MD5'])

    def test_escape_keys_in_xml_delete_objects(self):
        self.http_stubber.add_response()
        with self.http_stubber:
            response = self.client.delete_objects(
                Bucket='mybucket',
                Delete={
                    'Objects': [{'Key': 'some\r\n\rkey'}]
                },
            )
        request = self.http_stubber.requests[0]
        self.assertNotIn(b'\r\n\r', request.body)
        self.assertIn(b'&#xD;&#xA;&#xD;', request.body)
        self.assert_correct_content_md5(request)

    def test_escape_keys_in_xml_put_bucket_lifecycle_configuration(self):
        self.http_stubber.add_response()
        with self.http_stubber:
            response = self.client.put_bucket_lifecycle_configuration(
                Bucket='mybucket',
                LifecycleConfiguration={
                    'Rules': [{
                        'Prefix': 'my\r\n\rprefix',
                        'Status': 'ENABLED',
                    }]
                }
            )
        request = self.http_stubber.requests[0]
        self.assertNotIn(b'my\r\n\rprefix', request.body)
        self.assertIn(b'my&#xD;&#xA;&#xD;prefix', request.body)
        self.assert_correct_content_md5(request)
