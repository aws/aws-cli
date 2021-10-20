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
import string

import pytest
import jmespath
from jmespath.exceptions import JMESPathError

import botocore.session


KNOWN_PAGE_KEYS = set(
    ['input_token', 'py_input_token', 'output_token', 'result_key',
     'limit_key', 'more_results', 'non_aggregate_keys'])
MEMBER_NAME_CHARS = set(string.ascii_letters + string.digits)
# The goal here should be to remove all of these by updating the paginators
# to reference all the extra output keys. Nothing should ever be added to this
# list, it represents all the current released paginators that fail this test.
KNOWN_EXTRA_OUTPUT_KEYS = [
    'alexaforbusiness.SearchUsers.TotalCount',
    'alexaforbusiness.SearchProfiles.TotalCount',
    'alexaforbusiness.SearchSkillGroups.TotalCount',
    'alexaforbusiness.SearchDevices.TotalCount',
    'alexaforbusiness.SearchRooms.TotalCount',
    'apigateway.GetApiKeys.warnings',
    'apigateway.GetUsage.usagePlanId',
    'apigateway.GetUsage.startDate',
    'apigateway.GetUsage.endDate',
    'athena.GetQueryResults.ResultSet',
    'cloudfront.ListCloudFrontOriginAccessIdentities.CloudFrontOriginAccessIdentityList',
    'cloudfront.ListDistributions.DistributionList',
    'cloudfront.ListInvalidations.InvalidationList',
    'cloudfront.ListStreamingDistributions.StreamingDistributionList',
    'codedeploy.ListDeploymentGroups.applicationName',
    'dms.DescribeTableStatistics.ReplicationTaskArn',
    'dms.DescribeReplicationTaskAssessmentResults.BucketName',
    'ec2.DescribeSpotFleetInstances.SpotFleetRequestId',
    'ec2.DescribeVpcEndpointServices.ServiceNames',
    'efs.DescribeFileSystems.Marker',
    'efs.DescribeMountTargets.Marker',
    'efs.DescribeTags.Marker',
    'elasticache.DescribeCacheParameters.CacheNodeTypeSpecificParameters',
    'elasticache.DescribeEngineDefaultParameters.EngineDefaults',
    'glacier.ListParts.PartSizeInBytes',
    'glacier.ListParts.ArchiveDescription',
    'glacier.ListParts.MultipartUploadId',
    'glacier.ListParts.VaultARN',
    'glacier.ListParts.CreationDate',
    'kinesis.DescribeStream.StreamDescription',
    'mturk.ListAssignmentsForHIT.NumResults',
    'mturk.ListQualificationTypes.NumResults',
    'mturk.ListHITs.NumResults',
    'mturk.ListWorkerBlocks.NumResults',
    'mturk.ListReviewableHITs.NumResults',
    'mturk.ListHITsForQualificationType.NumResults',
    'mturk.ListQualificationRequests.NumResults',
    'mturk.ListWorkersWithQualificationType.NumResults',
    'mturk.ListBonusPayments.NumResults',
    'neptune.DescribeEngineDefaultParameters.EngineDefaults',
    'rds.DescribeEngineDefaultClusterParameters.EngineDefaults',
    'rds.DescribeEngineDefaultParameters.EngineDefaults',
    'redshift.DescribeDefaultClusterParameters.DefaultClusterParameters',
    'resource-groups.ListGroups.GroupIdentifiers',
    'resource-groups.SearchResources.QueryErrors',
    'resource-groups.ListGroupResources.QueryErrors',
    'route53.ListHealthChecks.MaxItems',
    'route53.ListHealthChecks.Marker',
    'route53.ListHostedZones.MaxItems',
    'route53.ListHostedZones.Marker',
    'route53.ListResourceRecordSets.MaxItems',
    's3.ListMultipartUploads.Delimiter',
    's3.ListMultipartUploads.KeyMarker',
    's3.ListMultipartUploads.Prefix',
    's3.ListMultipartUploads.Bucket',
    's3.ListMultipartUploads.MaxUploads',
    's3.ListMultipartUploads.UploadIdMarker',
    's3.ListMultipartUploads.EncodingType',
    's3.ListObjectVersions.MaxKeys',
    's3.ListObjectVersions.Delimiter',
    's3.ListObjectVersions.VersionIdMarker',
    's3.ListObjectVersions.KeyMarker',
    's3.ListObjectVersions.Prefix',
    's3.ListObjectVersions.Name',
    's3.ListObjectVersions.EncodingType',
    's3.ListObjects.MaxKeys',
    's3.ListObjects.Delimiter',
    's3.ListObjects.NextMarker',
    's3.ListObjects.Prefix',
    's3.ListObjects.Marker',
    's3.ListObjects.Name',
    's3.ListObjects.EncodingType',
    's3.ListObjectsV2.StartAfter',
    's3.ListObjectsV2.MaxKeys',
    's3.ListObjectsV2.Delimiter',
    's3.ListObjectsV2.ContinuationToken',
    's3.ListObjectsV2.KeyCount',
    's3.ListObjectsV2.Prefix',
    's3.ListObjectsV2.Name',
    's3.ListObjectsV2.EncodingType',
    's3.ListParts.PartNumberMarker',
    's3.ListParts.AbortDate',
    's3.ListParts.MaxParts',
    's3.ListParts.Bucket',
    's3.ListParts.Key',
    's3.ListParts.UploadId',
    's3.ListParts.AbortRuleId',
    's3.ListParts.RequestCharged',
    'sms.GetReplicationRuns.replicationJob',
    'sms.GetServers.lastModifiedOn',
    'sms.GetServers.serverCatalogStatus',
    'storagegateway.DescribeTapeRecoveryPoints.GatewayARN',
    'storagegateway.DescribeVTLDevices.GatewayARN',
    'storagegateway.ListVolumes.GatewayARN',
    'workdocs.DescribeUsers.TotalNumberOfUsers',
    'xray.BatchGetTraces.UnprocessedTraceIds',
    'xray.GetServiceGraph.EndTime',
    'xray.GetServiceGraph.ContainsOldGroupVersions',
    'xray.GetServiceGraph.StartTime',
    'xray.GetTraceSummaries.TracesProcessedCount',
    'xray.GetTraceSummaries.ApproximateTime',
]


def _pagination_configs():
    session = botocore.session.get_session()
    loader = session.get_component('data_loader')
    services = loader.list_available_services('paginators-1')
    for service_name in services:
        service_model = session.get_service_model(service_name)
        page_config = loader.load_service_model(service_name,
                                                'paginators-1')
        for op_name, single_config in page_config['pagination'].items():
            yield (
                op_name,
                single_config,
                service_model
            )

@pytest.mark.parametrize(
    "operation_name, page_config, service_model",
    _pagination_configs()
)
def test_lint_pagination_configs(operation_name, page_config, service_model):
    _validate_known_pagination_keys(page_config)
    _valiate_result_key_exists(page_config)
    _validate_referenced_operation_exists(operation_name, service_model)
    _validate_operation_has_output(operation_name, service_model)
    _validate_input_keys_match(operation_name, page_config, service_model)
    _validate_output_keys_match(operation_name, page_config, service_model)


def _validate_known_pagination_keys(page_config):
    for key in page_config:
        if key not in KNOWN_PAGE_KEYS:
            raise AssertionError("Unknown key '%s' in pagination config: %s"
                                 % (key, page_config))


def _valiate_result_key_exists(page_config):
    if 'result_key' not in page_config:
        raise AssertionError("Required key 'result_key' is missing "
                             "from pagination config: %s" % page_config)


def _validate_referenced_operation_exists(operation_name, service_model):
    if operation_name not in service_model.operation_names:
        raise AssertionError("Pagination config refers to operation that "
                             "does not exist: %s" % operation_name)


def _validate_operation_has_output(operation_name, service_model):
    op_model = service_model.operation_model(operation_name)
    output = op_model.output_shape
    if output is None or not output.members:
        raise AssertionError("Pagination config refers to operation "
                             "that does not have any output: %s"
                             % operation_name)


def _validate_input_keys_match(operation_name, page_config, service_model):
    input_tokens = page_config['input_token']
    if not isinstance(input_tokens, list):
        input_tokens = [input_tokens]
    valid_input_names = service_model.operation_model(
        operation_name).input_shape.members
    for token in input_tokens:
        if token not in valid_input_names:
            raise AssertionError("input_token '%s' refers to a non existent "
                                 "input member for operation: %s"
                                 % (token, operation_name))
    if 'limit_key' in page_config:
        limit_key = page_config['limit_key']
        if limit_key not in valid_input_names:
            raise AssertionError("limit_key '%s' refers to a non existent "
                                 "input member for operation: %s, valid keys: "
                                 "%s" % (limit_key, operation_name,
                                         ', '.join(list(valid_input_names))))


def _validate_output_keys_match(operation_name, page_config, service_model):
    # NOTE: The original version of this function from translate.py had logic
    # to ensure that the entire set of output_members was accounted for in the
    # union of 'result_key', 'output_token', 'more_results', and
    # 'non_aggregate_keys'.
    # There's enough state drift (especially with non_aggregate_keys) that
    # this is no longer a realistic thing to check.  Someone would have to
    # backport the missing keys to all the paginators.
    output_shape = service_model.operation_model(operation_name).output_shape
    output_members = set(output_shape.members)
    for key_name, output_key in _get_all_page_output_keys(page_config):
        if _looks_like_jmespath(output_key):
            _validate_jmespath_compiles(output_key)
        else:
            if output_key not in output_members:
                raise AssertionError("Pagination key '%s' refers to an output "
                                     "member that does not exist: %s" % (
                                         key_name, output_key))
            output_members.remove(output_key)

    for member in list(output_members):
        key = "%s.%s.%s" % (service_model.service_name,
                            operation_name,
                            member)
        if key in KNOWN_EXTRA_OUTPUT_KEYS:
            output_members.remove(member)

    if output_members:
        for member in output_members:
            key = "%s.%s.%s" % (service_model.service_name,
                                operation_name,
                                member)
            with open('/tmp/blah', 'a') as f:
                f.write("'%s',\n" % key)
        raise AssertionError("There are member names in the output shape of "
                             "%s that are not accounted for in the pagination "
                             "config for service %s: %s" % (
                                 operation_name, service_model.service_name,
                                 ', '.join(output_members)))


def _looks_like_jmespath(expression):
    if all(ch in MEMBER_NAME_CHARS for ch in expression):
        return False
    return True


def _validate_jmespath_compiles(expression):
    try:
        jmespath.compile(expression)
    except JMESPathError as e:
        raise AssertionError("Invalid JMESPath expression used "
                             "in pagination config: %s\nerror: %s"
                             % (expression, e))


def _get_all_page_output_keys(page_config):
    for key in _get_list_value(page_config, 'result_key'):
        yield 'result_key', key
    for key in _get_list_value(page_config, 'output_token'):
        yield 'output_token', key
    if 'more_results' in page_config:
        yield 'more_results', page_config['more_results']
    for key in page_config.get('non_aggregate_keys', []):
        yield 'non_aggregate_keys', key


def _get_list_value(page_config, key):
    # Some pagination config values can be a scalar value or a list of scalars.
    # This function will always return a list of scalar values, converting as
    # necessary.
    value = page_config[key]
    if not isinstance(value, list):
        value = [value]
    return value
