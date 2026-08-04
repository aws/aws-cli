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
import pytest

from botocore.config import Config
from botocore.handlers import get_bearer_auth_supported_services
from tests import create_session, mock

# In the future, a service may have a list of credentials requirements where one
# signature may fail and others may succeed. e.g. a service may want to use bearer
# auth but fall back to sigv4 if a token isn't available. There's currently no way to do
# this in botocore, so this test ensures we handle this gracefully when the need arises.

# Some services (such as Bedrock) have customizations that bypass this limitation
# by manually assigning a signer when credentials are unavailable. To avoid
# false positives, we filter these services out of the tests below.


# The dictionary's value here needs to be hashable to be added to the set below; any
# new auth types with multiple requirements should be added in a comma-separated list
AUTH_TYPE_REQUIREMENTS = {
    'aws.auth#sigv4': 'credentials',
    'aws.auth#sigv4a': 'credentials',
    'smithy.api#httpBearerAuth': 'bearer_token',
    'smithy.api#noAuth': 'none',
}

# Services with a `signing_name` that are known to have
# customizations for handling mixed authentication methods.
KNOWN_MIXED_AUTH_SERVICES = get_bearer_auth_supported_services()
KNOWN_MIXED_AUTH_SCHEMES = {'aws.auth#sigv4', 'smithy.api#httpBearerAuth'}


def _all_test_cases():
    session = create_session()
    loader = session.get_component('data_loader')

    services = loader.list_available_services('service-2')
    auth_services = []
    auth_operations = []

    for service in services:
        service_model = session.get_service_model(service)
        signing_name = service_model.signing_name
        auth_config = service_model.metadata.get('auth', {})
        if signing_name in KNOWN_MIXED_AUTH_SERVICES:
            if set(auth_config) == KNOWN_MIXED_AUTH_SCHEMES:
                # Skip service due to known mixed auth configurations.
                continue
        if auth_config:
            auth_services.append([service, auth_config])
        for operation in service_model.operation_names:
            operation_model = service_model.operation_model(operation)
            if operation_model.auth:
                auth_operations.append([service, operation_model])
    return auth_services, auth_operations


AUTH_SERVICES, AUTH_OPERATIONS = _all_test_cases()


@pytest.mark.validates_models
@pytest.mark.parametrize("auth_service, auth_config", AUTH_SERVICES)
def test_all_requirements_match_for_service(auth_service, auth_config):
    # Validates that all service-level signature types have the same requirements
    message = f'Found mixed signer requirements for service: {auth_service}'
    assert_all_requirements_match(auth_config, message)


@pytest.mark.validates_models
@pytest.mark.parametrize("auth_service, operation_model", AUTH_OPERATIONS)
def test_all_requirements_match_for_operation(auth_service, operation_model):
    # Validates that all operation-level signature types have the same requirements
    message = f'Found mixed signer requirements for operation: {auth_service}.{operation_model.name}'
    auth_config = operation_model.auth
    assert_all_requirements_match(auth_config, message)


def assert_all_requirements_match(auth_config, message):
    auth_requirements = set(
        AUTH_TYPE_REQUIREMENTS[auth_type] for auth_type in auth_config
    )
    assert len(auth_requirements) == 1, message


def get_config_file_path(base_path, value):
    if value is None:
        return "file-does-not-exist"

    tmp_config_file_path = base_path / "config"
    tmp_config_file_path.write_text(
        f"[default]\nsigv4a_signing_region_set={value}\n"
    )
    return tmp_config_file_path


def get_environ_mock(
    request,
    env_var_value=None,
    config_file_value=None,
):
    base_path = request.getfixturevalue("tmp_path")
    config_file_path = get_config_file_path(base_path, config_file_value)
    return {
        "AWS_CONFIG_FILE": str(config_file_path),
        "AWS_SIGV4A_SIGNING_REGION_SET": env_var_value,
    }


@pytest.mark.parametrize(
    "client_config, env_var_val, config_file_val, expected",
    [
        (Config(sigv4a_signing_region_set="foo"), "bar", "baz", "foo"),
        (Config(sigv4a_signing_region_set="foo"), None, None, "foo"),
        (None, "bar", "baz", "bar"),
        (None, None, "baz", "baz"),
        (Config(sigv4a_signing_region_set="foo"), None, "baz", "foo"),
        (None, None, None, None),
    ],
)
def test_sigv4a_signing_region_set_config_from_environment(
    client_config, env_var_val, config_file_val, expected, request
):
    environ_mock = get_environ_mock(request, env_var_val, config_file_val)
    with mock.patch('os.environ', environ_mock):
        session = create_session()
        s3 = session.create_client('s3', config=client_config)
        assert s3.meta.config.sigv4a_signing_region_set == expected
