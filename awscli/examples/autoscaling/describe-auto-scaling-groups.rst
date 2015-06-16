**To get a description of an Auto Scaling group**

This example describes the specified Auto Scaling group::

    aws autoscaling describe-auto-scaling-groups --auto-scaling-group-name my-asg

The following is example output::

    {
        "AutoScalingGroups": [
           {
              "AutoScalingGroupARN": "arn:aws:autoscaling:us-west-2:123456789012:autoScalingGroup:930d940e-891e-4781-a11a-7b0acd480f03:autoScalingGroupName/my-asg",
              "HealthCheckGracePeriod": 0,
              "SuspendedProcesses": [],
              "DesiredCapacity": 1,
              "Tags": [],
              "EnabledMetrics": [],
              "LoadBalancerNames": [],
              "AutoScalingGroupName": "my-test-asg",
              "DefaultCooldown": 300,
              "MinSize": 0,
              "Instances": [
                  {
                      "InstanceId": "i-4ba0837f",
                      "AvailabilityZone": "us-west-2c",
                      "HealthStatus": "Healthy",
                      "LifecycleState": "InService",
                      "LaunchConfigurationName": "my-test-lc"
                   }
               ],
               "MaxSize": 1,
               "VPCZoneIdentifier": null,
               "TerminationPolicies": [
                     "Default"
               ],
               "LaunchConfigurationName": "my-test-lc",
               "CreatedTime": "2013-08-19T20:53:25.584Z",
               "AvailabilityZones": [
                   "us-west-2c"
               ],
               "HealthCheckType": "EC2"
           }
        ]
    }

To return a specific number of Auto Scaling groups with this command, use the ``max-items`` parameter::

    aws autoscaling describe-auto-scaling-groups --max-items 1

If the output for this command includes a ``NextToken`` field, it indicates that there are more groups. You can use the value of this field with the ``starting-token`` parameter to return additional groups::

    aws autoscaling describe-auto-scaling-groups --starting-token None___1
