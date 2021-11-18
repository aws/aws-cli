# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Resolves regions and endpoints.

This module implements endpoint resolution, including resolving endpoints for a
given service and region and resolving the available endpoints for a service
in a specific AWS partition.
"""
import logging
import re

from botocore.exceptions import (
    NoRegionError, EndpointVariantError
)

LOG = logging.getLogger(__name__)
DEFAULT_URI_TEMPLATE = '{service}.{region}.{dnsSuffix}' # noqa
DEFAULT_SERVICE_DATA = {'endpoints': {}}


class BaseEndpointResolver(object):
    """Resolves regions and endpoints. Must be subclassed."""
    def construct_endpoint(self, service_name, region_name=None):
        """Resolves an endpoint for a service and region combination.

        :type service_name: string
        :param service_name: Name of the service to resolve an endpoint for
            (e.g., s3)

        :type region_name: string
        :param region_name: Region/endpoint name to resolve (e.g., us-east-1)
            if no region is provided, the first found partition-wide endpoint
            will be used if available.

        :rtype: dict
        :return: Returns a dict containing the following keys:
            - partition: (string, required) Resolved partition name
            - endpointName: (string, required) Resolved endpoint name
            - hostname: (string, required) Hostname to use for this endpoint
            - sslCommonName: (string) sslCommonName to use for this endpoint.
            - credentialScope: (dict) Signature version 4 credential scope
              - region: (string) region name override when signing.
              - service: (string) service name override when signing.
            - signatureVersions: (list<string>) A list of possible signature
              versions, including s3, v4, v2, and s3v4
            - protocols: (list<string>) A list of supported protocols
              (e.g., http, https)
            - ...: Other keys may be included as well based on the metadata
        """
        raise NotImplementedError

    def get_available_partitions(self):
        """Lists the partitions available to the endpoint resolver.

        :return: Returns a list of partition names (e.g., ["aws", "aws-cn"]).
        """
        raise NotImplementedError

    def get_available_endpoints(self, service_name, partition_name='aws',
                                allow_non_regional=False):
        """Lists the endpoint names of a particular partition.

        :type service_name: string
        :param service_name: Name of a service to list endpoint for (e.g., s3)

        :type partition_name: string
        :param partition_name: Name of the partition to limit endpoints to.
            (e.g., aws for the public AWS endpoints, aws-cn for AWS China
            endpoints, aws-us-gov for AWS GovCloud (US) Endpoints, etc.

        :type allow_non_regional: bool
        :param allow_non_regional: Set to True to include endpoints that are
             not regional endpoints (e.g., s3-external-1,
             fips-us-gov-west-1, etc).
        :return: Returns a list of endpoint names (e.g., ["us-east-1"]).
        """
        raise NotImplementedError


class EndpointResolver(BaseEndpointResolver):
    """Resolves endpoints based on partition endpoint metadata"""

    _UNSUPPORTED_DUALSTACK_PARTITIONS = ['aws-iso', 'aws-iso-b']

    def __init__(self, endpoint_data):
        """
        :param endpoint_data: A dict of partition data.
        """
        if 'partitions' not in endpoint_data:
            raise ValueError('Missing "partitions" in endpoint data')
        self._endpoint_data = endpoint_data

    def get_service_endpoints_data(self, service_name, partition_name='aws'):
        for partition in self._endpoint_data['partitions']:
            if partition['partition'] != partition_name:
                continue
            services = partition['services']
            if service_name not in services:
                continue
            return services[service_name]['endpoints']

    def get_available_partitions(self):
        result = []
        for partition in self._endpoint_data['partitions']:
            result.append(partition['partition'])
        return result

    def get_available_endpoints(self, service_name, partition_name='aws',
                                allow_non_regional=False,
                                endpoint_variant_tags=None):
        result = []
        for partition in self._endpoint_data['partitions']:
            if partition['partition'] != partition_name:
                continue
            services = partition['services']
            if service_name not in services:
                continue
            service_endpoints = services[service_name]['endpoints']
            for endpoint_name in service_endpoints:
                is_regional_endpoint = endpoint_name in partition['regions']
                # Only regional endpoints can be modeled with variants
                if endpoint_variant_tags and is_regional_endpoint:
                    variant_data = self._retrieve_variant_data(
                        service_endpoints[endpoint_name],
                        endpoint_variant_tags)
                    if variant_data:
                        result.append(endpoint_name)
                elif allow_non_regional or is_regional_endpoint:
                    result.append(endpoint_name)
        return result

    def get_partition_dns_suffix(self, partition_name,
                                 endpoint_variant_tags=None):
        for partition in self._endpoint_data['partitions']:
            if partition['partition'] == partition_name:
                if endpoint_variant_tags:
                    variant = self._retrieve_variant_data(
                        partition.get('defaults'), endpoint_variant_tags)
                    if variant and 'dnsSuffix' in variant:
                        return variant['dnsSuffix']
                else:
                    return partition['dnsSuffix']
        return None

    def construct_endpoint(self, service_name, region_name=None,
                           partition_name=None, use_dualstack_endpoint=False,
                           use_fips_endpoint=False):
        if service_name == 's3' and use_dualstack_endpoint and region_name is None:
            region_name = 'us-east-1'
        if partition_name is not None:
            valid_partition = None
            for partition in self._endpoint_data['partitions']:
                if partition['partition'] == partition_name:
                    valid_partition = partition

            if valid_partition is not None:
                result = self._endpoint_for_partition(
                    valid_partition, service_name,
                    region_name, use_dualstack_endpoint, use_fips_endpoint,
                    True
                )
                return result
            return None

        # Iterate over each partition until a match is found.
        for partition in self._endpoint_data['partitions']:
            if use_dualstack_endpoint and (
                    partition['partition'] in
                    self._UNSUPPORTED_DUALSTACK_PARTITIONS):
                continue
            result = self._endpoint_for_partition(
                partition, service_name, region_name, use_dualstack_endpoint,
                use_fips_endpoint
            )
            if result:
                return result

    def _endpoint_for_partition(self, partition, service_name, region_name,
                                use_dualstack_endpoint, use_fips_endpoint,
                                force_partition=False):
        partition_name = partition["partition"]
        if (use_dualstack_endpoint and
                partition_name in self._UNSUPPORTED_DUALSTACK_PARTITIONS):
            error_msg = ("Dualstack endpoints are currently not supported"
                         " for %s partition" % partition_name)
            raise EndpointVariantError(tags=['dualstack'], error_msg=error_msg)

        # Get the service from the partition, or an empty template.
        service_data = partition['services'].get(
            service_name, DEFAULT_SERVICE_DATA)
        # Use the partition endpoint if no region is supplied.
        if region_name is None:
            if 'partitionEndpoint' in service_data:
                region_name = service_data['partitionEndpoint']
            else:
                raise NoRegionError()

        resolve_kwargs = {
            'partition': partition,
            'service_name': service_name,
            'service_data': service_data,
            'endpoint_name': region_name,
            'use_dualstack_endpoint': use_dualstack_endpoint,
            'use_fips_endpoint': use_fips_endpoint,
        }

        # Attempt to resolve the exact region for this partition.
        if region_name in service_data['endpoints']:
            return self._resolve(**resolve_kwargs)

        # Check to see if the endpoint provided is valid for the partition.
        if self._region_match(partition, region_name) or force_partition:
            # Use the partition endpoint if set and not regionalized.
            partition_endpoint = service_data.get('partitionEndpoint')
            is_regionalized = service_data.get('isRegionalized', True)
            if partition_endpoint and not is_regionalized:
                LOG.debug('Using partition endpoint for %s, %s: %s',
                          service_name, region_name, partition_endpoint)
                resolve_kwargs['endpoint_name'] = partition_endpoint
                return self._resolve(**resolve_kwargs)
            LOG.debug('Creating a regex based endpoint for %s, %s',
                      service_name, region_name)
            return self._resolve(**resolve_kwargs)

    def _region_match(self, partition, region_name):
        if region_name in partition['regions']:
            return True
        if 'regionRegex' in partition:
            return re.compile(partition['regionRegex']).match(region_name)
        return False

    def _retrieve_variant_data(self, endpoint_data, tags):
        variants = endpoint_data.get('variants', [])
        for variant in variants:
            if set(variant['tags']) == set(tags):
                result = variant.copy()
                return result

    def _create_tag_list(self, use_dualstack_endpoint, use_fips_endpoint):
        tags = []
        if use_dualstack_endpoint:
            tags.append('dualstack')
        if use_fips_endpoint:
            tags.append('fips')
        return tags

    def _resolve_variant(self, tags, endpoint_data, service_defaults,
                         partition_defaults):
        result = {}
        for variants in [endpoint_data, service_defaults,
                         partition_defaults]:
            variant = self._retrieve_variant_data(variants, tags)
            if variant:
                self._merge_keys(variant, result)
        return result

    def _resolve(self, partition, service_name, service_data, endpoint_name,
                 use_dualstack_endpoint, use_fips_endpoint):
        endpoint_data = service_data.get('endpoints', {}).get(endpoint_name, {})

        if endpoint_data.get('deprecated'):
            LOG.warning(
                'Client is configured with the deprecated endpoint: %s' % (
                    endpoint_name
                )
            )

        service_defaults = service_data.get('defaults', {})
        partition_defaults = partition.get('defaults', {})
        tags = self._create_tag_list(use_dualstack_endpoint,
                                     use_fips_endpoint)

        if tags:
            result = self._resolve_variant(tags, endpoint_data,
                                           service_defaults,
                                           partition_defaults)
            if result == {}:
                error_msg = ("Endpoint does not exist for %s in region %s" % (
                    service_name, endpoint_name
                ))
                raise EndpointVariantError(tags=tags, error_msg=error_msg)
        else:
            result = endpoint_data

        # If dnsSuffix has not already been consumed from a variant definition
        if 'dnsSuffix' not in result:
            result['dnsSuffix'] = partition['dnsSuffix']

        result['partition'] = partition['partition']
        result['endpointName'] = endpoint_name

        # Merge in the service defaults then the partition defaults.
        self._merge_keys(service_defaults, result)
        self._merge_keys(partition_defaults, result)

        result['hostname'] = self._expand_template(
            partition, result['hostname'], service_name, endpoint_name,
            result['dnsSuffix']
        )
        if 'sslCommonName' in result:
            result['sslCommonName'] = self._expand_template(
                partition, result['sslCommonName'], service_name,
                endpoint_name, result['dnsSuffix'])

        return result

    def _merge_keys(self, from_data, result):
        for key in from_data:
            if key not in result:
                result[key] = from_data[key]

    def _expand_template(self, partition, template, service_name,
                         endpoint_name, dnsSuffix):
        return template.format(
            service=service_name, region=endpoint_name,
            dnsSuffix=dnsSuffix)
