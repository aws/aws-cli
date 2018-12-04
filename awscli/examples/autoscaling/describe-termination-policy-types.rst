**To describe termination policy types**

This example describes the available termination policy types::

    aws autoscaling describe-termination-policy-types

The following is example output::

    {
        "TerminationPolicyTypes": [
            "ClosestToNextInstanceHour",
            "Default",
            "NewestInstance",
            "OldestInstance",
            "OldestLaunchConfiguration"
        ]
    }

For more information, see `Controlling Which Instances Auto Scaling Terminates During Scale In`_ in the *Auto Scaling Developer Guide*.

.. _`Controlling Which Instances Auto Scaling Terminates During Scale In`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/AutoScalingBehavior.InstanceTermination.html#your-termination-policy
