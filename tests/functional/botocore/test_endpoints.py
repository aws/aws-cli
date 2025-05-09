# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore.session import get_session
from botocore.utils import CLIENT_NAME_TO_HYPHENIZED_SERVICE_ID_OVERRIDES

ENDPOINT_PREFIX_OVERRIDE = {
    # entry in endpoints.json -> actual endpoint prefix.
    # The autoscaling-* services actually send requests to the
    # autoscaling service, but they're exposed as separate clients
    # in botocore.
    'autoscaling-plans': 'autoscaling',
    'application-autoscaling': 'autoscaling',
    # For neptune, we send requests to the RDS endpoint.
    'neptune': 'rds',
    'docdb': 'rds',
    # iotevents data endpoints.json and service-2.json don't line up.
    'ioteventsdata': 'data.iotevents',
    'iotsecuredtunneling': 'api.tunneling.iot',
    'iotwireless': 'api.iotwireless',
    'data.iot': 'data-ats.iot',
}

NOT_SUPPORTED_IN_SDK = [
    'mobileanalytics',
    'transcribestreaming',
]


@pytest.fixture(scope="module")
def known_endpoint_prefixes():
    # The entries in endpoints.json are keyed off of the endpoint
    # prefix.  We don't directly have that data, so we have to load
    # every service model and look up its endpoint prefix in its
    # ``metadata`` section.
    session = get_session()
    loader = session.get_component('data_loader')
    known_services = sorted(loader.list_available_services('service-2'))
    return [
        session.get_service_model(service_name).endpoint_prefix
        for service_name in known_services
    ]


def _computed_endpoint_prefixes():
    # This verifies client names match up with data from the endpoints.json
    # file.  We want to verify that every entry in the endpoints.json
    # file corresponds to a client we can construct via
    # session.create_client(...).
    # So first we get a list of all the service names in the endpoints
    # file.
    session = get_session()
    loader = session.get_component('data_loader')
    endpoints = loader.load_data('endpoints')
    # A service can be in multiple partitions so we're using
    # a set here to remove dupes.
    services_in_endpoints_file = set([])
    for partition in endpoints['partitions']:
        for service in partition['services']:
            # There are some services we don't support in the SDK
            # so we don't need to add them to the list of services
            # we need to check.
            if service not in NOT_SUPPORTED_IN_SDK:
                services_in_endpoints_file.add(service)

    # Now we go through every known endpoint prefix in the endpoints.json
    # file and ensure it maps to an endpoint prefix we've seen
    # in a service model.
    for endpoint_prefix in sorted(list(services_in_endpoints_file)):
        # Check for an override where we know that an entry
        # in the endpoints.json actually maps to a different endpoint
        # prefix.
        endpoint_prefix = ENDPOINT_PREFIX_OVERRIDE.get(
            endpoint_prefix, endpoint_prefix
        )
        yield endpoint_prefix


@pytest.mark.validates_models
@pytest.mark.parametrize("endpoint_prefix", _computed_endpoint_prefixes())
def test_endpoint_matches_service(known_endpoint_prefixes, endpoint_prefix):
    # We need to cross check all computed endpoints against our
    # known values in endpoints.json, to ensure everything lines
    # up correctly.
    assert endpoint_prefix in known_endpoint_prefixes


def _available_services():
    # Load the list of available services. The names here represent what
    # will become the client names.
    session = get_session()
    loader = session.get_component('data_loader')
    return sorted(loader.list_available_services('service-2'))


@pytest.mark.validates_models
@pytest.mark.parametrize("service_name", _available_services())
def test_client_name_matches_hyphenized_service_id(service_name):
    """Generates tests for each service to verify that the computed service
    named based on the service id matches the service name used to
    create a client (i.e the directory name in botocore/data)
    unless there is an explicit exception.
    """
    session = get_session()
    service_model = session.get_service_model(service_name)
    computed_name = service_model.service_id.replace(' ', '-').lower()

    # Handle known exceptions where we have renamed the service directory
    # for one reason or another.
    actual_service_name = CLIENT_NAME_TO_HYPHENIZED_SERVICE_ID_OVERRIDES.get(
        service_name, service_name
    )

    err_msg = (
        f"Actual service name `{actual_service_name}` does not match "
        f"expected service name we computed: `{computed_name}`"
    )
    assert computed_name == actual_service_name, err_msg
