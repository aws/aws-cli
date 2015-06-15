#!/usr/bin/env python
# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import BaseAWSCommandParamsTest


class TestCreateCacheCluster(BaseAWSCommandParamsTest):
    maxDiff = None

    prefix = 'elasticache create-cache-cluster '

    def test_create_cache_cluster(self):
        args = ('--cache-cluster-id cachecluster-us-east-1c '
                '--num-cache-nodes 1 '
                '--cache-node-type cache.m1.small '
                '--engine memcached '
                '--engine-version 1.4.5 '
                '--cache-security-group-names group1 group2 '
                '--preferred-availability-zone us-east-1c '
                '--auto-minor-version-upgrade '
                '--preferred-maintenance-window fri:08:00-fri:09:00')
        cmdline = self.prefix + args
        result = {'AutoMinorVersionUpgrade': True,
                  'CacheClusterId': 'cachecluster-us-east-1c',
                  'CacheNodeType': 'cache.m1.small',
                  'CacheSecurityGroupNames': ['group1', 'group2'],
                  'Engine': 'memcached',
                  'EngineVersion': '1.4.5',
                  'NumCacheNodes': 1,
                  'PreferredAvailabilityZone': 'us-east-1c',
                  'PreferredMaintenanceWindow': 'fri:08:00-fri:09:00'}
        self.assert_params_for_cmd(cmdline, result)

    def test_create_cache_cluster_no_auto_minor_upgrade(self):
        args = ('--cache-cluster-id cachecluster-us-east-1c '
                '--num-cache-nodes 1 '
                '--cache-node-type cache.m1.small '
                '--engine memcached '
                '--engine-version 1.4.5 '
                '--cache-security-group-names group1 group2 '
                '--preferred-availability-zone us-east-1c '
                '--no-auto-minor-version-upgrade '
                '--preferred-maintenance-window fri:08:00-fri:09:00')
        cmdline = self.prefix + args
        result = {'AutoMinorVersionUpgrade': False,
                  'CacheClusterId': 'cachecluster-us-east-1c',
                  'CacheNodeType': 'cache.m1.small',
                  'CacheSecurityGroupNames': ['group1', 'group2'],
                  'Engine': 'memcached',
                  'EngineVersion': '1.4.5',
                  'NumCacheNodes': 1,
                  'PreferredAvailabilityZone': 'us-east-1c',
                  'PreferredMaintenanceWindow': 'fri:08:00-fri:09:00'}
        self.assert_params_for_cmd(cmdline, result)

    def test_minor_upgrade_arg_not_specified(self):
        args = ('--cache-cluster-id cachecluster-us-east-1c '
                '--num-cache-nodes 1 '
                '--cache-node-type cache.m1.small '
                '--engine memcached '
                '--engine-version 1.4.5 '
                '--cache-security-group-names group1 group2 '
                '--preferred-availability-zone us-east-1c '
                '--preferred-maintenance-window fri:08:00-fri:09:00')
        cmdline = self.prefix + args
        # Note how if neither '--auto-minor-version-upgrade' nor
        # '--no-auto-minor-version-upgrade' is specified, then
        # AutoMinorVersionUpgrade is not in the result dict.
        result = {'CacheClusterId': 'cachecluster-us-east-1c',
                  'CacheNodeType': 'cache.m1.small',
                  'CacheSecurityGroupNames': ['group1', 'group2'],
                  'Engine': 'memcached',
                  'EngineVersion': '1.4.5',
                  'NumCacheNodes': 1,
                  'PreferredAvailabilityZone': 'us-east-1c',
                  'PreferredMaintenanceWindow': 'fri:08:00-fri:09:00'}
        self.assert_params_for_cmd(cmdline, result)
