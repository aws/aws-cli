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
from botocore.session import get_session


def _multi_protocol_test_cases():
    session = get_session()
    loader = session.get_component('data_loader')
    services = loader.list_available_services('service-2')
    multi_protocol_services = []
    supported_protocols = []
    for service in services:
        service_model = session.get_service_model(service)
        if 'protocols' in service_model.metadata:
            multi_protocol_services.append(service)
            supported_protocols.append(
                service_model.metadata.get('protocols', [])
            )
    return list(zip(multi_protocol_services, supported_protocols))


def _single_protocol_test_cases():
    session = get_session()
    loader = session.get_component('data_loader')
    services = loader.list_available_services('service-2')
    single_protocol_services = []
    supported_protocol = []
    for service in services:
        service_model = session.get_service_model(service)
        if 'protocols' not in service_model.metadata:
            single_protocol_services.append(service)
            supported_protocol.append(service_model.metadata.get('protocol'))
    return list(zip(single_protocol_services, supported_protocol))


@pytest.mark.validates_models
@pytest.mark.parametrize(
    "service_name, supported_protocols",
    _multi_protocol_test_cases(),
)
def test_services_with_protocols_trait_have_supported_protocol(
    service_name, supported_protocols
):
    message = (
        f"No protocols supported for service {service_name}\n"
        f"Target={service_name}"
    )
    assert any(
        protocol in PRIORITY_ORDERED_SUPPORTED_PROTOCOLS
        for protocol in supported_protocols
    ), message


@pytest.mark.validates_models
@pytest.mark.parametrize(
    "service_name, supported_protocol",
    _single_protocol_test_cases(),
)
def test_services_without_protocols_trait_have_supported_protocol(
    service_name, supported_protocol
):
    message = (
        f"Service protocol not supported for {service_name}\n"
        f"Target={service_name}"
    )
    assert supported_protocol in PRIORITY_ORDERED_SUPPORTED_PROTOCOLS, message
