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

"""This module contains some helpers for mocking eks clusters"""

import os
from nose.tools import nottest


EXAMPLE_NAME = "ExampleCluster"

@nottest
def get_testdata(file_name):
    """Get the path of a specific fixture"""
    return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        "testdata",
                        file_name)


def list_cluster_response():
    """Get an example list_cluster call (For mocking)"""
    return {
        "clusters": [
            EXAMPLE_NAME
        ]
    }


def describe_cluster_response():
    """Get an example describe_cluster call (For mocking)"""
    return {
        "cluster": {
            "status": "ACTIVE",
            "endpoint": "https://endpoint.amazonaws.com",
            "name": EXAMPLE_NAME,
            "certificateAuthority": {
                "data": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tDQpWR1Z6ZEdsdVp5QkVZWFJoRFFwVVpYTjBhVzVuSUVSaGRHRU5DbFJsYzNScGJtY2dSR0YwWVEwS2EzVmlaWEp1WlhSbGN6QWVGdzBLVkdWemRHbHVaeUJFWVhSaERRcFVaWE4wYVc1bklFUmhkR0ZWQkFNVERRcHJkV0psY201bGRHVnpNQUVpTUEwS1ZHVnpkR2x1WnlCRVlYUmhEUXBVWlhOMGFXNW5JRVJoZEdFTkNsUmxjM1JwYm1jZ1JHRjBZY3UvR1FnbmFTcDNZaHBDTWhGVVpYTjBhVzVuSUVSaGRHRXl3clZqeEpWNjNwNFVHRmpZdHdGR1drUldJVkV1VkdWemRHbHVaeUJFWVhSaGJzT0MxSVJiTDhPd0lpMVhiWGg2VkdWemRHbHVaeUJFWVhSaFpXVndTTk9VVUZKNmN5QWJaaFpnWVNkTUV3MEtGMVJsYzNScGJtY2dSR0YwWVFZRFZSMFBBUUVFQkFNQ0FsUmxjM1JwYm1jZ1JHRjBZUUV3RFFvR0NTcElEUXBVWlhOMGFXNW5JRVJoZEdGcEgxc1pPRTNMa3lrMU9DWUNHUloyTEZjM3paOCtHell3WEZSbGMzUnBibWNnUkdGMFlYMUR5NjFNMVlGV1AxWVRIMVJsYzNScGJtY2dSR0YwWVd0aE5oMVphM2dWUDBGaGNSWjdKaW9oZVc4N1JsUmxjM1JwYm1jZ1JHRjBZUVpIVHd4NE9IdzZmZz09DQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0t"
            },
            "roleArn": "arn:aws:iam::111222333444/eksRole",
            "resourcesVpcConfig": {
                "subnetIds": [
                    "subnet-00000000000000000",
                    "subnet-00000000000000001",
                    "subnet-00000000000000002"
                ],
                "vpcId": "vpc-00000000000000000",
                "securityGroupIds": [
                    "sg-00000000000000000"
                ]
            },
            "version": "1.10",
            "arn": "arn:aws:eks:region:111222333444:cluster/" + EXAMPLE_NAME,
            "createdAt": 1500000000.000
        }
    }

def describe_cluster_no_status_response():
    """Get an example describe_cluster call (For mocking)"""
    return {
        "cluster": {
            "endpoint": "https://endpoint.amazonaws.com",
            "name": EXAMPLE_NAME,
            "certificateAuthority": {
                "data": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tDQpWR1Z6ZEdsdVp5QkVZWFJoRFFwVVpYTjBhVzVuSUVSaGRHRU5DbFJsYzNScGJtY2dSR0YwWVEwS2EzVmlaWEp1WlhSbGN6QWVGdzBLVkdWemRHbHVaeUJFWVhSaERRcFVaWE4wYVc1bklFUmhkR0ZWQkFNVERRcHJkV0psY201bGRHVnpNQUVpTUEwS1ZHVnpkR2x1WnlCRVlYUmhEUXBVWlhOMGFXNW5JRVJoZEdFTkNsUmxjM1JwYm1jZ1JHRjBZY3UvR1FnbmFTcDNZaHBDTWhGVVpYTjBhVzVuSUVSaGRHRXl3clZqeEpWNjNwNFVHRmpZdHdGR1drUldJVkV1VkdWemRHbHVaeUJFWVhSaGJzT0MxSVJiTDhPd0lpMVhiWGg2VkdWemRHbHVaeUJFWVhSaFpXVndTTk9VVUZKNmN5QWJaaFpnWVNkTUV3MEtGMVJsYzNScGJtY2dSR0YwWVFZRFZSMFBBUUVFQkFNQ0FsUmxjM1JwYm1jZ1JHRjBZUUV3RFFvR0NTcElEUXBVWlhOMGFXNW5JRVJoZEdGcEgxc1pPRTNMa3lrMU9DWUNHUloyTEZjM3paOCtHell3WEZSbGMzUnBibWNnUkdGMFlYMUR5NjFNMVlGV1AxWVRIMVJsYzNScGJtY2dSR0YwWVd0aE5oMVphM2dWUDBGaGNSWjdKaW9oZVc4N1JsUmxjM1JwYm1jZ1JHRjBZUVpIVHd4NE9IdzZmZz09DQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0t"
            },
            "roleArn": "arn:aws:iam::111222333444/eksRole",
            "resourcesVpcConfig": {
                "subnetIds": [
                    "subnet-00000000000000000",
                    "subnet-00000000000000001",
                    "subnet-00000000000000002"
                ],
                "vpcId": "vpc-00000000000000000",
                "securityGroupIds": [
                    "sg-00000000000000000"
                ]
            },
            "version": "1.10",
            "arn": "arn:aws:eks:region:111222333444:cluster/" + EXAMPLE_NAME,
            "createdAt": 1500000000.000
        }
    }

def describe_cluster_creating_response():
    """Get an example describe_cluster call during creation"""
    return {
        "cluster": {
            "status": "CREATING",
            "name": EXAMPLE_NAME,
            "certificateAuthority": {},
            "roleArn": "arn:aws:iam::111222333444/eksRole",
            "resourcesVpcConfig": {
                "subnetIds": [
                    "subnet-00000000000000000",
                    "subnet-00000000000000001",
                    "subnet-00000000000000002"
                ],
                "vpcId": "vpc-00000000000000000",
                "securityGroupIds": [
                    "sg-00000000000000000"
                ]
            },
            "version": "1.10",
            "arn": "arn:aws:eks:region:111222333444:cluster/" + EXAMPLE_NAME,
            "createdAt": 1500000000.000
        }
    }


def describe_cluster_deleting_response():
    """Get an example describe_cluster call during deletion"""
    return {
        "cluster": {
            "status": "DELETING",
            "endpoint": "https://endpoint.amazonaws.com",
            "name": EXAMPLE_NAME,
            "certificateAuthority": {
                "data": "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tDQpWR1Z6ZEdsdVp5QkVZWFJoRFFwVVpYTjBhVzVuSUVSaGRHRU5DbFJsYzNScGJtY2dSR0YwWVEwS2EzVmlaWEp1WlhSbGN6QWVGdzBLVkdWemRHbHVaeUJFWVhSaERRcFVaWE4wYVc1bklFUmhkR0ZWQkFNVERRcHJkV0psY201bGRHVnpNQUVpTUEwS1ZHVnpkR2x1WnlCRVlYUmhEUXBVWlhOMGFXNW5JRVJoZEdFTkNsUmxjM1JwYm1jZ1JHRjBZY3UvR1FnbmFTcDNZaHBDTWhGVVpYTjBhVzVuSUVSaGRHRXl3clZqeEpWNjNwNFVHRmpZdHdGR1drUldJVkV1VkdWemRHbHVaeUJFWVhSaGJzT0MxSVJiTDhPd0lpMVhiWGg2VkdWemRHbHVaeUJFWVhSaFpXVndTTk9VVUZKNmN5QWJaaFpnWVNkTUV3MEtGMVJsYzNScGJtY2dSR0YwWVFZRFZSMFBBUUVFQkFNQ0FsUmxjM1JwYm1jZ1JHRjBZUUV3RFFvR0NTcElEUXBVWlhOMGFXNW5JRVJoZEdGcEgxc1pPRTNMa3lrMU9DWUNHUloyTEZjM3paOCtHell3WEZSbGMzUnBibWNnUkdGMFlYMUR5NjFNMVlGV1AxWVRIMVJsYzNScGJtY2dSR0YwWVd0aE5oMVphM2dWUDBGaGNSWjdKaW9oZVc4N1JsUmxjM1JwYm1jZ1JHRjBZUVpIVHd4NE9IdzZmZz09DQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0t"
            },
            "roleArn": "arn:aws:iam::111222333444/eksRole",
            "resourcesVpcConfig": {
                "subnetIds": [
                    "subnet-00000000000000000",
                    "subnet-00000000000000001",
                    "subnet-00000000000000002"
                ],
                "vpcId": "vpc-00000000000000000",
                "securityGroupIds": [
                    "sg-00000000000000000"
                ]
            },
            "version": "1.10",
            "arn": "arn:aws:eks:region:111222333444:cluster/" + EXAMPLE_NAME,
            "createdAt": 1500000000.000
        }
    }
