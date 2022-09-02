# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from botocore.auth import BearerAuth
from botocore.awsrequest import AWSRequest
from botocore.exceptions import NoAuthTokenError
from botocore.tokens import FrozenAuthToken

cases = [
    {
        "documentation": "Minimal bearer auth case",
        "headers": {},
        "token": "mF_9.B5f-4.1JqM",
        "expectedHeaders": {"Authorization": "Bearer mF_9.B5f-4.1JqM"},
    },
    {
        "documentation": "Longer token case",
        "headers": {},
        "token": "eW91J3JlIG5vdCBzdXBwb3NlZCB0byBkZWNvZGUgdGhpcyE=",
        "expectedHeaders": {
            "Authorization": "Bearer eW91J3JlIG5vdCBzdXBwb3NlZCB0byBkZWNvZGUgdGhpcyE="
        },
    },
    {
        "documentation": "Signer should override existing header",
        "headers": {"Authorization": "Bearer foo"},
        "token": "mF_9.B5f-4.1JqM",
        "expectedHeaders": {"Authorization": "Bearer mF_9.B5f-4.1JqM"},
    },
    {
        "documentation": "Signer requires a token",
        "headers": {},
        "token": None,
        "expectedException": NoAuthTokenError,
    },
]


@pytest.mark.parametrize("test_case", cases)
def test_bearer_auth(test_case):
    url = "https://example.com"
    headers = test_case.get("headers", {})
    request = AWSRequest(method="GET", url=url, headers=headers)

    auth_token = None
    raw_token = test_case["token"]
    if raw_token:
        auth_token = FrozenAuthToken(test_case["token"], expiration=None)

    bearer_auth = BearerAuth(auth_token)
    expected_headers = test_case.get("expectedHeaders")
    expected_exception = test_case.get("expectedException")
    if expected_headers:
        bearer_auth.add_auth(request)
        for name in expected_headers:
            actual_header = request.headers[name]
            expected_header = expected_headers[name]
            assert actual_header == expected_header
    elif expected_exception:
        with pytest.raises(expected_exception):
            bearer_auth.add_auth(request)
