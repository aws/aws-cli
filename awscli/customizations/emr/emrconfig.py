# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import re

from awscli.customizations.emr.exceptions import ResolveServicePrincipalError

PUBLIC_REGION = "aws"
GOV_REGION = "aws-gov"
CN_REGION = "aws-cn"
PUBLIC_SUFFIX = "amazonaws.com"
CN_SUFFIX = "amazonaws.com.cn"
REGION_MAP = {
    "us-east-1": [PUBLIC_REGION, PUBLIC_SUFFIX],
    "us-west-1": [PUBLIC_REGION, PUBLIC_SUFFIX],
    "us-west-2": [PUBLIC_REGION, PUBLIC_SUFFIX],
    "eu-west-1": [PUBLIC_REGION, PUBLIC_SUFFIX],
    "ap-southeast-1": [PUBLIC_REGION, PUBLIC_SUFFIX],
    "ap-southeast-2": [PUBLIC_REGION, PUBLIC_SUFFIX],
    "ap-northeast-1": [PUBLIC_REGION, PUBLIC_SUFFIX],
    "sa-east-1": [PUBLIC_REGION, PUBLIC_SUFFIX],
    "us-gov-west-1": [GOV_REGION, PUBLIC_SUFFIX],
    "cn-north-1": [CN_REGION, CN_SUFFIX]
}

EMR_DEFAULT_REGION = "us-east-1"


def get_service_principal(service, region, endpoint_host):
    return service+'.'+_get_suffix(region, endpoint_host)


def _get_suffix(region, endpoint_host):
    if region in REGION_MAP:
        return REGION_MAP[region][1]
    else:
        return _get_suffix_from_endpoint_host(endpoint_host)


def _get_suffix_from_endpoint_host(endpoint_host):
    suffix_match = _get_regex_match_from_endpoint_host(endpoint_host)
    if suffix_match is not None and suffix_match.lastindex >= 3:
        suffix = suffix_match.group(3)
    else:
        raise ResolveServicePrincipalError

    return suffix


def _get_regex_match_from_endpoint_host(endpoint_host):
    if endpoint_host is None:
        return None
    regex_match = re.match("(https://)([^.]+).elasticmapreduce.(.*)",
                           endpoint_host)

    # Supports 'elasticmapreduce.{region}.' and '{region}.elasticmapreduce.'
    if regex_match is None:
        regex_match = re.match("(https://elasticmapreduce).([^.]+).(.*)",
                               endpoint_host)
    return regex_match
