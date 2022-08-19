# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


SSL_COMMON_NAMES = {
    "sqs": {
        "af-south-1": "af-south-1.queue.amazonaws.com",
        "ap-east-1": "ap-east-1.queue.amazonaws.com",
        "ap-northeast-1": "ap-northeast-1.queue.amazonaws.com",
        "ap-northeast-2": "ap-northeast-2.queue.amazonaws.com",
        "ap-northeast-3": "ap-northeast-3.queue.amazonaws.com",
        "ap-south-1": "ap-south-1.queue.amazonaws.com",
        "ap-southeast-1": "ap-southeast-1.queue.amazonaws.com",
        "ap-southeast-2": "ap-southeast-2.queue.amazonaws.com",
        "ap-southeast-3": "ap-southeast-3.queue.amazonaws.com",
        "ca-central-1": "ca-central-1.queue.amazonaws.com",
        "eu-central-1": "eu-central-1.queue.amazonaws.com",
        "eu-north-1": "eu-north-1.queue.amazonaws.com",
        "eu-south-1": "eu-south-1.queue.amazonaws.com",
        "eu-west-1": "eu-west-1.queue.amazonaws.com",
        "eu-west-2": "eu-west-2.queue.amazonaws.com",
        "eu-west-3": "eu-west-3.queue.amazonaws.com",
        "me-south-1": "me-south-1.queue.amazonaws.com",
        "sa-east-1": "sa-east-1.queue.amazonaws.com",
        "us-east-1": "queue.amazonaws.com",
        "us-east-2": "us-east-2.queue.amazonaws.com",
        "us-west-1": "us-west-1.queue.amazonaws.com",
        "us-west-2": "us-west-2.queue.amazonaws.com",
        "cn-north-1": "cn-north-1.queue.amazonaws.com.cn",
        "cn-northwest-1": "cn-northwest-1.queue.amazonaws.com.cn",
        "us-gov-west-1": "us-gov-west-1.queue.amazonaws.com",
        "us-isob-east-1": "us-isob-east-1.queue.sc2s.sgov.gov",
    },
    "emr": {
        "af-south-1": "af-south-1.elasticmapreduce.amazonaws.com",
        "ap-east-1": "ap-east-1.elasticmapreduce.amazonaws.com",
        "ap-northeast-1": "ap-northeast-1.elasticmapreduce.amazonaws.com",
        "ap-northeast-2": "ap-northeast-2.elasticmapreduce.amazonaws.com",
        "ap-northeast-3": "ap-northeast-3.elasticmapreduce.amazonaws.com",
        "ap-south-1": "ap-south-1.elasticmapreduce.amazonaws.com",
        "ap-southeast-1": "ap-southeast-1.elasticmapreduce.amazonaws.com",
        "ap-southeast-2": "ap-southeast-2.elasticmapreduce.amazonaws.com",
        "ap-southeast-3": "ap-southeast-3.elasticmapreduce.amazonaws.com",
        "ca-central-1": "ca-central-1.elasticmapreduce.amazonaws.com",
        "eu-north-1": "eu-north-1.elasticmapreduce.amazonaws.com",
        "eu-south-1": "eu-south-1.elasticmapreduce.amazonaws.com",
        "eu-west-1": "eu-west-1.elasticmapreduce.amazonaws.com",
        "eu-west-2": "eu-west-2.elasticmapreduce.amazonaws.com",
        "eu-west-3": "eu-west-3.elasticmapreduce.amazonaws.com",
        "me-south-1": "me-south-1.elasticmapreduce.amazonaws.com",
        "sa-east-1": "sa-east-1.elasticmapreduce.amazonaws.com",
        "us-east-2": "us-east-2.elasticmapreduce.amazonaws.com",
        "us-west-1": "us-west-1.elasticmapreduce.amazonaws.com",
        "us-west-2": "us-west-2.elasticmapreduce.amazonaws.com",
    },
    "rds": {
        "us-east-1": "rds.amazonaws.com",
    },
    "docdb": {
        "us-east-1": "rds.amazonaws.com",
    },
    "neptune": {
        "us-east-1": "rds.amazonaws.com",
    },
    "health": {
        "aws-global": "health.us-east-1.amazonaws.com",
        "af-south-1": "health.us-east-1.amazonaws.com",
        "ap-east-1": "health.us-east-1.amazonaws.com",
        "ap-northeast-1": "health.us-east-1.amazonaws.com",
        "ap-northeast-2": "health.us-east-1.amazonaws.com",
        "ap-northeast-3": "health.us-east-1.amazonaws.com",
        "ap-south-1": "health.us-east-1.amazonaws.com",
        "ap-southeast-1": "health.us-east-1.amazonaws.com",
        "ap-southeast-2": "health.us-east-1.amazonaws.com",
        "ap-southeast-3": "health.us-east-1.amazonaws.com",
        "ca-central-1": "health.us-east-1.amazonaws.com",
        "eu-central-1": "health.us-east-1.amazonaws.com",
        "eu-north-1": "health.us-east-1.amazonaws.com",
        "eu-south-1": "health.us-east-1.amazonaws.com",
        "eu-west-1": "health.us-east-1.amazonaws.com",
        "eu-west-2": "health.us-east-1.amazonaws.com",
        "eu-west-3": "health.us-east-1.amazonaws.com",
        "me-south-1": "health.us-east-1.amazonaws.com",
        "sa-east-1": "health.us-east-1.amazonaws.com",
        "us-east-1": "health.us-east-1.amazonaws.com",
        "us-east-2": "health.us-east-1.amazonaws.com",
        "us-west-1": "health.us-east-1.amazonaws.com",
        "us-west-2": "health.us-east-1.amazonaws.com",
        "cn-north-1": "health.cn-northwest-1.amazonaws.com.cn",
        "cn-northwest-1": "health.cn-northwest-1.amazonaws.com.cn",
        "aws-cn-global": "health.cn-northwest-1.amazonaws.com.cn",
    },
}

REGION_TO_PARTITION_OVERRIDE = {
    "aws-global": "aws",
    "aws-cn-global": "aws-cn",
}


def register_override_ssl_common_name(cli):
    cli.register_last(
        "before-building-argument-table-parser", update_endpoint_url
    )


def update_endpoint_url(session, parsed_globals, **kwargs):
    service = parsed_globals.command
    endpoints = SSL_COMMON_NAMES.get(service)
    # only change url if user has not overridden already themselves
    if endpoints is not None and parsed_globals.endpoint_url is None:
        region = session.get_config_variable("region")
        endpoint_url = endpoints.get(region)
        if endpoint_url is not None:
            parsed_globals.endpoint_url = f"https://{endpoint_url}"
            if service == "health":
                _override_health_region(region, session, parsed_globals)


def _override_health_region(region, session, parsed_globals):
    if region in REGION_TO_PARTITION_OVERRIDE:
        partition = REGION_TO_PARTITION_OVERRIDE[region]
    else:
        partition = session.get_partition_for_region(region)
    if partition == "aws-cn":
        parsed_globals.region = "cn-northwest-1"
    else:
        parsed_globals.region = "us-east-1"
