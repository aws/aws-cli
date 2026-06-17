# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import botocore.session
from tests import random_chars, unittest


class TestCognitoIdentity(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client(
            'cognito-identity', 'us-east-1'
        )

    def test_can_create_and_delete_identity_pool(self):
        pool_name = f'test{random_chars(10)}'
        response = self.client.create_identity_pool(
            IdentityPoolName=pool_name, AllowUnauthenticatedIdentities=True
        )
        self.client.delete_identity_pool(
            IdentityPoolId=response['IdentityPoolId']
        )


if __name__ == '__main__':
    unittest.main()
