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
import pytest

from botocore.loaders import Loader

LOADER = Loader()
AVAILABLE_SERVICES = LOADER.list_available_services(type_name='service-2')


def _endpoint_rule_set_cases():
    for service_name in AVAILABLE_SERVICES:
        versions = LOADER.list_api_versions(service_name, 'service-2')
        for version in versions:
            yield service_name, version


# endpoint tests validations are included in
# tests/functional/test_endpoint_rulesets.py
@pytest.mark.parametrize(
    "service_name, version",
    _endpoint_rule_set_cases(),
)
def test_all_endpoint_rule_sets_exist(service_name, version):
    """Tests the existence of endpoint-rule-set-1.json for each service
    and verifies that content is present."""
    type_name = 'endpoint-rule-set-1'
    data = LOADER.load_service_model(service_name, type_name, version)
    assert len(data['rules']) >= 1


def test_partitions_exists():
    """Tests the existence of partitions.json and verifies that content is present."""
    data = LOADER.load_data('partitions')
    assert len(data['partitions']) >= 4
