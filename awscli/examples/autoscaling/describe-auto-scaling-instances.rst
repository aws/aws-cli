**To describe one or more instances**

This example describes the specified instance::

    aws autoscaling describe-auto-scaling-instances --instance-ids i-4ba0837f

The following is example output::

  {
    "AutoScalingInstances": [
        {
            "InstanceId": "i-4ba0837f",
            "HealthStatus": "HEALTHY",
            "AvailabilityZone": "us-west-2c",
            "AutoScalingGroupName": "my-asg",
            "LifecycleState": "InService"
        }
    ]
  }

This example uses the ``max-items`` parameter to specify how many instances to return with this call::

	aws autoscaling describe-auto-scaling-instances --max-items 1

The following is example output::

  {
    "NextToken": "None___1",
    "AutoScalingInstances": [
        {
            "InstanceId": "i-4ba0837f",
            "HealthStatus": "HEALTHY",
            "AvailabilityZone": "us-west-2c",
            "AutoScalingGroupName": "my-asg",
            "LifecycleState": "InService"
        }
    ]
  }

Notice that the output for this command includes a ``NextToken`` field, which indicates that there are more instances. You can use the value of this field with the ``starting-token`` parameter as follows to return additional instances::

    aws autoscaling describe-auto-scaling-instances --starting-token None___1
