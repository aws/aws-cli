**To get a description of all the specified instances**

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

To return a specific number of instances with this command, use the ``max-items`` parameter::

	aws autoscaling describe-auto-scaling-instances --max-items 1

This command returns a JSON block that includes a ``NextToken`` field. You can use the value of this field with the ``starting-token`` parameter to return additional Auto Scaling instances::

    aws autoscaling describe-auto-scaling-instances --starting-token None___1

For more information, see `Basic Auto Scaling Configuration`_ in the *Auto Scaling Developer Guide*.

.. _`Basic Auto Scaling Configuration`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/US_BasicSetup.html

