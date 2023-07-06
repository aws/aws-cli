# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import json
from pathlib import Path

import pytest

from tests import CLIRunner
from awscli.compat import urlparse


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
                'client_args': test_suite['client_configs'].get(
                    test_case_data['client_config'], {}
                ),
                'config_file_contents': get_config_file_contents(
                    test_case_data['profile'], test_suite
                ),
                'environment': test_suite['environments'].get(
                    test_case_data['environment'], {}
                ),
            },
            marks=pytest.mark.skipif(
               'ignore_configured_endpoint_urls' in (
                    test_suite['client_configs']
                    .get(test_case_data['client_config'], {})
                ),
               reason="Parameter not supported on the command line"
            ),
            id=test_case_data['name']
        )


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


def _normalize_endpoint(url):
    split_endpoint = urlparse.urlsplit(url)
    actual_endpoint = f"{split_endpoint.scheme}://{split_endpoint.netloc}"
    return actual_endpoint


SERVICE_TO_OPERATION = {'s3api': 'list-buckets', 'dynamodb': 'list-tables'}


class TestConfiguredEndpointUrl:
    def assert_endpoint_used(
        self, cli_runner_result, test_case
    ):

        aws_request = cli_runner_result.aws_requests[0]
        assert test_case['expected_endpoint_url'] == \
            _normalize_endpoint(aws_request.http_requests[0].url)

    def _create_command(self, test_case):
        service = test_case['service']
        if test_case['service'] == 's3':
            service = 's3api'

        cmd = [
            service,
            SERVICE_TO_OPERATION[service],
            '--profile',
            f'{test_case["profile"]}'
        ]

        if test_case['client_args'].get('endpoint_url', None):
            cmd.extend([
                    '--endpoint-url',
                    f'{test_case["client_args"]["endpoint_url"]}'
                ]
            )

        return cmd

    @pytest.mark.parametrize('test_case', create_cases())
    def test_resolve_configured_endpoint_url(self, tmp_path, test_case):
        cli_runner = CLIRunner()

        config_filename = tmp_path / 'config'

        with open(config_filename, 'w') as f:
            f.write(test_case['config_file_contents'])
            f.flush()

        cli_runner.env['AWS_CONFIG_FILE'] = config_filename
        cli_runner.env.update(test_case['environment'])
        cli_runner.env.pop('AWS_DEFAULT_REGION')

        result = cli_runner.run(self._create_command(test_case))

        self.assert_endpoint_used(result, test_case)
