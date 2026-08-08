# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import pytest
from dateutil.tz import tzutc

import botocore.auth
from tests import FreezeTime

HOSTNAME = "peccy.dsql.us-east-1.on.aws"
REGION = "us-east-1"
AWS_ACCESS_KEY_ID = "akid"
AWS_SECRET_ACCESS_KEY = "secret"
DATE = datetime.datetime(2024, 8, 27, tzinfo=tzutc())


@pytest.fixture()
def client(patched_session):
    return patched_session.create_client(
        "dsql",
        REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )


@FreezeTime(botocore.auth.datetime, date=DATE)
def test_generate_db_connect_auth_token(client):
    auth_token = client.generate_db_connect_auth_token(
        Hostname=HOSTNAME, Region=REGION
    )
    assert f"{HOSTNAME}/?Action=DbConnect" in auth_token
    assert (
        f"X-Amz-Credential={AWS_ACCESS_KEY_ID}%2F20240827%2F{REGION}%2Fdsql%2Faws4_request"
        in auth_token
    )
    assert "X-Amz-Expires=900" in auth_token
    # Asserts that there is no scheme in the URL
    assert auth_token.startswith(HOSTNAME)


@FreezeTime(botocore.auth.datetime, date=DATE)
def test_generate_db_connect_admin_auth_token(client):
    auth_token = client.generate_db_connect_admin_auth_token(
        Hostname=HOSTNAME, Region=REGION
    )
    assert f"{HOSTNAME}/?Action=DbConnectAdmin" in auth_token
    assert (
        f"X-Amz-Credential={AWS_ACCESS_KEY_ID}%2F20240827%2F{REGION}%2Fdsql%2Faws4_request"
        in auth_token
    )
    assert "X-Amz-Expires=900" in auth_token
    # Asserts that there is no scheme in the URL
    assert auth_token.startswith(HOSTNAME)


def test_generate_db_connect_auth_token_extra_params(client):
    region = "us-west-2"
    expires_in = 3600
    auth_token = client.generate_db_connect_auth_token(
        HOSTNAME, Region=region, ExpiresIn=expires_in
    )
    assert f"X-Amz-Expires={expires_in}" in auth_token
    assert region in auth_token


def test_generate_db_connect_admin_auth_token_extra_params(client):
    region = "us-west-2"
    expires_in = 3600
    auth_token = client.generate_db_connect_admin_auth_token(
        HOSTNAME, Region=region, ExpiresIn=expires_in
    )
    assert f"&X-Amz-Expires={expires_in}" in auth_token
    assert region in auth_token
