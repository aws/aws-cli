# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import re
import functools

from tests import RawResponse

import mock

import botocore
from botocore.session import Session

from awscli.testutils import unittest
from awscli.testutils import BaseCLIDriverTest
from awscli.clidriver import CLIDriver


class TestSession(BaseCLIDriverTest):
    def setUp(self):
        super(TestSession, self).setUp()
        urllib3_session_send = 'botocore.httpsession.URLLib3Session.send'
        self._urllib3_patch = mock.patch(urllib3_session_send)
        self._send = self._urllib3_patch.start()
        self._send.side_effect = self.get_response
        self._responses = []

    def tearDown(self):
        self._urllib3_patch.stop()

    def get_response(self, request):
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def add_response(self, body, status_code=200):
        response = botocore.awsrequest.AWSResponse(
            url='http://169.254.169.254/',
            status_code=status_code,
            headers={},
            raw=RawResponse(body)
        )
        self._responses.append(response)

    def assert_correct_region(self, expected_region, request, **kwargs):
        url = request.url
        region = re.match(
            'https://.*?\.(.*?)\.amazonaws\.com', url).groups(1)[0]
        self.assertEqual(expected_region, region)

    def test_imds_region_is_used_as_fallback(self):
        # Remove region override from the environment variables.
        self.environ.pop('AWS_DEFAULT_REGION', 0)
        # First response should be from the IMDS server for an availibility
        # zone.
        self.add_response(b'us-mars-2a')
        # Once a region is fetched form the IMDS server we need to mock an
        # XML response from ec2 so that the CLI driver doesn't throw an error
        # during parsing.
        self.add_response(
            b'<?xml version="1.0" ?><foo><bar>text</bar></foo>')
        assert_correct_region = functools.partial(
            self.assert_correct_region, 'us-mars-2')
        self.session.register('before-send.ec2.*', assert_correct_region)
        self.driver.main(['ec2', 'describe-instances'])
