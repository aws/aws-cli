**To describe your lifecycle hooks**

This example describes the lifecycle hooks for the specified Auto Scaling group::

    aws autoscaling describe-lifecycle-hooks --auto-scaling-group-name my-auto-scaling-group

The following is example output::

    {
        "LifecycleHooks": [
            {
                "GlobalTimeout": 172800,
                "HeartbeatTimeout": 3600,
                "RoleARN": "arn:aws:iam::123456789012:role/my-auto-scaling-role",
                "AutoScalingGroupName": "my-auto-scaling-group",
                "LifecycleHookName": "my-lifecycle-hook",
                "DefaultResult": "ABANDON",
                "NotificationTargetARN": "arn:aws:sns:us-west-2:123456789012:my-sns-topic",
                "LifecycleTransition": "autoscaling:EC2_INSTANCE_LAUNCHING"
            }
        ]
    }
