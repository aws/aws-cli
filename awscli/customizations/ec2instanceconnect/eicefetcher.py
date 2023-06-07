# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import logging

from awscli.customizations.exceptions import ParamValidationError, ConfigurationError

logger = logging.getLogger(__name__)


class FipsEndpointUnsupported(ConfigurationError):
    pass


class InstanceConnectEndpointRequestFetcher:

    def get_eice_dns_name(self, eice_info, is_fips_enabled):
        fips_dns_name = eice_info.get('FipsDnsName')

        if not is_fips_enabled:
            return eice_info['DnsName']
        elif is_fips_enabled and fips_dns_name:
            return fips_dns_name
        elif is_fips_enabled and not fips_dns_name:
            raise FipsEndpointUnsupported("Unable to find FIPS Endpoint")

    def get_available_instance_connect_endpoint(self, ec2_client, vpc_id, subnet_id, instance_connect_endpoint_id):
        if instance_connect_endpoint_id:
            return self._get_instance_connect_endpoint_by_id(ec2_client, instance_connect_endpoint_id)
        else:
            return self._get_instance_connect_endpoint_by_vpc(ec2_client, vpc_id, subnet_id)

    def _get_instance_connect_endpoint_by_id(self, ec2_client, instance_connect_endpoint_id):
        args = {
            "Filters": [{"Name": "state", "Values": ["create-complete"]}],
            "InstanceConnectEndpointIds": [instance_connect_endpoint_id]
        }
        describe_eice_response = ec2_client.describe_instance_connect_endpoints(**args)
        instance_connect_endpoints = describe_eice_response["InstanceConnectEndpoints"]
        if instance_connect_endpoints:
            return instance_connect_endpoints[0]
        raise ParamValidationError(
            f"There are no available instance connect endpoints with {instance_connect_endpoint_id}")

    def _get_instance_connect_endpoint_by_vpc(self, ec2_client, vpc_id, subnet_id):
        ## Describe until subnet match and if none match subnet then return the first one based on vpc-id filter
        args = {"Filters": [
            {"Name": "state", "Values": ["create-complete"]},
            {"Name": "vpc-id", "Values": [vpc_id]}
        ]}

        paginator = ec2_client.get_paginator('describe_instance_connect_endpoints')
        page_iterator = paginator.paginate(**args)
        instance_connect_endpoints = []
        for page in page_iterator:
            page_result = page["InstanceConnectEndpoints"]
            instance_connect_endpoints = instance_connect_endpoints + page_result
            if page_result:
                for eice in page_result:
                    if eice['SubnetId'] == subnet_id:
                        logger.debug(f"Using EICE based on subnet: {instance_connect_endpoints[0]}")
                        return eice

        if instance_connect_endpoints:
            logger.debug(f"Using EICE based on vpc: {instance_connect_endpoints[0]}")
            return instance_connect_endpoints[0]

        raise ParamValidationError("There are no available instance connect endpoints.")
