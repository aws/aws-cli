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
                "AutoScalingGroupName": "my-auto-scaling-group",
                "LifecycleState": "InService"
            }
        ]
    }

This example uses the ``max-items`` parameter to specify how many instances to return with this call::

    aws autoscaling describe-auto-scaling-instances --max-items 1

The following is example output::

    {
        "NextToken": "Z3M3LMPEXAMPLE",
        "AutoScalingInstances": [
            {
                "InstanceId": "i-4ba0837f",
                "HealthStatus": "HEALTHY",
                "AvailabilityZone": "us-west-2c",
                "AutoScalingGroupName": "my-auto-scaling-group",
                "LifecycleState": "InService"
            }
        ]
    }

If the output includes a ``NextToken`` field, there are more instances. To get the additional instances, use the value of this field with the ``starting-token`` parameter in a subsequent call as follows::

    aws autoscaling describe-auto-scaling-instances --starting-token Z3M3LMPEXAMPLE
