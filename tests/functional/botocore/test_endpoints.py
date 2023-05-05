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


SERVICE_RENAMES = {
    # Actual service name we use -> Allowed computed service name.
    'alexaforbusiness': 'alexa-for-business',
    'apigateway': 'api-gateway',
    'application-autoscaling': 'application-auto-scaling',
    'appmesh': 'app-mesh',
    'autoscaling': 'auto-scaling',
    'autoscaling-plans': 'auto-scaling-plans',
    'ce': 'cost-explorer',
    'cloudhsmv2': 'cloudhsm-v2',
    'cloudsearchdomain': 'cloudsearch-domain',
    'cognito-idp': 'cognito-identity-provider',
    'config': 'config-service',
    'cur': 'cost-and-usage-report-service',
    'datapipeline': 'data-pipeline',
    'directconnect': 'direct-connect',
    'devicefarm': 'device-farm',
    'discovery': 'application-discovery-service',
    'dms': 'database-migration-service',
    'ds': 'directory-service',
    'dynamodbstreams': 'dynamodb-streams',
    'elasticbeanstalk': 'elastic-beanstalk',
    'elastictranscoder': 'elastic-transcoder',
    'elb': 'elastic-load-balancing',
    'elbv2': 'elastic-load-balancing-v2',
    'es': 'elasticsearch-service',
    'events': 'eventbridge',
    'globalaccelerator': 'global-accelerator',
    'iot-data': 'iot-data-plane',
    'iot-jobs-data': 'iot-jobs-data-plane',
    'iot1click-devices': 'iot-1click-devices-service',
    'iot1click-projects': 'iot-1click-projects',
    'iotevents-data': 'iot-events-data',
    'iotevents': 'iot-events',
    'iotwireless': 'iot-wireless',
    'kinesisanalytics': 'kinesis-analytics',
    'kinesisanalyticsv2': 'kinesis-analytics-v2',
    'kinesisvideo': 'kinesis-video',
    'lex-models': 'lex-model-building-service',
    'lexv2-models': 'lex-models-v2',
    'lex-runtime': 'lex-runtime-service',
    'lexv2-runtime': 'lex-runtime-v2',
    'logs': 'cloudwatch-logs',
    'machinelearning': 'machine-learning',
    'marketplacecommerceanalytics': 'marketplace-commerce-analytics',
    'marketplace-entitlement': 'marketplace-entitlement-service',
    'meteringmarketplace': 'marketplace-metering',
    'mgh': 'migration-hub',
    'resourcegroupstaggingapi': 'resource-groups-tagging-api',
    'route53': 'route-53',
    'route53domains': 'route-53-domains',
    's3control': 's3-control',
    'sdb': 'simpledb',
    'secretsmanager': 'secrets-manager',
    'serverlessrepo': 'serverlessapplicationrepository',
    'servicecatalog': 'service-catalog',
    'servicecatalog-appregistry': 'service-catalog-appregistry',
    'stepfunctions': 'sfn',
    'storagegateway': 'storage-gateway',
}


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
        endpoint_prefix = ENDPOINT_PREFIX_OVERRIDE.get(endpoint_prefix,
                                                       endpoint_prefix)
        yield endpoint_prefix


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


@pytest.mark.parametrize("service_name", _available_services())
def test_service_name_matches_endpoint_prefix(service_name):
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
    actual_service_name = SERVICE_RENAMES.get(service_name, service_name)

    err_msg = (
        f"Actual service name `{actual_service_name}` does not match "
        f"expected service name we computed: `{computed_name}`"
    )
    assert computed_name == actual_service_name, err_msg


_S3_ALLOWED_PSEUDO_FIPS_REGIONS = [
    'fips-accesspoint-ca-central-1',
    'fips-accesspoint-us-east-1',
    'fips-accesspoint-us-east-2',
    'fips-accesspoint-us-west-1',
    'fips-accesspoint-us-west-2',
    'fips-accesspoint-us-gov-east-1',
    'fips-accesspoint-us-gov-west-1',
    'fips-us-gov-west-1',
    'fips-us-gov-east-1',
    'fips-ca-central-1',
    'fips-us-east-1',
    'fips-us-east-2',
    'fips-us-west-1',
    'fips-us-west-2',
]


def _s3_region_names():
    session = get_session()
    loader = session.get_component('data_loader')
    endpoints = loader.load_data('endpoints')

    for partition in endpoints['partitions']:
        s3_service = partition['services'].get('s3', {})
        for region_name in s3_service.get('endpoints', []):
            yield region_name.lower()


@pytest.mark.parametrize("region_name", _s3_region_names())
def test_no_s3_fips_regions(region_name):
    # Fail if additional FIPS pseudo-regions are added to S3.
    # This may be removed once proper support is implemented for FIPS in S3.
    if region_name in _S3_ALLOWED_PSEUDO_FIPS_REGIONS:
        return

    err_msg = (
        'New S3 FIPS pseudo-region added: "{region_name}". '
        'FIPS has compliancy requirements that may not be met in all cases '
        'for S3 clients due to the custom endpoint resolution and '
        'construction logic.'
    )

    assert 'fips' not in region_name, err_msg
