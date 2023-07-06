# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import json
from pathlib import Path
from unittest import mock

import pytest

import botocore.configprovider
import botocore.utils
from botocore.compat import urlsplit
from botocore.config import Config
from tests import ClientHTTPStubber

ENDPOINT_TESTDATA_FILE = Path(__file__).parent / "profile-tests.json"


def dict_to_ini_section(ini_dict, section_header):
    section_str = f'[{section_header}]\n'
    for key, value in ini_dict.items():
        if isinstance(value, dict):
            section_str += f"{key} =\n"
            for new_key, new_value in value.items():
                section_str += f"  {new_key}={new_value}\n"
        else:
            section_str += f"{key}={value}\n"
    return section_str + "\n"


def create_cases():
    with open(ENDPOINT_TESTDATA_FILE) as f:
        test_suite = json.load(f)['testSuites'][0]

    for test_case_data in test_suite['endpointUrlTests']:
        yield pytest.param(
            {
                'service': test_case_data['service'],
                'profile': test_case_data['profile'],
                'expected_endpoint_url': test_case_data['output'][
                    'endpointUrl'
                ],
                'client_args': get_create_client_args(
                    test_suite['client_configs'].get(
                        test_case_data['client_config'], {}
                    )
                ),
                'config_file_contents': get_config_file_contents(
                    test_case_data['profile'], test_suite
                ),
                'environment': test_suite['environments'].get(
                    test_case_data['environment'], {}
                ),
            },
            id=test_case_data['name'],
        )


def get_create_client_args(test_case_client_config):
    create_client_args = {}

    if 'endpoint_url' in test_case_client_config:
        create_client_args['endpoint_url'] = test_case_client_config[
            'endpoint_url'
        ]

    if 'ignore_configured_endpoint_urls' in test_case_client_config:
        create_client_args['config'] = Config(
            ignore_configured_endpoint_urls=test_case_client_config[
                'ignore_configured_endpoint_urls'
            ]
        )

    return create_client_args


def get_config_file_contents(profile_name, test_suite):
    profile = test_suite['profiles'][profile_name]

    profile_str = dict_to_ini_section(
        profile,
        section_header=f"profile {profile_name}",
    )

    services_section_name = profile.get('services', None)

    if services_section_name is None:
        return profile_str

    services_section = test_suite['services'][services_section_name]

    service_section_str = dict_to_ini_section(
        services_section,
        section_header=f'services {services_section_name}',
    )

    return profile_str + service_section_str


@pytest.fixture
def client_creator(tmp_path):
    tmp_config_file_path = tmp_path / 'config'
    environ = {'AWS_CONFIG_FILE': str(tmp_config_file_path)}

    def _do_create_client(
        service,
        profile,
        client_args=None,
        config_file_contents=None,
        environment=None,
    ):
        environ.update(environment)
        with open(tmp_config_file_path, 'w') as f:
            f.write(config_file_contents)
            f.flush()

        return botocore.session.Session(profile=profile).create_client(
            service, **client_args
        )

    with mock.patch('os.environ', environ):
        yield _do_create_client


def _normalize_endpoint(url):
    split_endpoint = urlsplit(url)
    actual_endpoint = f"{split_endpoint.scheme}://{split_endpoint.netloc}"
    return actual_endpoint


def assert_client_endpoint_url(client, expected_endpoint_url):
    assert client.meta.endpoint_url == expected_endpoint_url


def assert_endpoint_url_used_for_operation(
    client, expected_endpoint_url, operation, params
):
    http_stubber = ClientHTTPStubber(client)
    http_stubber.start()
    http_stubber.add_response()

    # Call an operation on the client
    getattr(client, operation)(**params)

    assert (
        _normalize_endpoint(http_stubber.requests[0].url)
        == expected_endpoint_url
    )


def _known_service_names_and_ids():
    my_session = botocore.session.get_session()
    loader = my_session.get_component('data_loader')
    available_services = loader.list_available_services('service-2')

    result = []
    for service_name in available_services:
        model = my_session.get_service_model(service_name)
        result.append((model.service_name, model.service_id))
    return sorted(result)


SERVICE_TO_OPERATION = {'s3': 'list_buckets', 'dynamodb': 'list_tables'}


@pytest.mark.parametrize("test_case", create_cases())
def test_resolve_configured_endpoint_url(test_case, client_creator):
    client = client_creator(
        service=test_case['service'],
        profile=test_case['profile'],
        client_args=test_case['client_args'],
        config_file_contents=test_case['config_file_contents'],
        environment=test_case['environment'],
    )

    assert_endpoint_url_used_for_operation(
        client=client,
        expected_endpoint_url=test_case['expected_endpoint_url'],
        operation=SERVICE_TO_OPERATION[test_case['service']],
        params={},
    )


@pytest.mark.parametrize(
    'service_name,service_id', _known_service_names_and_ids()
)
def test_expected_service_env_var_name_is_respected(
    service_name, service_id, client_creator
):
    transformed_service_id = service_id.replace(' ', '_').upper()

    client = client_creator(
        service=service_name,
        profile='default',
        client_args={},
        config_file_contents=(
            '[profile default]\n'
            'aws_access_key_id=123\n'
            'aws_secret_access_key=456\n'
            'region=fake-region-10\n'
        ),
        environment={
            f'AWS_ENDPOINT_URL_{transformed_service_id}': 'https://endpoint-override'
        },
    )

    assert_client_endpoint_url(
        client=client, expected_endpoint_url='https://endpoint-override'
    )


@pytest.mark.parametrize(
    'service_name,service_id', _known_service_names_and_ids()
)
def test_expected_service_config_section_name_is_respected(
    service_name, service_id, client_creator
):
    transformed_service_id = service_id.replace(' ', '_').lower()

    client = client_creator(
        service=service_name,
        profile='default',
        client_args={},
        config_file_contents=(
            f'[profile default]\n'
            f'services=my-services\n'
            f'aws_access_key_id=123\n'
            f'aws_secret_access_key=456\n'
            f'region=fake-region-10\n\n'
            f'[services my-services]\n'
            f'{transformed_service_id} = \n'
            f'  endpoint_url = https://endpoint-override\n\n'
        ),
        environment={},
    )

    assert_client_endpoint_url(
        client=client, expected_endpoint_url='https://endpoint-override'
    )
