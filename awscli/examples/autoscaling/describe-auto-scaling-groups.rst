**Example 1: To describe the specified Auto Scaling group**

The following ``describe-auto-scaling-groups`` example describes the specified Auto Scaling group. ::

    aws autoscaling describe-auto-scaling-groups \
        --auto-scaling-group-names my-asg

Output::

    {
        "AutoScalingGroups": [
            {
                "AutoScalingGroupName": "my-asg",
                "AutoScalingGroupARN": "arn:aws:autoscaling:us-west-2:123456789012:autoScalingGroup:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111:autoScalingGroupName/my-asg",
                "LaunchTemplate": {
                    "LaunchTemplateName": "my-launch-template",
                    "Version": "1",
                    "LaunchTemplateId": "lt-1234567890abcde12"
                },
                "MinSize": 0,
                "MaxSize": 1,
                "DesiredCapacity": 1,
                "DefaultCooldown": 300,
                "AvailabilityZones": [
                    "us-west-2a",
                    "us-west-2b",
                    "us-west-2c"
                ],
                "LoadBalancerNames": [],
                "TargetGroupARNs": [],
                "HealthCheckType": "EC2",
                "HealthCheckGracePeriod": 0,
                "Instances": [
                    {
                        "InstanceId": "i-06905f55584de02da",
                        "InstanceType": "t2.micro",
                        "AvailabilityZone": "us-west-2a",
                        "HealthStatus": "Healthy",
                        "LifecycleState": "InService",
                        "ProtectedFromScaleIn": false,
                        "LaunchTemplate": {
                            "LaunchTemplateName": "my-launch-template",
                            "Version": "1",
                            "LaunchTemplateId": "lt-1234567890abcde12"
                        }
                    }
                ],
                "CreatedTime": "2023-10-28T02:39:22.152Z",
                "SuspendedProcesses": [],
                "VPCZoneIdentifier": "subnet-5ea0c127,subnet-6194ea3b,subnet-c934b782",
                "EnabledMetrics": [],
                "Tags": [],
                "TerminationPolicies": [
                    "Default"
                ],
                "NewInstancesProtectedFromScaleIn": false,
                "ServiceLinkedRoleARN": "arn:aws:iam::123456789012:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling",
                "TrafficSources": []
            }
        ]
    }

**Example 2: To describe the first 100 specified Auto Scaling group**

The following ``describe-auto-scaling-groups`` example describes the specified Auto Scaling groups. It allows you to specify up to 100 group names. ::

    aws autoscaling describe-auto-scaling-groups \
        --max-items 100 \
        --auto-scaling-group-names "group1" "group2" "group3" "group4"

Output::

    {
        "AutoScalingGroups": [
            {
                "AutoScalingGroupName": "group1",
                "AutoScalingGroupARN": "arn:aws:autoscaling:us-west-2:123456789012:autoScalingGroup:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111:autoScalingGroupName/group1",
                "LaunchTemplate": {
                    "LaunchTemplateName": "my-launch-template",
                    "Version": "1",
                    "LaunchTemplateId": "lt-1234567890abcde12"
                },
                "MinSize": 0,
                "MaxSize": 1,
                "DesiredCapacity": 0,
                "DefaultCooldown": 300,
                "AvailabilityZones": [
                    "us-west-2a",
                    "us-west-2b",
                    "us-west-2c"
                ],
                "LoadBalancerNames": [],
                "TargetGroupARNs": [],
                "HealthCheckType": "EC2",
                "HealthCheckGracePeriod": 0,
                "Instances": [],
                "CreatedTime": "2023-10-28T02:39:22.152Z",
                "SuspendedProcesses": [],
                "VPCZoneIdentifier": "subnet-5ea0c127,subnet-6194ea3b,subnet-c934b782",
                "EnabledMetrics": [],
                "Tags": [],
                "TerminationPolicies": [
                    "Default"
                ],
                "NewInstancesProtectedFromScaleIn": false,
                "ServiceLinkedRoleARN": "arn:aws:iam::123456789012:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling",
                "TrafficSources": []
            },
            {
                "AutoScalingGroupName": "group2",
                "AutoScalingGroupARN": "arn:aws:autoscaling:us-west-2:123456789012:autoScalingGroup:a1b2c3d4-5678-90ab-cdef-EXAMPLE22222:autoScalingGroupName/group2",
                "LaunchTemplate": {
                    "LaunchTemplateName": "my-launch-template",
                    "Version": "1",
                    "LaunchTemplateId": "lt-1234567890abcde12"
                },
                "MinSize": 0,
                "MaxSize": 1,
                "DesiredCapacity": 0,
                "DefaultCooldown": 300,
                "AvailabilityZones": [
                    "us-west-2a",
                    "us-west-2b",
                    "us-west-2c"
                ],
                "LoadBalancerNames": [],
                "TargetGroupARNs": [],
                "HealthCheckType": "EC2",
                "HealthCheckGracePeriod": 0,
                "Instances": [],
                "CreatedTime": "2023-10-28T02:39:22.152Z",
                "SuspendedProcesses": [],
                "VPCZoneIdentifier": "subnet-5ea0c127,subnet-6194ea3b,subnet-c934b782",
                "EnabledMetrics": [],
                "Tags": [],
                "TerminationPolicies": [
                    "Default"
                ],
                "NewInstancesProtectedFromScaleIn": false,
                "ServiceLinkedRoleARN": "arn:aws:iam::123456789012:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling",
                "TrafficSources": []
            },
            {
                "AutoScalingGroupName": "group3",
                "AutoScalingGroupARN": "arn:aws:autoscaling:us-west-2:123456789012:autoScalingGroup:a1b2c3d4-5678-90ab-cdef-EXAMPLE33333:autoScalingGroupName/group3",
                "LaunchTemplate": {
                    "LaunchTemplateName": "my-launch-template",
                    "Version": "1",
                    "LaunchTemplateId": "lt-1234567890abcde12"
                },
                "MinSize": 0,
                "MaxSize": 1,
                "DesiredCapacity": 0,
                "DefaultCooldown": 300,
                "AvailabilityZones": [
                    "us-west-2a",
                    "us-west-2b",
                    "us-west-2c"
                ],
                "LoadBalancerNames": [],
                "TargetGroupARNs": [],
                "HealthCheckType": "EC2",
                "HealthCheckGracePeriod": 0,
                "Instances": [],
                "CreatedTime": "2023-10-28T02:39:22.152Z",
                "SuspendedProcesses": [],
                "VPCZoneIdentifier": "subnet-5ea0c127,subnet-6194ea3b,subnet-c934b782",
                "EnabledMetrics": [],
                "Tags": [],
                "TerminationPolicies": [
                    "Default"
                ],
                "NewInstancesProtectedFromScaleIn": false,
                "ServiceLinkedRoleARN": "arn:aws:iam::123456789012:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling",
                "TrafficSources": []
            },
            {
                "AutoScalingGroupName": "group4",
                "AutoScalingGroupARN": "arn:aws:autoscaling:us-west-2:123456789012:autoScalingGroup:a1b2c3d4-5678-90ab-cdef-EXAMPLE44444:autoScalingGroupName/group4",
                "LaunchTemplate": {
                    "LaunchTemplateName": "my-launch-template",
                    "Version": "1",
                    "LaunchTemplateId": "lt-1234567890abcde12"
                },
                "MinSize": 0,
                "MaxSize": 1,
                "DesiredCapacity": 0,
                "DefaultCooldown": 300,
                "AvailabilityZones": [
                    "us-west-2a",
                    "us-west-2b",
                    "us-west-2c"
                ],
                "LoadBalancerNames": [],
                "TargetGroupARNs": [],
                "HealthCheckType": "EC2",
                "HealthCheckGracePeriod": 0,
                "Instances": [],
                "CreatedTime": "2023-10-28T02:39:22.152Z",
                "SuspendedProcesses": [],
                "VPCZoneIdentifier": "subnet-5ea0c127,subnet-6194ea3b,subnet-c934b782",
                "EnabledMetrics": [],
                "Tags": [],
                "TerminationPolicies": [
                    "Default"
                ],
                "NewInstancesProtectedFromScaleIn": false,
                "ServiceLinkedRoleARN": "arn:aws:iam::123456789012:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling",
                "TrafficSources": []
            }
        ]
    }

**Example 3: To describe an Auto Scaling group in the specified region**

The following ``describe-auto-scaling-groups`` example describes the Auto Scaling groups in the specified region, up to a maximum of 75 groups. ::

    aws autoscaling describe-auto-scaling-groups \
        --max-items 75 \
        --region us-west-2

Output::

    {
        "AutoScalingGroups": [
            {
                "AutoScalingGroupName": "my-asg",
                "AutoScalingGroupARN": "arn:aws:autoscaling:us-west-2:123456789012:autoScalingGroup:a1b2c3d4-5678-90ab-cdef-EXAMPLE55555:autoScalingGroupName/my-asg",
                "LaunchTemplate": {
                    "LaunchTemplateName": "my-launch-template",
                    "Version": "1",
                    "LaunchTemplateId": "lt-0123456789abcdef0"
                },
                "MinSize": 0,
                "MaxSize": 1,
                "DesiredCapacity": 1,
                "DefaultCooldown": 300,
                "AvailabilityZones": [
                    "us-west-2a",
                    "us-west-2b",
                    "us-west-2c"
                ],
                "LoadBalancerNames": [],
                "TargetGroupARNs": [],
                "HealthCheckType": "EC2",
                "HealthCheckGracePeriod": 0,
                "Instances": [
                    {
                        "InstanceId": "i-0123456789abcdef0",
                        "InstanceType": "t2.micro",
                        "AvailabilityZone": "us-west-2a",
                        "HealthStatus": "Healthy",
                        "LifecycleState": "InService",
                        "ProtectedFromScaleIn": false,
                        "LaunchTemplate": {
                            "LaunchTemplateName": "my-launch-template",
                            "Version": "1",
                            "LaunchTemplateId": "lt-0123456789abcdef0"
                        }
                    }
                ],
                "CreatedTime": "2023-10-28T02:39:22.152Z",
                "SuspendedProcesses": [],
                "VPCZoneIdentifier": "subnet-0a1b2c3d4e5f60001,subnet-0a1b2c3d4e5f60002,subnet-0a1b2c3d4e5f60003",
                "EnabledMetrics": [],
                "Tags": [],
                "TerminationPolicies": [
                    "Default"
                ],
                "NewInstancesProtectedFromScaleIn": false,
                "ServiceLinkedRoleARN": "arn:aws:iam::123456789012:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling",
                "TrafficSources": []
            }
        ]
    }

**Example 4: To describe the specified number of Auto Scaling group**

The following ``describe-auto-scaling-groups`` example uses the ``--max-items`` option to return a specific number of Auto Scaling groups. ::

    aws autoscaling describe-auto-scaling-groups \
        --max-items 1

Output::

    {
        "AutoScalingGroups": [
            {
                "AutoScalingGroupName": "my-asg",
                "AutoScalingGroupARN": "arn:aws:autoscaling:us-west-2:123456789012:autoScalingGroup:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111:autoScalingGroupName/my-asg",
                "LaunchTemplate": {
                    "LaunchTemplateName": "my-launch-template",
                    "Version": "1",
                    "LaunchTemplateId": "lt-1234567890abcde12"
                },
                "MinSize": 0,
                "MaxSize": 1,
                "DesiredCapacity": 1,
                "DefaultCooldown": 300,
                "AvailabilityZones": [
                    "us-west-2a",
                    "us-west-2b",
                    "us-west-2c"
                ],
                "LoadBalancerNames": [],
                "TargetGroupARNs": [],
                "HealthCheckType": "EC2",
                "HealthCheckGracePeriod": 0,
                "Instances": [
                    {
                        "InstanceId": "i-06905f55584de02da",
                        "InstanceType": "t2.micro",
                        "AvailabilityZone": "us-west-2a",
                        "HealthStatus": "Healthy",
                        "LifecycleState": "InService",
                        "ProtectedFromScaleIn": false,
                        "LaunchTemplate": {
                            "LaunchTemplateName": "my-launch-template",
                            "Version": "1",
                            "LaunchTemplateId": "lt-1234567890abcde12"
                        }
                    }
                ],
                "CreatedTime": "2023-10-28T02:39:22.152Z",
                "SuspendedProcesses": [],
                "VPCZoneIdentifier": "subnet-5ea0c127,subnet-6194ea3b,subnet-c934b782",
                "EnabledMetrics": [],
                "Tags": [],
                "TerminationPolicies": [
                    "Default"
                ],
                "NewInstancesProtectedFromScaleIn": false,
                "ServiceLinkedRoleARN": "arn:aws:iam::123456789012:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling",
                "TrafficSources": []
            }
        ],
        "NextToken": "Z3M3LMPEXAMPLE"
    }

If the output includes a ``NextToken`` field, there are more groups. To get the additional groups, use the value of this field with the ``--starting-token`` option in a subsequent call as follows. ::

    aws autoscaling describe-auto-scaling-groups \
        --starting-token Z3M3LMPEXAMPLE

See example 1 for sample output.

**Example 5: To describe Auto Scaling groups that use launch configurations**

The following ``describe-auto-scaling-groups`` example uses the ``--query`` option to describe Auto Scaling groups that use launch configurations. ::

    aws autoscaling describe-auto-scaling-groups \
        --query 'AutoScalingGroups[?LaunchConfigurationName!=`null`]'

Output::

    [
        {
            "AutoScalingGroupName": "my-asg",
            "AutoScalingGroupARN": "arn:aws:autoscaling:us-west-2:123456789012:autoScalingGroup:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111:autoScalingGroupName/my-asg",
            "LaunchConfigurationName": "my-lc",
            "MinSize": 0,
            "MaxSize": 1,
            "DesiredCapacity": 1,
            "DefaultCooldown": 300,
            "AvailabilityZones": [
                "us-west-2a",
                "us-west-2b",
                "us-west-2c"
            ],
            "LoadBalancerNames": [],
            "TargetGroupARNs": [],
            "HealthCheckType": "EC2",
            "HealthCheckGracePeriod": 0,
            "Instances": [
                {
                    "InstanceId": "i-088c57934a6449037",
                    "InstanceType": "t2.micro",
                    "AvailabilityZone": "us-west-2c",
                    "HealthStatus": "Healthy",
                    "LifecycleState": "InService",
                    "LaunchConfigurationName": "my-lc",
                    "ProtectedFromScaleIn": false
                }
            ],
            "CreatedTime": "2023-10-28T02:39:22.152Z",
            "SuspendedProcesses": [],
            "VPCZoneIdentifier": "subnet-5ea0c127,subnet-6194ea3b,subnet-c934b782",
            "EnabledMetrics": [],
            "Tags": [],
            "TerminationPolicies": [
                "Default"
            ],
            "NewInstancesProtectedFromScaleIn": false,
            "ServiceLinkedRoleARN": "arn:aws:iam::123456789012:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling",
            "TrafficSources": []
        }
    ]

For more information, see `Filter AWS CLI output <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-filter.html>`__ in the *AWS Command Line Interface User Guide*.