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
from tests import unittest, ClientHTTPStubber

import botocore.session
from botocore.exceptions import ClientError

class TestSTS(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        credentials = self.session.get_credentials()
        if credentials.token is not None:
            self.skipTest('STS tests require long-term credentials')

    def test_regionalized_endpoints(self):
        sts = self.session.create_client('sts', region_name='ap-southeast-1')
        response = sts.get_session_token()
        # Do not want to be revealing any temporary keys if the assertion fails
        self.assertIn('Credentials', response.keys())

        # Since we have to activate STS regionalization, we will test
        # that you can send an STS request to a regionalized endpoint
        # by making a call with the explicitly wrong region name
        sts = self.session.create_client(
            'sts', region_name='ap-southeast-1',
            endpoint_url='https://sts.us-west-2.amazonaws.com')
        self.assertEqual(sts.meta.region_name, 'ap-southeast-1')
        self.assertEqual(sts.meta.endpoint_url,
                         'https://sts.us-west-2.amazonaws.com')
        # Signing error will be thrown with the incorrect region name included.
        with self.assertRaisesRegex(ClientError, 'ap-southeast-1') as e:
            sts.get_session_token()


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
