# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from datetime import datetime
import re

import mock

from tests import BaseSessionTest
from tests import temporary_file
from tests import assert_url_equal
from tests import ClientHTTPStubber
from botocore.config import Config
from botocore.stub import Stubber


_V4_SIGNING_REGION_REGEX = re.compile(
    r'AWS4-HMAC-SHA256 '
    r'Credential=\w+/\d+/(?P<signing_region>[a-z0-9-]+)/'
)


class TestSTSPresignedUrl(BaseSessionTest):
    def setUp(self):
        super(TestSTSPresignedUrl, self).setUp()
        self.client = self.session.create_client('sts', 'us-west-2')
        # Makes sure that no requests will go through
        self.stubber = Stubber(self.client)
        self.stubber.activate()

    def test_presigned_url_contains_no_content_type(self):
        timestamp = datetime(2017, 3, 22, 0, 0)
        with mock.patch('botocore.auth.datetime') as _datetime:
            _datetime.datetime.utcnow.return_value = timestamp
            url = self.client.generate_presigned_url('get_caller_identity', {})

        # There should be no 'content-type' in x-amz-signedheaders
        expected_url = (
            'https://sts.us-west-2.amazonaws.com/?Action=GetCallerIdentity&'
            'Version=2011-06-15&X-Amz-Algorithm=AWS4-HMAC-SHA256&'
            'X-Amz-Credential=access_key%2F20170322%2Fus-west-2%2Fsts%2F'
            'aws4_request&X-Amz-Date=20170322T000000Z&X-Amz-Expires=3600&'
            'X-Amz-SignedHeaders=host&X-Amz-Signature=6544a55c35d587a56d10'
            '41de1abf443791f63be1f75f555ca11b609879cd2020'
        )
        assert_url_equal(url, expected_url)


class TestSTSEndpoints(BaseSessionTest):
    def create_sts_client(self, region, endpoint_url=None, use_ssl=True,
                          config=None):
        return self.session.create_client(
            'sts', region_name=region, endpoint_url=endpoint_url,
            use_ssl=use_ssl, config=config
        )

    def set_sts_regional_for_config_file(self, fileobj, config_val):
        fileobj.write(
            '[default]\n'
            'sts_regional_endpoints=%s\n' % config_val
        )
        fileobj.flush()
        self.environ['AWS_CONFIG_FILE'] = fileobj.name

    def assert_request_sent(self, sts, expected_url,
                            expected_signing_region=None):
        body = (
            b'<GetCallerIdentityResponse>'
            b'  <GetCallerIdentityResult>'
            b'     <Arn>arn:aws:iam::123456789012:user/myuser</Arn>'
            b'     <UserId>UserID</UserId>'
            b'     <Account>123456789012</Account>'
            b'   </GetCallerIdentityResult>'
            b'   <ResponseMetadata>'
            b'     <RequestId>some-request</RequestId>'
            b'   </ResponseMetadata>'
            b'</GetCallerIdentityResponse>'
        )
        with ClientHTTPStubber(sts) as http_stubber:
            http_stubber.add_response(body=body)
            sts.get_caller_identity()
            captured_request = http_stubber.requests[0]
            self.assertEqual(captured_request.url, expected_url)
            if expected_signing_region:
                self.assertEqual(
                    self._get_signing_region(captured_request),
                    expected_signing_region
                )

    def _get_signing_region(self, request):
        authorization_val = request.headers['Authorization'].decode('utf-8')
        match = _V4_SIGNING_REGION_REGEX.match(authorization_val)
        return match.group('signing_region')

    def test_sts_standard_endpoint(self):
        sts = self.create_sts_client('us-west-2')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.us-west-2.amazonaws.com/',
            expected_signing_region='us-west-2'
        )

    def test_fips_endpoint(self):
        sts = self.create_sts_client('us-west-2-fips')
        self.assert_request_sent(
            sts,
            expected_url='https://sts-fips.us-west-2.amazonaws.com/',
            expected_signing_region='us-west-2'
        )

    def test_dualstack_endpoint(self):
        dualstack_config = Config(use_dualstack_endpoint=True)
        sts = self.create_sts_client('us-west-2', config=dualstack_config)
        self.assert_request_sent(
            sts,
            expected_url='https://sts.us-west-2.api.aws/',
            expected_signing_region='us-west-2'
        )

    def test_nonaws_partition_region(self):
        sts = self.create_sts_client('cn-north-1')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.cn-north-1.amazonaws.com.cn/',
            expected_signing_region='cn-north-1'
        )

    def test_global_region_with_regional_configured(self):
        sts = self.create_sts_client('aws-global')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.amazonaws.com/',
            expected_signing_region='us-east-1'
        )

    def test_client_for_unknown_region(self):
        sts = self.create_sts_client('not-real')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.not-real.amazonaws.com/',
            expected_signing_region='not-real'
        )
