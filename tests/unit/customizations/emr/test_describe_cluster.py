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

import json

from tests.unit.customizations.emr import EMRBaseAWSCommandParamsTest as \
    BaseAWSCommandParamsTest
from mock import patch


describe_cluster_result_mock = {
    "Cluster": {
        "Status": {
            "Timeline": {
                "ReadyDateTime": 1398376089.0,
                "EndDateTime": 1398376477.0,
                "CreationDateTime": 1398375871.0
            },
            "State": "TERMINATED",
            "StateChangeReason": {
                "Message": "Terminated by user request",
                "Code": "USER_REQUEST"
            }
        },
        "Ec2InstanceAttributes": {
            "IamInstanceProfile": "EMR_EC2_DefaultRole",
            "Ec2AvailabilityZone": "us-east-1b"
        },
        "Name": "ABCD",
        "Tags": [],
        "TerminationProtected": "false",
        "RunningAmiVersion": "2.4.2",
        "Applications": [
            {
                "Version": "1.0.3",
                "Name": "hadoop"
            }
        ],
        "VisibleToAllUsers": "true",
        "RequestedAmiVersion": "2.4.2",
        "LogUri": "s3n://abc/logs/",
        "AutoTerminate": "false",
        "Id": "j-ABCD"
        }
    }
list_instance_groups_result_mock = {
    "ResponseMetadata": {
        "RequestId": '12ec323c-50b1-11e4-b653-afa4228d882f'
    },
    "InstanceGroups": [
        {
            "RequestedInstanceCount": 1,
            "Status": {
                "Timeline": {
                    "ReadyDateTime": 1398376083.0,
                    "EndDateTime": 1398376476.0,
                    "CreationDateTime": 1398375871.0
                },
                "State": "TERMINATED",
                "StateChangeReason": {
                    "Message": "Job flow terminated",
                    "Code": "CLUSTER_TERMINATED"
                }
            },
            "Name": "Master instance group",
            "InstanceGroupType": "MASTER",
            "InstanceType": "m1.large",
            "Id": "ig-ABCD",
            "Market": "ON_DEMAND",
            "RunningInstanceCount": 0
        },
        {
            "RequestedInstanceCount": 2,
            "Status": {
                "Timeline": {
                    "ReadyDateTime": 1398376089.0,
                    "EndDateTime": 1398376476.0,
                    "CreationDateTime": 1398375871.0
                },
                "State": "TERMINATED",
                "StateChangeReason": {
                    "Message": "Job flow terminated",
                    "Code": "CLUSTER_TERMINATED"
                }
            },
            "Name": "Core instance group",
            "InstanceGroupType": "CORE",
            "InstanceType": "m1.large",
            "Id": "ig-DEF",
            "Market": "ON_DEMAND",
            "RunningInstanceCount": 0
        }
    ]
}

list_bootstrap_actions_result_mock = {
    "ResponseMetadata": {
        "RequestId": '12ec323c-50b1-11e4-b653-afa4228d882f'
    },
    "BootstrapActions": [
        {
            "Args": [],
            "Name": "Install HBase",
            "ScriptPath": "s3://elasticmapreduce/bootstrap-actions/setup-hbase"
        }
    ]
}

list_instances_result_mock = {
    "ResponseMetadata": {
        "RequestId": '12ec323c-50b1-11e4-b653-afa4228d882f'
    },
    "Instances": [
        {
            "Status": {
                "Timeline": {
                    "ReadyDateTime": 1406583288.786,
                    "EndDateTime": 1406583367.255,
                    "CreationDateTime": 1406583080.779
                },
                "State": "TERMINATED",
                "StateChangeReason": {
                    "Message": "Cluster was terminated.",
                    "Code": "CLUSTER_TERMINATED"
                }
            },
            "Ec2InstanceId": "i-A1234567",
            "PublicDnsName": "ec2-01-01-1-188.compute-1.amazonaws.com",
            "PrivateDnsName": "ip-10-10-10-177.ec2.internal",
            "PublicIpAddress": "54.1.1.200",
            "Id": "ci-ABCDEFGHIJKL",
            "PrivateIpAddress": "10.10.100.177"
        }
    ]
}

EXPECTED_RESULT = {
    "Cluster": {
        "Ec2InstanceAttributes": {
            "IamInstanceProfile": "EMR_EC2_DefaultRole",
            "Ec2AvailabilityZone": "us-east-1b"
        },
        "Name": "ABCD",
        "TerminationProtected": "false",
        "RunningAmiVersion": "2.4.2",
        "MasterPublicDnsName": "ec2-01-01-1-188.compute-1.amazonaws.com",
        "InstanceGroups": [
            {
                "RequestedInstanceCount": 1,
                "Status": {
                    "Timeline": {
                        "ReadyDateTime": 1398376083.0,
                        "CreationDateTime": 1398375871.0,
                        "EndDateTime": 1398376476.0
                    },
                    "State": "TERMINATED",
                    "StateChangeReason": {
                        "Message": "Job flow terminated",
                        "Code": "CLUSTER_TERMINATED"
                    }
                },
                "RunningInstanceCount": 0,
                "Name": "Master instance group",
                "InstanceGroupType": "MASTER",
                "InstanceType": "m1.large",
                "Market": "ON_DEMAND",
                "Id": "ig-ABCD"
            },
            {
                "RequestedInstanceCount": 2,
                "Status": {
                    "Timeline": {
                        "ReadyDateTime": 1398376089.0,
                        "CreationDateTime": 1398375871.0,
                        "EndDateTime": 1398376476.0
                    },
                    "State": "TERMINATED",
                    "StateChangeReason": {
                        "Message": "Job flow terminated",
                        "Code": "CLUSTER_TERMINATED"
                    }
                },
                "RunningInstanceCount": 0,
                "Name": "Core instance group",
                "InstanceGroupType": "CORE",
                "InstanceType": "m1.large",
                "Market": "ON_DEMAND",
                "Id": "ig-DEF"
            }
        ],
        "RequestedAmiVersion": "2.4.2",
        "AutoTerminate": "false",
        "LogUri": "s3n://abc/logs/",
        "Status": {
            "Timeline": {
                "ReadyDateTime": 1398376089.0,
                "CreationDateTime": 1398375871.0,
                "EndDateTime": 1398376477.0
            },
            "State": "TERMINATED",
            "StateChangeReason": {
                "Message": "Terminated by user request",
                "Code": "USER_REQUEST"
            }
        },
        "Tags": [],
        "Applications": [
            {
                "Version": "1.0.3",
                "Name": "hadoop"
            }
        ],
        "VisibleToAllUsers": "true",
        "BootstrapActions": [
            {
                "Args": [],
                "Name": "Install HBase",
                "ScriptPath": "s3://elasticmapreduce/bootstrap-actions/"
                              "setup-hbase"
            }
        ],
        "Id": "j-ABCD"
    }
}


class TestDescribeCluster(BaseAWSCommandParamsTest):
    prefix = 'emr describe-cluster'

    @patch('awscli.customizations.emr.emr.DescribeCluster._construct_result')
    @patch('awscli.customizations.emr.emr.'
           'DescribeCluster._find_master_public_dns')
    def test_operations_called(
            self, find_master_public_dns_patch,
            construct_result_patch):
        find_master_public_dns_patch.return_value = \
            list_instances_result_mock["Instances"][0]['PublicDnsName']
        construct_result_patch.return_value = dict()

        args = ' --cluster-id j-ABCD'
        cmdline = self.prefix + args

        self.run_cmd(cmdline, expected_rc=0)

        self.assertEqual(len(self.operations_called), 3)
        self.assertEqual(self.operations_called[0][0].name,
                         'DescribeCluster')
        self.assertEqual(self.operations_called[0][1]['ClusterId'],
                         'j-ABCD')

        self.assertEqual(self.operations_called[1][0].name,
                         'ListInstanceGroups')
        self.assertEqual(self.operations_called[1][1]['ClusterId'],
                         'j-ABCD')

        self.assertEqual(self.operations_called[2][0].name,
                         'ListBootstrapActions')
        self.assertEqual(self.operations_called[2][1]['ClusterId'],
                         'j-ABCD')

    @patch('awscli.customizations.emr.emrutils._find_most_recently_created')
    @patch('awscli.customizations.emr.emr.DescribeCluster._call')
    def test_constructed_result(
            self, call_patch, find_most_recently_created_instance_patch):
        find_most_recently_created_instance_patch.return_value = \
            list_instances_result_mock['Instances'][0]

        call_patch.side_effect = side_effect_of_call

        args = ' --cluster-id j-ABCD'
        cmdline = self.prefix + args
        result = self.run_cmd(cmdline, expected_rc=0)
        result_json = json.loads(result[0])
        self.assertEquals(result_json, EXPECTED_RESULT)


def side_effect_of_call(*args, **kwargs):
    if args[1] == 'describe_cluster':
        return describe_cluster_result_mock
    elif args[1] == 'list_instance_groups':
        return list_instance_groups_result_mock
    elif args[1] == 'list_bootstrap_actions':
        return list_bootstrap_actions_result_mock
    elif args[1] == 'list_instances':
        return list_instances_result_mock


if __name__ == "__main__":
    unittest.main()
