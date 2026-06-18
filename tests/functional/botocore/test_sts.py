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
import datetime
import re

from botocore.config import Config
from botocore.stub import Stubber
from tests import (
    BaseSessionTest,
    ClientHTTPStubber,
    assert_url_equal,
    mock,
    temporary_file,
)

_V4_SIGNING_REGION_REGEX = re.compile(
    r'AWS4-HMAC-SHA256 Credential=\w+/\d+/(?P<signing_region>[a-z0-9-]+)/'
)


class TestSTSPresignedUrl(BaseSessionTest):
    def setUp(self):
        super().setUp()
        self.client = self.session.create_client('sts', 'us-west-2')
        # Makes sure that no requests will go through
        self.stubber = Stubber(self.client)
        self.stubber.activate()

    def test_presigned_url_contains_no_content_type(self):
        timestamp = datetime.datetime(
            2017, 3, 22, 0, 0, tzinfo=datetime.timezone.utc
        )
        with mock.patch('botocore.auth.datetime.datetime') as _datetime:
            _datetime.now.return_value = timestamp
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
    def create_sts_client(
        self, region, endpoint_url=None, use_ssl=True, config=None
    ):
        return self.session.create_client(
            'sts',
            region_name=region,
            endpoint_url=endpoint_url,
            use_ssl=use_ssl,
            config=config,
        )

    def set_sts_regional_for_config_file(self, fileobj, config_val):
        fileobj.write(f'[default]\nsts_regional_endpoints={config_val}\n')
        fileobj.flush()
        self.environ['AWS_CONFIG_FILE'] = fileobj.name

    def assert_request_sent(
        self, sts, expected_url, expected_signing_region=None
    ):
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
                    expected_signing_region,
                )

    def _get_signing_region(self, request):
        authorization_val = request.headers['Authorization'].decode('utf-8')
        match = _V4_SIGNING_REGION_REGEX.match(authorization_val)
        return match.group('signing_region')

    def test_legacy_region_with_legacy_configured(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'legacy'
        sts = self.create_sts_client('us-west-2')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.amazonaws.com/',
            expected_signing_region='us-east-1',
        )

    def test_legacy_region_with_regional_configured(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'regional'
        sts = self.create_sts_client('us-west-2')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.us-west-2.amazonaws.com/',
            expected_signing_region='us-west-2',
        )

    def test_fips_endpoint_with_legacy_configured(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'legacy'
        sts = self.create_sts_client('us-west-2-fips')
        self.assert_request_sent(
            sts,
            expected_url='https://sts-fips.us-west-2.amazonaws.com/',
            expected_signing_region='us-west-2',
        )

    def test_fips_endpoint_with_regional_configured(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'regional'
        sts = self.create_sts_client('us-west-2-fips')
        self.assert_request_sent(
            sts,
            expected_url='https://sts-fips.us-west-2.amazonaws.com/',
            expected_signing_region='us-west-2',
        )

    def test_dualstack_endpoint_with_legacy_configured(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'legacy'
        dualstack_config = Config(use_dualstack_endpoint=True)
        sts = self.create_sts_client('us-west-2', config=dualstack_config)
        self.assert_request_sent(
            sts,
            expected_url='https://sts.us-west-2.api.aws/',
            expected_signing_region='us-west-2',
        )

    def test_dualstack_endpoint_with_regional_configured(self):
        dualstack_config = Config(use_dualstack_endpoint=True)
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'regional'
        sts = self.create_sts_client('us-west-2', config=dualstack_config)
        self.assert_request_sent(
            sts,
            expected_url='https://sts.us-west-2.api.aws/',
            expected_signing_region='us-west-2',
        )

    def test_nonlegacy_region_with_legacy_configured(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'legacy'
        sts = self.create_sts_client('ap-east-1')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.ap-east-1.amazonaws.com/',
            expected_signing_region='ap-east-1',
        )

    def test_nonlegacy_region_with_regional_configured(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'regional'
        sts = self.create_sts_client('ap-east-1')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.ap-east-1.amazonaws.com/',
            expected_signing_region='ap-east-1',
        )

    def test_nonaws_partition_region_with_legacy_configured(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'legacy'
        sts = self.create_sts_client('cn-north-1')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.cn-north-1.amazonaws.com.cn/',
            expected_signing_region='cn-north-1',
        )

    def test_nonaws_partition_region_with_regional_configured(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'regional'
        sts = self.create_sts_client('cn-north-1')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.cn-north-1.amazonaws.com.cn/',
            expected_signing_region='cn-north-1',
        )

    def test_global_region_with_legacy_configured(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'legacy'
        sts = self.create_sts_client('aws-global')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.amazonaws.com/',
            expected_signing_region='us-east-1',
        )

    def test_global_region_with_regional_configured(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'regional'
        sts = self.create_sts_client('aws-global')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.amazonaws.com/',
            expected_signing_region='us-east-1',
        )

    def test_defaults_to_regional_endpoint(self):
        sts = self.create_sts_client('us-west-2')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.us-west-2.amazonaws.com/',
            expected_signing_region='us-west-2',
        )

    def test_defaults_to_regional_endpoint_for_us_east_1(self):
        sts = self.create_sts_client('us-east-1')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.us-east-1.amazonaws.com/',
            expected_signing_region='us-east-1',
        )

    def test_defaults_to_global_endpoint_for_legacy(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'legacy'
        sts = self.create_sts_client('us-west-2')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.amazonaws.com/',
            expected_signing_region='us-east-1',
        )

    def test_defaults_to_regional_endpoint_for_nonlegacy_region(self):
        sts = self.create_sts_client('ap-east-1')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.ap-east-1.amazonaws.com/',
            expected_signing_region='ap-east-1',
        )

    def test_configure_sts_regional_from_config_file(self):
        with temporary_file('w') as f:
            self.set_sts_regional_for_config_file(f, 'regional')
            sts = self.create_sts_client('us-west-2')
            self.assert_request_sent(
                sts,
                expected_url='https://sts.us-west-2.amazonaws.com/',
            )

    def test_env_var_overrides_config_file(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'legacy'
        with temporary_file('w') as f:
            self.set_sts_regional_for_config_file(f, 'regional')
            sts = self.create_sts_client('us-west-2')
            self.assert_request_sent(
                sts, expected_url='https://sts.amazonaws.com/'
            )

    def test_user_provided_endpoint_with_legacy_configured(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'legacy'
        sts = self.create_sts_client(
            'us-west-2', endpoint_url='https://custom.com'
        )
        self.assert_request_sent(sts, expected_url='https://custom.com/')

    def test_user_provided_endpoint_with_regional_configured(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'regional'
        sts = self.create_sts_client(
            'us-west-2', endpoint_url='https://custom.com'
        )
        self.assert_request_sent(sts, expected_url='https://custom.com/')

    def test_http_with_legacy_configured(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'legacy'
        sts = self.create_sts_client('us-west-2', use_ssl=False)
        self.assert_request_sent(sts, expected_url='http://sts.amazonaws.com/')

    def test_client_for_unknown_region(self):
        sts = self.create_sts_client('not-real')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.not-real.amazonaws.com/',
            expected_signing_region='not-real',
        )

    def test_client_for_unknown_region_with_legacy_configured(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'legacy'
        sts = self.create_sts_client('not-real')
        self.assert_request_sent(
            sts, expected_url='https://sts.not-real.amazonaws.com/'
        )

    def test_client_for_unknown_region_with_regional_configured(self):
        self.environ['AWS_STS_REGIONAL_ENDPOINTS'] = 'regional'
        sts = self.create_sts_client('not-real')
        self.assert_request_sent(
            sts,
            expected_url='https://sts.not-real.amazonaws.com/',
            expected_signing_region='not-real',
        )


def test_assume_role_with_saml_no_region_custom_endpoint(patched_session):
    # When an endpoint_url and no region are given, AssumeRoleWithSAML should
    # resolve to the endpoint_url and succeed, not fail in endpoint resolution:
    # https://github.com/aws/aws-cli/issues/7455

    client = patched_session.create_client(
        'sts', region_name=None, endpoint_url="https://custom.endpoint.aws"
    )
    assert client.meta.region_name is None

    mock_response_body = b"""\
<AssumeRoleWithSAMLResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
    <AssumeRoleWithSAMLResult></AssumeRoleWithSAMLResult>
</AssumeRoleWithSAMLResponse>
"""
    with ClientHTTPStubber(client) as http_stubber:
        http_stubber.add_response(body=mock_response_body)
        client.assume_role_with_saml(
            RoleArn='arn:aws:iam::123456789:role/RoleA',
            PrincipalArn='arn:aws:iam::123456789:role/RoleB',
            SAMLAssertion='xxxx',
        )
    captured_request = http_stubber.requests[0]
    assert captured_request.url == "https://custom.endpoint.aws/"
