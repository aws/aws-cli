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
from botocore.exceptions import UnsupportedTLSVersionWarning
from tests import BaseSessionTest, mock


class TestOpensslVersion(BaseSessionTest):
    def test_incompatible_openssl_version(self):
        with mock.patch('ssl.OPENSSL_VERSION_INFO', new=(0, 9, 8, 11, 15)):
            with mock.patch('warnings.warn') as mock_warn:
                self.session.create_client('iot-data', 'us-east-1')
                call_args = mock_warn.call_args[0]
                warning_message = call_args[0]
                warning_type = call_args[1]
                # We should say something specific about the service.
                self.assertIn('iot-data', warning_message)
                self.assertEqual(warning_type, UnsupportedTLSVersionWarning)

    def test_compatible_openssl_version(self):
        with mock.patch('ssl.OPENSSL_VERSION_INFO', new=(1, 0, 1, 1, 1)):
            with mock.patch('warnings.warn') as mock_warn:
                self.session.create_client('iot-data', 'us-east-1')
                self.assertFalse(mock_warn.called)
