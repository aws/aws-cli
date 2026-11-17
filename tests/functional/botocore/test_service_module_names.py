# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import copy

import pytest
from botocore.loaders import Loader
from botocore.model import ServiceModel
from botocore.service_module_names import SERVICE_MODULE_NAMES
from botocore.utils import get_service_module_name

LOADER = Loader()
DOCGEN_KEYS = ('serviceFullName', 'serviceAbbreviation')
SENTINEL = 'AWS Renamed Service'


def _all_service_models():
    for service_name in LOADER.list_available_services('service-2'):
        for api_version in LOADER.list_api_versions(service_name, 'service-2'):
            yield service_name, api_version


def _load(service_name, api_version):
    description = LOADER.load_service_model(
        service_name, 'service-2', api_version
    )
    return ServiceModel(description, service_name)


def _with_docgen_sentinels(service_model):
    description = copy.deepcopy(service_model._service_description)
    for key in DOCGEN_KEYS:
        description['metadata'][key] = SENTINEL
    return ServiceModel(description, service_model.service_name)


@pytest.mark.parametrize(
    'service_name, api_version', list(_all_service_models())
)
def test_module_name_ignores_docgen_ids(service_name, api_version):
    model = _load(service_name, api_version)
    expected = get_service_module_name(model)
    actual = get_service_module_name(_with_docgen_sentinels(model))
    assert actual == expected, (
        f'{service_name}/{api_version}: module name changed from '
        f'{expected!r} to {actual!r} when documentation ids changed'
    )


@pytest.mark.parametrize(
    'service_name, api_version', list(_all_service_models())
)
def test_every_shipped_model_has_service_id(service_name, api_version):
    model = _load(service_name, api_version)
    assert model.metadata.get('serviceId'), (
        f'{service_name}/{api_version} has no serviceId; the module name '
        f'would fall back to the model directory name'
    )


def test_table_keys_are_shipped_service_ids():
    shipped = {
        _load(s, v).metadata.get('serviceId') for s, v in _all_service_models()
    }
    unknown = set(SERVICE_MODULE_NAMES) - shipped
    assert not unknown, f'Table entries for unknown serviceIds: {unknown}'


def test_no_two_services_share_module_name():
    service_ids_by_name = {}
    for service_name, api_version in _all_service_models():
        model = _load(service_name, api_version)
        name = get_service_module_name(model)
        service_ids_by_name.setdefault(name, set()).add(
            model.metadata['serviceId']
        )
    collisions = {
        name: sorted(service_ids)
        for name, service_ids in service_ids_by_name.items()
        if len(service_ids) > 1
    }
    assert not collisions, f'Module name collisions: {collisions}'
