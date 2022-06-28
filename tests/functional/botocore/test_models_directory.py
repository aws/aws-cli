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

import botocore.session


@pytest.fixture
def loader():
    return botocore.session.Session().get_component('data_loader')


def _available_services():
    return botocore.session.Session().get_available_services()


def test_models_contains_no_examples_files(loader):
    assert loader.list_available_services('examples-1') == []


@pytest.mark.parametrize("service", _available_services())
def test_models_contains_single_api_version_per_service(service, loader):
    assert len(loader.list_api_versions(service, 'service-2')) == 1
