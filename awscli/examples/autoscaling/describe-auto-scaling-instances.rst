**To get description of all the specified instances**

The following ``describe-auto-scaling-instances`` command describes all the specified instances::

    aws autoscaling describe-auto-scaling-instances --instance-ids i-4ba0837f

The output of this command is a JSON block that describes the specified instances, similar to the following::

    {
       "AutoScalingInstances": [
           {
               "AvailabilityZone": "us-west-2c",
               "InstanceId": "i-4ba0837f",
               "AutoScalingGroupName": "my-test-asg",
               "HealthStatus": "HEALTHY",
               "LifecycleState": "InService",
               "LaunchConfigurationName": "my-test-lc"
           }
       ]
    }

For more information, see `Basic Auto Scaling Configuration`_ in the *Auto Scaling Developer Guide*.

.. _`Basic Auto Scaling Configuration`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/US_BasicSetup.html

