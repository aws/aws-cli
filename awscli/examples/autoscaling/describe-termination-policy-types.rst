**To describe termination policy types**

This example describes the available termination policy types::

    aws autoscaling describe-termination-policy-types

The following is example output::

    {
        "TerminationPolicyTypes": [
            "AllocationStrategy",
            "ClosestToNextInstanceHour",
            "Default",
            "NewestInstance",
            "OldestInstance",
            "OldestLaunchConfiguration",
            "OldestLaunchTemplate"
        ]
    }

For more information, see `Controlling Which Instances Auto Scaling Terminates During Scale In`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Controlling Which Instances Auto Scaling Terminates During Scale In`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-instance-termination.html
