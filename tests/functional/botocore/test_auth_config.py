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
from tests import create_session, mock

# In the future, a service may have a list of credentials requirements where one
# signature may fail and others may succeed. e.g. a service may want to use bearer
# auth but fall back to sigv4 if a token isn't available. There's currently no way to do
# this in botocore, so this test ensures we handle this gracefully when the need arises.


# The dictionary's value here needs to be hashable to be added to the set below; any
# new auth types with multiple requirements should be added in a comma-separated list
AUTH_TYPE_REQUIREMENTS = {
    'aws.auth#sigv4': 'credentials',
    'aws.auth#sigv4a': 'credentials',
    'smithy.api#httpBearerAuth': 'bearer_token',
    'smithy.api#noAuth': 'none',
}


def _all_test_cases():
    session = create_session()
    loader = session.get_component('data_loader')

    services = loader.list_available_services('service-2')
    auth_services = []
    auth_operations = []

    for service in services:
        service_model = session.get_service_model(service)
        auth_config = service_model.metadata.get('auth', {})
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


@pytest.mark.parametrize(
    "client_config_val, env_var_val, config_file_val, expected",
    [
        ("foo", "bar", "baz", "foo"),
        ("foo", None, None, "foo"),
        (None, "foo", "bar", "foo"),
        (None, None, "foo", "foo"),
        ("foo", None, "bar", "foo"),
        (None, None, None, None),
    ],
)
def test_sigv4a_signing_region_set_config_from_environment(
    client_config_val, env_var_val, config_file_val, expected, tmp_path
):
    if config_file_val:
        tmp_config_file_path = tmp_path / 'config'
        tmp_config_file_path.write_text(
            f'[default]\nsigv4a_signing_region_set={config_file_val}\n'
        )
        environ = {'AWS_CONFIG_FILE': str(tmp_config_file_path)}
    else:
        environ = {'AWS_CONFIG_FILE': "file-does-not-exist"}

    if env_var_val:
        environ['AWS_SIGV4A_SIGNING_REGION_SET'] = env_var_val

    if client_config_val:
        config = Config(sigv4a_signing_region_set=client_config_val)
    else:
        config = Config()

    with mock.patch('os.environ', environ):
        session = create_session()
        session.config_filename = 'no-exist-foo'
        s3 = session.create_client('s3', config=config)
        assert s3.meta.config.sigv4a_signing_region_set == expected