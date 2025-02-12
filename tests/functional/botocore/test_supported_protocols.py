# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from botocore.args import PRIORITY_ORDERED_SUPPORTED_PROTOCOLS
from botocore.loaders import Loader
from botocore.session import get_session


def _get_services_models_by_protocols_trait(has_protocol_trait):
    session = get_session()
    service_list = Loader().list_available_services('service-2')
    for service in service_list:
        service_model = session.get_service_model(service)
        if ('protocols' in service_model.metadata) == has_protocol_trait:
            yield service_model


@pytest.mark.validates_models
@pytest.mark.parametrize(
    "service",
    _get_services_models_by_protocols_trait(True),
)
def test_services_with_protocols_trait_have_supported_protocol(service):
    service_supported_protocols = service.metadata.get('protocols', [])
    message = f"No protocols supported for service {service.service_name}"
    assert any(
        protocol in PRIORITY_ORDERED_SUPPORTED_PROTOCOLS
        for protocol in service_supported_protocols
    ), message


@pytest.mark.validates_models
@pytest.mark.parametrize(
    "service",
    _get_services_models_by_protocols_trait(False),
)
def test_services_without_protocols_trait_have_supported_protocol(service):
    message = f"Service protocol not supported for {service.service_name}"
    assert (
        service.metadata.get('protocol')
        in PRIORITY_ORDERED_SUPPORTED_PROTOCOLS
    ), message