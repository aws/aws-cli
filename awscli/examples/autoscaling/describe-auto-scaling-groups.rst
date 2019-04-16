**To get a description of an Auto Scaling group**

This example describes the specified Auto Scaling group::

    aws autoscaling describe-auto-scaling-groups --auto-scaling-group-name my-auto-scaling-group

This example describes the specified Auto Scaling groups. It allows you to specify up to 100 group names::

    aws autoscaling describe-auto-scaling-groups --max-items 100 --auto-scaling-group-name "group1" "group2" "group3" "group4"

This example describes the Auto Scaling groups in the specified region, up to a maximum of 75 groups::

    aws autoscaling describe-auto-scaling-groups --max-items 75 --region us-east-1

The following is example output::

    {
        "AutoScalingGroups": [
            {
                "AutoScalingGroupARN": "arn:aws:autoscaling:us-west-2:123456789012:autoScalingGroup:930d940e-891e-4781-a11a-7b0acd480f03:autoScalingGroupName/my-auto-scaling-group",
                "HealthCheckGracePeriod": 300,
                "SuspendedProcesses": [],
                "DesiredCapacity": 1,
                "Tags": [],
                "EnabledMetrics": [],
                "LoadBalancerNames": [],
                "AutoScalingGroupName": "my-auto-scaling-group",
                "DefaultCooldown": 300,
                "MinSize": 0,
                "Instances": [
                    {
                        "InstanceId": "i-4ba0837f",
                        "AvailabilityZone": "us-west-2c",
                        "HealthStatus": "Healthy",
                        "LifecycleState": "InService",
                        "LaunchConfigurationName": "my-launch-config"
                    }
                ],
                "MaxSize": 1,
                "VPCZoneIdentifier": null,
                "TerminationPolicies": [
                    "Default"
                ],
                "LaunchConfigurationName": "my-launch-config",
                "CreatedTime": "2013-08-19T20:53:25.584Z",
                "AvailabilityZones": [
                    "us-west-2c"
                ],
                "HealthCheckType": "EC2",
                "NewInstancesProtectedFromScaleIn": false
            }
        ]
    }

To return a specific number of Auto Scaling groups, use the ``max-items`` parameter::

    aws autoscaling describe-auto-scaling-groups --max-items 1

If the output includes a ``NextToken`` field, there are more groups. To get the additional groups, use the value of this field with the ``starting-token`` parameter in a subsequent call as follows::

    aws autoscaling describe-auto-scaling-groups --starting-token Z3M3LMPEXAMPLE
