# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.botocore.session import get_session

_H2_REQUIRED = object()
# Service names to list of known HTTP 2 operations
_KNOWN_SERVICES = {
    'qbusiness': ['Chat'],
    'kinesis': ['SubscribeToShard'],
    'lexv2-runtime': ['StartConversation'],
    # Added only to keep a record of this feature being incompatible
    'bedrock-runtime': ['InvokeModelWithBidirectionalStream'],
}


def _all_test_cases():
    session = get_session()
    loader = session.get_component('data_loader')

    services = loader.list_available_services('service-2')
    h2_services = []
    h2_operations = []

    for service in services:
        service_model = session.get_service_model(service)
        h2_config = service_model.metadata.get('protocolSettings', {}).get(
            'h2'
        )
        if h2_config == 'required':
            h2_services.append(service)
        elif h2_config == 'eventstream':
            for operation in service_model.operation_names:
                operation_model = service_model.operation_model(operation)
                if operation_model.has_event_stream_output:
                    h2_operations.append([service, operation])

    return h2_services, h2_operations


H2_SERVICES, H2_OPERATIONS = _all_test_cases()


@pytest.mark.validates_models
@pytest.mark.parametrize("h2_service", H2_SERVICES)
def test_all_uses_of_h2_are_known(h2_service):
    # Validates that a service that requires HTTP 2 for all operations is known
    message = f'Found unknown HTTP 2 service: {h2_service}'
    assert _KNOWN_SERVICES.get(h2_service) is _H2_REQUIRED, message


@pytest.mark.validates_models
@pytest.mark.parametrize("h2_service, operation", H2_OPERATIONS)
def test_all_h2_operations_are_known(h2_service, operation):
    # Validates that an operation that requires HTTP 2 is known
    known_operations = _KNOWN_SERVICES.get(h2_service, [])
    message = f'Found unknown HTTP 2 operation: {h2_service}.{operation}'
    assert operation in known_operations, message
