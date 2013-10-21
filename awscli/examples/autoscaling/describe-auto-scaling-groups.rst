**To get description of an Auto Scaling group**

The following ``describe-auto-scaling-groups`` command describes the specified Auto Scaling group::

    aws autoscaling describe-auto-scaling-groups --auto-scaling-group-name my-test-asg

The output of this command is a JSON block that describes the Auto Scaling group, similar to the following::

    {
        "AutoScalingGroups": [
           {
              "AutoScalingGroupARN": "arn:aws:autoscaling:us-west-2:803981987763:autoScalingGroup:930d940e-891e-4781-a11a-7b0acd480f03:autoScalingGroupName/my-test-asg",
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

For more information, see `Basic Auto Scaling Configuration`_ in the *Auto Scaling Developer Guide*.

.. _`Basic Auto Scaling Configuration`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/US_BasicSetup.html

