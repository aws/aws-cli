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

import json
import yaml

from awscli.customizations.ecs import exceptions

MAX_CHAR_LENGTH = 46
APP_PREFIX = 'AppECS-'
DGP_PREFIX = 'DgpECS-'


def find_required_key(resource_name, obj, key):

    if obj is None:
        raise exceptions.MissingPropertyError(
            resource=resource_name, prop_name=key)

    result = _get_case_insensitive_key(obj, key)

    if result is None:
        raise exceptions.MissingPropertyError(
            resource=resource_name, prop_name=key)
    else:
        return result


def _get_case_insensitive_key(target_obj, target_key):
    key_to_match = target_key.lower()
    key_list = target_obj.keys()

    for key in key_list:
        if key.lower() == key_to_match:
            return key


def get_app_name(service, cluster, app_value):
    if app_value is not None:
        return app_value
    else:
        suffix = _get_ecs_suffix(service, cluster)
        return APP_PREFIX + suffix


def get_cluster_name_from_arn(arn):
    return arn.split('/')[1]


def get_deploy_group_name(service, cluster, dg_value):
    if dg_value is not None:
        return dg_value
    else:
        suffix = _get_ecs_suffix(service, cluster)
        return DGP_PREFIX + suffix


def _get_ecs_suffix(service, cluster):
    if cluster is None:
        cluster_name = 'default'
    else:
        cluster_name = cluster[:MAX_CHAR_LENGTH]

    return cluster_name + '-' + service[:MAX_CHAR_LENGTH]


def parse_appspec(appspec_str):
    try:
        return json.loads(appspec_str)
    except ValueError:
        return yaml.safe_load(appspec_str)
