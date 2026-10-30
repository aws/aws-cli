**To describe the available lifecycle hook types**

The following ``describe-lifecycle-hook-types`` example describes the available lifecycle hook types. ::

    aws autoscaling describe-lifecycle-hook-types

Output::

    {
        "LifecycleHookTypes": [
            "autoscaling:EC2_INSTANCE_LAUNCHING",
            "autoscaling:EC2_INSTANCE_TERMINATING"
        ]
    }

For more information, see `Amazon EC2 Auto Scaling lifecycle hooks <https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.
