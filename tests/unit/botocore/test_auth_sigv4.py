# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests import unittest

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

SECRET_KEY = "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"
ACCESS_KEY = 'AKIDEXAMPLE'


class TestSigV4Auth(unittest.TestCase):
    def setUp(self):
        self.credentials = Credentials(ACCESS_KEY, SECRET_KEY)
        self.sigv4 = SigV4Auth(self.credentials, 'host', 'us-weast-1')

    def test_signed_host_is_lowercase(self):
        endpoint = 'https://S5.Us-WeAsT-2.AmAZonAwS.com'
        expected_host = 's5.us-weast-2.amazonaws.com'
        request = AWSRequest(method='GET', url=endpoint)
        headers_to_sign = self.sigv4.headers_to_sign(request)
        self.assertEqual(expected_host, headers_to_sign.get('host'))
