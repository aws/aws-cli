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

import botocore.session
from botocore.handlers import SERVICE_NAME_ALIASES

CLIENT_KWARGS = {
    "region_name": "us-east-1",
    "aws_access_key_id": "foo",
    "aws_secret_access_key": "bar",
}


def _service_alias_test_cases():
    session = botocore.session.get_session()
    for alias, name in SERVICE_NAME_ALIASES.items():
        yield session, name, alias


@pytest.mark.parametrize(
    "session, service_name, service_alias", _service_alias_test_cases()
)
def test_can_use_service_alias(session, service_name, service_alias):
    original_client = session.create_client(service_name, **CLIENT_KWARGS)
    aliased_client = session.create_client(service_alias, **CLIENT_KWARGS)
    original_model_name = original_client.meta.service_model.service_name
    aliased_model_name = aliased_client.meta.service_model.service_name
    assert original_model_name == aliased_model_name
