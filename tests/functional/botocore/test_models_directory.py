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
import os

import pytest

import awscli.botocore.session


@pytest.fixture
def loader():
    return awscli.botocore.session.Session().get_component('data_loader')


def _available_services():
    return awscli.botocore.session.Session().get_available_services()


@pytest.mark.parametrize("service", _available_services())
def test_models_contain_only_known_file_types(service, loader):
    known_types = {
        "completions-1",
        "endpoint-rule-set-1",
        "paginators-1",
        "service-2",
        "waiters-2",
    }
    api_version = loader.determine_latest_version(service, "service-2")
    service_dir = os.path.join(loader.BUILTIN_DATA_PATH, service, api_version)
    for model_file in os.listdir(service_dir):
        assert model_file.split(".")[0] in known_types


@pytest.mark.parametrize("service", _available_services())
def test_models_contains_single_api_version_per_service(service, loader):
    assert len(loader.list_api_versions(service, 'service-2')) == 1


def test_models_contain_no_blocklisted_services():
    blocklisted_services = ['transcribe-streaming', 'sms-voice']
    services = _available_services()
    for service in blocklisted_services:
        assert service not in services


@pytest.mark.parametrize(
    ("service", "type_name"), [("autoscaling", "waiters-2")]
)
def test_service_contains_no_unexpected_file_type(service, type_name, loader):
    assert service not in loader.list_available_services(type_name)


def test_dbsnapshotcompleted_waiter_in_rds(loader):
    data = loader.load_service_model('rds', 'waiters-2')
    assert data['waiters'].get('DBSnapshotCompleted') is not None
