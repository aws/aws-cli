"""Smoke tests to verify basic communication to all AWS services.

If you want to control what services/regions are used you can
also provide two separate env vars:

    * AWS_SMOKE_TEST_REGION - The region used to create clients.
    * AWS_SMOKE_TEST_SERVICES - A CSV list of service names to test.

Otherwise, the ``REGION`` variable specifies the default region
to use and all the services in SMOKE_TESTS/ERROR_TESTS will be tested.

"""
import os
import mock
from pprint import pformat
import warnings
import logging

import pytest

from tests import ClientHTTPStubber
from botocore import xform_name
import botocore.session
from botocore.client import ClientError
from botocore.endpoint import Endpoint
from botocore.exceptions import ConnectionClosedError


# Mapping of service -> api calls to try.
# Each api call is a dict of OperationName->params.
# Empty params means that the operation will be called with no params.  This is
# used as a quick verification that we can successfully make calls to services.
SMOKE_TESTS = {
 'acm': {'ListCertificates': {}},
 'apigateway': {'GetRestApis': {}},
 'application-autoscaling': {
     'DescribeScalableTargets': {
         'ServiceNamespace': 'ecs'
     }},
 'autoscaling': {'DescribeAccountLimits': {},
                 'DescribeAdjustmentTypes': {}},
 'cloudformation': {'DescribeStacks': {},
                    'ListStacks': {}},
 'cloudfront': {'ListDistributions': {},
                'ListStreamingDistributions': {}},
 'cloudhsmv2': {'DescribeBackups': {}},
 'cloudsearch': {'DescribeDomains': {},
                 'ListDomainNames': {}},
 'cloudtrail': {'DescribeTrails': {}},
 'cloudwatch': {'ListMetrics': {}},
 'codecommit': {'ListRepositories': {}},
 'codedeploy': {'ListApplications': {}},
 'codepipeline': {'ListActionTypes': {}},
 'cognito-identity': {'ListIdentityPools': {'MaxResults': 1}},
 'cognito-sync': {'ListIdentityPoolUsage': {}},
 'config': {'DescribeDeliveryChannels': {}},
 'datapipeline': {'ListPipelines': {}},
 'devicefarm': {'ListProjects': {}},
 'directconnect': {'DescribeConnections': {}},
 'ds': {'DescribeDirectories': {}},
 'dynamodb': {'ListTables': {}},
 'dynamodbstreams': {'ListStreams': {}},
 'ec2': {'DescribeRegions': {},
         'DescribeInstances': {}},
  'ecr': {'DescribeRepositories': {}},
 'ecs': {'DescribeClusters': {}},
 'elasticache': {'DescribeCacheClusters': {}},
 'elasticbeanstalk': {'DescribeApplications': {}},
 'elastictranscoder': {'ListPipelines': {}},
 'elb': {'DescribeLoadBalancers': {}},
 'emr': {'ListClusters': {}},
 'es': {'ListDomainNames': {}},
 'events': {'ListRules': {}},
  'firehose': {'ListDeliveryStreams': {}},
 'gamelift': {'ListBuilds': {}},
 'glacier': {'ListVaults': {}},
 'iam': {'ListUsers': {}},
 # Does not work with session credentials so
 # importexport tests are not run.
 #'importexport': {'ListJobs': {}},
 'importexport': {},
 'inspector': {'DescribeCrossAccountAccessRole': {}},
 'iot': {'DescribeEndpoint': {}},
 'kinesis': {'ListStreams': {}},
 'kms': {'ListKeys': {}},
 'lambda': {'ListFunctions': {}},
 'logs': {'DescribeLogGroups': {}},
 'opsworks': {'DescribeStacks': {}},
 'rds': {'DescribeDBInstances': {}},
 'redshift': {'DescribeClusters': {}},
 'route53': {'ListHostedZones': {}},
 'route53domains': {'ListDomains': {}},
 's3': {'ListBuckets': {}},
 'sdb': {'ListDomains': {}},
 'ses': {'ListIdentities': {}},
 'shield': {'GetSubscriptionState': {}},
 'sns': {'ListTopics': {}},
 'sqs': {'ListQueues': {}},
 'ssm': {'ListDocuments': {}},
 'storagegateway': {'ListGateways': {}},
 # sts tests would normally go here, but
 # there aren't any calls you can make when
 # using session credentials so we don't run any
 # sts tests.
 'sts': {},
 #'sts': {'GetSessionToken': {}},
 # Subscription needed for support API calls.
 'support': {},
 'swf': {'ListDomains': {'registrationStatus': 'REGISTERED'}},
 'waf': {'ListWebACLs': {'Limit': 1}},
 'workspaces': {'DescribeWorkspaces': {}},
}


# Same thing as the SMOKE_TESTS hash above, except these verify
# that we get an error response back from the server because
# we've sent invalid params.
ERROR_TESTS = {
    'apigateway': {'GetRestApi': {'restApiId': 'fake-id'}},
    'application-autoscaling': {
        'DescribeScalableTargets': {
            'ServiceNamespace': 'fake-service-namespace'
        }},
    'autoscaling': {'CreateLaunchConfiguration': {
        'LaunchConfigurationName': 'foo',
        'ImageId': 'ami-12345678',
        'InstanceType': 'm1.small',
        }},
    'cloudformation': {'CreateStack': {
        'StackName': 'fake',
        'TemplateURL': 'http://s3.amazonaws.com/foo/bar',
        }},
    'cloudfront': {'GetDistribution': {'Id': 'fake-id'}},
    'cloudhsmv2': {'ListTags': {'ResourceId': 'fake-id'}},
    'cloudsearch': {'DescribeIndexFields': {'DomainName': 'fakedomain'}},
    'cloudtrail': {'DeleteTrail': {'Name': 'fake-trail'}},
    'cloudwatch': {'SetAlarmState': {
        'AlarmName': 'abc',
        'StateValue': 'mno',
        'StateReason': 'xyz',
        }},
    'logs': {'GetLogEvents': {'logGroupName': 'a', 'logStreamName': 'b'}},
    'codecommit': {'ListBranches': {'repositoryName': 'fake-repo'}},
    'codedeploy': {'GetDeployment': {'deploymentId': 'fake-id'}},
    'codepipeline': {'GetPipeline': {'name': 'fake-pipeline'}},
    'cognito-identity': {'DescribeIdentityPool': {'IdentityPoolId': 'fake'}},
    'cognito-sync': {'DescribeIdentityPoolUsage': {'IdentityPoolId': 'fake'}},
    'config': {
        'GetResourceConfigHistory': {'resourceType': '', 'resourceId': 'fake'},
        },
    'datapipeline': {'GetPipelineDefinition': {'pipelineId': 'fake'}},
    'devicefarm': {'GetDevice': {'arn': 'arn:aws:devicefarm:REGION::device:f'}},
    'directconnect': {'DescribeConnections': {'connectionId': 'fake'}},
    'ds': {'CreateDirectory': {'Name': 'n', 'Password': 'p', 'Size': '1'}},
    'dynamodb': {'DescribeTable': {'TableName': 'fake'}},
    'dynamodbstreams': {'DescribeStream': {'StreamArn': 'x'*37}},
    'ec2': {'DescribeInstances': {'InstanceIds': ['i-12345678']}},
    'ecs': {'StopTask': {'task': 'fake'}},
    'efs': {'DeleteFileSystem': {'FileSystemId': 'fake'}},
    'elasticache': {'DescribeCacheClusters': {'CacheClusterId': 'fake'}},
    'elasticbeanstalk': {
        'DescribeEnvironmentResources': {'EnvironmentId': 'x'},
        },
    'elb': {'DescribeLoadBalancers': {'LoadBalancerNames': ['fake']}},
    'elastictranscoder': {'ReadJob': {'Id': 'fake'}},
    'emr': {'DescribeCluster': {'ClusterId': 'fake'}},
    'es': {'DescribeElasticsearchDomain': {'DomainName': 'not-a-domain'}},
    'gamelift': {'DescribeBuild': {'BuildId': 'fake-build-id'}},
    'glacier': {'ListVaults': {'accountId': 'fake'}},
    'iam': {'GetUser': {'UserName': 'fake'}},
    'kinesis': {'DescribeStream': {'StreamName': 'fake'}},
    'kms': {'GetKeyPolicy': {'KeyId': 'fake', 'PolicyName': 'fake'}},
    'lambda': {'Invoke': {'FunctionName': 'fake'}},
    'opsworks': {'DescribeLayers': {'StackId': 'fake'}},
    'rds': {'DescribeDBInstances': {'DBInstanceIdentifier': 'fake'}},
    'redshift': {'DescribeClusters': {'ClusterIdentifier': 'fake'}},
    'route53': {'GetHostedZone': {'Id': 'fake'}},
    'route53domains': {'GetDomainDetail': {'DomainName': 'fake'}},
    's3': {'ListObjects': {'Bucket': 'thisbucketdoesnotexistasdf'}},
    'ses': {'VerifyEmailIdentity': {'EmailAddress': 'fake'}},
    'sdb': {'CreateDomain': {'DomainName': ''}},
    'sns': {
        'ConfirmSubscription': {'TopicArn': 'a', 'Token': 'b'},
        'Publish': {'Message': 'hello', 'TopicArn': 'fake'},
        },
    'sqs': {'GetQueueUrl': {'QueueName': 'fake'}},
    'ssm': {'GetDocument': {'Name': 'fake'}},
    'storagegateway': {'ListVolumes': {'GatewayARN': 'x'*50}},
    'sts': {'GetFederationToken': {'Name': 'fake', 'Policy': 'fake'}},
    'support': {'CreateCase': {
        'subject': 'x',
        'communicationBody': 'x',
        'categoryCode': 'x',
        'serviceCode': 'x',
        'severityCode': 'low',
        }},
    'swf': {'DescribeDomain': {'name': 'fake'}},
    'waf': {'GetWebACL': {'WebACLId': 'fake'}},
    'workspaces': {'DescribeWorkspaces': {'DirectoryId': 'fake-directory-id'}},
}

REGION = 'us-east-1'
REGION_OVERRIDES = {
    'devicefarm': 'us-west-2',
    'efs': 'us-west-2',
    'inspector': 'us-west-2',
}
MAX_RETRIES = 8
logger = logging.getLogger(__name__)


def _get_client(session, service):
    if os.environ.get('AWS_SMOKE_TEST_REGION', ''):
        region_name = os.environ['AWS_SMOKE_TEST_REGION']
    else:
        region_name = REGION_OVERRIDES.get(service, REGION)
    client = session.create_client(service, region_name=region_name)
    client.meta.events.register_first('needs-retry.*.*', retry_handler)
    return client


def retry_handler(response, attempts, **kwargs):
    if response is not None:
        _, parsed = response
        code = parsed.get('Error', {}).get('Code')
        # Catch ThrottleException, Throttling.
        is_throttle_error = code is not None and 'throttl' in code.lower()
        if is_throttle_error and attempts <= MAX_RETRIES:
            # We want the exponential behavior with a fixed 10 second
            # minimum, e.g. 11, 12, 14, 18, 26.  With a max retries of 8,
            # this is about 7-8 minutes total we'll retry.
            retry_delay = (2 ** (attempts - 1)) + 10
            logger.debug("Using custom retry delay of: %s", retry_delay)
            return retry_delay


def _list_services(dict_entries):
    # List all services in the provided dict_entry.
    # If the AWS_SMOKE_TEST_SERVICES is provided,
    # it's a comma separated list of services you can provide
    # if you only want to run the smoke tests for certain services.
    if 'AWS_SMOKE_TEST_SERVICES' not in os.environ:
        return dict_entries.keys()
    else:
        wanted_services = os.environ.get(
            'AWS_SMOKE_TEST_SERVICES', '').split(',')
        return [key for key in dict_entries if key in wanted_services]


@pytest.fixture()
def botocore_session():
    return botocore.session.get_session()


def _smoke_tests():
    for service_name in _list_services(SMOKE_TESTS):
        for operation_name in SMOKE_TESTS[service_name]:
            kwargs = SMOKE_TESTS[service_name][operation_name]
            yield service_name, operation_name, kwargs


def _error_tests():
    for service_name in _list_services(ERROR_TESTS):
        for operation_name in ERROR_TESTS[service_name]:
            kwargs = ERROR_TESTS[service_name][operation_name]
            yield service_name, operation_name, kwargs


@pytest.mark.parametrize("service_name, operation_name, kwargs", _smoke_tests())
def test_can_make_request_with_client(
    botocore_session, service_name, operation_name, kwargs
):
    # Same as test_can_make_request, but with Client objects
    # instead of service/operations.
    client = _get_client(botocore_session, service_name)
    method = getattr(client, xform_name(operation_name))
    with warnings.catch_warnings(record=True) as caught_warnings:
        response = method(**kwargs)
        err_msg = f"Warnings were emitted during smoke test: {caught_warnings}"
        assert len(caught_warnings) == 0, err_msg
        assert 'Errors' not in response


@pytest.mark.parametrize("service_name, operation_name, kwargs", _error_tests())
def test_can_make_request_and_understand_errors_with_client(
    botocore_session, service_name, operation_name, kwargs
):
    client = _get_client(botocore_session, service_name)
    method = getattr(client, xform_name(operation_name))
    with pytest.raises(ClientError):
        response = method(**kwargs)


@pytest.mark.parametrize("service_name, operation_name, kwargs", _smoke_tests())
def test_client_can_retry_request_properly(
    botocore_session, service_name, operation_name, kwargs
):
    client = _get_client(botocore_session, service_name)
    operation = getattr(client, xform_name(operation_name))
    exception = ConnectionClosedError(endpoint_url='https://mock.eror')
    with ClientHTTPStubber(client, strict=False) as http_stubber:
        http_stubber.responses.append(exception)
        try:
            response = operation(**kwargs)
        except ClientError as e:
            assert False, ('Request was not retried properly, '
                           'received error:\n%s' % pformat(e))
        # Ensure we used the stubber as we're not using it in strict mode
        assert len(http_stubber.responses) == 0, 'Stubber was not used!'
