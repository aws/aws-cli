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
import pytest

from tests import create_session, mock, ClientHTTPStubber


OPERATION_PARAMS = {
    'change_password': {
        'PreviousPassword': 'myoldbadpassword',
        'ProposedPassword': 'mynewgoodpassword',
        'AccessToken': 'foobar'
    },
    'confirm_forgot_password': {
        'ClientId': 'foo',
        'Username': 'myusername',
        'ConfirmationCode': 'thisismeforreal',
        'Password': 'whydowesendpasswordsviaemail'
    },
    'confirm_sign_up': {
        'ClientId': 'foo',
        'Username': 'myusername',
        'ConfirmationCode': 'ireallydowanttosignup'
    },
    'delete_user': {
        'AccessToken': 'foobar'
    },
    'delete_user_attributes': {
        'UserAttributeNames': ['myattribute'],
        'AccessToken': 'foobar'
    },
    'forgot_password': {
        'ClientId': 'foo',
        'Username': 'myusername'
    },
    'get_user': {
        'AccessToken': 'foobar'
    },
    'get_user_attribute_verification_code': {
        'AttributeName': 'myattribute',
        'AccessToken': 'foobar'
    },
    'resend_confirmation_code': {
        'ClientId': 'foo',
        'Username': 'myusername'
    },
    'set_user_settings': {
        'AccessToken': 'randomtoken',
        'MFAOptions': [{
            'DeliveryMedium': 'SMS',
            'AttributeName': 'someattributename'
        }]
    },
    'sign_up': {
        'ClientId': 'foo',
        'Username': 'bar',
        'Password': 'mysupersecurepassword',
    },
    'update_user_attributes': {
        'UserAttributes': [{
            'Name': 'someattributename',
            'Value': 'newvalue'
        }],
        'AccessToken': 'foobar'
    },
    'verify_user_attribute': {
        'AttributeName': 'someattributename',
        'Code': 'someverificationcode',
        'AccessToken': 'foobar'
    },
}

@pytest.mark.parametrize("operation_name, parameters", OPERATION_PARAMS.items())
def test_unsigned_operations(operation_name, parameters):
    environ = {
        'AWS_ACCESS_KEY_ID': 'access_key',
        'AWS_SECRET_ACCESS_KEY': 'secret_key',
        'AWS_CONFIG_FILE': 'no-exist-foo',
    }

    with mock.patch('os.environ', environ):
        session = create_session()
        session.config_filename = 'no-exist-foo'
        client = session.create_client('cognito-idp', 'us-west-2')
        http_stubber = ClientHTTPStubber(client)

        operation = getattr(client, operation_name)

        http_stubber.add_response(body=b'{}')
        with http_stubber:
            operation(**parameters)
            request = http_stubber.requests[0]

        assert 'authorization' not in request.headers, (
            'authorization header found in unsigned operation'
        )
